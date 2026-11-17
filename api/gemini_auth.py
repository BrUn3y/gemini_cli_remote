"""Check local Gemini authentication configuration without making API calls."""
import os
from pathlib import Path


def auth_method() -> str:
    """Identify the configured authentication source; credentials stay private."""
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
        return "vertex"
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return "api_key"
    if (Path.home() / ".gemini" / "oauth_creds.json").is_file():
        return "oauth"
    return "unconfigured"


def auth_error() -> str | None:
    """Return a configuration error, leaving credential validation to the CLI."""
    method = auth_method()
    if method == "vertex":
        if os.environ.get("GOOGLE_API_KEY", "").strip():
            return None
        if all(os.environ.get(name, "").strip() for name in (
            "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"
        )):
            return None
        return (
            "Vertex AI requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION "
            "with Application Default Credentials, or GOOGLE_API_KEY."
        )
    if method == "unconfigured":
        return (
            "Configure GEMINI_API_KEY, Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true), "
            "or sign in with `gemini` as the same OS user before starting."
        )
    return None
