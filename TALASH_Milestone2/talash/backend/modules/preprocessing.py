"""
backend/modules/preprocessing.py
Step 1 : Extract raw text from PDF  (pdfplumber)
Step 2 : Build structured dataset   (regex-based, your friend's logic)
Step 3 : Export to CSV / Excel      (pandas)
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))

DEGREE_KEYWORDS = {
    "SSE / Matric":        ["matric", "ssc", "secondary school", "o-level", "o level"],
    "HSSC / Intermediate": ["intermediate", "hssc", "fsc", "fa ", "ics", "a-level", "a level"],
    "BS / BSc":            ["bs ", "b.s", "bsc", "b.sc", "bachelor", "b.e", "be "],
    "MS / MPhil":          ["ms ", "m.s", "mphil", "m.phil", "master", "m.e", "me "],
    "PhD":                 ["phd", "ph.d", "doctor of philosophy"],
}

SKILL_KEYWORDS = {
    "Programming":      ["python", "java", "c++", "c#", "javascript", "typescript", "sql", "r "],
    "Data / Analytics": ["data analysis", "pandas", "numpy", "power bi", "tableau", "statistics"],
    "AI / ML":          ["machine learning", "deep learning", "nlp", "computer vision", "llm", "ai"],
    "Web / Software":   ["fastapi", "django", "flask", "react", "node", "api", "software"],
    "Academic":         ["research", "thesis", "publication", "journal", "conference", "supervisor"],
}

PUBLICATION_KEYWORDS  = ["journal", "conference", "proceedings", "publication", "paper", "article"]
EXPERIENCE_KEYWORDS   = [
    "experience", "employment", "worked", "position", "lecturer",
    "assistant professor", "intern", "engineer", "developer", "research assistant",
]


# ── Data class ────────────────────────────────────────────────────────────────
@dataclass
class StructuredDataset:
    candidate_id: int | None
    filename: str | None
    generated_at: str
    personal_info: list[dict[str, Any]]
    education_records: list[dict[str, Any]]
    experience_records: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    publications: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id":     self.candidate_id,
            "filename":         self.filename,
            "generated_at":     self.generated_at,
            "personal_info":    self.personal_info,
            "education_records":self.education_records,
            "experience_records":self.experience_records,
            "skills":           self.skills,
            "publications":     self.publications,
            "gaps":             self.gaps,
            "metadata":         self.metadata,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_whitespace(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _has_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)

def _extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))

def _extract_phones(text: str) -> list[str]:
    matches = re.findall(
        r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}(?:[\s-]?\d{3,4})?",
        text,
    )
    cleaned = []
    for m in matches:
        v = re.sub(r"\s+", " ", m).strip()
        if len(re.sub(r"\D", "", v)) >= 8:
            cleaned.append(v)
    return list(dict.fromkeys(cleaned))

def _extract_linkedin(text: str) -> list[str]:
    return list(dict.fromkeys(
        re.findall(r"https?://(?:www\.)?linkedin\.com/[\w\-./?=&%]+", text, flags=re.IGNORECASE)
    ))

def _find_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


# ── PDF Extraction (NEW — on top of friend's regex layer) ─────────────────────
def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF using pdfplumber. Returns empty string on failure."""
    parts: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
    except Exception as exc:
        return f"[PDF extraction error: {exc}]"
    return "\n\n".join(parts)


# ── Extraction functions (your friend's logic, unchanged) ─────────────────────
def extract_personal_info(raw_text: str, candidate_id: int | None = None,
                          filename: str | None = None) -> list[dict[str, Any]]:
    text = normalize_whitespace(raw_text)
    emails    = _extract_emails(text)
    phones    = _extract_phones(text)
    linkedins = _extract_linkedin(text)

    name_guess = None
    lines = _find_lines(raw_text)
    for line in lines[:12]:
        if any(tok in line.lower() for tok in ["cv", "resume", "curriculum vitae", "profile", "email", "phone"]):
            continue
        if 2 <= len(line.split()) <= 5 and not re.search(r"\d", line):
            name_guess = line
            break

    address_guess = None
    for line in lines:
        if _has_any(line, ["address","street","road","avenue","lane","city","town","sector","block"]) and len(line) > 12:
            address_guess = line
            break

    nationality_guess = None
    m = re.search(r"\b(nationality|citizenship)[:\-]?\s*([A-Za-z][A-Za-z\s-]{2,30})", raw_text, re.IGNORECASE)
    if m:
        nationality_guess = m.group(2).strip()

    return [{
        "candidate_id":  candidate_id,
        "filename":      filename,
        "full_name":     name_guess,
        "email":         emails[0]    if emails    else None,
        "phone":         phones[0]    if phones    else None,
        "address":       address_guess,
        "linkedin_url":  linkedins[0] if linkedins else None,
        "nationality":   nationality_guess,
    }]


