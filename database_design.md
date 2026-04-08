# Database/Storage Design for TALASH

## Storage Approach: CSV + Excel (Relational format)

### Table 1: Personal_Info
| Column | Type | Description |
|--------|------|-------------|
| candidate_id | INT (PK) | Unique identifier |
| name | TEXT | Full name |
| email | TEXT | Email address |
| phone | TEXT | Contact number |

### Table 2: Education
| Column | Type |
|--------|------|
| candidate_id | INT (FK) |
| degree | TEXT |
| institution | TEXT |
| cgpa | FLOAT |
| year | INT |

### Table 3: Experience
| Column | Type |
|--------|------|
| candidate_id | INT (FK) |
| job_title | TEXT |
| company | TEXT |
| start_date | DATE |
| end_date | DATE |

### Table 4: Publications
| Column | Type |
|--------|------|
| candidate_id | INT (FK) |
| title | TEXT |
| venue | TEXT |
| year | INT |
| authors | TEXT |

### Table 5: Skills
| Column | Type |
|--------|------|
| candidate_id | INT (FK) |
| skill_name | TEXT |

## File Structure:
/data/
  ├── raw_cvs/ (original PDFs)
  ├── extracted/ (CSV files per candidate)
  └── consolidated/ (master Excel file)