import logging
from django.conf import settings
from django.shortcuts import render, redirect
from home.models import Webhooks

logger = logging.getLogger('app')


def home_view(request):
    # View: /
    if not request.user.is_authenticated:
        return render(request, 'home.html')
    try:
        webhook = Webhooks.objects.get(user=request.user)
    except Exception:
        webhook = None
    return render(request, 'home.html', {'webhook': webhook})


def join_discord(request):
    # View: /discord/
    return redirect(settings.APP_DISCORD_INVITE)
