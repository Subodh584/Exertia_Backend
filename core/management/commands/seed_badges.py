"""Management command to seed badge definitions (idempotent — safe to run multiple times)."""

from django.core.management.base import BaseCommand

from core.models import Badge

BADGES = [
    # Sessions
    {"name": "First Steps",       "description": "Complete your first session",      "icon": "badge_first_steps",    "badge_type": "sessions",  "target_value": 1},
    {"name": "On a Roll",         "description": "Complete 5 sessions",              "icon": "badge_on_a_roll",      "badge_type": "sessions",  "target_value": 5},
    {"name": "Session Veteran",   "description": "Complete 10 sessions",             "icon": "badge_veteran",        "badge_type": "sessions",  "target_value": 10},
    # Distance
    {"name": "First Mile",        "description": "Cover 1 km total",                 "icon": "badge_first_mile",     "badge_type": "distance",  "target_value": 1.0},
    {"name": "Distance Walker",   "description": "Cover 10 km total",                "icon": "badge_walker",         "badge_type": "distance",  "target_value": 10.0},
    {"name": "Distance Runner",   "description": "Cover 50 km total",                "icon": "badge_runner",         "badge_type": "distance",  "target_value": 50.0},
    # Calories
    {"name": "Calorie Burner",    "description": "Burn 500 calories total",          "icon": "badge_calorie_burner", "badge_type": "calories",  "target_value": 500},
    {"name": "Calorie Crusher",   "description": "Burn 2000 calories total",         "icon": "badge_crusher",        "badge_type": "calories",  "target_value": 2000},
    # Jumps / Crouches
    {"name": "Jump King",         "description": "Make 100 total jumps",             "icon": "badge_jump_king",      "badge_type": "jumps",     "target_value": 100},
    {"name": "Crouch Master",     "description": "Make 50 total crouches",           "icon": "badge_crouch_master",  "badge_type": "crouches",  "target_value": 50},
    # Streak
    {"name": "Hot Streak",        "description": "Reach a 3-day streak",             "icon": "badge_hot_streak",     "badge_type": "streak",    "target_value": 3},
    {"name": "Week Warrior",      "description": "Reach a 7-day streak",             "icon": "badge_week_warrior",   "badge_type": "streak",    "target_value": 7},
]


class Command(BaseCommand):
    help = "Seed badge definitions (idempotent)."

    def handle(self, *args, **options):
        created_count = 0
        for data in BADGES:
            _, created = Badge.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(f"  [Created] Badge: {data['name']}")
            else:
                self.stdout.write(f"  [Exists]  Badge: {data['name']}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ {created_count} badges created, {len(BADGES) - created_count} already existed."))
