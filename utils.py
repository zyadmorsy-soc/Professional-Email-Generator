from __future__ import annotations

import html
import re
from urllib.parse import quote

from fpdf import FPDF

CV_ATTACHMENT_FILENAME = "TBNZ_CV.pdf"
COVER_LETTER_ATTACHMENT_FILENAME = "TBNZ_Cover_Letter.pdf"


def parse_email_content(email_text: str) -> tuple[str, str]:
    cleaned = email_text.strip()
    lines = [line.rstrip() for line in cleaned.splitlines()]
    subject = "Job Application"
    body_lines = lines

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip() or subject
        body_lines = lines[1:]

    body = "\n".join(body_lines).strip()
    return subject, body


def format_email_markdown(email_text: str) -> str:
    subject, body = parse_email_content(email_text)
    return f"### Subject\n**{subject}**\n\n### Email Draft\n{body.replace(chr(13), '').strip()}"


CV_SECTION_HEADINGS = {
    "PROFESSIONAL SUMMARY",
    "TECHNICAL SKILLS",
    "EDUCATION",
    "EXPERIENCE / PROJECTS",
    "EXPERIENCE/PROJECTS",
    "EXPERIENCE AND PROJECTS",
    "PROJECTS / EXPERIENCE",
    "PROJECTS/EXPERIENCE",
    "CERTIFICATIONS / COURSES",
    "CERTIFICATIONS/COURSES",
    "TOOLS / TECHNOLOGIES",
    "TOOLS/TECHNOLOGIES",
    "LANGUAGES",
}


def format_cv_markdown(document_text: str) -> str:
    blocks: list[str] = []
    lines = [line.rstrip() for line in document_text.replace("\r", "").splitlines()]

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        normalized = normalize_heading(stripped)
        if index == 0:
            blocks.append(f"# {escape_markdown_text(stripped)}")
            continue
        if index == 1:
            blocks.append(escape_markdown_text(stripped))
            continue
        if index == 2 and not is_section_heading(stripped):
            blocks.append(f"**{escape_markdown_text(stripped)}**")
            continue
        if is_section_heading(stripped):
            blocks.append(f"## {escape_markdown_text(normalized)}")
            continue
        if is_bullet_line(stripped):
            blocks.append(f"- {escape_markdown_text(strip_bullet_prefix(stripped))}")
            continue

        blocks.append(escape_markdown_text(stripped))

    return "\n\n".join(blocks).strip()


def document_to_txt_bytes(document_text: str) -> bytes:
    return document_text.strip().encode("utf-8")


def document_to_pdf_bytes(title: str, document_text: str) -> bytes:
    pdf = FPDF()
    pdf.set_margins(left=16, top=18, right=16)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    if looks_like_cv_document(document_text):
        render_cv_pdf(pdf, document_text)
    else:
        render_generic_pdf(pdf, title, document_text)

    output = pdf.output(dest="S")
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    return str(output).encode("latin-1", "replace")


def sanitize_pdf_text(value: str) -> str:
    normalized = (
        value.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2026", "...")
        .replace("\u00a0", " ")
    )
    return normalized.encode("latin-1", "replace").decode("latin-1")


def render_generic_pdf(pdf: FPDF, title: str, document_text: str) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(0, 8, sanitize_pdf_text(title))
    pdf.ln(3)
    pdf.set_font("Helvetica", size=11)
    line_height = 7
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin

    lines = document_text.splitlines() or [""]
    for raw_line in lines:
        safe_line = sanitize_pdf_text(raw_line.rstrip("\r"))
        text_to_render = safe_line if safe_line.strip() else " "

        for segment in split_for_pdf_width(pdf, text_to_render, usable_width):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_width, line_height, text=segment if segment else " ")


def render_cv_pdf(pdf: FPDF, document_text: str) -> None:
    lines = [sanitize_pdf_text(line.rstrip("\r")) for line in document_text.splitlines()]
    lines = trim_empty_edges(lines)
    if not lines:
        return

    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    line_height = 6.5
    section_gap = 4

    name_line = lines[0].strip()
    contact_line = lines[1].strip() if len(lines) > 1 else ""
    role_line = lines[2].strip() if len(lines) > 2 and not is_section_heading(lines[2]) else ""
    start_index = 3 if role_line else 2 if contact_line else 1

    if name_line:
        pdf.set_font("Helvetica", "B", 18)
        pdf.multi_cell(usable_width, 9, name_line, align="L")
        pdf.ln(1)

    if contact_line:
        pdf.set_font("Helvetica", size=10.5)
        pdf.set_text_color(60, 72, 88)
        pdf.multi_cell(usable_width, 5.5, contact_line, align="L")

    if role_line:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(usable_width, 6.5, role_line, align="L")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    for raw_line in lines[start_index:]:
        stripped = raw_line.strip()
        if not stripped:
            pdf.ln(2)
            continue

        if is_section_heading(stripped):
            pdf.ln(1.5)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(usable_width, 7, normalize_heading(stripped))
            pdf.ln(1.5)
            continue

        if is_bullet_line(stripped):
            bullet_text = strip_bullet_prefix(stripped)
            pdf.set_font("Helvetica", size=11)
            pdf.set_x(pdf.l_margin)
            pdf.cell(4, line_height, "-")
            pdf.multi_cell(usable_width - 4, line_height, bullet_text)
            pdf.ln(0.8)
            continue

        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(usable_width, line_height, stripped)
        pdf.ln(0.8)

    pdf.ln(section_gap)


