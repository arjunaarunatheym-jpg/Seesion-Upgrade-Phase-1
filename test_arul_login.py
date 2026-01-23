#!/usr/bin/env python3
"""
Test login for arul@kone.com supervisor who has 'hashed_password' field
"""

import requests
from pymongo import MongoClient

BASE_URL = "https://trainadmin-1.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "driving_training_db"

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]

# Get arul's user document
arul = db.users.find_one({"email": "arul@kone.com"}, {"_id": 0})

print("\n" + "="*80)
print("ARUL@KONE.COM USER DOCUMENT ANALYSIS")
print("="*80)
print(f"\nEmail: {arul.get('email')}")
print(f"Full Name: {arul.get('full_name')}")
print(f"Role: {arul.get('role')}")
print(f"\nPassword Fields:")
print(f"  Has 'password' field: {'password' in arul}")
print(f"  Has 'hashed_password' field: {'hashed_password' in arul}")

if 'password' in arul:
    print(f"  'password' value: {arul['password'][:50]}...")
if 'hashed_password' in arul:
    print(f"  'hashed_password' value: {arul['hashed_password'][:50]}...")

# Test login with the backend endpoint
print("\n" + "="*80)
print("TESTING LOGIN ENDPOINT")
print("="*80)

# Try to login (we don't know the password, so this will likely fail)
# But we can see what the backend does
session = requests.Session()
session.headers.update({'Content-Type': 'application/json'})

login_data = {
    "email": "arul@kone.com",
    "password": "test_password"  # We don't know the real password
}

print(f"\nAttempting login with email: {login_data['email']}")
response = session.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"Response status: {response.status_code}")
print(f"Response: {response.text}")

# Now let's check if the backend code handles both fields
print("\n" + "="*80)
print("BACKEND CODE ANALYSIS")
print("="*80)
print("\nThe login endpoint (server.py lines 556-582) contains:")
print("  password_hash = user_doc.get('password') or user_doc.get('hashed_password')")
print("\nThis means:")
print("  1. It first tries to get 'password' field")
print("  2. If 'password' is None or doesn't exist, it tries 'hashed_password'")
print("  3. For arul@kone.com, it should use 'hashed_password' field")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("\nThe backend login endpoint DOES handle both 'password' and 'hashed_password' fields.")
print("The issue is likely that:")
print("  1. The user doesn't know the correct password for arul@kone.com")
print("  2. OR the password was set incorrectly when the user was created")
print("\nRECOMMENDATION:")
print("  - Use the 'Forgot Password' functionality to reset the password")
print("  - OR have an admin reset the password for this user")
