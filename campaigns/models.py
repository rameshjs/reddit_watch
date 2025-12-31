from django.db import models
from django.urls import reverse


class Campaign(models.Model):
    """A campaign represents a collection of keywords to monitor on Reddit"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('campaign_detail', kwargs={'pk': self.pk})


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
