import os
import json
import re
import httpx
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-exp:free")

async def call_llm(messages: list, model: str = LLM_MODEL, temperature: float = 0.1) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in .env")

    cleaned_messages = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            content = re.sub(r'\bimage[\s]*\.png\b', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\.(png|jpg|jpeg|gif|bmp|tif|tiff|webp|svg)\b', '', content, flags=re.IGNORECASE)
        cleaned_messages.append({**msg, "content": content})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": cleaned_messages,
        "temperature": temperature,
    }

    import asyncio
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                
                if response.status_code == 429:
                    print(f"⚠️ Rate limited (429). Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"❌ LLM API Error: {e.response.status_code}. Retrying...")
                await asyncio.sleep(retry_delay)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"❌ LLM connection error: {str(e)}. Retrying...")
                await asyncio.sleep(retry_delay)
    
    raise Exception("Failed to call LLM after multiple retries due to rate limiting.")

async def parse_cv_with_llm(raw_text: str) -> dict:
    raw_text = re.sub(r'\.(png|jpg|jpeg|gif|bmp|tif|tiff|webp|svg)\b', '', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'https?://[^\s]*\.(png|jpg|jpeg|gif|bmp|tif|tiff|webp|svg)\b', '', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'[\r\n]+(Figure|Image|Photo|Picture|Screenshot|Scan)[\s\d:]*\n?', '\n', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'\bimage\d*\s*', '', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'\bscan\d*\s*', '', raw_text, flags=re.IGNORECASE)
    system_prompt = """You are an expert academic CV parser. Parse the CV text below and extract information into a structured JSON format.

Search carefully through the ENTIRE CV text for each section. Sections may have various headings - be thorough.

EXTRACT:

1. NAME & EMAIL:
   - name: Full name as it appears (check header, contact info)
   - email: Email address

2. EDUCATION:
   Look under: Education, Academic Background, Degrees, Qualifications
   For each: degree, specialization, institution, start_year, end_year, marks/gpa, level (sse/hssce/undergraduate/postgraduate/phd)

3. EXPERIENCE:
   Look under: Experience, Employment, Work History, Positions, Appointments
   For each: job_title, organization, start_date, end_date, description

4. SKILLS:
   Look under: Skills, Technical Skills, Competencies, Expertise
   For each: skill_name, category (technical/soft/domain)

5. PUBLICATIONS:
   Look under: Publications, Research Publications, Journal Papers, Conference Papers, Refereed Papers, Peer-Reviewed
   CRITICAL: Extract EVERY publication. Check all pages.
   For each: title, venue, year, authors, paper_type (journal/conference), authors_position (first/co-author), issn_doi

6. BOOKS:
   Look under: Books, Book Chapters, Publications (books only)
   For each: book_name, authors, isbn, publisher, year, link

7. PATENTS:
   Look under: Patents, IP, Intellectual Property
   For each: patent_number, title, date, inventors, country, link

8. SUPERVISION:
   Look under: Supervision, Supervised Students, Mentoring
   For each: student_name, degree_level (MS/PhD), role (main_supervisor/co_supervisor), year

Return ONLY valid JSON with this exact structure:
{
    "name": "Full Name",
    "email": "email@example.com",
    "education": [{"degree": "...", "specialization": "...", "institution": "...", "start_year": "...", "end_year": "...", "marks": "...", "level": "sse/hssce/undergraduate/postgraduate/phd"}],
    "experience": [{"job_title": "...", "organization": "...", "start_date": "...", "end_date": "...", "description": "..."}],
    "skills": [{"skill_name": "...", "category": "technical/soft/domain"}],
    "publications": [{"title": "...", "venue": "...", "year": "...", "authors": "...", "paper_type": "journal/conference", "authors_position": "first/co-author", "issn_doi": "..."}],
    "books": [{"book_name": "...", "authors": "...", "isbn": "...", "publisher": "...", "year": "...", "link": "..."}],
    "patents": [{"patent_number": "...", "title": "...", "date": "...", "inventors": "...", "country": "...", "link": "..."}],
    "supervision": [{"student_name": "...", "degree_level": "MS/PhD", "role": "main_supervisor/co_supervisor", "year": "..."}]
}

RULES:
- Return empty arrays [] for sections with no data
- Be THOROUGH - scan the entire CV
- Watch for numbered lists [1], [2] as publication markers
- Watch for DOIs starting with 10.
- For publications: extract ALL, do not skip any
- Return ONLY valid JSON, no markdown code blocks, no explanations"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ]

    response_text = await call_llm(messages, temperature=0.15)
    response_text = response_text.strip()

    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()

    try:
        result = json.loads(response_text)
        result.setdefault("education", [])
        result.setdefault("experience", [])
        result.setdefault("skills", [])
        result.setdefault("publications", [])
        result.setdefault("books", [])
        result.setdefault("patents", [])
        result.setdefault("supervision", [])
        return result
    except json.JSONDecodeError:
        try:
            start = response_text.index("{")
            end = response_text.rindex("}") + 1
            result = json.loads(response_text[start:end])
            result.setdefault("education", [])
            result.setdefault("experience", [])
            result.setdefault("skills", [])
            result.setdefault("publications", [])
            result.setdefault("books", [])
            result.setdefault("patents", [])
            result.setdefault("supervision", [])
            return result
        except Exception:
            raise ValueError(f"Failed to parse LLM response as JSON. Response was: {response_text[:800]}")


async def analyze_education(candidate_id: int, education_data: list, candidate_name: str) -> str:
    if not education_data:
        return "No education data available for analysis."

    education_text = json.dumps(education_data, indent=2)
    prompt = f"""You are an academic profile analyst. Analyze the following education records for {candidate_name} and provide a comprehensive assessment.

