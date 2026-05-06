# ESP32 — Terminal de Fábrica SorvPel

## Pré-requisitos

- [PlatformIO](https://platformio.org/) (extensão VS Code ou CLI)
- ESP32 DevKit com LCD 16x2 I2C + teclado matricial 4x4

## Configuração

1. Abra a pasta `esp32/` no VS Code com PlatformIO
2. Edite `src/config.h` com suas credenciais:
   ```c
   #define WIFI_SSID     "SUA_REDE_WIFI"
   #define WIFI_PASSWORD "SUA_SENHA"
   #define SERVER_URL    "http://IP_DO_SERVIDOR"
   #define API_KEY       "VALOR_DE_ESP32_API_KEY_NO_ARQUIVO_.env"
   #define DEVICE_ID     "ESP32-LINHA-A"   // nome único por terminal
   ```

## Conexões de Hardware

### LCD 16x2 I2C
| LCD    | ESP32   |
|--------|---------|
| VCC    | 3.3V    |
| GND    | GND     |
| SDA    | GPIO 21 |
| SCL    | GPIO 22 |

### Teclado Matricial 4x4
| Teclado | Pino config.h | GPIO padrão |
|---------|---------------|-------------|
| R1      | KP_ROW1       | 13          |
| R2      | KP_ROW2       | 12          |
| R3      | KP_ROW3       | 14          |
| R4      | KP_ROW4       | 27          |
| C1      | KP_COL1       | 26          |
| C2      | KP_COL2       | 25          |
| C3      | KP_COL3       | 33          |
| C4      | KP_COL4       | 32          |

### Scanner de Código de Barras (opcional)
- Descomente `#define SCANNER_ENABLED` em `config.h`
- Conecte TX do scanner ao GPIO 16 (RX2 do ESP32)

## Como usar o teclado

| Tecla | Função        |
|-------|---------------|
| A     | Subir na lista |
| B     | Descer na lista |
| #     | Confirmar     |
| *     | Cancelar/Voltar |
| 0-9   | Digitar quantidade |

## Compilar e Gravar

```bash
# Via CLI
pio run -t upload

# Via VS Code: botão "Upload" na barra inferior do PlatformIO
```

## OTA (Atualização sem fio)

### Push via PlatformIO
```bash
pio run -t upload --upload-port IP_DO_ESP32
```

### Pull automático
O terminal verifica automaticamente ao ligar se há firmware novo no servidor.
Para fazer upload de novo firmware:
1. Acesse o painel web como admin
2. Vá em API: `POST /api/v1/ota/upload`
3. Informe a versão (ex: `1.1.0`) e faça upload do arquivo `.bin`
4. Na próxima inicialização, o ESP32 baixará e aplicará o update automaticamente.

## Fluxo de Operação

```
Ligar → Conectar WiFi → Verificar OTA → Carregar dados
  ↓
[Tela Inicial: "Pressione #"]
  ↓ tecla #
[Selecionar Operador] (A/B scroll, # confirma)
  ↓
[1=Entrada  2=Saída]
  ↓
[Selecionar Produto] (A/B scroll, # confirma)
  ↓
[Digitar Quantidade] (0-9, # confirma, * apaga)
  ↓
[Confirmar] (# envia, * cancela)
  ↓
[Enviado! / Erro]
  ↓ volta ao início
```
