#!/usr/bin/env python3
"""
Check session invoice details for testing
"""

import requests
import json

# Configuration
BASE_URL = "https://hr-quote-system.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

def main():
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    # Login
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get first session
    response = session.get(f"{BASE_URL}/sessions", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get sessions: {response.status_code}")
        return
    
    sessions = response.json()
    if not sessions:
        print("No sessions found")
        return
    
    session_data = sessions[0]
    session_id = session_data['id']
    print(f"Session ID: {session_id}")
    print(f"Session Name: {session_data.get('name', 'N/A')}")
    print(f"Invoice ID: {session_data.get('invoice_id', 'N/A')}")
    print(f"Invoice Number: {session_data.get('invoice_number', 'N/A')}")
    print(f"Invoice Status: {session_data.get('invoice_status', 'N/A')}")
    
    # Check if there's an invoice
    invoice_id = session_data.get('invoice_id')
    if invoice_id:
        response = session.get(f"{BASE_URL}/finance/invoices/{invoice_id}", headers=headers)
        if response.status_code == 200:
            invoice = response.json()
            print(f"\nInvoice Details:")
            print(f"  Total Amount: RM {invoice.get('total_amount', 0)}")
            print(f"  Subtotal: RM {invoice.get('subtotal', 0)}")
            print(f"  Tax Amount: RM {invoice.get('tax_amount', 0)}")
            print(f"  Tax Rate: {invoice.get('tax_rate', 0)}%")
            print(f"  Status: {invoice.get('status', 'N/A')}")
        else:
            print(f"Failed to get invoice: {response.status_code}")
    else:
        print("No invoice associated with this session")

if __name__ == "__main__":
    main()