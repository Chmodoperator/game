from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<empire_id>\w+)/$', consumers.GameConsumer.as_asgi()),
    re_path(r'ws/chat/global/$', consumers.GlobalChatConsumer.as_asgi()),
    re_path(r'ws/chat/alliance/(?P<alliance_id>\w+)/$', consumers.AllianceChatConsumer.as_asgi()),
] 