FROM python:3.14.2-alpine3.22 AS base

ARG UV_VERSION=0.9.27
ARG UV_NO_MANAGED_PYTHON=1
ENV PYTHONOPTIMIZE=2

RUN apk update && apk upgrade && apk add --no-cache curl make gcc g++ libc-dev musl musl-dev

RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock /app/
COPY ai_artist_detector /app/ai_artist_detector/
WORKDIR /app

RUN uv export \
      --format requirements.txt \
      --no-dev \
      --no-editable \
      --frozen \
      --no-hashes \
      --no-annotate \
      --no-emit-project \
      --output-file=requirements.txt

RUN uv build --wheel
RUN pip install -r requirements.txt

FROM python:3.14.2-alpine3.22

ENV PYTHONOPTIMIZE=2
ENV SERVER_PORT=8080

RUN apk update && apk upgrade && apk add --no-cache curl sqlite
ENV PATH="/root/.local/bin:${PATH}"

COPY --from=redis:8.4.0-alpine3.22 /usr/local/bin/redis-cli /usr/local/bin/redis-cli

WORKDIR /app

COPY --from=base /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /app/dist/ /tmp/build/

RUN pip install /tmp/build/*.whl && rm -rf /tmp/build
COPY config/uvicorn_logging.ini /app/config/uvicorn_logging.ini

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --start-interval=100ms --retries=3 \
  CMD curl -f http://localhost:${SERVER_PORT}/ping || exit 1

CMD aiad workers api -p ${SERVER_PORT}
