# ==============================================================================
# OpsForge Single-Link Production Dockerfile for Render Deployment
# Stage 1: Build React Frontend
# Stage 2: Serve API + Built Static Frontend via FastAPI Uvicorn on $PORT
# ==============================================================================

# ── Stage 1: Build React Frontend ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy frontend source code
COPY frontend/ ./

# Build frontend with relative API base URL so API calls route directly to same host
ENV VITE_API_BASE_URL=""
RUN npm run build

# ── Stage 2: Python Backend + Static Files ────────────────────────────────────
FROM python:3.11-slim AS runner
WORKDIR /app

# Install system utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY backend/app ./app

# Copy built frontend dist from Stage 1 into backend static folder
COPY --from=frontend-builder /frontend/dist ./static

# Render injects PORT environment variable (default 10000)
ENV PORT=10000
EXPOSE 10000

# Run Uvicorn server binding to 0.0.0.0:$PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
