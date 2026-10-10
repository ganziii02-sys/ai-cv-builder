"""Multi-turn tool-calling agent (Week 3).

After the user accepts the profile summary the model chooses each next Action
(a Gemini function call) from the current state. Tools return Observations
(function responses); the loop stops at `finish` or `max_steps`. Every Action and
Observation is appended to `ProfileAgent.trace` for the report evidence
(03_Evidence/02_Agent/).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from google.genai import types

from .config import Config
from .llm import LLM
from .profile import ProfileState
from .prompts import AGENT_SYSTEM
from .retrieval import JobIndex, RetrievedJob, format_results, profile_query

AskFn = Callable[[str], str]  # given a question, return the user's answer

TOOLS: list[dict[str, Any]] = [
    {
        "name": "update_profile",
        "description": "Record newly confirmed profile fields (merged into state).",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "Subset of ProfileState fields to merge, e.g. "
                    '{"contact_email": "...", "job_goal": "..."}.',
                }
            },
            "required": ["fields"],
        },
    },
    {
        "name": "ask_user",
        "description": "Ask the user ONE follow-up question to fill a specific gap.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "retrieve_jobs",
        "description": "Retrieve the top-k most relevant jobs for the confirmed profile.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "finish",
        "description": "Stop: profile is complete and jobs have been retrieved.",
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


@dataclass
class AgentResult:
    profile: ProfileState
    retrieved: list[RetrievedJob]
    trace: list[dict[str, Any]]
    stopped_reason: str


class ProfileAgent:
    def __init__(self, cfg: Config, llm: LLM, index: JobIndex, ask: AskFn) -> None:
        self.cfg = cfg
        self.llm = llm
        self.index = index
        self.ask = ask
        self.trace: list[dict[str, Any]] = []

    def _log(self, kind: str, **data: Any) -> None:
        self.trace.append({"kind": kind, **data})

    def _run_tool(
        self,
        name: str,
        args: dict[str, Any],
        profile: ProfileState,
        retrieved: list[RetrievedJob],
    ) -> str:
        """Execute one tool, mutate state, return the Observation string."""
        if name == "update_profile":
            profile.merge(args.get("fields", {}))
            return f"profile updated. missing: {profile.missing() or 'none'}"
        if name == "ask_user":
            return f"user answered: {self.ask(args['question'])}"
        if name == "retrieve_jobs":
            k = min(int(args.get("k") or self.cfg.top_k), self.cfg.top_k)
            results = self.index.search(args["query"], k)
            retrieved[:] = results
            return "top jobs:\n" + format_results(results)
        if name == "finish":
            return "done"
        return f"unknown tool {name}"

    def run(self, profile: ProfileState) -> AgentResult:
        system = AGENT_SYSTEM.format(max_steps=self.cfg.max_steps)
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            "Confirmed profile summary the user just accepted:\n"
                            f"{profile.summary_text()}\n\n"
                            f"Missing fields: {profile.missing() or 'none'}\n"
                            f"Suggested retrieval query: "
                            f"{profile_query(profile.to_dict())}\n\n"
                            "Choose the next Action."
                        )
                    )
                ],
            )
        ]
        retrieved: list[RetrievedJob] = []
        stopped = "max_steps"

        for step in range(self.cfg.max_steps):
            resp = self.llm.generate(system, contents, tools=TOOLS)
            cand = resp.candidates[0]
            contents.append(cand.content)
            calls = [p.function_call for p in cand.content.parts if p.function_call]
            if not calls:
                stopped = "no_action"
                break

            responses: list[types.Part] = []
            for fc in calls:
                args = dict(fc.args or {})
                self._log("action", step=step, tool=fc.name, args=args)
                obs = self._run_tool(fc.name, args, profile, retrieved)
                self._log("observation", step=step, tool=fc.name, text=obs)
                responses.append(
                    types.Part.from_function_response(
                        name=fc.name, response={"result": obs}
                    )
                )
                if fc.name == "finish":
                    stopped = "finish"
            contents.append(types.Content(role="user", parts=responses))
            if stopped == "finish":
                break

        return AgentResult(profile, retrieved, self.trace, stopped)

    def dump_trace(self, path) -> None:
        lines = ["# Agent Actions and Observations\n"]
        for e in self.trace:
            if e["kind"] == "action":
                lines.append(
                    f"**Action** (step {e['step']}): `{e['tool']}` "
                    f"{json.dumps(e['args'], ensure_ascii=False)}"
                )
            else:
                lines.append(f"**Observation** (step {e['step']}): {e['text']}\n")
        path.write_text("\n".join(lines), encoding="utf-8")
