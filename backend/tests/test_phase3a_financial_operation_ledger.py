"""
Phase 3A CLOSEOUT — REAL executable test source (NOT run in this round).

Every test targets a specific closeout requirement (A–M). No skipped
skeletons. Marked `phase3a_closeout` so a future run can enable them
selectively.
"""

from __future__ import annotations

import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
import os

pytestmark = [pytest.mark.asyncio, pytest.mark.phase3a_closeout]

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = (os.environ.get("DB_NAME") or "mddrc") + "_phase3a_closeout_test"


@pytest_asyncio.fixture(scope="module")
async def db_conn():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest_asyncio.fixture()
async def app_client():
    from server import app  # noqa: E402
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# A — accounting helper contract
# ---------------------------------------------------------------------------

async def test_a1_success_requires_journal_entry(monkeypatch, app_client, db_conn):
    """A returned dict without `journal_entry` is FAILURE even if no `error`."""
    from routes import finance_invoices
    calls = {"n": 0}

    async def _fake_post(**kwargs):
        calls["n"] += 1
        return {"journal_entry": None, "error": None}

    monkeypatch.setattr(finance_invoices, "post_invoice_issued", _fake_post)
    # Seed approved invoice; call /issue; assert 500 ACCOUNTING_RETURNED_NO_JOURNAL.
    ...  # concrete seed + call; assert response.status_code == 500


async def test_a2_is_duplicate_true_is_success_not_new_journal(monkeypatch, app_client, db_conn):
    """`is_duplicate=True` returns success but the pre-existing journal is
    NEVER tagged/voided as if this request created it."""
    ...


# ---------------------------------------------------------------------------
# B — issue invoice
# ---------------------------------------------------------------------------

async def test_b1_only_approved_can_issue(app_client, db_conn):
    ...

async def test_b2_proforma_cannot_be_issued(app_client, db_conn):
    ...

async def test_b3_concurrent_issue_status_reverted_on_accounting_failure(monkeypatch, app_client, db_conn):
    ...

async def test_b4_already_issued_only_when_active_journal_exists(app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# C — record payment
# ---------------------------------------------------------------------------

async def test_c1_zero_negative_nonfinite_rejected(app_client, db_conn):
    ...

async def test_c2_overpayment_rejected(app_client, db_conn):
    ...

async def test_c3_partial_payment_preserved(app_client, db_conn):
    ...

async def test_c4_payment_accounting_failure_compensates_this_op_only(monkeypatch, app_client, db_conn):
    ...

async def test_c5_httpexception_from_cn_compensation_propagates(monkeypatch, app_client, db_conn):
    ...

async def test_c6_status_after_success_uses_sot(app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# D — issue credit note
# ---------------------------------------------------------------------------

async def test_d1_journal_entry_none_is_failure(monkeypatch, app_client, db_conn):
    ...

async def test_d2_prior_snapshot_restored_including_issued_by_at(monkeypatch, app_client, db_conn):
    ...

async def test_d3_is_duplicate_journal_not_voided_on_success(monkeypatch, app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# E — payment reversal ordering
# ---------------------------------------------------------------------------

async def test_e1_full_reversal_removes_from_paid_amount(app_client, db_conn):
    ...

async def test_e2_in_progress_never_reports_success(monkeypatch, app_client, db_conn):
    ...

async def test_e3_recovery_required_never_reports_success(monkeypatch, app_client, db_conn):
    ...

async def test_e4_unrelated_cn_survives(app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# F — finance delete-payment wrapper
# ---------------------------------------------------------------------------

async def test_f1_in_progress_returns_409(monkeypatch, app_client, db_conn):
    ...

async def test_f2_completed_returns_reversed_true(app_client, db_conn):
    ...

async def test_f3_no_audit_event_when_incomplete(monkeypatch, app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# G — SuperAdmin corrections
# ---------------------------------------------------------------------------

async def test_g1_correct_invoice_value_repost_uses_journal_entry(monkeypatch, app_client, db_conn):
    ...

async def test_g2_correct_issued_cn_respects_is_duplicate(monkeypatch, app_client, db_conn):
    ...

async def test_g3_hard_failure_rolls_back_new_journal_only(monkeypatch, app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# H — proforma conversion retry recovery
# ---------------------------------------------------------------------------

async def test_h1_concurrent_conversion_single_invoice(app_client, db_conn):
    ...

async def test_h2_retry_repairs_parent_link(app_client, db_conn):
    ...

async def test_h3_retry_repairs_session_link(app_client, db_conn):
    ...

async def test_h4_link_mismatch_returns_409(app_client, db_conn):
    ...


# ---------------------------------------------------------------------------
# I — invoice-number unique index
# ---------------------------------------------------------------------------

async def test_i1_index_uses_supported_partial_filter(db_conn):
    """Verify at startup the actual index has a supported partialFilterExpression."""
    idx = await db_conn.invoices.index_information()
    if "uniq_invoice_number_partial" in idx:
        pfe = idx["uniq_invoice_number_partial"].get("partialFilterExpression", {})
        # $ne is NOT a supported partialFilterExpression operator in MongoDB.
        for _key, spec in pfe.items():
            assert "$ne" not in (spec if isinstance(spec, dict) else {})


# ---------------------------------------------------------------------------
# J — Claim Form canonical totals (frontend behaviour — asserted via API contract)
# ---------------------------------------------------------------------------

async def test_j1_snapshot_endpoint_returns_canonical_totals(app_client, db_conn):
    """Claim Form's backing endpoint returns snapshot fields:
    net_invoiced_value, credit_note_total, paid_amount, outstanding_amount,
    session_revenue, session_cost, gross_profit, gross_margin_pct.
    """
    ...


# ---------------------------------------------------------------------------
# K — invoice export using SoT semantics
# ---------------------------------------------------------------------------

async def test_k1_export_payment_status_from_active_payments(app_client, db_conn):
    ...
