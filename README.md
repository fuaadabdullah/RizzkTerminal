# Rizzk Workspace

This repository is the single source of truth for the Rizzk trading stack: the Streamlit terminal, the Obsidian knowledge base, and the automation that keeps everything in lockstep.

## Repository Layout

```
rizzk/
  .devcontainer/          # VS Code Dev Container configuration
  infra/                  # Docker Compose runtime definitions
  obsidian/               # Obsidian vault and exports
    .obsidian/            # Minimal vault settings tracked in git
    00_inbox/             # Scratch notes, captured ideas
    10_brains/            # Curated research
    90_exports/           # Files exported from the app
  apps/                   # Application source (Streamlit, services, etc.)
    rizzk_pro/
      rizzk_pro.py
      tabs/
  scripts/                # Automation helpers (sync daemon, codex generator)
  .github/workflows/      # CI and scheduled jobs
  data/                   # Local app artefacts (SQLite journal, caches, etc.)
```

## Bootstrap Checklist

Follow this sequence once to get a reproducible environment on any machine:

1. **Clone & initialise**
   ```bash
   git clone <repo-url> rizzk
   cd rizzk
   git lfs install
   ```
2. **VS Code Dev Container (recommended)**
   - Open the folder in VS Code.
   - Run “Reopen in Container”.
   - Inside the container terminal execute:
     ```bash
     pip install -r requirements.txt
     pre-commit install
     ```
   - Alternatively, build locally with Docker Compose: `docker compose -f infra/docker-compose.yml up --build app` (and `sync`).
3. **Environment variables**
   - Copy `.env.example` to `.env` and fill in secrets.
   - Keys can also be pasted into the Streamlit sidebar at runtime.
4. **Obsidian setup**
   - Point Obsidian at `obsidian/`.
   - Keep plugins lean; cached plugin data is ignored via `.gitignore`.
5. **Journal database**
   - Create the SQLite journal once so Streamlit/CLI have a target:
     ```bash
     make db  # or: python scripts/db_init.py
     ```
   - The database lives at `data/rizzk.db` (ignored by Git so each workstation keeps its own ledger).
6. **Automation**
   - `scripts/sync_daemon.py` watches the vault, performs light housekeeping on `90_exports`, and commits/pushes snapshots every ~15 seconds when changes settle. Logs stream through `make logs` (or `just logs`) for quick inspection.
   - `scripts/daily_ops.py` + `scripts/refresh_data.py` run hourly inside the `cron` service. They generate a dashboard note in `obsidian/00_inbox/` and export fresh CSV/JSON snapshots into `obsidian/90_exports`, proving the loop even when you are offline.
   - `scripts/codex_fill.py` reads templates from `scripts/templates/` and auto-commits generated artefacts. Example:
     ```bash
     python scripts/codex_fill.py --tpl journal.md --out obsidian/00_inbox/2025-10-02-MSFT.md --name "MSFT earnings" --ticker MSFT
     ```
7. **Run the app**
   - Launch with Docker Compose (`make up`, `just up`, or `docker compose -f infra/docker-compose.yml up app sync cron`).
   - Visit http://localhost:8501.
   - Use the sidebar “Health” box to verify vault + export paths and container hostname.
   - Exports written to `obsidian/90_exports` are captured by the sync daemon automatically.
8. **Notebook hygiene**
   - `nbstripout` keeps notebook diffs clean. After installing dependencies run:
     ```bash
     pip install nbstripout
     nbstripout --install
     ```
   - Outputs will be stripped on commit.
9. **CI & Backups**
   - `.github/workflows/ci.yml` installs the repo requirements, runs Ruff, MyPy, and Pytest, and uploads a vault snapshot on every push, pull request, and on a six-hour cron.
   - Snapshots are rotated and retained for seven days. Add repository secrets (e.g., `OPENAI_API_KEY`) if the workflow needs them later.

## Makefile shortcuts

Common workflows are wrapped in the root `Makefile`:

