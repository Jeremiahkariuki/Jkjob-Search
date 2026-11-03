"""
Core data models for the EMEA Remote Tech Job Intelligence System.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

@dataclass
class CandidateProfile:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = "Kenya (Africa/Nairobi - EAT)"
    primary_roles: List[str] = field(default_factory=list)
    seniority_levels: List[str] = field(default_factory=list)
    years_of_experience: float = 0.0
    technical_skills: List[str] = field(default_factory=list)
    frontend_skills: List[str] = field(default_factory=list)
    backend_skills: List[str] = field(default_factory=list)
    database_skills: List[str] = field(default_factory=list)
    devops_cloud_skills: List[str] = field(default_factory=list)
    tools_frameworks: List[str] = field(default_factory=list)
    key_projects: List[Dict[str, Any]] = field(default_factory=list)
    differentiating_skills: List[str] = field(default_factory=list)
    ats_keywords: List[str] = field(default_factory=list)
    source_cv_files: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: List[str] = field(default_factory=list)

@dataclass
class JobPosting:
    job_id: str
    title: str
    company: str
    application_url: str
    source: str
    original_posting_date: str  # ISO 8601 string or RFC
    posting_timestamp: float    # Unix timestamp
    work_arrangement: str       # Remote, Hybrid, Onsite
    eligible_locations: str     # Raw string from listing
    emea_eligibility_status: str # "Confirmed eligible", "Potentially eligible", "Not eligible"
    eligibility_evidence: str
    employment_type: str        # Full-time, Contract, Part-time
    seniority: str              # Junior, Mid-level, Senior, Lead, Staff, Principal
    salary: str = "Undisclosed"
    required_skills: List[str] = field(default_factory=list)
    description_snippet: str = ""
    is_date_verified: bool = True
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class MatchEvaluation:
    score: int
    technical_skill_score: int       # max 30
    experience_project_score: int    # max 25
    seniority_alignment_score: int   # max 15
    emea_certainty_score: int        # max 15
    employment_career_score: int     # max 10
    freshness_score: int             # max 5
    match_reasons: List[str] = field(default_factory=list)
    cv_skills_matched: List[str] = field(default_factory=list)
    essential_requirements_met: List[str] = field(default_factory=list)
    missing_requirements_or_risks: List[str] = field(default_factory=list)
    recommended_action: str = "Investigate further" # "Prioritize applying", "Investigate further", "Skip"
