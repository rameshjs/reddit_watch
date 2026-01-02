from celery import shared_task
from django.utils import timezone

@shared_task
def check_reddit_campaign(campaign_id):
    """
    Task to check reddit for a specific campaign.
    For now, just prints a static message.
    """
    print(f"[{timezone.now()}] Checking Reddit for Campaign ID: {campaign_id}")
    return f"Checked Campaign {campaign_id}"
