"""
backend/modules/research_analysis.py
Partial research profile processing (Milestone 2).
Extracts and categorises publications from CV text.
"""
from __future__ import annotations

from typing import Any

from backend.modules.preprocessing import extract_publication_records
from backend.modules.llm_client import ask_llm_text


async def analyze_research(raw_text: str) -> dict[str, Any]:
    """Partial research profile — pub counts, types, and LLM quality summary."""
    publications = extract_publication_records(raw_text)

    journal_count    = sum(1 for p in publications if p.get("pub_type") == "journal")
    conference_count = sum(1 for p in publications if p.get("pub_type") == "conference")
    other_count      = len(publications) - journal_count - conference_count

    # Quick LLM quality note (only if pubs exist and text is long enough)
    quality_note = None
    if publications and len(raw_text) > 200:
        try:
            quality_note = await ask_llm_text(
                system_prompt=(
                    "You are a research profile evaluator. "
                    "Given the CV text, write 2-3 sentences summarising the research profile strength. "
                    "Focus on: publication venues, research areas, and authorship. Be concise."
                ),
                user_prompt=raw_text[:3000],
                temperature=0.4,
                max_tokens=180,
            )
        except Exception:
            quality_note = "LLM summary unavailable."

    return {
        "publications":  publications,
        "summary": {
            "publications_count":   len(publications),
            "journal_count":        journal_count,
            "conference_count":     conference_count,
            "other_count":          other_count,
            "quality_note":         quality_note,
            "is_partial_processing": True,
        },
    }
