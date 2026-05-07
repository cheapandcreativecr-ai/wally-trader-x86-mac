#!/usr/bin/env bash
set -e
HERE="$(dirname "$0")"
PROMPT='/journal --dry-run'
$HERE/run_cc.sh bitunix "$PROMPT" > /tmp/parity_journal_cc.json
$HERE/run_oc.sh bitunix "$PROMPT" > /tmp/parity_journal_oc.json
python3 $HERE/diff_outputs.py /tmp/parity_journal_cc.json /tmp/parity_journal_oc.json
