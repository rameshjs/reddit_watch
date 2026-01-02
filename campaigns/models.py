from django.db import models
from django.urls import reverse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class GlobalSettings(models.Model):
    """Global settings for the application, specifically for Reddit limits"""
    post_fetch_interval = models.IntegerField(default=300, help_text="Seconds between fetching posts")
    comment_fetch_interval = models.IntegerField(default=360, help_text="Seconds between fetching comments")
    last_post_id = models.CharField(max_length=20, blank=True, null=True, help_text="Fullname of last fetched post")
    last_comment_id = models.CharField(max_length=20, blank=True, null=True, help_text="Fullname of last fetched comment")
    empty_post_fetch_count = models.IntegerField(default=0, help_text="Consecutive empty post fetches (for stale ID detection)")
    empty_comment_fetch_count = models.IntegerField(default=0, help_text="Consecutive empty comment fetches (for stale ID detection)")
    
    
    def save(self, *args, **kwargs):
        if not self.pk and GlobalSettings.objects.exists():
            raise ValidationError('There can be only one GlobalSettings instance')
        return super(GlobalSettings, self).save(*args, **kwargs)

    def clean(self):
        if abs(self.post_fetch_interval - self.comment_fetch_interval) < 60:
            raise ValidationError("Post and Comment fetch intervals must differ by at least 60 seconds")

    def __str__(self):
        return "Global Configuration"


class Campaign(models.Model):
    """A campaign represents a collection of keywords to monitor on Reddit"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_watching = models.BooleanField(default=False)
    match_interval_seconds = models.IntegerField(default=3600, help_text="Interval in seconds to match keywords")
    last_matched_at = models.DateTimeField(null=True, blank=True)
    last_processed_post_id = models.BigIntegerField(default=0, help_text="Last processed RedditPost internal ID")
    last_processed_comment_id = models.BigIntegerField(default=0, help_text="Last processed RedditComment internal ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('campaign_detail', kwargs={'pk': self.pk})

    @property
    def schedule_name(self):
        return f"campaign_match_{self.pk}"

    def setup_task(self):
        """Creates or updates the PeriodicTask for this campaign's matching job"""
        task_name = self.schedule_name
        
        if self.is_watching:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=self.match_interval_seconds,
                period=IntervalSchedule.SECONDS,
            )
            
            PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    'task': 'campaigns.tasks.match_campaign',
                    'interval': schedule,
                    'args': json.dumps([self.pk]),
                    'enabled': True,
                }
            )
        else:
            PeriodicTask.objects.filter(name=task_name).delete()


@receiver(post_save, sender=Campaign)
def update_campaign_task(sender, instance, created, **kwargs):
    instance.setup_task()


@receiver(post_delete, sender=Campaign)
def delete_campaign_task(sender, instance, **kwargs):
    PeriodicTask.objects.filter(name=instance.schedule_name).delete()


@receiver(post_save, sender=GlobalSettings)
def update_global_tasks(sender, instance, created, **kwargs):
    # Setup Post Ingestion Task
    p_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=instance.post_fetch_interval,
        period=IntervalSchedule.SECONDS,
    )
    PeriodicTask.objects.update_or_create(
        name='global_ingest_posts',
        defaults={
            'task': 'campaigns.tasks.ingest_posts',
            'interval': p_schedule,
            'enabled': True,
        }
    )
    
    # Setup Comment Ingestion Task
    c_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=instance.comment_fetch_interval,
        period=IntervalSchedule.SECONDS,
    )
    PeriodicTask.objects.update_or_create(
        name='global_ingest_comments',
        defaults={
            'task': 'campaigns.tasks.ingest_comments',
            'interval': c_schedule,
            'enabled': True,
        }
    )


class Keyword(models.Model):
    """A keyword to monitor within a campaign"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='keywords')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['campaign', 'name']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.name}"


class Tag(models.Model):
    """A tag for categorizing keywords"""
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['keyword', 'name']
    
    def __str__(self):
        return self.name

class RedditPost(models.Model):
    """A Reddit post fetched from r/all"""
    reddit_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=300)
    url = models.URLField()
    author = models.CharField(max_length=100)
    subreddit = models.CharField(max_length=100)
    selftext = models.TextField(blank=True)
    permalink = models.CharField(max_length=300)
    
    score = models.IntegerField(default=0)
    num_comments = models.IntegerField(default=0)
    
    is_video = models.BooleanField(default=False)
    over_18 = models.BooleanField(default=False)
    spoiler = models.BooleanField(default=False)
    stickied = models.BooleanField(default=False)
    
    created_utc = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_utc']
        
    def __str__(self):
        return self.title


class RedditComment(models.Model):
    """A Reddit comment fetched from r/all"""
    reddit_id = models.CharField(max_length=20, unique=True)
    link_id = models.CharField(max_length=20, help_text="ID of the post this comment belongs to")
    body = models.TextField()
    author = models.CharField(max_length=100)
    subreddit = models.CharField(max_length=100)
    permalink = models.CharField(max_length=300)
    
    score = models.IntegerField(default=0)
    created_utc = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_utc']
        
    def __str__(self):
        return f"Comment by {self.author}"


class CampaignMatch(models.Model):
    """Records a match between a Campaign Keyword and a Reddit Post/Comment"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='matches')
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='matches')
    post = models.ForeignKey(RedditPost, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches')
    comment = models.ForeignKey(RedditComment, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches')
    
    match_text = models.TextField(help_text="The snippet of text that matched")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [('campaign', 'post', 'keyword'), ('campaign', 'comment', 'keyword')]

    def __str__(self):
        return f"Match for {self.campaign.name}: {self.keyword.name}"