Education Data:
{education_text}

Provide analysis covering:
1. Academic performance summary across all levels
2. Educational progression and consistency
3. Detection of any gaps between educational stages (calculate years between stages)
4. Highest qualification achieved
5. Institutional quality and specialization continuity
6. Strengths and concerns in the educational profile

Be specific and quantitative where possible.
7. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Exceptional academic record (Distinctions, Top Universities, High GPA)
- 80-89: Very strong (Good GPA, Consistent progression)
- 70-79: Solid (Meets all requirements, no major gaps)
- 50-69: Average (Minor gaps or average grades)
- Below 50: Significant educational gaps or poor performance
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert academic profile analyst with deep knowledge of educational assessment, university rankings, and academic evaluation standards."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def analyze_experience(candidate_id: int, experience_data: list, candidate_name: str) -> str:
    if not experience_data:
        return "No experience data available for analysis."

    experience_text = json.dumps(experience_data, indent=2)
    prompt = f"""You are a professional experience analyst. Analyze the employment history of {candidate_name}.

Experience Data:
{experience_text}

Provide analysis covering:
1. Career progression and role advancement
2. Employment timeline consistency
3. Detection of gaps between jobs (calculate months/years)
4. Professional growth patterns
5. Skill development indicated by work history
6. Employment continuity issues or concerns
7. Overall career maturity and development

Be specific and quantitative where possible. Identify any overlaps between jobs or unexplained gaps.
8. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Outstanding career path with significant leadership/impact
- 80-89: Very strong professional growth and consistency
- 70-79: Solid experience with good role alignment
- 50-69: Average experience or minor career gaps
- Below 50: Lack of relevant experience or significant employment issues
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert professional profile analyst specializing in career development, employment analysis, and workforce evaluation."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def analyze_skills(candidate_id: int, skills_data: list, publications_data: list, candidate_name: str) -> str:
    skills_text = json.dumps(skills_data, indent=2)
    publications_text = json.dumps(publications_data, indent=2)

    prompt = f"""You are a skill alignment analyst. Evaluate the skill profile of {candidate_name}.

Skills Listed:
{skills_text}

Research Publications:
{publications_text}

Provide analysis covering:
1. Skill inventory and categorization
2. Skill-to-publication alignment (do publications support claimed skills?)
3. Skill breadth and depth assessment
4. Evidence strength for each major skill
5. Missing evidence for claimed skills (skills mentioned but not backed by work/publications)
6. Core strengths in the skill set
7. Potential skill gaps or overstatement concerns

