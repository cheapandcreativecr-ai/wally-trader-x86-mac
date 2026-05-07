"""macro_gate_check tool — check if within macro event window."""
from datetime import datetime, timezone
from wally_core.macro import is_within_event_window


def macro_gate_check(window_min: int = 30) -> dict:
    """Check if currently within ±window_min minutes of a high-impact macro event.

    Returns: {within_event: bool, event: str | None, time_to_event_min: int | None}
    """
    return is_within_event_window(datetime.now(timezone.utc), window_min=window_min)
