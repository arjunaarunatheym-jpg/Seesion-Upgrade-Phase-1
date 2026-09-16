"""
Tests for the 3 marketing/quotation bug fixes (iter 52):
  1. PDF date range + Attn left-alignment (persisting end_date on client-response)
  2. Revert-acceptance endpoint (with financial-history guard)
  3. Session Costing costing endpoint returns linked quotation snapshot

Env: uses REACT_APP_BACKEND_URL from /app/frontend/.env, MONGO_URL from /app/backend/.env.
Auth: SuperAdmin arjuna@mddrc.com.my.
"""
import os
import uuid
import asyncio
from datetime import datetime

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

TEST_TAG = "iter52_test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"] if "access_token" in r.json() else r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def seeded_client(db):
    cid = str(uuid.uuid4())
    doc = {
        "id": cid,
        "company_name": f"TEST_CO_{cid[:6]}",
        "company_address": "1 Test Street",
        "contact_person": "Ms Test",
        "contact_email": "test@example.com",
        "contact_phone": "0123456789",
        "attn_person": "Ms Attn",
        TEST_TAG: True,
        "created_at": datetime.utcnow().isoformat(),
    }
    run(db.marketing_clients.insert_one(doc))
    yield doc
    run(db.marketing_clients.delete_one({"id": cid}))


def _seed_sent_quotation(db, client_id, extra=None):
    qid = str(uuid.uuid4())
    q = {
        "id": qid,
        "quotation_number": f"TEST-{qid[:6]}",
        "client_id": client_id,
        "programme_name": "Defensive Driving",
        "programme_id": "",
        "num_participants": 10,
        "pricing_type": "lumpsum",
        "group_price": 8000,
        "rate_per_pax": 0,
        "subtotal": 8000,
        "total_amount": 8000,
        "sst_amount": 0,
        "sst_rate": 0,
        "selected_items": [],
        "status": "sent",
        "created_by": "test",
        "created_at": datetime.utcnow().isoformat(),
        TEST_TAG: True,
    }
    if extra:
        q.update(extra)
    run(db.quotations.insert_one(q))
    return qid


@pytest.fixture()
def cleanup_test_data(db):
    yield
    for coll in ["quotations", "sessions", "marketing_clients", "invoices",
                 "trainer_fees", "coordinator_fees", "session_expenses",
                 "marketing_commissions", "companies"]:
        try:
            run(db[coll].delete_many({TEST_TAG: True}))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 1. client-response persists end_date
