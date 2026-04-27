"""
backend/modules/candidate_summary.py
Generates an initial LLM-based candidate summary from all analysis results.
"""
from __future__ import annotations

from typing import Any

from backend.modules.llm_client import ask_llm_text


async def generate_summary(
    personal_info: dict[str, Any],
    education:     dict[str, Any],
    experience:    dict[str, Any],
    research:      dict[str, Any],
    missing_fields: list[str],
) -> str:
    name    = personal_info.get("full_name") or "the candidate"
    highest = education.get("highest_qualification") or "unknown"
    exp_count = experience.get("summary", {}).get("records_count", 0)
    pub_count = research.get("summary", {}).get("publications_count", 0)
    gap_count = education.get("summary", {}).get("gap_count", 0)
    prog      = experience.get("timeline_checks", {}).get("progression_signal", "unknown")
    missing_str = ", ".join(missing_fields) if missing_fields else "none"

    prompt = (
        f"Candidate: {name}\n"
        f"Highest qualification: {highest}\n"
        f"Experience records found: {exp_count}\n"
        f"Publications found: {pub_count}\n"
        f"Educational gaps detected: {gap_count}\n"
        f"Career progression: {prog}\n"
        f"Missing information: {missing_str}\n\n"
        "Write a concise 3-4 sentence candidate summary for a recruiter. "
        "Mention strengths, any concerns, and overall suitability. Be professional and neutral."
    )

    try:
        return await ask_llm_text(
            system_prompt=(
                "You are an expert academic recruiter. Write brief, factual candidate summaries "
                "based on the structured profile data provided. Do not invent details."
            ),
            user_prompt=prompt,
            temperature=0.4,
            max_tokens=220,
        )
    except Exception as exc:
        return (
            f"{name.title()} holds a {highest} qualification with {exp_count} experience record(s) "
            f"and {pub_count} publication(s) detected. "
            f"Career progression is {prog}. "
            f"Missing fields: {missing_str}."
        )
