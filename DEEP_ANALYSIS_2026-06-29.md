# DEEP_ANALYSIS.md — UzVehicles / OLX Data Platform Audit

> Audit date: 2026-06-29  
> Reviewer: Claude Sonnet 4.6 (read-only mode)  
> Scope: all source files in the repo root (excluding `.claude/worktrees/`, `*.pkl`, `node_modules`)

---

## Executive Summary

The project is a well-executed one-developer scraping + analytics platform with
impressive feature breadth. The core data pipeline (scrape → PostgreSQL → Django
REST → Telegram bots) is solid, Flyway-managed schema is a good choice, and
the scraper's early-stop logic is thoughtful. **However, the project has
significant security gaps that must be addressed before any broader exposure.**

| Area | Health | Key risk |
|---|---|---|
| Architecture | ⚠️ Moderate | God-object `views.py`, N+1 queries, no pagination on CarList |
| Authentication | ❌ Critical | Django API has **zero** auth — any host process can destroy data |
| Secrets | ❌ Critical | Insecure SECRET_KEY in `.env`, weak admin password, bot tokens in plaintext `.env` |
| Django config | ❌ Critical | `DEBUG=True` + `ALLOWED_HOSTS=['*']` in production paths |
| Input validation | ⚠️ Medium | No whitelist on `category` param, `CarList` returns unbounded rows |
| Test coverage | ❌ None | Effectively no backend tests |

---

## Architecture Map

```
OLX.uz  ──────────────────────────────────────────────────────────────┐
                                                                       │
  cars scraper            apartments scraper       electronics scraper  │
  (v2, continuous loop)   (one-shot + scheduled)  (one-shot + auto)    │
          │                       │                      │             │
          └─────────── POST /api/{cars|apartments|electronics}/ ───────┘
                                  │
                                  ▼
  ┌────────────────────────── Django REST API (port 8000) ──────────────┐
  │  app: cars                                                          │
  │  views.py (1644 lines)  ← ALL logic lives here                     │
  │  models.py: Car, Apartment, Electronics                             │
  │  serializers.py: three __all__ serializers                         │
  │  NO AUTHENTICATION on any endpoint                                  │
  └──────────────────────────┬──────────────────────────────────────────┘
                             │ internal Docker network (car-dev-net)
            ┌────────────────┼─────────────────────────┐
            │                │                         │
    ┌───────▼────────┐  ┌────▼────────┐  ┌────────────▼────────┐
    │  tg_bot        │  │  ops_bot    │  │  tg_channel         │
    │  @MVehicleBot  │  │  @olx_data  │  │  analytics posts    │
    │  admin_panel   │  │  /status    │  │  10 post types      │
    └───────┬────────┘  └─────────────┘  └─────────────────────┘
            │
    ┌───────▼────────────────────────┐
    │  car_vision_api (port 8600)    │  ← Anthropic Claude Haiku
    │  /analyze — photo inspection   │
    └────────────────────────────────┘

  ml_api (port 8500)  ← RandomForest, two .pkl models
  PostgreSQL (port 5435→5432)  ← schema: marketplace
  Nginx (port 80)  ← React SPA + reverse proxy

  External deps: CBU API (UZS rate), Telegram API, Anthropic API
```

### Layer diagram

```
[Browser / Telegram users]
        ↓
[Nginx :80]    →  [React SPA]
        ↓              ↓
[Django API :8000]  ←  /api/*
        ↓
[PostgreSQL :5432]  ←  schema: marketplace
                           cars · apartments · electronics
                           scraper_runs · channel_post_config
```

### Services × profiles

| Service | Always-on | Profile | Port (host) |
|---|---|---|---|
| postgres | ✅ | — | 5435 |
| django | ✅ | — | **8000** (exposed) |
| frontend | ✅ | — | 80 |
| ml_api | ✅ | — | **8500** (exposed) |
| car_vision_api | ✅ | — | **8600** (exposed) |
| tg_bot | ✅ | — | — |
| ops_bot | ✅ | — | — |
| scraper | ✅ | — | — |
| scraper_electronics_auto | ✅ | — | — (new) |
| scraper_apartments | ❌ | `scrape_apartments` | — |
| scraper_electronics | ❌ | `scrape_electronics` | — |
| tg_channel | ❌ | `channel` | — |

