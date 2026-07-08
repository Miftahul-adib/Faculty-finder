# Single-service image for Railway: builds the React frontend, then serves
# it via nginx while proxying API paths to a FastAPI backend process
# running in the same container (kept to one service to fit the project's
# service-count limit; MySQL is a separate Railway-managed service reached
# over the private network).

FROM node:20-slim AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY docker/entrypoint.sh docker/nginx.conf.template ./docker/
RUN rm -f /etc/nginx/sites-enabled/default && chmod +x ./docker/entrypoint.sh

COPY --from=frontend-build /fe/dist ./frontend/dist

EXPOSE 8080
ENTRYPOINT ["/app/docker/entrypoint.sh"]
