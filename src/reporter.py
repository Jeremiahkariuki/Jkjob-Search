"""
Daily Report & Dashboard Generator.
Renders the Section 7 report format:
- A. Today's best opportunities
- B. Newly discovered jobs (< 48 hrs)
- C. Previously discovered jobs still open
- D. Location eligibility requiring confirmation
- E. Application priorities (Top 3)
- F. Search statistics
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class DailyReporter:
    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        stats: Dict[str, Any],
        top_opportunities: List[Dict[str, Any]],
        new_jobs: List[Dict[str, Any]],
        existing_open_jobs: List[Dict[str, Any]],
        potential_jobs: List[Dict[str, Any]],
        application_priorities: List[Dict[str, Any]]
    ) -> str:
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_file_str = datetime.now().strftime("%Y-%m-%d")

        md = []
        md.append(f"# EMEA Remote Tech Job Intelligence Report")
        md.append(f"**Execution Date & Time:** {today_str} EAT (Africa/Nairobi)")
        md.append(f"**Target Geography:** Kenya / EMEA / Worldwide Remote")
        md.append(f"**Freshness Window:** ≤ 48.0 hours\n")

        # Section A: Today's Best Opportunities
        md.append("## A. Today's Best Opportunities")
        if not top_opportunities:
            md.append("_No confirmed-eligible vacancies meeting the match threshold were found in this run._\n")
        else:
            for i, job in enumerate(top_opportunities[:10], 1):
                md.append(f"### {i}. [{job['job_title']}]({job['official_application_link']}) — **{job['company']}**")
                md.append(f"- **Match Score:** `{job['match_score']}/100` | **Posting Age:** ~{job['listing_age_hours']:.1f} hrs | **Location:** {job['eligible_hiring_locations']}")
                md.append(f"- **Seniority & Type:** {job['seniority']} • {job['employment_type']} | **Salary:** {job['salary_compensation']}")
                md.append(f"- **Why it matches:** {job['reasons_for_match']}")
                if job.get('missing_requirements_risks'):
                    md.append(f"- **Identified Gaps / Risks:** {job['missing_requirements_risks']}")
                md.append(f"- **Recommended Next Action:** `{job['recommended_next_action']}`")
                md.append("")

        # Section B: Newly Discovered Jobs (< 48 hrs)
        md.append("## B. Newly Discovered Jobs (≤ 48 Hours Old)")
        if not new_jobs:
            md.append("_No brand new postings discovered in the previous 48 hours for this run._\n")
        else:
            for job in new_jobs:
                md.append(f"- **[{job['job_title']}]({job['official_application_link']})** at **{job['company']}** ({job['seniority']}, {job['employment_type']}) — Discovered: {job['date_first_discovered'][:16]} | Age: ~{job['listing_age_hours']:.1f}h")
            md.append("")

        # Section C: Previously Discovered Jobs Still Open
        md.append("## C. Previously Discovered Jobs Still Open")
        if not existing_open_jobs:
            md.append("_No previously active jobs currently tracked in this category._\n")
        else:
            for job in existing_open_jobs[:10]:
                md.append(f"- **[{job['job_title']}]({job['official_application_link']})** at **{job['company']}** — Status: `{job['application_status']}` | First Seen: {job['date_first_discovered'][:10]} | Score: `{job['match_score']}/100`")
            md.append("")

        # Section D: Location Eligibility Requiring Confirmation
        md.append("## D. Location Eligibility Requiring Confirmation")
        if not potential_jobs:
            md.append("_No pending opportunities requiring location clarification._\n")
        else:
            for job in potential_jobs:
                md.append(f"- **[{job['job_title']}]({job['official_application_link']})** at **{job['company']}**")
                md.append(f"  * Listed Location: `{job['eligible_hiring_locations']}`")
                md.append(f"  * Verification Issue: {job.get('missing_requirements_risks', 'Exact hiring entity and payroll support for Kenya/Africa needs verification.')}")
            md.append("")

        # Section E: Application Priorities (Top 3)
        md.append("## E. Application Priorities")
        if not application_priorities:
            md.append("_No verified roles currently qualify for immediate top-priority application._\n")
        else:
            for i, job in enumerate(application_priorities[:3], 1):
                md.append(f"**Priority {i}: [{job['job_title']}]({job['official_application_link']}) at {job['company']}**")
                md.append(f"- **Strategic Rationale:** Matches core CV strengths with verified hiring eligibility for candidates residing in Kenya. Action: `{job['recommended_next_action']}`.")
                md.append(f"- **Essential Fit:** {job['reasons_for_match']}\n")

        # Section F: Search Statistics
        md.append("## F. Search Statistics")
        md.append(f"| Metric | Count |")
        md.append(f"| :--- | :--- |")
        md.append(f"| Total listings examined | **{stats.get('total_examined', 0)}** |")
        md.append(f"| Newly discovered listings | **{stats.get('new_discovered', 0)}** |")
        md.append(f"| Confirmed EMEA/Kenya-eligible matches | **{stats.get('confirmed_matches', 0)}** |")
        md.append(f"| Potential matches awaiting location verification | **{stats.get('potential_matches', 0)}** |")
        md.append(f"| Ineligible listings excluded (US/EU/UK only, etc.) | **{stats.get('ineligible_excluded', 0)}** |")
        md.append(f"| Duplicates removed | **{stats.get('duplicates_removed', 0)}** |")
        md.append(f"| Listings excluded (Date unverified / > 48h) | **{stats.get('unverified_excluded', 0)}** |")

        report_text = "\n".join(md)
        report_file = self.report_dir / f"daily_report_{date_file_str}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)

        # Also write latest
        with open(self.report_dir / "daily_report_latest.md", "w", encoding="utf-8") as f:
            f.write(report_text)

        return report_text
