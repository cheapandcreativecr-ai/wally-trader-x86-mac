#!/bin/bash
# Hook UserPromptSubmit: detecta palabras peligrosas y alerta + valida helpers críticos

PROMPT_INPUT=$(cat)

# ── Sanity check de helpers Python (silencioso si OK, ruidoso si rotos) ───
SCRIPTS_DIR="$(dirname "$0")"
TEST_FILE="$SCRIPTS_DIR/test_pdf_helpers.py"
TEST_STAMP="/tmp/.wally_helpers_last_check"
# Solo correr una vez por hora (no en cada prompt)
if [[ -f "$TEST_FILE" ]]; then
    last=$(stat -c %Y "$TEST_STAMP" 2>/dev/null || stat -f %m "$TEST_STAMP" 2>/dev/null || echo 0)
    now=$(date +%s)
    if (( now - last > 3600 )); then
        if ! python3 "$TEST_FILE" >/tmp/wally_helpers_test.log 2>&1; then
            cat <<HEALTH >&2

⚠️ ═══ HELPERS PDF ROTOS ═══
test_pdf_helpers.py FAILED — adx_calc / trailing_stop / backtest_split inestables.
Log: /tmp/wally_helpers_test.log
NO uses /trail, /regime, /backtest hasta validar.
══════════════════════════════

HEALTH
        fi
        touch "$TEST_STAMP"
    fi
fi
# ─────────────────────────────────────────────────────────────────────────

# Palabras clave de auto-sabotaje
if echo "$PROMPT_INPUT" | grep -qiE "(arriesgar (todo|mucho)|all.in|aumentar leverage|saltar.*filtro|entrar sin|mover el sl|recuperar (rapido|rápido)|subir el leverage|más apalancamiento)"; then
    cat <<EOF >&2

⚠️ ═══ ALERTA DE AUTO-SABOTAJE ═══

Detecté lenguaje de riesgo elevado en tu prompt.

Recordatorio de reglas sagradas:
  • Max 2% riesgo por trade (regla matemática)
  • Nunca mover SL en dirección contraria
  • Nunca subir leverage arriba de 10x
  • Nunca saltarse los 4 filtros
  • Nunca operar para "recuperar" pérdidas

Si realmente quieres romper una regla, detente 5 minutos.
Pregúntate: ¿qué diría mi yo del mes pasado?

Este mensaje NO bloquea tu acción — solo te advierte.

══════════════════════════════

EOF
fi

exit 0
