# AI-Powered CV Builder

> **UTS 43007 Advanced Artificial Intelligence** (Spring 2026) · Assessment 1: *Your First GenAI System*

A GenAI system that turns a user's plain-English introduction into a confirmed, reusable profile, retrieves the most relevant jobs with evidence, and generates a tailored, editable CV exported as a polished PDF.

![Architecture diagram](architecture_diagram.png)

## Highlights

- **Agentic intake**: an LLM agent asks follow-up questions to fill gaps before the profile is confirmed
- **Semantic job retrieval (RAG)**: local `sentence-transformers` embeddings (`all-MiniLM-L6-v2`), top-k jobs with evidence
- **Grounded CV generation**: uses only confirmed facts, with section-by-section editing
- **PDF export** with `fpdf2`
- **Google Gemini** via the `google-genai` SDK, with response caching to stay inside free-tier limits
- **Tests**: `pytest` unit tests plus recorded evaluation runs in [`test_results/`](test_results/)

**Tech stack:** Python · Google Gemini · sentence-transformers · NumPy · fpdf2 · PyYAML · pytest

**Technical report:** [`docs/A1_Report.pdf`](docs/A1_Report.pdf)

---

## Setup

```bash
# Verified on Python 3.14. Create the venv with 3.11+.
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml     # then add your key (git-ignored)
export GOOGLE_API_KEY=AIza...           # from aistudio.google.com/apikey (free tier)
```

Embeddings run locally with `sentence-transformers` (`all-MiniLM-L6-v2`,
downloaded on first run) — no key needed.

**Free-tier note:** the Gemini free tier limits requests per day per model. Every
LLM response is cached under `outputs/llm_cache/`, so repeated runs do not
re-spend quota. On `RESOURCE_EXHAUSTED`, switch `llm.model` in `config.yaml`
(e.g. `gemini-flash-latest`) or wait for the daily reset.

## Run

```bash
python -m cv_builder
```

The CLI walks one user through: introduction → agent follow-up questions →
profile confirmation → job retrieval → CV generation → section editing → PDF
export. Run it again to build a second user's profile; profiles never mix.

```bash
python -m pytest            # unit tests
```

## Layout

```
cv_builder/             application package + `python -m cv_builder` entry point
config.example.yaml     configuration template
data/                   supplied job + synthetic profile data
tests/                  unit tests
outputs/                generated CVs, PDFs, embedding cache (created at run time)
```

## Notes / limitations

The synthetic profiles in `data/` are fictional (see `data/README.md`);
synthetic links and organisations must stay marked as such in any output shown
outside the classroom. Known limitations (agent does not ask about work
experience; the nine-job dataset has no security-engineering role) are discussed
in the technical report.
