import logging
import time
import uuid
from io import BytesIO
from random import randint

import barcode
import segno
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from django.contrib.messages import MessageFailure
from django.db import connection
from django.http import HttpResponse, HttpRequest, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_POST

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from django_htmx.http import HttpResponseClientRedirect
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from ApiBillet.serializers import get_or_create_price_sold
from AuthBillet.models import TibilletUser, Wallet
from AuthBillet.serializers import MeSerializer
from AuthBillet.utils import get_or_create_user
from AuthBillet.views import activate
from BaseBillet.models import Configuration, Ticket, OptionGenerale, Product, Event, Price, LigneArticle, \
    Paiement_stripe, Membership
from BaseBillet.tasks import create_ticket_pdf, create_invoice_pdf
from BaseBillet.validators import LoginEmailValidator, MembershipValidator, LinkQrCodeValidator
from PaiementStripe.views import CreationPaiementStripe
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.validators import WalletValidator
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def encode_uid(pk):
    return force_str(urlsafe_base64_encode(force_bytes(pk)))


def get_context(request):
    config = Configuration.get_solo()
    base_template = "htmx/partial.html" if request.htmx else "htmx/base.html"
    serialized_user = MeSerializer(request.user).data if request.user.is_authenticated else None

    context = {
        "base_template": base_template,
        "url_name": request.resolver_match.url_name,
        "user": request.user,
        "profile": serialized_user,
        "config": config,
        "header": True,
    }
    return context


class Ticket_html_view(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk_uuid):
        ticket = get_object_or_404(Ticket, uuid=pk_uuid)
        qr = segno.make(f"{ticket.uuid}", micro=False)

        buffer_svg = BytesIO()
        qr.save(buffer_svg, kind="svg", scale=8)

        CODE128 = barcode.get_barcode_class("code128")
        buffer_barcode_SVG = BytesIO()
        bar_secret = encode_uid(f"{ticket.uuid}".split("-")[4])

        bar = CODE128(f"{bar_secret}")
        options = {
            "module_height": 30,
            "module_width": 0.6,
            "font_size": 10,
        }
        bar.write(buffer_barcode_SVG, options=options)

        context = {
            "ticket": ticket,
            "config": Configuration.get_solo(),
            "img_svg": buffer_svg.getvalue().decode("utf-8"),
            # 'img_svg64': base64.b64encode(buffer_svg.getvalue()).decode('utf-8'),
            "bar_svg": buffer_barcode_SVG.getvalue().decode("utf-8"),
            # 'bar_svg64': base64.b64encode(buffer_barcode_SVG.getvalue()).decode('utf-8'),
        }

        return render(request, "ticket/ticket.html", context=context)
        # return render(request, 'ticket/qrtest.html', context=context)


def test_jinja(request):
    context = {
        "list": [1, 2, 3, 4, 5, 6],
        "var1": "",
        "var2": "",
        "var3": "",
        "var4": "hello",
    }
    return TemplateResponse(request, "htmx/views/test_jinja.html", context=context)


# TODO: passer cette méthode en rendu partiel et la requete en htmx
def deconnexion(request):
    # un logout peut-il mal se passer ?
    logout(request)
    messages.add_message(request, messages.SUCCESS, "Déconnexion")
    return redirect('home')


def connexion(request):
    print("-> connexion:")
    if request.method == 'POST':
        validator = LoginEmailValidator(data=request.POST)
        if validator.is_valid():
            # Création de l'user et envoie du mail de validation
            email = validator.validated_data['email']
            user = get_or_create_user(email=email, send_mail=True)
            if settings.DEBUG:
                login(request, user)
                messages.add_message(request, messages.WARNING, "Debug : login auto, Connexion ok.")

            # Le mail a été ernvoyé par le get_or_create_user,
            # on redirige vers la page d'accueil et on leur demande de valider leur email
            context = {
                "modal_message": {
                    "type": "success",
                    "title": "Information",
                    "content": "Pour acceder à votre espace, merci de valider\n"
                               "votre adresse email. Pensez à regarder dans les spams !"
                }
            }
            return render(request, "htmx/components/modal_message.html", context=context)

    messages.add_message(request, messages.WARNING, "Erreur de validation de l'email")
    return redirect('home')


def emailconfirmation(request, uuid, token):
    activate(request, uuid, token)
    return redirect('home')


@require_GET
def home(request):
    template_context = get_context(request)
    template_context['events'] = Event.objects.all()
    return render(request, "htmx/views/home.html", context=template_context)


