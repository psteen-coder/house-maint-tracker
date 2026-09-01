# Operations

Day-to-day use of House Maint Tracker at 1944 Dinius.

## Roles

| Role | Can do |
|------|--------|
| `admin` | Everything: users, tasks, occurrences, weather reschedule, themes |
| `member` | Create/update tasks and occurrences, run weather reschedule; cannot create/delete users |
| `viewer` | Read board, calendar, people list, forecast; no mutations |

Seeded accounts (change before LAN exposure):

- admin: `patrick@1944dinius.local` / `adminpass`
- member: `alex@1944dinius.local` / `memberpass`
- viewer: `jamie@1944dinius.local` / `viewerpass`

There is no self-serve password-reset screen yet. To add a person: sign in as admin → People → Add household member.

To rotate a password today, create a replacement user and stop using the old email, or update `users.password_hash` in SQLite (PBKDF2 via `app.seed.hash_password`).

## Views

- **Board** — due in the next 7 days, in progress, completed in the last 7 days. Start / Complete / assignee on each card (not for viewers).
- **Calendar** — month grid; tap a day for that day’s occurrences.
- **Tasks** — catalog of recurring definitions; members/admins can add one (recurrence, season, estimate, outdoor flag, assignee).
- **People** — household roster.
- **Weather** — 16-day Open-Meteo forecast for the house lat/lon; **Reschedule from forecast** shifts outdoor occurrences.

Themes (light, dark, forest, terracotta, slate) persist per user.

## Scheduling

Recurrence on a task:

- `once` — next matching month/day on or after today
- `monthly` — `day` of month (clamped)
- `quarterly` — Jan/Apr/Jul/Oct
- `seasonal` — spring 20 Mar, summer 21 Jun, fall 22 Sep, winter 21 Dec
- `yearly` — month + day

Completing a non-`once` occurrence rolls the next due date.

Dependencies: a task can `depends_on` another. An occurrence is **blocked** while the parent still has an incomplete occurrence due on or before it. Start/Complete returns 409 until the parent is done.

## Weather reschedule

Outdoor tasks store prefs (default seed: require dry, max 0.8 mm precip, min 4 °C, max 40 km/h wind).

On **Reschedule from forecast**:

1. Pull Open-Meteo daily precip / max temp / max wind for house lat/lon (America/Detroit, 16 days).
2. Indoor tasks never move.
3. If the due day fails prefs, pick the closest day in **±3 days** that passes. Distance ties prefer the **earlier** day.
4. If nothing in the window is favorable, the due date stays.

Internet required for the feed. Kernel logic is unit-tested without the network (`backend/tests/test_weather.py`).

## House location

Seeded settings (SQLite `settings` table):

| key | value |
|-----|--------|
| name | 1944 Dinius |
| address | 1944 Dinius Road, Raisin Township, Lenawee County, Michigan 49286 |
| lat | 41.9849515 |
| lon | -83.9916572 |
| timezone | America/Detroit |

To move the weather pin (sqlite3 CLI):

```bash
sqlite3 house_maint.db "UPDATE settings SET value='41.98' WHERE key='lat';"
sqlite3 house_maint.db "UPDATE settings SET value='-83.99' WHERE key='lon';"
```

Restart not required; the next forecast call reads settings.

## Backup

Copy `house_maint.db`. That file is the source of truth. See [SERVER.md](SERVER.md) for a stop-copy-start sequence.

## Security notes

- Session tokens are random server-side rows (not JWT). Logout deletes the token.
- Passwords are PBKDF2-SHA256 (120k iterations), stored as `salt$hash`.
- CORS is open (`*`) for LAN/dev. Tighten if you put this on the public internet.
- No TLS in-app. Use a reverse proxy for HTTPS.
