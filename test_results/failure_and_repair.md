# Failure and Repair

## Failure observed

**Retrieval ignored the stated career goal.** In the first end-to-end run,
`student_profile_02` (an NLP-focused student whose introduction says "interested
in NLP and LLM applications" and whose confirmed `job_goal` is
"AI Intern, NLP Intern, Junior Machine Learning Engineer") retrieved:

| Rank | document_id | score |
|---|---|---|
| 1 | `graduate_ai_engineer` | 0.656 |
| 2 | `rag_agent_engineer` | 0.605 |
| 3 | `agentic_ai_engineer` | 0.555 |

The obvious match, `nlp_multimodal_ml_engineer`, was **not** in the top three.

**Likely cause.** The nine job records are all AI/ML-engineering roles and share a
long tail of tooling keywords (Python, Git, SQL, Docker, RAG, agents). The query
built by `profile_query()` listed the job goal once, then eight skills, then
project titles and the summary, so the shared tooling vocabulary dominated the
embedding and the role name / intent was drowned out. Job embeddings used the
description with the title only once, so title terms ("NLP & Multimodal") carried
little weight.

## Change

`cv_builder/retrieval.py` — `profile_query()`: repeat the job goal / target roles
twice at the front of the query and cut the skill list from 10 to 8 items.

`cv_builder/data_loader.py` — `job_text()`: prepend the title twice
(`"{title}. {title}. {description}"`) so the role name is weighted in the job
embedding.

```python
# profile_query (after)
parts = [goal, goal] if goal else []
parts += profile.get("technical_skills", [])[:8]
...

# job_text (after)
return f"{title}. {title}. {description}".strip()
```

**Expected improvement:** the profile's stated intent should outweigh shared
tooling terms, moving role-specific jobs up the ranking.

## Retest (actual)

Re-running retrieval for `student_profile_02` (embedding backend
`local:sentence-transformers/all-MiniLM-L6-v2`, `top_k = 3`):

| Rank | document_id | score |
|---|---|---|
| 1 | `graduate_ai_engineer` | 0.648 |
| 2 | `rag_agent_engineer` | 0.607 |
| 3 | **`nlp_multimodal_ml_engineer`** | 0.569 |

`nlp_multimodal_ml_engineer` now appears in the top three, as predicted.

## Repeat of an earlier test

`student_profile_01` (software / agent coursework) was re-run end to end after the
change: the agent still stopped with `finish`, the confirmed profile JSON
(`profile_student_profile_01.json`) was unchanged, and two tailored CVs
were produced with no dropped claims — so the retrieval change did not regress the
rest of the pipeline.

## Remaining limitation

`student_profile_04` (cybersecurity goal) still does not retrieve a security-
oriented role, because none of the nine jobs is a security-engineering position;
`trust_safety_ml_engineer` is an ML role for trust & safety, not a match for a
student with networking / Wireshark experience. This is a dataset limitation, not
a ranking bug, and is reported as-is in `five_profile_results.md`.
