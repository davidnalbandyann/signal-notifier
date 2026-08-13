import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tcm.db")

_local = threading.local()


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def infer_chart_type(name: str, url: str) -> str:
    n = (name or "").upper()
    u = (url or "").upper()

    # Forex check
    if "SYMBOL=FX:" in u or any(f in n for f in ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"]):
        return "forex"
    if any(n.startswith(f) for f in ["EUR/", "GBP/", "AUD/", "NZD/", "USD/"]):
        if any(c in n for c in ["USD", "JPY", "CAD", "CHF", "GBP", "EUR"]):
            return "forex"

    # Commodities check
    if "XAUUSD" in u or "GOLD/USD" in n or "XAGUSD" in u or "SILVER/USD" in n or "USOIL" in u or "OIL/USD" in n or "AMEX:GLD" in u or "AMEX:SLV" in u or "AMEX:USO" in u:
        return "commodities"

    # Indices check
    if "SYMBOL=INDEX:" in u or "SPXUSD" in u or "NSXUSD" in u or "SYMBOL=FOREXCOM:DJI" in u or "DEU40" in u or "S&P 500" in n or "NASDAQ 100" in n or "DOW JONES" in n or "DAX 40" in n:
        return "indices"

    # Stocks check
    if "SYMBOL=NASDAQ:" in u or "SYMBOL=NYSE:" in u or "SYMBOL=AMEX:" in u:
        if "SPY" in n or "QQQ" in n or "IWM" in n:
            return "indices"
        return "stocks"

    # Crypto check
    if "SYMBOL=BINANCE:" in u or "SYMBOL=BYBIT:" in u or "SYMBOL=COINBASE:" in u or "SYMBOL=KUCOIN:" in u or "SYMBOL=OKX:" in u or "USDT" in u or "USDT" in n or "/USDT" in n:
        return "crypto"

    return "other"


def init_db() -> None:
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            type TEXT DEFAULT 'crypto',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL NOT NULL,
            direction TEXT NOT NULL,
            reason TEXT NOT NULL,
            entry TEXT,
            stop_loss TEXT,
            take_profit TEXT,
            screenshot TEXT,
            error TEXT,
            sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER,
            chart_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL NOT NULL,
            direction TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'sent',
            caption TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cpp_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            engine_type TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ai_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS active_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mode TEXT NOT NULL CHECK(mode IN ('hybrid', 'ai_only', 'cpp_only')),
            enabled INTEGER DEFAULT 1,
            chart_id INTEGER REFERENCES charts(id) ON DELETE RESTRICT,
            cpp_strategy_id INTEGER REFERENCES cpp_strategies(id) ON DELETE RESTRICT,
            ai_strategy_id INTEGER REFERENCES ai_strategies(id) ON DELETE RESTRICT,
            min_score REAL,
            cooldown_minutes INTEGER DEFAULT 15,
            last_triggered_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_active_strategies_enabled ON active_strategies(enabled);
        CREATE INDEX IF NOT EXISTS idx_active_strategies_chart ON active_strategies(chart_id);

        CREATE INDEX IF NOT EXISTS idx_analyses_chart ON analyses(chart_name);
        CREATE INDEX IF NOT EXISTS idx_analyses_timestamp ON analyses(timestamp);
        CREATE INDEX IF NOT EXISTS idx_analyses_score ON analyses(score);
        CREATE INDEX IF NOT EXISTS idx_analyses_direction ON analyses(direction);
        CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp);
    """)
    try:
        db.execute("ALTER TABLE charts ADD COLUMN symbol TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE charts ADD COLUMN timeframe TEXT DEFAULT '15m'")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE charts ADD COLUMN type TEXT DEFAULT 'crypto'")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE analyses ADD COLUMN error TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE analyses ADD COLUMN signal_json TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE analyses ADD COLUMN active_strategy_id INTEGER REFERENCES active_strategies(id)")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE analyses ADD COLUMN active_strategy_name TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE notifications ADD COLUMN active_strategy_name TEXT")
    except Exception:
        pass
    db.commit()

    # Backfill or auto-infer type for existing charts in DB
    try:
        rows = db.execute("SELECT id, name, url, type FROM charts").fetchall()
        for r in rows:
            if not r["type"] or r["type"] == "crypto":
                inferred = infer_chart_type(r["name"], r["url"])
                if inferred != r["type"]:
                    db.execute("UPDATE charts SET type = ? WHERE id = ?", (inferred, r["id"]))
        db.commit()
    except Exception:
        pass

    try:
        db.execute("DELETE FROM charts WHERE TRIM(name) = '' OR TRIM(url) = ''")
        db.commit()
    except Exception:
        pass

    seed_charts()
    seed_strategies()


def seed_strategies() -> int:
    """Seed the libraries and active_strategies from legacy sources."""
    import json
    db = get_db()
    inserted = 0

    # Seed AI Strategies
    ai_count = db.execute("SELECT COUNT(*) AS c FROM ai_strategies").fetchone()["c"]
    ai_id = None
    if ai_count == 0:
        content = ""
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "strategy.md")
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass
        if content:
            cur = db.execute("INSERT INTO ai_strategies (name, content) VALUES (?, ?)", ("Default AI Strategy", content))
            ai_id = cur.lastrowid
            inserted += 1
    else:
        ai_id = db.execute("SELECT id FROM ai_strategies ORDER BY id ASC LIMIT 1").fetchone()["id"]

    # Seed C++ Strategies
    cpp_count = db.execute("SELECT COUNT(*) AS c FROM cpp_strategies").fetchone()["c"]
    cpp_id = None
    if cpp_count == 0:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "trading-signal-engine", "config.json",
        )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            strat_cfg = cfg.get("strategy", {})
            engine_type = strat_cfg.get("type", "")
            params = strat_cfg.get("params", {})
            if engine_type:
                cur = db.execute(
                    "INSERT INTO cpp_strategies (name, engine_type, params) VALUES (?, ?, ?)",
                    (f"Legacy {engine_type}", engine_type, json.dumps(params)),
                )
                cpp_id = cur.lastrowid
                inserted += 1
        except Exception:
            pass
    else:
        row = db.execute("SELECT id FROM cpp_strategies ORDER BY id ASC LIMIT 1").fetchone()
        if row: cpp_id = row["id"]

    # Seed Active Strategies (Hybrid by default if both exist)
    active_count = db.execute("SELECT COUNT(*) AS c FROM active_strategies").fetchone()["c"]
    if active_count == 0 and ai_id and cpp_id:
        chart_row = db.execute("SELECT id FROM charts ORDER BY id ASC LIMIT 1").fetchone()
        if chart_row:
            chart_id = chart_row["id"]
            db.execute(
                "INSERT INTO active_strategies (name, mode, enabled, chart_id, cpp_strategy_id, ai_strategy_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("Legacy Hybrid Pipeline", "hybrid", 1, chart_id, cpp_id, ai_id)
            )
            inserted += 1

    db.commit()
    return inserted


def seed_charts() -> int:
    import yaml
    db = get_db()
    urls_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "urls.yaml")
    charts_to_seed = []
    if os.path.exists(urls_file):
        try:
            with open(urls_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict) and "charts" in data:
                    charts_to_seed = data["charts"]
        except Exception:
            pass

    if not charts_to_seed:
        charts_to_seed = [
            {"name": "BTC/USD 15m", "url": "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=15", "type": "crypto"},
            {"name": "ETH/USD 1h", "url": "https://www.tradingview.com/chart/?symbol=BINANCE:ETHUSDT&interval=60", "type": "crypto"},
            {"name": "SOL/USD 15m", "url": "https://www.tradingview.com/chart/?symbol=BINANCE:SOLUSDT&interval=15", "type": "crypto"},
        ]

    inserted = 0
    for c in charts_to_seed:
        if isinstance(c, dict) and "name" in c and "url" in c:
            enabled_val = 1 if c.get("enabled", False) is True else 0
            chart_type = c.get("type") or infer_chart_type(c["name"], c["url"])
            cur = db.execute(
                "INSERT OR IGNORE INTO charts (name, url, type, enabled) VALUES (?, ?, ?, ?)",
                (c["name"], c["url"], chart_type, enabled_val),
            )
            if cur.rowcount > 0:
                inserted += cur.rowcount
            else:
                # Update type if not set
                db.execute(
                    "UPDATE charts SET type = ? WHERE name = ? AND (type IS NULL OR type = '')",
                    (chart_type, c["name"]),
                )
    db.commit()
    return inserted



def close_db() -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None

