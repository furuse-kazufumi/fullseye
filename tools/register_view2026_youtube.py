#!/usr/bin/env python3
"""Add the optional YouTube URL field to every featured exhibit."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/view2026/exhibits.json"


def main():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    for exhibit in d["exhibits"]:
        exhibit.setdefault("youtube_url", "")
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
