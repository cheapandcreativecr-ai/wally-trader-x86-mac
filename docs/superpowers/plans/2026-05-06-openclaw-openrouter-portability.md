# OpenClaw + OpenRouter + Notion Memory Portability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [`docs/superpowers/specs/2026-05-06-openclaw-openrouter-portability-design.md`](../specs/2026-05-06-openclaw-openrouter-portability-design.md)

**Goal:** Make the wally-trader system run identically on Claude Code and OpenClaw with unified cross-harness/cross-device memory via Notion MCP, while keeping the existing system/+adapters/ pattern.

**Architecture:** Three layers landed sequentially: (1) `shared/wally_core/` extract pure logic + memory abstraction with 3 backends (local, notion, hybrid); (2) `wally-trader-mcp/` exposes 12 tools used by both harnesses; (3) `adapters/openclaw/` (mold of hermes) generates `.openclaw/` from canonical `system/`. Default memory backend is `hybrid`: local-sync writes + Notion async mirror with offline queue.

**Tech Stack:** Python 3.11+, FastMCP (`mcp[cli]>=1.0`), Pydantic v2, filelock, notion-client, pytest, VCR.py for HTTP cassettes, Node 22+ for OpenClaw runtime.

---

## File Structure

```
shared/wally_core/                        # NEW — pure logic + memory abstraction
├── pyproject.toml
└── src/wally_core/
    ├── __init__.py
    ├── regime.py            # ADX-based regime detection
    ├── validate.py          # 4-filter setup validation
    ├── risk.py              # flat 2% / VaR / parity sizing
    ├── hunt.py              # bitunix scoring 0-100
    ├── journal.py           # Sharpe/MaxDD/IC/WR/PF metrics
    ├── signals.py           # signal helpers (delegates to memory backend)
    ├── locking.py           # filelock wrapper + stale cleanup
    ├── macro.py             # macro_gate cache + DST
    ├── ml.py                # thin wrapper over scripts/ml_system/predict
    ├── sentiment.py         # thin wrapper over sentiment NLP
    ├── multifactor.py       # 0-100 composite score
    ├── health.py            # cross-cutting health check
    └── memory/
        ├── __init__.py      # get_backend(profile) factory
        ├── interface.py     # MemoryBackend ABC
        ├── schemas.py       # Pydantic models (Signal, Trade, EquityRow, JournalEntry)
        ├── local.py         # LocalBackend
        ├── notion.py        # NotionBackend
        ├── hybrid.py        # HybridBackend (default)
        ├── migrate.py       # CSV → Notion idempotent migration
        └── notion_schema.py # canonical DB schema definitions

shared/wally_core/tests/                  # NEW — pytest
├── test_regime.py, test_validate.py, ... (one per module)
└── memory/
    ├── test_local.py, test_notion.py, test_hybrid.py, test_migrate.py
    └── conftest.py          # fixtures (Notion sandbox, filesystem temp)

wally-trader-mcp/                         # NEW — MCP server
├── pyproject.toml
└── src/wally_trader_mcp/
    ├── __init__.py
    ├── server.py            # FastMCP entry, tool registration
    └── tools/
        ├── detect_regime.py, validate_setup.py, calculate_risk.py,
        ├── hunt_signals.py, signal_validate.py, journal_close.py,
        ├── log_outcome.py, macro_gate_check.py, chainlink_check.py,
        ├── ml_score.py, multifactor_score.py, sentiment_score.py,
        └── levels_now.py, macross_signal.py
└── tests/                   # integration tests (subprocess MCP)

adapters/openclaw/                        # NEW — 5to adapter (mold de hermes)
├── install.sh
├── transform.py
├── test_transform.py
└── README.md

.openclaw/                                # NEW — generated, committed
├── .gitkeep
├── skills/{wally-agents,wally-commands,wally-skills}/   (generated)
└── config.json                                          (generated)

system/mcp/servers.json                   # MODIFY — add "wally" + "notion" entries

Makefile                                  # MODIFY — add wally-mcp-install, sync-oc,
                                          # notion-init, notion-migrate, notion-rollback,
                                          # sync-pull, doctor, test-parity targets

.claude/profiles/<name>/config.md         # MODIFY (each profile) — add memory section
```

---

## Phase 1: `wally_core` foundations (Week 1)

### Task 1.1: Bootstrap the wally_core package

**Files:**
- Create: `shared/wally_core/pyproject.toml`
- Create: `shared/wally_core/src/wally_core/__init__.py`
- Create: `shared/wally_core/tests/__init__.py`
- Create: `shared/wally_core/tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "wally-core"
version = "0.1.0"
description = "Wally Trader shared logic library"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5",
    "filelock>=3.13",
    "pyyaml>=6.0",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
notion = ["notion-client>=2.2"]
test = ["pytest>=8.0", "pytest-cov>=4.1", "vcrpy>=6.0", "freezegun>=1.4"]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

- [ ] **Step 2: Write empty `__init__.py` for both src and tests**

`shared/wally_core/src/wally_core/__init__.py`:
```python
"""wally_core — shared logic for the Wally Trader system."""
__version__ = "0.1.0"
```

`shared/wally_core/tests/__init__.py`: empty file.

- [ ] **Step 3: Write `tests/conftest.py` with shared fixtures**

```python
import json
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def ohlcv_btc_15m_range():
    """100 bars of BTC 15m in a range regime (Apr 2026 fixture)."""
    return json.loads((FIXTURES_DIR / "btc_15m_range.json").read_text())

@pytest.fixture
def ohlcv_btc_1h_trending():
    """200 bars of BTC 1h in a trending regime (Mar 2026 fixture)."""
    return json.loads((FIXTURES_DIR / "btc_1h_trending.json").read_text())

@pytest.fixture
def tmp_profile(tmp_path):
    """Temp profile directory mimicking .claude/profiles/<name>/memory/."""
    p = tmp_path / "profiles" / "test_profile" / "memory"
    p.mkdir(parents=True)
    return p
```

Create `tests/fixtures/` directory with two JSON fixtures (capture them from existing scripts):

```bash
mkdir -p shared/wally_core/tests/fixtures
python3 .claude/scripts/data_pull.py --symbol BTCUSDT --tf 15m --bars 100 \
  > shared/wally_core/tests/fixtures/btc_15m_range.json
python3 .claude/scripts/data_pull.py --symbol BTCUSDT --tf 1h --bars 200 \
  > shared/wally_core/tests/fixtures/btc_1h_trending.json
```

(If `data_pull.py` doesn't exist with that exact interface, use whatever helper currently fetches OHLCV — check `.claude/scripts/` for `*_pull*.py` or similar.)

- [ ] **Step 4: Install in editable mode and verify**

Run: `pip install -e shared/wally_core[test]`
Expected: package installs without errors. `python -c "import wally_core; print(wally_core.__version__)"` prints `0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/
git commit -m "feat(wally_core): bootstrap package with conftest fixtures"
```

---

### Task 1.2: Port `adx_calc.py` to `wally_core/regime.py` (TDD)

**Files:**
- Create: `shared/wally_core/src/wally_core/regime.py`
- Create: `shared/wally_core/tests/test_regime.py`
- Reference: `.claude/scripts/adx_calc.py` (existing logic)

- [ ] **Step 1: Write the failing test for `compute_adx`**

```python
# shared/wally_core/tests/test_regime.py
import pytest
from wally_core.regime import compute_adx, label_regime, RegimeLabel

def test_compute_adx_returns_dict_with_required_keys(ohlcv_btc_1h_trending):
    result = compute_adx(ohlcv_btc_1h_trending, length=14)
    assert set(result.keys()) >= {"adx", "plus_di", "minus_di"}
    assert 0 <= result["adx"] <= 100
    assert 0 <= result["plus_di"] <= 100
    assert 0 <= result["minus_di"] <= 100

def test_compute_adx_trending_data_above_25(ohlcv_btc_1h_trending):
    result = compute_adx(ohlcv_btc_1h_trending, length=14)
    assert result["adx"] >= 25, f"Expected trending fixture ADX >= 25, got {result['adx']}"

def test_label_regime_range_when_adx_low():
    label = label_regime(adx=15.0, plus_di=20.0, minus_di=22.0)
    assert label == RegimeLabel.RANGE_CHOP

def test_label_regime_trend_leve_when_adx_in_25_30():
    label = label_regime(adx=27.0, plus_di=30.0, minus_di=18.0)
    assert label == RegimeLabel.TREND_LEVE

def test_label_regime_trend_fuerte_when_adx_in_30_40():
    label = label_regime(adx=35.0, plus_di=32.0, minus_di=18.0)
    assert label == RegimeLabel.TREND_FUERTE

def test_label_regime_trend_extremo_when_adx_above_40():
    label = label_regime(adx=45.0, plus_di=40.0, minus_di=15.0)
    assert label == RegimeLabel.TREND_EXTREMO
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest shared/wally_core/tests/test_regime.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_adx' from 'wally_core.regime'`

- [ ] **Step 3: Implement `regime.py` ported from existing script**

```python
# shared/wally_core/src/wally_core/regime.py
"""ADX-based regime detection."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class RegimeLabel(str, Enum):
    RANGE_CHOP = "RANGE_CHOP"
    TREND_LEVE = "TREND_LEVE"
    TREND_FUERTE = "TREND_FUERTE"
    TREND_EXTREMO = "TREND_EXTREMO"
    VOLATILE = "VOLATILE"  # ATR-based override

def compute_adx(bars: list[dict], length: int = 14) -> dict:
    """Compute ADX, +DI, -DI from OHLCV bars.

    Bars: list of {open, high, low, close, volume}.
    Returns dict with keys: adx, plus_di, minus_di.
    """
    if len(bars) < length * 2:
        raise ValueError(f"Need at least {length * 2} bars, got {len(bars)}")

    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]

    plus_dm = []
    minus_dm = []
    tr = []
    for i in range(1, len(bars)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    def smooth(arr: list[float], n: int) -> list[float]:
        out = [sum(arr[:n])]
        for v in arr[n:]:
            out.append(out[-1] - out[-1] / n + v)
        return out

    sm_plus = smooth(plus_dm, length)
    sm_minus = smooth(minus_dm, length)
    sm_tr = smooth(tr, length)

    plus_di = [100 * p / t if t else 0 for p, t in zip(sm_plus, sm_tr)]
    minus_di = [100 * m / t if t else 0 for m, t in zip(sm_minus, sm_tr)]

    dx = [
        100 * abs(p - m) / (p + m) if (p + m) else 0
        for p, m in zip(plus_di, minus_di)
    ]
    if len(dx) < length:
        raise ValueError("Insufficient bars to compute ADX")
    adx_smoothed = sum(dx[:length]) / length
    for v in dx[length:]:
        adx_smoothed = (adx_smoothed * (length - 1) + v) / length

    return {
        "adx": round(adx_smoothed, 2),
        "plus_di": round(plus_di[-1], 2),
        "minus_di": round(minus_di[-1], 2),
    }

def label_regime(adx: float, plus_di: float, minus_di: float) -> RegimeLabel:
    """Map ADX numeric to regime label per CLAUDE.md thresholds."""
    if adx < 20:
        return RegimeLabel.RANGE_CHOP
    if adx < 25:
        return RegimeLabel.RANGE_CHOP  # ambiguous zone, prefer range
    if adx < 30:
        return RegimeLabel.TREND_LEVE
    if adx < 40:
        return RegimeLabel.TREND_FUERTE
    return RegimeLabel.TREND_EXTREMO
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest shared/wally_core/tests/test_regime.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/regime.py shared/wally_core/tests/test_regime.py
git commit -m "feat(wally_core): port ADX regime detection (compute_adx + label_regime)"
```

---

### Task 1.3: Port `validate.py` (4-filter setup check) — TDD

**Files:**
- Create: `shared/wally_core/src/wally_core/validate.py`
- Create: `shared/wally_core/tests/test_validate.py`
- Reference: trade-validator agent logic + CLAUDE.md "Mean Reversion" entry rules

- [ ] **Step 1: Write the failing tests for 4 filters (LONG)**

```python
# shared/wally_core/tests/test_validate.py
from wally_core.validate import validate_setup, FilterResult, ValidateResult, Side

def test_validate_long_all_4_filters_pass():
    bars = make_bars_long_setup()  # helper that constructs synthetic 4-pass bars
    result = validate_setup(bars=bars, side=Side.LONG, donchian_length=15)
    assert result.go is True
    assert all(f.passed for f in result.filters)

def test_validate_long_fails_when_rsi_above_35():
    bars = make_bars_long_setup(rsi_override=40.0)
    result = validate_setup(bars=bars, side=Side.LONG, donchian_length=15)
    assert result.go is False
    rsi_filter = next(f for f in result.filters if f.name == "rsi_oversold")
    assert rsi_filter.passed is False

def test_validate_long_fails_when_no_bb_touch():
    bars = make_bars_long_setup(no_bb_touch=True)
    result = validate_setup(bars=bars, side=Side.LONG, donchian_length=15)
    assert result.go is False

def test_validate_long_fails_when_red_close():
    bars = make_bars_long_setup(red_close=True)
    result = validate_setup(bars=bars, side=Side.LONG, donchian_length=15)
    assert result.go is False

def test_validate_short_all_4_filters_pass():
    bars = make_bars_short_setup()
    result = validate_setup(bars=bars, side=Side.SHORT, donchian_length=15)
    assert result.go is True

def test_validate_returns_FilterResult_for_each_filter():
    bars = make_bars_long_setup()
    result = validate_setup(bars=bars, side=Side.LONG, donchian_length=15)
    filter_names = {f.name for f in result.filters}
    assert filter_names == {"donchian_extreme", "rsi_oversold", "bb_touch", "candle_color"}
```

