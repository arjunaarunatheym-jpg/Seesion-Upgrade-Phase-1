"""Phase 2 — Financial Source of Truth tests (16 required tests + hardening).

READ-ONLY: every DB write in this file is a temporary isolated fixture
tagged with the marker ``ph2_test`` and cleaned up on teardown. No
production financial record is ever modified.

TEST DATABASE ISOLATION (Phase 2 final hardening)
--------------------------------------------------
Both the application under test AND the direct fixture DB connection are
FORCED to use an isolated test database (either the value of TEST_DB_NAME
or ``<DB_NAME>_phase2_test``) BEFORE any application module is imported.
A hard safety guard refuses to run this suite if the resolved test
database name does not match a recognized test pattern. This makes it
impossible for this file to write fixture records into a production or
live database. The production ``.env`` is never edited.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- HARD TEST-DB SAFETY GUARD (must run BEFORE any `server`/`core` import) ---
_PRODUCTION_DB_NAME = os.environ.get("DB_NAME", "")
TEST_DB_NAME = os.environ.get("TEST_DB_NAME") or (
    f"{_PRODUCTION_DB_NAME}_phase2_test" if _PRODUCTION_DB_NAME else ""
)


def _is_recognized_test_db(name: str) -> bool:
    """A DB name is only acceptable if it clearly identifies itself as a
    test database. Matches production names are refused."""
    if not name:
        return False
    lname = name.lower()
    if "_phase2_test" in lname:
        return True
    if lname.startswith("test_"):
        return True
    if lname.endswith("_test") or lname.endswith("-test"):
        return True
    return False


if not _is_recognized_test_db(TEST_DB_NAME):
    raise RuntimeError(
        "Phase 2 tests refuse to run: resolved test database name "
        f"{TEST_DB_NAME!r} is not a recognized test database. Expected "
        "the name to contain '_phase2_test', or to start with 'test_', "
        "or to end with '_test'. Override via the TEST_DB_NAME env var."
    )

if _PRODUCTION_DB_NAME and TEST_DB_NAME.lower() == _PRODUCTION_DB_NAME.lower():
    raise RuntimeError(
        f"Phase 2 tests refuse to run: TEST_DB_NAME {TEST_DB_NAME!r} equals "
        f"the production DB_NAME {_PRODUCTION_DB_NAME!r}. Refusing to write "
        "fixture records to a production database."
    )

# Force the FastAPI app under test to use the isolated test DB. The
# production .env value of DB_NAME is NEVER modified — this only sets
# the environment variable inside the pytest process.
os.environ["DB_NAME"] = TEST_DB_NAME

import uuid  # noqa: E402
import pytest  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = TEST_DB_NAME  # canonical test DB name for both app and fixtures

TEST_TAG = "ph2_test"


# -----------------------------------------------------------------------------
# Fixtures (module-scoped — auto-clean at end)
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
async def app_client():
    import sys
    sys.path.insert(0, str(ROOT_DIR))
    from server import app
    # Runtime safety: the app under test MUST be bound to the isolated
    # test database. If a previous test file already imported `core` with
    # a different DB_NAME, `core.db.name` will not match and we refuse to run.
    from core import db as _core_db  # type: ignore
    if _core_db.name != TEST_DB_NAME:
        raise RuntimeError(
            f"Refusing to run Phase 2 tests: FastAPI app is bound to database "
            f"{_core_db.name!r}, expected {TEST_DB_NAME!r}. Run this test file "
            "in its own pytest process, e.g. `pytest tests/test_financial_source_of_truth.py`."
        )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="module")
async def db_conn():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


async def _create_user(db_conn, role: str) -> tuple[str, str]:
    """Seed a user with the requested role. Returns (email, password)."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"ph2_{role}_{uuid.uuid4().hex[:6]}@test.local"
    password = "Test@1234"
    await db_conn.users.insert_one({
        "id": str(uuid.uuid4()),
        "email": email,
        "id_number": f"PH2{uuid.uuid4().hex[:8].upper()}",
        "full_name": f"PH2 {role}",
        "role": role,
        "password": pwd.hash(password),
        "is_active": True,
        TEST_TAG: True,
    })
    return email, password


@pytest.fixture(scope="module")
async def finance_token(app_client, db_conn):
    email, password = await _create_user(db_conn, "finance")
    r = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    yield r.json()["access_token"]
    await db_conn.users.delete_many({"email": email})


