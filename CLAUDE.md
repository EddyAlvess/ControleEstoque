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

### ESP32 simulator (Docker)
```powershell
# Start simulator alongside the stack
docker compose --profile sim up

# Simulator only
docker compose --profile sim up esp32-sim
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
- All others (`movements.py`, `operators.py`, `categories.py`, etc.) — return JSON for the REST API under `/api/v1/`

`report_service.py` handles all complex multi-join queries. Adding new report filters: modify `get_movements_query()` there, not in the router.

### Database schema key decisions
- `inventory_movements` has two timestamps: `recorded_at` (from ESP32 device clock, NTP-synced) and `created_at` (server receipt). Always use `recorded_at` for business logic.
- `operators.badge_code` is the identifier typed/scanned on the ESP32 — it is NOT the primary key.
- Shifts are stored in the `shifts` table (dynamic, not hardcoded). When a movement is recorded the server auto-detects shift by hour via `_detect_shift()` in `routers/movements.py`. Shift `name` is the stored identifier; `label` is the display label.
- Products belong to one `Category` (nullable FK). Categories are managed via `/admin/categories`.
- `company_settings` is a singleton table (always id=1). It holds `company_name`, `logo_path` (URL served via `/static/logos/`), and `logo_icon` (Bootstrap Icon class). Loaded at startup into `settings_cache` in `services/settings_service.py` and injected into every template as `cs`.

### Company branding / theme
`CompanySettings` (migration 005) is a singleton holding the company name and logo. At startup (`lifespan()` in `main.py`) the record is loaded into a module-level `_SettingsCache` object. Every Jinja2 template context receives it via the `cs` key injected in `_ctx()` in `routers/web.py`. On save (`PUT /api/v1/settings`), the cache is updated in-memory — no server restart needed.

Logo images are stored in `backend/app/static/logos/` and served by FastAPI's `StaticFiles` mount at `/static`. In Docker deployments add a bind-mount for this directory to persist logos across container restarts.

### Template safety rule
**Never pass user-entered strings directly into onclick attributes.** All admin templates (products, categories, shifts) embed their data as `const DATA = {{ items | tojson }};` in a script block and pass only integer IDs to onclick handlers (e.g. `onclick="openEdit({{ item.id }})"`). This avoids HTML attribute breakage when names contain quotes or special characters.

Routes that render admin templates must convert SQLAlchemy ORM objects to plain dicts before passing them to Jinja2 if the template uses `| tojson`.

### Report filter forms
Report filter forms intercept `submit` with JavaScript to strip empty-string values before building the query string. This prevents FastAPI from receiving `""` for `int | None` query parameters (which raises a 422 parse error). See `filterForm` submit handler in `templates/reports.html`.

### ESP32 Firmware (`esp32/src/`)

The firmware is a finite state machine in `menu.cpp`. All state transitions are in `Menu::handleKey()` and `Menu::handleScanner()`. The `render()` method is called every loop iteration and dispatches to per-state render functions.

Key flow: `main.cpp:setup()` connects WiFi → OTA check → loads operators/products from API → `menu.begin()`. The `loop()` calls `ArduinoOTA.handle()` first, then reads keypad or scanner and delegates to `menu.handleKey()` / `menu.handleScanner()`.

Scanner support is compile-time gated: uncomment `#define SCANNER_ENABLED` in `config.h`. When enabled, `scanner.available()` is checked before `keypad.read()` in `loop()`.

The simulator (`esp32-sim/simulator.py`) mirrors the ESP32 state machine in Python using `curses`. It uses a 20×4 LCD display simulation and fetches operators, products and shifts dynamically from the API.

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
| Company branding cache | `backend/app/services/settings_service.py` |
| Company settings model | `backend/app/models/settings.py` |
| Company settings API | `backend/app/routers/settings.py` |
| Dependency injection (auth guards) | `backend/app/dependencies.py` |
| HTML templates | `backend/app/templates/` |
| Admin theme template | `backend/app/templates/admin/settings.html` |
| Static files (logos) | `backend/app/static/logos/` |
| Alembic migrations | `backend/alembic/versions/` |
| ESP32 state machine | `esp32/src/menu.cpp` |
| ESP32 HTTP client | `esp32/src/api_client.cpp` |
| ESP32 credentials/pins | `esp32/src/config.h` |
| ESP32 Python simulator | `esp32-sim/simulator.py` |

## Web Portal Pages

| URL | Description | Auth |
|-----|-------------|------|
| `/dashboard` | KPIs do dia + estoque por categoria (drilldown) + últimos registros | user |
| `/reports` | Filtros avançados + paginação + export CSV | user |
| `/admin/operators` | CRUD operadores | admin |
| `/admin/products` | CRUD produtos com categoria | admin |
| `/admin/categories` | CRUD categorias | admin |
| `/admin/users` | CRUD usuários web | admin |
| `/admin/shifts` | CRUD turnos (detecção automática por hora) | admin |
| `/admin/settings` | Tema: nome da empresa + logotipo | admin |

## REST API Summary

| Prefix | Description |
|--------|-------------|
| `/api/v1/auth` | Login/logout |
| `/api/v1/movements` | Registrar entradas/saídas (ESP32 + web) |
| `/api/v1/operators` | Listagem e CRUD (ESP32 usa GET) |
| `/api/v1/products` | Listagem e CRUD (ESP32 usa GET) |
| `/api/v1/categories` | Listagem e CRUD |
| `/api/v1/shifts` | Listagem e CRUD |
| `/api/v1/reports/summary` | Totais agrupados por produto |
| `/api/v1/reports/stock/category` | Saldo acumulado por categoria |
| `/api/v1/reports/stock/product` | Saldo acumulado por produto (requer `category_id`) |
| `/api/v1/reports/export` | Download CSV com filtros |
| `/api/v1/ota` | OTA firmware update (ESP32) |
| `/api/v1/settings` | GET/PUT configurações de tema (nome, ícone) |
| `/api/v1/settings/logo` | POST upload / DELETE logotipo |
| `/static/logos/` | Arquivos de logotipo servidos pelo FastAPI StaticFiles |
