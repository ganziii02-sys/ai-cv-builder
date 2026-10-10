"""Turn the raw plain-English introduction into an initial ProfileState.

Extraction only — no inference. The agent fills the gaps afterwards.
"""

from __future__ import annotations

from .llm import LLM
from .profile import ProfileState

_BOOTSTRAP_SYSTEM = """\
Extract ONLY what the user explicitly stated in their introduction into a JSON
object with keys: name, contact_email, education, technical_skills (list of
strings), projects (list of {title, description}), experience (list of
{role, description}), achievements (list of strings), job_goal (string).
Use "" or [] for anything not stated. Do not infer or embellish.
Return the JSON object only.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "contact_email": {"type": "string"},
        "education": {"type": "string"},
        "technical_skills": {"type": "array", "items": {"type": "string"}},
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "achievements": {"type": "array", "items": {"type": "string"}},
        "job_goal": {"type": "string"},
    },
}


def bootstrap_profile(llm: LLM, user_id: str, intro: str) -> ProfileState:
    data = llm.json_object(_BOOTSTRAP_SYSTEM, intro, schema=_SCHEMA)
    profile = ProfileState(user_id=user_id, raw_introduction=intro)
    profile.merge(data)
    return profile