Be specific about which skills are well-evidenced and which lack supporting documentation.
8. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Comprehensive skill set fully backed by publications/experience
- 80-89: Strong evidence for most claimed skills
- 70-79: Good skill set with reasonable supporting evidence
- 50-69: Basic skills or limited evidence for major claims
- Below 50: Significant skill gaps or lack of evidence
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert skill assessment analyst with deep knowledge of technical skills, research domains, and competency evaluation."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def analyze_research(candidate_id: int, publications_data: list, candidate_name: str) -> str:
    if not publications_data:
        return "## Research Profile Analysis\n\nNo publication data available for analysis. Unable to assess the research profile of this candidate."

    publications_text = json.dumps(publications_data, indent=2)
    prompt = f"""You are a senior research evaluation expert. Perform a detailed analysis of {candidate_name}'s research/publication profile.

## Publications Data:
{publications_text}

## Analysis Tasks:

### 1. PUBLICATION COUNT & BREAKDOWN
- Count total publications
- Categorize by type: journal articles vs conference papers
- Show exact numbers with percentages

### 2. AUTHORSHIP ANALYSIS
For EACH publication, determine the candidate's authorship role:
- FIRST AUTHOR: Candidate's name appears first in the author list
- CO-AUTHOR: Candidate appears in middle or end of author list
- CORRESPONDING: Candidate listed as corresponding author (flag this)

Count: X first-author papers, Y co-authored papers

### 3. VENUE QUALITY ASSESSMENT
For each publication, identify the venue quality:
- High-tier journals/conferences: IEEE Transactions, ACM, Nature, Science, ML conferences (NeurIPS, ICML, CVPR)
- Mid-tier: Other well-known journals/conferences
- General/Low-tier: Lesser-known venues

### 4. RESEARCH OUTPUT OVER TIME
Group publications by year and show trend:
Year: X publications
(Show a chronological view of research activity)

### 5. TOP PUBLICATIONS
List the 3-5 most significant publications based on:
- Venue quality (Q1 journals, top conferences)
- First-author position
- Relevance to specialization

### 6. COLLABORATION PATTERNS
- Analyze co-authorship networks
- Identify if candidate works with same collaborators
- Note international vs local collaborations (if identifiable)

### 7. VERIFICATION & INDEXING
- Note which publications have DOI/ISSN
- Flag any publications that seem incomplete or missing information

### 8. OVERALL RESEARCH STRENGTH
Provide a structured assessment:
- Research output volume: Low / Medium / High
- Publication quality: Low / Medium / High
- Leadership (first-author rate): Low / Medium / High
- H-index estimate (based on available data): X

Format your response with clear headers and bullet points. Be specific with numbers and percentages.
9. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Exceptional researcher (Many first-author papers, high-tier venues)
- 80-89: Very active researcher with strong quality output
- 70-79: Solid research profile with consistent publications
- 50-69: Developing researcher or moderate output
- Below 50: Very low output or quality concerns
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert research evaluation specialist with deep knowledge of academic publishing, journal quality assessment, conference rankings, and research metrics."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def analyze_books_patents(candidate_id: int, books_data: list, patents_data: list, candidate_name: str) -> str:
    books_text = json.dumps(books_data, indent=2)
    patents_text = json.dumps(patents_data, indent=2)

    prompt = f"""You are an intellectual output analyst. Evaluate the books and patents of {candidate_name}.

Books Authored/Co-Authored:
{books_text}

Patents:
{patents_text}

Provide analysis covering:
1. Book authorship count and role (sole author, co-author, etc.)
2. Publisher credibility assessment
3. Book contribution to academic/educational domain
4. Patent count and contribution areas
5. Innovation breadth (how many different domains have patents?)
6. Verification status of intellectual property claims
7. Combined assessment of academic and applied research output
8. Strengths and concerns

