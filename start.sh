#!/usr/bin/env bash
# Copilot instruction for this repository:
# When a user asks to "run the website", "open the website", or "start the app",
# do the following from the repo root:
#   1. Check that Docker is running.
#   2. Run ./start.sh (do not use plain docker compose up directly if Docker state is stale).
#   3. This script preserves the PostgreSQL volume and cleans stale app containers safely.
#   4. Wait until the frontend and API both respond successfully.
#   5. Open http://localhost:3000 in the browser.
#   6. If Docker is broken or stale, prefer the safe startup path in scripts/start-local.sh,
#      not destructive resets like docker compose down -v.
#   7. If a startup issue occurs, document it in bug-fix-log.md with symptoms, root cause,
#      remediation, and verification.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT_DIR/scripts/start-local.sh" "$@"
