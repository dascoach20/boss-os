# syntax=docker/dockerfile:1
# ============================================================================
# Boss OS - container image
# "Brain" = Claude Code CLI (npm global). FastAPI app served by uvicorn.
# Code tree is immutable; ALL mutable state lives on the /data volume and the
# Claude auth volume (~/.claude). Pattern adapted from Hermes Agent's Dockerfile
# (Node-from-official-image, immutable-code + writable-data split, tini PID 1).
# ============================================================================

# ---------- Stage 1: Node 22 LTS source ----------
# Copy node/npm/npx from the official image instead of apt (Debian's nodejs lags LTS).
FROM node:22-bookworm-slim AS node_source

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim

# OCI image labels: Docker Manager (Hostinger) + registry đọc để hiện cột "Guide"
# (Documentation / Quick start / Source). Trỏ về docs trên GitHub.
LABEL org.opencontainers.image.title="Boss OS" \
      org.opencontainers.image.description="AI operating layer: chat + voice + second brain + tự động hoá, xây trên CLI của nhà cung cấp AI (Claude Code, ChatGPT/Codex)." \
      org.opencontainers.image.url="https://github.com/pham-dai-2000/boss-os" \
      org.opencontainers.image.source="https://github.com/pham-dai-2000/boss-os" \
      org.opencontainers.image.documentation="https://github.com/pham-dai-2000/boss-os/blob/main/docs/README.md" \
      org.opencontainers.image.licenses="MIT" \
      com.hostinger.documentation="https://github.com/pham-dai-2000/boss-os/blob/main/docs/README.md" \
      com.hostinger.quickstart="https://github.com/pham-dai-2000/boss-os/blob/main/QUICKSTART.md"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: ca-certs (TLS), git (Claude tools), ripgrep (fast search used by
# Claude's Grep), ffmpeg (edge-tts mp3), curl, tini (PID-1 reaper for the node
# subprocesses Claude spawns).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git ripgrep ffmpeg tini \
    && rm -rf /var/lib/apt/lists/*

# Node 22 LTS from stage 1 (npm/npx are symlinks → recreate on PATH).
COPY --from=node_source /usr/local/bin/node /usr/local/bin/node
COPY --from=node_source /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# The brain: Claude Code CLI, installed globally. Overridable build-arg.
ARG CLAUDE_CLI_VERSION=latest
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}" \
    && npm cache clean --force \
    && claude --version

# Codex CLI - cho provider ChatGPT subscription (OpenAI OAuth). BEST-EFFORT: lỗi cài KHÔNG làm hỏng
# build (Claude vẫn chạy). Đăng nhập 1 lần bằng `codex login` trong terminal (token lưu ở volume .codex).
RUN (npm install -g @openai/codex && npm cache clean --force && codex --version) \
    || echo "[build] codex cài KHÔNG thành công - provider ChatGPT subscription sẽ không dùng được (các provider khác vẫn chạy)."

WORKDIR /app

# Layer-cached Python deps (copy requirements first so app changes don't re-pip).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App source.
COPY . .

# Non-root runtime user. Code stays root-owned + read-only; state on volumes.
RUN useradd -u 10001 -m -d /home/boss boss \
    && mkdir -p /data/state /data/vault /brains /home/boss/.claude /home/boss/.codex \
    && chown -R boss:boss /data /brains /home/boss

# Writable state under /data; ALL second brains under /brains (mount riêng → git-backup được).
ENV BOSS_HOST=0.0.0.0 \
    BOSS_PORT=7777 \
    BOSS_STATE_DIR=/data/state \
    BRAIN_PATH=/data/brain \
    BRAINS_DIR=/brains \
    OBSIDIAN_VAULT_PATH=/data/vault \
    CLAUDE_CWD=/app \
    HOME=/home/boss \
    PATH=/usr/local/bin:$PATH

USER boss

# Persist state (/data) + brains (/brains) + Claude auth + Codex auth (login ChatGPT).
VOLUME ["/data", "/brains", "/home/boss/.claude", "/home/boss/.codex"]

EXPOSE 7777

# Healthcheck hits the public /health endpoint with stdlib only (no curl).
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.getenv('BOSS_PORT','7777')+'/health',timeout=4).status==200 else 1)" || exit 1

# tini reaps node subprocesses. uvicorn launched with --app-dir server because
# main.py uses the "main:app" import string and `from claude_cli import ...`.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "python -m uvicorn main:app --app-dir server --host ${BOSS_HOST} --port ${BOSS_PORT}"]
