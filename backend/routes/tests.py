"""
Tests routes - Test management and submission
Endpoints: 11
- POST /tests
- GET /tests/program/{program_id}
- DELETE /tests/{test_id}
- POST /tests/bulk-upload
- GET /tests/{test_id}
- POST /tests/submit
- GET /tests/results/participant/{participant_id}
- PUT /tests/results/{result_id}
- POST /tests/super-admin-submit
- GET /tests/results/session/{session_id}
- GET /tests/results/{result_id}
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List
from datetime import datetime, timezone
import random
import uuid

from core import db, get_current_user, get_malaysia_time, get_or_create_participant_access
from models import User

# Import models from server.py (these still exist there)
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Test models
class TestQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int

class Test(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    test_type: str
    questions: List[TestQuestion] = []
    created_at: datetime = Field(default_factory=get_malaysia_time)

class TestCreate(BaseModel):
    program_id: str
    test_type: str
    questions: List[TestQuestion]

class TestResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    test_id: str
    participant_id: str
    session_id: str
    test_type: str
    answers: List[int] = []
    score: float = 0.0
    total_questions: int = 0
    correct_answers: int = 0
    passed: bool = False
    submitted_at: datetime = Field(default_factory=get_malaysia_time)
    question_indices: Optional[List[int]] = None

class TestSubmit(BaseModel):
    test_id: str
    session_id: str
    answers: List[int]
    question_indices: Optional[List[int]] = None

class SuperAdminTestSubmit(BaseModel):
    test_id: str
    session_id: str
    participant_id: str
    answers: List[int]

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=Test)
async def create_test(test_data: TestCreate, current_user: User = Depends(get_current_user)):
    """Create a new test"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create tests")
    
    test_obj = Test(**test_data.model_dump())
    doc = test_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.tests.insert_one(doc)
    return test_obj


@router.get("/program/{program_id}", response_model=List[Test])
async def get_tests_by_program(program_id: str, current_user: User = Depends(get_current_user)):
    """Get all tests for a program"""
    tests = await db.tests.find({"program_id": program_id}, {"_id": 0}).to_list(100)
    for test in tests:
        if isinstance(test.get('created_at'), str):
            test['created_at'] = datetime.fromisoformat(test['created_at'])
    return tests


