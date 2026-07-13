from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets, exceptions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import SignupSerializer, LoginOrgSerializer, LoginBranchSerializer, UserManageSerializer

User = get_user_model()

def set_auth_cookies(response, access_token, refresh_token):
    """
    Configures and writes HttpOnly, Secure, and SameSite=None (in prod) or Lax (in dev) cookies
    for both access and refresh JWT tokens.
    """
    samesite_val = 'None' if not settings.DEBUG else 'Lax'
    secure_val = True if not settings.DEBUG else False

    # Access token cookie (expires in 15 minutes)
    response.set_cookie(
        key='access_token',
        value=str(access_token),
        max_age=15 * 60,
        httponly=True,
        secure=secure_val,
        samesite=samesite_val,
        path='/'
    )
    # Refresh token cookie (expires in 7 days)
    response.set_cookie(
        key='refresh_token',
        value=str(refresh_token),
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=secure_val,
        samesite=samesite_val,
        path='/'
    )


def delete_auth_cookies(response):
    """
    Deletes the authentication cookies with matching secure and samesite parameters.
    """
    samesite_val = 'None' if not settings.DEBUG else 'Lax'
    secure_val = True if not settings.DEBUG else False

    response.delete_cookie(
        key='access_token',
        path='/',
        secure=secure_val,
        samesite=samesite_val
    )
    response.delete_cookie(
        key='refresh_token',
        path='/',
        secure=secure_val,
        samesite=samesite_val
    )


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            response = Response({
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "org_id": user.organization.org_id,
                    "org_name": user.organization.name,
                },
                "csrf_token": get_token(request)
            }, status=status.HTTP_201_CREATED)
            
            set_auth_cookies(response, refresh.access_token, refresh)
            return response
            
        return Response(
            {"error": serializer.errors, "code": "VALIDATION_ERROR", "status": 400},
            status=status.HTTP_400_BAD_REQUEST
        )


class LoginOrgView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginOrgSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "code": "VALIDATION_ERROR", "status": 400},
                status=status.HTTP_400_BAD_REQUEST
            )

        org_id = serializer.validated_data['org_id']
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        role = serializer.validated_data['role']

        user = authenticate(request, username=username, password=password, org_id=org_id, role=role)
        
        # Defense-in-depth: Strict verification of role and organization association
        if user is not None:
            if user.role != role or not user.organization or user.organization.org_id != org_id.lower().strip():
                user = None

        if user is None:
            return Response(
                {"error": "Invalid organization ID, username, password, or role classification.", "code": "INVALID_CREDENTIALS", "status": 401},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"error": "User account has been disabled.", "code": "USER_DISABLED", "status": 403},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        response = Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "org_id": user.organization.org_id,
                "org_name": user.organization.name,
            },
            "csrf_token": get_token(request)
        }, status=status.HTTP_200_OK)

        set_auth_cookies(response, refresh.access_token, refresh)
        return response


class LoginBranchView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginBranchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "code": "VALIDATION_ERROR", "status": 400},
                status=status.HTTP_400_BAD_REQUEST
            )

        org_id = serializer.validated_data['org_id']
        branch_slug = serializer.validated_data['branch_slug']
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        role = serializer.validated_data['role']

        user = authenticate(
            request, 
            username=username, 
            password=password, 
            org_id=org_id, 
            branch_slug=branch_slug, 
            role=role
        )
        
        # Defense-in-depth: Strict verification of role, organization, and branch associations
        if user is not None:
            if (user.role != role or 
                not user.organization or user.organization.org_id != org_id.lower().strip() or
                not user.branch or user.branch.slug != branch_slug.strip()):
                user = None
        
        if user is None:
            return Response(
                {"error": "Invalid credentials or branch association.", "code": "INVALID_CREDENTIALS", "status": 401},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"error": "User account has been disabled.", "code": "USER_DISABLED", "status": 403},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        response = Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "org_id": user.organization.org_id,
                "org_name": user.organization.name,
                "branch_slug": user.branch.slug,
                "branch_name": user.branch.name,
            },
            "csrf_token": get_token(request)
        }, status=status.HTTP_200_OK)

        set_auth_cookies(response, refresh.access_token, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                # Blacklist the refresh token
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        delete_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {"error": "Refresh token is missing.", "code": "REFRESH_TOKEN_MISSING", "status": 401},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)

            if not user.is_active:
                raise TokenError("User is inactive.")

            # Generate new pair (forces rotation)
            new_refresh = RefreshToken.for_user(user)
            
            response = Response({
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "org_id": user.organization.org_id if user.organization else None,
                    "org_name": user.organization.name if user.organization else None,
                    "branch_slug": user.branch.slug if user.branch else None,
                    "branch_name": user.branch.name if user.branch else None,
                },
                "csrf_token": get_token(request)
            }, status=status.HTTP_200_OK)
            
            set_auth_cookies(response, new_refresh.access_token, new_refresh)
            
            # Blacklist old refresh token
            try:
                refresh.blacklist()
            except AttributeError:
                pass
                
            return response
            
        except (TokenError, User.DoesNotExist):
            response = Response(
                {"error": "Refresh token is invalid or expired.", "code": "INVALID_REFRESH_TOKEN", "status": 401},
                status=status.HTTP_401_UNAUTHORIZED
            )
            delete_auth_cookies(response)
            return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "org_id": user.organization.org_id if user.organization else None,
            "org_name": user.organization.name if user.organization else None,
            "branch_slug": user.branch.slug if user.branch else None,
            "branch_name": user.branch.name if user.branch else None,
            "csrf_token": get_token(request),
        }
        return Response(data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserManageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Only allow HQ roles or Branch Admin to access user lists
        if user.role not in [user.Role.ORG_ADMIN, user.Role.ORG_USER, user.Role.BRANCH_ADMIN]:
            return User.objects.none()

        if user.role in [user.Role.ORG_ADMIN, user.Role.ORG_USER]:
            # HQ users see all users in organization
            return User.objects.filter(organization=user.organization).order_by('username')
        else:
            # Branch admins see users of their specific branch
            return User.objects.filter(organization=user.organization, branch=user.branch).order_by('username')

    def check_permissions(self, request):
        super().check_permissions(request)
        user = request.user
        if user.role not in [user.Role.ORG_ADMIN, user.Role.ORG_USER, user.Role.BRANCH_ADMIN]:
            self.permission_denied(
                request, message="You do not have permission to access user management."
            )

    def perform_update(self, serializer):
        # Prevent users from self-lockouts (changing their own role or active status)
        target_user = self.get_object()
        if target_user == self.request.user:
            if 'role' in serializer.validated_data and serializer.validated_data['role'] != target_user.role:
                raise exceptions.ValidationError({"role": "You cannot change your own role."})
            if 'is_active' in serializer.validated_data and not serializer.validated_data['is_active']:
                raise exceptions.ValidationError({"is_active": "You cannot disable your own user account."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise exceptions.ValidationError("You cannot delete your own user account.")
        # Soft delete by disabling active status
        instance.is_active = False
        instance.save()

