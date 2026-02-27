from django.contrib import admin

from .models import Friendship, GameSession, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "display_name", "is_online", "last_seen"]
    search_fields = ["username", "display_name"]
    list_filter = ["is_online"]


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "track_id", "duration_minutes", "calories_burned", "completion_status", "created_at"]
    list_filter = ["completion_status"]
    search_fields = ["user__username", "track_id"]


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ["requester", "receiver", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["requester__username", "receiver__username"]
