import re
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from extractor import normalize_skill_name

def calculate_weighted_match(job: Dict[str, Any], candidate_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a weighted match score strictly between 0 and 100:
    - Required skills: 50%
    - Experience: 25%
    - Preferred skills: 15%
    - Job/Resume text similarity (TF-IDF + Cosine): 10%
    """
    job_id = job["job_id"]
    candidate_id = candidate_info["candidate_id"]
    candidate_name = candidate_info["candidate_name"]
    extracted_skills = candidate_info.get("extracted_skills", [])
    extracted_exp = float(candidate_info.get("extracted_experience", 0.0))
    resume_text = candidate_info.get("resume_text", "")

    # 1. Normalize Job Skills & Candidate Skills
    req_skills_raw = job.get("required_skills", [])
    pref_skills_raw = job.get("preferred_skills", [])

    req_map = {normalize_skill_name(s).lower(): s for s in req_skills_raw}
    pref_map = {normalize_skill_name(s).lower(): s for s in pref_skills_raw}
    cand_skills_lower = {s.lower() for s in extracted_skills}

    # Match Required Skills
    matched_req_keys = set(req_map.keys()) & cand_skills_lower
    matched_required = [req_map[k] for k in matched_req_keys]
    missing_required = [req_map[k] for k in (set(req_map.keys()) - cand_skills_lower)]

    # Match Preferred Skills
    matched_pref_keys = set(pref_map.keys()) & cand_skills_lower
    matched_preferred = [pref_map[k] for k in matched_pref_keys]
    missing_preferred = [pref_map[k] for k in (set(pref_map.keys()) - cand_skills_lower)]

    # Combined matched skills
    all_matched_skills = sorted(list(set(matched_required + matched_preferred)))

    # 2. Required Skills Score (50%)
    if len(req_map) > 0:
        req_ratio = len(matched_required) / len(req_map)
        req_score = req_ratio * 50.0
    else:
        req_ratio = 1.0
        req_score = 50.0

    # 3. Experience Score (25%) & Status
    min_exp = float(job.get("min_experience", 0.0))
    if min_exp > 0:
        exp_ratio = min(1.0, extracted_exp / min_exp)
        exp_score = exp_ratio * 25.0
        if extracted_exp >= min_exp + 1.5:
            exp_status = f"Exceeds Requirement ({extracted_exp}y vs {min_exp}y req)"
        elif extracted_exp >= min_exp:
            exp_status = f"Meets Requirement ({extracted_exp}y vs {min_exp}y req)"
        else:
            exp_status = f"Below Requirement ({extracted_exp}y vs {min_exp}y req)"
    else:
        exp_ratio = 1.0
        exp_score = 25.0
        exp_status = f"Requirement Met ({extracted_exp}y experience)"

    # 4. Preferred Skills Score (15%)
    if len(pref_map) > 0:
        pref_ratio = len(matched_preferred) / len(pref_map)
        pref_score = pref_ratio * 15.0
    else:
        pref_ratio = 1.0
        pref_score = 15.0

    # 5. Text Similarity (TF-IDF & Cosine) Score (10%)
    job_combined_text = f"{job.get('job_title', '')} {job.get('job_description', '')} " \
                        f"{' '.join(req_skills_raw)} {' '.join(pref_skills_raw)}"
    
    sim_score = 0.0
    cosine_val = 0.0
    try:
        if job_combined_text.strip() and resume_text.strip():
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            tfidf_matrix = vectorizer.fit_transform([job_combined_text, resume_text])
            sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            cosine_val = float(sim_matrix[0][0])
            clamped_sim = max(0.0, min(1.0, cosine_val))
            sim_score = clamped_sim * 10.0
    except Exception:
        # Graceful fallback if vectorizer encountered no words
        sim_score = 5.0
        cosine_val = 0.5

    # 6. Final Weighted Match Score (0 - 100)
    total_raw = req_score + exp_score + pref_score + sim_score
    final_score = round(max(0.0, min(100.0, total_raw)), 2)

    # 7. Construct Human-Readable Match Explanation
    exp_summary_notes = []
    if len(req_map) > 0:
        exp_summary_notes.append(f"Matched {len(matched_required)}/{len(req_map)} required skills ({req_score:.1f} pts)")
        if missing_required:
            exp_summary_notes.append(f"lacking: {', '.join(missing_required)}")
    else:
        exp_summary_notes.append("No required skills defined (50 pts)")

    if len(pref_map) > 0:
        exp_summary_notes.append(f"matched {len(matched_preferred)}/{len(pref_map)} preferred skills ({pref_score:.1f} pts)")
        if missing_preferred:
            exp_summary_notes.append(f"lacking preferred: {', '.join(missing_preferred)}")

    exp_summary_notes.append(f"Experience: {exp_status} ({exp_score:.1f} pts)")
    exp_summary_notes.append(f"Text similarity: {sim_score:.1f} pts (cosine: {cosine_val:.2f})")
    match_explanation = ". ".join(exp_summary_notes) + "."

    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "match_score": final_score,
        "matched_skills": all_matched_skills,
        "missing_skills": missing_required,
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "extracted_experience": extracted_exp,
        "experience_match_status": exp_status,
        "match_explanation": match_explanation,
        "breakdown": {
            "required_skills_score": round(req_score, 2),
            "required_skills_max": 50.0,
            "experience_score": round(exp_score, 2),
            "experience_max": 25.0,
            "preferred_skills_score": round(pref_score, 2),
            "preferred_skills_max": 15.0,
            "similarity_score": round(sim_score, 2),
            "similarity_max": 10.0,
            "cosine_similarity": round(cosine_val, 4)
        }
    }
