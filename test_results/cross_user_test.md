# Cross-User Test

**Users:** `student_profile_01` (Maya Chen) and `student_profile_02` (Liam Patel),
run in sequence through the same `cv_builder` code path.

## How separation is enforced

- Each user gets its own `ProfileState` object, keyed by `user_id`
  (`cv_builder/profile.py`); nothing is shared or global.
- A new `ProfileAgent` is constructed per user, so the agent transcript
  (`contents`) and trace never carry over.
- Confirmed profiles are written to separate files:
  `profile_student_profile_01.json`,
  `profile_student_profile_02.json`.
- Unit test `tests/test_data_and_retrieval.py::test_profile_isolation`
  mutates user A's skills and asserts user B is unaffected.

## Observed result

| Field | `student_profile_01` (Maya Chen) | `student_profile_02` (Liam Patel) |
|---|---|---|
| Skills | Python, Java, SQL, REST APIs, Git, GitHub, pytest, Jupyter Notebook | Python, pandas, NumPy, scikit-learn, PyTorch basics, SQL, Hugging Face Transformers basics, Git, Jupyter Notebook |
| Projects | Team Course Planner, AI Coursework Prototype | Coursework Retrieval Assistant, Text Classification Study |
| Retrieved top-3 | `agentic_ai_engineer`, `rag_agent_engineer`, `graduate_ai_engineer` | `graduate_ai_engineer`, `rag_agent_engineer`, `nlp_multimodal_ml_engineer` |
| CV matched skills | `Python` only (backend student vs AI-eng roles) | `Python`, `NumPy`, `pandas`, `scikit-learn`, `PyTorch basics`, `LLMs`, `RAG`, `Git` |

The two CVs contain no overlapping project or experience text, the skill lists are
distinct, and Liam's NLP-oriented profile pulls a different third job
(`nlp_multimodal_ml_engineer`) than Maya's. No field from one user appears in the
other user's profile JSON or CV.
