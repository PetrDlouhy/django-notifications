# -*- coding: utf-8 -*-
''' Django Notifications example views '''
from distutils.version import \
    StrictVersion  # pylint: disable=no-name-in-module,import-error

from django import get_version
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.generic import ListView
from swapper import load_model

from notifications import settings as notification_settings
from notifications.helpers import get_notification_list
from notifications.utils import slug2id

Notification = load_model('notifications', 'Notification')

if StrictVersion(get_version()) >= StrictVersion('1.7.0'):
    from django.http import JsonResponse  # noqa
else:
    # Django 1.6 doesn't have a proper JsonResponse
    import json

    from django.http import HttpResponse  # noqa

    def date_handler(obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    def JsonResponse(data):  # noqa
        return HttpResponse(
            json.dumps(data, default=date_handler),
            content_type="application/json")


class NotificationViewList(ListView):
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = notification_settings.get_config()['PAGINATE_BY']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(NotificationViewList, self).dispatch(
            request, *args, **kwargs)


class AllNotificationsList(NotificationViewList):
    """
    Index page for authenticated user
    """

    def get_queryset(self):
        if notification_settings.get_config()['SOFT_DELETE']:
            qset = self.request.user.notifications.active()
        else:
            qset = self.request.user.notifications.all()
        return qset


class UnreadNotificationsList(NotificationViewList):

    def get_queryset(self):
        return self.request.user.notifications.unread()


@login_required
def mark_all_as_read(request):
    request.user.notifications.mark_all_as_read()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))
    return redirect('notifications:unread')


@login_required
def mark_as_read(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)
    notification.mark_as_read()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@login_required
def mark_as_unread(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)
    notification.mark_as_unread()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@login_required
def delete(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)

    if notification_settings.get_config()['SOFT_DELETE']:
        notification.deleted = True
        notification.save()
    else:
        notification.delete()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:all')


@never_cache
def live_unread_notification_count(request):
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {
            'unread_count': 0
        }
    else:
        data = {
            'unread_count': request.user.notifications.unread().count(),
        }
    return JsonResponse(data)


def get_object_url(instance, notification, request):
    """
    Get url representing the instance object.
    This will return instance.get_url_for_notifications()
    with parameters `notification` and `request`,
    if it is defined and get_absolute_url() otherwise
    """
    if hasattr(instance, 'get_url_for_notifications'):
        return instance.get_url_for_notifications(notification, request)
    elif hasattr(instance, 'get_absolute_url'):
        return instance.get_absolute_url()
    return None


@never_cache
def live_unread_notification_list(request):
    ''' Return a json with a unread notification list '''
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {
            'unread_count': 0,
            'unread_list': []
        }
        return JsonResponse(data)

    unread_list = get_notification_list(request, 'unread')

    unread_list = []

    for notification in request.user.notifications.unread()[0:num_to_fetch]:
        struct = model_to_dict(notification)
        struct['slug'] = id2slug(notification.id)
        if notification.actor:
            struct['actor'] = str(notification.actor)
            actor_url = get_object_url(
                notification.actor, notification, request)
            if actor_url:
                struct['actor_url'] = actor_url
        if notification.target:
            struct['target'] = str(notification.target)
            target_url = get_object_url(
                notification.target, notification, request)
            if target_url:
                struct['target_url'] = target_url
        if notification.action_object:
            struct['action_object'] = str(notification.action_object)
            action_object_url = get_object_url(
                notification.action_object, notification, request)
            if action_object_url:
                struct['action_object_url'] = action_object_url
        if notification.data:
            struct['data'] = notification.data
        unread_list.append(struct)
        if request.GET.get('mark_as_read'):
            notification.mark_as_read()
    data = {
        'unread_count': request.user.notifications.unread().count(),
        'unread_list': unread_list
    }
    return JsonResponse(data)


@never_cache
def live_all_notification_list(request):
    ''' Return a json with a unread notification list '''
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {
            'all_count': 0,
            'all_list': []
        }
        return JsonResponse(data)

    all_list = get_notification_list(request)

    data = {
        'all_count': request.user.notifications.count(),
        'all_list': all_list
    }
    return JsonResponse(data)


def live_all_notification_count(request):
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {
            'all_count': 0
        }
    else:
        data = {
            'all_count': request.user.notifications.count(),
        }
    return JsonResponse(data)
