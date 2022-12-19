import json
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import connection
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
import stripe
from django.utils import timezone
from django.views import View
from rest_framework import serializers
from stripe.error import InvalidRequestError

from BaseBillet.models import Configuration, LigneArticle, Paiement_stripe, Reservation, Price, PriceSold
from django.utils.translation import gettext, gettext_lazy as _

import logging

from root_billet.models import RootConfiguration

logger = logging.getLogger(__name__)
User = get_user_model()


class creation_paiement_stripe():

    def __init__(self,
                 user: User,
                 liste_ligne_article: list,
                 metadata: dict,
                 reservation: (Reservation, None),
                 source: str,
                 absolute_domain: (str, None),
                 invoice=None,
                 ) -> None:

        self.fee = 0
        self.application_fee_percent = None
        self.get_fee_in_subscription = {}
        self.user = user
        self.email_paiement = user.email
        self.absolute_domain = absolute_domain
        self.invoice = invoice
        self.liste_ligne_article = liste_ligne_article
        self.metadata = metadata
        self.reservation = reservation
        self.source = source
        self.configuration = Configuration.get_solo()

        self.total = self._total()
        self.metadata_json = json.dumps(self.metadata)
        self.paiement_stripe_db = self._paiement_stripe_db()
        self.stripe_api_key = self._stripe_api_key()
        self.line_items = self._line_items()
        self.mode = self._mode()
        self.return_url = self._return_url()
        self.checkout_session = self._checkout_session()
        self.suspended_cashless = False

    def _total(self):
        total = 0
        for ligne in self.liste_ligne_article:
            total += float(ligne.qty) * float(ligne.pricesold.prix)
        return total

    def _paiement_stripe_db(self):
        dict_paiement = {
            'user': self.user,
            'total': self.total,
            'metadata_stripe': self.metadata_json,
            'reservation': self.reservation,
            'source': self.source,
            'status': Paiement_stripe.PENDING,
        }

        if self.invoice:
            dict_paiement['invoice_stripe'] = self.invoice.id
            if bool(self.invoice.subscription):
                dict_paiement['subscription'] = self.invoice.subscription

        paiementStripeDb = Paiement_stripe.objects.create(**dict_paiement)

        for ligne_article in self.liste_ligne_article:
            ligne_article: LigneArticle
            ligne_article.paiement_stripe = paiementStripeDb
            ligne_article.save()

        return paiementStripeDb

    def _stripe_api_key(self):
        api_key = RootConfiguration.get_solo().get_stripe_api()
        if api_key:
            stripe.api_key = api_key
            return stripe.api_key
        else:
            raise serializers.ValidationError(_(f"No Stripe Api Key in configuration"))

    def _line_items(self, force=False):
        line_items = []
        for ligne in self.liste_ligne_article:
            ligne: LigneArticle
            line_items.append(
                {
                    "price": f"{ligne.pricesold.get_id_price_stripe(force=force)}",
                    "quantity": int(ligne.qty),
                }
            )

            # Si on a un article don
            if ligne.pricesold.price.product.categorie_article == ligne.pricesold.price.product.DON :
                self.fee += Decimal(ligne.qty)

            if ligne.pricesold.gift :
                # C'est un paiement récurent, Stripe n'accepte que les pourcentages.
                if ligne.pricesold.price.recurring_payment :
                    # On calcule le pourcentage de gift dans le prix du paiement :
                    self.application_fee_percent = int(round((Decimal(ligne.pricesold.gift) * 100 ) / Decimal(ligne.pricesold.prix),2))
                    logger.info(f"application_fee_percent : {self.application_fee_percent}")

                # C'est un paiement en une seule fois :
                else:
                    self.fee += Decimal(ligne.pricesold.gift)


            # Si on a une recharge cashless en ligne
            if ligne.pricesold.price.product.categorie_article == ligne.pricesold.price.product.RECHARGE_SUSPENDUE :
                self.suspended_cashless = ligne.qty

        return line_items

    def _mode(self):
        subscription_types = [Price.MONTH, Price.YEAR]
        mode = 'payment'
        for ligne in self.liste_ligne_article:
            price = ligne.pricesold.price
            if price.subscription_type in subscription_types and price.recurring_payment :
                mode = 'subscription'
        return mode

    def _return_url(self):
        '''
        Si la source est le QRCode, alors c'est encore le model MVC de django qui gère ça.
        Sinon, c'est un paiement via la billetterie vue.js
        :return:
        '''

        if self.source == Paiement_stripe.QRCODE:
            return "/api/webhook_stripe/"
        else:
            return "/stripe/return/"


    def _checkout_session(self):
        if self.absolute_domain:
            data_checkout = {
                'success_url': f'{self.absolute_domain}{self.return_url}{self.paiement_stripe_db.uuid}',
                'cancel_url': f'{self.absolute_domain}{self.return_url}{self.paiement_stripe_db.uuid}',
                'payment_method_types': ["card"],
                'customer_email': f'{self.user.email}',
                'line_items': self.line_items,
                'mode': self.mode,
                'metadata': self.metadata,
                'client_reference_id': f"{self.user.pk}",
                'stripe_account' : f"{self.configuration.get_stripe_connect_account()}",
            }

            if self.application_fee_percent :
                subscription_data = {
                    # 'items': [{
                    #     'plan': 'plan_id',
                    # }],
                    'application_fee_percent': self.application_fee_percent,
                }
                data_checkout['subscription_data'] = subscription_data

            #     data_checkout['payment_intent_data'] = {
            #                       'application_fee_percent': f"{self.application_fee_percent}",
            #                   }

            if self.fee > 0:
                amount = int(Decimal(self.fee) * 100)
                data_checkout['payment_intent_data'] = {
                                  'application_fee_amount': f"{amount}",
                              }



            # try:
            checkout_session = stripe.checkout.Session.create(**data_checkout)

            # except InvalidRequestError:
                # L'id stripe est mauvais
                # probablement dû à un changement d'état de test/prod
                # on force là creation de nouvel ID
                # data_checkout['line_items'] = self._line_items(force=True)
                # checkout_session = stripe.checkout.Session.create(**data_checkout)

            logger.info(" ")
            logger.info("-" * 40)
            logger.info(f"Création d'un nouveau paiment stripe. Metadata : {self.metadata}")
            logger.info(f"checkout_session.id {checkout_session.id} payment_intent : {checkout_session.payment_intent}")
            logger.info("-" * 40)
            logger.info(" ")

            self.paiement_stripe_db.payment_intent_id = checkout_session.payment_intent
            self.paiement_stripe_db.checkout_session_id_stripe = checkout_session.id
            self.paiement_stripe_db.status = Paiement_stripe.PENDING
            self.paiement_stripe_db.save()

            return checkout_session

        # Si il n'y a pas d'absolute domain
        return None

    def is_valid(self):
        if self.checkout_session:
            if self.checkout_session.id and \
                    self.checkout_session.url:
                return True

        # Pas besoin de checkout, c'est déja payé.
        if self.invoice:
            return True

        else:
            return False

    def redirect_to_stripe(self):
        if self.checkout_session:
            return HttpResponseRedirect(self.checkout_session.url)
        else:
            return None


