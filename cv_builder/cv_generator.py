"""Generate an editable, confirmed-facts-only CV for one selected job, then a
fact-check pass drops any claim not traceable to the profile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .llm import LLM
from .profile import ProfileState
from .prompts import CV_SYSTEM

_WORD = re.compile(r"[a-z0-9]+")


@dataclass
class CV:
    job_document_id: str
    summary: str
    matched_skills: list[dict[str, str]]
    missing_requirements: list[dict[str, str]]
    sections: list[dict[str, Any]]
    dropped_claims: list[str] = field(default_factory=list)

    def edit_section(self, heading: str, items: list[str]) -> bool:
        for s in self.sections:
            if s["heading"].lower() == heading.lower():
                s["items"] = items
                return True
        return False


def _profile_evidence_corpus(profile: ProfileState) -> str:
    parts = [profile.summary_text()]
    for e in profile.skill_evidence:
        parts.append(
            f"{e.get('skill', '')} {e.get('source', '')}" if isinstance(e, dict) else str(e)
        )
    for p in profile.projects:
        parts.append(p.get("title", "") + " " + p.get("description", ""))
        parts += p.get("technologies", [])
    for e in profile.experience:
        parts.append(e.get("role", "") + " " + e.get("description", ""))
    return " ".join(parts).lower()


def _supported(evidence: str, corpus: str, threshold: float = 0.5) -> bool:
    toks = set(_WORD.findall(evidence.lower()))
    if not toks:
        return False
    hit = sum(1 for t in toks if t in corpus)
    return hit / len(toks) >= threshold


def generate_cv(llm: LLM, profile: ProfileState, job: dict[str, Any]) -> CV:
    user = (
        "CONFIRMED PROFILE (JSON):\n"
        + _json(profile.to_dict())
        + "\n\nTARGET JOB (JSON):\n"
        + _json({k: job[k] for k in ("document_id", "title", "description") if k in job})
    )
    data = llm.json_object(CV_SYSTEM, user)

    corpus = _profile_evidence_corpus(profile)
    kept, dropped = [], []
    for m in data.get("matched_skills", []):
        if _supported(m.get("profile_evidence", ""), corpus):
            kept.append(m)
        else:
            dropped.append(f"{m.get('skill')}: {m.get('profile_evidence')}")

    return CV(
        job_document_id=job["document_id"],
        summary=data.get("summary", ""),
        matched_skills=kept,
        missing_requirements=data.get("missing_requirements", []),
        sections=data.get("sections", []),
        dropped_claims=dropped,
    )


def _json(obj: Any) -> str:
    import json

    return json.dumps(obj, indent=2, ensure_ascii=False)