@pytest.fixture(scope="module")
async def coord_token(app_client, db_conn):
    email, password = await _create_user(db_conn, "coordinator")
    r = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    yield r.json()["access_token"]
    await db_conn.users.delete_many({"email": email})


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Helpers to seed isolated finance docs
# -----------------------------------------------------------------------------
async def seed_session(db_conn, name: str = "PH2 Session") -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "name": f"{name} {uuid.uuid4().hex[:4]}",
        "company_id": None,
        "start_date": "2026-01-15",
        "end_date": "2026-01-15",
        "participant_ids": [],
        "trainer_assignments": [],
        TEST_TAG: True,
    }
    await db_conn.sessions.insert_one(doc)
    return doc


async def seed_invoice(
    db_conn, session_id: str | None, amount: float,
    document_type: str = "invoice", status: str = "issued",
    converted_from_proforma_id: str | None = None,
    company_name: str = "PH2 Corp",
) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "invoice_number": f"INV/PH2/{uuid.uuid4().hex[:6].upper()}",
        "document_type": document_type,
        "session_id": session_id,
        "company_name": company_name,
        "bill_to_name": company_name,
        "total_amount": amount,
        "tax_amount": 0,
        "status": status,
        "converted_from_proforma_id": converted_from_proforma_id,
        TEST_TAG: True,
    }
    await db_conn.invoices.insert_one(doc)
    return doc


async def seed_payment(
    db_conn, invoice_id: str, amount: float, status: str | None = None,
) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "invoice_id": invoice_id,
        "amount": amount,
        "payment_date": "2026-01-20",
        "payment_method": "bank_transfer",
        "payment_type": "self_pay",
        "receipt_number": f"RCP/PH2/{uuid.uuid4().hex[:5].upper()}",
        "status": status,
        "created_at": "2026-01-20T10:00:00",
        TEST_TAG: True,
    }
    await db_conn.payments.insert_one(doc)
    return doc


async def seed_credit_note(
    db_conn, invoice_id: str | None, amount: float, status: str | None = "issued",
) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "cn_number": f"CN/PH2/{uuid.uuid4().hex[:5].upper()}",
        "invoice_id": invoice_id,
        "amount": amount,
        "status": status,
        TEST_TAG: True,
    }
    await db_conn.credit_notes.insert_one(doc)
    return doc


@pytest.fixture(scope="module")
async def cleanup(db_conn):
    yield
    # Only remove records this test module created (marker isolation).
    await db_conn.sessions.delete_many({TEST_TAG: True})
    await db_conn.invoices.delete_many({TEST_TAG: True})
    await db_conn.payments.delete_many({TEST_TAG: True})
    await db_conn.credit_notes.delete_many({TEST_TAG: True})
    await db_conn.users.delete_many({TEST_TAG: True})


