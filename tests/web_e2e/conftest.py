import pytest
import time


@pytest.fixture(scope="session")
def backend_url():
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def frontend_url():
    return "http://localhost:5173"


@pytest.fixture
def auth_token(backend_url):
    """Get a JWT token from the backend."""
    import requests
    r = requests.post(
        f"{backend_url}/api/auth/login",
        json={"username": "davo", "password": "davo"},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()