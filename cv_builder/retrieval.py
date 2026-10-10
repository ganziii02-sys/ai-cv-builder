"""Retrieval-Augmented Generation over data/jobs.jsonl.

Loads all job records, embeds each once (cached to disk), embeds the profile
query, ranks by cosine similarity, and returns the top-k with a supporting
excerpt from each record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config
from .data_loader import job_text, load_jobs
from .embeddings import EmbeddingBackend, build_backend

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+")


@dataclass
class RetrievedJob:
    document_id: str
    title: str
    score: float
    excerpt: str
    record: dict[str, Any]


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _best_excerpt(description: str, query: str, max_sentences: int = 2) -> str:
    """Sentence(s) from the job description with the most query-term overlap."""
    q = _tokens(query)
    sents = [s.strip() for s in _SENT_SPLIT.split(description) if s.strip()]
    if not sents:
        return description[:300]
    scored = sorted(
        sents, key=lambda s: len(_tokens(s) & q) / (len(_tokens(s)) or 1), reverse=True
    )
    return " ".join(scored[:max_sentences])


class JobIndex:
    def __init__(self, cfg: Config, backend: EmbeddingBackend | None = None) -> None:
        self.cfg = cfg
        self.jobs = load_jobs(cfg.jobs_path)
        self.backend = backend or build_backend(cfg.embeddings)
        self.matrix = self._load_or_build()

    def _load_or_build(self) -> np.ndarray:
        cache = self.cfg.index_cache
        texts = [job_text(j) for j in self.jobs]
        if cache.exists():
            data = np.load(cache, allow_pickle=True)
            if (
                str(data.get("backend")) == self.backend.name
                and list(data.get("ids")) == [j["document_id"] for j in self.jobs]
            ):
                return data["matrix"]
        matrix = self.backend.embed(texts)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            cache,
            matrix=matrix,
            backend=self.backend.name,
            ids=np.array([j["document_id"] for j in self.jobs]),
        )
        return matrix

    def search(self, query: str, k: int | None = None) -> list[RetrievedJob]:
        k = k or self.cfg.top_k
        qv = self.backend.embed([query])[0]
        scores = self.matrix @ qv  # cosine (vectors are unit norm)
        order = np.argsort(-scores)[:k]
        return [
            RetrievedJob(
                document_id=self.jobs[i]["document_id"],
                title=self.jobs[i].get("title", ""),
                score=float(scores[i]),
                excerpt=_best_excerpt(self.jobs[i].get("description", ""), query),
                record=self.jobs[i],
            )
            for i in order
        ]


def profile_query(profile: dict[str, Any]) -> str:
    """Build the retrieval query from confirmed profile facts + job goal.

    The job goal / target roles are repeated so intent outweighs the long tail
    of shared tooling keywords (Python, Git, SQL) that every profile lists.
    """
    goal = profile.get("job_goal") or profile.get("target_roles") or ""
    goal = goal if isinstance(goal, str) else ", ".join(goal)
    parts: list[str] = [goal, goal] if goal else []
    parts += profile.get("technical_skills", [])[:8]
    for p in profile.get("projects", []):
        parts.append(p.get("title", "") if isinstance(p, dict) else str(p))
    parts.append(profile.get("summary", ""))
    return " | ".join(p for p in parts if p)


def format_results(results: list[RetrievedJob]) -> str:
    lines = []
    for r in results:
        lines.append(f"- {r.document_id} (score {r.score:.3f}) — {r.title}")
        lines.append(f"  excerpt: {r.excerpt}")
    return "\n".join(lines)
