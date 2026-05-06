# Simulador de Terminal ESP32

Simula o terminal físico ESP32 em um container Docker com interface curses no terminal.
Replica fielmente a máquina de estados de `esp32/src/menu.cpp` e realiza chamadas HTTP reais ao backend.

## Pré-requisitos

- Stack principal rodando: `docker compose up -d`
- Banco populado com operadores e produtos: `docker compose run --rm backend python scripts/seed_data.py`

## Iniciando o simulador

```powershell
# Build + executa o simulador (interativo)
docker compose --profile sim run --rm esp32-sim
```

O simulador conecta em `http://nginx` (rede interna Docker) usando a mesma `ESP32_API_KEY` do `.env`.

## Interface

```
 ESP32 Terminal Simulator — SorvPel

┌──────────────────┐   Estado : IDLE
│ LCD 16x2         │   Turno  : MORNING
│ SorvPel Estoque  │   Device : SIM-TERMINAL-01
│ Pressione # ini  │   Server : http://nginx
└──────────────────┘
                       Teclas:
                         0-9            Digitos
                         Enter / #      Confirmar (#)
                         Esc / *        Cancelar / Voltar (*)
                         Seta UP / A    Cima  (A)
                         Seta DN / B    Baixo (B)
                         S              Modo Scanner (codigo)
                         R              Recarregar dados da API
                         Q              Sair do simulador

─────────────────── Log chamadas API ──────────────────
[09:12:01] GET /api/v1/operators -> 3 registros
[09:12:01] GET /api/v1/products  -> 5 registros
```

## Mapeamento de teclas (teclado → teclado físico 4x4)

| Teclado PC         | Tecla ESP32 | Função                      |
|--------------------|-------------|---------------------------  |
| `Enter` ou `#`     | `#`         | Confirmar / Selecionar       |
| `Esc` ou `*`       | `*`         | Cancelar / Voltar            |
| Seta ↑ ou `A`/`a`  | `A`         | Rolar para cima              |
| Seta ↓ ou `B`/`b`  | `B`         | Rolar para baixo             |
| `0`–`9`            | `0`–`9`     | Digitar quantidade           |
| `S`                | —           | Ativar modo scanner          |
| `R`                | —           | Recarregar dados da API      |
| `Q`                | —           | Encerrar o simulador         |

## Fluxo de uso (exemplo de registro de entrada)

```
IDLE → # → SELECT_OPERATOR
  ↑/↓ para navegar → # para confirmar operador
→ SELECT_TYPE
  1 (entrada) ou 2 (saída)
→ SELECT_PRODUCT
  ↑/↓ para navegar → # para confirmar produto
→ ENTER_QUANTITY
  Digitar quantidade (ex: 10) → # para confirmar
→ CONFIRM
  # para enviar → POST /api/v1/movements
→ SUCCESS
  Qualquer tecla → IDLE
```

## Modo Scanner

Pressione `S` para entrar no modo scanner. Digite o código e pressione `Enter`:

- Em `SELECT_OPERATOR`: informe o `badge_code` do operador
- Em `SELECT_PRODUCT`: informe o nome exato do produto

`Esc` cancela o modo scanner sem enviar.

## Variáveis de ambiente

Configuráveis em `.env` ou na linha de comando:

| Variável        | Padrão              | Descrição                        |
|-----------------|---------------------|----------------------------------|
| `ESP32_API_KEY` | —                   | Chave de autenticação (obrigatório) |
| `SIM_DEVICE_ID` | `SIM-TERMINAL-01`   | Identificador do dispositivo     |
| `MENU_IDLE_MS`  | `60000`             | Timeout de inatividade (ms)      |

## Rebuild após alterações

```powershell
docker compose --profile sim build esp32-sim
docker compose --profile sim run --rm esp32-sim
```

## Diferenças em relação ao hardware real

| Característica     | Hardware ESP32       | Simulador                     |
|--------------------|----------------------|-------------------------------|
| Display            | LCD I2C 16×2 físico  | Caixa no terminal              |
| Teclado            | Matriz 4×4 GPIO      | Teclado do PC                 |
| Scanner            | Serial UART          | Input de texto (`S`)          |
| Horário            | NTP sincronizado     | Relógio do container Docker   |
| OTA                | Firmware real        | Não implementado              |
| WiFi               | Rede sem fio         | Rede Docker interna           |