def extract_education_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)
    degree_terms = [t for terms in DEGREE_KEYWORDS.values() for t in terms]

    for line in lines:
        lower = line.lower()
        if not _has_any(lower, degree_terms):
            continue
        degree_level = next(
            (label for label, terms in DEGREE_KEYWORDS.items() if _has_any(lower, terms)), None
        )
        years       = re.findall(r"\b(?:19|20)\d{2}\b", line)
        percentages = re.findall(r"\b\d{2,3}(?:\.\d+)?%\b", line)
        cgpas       = re.findall(
            r"\b\d(?:\.\d{1,2})?\s*/\s*\d(?:\.\d{1,2})?\b|\b\d(?:\.\d{1,2})?\s*cgpa\b",
            line, flags=re.IGNORECASE,
        )
        records.append({
            "candidate_id":       candidate_id,
            "degree_level":       degree_level,
            "degree_title":       line[:180],
            "specialization":     None,
            "institution_name":   None,
            "board_or_affiliation": None,
            "raw_result":         line,
            "cgpa_normalized":    None,
            "percentage_normalized": None,
            "year_start":         int(years[0])  if years       else None,
            "year_end":           int(years[-1]) if years       else None,
            "performance_note": "; ".join(filter(None, [
                f"percentage={percentages[0]}" if percentages else None,
                f"cgpa={cgpas[0]}"             if cgpas       else None,
            ])) or None,
        })
    return records


def extract_experience_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)
    for line in lines:
        lower = line.lower()
        if not _has_any(lower, EXPERIENCE_KEYWORDS):
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", line)
        org   = None
        for tok in [" at ", " in ", " @ ", " with "]:
            if tok in lower:
                org = line.split(tok, 1)[1].strip()
                break
        records.append({
            "candidate_id":    candidate_id,
            "job_title":       line[:160],
            "organization":    org,
            "employment_type": None,
            "start_date":      int(years[0])  if years else None,
            "end_date":        int(years[-1]) if years else None,
            "is_current":      bool(re.search(r"current|present", lower)),
            "responsibilities": line,
            "career_level":    None,
            "progression_note": None,
        })
    return records


def extract_skill_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    text    = raw_text.lower()
    records: list[dict[str, Any]] = []
    seen:   set[tuple[str, str]]  = set()

    for category, terms in SKILL_KEYWORDS.items():
        for term in terms:
            if term not in text:
                continue
            key = (term, category)
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "candidate_id":             candidate_id,
                "skill_name":               term,
                "skill_category":           category,
                "evidence_strength":        "partial",
                "supported_by_experience":  _has_any(text, EXPERIENCE_KEYWORDS),
                "supported_by_publications":_has_any(text, PUBLICATION_KEYWORDS),
                "evidence_note":            f"Detected keyword '{term}' in CV text.",
                "job_relevance_score":      None,
            })
    return records


def extract_publication_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)
    for line in lines:
        lower = line.lower()
        if not _has_any(lower, PUBLICATION_KEYWORDS):
            continue
        ym       = re.search(r"\b(?:19|20)\d{2}\b", line)
        pub_type = ("conference" if ("conference" in lower or "proceedings" in lower)
                    else "journal" if "journal" in lower else "publication")
        records.append({
            "candidate_id":           candidate_id,
            "pub_type":               pub_type,
            "title":                  line[:240],
            "authors_raw":            None,
            "year":                   int(ym.group(0)) if ym else None,
            "authorship_role":        None,
            "candidate_author_position": None,
            "quality_note":           line[:240],
        })
    return records


