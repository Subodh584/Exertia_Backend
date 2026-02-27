from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Friendship, GameSession, User
from .serializers import (
    FriendshipSerializer,
    GameSessionSerializer,
    UserSerializer,
    UserStatsSerializer,
)


@api_view(["GET"])
def health_check(request):
    """Simple health check endpoint."""
    return Response({"status": "ok"})


# ── User ViewSet ─────────────────────────────────────
class UserViewSet(viewsets.ModelViewSet):
    """CRUD + custom actions for users."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """GET /api/users/{id}/stats/ – aggregate stats for a user."""
        user = self.get_object()
        sessions = user.game_sessions.all()
        agg = sessions.aggregate(
            total_minutes=Sum("duration_minutes"),
            total_calories=Sum("calories_burned"),
        )
        data = {
            "total_sessions": sessions.count(),
            "total_minutes": agg["total_minutes"] or 0,
            "total_calories": agg["total_calories"] or 0,
            "completed_sessions": sessions.filter(
                completion_status=GameSession.CompletionStatus.COMPLETED
            ).count(),
            "friend_count": Friendship.objects.filter(
                Q(requester=user) | Q(receiver=user),
                status=Friendship.Status.ACCEPTED,
            ).count(),
        }
        serializer = UserStatsSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """GET /api/users/{id}/sessions/ – list sessions for a user."""
        user = self.get_object()
        sessions = user.game_sessions.all()
        serializer = GameSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def friends(self, request, pk=None):
        """GET /api/users/{id}/friends/ – list accepted friends."""
        user = self.get_object()
        friendships = Friendship.objects.filter(
            Q(requester=user) | Q(receiver=user),
            status=Friendship.Status.ACCEPTED,
        )
        serializer = FriendshipSerializer(friendships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="go-online")
    def go_online(self, request, pk=None):
        """POST /api/users/{id}/go-online/ – mark user online."""
        user = self.get_object()
        user.is_online = True
        user.save(update_fields=["is_online"])
        return Response({"status": "online"})

    @action(detail=True, methods=["post"], url_path="go-offline")
    def go_offline(self, request, pk=None):
        """POST /api/users/{id}/go-offline/ – mark user offline & record last_seen."""
        from django.utils import timezone

        user = self.get_object()
        user.is_online = False
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])
        return Response({"status": "offline"})


# ── Game Session ViewSet ─────────────────────────────
class GameSessionViewSet(viewsets.ModelViewSet):
    """CRUD for game sessions."""

    queryset = GameSession.objects.select_related("user").all()
    serializer_class = GameSessionSerializer
    filterset_fields = ["user", "completion_status", "track_id"]

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """POST /api/sessions/{id}/complete/ – mark a session completed."""
        session = self.get_object()
        session.completion_status = GameSession.CompletionStatus.COMPLETED
        session.save(update_fields=["completion_status"])
        return Response(GameSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def abandon(self, request, pk=None):
        """POST /api/sessions/{id}/abandon/ – mark a session abandoned."""
        session = self.get_object()
        session.completion_status = GameSession.CompletionStatus.ABANDONED
        session.save(update_fields=["completion_status"])
        return Response(GameSessionSerializer(session).data)


# ── Friendship ViewSet ───────────────────────────────
class FriendshipViewSet(viewsets.ModelViewSet):
    """CRUD + accept / decline for friendships."""

    queryset = Friendship.objects.select_related("requester", "receiver").all()
    serializer_class = FriendshipSerializer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """POST /api/friendships/{id}/accept/"""
        friendship = self.get_object()
        if friendship.status != Friendship.Status.PENDING:
            return Response(
                {"error": "Only pending requests can be accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        friendship.status = Friendship.Status.ACCEPTED
        friendship.save(update_fields=["status"])
        return Response(FriendshipSerializer(friendship).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """POST /api/friendships/{id}/decline/"""
        friendship = self.get_object()
        if friendship.status != Friendship.Status.PENDING:
            return Response(
                {"error": "Only pending requests can be declined."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        friendship.status = Friendship.Status.DECLINED
        friendship.save(update_fields=["status"])
        return Response(FriendshipSerializer(friendship).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        """POST /api/friendships/{id}/block/"""
        friendship = self.get_object()
        friendship.status = Friendship.Status.BLOCKED
        friendship.save(update_fields=["status"])
        return Response(FriendshipSerializer(friendship).data)
