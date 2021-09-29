from django.db import models
from django.contrib.postgres.fields import JSONField
import uuid
# Create your models here.
from TiBillet import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
# from QrcodeCashless.views import postPaimentRecharge


class Paiement_stripe(models.Model):
    """
    La commande
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True, db_index=True)
    detail = models.CharField(max_length=50, blank=True, null=True)

    id_stripe = models.CharField(max_length=80, blank=True, null=True)
    metadata_stripe = JSONField(blank=True, null=True)

    order_date = models.DateTimeField(auto_now=True, verbose_name="Date")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True)

    NON, OPEN, PENDING, EXPIRE, PAID, VALID, CANCELED = 'N', 'O', 'W', 'E', 'P', 'V', 'C'
    STATUT_CHOICES = (
        (NON, 'Lien de paiement non crée'),
        (OPEN, 'Envoyée a Stripe'),
        (PENDING, 'En attente de paiement'),
        (EXPIRE, 'Expiré'),
        (PAID, 'Payée'),
        (VALID, 'Payée et validée'),  # envoyé sur serveur cashless
        (CANCELED, 'Annulée'),
    )

    status = models.CharField(max_length=1, choices=STATUT_CHOICES, default=NON, verbose_name="Statut de la commande")

    total = models.FloatField(default=0)

    def __str__(self):
        return f"{self.detail} - {self.status}"

''' RECEIVER PRESAVE DANS LE VIEW QRCODECASHELESS
@receiver(pre_save, sender=Paiement_stripe)
def changement_paid_to_valid(sender, instance: Paiement_stripe, update_fields=None, **kwargs):
    try:
        old_instance = Paiement_stripe.objects.get(pk=instance.pk)
        if old_instance.status != Paiement_stripe.PAID :
            print(f"on passe de {old_instance.status} à {instance.status}")
            if instance.status == Paiement_stripe.PAID:
                on lance la recharge vers le serveur cashless
'''
