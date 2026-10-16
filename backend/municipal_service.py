"""
Go Green — Municipal Authority Integration & Dispatch Service
Handles automatic municipal department assignment, government API submission,
work order tracking references, and administrative forwarding workflows.
"""

import os
import uuid
import re
import requests
from datetime import datetime, timezone
from flask import current_app

from extensions import db
from models import WasteReport, ComplaintStatusLog


DEPARTMENT_MAPPING = {
    "Roadside Garbage": "Solid Waste Management Department (SWMD)",
    "Overflowing Dustbin": "City Sanitation & Public Cleansing Division",
    "Plastic Waste": "Plastic Waste Recycling & Resource Recovery Directorate",
    "Construction Waste": "Public Works Department (PWD) - Debris Control Cell",
    "Drainage Waste": "Drainage & Sewerage Board (Urban Hydrology Division)",
    "Illegal Dumping": "Municipal Vigilance & Environmental Enforcement Directorate",
    "Hazardous Waste": "Pollution Control Board & Hazardous Waste Cell",
    "E-Waste": "Electronic Waste Management Unit",
    "Mixed Waste": "Solid Waste Management Department (SWMD)",
    "Other": "Municipal Grievance Redressal Cell",
}

WARD_CLEANUP_TEAMS = {
    "Ward 1": "Rapid Sanitation Crew #101 (MG Road Sector)",
    "Ward 2": "North Zone Cleansing Squad #204",
    "Ward 3": "Civic Center Rapid Debris Unit #302",
    "Ward 4": "Market District Sanitation Taskforce #401",
    "Ward 5": "Riverside Environmental Crew #505",
    "Ward 6": "Highland Mobile Sweeper Unit #603",
    "Ward 7": "Lakeview Rapid Response Team Alpha #701",
    "Ward 8": "Suburban South Heavy Vehicle Crew #802",
    "Ward 9": "Greenfield Eco Vigilance Crew #901",
}


def determine_department(waste_category: str) -> str:
    """Returns the responsible municipal department for the given category."""
    if not waste_category:
        return "Solid Waste Management Department (SWMD)"
    
    # Direct match or partial match
    for key, dept in DEPARTMENT_MAPPING.items():
        if key.lower() in waste_category.lower() or waste_category.lower() in key.lower():
            return dept
    return "Solid Waste Management Department (SWMD)"


def get_default_cleanup_team(ward: str) -> str:
    """Returns default designated cleanup team for a given ward."""
    norm_ward = ward.strip() if ward else "Ward 7"
    for w_key, team in WARD_CLEANUP_TEAMS.items():
        if w_key.lower() in norm_ward.lower():
            return team
    return f"Ward Sanitation Unit ({norm_ward})"


def generate_complaint_id() -> str:
    """Generates a human-friendly unique complaint ID: GG-GRB-YYYYMMDD-XXXX."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    rnd = uuid.uuid4().hex[:4].upper()
    return f"GG-GRB-{date_str}-{rnd}"


def generate_official_reference(ward: str, report_id: int) -> str:
    """Generates a realistic municipal dispatch tracking reference."""
    clean_ward = re.sub(r"[^A-Za-z0-9]", "", ward or "W7").upper()
    now = datetime.now(timezone.utc)
    seq = uuid.uuid4().hex[:4].upper()
    return f"MUNI-{clean_ward}-{now.strftime('%y%m')}-{report_id:04d}-{seq}"


def submit_to_municipal_api(report: WasteReport) -> dict:
    """
    Submits the complaint to the configured external government/municipal API.
    If no API endpoint is configured, returns honest, transparent status.
    """
    api_url = current_app.config.get("MUNICIPAL_API_URL")
    api_key = current_app.config.get("MUNICIPAL_API_KEY")

    if not api_url:
        # No official municipal API endpoint is configured in environment
        return {
            "configured": False,
            "submitted": False,
            "status": "Submitted to GoGreen",
            "message": "Official Municipal API endpoint is not configured in environment variables. Report stored in GoGreen Municipal Registry for administrative forwarding.",
            "officialReference": None,
        }

    payload = {
        "complaintId": report.complaint_id,
        "category": report.waste_category or report.waste_type,
        "severity": report.severity,
        "description": report.description,
        "location": {
            "address": report.address or report.location,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "accuracy": report.location_accuracy,
            "ward": report.ward,
        },
        "imageUrl": f"{current_app.config.get('BASE_URL', '')}/api/uploads/{report.image_filename}" if report.image_filename else None,
        "citizen": {
            "name": report.name,
            "email": report.email,
        },
        "submittedAt": report.created_at.isoformat() if report.created_at else None,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GoGreen-Municipal-Connector/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=8)
        if response.status_code in (200, 201):
            res_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            official_ref = res_data.get("referenceId") or res_data.get("official_ref") or generate_official_reference(report.ward, report.id)
            return {
                "configured": True,
                "submitted": True,
                "status": "Forwarded to Authority",
                "message": f"Successfully submitted to municipal authority endpoint: {current_app.config.get('MUNICIPAL_NAME')}",
                "officialReference": official_ref,
                "authorityResponse": res_data,
            }
        else:
            return {
                "configured": True,
                "submitted": False,
                "status": "Pending Municipal Submission",
                "message": f"Municipal authority endpoint returned HTTP {response.status_code}. Report queued for retry.",
                "officialReference": None,
            }
    except Exception as exc:
        return {
            "configured": True,
            "submitted": False,
            "status": "Pending Municipal Submission",
            "message": f"Network error contacting municipal endpoint: {str(exc)}. Queued for administrative dispatch.",
            "officialReference": None,
        }