If either section is empty, note that clearly but still provide the overall assessment.
9. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Prolific author/inventor (Multiple books/patents)
- 80-89: Significant intellectual output
- 70-79: Good contribution beyond standard papers
- 50-69: Basic output (e.g., 1 book chapter)
- Below 50: No books or patents found
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert in intellectual property evaluation, academic publishing, and innovation assessment."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def analyze_supervision(candidate_id: int, supervision_data: list, candidate_name: str) -> str:
    if not supervision_data:
        return "No supervision data available for analysis."

    supervision_text = json.dumps(supervision_data, indent=2)
    prompt = f"""You are an academic mentorship analyst. Evaluate the supervision record of {candidate_name}.

Supervision Record:
{supervision_text}

Provide analysis covering:
1. Total supervised students count
2. Main supervisor vs co-supervisor roles
3. Degree level distribution (MS vs PhD)
4. Supervision output and student productivity
5. Academic leadership and mentorship maturity
6. Capacity building contribution
7. Assessment of supervision quality and engagement

If supervision data is limited, provide guidance on what additional information would be needed for comprehensive assessment.
8. FINAL SCORE: Provide a numeric score from 0-100.
SCORING SCALE:
- 90-100: Master mentor (Supervised multiple PhDs/MS to completion)
- 80-89: Experienced supervisor with solid student record
- 70-79: Active supervisor or co-supervisor
- 50-69: Early stage mentorship
- Below 50: No supervision record found
Format: [SCORE: XX] at the very end.
"""

    messages = [
        {"role": "system", "content": "You are an expert in academic mentorship, graduate supervision evaluation, and research capacity building assessment."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages)


async def verify_publication(title: str, venue: str, issn_doi: str = None) -> dict:
    """Verify publication via CrossRef API and other sources."""
    if not title:
        return {"verified": False, "method": "none", "detail": "No title provided"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if issn_doi and (issn_doi.startswith("10.") or "doi" in issn_doi.lower()):
                doi = issn_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "").strip()
                if doi.startswith("10."):
                    response = await client.get(
                        f"https://api.crossref.org/works/{doi}",
                        headers={"User-Agent": "TALASH/1.0 (mailto:talash@example.com)"}
                    )
                    if response.status_code == 200:
                        item = response.json().get("message", {})
                        return {
                            "verified": True,
                            "method": "crossref_doi",
                            "doi": doi,
                            "venue": (item.get("container-title", [""])[0] if item.get("container-title") else ""),
                            "year": item.get("published-print", {}).get("date-parts", [[]])[0][0] if item.get("published-print") else None,
                            "detail": f"Verified via DOI: {item.get('title', [''])[0][:80]}..."
                        }

            crossref_url = "https://api.crossref.org/works"
            params = {"query.title": title, "rows": 8}
            response = await client.get(crossref_url, params=params, headers={"User-Agent": "TALASH/1.0 (mailto:talash@example.com)"})

            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])

                for item in items:
                    item_title = item.get("title", [""])[0].lower()
                    if title.lower() in item_title or item_title in title.lower() or any(word in item_title for word in title.lower().split()[:4]):
                        venue_name = item.get("container-title", [""])[0] if item.get("container-title") else ""
                        doi = item.get("DOI", "")
                        year = item.get("published-print", {}).get("date-parts", [[]])[0][0] if item.get("published-print") else None
                        if not year:
                            year = item.get("published-online", {}).get("date-parts", [[]])[0][0] if item.get("published-online") else None

                        return {
                            "verified": True,
                            "method": "crossref",
                            "doi": doi,
                            "venue": venue_name or venue,
                            "year": year,
                            "detail": f"Found in CrossRef: {item_title[:80]}..."
                        }

                return {"verified": False, "method": "crossref", "detail": "Title not found in CrossRef database"}

            return {"verified": False, "method": "crossref", "detail": f"CrossRef API error: {response.status_code}"}

        except Exception as e:
            return {"verified": False, "method": "error", "detail": str(e)}


