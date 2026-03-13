from __future__ import annotations

import importlib.metadata
import importlib.util
import re
from pathlib import Path


MIN_TEXT_LENGTHS = {
    "background": 30,
    "key_skills": 20,
    "job_description": 80,
}

FIELD_LABELS = {
    "full_name": "Full Name",
    "email_address": "Email Address",
    "phone_number": "Phone Number",
    "linkedin_url": "LinkedIn Profile URL",
    "recruiter_email": "Recruiter Email Address",
    "hiring_manager_name": "Hiring Manager Name",
    "company_name": "Company Name",
    "job_title": "Job Title Applying For",
    "background": "Current Role / Academic Background",
    "key_skills": "Key Skills",
    "job_description": "Job Advertisement / Job Description",
    "english_level": "English Level",
    "preferred_tone": "Preferred Tone",
    "content_basis": "Content Basis",
    "email_length": "Email Length",
    "education": "Education",
    "projects_experience": "Projects / Experience",
    "certifications": "Certifications / Courses",
    "tools_technologies": "Tools / Technologies",
}

OPTIONAL_FIELDS = {"education", "projects_experience", "certifications", "tools_technologies"}


def validate_form_data(form_data: dict[str, str]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_required_fields(form_data))

    if errors:
        return errors

    if len(form_data["full_name"].split()) < 2:
        errors.append("Full Name must include at least a first name and a last name.")

    if not _is_valid_email(form_data["email_address"]):
        errors.append("Enter a valid Email Address.")

    if not _is_valid_email(form_data["recruiter_email"]):
        errors.append("Enter a valid Recruiter Email Address.")

    if not _is_valid_phone_number(form_data["phone_number"]):
        errors.append("Enter a valid Phone Number using a realistic local or international format.")

    if not _is_valid_linkedin_url(form_data["linkedin_url"]):
        errors.append("Enter a valid LinkedIn Profile URL that includes `linkedin.com`.")

    if len(form_data["company_name"].strip()) < 2:
        errors.append("Company Name is too short.")

    if len(form_data["hiring_manager_name"].strip()) < 3:
        errors.append("Hiring Manager Name is too short.")

    if len(form_data["job_title"].strip()) < 2:
        errors.append("Job Title Applying For is too short.")

    for key, minimum in MIN_TEXT_LENGTHS.items():
        if len(_normalize_whitespace(form_data[key])) < minimum:
            errors.append(
                f"{FIELD_LABELS[key]} should contain more meaningful detail before generating the documents."
            )

    return errors


def _validate_required_fields(form_data: dict[str, str]) -> list[str]:
    missing_fields = [
        FIELD_LABELS[key]
        for key, value in form_data.items()
        if key not in OPTIONAL_FIELDS and not str(value).strip()
    ]
    if not missing_fields:
        return []
    return [f"{field} is required." for field in missing_fields]


def _is_valid_email(value: str) -> bool:
    external_validators = _load_third_party_validators()
    if external_validators is not None:
        return bool(external_validators.email(value))

    return bool(re.fullmatch(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", value, flags=re.IGNORECASE))


def _is_valid_linkedin_url(value: str) -> bool:
    external_validators = _load_third_party_validators()
    normalized = value.strip()
    if "linkedin.com" not in normalized.lower():
        return False
    if external_validators is not None:
        return bool(external_validators.url(normalized))
    return bool(re.fullmatch(r"^https?://[^\s/$.?#].[^\s]*$", normalized, flags=re.IGNORECASE))


def _is_valid_phone_number(value: str) -> bool:
    digits_only = re.sub(r"\D", "", value)
    if not 7 <= len(digits_only) <= 15:
        return False
    return bool(re.fullmatch(r"^\+?[0-9().\-\s]{7,25}$", value.strip()))


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _load_third_party_validators():
    try:
        distribution = importlib.metadata.distribution("validators")
        package_file = next(
            Path(distribution.locate_file(file_path))
            for file_path in distribution.files or []
            if str(file_path).replace("\\", "/").endswith("validators/__init__.py")
        )
        package_dir = str(package_file.parent)
        spec = importlib.util.spec_from_file_location(
            "third_party_validators",
            package_file,
            submodule_search_locations=[package_dir],
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None
