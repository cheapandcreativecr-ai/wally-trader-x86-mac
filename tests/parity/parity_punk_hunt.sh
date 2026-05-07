#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/punk-hunt'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_punk_hunt_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_punk_hunt_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_punk_hunt_cc.json /tmp/parity_punk_hunt_oc.json
