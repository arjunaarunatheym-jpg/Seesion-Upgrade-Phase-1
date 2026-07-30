#!/usr/bin/env python3
"""Seed isolated QA invoices for Finance > Invoices renumber UI verification."""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    ts = int(time.time())
    suffix = str(ts)[-4:]
    base_seq = 9100 + int(suffix) % 800
    now_iso = datetime.now(timezone.utc).isoformat()

    # Keep these in Jan 2026 so they appear in the 2026 UI but do not disturb July invoice sequencing.
    target_number = f"INV/MDDRC/2026/01/{base_seq:04d}"
    duplicate_number = f"INV/MDDRC/2026/01/{base_seq + 1:04d}"
    new_number = f"INV/MDDRC/2026/01/{base_seq + 2:04d}"
    proforma_number = f"PI/MDDRC/2026/01/{base_seq:04d}"

    # If the generated numbers somehow exist, retry a nearby range.
    for offset in range(0, 200, 10):
        candidate_numbers = [
            f"INV/MDDRC/2026/01/{base_seq + offset:04d}",
            f"INV/MDDRC/2026/01/{base_seq + offset + 1:04d}",
            f"INV/MDDRC/2026/01/{base_seq + offset + 2:04d}",
            f"PI/MDDRC/2026/01/{base_seq + offset:04d}",
        ]
        existing = await db.invoices.count_documents({"invoice_number": {"$in": candidate_numbers}})
        if existing == 0:
            target_number, duplicate_number, new_number, proforma_number = candidate_numbers
            break
    else:
        raise RuntimeError("Could not find unused QA invoice number range")

    def invoice_doc(kind: str, number: str, document_type: str = "invoice"):
        invoice_id = str(uuid.uuid4())
        is_proforma = document_type == "proforma"
        return {
            "id": invoice_id,
            "invoice_number": number,
            "document_type": document_type,
            "invoice_type": "adhoc" if not is_proforma else "session",
            "bill_to_name": f"QA Renumber {kind} {ts}",
            "bill_to_address": "QA Test Address",
            "company_name": f"QA Renumber {kind} {ts}",
            "session_name": "Ad-Hoc" if not is_proforma else f"QA Proforma Session {ts}",
            "line_items": [{"description": f"QA Renumber {kind}", "quantity": 1, "unit_price": 10, "amount": 10}],
            "subtotal": 10,
            "tax_rate": 0,
            "tax_amount": 0,
            "discount": 0,
            "rounding": 0,
            "total_amount": 10,
            "status": "draft",
            "invoice_date": "2026-01-15",
            "created_at": now_iso,
            "updated_at": now_iso,
            "created_by": "qa-bug-verification",
            "notes": "Seeded by focused bug verification; safe test data.",
        }

    target = invoice_doc("target", target_number)
    duplicate = invoice_doc("duplicate", duplicate_number)
    proforma = invoice_doc("proforma", proforma_number, "proforma")
    await db.invoices.insert_many([target, duplicate, proforma])

    arjuna = await db.users.find_one({"email": "arjuna@mddrc.com.my"}, {"_id": 0, "email": 1, "role": 1, "full_name": 1})

    output = {
        "seeded_at": now_iso,
        "user": arjuna,
        "target_invoice_id": target["id"],
        "target_old_number": target_number,
        "target_new_number": new_number,
        "duplicate_invoice_id": duplicate["id"],
        "duplicate_number": duplicate_number,
        "proforma_invoice_id": proforma["id"],
        "proforma_number": proforma_number,
    }
    out_path = Path("/app/test_reports/bug_renumber_seed_data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())