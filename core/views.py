from django.db.models import Max, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from .authentication import ExertiaRefreshToken

from .models import Badge, DailyProgress, Friendship, GameSession, User, UserBadge
from .serializers import (
    BadgeSerializer,
    DailyProgressSerializer,
    FriendshipSerializer,
    GameSessionSerializer,
    UserBadgeSerializer,
    UserSerializer,
    UserStatsSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check endpoint."""
    return Response({"status": "ok"})


# ── Auth Views ─────────────────────────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/auth/login/  — public, no token required.
    Body: { "username": "...", "password": "..." }
    Returns: { "access": "...", "refresh": "...", "user": {...} }

    Each call produces a unique token pair — two devices logging in as the
    same user get separate refresh tokens and can be invalidated independently.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"error": "username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.verify_password(password):
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Build a token pair and embed user_id as the lookup claim
        refresh = ExertiaRefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["username"] = user.username

        # Mark user online
        user.is_online = True
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/  — public, only needs the refresh token in body.
    Body: { "refresh": "..." }

    Blacklists the refresh token so it (and any access tokens derived from it)
    can no longer be used.  The device must log in again to get a fresh pair.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh", "")

        if not refresh_token:
            return Response(
                {"error": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = ExertiaRefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Mark user offline if we can identify them from the token
        try:
            user_id = token.payload.get("user_id")
            if user_id:
                user = User.objects.get(id=user_id)
                user.is_online = False
                user.last_seen = timezone.now()
                user.save(update_fields=["is_online", "last_seen"])
        except User.DoesNotExist:
            pass

        return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)



# ── User ViewSet ───────────────────────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """CRUD + custom actions for users."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        # Registration is public — everything else requires a valid Bearer token
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    # ── Stats ────────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """
        GET /api/users/{id}/stats/
        Returns lifetime aggregated stats for the user.
        Primary metric is distance; time is secondary.
        """
        user = self.get_object()
        sessions = user.game_sessions.filter(
            completion_status=GameSession.CompletionStatus.COMPLETED
        )

        agg = sessions.aggregate(
            total_distance=Sum("distance_covered"),
            total_calories=Sum("calories_burned"),
            total_minutes=Sum("duration_minutes"),
            personal_best_distance=Max("distance_covered"),
            personal_best_calories=Max("calories_burned"),
        )

        data = {
            "total_sessions": user.game_sessions.count(),
            "completed_sessions": sessions.count(),
            "total_distance": agg["total_distance"] or 0.0,
            "total_calories": agg["total_calories"] or 0,
            "total_minutes": agg["total_minutes"] or 0,
            "personal_best_distance": agg["personal_best_distance"] or 0.0,
            "personal_best_calories": agg["personal_best_calories"] or 0,
            "friend_count": Friendship.objects.filter(
                Q(requester=user) | Q(receiver=user),
                status=Friendship.Status.ACCEPTED,
            ).count(),
        }
        return Response(UserStatsSerializer(data).data)

    # ── Sessions ─────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """GET /api/users/{id}/sessions/ – list all sessions for a user."""
        user = self.get_object()
        sessions = user.game_sessions.all()
        serializer = GameSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    # ── Friends ──────────────────────────────────────────────────────────────

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

    # ── Badges ───────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def badges(self, request, pk=None):
        """GET /api/users/{id}/badges/ – list all badge progress for a user."""
        user = self.get_object()
        user_badges = UserBadge.objects.filter(user=user).select_related("badge")
        serializer = UserBadgeSerializer(user_badges, many=True)
        return Response(serializer.data)

    # ── Streak calendar ──────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="streak-calendar")
    def streak_calendar(self, request, pk=None):
        """
        GET /api/users/{id}/streak-calendar/
        Returns daily progress records (up to last 30 days by default).
        The iOS app uses this to render the weekly streak calendar widget.
        """
        user = self.get_object()
        days = int(request.query_params.get("days", 30))
        records = DailyProgress.objects.filter(user=user).order_by("-date")[:days]
        serializer = DailyProgressSerializer(records, many=True)
        return Response(serializer.data)

    # ── Presence ─────────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="go-online")
    def go_online(self, request, pk=None):
        """POST /api/users/{id}/go-online/"""
        user = self.get_object()
        user.is_online = True
        user.save(update_fields=["is_online"])
        return Response({"status": "online"})

    @action(detail=True, methods=["post"], url_path="go-offline")
    def go_offline(self, request, pk=None):
        """POST /api/users/{id}/go-offline/"""
        user = self.get_object()
        user.is_online = False
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])
        return Response({"status": "offline"})


# ── Game Session ViewSet ───────────────────────────────────────────────────────

class GameSessionViewSet(viewsets.ModelViewSet):
    """CRUD for game sessions."""

    queryset = GameSession.objects.select_related("user").all()
    serializer_class = GameSessionSerializer
    filterset_fields = ["user", "completion_status", "track_id", "character_id"]

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        POST /api/sessions/{id}/complete/
        Marks a session completed and triggers streak + badge updates.
        """
        session = self.get_object()
        session.completion_status = GameSession.CompletionStatus.COMPLETED
        session.save(update_fields=["completion_status"])

        # Update daily progress & streak
        _update_daily_progress(session)
        _update_streak(session.user)
        _update_badge_progress(session.user)

        return Response(GameSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def abandon(self, request, pk=None):
        """POST /api/sessions/{id}/abandon/"""
        session = self.get_object()
        session.completion_status = GameSession.CompletionStatus.ABANDONED
        session.save(update_fields=["completion_status"])
        return Response(GameSessionSerializer(session).data)


# ── Badge ViewSet ──────────────────────────────────────────────────────────────

class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of all badge definitions.
    Badges are managed via the Django admin — the app only reads them.
    """

    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer


# ── Friendship ViewSet ─────────────────────────────────────────────────────────

class FriendshipViewSet(viewsets.ModelViewSet):
    """CRUD + accept / decline / block for friendships."""

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


# ── Internal helpers (not exposed as endpoints) ────────────────────────────────

def _update_daily_progress(session: GameSession) -> None:
    """
    Upsert the DailyProgress row for the session's calendar date.
    Re-aggregates all completed sessions for that day so the numbers
    are always accurate even if sessions are edited retroactively.
    """
    from django.db.models import Sum as _Sum

    user = session.user
    date = session.created_at.date()

    day_sessions = GameSession.objects.filter(
        user=user,
        created_at__date=date,
        completion_status=GameSession.CompletionStatus.COMPLETED,
    ).aggregate(
        total_distance=_Sum("distance_covered"),
        total_calories=_Sum("calories_burned"),
        total_duration_mins=_Sum("duration_minutes"),
    )

    total_distance = day_sessions["total_distance"] or 0.0
    total_calories = day_sessions["total_calories"] or 0
    total_duration_mins = day_sessions["total_duration_mins"] or 0

    target_met = (
        total_distance >= user.daily_target_distance
        and total_calories >= user.daily_target_calories
    )

    DailyProgress.objects.update_or_create(
        user=user,
        date=date,
        defaults={
            "total_distance": total_distance,
            "total_calories": total_calories,
            "total_duration_mins": total_duration_mins,
            "target_met": target_met,
        },
    )


def _update_streak(user: User) -> None:
    """
    Recalculate current_streak and longest_streak for the user.

    A streak increments when today's (or yesterday's) DailyProgress row
    has target_met=True and is consecutive with the previous qualifying day.
    """
    from datetime import date, timedelta

    today = date.today()
    records = (
        DailyProgress.objects.filter(user=user, target_met=True)
        .order_by("-date")
        .values_list("date", flat=True)
    )

    if not records:
        user.current_streak = 0
        user.save(update_fields=["current_streak", "longest_streak"])
        return

    streak = 1
    longest = user.longest_streak
    prev_date = records[0]

    # Streak is still live only if the most recent qualifying day is today or yesterday
    if prev_date < today - timedelta(days=1):
        user.current_streak = 0
        user.longest_streak = max(longest, 0)
        user.save(update_fields=["current_streak", "longest_streak"])
        return

    for record_date in list(records)[1:]:
        if prev_date - record_date == timedelta(days=1):
            streak += 1
            prev_date = record_date
        else:
            break

    longest = max(longest, streak)
    user.current_streak = streak
    user.longest_streak = longest
    user.last_streak_date = records[0]
    user.save(update_fields=["current_streak", "longest_streak", "last_streak_date"])


def _update_badge_progress(user: User) -> None:
    """
    Recompute progress for every badge the user has not yet completed.
    Creates UserBadge rows for new badges if they don't exist yet.
    """
    from django.db.models import Sum as _Sum
    from django.utils import timezone as _tz

    all_badges = Badge.objects.all()
    if not all_badges.exists():
        return

    # Aggregate lifetime stats once
    agg = GameSession.objects.filter(
        user=user,
        completion_status=GameSession.CompletionStatus.COMPLETED,
    ).aggregate(
        total_calories=_Sum("calories_burned"),
        total_distance=_Sum("distance_covered"),
        total_jumps=_Sum("total_jumps"),
        total_crouches=_Sum("total_crouches"),
    )
    completed_count = GameSession.objects.filter(
        user=user,
        completion_status=GameSession.CompletionStatus.COMPLETED,
    ).count()

    stat_map = {
        Badge.BadgeType.CALORIES: agg["total_calories"] or 0,
        Badge.BadgeType.DISTANCE: agg["total_distance"] or 0.0,
        Badge.BadgeType.SESSIONS: completed_count,
        Badge.BadgeType.STREAK: user.longest_streak,
        Badge.BadgeType.JUMPS: agg["total_jumps"] or 0,
        Badge.BadgeType.CROUCHES: agg["total_crouches"] or 0,
    }

    for badge in all_badges:
        progress = stat_map.get(badge.badge_type, 0)
        completed = progress >= badge.target_value

        user_badge, _ = UserBadge.objects.get_or_create(
            user=user,
            badge=badge,
            defaults={"current_progress": progress, "is_completed": completed},
        )

        if not user_badge.is_completed:
            user_badge.current_progress = progress
            if completed:
                user_badge.is_completed = True
                user_badge.completed_at = _tz.now()
            user_badge.save(update_fields=["current_progress", "is_completed", "completed_at", "updated_at"])
