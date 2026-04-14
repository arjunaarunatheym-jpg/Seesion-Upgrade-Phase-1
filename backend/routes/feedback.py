"""
Feedback routes - Course feedback and trainer feedback management
Endpoints: 12+
- POST /feedback-templates
- GET /feedback-templates/program/{program_id}
- GET /feedback/templates/program/{program_id}
- DELETE /feedback-templates/{template_id}
- POST /feedback/submit
- GET /feedback/session/{session_id}
- GET /feedback/company/{company_id}
- GET /coordinator-feedback-template
- PUT /coordinator-feedback-template
- GET /chief-trainer-feedback-template
- PUT /chief-trainer-feedback-template
- POST /coordinator-feedback/{session_id}
- GET /coordinator-feedback/{session_id}
- POST /chief-trainer-feedback/{session_id}
- GET /chief-trainer-feedback/{session_id}
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Any
from datetime import datetime
import uuid

from core import db, get_current_user, get_malaysia_time
from models import User

from pydantic import BaseModel, Field, ConfigDict

# Feedback models
class FeedbackQuestion(BaseModel):
    question: str
    type: str = "rating"
    required: bool = True

class FeedbackTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    questions: List[dict] = []
    created_at: datetime = Field(default_factory=get_malaysia_time)

class FeedbackTemplateCreate(BaseModel):
    program_id: str
    questions: List[dict]

class FeedbackTemplateUpdate(BaseModel):
    questions: List[dict]

class CourseFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    program_id: str
    responses: Any = {}
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

class FeedbackSubmit(BaseModel):
    session_id: str
    program_id: str
    responses: Any

class CoordinatorFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: str
    responses: Any = {}
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

class ChiefTrainerFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    trainer_id: str
    responses: Any = {}
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

# Default templates
DEFAULT_FEEDBACK_QUESTIONS = [
    {"question": "Overall Training Experience", "type": "rating", "required": True},
    {"question": "Training Content Quality", "type": "rating", "required": True},
    {"question": "Trainer Effectiveness", "type": "rating", "required": True},
    {"question": "Venue & Facilities", "type": "rating", "required": True},
    {"question": "Suggestions for Improvement", "type": "text", "required": False},
    {"question": "Additional Comments", "type": "text", "required": False}
]

DEFAULT_COORDINATOR_QUESTIONS = [
    {"id": "training_quality", "question": "Rate the overall quality of training delivery", "type": "rating", "scale": 5},
    {"id": "trainer_preparedness", "question": "Rate trainer preparedness and knowledge", "type": "rating", "scale": 5},
    {"id": "participant_engagement", "question": "Rate participant engagement level", "type": "rating", "scale": 5},
    {"id": "facility_condition", "question": "Rate the condition of training facilities", "type": "rating", "scale": 5},
    {"id": "overall_comments", "question": "Please provide any additional comments or observations", "type": "text"}
]

DEFAULT_CHIEF_TRAINER_QUESTIONS = [
    {"id": "training_effectiveness", "question": "Rate the effectiveness of the training session", "type": "rating", "scale": 5},
    {"id": "participant_skill_improvement", "question": "Rate overall participant skill improvement", "type": "rating", "scale": 5},
    {"id": "safety_compliance", "question": "Rate participant safety compliance during training", "type": "rating", "scale": 5},
    {"id": "participant_dedication", "question": "Rate participant dedication and effort", "type": "rating", "scale": 5},
    {"id": "overall_impressions", "question": "Please share your overall impressions and recommendations", "type": "text"}
]

router = APIRouter(tags=["feedback"])


# Feedback Template Routes
@router.post("/feedback-templates", response_model=FeedbackTemplate)
async def create_feedback_template(template_data: FeedbackTemplateCreate, current_user: User = Depends(get_current_user)):
    """Create or update feedback template for a program"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create feedback templates")
    
    await db.feedback_templates.delete_many({"program_id": template_data.program_id})
    
    template_obj = FeedbackTemplate(
        program_id=template_data.program_id,
        questions=template_data.questions
    )
    
    doc = template_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.feedback_templates.insert_one(doc)
    return template_obj


@router.get("/feedback-templates/program/{program_id}")
async def get_feedback_template(program_id: str, current_user: User = Depends(get_current_user)):
    """Get feedback template for a program"""
    template = await db.feedback_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return {"program_id": program_id, "questions": DEFAULT_FEEDBACK_QUESTIONS}
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    return template


@router.get("/feedback/templates/program/{program_id}")
async def get_feedback_template_alias(program_id: str, current_user: User = Depends(get_current_user)):
    """Alias endpoint for backward compatibility - returns array format"""
    template = await db.feedback_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return [{"program_id": program_id, "questions": DEFAULT_FEEDBACK_QUESTIONS}]
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    return [template]