def looks_like_cv_document(document_text: str) -> bool:
    lines = [line.strip() for line in document_text.replace("\r", "").splitlines() if line.strip()]
    if len(lines) < 4:
        return False

    hits = sum(1 for line in lines if is_section_heading(line))
    return hits >= 3


def is_section_heading(value: str) -> bool:
    normalized = normalize_heading(value)
    return normalized in CV_SECTION_HEADINGS


def normalize_heading(value: str) -> str:
    cleaned = re.sub(r"[:\s]+$", "", value.strip())
    return re.sub(r"\s+", " ", cleaned).upper()


def is_bullet_line(value: str) -> bool:
    return bool(re.match(r"^([-*•]|[0-9]+\.)\s+", value.strip()))


def strip_bullet_prefix(value: str) -> str:
    return re.sub(r"^([-*•]|[0-9]+\.)\s+", "", value.strip(), count=1)


def trim_empty_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def escape_markdown_text(value: str) -> str:
    return value.replace("\\", "\\\\")


def split_for_pdf_width(pdf: FPDF, value: str, usable_width: float) -> list[str]:
    if not value:
        return [" "]

    segments: list[str] = []
    remaining = value
    while remaining:
        if pdf.get_string_width(remaining) <= usable_width:
            segments.append(remaining)
            break

        split_index = len(remaining)
        while split_index > 1 and pdf.get_string_width(remaining[:split_index]) > usable_width:
            split_index -= 1

        if split_index <= 1:
            split_index = 1

        last_space = remaining.rfind(" ", 0, split_index)
        if last_space > 0:
            split_index = last_space + 1

        segment = remaining[:split_index].rstrip()
        if not segment:
            segment = remaining[:1]
            split_index = 1

        segments.append(segment)
        remaining = remaining[split_index:].lstrip()

    return segments or [" "]


def build_gmail_compose_url(recipient: str, subject: str, body: str) -> str:
    encoded_to = quote(recipient or "", safe="")
    encoded_subject = quote(subject or "Job Application", safe="")
    encoded_body = quote(body or "", safe="")
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={encoded_to}&su={encoded_subject}&body={encoded_body}"
    )


def clear_app_state(session_state) -> None:
    defaults = {
        "english_level": "C1",
        "preferred_tone": "Formal",
        "content_basis": "Job ad + background + skills",
        "email_length": "Medium",
        "generated_documents": {},
        "generation_errors": {},
    }
    for key in [
        "full_name",
        "email_address",
        "phone_number",
        "linkedin_url",
        "recruiter_email",
        "hiring_manager_name",
        "company_name",
        "job_title",
        "background",
        "key_skills",
        "job_description",
        "education",
        "projects_experience",
        "certifications",
        "tools_technologies",
        "english_level",
        "preferred_tone",
        "content_basis",
        "email_length",
        "generated_email",
        "generated_cv",
        "generated_cover_letter",
        "parsed_email_subject",
        "parsed_email_body",
        "generated_documents",
        "generation_errors",
        "gmail_draft_id",
        "google_oauth_state",
        "google_auth_url",
        "gmail_auth_feedback",
    ]:
        if key in {"generated_documents", "generation_errors"}:
            session_state[key] = {}
        else:
            session_state[key] = defaults.get(key, "")


def build_copy_button_html(button_label: str, document_text: str, element_key: str) -> str:
    escaped_text = html.escape(document_text)
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "-", element_key)
    target_id = f"copy-target-{safe_key}"
    status_id = f"copy-status-{safe_key}"
    return f"""
    <div style="display:flex;align-items:center;height:48px;">
        <button
            onclick="navigator.clipboard.writeText(document.getElementById('{target_id}').innerText).then(() => {{
                document.getElementById('{status_id}').innerText = '{html.escape(button_label)} copied to clipboard.';
            }});"
            style="
                width:100%;
                min-height:44px;
                border:none;
                border-radius:12px;
                font-weight:600;
                color:#f8fafc;
                background:linear-gradient(135deg, #0ea5e9, #0369a1);
                cursor:pointer;
            "
        >
            Copy {html.escape(button_label)}
        </button>
        <div id="{target_id}" style="display:none;white-space:pre-wrap;">{escaped_text}</div>
        <div id="{status_id}" style="margin-left:12px;color:#cbd5e1;font-size:13px;"></div>
    </div>
    """
