"""Payment History (Phase 1) — backend tests.
Uses seeded test data via direct DB writes, then exercises the HTTP endpoints.

Run:
    cd /app/backend && python -m pytest tests/test_payment_history.py -v
"""
import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

TEST_TAG = "ph_test"  # marker on seeded records so we can clean up


@pytest.fixture(scope="module")
async def app_client():
    import sys
    sys.path.insert(0, str(ROOT_DIR))
    from server import app  # noqa: WPS433
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="module")
async def db_conn():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module")
async def finance_token(app_client, db_conn):
    """Create a temporary finance user, log in, return bearer token."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"ph_finance_{uuid.uuid4().hex[:6]}@test.local"
    password = "Test@1234"
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "id_number": f"PHF{uuid.uuid4().hex[:8].upper()}",
        "full_name": "PH Finance",
        "role": "finance",
        "password": pwd.hash(password),
        "is_active": True,
        f"{TEST_TAG}": True,
    }
    await db_conn.users.insert_one(user_doc)
    resp = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json().get("token") or resp.json().get("access_token")
    yield token
    await db_conn.users.delete_one({"id": user_doc["id"]})


@pytest.fixture(scope="module")
async def coordinator_token(app_client, db_conn):
    """Non-finance user to test authorization."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"ph_coord_{uuid.uuid4().hex[:6]}@test.local"
    password = "Test@1234"
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "id_number": f"PHC{uuid.uuid4().hex[:8].upper()}",
        "full_name": "PH Coordinator",
        "role": "coordinator",
        "password": pwd.hash(password),
        "is_active": True,
        f"{TEST_TAG}": True,
    }
    await db_conn.users.insert_one(user_doc)
    resp = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json().get("token") or resp.json().get("access_token")
    yield token
    await db_conn.users.delete_one({"id": user_doc["id"]})


@pytest.fixture(scope="module")
async def seeded_payments(db_conn):
    """Seed 130 payments across 2 invoices/clients so pagination past page 1 is meaningful."""
    invoice_a = {
        "id": str(uuid.uuid4()),
        "invoice_number": f"INV/PHTEST/{uuid.uuid4().hex[:4].upper()}",
        "company_name": "PH Alpha Sdn Bhd",
        "bill_to_name": "PH Alpha Sdn Bhd",
        "session_name": "Defensive Driving PH",
        "programme_name": "Defensive Driving PH",
        "total_amount": 1000.0,
        "status": "issued",
        TEST_TAG: True,
    }
    invoice_b = {
        "id": str(uuid.uuid4()),
        "invoice_number": f"INV/PHTEST/{uuid.uuid4().hex[:4].upper()}",
        "company_name": "PH Beta Bhd",
        "bill_to_name": "PH Beta Bhd",
        "session_name": "Forklift PH",
        "programme_name": "Forklift PH",
        "total_amount": 500.0,
        "status": "issued",
        TEST_TAG: True,
    }
    await db_conn.invoices.insert_many([invoice_a, invoice_b])

    payments = []
    for i in range(130):
        month = (i % 12) + 1
        day = (i % 27) + 1
        payments.append({
            "id": str(uuid.uuid4()),
            "invoice_id": (invoice_a if i % 2 == 0 else invoice_b)["id"],
            "amount": float(100 + i),  # 100..229
            "payment_date": f"2025-{month:02d}-{day:02d}",
            "payment_method": "bank_transfer" if i % 3 else "cash",
            "reference_number": f"REF-PHTEST-{i:04d}",
            "receipt_number": f"RCP/PHTEST/2025/{i:04d}",
            "payment_type": "hrdcorp" if i % 5 == 0 else "self_pay",
            "created_at": f"2025-{month:02d}-{day:02d}T10:00:00",
            "status": "reversed" if i == 129 else None,
            TEST_TAG: True,
        })
    await db_conn.payments.insert_many(payments)

    yield {"invoice_a": invoice_a, "invoice_b": invoice_b, "payments": payments}

    await db_conn.payments.delete_many({TEST_TAG: True})
    await db_conn.invoices.delete_many({TEST_TAG: True})


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ============ TESTS ============

