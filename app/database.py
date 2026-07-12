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


def init_db() -> None:
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
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

        CREATE INDEX IF NOT EXISTS idx_analyses_chart ON analyses(chart_name);
        CREATE INDEX IF NOT EXISTS idx_analyses_timestamp ON analyses(timestamp);
        CREATE INDEX IF NOT EXISTS idx_analyses_score ON analyses(score);
        CREATE INDEX IF NOT EXISTS idx_analyses_direction ON analyses(direction);
        CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp);
    """)
    try:
        db.execute("ALTER TABLE analyses ADD COLUMN error TEXT")
    except Exception:
        pass
    db.commit()


def close_db() -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
