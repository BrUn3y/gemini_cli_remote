"""Keep the offline suite independent of the developer's Gemini credentials."""
import pytest

import gemini_auth
import server


@pytest.fixture(autouse=True)
def isolate_gemini_auth(monkeypatch, tmp_path):
    for name in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(gemini_auth.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(server, "DEFAULT_WORKDIR", str(tmp_path))
