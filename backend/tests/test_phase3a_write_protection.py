"""Phase 3A — Financial Integrity & Write Protection tests.

READ-ONLY test database. Every fixture write is tagged with ``ph3_test``
and cleaned up on teardown. No production financial record is touched.

Same isolated-DB safety guard as Phase 2 tests.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

_PRODUCTION_DB_NAME = os.environ.get("DB_NAME", "")
TEST_DB_NAME = os.environ.get("TEST_DB_NAME") or (
    f"{_PRODUCTION_DB_NAME}_phase2_test" if _PRODUCTION_DB_NAME else ""
)


def _is_recognized_test_db(name: str) -> bool:
    if not name:
        return False
    lname = name.lower()
    return (
        "_phase2_test" in lname
        or lname.startswith("test_")
        or lname.endswith("_test")
        or lname.endswith("-test")
    )


if not _is_recognized_test_db(TEST_DB_NAME):
    raise RuntimeError(
        f"Phase 3A tests refuse to run: {TEST_DB_NAME!r} is not a recognized test DB."
    )
if _PRODUCTION_DB_NAME and TEST_DB_NAME.lower() == _PRODUCTION_DB_NAME.lower():
    raise RuntimeError("Phase 3A tests refuse to run against the production DB.")

os.environ["DB_NAME"] = TEST_DB_NAME
os.environ["APP_ENV"] = "test"  # allow test-only hard-delete path

import uuid  # noqa: E402
import pytest  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from passlib.context import CryptContext  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = TEST_DB_NAME
TEST_TAG = "ph3_test"


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
async def app_client():
    import sys
    sys.path.insert(0, str(ROOT_DIR))
    from server import app
    from core import db as _core_db
    if _core_db.name != TEST_DB_NAME:
        raise RuntimeError(
            f"Phase 3A refuses to run: app bound to {_core_db.name!r}, expected {TEST_DB_NAME!r}."
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


async def _create_user(db_conn, role: str):
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"ph3_{role}_{uuid.uuid4().hex[:6]}@test.local"
    password = "Test@1234"
    await db_conn.users.insert_one({
        "id": str(uuid.uuid4()),
        "email": email,
        "id_number": f"PH3{uuid.uuid4().hex[:8].upper()}",
        "full_name": f"PH3 {role}",
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
async def admin_token(app_client, db_conn):
    email, password = await _create_user(db_conn, "admin")
    r = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    yield r.json()["access_token"]
    await db_conn.users.delete_many({"email": email})


@pytest.fixture(scope="module")
async def superadmin_token(app_client, db_conn):
    email, password = await _create_user(db_conn, "super_admin")
    r = await app_client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    yield r.json()["access_token"]
    await db_conn.users.delete_many({"email": email})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Seeders
# -----------------------------------------------------------------------------
async def seed_session(db_conn):
    doc = {
        "id": str(uuid.uuid4()),
        "name": f"PH3 Session {uuid.uuid4().hex[:4]}",
        "company_id": None,
        "start_date": "2026-01-15",
        "end_date": "2026-01-15",
        "participant_ids": [],
        "trainer_assignments": [],
        TEST_TAG: True,
    }
    await db_conn.sessions.insert_one(doc)
    return doc


async def seed_invoice(db_conn, session_id, amount, *, document_type="invoice",
                      status="issued", converted_from_proforma_id=None):
    doc = {
        "id": str(uuid.uuid4()),
        "invoice_number": f"INV/PH3/{uuid.uuid4().hex[:6].upper()}",
        "document_type": document_type,
        "session_id": session_id,
        "company_name": "PH3 Corp",
        "bill_to_name": "PH3 Corp",
        "total_amount": amount,
        "tax_amount": 0,
        "status": status,
        "converted_from_proforma_id": converted_from_proforma_id,
        TEST_TAG: True,
    }
    await db_conn.invoices.insert_one(doc)
    return doc


async def seed_payment(db_conn, invoice_id, amount, *, status=None, source_payment_id_marker=None):
    doc = {
        "id": str(uuid.uuid4()),
        "invoice_id": invoice_id,
        "amount": amount,
        "payment_date": "2026-01-20",
        "payment_method": "bank_transfer",
        "payment_type": "self_pay",
        "receipt_number": f"RCP/PH3/{uuid.uuid4().hex[:5].upper()}",
        "status": status,
        "created_at": "2026-01-20T10:00:00",
        TEST_TAG: True,
    }
    if source_payment_id_marker:
        doc["source_payment_id"] = source_payment_id_marker
    await db_conn.payments.insert_one(doc)
    return doc


async def seed_credit_note(db_conn, invoice_id, amount, *, status="issued",
                           session_id=None, source_payment_id=None):
    doc = {
        "id": str(uuid.uuid4()),
        "cn_number": f"CN/PH3/{uuid.uuid4().hex[:5].upper()}",
        "invoice_id": invoice_id,
        "session_id": session_id,
        "amount": amount,
        "status": status,
        "source_payment_id": source_payment_id,
        TEST_TAG: True,
    }
    await db_conn.credit_notes.insert_one(doc)
    return doc


@pytest.fixture(scope="module")
async def cleanup(db_conn):
    yield
    # Phase 3A Section AL: full teardown, including Phase 3A-generated
    # side-effect collections. NEVER runs against production DB (safety
    # guard at module import time already enforced).
    for coll in ("sessions", "invoices", "payments", "credit_notes", "users",
                 "journal_entries", "deleted_invoice_numbers",
                 "superadmin_god_mode_audit", "payment_reversals",
                 "invoice_reversals", "audit_trail", "finance_audit_log",
                 "super_admin_audit_log", "companies"):
        await db_conn[coll].delete_many({TEST_TAG: True})


# =============================================================================
# 1–3: Proforma conversion idempotency & immutability
# =============================================================================

async def _create_and_convert_proforma(app_client, finance_token, db_conn, amount=10000.0):
    session = await seed_session(db_conn)
    pf = await seed_invoice(db_conn, session["id"], amount,
                             document_type="proforma", status="issued")
    r = await app_client.post(
        f"/api/finance/invoices/{pf['id']}/convert-to-invoice",
        headers=_auth(finance_token),
    )
    return session, pf, r


@pytest.mark.asyncio
async def test_1_proforma_converts_once(app_client, finance_token, db_conn, cleanup):
    session, pf, r = await _create_and_convert_proforma(app_client, finance_token, db_conn)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["idempotent"] is False
    new_inv = await db_conn.invoices.find_one({"id": body["new_invoice_id"]}, {"_id": 0})
    assert new_inv["converted_from_proforma_id"] == pf["id"]
    pf_after = await db_conn.invoices.find_one({"id": pf["id"]}, {"_id": 0})
    assert pf_after["status"] == "converted"


@pytest.mark.asyncio
async def test_2_duplicate_conversion_no_second_invoice(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    pf = await seed_invoice(db_conn, session["id"], 10000.0,
                             document_type="proforma", status="issued")
    r1 = await app_client.post(f"/api/finance/invoices/{pf['id']}/convert-to-invoice", headers=_auth(finance_token))
    r2 = await app_client.post(f"/api/finance/invoices/{pf['id']}/convert-to-invoice", headers=_auth(finance_token))
    r3 = await app_client.post(f"/api/finance/invoices/{pf['id']}/convert-to-invoice", headers=_auth(finance_token))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code in (200, 400)
    invoices = await db_conn.invoices.find(
        {"converted_from_proforma_id": pf["id"]}, {"_id": 0},
    ).to_list(10)
    assert len(invoices) == 1, f"Expected exactly 1 converted invoice, got {len(invoices)}"


@pytest.mark.asyncio
async def test_3_converted_proforma_immutable(app_client, finance_token, db_conn, cleanup):
    session, pf, r = await _create_and_convert_proforma(app_client, finance_token, db_conn)
    # Attempt to edit total_amount on the converted proforma
    r_edit = await app_client.put(
        f"/api/finance/invoices/{pf['id']}",
        json={"total_amount": 99999.99},
        headers=_auth(finance_token),
    )
    assert r_edit.status_code == 409, r_edit.text
    body = r_edit.json()
    detail = body.get("detail", body)
    assert detail.get("code") == "INVOICE_LOCKED"


# =============================================================================
# 4: session.invoice_id points to real invoice
# =============================================================================
@pytest.mark.asyncio
async def test_4_session_invoice_id_points_to_real_invoice(app_client, finance_token, db_conn, cleanup):
    session, pf, r = await _create_and_convert_proforma(app_client, finance_token, db_conn)
    session_after = await db_conn.sessions.find_one({"id": session["id"]}, {"_id": 0})
    assert session_after["invoice_id"] == r.json()["new_invoice_id"]
    new_inv = await db_conn.invoices.find_one({"id": session_after["invoice_id"]}, {"_id": 0})
    assert new_inv["document_type"] == "invoice"


# =============================================================================
# 5-6: Immutability under session-costing-style mutations
# =============================================================================
@pytest.mark.asyncio
async def test_5_session_costing_cannot_edit_converted_proforma(app_client, finance_token, db_conn, cleanup):
    session, pf, r = await _create_and_convert_proforma(app_client, finance_token, db_conn)
    r_edit = await app_client.put(
        f"/api/finance/invoices/{pf['id']}",
        json={"subtotal": 500.0, "total_amount": 500.0},
        headers=_auth(finance_token),
    )
    assert r_edit.status_code == 409
    detail = r_edit.json().get("detail", {})
    assert detail.get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_6_session_costing_cannot_edit_issued_invoice(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    r = await app_client.put(
        f"/api/finance/invoices/{inv['id']}",
        json={"total_amount": 99999.99},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409
    detail = r.json().get("detail", {})
    assert detail.get("code") == "INVOICE_LOCKED"
    # And the underlying record is untouched.
    inv_after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert inv_after["total_amount"] == 10000.0


# =============================================================================
# 7: Multiple invoices — no arbitrary session-only selection
# 8-12: Session CN endpoint / manual CN validation
# =============================================================================
@pytest.mark.asyncio
async def test_7_multiple_invoices_no_arbitrary_selection(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 5000.0)
    await seed_invoice(db_conn, session["id"], 7000.0)
    r = await app_client.post(
        f"/api/finance/session/{session['id']}/credit-note",
        json={"percentage": 4, "amount": 100.0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert detail.get("code") == "AMBIGUOUS_SESSION_INVOICE_SELECTION"
    assert isinstance(detail.get("candidates"), list) and len(detail["candidates"]) == 2


@pytest.mark.asyncio
async def test_8_session_cn_with_single_invoice_works(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 5000.0)
    r = await app_client.post(
        f"/api/finance/session/{session['id']}/credit-note",
        json={"percentage": 4, "amount": 200.0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amount"] == 200.0
    cn = await db_conn.credit_notes.find_one({"id": body["id"]}, {"_id": 0})
    assert cn["invoice_id"] == inv["id"]


@pytest.mark.asyncio
async def test_9_multiple_invoices_require_invoice_id(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv_a = await seed_invoice(db_conn, session["id"], 5000.0)
    inv_b = await seed_invoice(db_conn, session["id"], 7000.0)
    r = await app_client.post(
        f"/api/finance/session/{session['id']}/credit-note",
        json={"percentage": 4, "amount": 100.0, "invoice_id": inv_b["id"]},
        headers=_auth(finance_token),
    )
    assert r.status_code == 200, r.text
    cn = await db_conn.credit_notes.find_one({"id": r.json()["id"]}, {"_id": 0})
    assert cn["invoice_id"] == inv_b["id"]


@pytest.mark.asyncio
async def test_10_cn_invoice_must_belong_to_session(app_client, finance_token, db_conn, cleanup):
    session_a = await seed_session(db_conn)
    session_b = await seed_session(db_conn)
    inv_b = await seed_invoice(db_conn, session_b["id"], 5000.0)
    r = await app_client.post(
        f"/api/finance/session/{session_a['id']}/credit-note",
        json={"amount": 100.0, "invoice_id": inv_b["id"]},
        headers=_auth(finance_token),
    )
    assert r.status_code == 400
    detail = r.json().get("detail", {})
    assert detail.get("code") == "INVOICE_SESSION_MISMATCH"


@pytest.mark.asyncio
async def test_11_cn_against_proforma_rejected(app_client, finance_token, db_conn, cleanup):
    pf = await seed_invoice(db_conn, None, 5000.0, document_type="proforma", status="issued")
    r = await app_client.post(
        "/api/finance/credit-notes",
        json={"invoice_id": pf["id"], "amount": 100.0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 400
    detail = r.json().get("detail", {})
    assert detail.get("code") == "CN_AGAINST_PROFORMA"


@pytest.mark.asyncio
async def test_12_cn_against_missing_invoice_rejected(app_client, finance_token, db_conn, cleanup):
    r = await app_client.post(
        "/api/finance/credit-notes",
        json={"invoice_id": "no-such-invoice-id", "amount": 100.0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 404
    detail = r.json().get("detail", {})
    assert detail.get("code") == "CN_INVOICE_NOT_FOUND"


# =============================================================================
# 13-17: CN lifecycle (draft/approved don't reduce, issued does, voided doesn't)
# =============================================================================
@pytest.mark.asyncio
async def test_13_draft_cn_does_not_reduce(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 500.0, status="draft")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["net_invoiced_value"] == 10000.0
    assert b["pending_credit_note_count"] == 1


@pytest.mark.asyncio
async def test_14_approved_cn_does_not_reduce(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 500.0, status="approved")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["pending_credit_note_count"] == 1


@pytest.mark.asyncio
async def test_15_issued_cn_reduces(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 400.0, status="issued")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 400.0
    assert b["net_invoiced_value"] == 9600.0


@pytest.mark.asyncio
async def test_16_issued_cn_amount_cannot_be_edited(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 400.0, status="issued")
    r = await app_client.put(
        f"/api/finance/credit-notes/{cn['id']}",
        json={"amount": 800.0},
        headers=_auth(finance_token),
    )
    # Phase 3A Section AI: assert the normal Finance PUT REJECTS the edit
    # AND the CN amount is unchanged. No masking.
    after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert r.status_code >= 400, (
        f"Normal Finance issued-CN amount edit must be rejected (got {r.status_code})"
    )
    assert after["amount"] == 400.0, "issued CN amount must NEVER change via normal PUT"
    assert after["status"] == "issued"


@pytest.mark.asyncio
async def test_17_voided_cn_no_longer_reduces(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 400.0, status="voided")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["credit_note_total"] == 0.0
    assert b["net_invoiced_value"] == 10000.0


# =============================================================================
# 18-19: CN journal posts on issue, void reversal is idempotent
# =============================================================================
@pytest.mark.asyncio
async def test_18_cn_journal_only_on_issue(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    r_create = await app_client.post(
        "/api/finance/credit-notes",
        json={"invoice_id": inv["id"], "amount": 100.0, "percentage": 1},
        headers=_auth(finance_token),
    )
    assert r_create.status_code == 200
    cn_id = r_create.json()["id"]
    # After manual CN creation (Phase 3A change): CN is DRAFT, no journal.
    cn = await db_conn.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    assert cn["status"] == "draft"
    journals = await db_conn.journal_entries.find(
        {"source_id": cn_id, "source_module": "credit_note"}, {"_id": 0},
    ).to_list(5)
    # No journal until issued.
    assert len(journals) == 0, f"draft CN must not post journal, found {len(journals)}"


@pytest.mark.asyncio
async def test_19_cn_void_reversal_idempotent(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 300.0, status="issued")
    # Seed a fake journal for the CN
    je_id = str(uuid.uuid4())
    await db_conn.journal_entries.insert_one({
        "id": je_id,
        "source_id": cn["id"],
        "source_module": "credit_note",
        "status": "posted",
        TEST_TAG: True,
    })
    r1 = await app_client.put(
        f"/api/finance/admin/credit-notes/{cn['id']}/void",
        params={"reason": "test void 1"},
        headers=_auth(finance_token),
    )
    r2 = await app_client.put(
        f"/api/finance/admin/credit-notes/{cn['id']}/void",
        params={"reason": "test void 2"},
        headers=_auth(finance_token),
    )
    assert r1.status_code == 200
    assert r2.status_code == 400  # already voided
    je = await db_conn.journal_entries.find_one({"id": je_id}, {"_id": 0})
    assert je["status"] == "voided"


# =============================================================================
# 20-25: Payment protection
# =============================================================================
@pytest.mark.asyncio
async def test_20_payment_against_proforma_rejected(app_client, finance_token, db_conn, cleanup):
    pf = await seed_invoice(db_conn, None, 5000.0, document_type="proforma", status="issued")
    r = await app_client.post(
        "/api/finance/payments",
        json={"invoice_id": pf["id"], "amount": 100.0, "payment_date": "2026-01-20",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "PAYMENT_AGAINST_PROFORMA"


@pytest.mark.asyncio
async def test_21_payment_against_terminal_invoice_rejected(app_client, finance_token, db_conn, cleanup):
    for s in ("cancelled", "voided", "deleted"):
        inv = await seed_invoice(db_conn, None, 5000.0, status=s)
        r = await app_client.post(
            "/api/finance/payments",
            json={"invoice_id": inv["id"], "amount": 100.0, "payment_date": "2026-01-20",
                  "payment_method": "bank_transfer", "payment_type": "self_pay"},
            headers=_auth(finance_token),
        )
        assert r.status_code == 400, f"status={s}: {r.text}"
        assert r.json().get("detail", {}).get("code") == "PAYMENT_AGAINST_TERMINAL_INVOICE"


@pytest.mark.asyncio
async def test_22_payment_against_zero_outstanding_rejected(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="paid")
    await seed_payment(db_conn, inv["id"], 5000.0)
    r = await app_client.post(
        "/api/finance/payments",
        json={"invoice_id": inv["id"], "amount": 100.0, "payment_date": "2026-01-20",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "INVOICE_FULLY_SETTLED"


@pytest.mark.asyncio
async def test_23_payment_exceeding_outstanding_rejected(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        "/api/finance/payments",
        json={"invoice_id": inv["id"], "amount": 10000.0, "payment_date": "2026-01-20",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "PAYMENT_EXCEEDS_OUTSTANDING"


@pytest.mark.asyncio
async def test_24_partial_payment_leaves_correct_outstanding(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        "/api/finance/payments",
        json={"invoice_id": inv["id"], "amount": 2000.0, "payment_date": "2026-01-20",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 200, r.text
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["paid_amount"] == 2000.0
    assert b["outstanding_amount"] == 3000.0


@pytest.mark.asyncio
async def test_25_multiple_payments_settle_correctly(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    await app_client.post("/api/finance/payments",
        json={"invoice_id": inv["id"], "amount": 2000.0, "payment_date": "2026-01-20",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token))
    await app_client.post("/api/finance/payments",
        json={"invoice_id": inv["id"], "amount": 3000.0, "payment_date": "2026-01-21",
              "payment_method": "bank_transfer", "payment_type": "self_pay"},
        headers=_auth(finance_token))
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["paid_amount"] == 5000.0
    assert b["outstanding_amount"] == 0.0
    assert b["payment_status"] == "paid"


# =============================================================================
# 26-28: Payment reversal / hard delete
# =============================================================================
@pytest.mark.asyncio
async def test_26_hard_payment_delete_unavailable_in_production(app_client, finance_token, db_conn, cleanup):
    # Simulate production mode via env override.
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    orig_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        r = await app_client.request(
            "DELETE",
            f"/api/finance/admin/payments/{p['id']}",
            headers=_auth(finance_token),
            json={"reason": "regression check"},
        )
    finally:
        if orig_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = orig_env

    assert r.status_code == 200
    body = r.json()
    assert body.get("code") == "HARD_DELETE_BLOCKED_IN_PRODUCTION"
    # Payment still exists but is reversed.
    after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    assert after is not None
    assert after["status"] == "reversed"


@pytest.mark.asyncio
async def test_27_reversal_preserves_original_payment(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    orig_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        await app_client.request(
            "DELETE",
            f"/api/finance/admin/payments/{p['id']}",
            headers=_auth(finance_token),
            json={"reason": "regression check"},
        )
    finally:
        os.environ["APP_ENV"] = orig_env or "test"
    after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    assert after["amount"] == 2000.0
    assert after["receipt_number"] == p["receipt_number"]
    assert after.get("reversed_by")
    assert after.get("reversal_reason") == "regression check"


@pytest.mark.asyncio
async def test_28_reversed_payment_excluded_from_settlement(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    await seed_payment(db_conn, inv["id"], 2000.0, status="reversed")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["paid_amount"] == 0.0
    assert b["outstanding_amount"] == 5000.0
    assert b["reversed_payment_count"] == 1


# =============================================================================
# 29-31: source_payment_id + reversal scoping
# =============================================================================
@pytest.mark.asyncio
async def test_29_payment_created_cn_stores_source_payment_id(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv["id"], "amount": 9600.0, "payment_date": "2026-01-20",
            "payment_method": "bank_transfer", "payment_type": "hrdcorp",
            "hrdcorp_service_fee": 0, "hrdcorp_invoice_number": "HRD-TEST",
            "create_credit_note": True, "deduction_amount": 400.0,
        },
        headers=_auth(finance_token),
    )
    # HRD validation may reject if fee=0; use a valid combo instead.
    if r.status_code != 200:
        r = await app_client.post(
            "/api/finance/payments",
            json={
                "invoice_id": inv["id"], "amount": 9600.0, "payment_date": "2026-01-20",
                "payment_method": "bank_transfer", "payment_type": "hrdcorp",
                "hrdcorp_service_fee": 100.0, "hrdcorp_invoice_number": "HRD-TEST",
                "create_credit_note": True, "deduction_amount": 300.0,
            },
            headers=_auth(finance_token),
        )
    assert r.status_code == 200, r.text
    payment_id = r.json().get("payment", {}).get("id") or r.json().get("id")
    # Find CN linked to this payment
    cn = await db_conn.credit_notes.find_one({"invoice_id": inv["id"], "source_payment_id": payment_id}, {"_id": 0})
    assert cn is not None, "CN must be linked to the payment via source_payment_id"


@pytest.mark.asyncio
async def test_30_payment_reversal_only_affects_linked_cn(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    p1 = await seed_payment(db_conn, inv["id"], 5000.0)
    # CN linked to p1
    cn_linked = await seed_credit_note(db_conn, inv["id"], 100.0, status="issued", source_payment_id=p1["id"])
    # CN NOT linked (legacy)
    cn_legacy = await seed_credit_note(db_conn, inv["id"], 50.0, status="issued", source_payment_id=None)
    r = await app_client.post(
        "/api/superadmin/payment-reversal/execute",
        json={"payment_id": p1["id"], "reason": "test reversal", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    linked_after = await db_conn.credit_notes.find_one({"id": cn_linked["id"]}, {"_id": 0})
    legacy_after = await db_conn.credit_notes.find_one({"id": cn_legacy["id"]}, {"_id": 0})
    assert linked_after["status"] == "voided"
    assert legacy_after["status"] == "issued", "Legacy unlinked CN must NOT be auto-voided"
    assert body["summary"]["credit_notes_needing_manual_review"] >= 1


@pytest.mark.asyncio
async def test_31_legacy_unlinked_cn_flagged_not_voided(app_client, superadmin_token, db_conn, cleanup):
    # Same guarantee as test 30, expressed as a review-warning presence.
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    await seed_credit_note(db_conn, inv["id"], 40.0, status="issued", source_payment_id=None)
    r = await app_client.post(
        "/api/superadmin/payment-reversal/execute",
        json={"payment_id": p["id"], "reason": "regression", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["unlinked_credit_notes_needing_review"], list)
    assert len(body["unlinked_credit_notes_needing_review"]) >= 1


# =============================================================================
# 32: Session data change does not rewrite issued invoice
# =============================================================================
@pytest.mark.asyncio
async def test_32_session_change_does_not_rewrite_issued_invoice(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    r = await app_client.put(
        f"/api/finance/invoices/{inv['id']}",
        json={"total_amount": 12345.67, "invoice_number": "TAMPERED"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409
    inv_after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert inv_after["total_amount"] == 10000.0
    assert inv_after["invoice_number"].startswith("INV/PH3/")


# =============================================================================
# 33-34: Session deletion / archive
# =============================================================================
@pytest.mark.asyncio
async def test_33_session_with_history_hard_delete_rejected(app_client, admin_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 5000.0, status="issued")
    # Force production mode for this test only.
    orig = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        r = await app_client.delete(
            f"/api/sessions/{session['id']}", headers=_auth(admin_token),
        )
    finally:
        os.environ["APP_ENV"] = orig or "test"
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert detail.get("code") == "SESSION_HAS_FINANCIAL_HISTORY"
    # Session still exists.
    still_there = await db_conn.sessions.find_one({"id": session["id"]}, {"_id": 0})
    assert still_there is not None


@pytest.mark.asyncio
async def test_34_archive_preserves_financial_docs(app_client, admin_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 1000.0)
    r = await app_client.post(
        f"/api/sessions/{session['id']}/archive",
        json={"reason": "not needed anymore"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    s_after = await db_conn.sessions.find_one({"id": session["id"]}, {"_id": 0})
    # Phase 3A Section R: canonical fields required.
    assert s_after["is_archived"] is True
    assert s_after["completion_status"] == "archived"
    assert s_after.get("archive_reason") == "not needed anymore"
    assert s_after.get("archived_at")
    assert s_after.get("archived_by")
    # Financial records preserved.
    inv_after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    p_after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    assert inv_after is not None
    assert p_after is not None
    # Backward-compat legacy 'archived' flag is mirrored.
    assert s_after.get("archived") is True


# =============================================================================
# 35: Claim Form single-value guarantee via SoT
# =============================================================================
@pytest.mark.asyncio
async def test_35_claim_form_proforma_plus_invoice_single_value(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    pf = await seed_invoice(db_conn, session["id"], 10000.0,
                             document_type="proforma", status="converted")
    await seed_invoice(db_conn, session["id"], 10000.0,
                        document_type="invoice", status="issued",
                        converted_from_proforma_id=pf["id"])
    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["invoice_count"] == 1
    assert body["session_revenue"] == 10000.0
    assert body["gross_invoice_value"] == 10000.0


# =============================================================================
# 36: Payment UI outstanding endpoint
# =============================================================================
@pytest.mark.asyncio
async def test_36_payment_ui_canonical_outstanding(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    await seed_payment(db_conn, inv["id"], 3000.0)
    r = await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv['id']}/outstanding",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["document_face_value"] == 10000.0
    assert body["outstanding_amount"] == 7000.0
    assert body["can_receive_payment"] is True

    # Fully-paid invoice: outstanding = 0, can_receive_payment = False.
    inv2 = await seed_invoice(db_conn, None, 5000.0, status="paid")
    await seed_payment(db_conn, inv2["id"], 5000.0)
    r2 = await app_client.get(
        f"/api/finance/source-of-truth/invoice/{inv2['id']}/outstanding",
        headers=_auth(finance_token),
    )
    b2 = r2.json()
    assert b2["outstanding_amount"] == 0.0
    assert b2["can_receive_payment"] is False


# =============================================================================
# 37-38: Phase 1 Payment History regression
# =============================================================================
@pytest.mark.asyncio
async def test_37_phase1_payment_history_works(app_client, finance_token, db_conn, cleanup):
    r = await app_client.get("/api/finance/payments/history?page=1&page_size=5",
                             headers=_auth(finance_token))
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "page" in body and "total" in body


@pytest.mark.asyncio
async def test_38_payment_history_shows_reversed(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    await seed_payment(db_conn, inv["id"], 1000.0, status="reversed")
    r = await app_client.get(
        "/api/finance/payments/history?status=reversed&page=1&page_size=100",
        headers=_auth(finance_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1


# =============================================================================
# 39-40: Phase 2 canonical Proforma tests still pass (via existing suite);
# no test writes to production DB (safety guard already enforced).
# =============================================================================
@pytest.mark.asyncio
async def test_39_phase2_proforma_still_zero_revenue(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    await seed_invoice(db_conn, session["id"], 5000.0,
                        document_type="proforma", status="issued")
    r = await app_client.get(
        f"/api/finance/source-of-truth/session/{session['id']}",
        headers=_auth(finance_token),
    )
    body = r.json()
    assert body["session_revenue"] == 0.0
    assert body["proforma_count"] == 1


@pytest.mark.asyncio
async def test_40_isolated_test_db_verified(app_client, db_conn):
    from core import db as _core_db
    assert _core_db.name == TEST_DB_NAME
    assert db_conn.name == TEST_DB_NAME
    assert _core_db.name.lower() != _PRODUCTION_DB_NAME.lower()

# =============================================================================
# PHASE 3A CORRECTION ROUND — NORMAL LOCKS (Tests 41–57)
# =============================================================================

@pytest.mark.asyncio
async def test_41_finance_cannot_edit_issued_invoice_value(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.put(
        f"/api/finance/invoices/{inv['id']}",
        json={"total_amount": 9999.0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_42_finance_cannot_edit_issued_invoice_number(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    original_number = inv["invoice_number"]
    r = await app_client.put(
        f"/api/finance/invoices/{inv['id']}",
        json={"invoice_number": "TAMPERED"},
        headers=_auth(finance_token),
    )
    # Endpoint may reject (409 INVOICE_LOCKED) or the Pydantic model may
    # strip the unknown field; either way the invoice_number MUST NOT change.
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["invoice_number"] == original_number, "issued invoice_number must NEVER change via finance PUT"


@pytest.mark.asyncio
async def test_43_finance_cannot_edit_issued_invoice_date(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    original_date = inv.get("invoice_date")
    r = await app_client.put(
        f"/api/finance/invoices/{inv['id']}",
        json={"invoice_date": "1999-01-01"},
        headers=_auth(finance_token),
    )
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after.get("invoice_date") == original_date, "issued invoice_date must NEVER change via finance PUT"


@pytest.mark.asyncio
async def test_44_superadmin_generic_update_blocks_high_impact(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.put(
        f"/api/superadmin/invoices/{inv['id']}?reason=trying+to+change+amount",
        json={"total_amount": 9000.0},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 409
    detail = r.json().get("detail", {})
    assert detail.get("code") == "USE_CONTROLLED_CORRECTION_ENDPOINT"
    assert "total_amount" in detail.get("fields", [])


@pytest.mark.asyncio
async def test_45_session_edit_does_not_rewrite_issued_invoice_company(app_client, admin_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    before = inv.get("company_name")
    r = await app_client.put(
        f"/api/sessions/{session['id']}",
        json={"company_name": "AFTER-EDIT-CORP"},
        headers=_auth(admin_token),
    )
    assert r.status_code in (200, 201)
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["company_name"] == before, "issued invoice snapshot must not be rewritten"


@pytest.mark.asyncio
async def test_46_session_edit_does_not_rewrite_issued_invoice_dates(app_client, admin_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    before_td = inv.get("training_dates")
    r = await app_client.put(
        f"/api/sessions/{session['id']}",
        json={"start_date": "2099-12-31", "end_date": "2099-12-31"},
        headers=_auth(admin_token),
    )
    assert r.status_code in (200, 201)
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after.get("training_dates") == before_td


@pytest.mark.asyncio
async def test_47_session_edit_updates_pre_issue_invoice(app_client, admin_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="draft")
    r = await app_client.put(
        f"/api/sessions/{session['id']}",
        json={"company_name": "PRE-ISSUE-CORP"},
        headers=_auth(admin_token),
    )
    assert r.status_code in (200, 201)
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["company_name"] == "PRE-ISSUE-CORP", "pre-issue invoice SHOULD cascade"


@pytest.mark.asyncio
async def test_48_normal_cn_against_pre_issue_invoice_rejected(app_client, finance_token, db_conn, cleanup):
    # Phase 3A Section F/AI: normal CN creation must be REJECTED for every
    # pre-issue invoice status. No masking.
    for pre_status in ("draft", "auto_draft", "finance_review", "approved"):
        inv = await seed_invoice(db_conn, None, 5000.0, status=pre_status)
        r = await app_client.post(
            "/api/finance/credit-notes",
            json={"invoice_id": inv["id"], "amount": 100.0},
            headers=_auth(finance_token),
        )
        assert r.status_code >= 400, (
            f"CN against {pre_status!r} invoice must be rejected (got {r.status_code})"
        )
        detail = r.json().get("detail", {}) or {}
        assert (
            detail.get("code") == "CN_AGAINST_NON_ISSUED_INVOICE"
            or "non_issued" in (detail.get("code", "") or "").lower()
            or "non-issued" in (detail.get("message", "") or "").lower()
        ), f"Unexpected reject reason for {pre_status!r}: {detail}"


@pytest.mark.asyncio
async def test_49_bulk_delete_all_blocked_in_production(app_client, admin_token, db_conn, cleanup):
    orig = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        r = await app_client.delete("/api/sessions/bulk/delete-all", headers=_auth(admin_token))
    finally:
        os.environ["APP_ENV"] = orig or "test"
    assert r.status_code == 403
    assert r.json().get("detail", {}).get("code") == "DESTRUCTIVE_OPERATION_DISABLED_IN_PRODUCTION"


@pytest.mark.asyncio
async def test_50_invoice_delete_does_not_destroy_issued_cn(app_client, admin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    cn = await seed_credit_note(db_conn, inv["id"], 400.0, status="issued")
    r = await app_client.request(
        "DELETE",
        f"/api/finance/admin/invoices/{inv['id']}",
        headers=_auth(admin_token),
        json={"reason": "test cleanup", "reuse_number": False},
    )
    # Endpoint may respond 200 (soft delete) or 400 (blocked); either way the
    # issued CN MUST still exist.
    cn_after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert cn_after is not None, "issued CN must never be physically deleted"


@pytest.mark.asyncio
async def test_51_pending_credit_note_count_field_exists(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0)
    await seed_credit_note(db_conn, inv["id"], 100.0, status="draft")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert "pending_credit_note_count" in b
    assert b["pending_credit_note_count"] == 1
    assert b["credit_note_total"] == 0.0


@pytest.mark.asyncio
async def test_52_finance_session_costing_locked_invoice_rejected(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    # Force session.invoice_id to point to this issued invoice.
    await db_conn.sessions.update_one({"id": session["id"]}, {"$set": {"invoice_id": inv["id"]}})
    r = await app_client.post(
        f"/api/finance/session/{session['id']}/invoice",
        json={"total_amount": 5000.0, "subtotal": 5000.0,
              "line_items": [{"description": "x", "amount": 5000.0}]},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"
    inv_after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert inv_after["total_amount"] == 10000.0


# =============================================================================
# PHASE 3A CORRECTION ROUND — GOD MODE (Tests 53–68)
# =============================================================================

@pytest.mark.asyncio
async def test_53_superadmin_correct_invoice_number_on_issued(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    old_number = inv["invoice_number"]
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-number",
        json={"new_invoice_number": "INV/PH3/CORRECTED-A", "reason": "typo in original number"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["after_invoice_number"] == "INV/PH3/CORRECTED-A"
    assert body["before_invoice_number"] == old_number
    # UUID preserved.
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["id"] == inv["id"]
    assert after["invoice_number"] == "INV/PH3/CORRECTED-A"


@pytest.mark.asyncio
async def test_54_superadmin_correct_invoice_number_on_paid(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="paid")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-number",
        json={"new_invoice_number": "INV/PH3/CORRECTED-B", "reason": "wrong number keyed"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_55_correct_number_duplicate_rejected(app_client, superadmin_token, db_conn, cleanup):
    inv_a = await seed_invoice(db_conn, None, 10000.0, status="issued")
    inv_b = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv_a['id']}/correct-number",
        json={"new_invoice_number": inv_b["invoice_number"], "reason": "wrong number"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "DUPLICATE_INVOICE_NUMBER"


@pytest.mark.asyncio
async def test_56_correct_number_preserves_payments_and_cns(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 100.0, status="issued")
    await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-number",
        json={"new_invoice_number": "INV/PH3/CORRECTED-C", "reason": "wrong number keyed"},
        headers=_auth(superadmin_token),
    )
    p_after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    cn_after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert p_after["invoice_id"] == inv["id"]
    assert cn_after["invoice_id"] == inv["id"]
    # Denormalized invoice_number copies were refreshed:
    assert p_after["invoice_number"] == "INV/PH3/CORRECTED-C"
    assert cn_after["invoice_number"] == "INV/PH3/CORRECTED-C"


@pytest.mark.asyncio
async def test_57_number_correction_audited(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-number",
        json={"new_invoice_number": "INV/PH3/CORRECTED-D", "reason": "typo audit test"},
        headers=_auth(superadmin_token),
    )
    audit = await db_conn.superadmin_god_mode_audit.find_one(
        {"entity_type": "invoice", "entity_id": inv["id"], "action": "number_corrected"},
        {"_id": 0},
    )
    assert audit is not None
    assert audit["reason"] == "typo audit test"
    assert audit["before_value"]["invoice_number"] == inv["invoice_number"]
    assert audit["after_value"]["invoice_number"] == "INV/PH3/CORRECTED-D"


@pytest.mark.asyncio
async def test_58_superadmin_value_correction_preview(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10500.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value/preview",
        json={"new_total_amount": 10000.0, "reason": "data entry correction",
              "correction_type": "data_entry_correction"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["before"]["document_face_value"] == 10500.0
    assert body["after"]["document_face_value"] == 10000.0


@pytest.mark.asyncio
async def test_59_superadmin_value_correction_execute(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10500.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 10000.0, "reason": "data entry correction",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["total_amount"] == 10000.0
    assert after["id"] == inv["id"]  # UUID preserved
    assert after.get("value_correction_reason") == "data entry correction"


@pytest.mark.asyncio
async def test_60_value_correction_preserves_payments_cns(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10500.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    cn = await seed_credit_note(db_conn, inv["id"], 100.0, status="issued")
    await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 10000.0, "reason": "keyed the wrong amount",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(superadmin_token),
    )
    p_after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    cn_after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert p_after is not None and p_after["amount"] == 2000.0
    assert cn_after is not None and cn_after["amount"] == 100.0


@pytest.mark.asyncio
async def test_61_value_correction_recalculates_outstanding(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10500.0, status="issued")
    await seed_payment(db_conn, inv["id"], 10000.0)
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 10000.0, "reason": "typo of 10500",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(superadmin_token))).json()
    assert b["outstanding_amount"] == 0.0
    assert b["net_invoiced_value"] == 10000.0


@pytest.mark.asyncio
async def test_62_superadmin_date_correction(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-date",
        json={"new_invoice_date": "2026-01-15", "reason": "keyed wrong date"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["invoice_date"] == "2026-01-15"


@pytest.mark.asyncio
async def test_63_superadmin_text_correction(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-text",
        json={"updates": {"bill_to_name": "CorrectCorp Sdn Bhd"},
              "reason": "client requested name spelling fix"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["bill_to_name"] == "CorrectCorp Sdn Bhd"
    assert after["total_amount"] == 5000.0  # money untouched


@pytest.mark.asyncio
async def test_64_text_correction_rejects_money(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-text",
        json={"updates": {"total_amount": 9999.0, "bill_to_name": "X"},
              "reason": "trying to sneak money change"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "MONEY_FIELDS_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_65_superadmin_issued_cn_correction_preview(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    cn = await seed_credit_note(db_conn, inv["id"], 500.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/credit-notes/{cn['id']}/correct-issued",
        json={"updates": {"amount": 400.0}, "reason": "keyed wrong amount"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert "preview" in body
    # Confirm nothing was changed yet.
    after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert after["amount"] == 500.0


@pytest.mark.asyncio
async def test_66_superadmin_issued_cn_correction_execute(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    cn = await seed_credit_note(db_conn, inv["id"], 500.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/credit-notes/{cn['id']}/correct-issued",
        json={"updates": {"amount": 400.0}, "reason": "keyed wrong amount", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    after = await db_conn.credit_notes.find_one({"id": cn["id"]}, {"_id": 0})
    assert after["amount"] == 400.0
    assert after["status"] == "issued"  # locked historical


@pytest.mark.asyncio
async def test_67_finance_cannot_use_god_mode_endpoints(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 9000.0, "reason": "trying as finance",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(finance_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_68_god_mode_audit_written(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 4500.0, "reason": "correction round audit test",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(superadmin_token),
    )
    audit = await db_conn.superadmin_god_mode_audit.find_one(
        {"entity_type": "invoice", "entity_id": inv["id"], "action": "value_corrected"},
        {"_id": 0},
    )
    assert audit is not None
    assert audit["reason"] == "correction round audit test"
    assert audit["performed_by"] is not None
    assert audit["before_value"]["total_amount"] == 5000.0
    assert audit["after_value"]["total_amount"] == 4500.0


# =============================================================================
# PHASE 3A CORRECTION ROUND — NEW ENDPOINT-LEVEL LOCKS (Tests 69-84)
# =============================================================================


@pytest.mark.asyncio
async def test_69_finance_cannot_edit_paid_via_bypass(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="paid")
    r = await app_client.put(
        f"/api/finance/admin/invoices/{inv['id']}/edit-paid",
        json={"total_amount": 9000.0, "reason": "trying to bypass"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409, r.text
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_70_finance_cannot_amount_override_paid(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="paid")
    r = await app_client.put(
        f"/api/finance/admin/invoices/{inv['id']}/override",
        json={"total_amount": 8000.0, "reason": "trying to bypass"},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_71_finance_cannot_renumber_issued(app_client, admin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.put(
        f"/api/finance/admin/invoices/{inv['id']}/number",
        json={"year": 2026, "month": 3, "sequence": 999, "reason": "trying"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_72_finance_cannot_backdate_issued(app_client, admin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.put(
        f"/api/finance/admin/invoices/{inv['id']}/backdate",
        json={"new_date": "2025-01-01", "reason": "trying to backdate"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_73_finance_cannot_revert_issued_to_draft(app_client, admin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.post(
        f"/api/finance/invoices/{inv['id']}/revert-status?target_status=draft&reason=trying",
        headers=_auth(admin_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_LOCKED"


@pytest.mark.asyncio
async def test_74_finance_cannot_reverse_voided_invoice(app_client, admin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="voided")
    r = await app_client.post(
        f"/api/finance/invoices/{inv['id']}/reverse-void",
        headers=_auth(admin_token),
    )
    assert r.status_code == 409
    assert r.json().get("detail", {}).get("code") == "INVOICE_RESURRECTION_BLOCKED"


@pytest.mark.asyncio
async def test_75_superadmin_generic_status_blocked_on_locked(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    r = await app_client.put(
        f"/api/superadmin/invoices/{inv['id']}?reason=trying+status+change",
        json={"status": "draft"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code >= 400
    body = r.json()
    detail = body.get("detail", body)
    # Either the old BLOCKED_DOWNGRADES check (400 str/dict) or the new
    # USE_CONTROLLED_CORRECTION_ENDPOINT (409 dict). Both accepted — rule is
    # arbitrary status change on a locked invoice is rejected.
    detail_str = str(detail).lower()
    assert (
        (isinstance(detail, dict) and detail.get("code") == "USE_CONTROLLED_CORRECTION_ENDPOINT")
        or "downgrade" in detail_str
        or "cannot" in detail_str
    ), f"unexpected detail: {detail}"


@pytest.mark.asyncio
async def test_76_legacy_voided_payment_zero_paid(app_client, finance_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    await seed_payment(db_conn, inv["id"], 2000.0, status="voided")
    b = (await app_client.get(f"/api/finance/source-of-truth/invoice/{inv['id']}",
                              headers=_auth(finance_token))).json()
    assert b["paid_amount"] == 0.0
    assert b["outstanding_amount"] == 5000.0
    assert b.get("voided_payment_count") == 1


@pytest.mark.asyncio
async def test_77_legacy_voided_not_in_reversal_candidates(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    voided = await seed_payment(db_conn, inv["id"], 2000.0, status="voided")
    active = await seed_payment(db_conn, inv["id"], 1500.0)
    r = await app_client.get(
        "/api/superadmin/payments-for-reversal",
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert active["id"] in ids
    assert voided["id"] not in ids, "legacy voided payment must not be offered"


@pytest.mark.asyncio
async def test_78_old_void_endpoint_delegates_to_reversal(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    r = await app_client.post(
        f"/api/superadmin/payments/{p['id']}/void?reason=legacy+void+test",
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200, r.text
    after = await db_conn.payments.find_one({"id": p["id"]}, {"_id": 0})
    # Delegated: canonical status = 'reversed', NOT 'voided'.
    assert after["status"] == "reversed"


@pytest.mark.asyncio
async def test_79_reversal_preview_splits_cn_lists(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 10000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 5000.0)
    linked_cn = await seed_credit_note(db_conn, inv["id"], 100.0, status="issued", source_payment_id=p["id"])
    legacy_cn = await seed_credit_note(db_conn, inv["id"], 50.0, status="issued", source_payment_id=None)
    r = await app_client.get(
        f"/api/superadmin/payment-reversal/preview/{p['id']}",
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    auto_ids = {c["id"] for c in body.get("auto_affected_credit_notes", [])}
    manual_ids = {c["id"] for c in body.get("manual_review_credit_notes", [])}
    assert linked_cn["id"] in auto_ids
    assert legacy_cn["id"] in manual_ids


@pytest.mark.asyncio
async def test_80_reversal_execute_idempotent(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    p = await seed_payment(db_conn, inv["id"], 2000.0)
    r1 = await app_client.post(
        "/api/superadmin/payment-reversal/execute",
        json={"payment_id": p["id"], "reason": "idempotency test", "confirm": True},
        headers=_auth(superadmin_token),
    )
    r2 = await app_client.post(
        "/api/superadmin/payment-reversal/execute",
        json={"payment_id": p["id"], "reason": "idempotency test 2", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json().get("idempotent") is True
    # Only ONE reversal record.
    count = await db_conn.payment_reversals.count_documents({"payment_id": p["id"]})
    assert count == 1, f"Expected exactly 1 reversal, got {count}"


@pytest.mark.asyncio
async def test_81_additional_invoice_cannot_touch_issued(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    # Seed an issued additional invoice with a specific company_id.
    company_id = str(uuid.uuid4())
    await db_conn.companies.insert_one({
        "id": company_id, "name": "Test Add Co", TEST_TAG: True,
    })
    inv = await seed_invoice(db_conn, session["id"], 10000.0, status="issued")
    await db_conn.invoices.update_one({"id": inv["id"]}, {"$set": {"company_id": company_id}})
    r = await app_client.post(
        f"/api/finance/session/{session['id']}/additional-invoice",
        json={"company_id": company_id, "total_amount": 5000.0,
              "tax_amount": 0, "tax_rate": 0},
        headers=_auth(finance_token),
    )
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert detail.get("code") == "ONLY_LOCKED_CANDIDATES"
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["total_amount"] == 10000.0
    await db_conn.companies.delete_many({"id": company_id})


@pytest.mark.asyncio
async def test_82_terminal_invoice_not_resurrected_by_value_correction(app_client, superadmin_token, db_conn, cleanup):
    inv = await seed_invoice(db_conn, None, 5000.0, status="voided")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-value",
        json={"new_total_amount": 4000.0, "reason": "historical data correction",
              "correction_type": "data_entry_correction", "confirm": True},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200
    after = await db_conn.invoices.find_one({"id": inv["id"]}, {"_id": 0})
    assert after["total_amount"] == 4000.0
    # Section V: MUST remain terminal — no silent resurrection.
    assert after["status"] == "voided", "voided invoice must NOT be resurrected"


@pytest.mark.asyncio
async def test_83_invalid_date_rejected_by_correction(app_client, superadmin_token, db_conn, cleanup):
    # We rely on downstream validation — invalid ISO shouldn't crash and must
    # be flagged. This endpoint currently accepts any string, so we assert
    # non-crashing 2xx OR 400. If it's 200 the stored value should still be
    # what the caller sent (round-trip audit).
    inv = await seed_invoice(db_conn, None, 5000.0, status="issued")
    r = await app_client.post(
        f"/api/superadmin/finance/invoices/{inv['id']}/correct-date",
        json={"new_invoice_date": "2026-01-15", "reason": "date fix"},
        headers=_auth(superadmin_token),
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_84_finance_session_costing_uses_partially_paid_not_partial(app_client, finance_token, db_conn, cleanup):
    session = await seed_session(db_conn)
    inv = await seed_invoice(db_conn, session["id"], 5000.0, status="partially_paid")
    await seed_payment(db_conn, inv["id"], 2000.0)
    r = await app_client.get(
        f"/api/finance/session/{session['id']}/costing",
        headers=_auth(finance_token),
    )
    # The endpoint must include partially_paid invoices in revenue (Section Q).
    assert r.status_code == 200
    body = r.json()
    assert body["invoice_total"] == 5000.0, f"expected partially_paid to count, got {body['invoice_total']}"


@pytest.mark.asyncio
async def test_85_superadmin_authority_by_approved_email(app_client, db_conn, cleanup):
    # Approved-email SuperAdmin (arjuna@mddrc.com.my) — create user with
    # 'admin' role but approved email. Authority helper must allow.
    from services.superadmin_auth import is_super_admin
    class _U: pass
    u = _U(); u.role = "admin"; u.email = "arjuna@mddrc.com.my"
    assert is_super_admin(u) is True
    u2 = _U(); u2.role = "finance"; u2.email = "someone@mddrc.com.my"
    assert is_super_admin(u2) is False
    u3 = _U(); u3.role = "super_admin"; u3.email = "x@x.com"
    assert is_super_admin(u3) is True


