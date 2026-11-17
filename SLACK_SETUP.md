# Connect Gemini CLI Remote to Slack

1. At https://api.slack.com/apps, choose **Create New App → From a manifest**.
   Select your workspace and paste [slack/manifest.yaml](slack/manifest.yaml).
2. Install the app in your workspace. Under **OAuth & Permissions**, copy the
   **Bot User OAuth Token** (`xoxb-...`) into `SLACK_BOT_TOKEN` in `.env`.
3. Under **Basic Information → App-Level Tokens**, create a token with
   `connections:write`. Copy the `xapp-...` token into `SLACK_APP_TOKEN`.
4. Make sure **Socket Mode** is enabled. The manifest includes the `chat:write`,
   `channels:history`, and `files:read` scopes and the `message.channels` event.
5. Invite the bot to a public channel: `/invite @gemini_cli_remote`.
6. Configure Gemini authentication in `.env` as described in the README, then
   apply the configuration:

```bash
# Container:
podman compose up -d --force-recreate
podman compose logs -f gemini

# Or a native service:
sudo systemctl restart gemini-cli-remote.service
sudo journalctl -u gemini-cli-remote.service -n 60 --no-pager
```

Write a message in the channel without mentioning the bot. Its reply appears in
a thread, with a status indicator that updates while Gemini works. Follow-up
questions in the same thread include the previous context. Attachments are
downloaded to `SLACK_UPLOAD_DIR`, and Gemini receives their local paths.

To cancel an active job, type `cancel` or `stop` in its thread. Cron tasks can
post their results when they include the correct `channel` or when you set
`SLACK_DEFAULT_CHANNEL`.

Options in `.env`: `SLACK_ALLOWED_CHANNELS` restricts channels by ID,
`SLACK_MAX_CONCURRENT` limits simultaneous jobs (2 by default), and
`GEMINI_INVOKE_TIMEOUT` limits the wait time (600 seconds). Attachment limits
and cleanup options are documented in `.env.example`.

If either or both tokens are missing, `serve-all` starts the API on its own.
If the Slack connection fails with both tokens present, the supervisor stops
the processes so systemd or Compose can restart the service. Check the logs to
resolve scope, token, or connectivity issues.

Socket Mode uses an outbound connection: it requires neither a public port nor
an HTTP event URL.
