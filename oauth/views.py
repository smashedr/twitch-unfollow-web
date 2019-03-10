import logging
import requests
import urllib.parse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger('app')


def do_oauth(request):
    """
    # View  /oauth/
    """
    request.session['login_redirect_url'] = get_next_url(request)
    params = {
        'client_id': settings.TWITCH_CLIENT_ID,
        'redirect_uri': settings.TWITCH_REDIRECT_URI,
        'response_type': settings.OAUTH_RESPONSE_TYPE,
        'scope': settings.TWITCH_SCOPE,
    }
    url_params = urllib.parse.urlencode(params)
    url = 'https://id.twitch.tv/oauth2/authorize?{}'.format(url_params)
    return HttpResponseRedirect(url)


def callback(request):
    """
    # View  /oauth/callback/
    """
    try:
        oauth_code = request.GET['code']
        logger.debug('oauth_code: {}'.format(oauth_code))
        access_token = twitch_token(oauth_code)
        logger.debug('access_token: {}'.format(access_token))
        twitch_profile = get_twitch(access_token)
        logger.debug('twitch_profile: {}'.format(twitch_profile))
        logger.debug(twitch_profile)
        auth = login_user(request, twitch_profile)
        if not auth:
            err_msg = 'Unable to complete login process. Report as a Bug.'
            return HttpResponse(err_msg, content_type='text/plain')
        try:
            next_url = request.session['login_redirect_url']
        except Exception:
            next_url = '/'
        return HttpResponseRedirect(next_url)

    except Exception as error:
        logger.exception(error)
        err_msg = 'Fatal Login Error. Report as Bug: %s' % error
        return HttpResponse(err_msg, content_type='text/plain')


@require_http_methods(['POST'])
def log_out(request):
    """
    View  /oauth/logout/
    """
    next_url = get_next_url(request)
    request.session['login_next_url'] = next_url
    logout(request)
    return redirect(next_url)


def login_user(request, data):
    """
    Login or Create New User
    """
    try:
        user = User.objects.filter(username=data['username']).get()
        user = update_profile(user, data)
        user.save()
        login(request, user)
        return True
    except ObjectDoesNotExist:
        user = User.objects.create_user(data['username'], data['email'])
        user = update_profile(user, data)
        user.save()
        login(request, user)
        return True
    except Exception as error:
        logger.exception(error)
        return False


def twitch_token(code):
    """
    Post OAuth code to Twitch and Return access_token
    """
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'client_id': settings.TWITCH_CLIENT_ID,
        'client_secret': settings.TWITCH_CLIENT_SECRET,
        'grant_type': settings.TWITCH_GRANT_TYPE,
        'redirect_uri': settings.TWITCH_REDIRECT_URI,
        'code': code,
    }
    headers = {'Accept': 'application/json'}
    r = requests.post(url, data=data, headers=headers, timeout=10)
    logger.debug('status_code: {}'.format(r.status_code))
    logger.debug('content: {}'.format(r.content))
    return r.json()['access_token']


def get_twitch(access_token):
    """
    Get Twitch Profile for Authenticated User
    """
    url = 'https://api.twitch.tv/kraken/user'
    headers = {
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Authorization': 'OAuth {}'.format(access_token),
    }
    r = requests.get(url, headers=headers, timeout=10)
    logger.debug('status_code: {}'.format(r.status_code))
    logger.debug('content: {}'.format(r.content))
    twitch_profile = r.json()
    return {
        'username': twitch_profile['name'],
        'first_name': twitch_profile['display_name'],
        'email': twitch_profile['email'],
        'email_verified': twitch_profile['email_verified'],
        'user_id': twitch_profile['_id'],
        'logo_url': twitch_profile['logo'],
    }


def update_profile(user, data):
    """
    Update user_profile from GitHub data
    """
    user.first_name = data['first_name']
    user.email = data['email']
    user.profile.email_verified = data['email_verified']
    user.profile.twitch_id = data['user_id']
    user.profile.logo_url = data['logo_url']
    return user


def get_next_url(request):
    """
    Determine 'next' Parameter
    """
    try:
        next_url = request.GET['next']
    except Exception:
        try:
            next_url = request.POST['next']
        except Exception:
            try:
                next_url = request.session['login_next_url']
            except Exception:
                next_url = '/'
    if not next_url:
        next_url = '/'
    return next_url
