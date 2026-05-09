---
description: ASCII sparkline chart of any symbol
---

## Usage
- `/ascii BTCUSDT` — default 1h × 60 bars
- `/ascii ETHUSDT 4h 100` — custom TF + bars

## Implementation
```bash
ARG="$ARGUMENTS"
SYM=$(echo "$ARG" | awk '{print $1}')
TF=$(echo "$ARG" | awk '{print $2}')
BARS=$(echo "$ARG" | awk '{print $3}')
python3 .claude/scripts/ascii_chart.py --symbol "${SYM:-BTCUSDT}" --tf "${TF:-1h}" --bars "${BARS:-60}"
```
