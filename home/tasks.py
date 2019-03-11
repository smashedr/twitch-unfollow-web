from __future__ import absolute_import, unicode_literals
import json
import logging
import requests
import time
import urllib3
from django_statsd.clients import statsd
from django.conf import settings
from celery import task
from home.models import Followers, Webhooks

logger = logging.getLogger('celery')
urllib3.disable_warnings()


@task(name='process_unfollows')
def process_unfollows():
    hooks = Webhooks.objects.all()
    for hook in hooks:
        logger.debug('Starting process_channel for: {}'.format(hook.twitch_username))
        process_channel.delay(hook.pk)
        time.sleep(30)
    return 'Finished processing {} Webhooks.'.format(len(hooks))


@task(name='process_channel', retry_kwargs={'max_retries': 1, 'countdown': 120})
def process_channel(hook_pk):
    try:
        hook = Webhooks.objects.get(pk=hook_pk)
        logger.info('Starting unfollow run for channel: {}'.format(hook.twitch_username))
        followers, created = Followers.objects.get_or_create(user=hook.user, twitch_username=hook.twitch_username)
        original_followers = json.loads(followers.followers)
        url_string = 'https://api.twitch.tv/kraken/channels/{}/follows?direction=asc&limit=100&cursor='.format(
            hook.twitch_username)
        url_string += '{}'
        current_followers = []
        count = 0
        while True:
            count += 1
            if count == 1:
                cursor = 0

            url = url_string.format(cursor)
            r = requests.get(url, headers={'Client-ID': settings.TWITCH_CLIENT_ID})
            statsd.incr('tasks.process_channel.status_codes.{}'.format(r.status_code))
            if not r.ok:
                logger.warning(r.content.decode(r.encoding))
                r.raise_for_status()
            j = r.json()

            if '_cursor' in j:
                cursor = j['_cursor']
            else:
                break

            for x in j['follows']:
                current_followers.append(x['user']['name'])

            time.sleep(5)

        followers.followers = json.dumps(current_followers)
        followers.save()

        unfollow_list = []
        for unfollower in original_followers:
            if unfollower not in current_followers:
                unfollow_list.append(unfollower)

        if unfollow_list:
            message = '{} New Unfollow(s): {}'.format(len(unfollow_list), ', '.join(unfollow_list))
            send_alert.delay(hook_pk, message)
            logger.info('New Unfollows for {}: {}'.format(hook.twitch_username, ', '.join(unfollow_list)))

        return '{} processed {} followers with {} new unfollowers.'.format(
            hook.twitch_username, len(current_followers), len(unfollow_list))

    except Exception as error:
        statsd.incr('tasks.process_channel.errors')
        logger.exception(error)
        raise


@task(name='send_alert', retry_kwargs={'max_retries': 5, 'countdown': 120})
def send_alert(hook_pk, message):
    try:
        hook = Webhooks.objects.get(pk=hook_pk)
        body = {'content': message}
        r = requests.post(hook.webhook_url, json=body, timeout=30)
        statsd.incr('tasks.send_alert.status_codes.{}'.format(r.status_code))
        if r.status_code == 404:
            logger.warning('Hook {} removed by owner {} - {}'.format(
                hook.hook_id, hook.twitch_username, hook.webhook_url))
            hook.delete()
            statsd.incr('tasks.send_alert.hook_delete')
            return '404: Hook removed by owner and deleted from database.'

        if not r.ok:
            logger.warning(r.content.decode(r.encoding))
            r.raise_for_status()

        return '{}: {}'.format(r.status_code, r.content.decode(r.encoding))
    except Exception as error:
        statsd.incr('tasks.send_alert.errors')
        logger.exception(error)
        raise


@task(name='send_discord_message', retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_discord_message(url, message):
    try:
        body = {'content': message}
        r = requests.post(url, json=body, timeout=30)
        statsd.incr('tasks.send_discord_message.status_codes.{}'.format(r.status_code))
        if not r.ok:
            logger.warning(r.content.decode(r.encoding))
            r.raise_for_status()
        return '{}: {}'.format(r.status_code, r.content.decode(r.encoding))

    except Exception as error:
        statsd.incr('tasks.send_discord_message.errors.')
        logger.exception(error)
        raise
