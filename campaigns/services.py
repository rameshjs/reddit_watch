"""
Service layer for campaigns app.
Encapsulates business logic for creating, updating, and deleting
Campaigns, Keywords, Tags, and Global Settings.
"""
from django.shortcuts import get_object_or_404
from .models import Campaign, Keyword, Tag, GlobalSettings, RedditPost, RedditComment

# --- Campaign Services ---

def create_campaign(name, description, is_watching, hours, minutes, seconds):
    """Creates a new campaign with calculated interval."""
    try:
        h = int(hours or 0)
        m = int(minutes or 0)
        s = int(seconds or 0)
        interval_seconds = (h * 3600) + (m * 60) + s
        if interval_seconds < 30:
            interval_seconds = 30
    except ValueError:
        interval_seconds = 3600

    return Campaign.objects.create(
        name=name,
        description=description,
        is_watching=is_watching,
        match_interval_seconds=interval_seconds
    )


def update_campaign(pk, name, description, is_watching, hours, minutes, seconds):
    """Updates an existing campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.name = name
    campaign.description = description
    campaign.is_watching = is_watching
    
    try:
        h = int(hours or 0)
        m = int(minutes or 0)
        s = int(seconds or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        campaign.match_interval_seconds = total
    except ValueError:
        pass
    
    campaign.save()
    return campaign


def delete_campaign(pk):
    """Deletes a campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()


# --- Keyword Services ---

def create_keyword(campaign_pk, name, description):
    """Creates a new keyword for a campaign."""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    if name:
        return Keyword.objects.create(campaign=campaign, name=name, description=description)
    return None


def update_keyword(pk, name, description):
    """Updates an existing keyword."""
    keyword = get_object_or_404(Keyword, pk=pk)
    keyword.name = name
    keyword.description = description
    keyword.save()
    return keyword


def delete_keyword(pk):
    """Deletes a keyword."""
    keyword = get_object_or_404(Keyword, pk=pk)
    keyword.delete()


# --- Tag Services ---

def create_tag(keyword_pk, name, description):
    """Creates a new tag for a keyword."""
    keyword = get_object_or_404(Keyword, pk=keyword_pk)
    if name:
        return Tag.objects.create(keyword=keyword, name=name, description=description)
    return None


def update_tag(pk, name, description):
    """Updates an existing tag."""
    tag = get_object_or_404(Tag, pk=pk)
    tag.name = name
    tag.description = description
    tag.save()
    return tag


def delete_tag(pk):
    """Deletes a tag."""
    tag = get_object_or_404(Tag, pk=pk)
    tag.delete()


# --- Global Settings Services ---

def update_global_settings(post_hours, post_minutes, post_seconds, comment_hours, comment_minutes, comment_seconds):
    """Updates global fetch intervals."""
    settings = get_object_or_404(GlobalSettings, pk=1)
    
    # Update Post Interval
    try:
        h = int(post_hours or 0)
        m = int(post_minutes or 0)
        s = int(post_seconds or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        settings.post_fetch_interval = total
    except ValueError:
        pass
    
    # Update Comment Interval
    try:
        h = int(comment_hours or 0)
        m = int(comment_minutes or 0)
        s = int(comment_seconds or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        settings.comment_fetch_interval = total
    except ValueError:
        pass
    
    settings.save()
    return settings


def delete_all_ingested_data():
    """Deletes all Reddit posts and comments and resets pointers."""
    RedditPost.objects.all().delete()
    RedditComment.objects.all().delete()
    
    settings = get_object_or_404(GlobalSettings, pk=1)
    settings.last_post_id = None
    settings.last_comment_id = None
    settings.empty_post_fetch_count = 0
    settings.empty_comment_fetch_count = 0
    settings.save()
    
    Campaign.objects.update(last_processed_post_id=0, last_processed_comment_id=0)
