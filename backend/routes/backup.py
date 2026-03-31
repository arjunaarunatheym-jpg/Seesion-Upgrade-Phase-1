"""
Data Backup & Export Endpoints
- Full database export (JSON)
- Individual collection export (CSV)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from core import get_current_user, User, db
from datetime import datetime, timezone
import json
import io
import csv

router = APIRouter(tags=["backup"])

EXPORTABLE_COLLECTIONS = [
    "users", "companies", "programs", "sessions", "invoices", "quotations",
    "payslips", "hr_staff", "leads", "petty_cash_transactions", "journal_entries",
    "course_feedback", "tests", "test_results", "attendance", "vehicle_checklists",
    "vehicle_details", "certificates", "credit_notes", "billing_parties",
    "statutory_rates", "settings", "company_settings", "chart_of_accounts",
    "feedback_templates", "checklist_templates", "training_reports",
]


@router.get("/backup/collections")
async def list_exportable_collections(current_user: User = Depends(get_current_user)):
    """List all collections available for export with record counts."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = []
    for coll in EXPORTABLE_COLLECTIONS:
        try:
            count = await db[coll].count_documents({})
            result.append({"collection": coll, "count": count})
        except Exception:
            result.append({"collection": coll, "count": 0})
    
    return {"collections": result, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/backup/export/{collection_name}")
async def export_collection(collection_name: str, format: str = "json", current_user: User = Depends(get_current_user)):
    """Export a single collection as JSON or CSV."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if collection_name not in EXPORTABLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Collection '{collection_name}' is not exportable")
    
    docs = await db[collection_name].find({}, {"_id": 0}).to_list(None)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if format == "csv":
        if not docs:
            return StreamingResponse(io.BytesIO(b"No data"), media_type="text/csv")
        
        output = io.StringIO()
        all_keys = set()
        for d in docs:
            all_keys.update(d.keys())
        keys = sorted(all_keys)
        
        writer = csv.DictWriter(output, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for d in docs:
            row = {}
            for k in keys:
                val = d.get(k, "")
                row[k] = json.dumps(val) if isinstance(val, (dict, list)) else str(val) if val is not None else ""
            writer.writerow(row)
        
        content = output.getvalue().encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{collection_name}_{timestamp}.csv"'}
        )
    else:
        # Serialize dates and special types
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        
        content = json.dumps(docs, default=serialize, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{collection_name}_{timestamp}.json"'}
        )


@router.get("/backup/export-all")
async def export_all_collections(current_user: User = Depends(get_current_user)):
    """Export ALL collections as a single JSON file (full database backup)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    backup = {"exported_at": datetime.now(timezone.utc).isoformat(), "collections": {}}
    
    for coll in EXPORTABLE_COLLECTIONS:
        try:
            docs = await db[coll].find({}, {"_id": 0}).to_list(None)
            backup["collections"][coll] = docs
        except Exception:
            backup["collections"][coll] = []
    
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)
    
    content = json.dumps(backup, default=serialize, indent=2).encode("utf-8")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="full_backup_{timestamp}.json"'}
    )
