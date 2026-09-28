#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_NAME="${PROJECT_NAME:-bitmanga-local}"

ensure_docker_running() {
  if docker info >/dev/null 2>&1; then
    echo "Docker daemon is running."
    return 0
  fi

  echo "Docker daemon is not running. Attempting to start it..."

  if command -v sudo >/dev/null 2>&1; then
    sudo service docker start >/dev/null 2>&1 || sudo systemctl start docker >/dev/null 2>&1 || true
  fi

  if command -v dockerd >/dev/null 2>&1; then
    dockerd >/tmp/bitmanga-dockerd.log 2>&1 &
  fi

  for _ in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then
      echo "Docker daemon is now running."
      return 0
    fi
    sleep 1
  done

  echo "Docker daemon could not be started. Please start Docker and rerun ./start.sh." >&2
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

repair_stale_state() {
  echo "Resetting only the app containers; the Postgres volume is preserved."
  "${compose_cmd[@]}" stop || true

  docker ps -aq --filter "name=${PROJECT_NAME}-nextjs-1" | xargs -r docker rm -f >/dev/null 2>&1 || true
  docker ps -aq --filter "name=${PROJECT_NAME}-backend-api-1" | xargs -r docker rm -f >/dev/null 2>&1 || true
  docker ps -aq --filter "name=${PROJECT_NAME}-db-1" | xargs -r docker rm -f >/dev/null 2>&1 || true

  docker ps -aq --filter "name=${PROJECT_NAME}-nextjs" | xargs -r docker rm -f >/dev/null 2>&1 || true
  docker ps -aq --filter "name=${PROJECT_NAME}-backend-api" | xargs -r docker rm -f >/dev/null 2>&1 || true
  docker ps -aq --filter "name=${PROJECT_NAME}-db" | xargs -r docker rm -f >/dev/null 2>&1 || true

  "${compose_cmd[@]}" rm -f db nextjs backend-api || true
}

start_stack() {
  echo "Starting BIT.MANGA with the normal build path..."
  if ! "${compose_cmd[@]}" up -d --build; then
    echo "Normal startup failed. Retrying with the legacy Docker builder and a clean container state."
    repair_stale_state
    DOCKER_BUILDKIT=0 "${compose_cmd[@]}" up -d --build
  fi
}

ensure_builder
repair_stale_state
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
