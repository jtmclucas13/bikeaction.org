import zoneinfo

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from events.signin_cookie import delete_event_signin_cookie
from pbaabp.forms import NewsletterSignupForm


class ClearEventSignInCookieOnLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
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
