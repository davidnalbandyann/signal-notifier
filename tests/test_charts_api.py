import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_token
from app.config.settings import Settings
from app.database import get_db, init_db

@pytest.fixture
def auth_headers():
    settings = Settings()
    token = create_token(settings)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    db = get_db()
    db.execute("DELETE FROM active_strategies")
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM analyses")
    db.execute("DELETE FROM charts")
    db.execute("INSERT INTO charts (name, url, type, enabled) VALUES ('BTC/USDT', 'https://tradingview.com/chart/?symbol=BINANCE:BTCUSDT', 'crypto', 1)")
    db.execute("INSERT INTO charts (name, url, type, enabled) VALUES ('EUR/USD', 'https://tradingview.com/chart/?symbol=FX:EURUSD', 'forex', 1)")
    db.execute("INSERT INTO charts (name, url, type, enabled) VALUES ('NVDA 1h', 'https://tradingview.com/chart/?symbol=NASDAQ:NVDA', 'stocks', 1)")
    db.commit()
    yield


def test_list_charts_and_type_filter(auth_headers):
    client = TestClient(app)
    # List all charts
    res = client.get("/api/charts", headers=auth_headers)
    assert res.status_code == 200
    charts = res.json()
    assert len(charts) == 3
    
    # List forex charts
    res_forex = client.get("/api/charts?type=forex", headers=auth_headers)
    assert res_forex.status_code == 200
    forex_charts = res_forex.json()
    assert len(forex_charts) == 1
    assert forex_charts[0]["name"] == "EUR/USD"
    assert forex_charts[0]["type"] == "forex"

def test_create_chart_with_type_and_auto_infer(auth_headers):
    client = TestClient(app)
    # Create with explicit type
    res1 = client.post("/api/charts", json={"name": "GOLD/USD 1h", "url": "https://tradingview.com/chart/?symbol=OANDA:XAUUSD", "type": "commodities"}, headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["type"] == "commodities"

    # Create without type (auto-inferred)
    res2 = client.post("/api/charts", json={"name": "GBP/USD 1h", "url": "https://tradingview.com/chart/?symbol=FX:GBPUSD"}, headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["type"] == "forex"

def test_update_chart_type(auth_headers):
    client = TestClient(app)
    db = get_db()
    cur = db.execute("SELECT id FROM charts WHERE name = 'BTC/USDT'")
    chart_id = cur.fetchone()["id"]

    res = client.put(f"/api/charts/{chart_id}", json={"type": "other"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["type"] == "other"

def test_analyses_search_filter(auth_headers):
    client = TestClient(app)
    db = get_db()
    db.execute("INSERT INTO analyses (chart_name, timestamp, score, direction, reason) VALUES ('BTC/USDT', '2026-08-03T10:00:00', 8.5, 'LONG', 'Bullish breakout on 15m')")
    db.commit()

    res = client.get("/api/analyses?search=breakout", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["chart_name"] == "BTC/USDT"

def test_notifications_search_filter(auth_headers):
    client = TestClient(app)
    db = get_db()
    db.execute("INSERT INTO notifications (chart_name, timestamp, score, direction, status, caption) VALUES ('EUR/USD', '2026-08-03T10:05:00', 7.5, 'SHORT', 'sent', 'EUR/USD resistance test')")
    db.commit()

    res = client.get("/api/notifications?search=resistance", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["chart_name"] == "EUR/USD"

