# Pine Script Library

Indicadores Pine v6 generados por `/pine-gen` o curated manualmente.

Cada archivo `.pine` aquí debe:
- Empezar con `//@version=6`
- Tener docstring comments explicando qué hace y cuándo usarlo
- Compilar limpio (sin errors/warnings) en TradingView v6

Para compilar uno existente en TV:
```
mcp__tradingview__pine_open(name="<filename>")
mcp__tradingview__pine_smart_compile()
```