@router.delete("/{test_id}")
async def delete_test(test_id: str, current_user: User = Depends(get_current_user)):
    """Delete a test"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete tests")
    
    result = await db.tests.delete_one({"id": test_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {"message": "Test deleted successfully"}


@router.post("/bulk-upload")
async def bulk_upload_test_questions(
    file: UploadFile = File(...),
    program_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload test questions from Excel file"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")
    
    try:
        import pandas as pd
        import io
        
        contents = await file.read()
        
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
        df.columns = df.columns.str.strip()
        use_simplified_format = program_id is not None
        
        if use_simplified_format:
            program = await db.programs.find_one({"id": program_id}, {"_id": 0})
            if not program:
                raise HTTPException(status_code=404, detail="Program not found")
            
            column_mappings = {
                'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
                'Option A': ['Option A', 'OPTION A', 'A'],
                'Option B': ['Option B', 'OPTION B', 'B'],
                'Option C': ['Option C', 'OPTION C', 'C'],
                'Option D': ['Option D', 'OPTION D', 'D'],
                'Correct Answer': ['Correct Answer', 'CORRECT ANSWER', 'Answer', 'ANSWER', 'Correct'],
                'Points': ['Points', 'POINTS', 'Score', 'SCORE']
            }
        else:
            column_mappings = {
                'Program Name': ['Program Name', 'PROGRAM NAME', 'Program', 'PROGRAM'],
                'Question Type': ['Question Type', 'QUESTION TYPE', 'Type', 'TYPE'],
                'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
                'Option A': ['Option A', 'OPTION A', 'A'],
                'Option B': ['Option B', 'OPTION B', 'B'],
                'Option C': ['Option C', 'OPTION C', 'C'],
                'Option D': ['Option D', 'OPTION D', 'D'],
                'Correct Answer': ['Correct Answer', 'CORRECT ANSWER', 'Answer', 'ANSWER', 'Correct'],
                'Points': ['Points', 'POINTS', 'Score', 'SCORE']
            }
        
        final_columns = {}
        missing_required = []
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            if not found and standard_name != 'Points':
                missing_required.append(standard_name)
        
        if missing_required:
            raise HTTPException(status_code=400, detail=f"Missing required column(s): {', '.join(missing_required)}")
        
        df.rename(columns=final_columns, inplace=True)
        
        if use_simplified_format:
            import pandas as pd
            questions_list = []
            for idx, row in df.iterrows():
                correct_answer = str(row['Correct Answer']).strip().upper()
                correct_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}.get(correct_answer, 0)
                
                questions_list.append({
                    "question_text": str(row['Question Text']).strip(),
                    "options": [
                        str(row.get('Option A', '')).strip() if pd.notna(row.get('Option A')) else "",
                        str(row.get('Option B', '')).strip() if pd.notna(row.get('Option B')) else "",
                        str(row.get('Option C', '')).strip() if pd.notna(row.get('Option C')) else "",
                        str(row.get('Option D', '')).strip() if pd.notna(row.get('Option D')) else ""
                    ],
                    "correct_answer": correct_index,
                    "points": int(row['Points']) if 'Points' in df.columns and pd.notna(row.get('Points')) else 5
                })
            
            await db.tests.delete_many({"program_id": program_id})
            
            now = get_malaysia_time().isoformat()
            
            await db.tests.insert_one({
                "id": str(uuid.uuid4()),
                "program_id": program_id,
                "title": f"{program['name']} - Pre-Test",
                "test_type": "pre",
                "questions": questions_list,
                "created_at": now
            })
            
            await db.tests.insert_one({
                "id": str(uuid.uuid4()),
                "program_id": program_id,
                "title": f"{program['name']} - Post-Test",
                "test_type": "post",
                "questions": questions_list,
                "created_at": now
            })
            
            return {
                "message": "Questions uploaded successfully",
                "total_uploaded": len(questions_list),
                "program": program['name']
            }
        
        return {"message": "Legacy upload not implemented in modular version"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/{test_id}")
async def get_test(test_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific test"""
    test_doc = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if isinstance(test_doc.get('created_at'), str):
        test_doc['created_at'] = datetime.fromisoformat(test_doc['created_at'])
    
    questions = test_doc['questions'].copy()
    
    if current_user.role == "participant" and test_doc['test_type'] == "post":
        random.shuffle(questions)
    
    if current_user.role == "participant":
        test_doc['questions'] = [
            {
                'question': q['question'],
                'options': q['options'],
                'original_index': test_doc['questions'].index(q)
            }
            for q in questions
        ]
    else:
        test_doc['questions'] = questions
    
    return test_doc


