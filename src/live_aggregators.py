"""
Live Multi-Platform Aggregators for Jkjob-search.
Pulls fresh vacancies from:
1. We Work Remotely (Software Engineering RSS)
2. Himalayas.app Remote Tech API
3. RemoteOK Live Developer JSON Feed
4. Direct ATS Boards (Canonical, GiveDirectly, d.light, Alpaca)
5. LinkedIn (Kenya + EMEA remote, public guest API)
"""
import json
import logging
import re
import ssl
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl._create_unverified_context()

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (Jkjob-search/2.0)"

def make_request(url: str, timeout: int = 10) -> Optional[bytes]:
    """Makes a reliable HTTP GET request with standard browser headers and verified SSL."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
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

    # Target companies using Lever (only valid slugs)
    LEVER_BOARDS = [
        {"slug": "andela", "name": "Andela"},
        {"slug": "turing", "name": "Turing"},
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


# ---------------------------------------------------------------------------
# LinkedIn Public Guest Scraper
# ---------------------------------------------------------------------------

def _parse_li_relative_date(dt_attr: str, time_text: str = "") -> str:
    """Convert LinkedIn relative text ('2 hours ago', '1 day ago') or ISO date to UTC string."""
    now = datetime.now(timezone.utc)
    text = (time_text or "").lower().strip()
    if any(unit in text for unit in ["hour", "minute", "just now", "sec"]):
        m = re.search(r'(\d+)\s*hour', text)
        hrs = int(m.group(1)) if m else 1
        return (now - timedelta(hours=hrs)).isoformat()
    if "day" in text:
        m = re.search(r'(\d+)\s*day', text)
        days = int(m.group(1)) if m else 1
        return (now - timedelta(days=days)).isoformat()
    if "week" in text:
        m = re.search(r'(\d+)\s*week', text)
        wks = int(m.group(1)) if m else 1
        return (now - timedelta(weeks=wks)).isoformat()
    if dt_attr:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                return datetime.strptime(dt_attr, fmt).replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    return now.isoformat()


class _LICardParser:
    """Regex-based parser to extract LinkedIn guest job card fields."""

    @classmethod
    def parse(cls, html: str) -> List[Dict[str, Any]]:
        jobs = []
        li_blocks = re.findall(r'<li\b[^>]*>(.*?)</li>', html, re.DOTALL)
        for b in li_blocks:
            t_m = re.search(r'class="base-search-card__title"[^>]*>(.*?)</h3>', b, re.DOTALL)
            c_m = re.search(r'class="base-search-card__subtitle"[^>]*>(.*?)</h4>', b, re.DOTALL)
            l_m = re.search(r'class="job-search-card__location"[^>]*>(.*?)</span>', b, re.DOTALL)
            u_m = re.search(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)', b)
            d_m = re.search(r'<time[^>]*datetime="([^"]+)"[^>]*>(.*?)</time>', b, re.DOTALL)
            
            if not d_m:
                d_m_tag = re.search(r'<time[^>]*>(.*?)</time>', b, re.DOTALL)
                time_text = d_m_tag.group(1).strip() if d_m_tag else ""
                dt_attr = ""
            else:
                dt_attr = d_m.group(1)
                time_text = d_m.group(2).strip()

            title = re.sub(r'<[^<]+?>', '', t_m.group(1)).strip() if t_m else ""
            company = re.sub(r'<[^<]+?>', '', c_m.group(1)).strip() if c_m else ""
            loc = re.sub(r'<[^<]+?>', '', l_m.group(1)).strip() if l_m else ""
            url = u_m.group(1) if u_m else ""

            if title and url:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": url,
                    "datetime": dt_attr,
                    "time_text": time_text,
                })
        return jobs


class LinkedInScraper:
    """
    Scrapes LinkedIn public guest job-search endpoint (no auth required).
    CV-tailored keyword queries for Jeremiah Kariuki Beth.
    Rate-limited: 1.5s sleep between requests.
    """

    _BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    QUERIES = [
        ("Python Django",   "Kenya",     {}),
        ("Odoo Developer",   "Kenya",     {}),
        ("Full Stack",       "Kenya",     {}),
        ("Python Developer", "Kenya",     {}),
        ("Python Engineer",  "Nairobi",   {}),
        ("Django Developer", "Worldwide", {"f_WT": "2"}),
        ("Python Developer", "EMEA",      {"f_WT": "2"}),
    ]

    _TECH_KW = [
        "python", "django", "backend", "back-end", "full stack", "fullstack",
        "odoo", "fastapi", "developer", "engineer", "software", "react",
        "typescript", "node", "api", "erp", "devops", "qa"
    ]

    @classmethod
    def _build_url(cls, keywords: str, location: str, extra: dict, start: int = 0) -> str:
        params = {"keywords": keywords, "location": location, "start": str(start)}
        params.update(extra)
        return cls._BASE + "?" + urllib.parse.urlencode(params)

    @classmethod
    def _make_li_request(cls, url: str) -> Optional[bytes]:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.linkedin.com/jobs/search/",
            })
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as e:
            logger.debug(f"LinkedIn request failed for {url}: {e}")
        return None

    @classmethod
    def fetch(cls) -> List[Dict[str, Any]]:
        all_jobs: List[Dict[str, Any]] = []
        seen_urls: set = set()

        for keywords, location, extra in cls.QUERIES:
            logger.info(f"LinkedIn: querying '{keywords}' in '{location}'")
            url = cls._build_url(keywords, location, extra)
            raw = cls._make_li_request(url)

            if not raw:
                time.sleep(1.0)
                continue

            try:
                html = raw.decode("utf-8", errors="replace")
                cards = _LICardParser.parse(html)

                for card in cards:
                    title = card.get("title", "")
                    job_url = card.get("url", "")
                    company = card.get("company", "Unknown")
                    loc = card.get("location", location)
                    dt_attr = card.get("datetime", "")
                    time_text = card.get("time_text", "")

                    if not title or not job_url or job_url in seen_urls:
                        continue
                    if not any(kw in title.lower() for kw in cls._TECH_KW):
                        continue

                    seen_urls.add(job_url)
                    loc_lower = loc.lower()
                    emp_type = "Remote" if "remote" in loc_lower else ("Hybrid" if "hybrid" in loc_lower else "Full-time")
                    seniority = "Senior" if any(s in title.lower() for s in ["senior", "lead", "principal", "head"]) else "Mid-level"
                    slug = re.sub(r"[^a-z0-9]", "_", job_url.rstrip("/").split("/")[-1].lower())[:40]

                    all_jobs.append({
                        "id": f"li_{slug}",
                        "title": title,
                        "company": company,
                        "url": job_url,
                        "source": "LinkedIn",
                        "published_at": _parse_li_relative_date(dt_attr, time_text),
                        "location": loc,
                        "description": f"{title} at {company}. Location: {loc}. Apply on LinkedIn.",
                        "employment_type": emp_type,
                        "seniority": seniority,
                        "salary": "Not disclosed",
                        "skills": [],
                    })

                logger.info(f"LinkedIn: {len(cards)} cards parsed for '{keywords}'")
            except Exception as e:
                logger.warning(f"LinkedIn parse error for '{keywords}': {e}")

            time.sleep(1.0)

        logger.info(f"LinkedIn total: {len(all_jobs)} unique jobs")
        return all_jobs
