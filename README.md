# SorvPel - Controle de Estoque

Sistema de controle de produção (entradas/saídas) para fábricas de sorvetes e açaí.

## Arquitetura

```
ESP32 Terminal (LCD + Teclado)
        │ HTTP REST (WiFi)
        ▼
   Nginx (proxy)
        │
   FastAPI Backend ──── PostgreSQL
        │
   Interface Web (Bootstrap 5)
```

## Início Rápido

### Windows
```powershell
.\scripts\setup.ps1
```

### Linux / macOS
```bash
bash scripts/setup.sh
```

Acesse: `http://localhost` — Login: `admin` / `admin123`

> **IMPORTANTE:** Altere a senha do admin no primeiro acesso!

## Configuração do ESP32

Veja [esp32/README.md](esp32/README.md) para instruções detalhadas.

A `ESP32_API_KEY` está no arquivo `.env` gerado durante o setup.

## Estrutura do Projeto

```
├── backend/         # FastAPI + SQLAlchemy + Jinja2
│   ├── app/
│   │   ├── models/      # Tabelas do banco
│   │   ├── routers/     # Endpoints API + páginas web
│   │   ├── services/    # Lógica de negócio
│   │   └── templates/   # HTML Jinja2
│   └── alembic/         # Migrações de banco
├── esp32/           # Firmware Arduino C++ (PlatformIO)
├── nginx/           # Proxy reverso
├── postgres/        # Scripts de inicialização
└── scripts/         # Setup automatizado
```

## Permissões de Acesso Web

| Função  | Dashboard | Movimentos | Relatórios | Admin |
|---------|-----------|------------|------------|-------|
| admin   | ✓         | ✓          | ✓          | ✓     |
| user    | ✓         | ✓          | ✓          | ✗     |

## API para Integração

Documentação Swagger: `http://localhost/api/docs`

Endpoint principal para ESP32:
```
POST /api/v1/movements
Header: X-API-Key: <ESP32_API_KEY>

{
  "movement_type": "ENTRY",
  "operator_id": 1,
  "product_id": 2,
  "quantity": 50.0,
  "shift": "MORNING",
  "device_id": "ESP32-LINHA-A",
  "recorded_at": "2026-05-05T08:30:00"
}
```

## Deploy em Nuvem

O sistema já está preparado para cloud. Basta:
1. Alterar `SERVER_URL` no `config.h` do ESP32 para o domínio/IP do servidor
2. Configurar variáveis de ambiente na plataforma cloud (Railway, Render, DigitalOcean, etc.)
3. Executar `docker compose up` no servidor

## Tecnologias

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **Frontend:** Jinja2, Bootstrap 5, Chart.js
- **Banco:** PostgreSQL 16
- **Container:** Docker Compose
- **ESP32:** Arduino C++, PlatformIO, ArduinoOTA
