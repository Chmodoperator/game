from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from game.models import Alliance


@login_required
def global_chat_view(request):
    """Global chat room"""
    empire = request.user.empire
    
    context = {
        'empire': empire,
        'chat_type': 'global',
    }
    
    return render(request, 'chat/chat.html', context)


@login_required
def alliance_chat_view(request, alliance_id):
    """Alliance-specific chat room"""
    empire = request.user.empire
    alliance = get_object_or_404(Alliance, id=alliance_id)
    
    # Check if user is member of alliance
    if empire not in alliance.members.all():
        return render(request, 'chat/chat_denied.html', {'alliance': alliance})
    
    context = {
        'empire': empire,
        'alliance': alliance,
        'chat_type': 'alliance',
    }
    
    return render(request, 'chat/chat.html', context)