class ScanQrCode(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]

    def retrieve(self, request, pk=None):
        try:
            qrcode_uuid: uuid.uuid4 = uuid.UUID(pk)
        except ValueError:
            logger.warning("ValueError, not an uuid")
            raise Http404()
        except Exception as e:
            logger.error(e)
            raise e

        fedowAPI = FedowAPI()
        serialized_qrcode_card = fedowAPI.NFCcard.qr_retrieve(qrcode_uuid)
        if not serialized_qrcode_card:
            raise Http404()

        # La carte n'a pas d'user, on redirige vers la page de renseignement d'user
        if serialized_qrcode_card['is_wallet_ephemere']:
            logger.info("Wallet ephemere, on demande le mail")
            template_context = get_context(request)
            template_context['qrcode_uuid'] = qrcode_uuid
            return render(request, "htmx/views/inscription.html", context=template_context)

        wallet = Wallet.objects.get(uuid=serialized_qrcode_card['wallet_uuid'])
        user: TibilletUser = wallet.user
        user.is_active = True
        user.save()
        login(request, user)
        # authenticate(request=request, user=user)
        if not user.email_valid:
            logger.warning("User email not active")
            messages.add_message(request, messages.WARNING, _("Merci de valider votre email pour acceder à toute les fonctionnalitées de votre espace profil."))

        return redirect("/my_account")

    @action(detail=False, methods=['POST'])
    def link(self, request):
        # data=request.POST.dict() in the controler for boolean
        # logger.info(request.POST.dict())
        validator = LinkQrCodeValidator(data=request.POST.dict())
        if not validator.is_valid():
            for error in validator.errors:
                messages.add_message(request, messages.ERROR, f"{error} : {validator.errors[error][0]}")
            return HttpResponseClientRedirect(request.headers['Referer'])

        email = validator.validated_data['email']
        qrcode_uuid = validator.validated_data['qrcode_uuid']
        user = get_or_create_user(email)

        fedowAPI = FedowAPI()
        wallet, created = fedowAPI.wallet.get_or_create_wallet(user)

        # Si l'user possède déja un wallet et n'a pas validé son email,
        # il ne peut pas avoir de deuxième carte :
        if not created :
            retrieve_wallet = fedowAPI.wallet.retrieve_by_signature(user)
            if retrieve_wallet.validated_data['has_user_card']:
                messages.add_message(request, messages.ERROR, _("Vous semblez déja posséder une carte TiBillet en lien avec votre portefeuille. Merci de la révoquer d'abord dans votre espace profil."))
                return HttpResponseClientRedirect(request.headers['Referer'])

        linked_serialized_card = fedowAPI.NFCcard.linkwallet_cardqrcode(user=user, qrcode_uuid=qrcode_uuid)
        if not linked_serialized_card:
            messages.add_message(request, messages.ERROR, _("Not valid"))

        # On retourne sur la page GET /qr/
        # Qui redirigera si besoin, ou afficera l'erreur
        return HttpResponseClientRedirect(request.headers['Referer'])

    def get_permissions(self):
        permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class MyAccount(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [permissions.IsAuthenticated, ]

    def list(self, request: HttpRequest):
        template_context = get_context(request)
        # Pas de header sur cette page
        template_context['header'] = False

        if not request.user.email_valid:
            logger.warning("User email not active")
            messages.add_message(request, messages.WARNING, _("Merci de valider votre email pour acceder à toute les fonctionnalitées de votre espace profil."))

        return render(request, "htmx/views/my_account.html", context=template_context)

    ### ONGLET WALLET

    @action(detail=False, methods=['GET'])
    def wallet(self, request: HttpRequest) -> HttpResponse:
        template_context = get_context(request)
        # Pas de header sur cette page
        template_context['header'] = False
        return render(request, "htmx/fragments/my_account_wallet.html", context=template_context)

    @action(detail=False, methods=['GET'])
    def tokens_table(self, request):
        config = Configuration.get_solo()
        fedowAPI = FedowAPI()
        wallet = fedowAPI.wallet.cached_retrieve_by_signature(request.user).validated_data

        # On retire les adhésions, on les affiche dans l'autre table
        tokens = [token for token in wallet.get('tokens') if token.get('asset_category') != 'SUB']
        context = {
            'config': config,
            'tokens': tokens,
        }

        return render(request, "htmx/fragments/tokens_table.html", context=context)

    @action(detail=False, methods=['GET'])
    def transactions_table(self, request):
        config = Configuration.get_solo()
        fedowAPI = FedowAPI()
        # On utilise ici .data plutot que validated_data pour executer les to_representation (celui du WalletSerializer)
        # et les serializer.methodtruc
        paginated_list_by_wallet_signature = fedowAPI.transaction.paginated_list_by_wallet_signature(
            request.user).validated_data

        transactions = paginated_list_by_wallet_signature.get('results')
        next_url = paginated_list_by_wallet_signature.get('next')
        previous_url = paginated_list_by_wallet_signature.get('previous')

        # On retire les adhésions, on les affiche dans l'autre table
        # tokens = [token for token in wallet.get('tokens') if token.get('asset_category') != 'SUB']
        context = {
            'config': config,
            'transactions': transactions,
            'next_url': next_url,
            'previous_url': previous_url,
        }
        return render(request, "htmx/fragments/transactions_table.html", context=context)

    ### ONGLET ADHESION

    @action(detail=False, methods=['GET'])
    def membership(self, request: HttpRequest) -> HttpResponse:
        context = {}
        return render(request, "htmx/fragments/my_account_membership.html", context=context)

    @action(detail=False, methods=['GET'])
    def membership_table(self, request):
        config = Configuration.get_solo()
        fedowAPI = FedowAPI()
        wallet = fedowAPI.wallet.cached_retrieve_by_signature(request.user).validated_data

        # On ne garde que les adhésions
        tokens = [token for token in wallet.get('tokens') if token.get('asset_category') == 'SUB']

        context = {
            'config': config,
            'tokens': tokens,
        }
        return render(request, "htmx/fragments/tokens_membership_table.html", context=context)

    @action(detail=False, methods=['GET'])
    def profile(self, request: HttpRequest) -> HttpResponse:
        context = {}
        return render(request, "htmx/fragments/my_account_profil.html", context=context)

    #### REFILL STRIPE PRIMARY ####

    @action(detail=False, methods=['GET'])
    def refill_wallet(self, request):
        user = request.user
        fedowAPI = FedowAPI()
        stripe_checkout_url = fedowAPI.wallet.get_federated_token_refill_checkout(user)
        return HttpResponseClientRedirect(stripe_checkout_url)

    @action(detail=True, methods=['GET'])
    def return_refill_wallet(self, request, pk=None):
        # Le paiemetn stripe a été effectué. Stripe redirige ici.
        # On check referer stripe
        if request.headers.get('Referer') != 'https://checkout.stripe.com/':
            logger.error(f"Refill wallet return : Not from stripe")
            messages.add_message(request, messages.ERROR, "Erreur retour stripe")
            return redirect('/memberships/wallet')

        # On demande confirmation à Fedow qui a du recevoir la validation en webhook POST
        user = request.user
        fedowAPI = FedowAPI()

        # pk = checkout_stripe_db_fedow_uuid
        try:
            # TODO; checker la signature du paiement
            wallet = fedowAPI.wallet.retrieve_from_refill_checkout(user, pk)
            messages.add_message(request, messages.SUCCESS, "Wallet rechargé")
        except Exception as e:
            messages.add_message(request, messages.ERROR, "Erreur dans la vérification du paiement.")
        return redirect('/my_account/')

    #### END REFILL STRIPE PRIMARY ####


@require_GET
def event(request: HttpRequest, slug) -> HttpResponse:
    event = get_object_or_404(Event, slug=slug)
    template_context = get_context(request)
    template_context['event'] = event
    return render(request, "htmx/views/event.html", context=template_context)


def validate_event(request):
    if request.method == 'POST':
        print("-> validate_event, méthode POST !")
        # range-start-index - range-end-index, date-index 
        data = dict(request.POST.lists())
        print(f"data = {data}")

        # validé / pas validé retourner un message
        dev_validation = True

        if dev_validation == False:
            messages.add_message(request, messages.WARNING, "Le message d'erreur !")

        if dev_validation == True:
            messages.add_message(request, messages.SUCCESS, "Réservation validée !")

    return redirect('home')


def modal(request, level="info", title='Information', content: str = None):
    context = {
        "modal_message": {
            "type": level,
            "title": title,
            "content": content,
        }
    }
    return render(request, "htmx/components/modal_message.html", context=context)


class MembershipMVT(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]

    def list(self, request: HttpRequest):
        template_context = get_context(request)
        template_context["memberships"] = Product.objects.filter(categorie_article=Product.ADHESION)
        return render(request, "htmx/views/memberships.html", context=template_context)

    def create(self, request):
        membership_validator = MembershipValidator(data=request.data, context={'request': request})
        if not membership_validator.is_valid():
            error_messages = [str(item) for sublist in membership_validator.errors.values() for item in sublist]
            return modal(request, level="warning", content=', '.join(error_messages))

        # Fiche membre créée, si price payant, on crée le checkout stripe :
        membership = membership_validator.membership
        price: Price = membership.price
        user: TibilletUser = membership.user

        metadata = {
            'tenant': f'{connection.tenant.uuid}',
            'pk_adhesion': f"{price.pk}",
            'pk_membership': f"{membership.pk}",
            'pk_user': f"{user.pk}",
        }

        ligne_article_adhesion = LigneArticle.objects.create(
            pricesold=get_or_create_price_sold(price, None),
            qty=1,
        )

        # Création de l'objet paiement stripe en base de donnée
        new_paiement_stripe = CreationPaiementStripe(
            user=user,
            liste_ligne_article=[ligne_article_adhesion, ],
            metadata=metadata,
            reservation=None,
            source=Paiement_stripe.API_BILLETTERIE,
            success_url=f"stripe_return/",
            cancel_url=f"stripe_return/",
            absolute_domain=request.build_absolute_uri(),
        )

        # Passage du status en UNPAID
        if new_paiement_stripe.is_valid():
            paiement_stripe: Paiement_stripe = new_paiement_stripe.paiement_stripe_db
            paiement_stripe.lignearticles.all().update(status=LigneArticle.UNPAID)
            checkout_stripe_url = new_paiement_stripe.checkout_session.url
            return HttpResponseClientRedirect(checkout_stripe_url)

        return modal(request, level="error",
                     content="Erreur lors de la création du paiement, contactez l'administrateur.")

    @action(detail=True, methods=['GET'])
    def stripe_return(self, request, pk, *args, **kwargs):
        paiement_stripe = get_object_or_404(Paiement_stripe, uuid=pk)
        paiement_stripe.update_checkout_status()
        paiement_stripe.refresh_from_db()
        email = paiement_stripe.user.email

        try:
            if paiement_stripe.status == Paiement_stripe.VALID:
                messages.add_message(request, messages.SUCCESS,
                                     f"Votre abonnement a été validé. Vous allez recevoir un mail de confirmation à l'adresse {email}. Merci !")
            elif paiement_stripe.status == Paiement_stripe.PENDING:
                messages.add_message(request, messages.WARNING, f"Votre paiement est en attente de validation.")
            else:
                messages.add_message(request, messages.WARNING,
                                     f"Une erreur est survenue, merci de contacter l'administrateur.")
        except MessageFailure as e:
            # Surement un test unitaire, les messages plantent a travers la Factory Request
            pass
        except Exception as e:
            raise e

        return redirect('/memberships/')

    @action(detail=True, methods=['GET'])
    def invoice(self, request, pk):
        paiement_stripe = get_object_or_404(Paiement_stripe, uuid=pk)
        pdf_binary = create_invoice_pdf(paiement_stripe)
        response = HttpResponse(pdf_binary, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture.pdf"'
        return response

    def get_permissions(self):
        if self.action in ['retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class Espaces:
    def __init__(self, name, description, svg_src, svg_size, colorText, disable, categorie):
        self.name = name
        self.description = description
        self.svg_src = svg_src
        self.svg_size = svg_size
        self.colorText = colorText
        self.disable = disable
        self.categorie = categorie


def tenant_areas(request: HttpRequest) -> HttpResponse:
    espaces = []
    espaces.append(
        Espaces("Lieu / association", "Pour tous lieu ou association ...", "/media/images/home.svg", "4rem", "white",
                False,
                "S"))
    espaces.append(
        Espaces("Artist", "Pour tous lieu ou association ...", "/media/images/artist.svg", "4rem", "white", False,
                "A"))

    if request.method == 'GET':
        context = {
            "espaces": espaces
        }

    if request.method == 'POST':
        # TODO: inputs provenant d'un "validateur" (si erreur valeur = '', sinon valeur = valeur entrée par client
        clientInput = {"email": '', "categorie": 'S'}
        # TODO: errors provenant d'un "validateur"
        errors = {"email": True, "categorie": False}
        context = {
            "espaces": espaces,
            "errors": errors,
            "clientInput": clientInput
        }

    return render(request, "htmx/forms/tenant_areas.html", context=context)


def tenant_informations(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == 'POST':
        # TODO: inputs provenant d'un "validateur" (si erreur valeur = '', sinon valeur = valeur entrée par client
        clientInput = {"organisation": 'Au bon jardin', "short_description": "Mon petit coin de paradis",
                       "long_description": "", "image": "", "logo": ""}
        # TODO: errors provenant d'un "validateur"
        errors = {"organisation": False, "short_description": False, "long_description": True, "image": True,
                  "logo": True, }
        context = {
            "errors": errors,
            "clientInput": clientInput
        }

    return render(request, "htmx/forms/tenant_informations.html", context=context)


def tenant_summary(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == 'POST':
        print(f"requête : {request}")
        # retour modal de sucess ou erreur

    return render(request, "htmx/forms/tenant_summary.html", context=context)


@require_GET
def create_tenant(request: HttpRequest) -> HttpResponse:
    config = Configuration.get_solo()
    base_template = "htmx/partial.html" if request.htmx else "htmx/base.html"

    host = "http://" + request.get_host()
    if request.is_secure():
        host = "https://" + request.get_host()

    # image par défaut
    if hasattr(config.img, 'fhd'):
        header_img = config.img.fhd.url
    else:
        header_img = "/media/images/image_non_disponible.jpg"

    espaces = []
    espaces.append(
        Espaces("Lieu / association", "Pour tous lieu ou association ...", "/media/images/home.svg", "4rem", "white",
                False,
                "S"))
    espaces.append(
        Espaces("Artist", "Pour tous lieu ou association ...", "/media/images/artist.svg", "4rem", "white", False,
                "A"))
    context = {
        "base_template": base_template,
        "host": host,
        "url_name": request.resolver_match.url_name,
        "tenant": config.organisation,
        "configuration": config,
        "header": {
            "img": header_img,
            "title": config.organisation,
            "short_description": config.short_description,
            "long_description": config.long_description
        },
        "memberships": Product.objects.filter(categorie_article="A"),
        "espaces": espaces
    }
    return render(request, "htmx/views/create_tenant.html", context=context)


@require_GET
def create_event(request):
    config = Configuration.get_solo()
    base_template = "htmx/partial.html" if request.htmx else "htmx/base.html"

    host = "http://" + request.get_host()
    if request.is_secure():
        host = "https://" + request.get_host()

    # image par défaut
    if hasattr(config.img, 'fhd'):
        header_img = config.img.fhd.url
    else:
        header_img = "/media/images/image_non_disponible.jpg"

    options = OptionGenerale.objects.all()
    options_list = []
    for ele in options:
        options_list.append({"value": str(ele.uuid), "name": ele.name})

    categorie_list = [
        {"value": "B", "name": "Billet payant"},
        {"value": "P", "name": "Pack d'objets"},
        {"value": "R", "name": "Recharge cashless"},
        {"value": "S", "name": "Recharge suspendue"},
        {"value": "T", "name": "Vetement"},
        {"value": "M", "name": "Merchandasing"},
        {"value": "A", "name": "Abonnement et/ou adhésion associative"},
        {"value": "D", "name": "Don"},
        {"value": "F", "name": "Reservation gratuite"},
        {"value": "V", "name": "Nécessite une validation manuelle"},
    ]

    context = {
        "base_template": base_template,
        "host": host,
        "url_name": request.resolver_match.url_name,
        "tenant": config.organisation,
        "configuration": config,
        "header": None,
        "event_image": "/media/images/image_non_disponible.jpg",
        "options_list": options_list,
        "categorie_list": categorie_list
    }
    return render(request, "htmx/views/create_event.html", context=context)


def event_date(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == 'POST':
        # range-start-index - range-end-index, date-index 
        data = dict(request.POST.lists())
        print(f"data = {data}")
        # - si ok - sauvegarde partielle(uuid event + dates) dans db et retourner le template  "event_presentation.html" (nom, image, descriptions).
        # - si erreur = retourner les bons ranges et dates dans l'ordre adéquate et les erreurs (rester sur template)

    return render(request, "htmx/forms/event_date.html", context=context)


def event_presentation(request: HttpRequest) -> HttpResponse:
    context = {
        "event_image": "/media/images/image_non_disponible.jpg",
    }
    if request.method == 'POST':
        data = dict(request.POST.lists())
        print(f"data = {data}")
        # retour modal de sucess ou erreur

    return render(request, "htmx/forms/event_presentation.html", context=context)


def event_products(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == 'POST':
        data = dict(request.POST.lists())
        print(f"data = {data}")
        # retour modal de sucess ou erreur

    return render(request, "htmx/forms/event_products.html", context=context)
