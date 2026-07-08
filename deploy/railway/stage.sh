#!/bin/bash
# Regenerates the build context this Dockerfile expects (backend/, frontend/,
# requirements.txt) as copies of the real source, since Railway's single
# combined-service image needs both in one build context alongside this
# Dockerfile. Run from anywhere; paths are absolute to the repo.
set -e
ROOT=F:/Faculty-finder
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$HERE/backend" "$HERE/frontend/src" "$HERE/frontend/public"
cp "$ROOT"/backend/*.py "$HERE/backend/"
cp "$ROOT/requirements.txt" "$HERE/requirements.txt"
cp -r "$ROOT"/frontend/src/. "$HERE/frontend/src/"
cp -r "$ROOT"/frontend/public/. "$HERE/frontend/public/"
cp "$ROOT/frontend/package.json" "$ROOT/frontend/package-lock.json" "$ROOT/frontend/vite.config.js" "$ROOT/frontend/index.html" "$HERE/frontend/"

echo "Staged. Deploy with the Railway MCP 'deploy' tool, path=$HERE"
