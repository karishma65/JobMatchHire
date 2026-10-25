import os
import uuid
import secrets
import logging
from typing import List, Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from schemas import (
    JobRequirementInput,
    JobRequirementResponse,
    ResumeAnalysisResponse,
    HealthStatus
)
import database
import extractor
import matcher
import ecce_engine
import report_generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [JobMatchHire Portal B] %(message)s")
logger = logging.getLogger("version_b")

# Environment configuration
VERSION_A_URL = os.getenv("VERSION_A_URL", "http://127.0.0.1:8000").rstrip("/")
PORT = int(os.getenv("PORT", "8001"))

app = FastAPI(
    title="JobMatchHire - Candidate Matching & Evaluation Backend (ECCE)",
    description="Service for resume parsing, contextual competency assessment (ECCE), deterministic scoring, report generation, and candidate privacy.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    database.init_db()
    logger.info("Version B Database initialized at version_b.db")

# ----------------- Core REST Endpoints -----------------

@app.get("/health", response_model=HealthStatus, tags=["System"])
async def health_check(check_peer: bool = True):
    """Expose health status and check connectivity with Version A"""
    va_status = None
    if check_peer:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"{VERSION_A_URL}/health?check_peer=false")
                va_status = (resp.status_code == 200)
        except Exception:
            va_status = False

    return HealthStatus(
        status="healthy",
        service="Version B - Resume Analysis & Matching",
        version="1.0.0",
        port=PORT,
        database_connected=True,
        version_a_connected=va_status
    )

