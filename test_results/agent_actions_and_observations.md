# Agent Actions and Observations

Trace produced by `ProfileAgent.run()` / `dump_trace()` in `cv_builder/agent.py`
(LLM: Google Gemini `gemini-flash-lite-latest`).

## Tools (Gemini function declarations)

| Tool | Arguments | Effect / Observation |
|---|---|---|
| `update_profile` | `fields` (object) | `ProfileState.merge()` normalises and merges the confirmed fields; Observation = the new `missing` list |
| `ask_user` | `question` (string) | asks the user one follow-up question; Observation = the user's answer |
| `retrieve_jobs` | `query` (string), `k` (int, clamped to `top_k = 3`) | `JobIndex.search()`; Observation = the top-k `document_id`, score and a supporting excerpt |
| `finish` | `reason` (string) | stops the loop |

## Full trace — complete profile (`student_profile_01`, Maya Chen)

A confirmed profile with `missing = none`. The agent asks no questions.

```
Action (step 0): retrieve_jobs {"k": 5, "query": "Software Engineering Intern,
  Graduate Software Developer, Junior Backend Developer | Python | Java | SQL |
  REST APIs | Git | GitHub | pytest | Jupyter Notebook"}
Observation (step 0): top jobs:
  - agentic_ai_engineer   (score 0.521) — AI Engineer
  - rag_agent_engineer    (score 0.520) — AI Engineer
  - graduate_ai_engineer  (score 0.505) — Graduate AI Engineer
  (each with a requirements excerpt from data/jobs.jsonl)

Action (step 1): finish {"reason": "Profile complete and relevant jobs
  successfully retrieved."}
Observation (step 1): done
```

`k` was passed as 5 but is clamped to `top_k = 3` in
`ProfileAgent._run_tool()`, so exactly three jobs are returned.

## One Action → Python → Observation → state update (incomplete profile, step 5)

```
Action (step 5): update_profile {"fields": {
    "technical_skills": [{"skill": "Python", "evidence": "Used in library-catalogue project ..."}],
    "projects": [{"title": "Library Catalogue", "description": "..."},
                 {"title": "Data Structures Assignments", "description": "..."}]}}
```

Python: `ProfileAgent._run_tool("update_profile", args, ...)` →
`profile.merge(args["fields"])`. `_normalise_field()` coerces the malformed
`technical_skills` item to the string `"Python"` and keeps the two project dicts.

```
Observation (step 5): profile updated. missing: ['experience', 'skill_evidence for: Python']
```

State update: `profile.projects` gains two entries, `profile.technical_skills`
gains `"Python"`. The Observation is appended to the Gemini `contents` as a
`function_response` part and the loop continues.

## Stopping condition

The loop stops when the model calls `finish`, or when `step` reaches
`max_steps = 8` (`cv_builder/config.py`). Both recorded runs stopped with
`finish`.
