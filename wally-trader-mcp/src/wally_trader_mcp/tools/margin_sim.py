"""Margin call simulator MCP tool."""


def margin_sim(entry: float, leverage: int, side: str, maintenance_margin_pct: float = 0.5) -> dict:
    """Compute liquidation price + MFE/MAE table."""
    initial_margin_pct = 100 / leverage
    liq_buffer = initial_margin_pct - maintenance_margin_pct

    if side == "LONG":
        liq_price = entry * (1 - liq_buffer / 100)
    else:
        liq_price = entry * (1 + liq_buffer / 100)

    table = []
    for adverse_pct in [1, 2, 3, 5, 7, 10]:
        if adverse_pct >= liq_buffer:
            table.append({"adverse_pct": adverse_pct, "result": "LIQUIDATION"})
            break
        loss_pct_margin = adverse_pct / initial_margin_pct * 100
        table.append({"adverse_pct": adverse_pct, "loss_pct_margin": round(loss_pct_margin, 2)})

    return {
        "entry": entry,
        "side": side,
        "leverage": leverage,
        "initial_margin_pct": round(initial_margin_pct, 2),
        "liq_buffer_pct": round(liq_buffer, 2),
        "liq_price": round(liq_price, 8),
        "table": table,
    }
