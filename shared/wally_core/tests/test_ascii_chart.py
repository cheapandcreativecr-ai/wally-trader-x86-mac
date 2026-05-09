import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts"))

from ascii_chart import render_sparkline, BLOCKS


def test_sparkline_basic():
    values = [1, 2, 3, 4, 5]
    out = render_sparkline(values, width=5)
    assert len(out) == 5
    # Lowest value uses BLOCKS[0], highest uses BLOCKS[-1]
    assert out[0] == BLOCKS[0]
    assert out[-1] == BLOCKS[-1]


def test_sparkline_empty():
    assert render_sparkline([]) == ""


def test_sparkline_resamples():
    # 10 values, width 3 → resampled
    values = list(range(10))
    out = render_sparkline(values, width=3)
    assert len(out) == 3


def test_sparkline_flat_line():
    # All same values → should not crash (rng==0 guard)
    values = [100.0] * 10
    out = render_sparkline(values, width=10)
    assert len(out) == 10
    # All chars should be the lowest block (idx 0)
    assert all(c == BLOCKS[0] for c in out)


def test_sparkline_width_equals_len():
    values = [1.0, 2.0, 3.0]
    out = render_sparkline(values, width=3)
    assert len(out) == 3


def test_sparkline_width_larger_than_values():
    # width > len(values) → use values as-is (no resampling)
    values = [1.0, 5.0]
    out = render_sparkline(values, width=10)
    assert len(out) == 2