---

## Findings: Structure & Architecture

### A-1. God-object `views.py` (1644 lines, 20+ classes)

**File:** `backend/cars/views.py`

All API views, all analytics logic, all data normalization functions, all raw
SQL queries, and the live UZS rate fetcher live in a single 1644-line file.
This violates single-responsibility and makes the file hard to navigate, test,
or extend. The `ElectronicsReport.get()` and `ElectronicsListings.get()`
methods each contain identical 80-line SQL CASE blocks — any change must be
made in two places or they drift.

**Recommendation (long-term):** Split into:
- `views/cars.py`, `views/apartments.py`, `views/electronics.py`
- `services/currency.py` (rate cache)
- `services/analytics.py` (channel analytics)

### A-2. `cars` app owns apartments and electronics

**Files:** `backend/cars/models.py`, `backend/cars/urls.py`

The `cars` Django app is home to `Apartment` and `Electronics` ORM models.
The `app_label = 'cars'` on all three models and the single `urls.py`
importing all 18 views creates conceptual confusion and makes the codebase
harder for new contributors.

**Recommendation (medium-term):** Add `apartments` and `electronics` as
separate Django apps with their own models, views, and URL configs. Since
`managed = False`, this is a rename+move, no schema change needed.

### A-3. N+1 query problem in `WeeklyDigest`

**File:** `backend/cars/views.py:770–831`

```python
for row in brand_rows:          # 10 brands
    for m in model_rows:        # 5 models each
        with connection.cursor() as cur:
            cur.execute(...)    # percentile query — 50 extra DB calls
        qs_now  = ...aggregate  # + 50 ORM queries
        qs_year = ...aggregate  # + 50 ORM queries
```

This executes ~150 extra database calls per `/api/cars/weekly-digest/`
request beyond the initial aggregation. At 10–50ms per call, this is
1.5–7.5 seconds of DB time per channel post.

**Recommendation:** Rewrite as a single SQL CTE with window functions for
percentiles and year-ago values in one pass.

### A-4. `CarList.GET` returns all rows without pagination

**File:** `backend/cars/views.py:55–62`

```python
def get(self, request):
    cars = Car.objects.all()
    serializer = CarSerializer(cars, many=True)
    return Response(serializer.data)
```

`Car.objects.all()` with no limit. With 14+ months of car data (potentially
100k+ rows), a single `GET /api/cars/` serializes the entire table into one
JSON response. There is no `?limit=` or offset pagination.

**Recommendation:** Add DRF pagination class to this view (`LimitOffsetPagination`).

### A-5. Duplicate SQL in `ElectronicsReport` and `ElectronicsListings`

**File:** `backend/cars/views.py:1298–1397` and `1538–1612`

The chip-resolution CASE block (MacBook chip from specs, chip from title,
Intel fallback, RAM capacity fallback, CPU model_id fallback) is copy-pasted
verbatim in both views. Any change to normalization logic requires two
synchronized edits.

**Recommendation:** Extract into a named SQL fragment (string constant or
DB view).

### A-6. `build_filter_config()` fires O(N) DB queries per filter field

**File:** `backend/cars/views.py:200–345`

For each of 9 filter fields and 5 date-range options, `build_filter_config()`
calls `queryset.filter(...).count()` separately — roughly 30–40 DB round-trips
per `GET /api/cars/filtered-list/` request.

**Recommendation:** Replace with a single SQL query that computes all counts
in one pass using `COUNT(*) FILTER (WHERE ...)` syntax.

### A-7. `_brand_models` cache never invalidates

**File:** `tg_bot/bot.py:95`

```python
_brand_models: dict[str, list[str]] = {}  # module-level, never invalidated
```

New brands added to the DB won't appear in the bot until it is restarted.

**Recommendation:** Add a TTL (e.g., `time.time()` based, refresh every 6h).

### A-8. `import re` inside a hot request handler

**File:** `backend/cars/views.py:404`

```python
import re  # inside CarFilteredList.get()
```

Python caches module imports so this has negligible real cost, but it is bad
style and signals the file grew without editorial oversight.

