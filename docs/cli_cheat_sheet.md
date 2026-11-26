# Data Engineering CLI Cheat Sheet (Labs 0–4)

A quick-reference guide of frequently used terminal commands for managing your Python environment, code quality, Git workflow, and Prefect deployments.

---

## 1. Python & Package Management (`uv`)

### Project Setup & Dependencies
```bash
# Initialize a new src-layout Python 3.12 project
uv init --package --python 3.12 my-pipeline

# Sync/rebuild the virtual environment (.venv) from uv.lock
uv sync

# Add production dependencies
uv add prefect polars httpx python-dotenv

# Add development dependencies
uv add --dev ruff pytest
```

### Running Code
```bash
# Run a specific Python script inside the project environment
uv run python src/my_pipeline/hello.py

# Run the package's main entry point (defined in pyproject.toml)
uv run my-pipeline

# Run a Python one-liner (e.g., passing parameters to a flow)
uv run python -c "from my_pipeline.hello import hello_pipeline; hello_pipeline(name='Ama')"
```

---

## 2. Code Quality & Testing (`ruff` & `pytest`)

```bash
# Check code for linting errors and import sorting
uv run ruff check .

# Check if code formatting matches project rules
uv run ruff format --check .

# Automatically format all code files
uv run ruff format .

# Run the test suite
uv run pytest
```

---

## 3. Git & GitHub Workflow (`git` & `gh`)

### Daily Git Workflow
```bash
# Check which files are modified, staged, or untracked (verify .env is ignored)
git status

# Stage all changes
git add .

# Commit staged changes with a message
git commit -m "feat: add pipeline logic"

# Push commits to GitHub
git push
```

### Repository & Safety Checks
```bash
# Create a public GitHub repo from the current folder and push
gh repo create my-pipeline --public --source . --remote origin --push

# Open the GitHub repository in your web browser
gh repo view --web

# Verify that .env is NOT tracked by Git (should return nothing)
git ls-files | grep -E '^\.env$'

# Remove a file from Git tracking without deleting it locally (if committed by mistake)
git rm --cached .env
```

---

## 4. Prefect: Local Server & Profiles

### Switching Environments
```bash
# View current Prefect profile and API URL configuration
uv run prefect config view

# Switch to your local Prefect server
uv run prefect profile use local

# Switch to Prefect Cloud
uv run prefect profile use cloud
```

### Local Server Management
```bash
# Create and configure a local profile (one-time setup)
uv run prefect profile create local
uv run prefect profile use local
uv run prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api

# Start the local Prefect server and UI (http://127.0.0.1:4200)
uv run prefect server start

# Start the local server on a different port if 4200 is busy
uv run prefect server start --port 4201
```

---

## 5. Prefect Cloud & Deployments

### Cloud Setup & Work Pools
```bash
# Create a cloud profile and log in via browser/API key (one-time setup)
uv run prefect profile create cloud
uv run prefect profile use cloud
uv run prefect cloud login

# Create a Prefect Managed work pool
uv run prefect work-pool create --type prefect:managed my-managed-pool
```

### Deploying & Running Flows
```bash
# Register/update a deployment (must be run from inside src/)
cd src
uv run prefect deploy --prefect-file ../prefect.yaml --name hello --no-prompt
cd ..

# List all registered deployments in the active profile
uv run prefect deployment ls

# Trigger a cloud deployment run and stream logs in your terminal
uv run prefect deployment run 'hello-pipeline/hello' --watch
```

---

## 6. Utilities & Environment Check

```bash
# Test an API endpoint and inspect raw JSON output
curl "https://archive-api.open-meteo.com/v1/archive?latitude=5.56&longitude=-0.20&start_date=2026-11-01&end_date=2026-11-03&daily=temperature_2m_max&timezone=UTC"

# Create a local .env file from the example template
cp .env.example .env

# Verify core toolchain installations
git --version && uv --version && gh auth status
```