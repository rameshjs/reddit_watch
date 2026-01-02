from django.shortcuts import render, get_object_or_404
from .models import Campaign, GlobalSettings, CampaignMatch, RedditPost, RedditComment


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


def global_settings_view(request):
    """Display global settings page."""
    settings, _ = GlobalSettings.objects.get_or_create(pk=1, defaults={'post_fetch_interval': 300, 'comment_fetch_interval': 360})
    return render(request, 'campaigns/global_settings.html', {'settings': settings})


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
