import re
import io
import os
from datetime import datetime
from typing import List, Tuple, Set, Dict, Any, Optional
import pdfplumber
import docx
from skills_dict import SKILLS_DICTIONARY, SKILL_ALIASES

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber with fallback"""
    text_content = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
    except Exception as e:
        # Fallback to simple extraction or pypdf if available
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                pt = page.extract_text()
                if pt:
                    text_content.append(pt)
        except Exception:
            raise RuntimeError(f"Could not extract text from PDF file: {str(e)}")

    return "\n".join(text_content).strip()

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx"""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    
    # Also extract any text within tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())
                    
    return "\n".join(paragraphs).strip()

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT with multiple encoding attempts"""
    for encoding in ["utf-8", "latin-1", "windows-1252", "utf-16"]:
        try:
            return file_bytes.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore").strip()

def extract_text_from_resume(filename: str, file_bytes: bytes) -> str:
    """Dispatches extraction based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_bytes)
    elif ext in [".txt", ".rtf"]:
        return extract_text_from_txt(file_bytes)
    else:
        # Attempt txt decode as fallback
        try:
            return extract_text_from_txt(file_bytes)
        except Exception:
            raise ValueError(f"Unsupported file format: {ext}. Please provide .pdf, .docx, or .txt")

def extract_candidate_name(resume_text: str, filename: str) -> str:
    """
    Extract candidate name using regex heuristics or filename fallback.
    """
    # 1. Look for explicit pattern: "Name: John Doe" or "Full Name: Jane Smith"
    name_pattern = re.search(r'(?:Name|Candidate\s*Name|Full\s*Name)\s*[:\-]\s*([A-Za-z\s\.\'\-]{2,40})', resume_text, re.IGNORECASE)
    if name_pattern:
        cand_name = name_pattern.group(1).strip()
        # Clean up any trailing labels like Email, Phone
        cand_name = re.split(r'\n|\r|email|phone|contact|address', cand_name, flags=re.IGNORECASE)[0].strip()
        if len(cand_name.split()) >= 1 and len(cand_name) > 2:
            return cand_name.title()

    # 2. Inspect the top non-empty lines (resumes usually start with the candidate name)
    lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
    for line in lines[:5]:
        # Filter out common titles, emails, phone numbers, or section headers
        if re.search(r'@|github|linkedin|resume|curriculum|phone|\+?\d{10}|summary|objective', line, re.IGNORECASE):
            continue
        cleaned = re.sub(r'[^A-Za-z\s\.\-]', '', line).strip()
        tokens = cleaned.split()
        if 1 <= len(tokens) <= 4 and 2 < len(cleaned) <= 35:
            return cleaned.title()

    # 3. Fallback: derive name from filename (e.g., "John_Doe_Resume.pdf" -> "John Doe")
    base = os.path.splitext(filename)[0]
    base = re.sub(r'resume|cv|biodata|profile|doc|pdf|\d+', '', base, flags=re.IGNORECASE)
    base = re.sub(r'[_\-\.\+]+', ' ', base).strip()
    if base and len(base) > 2:
        return base.title()

    return "Candidate"

def normalize_skill_name(skill: str) -> str:
    """Normalize skill name against known aliases and canonical forms"""
    s_lower = skill.strip().lower()
    return SKILL_ALIASES.get(s_lower, skill.strip())

def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract skills from resume text using word boundary regex matching
    against the predefined skills dictionary and synonym aliases.
    """
    text_lower = text.lower()
    found_skills: Set[str] = set()

    # Combine dictionary and alias terms, checking longer multi-word phrases first
    all_terms = list(set(list(SKILLS_DICTIONARY) + list(SKILL_ALIASES.keys())))
    all_terms.sort(key=lambda s: len(s), reverse=True)

    for skill in all_terms:
        s_norm = normalize_skill_name(skill)
        s_target = skill.lower()

        # Handle special characters in tech names like C++, C#, .NET
        if skill.lower() in ["c++", "cplusplus"]:
            pattern = r'(?:\bC\+\+|\bcplusplus\b)'
        elif skill.lower() in ["c#", "csharp"]:
            pattern = r'(?:\bC\#|\bcsharp\b)'
        elif skill.lower() in [".net", "dotnet"]:
            pattern = r'(?:\.NET|\bdotnet\b)'
        elif skill.lower() == "c":
            # Exact isolated 'C' language to avoid matching letter C in general text
            pattern = r'(?:(?:\bprogramming in\s+c\b)|(?:\bc language\b)|(?:\bc\/c\+\+\b)|(?:\bC\s*\,|\bC\s*\/))'
        elif skill.lower() == "r":
            # Exact R language
            pattern = r'(?:(?:\bR language\b)|(?:\bR programming\b)|(?:\bprogramming in\s+r\b))'
        elif skill.lower() in ["go", "golang"]:
            pattern = r'(?:\bgolang\b|\bgo language\b|\bprogramming in go\b)'
        else:
            escaped = re.escape(s_target)
            pattern = rf'\b{escaped}\b'

        if re.search(pattern, text_lower, re.IGNORECASE):
            found_skills.add(s_norm)

    return sorted(list(found_skills))

def extract_experience_in_years(text: str) -> float:
    """
    Extract candidate experience using regular expressions.
    Looks for explicit statements ("5+ years of experience", "3 yrs exp")
    and date ranges ("2019 - 2024", "2020 - Present").
    """
    extracted_years = 0.0
    text_clean = re.sub(r'\s+', ' ', text)

    # 1. Explicit experience statements:
    # Matches "5 years of experience", "3.5 yrs", "4+ years in backend development"
    explicit_matches = re.findall(
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:hands-on\s+)?(?:experience|exp|in|working))?',
        text_clean,
        re.IGNORECASE
    )
    if explicit_matches:
        vals = []
        for v in explicit_matches:
            try:
                num = float(v)
                # Filter out absurd numbers (e.g. year numbers like 2022 or age 25)
                if 0.5 <= num <= 40.0:
                    vals.append(num)
            except ValueError:
                pass
        if vals:
            extracted_years = max(vals)

    # 2. Date ranges in experience sections (e.g., 2018 - 2023, 2021 to Present)
    current_year = datetime.now().year
    date_range_matches = re.findall(
        r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(20\d\d)\s*(?:-|–|—|to)\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(Present|Current|Now|20\d\d)',
        text_clean,
        re.IGNORECASE
    )

    total_range_years = 0.0
    for start_yr_str, end_yr_str in date_range_matches:
        try:
            start_yr = int(start_yr_str)
            if end_yr_str.lower() in ["present", "current", "now"]:
                end_yr = current_year
            else:
                end_yr = int(end_yr_str)

            if end_yr >= start_yr and 2000 <= start_yr <= current_year and end_yr <= current_year + 1:
                diff = end_yr - start_yr
                # If same year, consider as 0.5 or 1 year
                diff = max(0.5, float(diff))
                total_range_years += diff
        except ValueError:
            continue

    # Use the higher estimation between explicit statement and parsed date intervals (capped at 40 years)
    final_years = max(extracted_years, min(total_range_years, 35.0))
    return round(final_years, 1)
