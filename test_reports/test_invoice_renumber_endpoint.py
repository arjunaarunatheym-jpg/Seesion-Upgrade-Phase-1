#!/usr/bin/env python3
"""Focused backend verification for invoice renumber endpoint.

Uses curl for HTTP calls and MongoDB inspection for persistence proof.
Does not modify product code. Leaves QA-marked invoices/users as audit evidence.
"""
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pymongo import MongoClient


BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8001/api")
APP_DIR = Path("/app")
OUT_PATH = APP_DIR / "test_reports" / "invoice_renumber_endpoint_output.json"


class TestFailure(Exception):
    pass


def read_env(path: Path) -> dict:
    env = {}
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
    return env


def curl_api(method: str, path: str, token: str | None = None, body=None):
    url = f"{BASE_URL}{path}"
    cmd = ["curl", "-sS", "-X", method, url, "-H", "Content-Type: application/json", "-w", "\n%{http_code}"]
    if token:
        cmd.extend(["-H", f"Authorization: Bearer {token}"])
    if body is not None:
        cmd.extend(["--data-binary", json.dumps(body)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if proc.returncode != 0:
        raise TestFailure(f"curl failed for {method} {path}: {proc.stderr.strip()}")
    raw = proc.stdout
    if "\n" not in raw:
        raise TestFailure(f"Unexpected curl output for {method} {path}: {raw[:200]}")
    response_text, code_text = raw.rsplit("\n", 1)
    try:
        parsed = json.loads(response_text) if response_text else None
    except json.JSONDecodeError:
        parsed = response_text
    return int(code_text), parsed


def require(condition, message):
    if not condition:
        raise TestFailure(message)


def require_status(actual, expected, label, payload=None):
    require(actual == expected, f"{label}: expected HTTP {expected}, got {actual}, payload={payload}")


def seq(invoice_number: str) -> int:
    return int(invoice_number.split("/")[-1])


def prefix(invoice_number: str) -> str:
    return "/".join(invoice_number.split("/")[:-1]) + "/"


def next_non_current_number(db, run_seq: int) -> str:
    # Keep it outside the current YYYY/MM prefix so current invoice generation is not affected.
    candidate_seq = 8000 + (run_seq % 1500)
    while True:
        candidate = f"INV/MDDRC/2099/12/{candidate_seq:04d}"
        if not db.invoices.find_one({"invoice_number": candidate}, {"_id": 1}):
            return candidate
        candidate_seq += 1


def main():
    run_id = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y%m%d%H%M%S")
    run_seq = int(time.time()) % 100000
    today = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d")
    env = read_env(APP_DIR / "backend" / ".env")
    client = MongoClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    evidence = {
        "run_id": run_id,
        "base_url": BASE_URL,
        "steps": [],
        "created": {},
        "credential_attempts": [],
    }

    def step(name, details=None):
        evidence["steps"].append({"name": name, "details": details or {}})
        print(f"PASS: {name}")

    # Login: try the requested credential first, then environment-seeded admin fallback if needed.
    login_candidates = [
        ("requested", "arjuna@mddrc.com.my", "Dana102229"),
        ("env_admin", env.get("ADMIN_EMAIL"), env.get("ADMIN_PASSWORD")),
    ]
    admin_token = None
    admin_user = None
    for label, email, password in login_candidates:
        if not email or not password:
            continue
        status, payload = curl_api("POST", "/auth/login", body={"email": email, "password": password})
        evidence["credential_attempts"].append({"label": label, "email": email, "status": status, "role": (payload or {}).get("user", {}).get("role") if isinstance(payload, dict) else None})
        if status == 200:
            admin_token = payload["access_token"]
            admin_user = payload["user"]
            break
    require(admin_token, f"No usable admin login. Attempts: {evidence['credential_attempts']}")
    require(admin_user["role"] in ["admin", "super_admin"], f"Login user is not admin/super_admin: {admin_user}")
    step("authenticated admin/super_admin", {"email": admin_user.get("email"), "role": admin_user.get("role")})

    # Create a non-admin user through the API, then login as that user.
    participant_email = f"qa.renumber.{run_id}@example.com"
    participant_password = "Participant123!"
    register_body = {
        "email": participant_email,
        "password": participant_password,
        "full_name": f"QA Renumber Non Admin {run_id}",
        "id_number": f"QA-RN-{run_id}",
        "role": "participant",
        "phone_number": "",
    }
    status, reg_payload = curl_api("POST", "/auth/register", admin_token, register_body)
    require_status(status, 200, "register non-admin", reg_payload)
    status, non_admin_login = curl_api("POST", "/auth/login", body={"email": participant_email, "password": participant_password})
    require_status(status, 200, "login non-admin", non_admin_login)
    non_admin_token = non_admin_login["access_token"]
    step("created/logged-in non-admin test user", {"email": participant_email, "role": non_admin_login["user"].get("role")})

    def create_adhoc(label: str, amount: float):
        body = {
            "bill_to_name": f"QA Renumber {label} {run_id}",
            "bill_to_address": "QA address - safe test invoice",
            "contact_email": f"qa.renumber.{run_id}@example.com",
            "your_reference": f"QA-REN-{run_id}-{label}",
            "line_items": [{"description": f"QA renumber test item {label}", "quantity": 1, "unit_price": amount}],
            "sst_percent": 0,
            "notes": "Created by focused renumber endpoint verification",
            "invoice_date": today,
        }
        st, payload = curl_api("POST", "/finance/invoices/adhoc", admin_token, body)
        require_status(st, 200, f"create ad-hoc invoice {label}", payload)
        return payload

    inv_a = create_adhoc("gap-holder", 10.0)
    inv_b = create_adhoc("paid-target", 25.0)
    evidence["created"]["gap_holder_invoice"] = inv_a
    evidence["created"]["paid_target_invoice"] = inv_b
    require(prefix(inv_a["invoice_number"]) == prefix(inv_b["invoice_number"]), f"Created invoices not in same prefix: {inv_a['invoice_number']} vs {inv_b['invoice_number']}")
    require(seq(inv_b["invoice_number"]) == seq(inv_a["invoice_number"]) + 1, f"Created invoices were not consecutive: {inv_a['invoice_number']} then {inv_b['invoice_number']}")
    step("created two consecutive ad-hoc invoices", {"gap_number": inv_a["invoice_number"], "target_old_number": inv_b["invoice_number"]})

    # Edge cases against the target invoice before changing any number.
    conflict_body = {"new_invoice_number": inv_a["invoice_number"], "reason": "QA conflict validation reason"}
    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/renumber", admin_token, conflict_body)
    require_status(st, 400, "renumber conflict used number", payload)
    require("already used" in payload.get("detail", "").lower(), f"Conflict error not clear: {payload}")
    step("renumber to already-used invoice number returns clear 400", payload)

    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/renumber", admin_token, {"new_invoice_number": inv_b["invoice_number"], "reason": "QA same number validation"})
    require_status(st, 400, "renumber same number", payload)
    require("same" in payload.get("detail", "").lower(), f"Same-number error not clear: {payload}")
    step("renumber to same number returns 400", payload)

    short_reason_candidate = next_non_current_number(db, run_seq)
    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/renumber", admin_token, {"new_invoice_number": short_reason_candidate, "reason": "short"})
    require_status(st, 422, "renumber short reason validation", payload)
    step("renumber reason shorter than 10 chars returns 422", payload)

    non_admin_candidate = next_non_current_number(db, run_seq + 1)
    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/renumber", non_admin_token, {"new_invoice_number": non_admin_candidate, "reason": "QA non admin forbidden check"})
    require_status(st, 403, "non-admin renumber forbidden", payload)
    step("non-admin renumber attempt returns 403", payload)

    # Put the target invoice through issued -> paid flow to create real downstream payment/journal references.
    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/approve", admin_token)
    require_status(st, 200, "approve target invoice", payload)
    st, payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/issue", admin_token)
    require_status(st, 200, "issue target invoice", payload)
    payment_body = {
        "invoice_id": inv_b["id"],
        "amount": inv_b["total_amount"],
        "payment_date": today,
        "payment_method": "bank_transfer",
        "reference_number": f"QA-REN-PAY-{run_id}",
        "notes": "QA payment for invoice renumber verification",
        "payment_type": "self_pay",
    }
    st, payment_payload = curl_api("POST", "/finance/payments", admin_token, payment_body)
    require_status(st, 200, "record payment for target invoice", payment_payload)
    payment_id = payment_payload["id"]
    evidence["created"]["payment"] = {"id": payment_id, "receipt_number": payment_payload.get("receipt_number")}
    target_before_renumber = db.invoices.find_one({"id": inv_b["id"]}, {"_id": 0})
    require(target_before_renumber and target_before_renumber.get("status") == "paid", f"Target invoice not paid before renumber: {target_before_renumber}")
    step("target invoice approved, issued, and paid", {"invoice_id": inv_b["id"], "payment_id": payment_id})

    # Free the gap-holder's current number by moving it to a non-current prefix, then renumber paid target into the gap.
    moved_gap_number = next_non_current_number(db, run_seq + 2)
    st, move_payload = curl_api("POST", f"/finance/invoices/{inv_a['id']}/renumber", admin_token, {"new_invoice_number": moved_gap_number, "reason": "QA moving gap holder outside current prefix"})
    require_status(st, 200, "move gap-holder invoice out of current prefix", move_payload)
    step("freed current-month gap number", {"freed_number": inv_a["invoice_number"], "gap_holder_new_number": moved_gap_number})

    final_reason = "QA paid invoice renumber to fill freed audit gap"
    st, renumber_payload = curl_api("POST", f"/finance/invoices/{inv_b['id']}/renumber", admin_token, {"new_invoice_number": inv_a["invoice_number"], "reason": final_reason})
    require_status(st, 200, "renumber paid target invoice into gap", renumber_payload)
    require(renumber_payload.get("old_number") == inv_b["invoice_number"], f"old_number mismatch: {renumber_payload}")
    require(renumber_payload.get("new_number") == inv_a["invoice_number"], f"new_number mismatch: {renumber_payload}")
    step("paid invoice renumber endpoint returned expected 200 payload", renumber_payload)

    target_after = db.invoices.find_one({"id": inv_b["id"]}, {"_id": 0})
    require(target_after.get("invoice_number") == inv_a["invoice_number"], f"DB invoice_number not updated: {target_after}")
    require(target_after.get("renumbered_from") == inv_b["invoice_number"], f"renumbered_from missing/wrong: {target_after}")
    require(target_after.get("renumbered_by") == admin_user["id"], f"renumbered_by missing/wrong: {target_after}")
    require(target_after.get("renumbered_at"), f"renumbered_at missing: {target_after}")
    require(target_after.get("renumber_reason") == final_reason, f"renumber_reason missing/wrong: {target_after}")
    require(target_after.get("status") == "paid", f"renumber changed status unexpectedly: {target_after.get('status')}")
    audit_log = db.finance_audit_log.find_one({"entity_id": inv_b["id"], "action": "renumbered"}, {"_id": 0})
    require(audit_log, "finance_audit_log renumbered entry missing")
    step("MongoDB invoice state and audit fields updated", {"renumbered_from": target_after.get("renumbered_from"), "renumbered_by": target_after.get("renumbered_by"), "renumbered_at": target_after.get("renumbered_at")})

    st, paid_list = curl_api("GET", "/finance/invoices?status=paid", admin_token)
    require_status(st, 200, "GET paid invoices", paid_list if isinstance(paid_list, dict) else None)
    matching_paid = [x for x in paid_list if x.get("id") == inv_b["id"]]
    require(matching_paid and matching_paid[0].get("invoice_number") == inv_a["invoice_number"], f"GET paid invoices did not show renamed paid invoice: {matching_paid}")
    step("GET /finance/invoices?status=paid returns renamed invoice", {"invoice_number": matching_paid[0].get("invoice_number")})

    # Downstream payment and journal checks.
    payment_doc = db.payments.find_one({"id": payment_id}, {"_id": 0})
    require(payment_doc and payment_doc.get("invoice_id") == inv_b["id"], f"Payment no longer references target invoice id: {payment_doc}")
    st, receipt_payload = curl_api("GET", f"/finance/payments/{payment_id}/receipt", admin_token)
    require_status(st, 200, "GET payment receipt after renumber", receipt_payload)
    require(receipt_payload.get("invoice", {}).get("id") == inv_b["id"], f"Receipt invoice id mismatch after renumber: {receipt_payload}")
    require(receipt_payload.get("invoice", {}).get("invoice_number") == inv_a["invoice_number"], f"Receipt did not resolve new invoice number after renumber: {receipt_payload}")
    journal_invoice = db.journal_entries.find_one({"source_module": "invoice", "source_id": inv_b["id"]}, {"_id": 0})
    journal_payment = db.journal_entries.find_one({"source_module": "payment", "source_id": payment_id}, {"_id": 0})
    require(journal_invoice is None or (journal_invoice.get("status") == "posted" and journal_invoice.get("is_balanced") is True), f"Invoice journal entry broken: {journal_invoice}")
    require(journal_payment is None or (journal_payment.get("status") == "posted" and journal_payment.get("is_balanced") is True), f"Payment journal entry broken: {journal_payment}")
    step("downstream payment/receipt and journal source ids remain usable", {
        "payment_invoice_id": payment_doc.get("invoice_id"),
        "receipt_invoice_number": receipt_payload.get("invoice", {}).get("invoice_number"),
        "invoice_journal_source_reference": journal_invoice.get("source_reference") if journal_invoice else None,
        "payment_journal_source_reference": journal_payment.get("source_reference") if journal_payment else None,
    })

    # User-reported behavior: old max number should be freed for the next new invoice.
    inv_c = create_adhoc("next-after-renumber", 15.0)
    evidence["created"]["next_invoice"] = inv_c
    require(inv_c["invoice_number"] == inv_b["invoice_number"], f"New invoice did not take freed old number. Expected {inv_b['invoice_number']}, got {inv_c['invoice_number']}")
    step("new invoice used the freed old number", {"new_invoice_id": inv_c["id"], "invoice_number": inv_c["invoice_number"]})

    evidence["result"] = "passed"
    OUT_PATH.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence written to {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error_payload = {"result": "failed", "error": str(exc)}
        OUT_PATH.write_text(json.dumps(error_payload, indent=2, default=str))
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)