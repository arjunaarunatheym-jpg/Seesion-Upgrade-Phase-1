"""
Users routes - User management endpoints
Endpoints: 7
- GET /users
- GET /users/export/participants
- GET /users/{user_id}
- PUT /users/profile
- PUT /users/{user_id}
- DELETE /users/{user_id}
- POST /users/check-exists
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from typing import List, Optional
from datetime import datetime
import csv
import io

import uuid

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(tags=["users"])


@router.get("/users", response_model=List[User])
async def get_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all users with optional filters"""
    if current_user.role not in ["admin", "supervisor", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    query = {}
    
    if role:
        query["role"] = role
    
    if company_id:
        query["company_id"] = company_id
    
    if search:
        search_pattern = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"full_name": search_pattern},
            {"email": search_pattern},
            {"id_number": search_pattern}
        ]
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    return users


@router.get("/users/export/participants")
async def export_participants_csv(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Export participant contact details to CSV (Admin/Finance only)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can export participant data")
    
    query = {"role": "participant"}
    if company_id:
        query["company_id"] = company_id
    
    participants = await db.users.find(query, {"_id": 0, "password": 0}).to_list(5000)
    
    if session_id:
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if session:
            session_participant_ids = set(session.get("participant_ids", []))
            participants = [p for p in participants if p.get("id") in session_participant_ids]
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Full Name", "IC Number", "Login Email", "Contact Email", "Contact Phone",
        "Company", "Profile Verified", "Indemnity Accepted", "Created At"
    ])
    
    company_ids = list(set(p.get("company_id") for p in participants if p.get("company_id")))
    companies = await db.companies.find({"id": {"$in": company_ids}}, {"_id": 0}).to_list(500)
    company_map = {c["id"]: c.get("name", "") for c in companies}
    
    for p in participants:
        writer.writerow([
            p.get("full_name", ""),
            p.get("id_number", ""),
            p.get("email", ""),
            p.get("contact_email", ""),
            p.get("contact_phone", ""),
            company_map.get(p.get("company_id"), p.get("company_id", "")),
            "Yes" if p.get("profile_verified") else "No",
            "Yes" if p.get("indemnity_accepted") else "No",
            p.get("created_at", "")[:10] if p.get("created_at") else ""
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants_export.csv"}
    )


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific user by ID"""
    if current_user.role not in ["admin", "supervisor", "trainer", "coordinator"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return user


@router.put("/users/profile")
async def update_own_profile(profile_data: dict, request: Request, current_user: User = Depends(get_current_user)):
    """Allow users to update their own profile (limited fields)"""
    update_data = {}
    
    # Fields all users can update
    allowed_fields = [
        "full_name", "id_number", "phone", "emergency_contact", "emergency_phone",
        "emergency_contact_name", "emergency_contact_phone",
        "blood_type", "medical_conditions", "contact_email", "contact_phone",
        "social_popup_dismissed", "profile_verified", "indemnity_accepted",
        "indemnity_accepted_at", "indemnity_signature", "indemnity_signed_name",
        "indemnity_signed_ic", "indemnity_signed_date", "indemnity_sections_accepted",
        "indemnity_training_id", "indemnity_trainer_name", "indemnity_vehicle_reg",
        "indemnity_locked", "profile_photo", "digital_signature"
    ]
    
    for field in allowed_fields:
        if field in profile_data:
            update_data[field] = profile_data[field]
    
    # Capture IP and user agent when indemnity is accepted
    if profile_data.get("indemnity_accepted") == True:
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        update_data["indemnity_ip_address"] = client_ip
        update_data["indemnity_user_agent"] = request.headers.get("User-Agent", "unknown")
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_data["updated_at"] = get_malaysia_time().isoformat()
    
    await db.users.update_one({"id": current_user.id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "password": 0})
    return updated_user


@router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: dict, current_user: User = Depends(get_current_user)):
    """Update a user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    
    existing_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for email conflicts
    if user_data.get("email") and user_data["email"] != existing_user.get("email"):
        email_exists = await db.users.find_one({"email": user_data["email"], "id": {"$ne": user_id}}, {"_id": 0})
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already in use by another user")
    
    update_data = {}
    if "full_name" in user_data:
        update_data["full_name"] = user_data["full_name"]
    if "email" in user_data:
        update_data["email"] = user_data["email"]
    if "id_number" in user_data:
        new_ic = user_data["id_number"]
        if new_ic and new_ic != existing_user.get("id_number"):
            ic_exists = await db.users.find_one({"id_number": new_ic, "id": {"$ne": user_id}}, {"_id": 0})
            if ic_exists:
                raise HTTPException(status_code=400, detail="IC number already in use by another user")
        update_data["id_number"] = new_ic
    if "phone_number" in user_data:
        update_data["phone_number"] = user_data["phone_number"]
    if "additional_roles" in user_data:
        update_data["additional_roles"] = user_data["additional_roles"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    
    return User(**updated_user)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user and related data (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clean up related data
    await db.sessions.update_many(
        {"participant_ids": user_id},
        {"$pull": {"participant_ids": user_id}}
    )
    await db.participant_access.delete_many({"participant_id": user_id})
    await db.attendance.delete_many({"participant_id": user_id})
    
    return {"message": "User and all related data deleted successfully"}


@router.post("/users/check-exists")
async def check_user_exists(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    id_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Check if a user exists by name, email, or IC number (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can check user existence")
    
    query = {"$or": []}
    
    if full_name:
        query["$or"].append({"full_name": full_name})
    if email:
        query["$or"].append({"email": email})
    if id_number:
        query["$or"].append({"id_number": id_number})
    
    if not query["$or"]:
        return {"exists": False, "user": None}
    
    existing_user = await db.users.find_one(query, {"_id": 0, "hashed_password": 0})
    
    if existing_user:
        if isinstance(existing_user.get('created_at'), str):
            existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
        return {
            "exists": True,
            "user": User(**existing_user)
        }
    
    return {"exists": False, "user": None}



# Role-specific user creation endpoints

@router.post("/users/coordinator")
async def create_coordinator(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new coordinator user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create coordinators")
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from core import hash_password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    user_doc = {
        "id": user_id, "email": data.get("email"), "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""), "hashed_password": hashed_password,
        "role": "coordinator", "additional_roles": data.get("additional_roles", []),
        "is_verified": True, "created_at": get_malaysia_time().isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Coordinator created successfully"}


@router.post("/users/assistant-admin")
async def create_assistant_admin(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new assistant admin user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create assistant admins")
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from core import hash_password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    user_doc = {
        "id": user_id, "email": data.get("email"), "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""), "hashed_password": hashed_password,
        "role": "assistant_admin", "additional_roles": data.get("additional_roles", []),
        "is_verified": True, "created_at": get_malaysia_time().isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Assistant Admin created successfully"}


@router.post("/users/finance")
async def create_finance_user(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new finance user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create finance users")
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from core import hash_password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    user_doc = {
        "id": user_id, "email": data.get("email"), "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""), "hashed_password": hashed_password,
        "role": "finance", "additional_roles": data.get("additional_roles", []),
        "is_verified": True, "created_at": get_malaysia_time().isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Finance user created successfully"}


@router.post("/users/trainer")
async def create_trainer(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new trainer user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create trainers")
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from core import hash_password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    user_doc = {
        "id": user_id, "email": data.get("email"), "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""), "hashed_password": hashed_password,
        "role": "trainer", "additional_roles": data.get("additional_roles", []),
        "is_verified": True, "created_at": get_malaysia_time().isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Trainer created successfully"}


@router.post("/users/marketing")
async def create_marketing_user(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new marketing user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create marketing users")
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from core import hash_password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    user_doc = {
        "id": user_id, "email": data.get("email"), "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""), "hashed_password": hashed_password,
        "role": "marketing", "additional_roles": data.get("additional_roles", []),
        "is_verified": True, "created_at": get_malaysia_time().isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Marketing user created successfully"}