@pytest.mark.asyncio
async def test_default_returns_newest_first(app_client, finance_token, seeded_payments):
    r = await app_client.get("/api/finance/payments/history", headers=auth_headers(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["total"] >= 129  # excludes reversed by default
    dates = [item["payment_date"] for item in body["items"]]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_pagination_page_1_and_2_differ(app_client, finance_token, seeded_payments):
    r1 = await app_client.get("/api/finance/payments/history?page=1&page_size=25", headers=auth_headers(finance_token))
    r2 = await app_client.get("/api/finance/payments/history?page=2&page_size=25", headers=auth_headers(finance_token))
    assert r1.status_code == 200 and r2.status_code == 200
    ids1 = {p["id"] for p in r1.json()["items"]}
    ids2 = {p["id"] for p in r2.json()["items"]}
    assert len(ids1) == 25
    assert len(ids2) == 25
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_page_size_respected(app_client, finance_token, seeded_payments):
    r = await app_client.get("/api/finance/payments/history?page=1&page_size=50", headers=auth_headers(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert body["page_size"] == 50
    assert len(body["items"]) == 50


@pytest.mark.asyncio
async def test_access_records_beyond_first_100(app_client, finance_token, seeded_payments):
    r = await app_client.get("/api/finance/payments/history?page=2&page_size=100", headers=auth_headers(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 129
    assert len(body["items"]) >= 29  # remaining beyond first 100


@pytest.mark.asyncio
async def test_search_by_invoice_number(app_client, finance_token, seeded_payments):
    inv_num = seeded_payments["invoice_a"]["invoice_number"]
    r = await app_client.get(
        f"/api/finance/payments/history?q={inv_num}",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    for p in body["items"]:
        assert p["invoice_number"] == inv_num


@pytest.mark.asyncio
async def test_search_by_receipt_number(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?q=RCP/PHTEST/2025/0001",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(p["receipt_number"] == "RCP/PHTEST/2025/0001" for p in body["items"])


@pytest.mark.asyncio
async def test_search_by_company(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?q=PH Alpha",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    for p in r.json()["items"]:
        assert (p.get("company_name") or "").lower().find("alpha") >= 0


@pytest.mark.asyncio
async def test_date_filter(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?date_from=2025-03-01&date_to=2025-03-31&page_size=100",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    for p in r.json()["items"]:
        assert "2025-03-" in (p.get("payment_date") or "")


@pytest.mark.asyncio
async def test_payment_method_filter(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?payment_method=cash&page_size=100",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    for p in body["items"]:
        assert p["payment_method"] == "cash"


@pytest.mark.asyncio
async def test_funding_filter(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?funding_source=hrdcorp&page_size=100",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    for p in r.json()["items"]:
        assert p["payment_type"] == "hrdcorp"


@pytest.mark.asyncio
async def test_empty_result(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?q=zzz_no_match_zzz",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_unauthorized_user_forbidden(app_client, coordinator_token, seeded_payments):
    r = await app_client.get("/api/finance/payments/history", headers=auth_headers(coordinator_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_no_token_unauthorized(app_client):
    r = await app_client.get("/api/finance/payments/history")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_recent_payments_still_works(app_client, finance_token, seeded_payments):
    """Recent Payments (existing endpoint) must continue to work — READ-ONLY guarantee."""
    r = await app_client.get("/api/finance/payments", headers=auth_headers(finance_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_existing_payments_unchanged(app_client, finance_token, seeded_payments, db_conn):
    """Payment amounts/dates in DB are not mutated by history queries."""
    sample = seeded_payments["payments"][10]
    before = await db_conn.payments.find_one({"id": sample["id"]}, {"_id": 0})
    await app_client.get(
        f"/api/finance/payments/history?q={sample['reference_number']}",
        headers=auth_headers(finance_token),
    )
    after = await db_conn.payments.find_one({"id": sample["id"]}, {"_id": 0})
    assert before == after


@pytest.mark.asyncio
async def test_payment_detail(app_client, finance_token, seeded_payments):
    pid = seeded_payments["payments"][0]["id"]
    r = await app_client.get(f"/api/finance/payments/{pid}/detail", headers=auth_headers(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert body["payment"]["id"] == pid
    assert body["invoice"] is not None


@pytest.mark.asyncio
async def test_sort_highest(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?sort=highest&page_size=10",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    amounts = [p["amount"] for p in r.json()["items"]]
    assert amounts == sorted(amounts, reverse=True)


@pytest.mark.asyncio
async def test_status_reversed_filter(app_client, finance_token, seeded_payments):
    r = await app_client.get(
        "/api/finance/payments/history?status=reversed",
        headers=auth_headers(finance_token),
    )
    assert r.status_code == 200
    for p in r.json()["items"]:
        assert p.get("status") == "reversed"
