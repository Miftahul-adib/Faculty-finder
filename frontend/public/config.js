// Runtime config — overwritten at container start (see docker-entrypoint.sh)
// with the BACKEND_URL environment variable. In local `npm run dev` this
// default (pointing at the backend's default port) is used as-is.
window.__BACKEND_URL__ = "http://localhost:8000";
