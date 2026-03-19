from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"sessions", views.GameSessionViewSet)
router.register(r"friendships", views.FriendshipViewSet)
router.register(r"badges", views.BadgeViewSet)

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("debug-users/", views.debug_users, name="debug-users"),
    path("debug-delete-user/<str:username>/", views.debug_delete_user, name="debug-delete-user"),
    path("", include(router.urls)),
]
