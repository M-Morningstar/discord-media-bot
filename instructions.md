# Step 14: CI/CD Pipeline (GitHub Actions)

## What This Step Delivers

`.github/workflows/ci.yml` — a GitHub Actions workflow that runs on every push and PR to `main`. It lints, type-checks, tests (with 80% coverage floor), verifies the lockfile is in sync, and builds the Docker image on `main` pushes.

---

## File: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: pip install uv

      - name: Install project + dev dependencies
        run: uv pip install --system -e ".[dev]"

      - name: Check lockfile is in sync
        run: |
          uv pip compile --output-file=requirements.txt pyproject.toml
          git diff --exit-code requirements.txt

      - name: Lint
        run: ruff check src/ tests/

      - name: Format check
        run: ruff format --check src/ tests/

      - name: Type check
        run: mypy src/ --strict

      - name: Test
        run: pytest --cov=src --cov-report=term-missing --cov-fail-under=80

  build-docker:
    needs: lint-and-test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t discord-media-bot .

      - name: Smoke test
        run: >
          docker run --rm
          -e DISCORD_BOT_TOKEN=x
          -e DISCORD_RADARR_CHANNEL_ID=12345678901234567
          -e DISCORD_SONARR_CHANNEL_ID=12345678901234568
          -e RADARR_URL=http://localhost:7878
          -e RADARR_API_KEY=x
          -e RADARR_QUALITY_PROFILE_ID=1
          -e RADARR_ROOT_FOLDER_PATH=/movies
          -e SONARR_URL=http://localhost:8989
          -e SONARR_API_KEY=x
          -e SONARR_QUALITY_PROFILE_ID=1
          -e SONARR_ROOT_FOLDER_PATH=/tv
          discord-media-bot
          python -c "from src.config import Config; print('OK')"
```

### Notes
- Uses `uv` (not `pip-tools`) for lockfile verification since the project uses `uv pip compile`.
- Lockfile check: re-runs `uv pip compile` and ensures the commited `requirements.txt` matches — catches the mistake of updating `pyproject.toml` but forgetting to regenerate the lockfile.
- Docker build only runs on `main` (not PRs) to save CI minutes, but the smoke test validates the image can at least import `Config` successfully.
- Coverage floor: 80% (`--cov-fail-under=80`).

---

## Verification

After implementing, push to GitHub and verify:

```bash
git add .github/workflows/ci.yml
git commit -m "Add CI pipeline"
git push origin main
```

Then check the Actions tab — the `lint-and-test` job should pass, and on `main` the `build-docker` job should also succeed.

---

## Summary

| What | File | Description |
|------|------|-------------|
| GitHub Actions workflow | `.github/workflows/ci.yml` | Lint, type-check, test (≥80%), lockfile verify, Docker build |
