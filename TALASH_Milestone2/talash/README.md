#  TALASH — Milestone 2
**Talent Acquisition & Learning Automation for Smart Hiring**  
CS 417 · Large Language Models · Spring 2026 · BSDS-2K23

---

##  Quick Setup (do this once)

### 1. Clone / open the project in VS Code
```
code talash/
```

### 2. Create a virtual environment
```bash
python -m venv venv
```

Activate it:
- **Windows:**  `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API key
```bash
cp .env.example .env
```
Open `.env` and replace `gsk_your_groq_key_here` with your real key.  
Get a **free** key at → https://console.groq.com  
(No credit card needed. Very fast inference.)

---

##  Running the Application

You need **two terminals** open in VS Code (`Ctrl+Shift+`` ` twice).

### Terminal 1 — Start the FastAPI Backend
```bash
uvicorn backend.main:app --reload --port 8000
```
You should see: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2 — Start the Streamlit Frontend
```bash
streamlit run frontend/app.py
```
Browser opens automatically at → http://localhost:8501

---

##  Project Structure
```
talash/
├── backend/
│   ├── main.py                     ← FastAPI app (all endpoints)
│   └── modules/
│       ├── preprocessing.py        ← PDF text extraction + regex parsing
│       ├── education_analysis.py   ← Education profile analysis
│       ├── experience_analysis.py  ← Experience timeline analysis
│       ├── research_analysis.py    ← Partial research profile
│       ├── missing_info.py         ← Missing field detection + email drafts
│       ├── candidate_summary.py    ← LLM-generated summary
│       ├── qs_ranking_matcher.py   ← QS/THE ranking lookup
│       └── llm_client.py           ← Groq API wrapper
├── frontend/
│   └── app.py                      ← Streamlit UI (all screens)
├── cv_inbox/                       ← Drop PDFs here for folder analysis
├── exports/                        ← Auto-generated CSV/Excel outputs
├── qs_rankings/                    ← Optional: place QS Excel file here
├── .env.example                    ← Copy to .env and add your key
├── requirements.txt
└── README.md
```

---

## 🎬 Demo Flow (for evaluation)

1. Open app in browser (`http://localhost:8501`)
2. **Home / Upload** → upload a PDF CV → click Analyse
3. **Dashboard** → see bar charts, pie charts, comparison table
4. **Candidate Report** → click all 5 tabs:
   - Education (degree table, QS rank, gap chart)
   - Experience (Gantt timeline, gap analysis)
   - Research (publication breakdown, pie chart)
   - Missing Info (detected fields table)
   - Email Draft (personalized email, download button)
5. **Folder Analysis** → drop multiple PDFs in `cv_inbox/` → Process All

---

##  Milestone 2 Rubric Coverage

| Criterion | Marks | Where in app |
|-----------|-------|--------------|
| CV parsing & structured extraction | 6 | `preprocessing.py` → Education/Experience tabs |
| Educational profile analysis | 5 | Education tab → degree path, QS rank, gaps |
| Professional experience analysis | 4 | Experience tab → Gantt, gap analysis |
| Missing info detection & email drafting | 4 | Missing Info tab + Email Draft tab |
| Intermediate web app functionality | 6 | Full Streamlit app with 4 pages |
| **Total** | **25** | |

---

##  Optional: Add QS Rankings Excel

1. Download: https://www.topuniversities.com/world-university-rankings
2. Place the `.xlsx` file in `qs_rankings/` folder  
3. Name it exactly: `2026 QS World University Rankings 1.3 (For qs.com).xlsx`

Without the file, a built-in list of 20+ Pakistani + international universities is used automatically.

---

##  Troubleshooting

| Issue | Fix |
|-------|-----|
| `GROQ_API_KEY not set` | Check `.env` file exists and key is correct |
| `Cannot connect to backend` | Make sure `uvicorn` is running in Terminal 1 |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| PDF shows no text | The PDF may be image-scanned; try a text-based PDF |
| Slow analysis | Normal — Groq is processing; wait ~15-30 sec per CV |
