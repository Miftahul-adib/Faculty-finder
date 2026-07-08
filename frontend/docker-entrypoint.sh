#!/bin/sh
set -e

# Writes the browser-reachable backend URL into config.js at container start,
# since Vite bakes VITE_ env vars in at build time but BACKEND_URL needs to
# stay a runtime setting (same env var name docker-compose already used for
# the old Streamlit frontend).
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
cat > /usr/share/nginx/html/config.js <<EOF
window.__BACKEND_URL__ = "${BACKEND_URL}";
EOF

exec nginx -g "daemon off;"
