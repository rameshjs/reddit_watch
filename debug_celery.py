import os
import django
from django.utils import timezone
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reddit_watch.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule
from campaigns.models import Campaign, RedditPost
from campaigns.tasks import check_reddit_campaign
import json

def debug():
    print("--- Debugging Celery Tasks ---")
    
    # Check PeriodicTasks
    tasks = PeriodicTask.objects.all()
    print(f"Found {tasks.count()} PeriodicTasks:")
    for task in tasks:
        print(f"  - Name: {task.name}")
        print(f"    Task: {task.task}")
        print(f"    Args: {task.args}")
        print(f"    Enabled: {task.enabled}")
        print(f"    Last Run: {task.last_run_at}")

    # Check Campaigns
    campaigns = Campaign.objects.all()
    print(f"\nFound {campaigns.count()} Campaigns:")
    for c in campaigns:
        print(f"  - {c.name} (ID: {c.pk}, Watching: {c.is_watching})")

    if campaigns.exists():
        c = campaigns.first()
        print(f"\nAttempting to run task for Campaign ID: {c.pk}")
        
        # Count posts before
        before_count = RedditPost.objects.filter(campaign=c).count()
        
        # Run task directly
        result = check_reddit_campaign(c.pk)
        print(f"Task Result: {result}")
        
        # Count posts after
        after_count = RedditPost.objects.filter(campaign=c).count()
        print(f"RedditPost count: {before_count} -> {after_count}")
    else:
        print("\nNo campaigns found to test task.")

if __name__ == "__main__":
    debug()
