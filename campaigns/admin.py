from django.contrib import admin
from .models import Campaign, Keyword, Tag, RedditPost, RedditComment


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

@admin.register(RedditPost)
class RedditPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'campaign', 'score', 'num_comments', 'created_utc']
    search_fields = ['title', 'author']
    list_filter = ['campaign', 'created_utc']
    raw_id_fields = ['campaign']


@admin.register(RedditComment)
class RedditCommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'score', 'created_utc']
    search_fields = ['body', 'author']
    list_filter = ['created_utc']
    raw_id_fields = ['post']
