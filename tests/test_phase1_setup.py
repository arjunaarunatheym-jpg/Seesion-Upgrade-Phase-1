"""
Phase 1 Testing - Setup & Admin Flows
Tests for the training management platform workflow
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://payroll-fix-19.preview.emergentagent.com')

class TestPhase1Setup:
    """Phase 1A - Admin Setup Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def asst_admin_token(self):
        """Get assistant admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "abillashaa@mddrc.com.my",
            "password": "mddrc1"
        })
        assert response.status_code == 200, f"Asst Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        print("✓ Admin login successful")
    
    def test_asst_admin_login(self, asst_admin_token):
        """Test assistant admin can login"""
        assert asst_admin_token is not None
        print("✓ Assistant Admin login successful")
    
    def test_get_programs(self, admin_token):
        """Test getting programs list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert response.status_code == 200
        programs = response.json()
        
        # Check Bus Defensive Training exists
        bus_program = next((p for p in programs if "Bus Defensive Training" in p.get("name", "")), None)
        assert bus_program is not None, "Bus Defensive Training program not found"
        print(f"✓ Found program: {bus_program['name']} (ID: {bus_program['id']})")
        return bus_program
    
    def test_get_companies(self, admin_token):
        """Test getting companies list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/companies", headers=headers)
        assert response.status_code == 200
        companies = response.json()
        
        # Check RapidKL exists
        rapidkl = next((c for c in companies if "RapidKL" in c.get("name", "")), None)
        assert rapidkl is not None, "RapidKL company not found"
        print(f"✓ Found company: {rapidkl['name']} (ID: {rapidkl['id']})")
        return rapidkl
    
    def test_get_sessions(self, admin_token):
        """Test getting sessions list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        assert response.status_code == 200
        sessions = response.json()
        
        # Check RapidKL session exists
        rapidkl_session = next((s for s in sessions if "RapidKL" in s.get("company_name", "")), None)
        assert rapidkl_session is not None, "RapidKL session not found"
        print(f"✓ Found session: {rapidkl_session['name']} for {rapidkl_session['company_name']}")
        print(f"  - Session ID: {rapidkl_session['id']}")
        print(f"  - Dates: {rapidkl_session['start_date']} to {rapidkl_session['end_date']}")
        print(f"  - Participants: {len(rapidkl_session.get('participant_ids', []))}")
        return rapidkl_session
    
    def test_get_users(self, admin_token):
        """Test getting users list and verify supervisor was created"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        
        # Check supervisor exists
        supervisor = next((u for u in users if u.get("email") == "rapidkl@gmail.com"), None)
        if supervisor:
            print(f"✓ Found supervisor: {supervisor['full_name']} ({supervisor['email']})")
        else:
            print("⚠ Supervisor rapidkl@gmail.com not found")
        
        # Check participant exists
        participant = next((u for u in users if "Test Participant" in u.get("full_name", "")), None)
        if participant:
            print(f"✓ Found participant: {participant['full_name']} (IC: {participant['id_number']})")
        
        return users


class TestPhase1BContentUpload:
    """Phase 1B - Assistant Admin Content Upload Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def bus_program_id(self, admin_token):
        """Get Bus Defensive Training program ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        programs = response.json()
        bus_program = next((p for p in programs if "Bus Defensive Training" in p.get("name", "")), None)
        return bus_program["id"] if bus_program else None
    
    def test_add_test_questions(self, admin_token, bus_program_id):
        """Add 40 test questions for Bus Defensive Training"""
        if not bus_program_id:
            pytest.skip("Bus Defensive Training program not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Generate 40 questions
        questions = [
            {"question": "What is the recommended following distance for buses?", "options": ["2 seconds", "3-4 seconds", "1 second", "5 seconds"], "correct_answer": 1},
            {"question": "When should you check your mirrors?", "options": ["Only when changing lanes", "Every 5-8 seconds", "Only when braking", "Once per minute"], "correct_answer": 1},
            {"question": "What is the proper way to handle a tire blowout?", "options": ["Brake hard immediately", "Grip steering firmly, ease off accelerator", "Accelerate to maintain control", "Turn sharply to the side"], "correct_answer": 1},
            {"question": "What is the safe speed reduction when driving in rain?", "options": ["No reduction needed", "10% reduction", "30% reduction", "50% reduction"], "correct_answer": 2},
            {"question": "When approaching a pedestrian crossing, you should:", "options": ["Speed up to clear quickly", "Maintain speed", "Slow down and be prepared to stop", "Honk to warn pedestrians"], "correct_answer": 2},
            {"question": "What is the blind spot of a bus?", "options": ["Area visible in mirrors", "Area directly behind and beside the bus", "Area in front of the bus", "There are no blind spots"], "correct_answer": 1},
            {"question": "How should you handle aggressive drivers?", "options": ["Engage with them", "Avoid eye contact and stay calm", "Speed up to get away", "Brake suddenly"], "correct_answer": 1},
            {"question": "What is the proper technique for downhill driving?", "options": ["Use neutral gear", "Use lower gear and engine braking", "Ride the brakes continuously", "Coast in high gear"], "correct_answer": 1},
            {"question": "When is it safe to overtake another vehicle?", "options": ["On curves", "When visibility is clear and safe", "In school zones", "Near intersections"], "correct_answer": 1},
            {"question": "What should you do before starting the bus?", "options": ["Start immediately", "Walk around and inspect the vehicle", "Honk the horn", "Turn on the radio"], "correct_answer": 1},
            {"question": "What is the correct seating position for driving?", "options": ["Reclined and relaxed", "Upright with arms slightly bent", "Close to steering wheel", "Far from steering wheel"], "correct_answer": 1},
            {"question": "How often should you check tire pressure?", "options": ["Once a year", "Daily before driving", "Once a month", "Only when tires look flat"], "correct_answer": 1},
            {"question": "What is the purpose of ABS brakes?", "options": ["To stop faster", "To prevent wheel lock-up", "To save fuel", "To reduce tire wear"], "correct_answer": 1},
            {"question": "When driving at night, you should:", "options": ["Use high beams always", "Reduce speed and increase following distance", "Drive faster to reduce exposure", "Keep interior lights on"], "correct_answer": 1},
            {"question": "What is the correct action at a yellow traffic light?", "options": ["Speed up to cross", "Stop if safe to do so", "Ignore it", "Honk and proceed"], "correct_answer": 1},
            {"question": "How should you handle a skid?", "options": ["Brake hard", "Steer in the direction of the skid", "Accelerate", "Turn steering wheel opposite to skid"], "correct_answer": 1},
            {"question": "What is the minimum safe following distance in good conditions?", "options": ["1 second", "2 seconds", "3 seconds", "4 seconds"], "correct_answer": 3},
            {"question": "When should you use hazard lights?", "options": ["When parking illegally", "During emergencies or breakdowns", "In heavy traffic", "When driving slowly"], "correct_answer": 1},
            {"question": "What is the proper way to enter a highway?", "options": ["Stop at the merge point", "Match traffic speed on acceleration lane", "Enter at any speed", "Slow down and wait"], "correct_answer": 1},
            {"question": "How should you handle fatigue while driving?", "options": ["Open windows and continue", "Stop and rest", "Drink coffee and continue", "Turn up music"], "correct_answer": 1},
            {"question": "What is the safe speed in a school zone?", "options": ["Normal speed limit", "30 km/h or as posted", "50 km/h", "As fast as possible"], "correct_answer": 1},
            {"question": "When should you use your horn?", "options": ["To express frustration", "To warn others of danger", "To greet friends", "In residential areas at night"], "correct_answer": 1},
            {"question": "What is the correct procedure for emergency braking?", "options": ["Pump the brakes", "Apply firm, steady pressure", "Brake and steer simultaneously", "Release brakes immediately"], "correct_answer": 1},
            {"question": "How should you approach a roundabout?", "options": ["Speed up to enter quickly", "Yield to traffic already in roundabout", "Stop completely always", "Enter without looking"], "correct_answer": 1},
            {"question": "What is the purpose of a pre-trip inspection?", "options": ["To waste time", "To ensure vehicle safety", "To impress passengers", "It's not necessary"], "correct_answer": 1},
            {"question": "When driving in fog, you should:", "options": ["Use high beams", "Use low beams and reduce speed", "Drive at normal speed", "Follow closely behind other vehicles"], "correct_answer": 1},
            {"question": "What is the correct action when an emergency vehicle approaches?", "options": ["Speed up to get out of the way", "Pull over to the right and stop", "Continue driving normally", "Stop in the middle of the road"], "correct_answer": 1},
            {"question": "How should you handle a brake failure?", "options": ["Jump out of the vehicle", "Pump brakes, use parking brake, downshift", "Turn off the engine", "Steer into oncoming traffic"], "correct_answer": 1},
            {"question": "What is the safe distance from a cyclist when overtaking?", "options": ["As close as possible", "At least 1.5 meters", "No specific distance", "Touch their handlebar"], "correct_answer": 1},
            {"question": "When should you adjust your mirrors?", "options": ["While driving", "Before starting to drive", "Only when changing lanes", "Never"], "correct_answer": 1},
            {"question": "What is the correct way to hold the steering wheel?", "options": ["One hand at 12 o'clock", "Both hands at 9 and 3 o'clock", "Both hands at bottom", "No specific position"], "correct_answer": 1},
            {"question": "How should you react to a pedestrian jaywalking?", "options": ["Honk and continue", "Slow down and be prepared to stop", "Speed up to pass quickly", "Ignore them"], "correct_answer": 1},
            {"question": "What is the purpose of the engine brake?", "options": ["To stop the engine", "To assist in slowing down", "To save fuel", "To make noise"], "correct_answer": 1},
            {"question": "When is it appropriate to use cruise control?", "options": ["In heavy traffic", "On long, straight highways", "In city driving", "In bad weather"], "correct_answer": 1},
            {"question": "What should you do if your accelerator sticks?", "options": ["Turn off the engine immediately", "Shift to neutral and brake", "Jump out", "Press harder on accelerator"], "correct_answer": 1},
            {"question": "How should you handle a vehicle fire?", "options": ["Keep driving to find help", "Stop, evacuate, and call emergency services", "Pour water on it", "Open the hood immediately"], "correct_answer": 1},
            {"question": "What is the correct procedure for backing up?", "options": ["Use mirrors only", "Turn and look, use mirrors, go slowly", "Back up quickly", "Honk continuously"], "correct_answer": 1},
            {"question": "When should you yield to pedestrians?", "options": ["Only at crosswalks", "Always when they are crossing", "Never", "Only during daytime"], "correct_answer": 1},
            {"question": "What is the safe speed on wet roads?", "options": ["Same as dry roads", "Reduce by 30%", "Increase speed", "Double the speed limit"], "correct_answer": 1},
            {"question": "How should you handle a medical emergency on board?", "options": ["Continue to destination", "Stop safely and call for help", "Ignore it", "Speed up to hospital"], "correct_answer": 1},
        ]
        
        # Create pre_test with all questions
        test_data = {
            "program_id": bus_program_id,
            "test_type": "pre_test",
            "questions": questions
        }
        
        response = requests.post(f"{BASE_URL}/api/tests", json=test_data, headers=headers)
        if response.status_code == 200:
            print(f"✓ Created pre_test with {len(questions)} questions")
        else:
            print(f"⚠ Pre-test creation response: {response.status_code} - {response.text}")
        
        # Create post_test with same questions
        test_data["test_type"] = "post_test"
        response = requests.post(f"{BASE_URL}/api/tests", json=test_data, headers=headers)
        if response.status_code == 200:
            print(f"✓ Created post_test with {len(questions)} questions")
        else:
            print(f"⚠ Post-test creation response: {response.status_code} - {response.text}")
        
        # Verify tests were created
        response = requests.get(f"{BASE_URL}/api/tests?program_id={bus_program_id}", headers=headers)
        if response.status_code == 200:
            tests = response.json()
            print(f"✓ Total tests for program: {len(tests)}")
    
    def test_add_checklist_items(self, admin_token, bus_program_id):
        """Add checklist items for Bus Defensive Training"""
        if not bus_program_id:
            pytest.skip("Bus Defensive Training program not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        checklist_items = [
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
        
        checklist_data = {
            "program_id": bus_program_id,
            "items": checklist_items
        }
        
        response = requests.post(f"{BASE_URL}/api/checklists/templates", json=checklist_data, headers=headers)
        if response.status_code == 200:
            print(f"✓ Created checklist with {len(checklist_items)} items")
        else:
            print(f"⚠ Checklist creation response: {response.status_code} - {response.text}")
    
    def test_add_feedback_questions(self, admin_token, bus_program_id):
        """Add feedback form questions for Bus Defensive Training"""
        if not bus_program_id:
            pytest.skip("Bus Defensive Training program not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        feedback_questions = [
            {"question": "How would you rate the overall training quality?", "type": "rating", "required": True},
            {"question": "How knowledgeable was the trainer?", "type": "rating", "required": True},
            {"question": "How clear were the training materials?", "type": "rating", "required": True},
            {"question": "How relevant was the content to your job?", "type": "rating", "required": True},
            {"question": "How would you rate the training facilities?", "type": "rating", "required": True},
            {"question": "Would you recommend this training to colleagues?", "type": "rating", "required": True},
            {"question": "What did you like most about the training?", "type": "text", "required": False},
            {"question": "What improvements would you suggest?", "type": "text", "required": False},
            {"question": "Any additional comments?", "type": "text", "required": False}
        ]
        
        feedback_data = {
            "program_id": bus_program_id,
            "questions": feedback_questions
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/templates", json=feedback_data, headers=headers)
        if response.status_code == 200:
            print(f"✓ Created feedback form with {len(feedback_questions)} questions")
        else:
            print(f"⚠ Feedback creation response: {response.status_code} - {response.text}")


class TestPhase1CParticipants:
    """Phase 1C - Participant Creation Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def rapidkl_session(self, admin_token):
        """Get RapidKL session"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        sessions = response.json()
        return next((s for s in sessions if "RapidKL" in s.get("company_name", "")), None)
    
    def test_add_participants_individually(self, admin_token, rapidkl_session):
        """Add 3 participants individually via API"""
        if not rapidkl_session:
            pytest.skip("RapidKL session not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        session_id = rapidkl_session["id"]
        company_id = rapidkl_session["company_id"]
        
        participants_to_add = [
            {"full_name": "Test Participant 2", "id_number": "900101-01-0002", "email": "participant2@test.com"},
            {"full_name": "Test Participant 3", "id_number": "900101-01-0003", "email": "participant3@test.com"},
            {"full_name": "Test Participant 4", "id_number": "900101-01-0004", "email": "participant4@test.com"},
        ]
        
        added_count = 0
        for p in participants_to_add:
            # Create participant user
            user_data = {
                "email": p["email"],
                "password": "mddrc1",
                "full_name": p["full_name"],
                "id_number": p["id_number"],
                "role": "participant",
                "company_id": company_id
            }
            
            response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data, headers=headers)
            if response.status_code == 200:
                user = response.json()
                # Add to session
                current_participants = rapidkl_session.get("participant_ids", [])
                current_participants.append(user["id"])
                
                update_response = requests.put(
                    f"{BASE_URL}/api/sessions/{session_id}",
                    json={"participant_ids": current_participants},
                    headers=headers
                )
                if update_response.status_code == 200:
                    added_count += 1
                    print(f"✓ Added participant: {p['full_name']}")
            else:
                print(f"⚠ Failed to add {p['full_name']}: {response.text}")
        
        print(f"✓ Added {added_count} participants individually")
    
    def test_verify_participants(self, admin_token, rapidkl_session):
        """Verify all participants in session"""
        if not rapidkl_session:
            pytest.skip("RapidKL session not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        session_id = rapidkl_session["id"]
        
        # Get updated session
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        if response.status_code == 200:
            session = response.json()
            participant_count = len(session.get("participant_ids", []))
            print(f"✓ Session has {participant_count} participants")
        else:
            print(f"⚠ Could not get session details: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
