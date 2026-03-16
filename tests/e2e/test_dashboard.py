import json
import os
import time
from urllib import request

import pytest

playwright = pytest.importorskip("playwright.sync_api")
Page = playwright.Page
expect = playwright.expect


API_URL = os.getenv("VECTOR_PULSE_API_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "local-dev-admin-key")


def _json_request(
    path: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
) -> dict:
    body = None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(f"{API_URL}{path}", data=body, headers=request_headers, method=method)
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def seed_dashboard_data() -> None:
    email = f"e2e_{int(time.time())}@example.com"
    registration = _json_request(
        "/v1/register",
        method="POST",
        payload={"email": email, "plan": "starter", "admin_key": ADMIN_KEY},
    )
    api_key = registration["api_key"]

    _json_request(
        "/v1/risk-check",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={
            "uid": f"e2e-user-{int(time.time())}",
            "amt": 9999,
            "addr": "Bangalore Central",
            "pin": "560001",
            "ip": "8.8.8.8",
            "shadow": False,
        },
    )


@pytest.fixture(scope="session", autouse=True)
def seed_environment():
    try:
        seed_dashboard_data()
    except Exception as exc:
        pytest.skip(f"E2E environment unavailable: {exc}")


def login(page: Page):
    page.goto(f"{API_URL}/admin")
    expect(page.get_by_text("Control Center")).to_be_visible()
    page.get_by_placeholder("Admin Secret Key").fill(ADMIN_KEY)
    page.get_by_role("button", name="Access Dashboard").click()
    expect(page.get_by_text("Vantix Admin")).to_be_visible()


def test_admin_login_success(page: Page):
    login(page)
    expect(page.get_by_text("Logout")).to_be_visible()


def test_admin_login_failure(page: Page):
    page.goto(f"{API_URL}/admin")
    page.get_by_placeholder("Admin Secret Key").fill("wrong_key")
    page.get_by_role("button", name="Access Dashboard").click()
    expect(page.locator("#authError")).to_be_visible()
    expect(page.locator("#authError")).to_contain_text("Invalid admin credentials")


def test_dashboard_stats_and_table(page: Page):
    login(page)
    expect(page.get_by_text("Total Protected Users")).to_be_visible()
    expect(page.get_by_text("Monthly API Traffic")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Client Email")).to_be_visible()
    expect(page.get_by_role("columnheader", name="API Key")).to_be_visible()
    expect(page.get_by_role("button", name="PROFILE").first).to_be_visible()


def test_risk_profile_modal_opens(page: Page):
    login(page)
    page.get_by_role("button", name="PROFILE").first.click()
    expect(page.locator("#configModal")).to_be_visible()
    expect(page.get_by_text("Recent Profile Changes")).to_be_visible()


def test_explain_modal(page: Page):
    login(page)
    expect(page.get_by_text("Intercepted Events")).to_be_visible()
    explain_btn = page.get_by_role("button", name="EXPLAIN").first
    expect(explain_btn).to_be_visible()
    explain_btn.click()
    expect(page.locator("#explainModal")).to_be_visible()
    page.get_by_role("button", name="Close").click()
    expect(page.locator("#explainModal")).not_to_be_visible()