### A-9. Unused SQLite database configuration

**File:** `backend/car_marketplace/settings.py:96–99`

```python
'sqllite': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
}
```

Unused vestigial config from the original project scaffold. Dead code.

### A-10. Scrapers have no automated scheduling except cars

**Files:** `docker-compose.devlocal.yml`

Cars scrape every hour automatically. Apartments scraper is manual-only.
The new `scraper_electronics_auto` service fixes the electronics gap (added
in the current session), but apartments still requires a manual one-shot
trigger.

**Recommendation:** Add `scraper_apartments_auto` service with a 12h loop,
mirroring `scraper_electronics_auto`.

### A-11. `CorsMiddleware` placed last in middleware stack

**File:** `backend/car_marketplace/settings.py:57`

Django-cors-headers docs require `CorsMiddleware` to be placed before
`CommonMiddleware`. Placing it last may cause CORS preflight responses to be
rejected by browsers under some conditions.

**Recommendation:** Move `'corsheaders.middleware.CorsMiddleware'` to position 1
(before `SecurityMiddleware` or after it, but definitely before `CommonMiddleware`).

---

## Findings: Security

| # | File:Line | Severity | Title |
|---|---|---|---|
| S-1 | `settings.py:30,33` | **Critical** | DEBUG=True + ALLOWED_HOSTS=* |
| S-2 | `urls.py + views.py` | **Critical** | Django API: zero authentication |
| S-3 | `backend/.env:10` | **Critical** | Insecure Django SECRET_KEY |
| S-4 | `tg_bot/.env:1` / `ops_bot/.env:1` | **Critical** | Bot tokens in plaintext .env |
| S-5 | `tg_bot/.env:8` | **High** | Trivially weak admin password |
| S-6 | `car_vision_api/main.py:34-38` | **High** | Vision API: no auth, port exposed |
| S-7 | `ml_api/main.py` (no auth) | **High** | ML API: no auth, port exposed |
| S-8 | `views.py:1075-1080` | **Medium** | Dynamic SQL construction in PATCH |
| S-9 | `ops_bot/bot.py:319` | **Medium** | Empty ALLOWED_IDS = open access |
| S-10 | `settings.py:60-62` | **Medium** | CORS misconfiguration |
| S-11 | `car_vision_api/main.py:36` | **Medium** | CORS allow_origins=* on Vision API |
| S-12 | `views.py` (multiple) | **Medium** | No rate limiting on expensive endpoints |
| S-13 | `admin_panel.py:138` | **Low** | Timing-attack-vulnerable password check |
| S-14 | `ml_api/main.py:39` | **Low** | Full request data logged |
| S-15 | `docker-compose.yml:42` | **Low** | DB credentials hardcoded in compose command |

---

### S-1 · Critical · `DEBUG=True` and `ALLOWED_HOSTS=['*']`

**File:** `backend/car_marketplace/settings.py:30,33`

```python
DEBUG = True              # line 30
ALLOWED_HOSTS = ['*']     # line 33
```

`DEBUG=True` causes Django to expose full stack traces (including local
variables, settings values, SQL queries) in HTTP error responses. Any request
that triggers a 500 error returns a detailed debugging page visible to anyone
who can reach port 8000.

`ALLOWED_HOSTS=['*']` disables Django's Host header validation, enabling
HTTP Host header injection attacks (cache poisoning, password-reset link
hijacking).

**Exploit:** Send `GET /api/cars/ HTTP/1.1` with `Host: evil.com`. Django
will include `evil.com` in any URL generation (e.g., password reset emails).

**Fix:**
```python
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,django').split(',')
```

---

### S-2 · Critical · Django API has zero authentication

**Files:** `backend/cars/urls.py`, `backend/cars/views.py`

Every URL registered in `urls.py` uses DRF `APIView` with no
`permission_classes` or `authentication_classes`. DRF's default is
`IsAuthenticatedOrReadOnly` … unless `REST_FRAMEWORK` settings override it.
Since `settings.py` has no `REST_FRAMEWORK` key at all, DRF applies its
own default: `AllowAny` with `SessionAuthentication` (which is useless
without a login flow).

