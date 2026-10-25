from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class JobRequirementInput(BaseModel):
    job_id: str = Field(..., description="Job identifier sent by Version A")
    job_title: str = Field(..., description="Job Title")
    job_description: str = Field(..., description="Job Description")
    required_skills: List[str] = Field(default_factory=list, description="Mandatory required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills")
    min_experience: float = Field(0.0, ge=0.0, description="Minimum experience in years")
    education_requirement: str = Field("Bachelor's Degree", description="Education Requirement")

class JobRequirementResponse(JobRequirementInput):
    received_at: str

    class Config:
        from_attributes = True

class ScoreBreakdown(BaseModel):
    required_skills_score: float
    required_skills_max: float = 50.0
    experience_score: float
    experience_max: float = 25.0
    preferred_skills_score: float
    preferred_skills_max: float = 15.0
    similarity_score: float
    similarity_max: float = 10.0
    cosine_similarity: float

class ResumeAnalysisResponse(BaseModel):
    job_id: str
    candidate_id: str
    candidate_name: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    extracted_experience: float
    experience_match_status: str
    match_explanation: Optional[str] = None
    breakdown: Optional[ScoreBreakdown] = None
    extracted_skills_count: int
    all_extracted_skills: List[str]
    candidate_token: str
    resume_version: int = 1
    evaluation_status: str = "Evaluation Completed"
    evidence_summary: str = ""
    report_download_url: str = ""
    sync_to_version_a_status: str
    sync_to_version_a_message: Optional[str] = None
    created_at: str

class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    port: int
    database_connected: bool
    version_a_connected: Optional[bool] = None
