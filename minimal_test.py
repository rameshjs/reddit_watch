import os
import django
import sys

print("Setting up Django env...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reddit_watch.settings')
try:
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"Django setup failed: {e}")
