---
name: devops-master
description: Containerization (Docker), Deployment, and CI/CD Pipelines
license: MIT
compatibility: opencode
metadata:
  stack: docker, github-actions
---

## 🐳 DevOps & Deployment Protocol

You are responsible for the infrastructure. Code that cannot be deployed is useless code.

### 1. Dockerization Standard
- **Multi-Stage Builds:** Always use multi-stage builds to keep image size small.
  - *Builder Stage:* Install compilers, build-essentials.
  - *Runner Stage:* `python:slim` or `alpine` (if compatible), copy only virtualenv/artifacts.
- **No Root:** Create a non-root user in the Dockerfile for security.
- **Caching:** Copy `requirements.txt` and run `pip install` *before* copying source code to leverage Docker Layer Caching.

### 2. Docker Compose Strategy
- Define services clearly: `bot`, `postgres`, `redis`, `dashboard`.
- Use **Volumes** for persistent data (Database, Logs).
- Use **Healthchecks** to ensure the Bot waits for the Database to be ready.

### 3. CI/CD (GitHub Actions)
- **Linting:** pipeline must fail if `flake8` or `black` finds errors.
- **Testing:** pipeline must run `pytest`.
- **Deployment:** If `main` branch is pushed, trigger Docker build and restart logic.

### 4. Environment Management
- NEVER hardcode secrets. Use `.env` file and `os.getenv`.
- In Docker, map env-file: `env_file: .env`.