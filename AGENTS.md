# Repository Guidelines

Gemini CLI Remote is a Python 3.12+ FastAPI harness derived from
IBM_Bob_Harness/main at fec8e092242e10fd3140afb0f5eed2cfde3bcc7c.

Core code lives in `api/`: `server.py` handles API and execution,
`gemini_auth.py` checks local authentication configuration, `launcher.py`
supervises processes, `schedules.py` persists cron tasks and `slack_bot.py`
connects Slack Socket Mode. Matching `test_*.py` files stay beside modules.
`GEMINI.md` supplies runtime context. Keep persistent user data in the ignored
`workspace/`, examples in `httpie/` and Slack configuration in `slack/`.

Run `.venv/bin/python -m pytest -q api`, `bash -n run-harness.sh entrypoint.sh`
and `podman build -t gemini_cli_remote .` as appropriate. Use four spaces,
PEP 8 names, annotations for public interfaces and Conventional Commit subjects.
Mock Google and Slack calls. Test command construction, validation, failure
paths and process cleanup when changing execution behavior.

Never commit `.env`, cached OAuth credentials, service-account keys or tokens.
The API defaults to loopback on host port 8081. Treat approval flags and
network exposure as security-sensitive. `workdir` is not an isolation boundary.