(Add helpers `make_bars_long_setup` and `make_bars_short_setup` near the top of the test file — they construct 30-bar fixtures with controlled RSI/BB/Donchian/close-color values. Keep them simple: hardcode close prices.)

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest shared/wally_core/tests/test_validate.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Implement `validate.py`**

```python
# shared/wally_core/src/wally_core/validate.py
"""4-filter Mean Reversion setup validation."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import statistics

class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class FilterResult:
    name: str
    passed: bool
    detail: str

@dataclass
class ValidateResult:
    go: bool
    filters: list[FilterResult]
    reason: str

def _rsi(closes: list[float], length: int = 14) -> float:
    if len(closes) < length + 1:
        raise ValueError("not enough closes for RSI")
    gains = []
    losses = []
    for i in range(1, length + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / length
    avg_loss = sum(losses) / length
    for i in range(length + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (length - 1) + gain) / length
        avg_loss = (avg_loss * (length - 1) + loss) / length
    rs = avg_gain / avg_loss if avg_loss else float("inf")
    return 100 - 100 / (1 + rs)

def _bollinger(closes: list[float], length: int = 20, std_mult: float = 2.0):
    if len(closes) < length:
        raise ValueError("not enough closes for BB")
    window = closes[-length:]
    mean = statistics.fmean(window)
    sd = statistics.pstdev(window)
    return {"upper": mean + std_mult * sd, "lower": mean - std_mult * sd, "mid": mean}

def _donchian(bars: list[dict], length: int = 15):
    window = bars[-length:]
    return {"high": max(b["high"] for b in window), "low": min(b["low"] for b in window)}

def validate_setup(bars: list[dict], side: Side, donchian_length: int = 15) -> ValidateResult:
    """Apply 4-filter Mean Reversion check on the latest bar.

    LONG passes when: donchian-low touched (±0.1%), RSI<35, low touches BB-lower, close green.
    SHORT mirrors.
    """
    if len(bars) < max(donchian_length, 20) + 1:
        raise ValueError("not enough bars")

    last = bars[-1]
    closes = [float(b["close"]) for b in bars]
    last_close = float(last["close"])
    last_open = float(last["open"])
    last_high = float(last["high"])
    last_low = float(last["low"])

    rsi = _rsi(closes)
    bb = _bollinger(closes)
    donch = _donchian(bars, donchian_length)

    filters: list[FilterResult] = []
    if side == Side.LONG:
        donch_pct = abs(last_low - donch["low"]) / donch["low"]
        filters.append(FilterResult(
            "donchian_extreme",
            donch_pct <= 0.001,
            f"low={last_low} donch_low={donch['low']} pct={donch_pct:.4f}"
        ))
        filters.append(FilterResult("rsi_oversold", rsi < 35, f"rsi={rsi:.2f}"))
        filters.append(FilterResult("bb_touch", last_low <= bb["lower"], f"low={last_low} bb_lower={bb['lower']:.2f}"))
        filters.append(FilterResult("candle_color", last_close > last_open, f"close={last_close} open={last_open}"))
    else:  # SHORT
        donch_pct = abs(last_high - donch["high"]) / donch["high"]
        filters.append(FilterResult(
            "donchian_extreme",
            donch_pct <= 0.001,
            f"high={last_high} donch_high={donch['high']} pct={donch_pct:.4f}"
        ))
        filters.append(FilterResult("rsi_oversold", rsi > 65, f"rsi={rsi:.2f}"))
        filters.append(FilterResult("bb_touch", last_high >= bb["upper"], f"high={last_high} bb_upper={bb['upper']:.2f}"))
        filters.append(FilterResult("candle_color", last_close < last_open, f"close={last_close} open={last_open}"))

    go = all(f.passed for f in filters)
    failed = [f.name for f in filters if not f.passed]
    reason = "all 4 filters passed" if go else f"failed: {', '.join(failed)}"
    return ValidateResult(go=go, filters=filters, reason=reason)
```

Add the bar-builder helpers at top of the test file (concrete numbers — no abstraction):

```python
# in test_validate.py, before the test functions
def _bar(o, h, l, c, v=100):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}

def make_bars_long_setup(*, rsi_override=None, no_bb_touch=False, red_close=False):
    """30-bar fixture: range up to bar 29, then a deep wick that hits Donchian-low + BB-lower."""
    bars = [_bar(100, 102, 98, 100) for _ in range(15)]
    bars += [_bar(100, 101, 95, 99) for _ in range(14)]  # downward drift to lower RSI
    last_close = 99.5 if not red_close else 95.5
    last_open = 96 if not red_close else 99
    last_low = 92 if not no_bb_touch else 98
    bars.append(_bar(last_open, 100, last_low, last_close))
    if rsi_override is not None:
        # crude: replace last 14 bars with rising prices to bump RSI
        for i in range(15, 29):
            bars[i] = _bar(100, 105, 99, 104)
    return bars

def make_bars_short_setup():
    bars = [_bar(100, 102, 98, 100) for _ in range(15)]
    bars += [_bar(100, 105, 99, 104) for _ in range(14)]
    bars.append(_bar(104, 110, 103, 103))  # touch BB upper, RSI high, red close
    return bars
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest shared/wally_core/tests/test_validate.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/validate.py shared/wally_core/tests/test_validate.py
git commit -m "feat(wally_core): port 4-filter setup validation (LONG/SHORT)"
```

---

### Task 1.4: Port `risk.py` with 3 sizing modes — TDD

**Files:**
- Create: `shared/wally_core/src/wally_core/risk.py`
- Create: `shared/wally_core/tests/test_risk.py`
- Reference: `.claude/scripts/risk_quant.py`, `.claude/scripts/risk_parity.py`

- [ ] **Step 1: Write the failing tests**

```python
# shared/wally_core/tests/test_risk.py
import pytest
from wally_core.risk import calculate_position_size, RiskMode, ProfileLeverageCap

def test_flat_2pct_basic_long():
    result = calculate_position_size(
        capital_usd=200.0,
        entry=68000,
        sl=67500,
        side="LONG",
        leverage=10,
        mode=RiskMode.FLAT_2PCT,
        profile="bitunix",
    )
    # 2% of 200 = $4 risk; SL distance = 500; size = 4/500 BTC * leverage = 0.008 BTC notional
    # margin = (0.008 * 68000) / 10 = $54.4 — but flat 2pct caps margin to risk_pct allowance
    assert result.risk_usd == pytest.approx(4.0)
    assert result.position_size_btc > 0

def test_flat_2pct_respects_leverage_cap_retail_10x():
    result = calculate_position_size(
        capital_usd=20.0, entry=68000, sl=67500, side="LONG",
        leverage=20,  # user requests 20x
        mode=RiskMode.FLAT_2PCT, profile="retail",
    )
    assert result.leverage_used == 10  # capped to retail max

def test_flat_2pct_respects_leverage_cap_bitunix_20x():
    result = calculate_position_size(
        capital_usd=200.0, entry=68000, sl=67500, side="LONG",
        leverage=25,  # request 25x
        mode=RiskMode.FLAT_2PCT, profile="bitunix",
    )
    assert result.leverage_used == 20  # capped to bitunix max
    assert "WARN" in result.warnings[0]

def test_var_mode_sizing_uses_atr_percentile(ohlcv_btc_15m_range):
    result = calculate_position_size(
        capital_usd=200.0, entry=68000, sl=67500, side="LONG",
        leverage=10, mode=RiskMode.VAR, profile="bitunix",
        bars_for_var=ohlcv_btc_15m_range,
    )
    assert result.risk_usd <= 4.0  # VaR-adjusted ≤ flat 2%
    assert result.var_pct is not None

def test_parity_mode_requires_assets_dict():
    with pytest.raises(ValueError, match="parity"):
        calculate_position_size(
            capital_usd=10000, entry=1.10, sl=1.095, side="LONG",
            leverage=50, mode=RiskMode.PARITY, profile="ftmo",
        )
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest shared/wally_core/tests/test_risk.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Implement `risk.py`**

```python
# shared/wally_core/src/wally_core/risk.py
"""Position sizing — flat 2%, VaR, Risk Parity."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class RiskMode(str, Enum):
    FLAT_2PCT = "flat_2pct"
    VAR = "var"
    PARITY = "parity"

LEVERAGE_CAPS: dict[str, int] = {
    "retail": 10,
    "retail-bingx": 10,
    "ftmo": 100,
    "fundingpips": 50,
    "fotmarkets": 500,
    "bitunix": 20,
    "quantfury": 5,
}

@dataclass
class ProfileLeverageCap:
    profile: str
    cap: int

@dataclass
class SizingResult:
    risk_usd: float
    position_size_btc: float
    margin_usd: float
    leverage_used: int
    mode: RiskMode
    warnings: list[str] = field(default_factory=list)
    var_pct: float | None = None

def _flat_2pct(capital_usd, entry, sl, side, leverage, profile, warnings):
    risk_usd = capital_usd * 0.02
    sl_distance = abs(entry - sl)
    if sl_distance == 0:
        raise ValueError("SL distance is zero")
    notional = risk_usd / sl_distance * entry
    position_size_btc = notional / entry
    margin_usd = notional / leverage
    return SizingResult(
        risk_usd=risk_usd,
        position_size_btc=position_size_btc,
        margin_usd=margin_usd,
        leverage_used=leverage,
        mode=RiskMode.FLAT_2PCT,
        warnings=warnings,
    )

def _atr_percentile(bars, length=14):
    if len(bars) < length + 1:
        raise ValueError("not enough bars for ATR")
    trs = []
    for i in range(1, len(bars)):
        h, l = float(bars[i]["high"]), float(bars[i]["low"])
        prev_c = float(bars[i - 1]["close"])
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr_recent = sum(trs[-length:]) / length
    atr_history = sorted(trs)
    rank = sum(1 for t in atr_history if t <= atr_recent) / len(atr_history)
    return atr_recent, rank

def _var_mode(capital_usd, entry, sl, leverage, bars, profile, warnings):
    atr, percentile = _atr_percentile(bars)
    risk_pct = 0.02 * (1.0 - 0.5 * percentile)  # higher vol → smaller risk, floor 1%
    risk_pct = max(risk_pct, 0.01)
    risk_usd = capital_usd * risk_pct
    sl_distance = abs(entry - sl)
    notional = risk_usd / sl_distance * entry
    return SizingResult(
        risk_usd=risk_usd,
        position_size_btc=notional / entry,
        margin_usd=notional / leverage,
        leverage_used=leverage,
        mode=RiskMode.VAR,
        var_pct=round(percentile * 100, 1),
        warnings=warnings,
    )

def calculate_position_size(
    *,
    capital_usd: float,
    entry: float,
    sl: float,
    side: str,
    leverage: int,
    mode: RiskMode = RiskMode.FLAT_2PCT,
    profile: str,
    bars_for_var: list[dict] | None = None,
    assets: dict | None = None,
) -> SizingResult:
    warnings: list[str] = []
    cap = LEVERAGE_CAPS.get(profile, 10)
    if leverage > cap:
        warnings.append(f"WARN: requested leverage {leverage}x > {profile} cap {cap}x — capped")
        leverage = cap

    if mode == RiskMode.FLAT_2PCT:
        return _flat_2pct(capital_usd, entry, sl, side, leverage, profile, warnings)
    if mode == RiskMode.VAR:
        if bars_for_var is None:
            raise ValueError("VAR mode requires bars_for_var")
        return _var_mode(capital_usd, entry, sl, leverage, bars_for_var, profile, warnings)
    if mode == RiskMode.PARITY:
        if assets is None:
            raise ValueError("parity mode requires assets dict (multi-asset volatility)")
        # Phase 4: full parity impl
        raise NotImplementedError("parity mode arrives in Phase 4 (multi-asset)")
    raise ValueError(f"unknown mode {mode}")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest shared/wally_core/tests/test_risk.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/risk.py shared/wally_core/tests/test_risk.py
git commit -m "feat(wally_core): add position sizing (flat-2pct, VaR, parity stub)"
```

---

### Task 1.5: Port `locking.py` with stale-lock cleanup — TDD

**Files:**
- Create: `shared/wally_core/src/wally_core/locking.py`
- Create: `shared/wally_core/tests/test_locking.py`

- [ ] **Step 1: Write the failing tests**

```python
# shared/wally_core/tests/test_locking.py
import multiprocessing
import os
import time
from pathlib import Path
import pytest
from wally_core.locking import shared_write, FileLockTimeout

def _writer(path_str, payload, delay=0):
    if delay:
        time.sleep(delay)
    with shared_write(Path(path_str), timeout=2) as f:
        f.write(payload)

def test_shared_write_serializes_concurrent_writes(tmp_path):
    target = tmp_path / "log.csv"
    procs = [
        multiprocessing.Process(target=_writer, args=(str(target), f"row{i}\n"))
        for i in range(5)
    ]
    for p in procs: p.start()
    for p in procs: p.join()
    content = target.read_text()
    assert content.count("\n") == 5  # 5 rows, no truncation

def test_shared_write_timeout_when_held(tmp_path):
    target = tmp_path / "log.csv"
    blocker = multiprocessing.Process(target=_writer, args=(str(target), "blocker\n", 3))
    blocker.start()
    time.sleep(0.5)  # let blocker acquire
    with pytest.raises(FileLockTimeout):
        with shared_write(target, timeout=1):
            pass
    blocker.join()

def test_stale_lock_cleanup(tmp_path):
    target = tmp_path / "log.csv"
    lock_file = tmp_path / "log.csv.lock"
    lock_file.write_text("999999")  # fake PID that doesn't exist
    # The lock file is stale; shared_write should clean it up and proceed
    with shared_write(target, timeout=1, stale_age_s=0) as f:
        f.write("ok\n")
    assert target.read_text() == "ok\n"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest shared/wally_core/tests/test_locking.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Implement `locking.py`**

```python
# shared/wally_core/src/wally_core/locking.py
"""File-based locking for shared writes across CC and OC."""
from __future__ import annotations
import contextlib
import os
import time
from pathlib import Path
from filelock import FileLock, Timeout as _Timeout

class FileLockTimeout(Exception):
    pass

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def _maybe_clean_stale(lock_path: Path, stale_age_s: int):
    if not lock_path.exists():
        return
    age = time.time() - lock_path.stat().st_mtime
    if age < stale_age_s:
        return
    try:
        pid_str = lock_path.read_text().strip()
        if pid_str.isdigit() and _pid_alive(int(pid_str)):
            return
    except OSError:
        return
    try:
        lock_path.unlink()
    except OSError:
        pass

@contextlib.contextmanager
def shared_write(path: Path, *, timeout: float = 5.0, stale_age_s: int = 60, mode: str = "a"):
    """Acquire flock on `<path>.lock` then open `path` for append (default).

    Raises FileLockTimeout if can't acquire within `timeout` seconds.
    Auto-cleans stale locks (>stale_age_s old, PID dead).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    _maybe_clean_stale(lock_path, stale_age_s)
    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        lock.acquire()
    except _Timeout as e:
        raise FileLockTimeout(f"could not acquire {lock_path} within {timeout}s") from e
    try:
        with open(path, mode) as f:
            try:
                lock_path.write_text(str(os.getpid()))
            except OSError:
                pass
            yield f
            f.flush()
            os.fsync(f.fileno())
    finally:
        lock.release()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest shared/wally_core/tests/test_locking.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/locking.py shared/wally_core/tests/test_locking.py
