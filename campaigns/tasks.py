from celery import shared_task
from django.utils import timezone

@shared_task
def check_reddit_campaign(campaign_id):
    """
    Task to check reddit for a specific campaign.
    Generates dummy data for RedditPost and RedditComment.
    """
    from .models import Campaign, RedditPost, RedditComment
    import random
    from django.utils import timezone
    from datetime import timedelta
    import uuid

    print(f"[{timezone.now()}] Checking Reddit for Campaign ID: {campaign_id}")
    
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return f"Campaign {campaign_id} not found"

    # Generate a dummy post
    post_id = str(uuid.uuid4())[:8]
    post = RedditPost.objects.create(
        campaign=campaign,
        title=f"Dummy Post for {campaign.name} - {post_id}",
        url=f"https://reddit.com/r/test/{post_id}",
        author=f"user_{random.randint(1000, 9999)}",
        score=random.randint(1, 500),
        num_comments=random.randint(0, 50),
        created_utc=timezone.now() - timedelta(minutes=random.randint(0, 60)),
        reddit_id=f"t3_{post_id}"
    )
    
    # Generate some dummy comments
    num_comments = random.randint(1, 5)
    for i in range(num_comments):
        comment_id = str(uuid.uuid4())[:8]
        RedditComment.objects.create(
            post=post,
            body=f"This is a dummy comment {i+1} for post {post_id}",
            author=f"commenter_{random.randint(1000, 9999)}",
            score=random.randint(-5, 50),
            created_utc=timezone.now() - timedelta(minutes=random.randint(0, 30)),
            reddit_id=f"t1_{comment_id}"
        )

    return f"Checked Campaign {campaign_id}, created post {post.reddit_id} with {num_comments} comments"
