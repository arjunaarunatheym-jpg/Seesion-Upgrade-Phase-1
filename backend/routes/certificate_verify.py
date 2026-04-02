"""
Certificate Verification routes - Public verification endpoints (no auth required)
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from core import db

router = APIRouter(prefix="/verify", tags=["certificate-verification"])


def format_ic_number(ic: str) -> str:
    """Format IC number with dashes: 861125385720 -> 861125-38-5720"""
    digits = ''.join(c for c in str(ic) if c.isdigit())
    if len(digits) == 12:
        return f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"
    return ic


@router.get("/certificate/{cert_number}")
async def verify_certificate(cert_number: str):
    """Public endpoint - verify certificate by certificate number. No auth required."""
    cert = await db.certificates.find_one(
        {"certificate_number": cert_number},
        {"_id": 0}
    )
    if not cert:
        # Try with slashes replaced (URL-safe format)
        alt_number = cert_number.replace("-", "/")
        cert = await db.certificates.find_one(
            {"certificate_number": alt_number},
            {"_id": 0}
        )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Get participant info
    participant = await db.users.find_one(
        {"id": cert.get("participant_id")},
        {"_id": 0, "full_name": 1, "id_number": 1}
    )

    # Get session info
    session = await db.sessions.find_one(
        {"id": cert.get("session_id")},
        {"_id": 0, "program_id": 1, "company_id": 1, "start_date": 1,
         "location": 1, "cert_show_validity": 1, "cert_validity_months": 1}
    )

    # Get programme info
    program = None
    if session:
        program = await db.programs.find_one(
            {"id": session.get("program_id")},
            {"_id": 0, "name": 1, "certificate_title": 1}
        )

    # Get company info
    company = None
    if session:
        company = await db.companies.find_one(
            {"id": session.get("company_id")},
            {"_id": 0, "name": 1}
        )

    ic_raw = participant.get("id_number", "") if participant else ""

    return {
        "valid": True,
        "certificate_number": cert.get("certificate_number"),
        "participant_name": participant.get("full_name", "Unknown") if participant else "Unknown",
        "ic_number": format_ic_number(ic_raw),
        "company_name": company.get("name", "") if company else "",
        "programme": program.get("certificate_title") or program.get("name", "") if program else "",
        "training_date": session.get("start_date", "") if session else "",
        "venue": session.get("location", "") if session else "",
        "issue_date": cert.get("issue_date", ""),
        "show_validity": session.get("cert_show_validity", False) if session else False,
        "validity_start": cert.get("validity_start", ""),
        "validity_end": cert.get("validity_end", ""),
    }


@router.get("/search-ic/{ic_number}")
async def search_certificates_by_ic(ic_number: str):
    """Public endpoint - search certificates by IC number. No auth required."""
    # Strip dashes for search
    ic_clean = ''.join(c for c in ic_number if c.isdigit())
    if len(ic_clean) < 6:
        raise HTTPException(status_code=400, detail="Please enter at least 6 digits of the IC number")

    # Find participants matching this IC
    participants = await db.users.find(
        {"id_number": {"$regex": ic_clean, "$options": "i"}},
        {"_id": 0, "id": 1, "full_name": 1, "id_number": 1}
    ).to_list(20)

    if not participants:
        return {"certificates": []}

    participant_ids = [p["id"] for p in participants]
    participant_map = {p["id"]: p for p in participants}

    # Find all certificates for these participants
    certs = await db.certificates.find(
        {"participant_id": {"$in": participant_ids}},
        {"_id": 0}
    ).to_list(100)

    results = []
    for cert in certs:
        p = participant_map.get(cert.get("participant_id"), {})
        session = await db.sessions.find_one(
            {"id": cert.get("session_id")},
            {"_id": 0, "program_id": 1, "company_id": 1, "start_date": 1,
             "cert_show_validity": 1}
        )
        program = None
        company = None
        if session:
            program = await db.programs.find_one(
                {"id": session.get("program_id")},
                {"_id": 0, "name": 1, "certificate_title": 1}
            )
            company = await db.companies.find_one(
                {"id": session.get("company_id")},
                {"_id": 0, "name": 1}
            )

        results.append({
            "certificate_number": cert.get("certificate_number", ""),
            "participant_name": p.get("full_name", "Unknown"),
            "ic_number": format_ic_number(p.get("id_number", "")),
            "company_name": company.get("name", "") if company else "",
            "programme": program.get("certificate_title") or program.get("name", "") if program else "",
            "training_date": session.get("start_date", "") if session else "",
            "issue_date": cert.get("issue_date", ""),
            "show_validity": session.get("cert_show_validity", False) if session else False,
            "validity_start": cert.get("validity_start", ""),
            "validity_end": cert.get("validity_end", ""),
        })

    return {"certificates": results}
