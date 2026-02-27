import uuid

from django.db import models


class TimestampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class User(models.Model):
    """Application user profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    daily_target_mins = models.IntegerField(default=30)
    daily_target_calories = models.IntegerField(default=300)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self):
        return self.username


class GameSession(models.Model):
    """A single exercise / game session."""

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
    track_id = models.CharField(max_length=255)
    duration_minutes = models.IntegerField(default=0)
    calories_burned = models.IntegerField(default=0)
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
