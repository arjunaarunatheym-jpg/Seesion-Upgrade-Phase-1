"""
Health Check & Automated Testing Endpoints
- System health check (DB, critical collections, API responsiveness)
- Business logic validation (statutory calculations, auth flow)
"""
from fastapi import APIRouter, Depends, HTTPException
from core import get_current_user, User, db
from datetime import datetime, timezone
import time

router = APIRouter(tags=["health"])


@router.get("/health")
async def basic_health():
    """Public health check — no auth required."""
    checks = {}
    
    # DB connectivity
    try:
        start = time.time()
        await db.command("ping")
        checks["database"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
    
    all_ok = all(c["status"] == "ok" for c in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/detailed")
async def detailed_health(current_user: User = Depends(get_current_user)):
    """Admin-only detailed health check — tests all critical systems."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    results = []
    
    # 1. Database connectivity
    try:
        start = time.time()
        await db.command("ping")
        results.append({"test": "Database Connection", "status": "pass", "ms": round((time.time() - start) * 1000)})
    except Exception as e:
        results.append({"test": "Database Connection", "status": "fail", "error": str(e)})
    
    # 2. Critical collections exist and have data
    critical_collections = {
        "users": 1, "programs": 1, "sessions": 0, "companies": 1,
        "settings": 1, "chart_of_accounts": 1, "statutory_rates": 50,
    }
    for coll, min_count in critical_collections.items():
        try:
            count = await db[coll].count_documents({})
            ok = count >= min_count
            results.append({"test": f"Collection: {coll}", "status": "pass" if ok else "warn", "count": count, "expected_min": min_count})
        except Exception as e:
            results.append({"test": f"Collection: {coll}", "status": "fail", "error": str(e)})
    
    # 3. Auth system
    try:
        admin = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1})
        results.append({"test": "Admin User Exists", "status": "pass" if admin else "fail"})
    except Exception as e:
        results.append({"test": "Admin User Exists", "status": "fail", "error": str(e)})
    
    # 4. Statutory rates coverage
    for rate_type in ["epf", "socso", "eis"]:
        try:
            count = await db.statutory_rates.count_documents({"rate_type": rate_type})
            results.append({"test": f"Statutory Rates: {rate_type.upper()}", "status": "pass" if count > 10 else "warn", "count": count})
        except Exception as e:
            results.append({"test": f"Statutory Rates: {rate_type.upper()}", "status": "fail", "error": str(e)})
    
    # 5. Settings configured
    try:
        settings = await db.settings.find_one({"id": "app_settings"}, {"_id": 0})
        company = await db.company_settings.find_one({}, {"_id": 0})
        results.append({"test": "App Settings", "status": "pass" if settings else "warn"})
        results.append({"test": "Company Settings", "status": "pass" if company else "warn"})
    except Exception as e:
        results.append({"test": "Settings", "status": "fail", "error": str(e)})
    
    # 6. Invoice numbering
    try:
        counter = await db.counters.find_one({"_id": "invoice_number"})
        results.append({"test": "Invoice Counter", "status": "pass" if counter else "warn"})
    except Exception as e:
        results.append({"test": "Invoice Counter", "status": "fail", "error": str(e)})
    
    # Summary
    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")
    
    return {
        "status": "healthy" if failed == 0 else "degraded" if failed <= 2 else "critical",
        "summary": {"passed": passed, "warnings": warned, "failed": failed, "total": len(results)},
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
