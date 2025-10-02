"""Generate boilerplate files from templates and auto-commit them."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "scripts" / "templates"


def available_templates() -> Dict[str, Path]:
    """Return a mapping of template names to file paths."""

    if not TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"Template directory missing: {TEMPLATE_DIR}")
    return {tpl.name: tpl for tpl in TEMPLATE_DIR.glob("*") if tpl.is_file()}


def render_template(template: Path, context: Dict[str, str]) -> str:
    """Render the template file with the provided context."""

    text = template.read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def write_output(path: Path, text: str) -> None:
    """Persist rendered text to disk, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_commit(path: Path, message: str) -> None:
    """Stage, commit, and push the generated artifact if it changed."""

    try:
        subprocess.run(["git", "add", str(path)], cwd=ROOT, check=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False)
        if diff.returncode == 0:
            return
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=False)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - safety logging
        print(f"[codex] git automation skipped: {exc}", file=sys.stderr)


def main() -> None:
    templates = available_templates()

    parser = argparse.ArgumentParser(description="Render templates and commit the result.")
    parser.add_argument("--tpl", required=True, choices=sorted(templates.keys()), help="Template filename")
    parser.add_argument("--out", required=True, help="Output path relative to repo root")
    parser.add_argument("--name", default="Untitled", help="Name placeholder")
    parser.add_argument("--summary", default="", help="Summary placeholder")
    parser.add_argument("--ticker", default="", help="Ticker placeholder")
    parser.add_argument("--date", default=None, help="Override rendered date (YYYY-MM-DD)")
    args = parser.parse_args()

    render_date = args.date or dt.datetime.now().strftime("%Y-%m-%d")
    context = {
        "name": args.name,
        "summary": args.summary,
        "ticker": args.ticker,
        "date": render_date,
    }

    template_path = templates[args.tpl]
    output_path = ROOT / args.out

    rendered = render_template(template_path, context)
    write_output(output_path, rendered)
    git_commit(output_path, f"docs: add {args.tpl} -> {args.out}")


if __name__ == "__main__":
    main()
