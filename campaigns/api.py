"""
API module for AJAX endpoints.
All functions return JsonResponse with rendered HTML for dynamic updates.
"""
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Campaign, Keyword, Tag, GlobalSettings


@require_http_methods(["POST"])
def campaign_create_api(request):
    """Create a new campaign and return updated campaigns table HTML."""
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
        Campaign.objects.create(name=name, description=request.POST.get('description', ''), is_watching=is_watching, match_interval_seconds=interval_seconds)
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def campaign_update_api(request, pk):
    """Update an existing campaign and return updated campaigns table HTML."""
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
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def campaign_delete_api(request, pk):
    """Delete a campaign and return updated campaigns table HTML."""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_create_api(request, campaign_pk):
    """Create a new keyword and return updated keywords list HTML."""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    name = request.POST.get('name')
    
    if name:
        Keyword.objects.create(campaign=campaign, name=name, description=request.POST.get('description', ''))
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    html = render_to_string('campaigns/components/keyword/list.html', {'campaign': campaign}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_update_api(request, pk):
    """Update an existing keyword and return updated keyword card HTML."""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=pk)
    keyword.name = request.POST.get('name', keyword.name)
    keyword.description = request.POST.get('description', keyword.description)
    keyword.save()
    
    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_delete_api(request, pk):
    """Delete a keyword and return updated keywords list HTML."""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    keyword.delete()
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    html = render_to_string('campaigns/components/keyword/list.html', {'campaign': campaign}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_create_api(request, keyword_pk):
    """Create a new tag and return updated keyword card HTML."""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword_pk)
    name = request.POST.get('name')
    
    if name:
        Tag.objects.create(keyword=keyword, name=name, description=request.POST.get('description', ''))
        keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword_pk)
    
    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_update_api(request, pk):
    """Update an existing tag and return updated keyword card HTML."""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    tag.name = request.POST.get('name', tag.name)
    tag.description = request.POST.get('description', tag.description)
    tag.save()
    
    keyword = tag.keyword
    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_delete_api(request, pk):
    """Delete a tag and return updated keyword card HTML."""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    keyword = tag.keyword
    campaign = keyword.campaign
    tag.delete()
    
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword.pk)
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def global_settings_update_api(request):
    """Update global settings and return updated modal HTML."""
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
    html = render_to_string('campaigns/components/settings/global_modal.html', {'settings': settings}, request=request)
    return JsonResponse({'success': True, 'html': html})
