"""End-to-end interactive workflow. No source edits needed to run a full
user -> PDF pass. Run again for another user; profiles never share state.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .agent import ProfileAgent
from .config import load_config
from .cv_generator import generate_cv
from .data_loader import load_introductions
from .intake import bootstrap_profile
from .llm import LLM
from .pdf_export import render
from .retrieval import JobIndex


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def run_user(cfg, llm: LLM, index: JobIndex, *, user_id: str, intro: str,
             non_interactive: bool = False) -> None:
    print(f"\n=== User: {user_id} ===")
    profile = bootstrap_profile(llm, user_id, intro)

    print("\nInitial profile from your introduction:")
    print(profile.summary_text())
    if not non_interactive:
        input("\nPress Enter to accept this summary and start follow-up... ")

    ask = (lambda q: "(skipped)") if non_interactive else (lambda q: input(f"\nAgent asks: {q}\n> "))
    agent = ProfileAgent(cfg, llm, index, ask)
    result = agent.run(profile)

    agent.dump_trace(cfg.outputs_dir / f"agent_trace_{user_id}.md")
    print(f"\nAgent stopped: {result.stopped_reason}")
    print(f"Missing after follow-up: {profile.missing() or 'none'}")

    retrieved = result.retrieved or index.search(
        profile.job_goal or intro, cfg.top_k
    )
    print("\nTop retrieved jobs:")
    for r in retrieved:
        print(f"  [{r.document_id}] {r.title}  (score {r.score:.3f})")
        print(f"      excerpt: {r.excerpt}")

    targets = [retrieved[0].record] if non_interactive else _choose_jobs(retrieved)
    for job in targets:
        cv = generate_cv(llm, profile, job)
        if cv.dropped_claims:
            print(f"\n[fact-check] dropped unsupported claims: {cv.dropped_claims}")
        if not non_interactive:
            _edit_loop(cv)
        out = cfg.outputs_dir / f"CV_{user_id}_{job['document_id']}.pdf"
        render(cv, profile, job.get("title", ""), out)
        print(f"  wrote {out}")

    (cfg.outputs_dir / f"profile_{user_id}.json").write_text(
        json.dumps(profile.to_dict(), indent=2), encoding="utf-8"
    )


def _choose_jobs(retrieved) -> list:
    print("\nSelect job number(s) to build a CV for (comma-separated), e.g. 1,2:")
    raw = input("> ").strip() or "1"
    picks = [int(x) - 1 for x in raw.split(",") if x.strip().isdigit()]
    return [retrieved[i].record for i in picks if 0 <= i < len(retrieved)]


def _edit_loop(cv) -> None:
    while True:
        print("\nCurrent sections:")
        for i, s in enumerate(cv.sections, 1):
            print(f"  {i}. {s['heading']} ({len(s['items'])} items)")
        choice = input("Edit section number, or Enter to finish: ").strip()
        if not choice:
            return
        if choice.isdigit() and 1 <= int(choice) <= len(cv.sections):
            s = cv.sections[int(choice) - 1]
            print("Enter new items, one per line, blank line to end:")
            items = []
            while (line := input()):
                items.append(line)
            s["items"] = items


def main() -> None:
    cfg = load_config()
    llm = LLM(cfg.llm)
    index = JobIndex(cfg)

    intros = load_introductions(cfg.introductions_path)
    print("Available synthetic introductions:", ", ".join(intros))
    print("Enter a document_id to reuse one, or type your own introduction.")
    raw = input("> ").strip()
    if raw in intros:
        user_id = raw
        intro = intros[raw]["initial_introduction"]
    else:
        user_id = _slug(raw.split()[0] if raw else "user") or "user"
        intro = raw

    run_user(cfg, llm, index, user_id=user_id, intro=intro)


if __name__ == "__main__":
    main()
