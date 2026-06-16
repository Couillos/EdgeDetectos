# Stage 1: build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/webapp/frontend
COPY webapp/frontend/package*.json ./
RUN npm ci
COPY webapp/frontend/ ./
RUN npm run build

# Stage 2: backend with built frontend
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Copy built frontend assets into webapp/frontend/dist
COPY --from=frontend-builder /app/webapp/frontend/dist /app/webapp/frontend/dist

EXPOSE 8000
