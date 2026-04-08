from __future__ import annotations

import argparse
from pathlib import Path

from prompt_manager.builder import build_lorebook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build lorebook.json from Markdown entries")
    parser.add_argument("--source", required=True, help="LoreBook directory (contains entries/)")
    parser.add_argument("--output", required=True, help="Output lorebook.json path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    output = Path(args.output)
    build_lorebook(source=source, output=output)
    print(f"Built lorebook: {output}")


if __name__ == "__main__":
    main()
