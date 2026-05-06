#!/bin/bash
# Hook SessionStart: carga contexto de trading al iniciar Claude en este proyecto
# Output format: JSON con hookSpecificOutput.additionalContext para inyectar al modelo

HORA_CR=$(TZ='America/Costa_Rica' date +%H)
HORA_CR=${HORA_CR#0}
HORA_STR=$(TZ='America/Costa_Rica' date +%H:%M)

# ─────── Profile detection ───────
PROFILE_SCRIPT="$(dirname "$0")/profile.sh"
PROFILE=""
if [[ -x "$PROFILE_SCRIPT" ]]; then
  PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "")"
  if bash "$PROFILE_SCRIPT" stale >/dev/null 2>&1; then
    PROFILE_STALE_MSG="
⚠️  PROFILE STALE o no seteado. Último valor: ${PROFILE:-<ninguno>}
   Ejecuta /profile ftmo  o  /profile retail  para confirmar hoy."
  fi
fi
# ─────────────────────────────────

# ─────── Notion MCP detection (opcional) ──
NOTION_ENABLED=0
NOTION_STATUS_LINE=""
ENV_FILE="$(dirname "$0")/../.env"
if [[ -f "$ENV_FILE" ]]; then
  NOTION_RETAIL_DB=$(grep -E '^NOTION_RETAIL_DB_ID=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d ' "')
  NOTION_FTMO_DB=$(grep -E '^NOTION_FTMO_DB_ID=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d ' "')
  if [[ -n "$NOTION_RETAIL_DB" && -n "$NOTION_FTMO_DB" ]]; then
    NOTION_ENABLED=1
    NOTION_STATUS_LINE="**Notion MCP:** ✅ Habilitado — DBs configuradas (retail + ftmo). Dual-write activado para /journal, /order, /sync, /trades, /challenge."
  else
    NOTION_STATUS_LINE="**Notion MCP:** ⬜ Opcional (no configurado). Para activar ver docs/NOTION_SETUP.md"
  fi
else
  NOTION_STATUS_LINE="**Notion MCP:** ⬜ Opcional (no configurado). Para activar ver docs/NOTION_SETUP.md"
fi
# ─────────────────────────────────

# Determinar saludo según hora
if [ "$HORA_CR" -ge 5 ] 2>/dev/null && [ "$HORA_CR" -le 9 ] 2>/dev/null; then
    SALUDO="Buenos días — ventana de trading activa"
elif [ "$HORA_CR" -ge 10 ] 2>/dev/null && [ "$HORA_CR" -le 16 ] 2>/dev/null; then
    SALUDO="Sesión en curso"
elif [ "$HORA_CR" -ge 17 ] 2>/dev/null && [ "$HORA_CR" -le 20 ] 2>/dev/null; then
    SALUDO="Cierre de sesión — hora de journal"
else
    SALUDO="Fuera de ventana — planeando o revisando"
fi

# Leer capital actual de memoria según profile
CAP_LINE=""
if [[ "$PROFILE" == "ftmo" ]]; then
  CURVE="$(dirname "$0")/../profiles/ftmo/memory/equity_curve.csv"
  if [[ -f "$CURVE" && $(wc -l < "$CURVE") -gt 1 ]]; then
    LAST_EQ="$(tail -n1 "$CURVE" | cut -d',' -f2)"
    CAP_LINE="**Capital actual (FTMO):** \$$LAST_EQ"
  else
    CAP_LINE="**Capital actual (FTMO):** \$10,000 (inicial — corre /equity <valor> para actualizar)"
  fi
elif [[ "$PROFILE" == "retail" ]]; then
  MEMORY_DIR="$HOME/.claude/projects/<project-path-encoded>/memory"
  TRADING_LOG="$MEMORY_DIR/trading_log.md"
  CAP="13.63"
  if [ -f "$TRADING_LOG" ]; then
    FOUND=$(grep -oE 'Capital (actual|running|final)[: ]+\$[0-9]+\.[0-9]+' "$TRADING_LOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+\.[0-9]+')
    [ -n "$FOUND" ] && CAP="$FOUND"
  fi
  CAP_LINE="**Capital actual (RETAIL):** \$$CAP"
else
  CAP_LINE="**Capital actual:** (profile no detectado)"
fi

# Construir contexto como JSON
PROFILE_HEADER="## CONTEXTO TRADING SESSION"
if [[ -n "$PROFILE" ]]; then
  PROFILE_HEADER="## CONTEXTO TRADING SESSION — Profile: [$PROFILE]"
fi
STALE_MSG_OUTPUT=""
if [[ -n "${PROFILE_STALE_MSG:-}" ]]; then
  STALE_MSG_OUTPUT="$PROFILE_STALE_MSG"
fi

CONTEXT=$(cat <<EOF
$PROFILE_HEADER
$STALE_MSG_OUTPUT

**Hora CR:** $HORA_STR — $SALUDO
$CAP_LINE
**Símbolo:** BTCUSDT.P (BingX)
**Estrategia activa:** Mean Reversion 15m (según régimen)
$NOTION_STATUS_LINE

## Comandos rápidos disponibles
- /morning — análisis matutino completo (17 fases)
- /validate — validar entry actual (4 filtros)
- /regime — detectar régimen mercado
- /risk — calcular position sizing 2%
- /status — estado completo sistema
- /chart — redibujar niveles en TV
- /journal — cerrar día / log trade
- /review — review semanal
- /levels — niveles técnicos ahora
- /alert — configurar alerta custom
- /backtest — probar estrategia

## Reglas sagradas
1. Max 2% riesgo por trade
2. Max 3 trades/día
3. 2 SLs → STOP día
4. Nunca mover SL en contra
5. Leverage cap profile-aware (retail/quantfury 10x, bitunix 20x, ftmo/fundingpips per-provider)
6. 4/4 filtros obligatorios

## Agentes disponibles (auto-invocación)
morning-analyst, trade-validator, regime-detector, chart-drafter, risk-manager, journal-keeper, backtest-runner
EOF
)

# Output JSON con additionalContext para inyectar en el modelo
jq -n \
    --arg ctx "$CONTEXT" \
    '{
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": $ctx
        }
    }'
