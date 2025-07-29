from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('global/', views.global_chat_view, name='global_chat'),
    path('alliance/<int:alliance_id>/', views.alliance_chat_view, name='alliance_chat'),
] 