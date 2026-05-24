import zoneinfo

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from events.signin_cookie import (
    EVENT_SIGNIN_COOKIE_TYPE_USER,
    delete_event_signin_cookie,
    set_event_signin_cookie,
)
from pbaabp.forms import NewsletterSignupForm


EVENT_SIGNIN_LOGIN_USER_ATTR = "_event_signin_login_user"


@receiver(user_logged_in, dispatch_uid="set_event_signin_cookie_on_login")
def set_event_signin_cookie_on_login(sender, request, user, **kwargs):
    setattr(request, EVENT_SIGNIN_LOGIN_USER_ATTR, user)


class ClearEventSignInCookieOnLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        login_user = getattr(request, EVENT_SIGNIN_LOGIN_USER_ATTR, None)
        if login_user is not None:
            set_event_signin_cookie(
                response,
                {"type": EVENT_SIGNIN_COOKIE_TYPE_USER, "id": login_user.id},
            )

        try:
            logout_path = reverse("account_logout")
        except NoReverseMatch:
            return response

        if request.path == logout_path:
            delete_event_signin_cookie(response)
        return response


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = settings.TIME_ZONE
        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()
        return self.get_response(request)


class FooterNewsletterSignupFormMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.newsletter_form = NewsletterSignupForm(form_name="footer")
        request.google_recaptcha_site_key = settings.RECAPTCHA_PUBLIC_KEY
        return self.get_response(request)
