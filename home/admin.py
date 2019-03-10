from django.contrib import admin
from home.models import Followers, Webhooks

admin.site.register(Followers)


@admin.register(Webhooks)
class WebhooksAdmin(admin.ModelAdmin):
    list_display = ('twitch_username', 'hook_id', 'active')
