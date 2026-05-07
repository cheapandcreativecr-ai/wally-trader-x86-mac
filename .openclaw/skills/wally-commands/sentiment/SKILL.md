---
name: sentiment
description: Agregador NLP de sentimiento BTC (F&G + Reddit VADER + News RSS + Funding
  contrarian)
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/sentiment.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /sentiment -->


Invoca el agente `sentiment-analyst` para obtener el score agregado 0-100 de sentimiento BTC.

Combina:
1. **Fear & Greed Index** (alternative.me) — peso 35%
2. **News VADER** (CoinTelegraph + CoinDesk + Decrypt) — peso 30%
3. **Reddit VADER** (r/CryptoMarkets + r/Bitcoin + r/CryptoCurrency) — peso 20%
4. **Funding rate contrarian** (OKX) — peso 15%

Output: score 0-100 con interpretación + top 3 posts/noticias con polaridad + acción recomendada.

Útil antes de abrir sesión matutina o cuando ha habido movimiento extremo en últimas 4h.

$ARGUMENTS