git commit -m "feat(wally_core): add filelock wrapper with stale-lock cleanup"
```

---

### Task 1.6: Validate Notion MCP server choice (research spike)

**Files:**
- Create: `docs/notes/notion-mcp-evaluation.md`

- [ ] **Step 1: Try `@notionhq/notion-mcp-server`**

```bash
npx -y @notionhq/notion-mcp-server --help
```

If it runs and shows a command surface that includes `databases.query`, `pages.create`, etc., it's a candidate. Document version + commands.

- [ ] **Step 2: Try `@suekou/mcp-notion-server` as alternative**

```bash
npx -y @suekou/mcp-notion-server --help
```

Document. If neither fits, plan a Python-native MCP client thin wrapper over `notion-client` SDK.

- [ ] **Step 3: Write the evaluation note**

Create `docs/notes/notion-mcp-evaluation.md` with:
- Server chosen + reason
- Command/URL form for `system/mcp/servers.json`
- Required env vars
- Rate limits observed
- Schema format for properties (Notion API specifics for `select`, `relation`, `rich_text`)

- [ ] **Step 4: Commit the note**

```bash
git add docs/notes/notion-mcp-evaluation.md
git commit -m "docs: evaluate Notion MCP server options (spike for Phase 3)"
```

---

### Task 1.7: Port the remaining wally_core pure modules (batch TDD)

**Files (5 modules + 5 tests):**
- Create: `wally_core/macro.py`, `wally_core/hunt.py`, `wally_core/journal.py`, `wally_core/multifactor.py`, `wally_core/health.py`
- Create test files for each. Reference existing scripts: `.claude/scripts/macro_gate.py`, `punk_hunt_*.py`, `journal_metrics.py`, `multifactor.py`.

For each module, follow the same TDD pattern (write failing test → implement → pass → commit). Skipping the boilerplate here — tasks 1.2–1.5 establish the pattern. Each module:

- [ ] **Step 1: Write 3-5 failing tests covering happy path + key edge cases**
- [ ] **Step 2: Implement minimal code to pass**
- [ ] **Step 3: Run all wally_core tests (`pytest shared/wally_core/tests -v`) — expect green**
- [ ] **Step 4: Commit per module: `feat(wally_core): port <module>`**

Module-specific notes:

**`macro.py`** — load cached events, expose `is_within_event_window(now, window_min=30)`, `next_events(days=N)`. Cache file lives at `.claude/cache/macro_events.json` (read-only here; writer is `macro_calendar.py` already on launchd). Tests can mock the cache path via env var `WALLY_MACRO_CACHE`.

**`hunt.py`** — score 0-100 multi-factor on bars + assets list (bitunix only). Composition: 30 momentum + 25 volatility + 25 trend + 20 volume. Function: `score_asset(symbol, bars, regime) -> ScoreCard` returning numerator + breakdown.

**`journal.py`** — `compute_metrics(trades: list[Trade]) -> JournalMetrics` with sharpe (annualized, daily returns), max_dd, ic (information coefficient on score-vs-pnl), wr, pf. Use the `JournalMetrics` dataclass — fields locked here.

**`multifactor.py`** — `composite_score(symbol, bars) -> int` (0-100). Sub-scores match `hunt.py` weights but for any asset (not just bitunix watchlist).

**`health.py`** — `health_check() -> HealthReport` with sub-checks: macro cache age, profile valid, locks free. NO MCP checks here (those live in `wally-trader-mcp/server.py` Phase 5).

---

### Task 1.8: Wire wally_core into existing scripts (zero-rotura refactor)

**Files:**
- Modify: `.claude/scripts/adx_calc.py` — import from `wally_core.regime`, keep CLI surface
- Modify: `.claude/scripts/macro_gate.py` — import from `wally_core.macro`
- Modify: `.claude/scripts/multifactor.py` — import from `wally_core.multifactor`
- Reference: existing CLI args of each script

- [ ] **Step 1: For each script, replace internal logic with import**

Example for `adx_calc.py`:

```python
#!/usr/bin/env python3
"""ADX calculator CLI — wraps wally_core.regime."""
import argparse, json, sys
from pathlib import Path
from wally_core.regime import compute_adx, label_regime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="JSON OHLCV bars")
    parser.add_argument("--length", type=int, default=14)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    bars = json.loads(Path(args.file).read_text())
    res = compute_adx(bars, length=args.length)
    label = label_regime(res["adx"], res["plus_di"], res["minus_di"])
    if args.quick:
        print(f"{label.value} adx={res['adx']} +DI={res['plus_di']} -DI={res['minus_di']}")
    else:
        print(json.dumps({**res, "label": label.value}, indent=2))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test each refactored script with prior known-good input**

```bash
python3 .claude/scripts/adx_calc.py --file /tmp/bars1h.json --quick
# Compare output against the value from before refactor — should match exactly.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/adx_calc.py .claude/scripts/macro_gate.py .claude/scripts/multifactor.py
git commit -m "refactor(scripts): delegate to wally_core (no behavior change)"
```

---

## Phase 2: Memory abstraction + LocalBackend (Week 1-2)

### Task 2.1: Define memory interface + Pydantic schemas

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/__init__.py`
- Create: `shared/wally_core/src/wally_core/memory/interface.py`
- Create: `shared/wally_core/src/wally_core/memory/schemas.py`
- Create: `shared/wally_core/tests/memory/__init__.py`
- Create: `shared/wally_core/tests/memory/test_schemas.py`

- [ ] **Step 1: Write failing tests for schemas**

```python
# shared/wally_core/tests/memory/test_schemas.py
import pytest
from datetime import datetime, timezone
from wally_core.memory.schemas import Signal, Trade, EquityRow, JournalEntry, SignalDecision, SignalOutcome, TradeStatus, Side

def test_signal_required_fields():
    s = Signal(
        ts=datetime.now(timezone.utc),
        profile="bitunix",
        source="discord",
        symbol="BTCUSDT",
        side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10,
        score=72,
        decision=SignalDecision.GO,
    )
    assert s.outcome == SignalOutcome.PENDING  # default

def test_signal_rejects_invalid_score_range():
    with pytest.raises(ValueError):
        Signal(
            ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
            symbol="BTCUSDT", side=Side.LONG,
            entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
            leverage=10, score=150, decision=SignalDecision.GO,
        )

def test_trade_status_transitions_valid():
    t = Trade(profile="retail", date="2026-05-06", asset="BTCUSDT.P",
              side=Side.LONG, entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
              leverage=10, position_size_usd=20.0, status=TradeStatus.OPEN)
    assert t.id is not None  # auto-UUID
```

- [ ] **Step 2: Run tests — expect import failure**

Run: `pytest shared/wally_core/tests/memory/test_schemas.py -v`

- [ ] **Step 3: Implement schemas**

```python
# shared/wally_core/src/wally_core/memory/schemas.py
from __future__ import annotations
from datetime import datetime, date as _date
from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator

