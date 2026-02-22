#!/usr/bin/env python3
"""
Submit pre-tests for participants 1-13
- Participants 1-10: FAIL (answer 30-34 correctly)
- Participants 11-13: PASS (answer 36+ correctly)
"""

import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-command-center-16.preview.emergentagent.com').rstrip('/')
SESSION_ID = "d664b79d-91a1-4968-bd72-de82611cdb1f"
TEST_ID = "f3cb5358-41fe-4d7a-8e44-deefa85e5f5f"
PASSWORD = "mddrc1"

# Correct answers for the test
CORRECT_ANSWERS = [1,1,1,2,2,1,1,1,1,1,1,1,1,1,1,1,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

def get_wrong_answer(correct):
    """Get a wrong answer"""
    return (correct + 1) % 4

def submit_test(ic, correct_count):
    """Submit test for a participant with specified number of correct answers"""
    # Login
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ic,
        "password": PASSWORD
    })
    
    if login_response.status_code != 200:
        print(f"✗ {ic} - Login failed: {login_response.text}")
        return None
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if test already completed
    access_response = requests.get(f"{BASE_URL}/api/participant-access/session/{SESSION_ID}", headers=headers)
    
    # Generate answers
    answers = []
    for i, correct in enumerate(CORRECT_ANSWERS):
        if i < correct_count:
            answers.append(correct)  # Correct answer
        else:
            answers.append(get_wrong_answer(correct))  # Wrong answer
    
    # Submit test
    submit_data = {
        "test_id": TEST_ID,
        "session_id": SESSION_ID,
        "answers": answers
    }
    
    response = requests.post(f"{BASE_URL}/api/tests/submit", json=submit_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        status = "PASS" if result["passed"] else "FAIL"
        print(f"✓ {ic} - {status} ({result['score']:.1f}%, {result['correct_answers']}/{result['total_questions']})")
        return result
    elif "already" in response.text.lower():
        print(f"✓ {ic} - Already completed")
        return {"already_completed": True}
    else:
        print(f"✗ {ic} - Submit failed: {response.text}")
        return None

def main():
    print("="*60)
    print("SUBMITTING PRE-TESTS FOR PARTICIPANTS")
    print("="*60)
    
    results = {
        "passed": [],
        "failed": [],
        "errors": []
    }
    
    # Participants 1-10: FAIL (30-34 correct)
    for i in range(1, 11):
        ic = f"900101-01-{str(i).zfill(4)}"
        correct_count = 30 + (i % 5)  # 30, 31, 32, 33, 34
        result = submit_test(ic, correct_count)
        
        if result:
            if result.get("already_completed"):
                continue
            if result.get("passed"):
                results["passed"].append(ic)
            else:
                results["failed"].append(ic)
        else:
            results["errors"].append(ic)
    
    # Participants 11-13: PASS (36+ correct)
    for i in range(11, 14):
        ic = f"900101-01-{str(i).zfill(4)}"
        correct_count = 36 + (i - 11)  # 36, 37, 38
        result = submit_test(ic, correct_count)
        
        if result:
            if result.get("already_completed"):
                continue
            if result.get("passed"):
                results["passed"].append(ic)
            else:
                results["failed"].append(ic)
        else:
            results["errors"].append(ic)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Errors: {len(results['errors'])}")
    
    return results

if __name__ == "__main__":
    main()
