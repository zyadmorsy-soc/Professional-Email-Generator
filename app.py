from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from gemini_client import (
    GeminiClientError,
    generate_cover_letter,
    generate_cv,
    generate_email,
)
from gmail_client import (
    GmailClientError,
    create_gmail_draft_with_attachments,
    get_gmail_auth_status,
    get_google_auth_url,
    handle_google_oauth_callback,
)
from utils import (
    COVER_LETTER_ATTACHMENT_FILENAME,
    CV_ATTACHMENT_FILENAME,
    build_copy_button_html,
    build_gmail_compose_url,
    clear_app_state,
    document_to_pdf_bytes,
    document_to_txt_bytes,
    format_cv_markdown,
    format_email_markdown,
    parse_email_content,
)
from validators import validate_form_data


load_dotenv()

DOCUMENT_CONFIG = {
    "email": {
        "title": "Professional Email",
        "state_key": "generated_email",
        "button_label": "Email",
        "generator": generate_email,
        "txt_name": "job_application_email.txt",
        "pdf_name": "job_application_email.pdf",
        "pdf_title": "Professional Job Application Email",
    },
    "cv": {
        "title": "ATS-Friendly CV / Resume",
        "state_key": "generated_cv",
        "button_label": "CV",
        "generator": generate_cv,
        "txt_name": "job_application_cv.txt",
        "pdf_name": CV_ATTACHMENT_FILENAME,
        "pdf_title": "ATS-Friendly CV / Resume",
    },
    "cover_letter": {
        "title": "Professional Cover Letter",
        "state_key": "generated_cover_letter",
        "button_label": "Cover Letter",
        "generator": generate_cover_letter,
        "txt_name": "job_application_cover_letter.txt",
        "pdf_name": COVER_LETTER_ATTACHMENT_FILENAME,
        "pdf_title": "Professional Cover Letter",
    },
}


