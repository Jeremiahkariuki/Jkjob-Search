"""
Matching & 100-Point Scoring Algorithm.
Strictly implements the Section 5 rubric:
- Technical skill match: 30 points
- Relevant professional experience & project evidence: 25 points
- Seniority & responsibility alignment: 15 points
- EMEA/Kenya eligibility certainty: 15 points
- Employment type & career alignment: 10 points
- Evidence of fresh, active vacancy (< 48 hrs): 5 points
"""
import re
from typing import List, Tuple
from src.models import CandidateProfile, JobPosting, MatchEvaluation
from src.eligibility import EligibilityEngine

class JobMatcher:
    @classmethod
    def evaluate(cls, job: JobPosting, profile: CandidateProfile) -> MatchEvaluation:
        # Mandatory override check: if location is strictly ineligible, score drops to 0 and skip
        if job.emea_eligibility_status == EligibilityEngine.NOT_ELIGIBLE:
            return MatchEvaluation(
                score=0,
                technical_skill_score=0,
                experience_project_score=0,
                seniority_alignment_score=0,
                emea_certainty_score=0,
                employment_career_score=0,
                freshness_score=0,
                match_reasons=["Ineligible location (strictly restricted away from EMEA/Kenya)."],
                missing_requirements_or_risks=[f"Location restriction: {job.eligibility_evidence}"],
                recommended_action="Skip"
            )

        match_reasons = []
        cv_skills_matched = []
        missing_risks = []
        essential_met = []

        # 1. Technical skill match (max 30)
        tech_score = 0
        candidate_skills = [s.lower() for s in profile.technical_skills]
        if job.required_skills and candidate_skills:
            matched = [s for s in job.required_skills if any(cs in s.lower() or s.lower() in cs for cs in candidate_skills)]
            cv_skills_matched = matched
            ratio = len(matched) / max(len(job.required_skills), 1)
            tech_score = int(min(30, round(ratio * 30)))
            if matched:
                match_reasons.append(f"Strong overlap in core technologies: {', '.join(matched[:5])}")
            unmatched = [s for s in job.required_skills if s not in matched]
            if unmatched:
                missing_risks.append(f"Unmatched required skills in posting: {', '.join(unmatched[:4])}")
        else:
            # Fallback text matching on snippet/title
            text_to_search = f"{job.title} {job.description_snippet}".lower()
            matched = [s for s in candidate_skills if re.search(r"\b" + re.escape(s) + r"\b", text_to_search)]
            cv_skills_matched = matched
            if matched:
                tech_score = min(25, 10 + len(matched) * 3)
                match_reasons.append(f"Skills verified in description: {', '.join(matched[:5])}")
            else:
                tech_score = 5

        # 2. Relevant professional experience and project evidence (max 25)
        exp_score = 0
        req_years = cls._extract_required_years(f"{job.title} {job.description_snippet}")
        if req_years > 0:
            if profile.years_of_experience >= req_years:
                exp_score = 25
                essential_met.append(f"Meets or exceeds required experience: {profile.years_of_experience:.1f} yrs vs {req_years} required.")
            elif profile.years_of_experience >= (req_years - 1):
                exp_score = 18
                essential_met.append(f"Near experience threshold: {profile.years_of_experience:.1f} yrs vs {req_years} required.")
            else:
                exp_score = 10
                missing_risks.append(f"Role asks for {req_years}+ years experience; profile indicates ~{profile.years_of_experience:.1f} years.")
        else:
            # Default experience score based on candidate's verified background
            exp_score = 20 if profile.years_of_experience >= 3 else 15
            essential_met.append(f"Demonstrated production experience aligned with job scope.")

        # 3. Seniority and responsibility alignment (max 15)
        seniority_score = 0
        job_title_lower = job.title.lower()
        title_keywords = ["software engineer", "backend", "full-stack", "full stack", "developer", "odoo", "qa", "python", "django", "typescript"]
        if any(kw in job_title_lower for kw in title_keywords) or any(role.lower() in job_title_lower or any(part in job_title_lower for part in role.lower().split(" / ")) for role in profile.primary_roles):
            seniority_score += 8
            match_reasons.append(f"Direct role title alignment with profile domain: '{job.title}'")
        
        job_seniority = job.seniority.lower()
        candidate_seniority = [s.lower() for s in profile.seniority_levels]
        if any(s in job_seniority or s in job_title_lower for s in candidate_seniority) or "senior" in job_seniority or "mid" in job_seniority:
            seniority_score += 7
            match_reasons.append(f"Seniority level ({job.seniority}) aligns with candidate experience")
        else:
            seniority_score += 4

        # 4. EMEA/Kenya eligibility certainty (max 15)
        emea_score = 0
        if job.emea_eligibility_status == EligibilityEngine.CONFIRMED:
            emea_score = 15
            essential_met.append(f"Confirmed hiring eligibility: {job.eligibility_evidence}")
        elif job.emea_eligibility_status == EligibilityEngine.POTENTIAL:
            emea_score = 8
            missing_risks.append(f"Hiring location needs direct verification: {job.eligibility_evidence}")
        else:
            emea_score = 0

        # 5. Employment type and career-goal alignment (max 10)
        employment_score = 8
        if "full-time" in job.employment_type.lower() or "contract" in job.employment_type.lower():
            employment_score = 10
            essential_met.append(f"Verified employment model: {job.employment_type}")

        # 6. Evidence of a fresh, active vacancy (max 5)
        freshness_score = 5 if job.is_date_verified else 2
        if job.is_date_verified:
            essential_met.append(f"Verified fresh publication timestamp within active window.")

        total_score = min(100, tech_score + exp_score + seniority_score + emea_score + employment_score + freshness_score)

        # Decide recommended action
        if total_score >= 75 and job.emea_eligibility_status == EligibilityEngine.CONFIRMED:
            action = "Prioritize applying"
        elif total_score >= 50 or job.emea_eligibility_status == EligibilityEngine.POTENTIAL:
            action = "Investigate further"
        else:
            action = "Skip"

        return MatchEvaluation(
            score=total_score,
            technical_skill_score=tech_score,
            experience_project_score=exp_score,
            seniority_alignment_score=seniority_score,
            emea_certainty_score=emea_score,
            employment_career_score=employment_score,
            freshness_score=freshness_score,
            match_reasons=match_reasons,
            cv_skills_matched=cv_skills_matched,
            essential_requirements_met=essential_met,
            missing_requirements_or_risks=missing_risks,
            recommended_action=action
        )

    @staticmethod
    def _extract_required_years(text: str) -> float:
        matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", text.lower())
        if matches:
            return float(matches[0])
        return 0.0
