from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import GlobalSettings

@receiver(post_migrate)
def create_global_settings(sender, **kwargs):
    if sender.name == 'campaigns':
        GlobalSettings.objects.get_or_create()
