from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Webhooks(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    twitch_username = models.CharField(max_length=255)
    webhook_url = models.URLField(unique=True)
    hook_id = models.CharField(max_length=255, blank=True, null=True)
    guild_id = models.CharField(max_length=255, blank=True, null=True)
    channel_id = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}: {}'.format(self.twitch_username, self.hook_id)

    class Meta:
        verbose_name = 'Webhooks'
        verbose_name_plural = 'Webhooks'


class Followers(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    twitch_username = models.CharField(max_length=255)
    followers = models.TextField(default='[]')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} Followers'.format(self.twitch_username)

    class Meta:
        verbose_name = 'Followers'
        verbose_name_plural = 'Followers'
