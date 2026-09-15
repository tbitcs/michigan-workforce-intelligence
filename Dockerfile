# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.10.0 AS uv
FROM docker:29-cli AS dockercli
FROM python:3.12-slim-trixie AS runtime
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
WORKDIR /app
# Apply published distribution fixes in addition to the base-image release.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra mcp --no-install-project
COPY src ./src
COPY config ./config
COPY deploy ./deploy
COPY README.md ./
COPY LICENSE LICENSING.md THIRD_PARTY_NOTICES.md ./
COPY LICENSES ./LICENSES
RUN uv sync --frozen --no-dev --extra mcp && useradd --uid 10001 --create-home mijobs \
    && mkdir -p /data/artifacts /confidential && chown -R mijobs:mijobs /data /confidential
USER mijobs
CMD ["python", "-c", "from mijobs.mcp_server import serve_http; serve_http()"]

FROM runtime AS mcp-stdio
LABEL com.docker.mcp.packaging.version="v1.0" \
      io.modelcontextprotocol.server.name="michigan-workforce-intelligence"
ENTRYPOINT ["mijobs-mcp"]
CMD []

FROM runtime AS ci
USER root
RUN apt-get update && apt-get install -y --no-install-recommends bash curl ca-certificates make git \
    && rm -rf /var/lib/apt/lists/*
ARG RTK_VERSION=0.49.0
RUN set -eu; arch="$(uname -m)"; \
    case "$arch" in x86_64) target=x86_64-unknown-linux-musl;; aarch64) target=aarch64-unknown-linux-gnu;; *) exit 1;; esac; \
    base="https://github.com/rtk-ai/rtk/releases/download/v${RTK_VERSION}"; \
    curl -fsSL "$base/rtk-${target}.tar.gz" -o /tmp/rtk.tar.gz; \
    curl -fsSL "$base/checksums.txt" -o /tmp/checksums.txt; \
    hash="$(awk -v file="rtk-${target}.tar.gz" '$2 == file || $2 == "*"file {print $1}' /tmp/checksums.txt)"; \
    test -n "$hash"; echo "$hash  /tmp/rtk.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/rtk.tar.gz -C /usr/local/bin rtk; rtk gain; \
    rm /tmp/rtk.tar.gz /tmp/checksums.txt
RUN uv sync --frozen --extra mcp --extra dev
COPY tests ./tests
COPY scripts ./scripts
COPY specs ./specs
COPY .specify ./.specify
COPY .rtk ./.rtk
COPY AGENTS.md RTK.md Makefile ./
RUN chown -R mijobs:mijobs /app
USER mijobs
ENV STRICT_TOOLS=1
CMD ["make", "ci-local"]

FROM runtime AS reports
USER root
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen --no-dev --extra mcp --extra reports
ENV MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /workspace
ENTRYPOINT []
CMD ["python", "scripts/build_reports.py", "--help"]

FROM runtime AS manager
USER root
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
ENV MIJOBS_WORKSPACE=/workspace
ENTRYPOINT ["mijobs-tui"]
CMD []
