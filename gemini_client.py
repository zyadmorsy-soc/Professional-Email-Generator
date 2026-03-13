from __future__ import annotations

import os

import google.generativeai as genai
from dotenv import load_dotenv

from prompt_builder import build_cover_letter_prompt, build_cv_prompt, build_email_prompt

load_dotenv()

DEFAULT_MODEL_NAME = "gemini-2.5-flash"


class GeminiClientError(Exception):
    """Raised when Gemini generation cannot be completed safely."""


def generate_email(form_data: dict[str, str]) -> str:
    return _generate_document(form_data, build_email_prompt(form_data), "GEMINI_EMAIL_MODEL")


def generate_cv(form_data: dict[str, str]) -> str:
    return _generate_document(form_data, build_cv_prompt(form_data), "GEMINI_CV_MODEL")


def generate_cover_letter(form_data: dict[str, str]) -> str:
    return _generate_document(
        form_data,
        build_cover_letter_prompt(form_data),
        "GEMINI_COVER_LETTER_MODEL",
    )


def _generate_document(form_data: dict[str, str], prompt: str, model_env_key: str) -> str:
    _ = form_data
    model = _configured_model(model_env_key)

    try:
        response = model.generate_content(prompt)
        generated_text = getattr(response, "text", "") or ""
        generated_text = generated_text.strip()

        if not generated_text:
            raise GeminiClientError(
                "Gemini returned an empty response. Please try again with a more detailed job description."
            )

        return generated_text
    except GeminiClientError:
        raise
    except Exception as exc:
        raise GeminiClientError(_map_gemini_error(exc, model_env_key)) from exc


def _configured_model(model_env_key: str) -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = _resolve_model_name(model_env_key)

    if not api_key:
        raise GeminiClientError(
            "Gemini API key not found. Add GEMINI_API_KEY to your .env file and restart the app."
        )

    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name=model_name)
    except Exception as exc:
        raise GeminiClientError(_map_gemini_error(exc, model_env_key)) from exc


def _resolve_model_name(model_env_key: str) -> str:
    return (
        os.getenv(model_env_key, "").strip()
        or os.getenv("GEMINI_MODEL", "").strip()
        or DEFAULT_MODEL_NAME
    )


def _map_gemini_error(exc: Exception, model_env_key: str) -> str:
    message = str(exc).lower()
    configured_label = model_env_key.replace("GEMINI_", "").replace("_", " ").title()

    if any(keyword in message for keyword in ("api key", "permission denied", "unauthorized", "authentication")):
        return "Gemini authentication failed. Verify your API key and try again."
    if any(keyword in message for keyword in ("quota", "resource has been exhausted", "429")):
        return "Gemini quota appears to be exceeded right now. Please wait and try again later."
    if any(keyword in message for keyword in ("model", "not found", "unsupported", "404")):
        return (
            f"The configured Gemini model for {configured_label} is unavailable. "
            f"Check {model_env_key} or GEMINI_MODEL in your environment settings."
        )
    if any(keyword in message for keyword in ("network", "connection", "dns", "timeout", "timed out", "unreachable")):
        return "A network issue prevented Gemini from responding. Check connectivity and try again."

    return "Generation failed due to a Gemini service error. Please try again."
