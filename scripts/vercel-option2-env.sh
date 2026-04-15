#!/usr/bin/env bash
# Option 2: set API_KEY on the Flask Vercel project + API_PROXY_TARGET + NEXT_PUBLIC_API_KEY on the Next project.
#
# Rejects literal placeholders (YOUR_KEY, YOUR_API_BASE) and refuses to run if repo root and web/
# are linked to the same Vercel project (two-project deploy requires two links).
#
# Prerequisites: npx vercel login; vercel link from repo root (API) and from web/ (Next dashboard).
#
# Usage (from repo root):
#   chmod +x scripts/vercel-option2-env.sh
#   ./scripts/vercel-option2-env.sh 'https://quantum-hybrid-portfolio.vercel.app' --dry-run
#   ./scripts/vercel-option2-env.sh 'https://your-api.vercel.app' --apply
#
# Remove bad placeholder values in the dashboard first, or:
#   ./scripts/vercel-option2-env.sh --remove-wrong-env production
#   (runs vercel env rm for the three names in each linked directory — confirm when prompted)
#
# If --apply fails because web/ is linked to the same project as the API:
#   ./scripts/vercel-option2-env.sh --reset-web-link
#   then: cd web && npx vercel link   (choose the Next.js / dashboard project, e.g. …-5ch5)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"
VERCEL_BIN="${VERCEL_BIN:-npx --yes vercel@latest}"

_read_project_id() {
  local f="$1/.vercel/project.json"
  if [[ ! -f "$f" ]]; then
    echo ""
    return 0
  fi
  if command -v jq >/dev/null 2>&1; then
    jq -r '.projectId // empty' "$f" 2>/dev/null || true
  else
    sed -n 's/.*"projectId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" | head -1
  fi
}

_validate_not_placeholder() {
  local kind="$1"
  local val="$2"
  case "$val" in
    YOUR_KEY|YOUR_API_BASE|"https://YOUR_API_BASE"|"http://YOUR_API_BASE")
      echo "error: $kind looks like a documentation placeholder ($val). Use a real openssl-generated key and your real API https URL." >&2
      exit 1
      ;;
  esac
  if [[ "$kind" == "API_BASE" ]]; then
    if [[ "$val" != https://* ]]; then
      echo "error: API base must start with https:// (got: $val)" >&2
      exit 1
    fi
    if [[ "$val" == *localhost* || "$val" == *127.0.0.1* ]]; then
      echo "error: API base must be the public Vercel API hostname, not localhost/127.0.0.1" >&2
      exit 1
    fi
  fi
}

if [[ "${1:-}" == "--reset-web-link" ]]; then
  if [[ ! -d "$WEB/.vercel" ]]; then
    echo "Nothing to reset: $WEB/.vercel is missing. Run: cd $WEB && $VERCEL_BIN link"
    exit 0
  fi
  rm -rf "$WEB/.vercel"
  echo "Removed $WEB/.vercel"
  echo "Next (interactive):"
  echo "  cd $WEB && $VERCEL_BIN link"
  echo "Link to your **Next.js dashboard** project (different from the Flask API project), e.g. quantum-hybrid-portfolio-5ch5."
  echo "Then from repo root: ./scripts/vercel-option2-env.sh 'https://<your-api>.vercel.app' --apply"
  exit 0
fi

if [[ "${1:-}" == "--remove-wrong-env" ]]; then
  ENV_TARGET="${2:-production}"
  echo "Removing API_KEY (root), API_PROXY_TARGET + NEXT_PUBLIC_API_KEY (web/) for environment: $ENV_TARGET"
  echo "You may need to confirm each removal in the terminal."
  if [[ -d "$ROOT/.vercel" ]]; then
    ( cd "$ROOT" && $VERCEL_BIN env rm API_KEY "$ENV_TARGET" ) || true
  fi
  if [[ -d "$WEB/.vercel" ]]; then
    ( cd "$WEB" && $VERCEL_BIN env rm API_PROXY_TARGET "$ENV_TARGET" ) || true
    ( cd "$WEB" && $VERCEL_BIN env rm NEXT_PUBLIC_API_KEY "$ENV_TARGET" ) || true
  fi
  echo "Done. Re-run with a real API URL and --apply."
  exit 0
fi

API_BASE="${1:-}"
DRY_RUN=0
APPLY=0
for arg in "${@:2}"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --apply) APPLY=1 ;;
  esac
