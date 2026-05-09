# ML Multi-Asset Retrain — Step-by-Step

The current XGBoost model is trained on BTC only. This guide retrains it for the bitunix watchlist.

## Prerequisites
- Python venv: `shared/wally_core/.venv/bin/python`
- Disk: ~500MB for downloaded data
- Time: ~30 min download + ~10 min training

## Steps

### 1. Download multi-asset data
```bash
$VENV_PY scripts/ml_system/supervised/download.py \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,DYDXUSDT,LDOUSDT,ALGOUSDT,MSTRUSDT,DOGEUSDT,WIFUSDT,XLMUSDT \
  --tf 15m \
  --bars 8000 \
  --output scripts/ml_system/data/multi_asset_15m.parquet
```

### 2. Re-train XGBoost
```bash
$VENV_PY scripts/ml_system/supervised/train.py \
  --data scripts/ml_system/data/multi_asset_15m.parquet \
  --feature-set v2 \
  --output scripts/ml_system/supervised/model_v2/
```

### 3. Validate metrics
```bash
$VENV_PY scripts/ml_system/supervised/validate.py \
  --model scripts/ml_system/supervised/model_v2/ \
  --test-split 0.2
```

Expected: AUC > 0.65, precision > 0.55 on positive class.

### 4. Deploy
```bash
mv scripts/ml_system/supervised/model scripts/ml_system/supervised/model_btc_v1_backup
mv scripts/ml_system/supervised/model_v2 scripts/ml_system/supervised/model
```

### 5. Verify
```bash
# Test prediction on each asset
for sym in BTCUSDT ETHUSDT DYDXUSDT LDOUSDT; do
  echo "=== $sym ==="
  $VENV_PY -m scripts.ml_system.predict --symbol $sym --tf 15m
done
```

## Re-train cadence

After every 30 trade outcomes (data accumulated in `signals_received.csv` + `outcomes_v2.csv`), re-run validation. If AUC drops below 0.60, retrain.

## Feature set v2 additions (vs BTC-only v1)

| Feature | Description |
|---|---|
| `symbol_embed` | One-hot encoded asset category (BTC/ETH/altcoin/micro) |
| `vol_rank` | Volatility rank vs BTC over last 48h |
| `corr_btc_1h` | Rolling 1h correlation with BTC price |
| `funding_rate` | Current 8h funding rate (proxy for sentiment) |
| `oi_delta_pct` | Open interest change % over last 4h |

These features help the model distinguish regime per asset (e.g. DYDX behaves differently from BTC in ranging markets).
