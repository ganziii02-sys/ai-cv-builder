# Prompt Record

Each row is one development goal given to the coding agent (Claude Code):
the goal, the prompt used, the change it produced, the decision, how it was
verified, and the outcome. The section after the table records the one required
prompt improvement (`CV_SYSTEM_V1` → `V2`) with before/after model output.

| # | Goal | Exact prompt (to coding agent) | Proposed change | Decision | Verification method | Outcome |
|---|------|--------------------------------|-----------------|----------|---------------------|---------|
| 1 | Scaffold project structure + plan | "Scaffold + plan" | Create the `cv_builder/` package with a config-switchable embedding backend and a build plan | Accepted | import smoke test of deterministic modules | Modules import; retrieval ranks 9 jobs with a fake backend |
| 2 | Switch LLM to a free provider | "구글에서 get an api ... anthropic 말고 다르게" | Replace Anthropic SDK with `google-genai`; rewrite `llm.py` + `agent.py` for Gemini function calling | Accepted (no course key; Gemini has a free tier) | live end-to-end call | works; later moved from `gemini-flash-latest` to `gemini-flash-lite-latest` for a separate quota bucket |
| 3 | Fix slow / hanging model calls | (dev) | Add 90s HTTP timeout + retry on 503/429; `thinking_budget=0` | Accepted | timed calls | 54s/call → 4s/call |
| 4 | Survive the 20-req/day free quota | (dev) | Cache every LLM response to disk (`outputs/llm_cache/`); use synthetic data for the 5 confirmed profiles; only agent-demo + 4 CVs call the API | Accepted |  a batch test run | ~12 calls; re-runs free |
| 5 | Gemini 3 `thought_signature` 400 | (dev) | Preserve `thought_signature` bytes (base64) through the cache round-trip; return the original response object on the fresh path | Accepted | agent multi-turn run | follow-up turns work |
| 6 | PDF `FPDFUnicodeEncodingException` on `•` | (dev) | `_s()` maps Unicode punctuation → ASCII before every fpdf write | Accepted | PDF export | 4 CV PDFs render, text extracts cleanly |
| 7 | Agent sends list fields in wrong shape (`AttributeError: 'str'/'dict'`) | (dev) | `profile._normalise_field()` coerces every model-proposed field to the declared shape; unit test `test_merge_normalises_messy_model_output` | Accepted | `pytest` + a full batch run | 5/5 tests pass; run completes end-to-end |
| 8 | Retrieval ignores career goal (see failure_and_repair.md) | (dev) | weight job goal ×2 in query, weight job title ×2 in embedding | Accepted | re-run retrieval for all 6 profiles | `nlp_multimodal_ml_engineer` enters profile_02 top-3 |

## Required: one prompt improvement with before/after

**Prompt goal:** CV generation must use only confirmed profile facts and separate
matched skills from missing requirements.

Test input: `student_profile_01` (Maya Chen) + job `rag_agent_engineer`.

**Before (`prompts.CV_SYSTEM_V1`):**

```
You write tailored CVs. Given a candidate profile and a target job, produce a
CV in JSON with a summary, skills, experience, projects, and a list of missing
requirements. Make the candidate look as strong as possible for the job.
```

Observed V1 output (excerpt):

```json
"summary": "... a strong foundation in Python programming, REST APIs, and
database integration. Experienced in building AI-agent prototypes ...",
"skills": ["Python","Java","SQL","REST APIs","AI Agents & Tool Calling",
           "Prompt Design","Git & GitHub","pytest","Jupyter Notebook",
           "JSON Data Handling"]
```

Problems: (1) `skills` invents `"AI Agents & Tool Calling"`, `"Prompt Design"`,
`"JSON Data Handling"` — none are in the profile's `technical_skills`.
(2) The experience description is rewritten ("Collaborated within a fast-paced
team environment to ... resolve operational challenges") from the profile's plain
"Handled customer questions ... followed written procedures". (3) There is no
matched-vs-missing split: the marker cannot see which claims are job-relevant or
evidence-backed.

**After (`prompts.CV_SYSTEM_V2`):**

```
Role: you assemble a tailored CV. You do not evaluate or embellish the candidate.
Allowed evidence: ONLY the confirmed profile for candidate claims; ONLY the job
description for requirement/match reasons. ... `profile_evidence` must quote or
paraphrase a specific profile item ...
Output JSON: {summary, matched_skills:[{skill,profile_evidence,job_line}],
missing_requirements:[{requirement,job_line}], sections:[{heading,items}]}
```

Observed V2 output (excerpt):

```json
"summary": "Maya Chen is a third-year Bachelor of Computing Science student ...
with experience in Python programming and AI coursework projects.",
"matched_skills": [{"skill": "Python",
  "profile_evidence": "Team Course Planner and AI Coursework Prototype",
  "job_line": "strong Python programming."}],
"missing_requirements": [
  {"requirement": "A master's degree or above ...", "job_line": "A master's degree or above ..."},
  {"requirement": "Three or more years of research or engineering experience", "job_line": "three or more years ..."}]
```

V2 makes only one skill claim (`Python`), links it to a named project and a job
line, and lists what the profile lacks separately. A second, code-level
fact-check (`cv_generator._supported`, token-overlap ≥ 0.5 against the profile
corpus) then drops any `matched_skills` entry whose `profile_evidence` is not
traceable; for all four sample CVs `dropped_claims` was `[]`.

**How the test shaped the next prompt:** seeing V1 invent skills and rewrite the
experience line led directly to the "Allowed evidence" clause and the required
`profile_evidence` field in V2, and to adding the deterministic `_supported`
check as a safety net that does not depend on the model obeying the prompt.
