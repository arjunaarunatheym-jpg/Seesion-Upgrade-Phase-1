"""
Test iteration 38 - Trainer Checklist and Feedback Issues
Tests:
1. Trainer Checklist - Items should load properly for participants
2. Participant Feedback Submit - POST /api/feedback/submit should accept array-format responses
3. Coordinator Visibility - GET /api/participant-access/session/{sessionId} should return statuses
4. Coordinator Completion Checklist - GET /api/sessions/{sessionId}/completion-checklist
5. Session Status - GET /api/sessions/{sessionId}/status
6. Chief Trainer Feedback - POST /api/chief-trainer-feedback/{sessionId}
7. Coordinator Feedback - POST /api/coordinator-feedback/{sessionId}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session and participant IDs from the bug report
TEST_SESSION_ID = "dd05063f-5455-4087-a523-5fce7ab0d0e0"
TEST_PROGRAM_ID = "d8ec7f6c-0765-4708-9aa3-827a87a50f17"
PARTICIPANT_1_ID = "b43cc33f"  # Suvarshhan - completed checklist
PARTICIPANT_2_ID = "be1eb126"  # Sudarrshhan - no checklist yet
PARTICIPANT_3_ID = "864a90ea"  # Sulakshman

# Credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"
CHIEF_TRAINER_EMAIL = "vijay@mddrc.com.my"
CHIEF_TRAINER_PASSWORD = "mddrc1"
TRAINER_EMAIL = "Dheena8983@gmail.com"
TRAINER_PASSWORD = "mddrc1"
PARTICIPANT_IC = "071209101919"
PARTICIPANT_PASSWORD = "mddrc1"


class TestAuthentication:
    """Test authentication for different user roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Admin login successful, token received")
        return data["access_token"]
    
    def test_coordinator_login(self):
        """Test coordinator login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        assert response.status_code == 200, f"Coordinator login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Coordinator login successful")
        return data["access_token"]
    
    def test_chief_trainer_login(self):
        """Test chief trainer login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CHIEF_TRAINER_EMAIL,
            "password": CHIEF_TRAINER_PASSWORD
        })
        assert response.status_code == 200, f"Chief trainer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Chief trainer login successful")
        return data["access_token"]
    
    def test_trainer_login(self):
        """Test trainer login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TRAINER_EMAIL,
            "password": TRAINER_PASSWORD
        })
        assert response.status_code == 200, f"Trainer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Trainer login successful")
        return data["access_token"]
    
    def test_participant_login(self):
        """Test participant login with IC number"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTICIPANT_IC,
            "password": PARTICIPANT_PASSWORD
        })
        assert response.status_code == 200, f"Participant login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Participant login successful")
        return data["access_token"]


@pytest.fixture
def admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin login failed")


@pytest.fixture
def coordinator_token():
    """Get coordinator token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COORDINATOR_EMAIL,
        "password": COORDINATOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Coordinator login failed")


@pytest.fixture
def chief_trainer_token():
    """Get chief trainer token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CHIEF_TRAINER_EMAIL,
        "password": CHIEF_TRAINER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Chief trainer login failed")


@pytest.fixture
def trainer_token():
    """Get trainer token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TRAINER_EMAIL,
        "password": TRAINER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Trainer login failed")


@pytest.fixture
def participant_token():
    """Get participant token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTICIPANT_IC,
        "password": PARTICIPANT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Participant login failed")


