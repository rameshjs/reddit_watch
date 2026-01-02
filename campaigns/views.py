from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Campaign, Keyword, Tag, GlobalSettings, CampaignMatch


def campaign_list(request):
    """Display all campaigns"""
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    settings, _ = GlobalSettings.objects.get_or_create(
        pk=1,
        defaults={
            'post_fetch_interval': 300,
            'comment_fetch_interval': 360
        }
    )
    return render(request, 'campaigns/campaign_list.html', {'campaigns': campaigns, 'settings': settings})


def campaign_detail(request, pk):
    """Display campaign details with keywords and tags"""
    campaign = get_object_or_404(
        Campaign.objects.prefetch_related(
            'keywords__tags',
        ), 
        pk=pk
    )
    
    # Filter Matches
    matches = CampaignMatch.objects.filter(campaign=campaign).select_related('keyword', 'post', 'comment').order_by('-created_at')
    
    # 1. Keyword Filter
    keyword_id = request.GET.get('keyword')
    if keyword_id:
        matches = matches.filter(keyword_id=keyword_id)
        
    # 2. Type Filter (post vs comment)
    match_type = request.GET.get('type')
    if match_type == 'post':
        matches = matches.filter(post__isnull=False)
    elif match_type == 'comment':
        matches = matches.filter(comment__isnull=False)
        
    # 3. Subreddit Filter
    subreddit = request.GET.get('subreddit')
    if subreddit:
        # Complex query to check both post and comment subreddit
        from django.db.models import Q
        matches = matches.filter(
            Q(post__subreddit__icontains=subreddit) | 
            Q(comment__subreddit__icontains=subreddit)
        )

    # 4. Date Filter
    from django.utils.dateparse import parse_date
    date_from = request.GET.get('date_from')
    if date_from:
        d_from = parse_date(date_from)
        if d_from:
            matches = matches.filter(created_at__date__gte=d_from)
            
    date_to = request.GET.get('date_to')
    if date_to:
        d_to = parse_date(date_to)
        if d_to:
            matches = matches.filter(created_at__date__lte=d_to)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(matches, 20) # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    is_filtered = any([
        keyword_id,
        match_type and match_type != 'all',
        subreddit,
        date_from,
        date_to
    ])
    
    context = {
        'campaign': campaign,
        'matches': page_obj,
        'match_count': paginator.count,
        'is_filtered': is_filtered,
        # Pass filters back to template to keep state
        'filters': {
            'keyword': int(keyword_id) if keyword_id else '',
            'type': match_type or 'all',
            'subreddit': subreddit or '',
            'date_from': date_from or '',
            'date_to': date_to or '',
        }
    }
    return render(request, 'campaigns/campaign_detail.html', context)


@require_http_methods(["POST"])
def campaign_create(request):
    """Create a new campaign and return updated campaigns container"""
    name = request.POST.get('name')
    if name:
        is_watching = request.POST.get('is_watching') == 'on'
        # Calculate seconds from H/M/S
        try:
            h = int(request.POST.get('hours', 0) or 0)
            m = int(request.POST.get('minutes', 0) or 0)
            s = int(request.POST.get('seconds', 0) or 0)
            
            interval_seconds = (h * 3600) + (m * 60) + s
            if interval_seconds < 30:
                interval_seconds = 30
        except ValueError:
            interval_seconds = 3600 # Default 1 hour
            
        campaign = Campaign.objects.create(
            name=name, 
            description=request.POST.get('description', ''),
            is_watching=is_watching,
            match_interval_seconds=interval_seconds
        )
    
    # Check if update came from detail page
    if request.POST.get('source') == 'detail':
        # Refetch to ensure optimizations (though single object is cheap)
        campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign.pk)
        return render(request, 'campaigns/campaign_detail.html', {'campaign': campaign})

    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/campaign_list.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def campaign_update(request, pk):
    """Update an existing campaign and return updated campaigns container"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.name = request.POST.get('name', campaign.name)
    campaign.description = request.POST.get('description', campaign.description)
    
    # Handle checkbox for is_watching
    campaign.is_watching = request.POST.get('is_watching') == 'on'
    
    # Handle watch_interval_seconds
    try:
        h = int(request.POST.get('hours', 0) or 0)
        m = int(request.POST.get('minutes', 0) or 0)
        s = int(request.POST.get('seconds', 0) or 0)
        
        # Only update if we have at least some time input, or if it's explicitly 0 (though 0 becomes 30)
        # Assuming form always sends these
        total = (h * 3600) + (m * 60) + s
        
        if total < 30:
            total = 30
            
        campaign.match_interval_seconds = total
    except ValueError:
        pass # Keep existing value if invalid
            
    campaign.save()
    
    # Check if update came from detail page
    if request.POST.get('source') == 'detail':
        # Refetch to ensure optimizations
        campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign.pk)
        return render(request, 'campaigns/campaign_detail.html', {'campaign': campaign})

    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/campaign_list.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def campaign_delete(request, pk):
    """Delete a campaign and return updated campaigns container"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/campaign_list.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def keyword_create(request, campaign_pk):
    """Create a new keyword and return updated keywords list"""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    name = request.POST.get('name')
    
    if name:
        Keyword.objects.create(campaign=campaign, name=name, description=request.POST.get('description', ''))
    
    # Refetch campaign with updated keywords
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    return render(request, 'campaigns/campaign_detail.html#keywords_container', {'campaign': campaign})


