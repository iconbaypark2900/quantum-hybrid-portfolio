#!/usr/bin/env bash
# Deploy the Python/Flask API project to Vercel (production) from repo root.
# Prerequisite: run `npx vercel link` once in this directory and connect the API project.
#
# Usage:
#   ./scripts/vercel-deploy-api.sh
#   VERCEL_BIN=vercel ./scripts/vercel-deploy-api.sh   # use global vercel CLI
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERCEL_BIN="${VERCEL_BIN:-npx --yes vercel@latest}"

echo "Deploying API from: $ROOT"
exec $VERCEL_BIN deploy --prod "$@"
