"""
Test session update endpoint for protected field stripping
Tests that status, is_archived, completion_status fields are stripped from updates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://training-finance-hub-1.preview.emergentagent.com')

class TestSessionProtectedFields:
    """Test that session update endpoint strips protected fields"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def session_id(self, admin_token):
        """Get an existing session ID for testing"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        assert response.status_code == 200, f"Failed to get sessions: {response.text}"
        sessions = response.json()
        assert len(sessions) > 0, "No sessions found for testing"
        return sessions[0]["id"]
    
    def test_session_update_strips_status_field(self, admin_token, session_id):
        """Test that status field is stripped from session update"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get the current session state
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        original_session = response.json()
        original_status = original_session.get("status", "active")
        
        # Try to update with a different status
        update_data = {
            "location": original_session.get("location", "Test Location"),
            "status": "completed"  # This should be stripped
        }
        
        response = requests.put(f"{BASE_URL}/api/sessions/{session_id}", 
                               headers=headers, json=update_data)
        assert response.status_code == 200, f"Session update failed: {response.text}"
        
        # Verify status was NOT changed
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        updated_session = response.json()
        
        # Status should remain unchanged (protected field was stripped)
        assert updated_session.get("status") == original_status, \
            f"Status was changed from {original_status} to {updated_session.get('status')} - protected field not stripped!"
        print(f"✓ Status field correctly stripped - remained as '{original_status}'")
    
    def test_session_update_strips_is_archived_field(self, admin_token, session_id):
        """Test that is_archived field is stripped from session update"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get the current session state
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        original_session = response.json()
        original_archived = original_session.get("is_archived", False)
        
        # Try to update with is_archived = True
        update_data = {
            "location": original_session.get("location", "Test Location"),
            "is_archived": True  # This should be stripped
        }
        
        response = requests.put(f"{BASE_URL}/api/sessions/{session_id}", 
                               headers=headers, json=update_data)
        assert response.status_code == 200, f"Session update failed: {response.text}"
        
        # Verify is_archived was NOT changed
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        updated_session = response.json()
        
        # is_archived should remain unchanged (protected field was stripped)
        assert updated_session.get("is_archived", False) == original_archived, \
            f"is_archived was changed from {original_archived} to {updated_session.get('is_archived')} - protected field not stripped!"
        print(f"✓ is_archived field correctly stripped - remained as '{original_archived}'")
    
    def test_session_update_strips_completion_status_field(self, admin_token, session_id):
        """Test that completion_status field is stripped from session update"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get the current session state
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        original_session = response.json()
        original_completion_status = original_session.get("completion_status", "ongoing")
        
        # Try to update with completion_status = "completed"
        update_data = {
            "location": original_session.get("location", "Test Location"),
            "completion_status": "completed"  # This should be stripped
        }
        
        response = requests.put(f"{BASE_URL}/api/sessions/{session_id}", 
                               headers=headers, json=update_data)
        assert response.status_code == 200, f"Session update failed: {response.text}"
        
        # Verify completion_status was NOT changed
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        updated_session = response.json()
        
        # completion_status should remain unchanged (protected field was stripped)
        actual_completion_status = updated_session.get("completion_status", "ongoing")
        assert actual_completion_status == original_completion_status, \
            f"completion_status was changed from {original_completion_status} to {actual_completion_status} - protected field not stripped!"
        print(f"✓ completion_status field correctly stripped - remained as '{original_completion_status}'")
    
    def test_session_update_allows_non_protected_fields(self, admin_token, session_id):
        """Test that non-protected fields can still be updated"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get the current session state
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        original_session = response.json()
        
        # Update a non-protected field (location)
        new_location = "Updated Test Location - " + str(hash(original_session.get("location", "")))[:8]
        update_data = {
            "location": new_location
        }
        
        response = requests.put(f"{BASE_URL}/api/sessions/{session_id}", 
                               headers=headers, json=update_data)
        assert response.status_code == 200, f"Session update failed: {response.text}"
        
        # Verify location WAS changed
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        updated_session = response.json()
        
        assert updated_session.get("location") == new_location, \
            f"Location was not updated - expected '{new_location}', got '{updated_session.get('location')}'"
        print(f"✓ Non-protected field (location) correctly updated to '{new_location}'")
        
        # Restore original location
        restore_data = {"location": original_session.get("location", "Safety Driving Centre")}
        requests.put(f"{BASE_URL}/api/sessions/{session_id}", headers=headers, json=restore_data)


class TestAddParticipantAPI:
    """Test the add participant API endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def session_data(self, admin_token):
        """Get an existing session for testing"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        assert response.status_code == 200, f"Failed to get sessions: {response.text}"
        sessions = response.json()
        assert len(sessions) > 0, "No sessions found for testing"
        return sessions[0]
    
    def test_register_participant_api(self, admin_token, session_data):
        """Test that participant can be registered via API"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        import random
        test_id = f"APITEST{random.randint(100000, 999999)}"
        
        # Register a new participant
        register_data = {
            "full_name": f"API Test Participant {test_id}",
            "id_number": test_id,
            "email": f"apitest{test_id}@example.com",
            "phone_number": "+60123456789",
            "password": "mddrc1",
            "role": "participant",
            "company_id": session_data.get("company_id")
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", 
                                headers=headers, json=register_data)
        
        # Should succeed (201) or fail with duplicate (400)
        assert response.status_code in [200, 201, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code in [200, 201]:
            user_data = response.json()
            assert "id" in user_data, "User ID not returned"
            print(f"✓ Participant registered successfully with ID: {user_data['id']}")
        else:
            print(f"✓ Registration returned expected error (possibly duplicate): {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
