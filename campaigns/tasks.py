"""
Celery tasks for Reddit data ingestion and campaign keyword matching.
"""
import logging
import json
from datetime import datetime, timezone as datetime_timezone
from datetime import timedelta
from typing import Optional, Dict, Any

import redis
import requests
from celery import shared_task
from decouple import config
from django.conf import settings
from django.utils import timezone as django_timezone

from .models import Campaign, RedditPost, RedditComment, GlobalSettings, CampaignMatch

# Configure logger for this module
logger = logging.getLogger(__name__)

# Constants
REDDIT_API_LIMIT = 100
STALE_ID_THRESHOLD = 10  # Number of empty fetches before resetting ID
BATCH_SIZE = 1000
KEYWORD_LOOKBACK_MINUTES = 30
REDIS_PROGRESS_KEY = 'reddit_watch:ingestion_progress'


def get_redis_client() -> redis.Redis:
    """Get Redis client instance for progress tracking."""
    return redis.from_url(settings.REDIS_URL)


def update_progress(
    data_type: str,
    count: int,
    new_count: int,
    total: Optional[int] = None,
    status: str = 'success',
    error: Optional[str] = None
) -> None:
    """
    Update ingestion progress in Redis.
    
    Args:
        data_type: Type of data being ingested ('posts' or 'comments')
        count: Total items processed in this fetch
        new_count: Number of newly created items
        total: Total items in database (optional)
        status: Status of the operation ('success' or 'error')
        error: Error message if status is 'error'
    """
    try:
        r = get_redis_client()
        progress_raw = r.get(REDIS_PROGRESS_KEY)
        progress = json.loads(progress_raw) if progress_raw else {}
        
        progress[data_type] = {
            'last_fetch_at': django_timezone.now().isoformat(),
            'last_count': count,
            'new_count': new_count,
            'total': total or progress.get(data_type, {}).get('total', 0),
            'status': status,
            'error': error
        }
        
        r.set(REDIS_PROGRESS_KEY, json.dumps(progress))
    except Exception as e:
        logger.exception("Error updating Redis progress: %s", e)


