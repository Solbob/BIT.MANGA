# Bug Fix Log

> **Copilot instruction:** When diagnosing a recurring or new bug in BIT.MANGA, read this log before changing code. Compare the symptoms with earlier entries and check the relevant app/container logs. After fixing a new bug, append a dated entry with its symptoms, root cause, exact remediation, and verification. Preserve older entries, do not include secrets, and never recommend deleting the PostgreSQL volume as a routine fix.

## 2026-09-27 — Local Compose startup/build failure

**Symptoms**

- `docker compose -p bitmanga-local up -d --build` exited during image export with `failed to get reader from content store: content digest ... not found`.
- A no-cache retry failed with `parent snapshot ... does not exist`.
- Starting the prebuilt app then failed with `RWLayer ... is unexpectedly nil` for the existing PostgreSQL container.

**Cause**

The Docker/BuildKit layer and snapshot store was inconsistent, and the stopped PostgreSQL container had a broken writable layer. These were local Docker runtime-state problems, not application or database-schema failures. The PostgreSQL named volume remained intact.

**Fix**

1. If BuildKit reports missing content digests or parent snapshots, build both images with Docker's legacy builder:

   ```bash
   DOCKER_BUILDKIT=0 docker build --no-cache -t bitmanga-local-backend-api:latest ./backend-api
   DOCKER_BUILDKIT=0 docker build --no-cache -t bitmanga-local-nextjs:latest ./nextjs
   ```

2. If the existing database container specifically reports `RWLayer ... is unexpectedly nil`, remove and recreate only that container. This preserves its named data volume:

   ```bash
   docker compose -p bitmanga-local stop
   docker compose -p bitmanga-local rm -f db
   docker compose -p bitmanga-local up -d --no-build
   ```

3. Verify services with `docker compose -p bitmanga-local ps`; PostgreSQL should be healthy, and the web/API endpoints should respond at `http://localhost:3000` and `http://localhost:8000/docs`.

**Important**

`docker builder prune -f` alone did not repair this incident. Do not run `docker compose down -v` or remove `bitmanga-local_postgres_data`; that would delete stored application data.

## 2026-09-27 — Local login proxy could not resolve services

**Symptoms**

- Browser login failed and container logs showed `EAI_AGAIN backend-api`.
- The API also could not resolve `db` from inside Compose in this environment.

**Cause and fix**

This Codespaces Docker environment could not resolve/reach Compose service names across its bridge network, although host-published ports were reachable. Local Compose now routes Next.js to `host.docker.internal:8000` and FastAPI to `host.docker.internal:5432`; `extra_hosts` maps that name to the host gateway. Production Compose intentionally retains internal service names.

**Verification**

Reader and Admin login through `http://localhost:3000/api/auth/login` returned `200`; the API completed startup and the site returned `200`. If this symptom returns, inspect `docker compose -p bitmanga-local logs nextjs backend-api db` and verify the local gateway settings in `docker-compose.yaml` and `nextjs/next.config.mjs` before editing auth code.