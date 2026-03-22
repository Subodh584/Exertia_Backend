# Exertia Backend — iOS API Reference

**Base URL:** `https://exertia-backend.onrender.com/api`
**Format:** All requests and responses are JSON
**Auth:** JWT Bearer token (see Authentication section below)

---

## Authentication

### How it works

1. Call `POST /api/auth/login/` with username + password → get `access` + `refresh` tokens
2. Store both tokens on the device (Keychain recommended)
3. Attach the `access` token to **every** subsequent request as a header:
   ```
   Authorization: Bearer <access_token>
   ```
4. Access token expires after **3 days**. When it expires, call `POST /api/auth/refresh/` with the refresh token to get a new pair
5. On logout, call `POST /api/auth/logout/` to invalidate the refresh token server-side

### Token lifetime
| Token | Lifetime |
|---|---|
| Access token | 3 days |
| Refresh token | 30 days |

---

## Public Endpoints (no token required)

### Register
```
POST /api/users/
```
**Body:**
```json
{
  "username": "ekanshjindal",
  "password": "mypassword",
  "display_name": "Ekansh Jindal",
  "daily_target_distance": 5.0,
  "daily_target_calories": 500
}
```
**Required fields:** `username`, `password`
**Optional fields:** `display_name`, `email`, `daily_target_distance` (default: 1.0 km), `daily_target_calories` (default: 300 kcal), `current_weight`, `target_weight`

**Response 201:**
```json
{
  "id": "3207ab17-b287-4484-ad33-d4a87f46368e",
  "username": "ekanshjindal",
  "email": null,
  "display_name": "Ekansh Jindal",
  "daily_target_distance": 5.0,
  "daily_target_calories": 500,
  "current_weight": null,
  "target_weight": null,
  "current_streak": 0,
  "longest_streak": 0,
  "last_streak_date": null,
  "is_online": false,
  "last_seen": null
}
```
> Note: `password` is **never** returned in any response.

---

