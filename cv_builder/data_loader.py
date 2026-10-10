"""Read the supplied JSONL data files. No transformation beyond parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:  # pragma: no cover - defensive
                raise ValueError(f"{path.name}:{i}: invalid JSON: {e}") from e
    return rows


def load_jobs(path: Path) -> list[dict[str, Any]]:
    """All job records, each with a unique `document_id`."""
    jobs = _read_jsonl(path)
    ids = [j["document_id"] for j in jobs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate document_id in {path.name}")
    return jobs


def job_text(job: dict[str, Any]) -> str:
    """Single text used to embed a job for retrieval.

    The title is repeated so the role name carries weight against nine
    similarly-worded AI-engineering descriptions.
    """
    title = job.get("title", "")
    return f"{title}. {title}. {job.get('description', '')}".strip()


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    """Synthetic confirmed-profile facts, keyed by `document_id`."""
    return {p["document_id"]: p for p in _read_jsonl(path)}


def load_introductions(path: Path) -> dict[str, dict[str, Any]]:
    """Initial plain-English introductions, keyed by `document_id`."""
    return {p["document_id"]: p for p in _read_jsonl(path)}
