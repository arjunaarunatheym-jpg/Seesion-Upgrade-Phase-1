#!/usr/bin/env python3
"""Soft-delete leftover QA Soft Delete Test draft invoices created during verification."""

import os
from pathlib import Path

import requests
from pymongo import MongoClient


def parse_env(path: str) -> dict:
    data = {}
    for raw in Path(path).read_text().splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            data[key] = value.strip().strip('"').strip("'")
    return data


BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:8001/api")
EMAIL = os.environ.get("TEST_EMAIL", "arjuna@mddrc.com.my")
PASSWORD = os.environ.get("TEST_PASSWORD", "Dana102229")


def main():
    env = parse_env("/app/backend/.env")
    db = MongoClient(env.get("MONGO_URL", "mongodb://localhost:27017"))[env.get("DB_NAME", "driving_training_db")]
    sess = requests.Session()
    login_resp = sess.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    login_resp.raise_for_status()
    sess.headers.update({"Authorization": f"Bearer {login_resp.json()['access_token']}"})

    rows = list(db.invoices.find(
        {"bill_to_name": {"$regex": r"^QA Soft Delete Test"}, "status": {"$ne": "deleted"}},
        {"_id": 0, "id": 1, "invoice_number": 1, "status": 1, "bill_to_name": 1},
    ))
    for row in rows:
        resp = sess.delete(
            f"{BASE_URL}/finance/invoices/{row['id']}",
            json={"reason": "QA cleanup after focused soft-delete verification", "reuse_number": False},
            timeout=20,
        )
        print(f"cleanup {row['invoice_number']} ({row['status']}): HTTP {resp.status_code}")
        resp.raise_for_status()
    print(f"cleanup_count={len(rows)}")


if __name__ == "__main__":
    main()