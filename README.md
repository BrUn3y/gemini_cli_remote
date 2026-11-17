# Gemini CLI Remote

Run **Google Gemini CLI** through a REST API or Slack, with cancellable jobs,
SSE output, and cron schedules. A verification and retry loop lets Gemini
execute a task, runs a check command, and feeds failures back to Gemini until
the check passes or the attempt limit is reached.

This independent project is derived from
[IBM_Bob_Harness/main, commit fec8e09](https://github.com/BrUn3y/IBM_Bob_Harness/tree/fec8e092242e10fd3140afb0f5eed2cfde3bcc7c).
It is published as an import with its own Git history. Gemini CLI is the
execution engine; select its model with `model` or `GEMINI_MODEL`.

## Start with Docker or Podman

```bash
git clone https://github.com/BrUn3y/gemini_cli_remote.git
cd gemini_cli_remote
cp .env.example .env
# Edit .env and set GEMINI_API_KEY; leave the Slack tokens empty if not needed.
nano .env
podman compose up --build -d
curl -fsS http://127.0.0.1:8081/health
```

You can replace `podman` with `docker`. The image uses Gemini CLI **0.68.0** and
Python **3.12**. The API is published on **host port 8081**, bound to loopback,
and listens on port 8080 inside the container. Change `HARNESS_PORT` in `.env`
to use a different host port. Files and schedules persist in `./workspace`.

```bash
podman compose logs -f gemini
podman compose up -d --force-recreate  # Apply changes to .env.
podman compose down
```

## Run natively on a Google Cloud VM

Requires Python 3.12+, Node.js 22+, and npm. Install `cron` on Linux for scheduled
tasks and make sure its service is running.

```bash
npm install --global @google/gemini-cli@0.68.0
python3.12 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.txt
cp .env.example .env
nano .env
./run-harness.sh
```

`run-harness.sh` loads and exports `.env` before starting any processes, uses
`./workspace` as the working directory, and listens on `127.0.0.1:8081`.
Set `HARNESS_ENV_FILE` to use a different configuration file. Slack starts only
when **both** tokens are present; missing or incomplete tokens result in API-only
mode. Use `./run-harness.sh serve` to run the API on its own.

The supervisor checks the port before starting processes, waits for the API to
be ready before connecting Slack, and stops the remaining process if either
exits. If the port is occupied, identify the running instance before restarting:

```bash
sudo ss -ltnp 'sport = :8081'
curl -fsS http://127.0.0.1:8081/health
```

For systemd, update the user, paths, and `PATH` in
[deploy/gemini-cli-remote.service](deploy/gemini-cli-remote.service). Use the same
OS user that installed Gemini CLI and, if applicable, signed in to Google.

```bash
sudo cp deploy/gemini-cli-remote.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gemini-cli-remote.service
sudo systemctl status gemini-cli-remote.service --no-pager
sudo journalctl -u gemini-cli-remote.service -n 60 --no-pager
```

The Bob harness and this service can coexist using separate directories,
services, containers, and host ports. For native deployments, use a dedicated
Linux user for Gemini: each harness manages its user's crontab.
To access the service from your computer:

```bash
ssh -L 8081:127.0.0.1:8081 user@your-vm
# Open http://127.0.0.1:8081/docs on your computer.
```

## Google authentication

Choose one option. `/health` reports the configured method without exposing
secrets. Its `auth_configured` field checks local configuration; Gemini validates
credentials, permissions, quotas, and model availability when a task runs.

- **API key:** set `GEMINI_API_KEY` to a key from
  [Google AI Studio](https://aistudio.google.com/apikey).
- **Vertex AI / ADC:** leave `GEMINI_API_KEY` empty and set
  `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and
  `GOOGLE_CLOUD_LOCATION`. Enable Vertex AI and grant `roles/aiplatform.user`
  to the VM's service account. Compute Engine can use credentials from the
  metadata server. To use a JSON key, set `GOOGLE_APPLICATION_CREDENTIALS`;
  for containers, mount the key as a read-only file and use its path inside the
  container. Alternatively, Vertex express mode supports `GOOGLE_API_KEY` with
  the Vertex flag enabled.
- **Google sign-in, native deployments:** run `gemini` interactively once and
  complete sign-in. The service must run as the same OS user and use that user's
  `~/.gemini/oauth_creds.json`. Use an API key or Vertex AI for containers.

`GEMINI_MODEL=auto` lets the CLI select a model. You can also use a model name or
alias supported by your account. The authentication settings saved in
`~/.gemini/settings.json` must match your chosen method.

## API

Swagger UI: `http://127.0.0.1:8081/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Status and resolved configuration |
| POST | `/invoke` | Run synchronously |
| POST | `/jobs` | Create a cancellable job |
| POST | `/run` | Execute, verify, and retry |
| GET | `/jobs` | List jobs |
| GET / DELETE | `/jobs/{id}` | Inspect / cancel a job |
| GET | `/jobs/{id}/stream` | Stream job output over SSE |
| POST | `/stream` | Create a job and stream its output over SSE |
| GET / POST | `/schedules` | List / create schedules |
| GET / DELETE | `/schedules/{id}` | Inspect / delete a schedule |
| POST | `/schedules/{id}/run` | Run a schedule immediately |

```bash
curl -sS http://127.0.0.1:8081/invoke \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Create hello.py and print a greeting", "model":"auto"}'

curl -sS http://127.0.0.1:8081/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Create hello.py and print a greeting", "check":"python3 hello.py", "max_attempts":3}'

curl -N http://127.0.0.1:8081/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"List the files in the working directory"}'

curl -sS http://127.0.0.1:8081/schedules \
  -H 'Content-Type: application/json' \
  -d '{"cron":"0 9 * * 1-5", "prompt":"Review the project changes", "name":"Daily review"}'
```

`/invoke` returns `ok`, `exit_code`, `output`, `error`, and `command`.
`/jobs` and `/run` return an `id`; poll `/jobs/{id}` until the job reaches a
terminal state. `/run` includes `attempts`, `gemini_exit_code`, `check_exit_code`,
and `success`. SSE output delivers lines as the process writes them; it does
not guarantee an event for each token. Jobs and their results are stored in
memory and are lost on restart. The cron registry and workspace files persist.

Execution request fields include `prompt`, `model`, `workdir`, `timeout`
(1–3600 seconds), and `yolo` (defaults to `true`). With `yolo=true`, Gemini uses
`--approval-mode yolo`; with `false`, it uses `default`, and tools that require
approval cannot be approved interactively in headless mode. Schedules use five
cron fields and the system's time zone (UTC in the image). To send a scheduled
run's result to Slack, include `channel` when creating the schedule or set
`SLACK_DEFAULT_CHANNEL`.

Importable examples in [httpie/](httpie/) include OpenAPI, Postman, and HTTP
requests.

## Slack

Follow [SLACK_SETUP.md](SLACK_SETUP.md) and use
[slack/manifest.yaml](slack/manifest.yaml). The bot connects through Socket Mode
and replies in threads without requiring mentions. It supports thread context,
attachments, replies split across messages, event deduplication, and concurrency
limits. Type `cancel` or `stop` in the thread to cancel the active job.
Attachments are downloaded to the workspace; if the bot and API run separately,
they must share that path.

## Development

```bash
.venv/bin/python -m pip install -r api/requirements-dev.txt
.venv/bin/python -m pytest -q api
bash -n run-harness.sh entrypoint.sh
podman build -t gemini_cli_remote .
```

Tests run locally without connecting to Google or Slack. They cover command
construction, authentication configuration, errors, process-group cancellation,
retries, cron, reply formatting, startup without Slack, and occupied ports.
GitHub Actions runs the suite with Python 3.12 on every push and pull request.

The API can execute tools and commands and has no HTTP authentication. Keep it
bound to loopback and access it through SSH or a private network with access
controls. `workdir` selects the working directory; it is not a sandbox. Store
keys and tokens in `.env` or a secrets manager and never commit them to Git.

Official reference: [Gemini CLI headless](https://geminicli.com/docs/cli/headless/).
