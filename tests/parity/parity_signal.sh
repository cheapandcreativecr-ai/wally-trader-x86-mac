#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/signal BTCUSDT LONG entry=68000 sl=67500 tp=69000 leverage=10x score=72'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_signal_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_signal_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_signal_cc.json /tmp/parity_signal_oc.json
