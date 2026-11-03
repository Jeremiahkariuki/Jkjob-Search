# Jkjob-search — EMEA Remote Tech Job Intelligence System

A dedicated, evidence-based technical recruitment and opportunity-matching intelligence engine tailored for **Jeremiah Kariuki**, focusing strictly on verified remote vacancies open to candidates in **Kenya**, **Africa**, and the **EMEA timezone**.

---

## Project Structure

```
adventurous-bardeen/
├── cv/                              # Drop your CVs here (.pdf, .txt, .md, .docx)
├── profile/
│   ├── candidate_profile.json       # Consolidated machine-readable profile
│   └── candidate_profile.md         # Evidence-based profile & ATS keywords
├── data/
│   ├── jobs.db                      # SQLite persistent database (21-column schema)
│   ├── job_tracker.csv              # Continuous spreadsheet export
│   └── fresh_feed.json              # Fresh vacancies buffer (< 48 hrs)
├── reports/
│   ├── daily_report_latest.md       # Latest Daily Intelligence Report (Sections A-F)
│   └── daily_report_YYYY-MM-DD.md   # Historical reports
├── src/
│   ├── models.py                    # Data models
│   ├── cv_parser.py                 # Multi-CV parser & ATS extractor
│   ├── eligibility.py               # Strict EMEA / Kenya / Worldwide eligibility filter
│   ├── matcher.py                   # 100-point scoring algorithm
│   ├── fetcher.py                   # Multi-platform job puller (< 48-hr verification)
│   ├── tracker.py                   # SQLite storage & status preservation
│   ├── reporter.py                  # Report generator (Sections A-F)
│   └── runner.py                    # Orchestrator
├── automation/
│   ├── setup_cron.sh                # Cron installation for 08:00 EAT (Africa/Nairobi)
│   └── com.jeremiah.emea_job_intel.plist # macOS launchd agent configuration
└── run.py                           # Root CLI entrypoint
```

---

## 1. How to Upload Your CV

Place your CV file directly into the `cv/` directory:
- Supported formats: `.pdf`, `.txt`, `.md`, `.json`
- You can place multiple CVs (e.g., standard CV, frontend-focused CV, backend-focused CV). The parser consolidates them and flags any date or title discrepancies.

Run:
```bash
python3 run.py --parse-cv
```
Your consolidated profile, ATS keywords, and differentiator points will be saved to `profile/candidate_profile.md`.

---

## 2. Daily Pipeline Execution

Run the intelligence engine manually at any time:
```bash
python3 run.py
```
This will:
1. Load your consolidated candidate profile.
2. Search and pull vacancies across remote platforms (Remotive, Jobicy, Arbeitnow, Direct ATS like Greenhouse, Lever, Ashby).
3. Strictly filter out jobs older than 48 hours.
4. Enforce the strict EMEA/Kenya eligibility filter.
5. Score each vacancy out of 100 points against your CV.
6. Deduplicate and update the SQLite tracker (`data/jobs.db`).
7. Export the updated 21-column spreadsheet (`data/job_tracker.csv`).
8. Generate the daily intelligence report (`reports/daily_report_latest.md`).

---

## 3. Managing Application Statuses

When you apply for a job or get an interview, update its status so it is permanently preserved across future runs:

```bash
# Mark as Applied
python3 run.py --status "https://job-url-here" "Applied" --notes "Applied with tailored Next.js CV on 2026-11-03"

# Mark as Shortlisted or Interviewing
python3 run.py --status "https://job-url-here" "Interviewing" --notes "Screening interview scheduled"
```

Valid statuses:
- `Not reviewed` (default)
- `Shortlisted`
- `Applied`
- `Interviewing`
- `Rejected`
- `Closed`

---

## 4. Daily Automation Setup (Africa/Nairobi Time)

The system includes preconfigured scripts for daily automation at **08:00 AM East Africa Time (EAT / UTC+3)**:

### Option A: Standard Cron (Recommended)
```bash
bash automation/setup_cron.sh
```

### Option B: macOS Native launchd
```bash
cp automation/com.jeremiah.emea_job_intel.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jeremiah.emea_job_intel.plist
```
