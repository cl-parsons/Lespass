# Generated by Django 4.2.11 on 2024-04-18 07:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import stdimage.models
import stdimage.validators
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('QrcodeCashless', '0001_initial'),
        ('rest_framework_api_key', '0005_auto_20220110_1102'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('Customers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, max_length=250, null=True, unique=True)),
                ('datetime', models.DateTimeField()),
                ('created', models.DateTimeField(auto_now=True)),
                ('jauge_max', models.PositiveSmallIntegerField(default=50, verbose_name='Jauge maximale')),
                ('max_per_user', models.PositiveSmallIntegerField(default=10, help_text='ex : Un même email peut réserver plusieurs billets.', verbose_name='Nombre de reservation maximum par utilisateur')),
                ('short_description', models.CharField(blank=True, max_length=250, null=True)),
                ('long_description', models.TextField(blank=True, null=True)),
                ('is_external', models.BooleanField(default=False, help_text="Si l'évènement est géré par une autre billetterie ou un autre site de réservation. Ex : Un event Facebook", verbose_name='Billetterie/Reservation externe')),
                ('url_external', models.URLField(blank=True, null=True)),
                ('published', models.BooleanField(default=True, verbose_name='Publier')),
                ('minimum_cashless_required', models.SmallIntegerField(default=0, verbose_name='Montant obligatoire minimum de la recharge cashless')),
                ('img', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MaxSizeValidator(1920, 1920)], variations={'crop': (480, 270, True), 'crop_hdr': (960, 540, True), 'fhd': (1920, 1920), 'hdr': (1280, 1280), 'med': (480, 480), 'thumbnail': (150, 90)})),
                ('categorie', models.CharField(choices=[('LIV', 'Concert'), ('FES', 'Festival'), ('REU', 'Réunion'), ('CON', 'Conférence'), ('RES', 'Restauration')], default='LIV', max_length=3, verbose_name="Catégorie d'évènement")),
                ('booking', models.BooleanField(default=False, help_text="Si activé, l'évènement sera visible en haut de la page d'accueil, l'utilisateur pourra selectionner une date.", verbose_name='Mode restauration/booking')),
            ],
            options={
                'verbose_name': 'Evenement',
                'verbose_name_plural': 'Evenements',
                'ordering': ('datetime',),
            },
        ),
        migrations.CreateModel(
            name='FedowTransaction',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('hash', models.CharField(editable=False, max_length=64, unique=True)),
                ('datetime', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='OptionGenerale',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=30, unique=True)),
                ('description', models.CharField(blank=True, max_length=250, null=True)),
                ('poids', models.PositiveSmallIntegerField(default=0, verbose_name='Poids')),
            ],
            options={
                'verbose_name': 'Option',
                'verbose_name_plural': 'Options',
                'ordering': ('poids',),
            },
        ),
        migrations.CreateModel(
            name='Price',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('short_description', models.CharField(blank=True, max_length=250, null=True)),
                ('long_description', models.TextField(blank=True, null=True)),
                ('name', models.CharField(max_length=50, verbose_name='Précisez le nom du Tarif')),
                ('prix', models.DecimalField(decimal_places=2, max_digits=6)),
                ('vat', models.CharField(choices=[('NA', 'Non applicable'), ('DX', '10 %'), ('VG', '20 %')], default='NA', max_length=2, verbose_name='Taux TVA')),
                ('stock', models.SmallIntegerField(blank=True, null=True)),
                ('max_per_user', models.PositiveSmallIntegerField(default=10, help_text='ex : Un même email peut réserver plusieurs billets', verbose_name='Nombre de reservation maximum par utilisateur')),
                ('subscription_type', models.CharField(choices=[('N', 'Non applicable'), ('Y', '365 Jours'), ('M', '30 Jours'), ('C', 'Civile')], default='N', max_length=1, verbose_name="durée d'abonnement")),
                ('recurring_payment', models.BooleanField(default=False, help_text='Paiement récurrent avec Stripe, Ne peux être utilisé avec un autre article dans le même panier', verbose_name='Paiement récurrent')),
            ],
            options={
                'verbose_name': 'Tarif',
                'verbose_name_plural': 'Tarifs',
                'ordering': ('prix',),
            },
        ),
        migrations.CreateModel(
            name='PriceSold',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('id_price_stripe', models.CharField(blank=True, max_length=30, null=True)),
                ('qty_solded', models.SmallIntegerField(default=0)),
                ('prix', models.DecimalField(decimal_places=2, max_digits=6)),
                ('gift', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('price', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='BaseBillet.price')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=500, verbose_name='Nom')),
                ('short_description', models.CharField(blank=True, max_length=250, null=True, verbose_name='Description courte')),
                ('long_description', models.TextField(blank=True, null=True, verbose_name='Description longue')),
                ('publish', models.BooleanField(default=True)),
                ('poids', models.PositiveSmallIntegerField(default=0, help_text="Ordre d'apparition du plus leger au plus lourd", verbose_name='Poids')),
                ('terms_and_conditions_document', models.URLField(blank=True, null=True)),
                ('legal_link', models.URLField(blank=True, null=True, verbose_name='Mentions légales')),
                ('img', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MaxSizeValidator(1920, 1920)], variations={'crop': (480, 270, True), 'crop_hdr': (960, 540, True), 'fhd': (1920, 1920), 'hdr': (720, 720), 'med': (480, 480), 'thumbnail': (150, 90)}, verbose_name='Image du produit')),
                ('categorie_article', models.CharField(choices=[('N', 'Selectionnez une catégorie'), ('B', 'Billet payant'), ('P', "Pack d'objets"), ('R', 'Recharge cashless'), ('S', 'Recharge suspendue'), ('T', 'Vetement'), ('M', 'Merchandasing'), ('A', 'Abonnement et/ou adhésion associative'), ('D', 'Don'), ('F', 'Reservation gratuite'), ('V', 'Nécessite une validation manuelle')], default='N', max_length=3, verbose_name='Type de produit')),
                ('nominative', models.BooleanField(default=True, help_text='Nom/Prenom obligatoire lors de la réservation.')),
                ('archive', models.BooleanField(default=False)),
                ('send_to_cashless', models.BooleanField(default=False, help_text='Produit checké par le serveur cashless.', verbose_name='Envoyer au cashless')),
                ('option_generale_checkbox', models.ManyToManyField(blank=True, related_name='produits_checkbox', to='BaseBillet.optiongenerale')),
                ('option_generale_radio', models.ManyToManyField(blank=True, related_name='produits_radio', to='BaseBillet.optiongenerale')),
            ],
            options={
                'verbose_name': 'Produit',
                'verbose_name_plural': 'Produits',
                'ordering': ('poids',),
            },
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('C', 'Annulée'), ('R', 'Crée'), ('U', 'Non payée'), ('F', 'Mail non vérifié'), ('FA', 'Mail user vérifié'), ('P', 'Payée'), ('PE', 'Payée mais mail non valide'), ('PN', 'Payée mais mail non envoyé'), ('V', 'Validée')], default='R', max_length=3, verbose_name='Status de la réservation')),
                ('to_mail', models.BooleanField(default=True)),
                ('mail_send', models.BooleanField(default=False)),
                ('mail_error', models.BooleanField(default=False)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reservation', to='BaseBillet.event')),
                ('options', models.ManyToManyField(blank=True, to='BaseBillet.optiongenerale')),
                ('user_commande', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reservations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-datetime',),
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=50, verbose_name='Nom du tag')),
                ('color', models.CharField(default='#000000', max_length=7, verbose_name='Couleur du tag')),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
            },
        ),
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(default=False)),
                ('url', models.URLField()),
                ('event', models.CharField(choices=[('RV', 'Réservation validée')], default='RV', max_length=2, verbose_name='Évènement')),
                ('last_response', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Weekday',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.IntegerField(choices=[(0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')], unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('first_name', models.CharField(max_length=200)),
                ('last_name', models.CharField(max_length=200)),
                ('status', models.CharField(choices=[('C', 'Crée'), ('N', 'Non actif'), ('K', 'Non scanné'), ('S', 'scanné')], default='C', max_length=1, verbose_name='Status du scan')),
                ('seat', models.CharField(default='L', max_length=20)),
                ('pricesold', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='BaseBillet.pricesold')),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='BaseBillet.reservation')),
            ],
            options={
                'verbose_name': 'Réservation',
                'verbose_name_plural': 'Réservations',
            },
        ),
        migrations.CreateModel(
            name='ProductSold',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('id_product_stripe', models.CharField(blank=True, max_length=30, null=True)),
                ('categorie_article', models.CharField(choices=[('N', 'Selectionnez une catégorie'), ('B', 'Billet payant'), ('P', "Pack d'objets"), ('R', 'Recharge cashless'), ('S', 'Recharge suspendue'), ('T', 'Vetement'), ('M', 'Merchandasing'), ('A', 'Abonnement et/ou adhésion associative'), ('D', 'Don'), ('F', 'Reservation gratuite'), ('V', 'Nécessite une validation manuelle')], default='N', max_length=3, verbose_name='Type de produit')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='BaseBillet.event')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='BaseBillet.product')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='tag',
            field=models.ManyToManyField(blank=True, related_name='produit_tags', to='BaseBillet.tag'),
        ),
        migrations.AddField(
            model_name='pricesold',
            name='productsold',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='BaseBillet.productsold'),
        ),
        migrations.AddField(
            model_name='price',
            name='adhesion_obligatoire',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='adhesion_obligatoire', to='BaseBillet.product'),
        ),
        migrations.AddField(
            model_name='price',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='prices', to='BaseBillet.product'),
        ),
        migrations.CreateModel(
            name='Paiement_stripe',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('detail', models.CharField(blank=True, max_length=50, null=True)),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('checkout_session_id_stripe', models.CharField(blank=True, max_length=80, null=True)),
                ('payment_intent_id', models.CharField(blank=True, max_length=80, null=True)),
                ('metadata_stripe', models.JSONField(blank=True, null=True)),
                ('customer_stripe', models.CharField(blank=True, max_length=20, null=True)),
                ('invoice_stripe', models.CharField(blank=True, max_length=27, null=True)),
                ('subscription', models.CharField(blank=True, max_length=28, null=True)),
                ('order_date', models.DateTimeField(auto_now_add=True, verbose_name='Date')),
                ('last_action', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('N', 'Lien de paiement non créé'), ('O', 'Envoyée a Stripe'), ('W', 'En attente de paiement'), ('E', 'Expiré'), ('P', 'Payée'), ('V', 'Payée et validée'), ('S', 'Payée mais problème de synchro cashless'), ('C', 'Annulée')], default='N', max_length=1, verbose_name='Statut de la commande')),
                ('traitement_en_cours', models.BooleanField(default=False)),
                ('source_traitement', models.CharField(choices=[('N', 'Pas de traitement en cours'), ('W', 'Depuis webhook stripe'), ('G', 'Depuis Get'), ('I', 'Depuis webhook invoice')], default='N', max_length=1, verbose_name='Source du traitement')),
                ('source', models.CharField(choices=[('Q', 'Depuis scan QR-Code'), ('B', 'Depuis billetterie'), ('I', 'Depuis invoice')], default='B', max_length=1, verbose_name='Source de la commande')),
                ('total', models.FloatField(default=0)),
                ('fedow_transactions', models.ManyToManyField(blank=True, related_name='paiement_stripe', to='BaseBillet.fedowtransaction')),
                ('reservation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paiements', to='BaseBillet.reservation')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Paiement Stripe',
                'verbose_name_plural': 'Paiements Stripe',
            },
        ),
        migrations.CreateModel(
            name='LigneArticle',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, primary_key=True, serialize=False)),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('qty', models.SmallIntegerField()),
                ('vat', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('status', models.CharField(choices=[('C', 'Annulée'), ('O', 'Non envoyé en paiement'), ('U', 'Non payée'), ('F', 'Reservation gratuite'), ('P', 'Payée'), ('V', 'Validée par serveur cashless')], default='O', max_length=3, verbose_name='Status de ligne article')),
                ('carte', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='QrcodeCashless.cartecashless')),
                ('paiement_stripe', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lignearticles', to='BaseBillet.paiement_stripe')),
                ('pricesold', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='BaseBillet.pricesold')),
            ],
            options={
                'ordering': ('-datetime',),
            },
        ),
        migrations.CreateModel(
            name='ExternalApiKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True)),
                ('ip', models.GenericIPAddressField(verbose_name='Ip source')),
                ('revoquer_apikey', models.BooleanField(default=False, help_text="Selectionnez et validez pour générer ou supprimer une clé API. La clé ne sera affiché qu'a la création, notez la bien !", verbose_name='Créer / Révoquer')),
                ('created', models.DateTimeField(auto_now=True)),
                ('event', models.BooleanField(default=False, verbose_name="Creation d'évènements")),
                ('product', models.BooleanField(default=False, verbose_name='Creation de produits')),
                ('place', models.BooleanField(default=False, verbose_name='Creation de nouvelles instances lieux')),
                ('artist', models.BooleanField(default=False, verbose_name='Creation de nouvelles instances artiste')),
                ('reservation', models.BooleanField(default=False, verbose_name='Lister les reservations')),
                ('ticket', models.BooleanField(default=False, verbose_name='Lister et valider les billets')),
                ('key', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='api_key', to='rest_framework_api_key.apikey')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Api key',
                'verbose_name_plural': 'Api keys',
            },
        ),
        migrations.AddField(
            model_name='event',
            name='options_checkbox',
            field=models.ManyToManyField(blank=True, related_name='options_checkbox', to='BaseBillet.optiongenerale', verbose_name='Options choix multiple'),
        ),
        migrations.AddField(
            model_name='event',
            name='options_radio',
            field=models.ManyToManyField(blank=True, related_name='options_radio', to='BaseBillet.optiongenerale', verbose_name='Option choix unique'),
        ),
        migrations.AddField(
            model_name='event',
            name='products',
            field=models.ManyToManyField(blank=True, to='BaseBillet.product'),
        ),
        migrations.AddField(
            model_name='event',
            name='recurrent',
            field=models.ManyToManyField(blank=True, help_text="Selectionnez le jour de la semaine pour une récurence hebdomadaire. La date de l'évènement sera la date de fin de la récurence.", to='BaseBillet.weekday', verbose_name='Jours de la semaine'),
        ),
        migrations.AddField(
            model_name='event',
            name='tag',
            field=models.ManyToManyField(blank=True, related_name='events', to='BaseBillet.tag'),
        ),
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organisation', models.CharField(db_index=True, max_length=50, verbose_name="Nom de l'organisation")),
                ('slug', models.SlugField(default='')),
                ('short_description', models.CharField(blank=True, max_length=250, null=True, verbose_name='Description courte')),
                ('long_description', models.TextField(blank=True, null=True, verbose_name='Description longue')),
                ('adress', models.CharField(blank=True, max_length=250, null=True, verbose_name='Adresse')),
                ('postal_code', models.IntegerField(blank=True, null=True, verbose_name='Code postal')),
                ('city', models.CharField(blank=True, max_length=250, null=True, verbose_name='Ville')),
                ('tva_number', models.CharField(blank=True, max_length=20, null=True, verbose_name='Numéro de TVA')),
                ('siren', models.CharField(blank=True, max_length=20, null=True, verbose_name='Numéro de SIREN')),
                ('phone', models.CharField(max_length=20, verbose_name='Téléphone')),
                ('email', models.EmailField(max_length=254)),
                ('site_web', models.URLField(blank=True, null=True)),
                ('legal_documents', models.URLField(blank=True, null=True, verbose_name='Statuts associatif')),
                ('twitter', models.URLField(blank=True, null=True)),
                ('facebook', models.URLField(blank=True, null=True)),
                ('instagram', models.URLField(blank=True, null=True)),
                ('map_img', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MaxSizeValidator(1920, 1920)], variations={'fhd': (1920, 1920), 'hdr': (720, 720), 'med': (480, 480), 'thumbnail': (150, 90)}, verbose_name='Carte géographique')),
                ('carte_restaurant', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MaxSizeValidator(1920, 1920)], variations={'fhd': (1920, 1920), 'hdr': (720, 720), 'med': (480, 480), 'thumbnail': (150, 90)}, verbose_name='Carte du restaurant')),
                ('img', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MinSizeValidator(720, 135)], variations={'crop': (480, 270, True), 'crop_hdr': (960, 540, True), 'fhd': (1920, 1920), 'hdr': (720, 720), 'med': (480, 480), 'thumbnail': (150, 90)}, verbose_name='Background image')),
                ('fuseau_horaire', models.CharField(choices=[('Indian/Reunion', 'Indian/Reunion'), ('Europe/Paris', 'Europe/Paris')], default='Indian/Reunion', max_length=50)),
                ('logo', stdimage.models.StdImageField(blank=True, force_min_size=False, null=True, upload_to='images/', validators=[stdimage.validators.MaxSizeValidator(1920, 1920)], variations={'fhd': (1920, 1920), 'hdr': (720, 720), 'med': (480, 480), 'thumbnail': (300, 120)}, verbose_name='Logo')),
                ('jauge_max', models.PositiveSmallIntegerField(default=50, verbose_name='Jauge maximale')),
                ('server_cashless', models.URLField(blank=True, max_length=300, null=True, verbose_name='Adresse du serveur Cashless')),
                ('key_cashless', models.CharField(blank=True, max_length=41, null=True, verbose_name="Clé d'API du serveur cashless")),
                ('federated_cashless', models.BooleanField(default=False)),
                ('server_fedow', models.URLField(blank=True, max_length=300, null=True, verbose_name='Adresse du serveur fedow')),
                ('key_fedow', models.CharField(blank=True, max_length=41, null=True, verbose_name="Clé d'API du serveur fedow")),
                ('stripe_connect_account', models.CharField(blank=True, max_length=21, null=True)),
                ('stripe_connect_account_test', models.CharField(blank=True, max_length=21, null=True)),
                ('stripe_payouts_enabled', models.BooleanField(default=False)),
                ('stripe_api_key', models.CharField(blank=True, max_length=110, null=True)),
                ('stripe_test_api_key', models.CharField(blank=True, max_length=110, null=True)),
                ('stripe_mode_test', models.BooleanField(default=True)),
                ('vat_taxe', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('ghost_url', models.URLField(blank=True, null=True)),
                ('ghost_key', models.CharField(blank=True, max_length=200, null=True)),
                ('ghost_last_log', models.TextField(blank=True, null=True)),
                ('option_generale_checkbox', models.ManyToManyField(blank=True, related_name='checkbox', to='BaseBillet.optiongenerale')),
                ('option_generale_radio', models.ManyToManyField(blank=True, related_name='radiobutton', to='BaseBillet.optiongenerale')),
            ],
            options={
                'verbose_name': 'Paramètres',
                'verbose_name_plural': 'Paramètres',
            },
        ),
        migrations.CreateModel(
            name='Artist_on_event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Customers.client')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artists', to='BaseBillet.event')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='product',
            unique_together={('categorie_article', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='price',
            unique_together={('name', 'product')},
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_id_subscription', models.CharField(blank=True, max_length=28, null=True)),
                ('last_stripe_invoice', models.CharField(blank=True, max_length=278, null=True)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('first_contribution', models.DateField(blank=True, null=True)),
                ('last_contribution', models.DateField(blank=True, null=True)),
                ('last_action', models.DateTimeField(auto_now=True, verbose_name='Présence')),
                ('first_name', models.CharField(blank=True, db_index=True, max_length=200, null=True, verbose_name='Prénom')),
                ('last_name', models.CharField(blank=True, max_length=200, null=True, verbose_name='Nom')),
                ('pseudo', models.CharField(blank=True, max_length=50, null=True)),
                ('newsletter', models.BooleanField(default=True, verbose_name="J'accepte de recevoir la newsletter de l'association")),
                ('postal_code', models.IntegerField(blank=True, null=True)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('commentaire', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('O', 'Paiement unique'), ('A', 'Renouvellement automatique'), ('C', 'Annulée')], default='O', max_length=1, verbose_name='Status')),
                ('contribution_value', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('fedow_transactions', models.ManyToManyField(blank=True, related_name='membership', to='BaseBillet.fedowtransaction')),
                ('option_generale', models.ManyToManyField(blank=True, related_name='membership_options', to='BaseBillet.optiongenerale')),
                ('price', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user', to='BaseBillet.price')),
                ('stripe_paiement', models.ManyToManyField(blank=True, related_name='membership', to='BaseBillet.paiement_stripe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='membership', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Adhésion',
                'verbose_name_plural': 'Adhésions',
                'unique_together': {('user', 'price')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='event',
            unique_together={('name', 'datetime')},
        ),
    ]
