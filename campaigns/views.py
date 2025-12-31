from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Campaign, Keyword, Tag


def campaign_list(request):
    """Display all campaigns"""
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/campaign_list.html', {'campaigns': campaigns})


def campaign_detail(request, pk):
    """Display campaign details with keywords and tags"""
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=pk)
    return render(request, 'campaigns/campaign_detail.html', {'campaign': campaign})


@require_http_methods(["POST"])
def campaign_create(request):
    """Create a new campaign and return updated campaigns container"""
    name = request.POST.get('name')
    if name:
        Campaign.objects.create(name=name, description=request.POST.get('description', ''))
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/partials/campaign_list_partials.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def campaign_update(request, pk):
    """Update an existing campaign and return updated campaigns container"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.name = request.POST.get('name', campaign.name)
    campaign.description = request.POST.get('description', campaign.description)
    campaign.save()
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/partials/campaign_list_partials.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def campaign_delete(request, pk):
    """Delete a campaign and return updated campaigns container"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    
    campaigns = Campaign.objects.all().prefetch_related('keywords')
    return render(request, 'campaigns/partials/campaign_list_partials.html#campaigns_container', {'campaigns': campaigns})


@require_http_methods(["POST"])
def keyword_create(request, campaign_pk):
    """Create a new keyword and return updated keywords list"""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    name = request.POST.get('name')
    
    if name:
        Keyword.objects.create(campaign=campaign, name=name, description=request.POST.get('description', ''))
    
    # Refetch campaign with updated keywords
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    return render(request, 'campaigns/partials/keyword_partials.html#keywords_container', {'campaign': campaign})


@require_http_methods(["POST"])
def keyword_update(request, pk):
    """Update an existing keyword and return updated keyword card"""
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=pk)
    keyword.name = request.POST.get('name', keyword.name)
    keyword.description = request.POST.get('description', keyword.description)
    keyword.save()
    
    campaign = keyword.campaign
    return render(request, 'campaigns/partials/keyword_partials.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def keyword_delete(request, pk):
    """Delete a keyword and return updated keywords list"""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    keyword.delete()
    
    campaign = get_object_or_404(Campaign.objects.prefetch_related('keywords__tags'), pk=campaign_pk)
    return render(request, 'campaigns/partials/keyword_partials.html#keywords_container', {'campaign': campaign})


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
    return render(request, 'campaigns/partials/keyword_partials.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def tag_update(request, pk):
    """Update an existing tag and return updated keyword card"""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    tag.name = request.POST.get('name', tag.name)
    tag.description = request.POST.get('description', tag.description)
    tag.save()
    
    keyword = tag.keyword
    campaign = keyword.campaign
    return render(request, 'campaigns/partials/keyword_partials.html#keyword_card', {'campaign': campaign, 'keyword': keyword})


@require_http_methods(["POST"])
def tag_delete(request, pk):
    """Delete a tag and return updated keyword card"""
    tag = get_object_or_404(Tag.objects.select_related('keyword__campaign'), pk=pk)
    keyword = tag.keyword
    campaign = keyword.campaign
    tag.delete()
    
    # Refetch keyword to get updated tags
    keyword = get_object_or_404(Keyword.objects.select_related('campaign').prefetch_related('tags'), pk=keyword.pk)
    return render(request, 'campaigns/partials/keyword_partials.html#keyword_card', {'campaign': campaign, 'keyword': keyword})
