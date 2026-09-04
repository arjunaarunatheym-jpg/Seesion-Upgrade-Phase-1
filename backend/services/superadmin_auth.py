"""Canonical SuperAdmin authority helper (Phase 3A Section A).

Single source of truth for "is this user allowed to perform SuperAdmin /
God Mode actions?". Both the legacy ``superadmin_portal.py`` endpoints and
the new ``superadmin_finance_corrections.py`` correction endpoints delegate
here so authority rules can never diverge.

Rules:
    - Users with role == 'super_admin' are allowed.
    - Users whose email is listed in ``APPROVED_GOD_MODE_EMAILS`` are allowed
      (preserves the existing approved-owner override).
    - Everyone else is denied — including admin, finance, coordinator, etc.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


APPROVED_GOD_MODE_EMAILS = frozenset({
    "arjuna@mddrc.com.my",
})


def is_super_admin(user: Any) -> bool:
    """True iff the user has SuperAdmin authority."""
    if user is None:
        return False
    if getattr(user, "role", None) == "super_admin":
        return True
    email = (getattr(user, "email", None) or "").lower().strip()
    return email in {e.lower() for e in APPROVED_GOD_MODE_EMAILS}


def require_super_admin(user: Any) -> None:
    """Raise HTTP 403 unless the user is a SuperAdmin."""
    if not is_super_admin(user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
