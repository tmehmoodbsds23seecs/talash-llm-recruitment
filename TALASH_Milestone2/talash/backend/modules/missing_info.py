"""
backend/modules/missing_info.py
Detects missing fields and generates personalised email drafts.
"""
from __future__ import annotations

from typing import Any


def detect_missing_fields(
    candidate_snapshot: dict[str, Any],
    education:  dict[str, Any],
    experience: dict[str, Any],
    research:   dict[str, Any],
) -> list[str]:
    missing: list[str] = []

    if not candidate_snapshot.get("full_name"):
        missing.append("full name")
    if not candidate_snapshot.get("email"):
        missing.append("email address")
    if not candidate_snapshot.get("phone"):
        missing.append("phone number")
    if not candidate_snapshot.get("nationality"):
        missing.append("nationality")

    if not (education.get("records") or []):
        missing.append("education history")

    if not (experience.get("records") or []):
        missing.append("professional experience details")

    if not (research.get("publications") or []):
        missing.append("publication / research details")

    overlaps = (experience.get("timeline_checks") or {}).get("job_overlaps") or []
    if overlaps:
        missing.append("clarification for overlapping job periods")

    unjustified = [
        g for g in ((experience.get("timeline_checks") or {}).get("professional_gaps") or [])
        if not g.get("is_justified")
    ]
    if unjustified:
        missing.append(f"explanation for {len(unjustified)} unexplained professional gap(s)")

    return sorted(set(missing))


async def draft_missing_info_email(full_name: str | None,
                                   missing_fields: list[str]) -> str:
    name = full_name or "Candidate"

    if not missing_fields:
        return (
            f"Subject: TALASH Profile Update Confirmation\n\n"
            f"Dear {name},\n\n"
            "Thank you for submitting your profile. At this stage, no additional "
            "information is required from your side.\n\n"
            "Kind regards,\n"
            "TALASH Recruitment Team\n"
            "Faculty of Computing"
        )

    bullets = "\n".join(f"  • {item}" for item in missing_fields)
    return (
        f"Subject: Request for Missing Information – TALASH Profile Review\n\n"
        f"Dear {name},\n\n"
        "Thank you for submitting your CV for review through the TALASH recruitment system. "
        "After an initial analysis of your profile, we would like to request the following "
        "additional information to complete your evaluation:\n\n"
        f"{bullets}\n\n"
        "Please reply to this email with the requested details, or share an updated CV "
        "that includes this information. This will allow us to finalise your assessment "
        "and move your application forward without delay.\n\n"
        "Kind regards,\n"
        "TALASH Recruitment Team\n"
        "Faculty of Computing"
    )