@require_http_methods(["POST"])
def keyword_update(request, pk):
    """Update an existing keyword and return updated keyword card"""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=pk)
    keyword.name = request.POST.get('name', keyword.name)
    keyword.description = request.POST.get('description', keyword.description)
    keyword.save()
    
    campaign = keyword.campaign
    return render(request, 'campaigns/campaign_detail.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def keyword_delete(request, pk):
    """Delete a keyword and return updated keywords list"""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    keyword.delete()
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    return render(request, 'campaigns/campaign_detail.html#keywords_container', {'campaign': campaign})


@require_http_methods(["POST"])
def tag_create(request, keyword_pk):
    """Create a new tag and return updated keyword card"""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword_pk)
    name = request.POST.get('name')
    
    if name:
        Tag.objects.create(keyword=keyword, name=name, description=request.POST.get('description', ''))
        # Refetch to get updated tags
        keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword_pk)
    
    campaign = keyword.campaign
    return render(request, 'campaigns/campaign_detail.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def tag_update(request, pk):
    """Update an existing tag and return updated keyword card"""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    tag.name = request.POST.get('name', tag.name)
    tag.description = request.POST.get('description', tag.description)
    tag.save()
    
    keyword = tag.keyword
    campaign = keyword.campaign
    return render(request, 'campaigns/campaign_detail.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def tag_delete(request, pk):
    """Delete a tag and return updated keyword card"""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    keyword = tag.keyword
    campaign = keyword.campaign
    tag.delete()
    
    # Refetch keyword to get updated tags
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword.pk)
    return render(request, 'campaigns/campaign_detail.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


def global_settings_view(request):
    """Display global settings page"""
    settings, created = GlobalSettings.objects.get_or_create(
        pk=1,
        defaults={
            'post_fetch_interval': 300,
            'comment_fetch_interval': 360
        }
    )
    return render(request, 'campaigns/global_settings.html', {'settings': settings})


@require_http_methods(["POST"])
def global_settings_update(request):
    """Update global settings and return updated page"""
    settings = get_object_or_404(GlobalSettings, pk=1)
    
    # Handle post_fetch_interval
    try:
        h = int(request.POST.get('post_hours', 0) or 0)
        m = int(request.POST.get('post_minutes', 0) or 0)
        s = int(request.POST.get('post_seconds', 0) or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        settings.post_fetch_interval = total
    except ValueError:
        pass
    
    # Handle comment_fetch_interval
    try:
        h = int(request.POST.get('comment_hours', 0) or 0)
        m = int(request.POST.get('comment_minutes', 0) or 0)
        s = int(request.POST.get('comment_seconds', 0) or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        settings.comment_fetch_interval = total
    except ValueError:
        pass
    
    settings.save()
    
    # Return modal partial for HTMX requests
    return render(request, 'campaigns/campaign_list.html#global_settings_modal', {'settings': settings})

