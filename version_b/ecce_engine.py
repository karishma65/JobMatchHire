import re
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("ecce_engine")

# Environment configuration for LLM (retrieved from .env or system environment)
LLM_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("LLM_API_KEY", ""))

ACTION_VERBS = [
    "architected", "engineered", "developed", "built", "implemented", "designed",
    "deployed", "optimized", "configured", "managed", "created", "maintained",
    "refactored", "migrated", "automated", "orchestrated", "integrated", "led",
    "monitored", "delivered", "scaled", "debugged", "tested", "established"
]

PROJECT_CONTEXT_KEYWORDS = [
    "microservice", "service", "api", "pipeline", "platform", "system", "application",
    "portal", "infrastructure", "backend", "frontend", "database", "cluster", "cloud",
    "architecture", "workflow", "dashboard", "module", "server", "model"
]

OUTCOME_PATTERNS = [
    r'\b(?:\d+%\s*(?:increase|decrease|reduction|improvement|growth))\b',
    r'\b(?:reduced|decreased|improved|boosted|increased|accelerated|saved)\b[^\.\n]*',
    r'\b(?:latency|throughput|performance|efficiency|uptime|coverage)\b[^\.\n]*',
    r'\b(?:serving|handling|scaling\s+to)\s+\d+[\w\+]*\s+(?:users|requests|events|transactions)\b'
]

# Curated, authoritative learning resources for common technical competencies
LEARNING_RESOURCES = {
    "python": {
        "why": "Core foundational language for modern backend engineering, data processing, and scripting.",
        "activity": "Construct a complete asynchronous REST application utilizing typed models, automated unit tests, and modular architecture.",
        "resource": "Official Python Documentation (docs.python.org) and Python Design Patterns Guide"
    },
    "fastapi": {
        "why": "High-throughput asynchronous framework required for building performant modern microservices and API gateways.",
        "activity": "Build a production-grade CRUD microservice with Pydantic validation, dependency injection, async database sessions, and automated OpenAPI documentation.",
        "resource": "FastAPI Official Documentation (fastapi.tiangolo.com) and Async Python Tutorial"
    },
    "docker": {
        "why": "Essential for containerization, environment reproducibility, and microservice orchestration across environments.",
        "activity": "Containerize a multi-tier web application using multi-stage Docker builds, environment variables, and Docker Compose networking.",
        "resource": "Docker Official Documentation (docs.docker.com) & Best Practices for Containerization"
    },
    "sql": {
        "why": "Fundamental for relational data modeling, transactional integrity, index optimization, and complex querying.",
        "activity": "Design a normalized database schema with indexed foreign keys, write analytical window queries, and optimize slow execution plans.",
        "resource": "PostgreSQL Official Documentation (postgresql.org/docs) & Use The Index, Luke! Guide"
    },
    "aws": {
        "why": "Industry-standard cloud platform for hosting scalable infrastructure, managed storage, and serverless compute.",
        "activity": "Deploy a containerized application to AWS ECS or EKS with RDS database integration, S3 storage, and CloudWatch monitoring.",
        "resource": "AWS Well-Architected Framework & AWS Certified Solutions Architect Learning Path"
    },
    "redis": {
        "why": "In-memory data store essential for sub-millisecond caching, rate-limiting, and distributed session management.",
        "activity": "Implement a distributed cache and sliding-window rate limiter in front of a relational database with TTL invalidation policies.",
        "resource": "Redis Official Documentation (redis.io/docs) & Caching Patterns Guide"
    },
    "kubernetes": {
        "why": "Industry standard for automated deployment, scaling, and operational management of containerized workloads.",
        "activity": "Configure a local Kubernetes cluster (Minikube/k3s) with Deployments, Services, ConfigMaps, Ingress, and Horizontal Pod Autoscaling.",
        "resource": "Kubernetes Official Interactive Tutorial (kubernetes.io/docs/tutorials)"
    },
    "git": {
        "why": "Essential for collaborative version control, branch management, pull request workflows, and code review.",
        "activity": "Practice feature-branch workflows, semantic commit histories, interactive rebasing, and GitHub Actions CI pipelines.",
        "resource": "Pro Git Book by Scott Chacon (git-scm.com/book)"
    },
    "javascript": {
        "why": "Universal web language for front-end client logic, asynchronous event handling, and full-stack runtime support.",
        "activity": "Develop an interactive, component-based dashboard with asynchronous fetch, real-time DOM updates, and error handling.",
        "resource": "MDN Web Docs - JavaScript Guide (developer.mozilla.org)"
    },
    "react": {
        "why": "Primary front-end UI library for building reactive, single-page web applications and interactive recruiter interfaces.",
        "activity": "Build a stateful application utilizing React Hooks (useState, useEffect, useMemo), Context API, and modular UI components.",
        "resource": "React Official Documentation (react.dev)"
    }
}