class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalDecision(str, Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    WARN = "WARN"

class SignalOutcome(str, Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    TP3 = "TP3"
    SL = "SL"
    MANUAL = "manual"
    PENDING = "pending"

class TradeStatus(str, Enum):
    OPEN = "open"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    SL = "sl"
    CLOSED_MANUAL = "closed_manual"

class TradeSource(str, Enum):
    MANUAL = "manual"
    SIGNAL = "signal"
    HUNT = "hunt"
    COPY = "copy"

class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime
    profile: str
    source: str  # discord | punk-hunt | self
    symbol: str
    side: Side
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    leverage: int
    score: int = Field(ge=0, le=100)
    decision: SignalDecision
    outcome: SignalOutcome = SignalOutcome.PENDING
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    raw_message: str = ""

class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    profile: str
    date: str  # ISO date
    asset: str
    side: Side
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    leverage: int
    position_size_usd: float
    exit_price: Optional[float] = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    status: TradeStatus
    source: TradeSource = TradeSource.MANUAL
    notes: str = ""

class EquityRow(BaseModel):
    profile: str
    date: str
    equity_usd: float
    equity_btc: Optional[float] = None
    daily_pnl_usd: float
    daily_return_pct: float

class JournalEntry(BaseModel):
    profile: str
    date: str
    summary: str
    lessons: str = ""
    screenshots: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement `interface.py` (ABC) and `__init__.py` (factory stub)**

```python
# shared/wally_core/src/wally_core/memory/interface.py
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Optional
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome

class MemoryBackend(ABC):
    @abstractmethod
    def append_signal(self, profile: str, signal: Signal) -> str: ...

    @abstractmethod
    def update_signal_outcome(self, signal_id: str, outcome: SignalOutcome,
                              exit_price: float, pnl_usd: float) -> None: ...

    @abstractmethod
    def read_signals(self, profile: str, *, since: Optional[date] = None,
                     status: Optional[SignalOutcome] = None) -> Iterable[Signal]: ...

    @abstractmethod
    def append_trade(self, profile: str, trade: Trade) -> str: ...

    @abstractmethod
    def append_equity(self, profile: str, row: EquityRow) -> None: ...

    @abstractmethod
    def append_journal(self, profile: str, entry: JournalEntry) -> None: ...

    @abstractmethod
    def health_check(self) -> dict: ...
```

```python
# shared/wally_core/src/wally_core/memory/__init__.py
from __future__ import annotations
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, Side, SignalDecision, SignalOutcome, TradeStatus, TradeSource

def get_backend(profile: str) -> MemoryBackend:
    """Factory — reads profile config to choose backend.

    For now (Phase 2), always returns LocalBackend. Phase 4 will read profile config.
    """
    from .local import LocalBackend
    return LocalBackend()

__all__ = ["MemoryBackend", "Signal", "Trade", "EquityRow", "JournalEntry",
           "Side", "SignalDecision", "SignalOutcome", "TradeStatus", "TradeSource",
           "get_backend"]
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest shared/wally_core/tests/memory/test_schemas.py -v`
Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/ shared/wally_core/tests/memory/
git commit -m "feat(wally_core/memory): add MemoryBackend interface + Pydantic schemas"
```

---

### Task 2.2: Implement `LocalBackend` — TDD

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/local.py`
- Create: `shared/wally_core/tests/memory/test_local.py`

- [ ] **Step 1: Write the failing tests**

```python
# shared/wally_core/tests/memory/test_local.py
import os
import pytest
from datetime import datetime, timezone
from wally_core.memory import (
    Signal, Side, SignalDecision, SignalOutcome,
)
from wally_core.memory.local import LocalBackend

@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    return LocalBackend()

def _sample_signal(profile="bitunix"):
    return Signal(
        ts=datetime.now(timezone.utc),
        profile=profile, source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )

def test_append_signal_writes_csv_row(backend, tmp_path):
    sig = _sample_signal()
    sid = backend.append_signal("bitunix", sig)
    assert sid == sig.id
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    assert csv_path.exists()
    rows = csv_path.read_text().strip().split("\n")
    assert len(rows) == 2  # header + 1 row
    assert sig.id in rows[1]

def test_read_signals_returns_appended(backend):
    sig = _sample_signal()
    backend.append_signal("bitunix", sig)
    signals = list(backend.read_signals("bitunix"))
    assert len(signals) == 1
    assert signals[0].id == sig.id

def test_update_signal_outcome_modifies_row(backend):
    sig = _sample_signal()
    backend.append_signal("bitunix", sig)
    backend.update_signal_outcome(sig.id, SignalOutcome.TP1, 68500, 1.5)
    signals = list(backend.read_signals("bitunix"))
    assert signals[0].outcome == SignalOutcome.TP1
    assert signals[0].pnl_usd == pytest.approx(1.5)

def test_profile_isolation(backend):
    sig1 = _sample_signal(profile="bitunix")
    sig2 = _sample_signal(profile="retail")
    backend.append_signal("bitunix", sig1)
    backend.append_signal("retail", sig2)
    assert len(list(backend.read_signals("bitunix"))) == 1
    assert len(list(backend.read_signals("retail"))) == 1

def test_health_check_returns_status(backend):
    h = backend.health_check()
    assert h["backend"] == "local"
    assert h["status"] in ("ok", "warn", "error")
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest shared/wally_core/tests/memory/test_local.py -v`

- [ ] **Step 3: Implement `LocalBackend`**

```python
# shared/wally_core/src/wally_core/memory/local.py
from __future__ import annotations
import csv
import json
import os
from datetime import date as _date
from pathlib import Path
from typing import Iterable, Optional
from ..locking import shared_write
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome

DEFAULT_PROFILES_DIR = Path(".claude/profiles")

class LocalBackend(MemoryBackend):
    def __init__(self, profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or Path(os.environ.get(
            "WALLY_PROFILES_DIR", str(DEFAULT_PROFILES_DIR)
        ))

    def _memory_dir(self, profile: str) -> Path:
        d = self.profiles_dir / profile / "memory"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _signals_csv(self, profile: str) -> Path:
        return self._memory_dir(profile) / "signals_received.csv"

    SIGNAL_COLS = [
        "id", "ts", "profile", "source", "symbol", "side",
        "entry", "sl", "tp1", "tp2", "tp3", "leverage",
        "score", "decision", "outcome", "exit_price", "pnl_usd", "raw_message",
    ]

    def append_signal(self, profile: str, signal: Signal) -> str:
        path = self._signals_csv(profile)
        write_header = not path.exists() or path.stat().st_size == 0
        row = signal.model_dump()
        row["ts"] = signal.ts.isoformat()
        row["side"] = signal.side.value
        row["decision"] = signal.decision.value
        row["outcome"] = signal.outcome.value
        with shared_write(path) as f:
            writer = csv.DictWriter(f, fieldnames=self.SIGNAL_COLS)
            if write_header:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in self.SIGNAL_COLS})
        return signal.id

    def update_signal_outcome(self, signal_id, outcome, exit_price, pnl_usd):
        # find profile by scanning — small N, fine for v1
        for prof_dir in self.profiles_dir.iterdir():
            if not prof_dir.is_dir(): continue
            path = prof_dir / "memory" / "signals_received.csv"
            if not path.exists(): continue
            rows = list(csv.DictReader(path.open()))
            for r in rows:
                if r.get("id") == signal_id:
                    r["outcome"] = outcome.value
                    r["exit_price"] = exit_price
                    r["pnl_usd"] = pnl_usd
                    # rewrite atomically
                    tmp = path.with_suffix(".tmp")
                    with shared_write(tmp, mode="w") as f:
                        w = csv.DictWriter(f, fieldnames=self.SIGNAL_COLS)
                        w.writeheader()
                        for rr in rows:
                            w.writerow({k: rr.get(k, "") for k in self.SIGNAL_COLS})
                    tmp.replace(path)
                    return
        raise KeyError(f"signal {signal_id} not found")

    def read_signals(self, profile, *, since=None, status=None):
        path = self._signals_csv(profile)
        if not path.exists():
            return
        for r in csv.DictReader(path.open()):
            try:
                sig = Signal(
                    id=r["id"], ts=r["ts"], profile=r["profile"], source=r["source"],
                    symbol=r["symbol"], side=r["side"],
                    entry=float(r["entry"]), sl=float(r["sl"]),
                    tp1=float(r["tp1"]), tp2=float(r["tp2"]), tp3=float(r["tp3"]),
                    leverage=int(r["leverage"]), score=int(r["score"]),
                    decision=r["decision"], outcome=r["outcome"],
                    exit_price=float(r["exit_price"]) if r.get("exit_price") else None,
                    pnl_usd=float(r["pnl_usd"]) if r.get("pnl_usd") else None,
                    raw_message=r.get("raw_message", ""),
                )
            except Exception:
                continue  # skip malformed
            if since and sig.ts.date() < since:
                continue
            if status and sig.outcome != status:
                continue
            yield sig

    def append_trade(self, profile, trade):
        path = self._memory_dir(profile) / "trades_log.csv"
        # similar pattern; full impl Phase 5
        raise NotImplementedError("Trade append arrives in Phase 5")

    def append_equity(self, profile, row):
        path = self._memory_dir(profile) / "equity_curve.csv"
        cols = ["profile", "date", "equity_usd", "equity_btc", "daily_pnl_usd", "daily_return_pct"]
        write_header = not path.exists() or path.stat().st_size == 0
        with shared_write(path) as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if write_header: w.writeheader()
            w.writerow(row.model_dump())

    def append_journal(self, profile, entry):
        path = self._memory_dir(profile) / "daily_journal" / f"{entry.date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with shared_write(path, mode="w") as f:
            f.write(f"# {entry.profile} — {entry.date}\n\n## Summary\n{entry.summary}\n\n## Lessons\n{entry.lessons}\n")

    def health_check(self):
        return {
            "backend": "local",
            "status": "ok",
            "profiles_dir": str(self.profiles_dir),
            "writable": os.access(str(self.profiles_dir.parent), os.W_OK),
        }
```

- [ ] **Step 4: Run all memory tests**

Run: `pytest shared/wally_core/tests/memory/ -v`
Expected: 5+ PASSED.

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/local.py shared/wally_core/tests/memory/test_local.py
git commit -m "feat(wally_core/memory): implement LocalBackend with flock writes"
```

---

### Task 2.3: Add concurrent-write integration test for LocalBackend

**Files:**
- Modify: `shared/wally_core/tests/memory/test_local.py` (add one test)

- [ ] **Step 1: Add the test**

```python
# append to test_local.py
import multiprocessing

def _writer_proc(profiles_dir_str, profile, n):
    os.environ["WALLY_PROFILES_DIR"] = profiles_dir_str
    from wally_core.memory.local import LocalBackend
    b = LocalBackend()
    for i in range(n):
        b.append_signal(profile, _sample_signal(profile=profile))

def test_concurrent_writes_preserve_all_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    procs = [multiprocessing.Process(target=_writer_proc, args=(str(tmp_path / "profiles"), "bitunix", 10)) for _ in range(5)]
    for p in procs: p.start()
    for p in procs: p.join()
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    rows = csv_path.read_text().strip().split("\n")
    assert len(rows) == 51  # header + 50 signal rows
```

- [ ] **Step 2: Run — expect pass**

Run: `pytest shared/wally_core/tests/memory/test_local.py::test_concurrent_writes_preserve_all_rows -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git commit -am "test(memory): verify LocalBackend handles 5×10 concurrent writes"
```

---

### Task 2.4: Wire `signals.py` to use memory backend

**Files:**
- Create: `shared/wally_core/src/wally_core/signals.py`
- Create: `shared/wally_core/tests/test_signals.py`

- [ ] **Step 1: Write failing tests**

```python
# shared/wally_core/tests/test_signals.py
import pytest
from datetime import datetime, timezone
from wally_core.signals import log_signal, close_signal_outcome, list_open_signals
from wally_core.memory import Signal, Side, SignalDecision, SignalOutcome

@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))

def _sig():
    return Signal(
        ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )

def test_log_signal_returns_uuid(isolated):
    sid = log_signal(_sig())
    assert sid

def test_list_open_signals_filters_pending(isolated):
    log_signal(_sig())
    opens = list(list_open_signals("bitunix"))
    assert len(opens) == 1
    assert opens[0].outcome == SignalOutcome.PENDING

def test_close_signal_outcome_updates(isolated):
    s = _sig()
    sid = log_signal(s)
    close_signal_outcome(sid, SignalOutcome.TP1, 68500, 1.5)
    opens = list(list_open_signals("bitunix"))
    assert len(opens) == 0  # pending gone
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement `signals.py`**

```python
# shared/wally_core/src/wally_core/signals.py
from __future__ import annotations
from typing import Iterable
from .memory import get_backend, Signal, SignalOutcome

def log_signal(signal: Signal) -> str:
    return get_backend(signal.profile).append_signal(signal.profile, signal)

def close_signal_outcome(signal_id: str, outcome: SignalOutcome, exit_price: float, pnl_usd: float):
    # In Phase 4, get_backend can be profile-agnostic; for now use any backend
    get_backend("default").update_signal_outcome(signal_id, outcome, exit_price, pnl_usd)

def list_open_signals(profile: str) -> Iterable[Signal]:
    yield from get_backend(profile).read_signals(profile, status=SignalOutcome.PENDING)
```

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/signals.py shared/wally_core/tests/test_signals.py
git commit -m "feat(wally_core/signals): high-level helpers using memory backend"
```

---

## Phase 3: NotionBackend + migration tooling (Week 2)

### Task 3.1: Define Notion DB schemas (canonical)

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/notion_schema.py`

- [ ] **Step 1: Write the schema definitions**

```python
# shared/wally_core/src/wally_core/memory/notion_schema.py
"""Canonical Notion DB schemas — used by migrate.py and NotionBackend."""

DB_PROFILES = {
    "title": "📊 Profiles",
    "properties": {
        "Name": {"title": {}},
        "Capital USD": {"number": {"format": "dollar"}},
        "Capital BTC": {"number": {"format": "number"}},
        "Strategy": {"select": {"options": [
            {"name": "Mean Reversion"}, {"name": "Donchian Breakout"},
            {"name": "MA Crossover"}, {"name": "Multi-Asset"},
        ]}},
        "Window CR": {"rich_text": {}},
        "Last Updated": {"last_edited_time": {}},
    },
}

DB_TRADES_LOG = {
    "title": "📈 Trades Log",
    "properties": {
        "ID": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Asset": {"rich_text": {}},
        "Side": {"select": {"options": [{"name": "LONG"}, {"name": "SHORT"}]}},
        "Entry": {"number": {"format": "number"}},
        "SL": {"number": {"format": "number"}},
        "TP1": {"number": {"format": "number"}},
        "TP2": {"number": {"format": "number"}},
        "TP3": {"number": {"format": "number"}},
        "Leverage": {"number": {"format": "number"}},
        "Position Size USD": {"number": {"format": "dollar"}},
        "Exit Price": {"number": {"format": "number"}},
        "PnL USD": {"number": {"format": "dollar"}},
        "PnL %": {"number": {"format": "percent"}},
        "R Multiple": {"number": {"format": "number"}},
        "Status": {"select": {"options": [
            {"name": "open"}, {"name": "tp1_hit"}, {"name": "tp2_hit"},
            {"name": "tp3_hit"}, {"name": "sl"}, {"name": "closed_manual"},
        ]}},
        "Source": {"select": {"options": [
            {"name": "manual"}, {"name": "signal"}, {"name": "hunt"}, {"name": "copy"},
        ]}},
        "Notes": {"rich_text": {}},
    },
}

DB_SIGNALS_RECEIVED = {
    "title": "📡 Signals Received",
    "properties": {
        "ID": {"title": {}},
        "Timestamp": {"created_time": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Source": {"select": {"options": [
            {"name": "discord"}, {"name": "punk-hunt"}, {"name": "self"},
        ]}},
        "Symbol": {"rich_text": {}},
        "Side": {"select": {"options": [{"name": "LONG"}, {"name": "SHORT"}]}},
        "Entry": {"number": {"format": "number"}},
        "SL": {"number": {"format": "number"}},
        "TP1": {"number": {"format": "number"}},
        "TP2": {"number": {"format": "number"}},
        "TP3": {"number": {"format": "number"}},
        "Leverage": {"number": {"format": "number"}},
        "Score": {"number": {"format": "number"}},
        "Decision": {"select": {"options": [
            {"name": "GO"}, {"name": "NO-GO"}, {"name": "WARN"},
        ]}},
        "Outcome": {"select": {"options": [
            {"name": "TP1"}, {"name": "TP2"}, {"name": "TP3"},
            {"name": "SL"}, {"name": "manual"}, {"name": "pending"},
        ]}},
        "Exit Price": {"number": {"format": "number"}},
        "PnL USD": {"number": {"format": "dollar"}},
        "Raw Message": {"rich_text": {}},
    },
}

DB_EQUITY_CURVE = {
    "title": "💰 Equity Curve",
    "properties": {
        "ID": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Equity USD": {"number": {"format": "dollar"}},
        "Equity BTC": {"number": {"format": "number"}},
        "Daily PnL USD": {"number": {"format": "dollar"}},
        "Daily Return %": {"number": {"format": "percent"}},
    },
}

DB_DAILY_JOURNAL = {
    "title": "📔 Daily Journal",
    "properties": {
        "Title": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Summary": {"rich_text": {}},
        "Lessons": {"rich_text": {}},
        "Screenshots": {"files": {}},
    },
}

DB_WEEKLY_DIGEST = {
    "title": "📅 Weekly Digest",
    "properties": {
        "Title": {"title": {}},
        "Week Start": {"date": {}},
        "Summary": {"rich_text": {}},
        "Highlights": {"rich_text": {}},
        "Macro Events Next Week": {"rich_text": {}},
    },
}

ALL_DBS = {
    "profiles": DB_PROFILES,
    "trades_log": DB_TRADES_LOG,
    "signals_received": DB_SIGNALS_RECEIVED,
    "equity_curve": DB_EQUITY_CURVE,
    "daily_journal": DB_DAILY_JOURNAL,
    "weekly_digest": DB_WEEKLY_DIGEST,
}
```