def make_reddit_request(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make an authenticated request to Reddit's JSON API.
    
    Args:
        url: The Reddit API endpoint URL
        params: Optional query parameters
        
    Returns:
        JSON response as dictionary
        
    Raises:
        requests.RequestException: If the request fails
    """
    headers = {
        'User-Agent': config('REDDIT_USER_AGENT', default='reddit_watch:v1.0.0')
    }
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def handle_stale_id(
    global_settings: GlobalSettings,
    empty_count_field: str,
    last_id_field: str,
    data_type: str
) -> bool:
    """
    Handle stale ID detection and reset logic.
    
    Args:
        global_settings: GlobalSettings instance
        empty_count_field: Name of the empty count field
        last_id_field: Name of the last ID field
        data_type: Type of data ('posts' or 'comments') for logging
        
    Returns:
        True if ID was reset due to staleness
    """
    current_count = getattr(global_settings, empty_count_field)
    current_count += 1
    setattr(global_settings, empty_count_field, current_count)
    
    logger.info(
        "No new %s found (Consecutive empty: %d)",
        data_type, current_count
    )
    
    was_reset = False
    if current_count >= STALE_ID_THRESHOLD:
        logger.warning(
            "%s ID STALE: Resetting %s to None after %d empty fetches",
            data_type.upper(), last_id_field, STALE_ID_THRESHOLD
        )
        setattr(global_settings, last_id_field, None)
        setattr(global_settings, empty_count_field, 0)
        was_reset = True
    
    global_settings.save(update_fields=[empty_count_field, last_id_field])
    return was_reset


def parse_reddit_timestamp(timestamp: float) -> datetime:
    """Convert Reddit UTC timestamp to timezone-aware datetime."""
    return datetime.fromtimestamp(timestamp, tz=datetime_timezone.utc)


@shared_task
def ingest_posts() -> str:
    """
    Fetch new posts from r/all using Reddit's JSON API.
    
    Uses cursor-based pagination with the 'before' parameter to fetch
    only posts newer than the last ingested post. Implements stale ID
    detection to handle Reddit's limited pagination window.
    
    Returns:
        Status message describing the ingestion result
    """
    try:
        global_settings = GlobalSettings.objects.first()
        if not global_settings:
            logger.warning("No GlobalSettings found")
            return "No GlobalSettings found"
        
        params = {'limit': REDDIT_API_LIMIT}
        
        if global_settings.last_post_id:
            params['before'] = global_settings.last_post_id
            logger.info("Ingesting posts BEFORE %s", global_settings.last_post_id)
        else:
            logger.info("First fetch - getting latest posts")
            
        data = make_reddit_request("https://www.reddit.com/r/all/new.json", params)
        children = data.get('data', {}).get('children', [])
        
        if not children:
            handle_stale_id(
                global_settings,
                'empty_post_fetch_count',
                'last_post_id',
                'posts'
            )
            return "No new posts to ingest"
        
        newest_id = None
        count = 0
        created_count = 0
        
        for child in children:
            submission = child['data']
            post_id = submission['name']  # Format: t3_xxxxx
            
            # Track the newest ID (first in the list from /new)
            if newest_id is None:
                newest_id = post_id
                
            _, created = RedditPost.objects.get_or_create(
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
                    'created_utc': parse_reddit_timestamp(
                        submission.get('created_utc', 0)
                    )
                }
            )
            
            count += 1
            if created:
                created_count += 1
            
        # Update the last_post_id to the newest one we saw
        if newest_id:
            global_settings.last_post_id = newest_id
            global_settings.empty_post_fetch_count = 0
            global_settings.save(update_fields=['last_post_id', 'empty_post_fetch_count'])
            logger.info(
                "Processed %d posts (%d new). Newest ID: %s",
                count, created_count, newest_id
            )
        
        # Update progress in Redis
        total_posts = RedditPost.objects.count()
        update_progress('posts', count, created_count, total=total_posts)
            
        return f"Ingested {count} posts ({created_count} new). Newest ID: {newest_id}"
        
    except requests.RequestException as e:
        error_msg = f"Reddit API error ingesting posts: {e}"
        logger.exception(error_msg)
        update_progress('posts', 0, 0, status='error', error=str(e))
        return error_msg
    except Exception as e:
        error_msg = f"Error ingesting posts: {e}"
        logger.exception(error_msg)
        update_progress('posts', 0, 0, status='error', error=str(e))
        return error_msg


@shared_task
def ingest_comments() -> str:
    """
    Fetch new comments from r/all using Reddit's JSON API.
    
    Uses cursor-based pagination with the 'before' parameter to fetch
    only comments newer than the last ingested comment. Implements stale ID
    detection to handle Reddit's limited pagination window.
    
    Returns:
        Status message describing the ingestion result
    """
    try:
        global_settings = GlobalSettings.objects.first()
        if not global_settings:
            logger.warning("No GlobalSettings found")
            return "No GlobalSettings found"
            
        params = {'limit': REDDIT_API_LIMIT}
        
        if global_settings.last_comment_id:
            params['before'] = global_settings.last_comment_id
            logger.info("Ingesting comments BEFORE %s", global_settings.last_comment_id)
        else:
            logger.info("First fetch - getting latest comments")
        
        data = make_reddit_request("https://www.reddit.com/r/all/comments.json", params)
        children = data.get('data', {}).get('children', [])
        
        if not children:
            handle_stale_id(
                global_settings,
                'empty_comment_fetch_count',
                'last_comment_id',
                'comments'
            )
            return "No new comments to ingest"
        
        newest_id = None
        count = 0
        created_count = 0
        
        for child in children:
            comment = child['data']
            comment_id = comment['name']  # Format: t1_xxxxx
            
            # Track the newest ID (first in the list)
            if newest_id is None:
                newest_id = comment_id
            
            _, created = RedditComment.objects.get_or_create(
                reddit_id=comment_id,
                defaults={
                    'link_id': comment.get('link_id', ''),
                    'body': comment.get('body', ''),
                    'author': comment.get('author', 'unknown'),
                    'subreddit': comment.get('subreddit', ''),
                    'permalink': comment.get('permalink', ''),
                    'score': comment.get('score', 0),
                    'created_utc': parse_reddit_timestamp(
                        comment.get('created_utc', 0)
                    )
                }
            )
            
            count += 1
            if created:
                created_count += 1
            
        # Update the last_comment_id to the newest one we saw
        if newest_id:
            global_settings.last_comment_id = newest_id
            global_settings.empty_comment_fetch_count = 0
            global_settings.save(update_fields=['last_comment_id', 'empty_comment_fetch_count'])
            logger.info(
                "Processed %d comments (%d new). Newest ID: %s",
                count, created_count, newest_id
            )
        
        # Update progress in Redis
        total_comments = RedditComment.objects.count()
        update_progress('comments', count, created_count, total=total_comments)
            
        return f"Ingested {count} comments ({created_count} new). Newest ID: {newest_id}"
        
    except requests.RequestException as e:
        error_msg = f"Reddit API error ingesting comments: {e}"
        logger.exception(error_msg)
        update_progress('comments', 0, 0, status='error', error=str(e))
        return error_msg
    except Exception as e:
        error_msg = f"Error ingesting comments: {e}"
        logger.exception(error_msg)
        update_progress('comments', 0, 0, status='error', error=str(e))
        return error_msg


def process_posts_for_campaign(
    campaign: Campaign,
    keywords: list,
    keyword_start_times: Dict[int, timezone.datetime],
    earliest_start_time: timezone.datetime
) -> int:
    """
    Process posts for keyword matching in a campaign.
    
    Args:
        campaign: The campaign to match against
        keywords: List of keyword objects
        keyword_start_times: Dict mapping keyword ID to their start times
        earliest_start_time: Earliest time window for matching
        
    Returns:
        Number of matches found
    """
    match_count = 0
    max_post_id = campaign.last_processed_post_id
    
    while True:
        posts = list(
            RedditPost.objects.filter(
                id__gt=max_post_id,
                created_utc__gte=earliest_start_time
            ).order_by('id')[:BATCH_SIZE]
        )
        
        if not posts:
            break
            
        logger.debug(
            "Campaign %s: Scanning %d posts (ID > %s)",
            campaign.name, len(posts), max_post_id
        )
        
        for post in posts:
            text_to_scan = f"{post.title} {post.selftext}".lower()
            
            for kw in keywords:
                kw_start_time = keyword_start_times[kw.id]
                if post.created_utc >= kw_start_time and kw.name.lower() in text_to_scan:
                    _, created = CampaignMatch.objects.get_or_create(
                        campaign=campaign,
                        post=post,
                        keyword=kw,
                        defaults={'match_text': f"Title: {post.title[:200]}..."}
                    )
                    if created:
                        match_count += 1
            
            max_post_id = max(max_post_id, post.id)
        
        # Update checkpoint after every batch
        campaign.last_processed_post_id = max_post_id
        campaign.save(update_fields=['last_processed_post_id'])
    
    return match_count


def process_comments_for_campaign(
    campaign: Campaign,
    keywords: list,
    keyword_start_times: Dict[int, timezone.datetime],
    earliest_start_time: timezone.datetime
) -> int:
    """
    Process comments for keyword matching in a campaign.
    
    Args:
        campaign: The campaign to match against
        keywords: List of keyword objects
        keyword_start_times: Dict mapping keyword ID to their start times
        earliest_start_time: Earliest time window for matching
        
    Returns:
        Number of matches found
    """
    match_count = 0
    max_comment_id = campaign.last_processed_comment_id
    
    while True:
        comments = list(
            RedditComment.objects.filter(
                id__gt=max_comment_id,
                created_utc__gte=earliest_start_time
            ).order_by('id')[:BATCH_SIZE]
        )
        
        if not comments:
            break
            
        logger.debug(
            "Campaign %s: Scanning %d comments (ID > %s)",
            campaign.name, len(comments), max_comment_id
        )
        
        for comment in comments:
            text_to_scan = comment.body.lower()
            
            for kw in keywords:
                kw_start_time = keyword_start_times[kw.id]
                if comment.created_utc >= kw_start_time and kw.name.lower() in text_to_scan:
                    _, created = CampaignMatch.objects.get_or_create(
                        campaign=campaign,
                        comment=comment,
                        keyword=kw,
                        defaults={'match_text': comment.body[:200]}
                    )
                    if created:
                        match_count += 1
            
            max_comment_id = max(max_comment_id, comment.id)
        
        # Update checkpoint after every batch
        campaign.last_processed_comment_id = max_comment_id
        campaign.save(update_fields=['last_processed_comment_id'])
    
    return match_count


@shared_task
def match_campaign(campaign_id: int) -> str:
    """
    Match keywords against ingested data for a specific campaign.
    
    Processes both posts and comments in batches, checking each against
    the campaign's keywords. Only matches content created after the
    keyword's time window (keyword creation time - 30 minutes).
    
    Args:
        campaign_id: Primary key of the campaign to process
        
    Returns:
        Status message describing the matching result
    """
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        keywords = list(campaign.keywords.all())
        
        if not keywords:
            logger.info("No keywords for Campaign %s", campaign.name)
            return f"No keywords for Campaign {campaign.name}"

        # Calculate keyword time windows
        keyword_start_times = {
            kw.id: kw.created_at - timedelta(minutes=KEYWORD_LOOKBACK_MINUTES)
            for kw in keywords
        }
        earliest_start_time = min(keyword_start_times.values())
        
        logger.info(
            "Campaign %s: Earliest keyword window starts at %s",
            campaign.name, earliest_start_time
        )
        
        # Process posts and comments
        post_matches = process_posts_for_campaign(
            campaign, keywords, keyword_start_times, earliest_start_time
        )
        comment_matches = process_comments_for_campaign(
            campaign, keywords, keyword_start_times, earliest_start_time
        )
        
        total_matches = post_matches + comment_matches

        # Update timestamp for backward compatibility
        campaign.last_matched_at = django_timezone.now()
        campaign.save(update_fields=['last_matched_at'])
        
        logger.info(
            "Campaign %s: Found %d matches (%d posts, %d comments)",
            campaign.name, total_matches, post_matches, comment_matches
        )
        
        return f"Matched {total_matches} items for Campaign {campaign.name}"
        
    except Campaign.DoesNotExist:
        logger.warning("Campaign %s not found", campaign_id)
        return f"Campaign {campaign_id} not found"
    except Exception as e:
        logger.exception("Error matching campaign %s: %s", campaign_id, e)
        return f"Error matching campaign {campaign_id}: {e}"
