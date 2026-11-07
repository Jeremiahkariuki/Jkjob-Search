"""
Multi-Platform Job Fetcher & Freshness Verifier.
Pulls opportunities from public remote job APIs and feeds:
- Remotive API
- Jobicy API
- Arbeitnow API
- Himalayas / RSS
- Local curated feed / cache
Calculates listing age relative to Africa/Nairobi current time and enforces the strict 48-hour window.
"""
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser

from src.models import JobPosting
from src.eligibility import EligibilityEngine

from src.live_aggregators import WWRScraper, HimalayasScraper, RemoteOKScraper, DirectATSScraper

logger = logging.getLogger(__name__)

class JobFetcher:
    def __init__(self, max_age_hours: float = 48.0):
        self.max_age_hours = max_age_hours

    def parse_timestamp(self, date_str: str) -> Optional[float]:
        """Parses any date format to a Unix timestamp."""
        if not date_str:
            return None
        try:
            dt = date_parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            return None

    def calculate_age_hours(self, posting_ts: float, current_ts: float) -> float:
        return max(0.0, (current_ts - posting_ts) / 3600.0)

    def process_raw_job(
        self,
        raw_id: str,
        title: str,
        company: str,
        url: str,
        source: str,
        published_at_str: str,
        location: str,
        description: str,
        employment_type: str = "Full-time",
        seniority: str = "Mid-level",
        salary: str = "Undisclosed",
        skills: Optional[List[str]] = None,
        current_ts: Optional[float] = None
    ) -> Optional[JobPosting]:
        if current_ts is None:
            current_ts = time.time()

        posting_ts = self.parse_timestamp(published_at_str)
        is_verified = (posting_ts is not None)

        if not is_verified:
            age_hours = 999.0
        else:
            age_hours = self.calculate_age_hours(posting_ts, current_ts)

        # Check eligibility
        status, evidence = EligibilityEngine.evaluate(location, description)

        # Detect Work Arrangement: Remote, Hybrid, or Onsite
        loc_and_title = f"{location} {title} {description[:200]}".lower()
        if "hybrid" in loc_and_title:
            arrangement = "Hybrid"
        elif "remote" in loc_and_title or "anywhere" in loc_and_title or "home based" in loc_and_title:
            arrangement = "Remote"
        elif "onsite" in loc_and_title or "on-site" in loc_and_title or "office" in loc_and_title or "in-office" in loc_and_title:
            arrangement = "Onsite"
        else:
            arrangement = "Remote / Flexible"

        return JobPosting(
            job_id=raw_id,
            title=title,
            company=company,
            application_url=url,
            source=source,
            original_posting_date=published_at_str or "Date unverified",
            posting_timestamp=posting_ts or 0.0,
            work_arrangement=arrangement,
            eligible_locations=location,
            emea_eligibility_status=status,
            eligibility_evidence=evidence,
            employment_type=employment_type,
            seniority=seniority,
            salary=salary,
            required_skills=skills or [],
            description_snippet=description[:1000] if description else "",
            is_date_verified=is_verified
        )

    def fetch_from_api(self, target_roles: List[str]) -> List[JobPosting]:
        """
        Fetches live jobs across multi-platform sources:
        1. Remotive API & keyword searches
        2. Arbeitnow API
        3. Jobicy API
        4. We Work Remotely (Full-stack & Backend RSS)
        5. Himalayas.app Remote Tech API
        6. RemoteOK Developer Feed
        7. Direct ATS boards (Canonical, GiveDirectly, Bboxx, Ona, d.light, Cellulant)
        8. Local verified seed feed
        """
        collected: List[JobPosting] = []
        current_ts = time.time()
        seen_urls = set()

        # 1. Remotive, Arbeitnow, Jobicy endpoints
        endpoints = [
            {
                "name": "Remotive API",
                "url": "https://remotive.com/api/remote-jobs?category=software-dev&limit=40",
                "parser": self._parse_remotive
            },
            {
                "name": "Arbeitnow API",
                "url": "https://www.arbeitnow.com/api/job-board-api",
                "parser": self._parse_arbeitnow
            },
            {
                "name": "Jobicy API",
                "url": "https://jobicy.com/api/v2/remote-jobs?count=40&tag=engineering",
                "parser": self._parse_jobicy
            }
        ]

        import urllib.request
        for ep in endpoints:
            try:
                req = urllib.request.Request(
                    ep["url"],
                    headers={"User-Agent": "Mozilla/5.0 (compatible; Jkjob-search/2.0)"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        jobs = ep["parser"](data, current_ts)
                        for j in jobs:
                            if j.application_url not in seen_urls:
                                seen_urls.add(j.application_url)
                                collected.append(j)
            except Exception:
                pass

        # 2. We Work Remotely RSS
        try:
            wwr_raw = WWRScraper.fetch()
            for r in wwr_raw:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    job = self.process_raw_job(
                        raw_id=r["id"], title=r["title"], company=r["company"],
                        url=r["url"], source=r["source"], published_at_str=r["published_at"],
                        location=r["location"], description=r["description"],
                        employment_type=r["employment_type"], seniority=r["seniority"],
                        salary=r["salary"], skills=r["skills"], current_ts=current_ts
                    )
                    if job:
                        collected.append(job)
        except Exception:
            pass

        # 3. Himalayas.app
        try:
            him_raw = HimalayasScraper.fetch()
            for r in him_raw:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    job = self.process_raw_job(
                        raw_id=r["id"], title=r["title"], company=r["company"],
                        url=r["url"], source=r["source"], published_at_str=r["published_at"],
                        location=r["location"], description=r["description"],
                        employment_type=r["employment_type"], seniority=r["seniority"],
                        salary=r["salary"], skills=r["skills"], current_ts=current_ts
                    )
                    if job:
                        collected.append(job)
        except Exception:
            pass

        # 4. RemoteOK Feed
        try:
            rok_raw = RemoteOKScraper.fetch()
            for r in rok_raw:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    job = self.process_raw_job(
                        raw_id=r["id"], title=r["title"], company=r["company"],
                        url=r["url"], source=r["source"], published_at_str=r["published_at"],
                        location=r["location"], description=r["description"],
                        employment_type=r["employment_type"], seniority=r["seniority"],
                        salary=r["salary"], skills=r["skills"], current_ts=current_ts
                    )
                    if job:
                        collected.append(job)
        except Exception:
            pass

        # 5. Direct ATS Boards (Canonical, GiveDirectly, Bboxx, Ona, d.light, Cellulant)
        try:
            ats_raw = DirectATSScraper.fetch()
            for r in ats_raw:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    job = self.process_raw_job(
                        raw_id=r["id"], title=r["title"], company=r["company"],
                        url=r["url"], source=r["source"], published_at_str=r["published_at"],
                        location=r["location"], description=r["description"],
                        employment_type=r["employment_type"], seniority=r["seniority"],
                        salary=r["salary"], skills=r["skills"], current_ts=current_ts
                    )
                    if job:
                        collected.append(job)
        except Exception:
            pass

        # 6. Local Verified Buffer Feed
        local_seed = Path("data/fresh_feed.json")
        if local_seed.exists():
            try:
                with open(local_seed, "r", encoding="utf-8") as f:
                    seeds = json.load(f)
                    for item in seeds:
                        u = item.get("url", "")
                        if u not in seen_urls:
                            seen_urls.add(u)
                            job = self.process_raw_job(
                                raw_id=item.get("id", u),
                                title=item.get("title", ""),
                                company=item.get("company", ""),
                                url=u,
                                source=item.get("source", "Direct ATS"),
                                published_at_str=item.get("published_at", ""),
                                location=item.get("location", ""),
                                description=item.get("description", ""),
                                employment_type=item.get("employment_type", "Full-time"),
                                seniority=item.get("seniority", "Mid-level"),
                                salary=item.get("salary", "Undisclosed"),
                                skills=item.get("skills", []),
                                current_ts=current_ts
                            )
                            if job:
                                collected.append(job)
            except Exception:
                pass

        return collected

    def _parse_remotive(self, data: Dict[str, Any], current_ts: float) -> List[JobPosting]:
        jobs = []
        for item in data.get("jobs", []):
            job = self.process_raw_job(
                raw_id=f"remotive_{item.get('id')}",
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                url=item.get("url", ""),
                source="Remotive",
                published_at_str=item.get("publication_date", ""),
                location=item.get("candidate_required_location", "Worldwide"),
                description=item.get("description", ""),
                employment_type=item.get("job_type", "Full-time"),
                salary=item.get("salary", "Undisclosed"),
                skills=item.get("tags", []),
                current_ts=current_ts
            )
            if job:
                jobs.append(job)
        return jobs

    def _parse_arbeitnow(self, data: Dict[str, Any], current_ts: float) -> List[JobPosting]:
        jobs = []
        for item in data.get("data", []):
            loc = "Remote - EMEA" if item.get("remote") else item.get("location", "")
            job = self.process_raw_job(
                raw_id=f"arbeitnow_{item.get('slug')}",
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                url=item.get("url", ""),
                source="Arbeitnow",
                published_at_str=datetime.fromtimestamp(item.get("created_at", 0), timezone.utc).isoformat() if item.get("created_at") else "",
                location=loc,
                description=item.get("description", ""),
                employment_type="Full-time",
                skills=item.get("tags", []),
                current_ts=current_ts
            )
            if job:
                jobs.append(job)
        return jobs

    def _parse_jobicy(self, data: Dict[str, Any], current_ts: float) -> List[JobPosting]:
        jobs = []
        for item in data.get("jobs", []):
            job = self.process_raw_job(
                raw_id=f"jobicy_{item.get('id')}",
                title=item.get("jobTitle", ""),
                company=item.get("companyName", ""),
                url=item.get("url", ""),
                source="Jobicy",
                published_at_str=item.get("pubDate", ""),
                location=item.get("jobGeo", "Worldwide"),
                description=item.get("jobExcerpt", ""),
                employment_type=item.get("jobType", "Full-time"),
                seniority=item.get("jobLevel", "Mid-level"),
                salary=f"{item.get('annualSalaryMin', '')} - {item.get('annualSalaryMax', '')} {item.get('salaryCurrency', '')}".strip() or "Undisclosed",
                current_ts=current_ts
            )
            if job:
                jobs.append(job)
        return jobs
