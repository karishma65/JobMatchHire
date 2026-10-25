import os
import sys
import time
import requests
import json
import subprocess

PORT_A = 8000
PORT_B = 8001
URL_A = f"http://127.0.0.1:{PORT_A}"
URL_B = f"http://127.0.0.1:{PORT_B}"

def test_workflow():
    print("=" * 70)
    print("STARTING COMPLETE WORKFLOW VERIFICATION: JOBMATCHHIRE ECCE")
    print("=" * 70)

    # 1. Health Checks
    print("\n[Step 1] Checking backend health on ports 8000 & 8001...")
    try:
        res_a = requests.get(f"{URL_A}/health", timeout=5)
        assert res_a.status_code == 200, f"App A health status: {res_a.status_code}"
        print(f" -> Application A (Recruiter Portal): OK ({res_a.json()['service']})")
    except Exception as e:
        print(f" -> FAILED connecting to Application A: {e}")
        return False

    try:
        res_b = requests.get(f"{URL_B}/health", timeout=5)
        assert res_b.status_code == 200, f"App B health status: {res_b.status_code}"
        print(f" -> Application B (Candidate Portal): OK ({res_b.json()['service']})")
    except Exception as e:
        print(f" -> FAILED connecting to Application B: {e}")
        return False

    # 2. Verify Candidate Portal Privacy
    print("\n[Step 2] Testing Candidate Portal Privacy Enforcement...")
    res_shared = requests.get(f"{URL_B}/candidates")
    print(f" -> GET {URL_B}/candidates returned HTTP {res_shared.status_code}")
    assert res_shared.status_code == 403, f"Expected 403 Forbidden for shared candidates, got {res_shared.status_code}"
    print(" -> PASS: Shared candidate history endpoint is strictly blocked with HTTP 403 Forbidden.")

    res_html = requests.get(f"{URL_B}/")
    assert "Recent Evaluations" not in res_html.text, "Recent Evaluations still in HTML!"
    assert '<option value="">Select a job</option>' in res_html.text, "Dropdown placeholder 'Select a job' missing in HTML!"
    assert 'id="resume-file-input"' in res_html.text, "File input missing in HTML!"
    assert 'id="dropzone"' in res_html.text, "Dropzone missing in HTML!"
    print(" -> PASS: 'Recent Evaluations' section absent from HTML.")
    print(" -> PASS: Target Job dropdown initial placeholder is 'Select a job'.")
    print(" -> PASS: Resume upload file input and dropzone are properly placed in HTML.")

    # 3. Create Job in Application A & Verify Sync to B
    print("\n[Step 3] Creating new Job Requisition in Application A...")
    job_payload = {
        "job_id": f"JOB-{int(time.time()) % 10000}",
        "job_title": "Staff Cloud Systems Architect",
        "job_description": "We are seeking a Staff Cloud Systems Architect to design and deploy fault-tolerant microservices on AWS and Kubernetes. The candidate will lead backend scalability, optimize Docker container pipelines, and architect distributed Python databases.",
        "required_skills": ["Python", "AWS", "Kubernetes", "Docker"],
        "preferred_skills": ["PostgreSQL", "Terraform", "Redis"],
        "min_experience": 4.0,
        "education_requirement": "Bachelor's Degree in Computer Science or equivalent"
    }
    res_job = requests.post(f"{URL_A}/jobs", json=job_payload)
    assert res_job.status_code in (200, 201), f"Failed creating job: {res_job.text}"
    job_data = res_job.json()
    job_id = job_data["job_id"]
    print(f" -> Job created: {job_id} ('{job_data['job_title']}')")
    print(f" -> Job UTC timestamp: {job_data['created_at']}")
    assert job_data["created_at"].endswith("Z") or "T" in job_data["created_at"], f"Invalid UTC timestamp: {job_data['created_at']}"
    print(" -> PASS: Job created with consistent UTC ISO-8601 timestamp.")

    # Verify Job is synced to Application B
    res_b_jobs = requests.get(f"{URL_B}/jobs/{job_id}")
    assert res_b_jobs.status_code == 200, f"Job not found in App B: {res_b_jobs.text}"
    print(f" -> PASS: Job successfully synced to Application B via REST API.")

    # 4. Upload Candidate Resumes and Trigger ECCE Evaluations
    print("\n[Step 4] Submitting Resumes & Evaluating with ECCE...")
    
    # Candidate 1: Alex Rivera (TXT)
    txt_path = os.path.join("sample_resumes", "Alex_Rivera_Full_Stack.txt")
    with open(txt_path, "rb") as f:
        files = {"resume_file": (os.path.basename(txt_path), f, "text/plain")}
        data = {"job_id": job_id, "candidate_name": "Alex Rivera"}
        res_cand1 = requests.post(f"{URL_B}/analyze-resume", files=files, data=data)
    assert res_cand1.status_code == 200, f"Candidate 1 evaluation failed: {res_cand1.text}"
    c1_result = res_cand1.json()
    print(f" -> Candidate 1 Evaluated: {c1_result['candidate_name']} ({c1_result['candidate_id']})")
    print(f"    Match Score: {c1_result['match_score']}% | Status: {c1_result['evaluation_status']}")
    print(f"    Version: v{c1_result['resume_version']} | Token: {c1_result['candidate_token'][:8]}...")
    print(f"    Evaluated UTC: {c1_result.get('created_at', '')}")
    assert c1_result["resume_version"] == 1
    assert "report_download_url" in c1_result
    assert c1_result.get("created_at", "").endswith("Z") or "T" in c1_result.get("created_at", "")

    # Candidate 2: David Miller (PDF)
    pdf_path = os.path.join("sample_resumes", "David_Miller_Senior_Backend_Engineer.pdf")
    with open(pdf_path, "rb") as f:
        files = {"resume_file": (os.path.basename(pdf_path), f, "application/pdf")}
        data = {"job_id": job_id, "candidate_name": "David Miller"}
        res_cand2 = requests.post(f"{URL_B}/analyze-resume", files=files, data=data)
    assert res_cand2.status_code == 200, f"Candidate 2 evaluation failed: {res_cand2.text}"
    c2_result = res_cand2.json()
    print(f" -> Candidate 2 Evaluated: {c2_result['candidate_name']} ({c2_result['candidate_id']})")
    print(f"    Match Score: {c2_result['match_score']}% | Status: {c2_result['evaluation_status']}")

    # Candidate 3: Emily Watson (DOCX)
    docx_path = os.path.join("sample_resumes", "Emily_Watson_Junior_Developer.docx")
    with open(docx_path, "rb") as f:
        files = {"resume_file": (os.path.basename(docx_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {"job_id": job_id, "candidate_name": "Emily Watson"}
        res_cand3 = requests.post(f"{URL_B}/analyze-resume", files=files, data=data)
    assert res_cand3.status_code == 200, f"Candidate 3 evaluation failed: {res_cand3.text}"
    c3_result = res_cand3.json()
    print(f" -> Candidate 3 Evaluated: {c3_result['candidate_name']} ({c3_result['candidate_id']})")
    print(f"    Match Score: {c3_result['match_score']}% | Status: {c3_result['evaluation_status']}")

    # 5. Test PDF Report Generation & Token-based Access Security
    print("\n[Step 5] Testing PDF Report Download & Access Security...")
    # Unauthorized download attempt (no token)
    res_unauth = requests.get(f"{URL_B}/candidates/{c1_result['candidate_id']}/report")
    print(f" -> Unauthorized download without token: HTTP {res_unauth.status_code}")
    assert res_unauth.status_code == 403, f"Expected 403 Forbidden without token, got {res_unauth.status_code}"
    print(" -> PASS: Report download blocked without valid token.")

    # Unauthorized download attempt (wrong token)
    res_bad_tok = requests.get(f"{URL_B}/candidates/{c1_result['candidate_id']}/report?token=fake_unauthorized_token_123")
    assert res_bad_tok.status_code == 403
    print(" -> PASS: Report download blocked with invalid token.")

    # Authorized download attempt
    res_auth = requests.get(f"{URL_B}/candidates/{c1_result['candidate_id']}/report?token={c1_result['candidate_token']}")
    assert res_auth.status_code == 200, f"Authorized download failed: {res_auth.status_code}"
    assert res_auth.headers.get("content-type") == "application/pdf"
    assert len(res_auth.content) > 5000, "PDF content suspiciously small"
    print(f" -> PASS: Authorized PDF downloaded successfully ({len(res_auth.content)} bytes).")

    # 6. Test Re-evaluation / Version Increment
    print("\n[Step 6] Testing Resume Re-evaluation (Version Increment)...")
    with open(txt_path, "rb") as f:
        files = {"resume_file": (os.path.basename(txt_path), f, "text/plain")}
        data = {
            "job_id": job_id,
            "candidate_name": "Alex Rivera",
            "candidate_id": c1_result["candidate_id"]  # Pass existing candidate ID
        }
        res_re_eval = requests.post(f"{URL_B}/analyze-resume", files=files, data=data)
    assert res_re_eval.status_code == 200, f"Re-evaluation failed: {res_re_eval.text}"
    re_eval_data = res_re_eval.json()
    print(f" -> Re-evaluated Candidate ID: {re_eval_data['candidate_id']}")
    print(f" -> Version incremented to: v{re_eval_data['resume_version']}")
    assert re_eval_data["resume_version"] == 2, f"Expected version 2, got {re_eval_data['resume_version']}"
    print(" -> PASS: Re-evaluation successfully updated version to v2.")

    # 7. Check Recruiter Portal Ranked Applicants
    print("\n[Step 7] Testing Recruiter Portal Ranked Applicants Table...")
    res_ranked = requests.get(f"{URL_A}/jobs/{job_id}/candidates")
    assert res_ranked.status_code == 200, f"Failed getting ranked candidates: {res_ranked.text}"
    ranked_data = res_ranked.json()
    candidates = ranked_data["candidates"]
    print(f" -> Total Applicants for Job '{ranked_data['job_title']}': {len(candidates)}")
    for c in candidates:
        print(f"    Rank #{c['rank']}: {c['candidate_name']} - Score: {c['match_score']}% ({c['experience_match_status']})")

    # Verify descending sort order
    scores = [c["match_score"] for c in candidates]
    assert scores == sorted(scores, reverse=True), f"Candidates not sorted descending: {scores}"
    print(" -> PASS: Ranked applicants strictly sorted in descending order of matching score.")

    # 8. Verify Recruiter Privacy Enforcement (No private recommendations or tokens exposed)
    print("\n[Step 8] Testing Recruiter Candidate Detail Privacy Guardrails...")
    cand_detail_res = requests.get(f"{URL_A}/jobs/{job_id}/candidates/{c1_result['candidate_id']}/details")
    assert cand_detail_res.status_code == 200
    details = cand_detail_res.json()
    assert "private_skill_gap_recommendations" not in details
    assert "learning_recommendations" not in details
    assert "candidate_token" not in details
    print(" -> PASS: Candidate learning recommendations and tokens are strictly private and hidden from recruiters.")

    print("\n" + "=" * 70)
    print("ALL VERIFICATION STAGES COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_workflow()
    sys.exit(0 if success else 1)
