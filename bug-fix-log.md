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

1. Preferred fix: create and select a fresh BuildKit builder, then use the normal Compose command. Choose an unused builder name if `bitmanga-fresh` already exists:

   ```bash
   docker buildx create --name bitmanga-fresh --driver docker-container --use --bootstrap
   docker compose -p bitmanga-local up -d --build
   ```

   Selecting it with `--use` makes it the default builder for subsequent Compose builds in this Docker context. If the named builder already exists, select it with `docker buildx use bitmanga-fresh` instead of creating it again. This was verified to rebuild both images and start the app successfully.

2. If a fresh builder cannot be created or its image import is canceled, fall back to Docker's legacy builder:

   ```bash
   DOCKER_BUILDKIT=0 docker build --no-cache -t bitmanga-local-backend-api:latest ./backend-api
   DOCKER_BUILDKIT=0 docker build --no-cache -t bitmanga-local-nextjs:latest ./nextjs
   docker compose -p bitmanga-local up -d --no-build
   ```

3. If the existing database container specifically reports `RWLayer ... is unexpectedly nil`, remove and recreate only that container. This preserves its named data volume:

   ```bash
   docker compose -p bitmanga-local stop
   docker compose -p bitmanga-local rm -f db
   docker compose -p bitmanga-local up -d --no-build
   ```

4. Verify services with `docker compose -p bitmanga-local ps`; PostgreSQL should be healthy, and the web/API endpoints should respond at `http://localhost:3000` and `http://localhost:8000/docs`.

**Important**

`docker builder prune -f` alone did not repair this incident. Do not run `docker compose down -v` or remove `bitmanga-local_postgres_data`; that would delete stored application data.

## 2026-09-27 — Local login proxy could not resolve services

**Symptoms**

- Browser login failed and container logs showed `EAI_AGAIN backend-api`.
- The API also could not resolve `db` from inside Compose in this environment.

**Cause and fix**

This Codespaces Docker environment could not reach Compose services across its bridge network, although host-published ports were reachable. The portable `docker-compose.yaml` uses Compose service DNS (`backend-api` and `db`), which is the normal setup on other Docker hosts. For Codespaces only, use `docker-compose.codespaces.yaml`; it routes Next.js and FastAPI through `host.docker.internal` and maps that name to the host gateway. Production Compose also uses internal service names.

Start the Codespaces variant with:

```bash
docker compose -p bitmanga-local -f docker-compose.yaml -f docker-compose.codespaces.yaml up -d --build
```

**Verification**

Reader and Admin login through `http://localhost:3000/api/auth/login` returned `200`; the API completed startup and the site returned `200`. If this symptom returns, inspect `docker compose -p bitmanga-local logs nextjs backend-api db` and verify the Codespaces override and `nextjs/next.config.mjs` before editing auth code.

## 2026-09-28 — Repeating local startup failure caused by stale Docker runtime state

**Symptoms**

- `docker compose -p bitmanga-local up -d --build` failed during BuildKit startup with `RWLayer ... is unexpectedly nil`.
- The app containers were marked exited or unhealthy even though the application code had not changed.
- Browser/HTTP checks showed the frontend and API intermittently failing before they were ready.

**Cause**

The application itself was not failing. The local Docker daemon had stale BuildKit layer metadata and a broken container writable layer. This is a host-level Docker runtime issue, not a Bit.Manga code defect. The project also needed the Codespaces networking override because Compose service names do not resolve consistently in this environment.

**Fix**

1. Preserve the PostgreSQL data volume and recreate only the app containers.
2. Detect Codespaces and include `docker-compose.codespaces.yaml`.
3. Retry once using the legacy builder (`DOCKER_BUILDKIT=0`) if BuildKit remains broken.
4. Then poll the app until both `http://localhost:3000` and `http://localhost:8000/docs` respond successfully.
5. Use the one-click launcher at `./start.sh` for future restarts instead of the raw Compose command.

```bash
./start.sh
```

**Verification**

The launcher completed successfully in the current workspace with exit code `0`. Both endpoints returned `HTTP/1.1 200 OK` after startup, and the database container remained healthy without deleting the Postgres volume.