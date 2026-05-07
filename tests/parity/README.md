# Parity tests — CC ↔ OC

These scripts verify Claude Code and OpenClaw produce equivalent results from the same prompts.

## Prerequisites

- `claude` CLI on PATH (Anthropic Claude Code)
- `openclaw` CLI on PATH (NousResearch / OpenClaw runtime)
- Both configured with the wally-trader profile system (see `docs/openclaw-setup.md`)

## Run

```bash
make test-parity   # runs all parity_*.sh scripts
```

Or individually:
```bash
bash tests/parity/parity_risk.sh
```

Each script:
1. Runs the same prompt against CC and OC
2. Captures both outputs as JSON
3. Compares with `diff_outputs.py` (timestamps and UUIDs are normalized)

If `claude` or `openclaw` CLIs aren't installed, scripts will exit non-zero with a clear error.

## Acceptable divergence

- Timestamps and UUIDs (auto-normalized)
- Narrative LLM output text (we compare JSON-structured fields, not prose)
- Trailing whitespace