Result: **anyone who can reach port 8000 can:**
- `DELETE /api/cars/<pk>/` — delete any car listing
- `PUT /api/cars/<pk>/` — overwrite any car listing
- `PATCH /api/cars/post-config/brand_ranking/` — disable any channel post
- `PATCH /api/scraper-runs/<id>/` — corrupt scraper run records
- `POST /api/scraper-runs/` — insert fake run records

Port 8000 is explicitly exposed to the host (`ports: - "8000:8000"` in
`docker-compose.devlocal.yml:28`), so any process on the host, or any LAN
host if the machine is not firewalled, can exploit this.

**Exploit:** `curl -X DELETE http://localhost:8000/api/cars/1/`

**Fix (minimal, immediate):** Add an API key middleware or restrict
`REST_FRAMEWORK` default permissions:
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication'],
}
```
For internal-only scrapers, an internal shared API key header checked in a
custom permission class is enough. Alternatively, remove `- "8000:8000"` from
the compose file so Django is only accessible on the Docker network.

---

### S-3 · Critical · Insecure Django SECRET_KEY in `.env`

**File:** `backend/car_marketplace/.env:10`

```
SECRET_KEY = 'django-insecure-l!vwu=q)k%82h!2w#hw)kfftnow)7ahs%n#8p+k@wyzju2jbb('
```

The Django-generated default "insecure" key is in use. While `.env` is
correctly excluded by `.gitignore`, the key must never reach production. Any
SECRET_KEY leak allows:
- Forging session cookies → arbitrary user impersonation
- Forging CSRF tokens
- Decrypting `django.core.signing` payloads

**Fix:** Generate a new strong key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Remove the `django-insecure-` prefix and use a key of ≥50 characters with
full entropy.

---

### S-4 · Critical · Bot tokens in plaintext `.env` files

**Files:** `tg_bot/.env:1`, `ops_bot/.env:1`

```
BOT_TOKEN=7820828967:AAFgmIybPMy7cbeyh58x6I2E6ogpsIMt3wg
OPS_BOT_TOKEN=8635280450:AAHtw-OBtOfyXFHtTh4CcZLYzT0fGSZm_Og
```

These are live Telegram bot tokens included in this audit. If this repository
or these files are shared, logged, or stored in plaintext backups, the tokens
can be used to:
- Hijack the bots entirely (send messages to all users, revoke webhooks)
- Read all messages sent to the bots (historical and future)
- Impersonate the bots to users

`car_vision_api/.env` also contains the Anthropic API key.

**Fix:** Tokens are non-sensitive data in `.env` files NOT committed to git
(confirmed — only `.env.example` is tracked). The risk is the machine/backup
level. Ensure:
1. `.env` files have `chmod 600` permissions
2. Backups encrypt these files
3. Rotate tokens immediately if any breach is suspected

**Note:** The tokens visible in this audit report are real — redact before
sharing the report externally.

---

### S-5 · High · Weak admin password

**File:** `tg_bot/.env:8`

```
ADMIN_PASSWORD=admin2024
```

`admin2024` is a trivially guessable password. Any Telegram user who finds
`@MVehicleBot` and types `/admin` will be prompted for this password and
could guess it. The admin panel can toggle channel post publishing and preview
live DB analytics data.

**Fix:** Use a random 20+ character password, or rely solely on the
`ADMIN_USER_IDS` whitelist (which is already set) and set `ADMIN_PASSWORD`
to empty/unset to disable password fallback entirely.

---

### S-6 · High · Car Vision API: unauthenticated, port exposed

**File:** `car_vision_api/main.py`, `docker-compose.devlocal.yml`

The `/analyze` endpoint accepts any multipart file upload, sends it to
Anthropic's API (paid), and returns a JSON analysis. There is no API key,
no authentication, no rate limiting, and the port is exposed to the host
(`- "8600:8600"` in compose).

**Exploit:** Anyone on the LAN can run:
```bash
curl -X POST http://192.168.x.x:8600/analyze -F "file=@any_photo.jpg"
```
This costs you money (Anthropic tokens) and could be used to probe images
without authorization.

**Fix:** Remove the host port mapping (`- "8600:8600"`) from compose so the
service is only reachable on the Docker network `car-dev-net`. Access via
Nginx proxy only. Additionally add an internal API key header check.

---

### S-7 · High · ML API: unauthenticated, port exposed

**File:** `ml_api/main.py`, `docker-compose.devlocal.yml`

Same pattern as S-6. `/predict` and `/predict2` are completely unauthenticated
and exposed on `- "8500:8500"`. No rate limiting.

**Fix:** Remove `- "8500:8500"` from compose. Only Nginx (already configured
via `/predict2` proxy) needs to reach this service.

---

### S-8 · Medium · Dynamic SQL construction in `ScraperRunDetailView`

**File:** `backend/cars/views.py:1075-1080`

```python
allowed = ('status', 'pages_scraped', 'new_records', 'total_records',
           'early_stopped', 'finished_at', 'error_msg')
