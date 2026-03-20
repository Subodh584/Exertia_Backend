"""
Custom JWT authentication backend for Exertia.

We use our own core.models.User (not Django's auth.User), so we need two things:

1. ExertiaJWTAuthentication — subclasses JWTAuthentication and overrides get_user()
   to look up core.models.User instead of auth.User.

2. ExertiaRefreshToken — subclasses RefreshToken and overrides blacklist() so it
   doesn't try to resolve our UUID user_id against Django's integer-keyed auth.User.
   The OutstandingToken.user field is nullable, so we simply leave it None.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch


class ExertiaJWTAuthentication(JWTAuthentication):
    """JWT authentication that resolves tokens to core.models.User."""

    def get_user(self, validated_token):
        from .models import User

        try:
            user_id = validated_token["user_id"]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise InvalidToken("No user matching this token was found")


class ExertiaRefreshToken(RefreshToken):
    """
    Refresh token that skips the Django auth.User lookup when blacklisting.

    simplejwt's default blacklist() calls get_user_model() (→ auth.User) and
    tries to filter by our UUID, which fails on integer-keyed auth.User.
    We override to create the OutstandingToken with user=None instead.
    """

    def blacklist(self):
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        jti = self.payload["jti"]
        exp = self.payload["exp"]

        outstanding_token, _ = OutstandingToken.objects.get_or_create(
            jti=jti,
            defaults={
                "user": None,
                "token": str(self),
                "expires_at": datetime_from_epoch(exp),
            },
        )
        return BlacklistedToken.objects.get_or_create(token=outstanding_token)
