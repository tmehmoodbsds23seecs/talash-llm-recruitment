"""
backend/main.py
FastAPI backend for TALASH Milestone 2.

Endpoints:
  POST /analyze          – upload + analyze a single CV
  POST /analyze-folder   – analyze all PDFs in cv_inbox/
  GET  /candidates        – list all analyzed candidates (in-memory)
  GET  /candidate/{id}   – get full result for one candidate
  GET  /health           – Groq connectivity check
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from backend.modules.preprocessing      import (
    extract_text_from_pdf, build_structured_dataset, export_structured_dataset,
)
from backend.modules.education_analysis  import analyze_education
from backend.modules.experience_analysis import analyze_experience
from backend.modules.research_analysis   import analyze_research
from backend.modules.missing_info        import detect_missing_fields, draft_missing_info_email
from backend.modules.candidate_summary   import generate_summary
from backend.modules.llm_client          import check_groq_health

# ── Config ────────────────────────────────────────────────────────────────────
CV_INBOX   = Path(os.getenv("CV_INBOX",   "cv_inbox"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
CV_INBOX.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="TALASH API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: candidate_id → full result dict
_STORE: dict[str, dict[str, Any]] = {}


# ── Core pipeline ─────────────────────────────────────────────────────────────
async def run_pipeline(pdf_path: Path, candidate_id: str) -> dict[str, Any]:
    """
    Full Milestone 2 pipeline:
    1. PDF → raw text
    2. Regex-based structured extraction (preprocessing)
    3. Education analysis
    4. Experience analysis
    5. Research analysis (partial)
    6. Missing info detection
    7. Email draft
    8. Candidate summary (LLM)
    9. Export CSV / Excel
    """
    # 1. Extract text
    raw_text = extract_text_from_pdf(pdf_path)

    # 2. Build structured dataset
    dataset = build_structured_dataset(
        raw_text=raw_text,
        candidate_id=int(candidate_id[:8], 16) % 100000,  # numeric id from uuid
        filename=pdf_path.name,
    )
    personal = dataset.personal_info[0] if dataset.personal_info else {}

    # 3–5. Run analysis modules concurrently
    university = None
    if dataset.education_records:
        university = dataset.education_records[-1].get("institution_name")

    edu_task = analyze_education(raw_text, candidate_universities=university)
    exp_task = analyze_experience(raw_text)
    res_task = analyze_research(raw_text)

    education, experience, research = await asyncio.gather(edu_task, exp_task, res_task)

    # 6. Missing info
    missing = detect_missing_fields(personal, education, experience, research)

    # 7. Email draft
    email_draft = await draft_missing_info_email(personal.get("full_name"), missing)

    # 8. LLM summary
    summary = await generate_summary(personal, education, experience, research, missing)

    # 9. Export
    exports = export_structured_dataset(dataset, export_dir=EXPORT_DIR)

    result: dict[str, Any] = {
        "candidate_id":   candidate_id,
        "filename":       pdf_path.name,
        "personal_info":  personal,
        "education":      education,
        "experience":     experience,
        "research":       research,
        "missing_fields": missing,
        "email_draft":    email_draft,
        "summary":        summary,
        "metadata":       dataset.metadata,
        "exports":        exports,
    }
    _STORE[candidate_id] = result
    return result


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    groq = await check_groq_health()
    return {"api": "ok", **groq}


@app.post("/analyze")
async def analyze_single(file: UploadFile = File(...)):
    """Upload a PDF CV and get full analysis."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    cid      = str(uuid.uuid4())
    pdf_path = CV_INBOX / f"{cid}_{file.filename}"

    async with aiofiles.open(pdf_path, "wb") as fh:
        content = await file.read()
        await fh.write(content)

    try:
        result = await run_pipeline(pdf_path, cid)
    except Exception as exc:
        raise HTTPException(500, f"Pipeline error: {exc}")

    return result


@app.post("/analyze-folder")
async def analyze_folder():
    """Analyze all PDFs currently in the cv_inbox folder."""
    pdfs = list(CV_INBOX.glob("*.pdf"))
    if not pdfs:
        return {"message": "No PDF files found in cv_inbox/", "results": []}

    results = []
    for pdf_path in pdfs:
        cid = str(uuid.uuid4())
        try:
            res = await run_pipeline(pdf_path, cid)
            results.append({"filename": pdf_path.name, "candidate_id": cid, "status": "ok"})
        except Exception as exc:
            results.append({"filename": pdf_path.name, "status": "error", "detail": str(exc)})

    return {"processed": len(results), "results": results}


@app.get("/candidates")
async def list_candidates():
    """List all candidates processed in this session."""
    return [
        {
            "candidate_id": cid,
            "filename":     r.get("filename"),
            "name":         r.get("personal_info", {}).get("full_name"),
            "email":        r.get("personal_info", {}).get("email"),
            "highest_qual": r.get("education", {}).get("highest_qualification"),
            "pub_count":    r.get("research", {}).get("summary", {}).get("publications_count", 0),
            "missing_count":len(r.get("missing_fields", [])),
        }
        for cid, r in _STORE.items()
    ]


@app.get("/candidate/{candidate_id}")
async def get_candidate(candidate_id: str):
    if candidate_id not in _STORE:
        raise HTTPException(404, "Candidate not found.")
    return _STORE[candidate_id]
