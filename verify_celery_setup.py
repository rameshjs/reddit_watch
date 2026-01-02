import os
import sys
import time
from datetime import timedelta

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reddit_watch.settings')
import django
try:
    django.setup()
    print("Django setup successful.")
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from campaigns.models import Campaign, RedditPost
from campaigns.tasks import check_reddit_campaign
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

def verify_setup():
    print("\n--- Verifying Celery Configuration ---")
    
    # 1. Check Periodic Tasks
    tasks = PeriodicTask.objects.filter(task='campaigns.tasks.check_reddit_campaign')
    print(f"Found {tasks.count()} scheduled tasks for 'campaigns.tasks.check_reddit_campaign'.")
    for task in tasks:
        print(f"  - Task '{task.name}' args: {task.args} | Enabled: {task.enabled} | Last Run: {task.last_run_at}")

    # 2. Check Campaigns
    campaigns = Campaign.objects.filter(is_watching=True)
    print(f"\nFound {campaigns.count()} active watching campaigns.")
    
    if not campaigns.exists():
        print("No active campaigns found. Creating a test campaign...")
        c = Campaign.objects.create(name="Test Campaign", is_watching=True, watch_interval_seconds=60)
        print(f"Created campaign '{c.name}' (ID: {c.pk})")
        campaigns = [c]

    # 3. Test Task Execution (Direct)
    print("\n--- Testing Direct Task Execution ---")
    c = campaigns[0]
    print(f"Testing with Campaign ID: {c.pk}")
    
    initial_posts = RedditPost.objects.filter(campaign=c).count()
    print(f"Initial Post Count: {initial_posts}")
    
    try:
        result = check_reddit_campaign(c.pk)
        print(f"Task executed successfully. Result: {result}")
    except Exception as e:
        print(f"Task execution failed: {e}")
        return

    final_posts = RedditPost.objects.filter(campaign=c).count()
    print(f"Final Post Count: {final_posts}")
    
    if final_posts > initial_posts:
        print("SUCCESS: Dummy data was created.")
    else:
        print("WARNING: No new data created.")

    print("\n--- Instructions ---")
    print("If this script works, but you don't see data automatically, ensure your Celery Worker & Beat are running.")
    print("Run: celery -A reddit_watch worker --beat -l info")

if __name__ == "__main__":
    verify_setup()
