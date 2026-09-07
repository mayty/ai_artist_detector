# agent-name: ai-artist-detector
FROM claude-agent

ARG HOST_UID
ARG HOST_GID

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

ENV UV_PROJECT_ENVIRONMENT=/home/ubuntu/.uv-env
ENV UV_CACHE_DIR=/home/ubuntu/.uv-cache
ENV PATH=/home/ubuntu/.local/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir -p /home/ubuntu/.uv-cache && \
    apt-get update && apt-get install -y --no-install-recommends make sqlite3 && \
    rm -rf /var/lib/apt/lists/* && \
    chown -R $HOST_UID:$HOST_GID /home/ubuntu/.uv-cache

# agent-run-args: -v /home/ubuntu/.uv-cache
