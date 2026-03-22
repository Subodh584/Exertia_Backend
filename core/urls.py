from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"sessions", views.GameSessionViewSet)
router.register(r"friendships", views.FriendshipViewSet)
router.register(r"badges", views.BadgeViewSet)

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("auth/login/",   views.LoginView.as_view(),  name="auth-login"),
    path("auth/me/",              views.me,              name="auth-me"),
    path("auth/change-password/", views.change_password, name="change-password"),
    path("auth/delete-account/",  views.delete_account,  name="delete-account"),
    path("auth/refresh/", TokenRefreshView.as_view(),  name="auth-refresh"),
    path("auth/logout/",  views.LogoutView.as_view(),  name="auth-logout"),
    path("", include(router.urls)),
]
