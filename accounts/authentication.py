from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Retrieve the access token from cookies
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
        except Exception:
            # If the cookie is expired, invalid, or belongs to a deleted user,
            # treat the request as anonymous rather than throwing a hard 401.
            # Protected views will still block anonymous requests at the permission layer.
            return None
        
        # Enforce CSRF verification for cookie-based authentication to prevent CSRF attacks
        self.enforce_csrf(request)
        
        return user, validated_token

    def enforce_csrf(self, request):
        """
        Enforces CSRF validation manually for cookie-based authentication.
        """
        # Skip CSRF check for authentication endpoints (login, signup, logout, refresh, me)
        if request.path.startswith('/api/auth/'):
            return

        check = CSRFCheck(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')

