import os
import json
import re
import sqlite3
from PyPDF2 import PdfReader
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict

from database import init_db, get_db
import services

class MissingInfoRequest(BaseModel):
    missing_fields: dict

class AnalysisRequest(BaseModel):
    section: str

app = FastAPI(title="TALASH API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()



@app.get("/")
async def root():
    return {"message": "TALASH API is running", "status": "healthy"}


@app.get("/test-llm")
async def test_llm():
    try:
        result = await services.call_llm([
            {"role": "user", "content": "Say 'LLM is working!' in exactly those words."}
        ])
        return {"status": "ok", "response": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    import traceback
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        pdf_path = os.path.join(upload_dir, file.filename)
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print(f"\n📄 PDF saved: {pdf_path}")

        raw_text = extract_text_from_pdf(pdf_path)
        raw_text = re.sub(r'\.(png|jpg|jpeg|gif|bmp|tif|tiff|webp|svg)\b', '', raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r'https?://[^\s]*\.(png|jpg|jpeg|gif|bmp|tif|tiff|webp|svg)\b', '', raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r'[\r\n]+(Figure|Image|Photo|Picture|Screenshot|Scan)[\s\d:]*\n?', '\n', raw_text, flags=re.IGNORECASE)

        print(f"📝 Extracted {len(raw_text)} chars of text")
        print(f"🤖 Calling LLM ({services.LLM_MODEL})...")

        parsed_data = await services.parse_cv_with_llm(raw_text)

        print(f"✅ LLM parsed: {parsed_data.get('name', 'Unknown')}")

        candidate_id = save_candidate_to_db(parsed_data, pdf_path)

        print(f"💾 Saved to DB: candidate_id={candidate_id}")

        return {
            "candidate_id": candidate_id,
            "message": "CV parsed successfully",
            "name": parsed_data.get("name", "Unknown"),
            "sections": list(parsed_data.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ UPLOAD FAILED: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        raise HTTPException(status_code=500, detail=f"Upload failed: {type(e).__name__}: {str(e)}")



@app.get("/candidates")
async def list_candidates():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.email, c.pdf_path, c.created_at, 
                   IFNULL(AVG(ar.score), 0) as avg_score
            FROM candidates c
            LEFT JOIN analysis_results ar ON c.id = ar.candidate_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """)
        rows = cursor.fetchall()
        return [{"id": r["id"], "name": r["name"], "email": r["email"],
                 "pdf_path": r["pdf_path"], "created_at": r["created_at"],
                 "score": round(r["avg_score"], 1)} for r in rows]


@app.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        def fetch_table(table):
            try:
                cursor.execute(f"SELECT * FROM {table} WHERE candidate_id = ?", (candidate_id,))
                return [dict(row) for row in cursor.fetchall()]
            except Exception:
                return []

        return {
            "candidate": dict(candidate),
            "education": fetch_table("education"),
            "experience": fetch_table("experience"),
            "skills": fetch_table("skills"),
            "publications": fetch_table("publications"),
            "books": fetch_table("books"),
            "patents": fetch_table("patents"),
            "supervision": fetch_table("supervision"),
        }


@app.get("/candidates/{candidate_id}/section/{section}")
async def load_section_facts(candidate_id: int, section: str):
    valid_sections = ["education", "experience", "skills", "publications", "books", "patents", "supervision", "overall", "esearch"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section")

    if section in ["overall", "esearch"]:
        return {"candidate_id": candidate_id, "section": section, "data": [], "count": 0}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        cursor.execute(f"SELECT * FROM {section} WHERE candidate_id = ?", (candidate_id,))
        rows = [dict(row) for row in cursor.fetchall()]

        return {
            "candidate_id": candidate_id,
            "candidate_name": candidate["name"],
            "section": section,
            "data": rows,
            "count": len(rows)
        }


@app.post("/candidates/{candidate_id}/esearch")
async def run_esearch(candidate_id: int):
    """Search publications via CrossRef and PubMed - no LLM."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        cursor.execute("SELECT * FROM publications WHERE candidate_id = ?", (candidate_id,))
        pubs = [dict(row) for row in cursor.fetchall()]

        if not pubs:
            return {"candidate_id": candidate_id, "results": [], "count": 0}

        results = await services.verify_by_esearch(pubs)
        return {"candidate_id": candidate_id, "results": results, "count": len(results)}


@app.post("/candidates/{candidate_id}/verify/{section}")
async def verify_section(candidate_id: int, section: str):
    """Manually trigger verification for publications, books, or patents."""
    if section not in ["publications", "books", "patents"]:
        raise HTTPException(status_code=400, detail="Only publications/books/patents can be verified")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        cursor.execute(f"SELECT * FROM {section} WHERE candidate_id = ?", (candidate_id,))
        rows = [dict(row) for row in cursor.fetchall()]

        if not rows:
            return {"candidate_id": candidate_id, "section": section, "verified_count": 0, "results": []}

        import asyncio

        async def verify_row(row):
            if row.get("verified"):
                return {"id": row["id"], "verified": 1, "detail": row.get("verification_detail", "Already verified")}

            if section == "publications":
                v = await services.verify_publication(row.get("title", ""), row.get("venue", ""), row.get("issn_doi", ""))
            elif section == "books":
                v = await services.verify_book(row.get("book_name", ""), row.get("isbn", ""))
            else:
                v = await services.verify_patent(row.get("patent_number", ""))

            cursor.execute(f"UPDATE {section} SET verified = ?, verification_detail = ? WHERE id = ?",
                (1 if v.get("verified") else 0, v.get("detail"), row["id"]))

            return {"id": row["id"], "verified": 1 if v.get("verified") else 0, "detail": v.get("detail")}

        results = await asyncio.gather(*[verify_row(row) for row in rows])
        conn.commit()

        verified_count = sum(1 for r in results if r["verified"] == 1)
        return {"candidate_id": candidate_id, "section": section, "verified_count": verified_count, "total": len(rows), "results": results}


@app.post("/candidates/{candidate_id}/analyze/{section}")
async def run_section_analysis(candidate_id: int, section: str):
    valid_sections = ["education", "experience", "skills", "research", "books_patents", "supervision", "overall"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        candidate_name = candidate["name"]

        if section == "education":
            cursor.execute("SELECT * FROM education WHERE candidate_id = ?", (candidate_id,))
            data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_education(candidate_id, data, candidate_name)

        elif section == "experience":
            cursor.execute("SELECT * FROM experience WHERE candidate_id = ?", (candidate_id,))
            data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_experience(candidate_id, data, candidate_name)

        elif section == "skills":
            cursor.execute("SELECT * FROM skills WHERE candidate_id = ?", (candidate_id,))
            skills_data = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM publications WHERE candidate_id = ?", (candidate_id,))
            pub_data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_skills(candidate_id, skills_data, pub_data, candidate_name)

        elif section == "research":
            cursor.execute("SELECT * FROM publications WHERE candidate_id = ?", (candidate_id,))
            data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_research(candidate_id, data, candidate_name)

        elif section == "books_patents":
            cursor.execute("SELECT * FROM books WHERE candidate_id = ?", (candidate_id,))
            books_data = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM patents WHERE candidate_id = ?", (candidate_id,))
            patents_data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_books_patents(candidate_id, books_data, patents_data, candidate_name)

        elif section == "supervision":
            cursor.execute("SELECT * FROM supervision WHERE candidate_id = ?", (candidate_id,))
            data = [dict(row) for row in cursor.fetchall()]
            analysis = await services.analyze_supervision(candidate_id, data, candidate_name)

        elif section == "overall":
            cursor.execute("SELECT section, analysis_output, score FROM analysis_results WHERE candidate_id = ? AND section != 'overall'", (candidate_id,))
            rows = cursor.fetchall()
            if not rows:
                return {
                    "candidate_id": candidate_id,
                    "section": section,
                    "analysis": "⚠️ No sectional analyses found. Please run 'LLM Analysis' on individual sections (Education, Experience, Skills, etc.) first so I can synthesize a final verdict.",
                    "score": 0
                }
            summaries = {r["section"]: {"text": r["analysis_output"], "score": r["score"]} for r in rows}
            analysis = await services.generate_overall_summary(candidate_name, summaries)

        # Robust score extraction
        import re
        score = 0
        
        # Try multiple patterns for score
        patterns = [
            r'\[SCORE:\s*(\d+)\]',  # [SCORE: 85]
            r'SCORE:\s*(\d+)',       # SCORE: 85
            r'Rating:\s*(\d+)',      # Rating: 85
            r'Score is\s*(\d+)',     # Score is 85
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                break
        
        # Fallback for "overall" section: if LLM fails, use average of other sections
        if score == 0 and section == "overall":
            cursor.execute("SELECT score FROM analysis_results WHERE candidate_id = ? AND section != 'overall'", (candidate_id,))
            other_scores = [r["score"] for r in cursor.fetchall() if r["score"] > 0]
            if other_scores:
                score = int(sum(other_scores) / len(other_scores))
                print(f"ℹ️ Fallback score for overall: {score}")

        cursor.execute(
            "INSERT OR REPLACE INTO analysis_results (candidate_id, section, analysis_output, score) VALUES (?, ?, ?, ?)",
            (candidate_id, section, analysis, score)
        )
        conn.commit()

    return {
        "candidate_id": candidate_id,
        "section": section,
        "analysis": analysis,
        "score": score
    }


@app.get("/candidates/{candidate_id}/analysis/{section}")
async def get_section_analysis(candidate_id: int, section: str):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT analysis_output, score, analyzed_at FROM analysis_results WHERE candidate_id = ? AND section = ?",
                (candidate_id, section)
            )
            result = cursor.fetchone()
            if not result:
                return {"analysis": None, "score": 0, "message": "No analysis available. Run analysis first."}
            return {
                "candidate_id": candidate_id,
                "section": section,
                "analysis": result["analysis_output"],
                "score": result["score"],
                "analyzed_at": result["analyzed_at"]
            }
    except Exception:
        return {"analysis": None, "score": 0, "message": "No analysis available. Run analysis first."}


@app.post("/candidates/{candidate_id}/email-draft")
async def draft_missing_info_email(candidate_id: int, request: MissingInfoRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        candidate_name = candidate["name"]

    print(f"📧 [API] Drafting email for Candidate ID: {candidate_id} ({candidate_name})")
    print(f"📧 [API] Missing Fields: {json.dumps(request.missing_fields, indent=2)}")
    
    try:
        email = await services.generate_missing_info_email(candidate_name, request.missing_fields)
        if not email:
            raise ValueError("LLM returned empty email draft")
        
        print(f"✅ [API] Email draft generated successfully ({len(email)} chars)")
        return {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "email_draft": email
        }
    except Exception as e:
        print(f"❌ [API] Email drafting error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI drafting error: {str(e)}")


@app.get("/candidates/{candidate_id}/score")
async def get_overall_score(candidate_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM analysis_results WHERE candidate_id = ?", (candidate_id,))
        scores = [r["score"] for r in cursor.fetchall()]
        if not scores:
            return {"overall_score": 0, "count": 0, "scores": []}
        avg_score = sum(scores) / len(scores)
        return {"overall_score": round(avg_score, 1), "count": len(scores), "scores": scores}


@app.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        tables = ["education", "experience", "skills", "publications", "books", "patents", "supervision", "analysis_results"]
        for table in tables:
            cursor.execute(f"DELETE FROM {table} WHERE candidate_id = ?", (candidate_id,))
        cursor.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        conn.commit()
        return {"message": f"Candidate {candidate_id} deleted"}


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    text = re.sub(r'\.(png|jpg|jpeg|gif|bmp|tif|tiff|svg)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\r\n]+\s*(?:Figure|Image|Photo|Picture)\s*\d*', '\n', text, flags=re.IGNORECASE)
    return text


def save_candidate_to_db(parsed_data: dict, pdf_path: str) -> int:
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "talash.db"))
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO candidates (name, email, raw_text, pdf_path) VALUES (?, ?, ?, ?)",
        (
            parsed_data.get("name"),
            parsed_data.get("email"),
            json.dumps(parsed_data),
            pdf_path
        )
    )
    candidate_id = cursor.lastrowid

    for edu in parsed_data.get("education", []):
        cursor.execute(
            "INSERT INTO education (candidate_id, degree, specialization, institution, start_year, end_year, marks, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (candidate_id, edu.get("degree"), edu.get("specialization"), edu.get("institution"),
             edu.get("start_year"), edu.get("end_year"), edu.get("marks"), edu.get("level"))
        )

    for exp in parsed_data.get("experience", []):
        cursor.execute(
            "INSERT INTO experience (candidate_id, job_title, organization, start_date, end_date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (candidate_id, exp.get("job_title"), exp.get("organization"), exp.get("start_date"),
             exp.get("end_date"), exp.get("description"))
        )

    for skill in parsed_data.get("skills", []):
        cursor.execute(
            "INSERT INTO skills (candidate_id, skill_name, category) VALUES (?, ?, ?)",
            (candidate_id, skill.get("skill_name"), skill.get("category"))
        )

    for pub in parsed_data.get("publications", []):
        cursor.execute(
            "INSERT INTO publications (candidate_id, title, venue, year, authors, paper_type, authors_position, issn_doi) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (candidate_id, pub.get("title"), pub.get("venue"), pub.get("year"),
             pub.get("authors"), pub.get("paper_type"), pub.get("authors_position"), pub.get("issn_doi"))
        )

    for book in parsed_data.get("books", []):
        cursor.execute(
            "INSERT INTO books (candidate_id, book_name, authors, isbn, publisher, year, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (candidate_id, book.get("book_name"), book.get("authors"), book.get("isbn"),
             book.get("publisher"), book.get("year"), book.get("link"))
        )

    for patent in parsed_data.get("patents", []):
        cursor.execute(
            "INSERT INTO patents (candidate_id, patent_number, title, date, inventors, country, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (candidate_id, patent.get("patent_number"), patent.get("title"), patent.get("date"),
             patent.get("inventors"), patent.get("country"), patent.get("link"))
        )

    for sup in parsed_data.get("supervision", []):
        cursor.execute(
            "INSERT INTO supervision (candidate_id, student_name, degree_level, role, year) VALUES (?, ?, ?, ?, ?)",
            (candidate_id, sup.get("student_name"), sup.get("degree_level"), sup.get("role"), sup.get("year"))
        )

    conn.commit()
    conn.close()
    return candidate_id


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)