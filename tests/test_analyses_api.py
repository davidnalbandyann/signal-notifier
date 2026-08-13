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
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM analyses")
    db.execute("DELETE FROM active_strategies")
    db.execute("DELETE FROM charts")
    db.execute(
        "INSERT INTO analyses (chart_name, timestamp, score, direction, reason) "
        "VALUES ('BTC/USDT', '2026-08-03T10:00:00', 8.5, 'LONG', 'Bullish breakout on 15m')"
    )
    db.commit()
    yield


def test_get_existing_analysis_returns_200(auth_headers):
    client = TestClient(app)
    db = get_db()
    row = db.execute("SELECT id FROM analyses LIMIT 1").fetchone()
    r = client.get(f"/api/analyses/{row['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["direction"] == "LONG"


def test_get_missing_analysis_returns_404(auth_headers):
    client = TestClient(app)
    r = client.get("/api/analyses/999999999999", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"]


def test_get_missing_notification_returns_404(auth_headers):
    client = TestClient(app)
    r = client.get("/api/notifications/999999999999", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"]


def test_get_missing_chart_returns_404(auth_headers):
    client = TestClient(app)
    r = client.get("/api/charts/999999999999", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"]