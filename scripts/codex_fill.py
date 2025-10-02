"""Utility to populate common templates and auto-commit them."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Dict

TEMPLATES: Dict[str, str] = {
    "journal": "# Trade Journal\n\n- Date: {{date}}\n- Ticker: {{ticker}}\n- Thesis: \n- Entry/Exit: \n- R:R: \n- Notes:\n",
    "readme": "# {{name}}\n\n## Overview\n\n{{summary}}\n",
}


def fill(template: str, path: Path, **kwargs: str) -> None:
    """Render a template into *path*."""

    text = TEMPLATES[template]
    for key, value in kwargs.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_commit(path: Path, message: str) -> None:
    """Commit the given path with *message*."""

    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "-C", str(root), "add", str(path)], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True)
    subprocess.run(["git", "-C", str(root), "push"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate template files and auto-commit them.")
    parser.add_argument("--template", required=True, choices=TEMPLATES.keys())
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", default="Project")
    parser.add_argument("--summary", default="TBD")
    parser.add_argument("--date", default="2025-10-01")
    parser.add_argument("--ticker", default="")
    args = parser.parse_args()

    output_path = Path(args.out)
    fill(
        args.template,
        output_path,
        name=args.name,
        summary=args.summary,
        date=args.date,
        ticker=args.ticker,
    )
    git_commit(output_path, f"docs: add {args.template} -> {output_path}")


if __name__ == "__main__":
    main()
