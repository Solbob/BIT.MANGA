#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_NAME="${PROJECT_NAME:-bitmanga-local}"

start_docker_desktop() {
  local -a desktop_paths=()
  local desktop_exe
  local windows_exe

  if [[ -n "${ProgramW6432:-}" ]]; then
    desktop_paths+=("$(cygpath -u "$ProgramW6432")/Docker/Docker/Docker Desktop.exe")
  fi
  if [[ -n "${ProgramFiles:-}" ]]; then
    desktop_paths+=("$(cygpath -u "$ProgramFiles")/Docker/Docker/Docker Desktop.exe")
  fi
  if [[ -n "${LOCALAPPDATA:-}" ]]; then
    desktop_paths+=("$(cygpath -u "$LOCALAPPDATA")/Programs/DockerDesktop/Docker Desktop.exe")
  fi
  desktop_paths+=("/c/Program Files/Docker/Docker/Docker Desktop.exe")

  for desktop_exe in "${desktop_paths[@]}"; do
    if [[ -f "$desktop_exe" ]]; then
      if ! command -v powershell.exe >/dev/null 2>&1; then
        echo "Could not launch Docker Desktop: powershell.exe was not found." >&2
        return 1
      fi

      windows_exe="$(cygpath -w "$desktop_exe")"
      if ! powershell.exe -NoProfile -NonInteractive -Command \
        "Start-Process -FilePath '$windows_exe' -ErrorAction Stop" >/dev/null; then
        echo "Could not launch Docker Desktop at: $windows_exe" >&2
        return 1
      fi

      echo "Started Docker Desktop. Waiting for its engine to become ready..."
      return 0
    fi
  done

  echo "Could not find Docker Desktop. Install it or set it up at the default Windows location, then rerun ./start.sh." >&2
  return 1
}

ensure_docker_running() {
  if docker info >/dev/null 2>&1; then
    echo "Docker daemon is running."
    return 0
  fi

  echo "Docker daemon is not running. Attempting to start it..."

  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      start_docker_desktop || exit 1
      ;;
    *)
      if command -v sudo >/dev/null 2>&1; then
        sudo service docker start >/dev/null 2>&1 || sudo systemctl start docker >/dev/null 2>&1 || true
      fi

      if command -v dockerd >/dev/null 2>&1; then
        dockerd >/tmp/bitmanga-dockerd.log 2>&1 &
      fi
      ;;
  esac

  for _ in $(seq 1 120); do
    if docker info >/dev/null 2>&1; then
      echo "Docker daemon is now running."
      return 0
    fi
    sleep 1
  done

  echo "Docker daemon did not become ready. Check Docker Desktop for startup or setup errors, then rerun ./start.sh." >&2
  exit 1
}

ensure_docker_running

compose_cmd=(docker compose -p "$PROJECT_NAME")
compose_cmd+=(-f docker-compose.yaml)

if [[ -n "${CODESPACES:-}" || -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" || -n "${CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]]; then
  compose_cmd+=(-f docker-compose.codespaces.yaml)
  echo "Codespaces detected: enabling host.docker.internal override."
fi

ensure_builder() {
  local builder_name="bitmanga-fresh"

  if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
    echo "Creating fresh Docker BuildKit builder: $builder_name"
    docker buildx create --name "$builder_name" --driver docker-container --use --bootstrap >/dev/null 2>&1 || true
  fi

  if docker buildx inspect "$builder_name" >/dev/null 2>&1; then
    docker buildx use "$builder_name" >/dev/null 2>&1 || true
  fi
}

STACK_HAS_CONTAINERS=false

stop_existing_stack() {
  local existing_containers
  local running_containers
  existing_containers="$("${compose_cmd[@]}" ps --all -q)"
  running_containers="$("${compose_cmd[@]}" ps -q)"

  if [[ -n "$existing_containers" ]]; then
    STACK_HAS_CONTAINERS=true
  fi

  if [[ -z "$running_containers" ]]; then
    echo "No running BIT.MANGA services to stop."
    return
  fi

  echo "Stopping existing BIT.MANGA services before starting them again."
  "${compose_cmd[@]}" stop || true
}

repair_stale_state() {
  echo "Removing only stale app containers; the PostgreSQL container and volume are preserved."
  "${compose_cmd[@]}" stop || true
  "${compose_cmd[@]}" rm -f nextjs backend-api || true
}

start_stack() {
  if [[ "$STACK_HAS_CONTAINERS" == true ]]; then
    echo "Restarting the existing BIT.MANGA services without rebuilding images..."
    if "${compose_cmd[@]}" up -d; then
      return
    fi
    echo "Could not restart the existing stack. Falling back to a rebuild."
  fi

  echo "Starting BIT.MANGA with the normal build path..."
  if ! "${compose_cmd[@]}" up -d --build; then
    echo "Normal startup failed. Retrying with the legacy Docker builder and a clean container state."
    repair_stale_state
    DOCKER_BUILDKIT=0 "${compose_cmd[@]}" up -d --build
  fi
}

ensure_builder
stop_existing_stack
start_stack

echo "--- service status ---"
"${compose_cmd[@]}" ps

for _ in {1..60}; do
  if curl -fsS --max-time 5 http://localhost:8000/docs >/dev/null 2>&1 && \
     curl -fsS --max-time 5 http://localhost:3000 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "--- frontend ---"
curl -I --max-time 20 http://localhost:3000

echo "--- api ---"
curl -I --max-time 20 http://localhost:8000/docs

echo
echo "DBeaver (PostgreSQL) connection:"
echo "  Host: localhost"
echo "  Port: 5555"
echo "  Database: advcompro"
echo "  Username: temp"
echo "  Password: temp"
echo "To view accounts in DBeaver, expand Databases > advcompro > Schemas > public > Tables,"
echo "then double-click users. Right-click the table and choose Refresh to reload its rows."