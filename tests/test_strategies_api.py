import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_token
from app.config.settings import Settings
from app.database import get_db, init_db
from app.routes import strategies as strategies_module

@pytest.fixture
def auth_headers():
    settings = Settings()
    token = create_token(settings)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    init_db()
    db = get_db()
    db.execute("DELETE FROM active_strategies")
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM analyses")
    db.execute("DELETE FROM charts")
    db.execute("INSERT INTO charts (name, url, type, enabled) VALUES ('BTC/USDT', 'https://tradingview.com/chart/?symbol=BINANCE:BTCUSDT', 'crypto', 1)")
    db.commit()
    monkeypatch.setattr(strategies_module, "_generate_and_write_cpp_config", lambda request: None)
    async def _no_restart(request):
        return False
    monkeypatch.setattr(strategies_module, "_restart_engine_if_running", _no_restart)
    yield

def _seed_libraries(db):
    from app.database import seed_strategies
    seed_strategies()
    ai = db.execute("SELECT id FROM ai_strategies ORDER BY id ASC LIMIT 1").fetchone()
    cpp = db.execute("SELECT id FROM cpp_strategies ORDER BY id ASC LIMIT 1").fetchone()
    return (ai["id"] if ai else None), (cpp["id"] if cpp else None)


def test_create_and_list_active_strategy_uses_strategies_key(auth_headers):
    db = get_db()
    ai_id, cpp_id = _seed_libraries(db)
    chart_id = db.execute("SELECT id FROM charts ORDER BY id ASC LIMIT 1").fetchone()["id"]

    client = TestClient(app)
    res = client.post("/api/strategies/active", json={
        "name": "Test Pipeline",
        "mode": "hybrid",
        "chart_id": chart_id,
        "ai_strategy_id": ai_id,
        "cpp_strategy_id": cpp_id,
        "min_score": 8.0,
        "cooldown_minutes": 15,
    }, headers=auth_headers)
    assert res.status_code == 200
    created = res.json()
    assert created["id"] is not None
    assert created["name"] == "Test Pipeline"

    # GET must return the "strategies" key that the frontend reads
    res = client.get("/api/strategies/active", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "strategies" in body
    assert any(s["id"] == created["id"] for s in body["strategies"])
