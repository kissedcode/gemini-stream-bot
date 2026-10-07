FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/kissedcode/gemini-stream-bot"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Luxembourg

# Non-root user
RUN groupadd --system bot && useradd --system --gid bot --home /app bot

WORKDIR /app

# Deps layer (cache-friendly)
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App layer
COPY src/ ./src/

# No persistent data: the bot is stateless
RUN chown -R bot:bot /app

USER bot

CMD ["python", "-m", "src.main"]
