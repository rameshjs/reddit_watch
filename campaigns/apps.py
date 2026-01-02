from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    name = 'campaigns'

    def ready(self):
        from .models import GlobalSettings
        from django.db.utils import OperationalError, ProgrammingError
        
        try:
            # Check if table exists to avoid errors during migrations
            GlobalSettings.objects.get_or_create()
        except (OperationalError, ProgrammingError):
            pass
