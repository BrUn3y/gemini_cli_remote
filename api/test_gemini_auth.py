"""Authentication configuration checks; never authenticate with Google."""
import gemini_auth


def test_missing_credentials_explain_supported_methods():
    assert gemini_auth.auth_method() == "unconfigured"
    assert "GEMINI_API_KEY" in gemini_auth.auth_error()


def test_api_key_is_supported_without_exposing_it(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-key")
    assert gemini_auth.auth_method() == "api_key"
    assert gemini_auth.auth_error() is None


def test_vertex_adc_requires_project_and_location(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "ignored-in-vertex-mode")
    assert gemini_auth.auth_method() == "vertex"
    assert "GOOGLE_CLOUD_PROJECT" in gemini_auth.auth_error()
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    assert gemini_auth.auth_error() is not None
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    assert gemini_auth.auth_error() is None


def test_vertex_express_mode_accepts_google_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "private-test-key")
    assert gemini_auth.auth_error() is None


def test_cached_google_login_is_supported(tmp_path):
    cache = tmp_path / ".gemini" / "oauth_creds.json"
    cache.parent.mkdir()
    cache.write_text('{}')
    assert gemini_auth.auth_method() == "oauth"
    assert gemini_auth.auth_error() is None
