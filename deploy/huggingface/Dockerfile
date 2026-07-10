# Single-service image for a Hugging Face Docker Space: builds the React
# frontend, then serves it via nginx while proxying API paths to a FastAPI
# backend process running in the same container. Mirrors deploy/railway's
# combined image, adapted for HF Spaces' runtime which always executes the
# container as uid 1000 (regardless of any USER directive), so nginx's
# normally root-owned paths are reassigned before dropping privileges.

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

RUN mkdir -p /var/lib/nginx/body /var/cache/nginx /var/log/nginx /run \
    && chown -R 1000:1000 /app /etc/nginx /var/lib/nginx /var/cache/nginx /var/log/nginx /run

USER 1000
ENV HOME=/home/user

EXPOSE 8080
ENTRYPOINT ["/app/docker/entrypoint.sh"]
