import logging
from django.conf import settings
from django.shortcuts import render, redirect
# from home.models import Webhooks

logger = logging.getLogger('app')


def home_view(request):
    # View: /
    return render(request, 'home.html')


def join_discord(request):
    # View: /discord/
    return redirect(settings.APP_DISCORD_INVITE)
