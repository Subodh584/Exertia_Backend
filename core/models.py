import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class TimestampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# ── User ──────────────────────────────────────────────────────────────────────

class User(models.Model):
    """
    Application user profile.

    Password is stored as a Django hashed string (PBKDF2 by default).
    Use set_password() to hash and check_password() to verify — never
    store or compare raw passwords directly.

    Daily targets:
      - daily_target_distance  : km the user wants to cover each day
      - daily_target_calories  : kcal the user wants to burn each day

    Streak fields are updated by the backend whenever a session is completed:
      - current_streak   : consecutive days the daily target was met
      - longest_streak   : all-time best streak
      - last_streak_date : the calendar date of the last qualifying session
                          (used to decide whether today extends or resets the streak)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)          # nullable so existing rows survive migration
    password = models.CharField(max_length=255, blank=True, default="")   # always hashed

    display_name = models.CharField(max_length=255, blank=True, default="")

    # ── Daily targets ────────────────────────────────────────────────────────
    daily_target_distance = models.FloatField(default=1.0)    # km
    daily_target_calories = models.IntegerField(default=300)  # kcal

    # ── Body metrics ─────────────────────────────────────────────────────────
    current_weight = models.FloatField(null=True, blank=True)  # kg
    target_weight = models.FloatField(null=True, blank=True)   # kg

    # ── Streak ───────────────────────────────────────────────────────────────
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_streak_date = models.DateField(null=True, blank=True)

    # ── Presence ─────────────────────────────────────────────────────────────
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self):
        return self.username

    # ── Password helpers ─────────────────────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        """Hash raw_password and store it. Call save() afterwards."""
        self.password = make_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """Return True if raw_password matches the stored hash."""
        return check_password(raw_password, self.password)


# ── Game Session ──────────────────────────────────────────────────────────────

class GameSession(models.Model):
    """
    A single exercise / game session.

    Primary metrics (shown everywhere):
      - distance_covered  : km covered during this session
      - calories_burned   : kcal burned

    Secondary metrics (shown in session detail only):
      - duration_minutes  : total time of the session
      - average_speed     : km/h  (distance / time, computed and stored at session end)

    Game-specific counters:
      - total_jumps, total_crouches

    Local references (IDs only — definitions live on the device):
      - track_id, character_id
    """

    class CompletionStatus(models.TextChoices):
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"
        IN_PROGRESS = "in_progress", "In Progress"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="game_sessions",
    )

    # ── Local references ─────────────────────────────────────────────────────
    track_id = models.CharField(max_length=255)
    character_id = models.CharField(max_length=255, blank=True, default="")

    # ── Primary metrics ──────────────────────────────────────────────────────
    distance_covered = models.FloatField(default=0.0)   # km
    calories_burned = models.IntegerField(default=0)    # kcal

    # ── Secondary metrics ────────────────────────────────────────────────────
    duration_minutes = models.IntegerField(default=0)
    average_speed = models.FloatField(null=True, blank=True)  # km/h

    # ── Game counters ────────────────────────────────────────────────────────
    total_jumps = models.IntegerField(default=0)
    total_crouches = models.IntegerField(default=0)

    # ── Status & timestamp ───────────────────────────────────────────────────
    completion_status = models.CharField(
        max_length=20,
        choices=CompletionStatus.choices,
        default=CompletionStatus.IN_PROGRESS,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "game_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.track_id} ({self.completion_status})"


# ── Daily Progress ────────────────────────────────────────────────────────────

class DailyProgress(models.Model):
    """
    One row per (user, calendar-date).

    Aggregates all completed sessions for that day and flags whether the
    user hit both daily targets (distance AND calories).  This is the
    source-of-truth for the streak calendar shown in the Statistics screen.

    The backend updates this record whenever a session is marked completed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="daily_progress",
    )
    date = models.DateField()

    # ── Aggregated totals for the day ─────────────────────────────────────────
    total_distance = models.FloatField(default=0.0)    # km
    total_calories = models.IntegerField(default=0)    # kcal
    total_duration_mins = models.IntegerField(default=0)

    # ── Target check ─────────────────────────────────────────────────────────
    # True when BOTH daily_target_distance AND daily_target_calories are met
    target_met = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "daily_progress"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_daily_progress",
            ),
        ]

    def __str__(self):
        mark = "✓" if self.target_met else "✗"
        return f"{self.user.username} – {self.date} {mark}"


# ── Badge ─────────────────────────────────────────────────────────────────────

class Badge(models.Model):
    """
    Definition of an achievement badge.

    badge_type drives which stat is checked against target_value:
      calories  → total lifetime kcal burned
      distance  → total lifetime km covered
      sessions  → total completed sessions
      streak    → longest streak reached
      jumps     → total lifetime jumps
      crouches  → total lifetime crouches

    icon is a string identifier that maps to an asset bundled in the app.
    The actual image lives locally; we just store the key here.
    """

    class BadgeType(models.TextChoices):
        CALORIES = "calories", "Calories Burned"
        DISTANCE = "distance", "Distance Covered"
        SESSIONS = "sessions", "Sessions Completed"
        STREAK = "streak", "Streak"
        JUMPS = "jumps", "Total Jumps"
        CROUCHES = "crouches", "Total Crouches"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=255)          # asset key, e.g. "reactor_core"
    badge_type = models.CharField(
        max_length=50,
        choices=BadgeType.choices,
    )
    target_value = models.FloatField()               # e.g. 500 (calories), 10 (sessions)

    class Meta:
        db_table = "badges"
        ordering = ["badge_type", "target_value"]

    def __str__(self):
        return f"{self.name} ({self.badge_type} ≥ {self.target_value})"


# ── User Badge ────────────────────────────────────────────────────────────────

class UserBadge(models.Model):
    """
    Tracks each user's progress toward every badge.

    One row per (user, badge) pair — created automatically when a user is
    registered (or lazily on first session completion).

    current_progress mirrors the relevant lifetime stat so the iOS app
    can show the progress bar without a separate aggregation call.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="user_badges",
    )

    current_progress = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_badges"
        ordering = ["-is_completed", "badge__badge_type", "badge__target_value"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "badge"],
                name="unique_user_badge",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.username} – {self.badge.name} "
            f"({self.current_progress}/{self.badge.target_value})"
        )


# ── Friendship ────────────────────────────────────────────────────────────────

class Friendship(models.Model):
    """Friend request / relationship between two users."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_requests",
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "friendships"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "receiver"],
                name="unique_friendship",
            ),
        ]

    def __str__(self):
        return f"{self.requester.username} → {self.receiver.username} ({self.status})"
