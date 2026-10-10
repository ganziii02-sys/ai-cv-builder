"""Reusable confirmed-profile state.

One user builds ONE ProfileState. It is stored separately from any job-specific
CV content and stays unchanged when the target job changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# Agent-proposed list fields whose items must be dicts. If the model sends a
# bare string, wrap it under the given key.
_LIST_DICT_FIELDS = {
    "projects": "title",
    "experience": "role",
    "skill_evidence": "skill",
}


_STRING_LIST_FIELDS = ("technical_skills", "achievements")
_SCALAR_FIELDS = ("name", "contact_email", "education", "job_goal")


_NAME_KEYS = ("skill", "name", "title", "role", "value", "text")


def _flatten(v: Any) -> str:
    if isinstance(v, dict):
        for k in _NAME_KEYS:  # prefer a canonical label if present
            if v.get(k):
                return str(v[k])
        return " ".join(str(x) for x in v.values() if x)
    if isinstance(v, list):
        return ", ".join(_flatten(x) for x in v)
    return str(v)


def _normalise_field(field: str, value: Any) -> Any:
    """Coerce a model-proposed value into the shape ProfileState expects."""
    if field in _SCALAR_FIELDS:
        return _flatten(value) if value else ""

    if field in _STRING_LIST_FIELDS:
        if isinstance(value, dict):
            value = list(value.keys())
        if not isinstance(value, list):
            value = [value]
        return [_flatten(v).strip() for v in value if _flatten(v).strip()]

    if field in _LIST_DICT_FIELDS:
        key = _LIST_DICT_FIELDS[field]
        if isinstance(value, dict):
            value = [{key: k, "detail": _flatten(v)} for k, v in value.items()]
        if not isinstance(value, list):
            return value
        out = []
        for v in value:
            item = v if isinstance(v, dict) else {key: str(v)}
            item = {k: _flatten(val) for k, val in item.items()}
            if item.get(key, "").strip():
                out.append(item)
        return out

    return value


# Fields the CV needs before it can be generated.
REQUIRED_FIELDS = (
    "name",
    "contact_email",
    "education",
    "technical_skills",
    "experience",
    "projects",
    "job_goal",
)


@dataclass
class ProfileState:
    user_id: str
    name: str = ""
    contact_email: str = ""
    contact_other: dict[str, str] = field(default_factory=dict)
    education: str = ""
    technical_skills: list[str] = field(default_factory=list)
    skill_evidence: list[dict[str, str]] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    job_goal: str = ""
    confirmed: bool = False
    raw_introduction: str = ""

    def merge(self, fields: dict[str, Any]) -> None:
        """Apply agent-proposed fields. Lists extend (deduped), scalars overwrite."""
        for key, value in fields.items():
            if not hasattr(self, key):
                continue
            value = _normalise_field(key, value)
            current = getattr(self, key)
            if isinstance(current, list) and isinstance(value, list):
                for item in value:
                    if item not in current:
                        current.append(item)
            elif isinstance(current, dict) and isinstance(value, dict):
                current.update(value)
            else:
                setattr(self, key, value)

    def missing(self) -> list[str]:
        out = []
        for f in REQUIRED_FIELDS:
            v = getattr(self, f)
            if not v:
                out.append(f)
        # a claimed skill with no evidence link is also "missing" support
        evidenced = {
            str(e.get("skill", "")) if isinstance(e, dict) else str(e)
            for e in self.skill_evidence
        }
        unsupported = [
            s for s in self.technical_skills if str(s) not in evidenced
        ]
        if unsupported:
            out.append(f"skill_evidence for: {', '.join(unsupported)}")
        return out

    def is_complete(self) -> bool:
        return not self.missing()

    def summary_text(self) -> str:
        lines = [
            f"Name: {self.name}",
            f"Email: {self.contact_email or '(missing)'}",
            f"Education: {self.education or '(missing)'}",
            f"Job goal: {self.job_goal or '(missing)'}",
            f"Skills: {', '.join(self.technical_skills) or '(none)'}",
            f"Projects: {', '.join(p.get('title', '?') for p in self.projects) or '(none)'}",
            f"Experience: {', '.join(e.get('role', '?') for e in self.experience) or '(none)'}",
            f"Achievements: {', '.join(self.achievements) or '(none)'}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def from_synthetic(profile: dict[str, Any]) -> ProfileState:
    """Build a (confirmed) ProfileState from a data/student_profiles.jsonl row.

    Used for automated tests and the marker's additional profiles.
    """
    links = profile.get("links", {})
    return ProfileState(
        user_id=profile["document_id"],
        name=profile.get("name", ""),
        contact_email=f"{profile.get('name', 'user').split()[0].lower()}@example.com",
        contact_other={k: v for k, v in links.items()},
        education=" ".join(
            x for x in [profile.get("degree"), profile.get("institution"),
                        profile.get("year")] if x
        ),
        technical_skills=list(profile.get("technical_skills", [])),
        skill_evidence=list(profile.get("skill_evidence", [])),
        experience=list(profile.get("experience", [])),
        projects=list(profile.get("projects", [])),
        achievements=list(profile.get("activities", [])),
        job_goal=", ".join(profile.get("target_roles", [])),
        confirmed=True,
        raw_introduction="",
    )
