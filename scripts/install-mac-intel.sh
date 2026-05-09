#!/bin/bash
# =============================================================================
# Wally Trader — Instalador para Mac Intel (x86_64)
# macOS 12 Monterey / 13 Ventura / 14 Sonoma
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
step()  { echo -e "\n${BLUE}▶${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Wally Trader — Mac Intel x86 Installer    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Detectar arquitectura
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    warn "Este script es para Intel x86_64. Detectaste Apple Silicon (arm64)."
    warn "El repositorio funciona mejor en ARM64 sin estos ajustes."
    read -p "¿Continuar de todas formas? (s/n): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Ss]$ ]] && exit 1
fi

OS_VERSION=$(sw_vers -productVersion)
log "macOS detectado: $OS_VERSION ($ARCH)"

# ─── PASO 1: Xcode Command Line Tools ────────────────────────────────────────
step "Verificando Xcode Command Line Tools"
if xcode-select -p &>/dev/null; then
    log "Xcode CLT ya instalado: $(xcode-select -p)"
else
    warn "Xcode CLT no encontrado. Instalando..."
    xcode-select --install
    echo "Esperá a que termine el instalador gráfico y presioná ENTER para continuar..."
    read -r
fi

# ─── PASO 2: Homebrew ─────────────────────────────────────────────────────────
step "Verificando Homebrew"
if command -v brew &>/dev/null; then
    log "Homebrew ya instalado: $(brew --version | head -1)"
    warn "En macOS 13 Intel verás warnings de 'Tier 3' — son normales, no son errores."
else
    warn "Homebrew no encontrado. Instalando..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/homebrew-install/HEAD/install.sh)"
fi

# ─── PASO 3: Node.js ──────────────────────────────────────────────────────────
step "Verificando Node.js"
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
    if [ "$MAJOR" -ge 18 ]; then
        log "Node.js $NODE_VERSION ya instalado"
    else
        warn "Node.js $NODE_VERSION es muy antiguo. Actualizando..."
        brew install node
    fi
else
    warn "Node.js no encontrado. Instalando (puede tardar 15-30 min en Intel)..."
    brew install node
fi

# ─── PASO 4: Python ───────────────────────────────────────────────────────────
step "Verificando Python"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version)
    log "$PY_VERSION ya instalado"
else
    warn "Python no encontrado. Instalando python@3.13..."
    brew install python@3.13
fi

# ─── PASO 5: Hermes Agent ─────────────────────────────────────────────────────
step "Verificando Hermes Agent"
if command -v hermes &>/dev/null; then
    log "Hermes ya instalado: $(hermes --version | head -1)"
else
    warn "Hermes no encontrado. Instalando..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
fi

# ─── PASO 6: Clonar repo ──────────────────────────────────────────────────────
step "Clonando wally-trader"
INSTALL_DIR="$HOME/wally-trader"

if [ -d "$INSTALL_DIR" ]; then
    warn "El directorio $INSTALL_DIR ya existe."
    read -p "¿Actualizar submodules? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cd "$INSTALL_DIR"
        git pull
        git submodule update --init --recursive
        log "Repositorio actualizado"
    fi
else
    git clone --recurse-submodules https://github.com/sasasamaes/wally-trader.git "$INSTALL_DIR"
    log "Repositorio clonado en $INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ─── PASO 7: Virtual environment ─────────────────────────────────────────────
step "Configurando entorno Python"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log "Virtual environment creado"
fi
source venv/bin/activate
log "Virtual environment activado"

# ─── PASO 8: Setup del repo ───────────────────────────────────────────────────
step "Ejecutando setup del repositorio"
bash setup.sh

# ─── PASO 9: TradingView MCP ─────────────────────────────────────────────────
step "Instalando dependencias de TradingView MCP"
cd tradingview-mcp
npm install
cd ..
log "TradingView MCP instalado (78 herramientas disponibles)"

# ─── PASO 10: Configurar MCP en Hermes ───────────────────────────────────────
step "Configurando TradingView MCP en Hermes"
MCP_CONFIG="mcp_servers:
  tradingview:
    command: node
    args:
      - $INSTALL_DIR/tradingview-mcp/src/server.js"

if grep -q "mcp_servers" ~/.hermes/config.yaml 2>/dev/null; then
    warn "mcp_servers ya existe en config — verificá que apunta al path correcto"
else
    echo "" >> ~/.hermes/config.yaml
    echo "$MCP_CONFIG" >> ~/.hermes/config.yaml
    log "TradingView MCP agregado a ~/.hermes/config.yaml"
fi

# ─── PASO 11: Alias de conveniencia ──────────────────────────────────────────
step "Agregando alias útiles a ~/.zshrc"
ALIASES='
# Wally Trader aliases
alias tv="pkill -f TradingView 2>/dev/null; sleep 2; open -a TradingView --args --remote-debugging-port=9222 && echo \"TradingView lanzado con CDP en puerto 9222\""
alias wally="cd ~/wally-trader && source venv/bin/activate && hermes gateway run --replace"
alias wally-start="tv && sleep 10 && wally"
'

if ! grep -q "Wally Trader aliases" ~/.zshrc 2>/dev/null; then
    echo "$ALIASES" >> ~/.zshrc
    log "Aliases agregados a ~/.zshrc"
else
    warn "Aliases ya existen en ~/.zshrc"
fi

# ─── RESUMEN ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║              ✓ Instalación completa          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Próximos pasos:"
echo ""
echo "  1. Configurar proveedor LLM:"
echo "     hermes model"
echo "     → Seleccionar 'custom (direct API)'"
echo "     → URL: https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
echo "     → Model: gpt-oss-120b"
echo ""
echo "  2. Configurar Telegram Bot:"
echo "     hermes config set TELEGRAM_BOT_TOKEN TU_TOKEN"
echo ""
echo "  3. Iniciar todo en un solo comando:"
echo "     source ~/.zshrc && wally-start"
echo ""
echo "  4. Parear Telegram (primera vez):"
echo "     hermes pairing approve telegram TU_CODIGO"
echo ""
echo "Ver docs/INSTALL_MAC_INTEL.md para más detalles."
echo ""
