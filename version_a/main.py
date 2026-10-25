import os
import logging
from typing import List, Optional
import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from schemas import (
    JobCreate,
    JobResponse,
    CandidateResultCreate,
    CandidateResultResponse,
    RankedCandidatesResponse,
    HealthStatus
)
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [JobMatchHire Portal A] %(message)s")
logger = logging.getLogger("version_a")

# Environment configuration
VERSION_B_URL = os.getenv("VERSION_B_URL", "http://127.0.0.1:8001").rstrip("/")
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(
    title="JobMatchHire - Recruiter & Job Management Backend",
    description="Backend service for job postings, sending requirements to Application B, and ranking candidates by ECCE evaluation scores.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    database.init_db()
    logger.info("Version A Database initialized at version_a.db")

# ----------------- Core REST Endpoints -----------------

@app.get("/health", response_model=HealthStatus, tags=["System"])
async def health_check(check_peer: bool = True):
    """Expose health status and check connectivity with Version B"""
    vb_status = None
    if check_peer:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"{VERSION_B_URL}/health?check_peer=false")
                vb_status = (resp.status_code == 200)
        except Exception:
            vb_status = False

    return HealthStatus(
        status="healthy",
        service="Version A - Recruitment & Job Management",
        version="1.0.0",
        port=PORT,
        database_connected=True,
        version_b_connected=vb_status
    )

@app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
async def create_job(job: JobCreate):
    """
    1. Save job requirement in SQLite database.
    2. Dispatch job requirements to Version B through REST API via HTTP and JSON.
    """
    logger.info(f"Received request to create Job: {job.job_id} - '{job.job_title}'")
    
    # Save locally first
    saved = database.save_job(job.dict(), sync_status="pending", sync_message="Sending to Version B...")

    # Forward to Version B
    sync_status = "failed"
    sync_message = ""
    payload = {
        "job_id": job.job_id,
        "job_title": job.job_title,
        "job_description": job.job_description,
        "required_skills": job.required_skills,
        "preferred_skills": job.preferred_skills,
        "min_experience": job.min_experience,
        "education_requirement": job.education_requirement
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{VERSION_B_URL}/jobs", json=payload)
            if resp.status_code in [200, 201]:
                sync_status = "synced"
                sync_message = f"Successfully synced with Version B ({VERSION_B_URL})"
                logger.info(f"Job {job.job_id} successfully synced to Version B.")
            else:
                sync_status = "failed"
                sync_message = f"Version B responded with status {resp.status_code}: {resp.text}"
                logger.warning(f"Version B rejected job {job.job_id}: {resp.text}")
    except httpx.ConnectError:
        sync_status = "pending"
        sync_message = f"Version B is currently offline at {VERSION_B_URL}. Job saved locally; can sync later."
        logger.warning(f"Could not connect to Version B at {VERSION_B_URL}. Saved locally.")
    except Exception as e:
        sync_status = "failed"
        sync_message = f"Failed to sync with Version B: {str(e)}"
        logger.error(f"Error syncing job {job.job_id}: {str(e)}")

    database.update_job_sync_status(job.job_id, sync_status, sync_message)
    final_job = database.get_job(job.job_id)
    return final_job

@app.post("/jobs/{job_id}/sync", response_model=JobResponse, tags=["Jobs"])
async def retry_sync_job(job_id: str):
    """Retry sending an existing job's requirements to Version B"""
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    payload = {
        "job_id": job["job_id"],
        "job_title": job["job_title"],
        "job_description": job["job_description"],
        "required_skills": job["required_skills"],
        "preferred_skills": job["preferred_skills"],
        "min_experience": job["min_experience"],
        "education_requirement": job["education_requirement"]
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{VERSION_B_URL}/jobs", json=payload)
            if resp.status_code in [200, 201]:
                database.update_job_sync_status(job_id, "synced", f"Synced with Version B ({VERSION_B_URL})")
            else:
                database.update_job_sync_status(job_id, "failed", f"Version B error {resp.status_code}: {resp.text}")
    except Exception as e:
        database.update_job_sync_status(job_id, "failed", f"Connection error: {str(e)}")

    return database.get_job(job_id)

@app.get("/jobs", response_model=List[JobResponse], tags=["Jobs"])
async def list_all_jobs():
    """Retrieve all jobs stored in SQLite"""
    return database.list_jobs()

@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job_by_id(job_id: str):
    """Retrieve a single job by its ID"""
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job

@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_job_by_id(job_id: str):
    """Delete a job and its associated candidate records"""
    deleted = database.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return {"message": f"Job {job_id} and all related candidate records deleted successfully."}

@app.post("/match-results", response_model=CandidateResultResponse, status_code=status.HTTP_201_CREATED, tags=["Candidates"])
async def receive_match_results(result: CandidateResultCreate):
    """
    Receive candidate matching results from Version B and store them in SQLite.
    Output received from Version B: Job ID, candidate ID, candidate name, match score,
    matched skills, missing skills, extracted experience, and experience-match status.
    """
    logger.info(f"Received candidate matching result from Version B: Candidate '{result.candidate_name}' for Job '{result.job_id}' (Score: {result.match_score}%)")
    
    saved = database.save_candidate_result(result.dict())
    return saved

@app.get("/jobs/{job_id}/candidates", response_model=RankedCandidatesResponse, tags=["Candidates"])
async def get_ranked_candidates(job_id: str):
    """
    Retrieve candidate details and rank candidates by match score in descending order.
    """
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    
    candidates = database.get_ranked_candidates_for_job(job_id)
    return RankedCandidatesResponse(
        job_id=job["job_id"],
        job_title=job["job_title"],
        total_candidates=len(candidates),
        candidates=candidates
    )

@app.get("/jobs/{job_id}/candidates/{candidate_id}/details", tags=["Candidates"])
async def get_candidate_evaluation_details(job_id: str, candidate_id: str):
    """
    Allow authorised recruiters to open relevant hiring-related evaluation details.
    Excludes private learning recommendations.
    """
    cand = database.get_candidate_details(job_id, candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found for job {job_id}.")
    
    return {
        "candidate_id": cand["candidate_id"],
        "candidate_name": cand["candidate_name"],
        "job_id": cand["job_id"],
        "match_score": cand["match_score"],
        "matched_skills": cand["matched_skills"],
        "missing_skills": cand["missing_skills"],
        "extracted_experience": cand["extracted_experience"],
        "experience_match_status": cand["experience_match_status"],
        "evidence_summary": cand.get("evidence_summary", ""),
        "evaluation_status": cand.get("evaluation_status", "Completed"),
        "received_at": cand["received_at"]
    }

# ----------------- Recruiter Frontend -----------------

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/style.css", include_in_schema=False)
async def get_css_root():
    return FileResponse(os.path.join(STATIC_DIR, "style.css"), media_type="text/css")

@app.get("/app.js", include_in_schema=False)
async def get_js_root():
    return FileResponse(os.path.join(STATIC_DIR, "app.js"), media_type="application/javascript")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_recruiter_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Version A - Recruitment Backend</h1><p>Frontend static files not found.</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
