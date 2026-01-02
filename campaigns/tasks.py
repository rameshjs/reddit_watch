from celery import shared_task
from django.utils import timezone
from .models import Campaign, RedditPost, RedditComment, GlobalSettings, CampaignMatch, Keyword
import requests
from django.conf import settings
from decouple import config
import datetime

def make_request(url, params=None):
    headers = {
        'User-Agent': config('REDDIT_USER_AGENT', default='reddit_watch:v1.0.0')
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()

@shared_task
def ingest_posts():
    """Fetch new posts from r/all using JSON API"""
    try:
        global_settings = GlobalSettings.objects.first()
        if not global_settings:
            return "No GlobalSettings found"
        
        params = {'limit': 100}
        # Use 'before' to get posts NEWER than the last one we fetched
        if global_settings.last_post_id:
            params['before'] = global_settings.last_post_id
            print(f"[{timezone.now()}] Ingesting Posts BEFORE {global_settings.last_post_id}")
        else:
            print(f"[{timezone.now()}] First fetch - getting latest posts")
            
        data = make_request("https://www.reddit.com/r/all/new.json", params=params)
        children = data.get('data', {}).get('children', [])
        
        if not children:
            # Stale ID Detection: Increment empty fetch count
            global_settings.empty_post_fetch_count += 1
            print(f"[{timezone.now()}] No new posts found (Consecutive empty: {global_settings.empty_post_fetch_count})")
            
            # Reset after 10 consecutive empty fetches (~10 minutes at 60s interval)
            if global_settings.empty_post_fetch_count >= 10:
                print(f"[{timezone.now()}] POST ID STALE: Resetting last_post_id to None after 10 empty fetches")
                global_settings.last_post_id = None
                global_settings.empty_post_fetch_count = 0
            
            global_settings.save(update_fields=['empty_post_fetch_count', 'last_post_id'])
            return "No new posts to ingest"
        
        newest_id = None
        count = 0
        created_count = 0
        
        for child in children:
            submission = child['data']
            post_id = submission['name']  # Format: t3_xxxxx
            
            # Track the newest ID (first in the list from /new)
            if not newest_id:
                newest_id = post_id
                
            created = RedditPost.objects.get_or_create(
                reddit_id=post_id,
                defaults={
                    'title': submission.get('title', '')[:300],
                    'url': submission.get('url', ''),
                    'author': submission.get('author', 'unknown'),
                    'subreddit': submission.get('subreddit', ''),
                    'selftext': submission.get('selftext', ''),
                    'permalink': submission.get('permalink', ''),
                    'score': submission.get('score', 0),
                    'num_comments': submission.get('num_comments', 0),
                    'is_video': submission.get('is_video', False),
                    'over_18': submission.get('over_18', False),
                    'spoiler': submission.get('spoiler', False),
                    'stickied': submission.get('stickied', False),
                    'created_utc': datetime.datetime.fromtimestamp(submission.get('created_utc', 0), tz=datetime.timezone.utc)
                }
            )[1]  # [1] is the 'created' boolean
            
            count += 1
            if created:
                created_count += 1
            
        # Update the last_post_id to the newest one we saw
        if newest_id:
            global_settings.last_post_id = newest_id
            # Reset empty fetch count on success
            global_settings.empty_post_fetch_count = 0
            global_settings.save(update_fields=['last_post_id', 'empty_post_fetch_count'])
            print(f"[{timezone.now()}] Processed {count} posts ({created_count} new). Newest ID: {newest_id}")
            
        return f"Ingested {count} posts ({created_count} new). Newest ID: {newest_id}"
    except Exception as e:
        error_msg = f"Error ingesting posts: {str(e)}"
        print(f"[{timezone.now()}] {error_msg}")
        return error_msg


@shared_task
def ingest_comments():
    """Fetch new comments from r/all using JSON API"""
    try:
        global_settings = GlobalSettings.objects.first()
        if not global_settings:
            return "No GlobalSettings found"
            
        params = {'limit': 100}
        # Use 'before' to get comments NEWER than the last one we fetched
        if global_settings.last_comment_id:
            params['before'] = global_settings.last_comment_id
            print(f"[{timezone.now()}] Ingesting Comments BEFORE {global_settings.last_comment_id}")
        else:
            print(f"[{timezone.now()}] First fetch - getting latest comments")
        
        data = make_request("https://www.reddit.com/r/all/comments.json", params=params)
        children = data.get('data', {}).get('children', [])
        
        if not children:
            # Stale ID Detection: Increment empty fetch count
            global_settings.empty_comment_fetch_count += 1
            print(f"[{timezone.now()}] No new comments found (Consecutive empty: {global_settings.empty_comment_fetch_count})")
            
            # Reset after 10 consecutive empty fetches
            if global_settings.empty_comment_fetch_count >= 10:
                print(f"[{timezone.now()}] COMMENT ID STALE: Resetting last_comment_id to None after 10 empty fetches")
                global_settings.last_comment_id = None
                global_settings.empty_comment_fetch_count = 0
            
            global_settings.save(update_fields=['empty_comment_fetch_count', 'last_comment_id'])
            return "No new comments to ingest"
        
        newest_id = None
        count = 0
        created_count = 0
        
        for child in children:
            comment = child['data']
            comment_id = comment['name']  # Format: t1_xxxxx
            
            # Track the newest ID (first in the list)
            if not newest_id:
                newest_id = comment_id
            
            created = RedditComment.objects.get_or_create(
                reddit_id=comment_id,
                defaults={
                    'link_id': comment.get('link_id', ''),
                    'body': comment.get('body', ''),
                    'author': comment.get('author', 'unknown'),
                    'subreddit': comment.get('subreddit', ''),
                    'permalink': comment.get('permalink', ''),
                    'score': comment.get('score', 0),
                    'created_utc': datetime.datetime.fromtimestamp(comment.get('created_utc', 0), tz=datetime.timezone.utc)
                }
            )[1]  # [1] is the 'created' boolean
            
            count += 1
            if created:
                created_count += 1
            
        # Update the last_comment_id to the newest one we saw
        if newest_id:
            global_settings.last_comment_id = newest_id
            # Reset empty fetch count on success
            global_settings.empty_comment_fetch_count = 0
            global_settings.save(update_fields=['last_comment_id', 'empty_comment_fetch_count'])
            print(f"[{timezone.now()}] Processed {count} comments ({created_count} new). Newest ID: {newest_id}")
            
        return f"Ingested {count} comments ({created_count} new). Newest ID: {newest_id}"
    except Exception as e:
        error_msg = f"Error ingesting comments: {str(e)}"
        print(f"[{timezone.now()}] {error_msg}")
        return error_msg


@shared_task
def match_campaign(campaign_id):
    """Match keywords against ingested data for a specific campaign"""
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        
        # Determine time window
        end_time = timezone.now()
        start_time = campaign.last_matched_at
        
        if not start_time:
            # Default to 24 hours ago if first run
            start_time = end_time - datetime.timedelta(hours=24)
            
        print(f"[{timezone.now()}] Matching Campaign {campaign.name} Window: {start_time} -> {end_time}")
        
        date_range = (start_time, end_time)
        keywords = campaign.keywords.all()
        
        match_count = 0
        
        # 1. Check Posts
        # Filter posts in time window
        posts = RedditPost.objects.filter(created_utc__range=date_range)
        
        for post in posts:
            text_to_scan = (post.title + " " + post.selftext).lower()
            for kw in keywords:
                if kw.name.lower() in text_to_scan:
                    CampaignMatch.objects.get_or_create(
                        campaign=campaign,
                        keyword=kw,
                        post=post,
                        defaults={'match_text': f"Title: {post.title}..."}
                    )
                    match_count += 1
                    
        # 2. Check Comments
        comments = RedditComment.objects.filter(created_utc__range=date_range)
        
        for comment in comments:
            text_to_scan = comment.body.lower()
            for kw in keywords:
                 if kw.name.lower() in text_to_scan:
                    CampaignMatch.objects.get_or_create(
                        campaign=campaign,
                        keyword=kw,
                        comment=comment,
                        defaults={'match_text': comment.body[:100]}
                    )
                    match_count += 1
                    
        # Update last matched timestamp
        campaign.last_matched_at = end_time
        campaign.save(update_fields=['last_matched_at'])
        
        return f"Matched {match_count} items for Campaign {campaign.name}"
        
    except Campaign.DoesNotExist:
        return f"Campaign {campaign_id} not found"
    except Exception as e:
        return f"Error matching campaign {campaign_id}: {str(e)}"