fields = [(k, request.data[k]) for k in allowed if k in request.data]
set_clause = ', '.join(f"{k} = %s" for k, _ in fields)
cur.execute(
    f"UPDATE marketplace.scraper_runs SET {set_clause} WHERE id = %s",
    values,
)
```

Column names come from the hardcoded `allowed` tuple so SQL injection
via column names is not possible. However, the f-string construction of
`set_clause` is a pattern that is easy to get wrong if `allowed` ever
changes to accept user input. The `run_id` comes from URL (`<int:run_id>`)
and is safe. **Currently safe, but fragile.**

**Fix:** Use a dict of field→column mappings and always reference the
hardcoded mapping, never construct column names from user input even
transitively.

---

### S-9 · Medium · Empty `ALLOWED_IDS` means open ops bot

**File:** `ops_bot/bot.py:318-319`

```python
async def _check_access(update: Update) -> bool:
    if not ALLOWED_IDS or user_id in ALLOWED_IDS:
        return True
```

If `ADMIN_USER_IDS` is not set in `.env` (e.g., in a new deployment without
proper env setup), `ALLOWED_IDS` is an empty set, and the condition
`not ALLOWED_IDS` evaluates to `True` → every Telegram user gets access to
the ops monitoring bot.

**Fix:** Invert the logic — if `ALLOWED_IDS` is empty, deny all access and
log a warning:
```python
if not ALLOWED_IDS:
    logger.error("ADMIN_USER_IDS not configured — denying all access")
    return False
return user_id in ALLOWED_IDS
```

---

### S-10 · Medium · CORS misconfiguration

**File:** `backend/car_marketplace/settings.py:60-62` and `:57`

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

CORS allows only `localhost:3000` (the React dev server), which is correct.
But `ALLOWED_HOSTS = ['*']` means Host header injection still works at the
Django layer. Additionally, `CorsMiddleware` is at position 7 in middleware —
it must be first (or at least before `CommonMiddleware` at position 3) per the
django-cors-headers documentation.

**Fix:** Move `CorsMiddleware` to position 0. Add production origins
(`CORS_ALLOWED_ORIGINS` from env).

---

### S-11 · Medium · Car Vision API CORS: allow_origins=["*"]`

**File:** `car_vision_api/main.py:34-39`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This is a browser-accessible FastAPI service. With port 8600 exposed, any
webpage can make cross-origin requests to it (including uploading photos on
behalf of unsuspecting users).

**Fix:** Restrict to the internal Nginx origin or remove entirely (no browser
should hit this service directly).

---

### S-12 · Medium · No rate limiting on expensive endpoints

**Files:** `backend/cars/views.py:751` (`WeeklyDigest`), `:1279` (`ElectronicsReport`)

`WeeklyDigest` triggers ~150 DB queries (A-3 above). `ElectronicsReport`
runs two heavy CTE queries with `PERCENTILE_CONT`. Neither has any rate
limiting, caching, or auth. An attacker who can reach port 8000 can loop
these requests to saturate the DB.

**Fix:** Add Redis caching (`django-redis`) with a 10-minute TTL on these
analytics endpoints. Add DRF throttling (`AnonRateThrottle`).

---

### S-13 · Low · Timing-attack-vulnerable password comparison

**File:** `tg_bot/admin_panel.py:138`

```python
if text == ADMIN_PASSWORD:
```

