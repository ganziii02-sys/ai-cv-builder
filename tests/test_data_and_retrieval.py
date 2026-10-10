"""Unit tests that do not need any API key.

Retrieval tests use a deterministic fake embedding backend (hashed bag-of-words)
so cosine ranking is exercised without network or heavy models.
"""

from __future__ import annotations

import numpy as np
import pytest

from cv_builder.config import load_config
from cv_builder.data_loader import job_text, load_jobs, load_profiles
from cv_builder.profile import from_synthetic
from cv_builder.retrieval import JobIndex, profile_query

CFG = load_config()


class HashBackend:
    name = "hash:test"
    dim = 256

    def embed(self, texts):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, hash(w) % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return out / norms


def test_nine_unique_jobs():
    jobs = load_jobs(CFG.jobs_path)
    assert len(jobs) == 9
    assert len({j["document_id"] for j in jobs}) == 9
    assert all(job_text(j) for j in jobs)


def test_synthetic_profiles_complete_enough_for_query():
    profiles = load_profiles(CFG.profiles_path)
    assert len(profiles) == 5
    for pid, raw in profiles.items():
        q = profile_query(from_synthetic(raw).to_dict())
        assert len(q) > 20


def test_retrieval_ranks_and_returns_ids(tmp_path):
    cfg = load_config()
    cfg.index_cache = tmp_path / "idx.npz"
    idx = JobIndex(cfg, backend=HashBackend())
    results = idx.search("machine learning nlp language models rag agent", k=3)
    assert len(results) == 3
    assert len({r.document_id for r in results}) == 3
    assert results[0].score >= results[1].score >= results[2].score
    assert all(r.excerpt for r in results)


def test_merge_normalises_messy_model_output():
    from cv_builder.profile import ProfileState

    p = ProfileState(user_id="x")
    p.merge(
        {
            "name": {"first": "Casey", "last": "Lee"},           # dict -> str
            "technical_skills": [                                  # list[dict] -> names
                {"skill": "Python", "evidence": "Library API"},
                {"name": "SQL"},
            ],
            "projects": ["Library API", {"title": "Agent demo"}],  # mixed -> list[dict]
            "skill_evidence": {"Python": {"where": "Library API"}},  # nested dict
            "experience": [""],                                    # empty -> dropped
        }
    )
    assert p.name == "Casey Lee"
    assert set(p.technical_skills) == {"Python", "SQL"}
    assert all(isinstance(x, dict) and x.get("title") for x in p.projects)
    assert p.experience == []
    assert isinstance(p.missing(), list)  # must not raise


def test_profile_isolation():
    profiles = load_profiles(CFG.profiles_path)
    a = from_synthetic(profiles["student_profile_01"])
    b = from_synthetic(profiles["student_profile_02"])
    a.merge({"technical_skills": ["INJECTED"]})
    assert "INJECTED" not in b.technical_skills
