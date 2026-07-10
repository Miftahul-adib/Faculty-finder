#!/bin/bash
set -e

# Railway injects PORT dynamically; nginx must listen on it. The backend
# stays on a fixed internal port and is reached only via nginx's proxy.
PORT="${PORT:-8080}"
sed "s/__PORT__/${PORT}/" /app/docker/nginx.conf.template > /etc/nginx/conf.d/default.conf

cat > /app/frontend/dist/config.js <<'EOF'
window.__BACKEND_URL__ = "";
EOF

cd /app/backend
uvicorn main:app --host 127.0.0.1 --port 8000 &

echo "Waiting for backend..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

exec nginx -g "daemon off;"
