"""
Admin Dashboard KPI endpoint
Provides at-a-glance business metrics for the admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from core import db, get_current_user
from models import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard-kpis")
async def get_dashboard_kpis(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # --- Sessions this month ---
    all_sessions = await db.sessions.find({"_id": 0, "id": 1, "start_date": 1, "end_date": 1, "completion_status": 1, "participant_ids": 1, "trainer_assignments": 1}).to_list(None)
    # Workaround: fetch all sessions with projection
    all_sessions = await db.sessions.find({}, {"_id": 0}).to_list(None)

    sessions_this_month = 0
    active_sessions = 0
    completed_sessions_ytd = 0
    total_trainees_ytd = 0
    trainer_ids_with_sessions = set()

    for s in all_sessions:
        start = s.get("start_date", "")
        if isinstance(start, str) and len(start) >= 7:
            try:
                sd = datetime.fromisoformat(start.replace("Z", "+00:00")) if "T" in start else datetime.strptime(start[:10], "%Y-%m-%d")
            except Exception:
                continue

            # Sessions this month
            if sd.year == current_year and sd.month == current_month:
                sessions_this_month += 1

            # Active sessions (not completed/cancelled)
            status = s.get("completion_status", "active")
            if status in ["active", "in_progress", "scheduled", "confirmed"]:
                active_sessions += 1

            # YTD stats
            if sd.year == current_year:
                if status in ["completed", "closed"]:
                    completed_sessions_ytd += 1
                pids = s.get("participant_ids", [])
                if isinstance(pids, list):
                    total_trainees_ytd += len(pids)

                # Trainer utilization
                assignments = s.get("trainer_assignments", [])
                if isinstance(assignments, list):
                    for ta in assignments:
                        tid = ta.get("trainer_id") if isinstance(ta, dict) else None
                        if tid:
                            trainer_ids_with_sessions.add(tid)

    # --- Revenue YTD (paid invoices) ---
    paid_invoices = await db.invoices.find(
        {"status": "paid"},
        {"_id": 0, "total_amount": 1, "invoice_date": 1, "created_at": 1}
    ).to_list(None)

    revenue_ytd = 0
    for inv in paid_invoices:
        date_str = inv.get("invoice_date") or inv.get("created_at", "")
        if isinstance(date_str, str) and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
                if year == current_year:
                    revenue_ytd += inv.get("total_amount", 0) or 0
            except Exception:
                pass

    # --- Outstanding invoices ---
    outstanding_invoices = await db.invoices.find(
        {"status": {"$in": ["issued", "approved", "pending"]}},
        {"_id": 0, "total_amount": 1}
    ).to_list(None)
    outstanding_total = sum(inv.get("total_amount", 0) or 0 for inv in outstanding_invoices)
    outstanding_count = len(outstanding_invoices)

    # --- Average feedback score ---
    # Feedback responses are stored as arrays with question/answer pairs
    # Numeric answers (1-5) are the rating scores
    feedback_docs = await db.course_feedback.find({}, {"_id": 0, "responses": 1}).to_list(None)
    total_score = 0
    score_count = 0
    feedback_count = len(feedback_docs)
    for doc in feedback_docs:
        responses = doc.get("responses", [])
        for r in responses:
            ans = r.get("answer")
            if isinstance(ans, (int, float)) and 1 <= ans <= 5:
                total_score += ans
                score_count += 1
    avg_feedback = round(total_score / score_count, 1) if score_count > 0 else 0

    # --- Trainer utilization ---
    total_trainers = await db.users.count_documents({"role": "trainer", "is_active": {"$ne": False}})
    trainers_assigned = len(trainer_ids_with_sessions)
    trainer_utilization = round((trainers_assigned / total_trainers * 100) if total_trainers > 0 else 0)

    # --- Staff count ---
    staff_count = await db.users.count_documents({
        "role": {"$in": ["coordinator", "trainer", "marketing", "finance", "assistant_admin"]},
        "is_active": {"$ne": False}
    })

    # --- Pending quotations ---
    pending_quotes = await db.quotations.count_documents({"status": "pending_approval"})

    return {
        "sessions_this_month": sessions_this_month,
        "active_sessions": active_sessions,
        "completed_sessions_ytd": completed_sessions_ytd,
        "total_trainees_ytd": total_trainees_ytd,
        "revenue_ytd": round(revenue_ytd, 2),
        "outstanding_total": round(outstanding_total, 2),
        "outstanding_count": outstanding_count,
        "avg_feedback_score": avg_feedback,
        "feedback_count": feedback_count,
        "trainer_utilization": trainer_utilization,
        "total_trainers": total_trainers,
        "trainers_assigned": trainers_assigned,
        "staff_count": staff_count,
        "pending_quotations": pending_quotes,
        "year": current_year,
        "month": current_month,
    }
