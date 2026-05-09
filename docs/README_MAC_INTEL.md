# Wally Trader — Guía para Mac Intel (x86_64)

> **Compatibilidad:** macOS 12 Monterey / 13 Ventura / 14 Sonoma · Intel x86_64  
> **Probado en:** iMac Intel, macOS 13.7.8, Mayo 2026

---

## Instalación rápida

```bash
# Clonar el repo con submodules
git clone --recurse-submodules https://github.com/sasasamaes/wally-trader.git
cd wally-trader

# Instalar con el script para Intel
bash scripts/install-mac-intel.sh
```

El script hace todo automáticamente. Tarda 20-40 minutos en Mac Intel (compila algunos paquetes desde source).

---

## Inicio diario

```bash
bash ~/wally-trader/scripts/start.sh
```

O con el alias (se configura automáticamente):

```bash
wally-start
```

Esto lanza TradingView Desktop con CDP habilitado + Hermes gateway en secuencia.

---

## Qué funciona en Mac Intel x86

| Componente | Estado | Notas |
|---|---|---|
| Hermes Agent | ✅ Funciona | Instalar con curl script de Nous Research |
| TradingView MCP | ✅ Funciona | 78 herramientas disponibles |
| CDP port 9222 | ✅ Funciona | Lanzar TV con `--remote-debugging-port=9222` |
| Telegram Gateway | ✅ Funciona | Requiere pairing inicial |
| Screenshot de chart | ✅ Funciona | vía `mcp_tradingview_capture_screenshot` |
| Análisis de indicadores | ✅ Funciona | Lee Pine Script values en tiempo real |
| setup.sh | ✅ Funciona | Instala todas las deps Python automáticamente |
| OpenCode CLI | ⚠️ No probado | Puede tener problemas de compatibilidad x86 |

---

## Prerequisitos detallados

### 1. Xcode Command Line Tools

```bash
xcode-select --install
# Verificar:
xcode-select -p
# Debe mostrar: /Library/Developer/CommandLineTools
```

### 2. Node.js LTS ≥18

```bash
brew install node
node --version  # debe ser v18+
```

> ⚠️ En macOS 13 Intel puede tardar 15-30 minutos compilando desde source.

### 3. Python 3.9+

```bash
brew install python@3.13
python3 --version
```

> Usar `python@3.13` — `python3` intenta instalar 3.14 que requiere compilación larga.

### 4. Hermes Agent

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes --version
```

---

## Configuración de TradingView Desktop

### Lanzar con puerto CDP

```bash
pkill -f TradingView
sleep 3
open -a "TradingView" --args --remote-debugging-port=9222
sleep 10
# Verificar:
curl http://localhost:9222/json
```

Si ves JSON con `tradingview.com`, la conexión está activa.

> ⚠️ **Importante:** TradingView no recuerda este flag. Debés lanzarlo así cada vez que reiniciés el sistema. El script `start.sh` lo hace automáticamente.

### Agregar al config de Hermes

```bash
cat >> ~/.hermes/config.yaml << 'EOF'

mcp_servers:
  tradingview:
    command: node
    args:
      - /Users/TU_USUARIO/wally-trader/tradingview-mcp/src/server.js
EOF
```

Reemplazá `TU_USUARIO` con tu usuario (verificar con `echo $USER`).

### Habilitar las 78 herramientas

```bash
hermes tools
# → Configure MCP server tools
# → Confirmar todas con ENTER
```

---

## Configuración de Hermes

### Proveedor LLM recomendado

**OVHcloud gpt-oss-120b** (gratuito, 131K contexto, funciona bien para trading):

1. Registrarse en https://www.ovhcloud.com/
2. Generar token OAuth: https://kepler.ai.cloud.ovh.net/v1/oauth/ovh/authorize?iam_action=publicCloudProject:ai:endpoints/call
3. Verificar que funciona:

```bash
curl -s https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"hola"}]}'
```

4. Configurar en Hermes:

```bash
hermes model
# → custom (direct API)
# URL: https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
# API key: TU_TOKEN_JWT
# Model: gpt-oss-120b
# Context: dejar en blanco
```

### Alternativas

| Proveedor | Costo | Modelo | Comando |
|---|---|---|---|
| OVHcloud | Gratis | gpt-oss-120b | custom endpoint |
| OpenRouter | $5 créditos | deepseek/deepseek-chat | `hermes config set OPENROUTER_API_KEY TU_KEY` |
| DeepSeek | $2 créditos | deepseek-chat | `hermes config set DEEPSEEK_API_KEY TU_KEY` |
| Groq | Gratis (rate limit) | llama-3.3-70b-versatile | custom endpoint |

**Verificar Groq antes de configurar:**
```bash
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer TU_GROQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hola"}]}'
```

---

## Configuración de Telegram Bot

```bash
# 1. Crear bot en @BotFather → /newbot
# 2. Configurar token:
hermes config set TELEGRAM_BOT_TOKEN TU_TOKEN_BOTFATHER

