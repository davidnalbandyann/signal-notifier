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
    db.execute("DELETE FROM settings")

    # Insert charts
    db.execute("INSERT INTO charts (name, url, enabled) VALUES ('BTC/USDT', 'https://tradingview.com/chart/1', 1)")
    db.execute("INSERT INTO charts (name, url, enabled) VALUES ('ETH/USDT', 'https://tradingview.com/chart/2', 0)")

    # Insert analyses
    db.execute("""
        INSERT INTO analyses (chart_name, timestamp, score, direction, reason)
        VALUES ('BTC/USDT', '2026-08-03T10:00:00', 8.5, 'LONG', 'Bullish breakout')
    """)

    # Insert notifications
    db.execute("""
        INSERT INTO notifications (chart_name, timestamp, score, direction, status, caption)
        VALUES ('BTC/USDT', '2026-08-03T10:00:05', 8.5, 'LONG', 'sent', 'BTC setup alert')
    """)

    # Insert settings
    db.execute("INSERT INTO settings (key, value) VALUES ('CHECK_INTERVAL_SECONDS', '300')")
    db.commit()
    yield

def test_get_admin_charts_list(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/charts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2

def test_search_and_pagination(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/charts?search=BTC", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "BTC/USDT"

def test_get_admin_analyses(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/analyses", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["direction"] == "LONG"

def test_get_admin_notifications(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "sent"

def test_get_admin_settings(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["key"] == "CHECK_INTERVAL_SECONDS"

def test_crud_settings_table(auth_headers):
    client = TestClient(app)
    # Create setting
    res_create = client.post("/api/admin/settings", json={"key": "TEST_KEY", "value": "123"}, headers=auth_headers)
    assert res_create.status_code == 201
    assert res_create.json()["key"] == "TEST_KEY"

    # Update setting
    res_update = client.put("/api/admin/settings/TEST_KEY", json={"value": "456"}, headers=auth_headers)
    assert res_update.status_code == 200
    assert res_update.json()["value"] == "456"

    # Delete setting
    res_delete = client.delete("/api/admin/settings/TEST_KEY", headers=auth_headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "deleted"

def test_create_admin_chart(auth_headers):
    client = TestClient(app)
    payload = {"name": "SOL/USDT", "url": "https://tradingview.com/chart/3", "enabled": 1}
    response = client.post("/api/admin/charts", json=payload, headers=auth_headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == "SOL/USDT"

def test_update_admin_chart(auth_headers):
    client = TestClient(app)
    db = get_db()
    cur = db.execute("SELECT id FROM charts WHERE name = 'BTC/USDT'")
    chart_id = cur.fetchone()["id"]

    response = client.put(f"/api/admin/charts/{chart_id}", json={"url": "https://tradingview.com/updated", "enabled": 0}, headers=auth_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["url"] == "https://tradingview.com/updated"

def test_delete_admin_chart(auth_headers):
    client = TestClient(app)
    db = get_db()
    cur = db.execute("SELECT id FROM charts WHERE name = 'ETH/USDT'")
    chart_id = cur.fetchone()["id"]

    response = client.delete(f"/api/admin/charts/{chart_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

def test_bulk_delete_admin_charts(auth_headers):
    client = TestClient(app)
    db = get_db()
    cur = db.execute("SELECT id FROM charts")
    ids = [r["id"] for r in cur.fetchall()]

    response = client.post("/api/admin/charts/bulk-delete", json={"ids": ids}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["deleted_count"] == len(ids)

def test_filter_charts_by_enabled(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/charts?enabled=1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "BTC/USDT"

    response = client.get("/api/admin/charts?enabled=0", headers=auth_headers)
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "ETH/USDT"

def test_filter_charts_by_type(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/charts?type=crypto", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["type"] == "crypto" for item in data["items"])

    response = client.get("/api/admin/charts?type=forex", headers=auth_headers)
    assert response.json()["total"] == 0

def test_filter_analyses_by_direction(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/analyses?direction=LONG", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["direction"] == "LONG"

    response = client.get("/api/admin/analyses?direction=SHORT", headers=auth_headers)
    assert response.json()["total"] == 0

def test_filter_analyses_by_min_score(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/analyses?min_score=8", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/admin/analyses?min_score=9", headers=auth_headers)
    assert response.json()["total"] == 0

def test_filter_analyses_by_sent(auth_headers):
    client = TestClient(app)
    db = get_db()
    db.execute("UPDATE analyses SET sent = 1 WHERE chart_name = 'BTC/USDT'")
    db.commit()

    response = client.get("/api/admin/analyses?sent=1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/admin/analyses?sent=0", headers=auth_headers)
    assert response.json()["total"] == 0

def test_filter_notifications_by_status(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/notifications?status=sent", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "sent"

    response = client.get("/api/admin/notifications?status=failed", headers=auth_headers)
    assert response.json()["total"] == 0

def test_filter_date_range(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/analyses?date_from=2026-08-03&date_to=2026-08-03", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/admin/analyses?date_to=2026-08-02", headers=auth_headers)
    assert response.json()["total"] == 0

    response = client.get("/api/admin/notifications?date_from=2026-08-03", headers=auth_headers)
    assert response.json()["total"] == 1

def test_combined_search_and_filter(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/analyses?search=BTC&direction=LONG", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["chart_name"] == "BTC/USDT"

def test_unknown_filter_param_ignored(auth_headers):
    client = TestClient(app)
    response = client.get("/api/admin/charts?direction=LONG", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