done

if [[ -z "$API_BASE" || "$API_BASE" == --* ]]; then
  echo "usage: $0 'https://<api>.vercel.app' [--dry-run|--apply]" >&2
  echo "       $0 --remove-wrong-env [production|preview]" >&2
  echo "       $0 --reset-web-link   # delete web/.vercel so you can vercel link web/ to the Next project" >&2
  exit 1
fi

API_BASE="${API_BASE%/}"
_validate_not_placeholder "API_BASE" "$API_BASE"

KEY="$(openssl rand -hex 32)"

ROOT_ID="$(_read_project_id "$ROOT")"
WEB_ID="$(_read_project_id "$WEB")"

if [[ -z "$ROOT_ID" ]]; then
  echo "error: missing $ROOT/.vercel — run: cd $ROOT && $VERCEL_BIN link  (link to the Flask/API project)" >&2
  exit 1
fi
if [[ -z "$WEB_ID" ]]; then
  echo "error: missing $WEB/.vercel — run: cd $WEB && $VERCEL_BIN link  (link to the Next.js project, not the API)" >&2
  exit 1
fi
if [[ "$ROOT_ID" == "$WEB_ID" ]]; then
  echo "error: repo root and web/ point to the same Vercel projectId ($ROOT_ID)." >&2
  echo "  Option 2 needs two Vercel projects (API vs Next)." >&2
  echo "  Run: $0 --reset-web-link" >&2
  echo "  then: cd $WEB && $VERCEL_BIN link   (select the dashboard / Next project, not the API)" >&2
  exit 1
fi

echo ""
echo "=== Vercel projectIds (must differ) ==="
echo "  API (repo root): $ROOT_ID"
echo "  Next (web/):     $WEB_ID"
echo ""
echo "=== Generated shared secret (API_KEY = NEXT_PUBLIC_API_KEY) ==="
echo "$KEY"
echo ""
echo "=== API_PROXY_TARGET (Next project) ==="
echo "$API_BASE"
echo ""

if [[ "$DRY_RUN" -eq 1 ]]; then
  APPLY=0
fi

run_env_add() {
  local dir="$1"
  local name="$2"
  local value="$3"
  local env="${4:-production}"
  ( cd "$dir" && printf '%s' "$value" | $VERCEL_BIN env add "$name" "$env" )
}

if [[ "$APPLY" -eq 1 ]]; then
  echo "Adding API_KEY to API project (repo root)..."
  run_env_add "$ROOT" "API_KEY" "$KEY" production
  echo "Adding API_PROXY_TARGET to Next project (web/)..."
  run_env_add "$WEB" "API_PROXY_TARGET" "$API_BASE" production
  echo "Adding NEXT_PUBLIC_API_KEY to Next project (web/)..."
  run_env_add "$WEB" "NEXT_PUBLIC_API_KEY" "$KEY" production
  echo ""
  echo "Done. Vercel may warn that NEXT_PUBLIC_* is visible in the browser — expected for X-API-Key in this app."
  echo "Redeploy both projects (Deployments → Redeploy or push to main)."
  exit 0
fi

echo "=== Commands (copy-paste with real values above), or run: $0 '$API_BASE' --apply ==="
echo ""
echo "cd \"$ROOT\""
echo "printf '%s' '$KEY' | $VERCEL_BIN env add API_KEY production"
echo ""
echo "cd \"$WEB\""
echo "printf '%s' '$API_BASE' | $VERCEL_BIN env add API_PROXY_TARGET production"
echo "printf '%s' '$KEY' | $VERCEL_BIN env add NEXT_PUBLIC_API_KEY production"
echo ""