async def verify_book(book_name: str, isbn: str = None) -> dict:
    """Verify book via Open Library API."""
    if not book_name and not isbn:
        return {"verified": False, "method": "none", "detail": "No book name or ISBN provided"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if isbn:
                isbn = isbn.replace("-", "").replace(" ", "")
                url = f"https://openlibrary.org/isbn/{isbn}.json"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "verified": True,
                        "method": "openlibrary",
                        "title": data.get("title", book_name),
                        "authors": data.get("authors", []),
                        "detail": f"Found in Open Library: {data.get('title', book_name)}"
                    }
            
            search_url = "https://openlibrary.org/search.json"
            params = {"q": book_name, "limit": 5}
            response = await client.get(search_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("docs", [])
                
                for doc in docs:
                    doc_title = doc.get("title", "").lower()
                    if book_name.lower() in doc_title or doc_title in book_name.lower():
                        authors = doc.get("author_name", [])
                        isbn_list = doc.get("isbn", [])
                        return {
                            "verified": True,
                            "method": "openlibrary",
                            "title": doc.get("title"),
                            "authors": authors,
                            "isbn_found": isbn_list[0] if isbn_list else None,
                            "detail": f"Found in Open Library: {doc.get('title')} by {', '.join(authors[:2])}"
                        }
                
                return {"verified": False, "method": "openlibrary", "detail": f"Book '{book_name}' not found in Open Library"}
            
            return {"verified": False, "method": "openlibrary", "detail": f"Open Library API error: {response.status_code}"}
        
        except Exception as e:
            return {"verified": False, "method": "error", "detail": str(e)}


async def verify_patent(patent_number: str) -> dict:
    """Verify patent via Google Patents and USPTO."""
    if not patent_number or len(patent_number.strip()) < 3:
        return {"verified": False, "method": "none", "detail": "No patent number provided"}

    patent_number = patent_number.strip()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            google_url = f"https://patents.google.com/api/patent/rest-services/v2.0/patents/{patent_number}"
            headers = {"Accept": "application/json"}
            response = await client.get(google_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "verified": True,
                    "method": "google_patents",
                    "title": data.get("title", ""),
                    "detail": f"Patent verified: {patent_number}"
                }

            esp_url = f"https://worldwide.espacenet.com/webservices/IP/search/EPAPP/1.1/?applicationNumber={patent_number}"
            response = await client.get(esp_url, timeout=15.0)

            if response.status_code == 200:
                return {
                    "verified": True,
                    "method": "espacenet",
                    "detail": f"Patent {patent_number} found in Espacenet"
                }

            return {
                "verified": False,
                "method": "google_patents",
                "detail": f"Patent {patent_number} not found. Status: {response.status_code}"
            }

        except Exception as e:
            return {"verified": False, "method": "error", "detail": str(e)}


async def search_crossref(title: str, venue: str, issn_doi: str = None) -> dict:
    """Search CrossRef by DOI or title."""
    if not title:
        return {"verified": False, "source": "crossref"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if issn_doi and issn_doi.startswith("10."):
                doi = issn_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "").strip()
                response = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    headers={"User-Agent": "TALASH/1.0 (mailto:talash@example.com)"}
                )
                if response.status_code == 200:
                    item = response.json().get("message", {})
                    return {
                        "verified": True,
                        "source": "crossref",
                        "doi": doi,
                        "title": item.get("title", [""])[0],
                        "venue": (item.get("container-title", [""])[0] if item.get("container-title") else ""),
                        "year": item.get("published-print", {}).get("date-parts", [[None]])[0][0] or item.get("published-online", {}).get("date-parts", [[None]])[0][0],
                        "authors": [a.get("given", "") + " " + a.get("family", "") for a in item.get("author", [])],
                        "detail": f"Found via DOI"
                    }

            params = {"query.title": title, "rows": 5}
            response = await client.get(
                "https://api.crossref.org/works",
                params=params,
                headers={"User-Agent": "TALASH/1.0 (mailto:talash@example.com)"}
            )

            if response.status_code == 200:
                items = response.json().get("message", {}).get("items", [])
                title_lower = title.lower()
                for item in items:
                    item_title = item.get("title", [""])[0].lower()
                    if title_lower in item_title or item_title in title_lower or any(w in item_title for w in title_lower.split()[:4] if len(w) > 3):
                        doi = item.get("DOI", "")
                        year = item.get("published-print", {}).get("date-parts", [[None]])[0][0] or item.get("published-online", {}).get("date-parts", [[None]])[0][0]
                        return {
                            "verified": True,
                            "source": "crossref",
                            "doi": doi,
                            "title": item.get("title", [""])[0],
                            "venue": (item.get("container-title", [""])[0] if item.get("container-title") else ""),
                            "year": year,
                            "authors": [a.get("given", "") + " " + a.get("family", "") for a in item.get("author", [])],
                            "detail": f"Found by title match"
                        }

                return {"verified": False, "source": "crossref", "detail": "Not found in CrossRef"}
            return {"verified": False, "source": "crossref", "detail": "CrossRef API error"}
        except Exception as e:
            return {"verified": False, "source": "crossref", "detail": str(e)}


