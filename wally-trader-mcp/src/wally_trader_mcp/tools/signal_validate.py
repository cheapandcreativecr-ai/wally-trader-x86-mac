"""signal_validate tool — validate + log a signal to memory backend."""
from datetime import datetime, timezone
from wally_core.memory import get_backend, Signal, Side, SignalDecision


def signal_validate(
    profile: str,
    symbol: str,
    side: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    tp3: float,
    leverage: int,
    score: int,
    decision: str,
    raw_message: str = "",
    source: str = "discord",
) -> dict:
    """Append a validated signal to the configured memory backend.

    Args:
        profile: trading profile (e.g. 'bitunix', 'retail')
        symbol: asset symbol (e.g. 'BTCUSDT')
        side: 'LONG' or 'SHORT'
        entry: entry price
        sl: stop-loss price
        tp1: first take-profit price
        tp2: second take-profit price
        tp3: third take-profit price
        leverage: leverage used (integer)
        score: validation score 0-100
        decision: 'GO', 'NO-GO', or 'WARN'
        raw_message: original signal text (optional)
        source: signal source, e.g. 'discord', 'hunt' (default 'discord')

    Returns:
        dict with uuid, decision, score
    """
    sig = Signal(
        ts=datetime.now(timezone.utc),
        profile=profile,
        source=source,
        symbol=symbol,
        side=Side(side),
        entry=entry,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        leverage=leverage,
        score=score,
        decision=SignalDecision(decision),
        raw_message=raw_message,
    )
    uuid = get_backend(profile).append_signal(profile, sig)
    return {"uuid": uuid, "decision": decision, "score": score}
