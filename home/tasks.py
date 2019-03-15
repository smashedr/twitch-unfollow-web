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

        # change to loop to trigger new function: process_unfollowed_user
        if unfollow_list:
            logger.info('New Unfollows for {}: {}'.format(hook.twitch_username, ', '.join(unfollow_list)))
            for unfollower in unfollow_list:
                process_unfollowed_user.delay(hook_pk, unfollower)
            message = '{} New Unfollow(s): {}'.format(len(unfollow_list), ', '.join(unfollow_list))
            send_alert.delay(hook_pk, message)

        return '{} processed {} followers with {} new unfollowers.'.format(
            hook.twitch_username, len(current_followers), len(unfollow_list))

    except Exception as error:
        statsd.incr('tasks.process_channel.errors')
        logger.exception(error)
        raise


@task(name='process_unfollowed_user', retry_kwargs={'max_retries': 5, 'countdown': 120})
def process_unfollowed_user(hook_pk, username):
    # hook = Webhooks.objects.get(pk=hook_pk)
    url = 'https://api.twitch.tv/kraken/users?login={}'.format(username)
    r = requests.get(url, headers={'Accept': 'application/vnd.twitchtv.v5+json'}, timeout=30)
    if not r.ok:
        logger.warning(r.content.decode(r.encoding))
        r.raise_for_status()

    data = r.json()
    if not data['users']:
        # users was deleted or renamed
        message = 'Renamed or Deleted Account: {0}\n<https://www.twitch.tv/{0}>'.format(username.lower())
        send_alert.delay(hook_pk, message)
        return 'Unfollower Changed/Deleted: {}'.format(username)

    url = 'https://api.twitch.tv/kraken/channels/{}'.format(data['users'][0]['_id'])
    r = requests.get(url, headers={'Accept': 'application/vnd.twitchtv.v5+json'}, timeout=30)
    if not r.ok:
        logger.error(r.content.decode(r.encoding))
        r.raise_for_status()

    data = r.json()
    account_type = data['broadcaster_type'] if data['broadcaster_type'] else 'no'
    message = 'New Unfollower: {0}\nPartner/Affiliate: {1}\nViews/Follows: {2}/{3}\n<{4}>'.format(
        data['display_name'], account_type, data['views'], data['followers'], data['url'])
    send_alert.delay(hook_pk, message)
    return 'Unfollower Processed: {}.'.format(username)


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
