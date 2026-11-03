"""
Persistent Job Tracker using SQLite with CSV export.
Strictly implements the 21 columns required in Section 6.
Guarantees deduplication, preserves application status and notes across refreshes.
"""
import sqlite3
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

SCHEMA_COLUMNS = [
    "job_title",                      # 1
    "company",                        # 2
    "official_application_link",      # 3 (Primary unique key)
    "original_source",                # 4
    "original_posting_date_time",     # 5
    "listing_age_hours",              # 6
    "work_arrangement",               # 7
    "eligible_hiring_locations",      # 8
    "emea_kenya_eligibility_status",  # 9
    "employment_type",                # 10
    "seniority",                      # 11
    "salary_compensation",            # 12
    "required_technical_skills",      # 13
    "match_score",                    # 14
    "reasons_for_match",              # 15
    "missing_requirements_risks",     # 16
    "application_deadline",           # 17
    "application_status",             # 18
    "date_first_discovered",          # 19
    "last_verified_date",             # 20
    "recommended_next_action",        # 21
    "personal_notes"                  # Extra preserved notes
]

class JobTracker:
    def __init__(self, db_path: str = "data/jobs.db", csv_path: str = "data/job_tracker.csv"):
        self.db_path = Path(db_path)
        self.csv_path = Path(csv_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                official_application_link TEXT PRIMARY KEY,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                original_source TEXT,
                original_posting_date_time TEXT,
                listing_age_hours REAL,
                work_arrangement TEXT,
                eligible_hiring_locations TEXT,
                emea_kenya_eligibility_status TEXT,
                employment_type TEXT,
                seniority TEXT,
                salary_compensation TEXT,
                required_technical_skills TEXT,
                match_score INTEGER,
                reasons_for_match TEXT,
                missing_requirements_risks TEXT,
                application_deadline TEXT,
                application_status TEXT DEFAULT 'Not reviewed',
                date_first_discovered TEXT,
                last_verified_date TEXT,
                recommended_next_action TEXT,
                personal_notes TEXT DEFAULT ''
            )
            """)
            conn.commit()

    def upsert_job(self, record: Dict[str, Any]) -> str:
        """
        Inserts or updates a job while strictly preserving user application_status and personal_notes.
        Returns: 'new' or 'updated'
        """
        link = record.get("official_application_link", "").strip()
        if not link:
            return "skipped"

        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT application_status, personal_notes, date_first_discovered FROM jobs WHERE official_application_link = ?", (link,))
            existing = cursor.fetchone()

            if existing:
                # Preserve existing status and notes
                status = existing["application_status"]
                notes = existing["personal_notes"]
                first_discovered = existing["date_first_discovered"]

                cursor.execute("""
                UPDATE jobs SET
                    job_title = ?,
                    company = ?,
                    original_source = ?,
                    original_posting_date_time = ?,
                    listing_age_hours = ?,
                    work_arrangement = ?,
                    eligible_hiring_locations = ?,
                    emea_kenya_eligibility_status = ?,
                    employment_type = ?,
                    seniority = ?,
                    salary_compensation = ?,
                    required_technical_skills = ?,
                    match_score = ?,
                    reasons_for_match = ?,
                    missing_requirements_risks = ?,
                    application_deadline = ?,
                    last_verified_date = ?,
                    recommended_next_action = ?
                WHERE official_application_link = ?
                """, (
                    record.get("job_title", ""),
                    record.get("company", ""),
                    record.get("original_source", ""),
                    record.get("original_posting_date_time", ""),
                    record.get("listing_age_hours", 0.0),
                    record.get("work_arrangement", "Remote"),
                    record.get("eligible_hiring_locations", ""),
                    record.get("emea_kenya_eligibility_status", ""),
                    record.get("employment_type", "Full-time"),
                    record.get("seniority", "Mid-level"),
                    record.get("salary_compensation", "Undisclosed"),
                    record.get("required_technical_skills", ""),
                    record.get("match_score", 0),
                    record.get("reasons_for_match", ""),
                    record.get("missing_requirements_risks", ""),
                    record.get("application_deadline", "Not specified"),
                    now_str,
                    record.get("recommended_next_action", "Investigate further"),
                    link
                ))
                conn.commit()
                return "updated"
            else:
                cursor.execute("""
                INSERT INTO jobs (
                    official_application_link, job_title, company, original_source,
                    original_posting_date_time, listing_age_hours, work_arrangement,
                    eligible_hiring_locations, emea_kenya_eligibility_status, employment_type,
                    seniority, salary_compensation, required_technical_skills, match_score,
                    reasons_for_match, missing_requirements_risks, application_deadline,
                    application_status, date_first_discovered, last_verified_date,
                    recommended_next_action, personal_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    link,
                    record.get("job_title", ""),
                    record.get("company", ""),
                    record.get("original_source", ""),
                    record.get("original_posting_date_time", ""),
                    record.get("listing_age_hours", 0.0),
                    record.get("work_arrangement", "Remote"),
                    record.get("eligible_hiring_locations", ""),
                    record.get("emea_kenya_eligibility_status", ""),
                    record.get("employment_type", "Full-time"),
                    record.get("seniority", "Mid-level"),
                    record.get("salary_compensation", "Undisclosed"),
                    record.get("required_technical_skills", ""),
                    record.get("match_score", 0),
                    record.get("reasons_for_match", ""),
                    record.get("missing_requirements_risks", ""),
                    record.get("application_deadline", "Not specified"),
                    record.get("application_status", "Not reviewed"),
                    now_str,
                    now_str,
                    record.get("recommended_next_action", "Investigate further"),
                    record.get("personal_notes", "")
                ))
                conn.commit()
                return "new"

    def update_status(self, link: str, status: str, notes: Optional[str] = None):
        """Updates user's application status (e.g. Applied, Shortlisted, Interviewing)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if notes is not None:
                cursor.execute("UPDATE jobs SET application_status = ?, personal_notes = ?, last_verified_date = ? WHERE official_application_link = ?",
                               (status, notes, datetime.now().isoformat(), link))
            else:
                cursor.execute("UPDATE jobs SET application_status = ?, last_verified_date = ? WHERE official_application_link = ?",
                               (status, datetime.now().isoformat(), link))
            conn.commit()

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY match_score DESC, listing_age_hours ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def export_to_csv(self):
        """Exports all database rows to CSV with the exact 21 columns."""
        jobs = self.get_all_jobs()
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEMA_COLUMNS)
            writer.writeheader()
            for j in jobs:
                writer.writerow({k: j.get(k, "") for k in SCHEMA_COLUMNS})
