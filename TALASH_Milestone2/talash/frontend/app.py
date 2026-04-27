"""
frontend/app.py
TALASH Milestone 2 — Streamlit Frontend
Run:  streamlit run frontend/app.py
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(120.0)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TALASH – Smart HR Recruitment",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1B4F72, #1A8A5A);
        color: white; padding: 1.5rem 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2rem; }
    .main-header p  { color: #d0ede3; margin: 0.3rem 0 0; font-size: 1rem; }
    .metric-card {
        background: white; border: 1px solid #e8f4f0;
        border-left: 4px solid #1A8A5A;
        border-radius: 8px; padding: 1rem 1.2rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .metric-card .label { font-size: 0.75rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card .value { font-size: 1.8rem; font-weight: 700; color: #1B4F72; }
    .section-header {
        background: #f0f8f5; border-left: 4px solid #1A8A5A;
        padding: 0.6rem 1rem; border-radius: 0 8px 8px 0;
        font-weight: 600; color: #1B4F72; margin: 1.5rem 0 0.8rem;
    }
    .email-box {
        background: #f8fcfb; border: 1px solid #b8ddd2;
        border-radius: 8px; padding: 1.2rem;
        font-family: monospace; font-size: 0.85rem;
        white-space: pre-wrap; color: #2c3e50;
    }
    .summary-box {
        background: linear-gradient(135deg, #eaf4f0, #f0f8ff);
        border: 1px solid #b8ddd2; border-radius: 10px;
        padding: 1.2rem 1.5rem; font-size: 0.95rem; color: #1B4F72;
        line-height: 1.7;
    }
    .gap-badge-red   { background:#fde8e8; color:#c0392b; padding:2px 10px; border-radius:999px; font-size:0.78rem; }
    .gap-badge-green { background:#e8f8f0; color:#1A8A5A; padding:2px 10px; border-radius:999px; font-size:0.78rem; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def metric_card(label: str, value, col):
    col.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(f'<div class="section-header">📌 {title}</div>', unsafe_allow_html=True)


def api_get(path: str):
    try:
        r = httpx.get(f"{BACKEND}{path}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("❌ Cannot connect to backend. Make sure FastAPI is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post_file(path: str, file_bytes: bytes, filename: str):
    try:
        r = httpx.post(
            f"{BACKEND}{path}",
            files={"file": (filename, io.BytesIO(file_bytes), "application/pdf")},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("❌ Cannot connect to backend. Is FastAPI running?")
        return None
    except Exception as e:
        st.error(f"Upload error: {e}")
        return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 TALASH")
    st.markdown("**CS 417 – LLMs · Milestone 2**")
    st.divider()

    page = st.radio("Navigate", [
        "🏠 Home / Upload",
        "📊 Dashboard",
        "👤 Candidate Report",
        "📁 Folder Analysis",
    ])
    st.divider()

    health = api_get("/health")
    if health:
        status = health.get("status", "?")
        model  = health.get("model", "?")
        colour = "🟢" if status == "ok" else "🔴"
        st.markdown(f"{colour} **Groq:** {status}  \n🤖 **Model:** `{model}`")
    else:
        st.markdown("🔴 Backend offline")

    st.divider()
    st.caption("BSDS-2K23 · Spring 2026")
    st.caption("Prof. Dr. M. Moazam Fraz")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME / UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home / Upload":
    st.markdown("""
    <div class="main-header">
      <h1>🎯 TALASH</h1>
      <p>Talent Acquisition & Learning Automation for Smart Hiring · Milestone 2</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Upload a CV for Analysis")
    st.info("Upload a **PDF CV** — TALASH will parse it, analyse education, experience, research, detect missing info, and generate a personalised email draft.", icon="ℹ️")

    uploaded = st.file_uploader("Choose a PDF file", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        st.markdown(f"📄 **File:** `{uploaded.name}` ({uploaded.size / 1024:.1f} KB)")

        if st.button("🚀 Analyse CV", type="primary", use_container_width=True):
            with st.spinner("Running pipeline… PDF → Extract → Analyse → Summarise"):
                result = api_post_file("/analyze", uploaded.read(), uploaded.name)

            if result:
                st.session_state["last_result"]      = result
                st.session_state["last_candidate_id"] = result.get("candidate_id")
                st.success("✅ Analysis complete!")

                # Quick summary cards
                pi     = result.get("personal_info", {})
                edu    = result.get("education", {})
                exp    = result.get("experience", {})
                res    = result.get("research", {})
                mf     = result.get("missing_fields", [])

                c1, c2, c3, c4, c5 = st.columns(5)
                metric_card("Candidate",       pi.get("full_name") or "—",          c1)
                metric_card("Highest Degree",  edu.get("highest_qualification") or "—", c2)
                metric_card("Experience Roles",exp.get("summary",{}).get("records_count",0), c3)
                metric_card("Publications",    res.get("summary",{}).get("publications_count",0), c4)
                metric_card("Missing Fields",  len(mf),                              c5)

                st.markdown("---")
                st.markdown('<div class="summary-box">📝 ' + result.get("summary","") + '</div>',
                            unsafe_allow_html=True)

                st.markdown("---")
                st.info("Go to **👤 Candidate Report** in the sidebar for the full breakdown.", icon="👈")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.markdown("""
    <div class="main-header">
      <h1>📊 Dashboard</h1>
      <p>Aggregate view of all analysed candidates this session</p>
    </div>
    """, unsafe_allow_html=True)

    candidates = api_get("/candidates")
    if not candidates:
        st.warning("No candidates analysed yet. Upload CVs on the Home page.")
        st.stop()

    df = pd.DataFrame(candidates)

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    metric_card("Total CVs",          len(df),                                          c1)
    metric_card("With Publications",  int((df["pub_count"] > 0).sum()),                 c2)
    metric_card("Incomplete Profiles",int((df["missing_count"] > 0).sum()),             c3)
    metric_card("Avg Pub Count",      f'{df["pub_count"].mean():.1f}',                  c4)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # ── Bar: publications per candidate ───────────────────────────────────────
    with col_left:
        section("Publications per Candidate")
        fig = px.bar(
            df, x="name", y="pub_count",
            color="pub_count",
            color_continuous_scale=["#b8ddd2","#1A8A5A"],
            labels={"name": "Candidate", "pub_count": "Publications"},
            height=320,
        )
        fig.update_layout(margin=dict(t=10,b=10), coloraxis_showscale=False,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Pie: missing fields distribution ──────────────────────────────────────
    with col_right:
        section("Profile Completeness")
        complete   = int((df["missing_count"] == 0).sum())
        incomplete = len(df) - complete
        fig2 = go.Figure(go.Pie(
            labels=["Complete", "Has Missing Info"],
            values=[complete, incomplete],
            hole=0.5,
            marker_colors=["#1A8A5A", "#e74c3c"],
        ))
        fig2.update_layout(margin=dict(t=10,b=10), height=320,
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Qualification distribution ────────────────────────────────────────────
    section("Highest Qualification Distribution")
    qual_counts = df["highest_qual"].value_counts().reset_index()
    qual_counts.columns = ["Qualification", "Count"]
    fig3 = px.bar(
        qual_counts, x="Qualification", y="Count",
        color="Qualification",
        color_discrete_sequence=px.colors.qualitative.Set2,
        height=280,
    )
    fig3.update_layout(margin=dict(t=10,b=10), showlegend=False,
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    section("Candidate Comparison Table")
    display_df = df[["name","email","highest_qual","pub_count","missing_count"]].copy()
    display_df.columns = ["Name","Email","Highest Qualification","Publications","Missing Fields"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CANDIDATE REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👤 Candidate Report":
    st.markdown("""
    <div class="main-header">
      <h1>👤 Candidate Report</h1>
      <p>Full analysis breakdown for an individual candidate</p>
    </div>
    """, unsafe_allow_html=True)

    candidates = api_get("/candidates")

    # Pick candidate
    if not candidates:
        st.warning("No candidates analysed yet. Upload a CV first.")
        st.stop()

    options = {
        f"{c.get('name') or 'Unknown'} — {c.get('filename','')}": c["candidate_id"]
        for c in candidates
    }

    # Pre-select last uploaded if available
    default_label = None
    if "last_candidate_id" in st.session_state:
        for label, cid in options.items():
            if cid == st.session_state["last_candidate_id"]:
                default_label = label
                break

    selected_label = st.selectbox(
        "Select candidate",
        list(options.keys()),
        index=list(options.keys()).index(default_label) if default_label else 0,
    )
    selected_id = options[selected_label]

    data = api_get(f"/candidate/{selected_id}")
    if not data:
        st.stop()

    pi  = data.get("personal_info", {})
    edu = data.get("education", {})
    exp = data.get("experience", {})
    res = data.get("research", {})
    mf  = data.get("missing_fields", [])
    md  = data.get("metadata", {})

    # ── Header cards ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    metric_card("Name",     pi.get("full_name")  or "—", c1)
    metric_card("Email",    pi.get("email")       or "—", c2)
    metric_card("Phone",    pi.get("phone")       or "—", c3)
    metric_card("LinkedIn", pi.get("linkedin_url") or "—", c4)
    metric_card("Missing",  len(mf),                      c5)

    # ── AI Summary ────────────────────────────────────────────────────────────
    section("AI Candidate Summary")
    st.markdown(f'<div class="summary-box">📝 {data.get("summary","")}</div>',
                unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "🎓 Education",
        "💼 Experience",
        "📚 Research",
        "⚠️ Missing Info",
        "📧 Email Draft",
    ])

    # ────────────────────────────────────────────────────────────── EDUCATION ─
    with t1:
        section("Educational Profile")

        edu_sum = edu.get("summary", {})
        c1, c2, c3, c4 = st.columns(4)
        metric_card("Records Found",    edu_sum.get("records_count", 0),         c1)
        metric_card("Highest Degree",   edu.get("highest_qualification") or "—", c2)
        metric_card("Educational Gaps", edu_sum.get("gap_count", 0),             c3)
        qs = edu.get("qs_ranking_info", {})
        metric_card("QS Rank",
                    qs.get("qs_ranking") or "Not ranked / N/A",                  c4)

        records = edu.get("records", [])
        if records:
            section("Degree Records")
            df_edu = pd.DataFrame(records)
            # Show only useful columns
            cols = [c for c in ["degree_level","degree_title","year_start","year_end",
                                  "performance_note","qs_ranking"] if c in df_edu.columns]
            st.dataframe(df_edu[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No education records extracted.")

        gaps = edu.get("education_gaps", [])
        if gaps:
            section("Detected Gaps")
            for g in gaps:
                st.markdown(
                    f'<span class="gap-badge-red">⚠️ Gap: {g["gap_between"]} '
                    f'({g["gap_years"]} years)</span>',
                    unsafe_allow_html=True,
                )

        # Degree path chart
        if edu.get("degree_path"):
            section("Degree Path")
            dp = edu["degree_path"]
            years = edu.get("educational_years", list(range(len(dp))))
            fig = go.Figure(go.Scatter(
                x=years, y=list(range(1, len(dp)+1)),
                mode="lines+markers+text",
                text=dp, textposition="top center",
                line=dict(color="#1A8A5A", width=2),
                marker=dict(size=10, color="#1B4F72"),
            ))
            fig.update_layout(
                yaxis=dict(showticklabels=False),
                xaxis_title="Year", height=260,
                margin=dict(t=20,b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────────────────────────────── EXPERIENCE ──
    with t2:
        section("Professional Experience")

        exp_sum = exp.get("summary", {})
        tc      = exp.get("timeline_checks", {})
        c1, c2, c3, c4 = st.columns(4)
        metric_card("Roles Found",        exp_sum.get("records_count", 0),          c1)
        metric_card("Career Progression", tc.get("progression_signal", "—"),        c2)
        metric_card("Job Overlaps",        exp_sum.get("job_overlap_count", 0),      c3)
        metric_card("Prof. Gaps",          exp_sum.get("professional_gap_count", 0), c4)

        records = exp.get("records", [])
        if records:
            section("Employment Records")
            df_exp = pd.DataFrame(records)
            cols = [c for c in ["job_title","organization","start_date","end_date","is_current"]
                    if c in df_exp.columns]
            st.dataframe(df_exp[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No experience records extracted.")

        # Gantt-style chart
        if records:
            section("Career Timeline")
            chart_data = [
                {
                    "Role":  r.get("job_title", "")[:50],
                    "Start": r.get("start_date"),
                    "End":   r.get("end_date") or r.get("start_date"),
                }
                for r in records
                if r.get("start_date") and r.get("end_date")
            ]
            if chart_data:
                df_chart = pd.DataFrame(chart_data)
                fig = px.timeline(
                    df_chart.assign(
                        Start=pd.to_datetime(df_chart["Start"].astype(str) + "-01-01"),
                        End  =pd.to_datetime(df_chart["End"].astype(str)   + "-12-31"),
                    ),
                    x_start="Start", x_end="End", y="Role",
                    color="Role",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(showlegend=False, height=max(200, len(chart_data)*40+60),
                                  margin=dict(t=10,b=10),
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        # Gaps & overlaps
        prof_gaps = tc.get("professional_gaps", [])
        if prof_gaps:
            section("Professional Gaps")
            for g in prof_gaps:
                badge = "gap-badge-green" if g.get("is_justified") else "gap-badge-red"
                label = "✅ Justified" if g.get("is_justified") else "⚠️ Unexplained"
                st.markdown(
                    f'<span class="{badge}">{label} · {g["gap_window"]} '
                    f'({g["gap_duration_years"]}y)</span><br>'
                    f'<small style="color:#7f8c8d">{g.get("justification_note","")}</small><br><br>',
                    unsafe_allow_html=True,
                )

        edu_emp = tc.get("education_employment_overlaps", [])
        if edu_emp:
            section("Education–Employment Overlaps")
            st.dataframe(pd.DataFrame(edu_emp), use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────────────── RESEARCH ───
    with t3:
        section("Research Profile (Partial)")

        res_sum = res.get("summary", {})
        c1, c2, c3, c4 = st.columns(4)
        metric_card("Total Publications", res_sum.get("publications_count", 0), c1)
        metric_card("Journal Papers",     res_sum.get("journal_count", 0),      c2)
        metric_card("Conference Papers",  res_sum.get("conference_count", 0),   c3)
        metric_card("Other",              res_sum.get("other_count", 0),        c4)

        qn = res_sum.get("quality_note")
        if qn:
            st.markdown(f'<div class="summary-box">🔬 {qn}</div>', unsafe_allow_html=True)

        pubs = res.get("publications", [])
        if pubs:
            section("Publication Records")
            df_pub = pd.DataFrame(pubs)
            cols = [c for c in ["pub_type","title","year","authorship_role","quality_note"]
                    if c in df_pub.columns]
            st.dataframe(df_pub[cols], use_container_width=True, hide_index=True)

            # Pub type pie
            if res_sum.get("publications_count", 0) > 0:
                fig = go.Figure(go.Pie(
                    labels=["Journal", "Conference", "Other"],
                    values=[
                        res_sum.get("journal_count",0),
                        res_sum.get("conference_count",0),
                        res_sum.get("other_count",0),
                    ],
                    hole=0.45,
                    marker_colors=["#1A8A5A","#1B4F72","#7f8c8d"],
                ))
                fig.update_layout(height=280, margin=dict(t=10,b=10),
                                  paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No publications detected in this CV.")

    # ─────────────────────────────────────────────────────── MISSING INFO ───
    with t4:
        section("Missing Information Detection")

        if not mf:
            st.success("✅ No missing critical information detected in this profile.")
        else:
            st.error(f"⚠️ {len(mf)} missing field(s) detected:")
            for item in mf:
                st.markdown(f"- **{item.title()}**")

        # Skills table
        skills = data.get("metadata", {})
        section("Detected Skills")
        ds = api_get(f"/candidate/{selected_id}")
        if ds:
            raw_skills = ds.get("metadata", {})
            # skills come from dataset — load via metadata skills count
            skill_count = raw_skills.get("skills_count", 0)
            st.metric("Skills Detected", skill_count)

        # Metadata table
        section("Profile Metadata")
        meta_display = {k: v for k, v in md.items() if k != "detected_sections"}
        st.dataframe(
            pd.DataFrame([meta_display]).T.rename(columns={0: "Value"}),
            use_container_width=True,
        )

        detected_secs = md.get("detected_sections", [])
        if detected_secs:
            st.markdown("**Detected CV Sections:**  " +
                        "  |  ".join(f"✅ `{s}`" for s in detected_secs))

    # ──────────────────────────────────────────────────────── EMAIL DRAFT ───
    with t5:
        section("Personalised Email Draft")

        if not mf:
            st.success("✅ No missing info — confirmation email below.")
        else:
            st.warning(f"Email drafted for **{len(mf)} missing field(s)**.")

        email_text = data.get("email_draft", "")
        st.markdown(f'<div class="email-box">{email_text}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(
                "⬇️ Download Email",
                data=email_text,
                file_name=f"email_{pi.get('full_name','candidate').replace(' ','_')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ── Download Excel ────────────────────────────────────────────────────────
    st.markdown("---")
    section("Download Structured Data")
    exports = data.get("exports", {})
    wb_path = exports.get("workbook")
    if wb_path and Path(wb_path).exists():
        with open(wb_path, "rb") as fh:
            st.download_button(
                "⬇️ Download Full Excel Report",
                data=fh.read(),
                file_name=f"TALASH_{pi.get('full_name','candidate').replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=False,
            )
    else:
        st.info("Excel export will appear here after analysis.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FOLDER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Folder Analysis":
    st.markdown("""
    <div class="main-header">
      <h1>📁 Folder Analysis</h1>
      <p>Batch-process all PDFs in the cv_inbox/ folder</p>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "Place PDF CV files in the **`cv_inbox/`** folder inside the project directory, "
        "then click the button below to process all of them at once.",
        icon="📂",
    )

    inbox_path = Path("cv_inbox")
    pdfs = list(inbox_path.glob("*.pdf")) if inbox_path.exists() else []
    st.markdown(f"**PDFs in inbox:** {len(pdfs)}")
    if pdfs:
        for p in pdfs:
            st.markdown(f"  - `{p.name}`")

    if st.button("⚡ Process All CVs in Inbox", type="primary", use_container_width=True):
        with st.spinner("Processing folder..."):
            result = api_get("/analyze-folder")  # GET triggers folder processing
            if result is None:
                try:
                    r = httpx.post(f"{BACKEND}/analyze-folder", timeout=TIMEOUT)
                    result = r.json()
                except Exception as e:
                    st.error(str(e))

        if result:
            st.success(f"✅ Processed {result.get('processed',0)} files.")
            for r in result.get("results", []):
                icon = "✅" if r.get("status") == "ok" else "❌"
                st.markdown(f"{icon} `{r['filename']}` — {r.get('status')}")

            st.info("Go to **📊 Dashboard** to see results.")
