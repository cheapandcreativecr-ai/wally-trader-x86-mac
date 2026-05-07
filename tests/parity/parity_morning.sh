#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/morning'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_morning_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_morning_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_morning_cc.json /tmp/parity_morning_oc.json
