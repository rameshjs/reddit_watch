from django.contrib import admin
from .models import Campaign, Keyword, Tag


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['campaign', 'created_at']
    raw_id_fields = ['campaign']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'keyword', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    raw_id_fields = ['keyword']
