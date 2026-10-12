# Single deployable: Vite build is served by Django (WhiteNoise) next to /api.
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /web/dist ./frontend_dist
ENV PORT=8000
CMD gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3 --threads 4 --timeout 60
