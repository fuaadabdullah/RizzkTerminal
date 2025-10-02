# Merge Conflict Playbook

Follow this routine whenever the branch diverges from `main`. It assumes you want upstream defaults for repo plumbing and to keep your feature changes for the automation code.

## 0. Prep the working tree

```bash
git status
git stash -u   # optional if you have local edits
```

## 1. Sync `main` and start the reconciliation

```bash
git fetch origin
git switch main && git pull --ff-only
git switch -
```

Pick one flow:

- **Merge (simpler history)**
  ```bash
  git merge main
  ```
- **Rebase (cleaner history)**
  ```bash
  git rebase main
  ```

Either command will pause on the conflicting files listed below.

## 2. Pick winners by file group

Keep upstream (`--theirs`) for infrastructure and docs, keep the feature branch (`--ours`) for the Streamlit app and automation helpers.

```bash
# keep MAIN for repo plumbing
for f in \
  .gitattributes .github/workflows/ci.yml .gitignore .pre-commit-config.yaml \
  README.md infra/docker-compose.yml requirements.txt
do
  git checkout --theirs "$f"
  git add "$f"
done

# keep YOUR BRANCH for the active work
for f in apps/rizzk_pro/rizzk_pro.py scripts/codex_fill.py scripts/sync_daemon.py
do
  git checkout --ours "$f"
  git add "$f"
done
```

> **Note:** During a rebase Git swaps the meaning of “ours” and “theirs”. `--ours` still selects the branch you are keeping (your feature work) and `--theirs` selects the commit you are rebasing onto (upstream `main`).

## 3. Finish the merge or rebase

```bash
# merge path
git commit -m "merge: resolve conflicts (infra from main, code from feature)"

# rebase path
git rebase --continue
```

When rebasing, push with a lease to avoid clobbering other work:

```bash
git push --force-with-lease
```

Otherwise a normal `git push` is fine.

## 4. Sanity checks before pushing

```bash
pre-commit run --all-files || true
pytest -q || true
python -m py_compile $(git ls-files '*.py') || true
docker compose -f infra/docker-compose.yml config >/dev/null
```

If a file still shows conflict markers (`<<<<<<<` / `=======` / `>>>>>>>`), open it, remove the markers manually, and re-run the `git add` + `git commit` / `git rebase --continue` step.

## 5. Seatbelts so the next conflict is easier

```bash
# remember resolutions automatically
git config rerere.enabled true

# prefer the latest edit for Obsidian vault files
git config merge.ours.driver true
```

`.gitattributes` already contains `obsidian/** merge=ours`, so once the merge driver is configured, phone-versus-desktop vault edits stop colliding.

You can also use the newer plumbing command if you prefer:

```bash
# equivalent to git checkout --ours/--theirs on modern Git
git restore --ours <file>
git restore --theirs <file>
```

## 6. One-and-done helper snippet

Paste the following while a merge/rebase is paused to apply the defaults automatically:

```bash
for f in .gitattributes .github/workflows/ci.yml .gitignore .pre-commit-config.yaml README.md infra/docker-compose.yml requirements.txt; do
  git checkout --theirs "$f" && git add "$f"
done
for f in apps/rizzk_pro/rizzk_pro.py scripts/codex_fill.py scripts/sync_daemon.py; do
  git checkout --ours "$f" && git add "$f"
done
git commit -m "merge: resolve conflicts (infra from main, code from feature)" 2>/dev/null || git rebase --continue
```

Repeat the sanity checks, push, and you are back on a clean branch.
