"""Simple filesystem sync daemon for Obsidian vault snapshots."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

VAULT = Path(os.getenv("RIZZK_VAULT", "obsidian")).resolve()
EXPORTS = Path(os.getenv("RIZZK_EXPORTS", "obsidian/90_exports")).resolve()
ROOT = Path(__file__).resolve().parents[1]
GIT = ["git", "-C", str(ROOT)]

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
LOGGER = logging.getLogger("sync_daemon")


class DebouncedEventHandler(FileSystemEventHandler):
    """Marks the vault as dirty whenever a file-system event fires."""

    def __init__(self) -> None:
        self._dirty = False
        self._last_event: Optional[float] = None

    def on_any_event(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._dirty = True
        self._last_event = time.time()

    @property
    def dirty(self) -> bool:
        return self._dirty

    def consume(self) -> None:
        self._dirty = False

    @property
    def last_event(self) -> Optional[float]:
        return self._last_event


def safe_commit(message: str) -> None:
    """Commit and push if there are staged changes."""

    try:
        subprocess.run(GIT + ["add", "-A"], check=True)
        diff = subprocess.run(GIT + ["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            subprocess.run(GIT + ["commit", "-m", message], check=True)
            LOGGER.info("Committed snapshot: %s", message)
            subprocess.run(GIT + ["push"], check=True)
            LOGGER.info("Pushed snapshot to remote")
    except Exception as exc:  # pragma: no cover - best effort logging
        LOGGER.warning("git push skipped: %s", exc)


def export_housekeeping(max_files: int = 500) -> None:
    """Keep export directory from growing unbounded."""

    EXPORTS.mkdir(parents=True, exist_ok=True)
    files = sorted(EXPORTS.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[max_files:]:
        try:
            stale.unlink()
            LOGGER.info("Removed stale export: %s", stale)
        except FileNotFoundError:
            continue


def main() -> None:
    VAULT.mkdir(parents=True, exist_ok=True)
    handler = DebouncedEventHandler()
    observer = Observer()
    observer.schedule(handler, str(VAULT), recursive=True)
    observer.start()
    LOGGER.info("Watching vault: %s", VAULT)

    try:
        last_snapshot = 0.0
        while True:
            time.sleep(2)
            now = time.time()

            if handler.dirty and handler.last_event and now - handler.last_event >= 5:
                export_housekeeping()
                LOGGER.info("Detected changes; creating snapshot")
                safe_commit("chore(sync): vault snapshot")
                handler.consume()
                last_snapshot = now
                continue

            if now - last_snapshot >= 900:  # snapshot every 15 minutes regardless of changes
                export_housekeeping()
                LOGGER.info("Heartbeat snapshot triggered")
                safe_commit("chore(sync): heartbeat snapshot")
                last_snapshot = now
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
