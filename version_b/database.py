import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_b.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Table for Jobs received from Version A
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS received_jobs (
        job_id TEXT PRIMARY KEY,
        job_title TEXT NOT NULL,
        job_description TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        preferred_skills TEXT NOT NULL,
        min_experience REAL NOT NULL DEFAULT 0.0,
        education_requirement TEXT NOT NULL,
        received_at TEXT NOT NULL
    );
    """)

    # Table for Candidate Evaluations performed by Version B
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_evaluations (
        candidate_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        candidate_name TEXT NOT NULL,
        resume_filename TEXT NOT NULL,
        extracted_skills TEXT NOT NULL,
        matched_skills TEXT NOT NULL,
        missing_skills TEXT NOT NULL,
        extracted_experience REAL NOT NULL,
        experience_match_status TEXT NOT NULL,
        match_score REAL NOT NULL,
        score_breakdown TEXT NOT NULL,
        candidate_token TEXT NOT NULL DEFAULT '',
        resume_version INTEGER NOT NULL DEFAULT 1,
        report_path TEXT DEFAULT '',
        evidence_summary TEXT DEFAULT '',
        evaluation_status TEXT NOT NULL DEFAULT 'Completed',
        ecce_data TEXT DEFAULT '{}',
        sync_to_a_status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES received_jobs (job_id)
    );
    """)

    # Ensure migrations if table previously existed
    cursor.execute("PRAGMA table_info(candidate_evaluations);")
    existing_cols = [row[1] for row in cursor.fetchall()]
    new_cols = [
        ("candidate_token", "TEXT NOT NULL DEFAULT ''"),
        ("resume_version", "INTEGER NOT NULL DEFAULT 1"),
        ("report_path", "TEXT DEFAULT ''"),
        ("evidence_summary", "TEXT DEFAULT ''"),
        ("evaluation_status", "TEXT NOT NULL DEFAULT 'Completed'"),
        ("ecce_data", "TEXT DEFAULT '{}'")
    ]
    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE candidate_evaluations ADD COLUMN {col_name} {col_def};")

    conn.commit()
    conn.close()

def save_received_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    req_skills_json = json.dumps(job_data.get("required_skills", []))
    pref_skills_json = json.dumps(job_data.get("preferred_skills", []))

    cursor.execute("""
    INSERT OR REPLACE INTO received_jobs
    (job_id, job_title, job_description, required_skills, preferred_skills, min_experience, education_requirement, received_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["job_id"],
        job_data["job_title"],
        job_data["job_description"],
        req_skills_json,
        pref_skills_json,
        float(job_data.get("min_experience", 0.0)),
        job_data.get("education_requirement", "Bachelor's Degree"),
        now_str
    ))
    conn.commit()
    conn.close()
    return get_received_job(job_data["job_id"])

def get_received_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM received_jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["required_skills"] = json.loads(d["required_skills"])
    d["preferred_skills"] = json.loads(d["preferred_skills"])
    return d

def list_received_jobs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM received_jobs ORDER BY received_at DESC")
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["required_skills"] = json.loads(d["required_skills"])
        d["preferred_skills"] = json.loads(d["preferred_skills"])
        results.append(d)
    return results

def get_latest_resume_version(candidate_name: str, job_id: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT MAX(resume_version) FROM candidate_evaluations 
    WHERE candidate_name = ? AND job_id = ?
    """, (candidate_name, job_id))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] is not None:
        return int(row[0])
    return 0

def save_candidate_evaluation(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
    INSERT OR REPLACE INTO candidate_evaluations
    (candidate_id, job_id, candidate_name, resume_filename, extracted_skills, matched_skills, missing_skills,
     extracted_experience, experience_match_status, match_score, score_breakdown, candidate_token,
     resume_version, report_path, evidence_summary, evaluation_status, ecce_data, sync_to_a_status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["candidate_id"],
        data["job_id"],
        data["candidate_name"],
        data.get("resume_filename", "resume.txt"),
        json.dumps(data.get("all_extracted_skills", [])),
        json.dumps(data.get("matched_skills", [])),
        json.dumps(data.get("missing_skills", [])),
        float(data.get("extracted_experience", 0.0)),
        data.get("experience_match_status", "N/A"),
        float(data.get("match_score", 0.0)),
        json.dumps(data.get("breakdown", {})),
        data.get("candidate_token", ""),
        int(data.get("resume_version", 1)),
        data.get("report_path", ""),
        data.get("evidence_summary", ""),
        data.get("evaluation_status", "Completed"),
        json.dumps(data.get("ecce_data", {})),
        data.get("sync_to_version_a_status", "pending"),
        now_str
    ))
    conn.commit()
    conn.close()
    data["created_at"] = now_str
    return data

def get_candidate_evaluation(candidate_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidate_evaluations WHERE candidate_id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["extracted_skills"] = json.loads(d["extracted_skills"])
    d["matched_skills"] = json.loads(d["matched_skills"])
    d["missing_skills"] = json.loads(d["missing_skills"])
    d["score_breakdown"] = json.loads(d["score_breakdown"])
    d["ecce_data"] = json.loads(d["ecce_data"]) if d.get("ecce_data") else {}
    return d

def update_candidate_sync_status(candidate_id: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE candidate_evaluations SET sync_to_a_status = ? WHERE candidate_id = ?", (status, candidate_id))
    conn.commit()
    conn.close()

def list_candidate_evaluations(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidate_evaluations ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["extracted_skills"] = json.loads(d["extracted_skills"])
        d["matched_skills"] = json.loads(d["matched_skills"])
        d["missing_skills"] = json.loads(d["missing_skills"])
        d["score_breakdown"] = json.loads(d["score_breakdown"])
        results.append(d)
    return results