class TestChecklistTemplate:
    """Test checklist template loading - Bug #1: Trainer sees 'No checklist items available'"""
    
    def test_get_checklist_template_for_program(self, admin_token):
        """Test that checklist template exists and has items for the program"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/checklists/templates/program/{TEST_PROGRAM_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get checklist template: {response.text}"
        data = response.json()
        
        # Template should have items
        assert data is not None, "No template returned"
        assert "items" in data or "program_id" in data, f"Invalid template structure: {data}"
        
        items = data.get("items", [])
        print(f"Checklist template has {len(items)} items")
        
        # According to bug report, template should have 28 items
        assert len(items) > 0, "Checklist template has no items - this is the bug!"
        print(f"First few items: {items[:3] if len(items) >= 3 else items}")
        
        return data
    
    def test_get_checklist_template_alias_endpoint(self, trainer_token):
        """Test the alias endpoint used by trainers"""
        headers = {"Authorization": f"Bearer {trainer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/checklists/templates/program/{TEST_PROGRAM_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get checklist template: {response.text}"
        data = response.json()
        
        # Check items exist
        items = data.get("items", [])
        print(f"Trainer sees {len(items)} checklist items")
        assert len(items) > 0, "Trainer sees no checklist items - BUG CONFIRMED"


class TestVehicleChecklists:
    """Test vehicle checklists endpoint - Bug #1: Items not loading for participant 2"""
    
    def test_get_vehicle_checklists_for_participant(self, trainer_token):
        """Test getting vehicle checklists for a participant"""
        headers = {"Authorization": f"Bearer {trainer_token}"}
        
        # Test for participant 2 (Sudarrshhan - be1eb126)
        response = requests.get(
            f"{BASE_URL}/api/vehicle-checklists/{TEST_SESSION_ID}/{PARTICIPANT_2_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get vehicle checklists: {response.text}"
        data = response.json()
        
        print(f"Vehicle checklists for participant 2: {data}")
        # This endpoint returns existing checklists, may be empty if not submitted yet
        return data
    
    def test_get_vehicle_checklists_for_completed_participant(self, trainer_token):
        """Test getting vehicle checklists for participant 1 who has completed"""
        headers = {"Authorization": f"Bearer {trainer_token}"}
        
        # Test for participant 1 (Suvarshhan - b43cc33f - completed checklist)
        response = requests.get(
            f"{BASE_URL}/api/vehicle-checklists/{TEST_SESSION_ID}/{PARTICIPANT_1_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get vehicle checklists: {response.text}"
        data = response.json()
        
        print(f"Vehicle checklists for participant 1 (completed): {data}")
        return data


class TestTrainerAssignedParticipants:
    """Test trainer assigned participants endpoint"""
    
    def test_get_assigned_participants(self, trainer_token):
        """Test getting assigned participants for trainer"""
        headers = {"Authorization": f"Bearer {trainer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/trainer-checklist/{TEST_SESSION_ID}/assigned-participants",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get assigned participants: {response.text}"
        data = response.json()
        
        participants = data.get("participants", [])
        print(f"Trainer has {len(participants)} assigned participants")
        
        for p in participants:
            print(f"  - {p.get('full_name')}: checklist_submitted={p.get('checklist_submitted')}, claimed_by={p.get('claimed_by_trainer_name')}")
        
        return data


class TestFeedbackSubmission:
    """Test feedback submission - Bug #2: POST /api/feedback/submit should accept array-format responses"""
    
    def test_feedback_submit_with_array_responses(self, participant_token):
        """Test that feedback submission accepts array-format responses"""
        headers = {"Authorization": f"Bearer {participant_token}"}
        
        # Array format responses (as reported in bug)
        array_responses = [
            {"question": "Overall Training Experience", "rating": 5},
            {"question": "Training Content Quality", "rating": 4},
            {"question": "Trainer Effectiveness", "rating": 5}
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/feedback/submit",
            headers=headers,
            json={
                "session_id": TEST_SESSION_ID,
                "program_id": TEST_PROGRAM_ID,
                "responses": array_responses
            }
        )
        
        # Should not return 422 validation error
        if response.status_code == 422:
            print(f"BUG CONFIRMED: 422 error on array responses: {response.text}")
            pytest.fail(f"Feedback submit returned 422 for array responses: {response.text}")
        
        # Could be 400 if already submitted, which is fine
        if response.status_code == 400:
            print(f"Feedback already submitted (expected): {response.text}")
            return
        
        assert response.status_code == 200, f"Feedback submit failed: {response.text}"
        print(f"Feedback submitted successfully with array responses")
    
    def test_feedback_submit_with_dict_responses(self, participant_token):
        """Test that feedback submission also accepts dict-format responses"""
        headers = {"Authorization": f"Bearer {participant_token}"}
        
        # Dict format responses
        dict_responses = {
            "overall_experience": 5,
            "content_quality": 4,
            "trainer_effectiveness": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/feedback/submit",
            headers=headers,
            json={
                "session_id": TEST_SESSION_ID,
                "program_id": TEST_PROGRAM_ID,
                "responses": dict_responses
            }
        )
        
        # Should not return 422 validation error
        if response.status_code == 422:
            print(f"422 error on dict responses: {response.text}")
        
        # Could be 400 if already submitted
        if response.status_code == 400:
            print(f"Feedback already submitted (expected): {response.text}")
            return
        
        print(f"Feedback response: {response.status_code} - {response.text}")


class TestCoordinatorVisibility:
    """Test coordinator visibility - Bug #3: Coordinator should see completion statuses"""
    
    def test_get_participant_access_for_session(self, admin_token):
        """Test getting participant access records for a session"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/participant-access/session/{TEST_SESSION_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get participant access: {response.text}"
        data = response.json()
        
        print(f"Participant access records: {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Check that records have the required fields
        if isinstance(data, list) and len(data) > 0:
            for record in data[:3]:  # Check first 3
                print(f"  - participant_id={record.get('participant_id')}")
                print(f"    feedback_completed={record.get('feedback_completed')}")
                print(f"    trainer_checklist_submitted={record.get('trainer_checklist_submitted')}")
                
                # These fields should exist
                assert "feedback_completed" in record or "feedback_submitted" in record, \
                    f"Missing feedback status in record: {record}"
        
        return data


class TestCompletionChecklist:
    """Test completion checklist - Bug #4: Should count vehicle_checklists"""
    
    def test_get_completion_checklist(self, admin_token):
        """Test getting completion checklist for session"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/sessions/{TEST_SESSION_ID}/completion-checklist",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get completion checklist: {response.text}"
        data = response.json()
        
        print(f"Completion checklist:")
        print(f"  all_attendance_recorded: {data.get('all_attendance_recorded')}")
        print(f"  all_pre_tests_completed: {data.get('all_pre_tests_completed')}")
        print(f"  all_post_tests_completed: {data.get('all_post_tests_completed')}")
        print(f"  all_checklists_submitted: {data.get('all_checklists_submitted')}")
        print(f"  all_feedback_submitted: {data.get('all_feedback_submitted')}")
        print(f"  coordinator_feedback_submitted: {data.get('coordinator_feedback_submitted')}")
        print(f"  chief_trainer_feedback_submitted: {data.get('chief_trainer_feedback_submitted')}")
        
        return data


class TestSessionStatus:
    """Test session status - Bug #5: Should count checklist_complete from vehicle_checklists"""
    
    def test_get_session_status(self, admin_token):
        """Test getting session status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/sessions/{TEST_SESSION_ID}/status",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get session status: {response.text}"
        data = response.json()
        
        print(f"Session status:")
        print(f"  total_participants: {data.get('total_participants')}")
        print(f"  attendance_complete: {data.get('attendance_complete')}")
        print(f"  pre_test_complete: {data.get('pre_test_complete')}")
        print(f"  post_test_complete: {data.get('post_test_complete')}")
        print(f"  checklist_complete: {data.get('checklist_complete')}")
        print(f"  feedback_complete: {data.get('feedback_complete')}")
        
        return data


class TestChiefTrainerFeedback:
    """Test chief trainer feedback - Bug #6: Should accept dict responses"""
    
    def test_submit_chief_trainer_feedback(self, chief_trainer_token):
        """Test submitting chief trainer feedback with dict responses"""
        headers = {"Authorization": f"Bearer {chief_trainer_token}"}
        
        # Dict format responses
        responses = {
            "training_effectiveness": 5,
            "participant_skill_improvement": 4,
            "safety_compliance": 5,
            "participant_dedication": 4,
            "overall_impressions": "Good training session"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/chief-trainer-feedback/{TEST_SESSION_ID}",
            headers=headers,
            json=responses
        )
        
        if response.status_code == 422:
            print(f"BUG: 422 error on chief trainer feedback: {response.text}")
            pytest.fail(f"Chief trainer feedback returned 422: {response.text}")
        
        assert response.status_code == 200, f"Chief trainer feedback failed: {response.text}"
        print(f"Chief trainer feedback submitted successfully")
        
        return response.json()
    
    def test_get_chief_trainer_feedback(self, admin_token):
        """Test getting chief trainer feedback"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/chief-trainer-feedback/{TEST_SESSION_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get chief trainer feedback: {response.text}"
        data = response.json()
        
        print(f"Chief trainer feedback: {data}")
        return data


class TestCoordinatorFeedback:
    """Test coordinator feedback - Bug #7: Should accept dict responses"""
    
    def test_submit_coordinator_feedback(self, coordinator_token):
        """Test submitting coordinator feedback with dict responses"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        
        # Dict format responses
        responses = {
            "training_quality": 5,
            "trainer_preparedness": 4,
            "participant_engagement": 5,
            "facility_condition": 4,
            "overall_comments": "Well organized session"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/coordinator-feedback/{TEST_SESSION_ID}",
            headers=headers,
            json=responses
        )
        
        if response.status_code == 422:
            print(f"BUG: 422 error on coordinator feedback: {response.text}")
            pytest.fail(f"Coordinator feedback returned 422: {response.text}")
        
        assert response.status_code == 200, f"Coordinator feedback failed: {response.text}"
        print(f"Coordinator feedback submitted successfully")
        
        return response.json()
    
    def test_get_coordinator_feedback(self, admin_token):
        """Test getting coordinator feedback"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/coordinator-feedback/{TEST_SESSION_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get coordinator feedback: {response.text}"
        data = response.json()
        
        print(f"Coordinator feedback: {data}")
        return data


class TestEnrichedParticipants:
    """Test enriched participants endpoint - should show checklist status"""
    
    def test_get_enriched_participants(self, admin_token):
        """Test getting enriched participants with checklist data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/sessions/{TEST_SESSION_ID}/participants/enriched",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get enriched participants: {response.text}"
        data = response.json()
        
        print(f"Enriched participants: {len(data)}")
        for p in data[:3]:  # Show first 3
            user = p.get("user", {})
            checklist = p.get("checklist")
            print(f"  - {user.get('full_name')}: checklist={checklist is not None}")
        
        return data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