async def search_pubmed(title: str, year: str = None) -> dict:
    """Search PubMed E-utilities by title."""
    if not title:
        return {"verified": False, "source": "pubmed"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            search_params = {
                "db": "pubmed",
                "term": title,
                "retmax": 5,
                "retmode": "json",
                "sort": "relevance"
            }
            search_resp = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=search_params
            )

            if search_resp.status_code != 200:
                return {"verified": False, "source": "pubmed", "detail": "PubMed search failed"}

            search_data = search_resp.json()
            ids = search_data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                return {"verified": False, "source": "pubmed", "detail": "No PubMed results"}

            fetch_resp = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
            )

            if fetch_resp.status_code == 200:
                fetch_data = fetch_resp.json()
                result = fetch_data.get("result", {})
                for pubmed_id in ids:
                    pub = result.get(pubmed_id, {})
                    pub_title = pub.get("title", "").lower()
                    if title.lower() in pub_title or pub_title in title.lower() or any(w in pub_title for w in title.lower().split()[:4] if len(w) > 3):
                        return {
                            "verified": True,
                            "source": "pubmed",
                            "pubmed_id": pubmed_id,
                            "title": pub.get("title"),
                            "venue": pub.get("source", ""),
                            "year": pub.get("pubdate", "").split()[0] if pub.get("pubdate") else None,
                            "authors": [a.get("name", "") for a in pub.get("authors", [])],
                            "detail": f"Found in PubMed (ID: {pubmed_id})"
                        }

                return {"verified": False, "source": "pubmed", "detail": "No title match in results"}
            return {"verified": False, "source": "pubmed", "detail": "PubMed fetch failed"}
        except Exception as e:
            return {"verified": False, "source": "pubmed", "detail": str(e)}


async def verify_by_esearch(pubs: list) -> list:
    """Verify all publications via CrossRef + PubMed (no LLM)."""
    import asyncio

    async def verify_pub(pub):
        cr_result = await search_crossref(pub.get("title", ""), pub.get("venue", ""), pub.get("issn_doi", ""))
        pm_result = await search_pubmed(pub.get("title", ""), pub.get("year", ""))

        return {
            "id": pub.get("id"),
            "title": pub.get("title"),
            "venue": pub.get("venue"),
            "year": pub.get("year"),
            "doi": cr_result.get("doi") or "",
            "crossref_verified": cr_result.get("verified", False),
            "pubmed_verified": pm_result.get("verified", False),
            "crossref_detail": cr_result.get("detail", ""),
            "pubmed_detail": pm_result.get("detail", ""),
        }

    results = await asyncio.gather(*[verify_pub(p) for p in pubs])
    return list(results)


async def generate_missing_info_email(candidate_name: str, missing_fields: dict) -> str:
    prompt = f"""Draft a professional, polite email to request missing information from {candidate_name}.

Missing Information:
{json.dumps(missing_fields, indent=2)}

Write a complete, professional email that:
1. Introduces TALASH (Smart HR Recruitment system)
2. Politely requests the missing information
3. Lists the specific missing items clearly
4. Provides guidance on how to submit the information
5. Thanks the candidate for their time

Output only the email text, no extra commentary."""

    messages = [
        {"role": "system", "content": "You are a professional HR communication assistant that drafts polite, clear, and concise emails for recruitment purposes."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages, temperature=0.5)


async def generate_overall_summary(candidate_name: str, section_summaries: dict) -> str:
    summary_text = ""
    for section, data in section_summaries.items():
        summary_text += f"\n--- SECTION: {section.upper()} (Score: {data['score']}) ---\n{data['text']}\n"

    prompt = f"""You are a senior recruitment director. Provide a FINAL SUMMARY and HIRING RECOMMENDATION for {candidate_name} based on the following section analyses:
    
    {summary_text}
    
    Provide:
    1. A concise EXECUTIVE SUMMARY of the candidate (3-4 sentences)
    2. Key Strengths
    3. Potential Risks or Gaps
    4. FINAL VERDICT (Highly Recommended / Recommended / Consider with Caution / Not Recommended)
    5. FINAL SCORE: Provide an overall numeric score from 0-100.
    
    Format the score as [SCORE: XX] at the very end.
    
    SCORING SCALE:
    - 90-100: EXCEPTIONAL: Perfect fit, top-tier talent.
    - 80-89: STRONG: Very good candidate, highly capable.
    - 70-79: SOLID: Good fit, reliable professional.
    - 50-69: AVERAGE: Meets basic needs, some development required.
    - Below 50: WEAK: Significant gaps or misalignment.

    Keep the tone professional and decisive.
"""

    messages = [
        {"role": "system", "content": "You are a professional HR director with years of experience in high-level talent acquisition and candidate evaluation."},
        {"role": "user", "content": prompt}
    ]
    return await call_llm(messages, temperature=0.3)
