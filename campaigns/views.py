from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import Campaign, Keyword, Tag, GlobalSettings, CampaignMatch, RedditPost, RedditComment


def campaign_list(request):
    """Display all campaigns."""
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
    """Display campaign details with keywords and tags."""
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=pk)
    
    # Filter Matches
    matches = CampaignMatch.objects.filter(campaign=campaign).select_related('keyword', 'post', 'comment').order_by('-created_at')
    
    keyword_id = request.GET.get('keyword')
    if keyword_id:
        matches = matches.filter(keyword_id=keyword_id)
    
    match_type = request.GET.get('type')
    if match_type == 'post':
        matches = matches.filter(post__isnull=False)
    elif match_type == 'comment':
        matches = matches.filter(comment__isnull=False)
    
    subreddit = request.GET.get('subreddit')
    if subreddit:
        from django.db.models import Q
        matches = matches.filter(Q(post__subreddit__icontains=subreddit) | Q(comment__subreddit__icontains=subreddit))

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

    from django.core.paginator import Paginator
    paginator = Paginator(matches, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    is_filtered = any([keyword_id, match_type and match_type != 'all', subreddit, date_from, date_to])
    
    context = {
        'campaign': campaign,
        'matches': page_obj,
        'match_count': paginator.count,
        'is_filtered': is_filtered,
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
    """Create a new campaign (non-AJAX fallback)."""
    name = request.POST.get('name')
    if name:
        is_watching = request.POST.get('is_watching') == 'on'
        try:
            h = int(request.POST.get('hours', 0) or 0)
            m = int(request.POST.get('minutes', 0) or 0)
            s = int(request.POST.get('seconds', 0) or 0)
            interval_seconds = (h * 3600) + (m * 60) + s
            if interval_seconds < 30:
                interval_seconds = 30
        except ValueError:
            interval_seconds = 3600
        campaign = Campaign.objects.create(name=name, description=request.POST.get('description', ''), is_watching=is_watching, match_interval_seconds=interval_seconds)
        
        if request.POST.get('source') == 'detail':
            return redirect('campaigns:campaign_detail', pk=campaign.pk)
    
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def campaign_update(request, pk):
    """Update an existing campaign (non-AJAX fallback)."""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.name = request.POST.get('name', campaign.name)
    campaign.description = request.POST.get('description', campaign.description)
    campaign.is_watching = request.POST.get('is_watching') == 'on'
    
    try:
        h = int(request.POST.get('hours', 0) or 0)
        m = int(request.POST.get('minutes', 0) or 0)
        s = int(request.POST.get('seconds', 0) or 0)
        total = (h * 3600) + (m * 60) + s
        if total < 30:
            total = 30
        campaign.match_interval_seconds = total
    except ValueError:
        pass
    
    campaign.save()
    
    if request.POST.get('source') == 'detail':
        return redirect('campaigns:campaign_detail', pk=campaign.pk)
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def campaign_delete(request, pk):
    """Delete a campaign (non-AJAX fallback)."""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def keyword_create(request, campaign_pk):
    """Create a new keyword (non-AJAX fallback)."""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    name = request.POST.get('name')
    if name:
        Keyword.objects.create(campaign=campaign, name=name, description=request.POST.get('description', ''))
    return redirect('campaigns:campaign_detail', pk=campaign_pk)


@require_http_methods(["POST"])
def keyword_update(request, pk):
    """Update an existing keyword (non-AJAX fallback)."""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign'), pk=pk)
    keyword.name = request.POST.get('name', keyword.name)
    keyword.description = request.POST.get('description', keyword.description)
    keyword.save()
    return redirect('campaigns:campaign_detail', pk=keyword.campaign.pk)


@require_http_methods(["POST"])
def keyword_delete(request, pk):
    """Delete a keyword (non-AJAX fallback)."""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    keyword.delete()
    return redirect('campaigns:campaign_detail', pk=campaign_pk)


@require_http_methods(["POST"])
def tag_create(request, keyword_pk):
    """Create a new tag (non-AJAX fallback)."""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign'), pk=keyword_pk)
    name = request.POST.get('name')
    if name:
        Tag.objects.create(keyword=keyword, name=name, description=request.POST.get('description', ''))
    return redirect('campaigns:campaign_detail', pk=keyword.campaign.pk)


@require_http_methods(["POST"])
def tag_update(request, pk):
    """Update an existing tag (non-AJAX fallback)."""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    tag.name = request.POST.get('name', tag.name)
    tag.description = request.POST.get('description', tag.description)
    tag.save()
    return redirect('campaigns:campaign_detail', pk=tag.keyword.campaign.pk)


@require_http_methods(["POST"])
def tag_delete(request, pk):
    """Delete a tag (non-AJAX fallback)."""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    campaign_pk = tag.keyword.campaign.pk
    tag.delete()
    return redirect('campaigns:campaign_detail', pk=campaign_pk)


def global_settings_view(request):
    """Display global settings page."""
    settings, _ = GlobalSettings.objects.get_or_create(pk=1, defaults={'post_fetch_interval': 300, 'comment_fetch_interval': 360})
    return render(request, 'campaigns/global_settings.html', {'settings': settings})


@require_http_methods(["POST"])
def global_settings_update(request):
    """Update global settings (non-AJAX fallback)."""
    settings = get_object_or_404(GlobalSettings, pk=1)
    
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
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def global_data_delete(request):
    """Delete all ingested data and reset pointers."""
    RedditPost.objects.all().delete()
    RedditComment.objects.all().delete()
    
    settings = get_object_or_404(GlobalSettings, pk=1)
    settings.last_post_id = None
    settings.last_comment_id = None
    settings.empty_post_fetch_count = 0
    settings.empty_comment_fetch_count = 0
    settings.save()
    
    Campaign.objects.update(last_processed_post_id=0, last_processed_comment_id=0)
    messages.success(request, "All ingested data has been successfully deleted.")
    return redirect('campaigns:campaign_list')


def get_ingestion_progress(request):
    """API endpoint to get real-time ingestion progress from Redis."""
    import json
    import redis
    from django.conf import settings as django_settings
    from django.http import JsonResponse
    
    try:
        r = redis.from_url(django_settings.REDIS_URL)
        progress_raw = r.get('reddit_watch:ingestion_progress')
        
        if progress_raw:
            progress = json.loads(progress_raw)
        else:
            progress = {
                'posts': {'last_fetch_at': None, 'last_count': 0, 'new_count': 0, 'total': RedditPost.objects.count(), 'status': 'unknown'},
                'comments': {'last_fetch_at': None, 'last_count': 0, 'new_count': 0, 'total': RedditComment.objects.count(), 'status': 'unknown'}
            }
        
        return JsonResponse(progress)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
