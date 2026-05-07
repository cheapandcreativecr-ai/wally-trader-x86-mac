"""Canonical Notion DB schemas — used by migrate.py and NotionBackend."""

DB_PROFILES = {
    "title": "📊 Profiles",
    "properties": {
        "Name": {"title": {}},
        "Capital USD": {"number": {"format": "dollar"}},
        "Capital BTC": {"number": {"format": "number"}},
        "Strategy": {"select": {"options": [
            {"name": "Mean Reversion"}, {"name": "Donchian Breakout"},
            {"name": "MA Crossover"}, {"name": "Multi-Asset"},
        ]}},
        "Window CR": {"rich_text": {}},
        "Last Updated": {"last_edited_time": {}},
    },
}

DB_TRADES_LOG = {
    "title": "📈 Trades Log",
    "properties": {
        "ID": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Asset": {"rich_text": {}},
        "Side": {"select": {"options": [{"name": "LONG"}, {"name": "SHORT"}]}},
        "Entry": {"number": {"format": "number"}},
        "SL": {"number": {"format": "number"}},
        "TP1": {"number": {"format": "number"}},
        "TP2": {"number": {"format": "number"}},
        "TP3": {"number": {"format": "number"}},
        "Leverage": {"number": {"format": "number"}},
        "Position Size USD": {"number": {"format": "dollar"}},
        "Exit Price": {"number": {"format": "number"}},
        "PnL USD": {"number": {"format": "dollar"}},
        "PnL %": {"number": {"format": "percent"}},
        "R Multiple": {"number": {"format": "number"}},
        "Status": {"select": {"options": [
            {"name": "open"}, {"name": "tp1_hit"}, {"name": "tp2_hit"},
            {"name": "tp3_hit"}, {"name": "sl"}, {"name": "closed_manual"},
        ]}},
        "Source": {"select": {"options": [
            {"name": "manual"}, {"name": "signal"}, {"name": "hunt"}, {"name": "copy"},
        ]}},
        "Notes": {"rich_text": {}},
    },
}

DB_SIGNALS_RECEIVED = {
    "title": "📡 Signals Received",
    "properties": {
        "ID": {"title": {}},
        "Timestamp": {"created_time": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Source": {"select": {"options": [
            {"name": "discord"}, {"name": "punk-hunt"}, {"name": "self"},
        ]}},
        "Symbol": {"rich_text": {}},
        "Side": {"select": {"options": [{"name": "LONG"}, {"name": "SHORT"}]}},
        "Entry": {"number": {"format": "number"}},
        "SL": {"number": {"format": "number"}},
        "TP1": {"number": {"format": "number"}},
        "TP2": {"number": {"format": "number"}},
        "TP3": {"number": {"format": "number"}},
        "Leverage": {"number": {"format": "number"}},
        "Score": {"number": {"format": "number"}},
        "Decision": {"select": {"options": [
            {"name": "GO"}, {"name": "NO-GO"}, {"name": "WARN"},
        ]}},
        "Outcome": {"select": {"options": [
            {"name": "TP1"}, {"name": "TP2"}, {"name": "TP3"},
            {"name": "SL"}, {"name": "manual"}, {"name": "pending"},
        ]}},
        "Exit Price": {"number": {"format": "number"}},
        "PnL USD": {"number": {"format": "dollar"}},
        "Raw Message": {"rich_text": {}},
    },
}

DB_EQUITY_CURVE = {
    "title": "💰 Equity Curve",
    "properties": {
        "ID": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Equity USD": {"number": {"format": "dollar"}},
        "Equity BTC": {"number": {"format": "number"}},
        "Daily PnL USD": {"number": {"format": "dollar"}},
        "Daily Return %": {"number": {"format": "percent"}},
    },
}

DB_DAILY_JOURNAL = {
    "title": "📔 Daily Journal",
    "properties": {
        "Title": {"title": {}},
        "Profile": {"relation": {"database_id": "<resolved-at-runtime>"}},
        "Date": {"date": {}},
        "Summary": {"rich_text": {}},
        "Lessons": {"rich_text": {}},
        "Screenshots": {"files": {}},
    },
}

DB_WEEKLY_DIGEST = {
    "title": "📅 Weekly Digest",
    "properties": {
        "Title": {"title": {}},
        "Week Start": {"date": {}},
        "Summary": {"rich_text": {}},
        "Highlights": {"rich_text": {}},
        "Macro Events Next Week": {"rich_text": {}},
    },
}

ALL_DBS = {
    "profiles": DB_PROFILES,
    "trades_log": DB_TRADES_LOG,
    "signals_received": DB_SIGNALS_RECEIVED,
    "equity_curve": DB_EQUITY_CURVE,
    "daily_journal": DB_DAILY_JOURNAL,
    "weekly_digest": DB_WEEKLY_DIGEST,
}
