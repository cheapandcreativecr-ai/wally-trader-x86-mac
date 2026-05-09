#!/bin/bash
# =============================================================================
# Wally Trader — Script de inicio diario para Mac Intel
# Lanza TradingView con CDP + Hermes gateway en secuencia
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
info() { echo -e "${BLUE}▶${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Wally Trader — Inicio del día     ║"
echo "╚══════════════════════════════════════╝"
echo ""

INSTALL_DIR="$HOME/wally-trader"

# ─── Verificar que existe el repo ────────────────────────────────────────────
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}✗${NC} No se encontró ~/wally-trader. Ejecutá primero install-mac-intel.sh"
    exit 1
fi

# ─── Paso 1: Lanzar TradingView con CDP ──────────────────────────────────────
info "Lanzando TradingView Desktop con CDP..."
pkill -f TradingView 2>/dev/null || true
sleep 2
open -a "TradingView" --args --remote-debugging-port=9222

info "Esperando que TradingView cargue (15 segundos)..."
sleep 15

# Verificar conexión CDP
if curl -s http://localhost:9222/json | grep -q "tradingview.com"; then
    log "TradingView conectado en puerto 9222"
else
    warn "TradingView no responde en puerto 9222 todavía — puede seguir cargando"
    warn "Si falla, esperá unos segundos más y verificá con: curl http://localhost:9222/json"
fi

# ─── Paso 2: Activar venv y lanzar gateway ───────────────────────────────────
info "Activando entorno Python..."
cd "$INSTALL_DIR"
source venv/bin/activate
log "Virtual environment activado"

info "Iniciando Hermes gateway..."
echo ""
echo "──────────────────────────────────────────"
echo "  Gateway corriendo. Ctrl+C para detener."
echo "  Abrí Telegram y hablale a tu bot."
echo "──────────────────────────────────────────"
echo ""

hermes gateway run --replace