def new_entry_from_stripe_invoice(user, id_invoice):
    stripe.api_key = RootConfiguration.get_solo().get_stripe_api()
    invoice = stripe.Invoice.retrieve(id_invoice)

    lines = invoice.lines
    lignes_articles = []
    for line in lines['data']:
        ligne_article = LigneArticle.objects.create(
            pricesold=PriceSold.objects.get(id_price_stripe=line.price.id),
            qty=line.quantity,
        )
        lignes_articles.append(ligne_article)

    metadata = {
        'tenant': f'{connection.tenant.uuid}',
        'from_stripe_invoice': f"{invoice.id}",
    }

    new_paiement_stripe = creation_paiement_stripe(
        user=user,
        liste_ligne_article=lignes_articles,
        metadata=metadata,
        reservation=None,
        source=Paiement_stripe.INVOICE,
        invoice=invoice,
        absolute_domain=None,
    )

    if new_paiement_stripe.is_valid():
        paiement_stripe: Paiement_stripe = new_paiement_stripe.paiement_stripe_db
        paiement_stripe.lignearticle_set.all().update(status=LigneArticle.UNPAID)

        return paiement_stripe


#
# def get_fee_in_subscription(subscription_id, priceSold_id):
#     # On collecte le don dans le paiement récurent.
#
#     stripe.api_key = RootConfiguration.get_solo().get_stripe_api()
#     subscription = stripe.Subscription.retrieve(subscription_id)
#     customer = stripe.Customer.retrieve(subscription.customer)
#     priceSold = PriceSold.objects.get(id=priceSold_id)
#
#     invoice_item = stripe.InvoiceItem.create(
#         customer=customer.id,
#         subscription=subscription_id,
#         amount=int(priceSold.gift * 100),
#         currency='eur',
#         description='Fee for recurring payment',
#     )
#
#     # invoice = stripe.Invoice.create(
#     #     customer=customer.id,
#     #     auto_advance=True,
#     #     collection_method='charge_automatically',
#     #     default_tax_rates=[subscription.default_tax_rates],
#     #     subscription=subscription_id,
#     #     application_fee_amount=subscription.plan.amount,
#     # )
#     return invoice_item