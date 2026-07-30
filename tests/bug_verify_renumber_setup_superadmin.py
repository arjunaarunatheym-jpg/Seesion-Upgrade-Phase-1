#!/usr/bin/env python3
"""Create an isolated temporary super_admin login for role-gating verification."""
import json
import time
from pathlib import Path

import requests


BASE_URL = "http://localhost:8001/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"


def main():
    ts = int(time.time())
    email = f"qa.superadmin.renumber.{ts}@mddrc.test"
    password = "QaSuper102229"
    id_number = f"QASUP{ts}"

    login = requests.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    login.raise_for_status()
    admin_data = login.json()
    token = admin_data["access_token"]
    admin_user = admin_data["user"]

    payload = {
        "email": email,
        "password": password,
        "full_name": f"QA Super Admin Renumber {ts}",
        "id_number": id_number,
        "role": "super_admin",
        "additional_roles": [],
    }
    reg = requests.post(
        f"{BASE_URL}/auth/register",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    reg.raise_for_status()

    verify = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=20)
    verify.raise_for_status()
    verify_user = verify.json()["user"]

    out_path = Path("/app/test_reports/bug_renumber_seed_data.json")
    existing = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    existing.update({
        "provided_arjuna_login_role": admin_user.get("role"),
        "temp_super_admin_email": email,
        "temp_super_admin_password": password,
        "temp_super_admin_id_number": id_number,
        "temp_super_admin_user": verify_user,
    })
    out_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(json.dumps(existing, indent=2))


if __name__ == "__main__":
    main()