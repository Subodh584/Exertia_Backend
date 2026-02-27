"""Management command to seed the database with dummy data."""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Friendship, GameSession, User

TRACKS = [
    "track_sprint_hill",
    "track_forest_run",
    "track_beach_jog",
    "track_mountain_climb",
    "track_city_marathon",
    "track_yoga_flow",
    "track_hiit_blast",
    "track_cycling_coast",
]

USERS_DATA = [
    {"username": "alex_runner", "display_name": "Alex Runner", "daily_target_mins": 45, "daily_target_calories": 500},
    {"username": "jordan_fit", "display_name": "Jordan Fit", "daily_target_mins": 30, "daily_target_calories": 350},
    {"username": "sam_cyclist", "display_name": "Sam Cyclist", "daily_target_mins": 60, "daily_target_calories": 600},
    {"username": "taylor_yoga", "display_name": "Taylor Yoga", "daily_target_mins": 40, "daily_target_calories": 250},
    {"username": "morgan_hiker", "display_name": "Morgan Hiker", "daily_target_mins": 90, "daily_target_calories": 800},
    {"username": "casey_swim", "display_name": "Casey Swimmer", "daily_target_mins": 35, "daily_target_calories": 400},
    {"username": "riley_box", "display_name": "Riley Boxer", "daily_target_mins": 50, "daily_target_calories": 550},
    {"username": "drew_lift", "display_name": "Drew Lifter", "daily_target_mins": 60, "daily_target_calories": 450},
]


class Command(BaseCommand):
    help = "Seed the database with dummy users, game sessions, and friendships."

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding database...")

        # ── Users ────────────────────────────────────
        users = []
        for data in USERS_DATA:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "display_name": data["display_name"],
                    "daily_target_mins": data["daily_target_mins"],
                    "daily_target_calories": data["daily_target_calories"],
                    "is_online": random.choice([True, False]),
                    "last_seen": timezone.now() - timedelta(minutes=random.randint(0, 1440)),
                },
            )
            users.append(user)
            tag = "Created" if created else "Exists"
            self.stdout.write(f"  [{tag}] User: {user.username}")

        # ── Game Sessions ────────────────────────────
        session_count = 0
        for user in users:
            num_sessions = random.randint(3, 8)
            for _ in range(num_sessions):
                duration = random.randint(5, 90)
                GameSession.objects.create(
                    user=user,
                    track_id=random.choice(TRACKS),
                    duration_minutes=duration,
                    calories_burned=int(duration * random.uniform(5.0, 12.0)),
                    completion_status=random.choice(
                        [
                            GameSession.CompletionStatus.COMPLETED,
                            GameSession.CompletionStatus.COMPLETED,
                            GameSession.CompletionStatus.COMPLETED,
                            GameSession.CompletionStatus.ABANDONED,
                            GameSession.CompletionStatus.IN_PROGRESS,
                        ]
                    ),
                    created_at=timezone.now() - timedelta(days=random.randint(0, 30)),
                )
                session_count += 1
        self.stdout.write(f"  Created {session_count} game sessions")

        # ── Friendships ──────────────────────────────
        friendship_count = 0
        pairs_seen = set()
        for _ in range(12):
            a, b = random.sample(users, 2)
            pair = tuple(sorted([str(a.id), str(b.id)]))
            if pair in pairs_seen:
                continue
            pairs_seen.add(pair)
            Friendship.objects.get_or_create(
                requester=a,
                receiver=b,
                defaults={
                    "status": random.choice(
                        [
                            Friendship.Status.ACCEPTED,
                            Friendship.Status.ACCEPTED,
                            Friendship.Status.PENDING,
                            Friendship.Status.DECLINED,
                        ]
                    ),
                },
            )
            friendship_count += 1
        self.stdout.write(f"  Created {friendship_count} friendships")

        self.stdout.write(self.style.SUCCESS("\n✅ Seeding complete!"))