| Command | Purpose |
| ------- | ------- |
| `make up` | Build and start the app + sync + cron services in the background. |
| `make down` | Stop all Compose services. |
| `make logs` | Tail combined service logs. |
| `make lint` | Run the full pre-commit suite (Black, Isort, Ruff, MyPy, Pytest, etc.). |
| `make db` | Initialise or migrate the SQLite trade journal (`data/rizzk.db`). |
| `make snap` | Manual Git snapshot + push when you want an immediate checkpoint. |
| `make reset` | Hard reset the repo (use cautiously). |

## Justfile shortcuts

If GNU Make is unavailable (e.g., on Windows), install [`just`](https://github.com/casey/just) and use the equivalent commands:

| Command | Purpose |
| ------- | ------- |
| `just up` | Build and start the app + sync + cron services. |
| `just down` | Stop Compose services. |
| `just logs` | Tail service logs. |
| `just lint` | Run the pre-commit suite. |
| `just snap` | Manual Git snapshot + push. |
| `just db` | Initialise the trade journal database. |

## Trading journal & daily ops

- The Streamlit **Journal** tab now writes structured trades into `data/rizzk.db`, enforces per-trade risk limits based on the sidebar settings, and drops a Markdown receipt into `obsidian/90_exports/` for the sync daemon.
- From a terminal you can log entries without the UI:
  ```bash
  python scripts/trade_add.py --ticker MSFT --side long --entry 420 --stop 410 --exit 435 --qty 50 --thesis "VWAP reclaim"
  ```
  Override dollar risk/reward with `--risk`/`--reward` or adjust the guardrail via `--max-risk`.
- `scripts/daily_ops.py` produces a daily dashboard note in `obsidian/00_inbox/` summarising top tickers by R:R and listing the newest exports (with clear placeholders when no trades or exports exist yet). The cron container runs it hourly alongside `scripts/refresh_data.py`.

## Guardrails

- `.gitignore` removes transient Python, Streamlit, and Obsidian artefacts; secrets belong in `.env` (never commit it).
- Large binaries (images, video) are routed through Git LFS via `.gitattributes`; vault files prefer the latest change with `merge=ours` so desktop and mobile edits do not clash.
- `pre-commit` runs Black, Isort, Markdownlint, Ruff (with autofix), MyPy, and Pytest before every commit.
- Follow Conventional Commit messages (`feat:`, `fix:`, `chore:`) so history stays legible and changelog-friendly.

## Troubleshooting

| Issue | Fix |
| ----- | --- |
| Sync daemon not committing | Ensure `RIZZK_VAULT`/`RIZZK_EXPORTS` env vars point at the correct folders and that Git remotes are configured. |
| Port 8501 busy | Adjust the `ports` mapping in `infra/docker-compose.yml`. |
| Alpha Vantage/OpenAI errors | Provide valid API keys via `.env` or the Streamlit sidebar. |
| Excess exports | Housekeeping in `sync_daemon.py` keeps the newest 500 files; adjust `max_files` if required. |

## Disaster recovery drill

Backups only count once you have restored them. Run this periodically to make sure the workflow still works:

1. Clone the repository into a temp directory: `git clone <repo> _restore_test`.
2. Download the latest `obsidian_snapshot` artifact from GitHub Actions into `_restore_test/restore.tgz`.
3. Extract it: `tar -xzf restore.tgz` and confirm `obsidian/` contains your notes.
4. Remove the temp folder afterwards.

If any step fails, fix the pipeline before trusting the backups.

## Branch policy

Protect `main` with required status checks and at least one code review. Only merge when CI is green so the automation remains trustworthy.

## Merge conflict playbook

Conflicts usually appear when mobile Obsidian edits and desktop automation both touch the vault. When it happens, follow
[`docs/conflict-playbook.md`](docs/conflict-playbook.md) for the quick resolution recipe: sync `main`, rebase (or merge), keep
upstream copies of infrastructure files, keep this branch’s application code, and finish with a `pre-commit`/`pytest` sweep before
pushing. The playbook also captures the `merge=ours` seatbelt to keep the vault from starting new fights.

Ship the checklist once—after that you can iterate on code or notes and let the automations keep everything synchronised.
