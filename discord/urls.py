from django.urls import path

import discord.views as oauth

app_name = 'discord'


urlpatterns = [
    path('', oauth.do_oauth, name='login'),
    path('callback/', oauth.callback, name='callback'),
]
