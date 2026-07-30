#!/usr/bin/env python3
"""Focused verification for invoice soft-delete behavior.

Creates an identifiable ad-hoc test invoice through the API, deletes it through
the invoice DELETE endpoint, then verifies persistence in MongoDB and API list
filter behavior.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from pymongo import MongoClient


BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:8001/api")
EMAIL = os.environ.get("TEST_EMAIL", "arjuna@mddrc.com.my")
PASSWORD = os.environ.get("TEST_PASSWORD", "Dana102229")


def parse_env(path: str) -> dict:
    data = {}
    for raw in Path(path).read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key] = value.strip().strip('"').strip("'")
    return data


def require(condition: bool, message: str, details=None):
    if not condition:
        raise AssertionError(f"{message}: {details!r}")


def main():
    env = parse_env("/app/backend/.env")
    mongo_url = env.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = env.get("DB_NAME", "driving_training_db")
    client = MongoClient(mongo_url)
    db = client[db_name]

    sess = requests.Session()
    results = {
        "base_url": BASE_URL,
        "created_invoice_id": None,
        "created_invoice_number": None,
        "login_user_role": None,
        "checks": [],
    }

    def ok(name, extra=None):
        row = {"name": name, "ok": True}
        if extra is not None:
            row["extra"] = extra
        results["checks"].append(row)
        print(f"PASS: {name}" + (f" | {extra}" if extra is not None else ""))

    # Login
    login_resp = sess.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=20,
    )
    require(login_resp.status_code == 200, "login failed", login_resp.text)
    token = login_resp.json()["access_token"]
    user = login_resp.json().get("user", {})
    results["login_user_role"] = user.get("role")
    sess.headers.update({"Authorization": f"Bearer {token}"})
    ok("logged in", {"email": user.get("email"), "role": user.get("role")})

    # Create safe test invoice through API (actual app create endpoint is /finance/invoices/adhoc)
    stamp = int(time.time())
    payload = {
        "bill_to_name": f"QA Soft Delete Test {stamp}",
        "bill_to_address": "QA temporary test invoice - safe to keep as deleted",
        "bill_to_reg_no": "QA-TEST",
        "contact_person": "QA Automation",
        "contact_email": "qa-soft-delete@example.invalid",
        "contact_phone": "000",
        "your_reference": f"soft-delete-{stamp}",
        "line_items": [
            {"description": "Soft delete verification line", "quantity": 1, "unit_price": 1.23, "amount": 1.23}
        ],
        "sst_percent": 0,
        "discount": 0,
        "rounding": 0,
        "notes": "Created by focused invoice soft-delete verification script",
        "invoice_date": "2026-07-30",
        "due_date": "2026-08-14",
        "reference_text": "QA soft-delete verification",
    }
    create_resp = sess.post(f"{BASE_URL}/finance/invoices/adhoc", json=payload, timeout=20)
    require(create_resp.status_code == 200, "ad-hoc invoice create failed", create_resp.text)
    created = create_resp.json()
    invoice_id = created.get("id")
    invoice_number = created.get("invoice_number")
    results["created_invoice_id"] = invoice_id
    results["created_invoice_number"] = invoice_number
    require(invoice_id and invoice_number, "created invoice missing id/number", created)
    ok("created identifiable draft test invoice via API", {"id": invoice_id, "invoice_number": invoice_number})

    db_before = db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    require(db_before is not None, "created invoice not found in DB", invoice_id)
    require(db_before.get("status") == "draft", "DB created invoice status unexpected", db_before.get("status"))
    ok("created invoice exists in DB before delete", {"status": db_before.get("status")})

    # Delete through the fixed endpoint with reuse_number=false so no reuse pool side effects are expected.
    delete_reason = f"QA soft-delete verification {stamp}"
    del_resp = sess.delete(
        f"{BASE_URL}/finance/invoices/{invoice_id}",
        json={"reason": delete_reason, "reuse_number": False},
        timeout=20,
    )
    require(del_resp.status_code == 200, "delete endpoint did not return 200", del_resp.text)
    ok("DELETE /finance/invoices/{id} returned 200", del_resp.json())

    # Direct DB verification: invoice must still exist, with deletion audit fields.
    db_after = db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    require(db_after is not None, "invoice was hard-deleted from DB", invoice_id)
    require(db_after.get("status") == "deleted", "invoice status not soft-deleted", db_after.get("status"))
    required_fields = ["deleted_at", "deleted_by", "deletion_reason", "previous_status"]
    missing = [field for field in required_fields if not db_after.get(field)]
    require(not missing, "soft-delete metadata fields missing", missing)
    require(db_after.get("previous_status") == "draft", "previous_status not preserved", db_after.get("previous_status"))
    require(db_after.get("deletion_reason") == delete_reason, "deletion_reason not preserved", db_after.get("deletion_reason"))
    ok(
        "DB retained invoice with status=deleted and metadata",
        {field: db_after.get(field) for field in required_fields},
    )

    # API default list must not return the deleted invoice.
    default_resp = sess.get(f"{BASE_URL}/finance/invoices", timeout=20)
    require(default_resp.status_code == 200, "default invoice list failed", default_resp.text)
    default_ids = {inv.get("id") for inv in default_resp.json()}
    require(invoice_id not in default_ids, "deleted invoice returned in default invoice list", invoice_id)
    require(all(inv.get("status") != "deleted" for inv in default_resp.json()), "default list contains deleted rows")
    ok("GET /finance/invoices hides status=deleted by default", {"default_count": len(default_ids)})

    # Explicit deleted filter must return it.
    deleted_resp = sess.get(f"{BASE_URL}/finance/invoices", params={"status": "deleted"}, timeout=20)
    require(deleted_resp.status_code == 200, "deleted status list failed", deleted_resp.text)
    deleted_rows = deleted_resp.json()
    match = next((inv for inv in deleted_rows if inv.get("id") == invoice_id), None)
    require(match is not None, "deleted invoice not returned by status=deleted", invoice_id)
    require(match.get("status") == "deleted", "status=deleted response row has wrong status", match)
    ok("GET /finance/invoices?status=deleted returns soft-deleted invoice", {"deleted_count": len(deleted_rows)})

    # Existing status filters still respond and only return requested status.
    status_filter_results = {}
    for status in ["draft", "issued", "paid", "cancelled", "voided", "converted", "approved", "pending"]:
        resp = sess.get(f"{BASE_URL}/finance/invoices", params={"status": status}, timeout=20)
        require(resp.status_code == 200, f"status filter {status} failed", resp.text)
        rows = resp.json()
        wrong = [inv.get("status") for inv in rows if inv.get("status") != status]
        require(not wrong, f"status filter {status} returned wrong statuses", wrong[:5])
        status_filter_results[status] = len(rows)
    ok("non-deleted status filters still return 200 and matching statuses", status_filter_results)

    print("RESULT_JSON=" + json.dumps(results, default=str, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise