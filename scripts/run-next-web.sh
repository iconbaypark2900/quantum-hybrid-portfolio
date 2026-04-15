#!/usr/bin/env bash
# Run the Next.js app in web/ on a port in the 3000s (default 3042) so it does not
# clash with the CRA dashboard (3000) or Flask (5000).
#
# Usage:
#   ./scripts/run-next-web.sh
#   NEXT_WEB_PORT=3080 ./scripts/run-next-web.sh
#
# Typical parallel setup:
#   Terminal 1: python -m api              # :5000
#   Terminal 2: cd frontend && npm start       # :3000
#   Terminal 3: ./scripts/run-next-web.sh      # :3042 (this script)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"
PORT="${NEXT_WEB_PORT:-3042}"
NEXT_BIN="$WEB/node_modules/.bin/next"

if [[ ! -x "$NEXT_BIN" ]]; then
  echo "error: Next.js not found at $NEXT_BIN" >&2
  echo "  From repo root: cd web && npm install" >&2
  exit 1
fi

cd "$WEB"
exec "$NEXT_BIN" dev -p "$PORT"
