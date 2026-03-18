# Exertia Backend — Complete API & Database Guide

> **Branch:** `feat/schema-v2-distance-streaks-badges`
> **Hosted on:** Render (PostgreSQL + Django/Gunicorn)
> **Last updated:** 2026-03-18

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Database Schema](#2-database-schema)
   - [User](#21-user)
   - [GameSession](#22-gamesession)
   - [DailyProgress](#23-dailyprogress)
   - [Badge](#24-badge)
   - [UserBadge](#25-userbadge)
   - [Friendship](#26-friendship)
3. [How Core Logic Works](#3-how-core-logic-works)
   - [Password Hashing](#31-password-hashing)
   - [Streak Calculation](#32-streak-calculation)
   - [Daily Progress Aggregation](#33-daily-progress-aggregation)
   - [Badge Progress Updates](#34-badge-progress-updates)
4. [API Reference](#4-api-reference)
   - [Health Check](#40-health-check)
   - [Users](#41-users)
   - [Game Sessions](#42-game-sessions)
   - [Badges](#43-badges)
   - [Friendships](#44-friendships)
5. [What Lives Locally (On-Device)](#5-what-lives-locally-on-device)
6. [Schema Diagram](#6-schema-diagram)

---

## 1. Project Overview

Exertia is a fitness video game for iOS. The phone's sensors detect physical movement (running, jumping, crouching) and translate them into in-game actions for a character. The backend is a pure data layer — it stores user profiles, session results, progress and achievements. It does **not** run the game, handle real-time events, or store character/track assets.

**Primary metric:** Distance covered (km)
**Secondary metric:** Calories burned (kcal)
**Time** is recorded per session (duration + average speed) but is not the main target or streak driver.

The app can run **offline** during a session. The backend is called:
- On app launch / profile load
- At the end of a session (to save results)
- When viewing Statistics or Profile screens

---

## 2. Database Schema

### 2.1 `User`

**Table:** `users`
**Purpose:** Stores the player's account details, daily targets, body metrics, streak counters, and presence state.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. Exposed to the user as their short ID (e.g. `877C82B0`). |
| `username` | VARCHAR(150) | No | — | Unique handle. Used for the `@Demo` display. |
| `email` | VARCHAR(254) | Yes | — | Unique email address. Required for account creation going forward. Nullable so existing rows survive migration. |
| `password` | VARCHAR(255) | No | `""` | **Always a Django PBKDF2 hash.** Never stored or returned as plaintext. |
| `display_name` | VARCHAR(255) | No | `""` | Full name shown on profile (e.g. "Ekansh"). |
| `daily_target_distance` | FLOAT | No | `1.0` | km the user wants to run per day (drives streak + progress bar). |
| `daily_target_calories` | INTEGER | No | `300` | kcal the user wants to burn per day (drives streak + progress bar). |
| `current_weight` | FLOAT | Yes | `null` | kg — used for the Weight Goal Progress bar on the Statistics screen. |
| `target_weight` | FLOAT | Yes | `null` | kg — the user's goal weight. |
| `current_streak` | INTEGER | No | `0` | Consecutive days both daily targets were met. Auto-updated by the backend on session completion. |
| `longest_streak` | INTEGER | No | `0` | All-time best streak. Never decreases. |
| `last_streak_date` | DATE | Yes | `null` | Calendar date of the last day a target-meeting session was completed. Used internally to determine if the streak is still live. |
| `is_online` | BOOLEAN | No | `false` | Whether the user is currently in an active app session. |
| `last_seen` | DATETIME | Yes | `null` | Timestamp when the user last went offline. |

**Notes:**
- `current_streak`, `longest_streak`, and `last_streak_date` are **read-only** from the API. The backend calculates them automatically — the iOS app should never send these.
- `password` is **write-only** — it is accepted by `POST /api/users/` and `PATCH /api/users/{id}/` but is **never returned** in any response.

---

### 2.2 `GameSession`

**Table:** `game_sessions`
**Purpose:** Records a single exercise session — what happened, how far the player ran, how many calories they burned, and what game actions they performed.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. |
| `user` | FK → User | No | — | The player who ran this session. Cascades on user delete. |
| `track_id` | VARCHAR(255) | No | — | Local identifier for the selected track (e.g. `"warzone"`). Definition lives on-device. |
| `character_id` | VARCHAR(255) | No | `""` | Local identifier for the selected character. Definition lives on-device. |
| `distance_covered` | FLOAT | No | `0.0` | **Primary metric.** km covered during this session. |
| `calories_burned` | INTEGER | No | `0` | kcal burned. Shown in session cards and the Statistics screen. |
| `duration_minutes` | INTEGER | No | `0` | Total time of the session in minutes. Shown as a secondary stat. |
| `average_speed` | FLOAT | Yes | `null` | km/h. Computed as `distance / time` at session end and stored here. |
| `total_jumps` | INTEGER | No | `0` | Total jump actions detected during the session. |
| `total_crouches` | INTEGER | No | `0` | Total crouch actions detected during the session. |
| `completion_status` | VARCHAR(20) | No | `in_progress` | One of: `in_progress`, `completed`, `abandoned`. |
| `created_at` | DATETIME | No | auto | When the session was started. Used as the session date in history logs. |

**Completion status lifecycle:**
```
in_progress  →  completed   (via POST /api/sessions/{id}/complete/)
in_progress  →  abandoned   (via POST /api/sessions/{id}/abandon/)
```
Only transitioning to `completed` triggers the streak + badge update logic.

**What the iOS app should send at session end:**
```json
{
  "distance_covered": 2.4,
  "calories_burned": 96,
  "duration_minutes": 12,
  "average_speed": 12.0,
  "total_jumps": 55,
  "total_crouches": 20
}
```
Then immediately call `POST /api/sessions/{id}/complete/`.

---

### 2.3 `DailyProgress`

**Table:** `daily_progress`
**Purpose:** One row per (user, calendar date). Aggregates all completed sessions for that day and records whether the user hit both daily targets. This is the source of truth for the streak calendar widget (the SUN/MON/TUE view in Statistics).

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. |
| `user` | FK → User | No | — | The user this record belongs to. |
| `date` | DATE | No | — | Calendar date (no time component). Unique per user. |
| `total_distance` | FLOAT | No | `0.0` | Sum of `distance_covered` across all completed sessions that day (km). |
| `total_calories` | INTEGER | No | `0` | Sum of `calories_burned` across all completed sessions that day (kcal). |
| `total_duration_mins` | INTEGER | No | `0` | Sum of `duration_minutes` across all completed sessions that day. |
| `target_met` | BOOLEAN | No | `false` | `true` when `total_distance >= daily_target_distance` AND `total_calories >= daily_target_calories`. |
| `created_at` | DATETIME | No | auto | When this record was first created. |
| `updated_at` | DATETIME | No | auto | Last time this record was updated. |

**Constraints:**
- `UNIQUE(user, date)` — one row per user per day, always.

**Notes:**
- This table is **never written to directly by the iOS app.** It is created and updated automatically by the backend whenever `POST /api/sessions/{id}/complete/` is called.
- The iOS app reads this via `GET /api/users/{id}/streak-calendar/` to render the calendar widget.
- A day with `target_met = true` shows the gold medal badge in the calendar. A day with `target_met = false` (but a row exists) shows a grey circle (session happened but target missed).

---

### 2.4 `Badge`

**Table:** `badges`
**Purpose:** Defines the achievement badges available in the game. These are managed by the team via the Django admin panel — not created by the app or users.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. |
| `name` | VARCHAR(255) | No | — | Display name (e.g. `"Reactor Core"`). |
| `description` | TEXT | No | — | Short description shown in the badge card (e.g. `"Burn 500 active calories."`). |
| `icon` | VARCHAR(255) | No | — | Asset key that maps to a locally-bundled image in the iOS app (e.g. `"reactor_core"`). The backend does not store the image. |
| `badge_type` | VARCHAR(50) | No | — | What stat this badge tracks. One of: `calories`, `distance`, `sessions`, `streak`, `jumps`, `crouches`. |
| `target_value` | FLOAT | No | — | The threshold to reach. E.g. `500` for calories, `10` for sessions. |

**Badge types and what they track:**

| `badge_type` | Tracks |
|---|---|
| `calories` | Total lifetime kcal burned across all completed sessions |
| `distance` | Total lifetime km covered across all completed sessions |
| `sessions` | Total number of completed sessions |
| `streak` | Longest streak ever reached |
| `jumps` | Total lifetime jumps across all completed sessions |
| `crouches` | Total lifetime crouches across all completed sessions |

**Examples from the app:**
| Badge | Type | Target |
|---|---|---|
| Reactor Core | `calories` | 500 |
| Nebula Walker | `distance` | 100 (km... or mins — to be updated per new metric) |
| Titanium Lungs | `sessions` | 10 |

---

### 2.5 `UserBadge`

**Table:** `user_badges`
**Purpose:** Tracks each individual user's progress toward every badge. One row per (user, badge) pair. Created and updated automatically by the backend — the iOS app only reads this.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. |
| `user` | FK → User | No | — | The user. |
| `badge` | FK → Badge | No | — | The badge being tracked. |
| `current_progress` | FLOAT | No | `0.0` | Current value of the tracked stat (e.g. `96` calories burned so far). |
| `is_completed` | BOOLEAN | No | `false` | `true` when `current_progress >= badge.target_value`. |
| `completed_at` | DATETIME | Yes | `null` | Timestamp when the badge was first completed. |
| `created_at` | DATETIME | No | auto | When this tracking record was created. |
| `updated_at` | DATETIME | No | auto | Last update. |

**Constraints:**
- `UNIQUE(user, badge)` — one progress row per user per badge, always.

**How the profile badge screen maps to this:**
- **"In Progress" tab** → `UserBadge` rows where `is_completed = false`, ordered by `badge_type` then `target_value`
- **"Completed" tab** → `UserBadge` rows where `is_completed = true`, ordered by `completed_at` descending
- Progress bar: `current_progress / badge.target_value`

---

### 2.6 `Friendship`

**Table:** `friendships`
**Purpose:** Tracks friend relationships between users for the Multiplayer screen.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | auto | Primary key. |
| `requester` | FK → User | No | — | The user who sent the friend request. |
| `receiver` | FK → User | No | — | The user who received the request. |
| `status` | VARCHAR(20) | No | `pending` | One of: `pending`, `accepted`, `declined`, `blocked`. |
| `created_at` | DATETIME | No | auto | When the request was sent. |

**Constraints:**
- `UNIQUE(requester, receiver)` — one relationship record per pair (directional).

---

## 3. How Core Logic Works

### 3.1 Password Hashing

Passwords are **never stored in plaintext.** When a password is submitted (create or update user), the serializer calls `user.set_password(raw_password)` which runs it through Django's PBKDF2-SHA256 hasher. The resulting hash (e.g. `pbkdf2_sha256$600000$salt$hash`) is stored in the `password` column.

**Verifying a password:**
```python
user.verify_password("user_typed_this")  # returns True or False
```

**The `password` field is never returned in any API response.** It is `write_only=True` in the serializer.

> **⚠️ TODO for the team:** A proper login endpoint (`POST /api/auth/login/`) that accepts `{username, password}` and returns a token (JWT or session) needs to be built before the app goes to production. Right now authentication is not enforced on any endpoint.

---

### 3.2 Streak Calculation

Streaks are calculated automatically each time `POST /api/sessions/{id}/complete/` is called. The flow is:

1. The completed session's date is determined from `session.created_at.date()`
2. `DailyProgress` for that date is upserted (see §3.3)
3. If `target_met` is now `True` for that date, the streak logic runs:
   - All `DailyProgress` rows for the user where `target_met = True` are fetched, ordered most-recent-first
   - Starting from the most recent qualifying date, consecutive days are counted
   - If the most recent qualifying day is **before yesterday**, `current_streak` resets to `0`
   - `longest_streak` only ever goes up, never down
4. `user.current_streak`, `user.longest_streak`, and `user.last_streak_date` are saved

**Example:**
```
Mon ✓ → Tue ✓ → Wed ✓ → Thu ✗ → Fri ✓ (today)
                         ↑ streak broken
current_streak = 1  (only today qualifies as a live streak)
longest_streak = 3  (Mon–Wed)
```

---

### 3.3 Daily Progress Aggregation

Every time a session is completed, the `DailyProgress` row for that session's date is **fully re-aggregated** from scratch (not just incremented). This means:

- If a user completes 3 sessions in one day, `total_distance` = sum of all 3
- If a session is somehow edited retroactively, the numbers stay correct
- `target_met` is rechecked each time: `total_distance >= user.daily_target_distance AND total_calories >= user.daily_target_calories`

---

### 3.4 Badge Progress Updates

After every completed session, all badges are checked against the user's current lifetime stats:

| Badge Type | Lifetime stat used |
|---|---|
| `calories` | `SUM(calories_burned)` of all completed sessions |
| `distance` | `SUM(distance_covered)` of all completed sessions |
| `sessions` | `COUNT(*)` of all completed sessions |
| `streak` | `user.longest_streak` |
| `jumps` | `SUM(total_jumps)` of all completed sessions |
| `crouches` | `SUM(total_crouches)` of all completed sessions |

For each badge:
- If the `UserBadge` row doesn't exist yet, it is created
- `current_progress` is updated to the current stat value
- If `current_progress >= badge.target_value` and not previously completed, `is_completed` flips to `True` and `completed_at` is stamped

---

## 4. API Reference

**Base URL:** `https://your-render-app.onrender.com/api/`

All responses are JSON. All IDs are UUIDs unless stated otherwise.

---

### 4.0 Health Check

#### `GET /api/health/`

Verify the server is running. No auth required.

**Response `200`:**
```json
{ "status": "ok" }
```

---

### 4.1 Users

#### `POST /api/users/` — Create a new user

Called during account registration.

**Request body:**
```json
{
  "username": "ekansh",
  "email": "ekansh@example.com",
  "password": "supersecret123",
  "display_name": "Ekansh",
  "daily_target_distance": 2.0,
  "daily_target_calories": 300,
  "current_weight": 78.0,
  "target_weight": 73.0
}
```

| Field | Required | Notes |
|---|---|---|
| `username` | Yes | Must be unique |
| `email` | No | Must be unique if provided |
| `password` | No | Hashed before storage; never returned |
| `display_name` | No | Defaults to `""` |
| `daily_target_distance` | No | Defaults to `1.0` km |
| `daily_target_calories` | No | Defaults to `300` kcal |
| `current_weight` | No | kg |
| `target_weight` | No | kg |

**Response `201`:**
```json
{
  "id": "877c82b0-...",
  "username": "ekansh",
  "email": "ekansh@example.com",
  "display_name": "Ekansh",
  "daily_target_distance": 2.0,
  "daily_target_calories": 300,
  "current_weight": 78.0,
  "target_weight": 73.0,
  "current_streak": 0,
  "longest_streak": 0,
  "last_streak_date": null,
  "is_online": false,
  "last_seen": null
}
```
> `password` is **not** in the response — ever.

---

#### `GET /api/users/` — List all users

Returns all user profiles. Useful for searching players to add as friends.

**Response `200`:** Array of user objects (same shape as above).

---

#### `GET /api/users/{id}/` — Get a user profile

Called on app launch to load the current user's profile.

**Response `200`:** Single user object.

---

#### `PATCH /api/users/{id}/` — Update a user profile

Called when the user edits their profile, changes targets, or updates weight.

**Request body** (all fields optional):
```json
{
  "display_name": "Ekansh Jindal",
  "daily_target_distance": 3.0,
  "daily_target_calories": 400,
  "current_weight": 75.0,
  "target_weight": 72.0,
  "password": "newpassword456"
}
```

**Response `200`:** Updated user object.

---

#### `DELETE /api/users/{id}/` — Delete a user

Cascades to all sessions, daily progress, badges, and friendships.

**Response `204`:** No content.

---

#### `GET /api/users/{id}/stats/` — Lifetime statistics

Powers the **Statistics screen** — Cal Burn / Runtime toggle, Last Run card, Personal Best card, Weight Goal Progress.

**Response `200`:**
```json
{
  "total_sessions": 12,
  "completed_sessions": 10,
  "total_distance": 24.6,
  "total_calories": 1204,
  "total_minutes": 145,
  "personal_best_distance": 5.2,
  "personal_best_calories": 200,
  "friend_count": 3
}
```

| Field | Description |
|---|---|
| `total_sessions` | All sessions ever started (including abandoned) |
| `completed_sessions` | Sessions with `completion_status = completed` |
| `total_distance` | Lifetime km covered (completed sessions only) |
| `total_calories` | Lifetime kcal burned (completed sessions only) |
| `total_minutes` | Lifetime minutes exercised (completed sessions only) |
| `personal_best_distance` | Best single-session distance (km) |
| `personal_best_calories` | Best single-session calorie burn (kcal) |
| `friend_count` | Number of accepted friends |

---

#### `GET /api/users/{id}/sessions/` — All sessions for a user

Powers the **History Log** in Session Analysis.

**Response `200`:** Array of session objects (see §4.2 for shape).

---

#### `GET /api/users/{id}/streak-calendar/?days=30` — Streak calendar data

Powers the **streak calendar widget** (SUN/MON/TUE view). Returns up to `days` days of daily progress records, newest first.

**Query params:**
| Param | Default | Description |
|---|---|---|
| `days` | `30` | How many days of history to return |

**Response `200`:**
```json
[
  {
    "id": "...",
    "user": "877c82b0-...",
    "date": "2026-03-18",
    "total_distance": 2.4,
    "total_calories": 96,
    "total_duration_mins": 12,
    "target_met": false,
    "created_at": "2026-03-18T17:30:00Z",
    "updated_at": "2026-03-18T17:30:00Z"
  }
]
```

**How the iOS app should use this:**
- `target_met = true` → show gold medal badge for that day
- A row exists but `target_met = false` → show grey circle (trained but didn't hit target)
- No row for a day → no activity (empty slot)

---

#### `GET /api/users/{id}/badges/` — User's badge progress

Powers the **Badges section** on the Profile screen (In Progress + Completed tabs).

**Response `200`:**
```json
[
  {
    "id": "...",
    "badge": {
      "id": "...",
      "name": "Reactor Core",
      "description": "Burn 500 active calories.",
      "icon": "reactor_core",
      "badge_type": "calories",
      "target_value": 500.0
    },
    "current_progress": 96.0,
    "is_completed": false,
    "completed_at": null,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

Progress bar value: `current_progress / badge.target_value`

---

#### `GET /api/users/{id}/friends/` — List accepted friends

Returns all accepted `Friendship` records for this user (both sent and received).

**Response `200`:** Array of friendship objects (see §4.4).

---

#### `POST /api/users/{id}/go-online/` — Mark user online

Call when the app becomes active / user starts a session.

**Response `200`:**
```json
{ "status": "online" }
```

---

#### `POST /api/users/{id}/go-offline/` — Mark user offline

Call when the app backgrounds or the user exits.

**Response `200`:**
```json
{ "status": "offline" }
```

---

### 4.2 Game Sessions

#### `POST /api/sessions/` — Start a new session

Called when the user taps **START**. Creates a session in `in_progress` state.

**Request body:**
```json
{
  "user": "877c82b0-...",
  "track_id": "warzone",
  "character_id": "robot_bunny"
}
```

**Response `201`:**
```json
{
  "id": "abc123-...",
  "user": "877c82b0-...",
  "username": "ekansh",
  "track_id": "warzone",
  "character_id": "robot_bunny",
  "distance_covered": 0.0,
  "calories_burned": 0,
  "duration_minutes": 0,
  "average_speed": null,
  "total_jumps": 0,
  "total_crouches": 0,
  "completion_status": "in_progress",
  "created_at": "2026-03-18T17:00:00Z"
}
```

---

#### `PATCH /api/sessions/{id}/` — Update session data

Called at the end of a session (before completing/abandoning) to send the final stats.

**Request body:**
```json
{
  "distance_covered": 2.4,
  "calories_burned": 96,
  "duration_minutes": 12,
  "average_speed": 12.0,
  "total_jumps": 55,
  "total_crouches": 20
}
```

**Response `200`:** Updated session object.

---

#### `POST /api/sessions/{id}/complete/` — Complete a session ⭐

The most important endpoint. Call this **after** PATCHing the final stats. This:
1. Sets `completion_status` to `completed`
2. Upserts the `DailyProgress` row for today
3. Recalculates the user's streak (`current_streak`, `longest_streak`, `last_streak_date`)
4. Updates progress on all badges and unlocks any newly-achieved ones

**No request body needed.**

**Response `200`:** The completed session object with all final stats.

> **Recommended flow for ending a session:**
> ```
> PATCH /api/sessions/{id}/    ← send distance, calories, time, jumps, crouches
> POST  /api/sessions/{id}/complete/   ← trigger all downstream logic
> GET   /api/users/{id}/stats/         ← refresh the Statistics screen
> GET   /api/users/{id}/streak-calendar/  ← refresh the streak calendar
> GET   /api/users/{id}/badges/        ← check for newly unlocked badges
> ```

---

#### `POST /api/sessions/{id}/abandon/` — Abandon a session

Sets `completion_status` to `abandoned`. Does **not** update daily progress, streaks, or badges.

**No request body needed.**

**Response `200`:** The abandoned session object.

---

#### `GET /api/sessions/` — List all sessions (filterable)

Supports query params for filtering:

| Param | Example | Description |
|---|---|---|
| `user` | `?user=877c82b0-...` | Filter by user UUID |
| `completion_status` | `?completion_status=completed` | Filter by status |
| `track_id` | `?track_id=warzone` | Filter by track |
| `character_id` | `?character_id=robot_bunny` | Filter by character |

**Response `200`:** Array of session objects.

---

#### `GET /api/sessions/{id}/` — Get a single session

**Response `200`:** Single session object.

---

### 4.3 Badges

#### `GET /api/badges/` — List all badge definitions

Returns all badges that exist in the system. The iOS app uses this to know what icons to show and what the thresholds are.

**Response `200`:**
```json
[
  {
    "id": "...",
    "name": "Reactor Core",
    "description": "Burn 500 active calories.",
    "icon": "reactor_core",
    "badge_type": "calories",
    "target_value": 500.0
  },
  {
    "id": "...",
    "name": "Nebula Walker",
    "description": "Cover 100 km in total.",
    "icon": "nebula_walker",
    "badge_type": "distance",
    "target_value": 100.0
  }
]
```

#### `GET /api/badges/{id}/` — Get a single badge definition

**Response `200`:** Single badge object.

> Badges are **read-only** from the API. Create and manage them via the Django admin panel at `/admin/`.

---

### 4.4 Friendships

#### `POST /api/friendships/` — Send a friend request

**Request body:**
```json
{
  "requester": "877c82b0-...",
  "receiver": "999abc-..."
}
```

**Response `201`:**
```json
{
  "id": "...",
  "requester": "877c82b0-...",
  "requester_username": "ekansh",
  "receiver": "999abc-...",
  "receiver_username": "demo2",
  "status": "pending",
  "created_at": "..."
}
```

---

#### `POST /api/friendships/{id}/accept/` — Accept a friend request

Only works if `status = pending`. Sets status to `accepted`.

**Response `200`:** Updated friendship object.

---

#### `POST /api/friendships/{id}/decline/` — Decline a friend request

Only works if `status = pending`. Sets status to `declined`.

**Response `200`:** Updated friendship object.

---

#### `POST /api/friendships/{id}/block/` — Block a user

Works from any status. Sets status to `blocked`.

**Response `200`:** Updated friendship object.

---

#### `GET /api/friendships/` — List all friendships

Returns all friendship records system-wide.

**Response `200`:** Array of friendship objects.

---

#### `GET /api/friendships/{id}/` — Get a single friendship record

**Response `200`:** Single friendship object.

---

## 5. What Lives Locally (On-Device)

The following are intentionally **not** in the database. They are bundled directly in the iOS app:

| Item | Reason |
|---|---|
| **Character definitions** (name, image, animations) | Only 2 characters; game runs offline; no backend lookup needed |
| **Track definitions** (name, background, layout) | Only 2 tracks; same reasoning |
| **Badge icons / images** | Images are app assets; the backend stores only the `icon` key string |
| **Game physics & motion detection logic** | Lives in the game engine, runs entirely on-device |

The backend only stores the **string ID** (`track_id`, `character_id`, `icon`) for reference and history. The app resolves these to actual assets locally.

---

## 6. Schema Diagram

```
┌─────────────────────────────────┐
│            users                │
├─────────────────────────────────┤
│ id (UUID, PK)                   │
│ username (unique)               │
│ email (unique, nullable)        │
│ password (hashed, write-only)   │
│ display_name                    │
│ daily_target_distance (km)      │
│ daily_target_calories (kcal)    │
│ current_weight (kg)             │
│ target_weight (kg)              │
│ current_streak                  │
│ longest_streak                  │
│ last_streak_date                │
│ is_online                       │
│ last_seen                       │
└────────────┬────────────────────┘
             │ 1
             │
     ┌───────┼──────────────────────────┐
     │       │                          │
     │ n     │ n                        │ n
     ▼       ▼                          ▼
┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  game_sessions   │  │  daily_progress   │  │   user_badges    │
├──────────────────┤  ├───────────────────┤  ├──────────────────┤
│ id (UUID, PK)    │  │ id (UUID, PK)     │  │ id (UUID, PK)    │
│ user (FK)        │  │ user (FK)         │  │ user (FK)        │
│ track_id         │  │ date              │  │ badge (FK)       │
│ character_id     │  │ total_distance    │  │ current_progress │
│ distance_covered │  │ total_calories    │  │ is_completed     │
│ calories_burned  │  │ total_duration    │  │ completed_at     │
│ duration_minutes │  │ target_met        │  │ created_at       │
│ average_speed    │  │ created_at        │  │ updated_at       │
│ total_jumps      │  │ updated_at        │  └────────┬─────────┘
│ total_crouches   │  │                   │           │ n
│ completion_status│  │ UNIQUE(user,date) │           │
│ created_at       │  └───────────────────┘           │ 1
└──────────────────┘                        ┌─────────┴────────┐
                                            │      badges      │
┌──────────────────────────────────┐        ├──────────────────┤
│           friendships            │        │ id (UUID, PK)    │
├──────────────────────────────────┤        │ name             │
│ id (UUID, PK)                    │        │ description      │
│ requester (FK → users)           │        │ icon             │
│ receiver (FK → users)            │        │ badge_type       │
│ status (pending/accepted/        │        │ target_value     │
│         declined/blocked)        │        └──────────────────┘
│ created_at                       │
│ UNIQUE(requester, receiver)      │
└──────────────────────────────────┘
```

---

*This guide reflects schema v2. For historical schema v1 reference, see migration `0001_initial.py`.*
