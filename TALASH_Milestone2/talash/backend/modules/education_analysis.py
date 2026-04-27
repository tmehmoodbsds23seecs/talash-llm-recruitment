"""
backend/modules/education_analysis.py
Builds a full structured educational profile from parsed CV data.
"""
from __future__ import annotations

from typing import Any

from backend.modules.preprocessing import extract_education_records
from backend.modules.qs_ranking_matcher import get_qs_ranking


async def analyze_education(raw_text: str,
                             candidate_universities: str | None = None) -> dict[str, Any]:
    """Build a structured educational profile summary from CV text."""
    records = extract_education_records(raw_text)

    levels = [r.get("degree_level") for r in records if r.get("degree_level")]
    years  = sorted({
        yr
        for r in records
        for yr in (r.get("year_start"), r.get("year_end"))
        if isinstance(yr, int)
    })

    # QS ranking for provided university
    qs_ranking       = None
    institution_name = None
    if candidate_universities:
        institution_name, qs_ranking = get_qs_ranking(candidate_universities)

    # Attach QS info to last education record if available
    if records:
        records[-1]["institution_name"] = institution_name or candidate_universities
        records[-1]["qs_ranking"]        = qs_ranking

    # Gap detection (≥ 3-year gaps between consecutive academic years)
    gaps: list[dict[str, Any]] = []
    for i in range(1, len(years)):
        gap = years[i] - years[i - 1]
        if gap >= 3:
            gaps.append({"gap_between": f"{years[i-1]}-{years[i]}", "gap_years": gap})

    return {
        "records":            records,
        "highest_qualification": levels[-1] if levels else None,
        "degree_path":        levels,
        "educational_years":  years,
        "education_gaps":     gaps,
        "qs_ranking_info": {
            "searched_university": candidate_universities,
            "matched_institution": institution_name,
            "qs_ranking":          qs_ranking,
        },
        "summary": {
            "records_count":       len(records),
            "has_school_stage":    any(l in {"SSE / Matric", "HSSC / Intermediate"} for l in levels),
            "has_higher_education":any(l in {"BS / BSc", "MS / MPhil", "PhD"} for l in levels),
            "gap_count":           len(gaps),
        },
    }
