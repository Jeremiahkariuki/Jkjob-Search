"""
Live Multi-Platform Aggregators for Jkjob-search.
Pulls fresh vacancies from:
1. We Work Remotely (Software Engineering RSS)
2. Himalayas.app Remote Tech API
3. RemoteOK Live Developer JSON Feed
4. Direct ATS Boards (Canonical, GiveDirectly, Bboxx, Ona, d.light)
"""
import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (Jkjob-search/2.0)"

def make_request(url: str, timeout: int = 10) -> Optional[bytes]:
    """Makes a reliable HTTP GET request with standard browser headers."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read()
    except Exception as e:
        logger.debug(f"Request failed for {url}: {e}")
    return None

class WWRScraper:
    """We Work Remotely RSS Feeds"""
    FEEDS = [
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss"
    ]

    @classmethod
    def fetch(cls) -> List[Dict[str, Any]]:
        jobs = []
        for feed_url in cls.FEEDS:
            data = make_request(feed_url)
            if not data:
                continue
            try:
                root = ET.fromstring(data)
                for item in root.findall(".//item"):
                    title = item.findtext("title", "").strip()
                    link = item.findtext("link", "").strip()
                    pub_date = item.findtext("pubDate", "").strip()
                    desc = item.findtext("description", "")
                    guid = item.findtext("guid", link)
                    
                    # Split title if format is "Company: Title"
                    company = "Unknown"
                    job_title = title
                    if ":" in title:
                        parts = title.split(":", 1)
                        company = parts[0].strip()
                        job_title = parts[1].strip()

                    region = item.findtext("region", "Worldwide / Remote")

                    jobs.append({
                        "id": f"wwr_{guid.split('/')[-1]}",
                        "title": job_title,
                        "company": company,
                        "url": link,
                        "source": "We Work Remotely",
                        "published_at": pub_date,
                        "location": region or "Worldwide / Remote",
                        "description": desc,
                        "employment_type": "Full-time",
                        "seniority": "Mid-level",
                        "salary": "Undisclosed",
                        "skills": []
                    })
            except Exception as e:
                logger.debug(f"Failed parsing WWR feed {feed_url}: {e}")
        return jobs

class HimalayasScraper:
    """Himalayas.app Remote Jobs API"""
    ENDPOINT = "https://himalayas.app/jobs/api?limit=40"

    @classmethod
    def fetch(cls) -> List[Dict[str, Any]]:
        jobs = []
        data = make_request(cls.ENDPOINT)
        if not data:
            return jobs
        try:
            payload = json.loads(data.decode("utf-8"))
            for item in payload.get("jobs", []):
                categories = item.get("categories", [])
                # Only include dev / engineering
                if any(c.lower() in ["software development", "engineering", "backend", "frontend", "full-stack"] for c in categories):
                    loc_restrictions = ", ".join(item.get("countryRestrictions", [])) or "Worldwide / Remote"
                    salary_min = item.get("minSalary")
                    salary_max = item.get("maxSalary")
                    salary_cur = item.get("salaryCurrency", "USD")
                    salary_str = f"{salary_min:,} - {salary_max:,} {salary_cur}" if salary_min and salary_max else "Undisclosed"

                    jobs.append({
                        "id": f"himalayas_{item.get('id', item.get('slug'))}",
                        "title": item.get("title", ""),
                        "company": item.get("companyName", "Company"),
                        "url": item.get("applicationLink") or f"https://himalayas.app/jobs/{item.get('slug')}",
                        "source": "Himalayas",
                        "published_at": item.get("pubDate", ""),
                        "location": loc_restrictions,
                        "description": item.get("excerpt", "") or item.get("description", ""),
                        "employment_type": item.get("employmentType", "Full-time"),
                        "seniority": item.get("seniority", "Mid-level"),
                        "salary": salary_str,
                        "skills": item.get("skills", [])
                    })
        except Exception as e:
            logger.debug(f"Failed parsing Himalayas: {e}")
        return jobs

class RemoteOKScraper:
    """RemoteOK JSON Feed"""
    ENDPOINT = "https://remoteok.com/api?tag=dev"

    @classmethod
    def fetch(cls) -> List[Dict[str, Any]]:
        jobs = []
        data = make_request(cls.ENDPOINT)
        if not data:
            return jobs
        try:
            items = json.loads(data.decode("utf-8"))
            # RemoteOK returns a legal notice object as first element
            if items and isinstance(items, list):
                for item in items[1:35]:
                    if not isinstance(item, dict):
                        continue
                    pub_ts = item.get("epoch")
                    pub_iso = datetime.fromtimestamp(pub_ts, timezone.utc).isoformat() if pub_ts else item.get("date", "")
                    
                    sal_min = item.get("salary_min")
                    sal_max = item.get("salary_max")
                    salary_str = f"${sal_min:,} - ${sal_max:,} USD" if sal_min and sal_max else "Undisclosed"

                    jobs.append({
                        "id": f"remoteok_{item.get('id')}",
                        "title": item.get("position", ""),
                        "company": item.get("company", ""),
                        "url": item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id')}"),
                        "source": "RemoteOK",
                        "published_at": pub_iso,
                        "location": item.get("location", "Worldwide Remote"),
                        "description": item.get("description", ""),
                        "employment_type": "Full-time",
                        "seniority": "Mid-level",
                        "salary": salary_str,
                        "skills": item.get("tags", [])
                    })
        except Exception as e:
            logger.debug(f"Failed parsing RemoteOK: {e}")
        return jobs

class DirectATSScraper:
    """Direct ATS scraping for employers known to hire in Kenya and Africa / EMEA."""
    
    # Target companies using Greenhouse
    GREENHOUSE_BOARDS = [
        {"slug": "canonical", "name": "Canonical"},
        {"slug": "givedirectly", "name": "GiveDirectly"},
        {"slug": "dlight", "name": "d.light"},
        {"slug": "alpaca", "name": "Alpaca"}
    ]

    # Target companies using Lever
    LEVER_BOARDS = [
        {"slug": "bboxx", "name": "Bboxx"},
        {"slug": "ona", "name": "Ona"},
        {"slug": "cellulant", "name": "Cellulant"}
    ]

    @classmethod
    def fetch(cls) -> List[Dict[str, Any]]:
        jobs = []
        # 1. Greenhouse Boards
        for gh in cls.GREENHOUSE_BOARDS:
            url = f"https://boards-api.greenhouse.io/v1/boards/{gh['slug']}/jobs?content=true"
            data = make_request(url)
            if not data:
                continue
            try:
                payload = json.loads(data.decode("utf-8"))
                for item in payload.get("jobs", []):
                    title = item.get("title", "")
                    loc = item.get("location", {}).get("name", "Remote")
                    # Target software / tech roles
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ["engineer", "developer", "backend", "full stack", "frontend", "software", "python"]):
                        jobs.append({
                            "id": f"gh_{gh['slug']}_{item.get('id')}",
                            "title": title,
                            "company": gh["name"],
                            "url": item.get("absolute_url", f"https://boards.greenhouse.io/{gh['slug']}/jobs/{item.get('id')}"),
                            "source": f"Greenhouse ({gh['name']})",
                            "published_at": item.get("updated_at", ""),
                            "location": loc,
                            "description": item.get("content", ""),
                            "employment_type": "Full-time",
                            "seniority": "Senior" if "senior" in title_lower or "lead" in title_lower else "Mid-level",
                            "salary": "Disclosed upon application",
                            "skills": []
                        })
            except Exception as e:
                logger.debug(f"Failed Greenhouse {gh['slug']}: {e}")

        # 2. Lever Boards
        for lev in cls.LEVER_BOARDS:
            url = f"https://api.lever.co/v0/postings/{lev['slug']}?mode=json"
            data = make_request(url)
            if not data:
                continue
            try:
                payload = json.loads(data.decode("utf-8"))
                for item in payload:
                    title = item.get("text", "")
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ["engineer", "developer", "backend", "full stack", "frontend", "software", "python"]):
                        categories = item.get("categories", {})
                        loc = categories.get("location", "Remote")
                        work_type = categories.get("commitment", "Full-time")
                        created_ts = item.get("createdAt")
                        created_iso = datetime.fromtimestamp(created_ts / 1000.0, timezone.utc).isoformat() if created_ts else ""

                        jobs.append({
                            "id": f"lever_{lev['slug']}_{item.get('id')}",
                            "title": title,
                            "company": lev["name"],
                            "url": item.get("hostedUrl", ""),
                            "source": f"Lever ({lev['name']})",
                            "published_at": created_iso,
                            "location": loc,
                            "description": item.get("descriptionPlain", "") or item.get("description", ""),
                            "employment_type": work_type,
                            "seniority": "Senior" if "senior" in title_lower or "lead" in title_lower else "Mid-level",
                            "salary": "Disclosed upon application",
                            "skills": []
                        })
            except Exception as e:
                logger.debug(f"Failed Lever {lev['slug']}: {e}")

        return jobs
