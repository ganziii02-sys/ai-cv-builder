# Five-Profile Results

Embedding backend `local:sentence-transformers/all-MiniLM-L6-v2`, `top_k = 3`.
The five confirmed profiles come straight from `data/student_profiles.jsonl`; a
sixth, deliberately incomplete profile is added to exercise the agent's
follow-up questions. Full retrieved lists and excerpts:
`retrieval_results.md`. Confirmed profile states:
`profile_*.json`.

## Predictions (made before running retrieval)

| Profile | Career goal | Predicted relevant job(s) | Reasoning |
|---|---|---|---|
| 01 Maya Chen | Software / backend | `rag_agent_engineer`, `graduate_ai_engineer` | Python, REST APIs, SQL, a tool-call agent coursework prototype |
| 02 Liam Patel | AI / NLP | `nlp_multimodal_ml_engineer`, `rag_agent_engineer` | retrieval assistant + text classifier, PyTorch/Transformers basics |
| 03 Sofia Williams | Data analysis / BI | `graduate_ai_engineer`, `agentic_ai_data_scientist` | data cleaning, dashboards; `graduate_ai_engineer` lists "data analysis" |
| 04 Noah Ibrahim | Cybersecurity / systems | `trust_safety_ml_engineer` (weak) | security interest; no security-engineering role exists in the 9 jobs |
| 05 Ethan Nguyen | Backend / cloud | `agentic_ai_engineer`, `rag_agent_engineer` | backend + tool-call projects, Docker/CI basics, software cadet role |

## Actual vs predicted

| Profile | Actual top-3 | Predicted job in top-3? | Notes |
|---|---|---|---|
| 01 | `agentic_ai_engineer`, `rag_agent_engineer`, `graduate_ai_engineer` | **Yes** (`rag_agent_engineer`, `graduate_ai_engineer`) | agent stopped with `finish`, 0 follow-up questions (profile already complete) |
| 02 | `graduate_ai_engineer`, `rag_agent_engineer`, `nlp_multimodal_ml_engineer` | **Yes** (`nlp_multimodal_ml_engineer`, `rag_agent_engineer`) | `nlp_multimodal_ml_engineer` only entered the top-3 after the retrieval fix (see `failure_and_repair.md`) |
| 03 | `graduate_ai_engineer`, `rag_agent_engineer`, `agentic_ai_data_scientist` | **Yes** (`graduate_ai_engineer`, `agentic_ai_data_scientist`) | data-analysis wording in `graduate_ai_engineer` drives the match |
| 04 | `agentic_ai_engineer`, `agentic_ai_data_scientist`, `rag_agent_engineer` | **No** | dataset limitation: none of the 9 jobs is a security-engineering role; documented as a known failure |
| 05 | `agentic_ai_engineer`, `agentic_ai_data_scientist`, `rag_agent_engineer` | **Yes** (`agentic_ai_engineer`, `rag_agent_engineer`) | strong match on Python + tool-call / backend projects |
| incomplete_user | `agentic_ai_engineer`, `graduate_ai_engineer`, `rag_agent_engineer` | n/a | agent asked 3 follow-up questions (name, email, Python evidence), then retrieved and called `finish`; still missing `experience` |

**Score: 4 / 5 predicted jobs appeared in the top-3.** The one miss (profile 04)
is a gap in the job dataset, not a ranking error.

**General observation.** All six queries cluster on the "agentic / graduate AI
engineer" postings. The nine jobs are all AI/ML-engineering roles for a 43007 AI
cohort and share heavy tooling vocabulary (Python, Git, RAG, agents), so
retrieval separates them mainly by the stated career goal — which is why the
goal is weighted twice in `profile_query()`.
