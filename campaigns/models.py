from django.db import models
from django.urls import reverse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Campaign(models.Model):
    """A campaign represents a collection of keywords to monitor on Reddit"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_watching = models.BooleanField(default=False)
    watch_interval_minutes = models.IntegerField(default=60, help_text="Interval in minutes to check Reddit")
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
        return f"campaign_watch_{self.pk}"

    def setup_task(self):
        """Creates or updates the PeriodicTask for this campaign"""
        task_name = self.schedule_name
        
        if self.is_watching:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=self.watch_interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    'task': 'campaigns.tasks.check_reddit_campaign',
                    'interval': schedule,
                    'args': json.dumps([self.pk]),
                    'enabled': True,
                }
            )
        else:
            # If watching is disabled, delete the task if it exists
            PeriodicTask.objects.filter(name=task_name).delete()


@receiver(post_save, sender=Campaign)
def update_campaign_task(sender, instance, created, **kwargs):
    instance.setup_task()


@receiver(post_delete, sender=Campaign)
def delete_campaign_task(sender, instance, **kwargs):
    PeriodicTask.objects.filter(name=instance.schedule_name).delete()


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
