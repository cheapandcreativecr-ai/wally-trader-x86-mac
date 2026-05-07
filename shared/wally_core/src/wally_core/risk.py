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
    risk_pct = 0.02 * (1.0 - 0.5 * percentile)
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
        raise NotImplementedError("parity mode arrives in Phase 4 (multi-asset)")
    raise ValueError(f"unknown mode {mode}")
