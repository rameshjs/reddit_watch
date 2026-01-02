"""
API module for AJAX endpoints.
All functions return JsonResponse with rendered HTML for dynamic updates.
"""
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Campaign, Keyword, GlobalSettings
from . import services


@require_http_methods(["POST"])
def campaign_create_api(request):
    """Create a new campaign and return updated campaigns table HTML."""
    name = request.POST.get('name')
    if name:
        is_watching = request.POST.get('is_watching') == 'on'
        services.create_campaign(
            name=name,
            description=request.POST.get('description', ''),
            is_watching=is_watching,
            hours=request.POST.get('hours'),
            minutes=request.POST.get('minutes'),
            seconds=request.POST.get('seconds')
        )
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def campaign_update_api(request, pk):
    """Update an existing campaign and return updated campaigns table HTML."""
    is_watching = request.POST.get('is_watching') == 'on'
    services.update_campaign(
        pk=pk,
        name=request.POST.get('name'),
        description=request.POST.get('description'),
        is_watching=is_watching,
        hours=request.POST.get('hours'),
        minutes=request.POST.get('minutes'),
        seconds=request.POST.get('seconds')
    )
    
    if request.POST.get('source') == 'detail':
        return JsonResponse({'success': True, 'reload': True})

    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def campaign_delete_api(request, pk):
    """Delete a campaign and return updated campaigns table HTML."""
    services.delete_campaign(pk)
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    html = render_to_string('campaigns/components/campaign/table.html', {'campaigns': campaigns}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_create_api(request, campaign_pk):
    """Create a new keyword and return updated keywords list HTML."""
    services.create_keyword(
        campaign_pk=campaign_pk,
        name=request.POST.get('name'),
        description=request.POST.get('description', '')
    )
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    html = render_to_string('campaigns/components/keyword/list.html', {'campaign': campaign}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_update_api(request, pk):
    """Update an existing keyword and return updated keyword card HTML."""
    keyword = services.update_keyword(
        pk=pk,
        name=request.POST.get('name'),
        description=request.POST.get('description')
    )
    
    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def keyword_delete_api(request, pk):
    """Delete a keyword and return updated keywords list HTML."""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    services.delete_keyword(pk)
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    html = render_to_string('campaigns/components/keyword/list.html', {'campaign': campaign}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_create_api(request, keyword_pk):
    """Create a new tag and return updated keyword card HTML."""
    tag = services.create_tag(
        keyword_pk=keyword_pk,
        name=request.POST.get('name'),
        description=request.POST.get('description', '')
    )
    
    if tag:
        keyword = tag.keyword
    else:
        keyword = get_object_or_404(Keyword, pk=keyword_pk)

    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_update_api(request, pk):
    """Update an existing tag and return updated keyword card HTML."""
    tag = services.update_tag(
        pk=pk,
        name=request.POST.get('name'),
        description=request.POST.get('description')
    )
    
    keyword = tag.keyword
    campaign = keyword.campaign
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def tag_delete_api(request, pk):
    """Delete a tag and return updated keyword card HTML."""
    tag = services.delete_tag(pk) # Note: services.delete_tag returns nothing, so we get objects before or handle it
    # Actually services.delete_tag deletes the object, so we can't access it after.
    # Refactor: We need keyword and campaign before deletion to render the template.
    # But wait, services.delete_tag takes PK. So let's fetch keyword/campaign first in view?
    # Or just fetch tag here to get relations.
    
    # Actually, let's look at logic... existing code did:
    # tag = get_object_or_404(...)
    # keyword = tag.keyword ...
    # tag.delete()
    
    # Let's override the service pattern slightly here or just grab it first.
    # services.delete_tag does the deletion.
    # We need to know the parent keyword to render the card.
    
    # Let's cheat and grab it first.
    from .models import Tag
    tag_obj = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    keyword = tag_obj.keyword
    campaign = keyword.campaign
    
    services.delete_tag(pk)
    
    # Refresh keyword to get updated tags
    keyword = get_object_or_404(Keyword.objects.prefetch_related('tags'), pk=keyword.pk)
    
    html = render_to_string('campaigns/components/keyword/card.html', {'campaign': campaign, 'keyword': keyword}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def global_settings_update_api(request):
    """Update global settings and return updated modal HTML."""
    settings = services.update_global_settings(
        post_hours=request.POST.get('post_hours'),
        post_minutes=request.POST.get('post_minutes'),
        post_seconds=request.POST.get('post_seconds'),
        comment_hours=request.POST.get('comment_hours'),
        comment_minutes=request.POST.get('comment_minutes'),
        comment_seconds=request.POST.get('comment_seconds')
    )
    
    html = render_to_string('campaigns/components/settings/global_modal.html', {'settings': settings}, request=request)
    return JsonResponse({'success': True, 'html': html})


@require_http_methods(["POST"])
def global_data_delete_api(request):
    """Delete all ingested data and reset pointers."""
    services.delete_all_ingested_data()
    # Return success, client will likely reload page
    return JsonResponse({'success': True, 'reload': True})