# 3. Iniciar gateway:
cd ~/wally-trader && source venv/bin/activate
hermes gateway run --replace

# 4. En Telegram, escribirle al bot → recibirás un código de pairing
# 5. En otra terminal:
hermes pairing approve telegram TU_CODIGO

# 6. En Telegram: /sethome
```

---

## Uso desde Telegram

Una vez configurado, podés pedirle al bot:

```
# Screenshot del chart
toma un screenshot del chart actual de TradingView

# Análisis matutino completo
lee el archivo ~/wally-trader/MORNING_PROMPT.md y ejecuta el análisis matutino

# Indicadores en tiempo real
dame los valores actuales de todos los indicadores visibles

# Watchlist
muéstrame todos los símbolos de mi watchlist con precios

# Sistema Neptune
analiza el chart actual con el sistema Neptune y dame señales de entrada

# Riesgo
calcula el riesgo para una entrada en el símbolo actual
```

> **Tip:** Si el bot usa el browser en vez del MCP local, pedile explícitamente:  
> `usa mcp_tradingview_capture_screenshot para tomar el screenshot`

---

## Solución de problemas

### TradingView no conecta (CDP failed)

```bash
pkill -f TradingView
sleep 3
open -a "TradingView" --args --remote-debugging-port=9222
sleep 10
curl http://localhost:9222/json
```

### Hermes usa proveedor equivocado

```bash
pkill -f hermes
rm -rf ~/.hermes/sessions/*
cd ~/wally-trader && source venv/bin/activate
hermes gateway run --replace
# En Telegram: /reset
```

### MCP de TradingView no aparece

```bash
grep -A5 "mcp_servers" ~/.hermes/config.yaml
```

Si está vacío, agregarlo manualmente (ver sección de configuración arriba).

### Error de cuota LLM

| Error | Causa | Solución |
|---|---|---|
| HTTP 429 Gemini | 250 req/día agotadas | Esperar 24h o activar billing |
| HTTP 402 OpenRouter | Sin créditos | Recargar en openrouter.ai/settings/credits |
| HTTP 402 DeepSeek | Sin créditos | Recargar en platform.deepseek.com |
| HTTP 403 OVHcloud | Token JWT expirado | Regenerar en kepler.ai.cloud.ovh.net |

### El token JWT de OVHcloud expiró

Ir a: https://kepler.ai.cloud.ovh.net/v1/oauth/ovh/authorize?iam_action=publicCloudProject:ai:endpoints/call  
Autenticarse → copiar nuevo token → `hermes model` → actualizar API key.

---

## Diferencias ARM64 vs Intel x86

| | Apple Silicon (M1/M2/M3) | Intel x86_64 |
|---|---|---|
| Homebrew prefix | `/opt/homebrew` | `/usr/local` |
| Soporte Homebrew | Tier 1 (pleno) | Tier 3 (warnings normales) |
| Tiempo instalación | 5-10 min | 20-40 min |
| Compilación paquetes | Bottles precompilados | Puede compilar desde source |
| TradingView Desktop | App Universal ✅ | App Universal ✅ |
| CDP port 9222 | Igual ✅ | Igual ✅ |
| Hermes Agent | Funciona ✅ | Funciona ✅ |
| TradingView MCP | Funciona ✅ | Funciona ✅ |

---

## Archivos incluidos en este paquete

```
wally-trader-x86/
├── README_MAC_INTEL.md          ← Esta guía
├── scripts/
│   ├── install-mac-intel.sh     ← Instalador automático
│   └── start.sh                 ← Script de inicio diario
└── docs/
    └── hermes-config-template.yaml  ← Template de configuración
```

---

*Probado y documentado en Mayo 2026 · iMac Intel · macOS 13.7.8 Ventura*