# =============================================================================
# TEST 1 — Single invoice, no payment, no CN
# =============================================================================
@pytest.mark.asyncio
async def test_1_invoice_only(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert body["net_invoiced_value"] == 10000.0
    assert body["paid_amount"] == 0.0
    assert body["outstanding_amount"] == 10000.0
    assert body["payment_status"] == "unpaid"


# =============================================================================
# TEST 2 — Payment reduces outstanding
# =============================================================================
@pytest.mark.asyncio
async def test_2_partial_payment(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_payment(db_conn, inv["id"], 4000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["paid_amount"] == 4000.0
    assert body["outstanding_amount"] == 6000.0
    assert body["payment_status"] == "partially_paid"


# =============================================================================
# TEST 3 — Reversed payment doesn't count
# =============================================================================
@pytest.mark.asyncio
async def test_3_reversed_payment_excluded(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_payment(db_conn, inv["id"], 4000.0)
    await seed_payment(db_conn, inv["id"], 2000.0, status="reversed")
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["paid_amount"] == 4000.0
    assert body["reversed_payment_count"] == 1
    assert body["outstanding_amount"] == 6000.0


# =============================================================================
# TEST 4 — Credit note reduces net invoiced
# =============================================================================
@pytest.mark.asyncio
async def test_4_credit_note_reduces_net(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 1000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["credit_note_total"] == 1000.0
    assert body["net_invoiced_value"] == 9000.0
    assert body["outstanding_amount"] == 9000.0


# =============================================================================
# TEST 5 — Proforma is NOT revenue
# =============================================================================
@pytest.mark.asyncio
async def test_5_proforma_not_revenue(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    pf = await seed_invoice(db_conn, session["id"], 10000.0, document_type="proforma", status="issued")
    # Per-invoice: proforma contributes 0 to net
    r1 = await app_client.get(f"/api/finance/source-of-truth/invoice/{pf['id']}", headers=_auth(finance_token))
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["is_proforma"] is True
    assert b1["net_invoiced_value"] == 0.0
    assert b1["payment_status"] == "n/a_proforma"
    # Session: 0 revenue, 1 proforma count
    r2 = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    b2 = r2.json()
    assert b2["proforma_count"] == 1
    assert b2["invoice_count"] == 0
    assert b2["session_revenue"] == 0.0


# =============================================================================
# TEST 6 — Proforma + linked Invoice = single revenue (RM10k, NOT RM20k)
# =============================================================================
@pytest.mark.asyncio
async def test_6_linked_proforma_and_invoice_not_double_counted(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    pf = await seed_invoice(db_conn, session["id"], 10000.0, document_type="proforma", status="converted")
    await seed_invoice(
        db_conn, session["id"], 10000.0,
        document_type="invoice", status="issued",
        converted_from_proforma_id=pf["id"],
    )
    r = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["invoice_count"] == 1
    assert body["proforma_count"] == 1
    assert body["session_revenue"] == 10000.0, f"Expected 10000 (not 20000), got {body['session_revenue']}"
    # No unlinked-match warning because the link is known.
    warn_codes = {w["code"] for w in body["integrity_warnings"]}
    assert "PROFORMA_UNLINKED_MATCH" not in warn_codes


# =============================================================================
# TEST 7 — Ambiguous Proforma + Invoice same value, no link -> integrity warning
# =============================================================================
@pytest.mark.asyncio
async def test_7_ambiguous_proforma_flags_warning(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 10000.0, document_type="proforma", status="issued")
    await seed_invoice(db_conn, session["id"], 10000.0, document_type="invoice", status="issued")
    r = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["session_revenue"] == 10000.0, "must not double-count ambiguous pair"
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "PROFORMA_UNLINKED_MATCH" in codes


# =============================================================================
# TEST 8 — Two legitimate invoices in one session sum correctly
# =============================================================================
@pytest.mark.asyncio
async def test_8_multiple_invoices_per_session(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 6000.0)
    await seed_invoice(db_conn, session["id"], 4000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["invoice_count"] == 2
    assert body["session_revenue"] == 10000.0
    assert body["gross_invoice_value"] == 10000.0


# =============================================================================
# TEST 9 — Payment distributed across multiple invoices
# =============================================================================
@pytest.mark.asyncio
async def test_9_payments_across_invoices(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    a = await seed_invoice(db_conn, session["id"], 6000.0)
    b = await seed_invoice(db_conn, session["id"], 4000.0)
    await seed_payment(db_conn, a["id"], 6000.0)
    await seed_payment(db_conn, b["id"], 1000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["paid_amount"] == 7000.0
    assert body["outstanding_amount"] == 3000.0


# =============================================================================
# TEST 10 — Invoice with multiple credit notes aggregates correctly
# =============================================================================
@pytest.mark.asyncio
async def test_10_multiple_credit_notes(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 500.0)
    await seed_credit_note(db_conn, inv["id"], 250.0)
    await seed_credit_note(db_conn, inv["id"], 250.0, status="voided")  # ignored
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["credit_note_total"] == 750.0
    assert body["credit_note_count"] == 2
    assert body["active_credit_note_count"] == 2
    assert body["voided_credit_note_count"] == 1  # STRICT — only status == "voided"
    assert body["inactive_credit_note_count"] == 1
    assert body["unrecognized_credit_note_count"] == 0
    assert body["net_invoiced_value"] == 9250.0


# =============================================================================
# TEST 11 — Reversed payment cannot inflate paid amount
# =============================================================================
@pytest.mark.asyncio
async def test_11_only_reversed_payment(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_payment(db_conn, inv["id"], 5000.0, status="reversed")
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["paid_amount"] == 0.0
    assert body["outstanding_amount"] == 10000.0


# =============================================================================
# TEST 12 — Payment referencing missing invoice -> integrity warning, no crash
# =============================================================================
@pytest.mark.asyncio
async def test_12_payment_missing_invoice_warning(app_client, finance_token, db_conn, cleanup):
    ghost_invoice_id = str(uuid.uuid4())
    await seed_payment(db_conn, ghost_invoice_id, 100.0)
    r = await app_client.get("/api/finance/source-of-truth/integrity/payments", headers=_auth(finance_token))
    assert r.status_code == 200
    warns = r.json()["warnings"]
    codes = {w["code"] for w in warns}
    assert "PAYMENT_MISSING_INVOICE" in codes


# =============================================================================
# TEST 13 — Credit note referencing missing invoice -> integrity warning
# =============================================================================
@pytest.mark.asyncio
async def test_13_credit_note_missing_invoice_warning(app_client, finance_token, db_conn, cleanup):
    await seed_credit_note(db_conn, str(uuid.uuid4()), 50.0)
    r = await app_client.get("/api/finance/source-of-truth/integrity/credit-notes", headers=_auth(finance_token))
    assert r.status_code == 200
    codes = {w["code"] for w in r.json()["warnings"]}
    assert "CN_MISSING_INVOICE" in codes


# =============================================================================
# TEST 14 — Authorization: unauthorized role is rejected
# =============================================================================
@pytest.mark.asyncio
async def test_14_authorization(app_client, coord_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 100.0)
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(coord_token))
    assert r.status_code == 403
    r2 = await app_client.get(f"/api/finance/source-of-truth/session/dummy", headers=_auth(coord_token))
    assert r2.status_code == 403
    # Missing token -> 401/403
    r3 = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}")
    assert r3.status_code in (401, 403)


# =============================================================================
# TEST 15 — READ-ONLY guarantee: DB records unchanged after calls
# =============================================================================
@pytest.mark.asyncio
async def test_15_read_only_guarantee(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0)
    pay = await seed_payment(db_conn, inv["id"], 3000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 500.0)

    before_inv = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    before_pay = await db_conn.payments.find_one({"id": pay["id"]}, {"_id": 0})
    before_cn = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    before_sess = await db_conn.sessions.find_one({"id": session["id"]}, {"_id": 0})

    # Exercise every read endpoint
    await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    await app_client.get("/api/finance/source-of-truth/integrity/payments", headers=_auth(finance_token))
    await app_client.get("/api/finance/source-of-truth/integrity/credit-notes", headers=_auth(finance_token))

    after_inv = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    after_pay = await db_conn.payments.find_one({"id": pay["id"]}, {"_id": 0})
    after_cn = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    after_sess = await db_conn.sessions.find_one({"id": session["id"]}, {"_id": 0})

    assert before_inv == after_inv
    assert before_pay == after_pay
    assert before_cn == after_cn
    assert before_sess == after_sess


# =============================================================================
# TEST 16 — Phase 1 regression: Payment History endpoints still respond
# =============================================================================
@pytest.mark.asyncio
async def test_16_phase1_regression(app_client, finance_token, db_conn, cleanup):
    r = await app_client.get("/api/finance/payments/history?page=1&page_size=5", headers=_auth(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "page" in body and "total" in body
    # CSV export still works
    r2 = await app_client.get("/api/finance/payments/history/export", headers=_auth(finance_token))
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("text/csv")
    # page_size > 100 still rejected
    r3 = await app_client.get("/api/finance/payments/history?page_size=101", headers=_auth(finance_token))
    assert r3.status_code == 422


# =============================================================================
# Bonus regression — 404 for nonexistent snapshots
# =============================================================================
@pytest.mark.asyncio
async def test_nonexistent_returns_404(app_client, finance_token, db_conn, cleanup):
    r1 = await app_client.get("/api/finance/source-of-truth/invoice/nope-nope", headers=_auth(finance_token))
    assert r1.status_code == 404
    r2 = await app_client.get("/api/finance/source-of-truth/session/nope-nope", headers=_auth(finance_token))
    assert r2.status_code == 404


# =============================================================================
# CORRECTION 1 & 2 — Strict whitelist eligibility + router mount verification
# =============================================================================

@pytest.mark.asyncio
async def test_A_draft_invoice_not_revenue(app_client, finance_token, db_conn, cleanup):
    """TEST A — Draft invoice must contribute zero canonical revenue."""
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="draft")

    r1 = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r1.json()
    assert body["is_revenue_eligible"] is False
    assert body["net_invoiced_value"] == 0.0
    assert body["outstanding_amount"] == 0.0
    assert body["payment_status"] == "n/a_draft"

    r2 = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body2 = r2.json()
    assert body2["invoice_count"] == 0
    assert body2["session_revenue"] == 0.0


@pytest.mark.asyncio
async def test_B_unknown_status_not_revenue(app_client, finance_token, db_conn, cleanup):
    """TEST B — Unknown legacy status must contribute zero and trigger warning."""
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="legacy_unknown")

    r1 = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r1.json()
    assert body["is_revenue_eligible"] is False
    assert body["net_invoiced_value"] == 0.0
    assert body["outstanding_amount"] == 0.0
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "UNRECOGNIZED_INVOICE_STATUS" in codes
    assert body["payment_status"] == "n/a_unknown"

    r2 = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    body2 = r2.json()
    assert body2["session_revenue"] == 0.0


@pytest.mark.asyncio
async def test_C_cancelled_and_voided_consistency(app_client, finance_token, db_conn, cleanup):
    """TEST C — Cancelled and voided invoices contribute zero canonical revenue,
    and per-invoice + session snapshots agree.
    """
    for excluded_status in ("cancelled", "voided"):
        session = await seed_session(db_conn)
        inv = await seed_invoice(db_conn, session["id"], 10000.0, status=excluded_status)

        r1 = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
        b1 = r1.json()
        assert b1["is_revenue_eligible"] is False, f"{excluded_status} must be non-eligible"
        assert b1["net_invoiced_value"] == 0.0
        assert b1["outstanding_amount"] == 0.0
        assert b1["payment_status"] == excluded_status

        r2 = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
        b2 = r2.json()
        assert b2["session_revenue"] == 0.0
        assert b2["invoice_count"] == 0


@pytest.mark.asyncio
async def test_D_router_actually_mounted(app_client, finance_token, db_conn, cleanup):
    """TEST D — Route is registered on the actual FastAPI app (server.py).
    Verifies that both the invoice and session endpoints respond with the
    Phase 2 canonical shape rather than 404.
    """
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 500.0)

    r_inv = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    assert r_inv.status_code == 200, f"invoice route not mounted: {r_inv.status_code} {r_inv.text[:200]}"
    body_inv = r_inv.json()
    # Canonical Phase 2 keys must be present
    for k in ("net_invoiced_value", "is_revenue_eligible", "payment_status", "breakdown", "integrity_warnings"):
        assert k in body_inv, f"missing canonical key: {k}"

    r_sess = await app_client.get(f"/api/finance/source-of-truth/session/{session['id']}", headers=_auth(finance_token))
    assert r_sess.status_code == 200, f"session route not mounted: {r_sess.status_code} {r_sess.text[:200]}"
    for k in ("session_revenue", "session_cost", "gross_profit", "invoice_count", "proforma_count", "integrity_warnings"):
        assert k in r_sess.json()


@pytest.mark.asyncio
async def test_E_non_eligible_with_payment(app_client, finance_token, db_conn, cleanup):
    """TEST E — Draft invoice with an active payment.
    Canonical net_invoiced / outstanding must remain 0.
    Underlying payment record must NOT be changed.
    Integrity warning should be surfaced.
    """
    inv = await seed_invoice(db_conn, None, 10000.0, status="draft")
    pay = await seed_payment(db_conn, inv["id"], 2000.0)

    before_pay = await db_conn.payments.find_one({"id": pay["id"]}, {"_id": 0})

    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    body = r.json()
    assert body["is_revenue_eligible"] is False
    assert body["net_invoiced_value"] == 0.0
    assert body["outstanding_amount"] == 0.0
    # The paid_amount is still readable (records are preserved), but canonical
    # net/outstanding are 0 because the invoice is non-eligible.
    assert body["paid_amount"] == 2000.0
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY" in codes

    after_pay = await db_conn.payments.find_one({"id": pay["id"]}, {"_id": 0})
    assert before_pay == after_pay, "Phase 2 must never mutate payment records"


@pytest.mark.asyncio
async def test_E2_cancelled_with_payment_has_two_warnings(app_client, finance_token, db_conn, cleanup):
    """Cancelled + active payment yields BOTH NON_ELIGIBLE_INVOICE_HAS_ACTIVITY
    and VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS."""
    inv = await seed_invoice(db_conn, None, 5000.0, status="cancelled")
    await seed_payment(db_conn, inv["id"], 1000.0)
    r = await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}", headers=_auth(finance_token))
    codes = {w["code"] for w in r.json()["integrity_warnings"]}
    assert "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY" in codes
    assert "VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS" in codes


# =============================================================================
# CREDIT NOTE STRICT ELIGIBILITY — Correction (tests A–I)
# =============================================================================

@pytest.mark.asyncio
async def test_CN_A_draft_reduces_net(app_client, finance_token, db_conn, cleanup):
    """CN with status='draft' MUST reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 300.0, status="draft")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 300.0
    assert b["net_invoiced_value"] == 9700.0


@pytest.mark.asyncio
async def test_CN_B_approved_reduces_net(app_client, finance_token, db_conn, cleanup):
    """CN with status='approved' MUST reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 250.0, status="approved")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 250.0
    assert b["net_invoiced_value"] == 9750.0


@pytest.mark.asyncio
async def test_CN_C_issued_reduces_net(app_client, finance_token, db_conn, cleanup):
    """CN with status='issued' MUST reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 500.0, status="issued")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 500.0
    assert b["net_invoiced_value"] == 9500.0


@pytest.mark.asyncio
async def test_CN_D_voided_does_not_reduce_net(app_client, finance_token, db_conn, cleanup):
    """CN with status='voided' MUST NOT reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 999.0, status="voided")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["voided_credit_note_count"] == 1
    assert b["net_invoiced_value"] == 10000.0


@pytest.mark.asyncio
async def test_CN_E_cancelled_does_not_reduce_net(app_client, finance_token, db_conn, cleanup):
    """CN with status='cancelled' MUST NOT reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 800.0, status="cancelled")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["net_invoiced_value"] == 10000.0


@pytest.mark.asyncio
async def test_CN_F_unknown_status_does_not_reduce_net(app_client, finance_token, db_conn, cleanup):
    """CN with an unknown/typo status MUST NOT reduce net invoiced value."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 750.0, status="legacy_typo")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["net_invoiced_value"] == 10000.0


@pytest.mark.asyncio
async def test_CN_G_unknown_status_emits_warning(app_client, finance_token, db_conn, cleanup):
    """Unknown CN status MUST emit UNRECOGNIZED_CREDIT_NOTE_STATUS."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="mystery_status")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    codes = {w["code"] for w in b["integrity_warnings"]}
    assert "UNRECOGNIZED_CREDIT_NOTE_STATUS" in codes


@pytest.mark.asyncio
async def test_CN_H_unknown_cn_record_unchanged(app_client, finance_token, db_conn, cleanup):
    """The underlying CN record MUST NOT be modified by the API call."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 100.0, status="mystery_status")
    before = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                         headers=_auth(finance_token))
    after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert before == after, "Phase 2 must NEVER mutate credit-note records"


@pytest.mark.asyncio
async def test_CN_I_missing_status_treated_safely(app_client, finance_token, db_conn, cleanup):
    """Per the read-only Phase 2 CN status audit, no legacy rows have missing
    status (0 records). Safest canonical treatment: missing/null status is
    treated as unrecognized (does NOT reduce net) and emits
    UNRECOGNIZED_CREDIT_NOTE_STATUS. The underlying record is untouched.
    """
    inv = await seed_invoice(db_conn, None, 10000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 400.0, status=None)
    before = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0, "null/missing CN status must not reduce net"
    assert b["net_invoiced_value"] == 10000.0
    codes = {w["code"] for w in b["integrity_warnings"]}
    assert "UNRECOGNIZED_CREDIT_NOTE_STATUS" in codes
    after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert before == after


# =============================================================================
# FINAL HARDENING 1 — Session integrity warnings for excluded invoices
# =============================================================================

@pytest.mark.asyncio
async def test_HARDENING_session_cancelled_invoice_with_payment_surfaces_warnings(
    app_client, finance_token, db_conn, cleanup,
):
    """SESSION + CANCELLED RM10,000 invoice + ACTIVE RM2,000 payment.
    Canonical session totals MUST remain zero and must NOT include the
    cancelled invoice value or the payment. Session integrity warnings
    MUST include NON_ELIGIBLE_INVOICE_HAS_ACTIVITY and
    VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS.
    """
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="cancelled")
    await seed_payment(db_conn, inv["id"], 2000.0)

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()

    # Canonical totals — cancelled invoice contributes ZERO to every total.
    assert body["session_revenue"] == 0.0
    assert body["net_invoiced_value"] == 0.0
    assert body["outstanding_amount"] == 0.0
    assert body["gross_invoice_value"] == 0.0
    assert body["paid_amount"] == 0.0

    # Counts — no active invoice, exactly one excluded invoice.
    assert body["invoice_count"] == 0
    assert body["excluded_invoice_count"] == 1

    # Excluded invoice is exposed for audit only; financial values still 0.
    assert len(body["excluded_invoice_summaries"]) == 1
    summary = body["excluded_invoice_summaries"][0]
    assert summary["invoice_id"] == inv["id"]
    assert summary["normalized_status"] == "cancelled"
    assert summary["net_invoiced_value"] == 0.0
    assert summary["outstanding_amount"] == 0.0

    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY" in codes
    assert "VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS" in codes


@pytest.mark.asyncio
async def test_HARDENING_session_unknown_status_invoice_surfaces_warning(
    app_client, finance_token, db_conn, cleanup,
):
    """SESSION + invoice with an UNKNOWN status.
    Session revenue MUST be 0 and session integrity warnings MUST include
    UNRECOGNIZED_INVOICE_STATUS.
    """
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 10000.0, status="something_weird")

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()

    assert body["session_revenue"] == 0.0
    assert body["invoice_count"] == 0
    assert body["excluded_invoice_count"] == 1
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "UNRECOGNIZED_INVOICE_STATUS" in codes


@pytest.mark.asyncio
async def test_HARDENING_session_excluded_invoice_does_not_duplicate_warnings(
    app_client, finance_token, db_conn, cleanup,
):
    """A cancelled invoice with a payment must produce EXACTLY ONE
    NON_ELIGIBLE_INVOICE_HAS_ACTIVITY warning at the session level (not one
    per aggregation pass)."""
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 5000.0, status="cancelled")
    await seed_payment(db_conn, inv["id"], 1000.0)

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    body = r.json()
    non_eligible_warnings = [
        w for w in body["integrity_warnings"]
        if w["code"] == "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY"
    ]
    assert len(non_eligible_warnings) == 1, (
        f"expected exactly 1 warning, got {len(non_eligible_warnings)}"
    )


# =============================================================================
# FINAL HARDENING 2 — Test DB isolation guarantees
# =============================================================================

@pytest.mark.asyncio
async def test_HARDENING_app_and_fixtures_use_isolated_test_db(app_client, db_conn):
    """Guardrail: the running app AND the direct fixture connection MUST
    both be bound to the isolated test DB (name != production DB_NAME)."""
    from core import db as _core_db  # type: ignore
    assert _core_db.name == TEST_DB_NAME
    assert db_conn.name == TEST_DB_NAME
    # Production DB name must NEVER equal the test DB name.
    prod = _PRODUCTION_DB_NAME
    if prod:
        assert _core_db.name.lower() != prod.lower()
        assert db_conn.name.lower() != prod.lower()


def test_HARDENING_test_db_name_is_recognized():
    """The resolved TEST_DB_NAME must satisfy the recognizer used by the
    hard safety guard at import time."""
    assert _is_recognized_test_db(TEST_DB_NAME)


# =============================================================================
# FINAL HARDENING 3 — Credit Note count semantics
# =============================================================================

@pytest.mark.asyncio
async def test_HARDENING_cn_count_issued_is_active(app_client, finance_token, db_conn, cleanup):
    """Issued CN counts under active_credit_note_count and NOT under
    voided_credit_note_count / inactive_credit_note_count / unrecognized."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="issued")
    b = (await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv['id']}",
        headers=_auth(finance_token),
    )).json()
    assert b["active_credit_note_count"] == 1
    assert b["credit_note_count"] == 1
    assert b["inactive_credit_note_count"] == 0
    assert b["voided_credit_note_count"] == 0
    assert b["unrecognized_credit_note_count"] == 0


@pytest.mark.asyncio
async def test_HARDENING_cn_count_voided_is_voided(app_client, finance_token, db_conn, cleanup):
    """Voided CN counts under voided_credit_note_count AND inactive_credit_note_count."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="voided")
    b = (await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv['id']}",
        headers=_auth(finance_token),
    )).json()
    assert b["active_credit_note_count"] == 0
    assert b["voided_credit_note_count"] == 1
    assert b["inactive_credit_note_count"] == 1
    assert b["unrecognized_credit_note_count"] == 0


