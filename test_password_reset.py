#!/usr/bin/env python3
"""
Test password reset functionality for arul@kone.com
"""

import requests
from pymongo import MongoClient

BASE_URL = "https://payment-accuracy.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "driving_training_db"

session = requests.Session()
session.headers.update({'Content-Type': 'application/json'})

print("\n" + "="*80)
print("PASSWORD RESET TEST FOR ARUL@KONE.COM")
print("="*80)

# Step 1: Check current password field
print("\nStep 1: Checking current password field in database...")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]

arul_before = db.users.find_one({"email": "arul@kone.com"}, {"_id": 0, "email": 1, "password": 1, "hashed_password": 1})
print(f"  Email: {arul_before.get('email')}")
print(f"  Has 'password' field: {'password' in arul_before}")
print(f"  Has 'hashed_password' field: {'hashed_password' in arul_before}")
if 'hashed_password' in arul_before:
    print(f"  'hashed_password' value (first 30 chars): {arul_before['hashed_password'][:30]}...")

# Step 2: Use forgot password endpoint
print("\nStep 2: Calling forgot password endpoint...")
forgot_data = {
    "email": "arul@kone.com"
}
response = session.post(f"{BASE_URL}/auth/forgot-password", json=forgot_data)
print(f"  Status: {response.status_code}")
print(f"  Response: {response.json()}")

# Step 3: Reset password
print("\nStep 3: Resetting password to 'newpassword123'...")
reset_data = {
    "email": "arul@kone.com",
    "new_password": "newpassword123"
}
response = session.post(f"{BASE_URL}/auth/reset-password", json=reset_data)
print(f"  Status: {response.status_code}")
print(f"  Response: {response.json()}")

# Step 4: Check password field after reset
print("\nStep 4: Checking password field after reset...")
arul_after = db.users.find_one({"email": "arul@kone.com"}, {"_id": 0, "email": 1, "password": 1, "hashed_password": 1})
print(f"  Email: {arul_after.get('email')}")
print(f"  Has 'password' field: {'password' in arul_after}")
print(f"  Has 'hashed_password' field: {'hashed_password' in arul_after}")
if 'password' in arul_after:
    print(f"  'password' value (first 30 chars): {arul_after['password'][:30]}...")
if 'hashed_password' in arul_after:
    print(f"  'hashed_password' value (first 30 chars): {arul_after['hashed_password'][:30]}...")

# Step 5: Test login with new password
print("\nStep 5: Testing login with new password...")
login_data = {
    "email": "arul@kone.com",
    "password": "newpassword123"
}
response = session.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"  ✅ Login successful!")
    print(f"  User: {data['user']['full_name']}")
    print(f"  Role: {data['user']['role']}")
else:
    print(f"  ❌ Login failed: {response.text}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("\nThe password reset endpoint (server.py lines 611-632):")
print("  - Updates the password using: {'$set': {'password': hashed_password}}")
print("  - This creates/updates the 'password' field")
print("  - It does NOT remove the old 'hashed_password' field")
print("\nAfter reset:")
print("  - User will have BOTH 'password' and 'hashed_password' fields")
print("  - Login will use 'password' field (checked first)")
print("  - The old 'hashed_password' field becomes obsolete but harmless")
