# Rizzk Workspace

This repository hosts the full Rizzk trading environment: a Streamlit terminal, an Obsidian vault, and the automation glue that keeps everything in sync.

## Structure

```
rizzk/
  .devcontainer/          # VS Code Dev Container configuration
  infra/                  # Docker Compose runtime definitions
  obsidian/               # Obsidian vault and exports
  apps/                   # Application source (Streamlit, services, etc.)
  scripts/                # Automation helpers (sync daemon, codex generator)
  .github/workflows/      # CI and scheduled jobs
```

## Getting Started

1. Install Git LFS once with `git lfs install`.
2. Open the folder in VS Code and "Reopen in Container" to provision the standard toolchain.
3. Use `docker compose -f infra/docker-compose.yml up --build` to launch the Streamlit app and the sync daemon.
4. Add boilerplate docs with `python scripts/codex_fill.py --template journal --out obsidian/00_inbox/example.md`.

## Automation

- `scripts/sync_daemon.py` watches the vault, snapshots changes, and performs light export housekeeping.
- `scripts/codex_fill.py` materialises predefined templates and immediately commits them.
- `.github/workflows/ci.yml` compiles Python modules, builds the container, and archives the vault every six hours.

## Contributing

Run `pre-commit install` inside the dev container to ensure formatting and linting gates fire before each commit.
