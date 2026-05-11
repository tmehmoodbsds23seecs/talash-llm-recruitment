# 🛡️ TALASH: Milestone 3 - Smart HR Recruitment & Talent Analysis

Welcome to the production-ready version of **TALASH**. This system uses Advanced LLMs to analyze, score, and verify academic and professional CVs.

---

## 🚀 How to Run the Project Locally

### 1. Backend Setup (Python)
1. Navigate to the `backend` folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your API key:
   ```env
   OPENROUTER_API_KEY=your_key_here
   ```
4. Start the server:
   ```bash
   python main.py
   ```

### 2. Frontend Setup (React/Vite)
1. Navigate to the `frontend` folder.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dashboard:
   ```bash
   npm run dev
   ```

---

## ⚠️ Important Usage Tips (For Best Results)

### 1. CV Upload Limit
To ensure maximum accuracy and avoid "Rate Limit" errors from the AI, we recommend **uploading 1 CV at a time**.
*   The system includes automatic retry logic (Exponential Backoff), but single uploads provide the fastest results.

### 2. External Verification (eSearch)
When viewing a candidate, use the **eSearch** tab to verify research papers via CrossRef and PubMed APIs. This is a "Zero-Trust" module that confirms the credibility of the candidate's claims.

### 3. Aggregate Scoring
Each section (Education, Experience, etc.) is scored from 0-100. The **Status** tab provides the final hiring recommendation based on the combined weight of all sections.

---

## 🛠️ Tech Stack
*   **Frontend**: React, TypeScript, Vite, CSS (Glassmorphism).
*   **Backend**: FastAPI, SQLAlchemy, SQLite.
*   **AI**: OpenRouter (Gemini 2.0 Flash / GPT-OSS).
*   **APIs**: CrossRef, PubMed, OpenLibrary.

**TALASH | Smart Recruitment | Milestone 3**
