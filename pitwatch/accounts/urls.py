from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AdminLoginView,
    AdminLogoutView,
    AdminMeView,
    AdminTokenRefreshView,
    ProfileView,
    SignupView,
    UserRefreshTokenView,
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", UserRefreshTokenView.as_view(), name="token_refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin/token/refresh/", AdminTokenRefreshView.as_view(), name="admin-token-refresh"),
    path("admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("admin/me/", AdminMeView.as_view(), name="admin-me"),
]