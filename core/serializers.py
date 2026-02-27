from rest_framework import serializers

from .models import Friendship, GameSession, User


# ── User ─────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "daily_target_mins",
            "daily_target_calories",
            "is_online",
            "last_seen",
        ]
        read_only_fields = ["id"]


class UserStatsSerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    total_minutes = serializers.IntegerField()
    total_calories = serializers.IntegerField()
    completed_sessions = serializers.IntegerField()
    friend_count = serializers.IntegerField()


# ── Game Session ─────────────────────────────────────
class GameSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = GameSession
        fields = [
            "id",
            "user",
            "username",
            "track_id",
            "duration_minutes",
            "calories_burned",
            "completion_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ── Friendship ───────────────────────────────────────
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
