from django.urls import path
from . import views
from . import api

app_name = 'campaigns'

urlpatterns = [
    # Global Settings
    path('settings/', views.global_settings_view, name='global_settings'),
    
    # Ingestion Progress API
    path('api/ingestion-progress/', views.get_ingestion_progress, name='ingestion_progress'),
    
    # Page Views
    path('', views.campaign_list, name='campaign_list'),
    path('<int:pk>/', views.campaign_detail, name='campaign_detail'),
    
    # API endpoints (AJAX)
    path('api/campaigns/create/', api.campaign_create_api, name='campaign_create_api'),
    path('api/campaigns/<int:pk>/update/', api.campaign_update_api, name='campaign_update_api'),
    path('api/campaigns/<int:pk>/delete/', api.campaign_delete_api, name='campaign_delete_api'),
    path('api/campaigns/<int:campaign_pk>/keywords/create/', api.keyword_create_api, name='keyword_create_api'),
    path('api/keywords/<int:pk>/update/', api.keyword_update_api, name='keyword_update_api'),
    path('api/keywords/<int:pk>/delete/', api.keyword_delete_api, name='keyword_delete_api'),
    path('api/keywords/<int:keyword_pk>/tags/create/', api.tag_create_api, name='tag_create_api'),
    path('api/tags/<int:pk>/update/', api.tag_update_api, name='tag_update_api'),
    path('api/tags/<int:pk>/delete/', api.tag_delete_api, name='tag_delete_api'),
    path('api/settings/update/', api.global_settings_update_api, name='global_settings_update_api'),
    path('api/settings/delete-data/', api.global_data_delete_api, name='global_data_delete_api'),
]
