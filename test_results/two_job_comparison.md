# Two Jobs, Same Confirmed Profile

**Profile:** `student_profile_01` (Maya Chen) — confirmed from
`profile_student_profile_01.json`, byte-identical across both runs.
**Jobs:** `agentic_ai_engineer` vs `rag_agent_engineer`.
Sources: `cv_student_profile_01_agentic_ai_engineer.json` /
`cv_student_profile_01_rag_agent_engineer.json` and the matching PDFs.

| Aspect | CV for `agentic_ai_engineer` | CV for `rag_agent_engineer` |
|---|---|---|
| Summary | "...experience in Python development, **REST APIs**, and building AI prototypes... a **web API** using Python, SQL, and Git." | "...experience in **Python programming and AI coursework projects**... prototypes including a **tool-call agent prototype** and a Team Course Planner web API." |
| Section order | Education → Technical Skills → Projects → Experience → Achievements | Education → Technical Skills → Projects → Experience → Achievements (same) |
| Matched skills | `Python` | `Python` |
| Missing requirements | Two or more years of Python development · Langflow · LLM orchestration / RAG / AI-agent experience · Modern AI tooling · Cloud infrastructure · Terraform or Kubernetes · Docker · Stakeholder engagement | A master's degree or above · Three or more years of research/engineering experience · Experience with LLMs, RAG, AI agents · LangChain, LangGraph, LlamaIndex, vector/graph databases, cloud AI platforms |
| Emphasis | Backend / API framing — the summary foregrounds REST APIs and the web service. | Research / agent framing — the summary foregrounds the tool-call agent prototype and coursework. |

**Reading.** The confirmed profile is unchanged; only the job-specific content
moves. Both jobs match just `Python` because Maya's coursework profile does not
meet the AI-engineering requirements of either role — the `missing_requirements`
lists are drawn entirely from each job description and differ accordingly
(deployment tooling for `agentic_ai_engineer`; postgraduate study and LLM
frameworks for `rag_agent_engineer`). The fact-check pass dropped no claims
(`dropped_claims: []`) in either CV.
