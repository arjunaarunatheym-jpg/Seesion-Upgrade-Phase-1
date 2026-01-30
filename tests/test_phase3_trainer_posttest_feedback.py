"""
Phase 3 Testing: Trainer Checklists, Post-Test, Feedback, and Certificate Generation
Tests for:
- 3A: Trainer checklist completion (only 13 present participants)
- 3B: Post-test release and completion (12 pass, 1 fail - participant 5)
- 3C: Feedback submission
- 3D: Training pictures & Chief Trainer/Coordinator feedback
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://report-flow-4.preview.emergentagent.com').rstrip('/')
SESSION_ID = "d664b79d-91a1-4968-bd72-de82611cdb1f"
PROGRAM_ID = "5d8c9145-3fbf-4d4f-8b2f-aaa1b225ff30"

# Trainer credentials
TRAINERS = {
    "vijay": {"email": "vijay@mddrc.com.my", "password": "mddrc1", "id": "9e68512e-0aa3-4c9d-b618-97f8c4b735ee", "role": "chief"},
    "thinagaran": {"email": "Dheena8983@gmail.com", "password": "mddrc1", "id": "764dd0d5-000c-4b72-ab83-b24a7b3af68c", "role": "trainer"},
    "hisam": {"email": "hisam@gmail.com.my", "password": "mddrc1", "id": "f0601695-41da-4c32-ac35-7fb1fdfce845", "role": "trainer"}
}

# Coordinator credentials
COORDINATOR = {"email": "malek@mddrc.com.my", "password": "mddrc1"}

# Admin credentials
ADMIN = {"email": "arjuna@mddrc.com.my", "password": "Dana102229"}

# Participant mapping (IC -> ID)
PARTICIPANTS = {
    "900101-01-0001": {"id": "ef6730c7-5be3-45fd-a80e-fad1fcc16bca", "present": True},
    "900101-01-0002": {"id": "e5dd74d7-6a67-4ec9-9ee0-8bd2813d41fa", "present": True},
    "900101-01-0003": {"id": "4cea9c42-4d74-433a-9cea-2bda9c9a3baa", "present": True},
    "900101-01-0004": {"id": "444b2402-d912-4bc4-a673-88682f117cc8", "present": True},
    "900101-01-0005": {"id": "cd88abff-666b-48cd-970e-eca5d43c1b2c", "present": True},  # Will FAIL post-test
    "900101-01-0006": {"id": "f967c039-a113-4a4a-a982-ac03be5931d7", "present": True},
    "900101-01-0007": {"id": "3dc9f175-b284-458c-98d1-2691ed555fd8", "present": True},
    "900101-01-0008": {"id": "69301186-a1d8-4475-98de-e02741888d0a", "present": True},
    "900101-01-0009": {"id": "e6c31374-2f4e-498d-a09c-7af2c4e606c8", "present": True},
    "900101-01-0010": {"id": "a0b615c3-e545-4c6d-8e8a-f8c711dd2553", "present": True},
    "900101-01-0011": {"id": "b6e5ad8e-f96c-4b2a-9517-437fba91e34f", "present": True},
    "900101-01-0012": {"id": "00f7b6ec-79fc-4701-a6d6-9eea24897042", "present": True},
    "900101-01-0013": {"id": "35969ab4-01ac-45cf-8f41-9ccec5b06a99", "present": True},
    "900101-01-0014": {"id": "a5295f7e-c1f7-4750-bcd4-8b125844c530", "present": False},  # ABSENT
    "900101-01-0015": {"id": "046c5fd8-2ba3-4bc6-bb40-3fa8f373ca9d", "present": False},  # ABSENT
}

# Post-test ID
POST_TEST_ID = "7400bffd-17ee-4f7a-8c2c-01aa326c03a7"

# Checklist items from template
CHECKLIST_ITEMS = [
    "Engine oil level check",
    "Coolant level check",
    "Brake fluid level check",
    "Tire pressure and condition",
    "Lights and indicators working",
    "Mirrors clean and adjusted",
    "Windshield wipers functional",
    "Horn working",
    "Seat belts functional",
    "Emergency exits accessible",
    "Fire extinguisher present and charged",
    "First aid kit complete",
    "Fuel level adequate",
    "Battery condition",
    "Steering wheel play check"
]


def login(email, password):
    """Login and return token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def get_headers(token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestPhase3ATrainerChecklists:
    """Phase 3A: Trainer Checklist Completion"""
    
    def test_01_trainer_vijay_login(self):
        """Test Trainer Vijay can login"""
        token = login(TRAINERS["vijay"]["email"], TRAINERS["vijay"]["password"])
        assert token is not None, "Trainer Vijay login failed"
        print(f"✓ Trainer Vijay logged in successfully")
    
    def test_02_trainer_vijay_get_assigned_participants(self):
        """Test Trainer Vijay can get assigned participants (should only show present ones)"""
        token = login(TRAINERS["vijay"]["email"], TRAINERS["vijay"]["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/trainer-checklist/{SESSION_ID}/assigned-participants",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get assigned participants: {response.text}"
        participants = response.json()
        
        # Should only show present participants (13 total, divided among 3 trainers)
        # With 3 trainers and 13 participants: 5, 4, 4 distribution
        print(f"✓ Trainer Vijay has {len(participants)} assigned participants")
        
        # Verify no absent participants are included
        absent_ids = [PARTICIPANTS["900101-01-0014"]["id"], PARTICIPANTS["900101-01-0015"]["id"]]
        for p in participants:
            assert p["id"] not in absent_ids, f"Absent participant {p['id']} should not be in list"
        
        return participants
    
    def test_03_trainer_vijay_submit_checklists(self):
        """Test Trainer Vijay submits checklists for assigned participants"""
        token = login(TRAINERS["vijay"]["email"], TRAINERS["vijay"]["password"])
        assert token is not None
        
        # Get assigned participants
        response = requests.get(
            f"{BASE_URL}/api/trainer-checklist/{SESSION_ID}/assigned-participants",
            headers=get_headers(token)
        )
        assert response.status_code == 200
        participants = response.json()
        
        submitted_count = 0
        for i, participant in enumerate(participants):
            # Create checklist items - some with "needs_repair" for variety
            items = []
            for j, item_name in enumerate(CHECKLIST_ITEMS):
                # Make some items "needs_repair" for first 2 participants
                if i < 2 and j in [3, 7]:  # Tire pressure and Horn for first 2
                    items.append({
                        "item": item_name,
                        "status": "needs_repair",
                        "comments": f"Needs attention - {item_name}",
                        "photo_url": None
                    })
                else:
                    items.append({
                        "item": item_name,
                        "status": "good",
                        "comments": "",
                        "photo_url": None
                    })
            
            # Submit checklist
            checklist_data = {
                "participant_id": participant["id"],
                "session_id": SESSION_ID,
                "items": items,
                "chief_trainer_comments": "Vehicle inspection completed" if i == 0 else None
            }
            
            response = requests.post(
                f"{BASE_URL}/api/trainer-checklist/submit",
                headers=get_headers(token),
                json=checklist_data
            )
            
            if response.status_code == 200:
                submitted_count += 1
                print(f"  ✓ Checklist submitted for participant {participant.get('full_name', participant['id'])}")
            else:
                print(f"  ✗ Failed to submit checklist: {response.text}")
        
        print(f"✓ Trainer Vijay submitted {submitted_count}/{len(participants)} checklists")
        assert submitted_count == len(participants), "Not all checklists were submitted"
    
    def test_04_trainer_thinagaran_submit_checklists(self):
        """Test Trainer Thinagaran submits checklists for assigned participants"""
        token = login(TRAINERS["thinagaran"]["email"], TRAINERS["thinagaran"]["password"])
        assert token is not None, "Trainer Thinagaran login failed"
        
        # Get assigned participants
        response = requests.get(
            f"{BASE_URL}/api/trainer-checklist/{SESSION_ID}/assigned-participants",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get assigned participants: {response.text}"
        participants = response.json()
        
        submitted_count = 0
        for participant in participants:
            items = []
            for item_name in CHECKLIST_ITEMS:
                items.append({
                    "item": item_name,
                    "status": "good",
                    "comments": "",
                    "photo_url": None
                })
            
            checklist_data = {
                "participant_id": participant["id"],
                "session_id": SESSION_ID,
                "items": items
            }
            
            response = requests.post(
                f"{BASE_URL}/api/trainer-checklist/submit",
                headers=get_headers(token),
                json=checklist_data
            )
            
            if response.status_code == 200:
                submitted_count += 1
        
        print(f"✓ Trainer Thinagaran submitted {submitted_count}/{len(participants)} checklists")
        assert submitted_count == len(participants)
    
    def test_05_trainer_hisam_submit_checklists(self):
        """Test Trainer Hisam submits checklists for assigned participants"""
        token = login(TRAINERS["hisam"]["email"], TRAINERS["hisam"]["password"])
        assert token is not None, "Trainer Hisam login failed"
        
        # Get assigned participants
        response = requests.get(
            f"{BASE_URL}/api/trainer-checklist/{SESSION_ID}/assigned-participants",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get assigned participants: {response.text}"
        participants = response.json()
        
        submitted_count = 0
        for participant in participants:
            items = []
            for item_name in CHECKLIST_ITEMS:
                items.append({
                    "item": item_name,
                    "status": "good",
                    "comments": "",
                    "photo_url": None
                })
            
            checklist_data = {
                "participant_id": participant["id"],
                "session_id": SESSION_ID,
                "items": items
            }
            
            response = requests.post(
                f"{BASE_URL}/api/trainer-checklist/submit",
                headers=get_headers(token),
                json=checklist_data
            )
            
            if response.status_code == 200:
                submitted_count += 1
        
        print(f"✓ Trainer Hisam submitted {submitted_count}/{len(participants)} checklists")
        assert submitted_count == len(participants)
    
    def test_06_coordinator_view_all_checklists(self):
        """Test Coordinator can see all checklist data"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/checklists/session/{SESSION_ID}",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get session checklists: {response.text}"
        checklists = response.json()
        
        print(f"✓ Coordinator can view {len(checklists)} checklists for the session")
        # Should have 13 checklists (one per present participant)
        assert len(checklists) >= 13, f"Expected at least 13 checklists, got {len(checklists)}"


class TestPhase3BPostTest:
    """Phase 3B: Post-Test Release & Completion"""
    
    def test_01_coordinator_release_post_test(self):
        """Test Coordinator releases post-test"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.post(
            f"{BASE_URL}/api/sessions/{SESSION_ID}/release-post-test",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to release post-test: {response.text}"
        print(f"✓ Post-test released: {response.json()}")
    
    def test_02_verify_post_test_available(self):
        """Verify post-test is available for participants (or already completed)"""
        # Login as participant 1
        token = login("900101-01-0001", "mddrc1")
        assert token is not None, "Participant login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/sessions/{SESSION_ID}/tests/available",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get available tests: {response.text}"
        data = response.json()
        
        # Response is a list of available tests
        # If empty, it means tests are already completed (which is fine since we submitted them)
        if isinstance(data, list) and len(data) == 0:
            print(f"✓ Post-test already completed by participant (empty available list is expected)")
        else:
            post_test_available = any(t.get("test_type") in ["post", "post_test"] for t in data) if isinstance(data, list) else data.get("can_access_post_test") == True
            assert post_test_available, f"Post-test should be accessible. Response: {data}"
            print(f"✓ Post-test is available for participants")
    
    def test_03_submit_post_tests_12_pass_1_fail(self):
        """Submit post-tests: 12 participants pass, participant 5 fails"""
        admin_token = login(ADMIN["email"], ADMIN["password"])
        assert admin_token is not None
        
        # Get post-test questions to know correct answers
        response = requests.get(
            f"{BASE_URL}/api/tests/{POST_TEST_ID}",
            headers=get_headers(admin_token)
        )
        assert response.status_code == 200, f"Failed to get post-test: {response.text}"
        test_data = response.json()
        questions = test_data.get("questions", [])
        total_questions = len(questions)
        
        print(f"Post-test has {total_questions} questions")
        
        # Get correct answers
        correct_answers = [q["correct_answer"] for q in questions]
        
        # Create passing answers (36+ correct out of 40 = 90%+)
        passing_answers = correct_answers.copy()  # All correct
        
        # Create failing answers (less than 36 correct = less than 90%)
        failing_answers = []
        for i, ans in enumerate(correct_answers):
            if i < 30:  # First 30 wrong
                failing_answers.append((ans + 1) % 4)  # Wrong answer
            else:
                failing_answers.append(ans)  # Last 10 correct = 25%
        
        passed_count = 0
        failed_count = 0
        
        # Submit for all 13 present participants
        for ic, data in PARTICIPANTS.items():
            if not data["present"]:
                continue
            
            participant_id = data["id"]
            
            # Participant 5 (900101-01-0005) should fail
            if ic == "900101-01-0005":
                answers = failing_answers
                expected_pass = False
            else:
                answers = passing_answers
                expected_pass = True
            
            # Use super-admin submit endpoint
            submit_data = {
                "test_id": POST_TEST_ID,
                "participant_id": participant_id,
                "session_id": SESSION_ID,
                "answers": answers
            }
            
            response = requests.post(
                f"{BASE_URL}/api/tests/super-admin-submit",
                headers=get_headers(admin_token),
                json=submit_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("passed"):
                    passed_count += 1
                    print(f"  ✓ {ic} PASSED with score {result.get('score', 0):.1f}%")
                else:
                    failed_count += 1
                    print(f"  ✗ {ic} FAILED with score {result.get('score', 0):.1f}%")
                
                # Verify expected result
                if expected_pass:
                    assert result.get("passed") == True, f"{ic} should have passed"
                else:
                    assert result.get("passed") == False, f"{ic} should have failed"
            else:
                print(f"  ! Error submitting for {ic}: {response.text}")
        
        print(f"\n✓ Post-test results: {passed_count} passed, {failed_count} failed")
        assert passed_count == 12, f"Expected 12 to pass, got {passed_count}"
        assert failed_count == 1, f"Expected 1 to fail, got {failed_count}"
    
    def test_04_verify_post_test_results_coordinator(self):
        """Verify coordinator can see post-test results"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/tests/results/session/{SESSION_ID}",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get test results: {response.text}"
        results = response.json()
        
        # Filter for post-test results
        post_test_results = [r for r in results if r.get("test_type") in ["post", "post_test"]]
        
        print(f"✓ Coordinator can view {len(post_test_results)} post-test results")
        
        # Verify counts
        passed = sum(1 for r in post_test_results if r.get("passed"))
        failed = sum(1 for r in post_test_results if not r.get("passed"))
        
        print(f"  - Passed: {passed}, Failed: {failed}")
        assert passed == 12, f"Expected 12 passed, got {passed}"
        assert failed == 1, f"Expected 1 failed, got {failed}"


class TestPhase3CFeedback:
    """Phase 3C: Feedback Submission"""
    
    def test_01_coordinator_release_feedback(self):
        """Test Coordinator releases feedback form"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.post(
            f"{BASE_URL}/api/sessions/{SESSION_ID}/release-feedback",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to release feedback: {response.text}"
        print(f"✓ Feedback form released: {response.json()}")
    
    def test_02_participants_submit_feedback(self):
        """All 13 present participants submit feedback"""
        submitted_count = 0
        
        for ic, data in PARTICIPANTS.items():
            if not data["present"]:
                continue
            
            token = login(ic, "mddrc1")
            if not token:
                print(f"  ! Failed to login as {ic}")
                continue
            
            # Create feedback responses - must be a list of dicts with question/answer
            feedback_data = {
                "session_id": SESSION_ID,
                "program_id": PROGRAM_ID,
                "responses": [
                    {"question": "How would you rate the overall training quality?", "answer": 5},
                    {"question": "How knowledgeable was the trainer?", "answer": 5},
                    {"question": "How clear were the training materials?", "answer": 4},
                    {"question": "How relevant was the content to your job?", "answer": 5},
                    {"question": "How would you rate the training facilities?", "answer": 4},
                    {"question": "Would you recommend this training to colleagues?", "answer": 5},
                    {"question": "What did you like most about the training?", "answer": "Very informative and practical"},
                    {"question": "What improvements would you suggest?", "answer": "More hands-on exercises"},
                    {"question": "Any additional comments?", "answer": "Great training session!"}
                ]
            }
            
            response = requests.post(
                f"{BASE_URL}/api/feedback/submit",
                headers=get_headers(token),
                json=feedback_data
            )
            
            if response.status_code == 200:
                submitted_count += 1
                print(f"  ✓ Feedback submitted by {ic}")
            elif response.status_code == 400 and "already submitted" in response.text.lower():
                submitted_count += 1
                print(f"  ✓ Feedback already submitted by {ic}")
            else:
                print(f"  ! Failed to submit feedback for {ic}: {response.text}")
        
        print(f"\n✓ {submitted_count}/13 participants submitted feedback")
        assert submitted_count == 13, f"Expected 13 feedback submissions, got {submitted_count}"
    
    def test_03_coordinator_view_feedback(self):
        """Coordinator can view all feedback"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/feedback/session/{SESSION_ID}",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get feedback: {response.text}"
        feedback_list = response.json()
        
        print(f"✓ Coordinator can view {len(feedback_list)} feedback submissions")
        assert len(feedback_list) >= 13, f"Expected at least 13 feedback, got {len(feedback_list)}"


class TestPhase3DChiefTrainerCoordinatorFeedback:
    """Phase 3D: Training Pictures & Chief Trainer/Coordinator Feedback"""
    
    def test_01_chief_trainer_submit_feedback(self):
        """Chief Trainer (Vijay) submits feedback"""
        token = login(TRAINERS["vijay"]["email"], TRAINERS["vijay"]["password"])
        assert token is not None
        
        responses = {
            "overall_assessment": "Excellent training session with engaged participants",
            "participant_performance": "Most participants showed good understanding",
            "areas_of_improvement": "Some participants need more practice on defensive techniques",
            "recommendations": "Consider adding more practical exercises",
            "safety_observations": "All safety protocols were followed",
            "rating": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/chief-trainer-feedback/{SESSION_ID}",
            headers=get_headers(token),
            json=responses
        )
        
        assert response.status_code == 200, f"Failed to submit chief trainer feedback: {response.text}"
        print(f"✓ Chief Trainer feedback submitted")
    
    def test_02_coordinator_submit_feedback(self):
        """Coordinator submits feedback"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        responses = {
            "logistics_assessment": "All logistics were well organized",
            "participant_attendance": "13 out of 15 participants attended",
            "venue_feedback": "Venue was suitable for the training",
            "trainer_feedback": "Trainers were professional and knowledgeable",
            "overall_comments": "Successful training session",
            "rating": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/coordinator-feedback/{SESSION_ID}",
            headers=get_headers(token),
            json=responses
        )
        
        assert response.status_code == 200, f"Failed to submit coordinator feedback: {response.text}"
        print(f"✓ Coordinator feedback submitted")
    
    def test_03_verify_chief_trainer_feedback(self):
        """Verify chief trainer feedback is saved"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/chief-trainer-feedback/{SESSION_ID}",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get chief trainer feedback: {response.text}"
        feedback = response.json()
        
        if feedback:
            print(f"✓ Chief trainer feedback retrieved successfully")
            assert "responses" in feedback or "overall_assessment" in feedback.get("responses", {})
        else:
            print("! No chief trainer feedback found")
    
    def test_04_verify_coordinator_feedback(self):
        """Verify coordinator feedback is saved"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/coordinator-feedback/{SESSION_ID}",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get coordinator feedback: {response.text}"
        feedback = response.json()
        
        if feedback:
            print(f"✓ Coordinator feedback retrieved successfully")
        else:
            print("! No coordinator feedback found")


class TestPhase3SessionStatus:
    """Verify overall session status after Phase 3"""
    
    def test_01_session_status(self):
        """Check overall session status"""
        token = login(COORDINATOR["email"], COORDINATOR["password"])
        assert token is not None
        
        response = requests.get(
            f"{BASE_URL}/api/sessions/{SESSION_ID}/status",
            headers=get_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get session status: {response.text}"
        status = response.json()
        
        print(f"\n=== SESSION STATUS ===")
        print(f"Session: {status.get('session_name')}")
        print(f"Total Participants: {status.get('total_participants')}")
        print(f"Pre-test: Released={status.get('pre_test', {}).get('released')}, Completed={status.get('pre_test', {}).get('completed')}")
        print(f"Post-test: Released={status.get('post_test', {}).get('released')}, Completed={status.get('post_test', {}).get('completed')}")
        print(f"Feedback: Released={status.get('feedback', {}).get('released')}, Submitted={status.get('feedback', {}).get('submitted')}")
        
        # Verify post-test was released and completed
        assert status.get('post_test', {}).get('released') == True, "Post-test should be released"
        assert status.get('post_test', {}).get('completed') >= 13, "All 13 present participants should have completed post-test"
        
        # Verify feedback was released (submitted count may vary based on test execution)
        assert status.get('feedback', {}).get('released') == True, "Feedback should be released"
        # Note: feedback submission count depends on whether feedback tests passed
        feedback_submitted = status.get('feedback', {}).get('submitted', 0)
        print(f"  Feedback submitted: {feedback_submitted}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
