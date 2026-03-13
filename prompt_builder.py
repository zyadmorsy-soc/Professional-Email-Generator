from __future__ import annotations


def _build_candidate_profile(form_data: dict[str, str]) -> str:
    optional_sections = [
        ("Education", form_data.get("education", "")),
        ("Projects / Experience", form_data.get("projects_experience", "")),
        ("Certifications / Courses", form_data.get("certifications", "")),
        ("Tools / Technologies", form_data.get("tools_technologies", "")),
    ]

    extras = "\n".join(
        f"- {label}: {value}" for label, value in optional_sections if str(value).strip()
    )

    base = f"""
Applicant details:
- Full name: {form_data["full_name"]}
- Email: {form_data["email_address"]}
- Phone: {form_data["phone_number"]}
- LinkedIn: {form_data["linkedin_url"]}
- Current role / academic background: {form_data["background"]}
- Key skills: {form_data["key_skills"]}
""".strip()

    if extras:
        return f"{base}\n{extras}"
    return base


def build_email_prompt(form_data: dict[str, str]) -> str:
    content_basis = form_data["content_basis"]
    basis_instruction = (
        "Use the job advertisement as the main decision driver. Keep the applicant's "
        "identity minimal and avoid expanding heavily on background or skills beyond "
        "what is necessary for credibility."
        if content_basis == "Job ad only"
        else
        "Use the job advertisement, background, and key skills in a detailed, role-specific "
        "way. Make the applicant's fit feel concrete, credible, and naturally persuasive."
    )

    length_instruction = {
        "Short": "Keep the email compact and efficient, around 140 to 190 words.",
        "Medium": "Keep the email balanced and substantial, around 190 to 260 words.",
        "Detailed": "Keep the email more developed and persuasive, around 260 to 360 words.",
    }[form_data["email_length"]]

    tone_instruction = {
        "Formal": "Maintain a formal professional tone without sounding stiff.",
        "Very Formal": "Use highly polished, respectful business language.",
        "Friendly but Professional": "Sound warm, approachable, and professional.",
        "Confident": "Sound self-assured and credible without exaggeration.",
        "Polite": "Use courteous, respectful language throughout.",
    }[form_data["preferred_tone"]]

    return f"""
You are an expert executive communications writer specializing in professional job application emails.

Write one realistic, polished, ready-to-send job application email in English for the applicant below.

Non-negotiable requirements:
- Return only the final email content ready to send.
- Do not include notes, explanations, bullet points, or placeholders.
- The email must start with a clear subject line in this format: Subject: ...
- Use a greeting that addresses the hiring manager by name.
- Include a natural introduction, role-specific relevance, and a professional closing.
- End with a full signature containing the applicant's full name, phone number, email address, and LinkedIn URL.
- Avoid robotic phrasing, empty buzzwords, cliches, exaggerated claims, and generic motivational language.
- Make the wording sound human, credible, and tailored to the role and company.
- Respect the selected English level, tone, and email length.

Writing controls:
- English level: {form_data["english_level"]}
- Tone: {form_data["preferred_tone"]}
- Length preference: {form_data["email_length"]}. {length_instruction}
- Content basis: {content_basis}. {basis_instruction}
- Company: {form_data["company_name"]}
- Job title: {form_data["job_title"]}

{_build_candidate_profile(form_data)}

Recipient details:
- Recruiter email: {form_data["recruiter_email"]}
- Hiring manager name: {form_data["hiring_manager_name"]}

Job advertisement / job description:
{form_data["job_description"]}

Additional guidance:
- The introduction should clearly state the role being applied for.
- Connect the applicant's profile to the job requirements in a specific and believable way.
- Keep the structure clean and ready for email use.
- {tone_instruction}
- Use wording suitable for {form_data["english_level"]}.
""".strip()


def build_cv_prompt(form_data: dict[str, str]) -> str:
    return f"""
You are an expert ATS resume writer and professional recruiter-facing CV specialist.

Write a highly professional, ATS-friendly, recruiter-readable CV tailored to the target role.

The CV must be:
- clean
- structured
- realistic
- keyword-aligned with the job advertisement
- easy for both ATS systems and human recruiters to read

Important formatting rules:
- Use clear section headings
- Use bullet points for skills, projects, experience, certifications, and tools where appropriate
- Do NOT return one large block of text
- Keep a clean hierarchy and spacing between sections
- Avoid tables, columns, icons, graphics, and decorative formatting
- Keep the layout ATS-safe

Required CV structure in this exact order:
1. Full Name
2. Contact Information (Phone | Email | LinkedIn)
3. Professional Title / Target Role
4. Professional Summary
5. Technical Skills
6. Education
7. Experience / Projects
8. Certifications / Courses
9. Tools / Technologies
10. Languages

Writing rules:
- Tailor the CV strongly to the job requirements
- Highlight relevant skills and keywords naturally
- Keep the summary concise and professional in paragraph form
- Use bullet points for project and experience descriptions
- Use bullet points for skills, certifications, and tools when appropriate
- Do not invent fake experience
- Do not exaggerate impact, seniority, or responsibilities
- If formal work experience is limited, strengthen the CV through projects, coursework, internships, military service, certifications, and academic achievements
- Keep the tone highly professional and realistic
- Base the CV only on the information provided by the applicant and the job advertisement

Output rules:
- Return only the final CV content
- No explanations
- No commentary
- No markdown code block
- Make the content ready for markdown display, TXT export, and PDF export
- Keep section titles explicit and easy to detect
- Keep each section separated clearly instead of merging everything into one block
- If some optional sections have limited input, keep them concise and truthful instead of inventing details

Target role:
- Company: {form_data["company_name"]}
- Job title: {form_data["job_title"]}
- English level: {form_data["english_level"]}
- Tone: {form_data["preferred_tone"]}

{_build_candidate_profile(form_data)}

Job advertisement / job description:
{form_data["job_description"]}
""".strip()


def build_cover_letter_prompt(form_data: dict[str, str]) -> str:
    tone_instruction = {
        "Formal": "Maintain a formal professional tone without sounding stiff.",
        "Very Formal": "Use highly polished, respectful business language.",
        "Friendly but Professional": "Sound warm, approachable, and professional.",
        "Confident": "Sound confident and grounded, never overstated.",
        "Polite": "Use courteous, respectful language throughout.",
    }[form_data["preferred_tone"]]

    return f"""
You are an expert professional cover letter writer.

Write a highly professional, tailored cover letter based on the applicant's information and the target job advertisement.

The cover letter must:
- Sound human, natural, and polished
- Be tailored to the company and role
- Connect the applicant's skills and background to the job requirements
- Avoid cliches, exaggeration, and generic AI tone
- Be realistic, concise, and ready to send or download
- Use a proper business-letter flow with greeting, strong middle paragraphs, and a professional sign-off

Output rules:
- Return only the final cover letter
- No explanations
- No notes
- No markdown code block
- No bullet points unless absolutely necessary

Writing controls:
- English level: {form_data["english_level"]}
- Tone: {form_data["preferred_tone"]}. {tone_instruction}
- Company: {form_data["company_name"]}
- Job title: {form_data["job_title"]}
- Hiring manager name: {form_data["hiring_manager_name"]}

{_build_candidate_profile(form_data)}

Job advertisement / job description:
{form_data["job_description"]}
""".strip()
