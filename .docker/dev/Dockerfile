FROM python:3.14.2-alpine3.22 AS base

ARG UV_VERSION=0.9.27
ENV SERVER_PORT=8080
ENV UV_PYTHON=/usr/local/bin/python
ENV UV_LINK_MODE=copy

RUN apk update && apk upgrade && apk add --no-cache curl make gcc g++ libc-dev musl musl-dev

RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

RUN uv venv --no-project

ENV VIRTUAL_ENV='/app/.venv'
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --start-interval=100ms --retries=3 \
  CMD curl -f http://localhost:${SERVER_PORT}/ping || exit 1

COPY .docker/dev/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ai-artist-detector workers api-dev -p ${SERVER_PORT}
