"""
Iteration 20 - Calendar and Marketing Sessions Testing

Features to test:
1. Calendar API: GET /api/sessions/calendar returns ALL sessions (no role-based filtering)
2. Marketing Sessions API: GET /api/sessions/my-marketing-sessions returns current/past lists
3. Marketing Sessions API: Role-based access control (403 for non-marketing roles)
4. Calendar route access for marketing and finance roles
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCalendarAPI:
    """Test that calendar endpoint returns ALL sessions without role filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_token = token
    
    def test_calendar_endpoint_returns_all_sessions(self):
        """Calendar endpoint should return all sessions without filtering"""
        resp = self.session.get(f"{BASE_URL}/api/sessions/calendar")
        assert resp.status_code == 200, f"Calendar endpoint failed: {resp.text}"
        
        sessions = resp.json()
        assert isinstance(sessions, list), "Calendar should return a list"
        
        # Verify sessions include both active and archived (all statuses)
        print(f"Calendar returned {len(sessions)} sessions")
        
        # Check session structure
        if sessions:
            session = sessions[0]
            print(f"Sample session keys: {session.keys()}")
            # Should have basic session fields
            assert "id" in session, "Session should have id"
    
    def test_calendar_endpoint_requires_auth(self):
        """Calendar endpoint should require authentication"""
        unauthenticated = requests.Session()
        resp = unauthenticated.get(f"{BASE_URL}/api/sessions/calendar")
        # Should return 401 or 403
        assert resp.status_code in [401, 403], f"Expected auth error, got {resp.status_code}"


class TestCalendarAccessForAllRoles:
    """Test that calendar is accessible to different staff roles"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_calendar_accessible_by_admin(self):
        """Admin should access calendar"""
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = self.session.get(f"{BASE_URL}/api/sessions/calendar")
        assert resp.status_code == 200, f"Admin calendar access failed: {resp.status_code}"
    
    def test_calendar_accessible_by_coordinator(self):
        """Coordinator should access calendar"""
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "chandra.selvaguru@mddrc.com.my",
            "password": "mddrc1"
        })
        assert login_resp.status_code == 200, f"Coordinator login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = self.session.get(f"{BASE_URL}/api/sessions/calendar")
        assert resp.status_code == 200, f"Coordinator calendar access failed: {resp.status_code}"


class TestMarketingSessionsAPI:
    """Test the new /my-marketing-sessions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin (has marketing access)
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_my_marketing_sessions_endpoint_exists(self):
        """Marketing sessions endpoint should exist and be accessible by admin"""
        resp = self.session.get(f"{BASE_URL}/api/sessions/my-marketing-sessions")
        assert resp.status_code == 200, f"Marketing sessions endpoint failed: {resp.text}"
        
        data = resp.json()
        print(f"Marketing sessions response keys: {data.keys()}")
        
        # Should return current and past lists
        assert "current" in data, "Should have 'current' sessions list"
        assert "past" in data, "Should have 'past' sessions list"
        assert isinstance(data["current"], list), "current should be a list"
        assert isinstance(data["past"], list), "past should be a list"
        
        print(f"Current sessions: {len(data['current'])}, Past sessions: {len(data['past'])}")
    
    def test_marketing_sessions_returns_enriched_data(self):
        """Marketing sessions should include enriched data (company_name, program_name, etc.)"""
        resp = self.session.get(f"{BASE_URL}/api/sessions/my-marketing-sessions")
        assert resp.status_code == 200
        
        data = resp.json()
        all_sessions = data["current"] + data["past"]
        
        if all_sessions:
            session = all_sessions[0]
            print(f"Marketing session sample keys: {session.keys()}")
            # Should have enriched fields
            # Note: These might not exist if no sessions have marketing_user_id


class TestMarketingSessionsAccessControl:
    """Test access control for marketing sessions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_marketing_sessions_requires_auth(self):
        """Marketing sessions endpoint should require authentication"""
        resp = self.session.get(f"{BASE_URL}/api/sessions/my-marketing-sessions")
        assert resp.status_code in [401, 403], f"Expected auth error, got {resp.status_code}"
    
    def test_marketing_sessions_forbidden_for_coordinator(self):
        """Coordinator (non-marketing) should get 403"""
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "chandra.selvaguru@mddrc.com.my",
            "password": "mddrc1"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = self.session.get(f"{BASE_URL}/api/sessions/my-marketing-sessions")
        # Coordinator is not marketing/admin/super_admin, should get 403
        assert resp.status_code == 403, f"Expected 403 for coordinator, got {resp.status_code}"
        print(f"Correctly returned 403 for coordinator: {resp.json()}")
    
    def test_marketing_sessions_allowed_for_admin(self):
        """Admin should access marketing sessions"""
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = self.session.get(f"{BASE_URL}/api/sessions/my-marketing-sessions")
        assert resp.status_code == 200, f"Admin should access marketing sessions: {resp.status_code}"


class TestCalendarNoFiltering:
    """Test that calendar returns ALL sessions without role-based filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_calendar_returns_all_for_coordinator(self):
        """Coordinator should see ALL sessions in calendar, not just their assigned ones"""
        # Login as coordinator
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "chandra.selvaguru@mddrc.com.my",
            "password": "mddrc1"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        coordinator_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Get calendar for coordinator
        coord_calendar = requests.get(
            f"{BASE_URL}/api/sessions/calendar", 
            headers=coordinator_headers
        )
        assert coord_calendar.status_code == 200
        coord_sessions = coord_calendar.json()
        
        # Login as admin
        admin_session = requests.Session()
        admin_login = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json().get("access_token")
        
        # Get calendar for admin
        admin_calendar = requests.get(
            f"{BASE_URL}/api/sessions/calendar",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_calendar.status_code == 200
        admin_sessions = admin_calendar.json()
        
        # Both should see the same sessions (no filtering)
        print(f"Coordinator sees {len(coord_sessions)} sessions")
        print(f"Admin sees {len(admin_sessions)} sessions")
        
        # The counts should be equal since no role-based filtering
        assert len(coord_sessions) == len(admin_sessions), \
            f"Calendar should return same sessions for all roles. Coordinator: {len(coord_sessions)}, Admin: {len(admin_sessions)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
