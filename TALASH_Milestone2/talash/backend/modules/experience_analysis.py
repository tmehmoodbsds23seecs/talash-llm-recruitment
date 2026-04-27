"""
backend/modules/experience_analysis.py
Analyses professional timeline: overlaps, gaps, career progression.
"""
from __future__ import annotations

import re
from typing import Any

from backend.modules.preprocessing import extract_education_records, extract_experience_records

PRODUCTIVE_ACTIVITY_KEYWORDS = {
    "higher education":    ["ms", "mphil", "phd", "masters", "degree", "university"],
    "research assistantship": ["research assistant", "ra"],
    "internship":          ["intern", "internship"],
    "freelancing":         ["freelance", "freelancer"],
    "consultancy":         ["consultant", "consultancy"],
    "entrepreneurship":    ["startup", "entrepreneur", "founder"],
    "training":            ["training", "certification", "course"],
    "teaching":            ["lecturer", "teaching", "instructor", "assistant professor"],
}


def _period(s, e):
    if s is None and e is None:
        return None, None
    if s is None:
        return e, e
    if e is None:
        return s, s
    return min(s, e), max(s, e)


def _overlap(a0, a1, b0, b1) -> bool:
    return max(a0, b0) <= min(a1, b1)


def _job_level_score(title: str | None) -> int:
    if not title:
        return 0
    t = title.lower()
    if any(x in t for x in ["head", "director", "chair", "professor"]):           return 5
    if any(x in t for x in ["lead", "principal", "senior", "manager", "assistant professor"]): return 4
    if any(x in t for x in ["engineer", "developer", "analyst", "lecturer"]):     return 3
    if any(x in t for x in ["associate", "junior", "intern", "trainee", "assistant"]): return 2
    return 1


def _gap_justification(raw_text: str, gap_start: int, gap_end: int):
    lower = raw_text.lower()
    yrs   = {str(y) for y in range(gap_start, gap_end + 1)}
    for label, kws in PRODUCTIVE_ACTIVITY_KEYWORDS.items():
        if not any(kw in lower for kw in kws):
            continue
        for line in raw_text.splitlines():
            ll = line.lower()
            if any(kw in ll for kw in kws) and (any(y in line for y in yrs) or not yrs):
                return True, f"Justified by {label}: '{line.strip()[:140]}'"
        return True, f"May be justified by {label} activity mentioned in CV."
    return False, None


async def analyze_experience(raw_text: str) -> dict[str, Any]:
    edu_records = extract_education_records(raw_text)
    exp_records = extract_experience_records(raw_text)

    edu_periods = []
    for e in edu_records:
        s, en = _period(e.get("year_start"), e.get("year_end"))
        if s is not None and en is not None:
            edu_periods.append({"label": e.get("degree_level") or "education",
                                 "start_year": s, "end_year": en})

    job_periods = []
    for j in exp_records:
        s, en = _period(j.get("start_date"), j.get("end_date"))
        if s is not None and en is not None:
            job_periods.append({"job_title": j.get("job_title") or "role",
                                 "organization": j.get("organization"),
                                 "start_year": s, "end_year": en})

    edu_emp_overlaps = [
        {"education": e["label"], "job_title": j["job_title"],
         "organization": j["organization"],
         "overlap_window": f"{max(e['start_year'],j['start_year'])}-{min(e['end_year'],j['end_year'])}"}
        for e in edu_periods for j in job_periods
        if _overlap(e["start_year"], e["end_year"], j["start_year"], j["end_year"])
    ]

    job_overlaps = [
        {"job_a": job_periods[i]["job_title"], "job_b": job_periods[j]["job_title"],
         "overlap_window": f"{max(job_periods[i]['start_year'],job_periods[j]['start_year'])}-"
                           f"{min(job_periods[i]['end_year'],job_periods[j]['end_year'])}"}
        for i in range(len(job_periods))
        for j in range(i + 1, len(job_periods))
        if _overlap(job_periods[i]["start_year"], job_periods[i]["end_year"],
                    job_periods[j]["start_year"], job_periods[j]["end_year"])
    ]

    sorted_jobs = sorted(job_periods, key=lambda x: (x["start_year"], x["end_year"]))
    prof_gaps: list[dict[str, Any]] = []
    for i in range(1, len(sorted_jobs)):
        prev_end   = sorted_jobs[i - 1]["end_year"]
        next_start = sorted_jobs[i]["start_year"]
        gap_yrs    = next_start - prev_end
        if gap_yrs <= 1:
            continue
        gs, ge = prev_end + 1, next_start - 1
        justified, note = _gap_justification(raw_text, gs, ge)
        prof_gaps.append({
            "gap_window":         f"{gs}-{ge}",
            "gap_duration_years": gap_yrs - 1,
            "is_justified":       justified,
            "justification_note": note or "No clear productive activity found.",
        })

    progression = "insufficient data"
    if len(sorted_jobs) >= 2:
        f = _job_level_score(sorted_jobs[0].get("job_title"))
        l = _job_level_score(sorted_jobs[-1].get("job_title"))
        progression = "upward" if l > f else "downward" if l < f else "stable"

    return {
        "records": exp_records,
        "timeline_checks": {
            "education_employment_overlaps": edu_emp_overlaps,
            "job_overlaps":                  job_overlaps,
            "professional_gaps":             prof_gaps,
            "progression_signal":            progression,
        },
        "summary": {
            "records_count":                    len(exp_records),
            "education_employment_overlap_count": len(edu_emp_overlaps),
            "job_overlap_count":                 len(job_overlaps),
            "professional_gap_count":            len(prof_gaps),
            "unjustified_gap_count":             sum(1 for g in prof_gaps if not g.get("is_justified")),
        },
    }
