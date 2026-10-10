"""Render a CV to a polished PDF with fpdf2.

fpdf2's built-in fonts are latin-1 only, so all model/profile text is passed
through `_s()` which maps common Unicode punctuation to ASCII and drops anything
else. Good enough for an English CV; swap in a Unicode TTF via `add_font` if you
need full Unicode.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from .cv_generator import CV
from .profile import ProfileState

_REPLACE = {
    "•": "-", "–": "-", "—": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ", "−": "-",
    "·": "-", "‐": "-", "‑": "-",
}


def _s(text: str) -> str:
    text = str(text)
    for k, v in _REPLACE.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class _CVPdf(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=7)
        self.set_text_color(150)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _h(pdf: _CVPdf, text: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30)
    pdf.cell(0, 7, _s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1)


def _bullets(pdf: _CVPdf, items: list[str]) -> None:
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(50)
    for it in items:
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(0, 5, _s(f"-  {it}"), new_x="LMARGIN", new_y="NEXT")


def render(cv: CV, profile: ProfileState, job_title: str, out_path: Path) -> Path:
    pdf = _CVPdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20)
    pdf.cell(0, 10, _s(profile.name or "Candidate"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(90)
    contact = [profile.contact_email] + [
        f"{k}: {v}" for k, v in profile.contact_other.items()
    ]
    pdf.multi_cell(
        0, 5, _s("  |  ".join(c for c in contact if c)), new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0, 5, _s(f"Tailored for: {job_title} ({cv.job_document_id})"),
        new_x="LMARGIN", new_y="NEXT",
    )

    _h(pdf, "Summary")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(50)
    pdf.multi_cell(0, 5, _s(cv.summary), new_x="LMARGIN", new_y="NEXT")

    if cv.matched_skills:
        _h(pdf, "Matched skills")
        _bullets(
            pdf,
            [f"{m['skill']} - {m.get('profile_evidence', '')}" for m in cv.matched_skills],
        )

    if cv.missing_requirements:
        _h(pdf, "Requirements not yet evidenced")
        _bullets(pdf, [m["requirement"] for m in cv.missing_requirements])

    for section in cv.sections:
        _h(pdf, section.get("heading", ""))
        _bullets(pdf, section.get("items", []))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path
