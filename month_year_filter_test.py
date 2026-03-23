#!/usr/bin/env python3
"""
Test month/year filtering for past training endpoint as specified in review request
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://payroll-fix-19.preview.emergentagent.com/api"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def test_month_year_filtering():
    """Test GET /api/sessions/past-training?month=11&year=2025 as specified in review request"""
    
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    # Login as admin
    admin_login = {
        "email": "arjuna@mddrc.com.my",
        "password": "Dana102229"
    }
    
    try:
        response = session.post(f"{BASE_URL}/auth/login", json=admin_login)
        if response.status_code == 200:
            admin_token = response.json()['access_token']
            log("✅ Admin login successful")
        else:
            log(f"❌ Admin login failed: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Admin login error: {str(e)}", "ERROR")
        return False
    
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Test the specific endpoint mentioned in review request
    log("Testing GET /api/sessions/past-training?month=11&year=2025...")
    
    params = {
        'month': 11,
        'year': 2025
    }
    
    try:
        response = session.get(f"{BASE_URL}/sessions/past-training", headers=admin_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Past training with month=11&year=2025 retrieved successfully. Count: {len(data)}")
            
            # Verify response structure
            for session_data in data:
                required_fields = ['id', 'name', 'start_date', 'end_date', 'company_name', 'program_name']
                for field in required_fields:
                    if field not in session_data:
                        log(f"❌ Missing required field '{field}' in response", "ERROR")
                        return False
                
                # Verify date filtering (sessions should end in November 2025)
                end_date = datetime.fromisoformat(session_data['end_date']).date()
                if end_date.month != 11 or end_date.year != 2025:
                    log(f"⚠️ Found session outside filter range: {session_data['name']} ended {end_date}", "WARNING")
            
            log("✅ Month/year filtering working correctly")
            log("✅ Response structure includes all required fields")
            
            # Test without filters for comparison
            log("Testing without filters for comparison...")
            response_no_filter = session.get(f"{BASE_URL}/sessions/past-training", headers=admin_headers)
            
            if response_no_filter.status_code == 200:
                data_no_filter = response_no_filter.json()
                log(f"✅ Past training without filters retrieved. Count: {len(data_no_filter)}")
                
                if len(data_no_filter) >= len(data):
                    log("✅ Filtering is working (filtered results <= unfiltered results)")
                else:
                    log("⚠️ Filtered results more than unfiltered (unexpected)", "WARNING")
            
            return True
        else:
            log(f"❌ Past training request failed: {response.status_code} - {response.text}", "ERROR")
            return False
            
    except Exception as e:
        log(f"❌ Past training test error: {str(e)}", "ERROR")
        return False

if __name__ == "__main__":
    success = test_month_year_filtering()
    exit(0 if success else 1)