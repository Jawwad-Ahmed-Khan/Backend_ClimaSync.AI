# Production Deployment Checklist

Use this checklist before deploying the FastAPI application to production.

---

## Configuration

- [ ] `ENVIRONMENT` set to `"production"`
- [ ] `DEBUG` set to `False`
- [ ] `SECRET_KEY` is unique, cryptographically random (≥ 256 bits)
- [ ] `DATABASE_URL` points to production database
- [ ] `CORS_ORIGINS` restricted to actual frontend domains
- [ ] `ALLOWED_HOSTS` configured (no wildcards)
- [ ] API docs disabled (`docs_url=None`, `redoc_url=None`, `openapi_url=None`)
- [ ] `.env` file is NOT committed — deployed via secrets manager or environment

## Database

- [ ] All Alembic migrations applied: `alembic upgrade head`
- [ ] Migration history verified — no missing or out-of-order migrations
- [ ] Database connection pool tuned: `pool_size`, `max_overflow`, `pool_timeout`
- [ ] `pool_pre_ping=True` enabled for connection health checks
- [ ] Database backups configured and tested
- [ ] Database user has minimal required permissions
- [ ] SSL/TLS enabled for database connections

## Application Server

- [ ] Using Uvicorn with multiple workers: `--workers N` (N = 2×CPU + 1)
- [ ] Or using Gunicorn with Uvicorn workers:
  ```bash
  gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
- [ ] `--reload` flag is NOT used in production
- [ ] Process manager configured (systemd, supervisord, or Docker)
- [ ] Graceful shutdown handling (lifespan shutdown hooks)
- [ ] Resource limits set (memory, CPU, file descriptors)

## Docker

- [ ] Multi-stage build used (smaller production image)
- [ ] Non-root user configured (`USER appuser`)
- [ ] Base image uses specific version tag (not `latest`)
- [ ] `.dockerignore` excludes unnecessary files (tests, docs, .git)
- [ ] Health check configured in `docker-compose.yml` or Dockerfile
- [ ] Container restart policy set (`unless-stopped` or `always`)
- [ ] No secrets baked into the image — use env vars or secrets at runtime

## Networking & Reverse Proxy

- [ ] HTTPS/TLS certificate configured (Let's Encrypt, Cloudflare, etc.)
- [ ] Reverse proxy (nginx, Traefik, Caddy) in front of Uvicorn
- [ ] HTTP → HTTPS redirect configured
- [ ] Security headers verified (use securityheaders.com)
- [ ] Rate limiting configured at proxy level
- [ ] Request size limits set
- [ ] WebSocket support configured (if using WebSockets)

## Monitoring & Observability

- [ ] Structured JSON logging enabled (`LOG_FORMAT=json`)
- [ ] Log level set to `INFO` (not `DEBUG`)
- [ ] `/health` endpoint returns basic health status
- [ ] `/health/ready` endpoint checks database connectivity
- [ ] Application metrics exposed (Prometheus, Datadog, etc.)
- [ ] Error tracking configured (Sentry, Rollbar, etc.)
- [ ] Alerting configured for:
  - [ ] 5xx error rate > threshold
  - [ ] Response latency p95 > threshold
  - [ ] Database connection pool exhaustion
  - [ ] Disk space / memory usage

## CI/CD Pipeline

- [ ] Tests pass: `pytest --cov=app`
- [ ] Coverage ≥ 80%
- [ ] Lint passes: `ruff check app/`
- [ ] Type check passes: `mypy app/`
- [ ] Dependency audit passes: `pip audit`
- [ ] Docker image builds successfully
- [ ] Migrations run without errors in CI
- [ ] Rollback strategy documented and tested

## Post-Deployment

- [ ] Smoke test: hit `/health` and `/health/ready`
- [ ] Verify API docs are NOT accessible
- [ ] Verify CORS allows only configured origins
- [ ] Check logs for startup errors
- [ ] Run a few API calls and verify responses
- [ ] Monitor error rates for the first hour
- [ ] Verify database migrations applied correctly
