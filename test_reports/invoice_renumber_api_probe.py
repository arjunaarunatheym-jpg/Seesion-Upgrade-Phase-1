import os
import requests

BASE_URL = os.environ.get("BASE_URL", "https://training-finance-hub-1.preview.emergentagent.com/api")


def login(email: str, password: str):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=20)
    print(f"LOGIN {email}: status={r.status_code}")
    r.raise_for_status()
    data = r.json()
    user = data.get("user", {})
    print({"email": user.get("email"), "role": user.get("role"), "id": user.get("id")})
    return data.get("access_token"), user


def get_invoices(token: str):
    r = requests.get(f"{BASE_URL}/finance/invoices", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    print(f"GET /finance/invoices: status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500])
        return []
    invoices = r.json()
    print(f"invoice_count={len(invoices)}")
    doc_type_counts = {}
    for inv in invoices:
        key = inv.get("document_type") or "<missing>"
        doc_type_counts[key] = doc_type_counts.get(key, 0) + 1
    print(f"document_type_counts={doc_type_counts}")
    for inv in invoices[:10]:
        print({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "document_type": inv.get("document_type"),
            "status": inv.get("status"),
            "company_name": inv.get("company_name") or inv.get("bill_to_name"),
            "total_amount": inv.get("total_amount"),
        })
    return invoices


if __name__ == "__main__":
    token, user = login("arjuna@mddrc.com.my", "Dana102229")
    get_invoices(token)
    try:
        coord_token, coord_user = login("malek@mddrc.com.my", "mddrc1")
        get_invoices(coord_token)
    except Exception as exc:
        print(f"non_admin_probe_failed={exc}")