"""Load configuration from config.yaml (falling back to config.example.yaml) and
the environment. Keeps secrets out of source: env vars win over file values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_raw() -> dict[str, Any]:
    for name in ("config.yaml", "config.example.yaml"):
        p = ROOT / name
        if p.exists():
            with p.open() as f:
                return yaml.safe_load(f) or {}
    raise FileNotFoundError("No config.yaml or config.example.yaml found")


@dataclass
class LLMConfig:
    provider: str = "google"
    model: str = "gemini-flash-lite-latest"
    max_tokens: int = 4000
    thinking_budget: int | None = 0  # 0 = off (much faster); None = model default
    api_key: str | None = None

    def resolved_key(self) -> str | None:
        env = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        return env or (
            self.api_key if self.api_key and "YOUR_" not in self.api_key else None
        )


@dataclass
class EmbeddingsConfig:
    backend: str = "local"
    local_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    top_k: int = 3
    index_cache: Path = ROOT / "outputs" / "job_index.npz"
    max_steps: int = 8
    jobs_path: Path = ROOT / "data" / "jobs.jsonl"
    profiles_path: Path = ROOT / "data" / "student_profiles.jsonl"
    introductions_path: Path = ROOT / "data" / "student_introductions.jsonl"
    outputs_dir: Path = ROOT / "outputs"


def load_config() -> Config:
    raw = _load_raw()
    llm_raw = raw.get("llm", {})
    emb_raw = raw.get("embeddings", {})
    ret_raw = raw.get("retrieval", {})
    agent_raw = raw.get("agent", {})
    paths_raw = raw.get("paths", {})

    cfg = Config(
        llm=LLMConfig(
            provider=llm_raw.get("provider", "google"),
            model=llm_raw.get("model", "gemini-flash-lite-latest"),
            max_tokens=int(llm_raw.get("max_tokens", 4000)),
            thinking_budget=llm_raw.get("thinking_budget", 0),
            api_key=llm_raw.get("api_key"),
        ),
        embeddings=EmbeddingsConfig(
            backend=emb_raw.get("backend", "local"),
            local_model=emb_raw.get("local", {}).get(
                "model", "sentence-transformers/all-MiniLM-L6-v2"
            ),
        ),
        top_k=int(ret_raw.get("top_k", 3)),
        max_steps=int(agent_raw.get("max_steps", 8)),
    )
    if "index_cache" in ret_raw:
        cfg.index_cache = ROOT / ret_raw["index_cache"]
    for key, attr in (
        ("jobs", "jobs_path"),
        ("profiles", "profiles_path"),
        ("introductions", "introductions_path"),
        ("outputs", "outputs_dir"),
    ):
        if key in paths_raw:
            setattr(cfg, attr, ROOT / paths_raw[key])
    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
