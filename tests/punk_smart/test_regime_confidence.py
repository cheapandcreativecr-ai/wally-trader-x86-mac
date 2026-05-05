"""Tests for regime_confidence (position sizing helper)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import regime_confidence as rc


def test_ranging_high_quality_size():
    out = rc.compute(pnl_per_trade=2.68, base_margin=4.0)
    assert abs(out["size_mult"] - 1.34) < 0.01
    assert abs(out["margin_usd"] - 5.36) < 0.01
    assert abs(out["notional_10x"] - 53.60) < 0.1


def test_marginal_regime_clipped_at_min():
    out = rc.compute(pnl_per_trade=0.22, base_margin=4.0)
    assert out["size_mult"] == 0.30
    assert abs(out["margin_usd"] - 1.20) < 0.01


def test_huge_pnl_clipped_at_max():
    out = rc.compute(pnl_per_trade=10.0, base_margin=4.0)
    assert out["size_mult"] == 1.50


def test_negative_pnl_clipped_at_min():
    out = rc.compute(pnl_per_trade=-1.5, base_margin=4.0)
    assert out["size_mult"] == 0.30


def test_dynamic_disabled_returns_full_size():
    out = rc.compute(pnl_per_trade=0.5, base_margin=4.0, dynamic=False)
    assert out["size_mult"] == 1.0
    assert abs(out["margin_usd"] - 4.0) < 0.01
