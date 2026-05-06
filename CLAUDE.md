# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Start the full stack
```powershell
# Windows — first time
.\scripts\setup.ps1

# Subsequent runs
docker compose up -d

# With hot reload (dev mode via override)
docker compose up
```

> **Windows note:** Port 80 is often blocked. The `.env` uses `NGINX_PORT=8080` by default. Access at `http://localhost:8080`.

> **bcrypt note:** `requirements.txt` pins `bcrypt==3.2.2` to stay compatible with `passlib==1.7.4`. Do not upgrade bcrypt past 3.x without also upgrading passlib.

> **DATABASE_URL note:** `?ssl=disable` is appended in `docker-compose.yml` because asyncpg defaults to SSL which fails inside Docker's internal network.

### Backend only (local, no Docker)
```powershell
cd backend
pip install -r requirements.txt
# Requires DATABASE_URL env var pointing to a running postgres
uvicorn app.main:app --reload
```

### Database migrations
```powershell
# Inside Docker
docker compose run --rm backend alembic upgrade head

# New migration
docker compose run --rm backend alembic revision --autogenerate -m "description"
```

### Seed initial data
```powershell
docker compose run --rm backend python scripts/seed_data.py
```

### View logs
```powershell
docker compose logs -f backend
docker compose logs -f postgres
```

### Rebuild after dependency changes
```powershell
docker compose build backend
```

### ESP32 firmware
```bash
# Requires PlatformIO CLI or VS Code PlatformIO extension
cd esp32
pio run -t upload              # compile + flash via USB
pio device monitor             # serial monitor
pio run -t upload --upload-port 192.168.x.x   # OTA push
```

## Architecture

### Backend (`backend/app/`)

Request flow: **Nginx → FastAPI → SQLAlchemy async → PostgreSQL**

Two authentication paths coexist:
- **Web users** (browser): JWT stored in HttpOnly cookie `access_token`. Dependencies: `require_user()` → `require_admin()` in `dependencies.py`.
- **ESP32 terminals**: static `X-API-Key` header validated by `verify_esp32_key()` in `dependencies.py`. The key is set via `ESP32_API_KEY` env var.

Routes are split into two categories in `routers/`:
- `web.py` — returns `TemplateResponse` (Jinja2 HTML pages, one function per page)
- All others (`movements.py`, `operators.py`, etc.) — return JSON for the REST API under `/api/v1/`

`report_service.py` handles all complex multi-join queries. Adding new report filters: modify `get_movements_query()` there, not in the router.

### Database schema key decisions
- `inventory_movements` has two timestamps: `recorded_at` (from ESP32 device clock, NTP-synced) and `created_at` (server receipt). Always use `recorded_at` for business logic.
- `operators.badge_code` is the identifier typed/scanned on the ESP32 — it is NOT the primary key.
- Shift (`MORNING`/`AFTERNOON`/`NIGHT`) is sent by the ESP32, derived from its local time in `api_client.cpp:currentShift()`.

### ESP32 Firmware (`esp32/src/`)

The firmware is a finite state machine in `menu.cpp`. All state transitions are in `Menu::handleKey()` and `Menu::handleScanner()`. The `render()` method is called every loop iteration and dispatches to per-state render functions.

Key flow: `main.cpp:setup()` connects WiFi → OTA check → loads operators/products from API → `menu.begin()`. The `loop()` calls `ArduinoOTA.handle()` first, then reads keypad or scanner and delegates to `menu.handleKey()` / `menu.handleScanner()`.

Scanner support is compile-time gated: uncomment `#define SCANNER_ENABLED` in `config.h`. When enabled, `scanner.available()` is checked before `keypad.read()` in `loop()`.

### Configuration

All secrets are in `.env` (git-ignored). The template is `.env.example`. The ESP32 config is hardcoded in `esp32/src/config.h` (also git-ignored via `config_local.h` pattern — keep credentials out of `config.h` if committing).

The `docker-compose.override.yml` activates automatically in dev: mounts the full `backend/` directory for hot reload and shifts Nginx to port 8080.

## Key File Locations

| What | Where |
|------|-------|
| DB models | `backend/app/models/` |
| API route definitions | `backend/app/routers/` |
| Complex report queries | `backend/app/services/report_service.py` |
| Auth logic (JWT, bcrypt) | `backend/app/services/auth_service.py` |
| Dependency injection (auth guards) | `backend/app/dependencies.py` |
| HTML templates | `backend/app/templates/` |
| Alembic migration | `backend/alembic/versions/001_initial_schema.py` |
| ESP32 state machine | `esp32/src/menu.cpp` |
| ESP32 HTTP client | `esp32/src/api_client.cpp` |
| ESP32 credentials/pins | `esp32/src/config.h` |