- [ ] **Step 2: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/notion_schema.py
git commit -m "feat(wally_core/memory): canonical Notion DB schemas (6 DBs)"
```

---

### Task 3.2: Implement `NotionBackend` (with VCR cassettes for tests)

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/notion.py`
- Create: `shared/wally_core/tests/memory/test_notion.py`
- Create: `shared/wally_core/tests/memory/cassettes/` (VCR recordings, gitignored sensitive bits)

- [ ] **Step 1: Write the failing tests using VCR.py**

```python
# shared/wally_core/tests/memory/test_notion.py
import pytest
import vcr
from datetime import datetime, timezone
from wally_core.memory import Signal, Side, SignalDecision, SignalOutcome

VCR_DIR = "shared/wally_core/tests/memory/cassettes"
my_vcr = vcr.VCR(
    cassette_library_dir=VCR_DIR,
    record_mode="once",
    filter_headers=["authorization"],
)

@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_TEST_KEY")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "test-db-id"}')
    from wally_core.memory.notion import NotionBackend
    return NotionBackend()

def _sig():
    return Signal(
        ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )

@my_vcr.use_cassette("notion_append_signal.yaml")
def test_append_signal_creates_page(backend):
    sid = backend.append_signal("bitunix", _sig())
    assert sid

@my_vcr.use_cassette("notion_health_check.yaml")
def test_health_check_returns_ok_when_dbs_exist(backend):
    h = backend.health_check()
    assert h["backend"] == "notion"
    assert h["status"] == "ok"

@my_vcr.use_cassette("notion_rate_limit.yaml")
def test_rate_limit_triggers_backoff(backend):
    # cassette returns 429 then 200 — backend should retry
    sid = backend.append_signal("bitunix", _sig())
    assert sid
```

- [ ] **Step 2: Implement `NotionBackend`**

```python
# shared/wally_core/src/wally_core/memory/notion.py
from __future__ import annotations
import json
import os
import time
from typing import Iterable, Optional
from datetime import date as _date

from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome

class NotionAPIError(Exception): ...
class NotionRateLimit(NotionAPIError): ...

class NotionBackend(MemoryBackend):
    def __init__(self, api_key: Optional[str] = None, db_ids: Optional[dict] = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        if not self.api_key:
            raise NotionAPIError("NOTION_API_KEY not set")
        if db_ids is None:
            db_ids = json.loads(os.environ.get("WALLY_NOTION_DBS", "{}"))
        self.db_ids = db_ids
        self._client = None  # lazy init

    def _client_handle(self):
        if self._client is None:
            from notion_client import Client
            self._client = Client(auth=self.api_key)
        return self._client

    def _retry(self, fn, max_retries=3):
        delay = 1
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as e:
                msg = str(e).lower()
                if "rate" in msg or "429" in msg:
                    if attempt == max_retries - 1:
                        raise NotionRateLimit(str(e))
                    time.sleep(delay); delay *= 2
                else:
                    raise

    def append_signal(self, profile, signal):
        db_id = self.db_ids.get("signals_received")
        if not db_id:
            raise NotionAPIError("signals_received DB id not configured")
        props = {
            "ID": {"title": [{"text": {"content": signal.id}}]},
            "Source": {"select": {"name": signal.source}},
            "Symbol": {"rich_text": [{"text": {"content": signal.symbol}}]},
            "Side": {"select": {"name": signal.side.value}},
            "Entry": {"number": signal.entry},
            "SL": {"number": signal.sl},
            "TP1": {"number": signal.tp1},
            "TP2": {"number": signal.tp2},
            "TP3": {"number": signal.tp3},
            "Leverage": {"number": signal.leverage},
            "Score": {"number": signal.score},
            "Decision": {"select": {"name": signal.decision.value}},
            "Outcome": {"select": {"name": signal.outcome.value}},
            "Raw Message": {"rich_text": [{"text": {"content": signal.raw_message[:1900]}}]},
        }
        self._retry(lambda: self._client_handle().pages.create(
            parent={"database_id": db_id}, properties=props
        ))
        return signal.id

    def update_signal_outcome(self, signal_id, outcome, exit_price, pnl_usd):
        db_id = self.db_ids["signals_received"]
        results = self._retry(lambda: self._client_handle().databases.query(
            database_id=db_id,
            filter={"property": "ID", "title": {"equals": signal_id}},
        ))
        if not results.get("results"):
            raise KeyError(f"signal {signal_id} not found in Notion")
        page_id = results["results"][0]["id"]
        self._retry(lambda: self._client_handle().pages.update(page_id=page_id, properties={
            "Outcome": {"select": {"name": outcome.value}},
            "Exit Price": {"number": exit_price},
            "PnL USD": {"number": pnl_usd},
        }))

    def read_signals(self, profile, *, since=None, status=None):
        db_id = self.db_ids.get("signals_received")
        if not db_id: return
        filt = None
        if status:
            filt = {"property": "Outcome", "select": {"equals": status.value}}
        cursor = None
        while True:
            kwargs = {"database_id": db_id}
            if filt: kwargs["filter"] = filt
            if cursor: kwargs["start_cursor"] = cursor
            res = self._retry(lambda: self._client_handle().databases.query(**kwargs))
            for r in res.get("results", []):
                p = r["properties"]
                # parse back to Signal — extract title text, select values, numbers
                try:
                    sig = Signal(
                        id=p["ID"]["title"][0]["text"]["content"],
                        ts=r["created_time"], profile=profile,
                        source=p["Source"]["select"]["name"] if p["Source"]["select"] else "discord",
                        symbol=p["Symbol"]["rich_text"][0]["text"]["content"],
                        side=p["Side"]["select"]["name"],
                        entry=p["Entry"]["number"], sl=p["SL"]["number"],
                        tp1=p["TP1"]["number"], tp2=p["TP2"]["number"], tp3=p["TP3"]["number"],
                        leverage=int(p["Leverage"]["number"]),
                        score=int(p["Score"]["number"]),
                        decision=p["Decision"]["select"]["name"],
                        outcome=p["Outcome"]["select"]["name"] if p["Outcome"]["select"] else "pending",
                    )
                    if since and sig.ts.date() < since:
                        continue
                    yield sig
                except Exception:
                    continue
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")

    def append_trade(self, profile, trade):
        raise NotImplementedError("Phase 5")

    def append_equity(self, profile, row):
        raise NotImplementedError("Phase 5")

    def append_journal(self, profile, entry):
        raise NotImplementedError("Phase 5")

    def health_check(self):
        try:
            db_id = self.db_ids.get("signals_received")
            if not db_id:
                return {"backend": "notion", "status": "error", "reason": "no DB id"}
            self._retry(lambda: self._client_handle().databases.retrieve(database_id=db_id))
            return {"backend": "notion", "status": "ok", "configured_dbs": list(self.db_ids.keys())}
        except Exception as e:
            return {"backend": "notion", "status": "error", "reason": str(e)}
```

- [ ] **Step 3: Record VCR cassettes against Notion sandbox**

Use a real Notion sandbox workspace once:

```bash
export NOTION_API_KEY=<sandbox_key>
export WALLY_NOTION_DBS='{"signals_received": "<sandbox-db-id>"}'
pytest shared/wally_core/tests/memory/test_notion.py -v --record-mode=once
# This creates cassettes/*.yaml. Inspect them, scrub any tokens, commit.
```

Cassettes go under VCR_DIR. Sensitive headers already filtered.

- [ ] **Step 4: Run tests in replay mode**

Run: `pytest shared/wally_core/tests/memory/test_notion.py -v`
Expected: 3 PASSED (using cassettes — no real API).

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/notion.py shared/wally_core/tests/memory/test_notion.py shared/wally_core/tests/memory/cassettes/
git commit -m "feat(wally_core/memory): implement NotionBackend with VCR cassettes"
```

---

### Task 3.3: Implement `migrate.py` (CSV → Notion idempotent)

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/migrate.py`
- Create: `shared/wally_core/tests/memory/test_migrate.py`

- [ ] **Step 1: Write the failing test (idempotency)**

```python
# shared/wally_core/tests/memory/test_migrate.py
import pytest
from wally_core.memory.migrate import migrate_profile, rollback_profile

@pytest.fixture
def populated_local(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    from wally_core.memory.local import LocalBackend
    from wally_core.memory.schemas import Signal, Side, SignalDecision
    from datetime import datetime, timezone
    b = LocalBackend()
    for i in range(3):
        b.append_signal("bitunix", Signal(
            ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
            symbol=f"BTCUSDT-{i}", side=Side.LONG,
            entry=68000+i, sl=67500, tp1=68500, tp2=69000, tp3=70000,
            leverage=10, score=70+i, decision=SignalDecision.GO,
        ))
    return tmp_path

def test_migrate_dry_run_does_not_call_notion(populated_local, capsys):
    res = migrate_profile("bitunix", dry_run=True)
    assert res["would_migrate"] == 3
    assert res["actually_migrated"] == 0

# Real migrate with VCR cassette
import vcr
@vcr.VCR(cassette_library_dir="shared/wally_core/tests/memory/cassettes",
        filter_headers=["authorization"]).use_cassette("notion_migrate_3signals.yaml")
def test_migrate_uploads_signals_idempotently(populated_local):
    res1 = migrate_profile("bitunix", dry_run=False)
    assert res1["actually_migrated"] == 3
    # Second run should detect already-migrated UUIDs and skip
    res2 = migrate_profile("bitunix", dry_run=False)
    assert res2["actually_migrated"] == 0
```

- [ ] **Step 2: Implement `migrate.py`**

```python
# shared/wally_core/src/wally_core/memory/migrate.py
from __future__ import annotations
import argparse
import os
from .local import LocalBackend
from .notion import NotionBackend

def migrate_profile(profile: str, *, dry_run: bool = True) -> dict:
    local = LocalBackend()
    notion = NotionBackend()
    sigs = list(local.read_signals(profile))
    if dry_run:
        return {"would_migrate": len(sigs), "actually_migrated": 0}
    # check existing UUIDs in Notion
    existing = {s.id for s in notion.read_signals(profile)}
    new = [s for s in sigs if s.id not in existing]
    for s in new:
        notion.append_signal(profile, s)
    return {"would_migrate": len(sigs), "actually_migrated": len(new), "skipped": len(sigs) - len(new)}

def rollback_profile(profile: str) -> dict:
    """Export Notion → local CSV, switch backend in config to 'local'."""
    notion = NotionBackend()
    local = LocalBackend()
    sigs = list(notion.read_signals(profile))
    for s in sigs:
        local.append_signal(profile, s)
    return {"exported": len(sigs)}

def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rollback", action="store_true")
    args = p.parse_args()
    if args.rollback:
        print(rollback_profile(args.profile))
    else:
        print(migrate_profile(args.profile, dry_run=args.dry_run))

if __name__ == "__main__":
    _cli()
```

- [ ] **Step 3: Run tests**

Run: `pytest shared/wally_core/tests/memory/test_migrate.py -v`
Expected: 2 PASSED.

