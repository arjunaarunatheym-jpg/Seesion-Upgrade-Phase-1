"""One-time script to add indexes supporting the Payment History query patterns.
Safe to run repeatedly (create_index is idempotent).
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


async def _safe_index(collection, keys, **kwargs):
    try:
        await collection.create_index(keys, **kwargs)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "indexoptionsconflict" in msg:
            return False
        raise


async def main():
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("Creating payment-history indexes...")
    # Primary sort order — newest first / oldest first
    await _safe_index(db.payments, [("payment_date", -1), ("created_at", -1)], name="payment_date_created_desc")
    # Amount-based sort
    await _safe_index(db.payments, "amount", name="payment_amount")
    # Common exact-match filters
    await _safe_index(db.payments, "payment_method", name="payment_method")
    await _safe_index(db.payments, "payment_type", name="payment_type")
    await _safe_index(db.payments, "status", name="payment_status")
    await _safe_index(db.payments, "invoice_id", name="payment_invoice_id")
    # Search on receipt / reference numbers (regex uses prefix scan; a plain index still helps)
    await _safe_index(db.payments, "receipt_number", name="payment_receipt_number")
    await _safe_index(db.payments, "reference_number", name="payment_reference_number")

    # Helpful indexes on invoices for search join
    await _safe_index(db.invoices, "invoice_number", name="invoice_number_idx")
    await _safe_index(db.invoices, "company_name", name="invoice_company_name_idx")
    await _safe_index(db.invoices, "bill_to_name", name="invoice_bill_to_name_idx")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