@app.post("/jobs", response_model=JobRequirementResponse, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
async def receive_job_requirement(job: JobRequirementInput):
    """
    Endpoint called by Version A (POST /jobs).
    Receives and validates job requirements from Version A, saving them in Version B's SQLite database.
    """
    logger.info(f"Received and validated Job Requirement from Version A: ID={job.job_id}, Title='{job.job_title}'")
    saved = database.save_received_job(job.dict())
    return saved

@app.get("/jobs", response_model=List[JobRequirementResponse], tags=["Jobs"])
async def list_received_jobs(sync_from_a: bool = True):
    """List all job requirements, pulling latest real jobs from Version A if available"""
    if sync_from_a:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{VERSION_A_URL}/jobs")
                if resp.status_code == 200:
                    for j in resp.json():
                        database.save_received_job({
                            "job_id": j["job_id"],
                            "job_title": j["job_title"],
                            "job_description": j["job_description"],
                            "required_skills": j.get("required_skills", []),
                            "preferred_skills": j.get("preferred_skills", []),
                            "min_experience": float(j.get("min_experience", 0.0)),
                            "education_requirement": j.get("education_requirement", "Bachelor's Degree")
                        })
        except Exception as e:
            logger.warning(f"Could not pull jobs from Version A: {e}")

    return database.list_received_jobs()

@app.get("/jobs/{job_id}", response_model=JobRequirementResponse, tags=["Jobs"])
async def get_received_job(job_id: str):
    """Get single job requirement by ID"""
    job = database.get_received_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job requirement '{job_id}' not found in Version B.")
    return job

@app.post("/analyze-resume", response_model=ResumeAnalysisResponse, tags=["Resume Matching"])
async def analyze_and_match_resume(
    job_id: str = Form(..., description="Target Job ID"),
    resume_file: UploadFile = File(..., description="Resume file in .pdf, .docx, or .txt format"),
    candidate_name: Optional[str] = Form(None, description="Optional manual candidate name override"),
    candidate_id: Optional[str] = Form(None, description="Optional candidate identifier")
):
    """
    Core matching workflow:
    1. Validate job ID against received jobs.
    2. Read uploaded resume bytes (.pdf, .docx, or .txt).
    3. Extract text using pdfplumber / python-docx.
    4. Extract skills via predefined dictionary and experience via regex.
    5. Compute weighted match score (50% Req Skills, 25% Experience, 15% Pref Skills, 10% TF-IDF Cosine Similarity).
    6. Automatically dispatch result to Version A's POST /match-results endpoint.
    7. Save candidate evaluation in Version B's SQLite database.
    8. Return comprehensive analysis to client.
    """
    logger.info(f"Initiating resume analysis for Job '{job_id}', File: '{resume_file.filename}'")

    # 1. Fetch Target Job
    job = database.get_received_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404, 
            detail=f"Job '{job_id}' does not exist in Version B. Ensure it has been created and synced from Version A."
        )

    # 2. Read File Bytes
    try:
        file_bytes = await resume_file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    # 3. Extract Text from Resume
    try:
        resume_text = extractor.extract_text_from_resume(resume_file.filename, file_bytes)
        if not resume_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text could be extracted from the document. Please verify the file contains extractable text."
            )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error extracting resume text: {str(e)}")

    # 4. Extract Candidate Name, Skills, and Experience
    cand_id = candidate_id.strip() if candidate_id and candidate_id.strip() else f"CAN-{uuid.uuid4().hex[:6].upper()}"
    
    if candidate_name and candidate_name.strip():
        resolved_name = candidate_name.strip()
    else:
        resolved_name = extractor.extract_candidate_name(resume_text, resume_file.filename)

    extracted_skills = extractor.extract_skills_from_text(resume_text)
    extracted_experience = extractor.extract_experience_in_years(resume_text)

    # Calculate resume version for candidate and job
    prev_version = database.get_latest_resume_version(resolved_name, job_id)
    current_version = prev_version + 1

    # Generate secure candidate authorization token
    candidate_token = f"tok_{secrets.token_urlsafe(16)}"

    # 5. Compute Deterministic Weighted Matching Score
    candidate_payload = {
        "candidate_id": cand_id,
        "candidate_name": resolved_name,
        "resume_text": resume_text,
        "extracted_skills": extracted_skills,
        "extracted_experience": extracted_experience
    }
    match_result = matcher.calculate_weighted_match(job, candidate_payload)

    # 6. Run ECCE (Explainable Contextual Competency Engine)
    ecce_result = ecce_engine.run_ecce_evaluation(job, candidate_payload, match_result)
    evidence_summary = ecce_result.get("evidence_summary", "")
    eval_status = ecce_result.get("evaluation_status", "Evaluation Completed")

    # 7. Generate Individual Downloadable PDF Evaluation Report
    report_filename = f"{cand_id}_v{current_version}_report.pdf"
    report_path = os.path.join(report_generator.REPORTS_DIR, report_filename)
    try:
        report_generator.generate_ecce_pdf_report(ecce_result, output_path=report_path)
        logger.info(f"Generated ECCE PDF report for candidate {cand_id} (version {current_version})")
    except Exception as e:
        logger.error(f"Failed to generate PDF report for {cand_id}: {e}")
        report_path = ""

    # 8. Send Hiring-Related Results to Application A REST API
    # PRIVACY RULE: Do not send candidate's private learning guidance, token, or report path
    sync_status = "failed"
    sync_message = ""
    version_a_payload = {
        "job_id": job_id,
        "candidate_id": cand_id,
        "candidate_name": resolved_name,
        "match_score": match_result["match_score"],
        "matched_skills": match_result["matched_skills"],
        "missing_skills": match_result["missing_skills"],
        "extracted_experience": match_result["extracted_experience"],
        "experience_match_status": match_result["experience_match_status"],
        "evidence_summary": evidence_summary,
        "evaluation_status": eval_status
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{VERSION_A_URL}/match-results", json=version_a_payload)
            if resp.status_code in [200, 201]:
                sync_status = "synced"
                sync_message = f"Delivered to Version A ({VERSION_A_URL}/match-results)"
                logger.info(f"Successfully transmitted match results for Candidate {cand_id} to Version A.")
            else:
                sync_status = "failed"
                sync_message = f"Version A returned status {resp.status_code}: {resp.text}"
                logger.warning(f"Version A rejected match result: {resp.text}")
    except httpx.ConnectError:
        sync_status = "pending"
        sync_message = f"Version A is offline at {VERSION_A_URL}. Results saved in Version B."
        logger.warning(f"Version A offline at {VERSION_A_URL}. Saved locally.")
    except Exception as e:
        sync_status = "failed"
        sync_message = f"Transmission error to Version A: {str(e)}"
        logger.error(f"Error sending match results to Version A: {str(e)}")

    # 9. Store Complete Evaluation Record in Version B Database
    eval_record = {
        "candidate_id": cand_id,
        "job_id": job_id,
        "candidate_name": resolved_name,
        "resume_filename": resume_file.filename,
        "all_extracted_skills": extracted_skills,
        "matched_skills": match_result["matched_skills"],
        "missing_skills": match_result["missing_skills"],
        "extracted_experience": match_result["extracted_experience"],
        "experience_match_status": match_result["experience_match_status"],
        "match_score": match_result["match_score"],
        "breakdown": match_result["breakdown"],
        "candidate_token": candidate_token,
        "resume_version": current_version,
        "report_path": report_path,
        "evidence_summary": evidence_summary,
        "evaluation_status": eval_status,
        "ecce_data": ecce_result,
        "sync_to_version_a_status": sync_status,
        "sync_to_version_a_message": sync_message
    }
    saved_eval = database.save_candidate_evaluation(eval_record)

    report_url = f"/candidates/{cand_id}/report?token={candidate_token}"

    # 10. Return Response to Candidate
    return ResumeAnalysisResponse(
        job_id=job_id,
        candidate_id=cand_id,
        candidate_name=resolved_name,
        match_score=match_result["match_score"],
        matched_skills=match_result["matched_skills"],
        missing_skills=match_result["missing_skills"],
        missing_required_skills=match_result.get("missing_required_skills", []),
        missing_preferred_skills=match_result.get("missing_preferred_skills", []),
        extracted_experience=match_result["extracted_experience"],
        experience_match_status=match_result["experience_match_status"],
        match_explanation=match_result.get("match_explanation", ""),
        breakdown=match_result["breakdown"],
        extracted_skills_count=len(extracted_skills),
        all_extracted_skills=extracted_skills,
        candidate_token=candidate_token,
        resume_version=current_version,
        evaluation_status=eval_status,
        evidence_summary=evidence_summary,
        report_download_url=report_url,
        sync_to_version_a_status=sync_status,
        sync_to_version_a_message=sync_message,
        created_at=saved_eval.get("created_at", "")
    )

@app.get("/candidates/{candidate_id}/report", tags=["Candidate Reports"])
async def download_candidate_pdf_report(candidate_id: str, token: Optional[str] = Query(None, description="Candidate security token")):
    """
    Enforce Candidate-Only Access:
    Validates candidate access token to ensure only the authorized candidate downloads their report.
    Returns the individual ECCE PDF Evaluation Report.
    """
    cand = database.get_candidate_evaluation(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate evaluation not found.")

    stored_token = cand.get("candidate_token")
    if not token or not stored_token or token.strip() != stored_token.strip():
        logger.warning(f"Unauthorized report access attempt for candidate '{candidate_id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid or missing candidate authorization token. You may only access your own evaluation report."
        )

    report_path = cand.get("report_path")
    if not report_path or not os.path.exists(report_path):
        # Regenerate if missing
        ecce_data = cand.get("ecce_data")
        if ecce_data:
            report_path = report_generator.generate_ecce_pdf_report(ecce_data)
        else:
            raise HTTPException(status_code=404, detail="Evaluation report file is unavailable.")

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=f"{candidate_id}_v{cand.get('resume_version', 1)}_evaluation_report.pdf"
    )

@app.get("/candidates/{candidate_id}/status", tags=["Candidate Reports"])
async def get_candidate_evaluation_status(candidate_id: str, token: Optional[str] = Query(None, description="Candidate security token")):
    """
    Secure status verification for authenticated candidate.
    """
    cand = database.get_candidate_evaluation(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate evaluation not found.")

    stored_token = cand.get("candidate_token", "")
    if not token or not stored_token or token.strip() != stored_token.strip():
        raise HTTPException(status_code=403, detail="Unauthorized candidate token.")

    return {
        "candidate_id": cand["candidate_id"],
        "candidate_name": cand["candidate_name"],
        "job_id": cand["job_id"],
        "resume_version": cand.get("resume_version", 1),
        "evaluation_status": cand.get("evaluation_status", "Completed"),
        "match_score": cand["match_score"],
        "report_download_url": f"/candidates/{candidate_id}/report?token={token}",
        "created_at": cand["created_at"]
    }

@app.get("/candidates", tags=["Resume Matching"])
async def list_recent_candidates():
    """Candidate evaluation history is private and accessible only via individual token."""
    raise HTTPException(
        status_code=403,
        detail="Candidate evaluation history is private. Candidates may only access their individual results via authorized candidate token."
    )


# ----------------- Version B Frontend -----------------

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/style.css", include_in_schema=False)
async def get_css_root_b():
    return FileResponse(os.path.join(STATIC_DIR, "style.css"), media_type="text/css")

@app.get("/app.js", include_in_schema=False)
async def get_js_root_b():
    return FileResponse(os.path.join(STATIC_DIR, "app.js"), media_type="application/javascript")

@app.get("/landing.css", include_in_schema=False)
async def get_landing_css_root_b():
    return FileResponse(os.path.join(STATIC_DIR, "landing.css"), media_type="text/css")

@app.get("/landing.js", include_in_schema=False)
async def get_landing_js_root_b():
    return FileResponse(os.path.join(STATIC_DIR, "landing.js"), media_type="application/javascript")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_candidate_landing():
    landing_file = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(landing_file):
        with open(landing_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Candidate Portal</h1><p>Frontend static files not found.</p>")

@app.get("/portal", response_class=HTMLResponse, include_in_schema=False)
@app.get("/candidate", response_class=HTMLResponse, include_in_schema=False)
@app.get("/apply", response_class=HTMLResponse, include_in_schema=False)
async def serve_candidate_workspace():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Candidate Workspace</h1><p>Frontend static files not found.</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
