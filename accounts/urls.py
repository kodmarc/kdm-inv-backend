from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SignupView, 
    LoginOrgView, 
    LoginBranchView, 
    LogoutView, 
    TokenRefreshView, 
    MeView,
    UserViewSet
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user_management')

urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login-org/', LoginOrgView.as_view(), name='login_org'),
    path('auth/login-branch/', LoginBranchView.as_view(), name='login_branch'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
