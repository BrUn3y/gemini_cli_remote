"""Native startup regressions using local child processes and fake credentials."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

import pytest

import launcher

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def native_env(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    # API startup must never install a real crontab during tests.
    crontab = bindir / "crontab"
    crontab.write_text("#!/bin/sh\nexit 0\n")
    crontab.chmod(0o755)
    fake = bindir / "gemini"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "assert os.environ['GEMINI_API_KEY'] == 'offline-launch-key'\n"
        "assert '--approval-mode' in sys.argv\n"
        "print('offline Gemini result')\n"
    )
    fake.chmod(0o755)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"GEMINI_API_KEY=offline-launch-key\nGEMINI_BIN={fake}\n"
        f"HARNESS_PORT={port}\nGEMINI_WORKDIR={tmp_path / 'workspace'}\n"
    )
    env = {key: value for key, value in os.environ.items() if not key.startswith((
        "GEMINI_", "GOOGLE_", "HARNESS_", "SLACK_"
    ))}
    env.update({
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "HARNESS_ENV_FILE": str(env_file),
        "HARNESS_PYTHON": sys.executable,
        "HARNESS_HOST": "127.0.0.1",
        "PYTHONUNBUFFERED": "1",
        "HOME": str(tmp_path),
    })
    return env, port


@pytest.mark.parametrize("partial_token", [False, True])
def test_native_exports_env_starts_without_slack_and_stops(native_env, partial_token):
    env, port = native_env
    if partial_token:
        env["SLACK_BOT_TOKEN"] = "incomplete-offline-configuration"
    process = subprocess.Popen(
        ["bash", str(ROOT / "run-harness.sh")], cwd=ROOT.parent,
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(process.communicate()[0])
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=0.2) as response:
                    health = json.load(response)
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        else:
            pytest.fail("Native API did not start")
        assert health["gemini_present"] is True
        assert health["auth_method"] == "api_key"
        request = urllib.request.Request(
            f"{url}/invoke", data=json.dumps({"prompt": "--literal; $(ignored)", "yolo": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
        assert result["ok"] is True
        assert result["output"] == "offline Gemini result\n"
        assert result["command"][-1] == "--prompt=--literal; $(ignored)"
        process.terminate()
        output, _ = process.communicate(timeout=15)
        assert process.returncode == 0, output
        assert "starting API only" in output
        assert "offline-launch-key" not in output
        with socket.socket() as connection:
            assert connection.connect_ex(("127.0.0.1", port)) != 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)


def test_native_occupied_port_fails_before_starting_children(native_env, tmp_path):
    env, _ = native_env
    with socket.create_server(("127.0.0.1", 0)) as listener:
        port = listener.getsockname()[1]
        with Path(env["HARNESS_ENV_FILE"]).open("a") as config:
            config.write(f"HARNESS_PORT={port}\n")
        result = subprocess.run(
            ["bash", str(ROOT / "run-harness.sh")], env=env,
            capture_output=True, text=True, timeout=5,
        )
    assert result.returncode == 1
    assert f"cannot listen on 127.0.0.1:{port}" in result.stderr
    assert "Started server process" not in result.stderr


def test_failed_api_never_starts_slack(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "offline-bot")
    monkeypatch.setenv("SLACK_APP_TOKEN", "offline-app")
    failed_api = Mock()
    failed_api.poll.return_value = 1
    failed_api.returncode = 1
    with patch.object(launcher, "_check_port"), patch.object(
        launcher.subprocess, "Popen", return_value=failed_api
    ) as spawn:
        assert launcher.serve(with_slack=True) == 1
    assert spawn.call_count == 1


def test_slack_failure_stops_api(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "offline-bot")
    monkeypatch.setenv("SLACK_APP_TOKEN", "offline-app")
    api = Mock()
    api.poll.return_value = None
    bot = Mock()
    bot.poll.return_value = 1
    with patch.object(launcher, "_check_port"), patch.object(
        launcher, "_wait_ready", return_value=True
    ), patch.object(launcher.subprocess, "Popen", side_effect=[api, bot]):
        assert launcher.serve(with_slack=True) == 1
    api.terminate.assert_called_once()
    api.wait.assert_called_once()
