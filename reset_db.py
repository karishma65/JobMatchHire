import os
import glob

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def reset_project_database():
    """
    Cleans all stored candidate evaluations, job postings, and generated PDF reports
    so you can present a 100% clean, fresh demo to your faculty.
    Both SQLite database files are safely removed; they will be automatically
    recreated with fresh empty tables the next time you start the servers.
    """
    db_a = os.path.join(CURRENT_DIR, "version_a", "version_a.db")
    db_b = os.path.join(CURRENT_DIR, "version_b", "version_b.db")
    reports_dir = os.path.join(CURRENT_DIR, "version_b", "reports")

    deleted_count = 0

    # 1. Remove Version A Database
    if os.path.exists(db_a):
        try:
            os.remove(db_a)
            print("[RESET] Removed version_a.db (Recruiter database reset)")
            deleted_count += 1
        except Exception as e:
            print(f"[ERROR] Could not delete {db_a}: {e}")

    # 2. Remove Version B Database
    if os.path.exists(db_b):
        try:
            os.remove(db_b)
            print("[RESET] Removed version_b.db (Candidate database reset)")
            deleted_count += 1
        except Exception as e:
            print(f"[ERROR] Could not delete {db_b}: {e}")

    # 3. Clean generated PDF reports
    if os.path.exists(reports_dir):
        pdf_reports = glob.glob(os.path.join(reports_dir, "*.pdf"))
        for pdf_path in pdf_reports:
            try:
                os.remove(pdf_path)
            except Exception:
                pass
        print(f"[RESET] Cleared {len(pdf_reports)} generated PDF reports from version_b/reports/")

    print("\nDatabase reset complete!")
    print("When you launch Application A (port 8000) and Application B (port 8001),")
    print("fresh, completely empty database tables will be automatically created.\n")

if __name__ == "__main__":
    reset_project_database()