# ---------------------------------------------------------------------------
class TestClientResponsePersistsEndDate:
    def test_accept_with_end_date_persists(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"])
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers,
            json={
                "response": "accepted",
                "training_date": "2026-10-03",
                "end_date": "2026-10-04",
                "venue": "Test Venue",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        q = run(db.quotations.find_one({"id": qid}, {"_id": 0}))
        assert q["status"] == "accepted"
        assert q.get("end_date") == "2026-10-04"
        assert q.get("training_date") == "2026-10-03"

    def test_accept_without_end_date_defaults_to_training_date(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"])
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers,
            json={"response": "accepted", "training_date": "2026-11-01", "venue": "V"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        q = run(db.quotations.find_one({"id": qid}, {"_id": 0}))
        assert q.get("end_date") == "2026-11-01"


# ---------------------------------------------------------------------------
# 2. PDF renders single / range / list dates
# ---------------------------------------------------------------------------
class TestQuotationPDFRendering:
    def _accept_and_get_pdf(self, db, client_id, auth_headers, body):
        qid = _seed_sent_quotation(db, client_id)
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers, json=body, timeout=30,
        )
        assert r.status_code == 200, r.text
        pr = requests.get(
            f"{BASE_URL}/api/marketing/quotations/{qid}/download-pdf",
            headers=auth_headers, timeout=60,
        )
        return pr, qid

    def test_pdf_single_date(self, db, seeded_client, auth_headers, cleanup_test_data):
        pr, _ = self._accept_and_get_pdf(db, seeded_client["id"], auth_headers, {
            "response": "accepted", "training_date": "2026-10-03", "venue": "V"
        })
        assert pr.status_code == 200, pr.text[:400]
        assert "application/pdf" in pr.headers.get("content-type", ""), pr.headers

    def test_pdf_date_range(self, db, seeded_client, auth_headers, cleanup_test_data):
        pr, _ = self._accept_and_get_pdf(db, seeded_client["id"], auth_headers, {
            "response": "accepted",
            "training_date": "2026-10-03",
            "end_date": "2026-10-04",
            "venue": "V",
        })
        assert pr.status_code == 200, pr.text[:400]
        assert "application/pdf" in pr.headers.get("content-type", ""), pr.headers

    def test_pdf_multiple_non_consecutive_dates(self, db, seeded_client, auth_headers, cleanup_test_data):
        pr, _ = self._accept_and_get_pdf(db, seeded_client["id"], auth_headers, {
            "response": "accepted",
            "training_date": "2026-10-03",
            "training_dates": ["2026-10-03", "2026-10-07", "2026-10-15"],
            "venue": "V",
        })
        assert pr.status_code == 200, pr.text[:400]
        assert "application/pdf" in pr.headers.get("content-type", ""), pr.headers


# ---------------------------------------------------------------------------
# 3. Revert acceptance
# ---------------------------------------------------------------------------
class TestRevertAcceptance:
    def test_revert_happy_path(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"])
        # Accept
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers,
            json={"response": "accepted", "training_date": "2026-10-03",
                  "end_date": "2026-10-04", "venue": "V"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        session_id = r.json().get("session_id")
        assert session_id
        # Mark session with test tag for cleanup
        run(db.sessions.update_one({"id": session_id}, {"$set": {TEST_TAG: True}}))

        # Revert
        rv = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/revert-acceptance",
            headers=auth_headers, timeout=30,
        )
        assert rv.status_code == 200, rv.text

        # Assert quotation reset
        q = run(db.quotations.find_one({"id": qid}, {"_id": 0}))
        assert q["status"] == "sent"
        assert "end_date" not in q or q.get("end_date") in (None, "")
        assert "training_date" not in q or q.get("training_date") in (None, "")

        # Session deleted
        s = run(db.sessions.find_one({"quotation_id": qid}))
        assert s is None, f"session should have been deleted: {s}"

    def test_revert_blocked_by_financial_history(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"])
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers,
            json={"response": "accepted", "training_date": "2026-10-03",
                  "end_date": "2026-10-04", "venue": "V"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        session_id = r.json()["session_id"]
        run(db.sessions.update_one({"id": session_id}, {"$set": {TEST_TAG: True}}))

        # Seed an ISSUED invoice for the session
        inv_id = str(uuid.uuid4())
        run(db.invoices.insert_one({
            "id": inv_id,
            "session_id": session_id,
            "status": "issued",
            "total_amount": 8000,
            "created_at": datetime.utcnow().isoformat(),
            TEST_TAG: True,
        }))

        rv = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/revert-acceptance",
            headers=auth_headers, timeout=30,
        )
        assert rv.status_code == 409, rv.text
        body = rv.json()
        # FastAPI wraps custom detail dict under "detail"
        detail = body.get("detail") if isinstance(body, dict) else None
        assert isinstance(detail, dict), body
        assert detail.get("code") == "SESSION_HAS_FINANCIAL_HISTORY"

        # Quotation still accepted, session still present
        q = run(db.quotations.find_one({"id": qid}, {"_id": 0}))
        assert q["status"] == "accepted"
        s = run(db.sessions.find_one({"id": session_id}))
        assert s is not None

    def test_revert_state_guard_sent_not_allowed(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"])
        rv = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/revert-acceptance",
            headers=auth_headers, timeout=30,
        )
        assert rv.status_code == 400, rv.text


# ---------------------------------------------------------------------------
# 4. Costing endpoint returns quotation snapshot
# ---------------------------------------------------------------------------
class TestSessionCostingQuotationSnapshot:
    def test_costing_returns_quotation_for_linked_session(self, db, seeded_client, auth_headers, cleanup_test_data):
        qid = _seed_sent_quotation(db, seeded_client["id"], extra={
            "total_amount": 8000, "pricing_type": "lumpsum", "group_price": 8000
        })
        r = requests.post(
            f"{BASE_URL}/api/marketing/quotations/{qid}/client-response",
            headers=auth_headers,
            json={"response": "accepted", "training_date": "2026-10-03", "venue": "V"},
            timeout=30,
        )
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        run(db.sessions.update_one({"id": session_id}, {"$set": {TEST_TAG: True}}))

        cr = requests.get(
            f"{BASE_URL}/api/finance/session/{session_id}/costing",
            headers=auth_headers, timeout=30,
        )
        assert cr.status_code == 200, cr.text
        body = cr.json()
        assert "quotation" in body
        assert body["quotation"] is not None
        assert body["quotation"].get("total_amount") == 8000
        assert body["quotation"].get("pricing_type") == "lumpsum"

    def test_costing_no_quotation_for_manual_session(self, db, auth_headers, cleanup_test_data):
        # Create a manual session with no quotation_id
        sid = str(uuid.uuid4())
        run(db.sessions.insert_one({
            "id": sid,
            "name": "TEST manual session",
            "program_id": "",
            "company_id": "",
            "location": "V",
            "start_date": "2026-11-01",
            "end_date": "2026-11-01",
            "expected_participants": 5,
            "status": "draft",
            "supervisor_ids": [],
            "participant_ids": [],
            "trainer_assignments": [],
            "created_at": datetime.utcnow().isoformat(),
            TEST_TAG: True,
        }))
        cr = requests.get(
            f"{BASE_URL}/api/finance/session/{sid}/costing",
            headers=auth_headers, timeout=30,
        )
        assert cr.status_code == 200, cr.text
        body = cr.json()
        assert body.get("quotation") is None


# ---------------------------------------------------------------------------
# 5. Regression — invoice write guard still 409 on issued invoice
# ---------------------------------------------------------------------------
class TestPhase3AInvoiceGuardRegression:
    def test_invoice_endpoint_blocked_when_issued(self, db, auth_headers, cleanup_test_data):
        sid = str(uuid.uuid4())
        run(db.sessions.insert_one({
            "id": sid, "name": "TEST regress", "program_id": "", "company_id": "",
            "location": "V", "start_date": "2026-11-01", "end_date": "2026-11-01",
            "expected_participants": 5, "status": "draft",
            "supervisor_ids": [], "participant_ids": [], "trainer_assignments": [],
            "created_at": datetime.utcnow().isoformat(),
            TEST_TAG: True,
        }))
        inv_id = str(uuid.uuid4())
        run(db.invoices.insert_one({
            "id": inv_id, "session_id": sid, "status": "issued",
            "total_amount": 5000, "invoice_number": f"TEST-INV-{inv_id[:6]}",
            "document_type": "invoice",
            "created_at": datetime.utcnow().isoformat(), TEST_TAG: True,
        }))
        # Link the invoice as the session's primary so the guard resolver picks it up
        run(db.sessions.update_one({"id": sid}, {"$set": {"invoice_id": inv_id}}))
        r = requests.post(
            f"{BASE_URL}/api/finance/session/{sid}/invoice",
            headers=auth_headers,
            json={"lumpsum_amount": 6000, "invoice_date": "2026-11-01"},
            timeout=30,
        )
        assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text}"
        body = r.json()
        detail = body.get("detail")
        text = str(detail)
        assert "INVOICE_LOCKED" in text or "LOCKED" in text.upper(), body
