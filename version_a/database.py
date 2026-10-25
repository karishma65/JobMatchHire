import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_a.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table for Jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        job_title TEXT NOT NULL,
        job_description TEXT NOT NULL,
        required_skills TEXT NOT NULL,  -- JSON list
        preferred_skills TEXT NOT NULL, -- JSON list
        min_experience REAL NOT NULL DEFAULT 0.0,
        education_requirement TEXT NOT NULL,
        sync_status TEXT NOT NULL DEFAULT 'pending', -- 'synced', 'failed', 'pending'
        sync_message TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    """)

    # Table for Candidate Results received from Version B
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        candidate_id TEXT NOT NULL,
        candidate_name TEXT NOT NULL,
        match_score REAL NOT NULL,
        matched_skills TEXT NOT NULL,  -- JSON list
        missing_skills TEXT NOT NULL,  -- JSON list
        extracted_experience REAL NOT NULL,
        experience_match_status TEXT NOT NULL,
        evidence_summary TEXT DEFAULT '',
        evaluation_status TEXT DEFAULT 'Completed',
        received_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE
    );
    """)

    # Migration check for existing table
    cursor.execute("PRAGMA table_info(candidate_results);")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "evidence_summary" not in existing_cols:
        cursor.execute("ALTER TABLE candidate_results ADD COLUMN evidence_summary TEXT DEFAULT '';")
    if "evaluation_status" not in existing_cols:
        cursor.execute("ALTER TABLE candidate_results ADD COLUMN evaluation_status TEXT DEFAULT 'Completed';")

    # Index for fast ranking query
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_candidates_job_score 
    ON candidate_results (job_id, match_score DESC);
    """)

    conn.commit()
    conn.close()

def save_job(job_data: Dict[str, Any], sync_status: str = "pending", sync_message: str = "") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = job_data.get("created_at") or job_data.get("received_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    req_skills_json = json.dumps(job_data.get("required_skills", []))
    pref_skills_json = json.dumps(job_data.get("preferred_skills", []))

    cursor.execute("""
    INSERT OR REPLACE INTO jobs 
    (job_id, job_title, job_description, required_skills, preferred_skills, min_experience, education_requirement, sync_status, sync_message, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["job_id"],
        job_data["job_title"],
        job_data["job_description"],
        req_skills_json,
        pref_skills_json,
        float(job_data.get("min_experience", 0.0)),
        job_data.get("education_requirement", "Bachelor's Degree"),
        sync_status,
        sync_message,
        now_str
    ))
    conn.commit()
    conn.close()
    return get_job(job_data["job_id"])

def update_job_sync_status(job_id: str, sync_status: str, sync_message: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE jobs 
    SET sync_status = ?, sync_message = ?
    WHERE job_id = ?
    """, (sync_status, sync_message, job_id))
    conn.commit()
    conn.close()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT j.*, 
           (SELECT COUNT(*) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS candidate_count,
           (SELECT MAX(match_score) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS top_score,
           (SELECT MAX(received_at) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS latest_candidate_at
    FROM jobs j 
    WHERE j.job_id = ?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["required_skills"] = json.loads(d["required_skills"])
    d["preferred_skills"] = json.loads(d["preferred_skills"])
    d["candidate_count"] = int(d.get("candidate_count") or 0)
    d["top_score"] = float(d.get("top_score") or 0.0)
    return d

def list_jobs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT j.*, 
           (SELECT COUNT(*) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS candidate_count,
           (SELECT MAX(match_score) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS top_score,
           (SELECT MAX(received_at) FROM candidate_results cr WHERE cr.job_id = j.job_id) AS latest_candidate_at
    FROM jobs j 
    ORDER BY j.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["required_skills"] = json.loads(d["required_skills"])
        d["preferred_skills"] = json.loads(d["preferred_skills"])
        d["candidate_count"] = int(d.get("candidate_count") or 0)
        d["top_score"] = float(d.get("top_score") or 0.0)
        result.append(d)
    return result

def save_candidate_result(res_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    matched_skills_json = json.dumps(res_data.get("matched_skills", []))
    missing_skills_json = json.dumps(res_data.get("missing_skills", []))
    evidence_sum = res_data.get("evidence_summary", "")
    eval_status = res_data.get("evaluation_status", "Completed")

    # If candidate already evaluated for this job, remove old evaluation to update to latest
    cursor.execute("""
    DELETE FROM candidate_results 
    WHERE job_id = ? AND candidate_id = ?
    """, (res_data["job_id"], res_data["candidate_id"]))

    cursor.execute("""
    INSERT INTO candidate_results 
    (job_id, candidate_id, candidate_name, match_score, matched_skills, missing_skills, extracted_experience, experience_match_status, evidence_summary, evaluation_status, received_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        res_data["job_id"],
        res_data["candidate_id"],
        res_data["candidate_name"],
        float(res_data["match_score"]),
        matched_skills_json,
        missing_skills_json,
        float(res_data.get("extracted_experience", 0.0)),
        res_data.get("experience_match_status", "N/A"),
        evidence_sum,
        eval_status,
        now_str
    ))
    res_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": res_id,
        "job_id": res_data["job_id"],
        "candidate_id": res_data["candidate_id"],
        "candidate_name": res_data["candidate_name"],
        "match_score": float(res_data["match_score"]),
        "matched_skills": res_data.get("matched_skills", []),
        "missing_skills": res_data.get("missing_skills", []),
        "extracted_experience": float(res_data.get("extracted_experience", 0.0)),
        "experience_match_status": res_data.get("experience_match_status", "N/A"),
        "evidence_summary": evidence_sum,
        "evaluation_status": eval_status,
        "received_at": now_str
    }

def get_ranked_candidates_for_job(job_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM candidate_results 
    WHERE job_id = ? 
    ORDER BY match_score DESC, extracted_experience DESC
    """, (job_id,))
    rows = cursor.fetchall()
    conn.close()

    ranked = []
    for idx, r in enumerate(rows, start=1):
        d = dict(r)
        d["rank"] = idx
        d["matched_skills"] = json.loads(d["matched_skills"])
        d["missing_skills"] = json.loads(d["missing_skills"])
        ranked.append(d)
    return ranked

def get_candidate_details(job_id: str, candidate_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM candidate_results 
    WHERE job_id = ? AND candidate_id = ?
    ORDER BY id DESC LIMIT 1
    """, (job_id, candidate_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["matched_skills"] = json.loads(d["matched_skills"])
    d["missing_skills"] = json.loads(d["missing_skills"])
    return d

def delete_job(job_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidate_results WHERE job_id = ?", (job_id,))
    cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