### Login
```
POST /api/auth/login/
```
**Body:**
```json
{
  "username": "demo",
  "password": "abc123"
}
```
**Response 200:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "3207ab17-b287-4484-ad33-d4a87f46368e",
    "username": "demo",
    "email": null,
    "display_name": "Demo",
    "daily_target_distance": 1.0,
    "daily_target_calories": 300,
    "current_weight": null,
    "target_weight": null,
    "current_streak": 0,
    "longest_streak": 0,
    "last_streak_date": null,
    "is_online": true,
    "last_seen": "2026-03-20T10:00:00Z"
  }
}
```
**Error 401:**
```json
{ "error": "Invalid credentials" }
```
> Save the `user.id` — you'll need it for all user-specific calls.
> Login also sets `is_online = true` and updates `last_seen` automatically.

---

### Verify token / Get current user (use on app launch)
```
GET /api/auth/me/
Authorization: Bearer <access_token>
```
**Response 200:** Current user object (same format as Get single user)
**Response 401:** Token missing, expired, or invalid → redirect to login

> **iOS flow:** On every app launch, call this with the stored token.
> - `200` → go straight to home screen
> - `401` → try `POST /api/auth/refresh/` with stored refresh token
>   - New token received → save it and retry `GET /api/auth/me/`
>   - Refresh also fails → show login screen

---

### Refresh Token
```
POST /api/auth/refresh/
```
**Body:**
```json
{
  "refresh": "<refresh_token>"
}
```
**Response 200:**
```json
{
  "access": "<new_access_token>",
  "refresh": "<new_refresh_token>"
}
```
> Both tokens rotate — save the new refresh token, the old one is now invalid.

---

### Change Password
```
POST /api/auth/change-password/
Authorization: Bearer <access_token>
```
**Body:**
```json
{
  "old_password": "abc123",
  "new_password": "newpassword"
}
```
**Response 200:**
```json
{ "detail": "Password changed successfully." }
```
**Error responses:**
```json
{ "detail": "Both fields are required." }         // 400 — missing field
{ "detail": "Current password is incorrect." }    // 400 — wrong old password
{ "detail": "Password must be at least 6 characters." } // 400 — too short
```

---

### Logout
```
POST /api/auth/logout/
```
**Body:**
```json
{
  "refresh": "<refresh_token>"
}
```
**Response 200:**
```json
{ "detail": "Successfully logged out" }
```
> Also sets `is_online = false` and updates `last_seen` automatically.

---

## Protected Endpoints (Bearer token required)

All requests below require:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Users

### Get all users
```
GET /api/users/
```
**Response 200:**
```json
{
  "count": 9,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3207ab17-b287-4484-ad33-d4a87f46368e",
      "username": "demo",
      "email": null,
      "display_name": "Demo",
      "daily_target_distance": 1.0,
      "daily_target_calories": 300,
      "current_weight": null,
      "target_weight": null,
      "current_streak": 0,
      "longest_streak": 0,
      "last_streak_date": null,
      "is_online": true,
      "last_seen": "2026-03-20T10:00:00Z"
    }
  ]
}
```

---

### Get single user
```
GET /api/users/{user_id}/
```
**Response 200:** Same as single user object above.

---

### Update user
```
PATCH /api/users/{user_id}/
```
**Body (any subset of fields):**
```json
{
  "display_name": "New Name",
  "daily_target_distance": 8.0,
  "daily_target_calories": 600,
  "current_weight": 75.5,
  "target_weight": 70.0,
  "email": "user@example.com"
}
```
**Response 200:** Updated user object.

---

### Delete user
```
DELETE /api/users/{user_id}/
```
**Response 204:** No content.

---

### Get user stats (lifetime aggregates)
```
GET /api/users/{user_id}/stats/
```
**Response 200:**
```json
{
  "total_sessions": 12,
  "completed_sessions": 9,
  "total_distance": 45.3,
  "total_calories": 3200,
  "total_minutes": 480,
  "personal_best_distance": 8.5,
  "personal_best_calories": 650,
  "friend_count": 3
}
```

---

### Get user sessions
```
GET /api/users/{user_id}/sessions/
```
**Response 200:** Array of session objects (see Sessions section).

---

### Get user badges
```
GET /api/users/{user_id}/badges/
```
**Response 200:**
```json
[
  {
    "id": "uuid",
    "badge": {
      "id": "uuid",
      "name": "First Steps",
      "description": "Complete your first session",
      "icon": "badge_first_steps",
      "badge_type": "sessions",
      "target_value": 1.0
    },
    "current_progress": 0.0,
    "is_completed": false,
    "completed_at": null,
    "created_at": "2026-03-20T10:00:00Z",
    "updated_at": "2026-03-20T10:00:00Z"
  }
]
```

---

### Get streak calendar
```
GET /api/users/{user_id}/streak-calendar/
GET /api/users/{user_id}/streak-calendar/?days=7
```
**Response 200:**
```json
[
  {
    "id": "uuid",
    "user": "uuid",
    "date": "2026-03-20",
    "total_distance": 5.2,
    "total_calories": 420,
    "total_duration_mins": 35,
    "target_met": true,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### Go online / Go offline
```
POST /api/users/{user_id}/go-online/
POST /api/users/{user_id}/go-offline/
```
**Body:** Empty
**Response 200:**
```json
{ "status": "online" }
{ "status": "offline" }
```

---

## Game Sessions

### Create session (start game)
```
POST /api/sessions/
```
**Body:**
```json
{
  "user": "3207ab17-b287-4484-ad33-d4a87f46368e",
  "track_id": "track_forest_run",
  "character_id": "character_default",
  "distance_covered": 0.0,
  "calories_burned": 0,
  "duration_minutes": 0
}
```
**Required fields:** `user`, `track_id`
**Response 201:** Session object with `completion_status: "in_progress"`

---

### Get all sessions
```
GET /api/sessions/
```
**Filter options:**
```
GET /api/sessions/?user=<user_id>
GET /api/sessions/?completion_status=completed
GET /api/sessions/?completion_status=in_progress
GET /api/sessions/?completion_status=abandoned
GET /api/sessions/?track_id=track_forest_run
GET /api/sessions/?character_id=character_default
```

---

### Get single session
```
GET /api/sessions/{session_id}/
```
**Response 200:**
```json
{
  "id": "uuid",
  "user": "uuid",
  "username": "demo",
  "track_id": "track_forest_run",
  "character_id": "character_default",
  "distance_covered": 3.5,
  "calories_burned": 280,
  "duration_minutes": 22,
  "average_speed": 9.5,
  "total_jumps": 12,
  "total_crouches": 8,
  "total_left_leans": 15,
  "total_right_leans": 11,
  "completion_status": "in_progress",
  "created_at": "2026-03-20T10:00:00Z"
}
```

---

### Update session (send sensor data)
```
PATCH /api/sessions/{session_id}/
```
**Body:** Any fields to update during gameplay:
```json
{
  "distance_covered": 3.5,
  "calories_burned": 280,
  "duration_minutes": 22,
  "average_speed": 9.5,
  "total_jumps": 12,
  "total_crouches": 8,
  "total_left_leans": 15,
  "total_right_leans": 11
}
```

---

### Complete session (end game — triggers streak + badge update)
```
POST /api/sessions/{session_id}/complete/
```
**Body:** Empty (or send final stats via PATCH first, then complete)
**Response 200:** Final session object.
> This triggers: daily progress update → streak recalculation → badge progress update.

---

### Abandon session
```
POST /api/sessions/{session_id}/abandon/
```
**Body:** Empty
**Response 200:** Session object with `completion_status: "abandoned"`

---

## Badges

### List all badge definitions
```
GET /api/badges/
```
**Response 200:**
```json
{
  "count": 6,
  "results": [
    {
      "id": "uuid",
      "name": "Speed Demon",
      "description": "Cover 100km total",
      "icon": "badge_speed_demon",
      "badge_type": "distance",
      "target_value": 100.0
    }
  ]
}
```
**Badge types:** `calories`, `distance`, `sessions`, `streak`, `jumps`, `crouches`

---

## Friendships

### Send friend request
```
POST /api/friendships/
```
**Body:**
```json
{
  "requester": "<your_user_id>",
  "receiver": "<their_user_id>"
}
```
**Response 201:** Friendship object with `status: "pending"`

---

### Get friendships
```
GET /api/friendships/
```

### Accept / Decline / Block
```
POST /api/friendships/{friendship_id}/accept/
POST /api/friendships/{friendship_id}/decline/
POST /api/friendships/{friendship_id}/block/
```
**Body:** Empty
**Response 200:** Updated friendship object.

---

## Typical iOS App Flow

```
1. App launch
   └── Check Keychain for stored access token
       ├── No token → show login screen
       └── Token exists → GET /api/auth/me/
           ├── 200 → go straight to home screen with user data
           └── 401 → POST /api/auth/refresh/ with stored refresh token
               ├── 200 → save new tokens, retry GET /api/auth/me/ → home screen
               └── 401 → show login screen

2. Login screen
   └── POST /api/auth/login/ → save access + refresh + user.id to Keychain

3. During session
   ├── POST /api/sessions/ → get session_id
   ├── PATCH /api/sessions/{id}/ → update stats as sensors fire
   └── POST /api/sessions/{id}/complete/ → end game, triggers streak/badge update

4. Token expired (API returns 401)
   ├── POST /api/auth/refresh/ with stored refresh token
   ├── Save new access + refresh tokens
   └── Retry original request

5. Logout
   └── POST /api/auth/logout/ with refresh token → clear Keychain
```

---

## Error Reference

| Status | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `204` | Deleted (no content) |
| `400` | Bad request — check your JSON body |
| `401` | Unauthorized — missing/expired/invalid token |
| `403` | Forbidden |
| `404` | Resource not found |
| `500` | Server error |

**401 response format:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
or
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

---

## User Object Reference

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | Primary key — store this after login |
| `username` | string | Unique |
| `email` | string or null | Optional |
| `display_name` | string | Display name in UI |
| `daily_target_distance` | float | km, default 1.0 |
| `daily_target_calories` | int | kcal, default 300 |
| `current_weight` | float or null | kg |
| `target_weight` | float or null | kg |
| `current_streak` | int | Read-only, server-managed |
| `longest_streak` | int | Read-only, server-managed |
| `last_streak_date` | date string or null | Read-only, server-managed |
| `is_online` | bool | Updated by login/logout/go-online/go-offline |
| `last_seen` | datetime or null | Updated automatically |

## Session Object Reference

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | |
| `user` | UUID string | User ID |
| `username` | string | Read-only, from user |
| `track_id` | string | Track identifier from app |
| `character_id` | string | Character identifier from app |
| `distance_covered` | float | km |
| `calories_burned` | int | kcal |
| `duration_minutes` | int | |
| `average_speed` | float or null | km/h |
| `total_jumps` | int | Jump sensor count |
| `total_crouches` | int | Crouch sensor count |
| `total_left_leans` | int | Left lean/turn sensor count |
| `total_right_leans` | int | Right lean/turn sensor count |
| `completion_status` | string | `in_progress`, `completed`, `abandoned` |
| `created_at` | datetime | |
