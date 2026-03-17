from rest_framework import serializers

from .models import Badge, DailyProgress, Friendship, GameSession, User, UserBadge


# ── User ──────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """
    Public user profile serializer.
    - password is write-only (accepted on create/update, never returned)
    - email is required on create; validated for uniqueness by the model
    """

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "display_name",
            "daily_target_distance",
            "daily_target_calories",
            "current_weight",
            "target_weight",
            "current_streak",
            "longest_streak",
            "last_streak_date",
            "is_online",
            "last_seen",
        ]
        read_only_fields = ["id", "current_streak", "longest_streak", "last_streak_date"]

    def create(self, validated_data):
        raw_password = validated_data.pop("password", None)
        user = User(**validated_data)
        if raw_password:
            user.set_password(raw_password)
        user.save()
        return user

    def update(self, instance, validated_data):
        raw_password = validated_data.pop("password", None)
        if raw_password:
            instance.set_password(raw_password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserStatsSerializer(serializers.Serializer):
    """Aggregated lifetime stats for a user."""
    total_sessions = serializers.IntegerField()
    total_distance = serializers.FloatField()
    total_calories = serializers.IntegerField()
    total_minutes = serializers.IntegerField()
    completed_sessions = serializers.IntegerField()
    personal_best_distance = serializers.FloatField()
    personal_best_calories = serializers.IntegerField()
    friend_count = serializers.IntegerField()


# ── Game Session ──────────────────────────────────────────────────────────────

class GameSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = GameSession
        fields = [
            "id",
            "user",
            "username",
            "track_id",
            "character_id",
            "distance_covered",
            "calories_burned",
            "duration_minutes",
            "average_speed",
            "total_jumps",
            "total_crouches",
            "completion_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ── Daily Progress ────────────────────────────────────────────────────────────

class DailyProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyProgress
        fields = [
            "id",
            "user",
            "date",
            "total_distance",
            "total_calories",
            "total_duration_mins",
            "target_met",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Badge ─────────────────────────────────────────────────────────────────────

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "badge_type",
            "target_value",
        ]
        read_only_fields = ["id"]


class UserBadgeSerializer(serializers.ModelSerializer):
    """Badge + user progress in a single response."""
    badge = BadgeSerializer(read_only=True)
    badge_id = serializers.PrimaryKeyRelatedField(
        queryset=Badge.objects.all(), source="badge", write_only=True
    )

    class Meta:
        model = UserBadge
        fields = [
            "id",
            "badge",
            "badge_id",
            "current_progress",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_progress",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        ]


# ── Friendship ────────────────────────────────────────────────────────────────

class FriendshipSerializer(serializers.ModelSerializer):
    requester_username = serializers.CharField(
        source="requester.username", read_only=True
    )
    receiver_username = serializers.CharField(
        source="receiver.username", read_only=True
    )

    class Meta:
        model = Friendship
        fields = [
            "id",
            "requester",
            "requester_username",
            "receiver",
            "receiver_username",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
