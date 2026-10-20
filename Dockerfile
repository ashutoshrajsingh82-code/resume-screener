
# syntax=docker/dockerfile:1

# ---------- Frontend: build JSX -> dist/ ----------
FROM node:22-slim AS frontend-build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


# ---------- Frontend: serve with Nginx ----------
FROM nginx:alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html

EXPOSE 80


# ---------- Backend: FastAPI + Sentence Transformers ----------
FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache

WORKDIR /app

# Install CPU-only PyTorch and application dependencies
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
       torch \
       --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Download the embedding model during image build
ARG MODEL_NAME=all-MiniLM-L6-v2
ENV MODEL_NAME=${MODEL_NAME}

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}')"

# Copy backend source files
COPY backend_api.py ranker.py scoring.py document_processing.py ./

# Create a non-root user and configure permissions
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app /opt/hf-cache

USER appuser

# Frontend origins
ENV ALLOWED_ORIGINS="http://127.0.0.1:8010,http://localhost:8010"

# Internal backend port (host port 8001 is configured in Compose)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# Start FastAPI
CMD ["uvicorn", "backend_api:app", "--host", "0.0.0.0", "--port", "8000"]
