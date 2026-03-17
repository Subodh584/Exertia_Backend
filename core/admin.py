from django.contrib import admin

from .models import Badge, DailyProgress, Friendship, GameSession, User, UserBadge


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "username", "display_name", "email",
        "current_streak", "longest_streak",
        "daily_target_distance", "daily_target_calories",
        "current_weight", "target_weight",
        "is_online", "last_seen",
    ]
    search_fields = ["username", "display_name", "email"]
    list_filter = ["is_online"]
    readonly_fields = ["current_streak", "longest_streak", "last_streak_date"]


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "track_id", "character_id",
        "distance_covered", "calories_burned",
        "duration_minutes", "average_speed",
        "total_jumps", "total_crouches",
        "completion_status", "created_at",
    ]
    list_filter = ["completion_status", "track_id", "character_id"]
    search_fields = ["user__username", "track_id", "character_id"]


@admin.register(DailyProgress)
class DailyProgressAdmin(admin.ModelAdmin):
    list_display = [
        "user", "date",
        "total_distance", "total_calories", "total_duration_mins",
        "target_met",
    ]
    list_filter = ["target_met"]
    search_fields = ["user__username"]
    date_hierarchy = "date"


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ["name", "badge_type", "target_value", "icon"]
    list_filter = ["badge_type"]
    search_fields = ["name", "description"]


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = [
        "user", "badge", "current_progress",
        "is_completed", "completed_at",
    ]
    list_filter = ["is_completed", "badge__badge_type"]
    search_fields = ["user__username", "badge__name"]
    readonly_fields = ["current_progress", "is_completed", "completed_at"]


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ["requester", "receiver", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["requester__username", "receiver__username"]