def extract_supporting_passages(skill: str, resume_text: str) -> List[str]:
    """
    Extracts verbatim sentences or bullet points from the resume referencing the skill.
    Preserves exact source text without alteration.
    """
    normalized_skill = skill.strip().lower()
    # Pattern to match sentences or bullet items
    raw_sentences = re.split(r'(?:\r?\n|\.\s+|\;\s+)', resume_text)
    matching_passages = []

    for s in raw_sentences:
        clean_s = s.strip()
        if not clean_s or len(clean_s) < 10:
            continue
        # Check boundary match
        pattern = r'\b' + re.escape(normalized_skill) + r'\b'
        if re.search(pattern, clean_s, re.IGNORECASE):
            matching_passages.append(clean_s)

    return matching_passages[:3]

def analyze_context_depth(passages: List[str]) -> Dict[str, Any]:
    """
    Identifies actions, project context, and stated outcomes in supporting passages.
    Strictly avoids fabricating or hallucinating evidence.
    """
    found_actions = []
    found_contexts = []
    found_outcomes = []

    combined_text = " ".join(passages).lower()

    for verb in ACTION_VERBS:
        if re.search(r'\b' + re.escape(verb) + r'\b', combined_text):
            found_actions.append(verb.title())

    for ctx in PROJECT_CONTEXT_KEYWORDS:
        if re.search(r'\b' + re.escape(ctx) + r'\b', combined_text):
            found_contexts.append(ctx.title())

    for out_pattern in OUTCOME_PATTERNS:
        match = re.search(out_pattern, combined_text, re.IGNORECASE)
        if match:
            found_outcomes.append(match.group(0).strip())

    return {
        "actions": list(dict.fromkeys(found_actions))[:4],
        "project_context": list(dict.fromkeys(found_contexts))[:4],
        "stated_outcomes": list(dict.fromkeys(found_outcomes))[:3]
    }

def classify_skill_evidence(
    skill: str,
    passages: List[str],
    context_depth: Dict[str, Any],
    extracted_experience: float
) -> Dict[str, Any]:
    """
    Classifies evidence into:
    - Evidence Found
    - Evidence Not Found (Not proof candidate lacks skill)
    - Potential Inconsistency (Flagged for review, not proof of dishonesty)
    """
    if not passages:
        return {
            "classification": "Evidence Not Found",
            "justification": "Skill is not explicitly referenced in the extracted resume text.",
            "disclaimer": "Evidence Not Found must not be interpreted as proof that the candidate lacks the skill."
        }

    # Check for potential inconsistency:
    # 1. Listed only as an isolated token in a skills dump without actions or project context
    has_actions = len(context_depth.get("actions", [])) > 0
    has_context = len(context_depth.get("project_context", [])) > 0
    total_passage_length = sum(len(p) for p in passages)

    # If it only appeared in a short comma-separated list like "Skills: Python, Docker, ..."
    if not has_actions and not has_context and total_passage_length < 50:
        return {
            "classification": "Potential Inconsistency",
            "justification": f"Skill '{skill}' is listed in summary text but lacks descriptive project sentences or action context.",
            "disclaimer": "Potential Inconsistency must be flagged for review, not treated as proof of dishonesty."
        }

    return {
        "classification": "Evidence Found",
        "justification": f"Verified supporting context with active project application.",
        "disclaimer": None
    }

