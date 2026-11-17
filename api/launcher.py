"""Supervise the API and optional Slack process in containers or on a VM."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from gemini_auth import auth_error
from runtime_config import api_url

API_DIR = Path(__file__).resolve().parent


def _check_port(host: str, port: int) -> None:
    """Fail before starting either child when the listening address is occupied."""
    with socket.create_server((host, port)):
        pass


def _stop(children: list[subprocess.Popen]) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def _wait_ready(api: subprocess.Popen, url: str, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while api.poll() is None and time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=0.5) as response:
                if response.status == 200 and api.poll() is None:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.1)
    return False


def serve(with_slack: bool) -> int:
    """Run children until one exits or the supervisor receives a stop signal."""
    host = os.environ.get("HARNESS_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("HARNESS_PORT", "8081"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("ERROR: HARNESS_PORT must be an integer from 1 to 65535.", file=sys.stderr)
        return 1
    try:
        _check_port(host, port)
    except OSError as exc:
        print(f"ERROR: cannot listen on {host}:{port}: {exc}", file=sys.stderr)
        return 1

    local_host = "127.0.0.1" if host == "0.0.0.0" else host
    os.environ.setdefault("GEMINI_REMOTE_URL", f"http://{local_host}:{port}")
    tokens = [bool(os.environ.get(name)) for name in ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN")]
    slack_enabled = with_slack and all(tokens)
    if with_slack and not slack_enabled:
        print("Gemini CLI Remote: starting API only; both Slack tokens are needed for the bot.", flush=True)

    children: list[subprocess.Popen] = []
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", host, "--port", str(port)],
            cwd=API_DIR, stdin=subprocess.DEVNULL,
        )
        children.append(api)
        if not _wait_ready(api, f"http://{local_host}:{port}"):
            print("ERROR: API did not become ready; Slack was not started.", file=sys.stderr)
            return api.returncode or 1
        if slack_enabled and not stopping:
            children.append(subprocess.Popen(
                [sys.executable, str(API_DIR / "slack_bot.py")],
                cwd=API_DIR, stdin=subprocess.DEVNULL,
            ))
        while not stopping:
            for child in children:
                code = child.poll()
                if code is not None:
                    return code if code >= 0 else 128 - code
            time.sleep(0.1)
        return 0
    finally:
        _stop(children)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main() -> int:
    """Validate configuration and dispatch the entrypoint command."""
    command, *args = sys.argv[1:] or ["serve-all"]
    if command in {"gemini", "shell"}:
        os.execvp(os.environ.get("GEMINI_BIN", "gemini"), [os.environ.get("GEMINI_BIN", "gemini"), *args])
    if command not in {"serve", "serve-all", "slack"}:
        os.execvp(command, [command, *args])
    if command != "slack" and not shutil.which(os.environ.get("GEMINI_BIN", "gemini")):
        print("ERROR: 'gemini' not found. Install @google/gemini-cli (see README).", file=sys.stderr)
        return 1
    if command != "slack":
        error = auth_error()
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
    if command == "slack":
        print(f"Gemini CLI Remote: Slack API target {api_url()}", flush=True)
        os.execv(sys.executable, [sys.executable, str(API_DIR / "slack_bot.py")])
    return serve(with_slack=command == "serve-all")


if __name__ == "__main__":
    raise SystemExit(main())
