from __future__ import absolute_import, unicode_literals
import logging
import requests
import urllib3
from django_statsd.clients import statsd
from django.conf import settings
from celery import task
from home.models import Followers, Webhooks

logger = logging.getLogger('celery')
urllib3.disable_warnings()


@task(name='process_unfollows')
def process_unfollows():
    logger.info('process_hacks: executed')
    hooks = Webhooks.objects.all()
    for hook in hooks:
        logger.info('Processing channel: {}'.format(hook.twitch_username))
    return 'Processed {} Webhooks.'.format(len(hooks))


@task(name='send_alert', retry_kwargs={'max_retries': 5, 'countdown': 120})
def send_alert(hook_pk, message):
    try:
        hook = Webhooks.objects.get(pk=hook_pk)
        body = {'content': message}
        r = requests.post(hook.webhook_url, json=body, timeout=30)
        statsd.incr('tasks.send_alert.status_codes.{}'.format(r.status_code))
        if r.status_code == 404:
            logger.warning('Hook {} removed by owner {} - {}'.format(
                hook.hook_id, hook.owner_username, hook.webhook_url))
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