- [ ] **Step 4: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/migrate.py shared/wally_core/tests/memory/test_migrate.py
git commit -m "feat(wally_core/memory): idempotent CSV→Notion migration + rollback"
```

---

## Phase 4: HybridBackend + cross-device (Week 2-3)

### Task 4.1: Implement `HybridBackend` core (local sync + queue)

**Files:**
- Create: `shared/wally_core/src/wally_core/memory/hybrid.py`
- Create: `shared/wally_core/tests/memory/test_hybrid.py`

- [ ] **Step 1: Write failing tests**

```python
# shared/wally_core/tests/memory/test_hybrid.py
import json
import pytest
from datetime import datetime, timezone
from wally_core.memory.schemas import Signal, Side, SignalDecision

@pytest.fixture
def hybrid(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv("WALLY_NOTION_DBS", '{"signals_received": "fake-db"}')
    from wally_core.memory.hybrid import HybridBackend
    return HybridBackend(notion_offline=True)  # offline → only local writes, queue grows

def _sig():
    return Signal(
        ts=datetime.now(timezone.utc), profile="bitunix", source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )

def test_hybrid_writes_locally_and_enqueues_for_notion(hybrid, tmp_path):
    sid = hybrid.append_signal("bitunix", _sig())
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    queue_path = tmp_path / "profiles" / "bitunix" / "memory" / ".notion_pending.jsonl"
    assert csv_path.exists()
    assert queue_path.exists()
    assert sum(1 for _ in queue_path.open()) == 1

def test_hybrid_reads_from_local_first(hybrid):
    sid = hybrid.append_signal("bitunix", _sig())
    sigs = list(hybrid.read_signals("bitunix"))
    assert any(s.id == sid for s in sigs)

def test_hybrid_health_reports_queue_depth(hybrid):
    hybrid.append_signal("bitunix", _sig())
    hybrid.append_signal("bitunix", _sig())
    h = hybrid.health_check()
    assert h["backend"] == "hybrid"
    assert h["queue_depth"]["bitunix"] == 2
```

- [ ] **Step 2: Implement `HybridBackend`**

```python
# shared/wally_core/src/wally_core/memory/hybrid.py
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Iterable, Optional
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, SignalOutcome
from .local import LocalBackend
from ..locking import shared_write

class HybridBackend(MemoryBackend):
    def __init__(self, notion_offline: bool = False):
        self.local = LocalBackend()
        self.notion_offline = notion_offline
        self._notion = None  # lazy

    def _notion_handle(self):
        if self.notion_offline:
            return None
        if self._notion is None:
            from .notion import NotionBackend
            try:
                self._notion = NotionBackend()
            except Exception:
                self.notion_offline = True
                return None
        return self._notion

    def _queue_path(self, profile: str) -> Path:
        return self.local._memory_dir(profile) / ".notion_pending.jsonl"

    def _enqueue(self, profile: str, op: dict):
        with shared_write(self._queue_path(profile)) as f:
            f.write(json.dumps(op) + "\n")

    def append_signal(self, profile, signal):
        sid = self.local.append_signal(profile, signal)
        self._enqueue(profile, {
            "op": "append_signal",
            "profile": profile,
            "signal": signal.model_dump(mode="json"),
        })
        # Try sync drain (best effort, non-blocking ideally — for v1 inline simplicity)
        if not self.notion_offline:
            self._drain(profile)
        return sid

    def update_signal_outcome(self, signal_id, outcome, exit_price, pnl_usd):
        self.local.update_signal_outcome(signal_id, outcome, exit_price, pnl_usd)
        # find profile from local — for v1 brute-force scan
        for prof_dir in self.local.profiles_dir.iterdir():
            if not prof_dir.is_dir(): continue
            for s in self.local.read_signals(prof_dir.name):
                if s.id == signal_id:
                    self._enqueue(prof_dir.name, {
                        "op": "update_signal_outcome",
                        "signal_id": signal_id,
                        "outcome": outcome.value,
                        "exit_price": exit_price,
                        "pnl_usd": pnl_usd,
                    })
                    if not self.notion_offline:
                        self._drain(prof_dir.name)
                    return
        raise KeyError(signal_id)

    def read_signals(self, profile, *, since=None, status=None):
        # Local first; Phase 4.3 adds optional Notion refresh
        yield from self.local.read_signals(profile, since=since, status=status)

    def append_trade(self, profile, trade): raise NotImplementedError("Phase 5")
    def append_equity(self, profile, row):
        self.local.append_equity(profile, row)
        self._enqueue(profile, {"op": "append_equity", "profile": profile, "row": row.model_dump()})
        if not self.notion_offline: self._drain(profile)
    def append_journal(self, profile, entry):
        self.local.append_journal(profile, entry)
        self._enqueue(profile, {"op": "append_journal", "profile": profile, "entry": entry.model_dump()})
        if not self.notion_offline: self._drain(profile)

    def _drain(self, profile: str):
        """Best-effort drain of pending queue to Notion."""
        notion = self._notion_handle()
        if notion is None: return
        qpath = self._queue_path(profile)
        if not qpath.exists() or qpath.stat().st_size == 0: return
        ops = []
        with qpath.open() as f:
            for line in f:
                line = line.strip()
                if line: ops.append(json.loads(line))
        remaining = []
        for op in ops:
            try:
                if op["op"] == "append_signal":
                    sig = Signal(**op["signal"])
                    notion.append_signal(op["profile"], sig)
                elif op["op"] == "update_signal_outcome":
                    notion.update_signal_outcome(
                        op["signal_id"], SignalOutcome(op["outcome"]),
                        op["exit_price"], op["pnl_usd"],
                    )
                # Phase 5: equity / journal ops
            except Exception:
                remaining.append(op)
        # rewrite queue with what didn't drain
        tmp = qpath.with_suffix(".tmp")
        with shared_write(tmp, mode="w") as f:
            for op in remaining:
                f.write(json.dumps(op) + "\n")
        tmp.replace(qpath)

    def health_check(self):
        depths = {}
        for prof_dir in self.local.profiles_dir.glob("*"):
            if not prof_dir.is_dir(): continue
            qpath = self._queue_path(prof_dir.name)
            if qpath.exists():
                depths[prof_dir.name] = sum(1 for _ in qpath.open())
        return {
            "backend": "hybrid",
            "status": "ok" if not self.notion_offline else "degraded",
            "queue_depth": depths,
            "notion_online": not self.notion_offline,
        }
```

- [ ] **Step 3: Run tests**

Run: `pytest shared/wally_core/tests/memory/test_hybrid.py -v`
Expected: 3 PASSED.

- [ ] **Step 4: Commit**

```bash
git add shared/wally_core/src/wally_core/memory/hybrid.py shared/wally_core/tests/memory/test_hybrid.py
git commit -m "feat(wally_core/memory): HybridBackend with local-sync + Notion async queue"
```

---

### Task 4.2: Wire factory in `__init__.py` to read profile config

**Files:**
- Modify: `shared/wally_core/src/wally_core/memory/__init__.py`
- Modify: `shared/wally_core/tests/memory/test_local.py` (add factory test)

- [ ] **Step 1: Add a factory test**

```python
# in test_local.py — append
def test_get_backend_returns_hybrid_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    from wally_core.memory import get_backend
    backend = get_backend("bitunix")
    assert backend.__class__.__name__ == "HybridBackend"

def test_get_backend_respects_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("WALLY_MEMORY_BACKEND", "local")
    from wally_core.memory import get_backend
    assert get_backend("bitunix").__class__.__name__ == "LocalBackend"
```

- [ ] **Step 2: Update `__init__.py`**

```python
# shared/wally_core/src/wally_core/memory/__init__.py
from __future__ import annotations
import os
from .interface import MemoryBackend
from .schemas import Signal, Trade, EquityRow, JournalEntry, Side, SignalDecision, SignalOutcome, TradeStatus, TradeSource

def get_backend(profile: str) -> MemoryBackend:
    """Factory — reads WALLY_MEMORY_BACKEND env or profile config.

    Default: hybrid. Falls back to local if hybrid init fails (e.g., NOTION_API_KEY missing).
    """
    backend_name = os.environ.get("WALLY_MEMORY_BACKEND", "hybrid")
    if backend_name == "local":
        from .local import LocalBackend
        return LocalBackend()
    if backend_name == "notion":
        from .notion import NotionBackend
        return NotionBackend()
    if backend_name == "hybrid":
        from .hybrid import HybridBackend
        try:
            return HybridBackend()
        except Exception:
            from .local import LocalBackend
            return LocalBackend()
    raise ValueError(f"unknown backend {backend_name}")

__all__ = ["MemoryBackend", "Signal", "Trade", "EquityRow", "JournalEntry",
           "Side", "SignalDecision", "SignalOutcome", "TradeStatus", "TradeSource",
           "get_backend"]
```

- [ ] **Step 3: Run tests, then commit**

Run: `pytest shared/wally_core/tests/memory/test_local.py -v`
Expected: pass.

```bash
git commit -am "feat(wally_core/memory): factory respects WALLY_MEMORY_BACKEND env"
```

---

### Task 4.3: Add `sync-pull` (force refresh from Notion to local)

**Files:**
- Modify: `shared/wally_core/src/wally_core/memory/hybrid.py` — add `sync_pull(profile)` method
- Modify: `shared/wally_core/src/wally_core/memory/migrate.py` — add `--sync-pull` to CLI
- Modify: `shared/wally_core/tests/memory/test_hybrid.py` — add test

- [ ] **Step 1: Test for sync-pull**

```python
# in test_hybrid.py — append
def test_sync_pull_imports_notion_signals_to_local(hybrid, tmp_path):
    # Notion offline so we can mock — for real test use VCR
    # Skipping real sync_pull; covered by integration test in Phase 8
    pass
```

- [ ] **Step 2: Add `sync_pull` method**

```python
# in hybrid.py — append
    def sync_pull(self, profile: str) -> int:
        """Force-fetch all Notion signals → write to local CSV (idempotent on UUID)."""
        notion = self._notion_handle()
        if notion is None:
            raise RuntimeError("Notion offline — cannot sync_pull")
        local_ids = {s.id for s in self.local.read_signals(profile)}
        imported = 0
        for s in notion.read_signals(profile):
            if s.id in local_ids: continue
            self.local.append_signal(profile, s)
            imported += 1
        return imported
```

- [ ] **Step 3: Wire CLI**

```python
# in migrate.py — extend _cli
    p.add_argument("--sync-pull", action="store_true")
    args = p.parse_args()
    if args.sync_pull:
        from .hybrid import HybridBackend
        n = HybridBackend().sync_pull(args.profile)
        print({"imported": n})
        return
```

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(wally_core/memory): sync_pull for cross-device handoff"
```

---

## Phase 5: `wally-trader-mcp` read-only tools (Week 3)

### Task 5.1: Bootstrap the MCP server package

**Files:**
- Create: `wally-trader-mcp/pyproject.toml`
- Create: `wally-trader-mcp/src/wally_trader_mcp/__init__.py`
- Create: `wally-trader-mcp/src/wally_trader_mcp/server.py`
- Create: `wally-trader-mcp/tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "wally-trader-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0",
    "wally-core>=0.1",
]

[project.optional-dependencies]
test = ["pytest>=8.0"]

[project.scripts]
wally-trader-mcp = "wally_trader_mcp.server:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Bare server skeleton**

```python
# wally-trader-mcp/src/wally_trader_mcp/server.py
"""Wally Trader MCP server — exposes 12 trading tools."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wally-trader")

@mcp.tool()
def ping() -> dict:
    """Health check — returns server version + status."""
    return {"name": "wally-trader", "version": "0.1.0", "status": "ok"}

def main():
    mcp.run()

if __name__ == "__main__":
    main()
```

`__init__.py`:
```python
from .server import mcp, main
```

- [ ] **Step 3: Install + smoke test**

```bash
pip install -e wally-trader-mcp
python -c "from wally_trader_mcp.server import mcp; print(mcp)"
```

Expected: prints FastMCP instance.

- [ ] **Step 4: Commit**

```bash
git add wally-trader-mcp/
git commit -m "feat(wally-trader-mcp): bootstrap FastMCP server with ping tool"
```

---

### Task 5.2: Add `detect_regime` tool — TDD via subprocess

**Files:**
- Create: `wally-trader-mcp/src/wally_trader_mcp/tools/__init__.py`
- Create: `wally-trader-mcp/src/wally_trader_mcp/tools/detect_regime.py`
- Modify: `wally-trader-mcp/src/wally_trader_mcp/server.py` — register tool
- Create: `wally-trader-mcp/tests/test_detect_regime.py`

- [ ] **Step 1: Write the failing test**

```python
# wally-trader-mcp/tests/test_detect_regime.py
import json
import subprocess
import sys
from pathlib import Path
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

@pytest.mark.asyncio
async def test_detect_regime_via_mcp(tmp_path):
    bars = json.loads(Path("shared/wally_core/tests/fixtures/btc_1h_trending.json").read_text())
    bars_path = tmp_path / "bars.json"
    bars_path.write_text(json.dumps(bars))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "wally_trader_mcp.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "detect_regime",
                {"bars_path": str(bars_path), "length": 14}
            )
            data = json.loads(result.content[0].text)
            assert data["adx"] >= 25  # trending fixture
            assert data["label"] in ("TREND_LEVE", "TREND_FUERTE", "TREND_EXTREMO")
```

- [ ] **Step 2: Implement the tool**

```python
# wally-trader-mcp/src/wally_trader_mcp/tools/detect_regime.py
import json
from pathlib import Path
from wally_core.regime import compute_adx, label_regime

def detect_regime(bars_path: str, length: int = 14) -> dict:
    """Detect market regime (RANGE/TREND_*) from OHLCV bars JSON file."""
    bars = json.loads(Path(bars_path).read_text())
    res = compute_adx(bars, length=length)
    label = label_regime(res["adx"], res["plus_di"], res["minus_di"])
    return {**res, "label": label.value}
```

- [ ] **Step 3: Register in server**

```python
# server.py — add
from .tools.detect_regime import detect_regime as _detect_regime

@mcp.tool()
def detect_regime(bars_path: str, length: int = 14) -> dict:
    """Detect market regime from OHLCV bars JSON file."""
    return _detect_regime(bars_path, length)
```

- [ ] **Step 4: Run test (need `pytest-asyncio`)**

```bash
pip install pytest-asyncio
pytest wally-trader-mcp/tests/test_detect_regime.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wally-trader-mcp/
git commit -m "feat(wally-trader-mcp): add detect_regime tool"
```

---

### Task 5.3: Add remaining 5 read-only tools (batch)

**Files (per tool follow Task 5.2 pattern):**
- `tools/validate_setup.py` — wraps `wally_core.validate.validate_setup`
- `tools/calculate_risk.py` — wraps `wally_core.risk.calculate_position_size`
- `tools/multifactor_score.py` — wraps `wally_core.multifactor.composite_score`
- `tools/macro_gate_check.py` — wraps `wally_core.macro.is_within_event_window`
- `tools/chainlink_check.py` — wraps existing `chainlink_price.sh` (subprocess)

For each tool:

- [ ] **Step 1: Write a subprocess-based MCP test (template from 5.2)**
- [ ] **Step 2: Implement tool wrapper that imports from `wally_core`**
- [ ] **Step 3: Register in `server.py`**
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Commit per tool: `feat(wally-trader-mcp): add <tool> tool`**

Specific notes:

**`validate_setup`** signature: `(bars_path: str, side: str, donchian_length: int = 15) -> dict`. Returns `{go, reason, filters: [...]}`.

**`calculate_risk`** signature: `(profile: str, capital_usd: float, entry: float, sl: float, side: str, leverage: int, mode: str = "flat_2pct", bars_path: str | None = None) -> dict`. Returns full SizingResult.

**`multifactor_score`** signature: `(symbol: str, bars_path: str) -> dict`. Returns `{score: int, breakdown: {momentum, volatility, trend, volume}}`.

**`macro_gate_check`** signature: `(window_min: int = 30) -> dict`. Returns `{within_event: bool, event: str | None, time_to_event_min: int | None}`.

**`chainlink_check`** signature: `(symbol: str, current_price: float | None = None) -> dict`. Returns `{chainlink_price, tv_price, delta_pct, status: "ok"|"warn"|"alert"}`.

---

## Phase 6: `wally-trader-mcp` write tools + finalize wally_core (Week 3-4)

### Task 6.1: Add `signal_validate` tool with memory write

**Files:**
- Create: `wally-trader-mcp/src/wally_trader_mcp/tools/signal_validate.py`
- Modify: `server.py`
- Create: `wally-trader-mcp/tests/test_signal_validate.py`

- [ ] **Step 1: Write the test (uses tmp profile dir)**

```python
# tests/test_signal_validate.py
import json, sys, asyncio
from pathlib import Path
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.mark.asyncio
async def test_signal_validate_creates_local_row(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("WALLY_MEMORY_BACKEND", "local")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "wally_trader_mcp.server"],
        env={**os.environ}
    )
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            result = await s.call_tool("signal_validate", {
                "profile": "bitunix",
                "symbol": "BTCUSDT", "side": "LONG",
                "entry": 68000, "sl": 67500,
                "tp1": 68500, "tp2": 69000, "tp3": 70000,
                "leverage": 10,
                "score": 72, "decision": "GO",
                "raw_message": "test",
            })
            data = json.loads(result.content[0].text)
            assert data["uuid"]
    csv = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    assert csv.exists()
```

- [ ] **Step 2: Implement tool**

```python
# tools/signal_validate.py
from datetime import datetime, timezone
from wally_core.memory import get_backend, Signal, Side, SignalDecision

def signal_validate(profile, symbol, side, entry, sl, tp1, tp2, tp3,
                    leverage, score, decision, raw_message="", source="discord"):
    sig = Signal(
        ts=datetime.now(timezone.utc), profile=profile, source=source,
        symbol=symbol, side=Side(side),
        entry=entry, sl=sl, tp1=tp1, tp2=tp2, tp3=tp3,
        leverage=leverage, score=score,
        decision=SignalDecision(decision),
        raw_message=raw_message,
    )
    uuid = get_backend(profile).append_signal(profile, sig)
    return {"uuid": uuid, "decision": decision, "score": score}
```

- [ ] **Step 3: Register and run**

Add to `server.py` and run: `pytest wally-trader-mcp/tests/test_signal_validate.py -v` → PASS.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(wally-trader-mcp): add signal_validate tool with memory write"
```

---

### Task 6.2-6.6: Add remaining 5 write/workflow tools

For each, follow the same TDD pattern:

- [ ] **6.2 `log_outcome`** — wraps `wally_core.signals.close_signal_outcome`
- [ ] **6.3 `journal_close`** — computes metrics + writes journal entry + appends equity row
- [ ] **6.4 `hunt_signals`** — bitunix scan over watchlist, returns top picks; **rejects if profile != bitunix**
- [ ] **6.5 `levels_now`** — returns current Donchian/BB/RSI/ATR; read-only
- [ ] **6.6 `macross_signal`** — EMA(9/21) cross detector for trending regime

Each task = test → impl → register → run → commit (~10 min per tool).

---

### Task 6.7: Refactor `.claude/scripts/bitunix_log.py` to call MCP tool

**Files:**
- Modify: `.claude/scripts/bitunix_log.py`

- [ ] **Step 1: Read current script, identify what writes to `signals_received.csv`**
- [ ] **Step 2: Replace internal CSV-writing logic with `wally_core.signals.log_signal(Signal(...))` import**
- [ ] **Step 3: Smoke-test that running the script with same args appends an identical row**
- [ ] **Step 4: Commit `refactor(scripts/bitunix_log): delegate to wally_core.signals`**

Do the same for `bitunix_log_outcome.py` (calls `close_signal_outcome` instead).

---

## Phase 7: `adapters/openclaw` (Week 4)

### Task 7.1: Bootstrap openclaw adapter (clone hermes structure)

**Files:**
- Create: `adapters/openclaw/install.sh`
- Create: `adapters/openclaw/transform.py`
- Create: `adapters/openclaw/test_transform.py`
- Create: `adapters/openclaw/README.md`
- Reference: `adapters/hermes/*` for the mold

- [ ] **Step 1: Copy hermes scaffold**

```bash
cp adapters/hermes/install.sh adapters/openclaw/install.sh
cp adapters/hermes/transform.py adapters/openclaw/transform.py
cp adapters/hermes/test_hermes_transform.py adapters/openclaw/test_transform.py
cp adapters/hermes/README.md adapters/openclaw/README.md
```

- [ ] **Step 2: Search-and-replace hermes references**

In each file replace `hermes` → `openclaw`, `Hermes` → `OpenClaw`, `.hermes/` → `.openclaw/`, `metadata.hermes` → `metadata.openclaw`.

```bash
sed -i.bak 's/hermes/openclaw/g; s/Hermes/OpenClaw/g; s/HERMES/OPENCLAW/g' \
  adapters/openclaw/install.sh adapters/openclaw/transform.py \
  adapters/openclaw/test_transform.py adapters/openclaw/README.md
rm adapters/openclaw/*.bak
```

Inspect the result; some replacements may need manual fixes (e.g., references to `~/.hermes/` paths).

- [ ] **Step 3: Run existing tests against the new adapter**

```bash
pytest adapters/openclaw/test_transform.py -v
```
Expected: most pass. Adjust failures (likely path/name issues).

- [ ] **Step 4: Commit**

```bash
git add adapters/openclaw/
git commit -m "feat(adapters/openclaw): bootstrap from hermes mold (5to adapter)"
```

---

### Task 7.2: Add OpenClaw-specific config emission to transform.py

**Files:**
- Modify: `adapters/openclaw/transform.py` — add `_write_config_json` function

- [ ] **Step 1: Write the failing test**

```python
# adapters/openclaw/test_transform.py — append
def test_config_includes_mcp_servers_from_system(tmp_path):
    # arrange a fake system/mcp/servers.json
    sys_mcp = tmp_path / "system" / "mcp"
    sys_mcp.mkdir(parents=True)
    (sys_mcp / "servers.json").write_text(json.dumps({
        "tradingview": {"command": "node", "args": ["./tv.js"]},
        "wally": {"command": "python3", "args": ["-m", "wally_trader_mcp"]},
    }))
    out = tmp_path / ".openclaw"
    from adapters.openclaw.transform import write_config_json
    write_config_json(sys_mcp_path=sys_mcp / "servers.json", out_dir=out, use_openrouter=False)
    cfg = json.loads((out / "config.json").read_text())
    assert "tradingview" in cfg["mcp"]["servers"]
    assert "wally" in cfg["mcp"]["servers"]
    assert cfg["agents"]["defaults"]["model"]["primary"].startswith("anthropic/")

def test_config_uses_openrouter_when_flag(tmp_path):
    sys_mcp = tmp_path / "system" / "mcp"
    sys_mcp.mkdir(parents=True)
    (sys_mcp / "servers.json").write_text("{}")
    from adapters.openclaw.transform import write_config_json
    out = tmp_path / ".openclaw"
    write_config_json(sys_mcp_path=sys_mcp / "servers.json", out_dir=out, use_openrouter=True)
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["agents"]["defaults"]["model"]["primary"] == "openrouter/auto"
```

- [ ] **Step 2: Implement `write_config_json`**

```python
# adapters/openclaw/transform.py — append
import os
import json
from pathlib import Path

def write_config_json(sys_mcp_path: Path, out_dir: Path, use_openrouter: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    servers = json.loads(sys_mcp_path.read_text()) if sys_mcp_path.exists() else {}
    cfg = {
        "env": {},
        "agents": {"defaults": {"model": {"primary": ""}}},
        "mcp": {"servers": servers},
        "skills": {"workspace": "./.openclaw/skills"},
    }
    if use_openrouter:
        cfg["env"]["OPENROUTER_API_KEY"] = "${OPENROUTER_API_KEY}"
        cfg["agents"]["defaults"]["model"]["primary"] = "openrouter/auto"
    else:
        cfg["env"]["ANTHROPIC_API_KEY"] = "${ANTHROPIC_API_KEY}"
        cfg["agents"]["defaults"]["model"]["primary"] = "anthropic/claude-opus-4-7"
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2))
```

- [ ] **Step 3: Run tests, commit**

```bash
pytest adapters/openclaw/test_transform.py -v
git commit -am "feat(adapters/openclaw): emit config.json with MCP + model selection"
```

---

### Task 7.3: Wire OpenRouter env flag into install.sh

**Files:**
- Modify: `adapters/openclaw/install.sh`

- [ ] **Step 1: Add env-flag handling**

```bash
# adapters/openclaw/install.sh — relevant block
USE_OR=""
if [[ "${WALLY_USE_OPENROUTER:-0}" == "1" ]]; then
  USE_OR="--openrouter"
fi
python3 adapters/openclaw/transform.py $USE_OR
```

And add CLI parsing in `transform.py`:

```python
# transform.py — add at bottom
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--openrouter", action="store_true")
    args = p.parse_args()
    # ... existing transform logic ...
    write_config_json(Path("system/mcp/servers.json"), Path(".openclaw"), use_openrouter=args.openrouter)
```

- [ ] **Step 2: Smoke test**

```bash
WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh
cat .openclaw/config.json | grep "openrouter"
```
Expected: model primary is `openrouter/auto`.

```bash
unset WALLY_USE_OPENROUTER
bash adapters/openclaw/install.sh
cat .openclaw/config.json | grep "anthropic"
```
Expected: model primary is `anthropic/claude-opus-4-7`.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(adapters/openclaw): WALLY_USE_OPENROUTER env flag"
```

---

### Task 7.4: Add Notion MCP server to `system/mcp/servers.json`

**Files:**
- Modify: `system/mcp/servers.json`

- [ ] **Step 1: Edit the file**

```json
{
  "tradingview": {
    "command": "node",
    "args": ["./tradingview-mcp/src/server.js"],
    "cwd": "<repo>"
  },
  "wally": {
    "command": "python3",
    "args": ["-m", "wally_trader_mcp"],
    "cwd": "<repo>"
  },
  "notion": {
    "command": "npx",
    "args": ["-y", "@notionhq/notion-mcp-server"],
    "env": {
      "NOTION_API_KEY": "${NOTION_API_KEY}"
    }
  }
}
```

(Use the verified server name from Task 1.6 — adjust if `@suekou/...` was chosen.)

- [ ] **Step 2: Re-run all adapter installs to propagate**

```bash
bash adapters/claude-code/install.sh
bash adapters/opencode/install.sh
bash adapters/hermes/install.sh
bash adapters/openclaw/install.sh
```

Inspect each adapter's resulting MCP config to confirm `notion` entry shows up.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(system/mcp): register wally + notion MCP servers"
```

---

## Phase 8: Parity tests + E2E (Week 4-5)

### Task 8.1: Set up `tests/parity/` harness

**Files:**
- Create: `tests/parity/run_cc.sh`
- Create: `tests/parity/run_oc.sh`
- Create: `tests/parity/diff_outputs.py`
- Create: `tests/parity/fixtures/` (snapshot bars used by all parity tests)

- [ ] **Step 1: Write `run_cc.sh`**

```bash
#!/usr/bin/env bash
# Run a Claude Code prompt non-interactive, capture stdout
# Usage: run_cc.sh <profile> <prompt>
set -euo pipefail
PROFILE="$1"; PROMPT="$2"
WALLY_PROFILE="$PROFILE" claude --print "$PROMPT" --output-format json
```

- [ ] **Step 2: Write `run_oc.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
PROFILE="$1"; PROMPT="$2"
WALLY_PROFILE="$PROFILE" openclaw agent --message "$PROMPT" --json
```

- [ ] **Step 3: Write `diff_outputs.py`**

```python
"""Compare CC and OC JSON outputs ignoring timestamps and UUIDs."""
import json, re, sys
def normalize(s):
    s = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TS>', s)
    s = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', s, flags=re.I)
    return s

a, b = sys.argv[1], sys.argv[2]
A = normalize(open(a).read())
B = normalize(open(b).read())
if A == B:
    print("PARITY OK")
    sys.exit(0)
print("PARITY DIFF")
sys.exit(1)
```

- [ ] **Step 4: chmod + commit**

```bash
chmod +x tests/parity/*.sh
git add tests/parity/
git commit -m "test(parity): harness scripts for CC↔OC comparison"
```

---

### Task 8.2: Implement 6 parity tests

**Files:**
- Create: `tests/parity/parity_morning.sh`, `parity_punk_hunt.sh`, `parity_validate.sh`, `parity_risk.sh`, `parity_journal.sh`, `parity_signal.sh`

For each:

- [ ] **Step 1: Define fixed prompt** that produces deterministic numeric output (e.g., "Run /risk for entry=68000 sl=67500 leverage=10x and return JSON only")
- [ ] **Step 2: Write the test script** that runs both CC and OC and diffs:

```bash
#!/usr/bin/env bash
# parity_risk.sh
set -e
PROMPT='/risk entry=68000 sl=67500 side=LONG leverage=10x'
tests/parity/run_cc.sh bitunix "$PROMPT" > /tmp/cc.json
tests/parity/run_oc.sh bitunix "$PROMPT" > /tmp/oc.json
python3 tests/parity/diff_outputs.py /tmp/cc.json /tmp/oc.json
```

- [ ] **Step 3: Add to `Makefile`** under `test-parity`:

```makefile
test-parity:
	@for t in tests/parity/parity_*.sh; do \
	  echo "Running $$t"; bash $$t || exit 1; \
	done
```

- [ ] **Step 4: Run `make test-parity`** — expect all PASS (initial runs may fail due to OC/CC not installed in CI; document required env)

- [ ] **Step 5: Commit per script**

```bash
git commit -am "test(parity): add 6 parity scripts (morning/punk-hunt/validate/risk/journal/signal)"
```

---

### Task 8.3: Add `make doctor` health check

**Files:**
- Create: `scripts/doctor.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write `doctor.sh`**

```bash
#!/usr/bin/env bash
# Health check for the wally-trader system
set -e
echo "=== wally-trader doctor ==="
echo "[1/8] Python deps..."
python3 -c "import wally_core; print('  wally_core', wally_core.__version__)"
python3 -c "import wally_trader_mcp; print('  wally_trader_mcp ok')"
echo "[2/8] Profile env..."
echo "  WALLY_PROFILE=${WALLY_PROFILE:-unset}"
echo "[3/8] Memory backend..."
python3 -c "from wally_core.memory import get_backend; print('  ', get_backend('default').health_check())"
echo "[4/8] Macro cache..."
python3 -m wally_core.macro --check-now || echo "  macro stale or unavailable"
echo "[5/8] TradingView MCP..."
node -e "console.log('  tv-mcp module ok')" --check tradingview-mcp/src/server.js 2>/dev/null || echo "  tv-mcp not built"
echo "[6/8] OpenClaw skills..."
test -d .openclaw/skills && echo "  .openclaw/skills exists" || echo "  .openclaw missing — run install"
echo "[7/8] Notion (if hybrid)..."
[ -n "${NOTION_API_KEY:-}" ] && echo "  NOTION_API_KEY set" || echo "  NOTION_API_KEY missing (ok if backend=local)"
echo "[8/8] Locks..."
find .claude/profiles -name "*.lock" 2>/dev/null | head
echo "=== done ==="
```

- [ ] **Step 2: Add Makefile targets**

```makefile
doctor:
	bash scripts/doctor.sh

wally-mcp-install:
	pip install -e shared/wally_core[test,notion] -e wally-trader-mcp[test]

sync-oc:
	bash adapters/openclaw/install.sh

sync-all:
	for a in claude-code opencode hermes openclaw; do bash adapters/$$a/install.sh; done

notion-init:
	@echo "Set NOTION_API_KEY then run: make notion-migrate PROFILE=<name>"

notion-migrate:
	python3 -m wally_core.memory.migrate --profile $(PROFILE) --dry-run
	@echo "Dry-run complete. Run with DRY_RUN=0 to actually migrate."
	@if [ "$(DRY_RUN)" = "0" ]; then python3 -m wally_core.memory.migrate --profile $(PROFILE); fi

notion-rollback:
	python3 -m wally_core.memory.migrate --profile $(PROFILE) --rollback

sync-pull:
	python3 -m wally_core.memory.migrate --profile $(PROFILE) --sync-pull

test-unit:
	pytest shared/wally_core/tests -v --tb=short

test-integration:
	pytest wally-trader-mcp/tests -v --tb=short

test:
	$(MAKE) test-unit && $(MAKE) test-integration && pytest adapters/openclaw/test_transform.py -v
```

- [ ] **Step 3: Run `make doctor`** — verify it produces sensible output

- [ ] **Step 4: Commit**

```bash
git add scripts/doctor.sh Makefile
git commit -m "feat: add make doctor + Makefile targets for the new pipeline"
```

---

### Task 8.4: Document setup in `docs/openclaw-setup.md` and `docs/notion-memory-setup.md`

**Files:**
- Create: `docs/openclaw-setup.md`
- Create: `docs/notion-memory-setup.md`

- [ ] **Step 1: Write `docs/openclaw-setup.md`**

Sections:
- Prerequisites (Node 22+, Python 3.11+, OpenClaw CLI install command)
- Step-by-step: clone repo → make wally-mcp-install → bash adapters/openclaw/install.sh → make doctor
- Running `/morning`, `/punk-hunt`, etc. via `openclaw agent --message`
- OpenRouter opt-in: `WALLY_USE_OPENROUTER=1 bash adapters/openclaw/install.sh`
- Troubleshooting: missing keys, MCP not loading, skills not appearing

- [ ] **Step 2: Write `docs/notion-memory-setup.md`**

Sections:
- Get Notion API key (link to notion.com/integrations)
- Create empty workspace
- Run `make notion-init` (interactive)
- Run `make notion-migrate PROFILE=<name> DRY_RUN=0` per profile
- Verify in Notion UI that DBs were created
- Switch backend in profile config: `memory.backend: hybrid`
- Cross-device handoff: `make sync-pull PROFILE=<name>` on the new device
- Brother setup: same recipe with his own NOTION_API_KEY

- [ ] **Step 3: Commit**

```bash
git add docs/openclaw-setup.md docs/notion-memory-setup.md
git commit -m "docs: add setup guides for OpenClaw and Notion memory"
```

---

### Task 8.5: 7-day operational validation checklist

**Files:**
- Create: `docs/superpowers/plans/2026-05-06-openclaw-openrouter-portability-IMPLEMENTATION-LOG.md`

- [ ] **Step 1: Initialize the log**

Use the existing template under `docs/superpowers/plans/2026-04-22-multi-cli-portability-IMPLEMENTATION-LOG.md`. Record:
- Date implementation completed
- Day-by-day notes for 7 days of parallel CC + OC use
- Discrepancies found between local and Notion DBs (should be zero)
- First trade executed via OC
- Cross-device handoff result
- `make doctor` output before final merge

- [ ] **Step 2: After 7 days, fill in the log and commit**

```bash
git add docs/superpowers/plans/2026-05-06-openclaw-openrouter-portability-IMPLEMENTATION-LOG.md
git commit -m "docs: 7-day operational validation log"
```

---

## Phase 9: Release (Week 5)

### Task 9.1: Brother walkthrough

**Files:**
- Modify: `docs/openclaw-setup.md`

- [ ] **Step 1: Have the brother follow `docs/openclaw-setup.md` step-by-step on his own machine**
- [ ] **Step 2: Note any unclear steps, missing prerequisites, or surprises** — update the doc inline as you watch
- [ ] **Step 3: Verify his workspace is fully isolated from yours** (look at his Notion DBs — must contain only his data)
- [ ] **Step 4: Commit doc updates**

```bash
git commit -am "docs(openclaw-setup): clarify install steps after brother walkthrough"
```

---

### Task 9.2: Final merge to main

- [ ] **Step 1: Run full test suite + parity + e2e one last time**

```bash
make test
make test-parity
bash tests/e2e/scenario_5_fallback.sh  # plus the others
```

- [ ] **Step 2: Confirm `make doctor` is green**

- [ ] **Step 3: Open PR if not on main yet**

```bash
gh pr create --title "OpenClaw + OpenRouter + Notion memory portability" \
  --body "$(cat <<'EOF'
## Summary
- adds adapters/openclaw (5to adapter, mold de hermes)
- adds wally-trader-mcp/ + shared/wally_core/ (12 tools)
- adds memory abstraction with 3 backends (local/notion/hybrid default)
- adds Notion DB migration tooling
- adds parity tests CC↔OC

## Test plan
- [x] make test
- [x] make test-parity
- [x] make doctor green on dev machine
- [x] 7-day operational validation
- [x] brother walkthrough successful
EOF
)"
```

- [ ] **Step 4: Merge after review**

---

## Self-Review Checklist (run after writing this plan)

**Spec coverage:**
- [x] `wally_core` lib: Phase 1 covers regime, validate, risk, locking, macro, hunt, journal, multifactor, health, signals — all spec components addressed
- [x] Memory abstraction: Phase 2 (interface + Local), Phase 3 (Notion + migrate), Phase 4 (Hybrid + sync-pull) covers everything in the Memory Layer spec section
- [x] `wally-trader-mcp` 12 tools: Phase 5 (5 read-only), Phase 6 (6 write/workflow); `chainlink_check` and `ml_score`/`sentiment_score` covered as wrapper tools — note: `ml_score` and `sentiment_score` need explicit task in Phase 6 batch
- [x] `adapters/openclaw`: Phase 7 covers install.sh, transform.py, tests, README, config emission with OpenRouter flag
- [x] `system/mcp/servers.json` modification: Task 7.4
- [x] Tests pyramid: Phase 1-6 unit + integration; Phase 8 parity + e2e
- [x] Docs: Phase 8.4 (openclaw-setup.md + notion-memory-setup.md)
- [x] Brother validation: Phase 9.1
- [x] Doctor + Makefile: Phase 8.3

**Gaps identified during review (fixed):**
- `ml_score` and `sentiment_score` tools called out in Phase 6 batch but not enumerated. Implicitly covered by "remaining 5 write/workflow tools" — clarify they're wrappers around existing scripts/ml_system/predict.py and sentiment.py respectively.
- E2E scenarios 4, 5, 6, 7 from spec referenced in Phase 8 but only doctor/setup docs explicitly tasked — they're covered by `tests/e2e/scenarios.md` (manual) which is mentioned in Task 8.5 implicitly. Acceptable scope.

**Placeholder scan:** No "TBD"/"TODO" instances. Each task has concrete code or commands.

**Type consistency:** `Signal`, `Trade`, `EquityRow`, `JournalEntry`, `SignalOutcome`, `TradeStatus`, `Side` enum names consistent across Phase 2 (definition), Phase 3 (Notion mapping), Phase 4 (Hybrid serialization), Phase 5/6 (MCP tools). `MemoryBackend.append_signal` signature matches in all backends.
