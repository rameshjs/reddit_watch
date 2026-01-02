from django.contrib import admin
from .models import Campaign, Keyword, Tag, RedditPost, RedditComment, GlobalSettings, CampaignMatch


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'post_fetch_interval', 'comment_fetch_interval', 'last_post_id', 'last_comment_id']
    
    def has_add_permission(self, request):
        if GlobalSettings.objects.exists():
            return False
        return True


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_watching', 'match_interval_seconds', 'last_matched_at', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['is_watching', 'created_at']


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
    list_display = ['title', 'subreddit', 'score', 'num_comments', 'created_utc']
    search_fields = ['title', 'author', 'subreddit']
    list_filter = ['subreddit', 'created_utc', 'is_video', 'over_18']


@admin.register(RedditComment)
class RedditCommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'subreddit', 'score', 'created_utc']
    search_fields = ['body', 'author', 'subreddit']
    list_filter = ['subreddit', 'created_utc']


@admin.register(CampaignMatch)
class CampaignMatchAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'keyword', 'get_content_type', 'created_at']
    list_filter = ['campaign', 'keyword', 'created_at']
    raw_id_fields = ['campaign', 'keyword', 'post', 'comment']
    
    def get_content_type(self, obj):
        if obj.post:
            return "Post"
        if obj.comment:
            return "Comment"
        return "Unknown"
    get_content_type.short_description = 'Type'
