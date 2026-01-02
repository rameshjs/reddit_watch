from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    # Global Settings
    path('settings/', views.global_settings_view, name='global_settings'),
    path('settings/update/', views.global_settings_update, name='global_settings_update'),
    path('settings/delete-data/', views.global_data_delete, name='global_data_delete'),
    
    # Campaign URLs
    path('', views.campaign_list, name='campaign_list'),
    path('<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('create/', views.campaign_create, name='campaign_create'),
    path('<int:pk>/update/', views.campaign_update, name='campaign_update'),
    path('<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    
    # Keyword URLs
    path('<int:campaign_pk>/keywords/create/', views.keyword_create, name='keyword_create'),
    path('keywords/<int:pk>/update/', views.keyword_update, name='keyword_update'),
    path('keywords/<int:pk>/delete/', views.keyword_delete, name='keyword_delete'),
    
    # Tag URLs
    path('keywords/<int:keyword_pk>/tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:pk>/update/', views.tag_update, name='tag_update'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
]
