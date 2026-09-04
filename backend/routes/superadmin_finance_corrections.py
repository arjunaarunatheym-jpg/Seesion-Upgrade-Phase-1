"""SuperAdmin financial-correction endpoints (Phase 3A — controlled God Mode).

All endpoints here REQUIRE the ``super_admin`` role. They provide the ONLY
paths through which locked/terminal invoices and issued Credit Notes may be
materially corrected. Every operation is audited and preserves internal
UUIDs, payments, credit notes, and journal links.

Endpoints:
    POST /api/superadmin/finance/invoices/{invoice_id}/correct-number
    POST /api/superadmin/finance/invoices/{invoice_id}/correct-value/preview
    POST /api/superadmin/finance/invoices/{invoice_id}/correct-value
    POST /api/superadmin/finance/invoices/{invoice_id}/correct-date
    POST /api/superadmin/finance/invoices/{invoice_id}/correct-text
    POST /api/superadmin/finance/credit-notes/{cn_id}/correct-issued
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user, User
from services.financial_write_guard import FinancialSafetyError
from services.superadmin_auth import require_super_admin
from services.superadmin_financial_correction import (
    SuperAdminFinancialCorrection,
    CORRECTION_TYPES,
)

router = APIRouter(prefix="/superadmin/finance", tags=["superadmin-finance-correction"])


def _require_superadmin(user: User) -> None:
    """Phase 3A Section A: delegate to the single canonical helper so
    role == 'super_admin' AND approved-email overrides stay in sync with
    the legacy SuperAdmin portal."""
    require_super_admin(user)


def _svc() -> SuperAdminFinancialCorrection:
    return SuperAdminFinancialCorrection(db)


def _to_http(e: FinancialSafetyError) -> HTTPException:
    return HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})


# -----------------------------------------------------------------------------
# Payloads
# -----------------------------------------------------------------------------
class NumberCorrection(BaseModel):
    new_invoice_number: str
    reason: str


class ValueCorrection(BaseModel):
    new_total_amount: float
    reason: str
    correction_type: str = Field(..., description=f"One of: {list(CORRECTION_TYPES)}")
    confirm: bool = False


class DateCorrection(BaseModel):
    new_invoice_date: str
    reason: str


class TextCorrection(BaseModel):
    updates: Dict[str, Any]
    reason: str


class CnIssuedCorrection(BaseModel):
    updates: Dict[str, Any]
    reason: str
    confirm: bool = False


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post("/invoices/{invoice_id}/correct-number")
async def correct_invoice_number(
    invoice_id: str, body: NumberCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().correct_invoice_number(
            invoice_id, body.new_invoice_number, body.reason, current_user,
        )
    except FinancialSafetyError as e:
        raise _to_http(e)


@router.post("/invoices/{invoice_id}/correct-value/preview")
async def preview_value_correction(
    invoice_id: str, body: ValueCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().preview_value_correction(invoice_id, body.new_total_amount)
    except FinancialSafetyError as e:
        raise _to_http(e)


@router.post("/invoices/{invoice_id}/correct-value")
async def correct_invoice_value(
    invoice_id: str, body: ValueCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().correct_invoice_value(
            invoice_id, body.new_total_amount, body.reason,
            body.correction_type, current_user, body.confirm,
        )
    except FinancialSafetyError as e:
        raise _to_http(e)


@router.post("/invoices/{invoice_id}/correct-date")
async def correct_invoice_date(
    invoice_id: str, body: DateCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().correct_invoice_date(
            invoice_id, body.new_invoice_date, body.reason, current_user,
        )
    except FinancialSafetyError as e:
        raise _to_http(e)


@router.post("/invoices/{invoice_id}/correct-text")
async def correct_invoice_text(
    invoice_id: str, body: TextCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().correct_invoice_text(
            invoice_id, body.updates, body.reason, current_user,
        )
    except FinancialSafetyError as e:
        raise _to_http(e)


@router.post("/credit-notes/{cn_id}/correct-issued")
async def correct_issued_credit_note(
    cn_id: str, body: CnIssuedCorrection,
    current_user: User = Depends(get_current_user),
):
    _require_superadmin(current_user)
    try:
        return await _svc().correct_issued_credit_note(
            cn_id, body.updates, body.reason, current_user, body.confirm,
        )
    except FinancialSafetyError as e:
        raise _to_http(e)