def detect_gaps(raw_text: str, education_records: list[dict[str, Any]],
                experience_records: list[dict[str, Any]], candidate_id: int | None = None) -> list[dict[str, Any]]:
    years: list[int] = []
    for rec in education_records:
        for k in ("year_start", "year_end"):
            v = rec.get(k)
            if isinstance(v, int):
                years.append(v)
    for rec in experience_records:
        for k in ("start_date", "end_date"):
            v = rec.get(k)
            if isinstance(v, int):
                years.append(v)
    years = sorted(set(years))
    gaps: list[dict[str, Any]] = []
    for i in range(1, len(years)):
        gap = years[i] - years[i - 1]
        if gap >= 3:
            gaps.append({
                "candidate_id":       candidate_id,
                "gap_between":        f"{years[i-1]}-{years[i]}",
                "gap_duration_months": gap * 12,
                "is_justified":       None,
                "justification_note": None,
            })
    return gaps


def build_structured_dataset(raw_text: str, candidate_id: int | None = None,
                              filename: str | None = None) -> StructuredDataset:
    cleaned    = normalize_whitespace(raw_text)
    now        = datetime.utcnow().isoformat(timespec="seconds")
    personal   = extract_personal_info(raw_text,    candidate_id=candidate_id, filename=filename)
    education  = extract_education_records(raw_text, candidate_id=candidate_id)
    experience = extract_experience_records(raw_text, candidate_id=candidate_id)
    skills     = extract_skill_records(raw_text,    candidate_id=candidate_id)
    pubs       = extract_publication_records(raw_text, candidate_id=candidate_id)
    gaps       = detect_gaps(raw_text, education, experience, candidate_id=candidate_id)

    detected = [
        label for label, terms in {
            "education":  ["education", "qualification", "academic"],
            "experience": ["experience", "employment", "career"],
            "research":   ["publication", "conference", "journal", "research"],
            "skills":     ["skills", "technical", "tools"],
        }.items()
        if _has_any(cleaned, terms)
    ]

    metadata = {
        "character_count":            len(raw_text or ""),
        "line_count":                 len(_find_lines(raw_text)),
        "detected_sections":          detected,
        "personal_info_completeness": sum(1 for v in personal[0].values() if v) if personal else 0,
        "education_records_count":    len(education),
        "experience_records_count":   len(experience),
        "skills_count":               len(skills),
        "publications_count":         len(pubs),
        "gaps_count":                 len(gaps),
    }
    return StructuredDataset(
        candidate_id=candidate_id, filename=filename, generated_at=now,
        personal_info=personal, education_records=education,
        experience_records=experience, skills=skills,
        publications=pubs, gaps=gaps, metadata=metadata,
    )


def export_structured_dataset(dataset: StructuredDataset,
                               export_dir: Path | None = None) -> dict[str, str]:
    base = export_dir or DEFAULT_EXPORT_DIR
    label = f"candidate_{dataset.candidate_id}" if dataset.candidate_id is not None else "dataset"
    target = base / label
    target.mkdir(parents=True, exist_ok=True)

    rows = {
        "personal_info":     dataset.personal_info,
        "education_records": dataset.education_records,
        "experience_records":dataset.experience_records,
        "skills":            dataset.skills,
        "publications":      dataset.publications,
        "gaps":              dataset.gaps,
    }
    csv_files: dict[str, str] = {}
    for name, table in rows.items():
        path = target / f"{name}.csv"
        fieldnames = sorted({k for row in table for k in row}) if table else []
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader(); w.writerows(table)
        csv_files[name] = str(path)

    wb_path = target / f"{label}_structured_profile.xlsx"
    with pd.ExcelWriter(wb_path, engine="openpyxl") as writer:
        for name, table in rows.items():
            pd.DataFrame(table).to_excel(writer, sheet_name=name[:31], index=False)
        pd.DataFrame([dataset.metadata]).to_excel(writer, sheet_name="summary", index=False)

    manifest = {
        "candidate_id": str(dataset.candidate_id) if dataset.candidate_id is not None else "",
        "filename":     dataset.filename or "",
        "generated_at": dataset.generated_at,
        "workbook_path": str(wb_path),
        "tables":        json.dumps(csv_files),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {"directory": str(target), "workbook": str(wb_path),
            "manifest": str(target / "manifest.json"), **csv_files}


def build_and_export_dataset(raw_text: str, candidate_id: int | None = None,
                              filename: str | None = None,
                              export_dir: Path | None = None) -> tuple[StructuredDataset, dict[str, str]]:
    ds = build_structured_dataset(raw_text=raw_text, candidate_id=candidate_id, filename=filename)
    ex = export_structured_dataset(ds, export_dir=export_dir)
    return ds, ex
