# Disaster Recovery Runbook — wally-trader

## When to use this
- Mac wiped or unrecoverable
- Repo corruption
- Notion data loss / accidental deletion
- Need to restore on new machine

## Pre-disaster checklist
- [ ] `~/wally-backups/` exists with daily backups (auto via `make ops-install`)
- [ ] NOTION_API_KEY noted in password manager
- [ ] TELEGRAM_BOT_TOKEN noted in password manager
- [ ] git repo pushed to origin

## Recovery steps

### 1. Restore from backup
```bash
cd ~
ls ~/wally-backups/
# Pick most recent: wally-backup-YYYY-MM-DD.tar.gz
git clone <repo-url> wally-trader
cd wally-trader
tar -xzf ~/wally-backups/wally-backup-LATEST.tar.gz
```

### 2. Re-install Python venv
```bash
make wally-mcp-install
```

### 3. Restore env vars
```bash
export NOTION_API_KEY="secret_xxx"
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
# Add to ~/.zshrc or ~/.bashrc
```

### 4. Verify state
```bash
make doctor
make health
```

### 5. Verify Notion sync (optional)
```bash
make sync-pull PROFILE=bitunix
# Notion should be source of truth, local cache rebuilt
```

### 6. Re-install daemons
```bash
make ops-install         # health + backup + watchdog
make hermes-install      # if using Hermes (macOS optional)
make dashboard-install   # web dashboard
```

### 7. Verify dashboard
```bash
curl http://127.0.0.1:8080/api/health
```

### 8. Verify audit chain integrity
```bash
shared/wally_core/.venv/bin/python -c "from wally_core.audit import verify_chain; print(verify_chain())"
```

## Cross-OS handoff (Mac → Windows WSL)

If Mac is dead, work continues on Windows:
1. WSL Ubuntu: `git clone` repo
2. `bash scripts/setup-windows-wsl.sh`
3. `make sync-pull PROFILE=bitunix` — Notion is source of truth
4. Use Hermes daemon for Telegram bot

## RPO/RTO
- **RPO** (data loss tolerance): up to 24h (last daily backup)
- **RTO** (time to restore): 30-60 min on fresh machine
- **Cross-OS RTO**: 15 min if Notion alive