@router.post("/submit", response_model=TestResult)
async def submit_test(submission: TestSubmit, current_user: User = Depends(get_current_user)):
    """Submit test answers"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit tests")
    
    test_doc = await db.tests.find_one({"id": submission.test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    program_doc = await db.programs.find_one({"id": test_doc['program_id']}, {"_id": 0})
    pass_percentage = program_doc.get('pass_percentage', 70.0) if program_doc else 70.0
    
    questions = test_doc['questions']
    
    correct = 0
    for i, ans in enumerate(submission.answers):
        if i < len(questions):
            if submission.question_indices and i < len(submission.question_indices):
                original_idx = submission.question_indices[i]
            else:
                original_idx = i
            
            if original_idx < len(questions):
                submitted_answer = int(ans)
                correct_answer = int(questions[original_idx]['correct_answer'])
                if submitted_answer == correct_answer:
                    correct += 1
    
    score = (correct / len(questions)) * 100 if questions else 0
    passed = score >= pass_percentage
    
    result_obj = TestResult(
        test_id=submission.test_id,
        participant_id=current_user.id,
        session_id=submission.session_id,
        test_type=test_doc['test_type'],
        answers=submission.answers,
        score=score,
        total_questions=len(questions),
        correct_answers=correct,
        passed=passed,
        question_indices=submission.question_indices
    )
    
    doc = result_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.test_results.insert_one(doc)
    
    test_type = test_doc['test_type']
    if test_type in ['pre', 'pre_test']:
        update_field = 'pre_test_completed'
    else:
        update_field = 'post_test_completed'
    await db.participant_access.update_one(
        {"participant_id": current_user.id, "session_id": submission.session_id},
        {"$set": {update_field: True}}
    )
    
    return result_obj


@router.get("/results/participant/{participant_id}", response_model=List[TestResult])
async def get_participant_results(participant_id: str, current_user: User = Depends(get_current_user)):
    """Get all test results for a participant"""
    if current_user.role == "participant" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    results = await db.test_results.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for result in results:
        if isinstance(result.get('submitted_at'), str):
            result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
        if 'test_type' not in result:
            result['test_type'] = 'pre'
        if 'total_questions' not in result:
            result['total_questions'] = len(result.get('answers', []))
        if 'correct_answers' not in result:
            result['correct_answers'] = int((result.get('score', 0) / 100) * result['total_questions'])
    return results


@router.put("/results/{result_id}")
async def update_test_result(result_id: str, score: float, passed: bool, current_user: User = Depends(get_current_user)):
    """Update test result - Super Admin only"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can update test results")
    
    result = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    await db.test_results.update_one(
        {"id": result_id},
        {"$set": {"score": score, "passed": passed}}
    )
    
    return {"message": "Test result updated successfully"}


@router.post("/super-admin-submit", response_model=TestResult)
async def super_admin_submit_test(data: SuperAdminTestSubmit, current_user: User = Depends(get_current_user)):
    """Submit test on behalf of participant - Super Admin only"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit tests for participants")
    
    test_doc = await db.tests.find_one({"id": data.test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    program_doc = await db.programs.find_one({"id": test_doc['program_id']}, {"_id": 0})
    pass_percentage = program_doc.get('pass_percentage', 70.0) if program_doc else 70.0
    
    questions = test_doc['questions']
    
    correct = 0
    for i, ans in enumerate(data.answers):
        if i < len(questions):
            submitted_answer = int(ans)
            correct_answer = int(questions[i]['correct_answer'])
            if submitted_answer == correct_answer:
                correct += 1
    
    score = (correct / len(questions)) * 100 if questions else 0
    passed = score >= pass_percentage
    
    result_obj = TestResult(
        test_id=data.test_id,
        participant_id=data.participant_id,
        session_id=data.session_id,
        test_type=test_doc['test_type'],
        answers=data.answers,
        score=score,
        total_questions=len(questions),
        correct_answers=correct,
        passed=passed
    )
    
    doc = result_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    existing = await db.test_results.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id,
        "test_type": test_doc['test_type']
    })
    
    if existing:
        await db.test_results.update_one(
            {
                "participant_id": data.participant_id,
                "session_id": data.session_id,
                "test_type": test_doc['test_type']
            },
            {"$set": {
                "test_id": data.test_id,
                "answers": data.answers,
                "score": score,
                "total_questions": len(questions),
                "correct_answers": correct,
                "passed": passed,
                "submitted_at": doc['submitted_at']
            }}
        )
    else:
        await db.test_results.insert_one(doc)
    
    update_field = 'pre_test_completed' if test_doc['test_type'] == 'pre' else 'post_test_completed'
    await db.participant_access.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": {update_field: True}},
        upsert=True
    )
    
    return result_obj


@router.get("/results/session/{session_id}")
async def get_session_results(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all test results for a session"""
    results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    for result in results:
        if isinstance(result.get('submitted_at'), str):
            result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
    return results


@router.get("/results/{result_id}")
async def get_test_result(result_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific test result"""
    result = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    if isinstance(result.get('submitted_at'), str):
        result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
    
    return result