@router.delete("/feedback-templates/{template_id}")
async def delete_feedback_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete a feedback template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete feedback templates")
    
    result = await db.feedback_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback template not found")
    
    return {"message": "Feedback template deleted successfully"}


# Course Feedback Routes
@router.post("/feedback/submit")
async def submit_feedback(feedback_data: FeedbackSubmit, current_user: User = Depends(get_current_user)):
    """Submit course feedback"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit feedback")
    
    existing_feedback = await db.course_feedback.find_one({
        "participant_id": current_user.id,
        "session_id": feedback_data.session_id
    })
    
    if existing_feedback:
        raise HTTPException(status_code=400, detail="You have already submitted feedback for this session")
    
    feedback_obj = CourseFeedback(
        participant_id=current_user.id,
        session_id=feedback_data.session_id,
        program_id=feedback_data.program_id,
        responses=feedback_data.responses
    )
    
    doc = feedback_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.course_feedback.insert_one(doc)
    
    await db.participant_access.update_one(
        {"participant_id": current_user.id, "session_id": feedback_data.session_id},
        {"$set": {"feedback_completed": True, "feedback_submitted": True}},
        upsert=True
    )
    
    return feedback_obj


@router.get("/feedback/session/{session_id}")
async def get_session_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all feedback for a session"""
    if current_user.role not in ["admin", "supervisor", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    feedback = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    for fb in feedback:
        if isinstance(fb.get('submitted_at'), str):
            fb['submitted_at'] = datetime.fromisoformat(fb['submitted_at'])
    return feedback


@router.get("/feedback/company/{company_id}")
async def get_company_feedback(company_id: str, current_user: User = Depends(get_current_user)):
    """Get all feedback for a company's sessions"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view company feedback")
    
    sessions = await db.sessions.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
    session_ids = [s['id'] for s in sessions]
    
    feedback = await db.course_feedback.find({"session_id": {"$in": session_ids}}, {"_id": 0}).to_list(1000)
    for fb in feedback:
        if isinstance(fb.get('submitted_at'), str):
            fb['submitted_at'] = datetime.fromisoformat(fb['submitted_at'])
    
    return feedback


# Coordinator Feedback Routes
@router.get("/coordinator-feedback-template")
async def get_coordinator_feedback_template(current_user: User = Depends(get_current_user)):
    """Get coordinator feedback template"""
    template = await db.feedback_templates.find_one({"id": "coordinator_feedback_template"}, {"_id": 0})
    if not template:
        return {"id": "coordinator_feedback_template", "questions": DEFAULT_COORDINATOR_QUESTIONS}
    return template


@router.put("/coordinator-feedback-template")
async def update_coordinator_feedback_template(template_update: FeedbackTemplateUpdate, current_user: User = Depends(get_current_user)):
    """Update coordinator feedback template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update feedback templates")
    
    await db.feedback_templates.update_one(
        {"id": "coordinator_feedback_template"},
        {"$set": {"questions": template_update.questions, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    return {"message": "Template updated successfully"}


@router.post("/coordinator-feedback/{session_id}")
async def submit_coordinator_feedback(session_id: str, responses: dict, current_user: User = Depends(get_current_user)):
    """Submit coordinator feedback for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can submit coordinator feedback")
    
    existing = await db.coordinator_feedback.find_one({"session_id": session_id}, {"_id": 0})
    
    feedback = CoordinatorFeedback(
        session_id=session_id,
        coordinator_id=current_user.id,
        responses=responses
    )
    
    doc = feedback.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    if existing:
        await db.coordinator_feedback.update_one({"session_id": session_id}, {"$set": doc})
    else:
        await db.coordinator_feedback.insert_one(doc)
    
    return {"message": "Coordinator feedback submitted successfully", "feedback": feedback}


@router.get("/coordinator-feedback/{session_id}")
async def get_coordinator_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Get coordinator feedback for a session"""
    feedback = await db.coordinator_feedback.find_one({"session_id": session_id}, {"_id": 0})
    return feedback


# Chief Trainer Feedback Routes
@router.get("/chief-trainer-feedback-template")
async def get_chief_trainer_feedback_template(current_user: User = Depends(get_current_user)):
    """Get chief trainer feedback template"""
    template = await db.feedback_templates.find_one({"id": "chief_trainer_feedback_template"}, {"_id": 0})
    if not template:
        return {"id": "chief_trainer_feedback_template", "questions": DEFAULT_CHIEF_TRAINER_QUESTIONS}
    return template


@router.put("/chief-trainer-feedback-template")
async def update_chief_trainer_feedback_template(template_update: FeedbackTemplateUpdate, current_user: User = Depends(get_current_user)):
    """Update chief trainer feedback template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update feedback templates")
    
    await db.feedback_templates.update_one(
        {"id": "chief_trainer_feedback_template"},
        {"$set": {"questions": template_update.questions, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    return {"message": "Template updated successfully"}


@router.post("/chief-trainer-feedback/{session_id}")
async def submit_chief_trainer_feedback(session_id: str, responses: dict, current_user: User = Depends(get_current_user)):
    """Submit chief trainer feedback for a session"""
    if current_user.role not in ["chief_trainer", "trainer", "admin"]:
        raise HTTPException(status_code=403, detail="Only trainers and admins can submit chief trainer feedback")
    
    existing = await db.chief_trainer_feedback.find_one({"session_id": session_id}, {"_id": 0})
    
    feedback = ChiefTrainerFeedback(
        session_id=session_id,
        trainer_id=current_user.id,
        responses=responses
    )
    
    doc = feedback.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    if existing:
        await db.chief_trainer_feedback.update_one({"session_id": session_id}, {"$set": doc})
    else:
        await db.chief_trainer_feedback.insert_one(doc)
    
    return {"message": "Chief trainer feedback submitted successfully", "feedback": feedback}


@router.get("/chief-trainer-feedback/{session_id}")
async def get_chief_trainer_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Get chief trainer feedback for a session"""
    feedback = await db.chief_trainer_feedback.find_one({"session_id": session_id}, {"_id": 0})
    return feedback



@router.post("/feedback-templates/bulk-upload")
async def bulk_upload_feedback_questions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload feedback questions from Excel file"""
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
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

        df.columns = df.columns.str.strip()

        column_mappings = {
            'Program Name': ['Program Name', 'PROGRAM NAME', 'Program', 'PROGRAM'],
            'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
            'Question Type': ['Question Type', 'QUESTION TYPE', 'Type', 'TYPE'],
            'Options': ['Options', 'OPTIONS', 'Choices', 'CHOICES']
        }

        final_columns = {}
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            if not found and standard_name != 'Options':
                raise HTTPException(status_code=400, detail=f"Missing required column: {standard_name}")

        df.rename(columns=final_columns, inplace=True)

        errors = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            if pd.isna(row['Program Name']) or str(row['Program Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Program Name")
            if pd.isna(row['Question Text']) or str(row['Question Text']).strip() == '':
                errors.append(f"Row {row_num}: Missing Question Text")
            if pd.isna(row['Question Type']) or str(row['Question Type']).strip() == '':
                errors.append(f"Row {row_num}: Missing Question Type")
            elif str(row['Question Type']).lower() not in ['rating', 'multiple_choice', 'text']:
                errors.append(f"Row {row_num}: Question Type must be 'rating', 'multiple_choice', or 'text'")

        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))

        added_questions = []
        programs_not_found = []

        for idx, row in df.iterrows():
            program_name = str(row['Program Name']).strip()
            question_text = str(row['Question Text']).strip()
            question_type = str(row['Question Type']).lower().strip()

            options = []
            if 'Options' in df.columns and pd.notna(row['Options']) and str(row['Options']).strip():
                options = [opt.strip() for opt in str(row['Options']).split(',')]

            program = await db.programs.find_one({"name": program_name}, {"_id": 0})
            if not program:
                if program_name not in programs_not_found:
                    programs_not_found.append(program_name)
                continue

            question_data = {
                "question_text": question_text,
                "question_type": question_type,
                "options": options if question_type == "multiple_choice" else []
            }

            template = await db.feedback_templates.find_one({"program_id": program["id"]}, {"_id": 0})

            if template:
                await db.feedback_templates.update_one(
                    {"id": template["id"]},
                    {"$push": {"questions": question_data}}
                )
                added_questions.append({"program": program_name, "question": question_text, "action": "added_to_existing_template"})
            else:
                template_id = str(uuid.uuid4())
                template_data = {
                    "id": template_id,
                    "program_id": program["id"],
                    "questions": [question_data],
                    "created_at": datetime.now().isoformat()
                }
                await db.feedback_templates.insert_one({**template_data, "_id": template_id})
                added_questions.append({"program": program_name, "question": question_text, "action": "created_new_template"})

        response = {
            "message": "Bulk upload successful",
            "total_uploaded": len(added_questions),
            "questions": added_questions
        }

        if programs_not_found:
            response["warnings"] = f"Programs not found: {', '.join(programs_not_found)}"

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