@pytest.mark.asyncio
async def test_HARDENING_cn_count_cancelled_is_inactive_but_not_voided(
    app_client, finance_token, db_conn, cleanup,
):
    """Cancelled CN counts under inactive_credit_note_count but NOT under
    the strict voided_credit_note_count."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="cancelled")
    b = (await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv['id']}",
        headers=_auth(finance_token),
    )).json()
    assert b["active_credit_note_count"] == 0
    assert b["voided_credit_note_count"] == 0, "cancelled is NOT voided"
    assert b["inactive_credit_note_count"] == 1
    assert b["unrecognized_credit_note_count"] == 0


@pytest.mark.asyncio
async def test_HARDENING_cn_count_unknown_is_unrecognized_and_warns(
    app_client, finance_token, db_conn, cleanup,
):
    """Unknown-status CN counts under unrecognized_credit_note_count only,
    NOT under voided or inactive, and produces an integrity warning."""
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="mystery_x")
    b = (await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv['id']}",
        headers=_auth(finance_token),
    )).json()
    assert b["active_credit_note_count"] == 0
    assert b["voided_credit_note_count"] == 0
    assert b["inactive_credit_note_count"] == 0
    assert b["unrecognized_credit_note_count"] == 1
    codes = {w["code"] for w in b["integrity_warnings"]}
    assert "UNRECOGNIZED_CREDIT_NOTE_STATUS" in codes

# =============================================================================
# FINAL PROFORMA INTEGRITY HARDENING — session-level warning propagation
# =============================================================================

@pytest.mark.asyncio
async def test_HARDENING_proforma_with_active_payment_surfaces_warning(
    app_client, finance_token, db_conn, cleanup,
):
    """TEST 1 — Session + RM10,000 Proforma + RM2,000 active payment.
    Session canonical totals MUST remain 0 (Proforma is never revenue),
    but the session integrity_warnings MUST include
    NON_ELIGIBLE_INVOICE_HAS_ACTIVITY surfaced from the Proforma.
    """
    session = await seed_session(db_conn)
    pf = await seed_invoice(
        db_conn, session["id"], 10000.0,
        document_type="proforma", status="issued",
    )
    await seed_payment(db_conn, pf["id"], 2000.0)

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()

    # Proforma contributes ZERO to every canonical session total.
    assert body["session_revenue"] == 0.0
    assert body["net_invoiced_value"] == 0.0
    assert body["paid_amount"] == 0.0
    assert body["outstanding_amount"] == 0.0
    assert body["gross_invoice_value"] == 0.0

    # Counts — no active invoice, exactly one proforma.
    assert body["invoice_count"] == 0
    assert body["proforma_count"] == 1

    # Proforma is exposed for audit only; financial values still 0.
    assert len(body["proforma_summaries"]) == 1
    summary = body["proforma_summaries"][0]
    assert summary["invoice_id"] == pf["id"]
    assert summary["document_type"] == "proforma"
    assert summary["payment_status"] == "n/a_proforma"
    assert summary["net_invoiced_value"] == 0.0
    assert summary["outstanding_amount"] == 0.0

    # The integrity warning attached to the proforma MUST reach the session.
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY" in codes

    # Exactly one such warning — not duplicated by any other loop.
    non_eligible = [
        w for w in body["integrity_warnings"]
        if w["code"] == "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY"
    ]
    assert len(non_eligible) == 1


@pytest.mark.asyncio
async def test_HARDENING_proforma_with_unknown_status_cn_surfaces_warning(
    app_client, finance_token, db_conn, cleanup,
):
    """TEST 2 — Session + Proforma + Credit Note with unrecognized status.
    Proforma contributes zero financial value.
    UNRECOGNIZED_CREDIT_NOTE_STATUS MUST appear at session level.
    Underlying CN record MUST remain unchanged.
    """
    session = await seed_session(db_conn)
    pf = await seed_invoice(
        db_conn, session["id"], 10000.0,
        document_type="proforma", status="issued",
    )
    cn = await seed_credit_note(db_conn, pf["id"], 250.0, status="mystery_xyz")
    before_cn = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()

    # Proforma still zero-revenue.
    assert body["session_revenue"] == 0.0
    assert body["net_invoiced_value"] == 0.0
    assert body["credit_note_total"] == 0.0
    assert body["invoice_count"] == 0
    assert body["proforma_count"] == 1

    codes = {w["code"] for w in body["integrity_warnings"]}
    assert "UNRECOGNIZED_CREDIT_NOTE_STATUS" in codes

    # Underlying CN record must be untouched.
    after_cn = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert before_cn == after_cn, "Phase 2 must NEVER mutate credit-note records"


@pytest.mark.asyncio
async def test_HARDENING_clean_proforma_produces_no_false_positive(
    app_client, finance_token, db_conn, cleanup,
):
    """TEST 3 — Session + normal Proforma with no suspicious activity.
    Proforma still contributes zero revenue.
    No NON_ELIGIBLE_INVOICE_HAS_ACTIVITY / VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS /
    UNRECOGNIZED_INVOICE_STATUS / UNRECOGNIZED_CREDIT_NOTE_STATUS should be
    fabricated for a clean proforma.
    """
    session = await seed_session(db_conn)
    await seed_invoice(
        db_conn, session["id"], 7500.0,
        document_type="proforma", status="issued",
    )

    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()

    assert body["session_revenue"] == 0.0
    assert body["net_invoiced_value"] == 0.0
    assert body["paid_amount"] == 0.0
    assert body["outstanding_amount"] == 0.0
    assert body["invoice_count"] == 0
    assert body["proforma_count"] == 1
    assert len(body["proforma_summaries"]) == 1

    forbidden_codes = {
        "NON_ELIGIBLE_INVOICE_HAS_ACTIVITY",
        "VOIDED_INVOICE_HAS_ACTIVE_PAYMENTS",
        "UNRECOGNIZED_INVOICE_STATUS",
        "UNRECOGNIZED_CREDIT_NOTE_STATUS",
    }
    codes = {w["code"] for w in body["integrity_warnings"]}
    assert not (codes & forbidden_codes), (
        f"Clean proforma must not fabricate warnings; got: {codes & forbidden_codes}"
    )