String equality `==` is not constant-time. A determined attacker making
thousands of attempts could infer the password character by character via
timing. In practice, Telegram's network latency dwarfs any timing difference,
making this very low risk.

**Fix:** `import hmac; hmac.compare_digest(text, ADMIN_PASSWORD)`.

---

### S-14 · Low · Full request data logged in ML API

**File:** `ml_api/main.py:38-40`

```python
logger.info(f"Received prediction request (v2): {data}")
logger.info(f"Prediction result (v2): {prediction}")
```

Logs every prediction request with all fields (brand, model, year, mileage,
color, gear). This data is not individually sensitive, but may fill disk
quickly at high request rates and creates a long-lived structured log of user
activity.

---

### S-15 · Low · DB credentials hardcoded in `docker-compose.yml`

**File:** `docker-compose.yml:42`

```yaml
command: -url=jdbc:postgresql://postgres:5432/postgres
         -user=marketplace_user -password=marketplace_user
         -locations=filesystem:/flyway/sql migrate
```

And at line 117:
```yaml
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://marketplace_user:marketplace_user@postgres:5432/postgres
```

DB credentials are hardcoded in `docker-compose.yml` (which IS committed to
git per the gitignore — `.env` is excluded, but `docker-compose.yml` is not).
These appear to be the same `marketplace_user:marketplace_user` credentials
used in production.

**Fix:** Move to `${POSTGRES_PASSWORD}` env var substitution, read from
`docker-compose.yml`'s `env_file:` or passed in via CI/CD secrets.

---

## Prioritized Fix Plan

### 🔴 Critical — Fix now (before any production exposure)

| # | Action | File(s) | Effort |
|---|---|---|---|
| 1 | **Remove host port mappings for Django, ML API, Vision API** | `docker-compose.devlocal.yml:28,62,77` | 5 min |
| 2 | **Set `DEBUG=False` and real `ALLOWED_HOSTS` for production** | `settings.py:30,33` + `.env` | 10 min |
| 3 | **Add DRF authentication** — at minimum, add a `DEFAULT_PERMISSION_CLASSES` to deny anonymous write access | `settings.py` | 30 min |
| 4 | **Replace `django-insecure` SECRET_KEY** with a strong random key | `.env` | 5 min |
| 5 | **Fix `ops_bot` empty ALLOWED_IDS logic** (S-9) | `ops_bot/bot.py:319` | 5 min |
| 6 | **Change admin password** from `admin2024` to a strong random value | `tg_bot/.env` | 2 min |

> Highest-impact fix: **#1** (close exposed ports) + **#3** (add auth).
> Together they prevent external destruction of data with ~35 minutes of work.

---

### 🟡 Medium-term — Fix within 1–2 weeks

| # | Action | File(s) | Effort |
|---|---|---|---|
| 7 | **Add pagination to `CarList.get()`** | `views.py:55-62` | 1h |
| 8 | **Cache analytics endpoints** (WeeklyDigest, ElectronicsReport) with 10-min Redis TTL | `views.py` | 2h |
| 9 | **Fix CorsMiddleware position** in middleware list | `settings.py:57` | 2 min |
| 10 | **Restrict car_vision_api CORS** to internal only | `car_vision_api/main.py:36` | 5 min |
| 11 | **Move DB credentials** from `docker-compose.yml` command line to env vars | `docker-compose.yml:42,117` | 20 min |
| 12 | **Add TTL to `_brand_models` cache** in tg_bot | `tg_bot/bot.py:95` | 15 min |
| 13 | **Add apartments auto-scraper service** (mirror `scraper_electronics_auto`) | `docker-compose.devlocal.yml` | 10 min |

---

### 🟢 Long-term refactoring

| # | Action | Why | Effort |
|---|---|---|---|
| 14 | **Split `views.py`** into per-domain modules | Maintainability; currently 1644 lines | 4–8h |
| 15 | **Rewrite `WeeklyDigest` as a single SQL CTE** | Eliminates ~150 DB calls per post (A-3) | 3h |
| 16 | **Rewrite `build_filter_config()`** as a single aggregation SQL | Eliminates ~40 DB round-trips per filtered-list request | 2h |
| 17 | **Deduplicate chip-resolution SQL** in ElectronicsReport/ElectronicsListings | DRY; currently 80 lines copy-pasted | 1h |
| 18 | **Add test suite** — at minimum, integration tests for API endpoints | Catch regressions early | Ongoing |
| 19 | **Split `cars` app into `cars`, `apartments`, `electronics`** | SRP; current app name misleads | 4h |