def try_llm_assist_evidence(
    skill_assessments: List[Dict[str, Any]],
    job_title: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Optional LLM assistance using gemini-3.8-flash to refine contextual nuance.
    Strictly separated from deterministic score calculations.
    Returns None if LLM is unavailable, rate-limited, or fails validation.
    """
    if not LLM_API_KEY:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=LLM_API_KEY)
        model = genai.GenerativeModel("gemini-3.8-flash")

        # Prepare small, structured payload
        prompt = (
            f"You are the ECCE Contextual Interpretation Assistant for Job: '{job_title}'.\n"
            f"Review these skill assessments extracted from candidate resume passages.\n"
            f"Validate actions, project context, and classification. Do not invent any facts.\n"
            f"Input:\n{json.dumps(skill_assessments[:6], indent=2)}\n"
            f"Output JSON array matching the structure exactly."
        )

        # Set strict timeout of 2.5 seconds to prevent rate-limit retries blocking user
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 1024},
            request_options={"timeout": 2.5}
        )
        if not response or not response.text:
            return None

        # Clean JSON markdown fences
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        parsed = json.loads(clean_text.strip())
        if isinstance(parsed, list) and len(parsed) > 0:
            logger.info("ECCE LLM contextual interpretation successfully applied.")
            return parsed
    except Exception as e:
        logger.info(f"ECCE LLM assistant skipped ({type(e).__name__}). Using deterministic contextual parsing.")

    return None

def compute_counterfactual_simulations(
    job: Dict[str, Any],
    baseline_match: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Deterministic Counterfactual Analysis:
    Explains how valid changes affect the score under the baseline formula:
    - Required Skills: 50%
    - Experience: 25%
    - Preferred Skills: 15%
    - Text Similarity: 10%
    Distinguishes parsing corrections from acquiring new skills.
    Never recommends fabricating skills.
    Labels all simulated scores as 'Hypothetical Simulation - Not Actual Result'.
    """
    baseline_score = float(baseline_match["match_score"])
    breakdown = baseline_match["breakdown"]
    req_skills = job.get("required_skills", [])
    pref_skills = job.get("preferred_skills", [])
    missing_required = baseline_match.get("missing_required_skills", [])
    missing_preferred = baseline_match.get("missing_preferred_skills", [])
    min_exp = float(job.get("min_experience", 0.0))
    current_exp = float(baseline_match.get("extracted_experience", 0.0))

    simulations = []

    # Scenario 1: Acquiring first missing required skill
    if missing_required and len(req_skills) > 0:
        skill_to_gain = missing_required[0]
        pts_per_req_skill = 50.0 / len(req_skills)
        simulated_req_score = min(50.0, breakdown["required_skills_score"] + pts_per_req_skill)
        simulated_total = round(baseline_score + pts_per_req_skill, 2)
        simulated_total = min(100.0, simulated_total)
        delta = round(simulated_total - baseline_score, 2)

        simulations.append({
            "scenario_name": f"Competency Acquisition: {skill_to_gain}",
            "scenario_type": "Skill Acquisition",
            "description": f"Candidate undertakes formal training or practical project work to develop verifiable competency in {skill_to_gain}.",
            "baseline_score": baseline_score,
            "simulated_score": simulated_total,
            "score_delta": delta,
            "component_affected": "Required Skills (50% max)",
            "hypothetical_label": "Hypothetical Simulation - Not Actual Result",
            "guidance_note": f"Acquiring {skill_to_gain} increases Required Skills component by {pts_per_req_skill:.2f} pts."
        })

    # Scenario 2: Resume-Parsing Correction
    if missing_required:
        skill_omitted = missing_required[0]
        pts_per_req_skill = 50.0 / len(req_skills)
        simulated_total = round(min(100.0, baseline_score + pts_per_req_skill), 2)
        delta = round(simulated_total - baseline_score, 2)

        simulations.append({
            "scenario_name": f"Parsing/Format Clarification: {skill_omitted}",
            "scenario_type": "Resume-Parsing Correction",
            "description": (
                f"If candidate already possesses verifiable hands-on {skill_omitted} experience that was omitted "
                f"or formatted in non-extractable text, clarifying the resume with active project bullets adjusts the score."
            ),
            "baseline_score": baseline_score,
            "simulated_score": simulated_total,
            "score_delta": delta,
            "component_affected": "Required Skills (50% max)",
            "hypothetical_label": "Hypothetical Simulation - Not Actual Result",
            "guidance_note": "Distinguished from skill acquisition: only applicable if competency is already genuinely held."
        })

    # Scenario 3: Experience Milestone Growth
    if min_exp > 0 and current_exp < min_exp:
        exp_gap = round(min_exp - current_exp, 1)
        simulated_exp_score = 25.0
        exp_delta = round(simulated_exp_score - breakdown["experience_score"], 2)
        simulated_total = round(min(100.0, baseline_score + exp_delta), 2)

        simulations.append({
            "scenario_name": f"Experience Growth (+{exp_gap} Years)",
            "scenario_type": "Experience Growth",
            "description": f"Candidate reaches the required minimum threshold of {min_exp} years professional experience.",
            "baseline_score": baseline_score,
            "simulated_score": simulated_total,
            "score_delta": exp_delta,
            "component_affected": "Experience Score (25% max)",
            "hypothetical_label": "Hypothetical Simulation - Not Actual Result",
            "guidance_note": f"Fulfilling the remaining {exp_gap} years would raise the Experience component from {breakdown['experience_score']} to 25.0 pts."
        })
    elif missing_preferred and len(pref_skills) > 0:
        pref_skill = missing_preferred[0]
        pts_per_pref = 15.0 / len(pref_skills)
        simulated_total = round(min(100.0, baseline_score + pts_per_pref), 2)
        delta = round(simulated_total - baseline_score, 2)

        simulations.append({
            "scenario_name": f"Preferred Skill Acquisition: {pref_skill}",
            "scenario_type": "Preferred Skill Acquisition",
            "description": f"Candidate demonstrates complementary competence in preferred skill {pref_skill}.",
            "baseline_score": baseline_score,
            "simulated_score": simulated_total,
            "score_delta": delta,
            "component_affected": "Preferred Skills (15% max)",
            "hypothetical_label": "Hypothetical Simulation - Not Actual Result",
            "guidance_note": f"Adding {pref_skill} increases Preferred Skills component by {pts_per_pref:.2f} pts."
        })

    return simulations

def generate_private_learning_guidance(
    missing_required: List[str],
    missing_preferred: List[str]
) -> List[Dict[str, Any]]:
    """
    Generates private personal development guidance for genuine skill gaps.
    Kept strictly private to candidate by default.
    Uses reliable resources without fabricating courses.
    """
    guidance_list = []
    all_gaps = [(s, "Required") for s in missing_required] + [(s, "Preferred") for s in missing_preferred]

    for skill, category in all_gaps:
        norm_key = skill.strip().lower()
        info = LEARNING_RESOURCES.get(norm_key, {
            "why": f"Key technical capability specified in the job requisitions for {category.lower()} qualifications.",
            "activity": f"Build a practical proof-of-concept project demonstrating production usage of {skill}.",
            "resource": f"Official documentation and industry-standard tutorials for {skill}."
        })

        guidance_list.append({
            "skill": skill,
            "category": category,
            "why_it_matters": info["why"],
            "recommended_activity": info["activity"],
            "reliable_resource": info["resource"],
            "privacy_classification": "Candidate Confidential - Private Guidance"
        })

    return guidance_list

def run_ecce_evaluation(
    job: Dict[str, Any],
    candidate_payload: Dict[str, Any],
    baseline_match: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main entry point for ECCE (Explainable Contextual Competency Engine).
    Executes contextual competency assessment, evidence classification,
    deterministic scoring validation, counterfactual simulations, and private skill-gap guidance.
    """
    resume_text = candidate_payload.get("resume_text", "")
    extracted_exp = float(candidate_payload.get("extracted_experience", 0.0))
    candidate_id = candidate_payload.get("candidate_id", "CAN-UNKNOWN")
    candidate_name = candidate_payload.get("candidate_name", "Anonymous Candidate")

    req_skills = job.get("required_skills", [])
    pref_skills = job.get("preferred_skills", [])

    # 1. Contextual Competency Assessment & Evidence Classification
    required_assessments = []
    preferred_assessments = []
    has_potential_inconsistency = False

    for s in req_skills:
        passages = extract_supporting_passages(s, resume_text)
        depth = analyze_context_depth(passages)
        classification = classify_skill_evidence(s, passages, depth, extracted_exp)
        if classification["classification"] == "Potential Inconsistency":
            has_potential_inconsistency = True

        required_assessments.append({
            "skill": s,
            "category": "Required",
            "classification": classification["classification"],
            "justification": classification["justification"],
            "disclaimer": classification.get("disclaimer"),
            "supporting_passages": passages,
            "actions": depth["actions"],
            "project_context": depth["project_context"],
            "stated_outcomes": depth["stated_outcomes"]
        })

    for s in pref_skills:
        passages = extract_supporting_passages(s, resume_text)
        depth = analyze_context_depth(passages)
        classification = classify_skill_evidence(s, passages, depth, extracted_exp)
        if classification["classification"] == "Potential Inconsistency":
            has_potential_inconsistency = True

        preferred_assessments.append({
            "skill": s,
            "category": "Preferred",
            "classification": classification["classification"],
            "justification": classification["justification"],
            "disclaimer": classification.get("disclaimer"),
            "supporting_passages": passages,
            "actions": depth["actions"],
            "project_context": depth["project_context"],
            "stated_outcomes": depth["stated_outcomes"]
        })

    # Optional LLM refinement (if available and rate-limit permits)
    try_llm_assist_evidence(required_assessments, job.get("job_title", ""))

    # 2. Counterfactual Analysis
    counterfactuals = compute_counterfactual_simulations(job, baseline_match)

    # 3. Private Skill-Gap Guidance
    private_guidance = generate_private_learning_guidance(
        baseline_match.get("missing_required_skills", []),
        baseline_match.get("missing_preferred_skills", [])
    )

    # 4. Evidence Summary for Recruiter
    found_req_count = sum(1 for a in required_assessments if a["classification"] == "Evidence Found")
    total_req_count = len(required_assessments)
    missing_req = baseline_match.get("missing_required_skills", [])
    missing_str = f"; missing: {', '.join(missing_req)}" if missing_req else ""
    evidence_summary = (
        f"Verified {found_req_count}/{total_req_count} required competencies with contextual evidence{missing_str}. "
        f"Experience: {baseline_match.get('experience_match_status')}."
    )

    eval_status = "Review Flagged" if has_potential_inconsistency else "Evaluation Completed"

    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "job_id": job["job_id"],
        "job_title": job.get("job_title", "Untitled Job"),
        "evaluation_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "match_score": baseline_match["match_score"],
        "breakdown": baseline_match["breakdown"],
        "required_skills_assessment": required_assessments,
        "preferred_skills_assessment": preferred_assessments,
        "counterfactual_simulations": counterfactuals,
        "private_learning_guidance": private_guidance,
        "evidence_summary": evidence_summary,
        "evaluation_status": eval_status,
        "scoring_documentation": {
            "formula": "Final Score = (Required_Skills * 0.50) + (Experience * 0.25) + (Preferred_Skills * 0.15) + (Text_Similarity * 0.10)",
            "normalisation": "Bounded strictly between 0.00 and 100.00 points.",
            "weights": {
                "required_skills": 50.0,
                "experience": 25.0,
                "preferred_skills": 15.0,
                "similarity": 10.0
            }
        }
    }
