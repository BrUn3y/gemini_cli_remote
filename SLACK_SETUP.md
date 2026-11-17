# Conectar Gemini CLI Remote con Slack

1. En https://api.slack.com/apps elige **Create New App → From a manifest**.
   Selecciona tu workspace y pega [slack/manifest.yaml](slack/manifest.yaml).
2. Instala la app en el workspace. En **OAuth & Permissions**, copia el
   **Bot User OAuth Token** (`xoxb-...`) a `SLACK_BOT_TOKEN` en `.env`.
3. En **Basic Information → App-Level Tokens**, crea un token con
   `connections:write`. Copia el token `xapp-...` a `SLACK_APP_TOKEN`.
4. Verifica que **Socket Mode** esté activado. El manifiesto incluye los scopes
   `chat:write`, `channels:history` y `files:read`, y el evento `message.channels`.
5. Invita al bot a un canal público: `/invite @gemini_cli_remote`.
6. Configura la autenticación de Gemini en `.env` como indica el README y aplica
   la configuración:

```bash
# Contenedor:
podman compose up -d --force-recreate
podman compose logs -f gemini

# O servicio nativo:
sudo systemctl restart gemini-cli-remote.service
sudo journalctl -u gemini-cli-remote.service -n 60 --no-pager
```

Escribe en el canal sin mencionar al bot. La respuesta aparece en un hilo y
actualiza un indicador mientras Gemini trabaja. Las preguntas posteriores del
mismo hilo incluyen el contexto anterior. Los archivos adjuntos se descargan en
`SLACK_UPLOAD_DIR` y Gemini recibe sus rutas locales.

Para cancelar un trabajo activo, escribe `cancelar`, `cancel` o `stop` en ese
hilo. Las tareas cron pueden publicar sus resultados si incluyen el `channel`
correcto o si configuras `SLACK_DEFAULT_CHANNEL`.

Opciones de `.env`: `SLACK_ALLOWED_CHANNELS` limita los canales por ID,
`SLACK_MAX_CONCURRENT` limita los trabajos simultáneos (2 por defecto) y
`GEMINI_INVOKE_TIMEOUT` limita la espera (600 segundos). Los límites y la limpieza
de adjuntos se documentan en `.env.example`.

Si falta uno o ambos tokens, `serve-all` inicia solo la API. Si falla la conexión
a Slack con ambos tokens presentes, el supervisor detiene los procesos y
systemd/Compose puede reiniciar el servicio. Consulta los logs para corregir
scopes, tokens o conectividad.

Socket Mode establece una conexión saliente: no requiere abrir un puerto
público ni configurar una URL HTTP de eventos.
