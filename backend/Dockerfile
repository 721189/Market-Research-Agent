FROM python:3.11-slim@sha256:773ecb113708e33465efb773cb2d2c1cb73f1d24efec6aef9e36eb69502b4ed3

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user
RUN groupadd -r marketai && useradd -r -g marketai -d /app marketai

# Install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy source code and set ownership
COPY --chown=marketai:marketai backend/ /app/backend

ENV PYTHONPATH=/app

USER marketai

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1
