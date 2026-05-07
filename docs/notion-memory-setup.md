# Notion Memory Setup

Sync Wally Trader memory across devices (Mac casa ↔ Mac oficina) and harnesses (Claude Code ↔ OpenClaw) via Notion as a shared backend.

Without this setup, memory is local CSV only. With it, any device with the repo and a valid `NOTION_API_KEY` sees the same trade log, signals, and equity curve — live.

---

## 1. What this enables

- **Cross-harness:** Claude Code and OpenClaw read/write the same data.
- **Cross-device:** pull `make sync-pull PROFILE=bitunix` on a new machine to get the latest state before trading.
- **Dashboards:** query trade history directly from Notion with filters, charts, and views.
- **Rollback:** if Notion is down or misconfigured, system falls back to local CSV automatically.

---

## 2. Get a Notion API key

1. Go to https://www.notion.so/my-integrations
2. Click **+ New integration**
3. Name it `wally-trader`, select your workspace, leave capabilities as default (Read/Write content)
4. Click **Submit** → copy the **Internal Integration Secret** (starts with `secret_`)

Keep this key private — it grants write access to your Notion workspace.

---

## 3. Create the Notion workspace

1. In Notion, create a new top-level page named **Wally Trader** (or any name you prefer).
2. Open the page, click **Share** (top right) → **Invite** → search for your integration name (`wally-trader`) → give it **Edit** access.

The migration script will auto-create the 6 databases inside this page. You do not need to create them manually.

---

## 4. Run setup

```bash
# Step 1: set your API key
export NOTION_API_KEY=secret_xxx

# Step 2: review what will happen (dry run)
make notion-migrate PROFILE=bitunix

# Step 3: run the real migration (creates DBs + imports existing CSV rows)
make notion-migrate PROFILE=bitunix DRY_RUN=0

# Repeat for each profile you use
make notion-migrate PROFILE=retail DRY_RUN=0
make notion-migrate PROFILE=ftmo DRY_RUN=0
```

To persist the key across sessions add it to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export NOTION_API_KEY=secret_xxx
```

---

## 5. Verify in the Notion UI

After migration, open the **Wally Trader** page in Notion. You should see 6 databases auto-created:

| Database | Profile |
|---|---|
| `signals_received` | bitunix |
| `equity_curve` | bitunix |
| `trading_log` | retail / retail-bingx |
| `trades` | ftmo / fundingpips |
| `journal` | all profiles |
| `macro_events` | system-wide |

Each database has rows matching your existing CSV history.

---

## 6. Switch backend per profile

Control the backend via the `WALLY_MEMORY_BACKEND` environment variable:

| Value | Behavior |
|---|---|
| `hybrid` | (default) Writes go to local CSV + Notion. Reads prefer local cache, pulls Notion on miss. |
| `local` | Local CSV only. No Notion calls. Fastest, no internet needed. |
| `notion` | Notion only. Local CSV used as emergency fallback if Notion is unreachable. |

Per-terminal override:
```bash
# Use hybrid for bitunix
export WALLY_MEMORY_BACKEND=hybrid
export WALLY_PROFILE=bitunix

# Use local-only for a quick offline session
WALLY_MEMORY_BACKEND=local openclaw agent --message "/status"
```

The default `hybrid` is recommended for most use. Local CSV always stays in sync as a fallback.

---

## 7. Cross-device handoff

On any new machine (or after a long pause on an existing one):

```bash
# Pull latest from Notion before starting your session
make sync-pull PROFILE=bitunix
make sync-pull PROFILE=retail

# Then verify
make doctor
```

This force-overwrites the local cache with Notion's current state. Run it once at session start when switching devices.

---

## 8. Brother setup (multi-tenant)

To set up an identical system for another person with completely isolated data:

1. They clone the same repo (or a fork).
2. They go to https://www.notion.so/my-integrations and create **their own** integration under **their Notion account**.
3. They set `export NOTION_API_KEY=secret_their_key` — pointing to their workspace.
4. They run `make notion-migrate PROFILE=<name> DRY_RUN=0` to initialize their DBs.

There is zero data leakage between accounts because:
- The `NOTION_API_KEY` scopes all reads/writes to the workspace that integration was created under.
- Notion's access controls block cross-account access by default.

---

## 9. Troubleshooting

### Rate limit (HTTP 429)
Notion enforces ~3 requests/second. The `NotionBackend` retries once with a 2-second delay. If you see persistent 429s during a bulk migration, the migration script pauses automatically. You can re-run `make notion-migrate` — it skips rows already present (idempotent by row ID).

See https://developers.notion.com/reference/request-limits for current limits.

### Schema drift
If you see `schema validation error` after updating wally_core, run:
```bash
make notion-rollback PROFILE=<name>   # export current Notion rows back to local CSV
# update schema, re-migrate
make notion-migrate PROFILE=<name> DRY_RUN=0
```

### Fallback to local is happening
Check `make doctor` output — if step 3 shows `notion_online: false`, verify:
1. `NOTION_API_KEY` is set and starts with `secret_`.
2. The integration has edit access to the Wally Trader page (step 3 of setup above).
3. Internet is reachable: `curl -s https://api.notion.com/v1/users/me -H "Authorization: Bearer $NOTION_API_KEY" | python3 -m json.tool | head -5`

### Roll back everything
```bash
make notion-rollback PROFILE=bitunix   # exports Notion → local CSV
# unset NOTION_API_KEY to disable Notion permanently
unset NOTION_API_KEY
```

Local CSVs are always the source of truth in git. Notion is an enhancement layer.
