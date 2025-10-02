# Merge Conflict Playbook

When this branch drifts from `main`, use the following procedure to reconcile the histories without losing the automation wiring.

## 1. Sync `main`

```bash
git fetch origin
git switch main
git pull --ff-only
git switch -
```

## 2. Rebase (preferred) or merge

Rebase keeps the history linear. If you prefer merge commits, swap `git rebase` for `git merge` in the next command.

```bash
git rebase main
```

Git will stop at the conflicting files listed in the output.

## 3. Pick winners by file group

| File(s) | Winning version | Reason |
| --- | --- | --- |
| `.gitattributes`, `.gitignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `infra/docker-compose.yml`, `requirements.txt`, `README.md` | `--theirs` (from `main`) | These govern repo plumbing; we take the upstream defaults to avoid drift. |
| `apps/rizzk_pro/rizzk_pro.py`, `scripts/codex_fill.py`, `scripts/sync_daemon.py`, `apps/rizzk_pro/journal.py`, `scripts/daily_ops.py` | `--ours` (current branch) | These files hold the latest journaling and automation logic. |

Example:

```bash
git checkout --theirs .gitattributes .github/workflows/ci.yml .gitignore \
  .pre-commit-config.yaml README.md infra/docker-compose.yml requirements.txt
git checkout --ours apps/rizzk_pro/rizzk_pro.py scripts/codex_fill.py scripts/sync_daemon.py \
  apps/rizzk_pro/journal.py scripts/daily_ops.py
git add .
```

## 4. Continue the rebase (or finish the merge)

```bash
git rebase --continue  # or: git commit
```

## 5. Sanity check and push

```bash
pre-commit run --all-files
pytest -q
git push --force-with-lease  # add --force-with-lease only when rebasing
```

## 6. Seatbelts for the Obsidian vault

Vault files prefer the latest edit to avoid phone vs desktop conflict loops:

```bash
git config merge.ours.driver true
```

The repository already tracks `obsidian/** merge=ours` in `.gitattributes`, so once the config is set the vault will stop starting fights.

