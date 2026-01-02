from celery import shared_task
from django.utils import timezone
from .models import Campaign, RedditPost, RedditComment, GlobalSettings, CampaignMatch, Keyword
import requests
from django.conf import settings
from decouple import config
import datetime
import json
import redis

# Redis connection for progress tracking
def get_redis_client():
    return redis.from_url(settings.REDIS_URL)

REDIS_PROGRESS_KEY = 'reddit_watch:ingestion_progress'

def update_progress(data_type, count, new_count, total=None, status='success', error=None):
    """Update ingestion progress in Redis"""
    try:
        r = get_redis_client()
        progress_raw = r.get(REDIS_PROGRESS_KEY)
        progress = json.loads(progress_raw) if progress_raw else {}
        
        progress[data_type] = {
            'last_fetch_at': timezone.now().isoformat(),
            'last_count': count,
            'new_count': new_count,
            'total': total or progress.get(data_type, {}).get('total', 0),
            'status': status,
            'error': error
        }
        
        r.set(REDIS_PROGRESS_KEY, json.dumps(progress))
    except Exception as e:
        print(f"[{timezone.now()}] Error updating Redis progress: {e}")

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
        
        # Update progress in Redis
        total_posts = RedditPost.objects.count()
        update_progress('posts', count, created_count, total=total_posts)
            
        return f"Ingested {count} posts ({created_count} new). Newest ID: {newest_id}"
    except Exception as e:
        error_msg = f"Error ingesting posts: {str(e)}"
        print(f"[{timezone.now()}] {error_msg}")
        update_progress('posts', 0, 0, status='error', error=str(e))
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
        
        # Update progress in Redis
        total_comments = RedditComment.objects.count()
        update_progress('comments', count, created_count, total=total_comments)
            
        return f"Ingested {count} comments ({created_count} new). Newest ID: {newest_id}"
    except Exception as e:
        error_msg = f"Error ingesting comments: {str(e)}"
        print(f"[{timezone.now()}] {error_msg}")
        update_progress('comments', 0, 0, status='error', error=str(e))
        return error_msg


@shared_task
def match_campaign(campaign_id):
    """Match keywords against ingested data for a specific campaign"""
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        keywords = list(campaign.keywords.all())
        
        if not keywords:
            return f"No keywords for Campaign {campaign.name}"

        match_count = 0
        BATCH_SIZE = 1000
        
        # Calculate the earliest keyword start time (keyword.created_at - 30 minutes)
        # This determines the minimum time window for matching
        from datetime import timedelta
        keyword_start_times = {kw.id: kw.created_at - timedelta(minutes=30) for kw in keywords}
        earliest_start_time = min(keyword_start_times.values())
        
        print(f"[{timezone.now()}] Campaign {campaign.name}: Earliest keyword window starts at {earliest_start_time}")
        
        # --- 1. Process Posts ---
        last_post_id = campaign.last_processed_post_id
        max_post_id_processed = last_post_id
        
        while True:
            # Fetch batch of posts with ID > last_processed AND created_utc >= earliest start time
            posts = list(
                RedditPost.objects.filter(
                    id__gt=max_post_id_processed,
                    created_utc__gte=earliest_start_time
                ).order_by('id')[:BATCH_SIZE]
            )
            
            if not posts:
                break
                
            print(f"[{timezone.now()}] Campaign {campaign.name}: Scanning {len(posts)} posts (ID > {max_post_id_processed})")
            
            for post in posts:
                text_to_scan = (post.title + " " + post.selftext).lower()
                
                # Check ALL keywords for this post
                for kw in keywords:
                    # Only match if post was created after keyword's time window
                    kw_start_time = keyword_start_times[kw.id]
                    if post.created_utc >= kw_start_time and kw.name.lower() in text_to_scan:
                        CampaignMatch.objects.get_or_create(
                            campaign=campaign,
                            post=post,
                            keyword=kw,
                            defaults={
                                'match_text': f"Title: {post.title[:200]}..."
                            }
                        )
                        match_count += 1
                
                # Keep track of the highest ID processed so far
                if post.id > max_post_id_processed:
                    max_post_id_processed = post.id

            # Update checkpoint after every batch to be safe
            campaign.last_processed_post_id = max_post_id_processed
            campaign.save(update_fields=['last_processed_post_id'])

        # --- 2. Process Comments ---
        last_comment_id = campaign.last_processed_comment_id
        max_comment_id_processed = last_comment_id
        
        while True:
            # Fetch batch of comments with ID > last_processed AND created_utc >= earliest start time
            comments = list(
                RedditComment.objects.filter(
                    id__gt=max_comment_id_processed,
                    created_utc__gte=earliest_start_time
                ).order_by('id')[:BATCH_SIZE]
            )
            
            if not comments:
                break
                
            print(f"[{timezone.now()}] Campaign {campaign.name}: Scanning {len(comments)} comments (ID > {max_comment_id_processed})")
            
            for comment in comments:
                text_to_scan = comment.body.lower()
                
                # Check ALL keywords for this comment
                for kw in keywords:
                    # Only match if comment was created after keyword's time window
                    kw_start_time = keyword_start_times[kw.id]
                    if comment.created_utc >= kw_start_time and kw.name.lower() in text_to_scan:
                        CampaignMatch.objects.get_or_create(
                            campaign=campaign,
                            comment=comment,
                            keyword=kw,
                            defaults={
                                'match_text': comment.body[:200]
                            }
                        )
                        match_count += 1

                # Keep track of the highest ID processed so far
                if comment.id > max_comment_id_processed:
                    max_comment_id_processed = comment.id

            # Update checkpoint after every batch
            campaign.last_processed_comment_id = max_comment_id_processed
            campaign.save(update_fields=['last_processed_comment_id'])

        # Update legacy timestamp for backward compatibility/display
        campaign.last_matched_at = timezone.now()
        campaign.save(update_fields=['last_matched_at'])
        
        return f"Matched {match_count} items for Campaign {campaign.name}"
        
    except Campaign.DoesNotExist:
        return f"Campaign {campaign_id} not found"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error matching campaign {campaign_id}: {str(e)}"
