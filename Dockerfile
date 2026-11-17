FROM node:22-bookworm-slim AS gemini
ARG GEMINI_VERSION=0.68.0
RUN npm install --global --loglevel=error "@google/gemini-cli@${GEMINI_VERSION}"

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    GEMINI_WORKDIR=/workspace \
    HARNESS_HOST=0.0.0.0 \
    HARNESS_PORT=8080
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git cron libatomic1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=gemini /usr/local/bin/node /usr/local/bin/node
COPY --from=gemini /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/@google/gemini-cli/bundle/gemini.js /usr/local/bin/gemini \
    && ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && gemini --version
WORKDIR /app
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ ./
COPY GEMINI.md ./GEMINI.md
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /workspace
WORKDIR /workspace
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["serve-all"]
