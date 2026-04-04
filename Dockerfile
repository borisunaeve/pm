# 1. Build the Node/Next.js frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY ./frontend/package.json ./frontend/package-lock.json ./
RUN npm ci
COPY ./frontend ./
RUN npm run build

# 2. Build the python slim image
FROM python:3.11-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

# Set working directory
WORKDIR /app

# We keep the container simple for development
COPY ./backend/requirements.txt /app/backend/requirements.txt

# Install python dependencies via uv
RUN uv pip install --system -r /app/backend/requirements.txt

# Now copy the backend directory
COPY ./backend /app/backend

# Copy the static Next.js frontend build from the builder stage
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Expose port
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
