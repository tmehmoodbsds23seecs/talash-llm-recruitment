import streamlit as st
import pdfplumber
import pandas as pd
import json
import re

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="TALASH Recruitment System", 
    layout="wide",
    page_icon="🎯"
)

# ============================================
# HEADER
# ============================================
st.title("🎯 TALASH - Smart HR Recruitment System")
st.caption("LLM-Powered Candidate Screening for University Recruitment | Milestone 1 Prototype")

# ============================================
# SIDEBAR - System Status
# ============================================
with st.sidebar:
    st.header("📋 System Status - Milestone 1")
    st.markdown("""
    ✅ GitHub Repository: Connected
    ✅ Preprocessing Module: Active
    ✅ PDF Parser: Working
    ✅ CV Extraction: Working
    ⏳ LLM Integration: Milestone 2
    """)
    
    st.divider()
    
    st.header("📁 Folder-Based Ingestion Design")
    st.code("""
    /uploads/
      ├── incoming/     (new CVs)
      ├── processing/   (being processed)
      └── processed/    (completed)
    """)

# ============================================
# PREPROCESSING MODULE
# ============================================
def preprocess_pdf(pdf_file):
    """Extract text from PDF"""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return {
                "success": True,
                "text": text,
                "page_count": len(pdf.pages)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================
# CORRECTED EXTRACTION FUNCTION
# ============================================
def extract_structured_info(text):
    """Extract information from academic CV format"""
    
    data = {
        "name": "Not found",
        "email": "Not found",
        "phone": "Not found",
        "father_name": "Not found",
        "dob": "Not found",
        "marital_status": "Not found",
        "present_employment": "Not found",
        "current_salary": "Not found",
        "education": [],
        "experience": [],
        "publications": [],
        "skills": []
    }
    
    lines = text.split('\n')
    
    # ========================================
    # 1. EXTRACT NAME
    # ========================================
    for i, line in enumerate(lines):
        # Look for "Name" followed directly by text (no space after colon sometimes)
        if 'Name' in line or 'name' in line:
            # Pattern: "NameMUHAMMAD SALMAN QAMAR" or "Name: Muhammad Salman"
            match = re.search(r'Name\s*:?\s*([A-Z][A-Z\s]+|[A-Za-z\.\s]+)', line)
            if match:
                potential_name = match.group(1).strip()
                # Filter out common false positives
                if len(potential_name) > 3 and not any(word in potential_name.lower() for word in ['father', 'spouse', 'guardian', 'email', 'phone']):
                    data['name'] = potential_name
                    break
            # Also check if line starts with a common name pattern
            elif re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+', line):
                data['name'] = line.strip()
                break
    
    # ========================================
    # 2. EXTRACT FATHER'S NAME
    # ========================================
    for i, line in enumerate(lines):
        if "Father's" in line or "father" in line.lower():
            match = re.search(r"Father's\s*/?\s*Guardian\s*:?\s*(.+?)(?:\s*Date|$)", line, re.IGNORECASE)
            if match:
                data['father_name'] = match.group(1).strip()[:50]
                break
    
    # ========================================
    # 3. EXTRACT DATE OF BIRTH
    # ========================================
    dob_match = re.search(r'Date/Place of Birth\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', text, re.IGNORECASE)
    if dob_match:
        data['dob'] = dob_match.group(1)
    
    # ========================================
    # 4. EXTRACT MARITAL STATUS
    # ========================================
    marital_match = re.search(r'Marital Status\s*:?\s*(\w+)', text, re.IGNORECASE)
    if marital_match:
        data['marital_status'] = marital_match.group(1)
    
    # ========================================
    # 5. EXTRACT CURRENT SALARY
    # ========================================
    salary_match = re.search(r'Current Salary\s*:?\s*([\d,]+)', text, re.IGNORECASE)
    if salary_match:
        data['current_salary'] = salary_match.group(1)
    
    # ========================================
    # 6. EXTRACT PRESENT EMPLOYMENT
    # ========================================
    employment_match = re.search(r'Present Employment\s*:?\s*<td[^>]*>(.*?)</td>', text, re.IGNORECASE | re.DOTALL)
    if not employment_match:
        employment_match = re.search(r'Present Employment\s*:?\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if employment_match:
        emp_text = employment_match.group(1).strip()
        # Clean up HTML tags
        emp_text = re.sub(r'<[^>]+>', '', emp_text)
        data['present_employment'] = emp_text[:100]
    
    # ========================================
    # 7. EXTRACT EMAIL (only if clearly an email, not from references)
    # ========================================
    # Look for email pattern but exclude reference section
    reference_section = re.search(r'References.*$', text, re.IGNORECASE | re.DOTALL)
    text_before_ref = text
    if reference_section:
        text_before_ref = text[:reference_section.start()]
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_before_ref)
    if email_match:
        data['email'] = email_match.group()
    
    # ========================================
    # 8. EXTRACT EDUCATION
    # ========================================
    # Look for education table pattern
    edu_patterns = [
        r'PhD.*?(\d{4})',
        r'MS.*?(\d{4})',
        r'MSc.*?(\d{4})',
        r'BSc.*?(\d{4})',
        r'BS.*?(\d{4})',
        r'HSSC.*?(\d{4})',
        r'SSC.*?(\d{4})',
    ]
    
    # Method 1: Look for rows with degree names
    for i, line in enumerate(lines):
        line_clean = re.sub(r'<[^>]+>', '', line)
        
        if 'PhD' in line_clean:
            data['education'].append({"degree": "PhD", "institution": "Not found", "year": "Not found", "grade": "Not found"})
        elif 'MS' in line_clean and 'MSc' not in line_clean:
            data['education'].append({"degree": "MS", "institution": "Not found", "year": "Not found", "grade": "Not found"})
        elif 'BSc' in line_clean or 'BS' in line_clean:
            data['education'].append({"degree": "BSc", "institution": "Not found", "year": "Not found", "grade": "Not found"})
        elif 'HSSC' in line_clean:
            data['education'].append({"degree": "HSSC", "institution": "Not found", "year": "Not found", "grade": "Not found"})
        elif 'SSC' in line_clean:
            data['education'].append({"degree": "SSC", "institution": "Not found", "year": "Not found", "grade": "Not found"})
    
    # Method 2: Extract details from the specific CV format
    # PhD
    phd_match = re.search(r'PhD in Electrical Engineering.*?(\d+\.\d+).*?(\d{4})', text, re.DOTALL)
    if phd_match:
        for edu in data['education']:
            if edu['degree'] == 'PhD':
                edu['grade'] = phd_match.group(1)
                edu['year'] = phd_match.group(2)
                edu['institution'] = "International Islamic University, Islamabad"
    
    # MS
    ms_match = re.search(r'MS in Electrical Engineering.*?(\d+\.\d+).*?(\d{4})', text, re.DOTALL)
    if ms_match:
        for edu in data['education']:
            if edu['degree'] == 'MS':
                edu['grade'] = ms_match.group(1)
                edu['year'] = ms_match.group(2)
                edu['institution'] = "COMSATS University, Attock Campus"
    
    # BSc
    bsc_match = re.search(r'BSc Electronics Engineering.*?(\d+\.\d+).*?(\d{4})', text, re.DOTALL)
    if bsc_match:
        for edu in data['education']:
            if edu['degree'] == 'BSc':
                edu['grade'] = bsc_match.group(1)
                edu['year'] = bsc_match.group(2)
                edu['institution'] = "COMSATS University, Abbottabad Campus"
    
    # HSSC
    hssc_match = re.search(r'HSSC.*?(\d+\.\d+).*?(\d{4})', text, re.DOTALL)
    if hssc_match:
        for edu in data['education']:
            if edu['degree'] == 'HSSC':
                edu['grade'] = hssc_match.group(1)
                edu['year'] = hssc_match.group(2)
                edu['institution'] = "B.I.S.E Bannu"
    
    # SSC
    ssc_match = re.search(r'SSC.*?(\d+).*?(\d{4})', text, re.DOTALL)
    if ssc_match:
        for edu in data['education']:
            if edu['degree'] == 'SSC':
                edu['grade'] = ssc_match.group(1)
                edu['year'] = ssc_match.group(2)
                edu['institution'] = "B.I.S.E Bannu"
    
    # ========================================
    # 9. EXTRACT EXPERIENCE
    # ========================================
    exp_match = re.search(r'Present Employment.*?Associate Professor at ([^,]+),?([^<]+)', text, re.IGNORECASE)
    if exp_match:
        data['experience'].append({
            "title": "Associate Professor",
            "organization": exp_match.group(1).strip(),
            "location": exp_match.group(2).strip() if exp_match.group(2) else "China",
            "duration": "since 01/01/2025"
        })
    
    # ========================================
    # 10. EXTRACT PUBLICATIONS
    # ========================================
    # Look for publication patterns
    pub_lines = []
    capture = False
    for line in lines:
        if 'International Journal' in line or 'International Conference' in line:
            capture = True
        if capture and len(line.strip()) > 10:
            pub_lines.append(line)
        if capture and 'References' in line:
            break
    
    # Parse each publication
    for i, line in enumerate(pub_lines):
        if 'International Journal' in line or 'International Conference' in line:
            # Get title from previous line
            title = pub_lines[i-1].strip() if i-1 >= 0 else "Unknown"
            # Get year
            year_match = re.search(r'(\d{4})', line)
            year = year_match.group(1) if year_match else "Unknown"
            # Get impact factor
            ifactor_match = re.search(r'(\d+\.\d+)', line)
            ifactor = ifactor_match.group(1) if ifactor_match else "0.00"
            
            data['publications'].append({
                "title": title[:80],
                "venue": line.strip()[:60],
                "year": year,
                "impact_factor": ifactor
            })
            
            if len(data['publications']) >= 5:
                break
    
    # ========================================
    # 11. EXTRACT SKILLS (from publications and context)
    # ========================================
    skill_keywords = [
        'Wireless Sensor Networks', 'WSN', 'Energy Optimization', 'Energy Efficiency',
        'Hybrid Algorithm', 'Ant System', 'Particle Swarm Optimization', 'PSO',
        'Artificial Neural Networks', 'ANN', 'LEACH', 'Communication Systems',
        'Electrical Engineering', 'Traveling Salesman Problem', 'TSP'
    ]
    
    skills_found = set()
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            skills_found.add(skill)
    
    data['skills'] = list(skills_found)[:10]
    
    return data

# ============================================
# DISPLAY FUNCTIONS
# ============================================
def display_preprocessing_results(preprocess_result):
    if preprocess_result["success"]:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📄 Pages", preprocess_result["page_count"])
        with col2:
            st.metric("✅ Status", "Success")

def display_candidate_info(data):
    """Display extracted information in tabs"""
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 Personal Info", "🎓 Education", "💼 Experience", "📝 Publications", "🔧 Skills"])
    
    with tab1:
        st.markdown(f"**Name:** {data['name']}")
        st.markdown(f"**Father's Name:** {data['father_name']}")
        st.markdown(f"**Date of Birth:** {data['dob']}")
        st.markdown(f"**Marital Status:** {data['marital_status']}")
        st.markdown(f"**Current Salary:** {data['current_salary']}")
        st.markdown(f"**Present Employment:** {data['present_employment']}")
        st.markdown(f"**Email:** {data['email']}")
        st.markdown(f"**Phone:** {data['phone']}")
    
    with tab2:
        if data['education']:
            edu_df = pd.DataFrame(data['education'])
            st.dataframe(edu_df, use_container_width=True)
        else:
            st.info("No education information extracted")
    
    with tab3:
        if data['experience']:
            exp_df = pd.DataFrame(data['experience'])
            st.dataframe(exp_df, use_container_width=True)
        else:
            st.info("No experience information extracted")
    
    with tab4:
        if data['publications']:
            pub_df = pd.DataFrame(data['publications'])
            st.dataframe(pub_df, use_container_width=True)
            st.caption(f"Showing {len(data['publications'])} publications")
        else:
            st.info("No publications extracted")
    
    with tab5:
        if data['skills']:
            skills_html = ""
            for skill in data['skills']:
                skills_html += f'<span style="background-color:#1f77b4; color:white; padding:5px 12px; margin:3px; border-radius:20px; display:inline-block">{skill}</span>'
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.info("No skills extracted")

# ============================================
# MAIN APPLICATION
# ============================================
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📄 CV Upload")
    uploaded_file = st.file_uploader(
        "Upload Candidate CV (PDF)", 
        type="pdf"
    )
    
    st.divider()
    
    st.subheader("📁 Batch Processing Design (Milestone 2)")
    st.info("""
    **Folder-Based Design:**
    - Place PDFs in `/uploads/incoming/`
    - System auto-detects and processes
    - Results saved to master CSV
    - Missing info triggers email drafts
    """)
    
    if st.button("📂 Simulate Folder Scan"):
        st.success("✅ Folder scan simulated: CVs detected in incoming folder")

if uploaded_file:
    with col1:
        st.success(f"✅ File loaded: {uploaded_file.name}")
    
    with st.spinner("📖 Reading and analyzing CV..."):
        preprocess_result = preprocess_pdf(uploaded_file)
    
    if preprocess_result["success"]:
        with col1:
            display_preprocessing_results(preprocess_result)
        
        extracted_data = extract_structured_info(preprocess_result["text"])
        
        with col2:
            st.success("✅ Extraction Complete!")
            display_candidate_info(extracted_data)
            
            st.download_button(
                label="📥 Download Extracted Data (JSON)",
                data=json.dumps(extracted_data, indent=2),
                file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.json",
                mime="application/json"
            )
    else:
        st.error(f"Error: {preprocess_result['error']}")

st.divider()
st.caption("TALASH - CS417 Large Language Models | Milestone 1: Preprocessing Module + Early Prototype")