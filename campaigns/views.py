from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
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
    """Create a new campaign"""
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    
    if name:
        campaign = Campaign.objects.create(name=name, description=description)
        return redirect('campaigns:campaign_detail', pk=campaign.pk)
    
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def campaign_update(request, pk):
    """Update an existing campaign"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.name = request.POST.get('name', campaign.name)
    campaign.description = request.POST.get('description', campaign.description)
    campaign.save()
    
    return redirect('campaigns:campaign_detail', pk=campaign.pk)


@require_http_methods(["POST"])
def campaign_delete(request, pk):
    """Delete a campaign"""
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    return redirect('campaigns:campaign_list')


@require_http_methods(["POST"])
def keyword_create(request, campaign_pk):
    """Create a new keyword for a campaign"""
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    
    if name:
        Keyword.objects.create(campaign=campaign, name=name, description=description)
    
    return redirect('campaigns:campaign_detail', pk=campaign_pk)


@require_http_methods(["POST"])
def keyword_update(request, pk):
    """Update an existing keyword"""
    keyword = get_object_or_404(Keyword, pk=pk)
    keyword.name = request.POST.get('name', keyword.name)
    keyword.description = request.POST.get('description', keyword.description)
    keyword.save()
    
    return redirect('campaigns:campaign_detail', pk=keyword.campaign.pk)


@require_http_methods(["POST"])
def keyword_delete(request, pk):
    """Delete a keyword"""
    keyword = get_object_or_404(Keyword, pk=pk)
    campaign_pk = keyword.campaign.pk
    keyword.delete()
    return redirect('campaigns:campaign_detail', pk=campaign_pk)


@require_http_methods(["POST"])
def tag_create(request, keyword_pk):
    """Create a new tag for a keyword"""
    keyword = get_object_or_404(Keyword, pk=keyword_pk)
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    
    if name:
        Tag.objects.create(keyword=keyword, name=name, description=description)
    
    return redirect('campaigns:campaign_detail', pk=keyword.campaign.pk)


@require_http_methods(["POST"])
def tag_update(request, pk):
    """Update an existing tag"""
    tag = get_object_or_404(Tag, pk=pk)
    tag.name = request.POST.get('name', tag.name)
    tag.description = request.POST.get('description', tag.description)
    tag.save()
    
    return redirect('campaigns:campaign_detail', pk=tag.keyword.campaign.pk)


@require_http_methods(["POST"])
def tag_delete(request, pk):
    """Delete a tag"""
    tag = get_object_or_404(Tag, pk=pk)
    campaign_pk = tag.keyword.campaign.pk
    tag.delete()
    return redirect('campaigns:campaign_detail', pk=campaign_pk)