---

## Appendix: Checked vs Unchecked

### ✅ Files read and analyzed

| File | What was checked |
|---|---|
| `backend/car_marketplace/settings.py` | DEBUG, ALLOWED_HOSTS, CORS, DATABASES, SECRET_KEY |
| `backend/car_marketplace/.env` | SECRET_KEY value, DB credentials |
| `backend/cars/views.py` | All 20+ views, SQL, auth, input validation, normalization |
| `backend/cars/models.py` | Model definitions, managed=False, app_label |
| `backend/cars/serializers.py` | `__all__` usage on write endpoints |
| `backend/cars/urls.py` | All routes, auth guards (none found) |
| `backend/requirements.txt` | Dependencies (no known CVEs spotted in Django 5.1.4, DRF) |
| `tg_bot/bot.py` | Conv handlers, input validation, API calls |
| `tg_bot/admin_panel.py` | Auth flow, password comparison, post-toggle |
| `tg_bot/.env` | Bot token, admin password |
| `ops_bot/bot.py` | Access control, open-access edge case |
| `ops_bot/.env` | Bot token |
| `ops_bot/electronics_menu.yaml` | Config structure |
| `car_vision_api/main.py` | CORS, file validation, auth |
| `car_vision_api/.env` | Anthropic key (present but redacted here) |
| `ml_api/main.py` | Endpoints, auth, logging |
| `scraper/scraper_utils.py` | RunTracker, human_sleep |
| `scraper/scrape_electronics.py` (header) | Structure, RateLimiter, save_to_db |
| `scraper/scrape_electronics_config.json` | Category URLs |
| `db/init_db.sql` | Schema init (legacy; contains DROP SCHEMA) |
| `db/updates/V10__add_new_category_tables.sql` | Tables, grants |
| `db/updates/V11__add_scraper_runs.sql` | scraper_runs table, grants |
| `db/.env` | DB credentials |
| `docker-compose.devlocal.yml` | Port mappings, env_file usage, services |
| `docker-compose.yml` | Hardcoded DB credentials in Flyway command |
| `frontend/nginx.conf` | Proxy config, missing security headers |
| `.gitignore` | Confirmed `.env` excluded; `*.txt` excludes txt files but `!requirements.txt` re-includes |
| `backend/cars/tests.py` | Effectively empty |

### ❓ Not audited / requires further investigation

| Area | Why not covered |
|---|---|
| Frontend React source (`frontend/src/`) | Out of scope for this Python/infra audit |
| Airflow DAGs (`airflow/dags/`) | Not read — Airflow is on shared DB (known issue #7 in CLAUDE.md) |
| Terraform configs | Cloud infra — different threat model |
| `scraper/run_task_scraping_olx_vehicle_v2.py` | Main cars scraper — not fully read |
| `tg_channel/analytics/*.py` | 10 analytics modules — structure only reviewed via CLAUDE.md |
| `kubernetes-manifests.yaml` | K8s deployment security (image pull policy, RBAC, secrets) |
| Dependency versions vs CVE databases | Would need `pip-audit` or `safety` scan |
| `db/updates/V1-V9` migrations | Schema evolution — not reviewed in detail |
| ML model security (`*.pkl` joblib deserialization) | Pickle deserialization RCE is a risk if model files can be tampered with |

### Notable: ML model `.pkl` deserialization risk

`ml_api/main.py:13-14` uses `joblib.load()` on model files mounted from the
host. Pickle/joblib files can execute arbitrary code on `load()`. If the
`./ml_api/models/` directory is writable by an attacker (e.g., via a
directory traversal in another service), they can achieve RCE. The current
mount is `:ro` (read-only) which mitigates but does not eliminate this if
the source directory is compromised. **Requires investigation: who can write
to `ml_api/models/` on the host?**

---

*End of DEEP_ANALYSIS.md*
