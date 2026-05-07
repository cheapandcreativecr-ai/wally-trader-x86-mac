#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/validate profile=bitunix symbol=BTCUSDT side=LONG entry=68000 sl=67500'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_validate_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_validate_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_validate_cc.json /tmp/parity_validate_oc.json
