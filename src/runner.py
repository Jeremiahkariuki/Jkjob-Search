"""
Main Pipeline Orchestrator for EMEA Remote Tech Job Intelligence System.
"""
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List

from src.models import CandidateProfile
from src.cv_parser import CVParser
from src.fetcher import JobFetcher
from src.matcher import JobMatcher
from src.tracker import JobTracker
from src.reporter import DailyReporter
from src.eligibility import EligibilityEngine

class PipelineRunner:
    def __init__(self):
        self.parser = CVParser()
        self.fetcher = JobFetcher(max_age_hours=48.0)
        self.tracker = JobTracker()
        self.reporter = DailyReporter()

    def run(self, force_refresh: bool = False) -> Dict[str, Any]:
        print("=" * 60)
        print("Starting Jkjob-search: EMEA Remote Job Intelligence Pipeline")
        print(f"Candidate: Jeremiah Kariuki Beth | Nairobi, Kenya (EAT)")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT (Africa/Nairobi)")
        print("=" * 60)

        # 1. Candidate Profile
        profile = self.parser.consolidate_profiles()
        if not profile.technical_skills and not profile.primary_roles:
            print("\n[!] CANDIDATE PROFILE EMPTY:")
            print("No CV files found in 'cv/' directory or 'profile/candidate_profile.json'.")
            print("Please place your CV (.pdf, .txt, .md) in the 'cv/' directory to enable personalized matching.")
        else:
            print(f"\n[+] Loaded Profile: {profile.full_name or 'Verified Candidate'}")
            print(f"    Roles: {', '.join(profile.primary_roles[:4])}")
            print(f"    Skills: {', '.join(profile.technical_skills[:8])}...")
            print(f"    Years of Experience: ~{profile.years_of_experience:.1f} yrs")

        # 2. Fetch Jobs
        print("\n[+] Pulling vacancies across multi-platform aggregators (WWR, Himalayas, RemoteOK, Remotive, Jobicy, Arbeitnow, Direct ATS)...")
        raw_jobs = self.fetcher.fetch_from_api(profile.primary_roles)
        print(f"    Fetched {len(raw_jobs)} candidate listings across all aggregators.")

        current_ts = time.time()
        stats = {
            "total_examined": len(raw_jobs),
            "new_discovered": 0,
            "confirmed_matches": 0,
            "potential_matches": 0,
            "ineligible_excluded": 0,
            "duplicates_removed": 0,
            "unverified_excluded": 0
        }

        seen_links = set()
        new_jobs_list = []
        confirmed_eligible_evaluated = []
        potential_eligible_evaluated = []

        for job in raw_jobs:
            link = job.application_url.strip()
            if not link or link in seen_links:
                stats["duplicates_removed"] += 1
                continue
            seen_links.add(link)

            # Date verification
            if not job.is_date_verified or job.posting_timestamp == 0.0:
                stats["unverified_excluded"] += 1
                continue

            age_hours = (current_ts - job.posting_timestamp) / 3600.0
            if age_hours > 48.0:
                stats["unverified_excluded"] += 1
                continue

            # Location eligibility
            if job.emea_eligibility_status == EligibilityEngine.NOT_ELIGIBLE:
                stats["ineligible_excluded"] += 1
                continue

            # Evaluate match score against candidate profile
            eval_result = JobMatcher.evaluate(job, profile)

            now_iso = datetime.now().isoformat()
            record = {
                "job_title": job.title,
                "company": job.company,
                "official_application_link": job.application_url,
                "original_source": job.source,
                "original_posting_date_time": job.original_posting_date,
                "listing_age_hours": round(age_hours, 1),
                "work_arrangement": job.work_arrangement,
                "eligible_hiring_locations": job.eligible_locations,
                "emea_kenya_eligibility_status": f"{job.emea_eligibility_status} ({job.eligibility_evidence})",
                "employment_type": job.employment_type,
                "seniority": job.seniority,
                "salary_compensation": job.salary,
                "required_technical_skills": ", ".join(job.required_skills),
                "match_score": eval_result.score,
                "reasons_for_match": " | ".join(eval_result.match_reasons),
                "missing_requirements_risks": " | ".join(eval_result.missing_requirements_or_risks),
                "application_deadline": "Not specified",
                "application_status": "Not reviewed",
                "date_first_discovered": now_iso,
                "last_verified_date": now_iso,
                "recommended_next_action": eval_result.recommended_action
            }

            status_result = self.tracker.upsert_job(record)
            if status_result == "new":
                stats["new_discovered"] += 1
                new_jobs_list.append(record)

            if job.emea_eligibility_status == EligibilityEngine.CONFIRMED:
                stats["confirmed_matches"] += 1
                confirmed_eligible_evaluated.append(record)
            elif job.emea_eligibility_status == EligibilityEngine.POTENTIAL:
                stats["potential_matches"] += 1
                potential_eligible_evaluated.append(record)

        # 3. Export CSV
        self.tracker.export_to_csv()

        # 4. Generate Report
        confirmed_sorted = sorted(confirmed_eligible_evaluated, key=lambda x: (x["match_score"], -x["listing_age_hours"]), reverse=True)
        top_priorities = [j for j in confirmed_sorted if j["recommended_next_action"] == "Prioritize applying"][:3]
        if len(top_priorities) < 3:
            top_priorities = confirmed_sorted[:3]

        all_tracked = self.tracker.get_all_jobs()
        existing_open = [j for j in all_tracked if j.get("application_status") != "Closed" and j not in new_jobs_list]

        report_md = self.reporter.generate_report(
            stats=stats,
            top_opportunities=confirmed_sorted,
            new_jobs=new_jobs_list,
            existing_open_jobs=existing_open,
            potential_jobs=potential_eligible_evaluated,
            application_priorities=top_priorities
        )

        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        for k, v in stats.items():
            print(f"  {k.replace('_', ' ').capitalize()}: {v}")
        print("\n[✓] Job tracker database updated: data/jobs.db")
        print("[✓] Tracker CSV exported: data/job_tracker.csv")
        print("[✓] Daily report created: reports/daily_report_latest.md")
        print("=" * 60)

        return {
            "stats": stats,
            "report_md": report_md,
            "profile": profile
        }

if __name__ == "__main__":
    runner = PipelineRunner()
    runner.run()
