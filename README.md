# TBNZ Professional Email Generator

TBNZ Professional Email Generator is a multi-document Streamlit job application suite. It generates a professional job application email, an ATS-friendly CV / resume, and a tailored cover letter from one shared applicant and job form. It also supports creating a real Gmail draft with the generated CV and cover letter attached through Gmail API and OAuth 2.0.

## Features

- Dark-themed professional Streamlit interface
- Shared input form for applicant details, job details, and writing preferences
- Parallel AI generation for:
  - Professional Job Application Email
  - ATS-Friendly CV / Resume
  - Professional Cover Letter
- Separate internal prompt builders for email, CV, and cover letter
- Session state persistence for all generated outputs
- Independent success and error handling per generated document
- TXT and PDF download support for all three outputs
- Gmail web draft opening with prefilled recipient, subject, and body
- Real Gmail draft creation with PDF attachments using Gmail API and OAuth 2.0
- Modular utilities for parsing, export, copy actions, Gmail compose URL generation, and Gmail API draft creation
- Flexible Gemini model selection through environment variables

## Tech Stack

- Python
- Streamlit
- google-generativeai
- python-dotenv
- validators
- fpdf2
- google-api-python-client
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- urllib.parse
- concurrent.futures
- email.mime
- base64

## Folder Structure

```text
TBNZ_Professional_Email_Generator/
|-- app.py
|-- prompt_builder.py
|-- gemini_client.py
|-- gmail_client.py
|-- validators.py
|-- utils.py
|-- requirements.txt
|-- .env.example
|-- credentials.json        # add manually for Gmail OAuth
|-- token.json              # created automatically after first Gmail auth
`-- README.md
```

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Setup

Create a `.env` file in the project root based on `.env.example`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMAIL_MODEL=
GEMINI_CV_MODEL=
GEMINI_COVER_LETTER_MODEL=
```

Model behavior:

- `GEMINI_EMAIL_MODEL` overrides the email generator model when set.
- `GEMINI_CV_MODEL` overrides the CV generator model when set.
- `GEMINI_COVER_LETTER_MODEL` overrides the cover letter generator model when set.
- Any unset document-specific model falls back to `GEMINI_MODEL`.

## Gmail API OAuth Setup

This is required for `Create Gmail Draft with Attachments`.

### 1. Enable Gmail API

1. Open Google Cloud Console.
2. Create a project or select an existing one.
3. Go to `APIs & Services` -> `Library`.
4. Search for `Gmail API`.
5. Enable it.

### 2. Configure OAuth Consent Screen

1. Go to `APIs & Services` -> `OAuth consent screen`.
2. Choose `External` or `Internal` as appropriate.
3. Fill in the application name and required details.
4. Add yourself as a test user if the app is in testing mode.
5. Save the consent screen configuration.

### 3. Create OAuth Desktop Credentials

1. Go to `APIs & Services` -> `Credentials`.
2. Click `Create Credentials` -> `OAuth client ID`.
3. Choose `Desktop app`.
4. Download the generated client secret JSON file.
5. Rename it to `credentials.json`.
6. Place `credentials.json` in the project root beside `app.py`.

### 4. First-Time Authentication Flow

1. Run the app with `streamlit run app.py`.
2. Generate the email, CV, and cover letter.
3. Click `Create Gmail Draft with Attachments`.
4. A browser window opens for Google sign-in and consent.
5. Approve the requested Gmail compose scope.
6. After success, the app saves `token.json` locally.

The scope used is:

```text
https://www.googleapis.com/auth/gmail.compose
```

`token.json` is reused on later runs and refreshed when possible.

## Run The App

From the project folder:

```bash
streamlit run app.py
```

## Input Fields

Required fields:

- Full Name
- Email Address
- Phone Number
- LinkedIn Profile URL
- Recruiter Email Address
- Hiring Manager Name
- Company Name
- Job Title Applying For
- Current Role / Academic Background
- Key Skills
- Job Advertisement / Job Description
- English Level
- Preferred Tone
- Content Basis
- Email Length

Optional fields:

- Education
- Projects / Experience
- Certifications / Courses
- Tools / Technologies

## Output Actions

Email:

- Copy Email
- Download Email TXT
- Download Email PDF
- Open Gmail Draft
- Create Gmail Draft with Attachments

CV:

- Copy CV
- Download CV TXT
- Download CV PDF

Cover Letter:

- Copy Cover Letter
- Download Cover Letter TXT
- Download Cover Letter PDF

## Gmail Draft Behavior

The app supports two draft paths.

### Open Gmail Draft

Uses a Gmail compose URL in this form:

```text
https://mail.google.com/mail/?view=cm&fs=1&to=...&su=...&body=...
```

This supports:

- Prefilled recruiter email
- Prefilled subject
- Prefilled email body

This does not attach files.

### Create Gmail Draft with Attachments

Uses Gmail API and OAuth 2.0 to create a real saved Gmail draft containing:

- Recruiter email as recipient
- Generated subject
- Generated email body
- `TBNZ_CV.pdf`
- `TBNZ_Cover_Letter.pdf`

The draft is created but not sent automatically.

## Error Handling

The app handles:

- Missing or invalid Gemini API key
- Unavailable Gemini model
- Gemini quota issues
- Network-related generation errors
- Partial generation failures where one document fails and the others still complete
- Missing `credentials.json`
- Gmail OAuth failures
- Gmail API draft creation failures

## Security Notes

- Never hardcode API keys or OAuth secrets in source files.
- Keep `.env`, `credentials.json`, and `token.json` private and out of version control.
- Review generated content before sending any real application.
