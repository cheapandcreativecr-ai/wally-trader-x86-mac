#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/risk profile=bitunix capital_usd=200 entry=68000 sl=67500 side=LONG leverage=10x'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_risk_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_risk_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_risk_cc.json /tmp/parity_risk_oc.json
