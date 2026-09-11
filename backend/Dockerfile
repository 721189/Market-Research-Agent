FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy source code
COPY backend/ /app/backend

# Set Python path so 'backend.module' imports work
ENV PYTHONPATH=/app
