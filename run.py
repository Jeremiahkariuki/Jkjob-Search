#!/usr/bin/env python3
"""
Root execution script for EMEA Remote Tech Job Intelligence System.
Usage:
  python3 run.py                 # Run full daily intelligence pipeline
  python3 run.py --parse-cv      # Re-parse CVs in cv/ directory and update profile
  python3 run.py --status <URL> <NEW_STATUS> # Update status (e.g. Applied, Shortlisted)
"""
import sys
import argparse
from src.runner import PipelineRunner
from src.cv_parser import CVParser
from src.tracker import JobTracker

def main():
    parser = argparse.ArgumentParser(description="EMEA Remote Tech Job Intelligence System")
    parser.add_argument("--parse-cv", action="store_true", help="Parse uploaded CVs and regenerate profile")
    parser.add_argument("--status", nargs=2, metavar=("URL", "STATUS"), help="Update job status (e.g. Applied, Shortlisted, Interviewing)")
    parser.add_argument("--notes", type=str, help="Add personal notes when updating status")
    
    args = parser.parse_args()

    if args.parse_cv:
        print("[+] Parsing CVs in cv/ directory...")
        p = CVParser()
        profile = p.consolidate_profiles()
        print(f"[✓] Candidate profile generated for {profile.full_name or 'Verified Candidate'}")
        print(f"    Check profile/candidate_profile.md for detailed breakdown.")
        return

    if args.status:
        url, status = args.status
        tracker = JobTracker()
        tracker.update_status(url, status, args.notes)
        tracker.export_to_csv()
        print(f"[✓] Successfully updated status for {url} to '{status}'")
        return

    # Default run
    runner = PipelineRunner()
    runner.run()

if __name__ == "__main__":
    main()