st.set_page_config(
    page_title="TBNZ AI Job Application Suite",
    page_icon="📧",
    layout="wide",
)


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg-main: #0b1220;
                --bg-panel: #121a2a;
                --bg-panel-soft: #182235;
                --border: rgba(148, 163, 184, 0.18);
                --text-main: #f8fafc;
                --text-soft: #cbd5e1;
                --accent: #38bdf8;
                --accent-soft: rgba(56, 189, 248, 0.14);
                --warning-soft: rgba(251, 191, 36, 0.12);
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(14, 165, 233, 0.16), transparent 34%),
                    radial-gradient(circle at top right, rgba(56, 189, 248, 0.10), transparent 25%),
                    linear-gradient(180deg, #08111f 0%, var(--bg-main) 100%);
                color: var(--text-main);
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a 0%, #111c31 100%);
                border-right: 1px solid var(--border);
            }

            div[data-testid="stForm"] {
                background: rgba(15, 23, 42, 0.78);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 1.25rem 1.25rem 0.5rem 1.25rem;
                box-shadow: 0 20px 45px rgba(2, 6, 23, 0.28);
            }

            h1, h2, h3 {
                color: var(--text-main);
                letter-spacing: -0.02em;
            }

            .hero-card {
                background: linear-gradient(135deg, rgba(14, 165, 233, 0.14), rgba(15, 23, 42, 0.92));
                border: 1px solid var(--border);
                border-radius: 22px;
                padding: 1.6rem 1.4rem;
                margin-bottom: 1.2rem;
            }

            .section-card, .output-card, .note-card {
                background: rgba(15, 23, 42, 0.78);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 1.2rem;
                margin-top: 1rem;
            }

            .note-card {
                background: linear-gradient(135deg, var(--warning-soft), rgba(15, 23, 42, 0.92));
            }

            .section-label {
                color: var(--accent);
                font-size: 0.82rem;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .helper-note {
                color: var(--text-soft);
                font-size: 0.93rem;
            }

            .status-chip {
                display: inline-block;
                padding: 0.3rem 0.65rem;
                border-radius: 999px;
                background: rgba(34, 197, 94, 0.12);
                color: #bbf7d0;
                border: 1px solid rgba(34, 197, 94, 0.25);
                font-size: 0.82rem;
                margin-top: 0.4rem;
            }

            .stDownloadButton button, .stButton button, .stLinkButton a {
                border-radius: 12px;
                min-height: 2.8rem;
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "full_name": "",
        "email_address": "",
        "phone_number": "",
        "linkedin_url": "",
        "recruiter_email": "",
        "hiring_manager_name": "",
        "company_name": "",
        "job_title": "",
        "background": "",
        "key_skills": "",
        "job_description": "",
        "education": "",
        "projects_experience": "",
        "certifications": "",
        "tools_technologies": "",
        "english_level": "C1",
        "preferred_tone": "Formal",
        "content_basis": "Job ad + background + skills",
        "email_length": "Medium",
        "generated_email": "",
        "generated_cv": "",
        "generated_cover_letter": "",
        "parsed_email_subject": "",
        "parsed_email_body": "",
        "generated_documents": {},
        "generation_errors": {},
        "gmail_draft_id": "",
        "google_oauth_state": "",
        "google_auth_url": "",
        "gmail_auth_status": "Not connected",
        "gmail_auth_detail": "Sign in with Google to enable Gmail draft creation with attachments.",
        "gmail_auth_feedback": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def collect_form_data() -> dict[str, str]:
    return {
        "full_name": st.session_state.full_name,
        "email_address": st.session_state.email_address,
        "phone_number": st.session_state.phone_number,
        "linkedin_url": st.session_state.linkedin_url,
        "recruiter_email": st.session_state.recruiter_email,
        "hiring_manager_name": st.session_state.hiring_manager_name,
        "company_name": st.session_state.company_name,
        "job_title": st.session_state.job_title,
        "background": st.session_state.background,
        "key_skills": st.session_state.key_skills,
        "job_description": st.session_state.job_description,
        "education": st.session_state.education,
        "projects_experience": st.session_state.projects_experience,
        "certifications": st.session_state.certifications,
        "tools_technologies": st.session_state.tools_technologies,
        "english_level": st.session_state.english_level,
        "preferred_tone": st.session_state.preferred_tone,
        "content_basis": st.session_state.content_basis,
        "email_length": st.session_state.email_length,
    }


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## Suite Overview")
        st.write(
            "Generate a professional application email, an ATS-friendly CV, and a tailored cover letter "
            "from one shared input form."
        )
        st.markdown("## Generation Tips")
        st.write(
            "- Paste the full job advertisement for stronger keyword alignment.\n"
            "- Keep your background factual and concrete.\n"
            "- Use optional education, project, certification, and tool fields when they improve credibility."
        )
        st.markdown("## Gmail Draft Note")
        st.write(
            "Open Gmail Draft uses Gmail Web with prefilled recipient, subject, and body. "
            "Create Gmail Draft with Attachments uses Gmail API OAuth to create a real Gmail draft "
            "with the CV and cover letter PDFs attached."
        )
        st.markdown("## Gmail Status")
        st.write(f"**{st.session_state.gmail_auth_status}**")
        st.caption(st.session_state.gmail_auth_detail)
        st.markdown("## Privacy")
        st.write(
            "Your input stays within the app flow for prompt building, generation, and document export."
        )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="section-label">AI Job Application Toolkit</div>
            <h1 style="margin-bottom:0.35rem;">TBNZ Professional Email Generator</h1>
            <p style="margin:0;font-size:1.02rem;">
                Multi-document job application suite for email, ATS-friendly CV, and tailored cover letter generation
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_form() -> bool:
    with st.form("job_application_suite_form", clear_on_submit=False):
        st.markdown('<div class="section-label">Applicant Details</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name", key="full_name", placeholder="e.g. Sarah Ahmed")
            st.text_input("Email Address", key="email_address", placeholder="e.g. sarah.ahmed@email.com")
            st.text_input("Phone Number", key="phone_number", placeholder="e.g. +20 101 234 5678")
            st.text_input(
                "LinkedIn Profile URL",
                key="linkedin_url",
                placeholder="https://www.linkedin.com/in/your-profile",
            )
        with col2:
            st.text_input("Recruiter Email Address", key="recruiter_email", placeholder="recruiter@company.com")
            st.text_input("Hiring Manager Name", key="hiring_manager_name", placeholder="e.g. Mr. Kareem Hassan")
            st.text_input("Company Name", key="company_name", placeholder="e.g. Horizon Analytics")
            st.text_input("Job Title Applying For", key="job_title", placeholder="e.g. Senior Data Analyst")

        st.markdown('<div class="section-label">Professional Context</div>', unsafe_allow_html=True)
        st.text_area(
            "Current Role / Academic Background",
            key="background",
            height=120,
            placeholder="Summarize your current role, education, and relevant experience.",
            help="Add enough detail for realistic, role-targeted outputs.",
        )
        st.text_area(
            "Key Skills",
            key="key_skills",
            height=120,
            placeholder="List technical skills, domain expertise, achievements, and tools.",
            help="Concrete, role-relevant skills produce better results.",
        )
        st.text_area(
            "Job Advertisement / Job Description",
            key="job_description",
            height=180,
            placeholder="Paste the job ad or description here.",
            help="This drives role relevance across all three generated documents.",
        )

        with st.expander("Optional CV / Cover Letter Inputs"):
            extra_col1, extra_col2 = st.columns(2)
            with extra_col1:
                st.text_area(
                    "Education",
                    key="education",
                    height=110,
                    placeholder="Degree, university, graduation year, notable coursework, or academic achievements.",
                )
                st.text_area(
                    "Projects / Experience",
                    key="projects_experience",
                    height=150,
                    placeholder="Relevant projects, internships, freelance work, or practical experience.",
                )
            with extra_col2:
                st.text_area(
                    "Certifications / Courses",
                    key="certifications",
                    height=110,
                    placeholder="Relevant certifications, trainings, or online courses.",
                )
                st.text_area(
                    "Tools / Technologies",
                    key="tools_technologies",
                    height=150,
                    placeholder="Platforms, languages, frameworks, analytics tools, or software proficiencies.",
                )

        st.markdown('<div class="section-label">Writing Preferences</div>', unsafe_allow_html=True)
        pref_col1, pref_col2, pref_col3 = st.columns(3)
        with pref_col1:
            st.selectbox(
                "English Level",
                ["A1", "A2", "B1", "B2", "C1", "C2", "Business English"],
                key="english_level",
            )
        with pref_col2:
            st.selectbox(
                "Preferred Tone",
                ["Formal", "Very Formal", "Friendly but Professional", "Confident", "Polite"],
                key="preferred_tone",
            )
        with pref_col3:
            st.selectbox("Content Basis", ["Job ad only", "Job ad + background + skills"], key="content_basis")
        st.radio("Email Length", ["Short", "Medium", "Detailed"], key="email_length", horizontal=True)
        st.caption(
            "Required fields power all outputs. Optional fields improve CV and cover letter quality without being mandatory."
        )
        return st.form_submit_button("Generate Email, CV, and Cover Letter", use_container_width=True, type="primary")


def handle_generation() -> None:
    form_data = collect_form_data()
    errors = validate_form_data(form_data)
    if errors:
        for error in errors:
            st.error(error)
        return

    generation_errors: dict[str, str] = {}
    generated_documents: dict[str, str] = {}

    with st.spinner("Generating email, CV, and cover letter in parallel..."):
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_key = {
                executor.submit(config["generator"], form_data): key for key, config in DOCUMENT_CONFIG.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    generated_documents[key] = future.result().strip()
                except GeminiClientError as exc:
                    generation_errors[key] = str(exc)
                except Exception as exc:
                    generation_errors[key] = f"Unexpected error while generating {DOCUMENT_CONFIG[key]['button_label']}: {exc}"

    st.session_state.generated_documents = generated_documents
    st.session_state.generation_errors = generation_errors

    for key, config in DOCUMENT_CONFIG.items():
        document_text = generated_documents.get(key, "")
        st.session_state[config["state_key"]] = document_text
        if not document_text:
            st.session_state[config["state_key"]] = ""

    if st.session_state.generated_email:
        subject, body = parse_email_content(st.session_state.generated_email)
        st.session_state.parsed_email_subject = subject
        st.session_state.parsed_email_body = body
    else:
        st.session_state.parsed_email_subject = ""
        st.session_state.parsed_email_body = ""

    render_generation_status()


def render_generation_status() -> None:
    for key, config in DOCUMENT_CONFIG.items():
        if st.session_state.get(config["state_key"]):
            st.success(f"{config['title']} generated successfully.")
        elif st.session_state.generation_errors.get(key):
            st.error(f"{config['title']}: {st.session_state.generation_errors[key]}")


def render_top_actions() -> None:
    clear_col, spacer_col = st.columns([1, 2.6])
    with clear_col:
        if st.button("Clear Form and Results", use_container_width=True):
            clear_app_state(st.session_state)
            st.rerun()
    with spacer_col:
        st.markdown(
            """
            <div class="note-card">
                <div class="section-label">Gmail Draft Options</div>
                <p class="helper-note" style="margin:0.35rem 0 0 0;">
                    Open Gmail Draft uses the browser-based compose screen and cannot attach local files. Create Gmail
                    Draft with Attachments uses Gmail API OAuth and creates a real saved Gmail draft with the CV and
                    cover letter PDFs attached.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def sync_gmail_auth_state() -> None:
    auth_status = get_gmail_auth_status()
    st.session_state.gmail_auth_status = str(auth_status["label"])
    st.session_state.gmail_auth_detail = str(auth_status["detail"])


def handle_pending_google_oauth_callback() -> None:
    query_params = dict(st.query_params)
    if not any(key in query_params for key in ("code", "error", "state")):
        return

    try:
        handle_google_oauth_callback(
            query_params=query_params,
            expected_state=st.session_state.google_oauth_state or None,
        )
    except GmailClientError as exc:
        st.session_state.gmail_auth_feedback = str(exc)
        st.session_state.gmail_auth_status = "Not connected"
        st.session_state.gmail_auth_detail = "Google OAuth did not complete successfully."
        st.session_state.google_oauth_state = ""
        st.session_state.google_auth_url = ""
    else:
        st.session_state.gmail_auth_feedback = "Connected successfully"
        st.session_state.google_oauth_state = ""
        st.session_state.google_auth_url = ""
    finally:
        st.query_params.clear()

    sync_gmail_auth_state()
    st.rerun()


def get_or_create_google_auth_url() -> str:
    if st.session_state.google_auth_url and st.session_state.google_oauth_state:
        return st.session_state.google_auth_url

    auth_url, state = get_google_auth_url()
    st.session_state.google_auth_url = auth_url
    st.session_state.google_oauth_state = state
    return auth_url


def render_outputs() -> None:
    tab_email, tab_cv, tab_cover = st.tabs(
        ["Email", "CV / Resume", "Cover Letter"]
    )

    with tab_email:
        render_email_section()
    with tab_cv:
        render_document_section("cv")
    with tab_cover:
        render_document_section("cover_letter")


def render_email_section() -> None:
    document_text = st.session_state.generated_email
    error_message = st.session_state.generation_errors.get("email", "")

    if not document_text and not error_message:
        render_placeholder(
            "Professional Email",
            "Your AI-generated job application email will appear here after a successful run.",
        )
        return

    if error_message and not document_text:
        st.error(error_message)
        render_placeholder(
            "Professional Email",
            "Email generation did not complete successfully in the latest run.",
        )
        return

    st.markdown(
        """
        <div class="output-card">
            <div class="section-label">Professional Email</div>
            <div class="status-chip">Ready for review, download, copy, and Gmail drafting</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(format_email_markdown(document_text))
    render_email_actions(document_text)


def render_document_section(document_key: str) -> None:
    config = DOCUMENT_CONFIG[document_key]
    document_text = st.session_state.get(config["state_key"], "")
    error_message = st.session_state.generation_errors.get(document_key, "")

    if not document_text and not error_message:
        render_placeholder(
            config["title"],
            f"Your AI-generated {config['button_label'].lower()} will appear here after a successful run.",
        )
        return

    if error_message and not document_text:
        st.error(error_message)
        render_placeholder(
            config["title"],
            f"{config['button_label']} generation did not complete successfully in the latest run.",
        )
        return

    st.markdown(
        f"""
        <div class="output-card">
            <div class="section-label">{config["title"]}</div>
            <div class="status-chip">Ready for review, download, and copy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if document_key == "cv":
        st.markdown(format_cv_markdown(document_text))
    else:
        st.text_area(
            f"{config['button_label']} Preview",
            value=document_text,
            height=520,
            disabled=True,
            label_visibility="collapsed",
        )
    render_document_actions(document_key, document_text)


def render_placeholder(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-label">{title}</div>
            <p class="helper-note">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_email_actions(document_text: str) -> None:
    txt_bytes = document_to_txt_bytes(document_text)
    pdf_bytes = document_to_pdf_bytes("Professional Job Application Email", document_text)
    cv_pdf_bytes = document_to_pdf_bytes(
        DOCUMENT_CONFIG["cv"]["pdf_title"],
        st.session_state.generated_cv,
    )
    cover_letter_pdf_bytes = document_to_pdf_bytes(
        DOCUMENT_CONFIG["cover_letter"]["pdf_title"],
        st.session_state.generated_cover_letter,
    )
    gmail_link = build_gmail_compose_url(
        recipient=st.session_state.recruiter_email,
        subject=st.session_state.parsed_email_subject,
        body=st.session_state.parsed_email_body,
    )
    is_gmail_connected = st.session_state.gmail_auth_status == "Connected successfully"

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        components.html(build_copy_button_html("Email", document_text, "email"), height=56)
    with action_col2:
        st.download_button(
            "Download Email TXT",
            data=txt_bytes,
            file_name=DOCUMENT_CONFIG["email"]["txt_name"],
            mime="text/plain",
            use_container_width=True,
        )
    with action_col3:
        st.download_button(
            "Download Email PDF",
            data=pdf_bytes,
            file_name=DOCUMENT_CONFIG["email"]["pdf_name"],
            mime="application/pdf",
            use_container_width=True,
        )
    with action_col4:
        st.link_button("Open Gmail Draft", gmail_link, use_container_width=True)

    st.markdown("#### Gmail API Authentication")
    if is_gmail_connected:
        st.success("Connected successfully")
    else:
        st.warning("Not connected")

    st.caption(st.session_state.gmail_auth_detail)
    if st.session_state.gmail_auth_feedback:
        if is_gmail_connected:
            st.success(st.session_state.gmail_auth_feedback)
        else:
            st.error(st.session_state.gmail_auth_feedback)

    if not is_gmail_connected:
        try:
            google_auth_url = get_or_create_google_auth_url()
        except GmailClientError as exc:
            st.error(str(exc))
            google_auth_url = ""

        if google_auth_url:
            st.link_button("Sign in with Google", google_auth_url, use_container_width=True)

    can_create_api_draft = all(
        [
            is_gmail_connected,
            st.session_state.generated_email.strip(),
            st.session_state.generated_cv.strip(),
            st.session_state.generated_cover_letter.strip(),
            st.session_state.parsed_email_subject.strip(),
            st.session_state.parsed_email_body.strip(),
            st.session_state.recruiter_email.strip(),
        ]
    )

    if st.button(
        "Create Gmail Draft with Attachments",
        use_container_width=True,
        disabled=not can_create_api_draft,
        help=(
            "Requires Gmail authentication plus generated email, CV, and cover letter. The Google OAuth web flow "
            "uses credentials.json and saves token.json locally after a successful sign-in."
        ),
    ):
        handle_gmail_api_draft_creation(
            cv_pdf_bytes=cv_pdf_bytes,
            cover_letter_pdf_bytes=cover_letter_pdf_bytes,
        )

    st.caption(
        "The Gmail API draft button creates a real Gmail draft with `TBNZ_CV.pdf` and "
        "`TBNZ_Cover_Letter.pdf` attached. First-time use requires Google OAuth authentication."
    )


def render_document_actions(document_key: str, document_text: str) -> None:
    config = DOCUMENT_CONFIG[document_key]
    txt_bytes = document_to_txt_bytes(document_text)
    pdf_bytes = document_to_pdf_bytes(config["pdf_title"], document_text)

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        components.html(
            build_copy_button_html(config["button_label"], document_text, document_key),
            height=56,
        )
    with action_col2:
        st.download_button(
            f"Download {config['button_label']} TXT",
            data=txt_bytes,
            file_name=config["txt_name"],
            mime="text/plain",
            use_container_width=True,
        )
    with action_col3:
        st.download_button(
            f"Download {config['button_label']} PDF",
            data=pdf_bytes,
            file_name=config["pdf_name"],
            mime="application/pdf",
            use_container_width=True,
        )


def handle_gmail_api_draft_creation(cv_pdf_bytes: bytes, cover_letter_pdf_bytes: bytes) -> None:
    with st.spinner("Creating Gmail draft with attachments..."):
        try:
            draft_response = create_gmail_draft_with_attachments(
                recipient=st.session_state.recruiter_email,
                subject=st.session_state.parsed_email_subject,
                body=st.session_state.parsed_email_body,
                cv_pdf_bytes=cv_pdf_bytes,
                cover_letter_pdf_bytes=cover_letter_pdf_bytes,
                cv_filename=CV_ATTACHMENT_FILENAME,
                cover_letter_filename=COVER_LETTER_ATTACHMENT_FILENAME,
            )
        except GmailClientError as exc:
            st.error(str(exc))
            return

    draft_id = draft_response.get("id", "")
    st.session_state.gmail_draft_id = draft_id
    if draft_id:
        st.success(f"Gmail draft created successfully. Draft ID: {draft_id}")
    else:
        st.success("Gmail draft created successfully.")


def main() -> None:
    initialize_state()
    sync_gmail_auth_state()
    handle_pending_google_oauth_callback()
    apply_custom_theme()
    render_sidebar()
    render_header()

    submitted = render_form()
    if submitted:
        handle_generation()

    render_top_actions()
    render_outputs()


if __name__ == "__main__":
    main()
