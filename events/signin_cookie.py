import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


EVENT_SIGNIN_COOKIE_NAME = "pba_event_signin"
EVENT_SIGNIN_COOKIE_MAX_AGE = 10 * 365 * 24 * 60 * 60
EVENT_SIGNIN_COOKIE_TYPE_USER = "user"
EVENT_SIGNIN_COOKIE_TYPE_SIGNIN = "signin"


def _fernet_keys():
    secret_keys = [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]
    return [
        base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
        for secret_key in secret_keys
    ]


def encrypt_event_signin_payload(payload):
    return (
        Fernet(_fernet_keys()[0])
        .encrypt(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
    )


def decrypt_event_signin_payload(token):
    if not token:
        return None

    for key in _fernet_keys():
        try:
            payload = Fernet(key).decrypt(token.encode()).decode()
            return json.loads(payload)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError, TypeError):
            continue
    return None


def set_event_signin_cookie(response, payload):
    response.set_cookie(
        EVENT_SIGNIN_COOKIE_NAME,
        encrypt_event_signin_payload(payload),
        max_age=EVENT_SIGNIN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )


def delete_event_signin_cookie(response):
    response.delete_cookie(EVENT_SIGNIN_COOKIE_NAME, samesite="Lax")
