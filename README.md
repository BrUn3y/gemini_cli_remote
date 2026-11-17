# Gemini CLI Remote

Ejecuta **Google Gemini CLI** desde una API REST o desde Slack, con trabajos
cancelables, salida por SSE y tareas programadas con cron. Incluye un bucle de
verificación y reintentos: Gemini ejecuta la tarea, el harness corre un comando
de comprobación y devuelve los errores a Gemini hasta que pase o agote los intentos.

Proyecto independiente derivado de
[IBM_Bob_Harness/main, commit fec8e09](https://github.com/BrUn3y/IBM_Bob_Harness/tree/fec8e092242e10fd3140afb0f5eed2cfde3bcc7c).
Se publica como una importación con historial independiente. El ejecutor es
Gemini CLI; la selección de modelo se configura con `model` / `GEMINI_MODEL`.

## Arranque con Docker o Podman

```bash
git clone https://github.com/BrUn3y/gemini_cli_remote.git
cd gemini_cli_remote
cp .env.example .env
# Edita .env y configura GEMINI_API_KEY; deja Slack vacío si no lo necesitas.
nano .env
podman compose up --build -d
curl -fsS http://127.0.0.1:8081/health
```

Puedes sustituir `podman` por `docker`. Se fijan Gemini CLI **0.68.0** y Python
**3.12**. La API escucha en el puerto **8081 del host**, publicado solo en
loopback, y en el 8080 dentro del contenedor. Puedes cambiar `HARNESS_PORT` en
`.env`. Los archivos y las programaciones persisten en `./workspace`.

```bash
podman compose logs -f gemini
podman compose up -d --force-recreate  # aplicar cambios en .env
podman compose down
```

## Arranque nativo en una VM de Google Cloud

Requiere Python 3.12+, Node.js 22+ y npm. Instala `cron` en Linux para las tareas
programadas y verifica que su servicio esté activo.

```bash
npm install --global @google/gemini-cli@0.68.0
python3.12 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.txt
cp .env.example .env
nano .env
./run-harness.sh
```

`run-harness.sh` carga y exporta `.env` antes de lanzar los procesos, usa
`./workspace` como directorio de trabajo y escucha en `127.0.0.1:8081`.
Puedes usar `HARNESS_ENV_FILE` para otro archivo de configuración. Slack se
activa únicamente cuando están presentes **ambos** tokens; con tokens ausentes
o incompletos arranca la API. `./run-harness.sh serve` ejecuta solo la API.

El supervisor comprueba el puerto antes de iniciar procesos, espera a que su
API esté lista antes de conectar Slack y detiene el proceso compañero si alguno
termina. Si el puerto está ocupado, identifica la instancia antes de reiniciar:

```bash
sudo ss -ltnp 'sport = :8081'
curl -fsS http://127.0.0.1:8081/health
```

Para systemd, adapta el usuario, las rutas y el `PATH` de
[deploy/gemini-cli-remote.service](deploy/gemini-cli-remote.service). Usa el mismo
usuario que instaló Gemini CLI y, si aplica, inició sesión en Google.

```bash
sudo cp deploy/gemini-cli-remote.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gemini-cli-remote.service
sudo systemctl status gemini-cli-remote.service --no-pager
sudo journalctl -u gemini-cli-remote.service -n 60 --no-pager
```

El harness de Bob y este servicio pueden coexistir: tienen carpetas, servicio,
contenedor y puerto de host distintos. En despliegues nativos usa un usuario
Linux dedicado para Gemini: cada harness administra el crontab de su usuario.
Acceso remoto desde tu computadora:

```bash
ssh -L 8081:127.0.0.1:8081 usuario@tu-vm
# Abre http://127.0.0.1:8081/docs en tu computadora.
```

## Autenticación con Google

Elige una opción; `/health` muestra el método configurado, nunca los secretos.
El estado `auth_configured` verifica configuración local; Gemini valida permisos,
credenciales, cuotas y disponibilidad del modelo al ejecutar una tarea.

- **API key:** establece `GEMINI_API_KEY` con una clave de
  [Google AI Studio](https://aistudio.google.com/apikey).
- **Vertex AI / ADC:** deja `GEMINI_API_KEY` vacío y configura
  `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT` y
  `GOOGLE_CLOUD_LOCATION`. Habilita Vertex AI y asigna `roles/aiplatform.user`
  a la cuenta de servicio de la VM. En Compute Engine puede usar las credenciales
  del servidor de metadatos. Para una clave JSON, configura
  `GOOGLE_APPLICATION_CREDENTIALS` y, en contenedores, móntala como archivo de
  solo lectura con la ruta correspondiente dentro del contenedor. Como
  alternativa, Vertex express mode admite `GOOGLE_API_KEY` con el flag Vertex.
- **Inicio de sesión Google, nativo:** ejecuta `gemini` de forma interactiva una
  vez y completa el acceso. El servicio debe usar el mismo usuario y su archivo
  `~/.gemini/oauth_creds.json`. Para contenedores usa API key o Vertex AI.

`GEMINI_MODEL=auto` deja la selección al CLI. También puedes usar un nombre o
alias de modelo compatible con tu cuenta. La configuración de autenticación
guardada en `~/.gemini/settings.json` debe coincidir con el método elegido.

## API

Swagger UI: `http://127.0.0.1:8081/docs`.

| Método | Ruta | Función |
| --- | --- | --- |
| GET | `/health` | Estado y configuración resuelta |
| POST | `/invoke` | Ejecución síncrona |
| POST | `/jobs` | Crear un trabajo cancelable |
| POST | `/run` | Ejecutar, verificar y reintentar |
| GET | `/jobs` | Listar trabajos |
| GET / DELETE | `/jobs/{id}` | Consultar / cancelar |
| GET | `/jobs/{id}/stream` | Salida SSE de un trabajo |
| POST | `/stream` | Crear trabajo y seguir su salida SSE |
| GET / POST | `/schedules` | Listar / crear tareas programadas |
| GET / DELETE | `/schedules/{id}` | Consultar / eliminar programación |
| POST | `/schedules/{id}/run` | Ejecutar programación ahora |

```bash
curl -sS http://127.0.0.1:8081/invoke \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Crea hello.py e imprime un saludo", "model":"auto"}'

curl -sS http://127.0.0.1:8081/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Crea hello.py e imprime un saludo", "check":"python3 hello.py", "max_attempts":3}'

curl -N http://127.0.0.1:8081/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Lista los archivos del directorio de trabajo"}'

curl -sS http://127.0.0.1:8081/schedules \
  -H 'Content-Type: application/json' \
  -d '{"cron":"0 9 * * 1-5", "prompt":"Revisa los cambios del proyecto", "name":"Revisión diaria"}'
```

`/invoke` devuelve `ok`, `exit_code`, `output`, `error` y `command`.
`/jobs` y `/run` devuelven un `id`; consulta `/jobs/{id}` hasta el estado final.
`/run` incluye `attempts`, `gemini_exit_code`, `check_exit_code` y `success`.
La salida SSE entrega líneas a medida que el proceso las escribe; no garantiza
un evento por token. Los trabajos y sus resultados viven en memoria: un reinicio
los pierde. El registro de cron y los archivos del workspace sí persisten.

Campos comunes: `prompt`, `model`, `workdir`, `timeout` (1–3600 segundos) y
`yolo` (por defecto `true`). Con `yolo=true`, Gemini usa
`--approval-mode yolo`; con `false`, usa `default` y las herramientas que
requieren aprobación no pueden aprobarse interactivamente en modo headless.
Las programaciones usan cron de cinco campos y la zona horaria del sistema
(UTC en la imagen). Para enviar su resultado a Slack, incluye `channel` al
crearlas o configura `SLACK_DEFAULT_CHANNEL`.

Ejemplos importables en [httpie/](httpie/): OpenAPI, Postman y solicitudes HTTP.

## Slack

Sigue [SLACK_SETUP.md](SLACK_SETUP.md) y usa [slack/manifest.yaml](slack/manifest.yaml).
El bot se conecta por Socket Mode y responde en hilos sin necesitar menciones.
Incluye contexto del hilo, archivos adjuntos, respuesta dividida en mensajes,
deduplicación de eventos y límite de concurrencia. Escribe `cancelar` o `cancel`
en el hilo para cancelar el trabajo activo. Los adjuntos se descargan en el
workspace; si ejecutas bot y API por separado, deben compartir esa ruta.

## Desarrollo

```bash
.venv/bin/python -m pip install -r api/requirements-dev.txt
.venv/bin/python -m pytest -q api
bash -n run-harness.sh entrypoint.sh
podman build -t gemini_cli_remote .
```

Las pruebas son locales y sin conexión a Google o Slack. Hay pruebas de
comandos, autenticación, errores, cancelación de grupos de procesos, reintentos,
cron, formato de respuestas, arranque sin Slack y puertos ocupados. GitHub Actions
ejecuta la suite con Python 3.12 en cada push y pull request.

La API permite ejecutar herramientas y comandos y no tiene autenticación HTTP.
Mantenla en loopback y accede mediante SSH o una red privada con control de
acceso. `workdir` selecciona el directorio de trabajo; no es una sandbox.
Guarda claves y tokens en `.env` o un gestor de secretos y nunca los subas a Git.

Referencia oficial: [Gemini CLI headless](https://geminicli.com/docs/cli/headless/).
