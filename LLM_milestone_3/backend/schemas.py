from pydantic import BaseModel
from typing import Optional, List

class EducationEntry(BaseModel):
    degree: str
    specialization: Optional[str] = None
    institution: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    marks: Optional[str] = None
    level: str

class ExperienceEntry(BaseModel):
    job_title: str
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class SkillEntry(BaseModel):
    skill_name: str
    category: Optional[str] = None

class PublicationEntry(BaseModel):
    title: str
    venue: Optional[str] = None
    year: Optional[str] = None
    authors: Optional[str] = None
    paper_type: str
    authors_position: Optional[str] = None

class BookEntry(BaseModel):
    book_name: str
    authors: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[str] = None
    link: Optional[str] = None

class PatentEntry(BaseModel):
    patent_number: Optional[str] = None
    title: str
    date: Optional[str] = None
    inventors: Optional[str] = None
    country: Optional[str] = None
    link: Optional[str] = None

class SupervisionEntry(BaseModel):
    student_name: Optional[str] = None
    degree_level: str
    role: str
    year: Optional[str] = None

class CandidateData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    education: List[EducationEntry] = []
    experience: List[ExperienceEntry] = []
    skills: List[SkillEntry] = []
    publications: List[PublicationEntry] = []
    books: List[BookEntry] = []
    patents: List[PatentEntry] = []
    supervision: List[SupervisionEntry] = []