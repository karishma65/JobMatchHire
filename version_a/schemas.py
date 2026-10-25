from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class JobBase(BaseModel):
    job_id: str = Field(..., description="Unique alphanumeric identifier for the job", example="JOB-101")
    job_title: str = Field(..., description="Job role or title", example="Senior Python Developer")
    job_description: str = Field(..., description="Detailed description of the job responsibilities", example="Design and build high-performance APIs and microservices.")
    required_skills: List[str] = Field(default_factory=list, description="Must-have technical and professional skills", example=["Python", "FastAPI", "Docker", "SQL"])
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills", example=["AWS", "Redis", "Kubernetes"])
    min_experience: float = Field(0.0, ge=0.0, description="Minimum required experience in years", example=3.0)
    education_requirement: str = Field("Bachelor's Degree", description="Minimum education qualification", example="B.Tech in Computer Science or equivalent")

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    sync_status: str = Field("pending", description="Status of sync with Version B: synced, failed, pending")
    sync_message: Optional[str] = None
    created_at: str
    candidate_count: Optional[int] = 0
    top_score: Optional[float] = 0.0
    latest_candidate_at: Optional[str] = None

    class Config:
        from_attributes = True

class CandidateResultCreate(BaseModel):
    job_id: str = Field(..., description="Target Job ID")
    candidate_id: str = Field(..., description="Unique candidate identifier")
    candidate_name: str = Field(..., description="Candidate Full Name")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Weighted match score between 0 and 100")
    matched_skills: List[str] = Field(default_factory=list, description="Candidate skills that match required/preferred skills")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills candidate is missing")
    extracted_experience: float = Field(..., ge=0.0, description="Extracted years of experience")
    experience_match_status: str = Field(..., description="Status such as 'Met requirement', 'Insufficient', 'Exceeds requirement'")
    evidence_summary: Optional[str] = Field("", description="Recruiter-safe summary of verified contextual evidence")
    evaluation_status: Optional[str] = Field("Completed", description="ECCE Evaluation Status: Completed, Review Flagged")

class CandidateResultResponse(CandidateResultCreate):
    id: int
    received_at: str

    class Config:
        from_attributes = True

class RankedCandidateItem(BaseModel):
    rank: int
    candidate_id: str
    candidate_name: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    extracted_experience: float
    experience_match_status: str
    evidence_summary: Optional[str] = ""
    evaluation_status: Optional[str] = "Completed"
    received_at: str

class RankedCandidatesResponse(BaseModel):
    job_id: str
    job_title: str
    total_candidates: int
    candidates: List[RankedCandidateItem]

class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    port: int
    database_connected: bool
    version_b_connected: Optional[bool] = None
