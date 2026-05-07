from wally_core.validate import validate_setup, FilterResult, ValidateResult, Side


def _bar(o, h, l, c, v=100):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def make_bars_long_setup(*, rsi_override=None, no_bb_touch=False, red_close=False):
    """30-bar fixture engineered to satisfy all 4 LONG filters by default.

    Structure:
    - bars[0..14]: flat at 100 (establishes baseline RSI context)
    - bars[15..28]: declining 0.5/bar (99.5..93.0) — drives RSI near 0 (<35)
    - bars[29]: last bar — wick below Donchian-low+BB-lower, green close

    Variants override exactly one filter at a time.
    """
    bars = [_bar(100, 102, 98, 100) for _ in range(15)]

    if rsi_override is not None:
        # Rising bars push RSI to ~100 (well above 35), so rsi_oversold filter fails.
        # Last bar also continues the rising trend — no extreme wick touch needed.
        for _ in range(14):
            bars.append(_bar(100, 105, 99, 104))
        bars.append(_bar(103, 106, 102, 104.5))
    else:
        for i in range(14):
            c = 100 - (i + 1) * 0.5  # 99.5, 99.0, ..., 93.0
            bars.append(_bar(c + 0.2, c + 0.5, c - 0.5, c))

        last_close = 93.2 if not red_close else 92.6
        last_open = 92.8 if not red_close else 93.0
        # no_bb_touch: raise the low above BB lower (~92.05) so bb_touch fails
        last_low = 92.0 if not no_bb_touch else 93.5
        bars.append(_bar(last_open, 93.5, last_low, last_close))

    return bars


def make_bars_short_setup():
    """30-bar rising fixture that satisfies all 4 SHORT filters on bar 29."""
    bars = [_bar(100, 102, 98, 100) for _ in range(15)]
    for i in range(14):
        c = 100 + (i + 1) * 0.5  # 100.5, 101.0, ..., 107.0
        bars.append(_bar(c - 0.2, c + 0.5, c - 0.5, c))
    # Last bar: high wick touches above BB upper (~108.01), RSI ~100 (>65), red close
    bars.append(_bar(107.2, 108.2, 106.8, 107.1))
    return bars


def test_validate_long_all_4_filters_pass():
    bars = make_bars_long_setup()
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
