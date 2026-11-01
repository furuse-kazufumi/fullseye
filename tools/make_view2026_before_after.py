#!/usr/bin/env python3
"""A 群14展示の変更前後を、展示ごとに1枚の一覧JPEGへ並べる。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from check_view2026_figure_scale import SHORTLIST


THUMB = (540, 190)
LABEL_H = 22


def _manifest(root: Path, poc_id: str) -> dict[str, Path]:
    directory = root / poc_id
    rows = json.loads((directory / "figures.json").read_text(encoding="utf-8-sig"))
    return {str(row["name"]): directory / str(row["file"])
            for row in rows if str(row.get("file", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif"))}


def _thumb(path: Path | None) -> Image.Image:
    if path is None or not path.is_file():
        image = Image.new("RGB", THUMB, "#eee8e3")
        ImageDraw.Draw(image).text((12, 84), "missing", fill="#9b2d20")
        return image
    with Image.open(path) as source:
        source.seek(0)
        image = source.convert("RGB")
    image.thumbnail(THUMB, Image.Resampling.LANCZOS)
    return ImageOps.pad(image, THUMB, color="white", method=Image.Resampling.LANCZOS)


def make_sheet(poc_id: str, before: dict[str, Path], after: dict[str, Path]) -> Image.Image:
    names = sorted(set(before) | set(after))
    width = THUMB[0] * 2 + 30
    height = 52 + len(names) * (THUMB[1] + LABEL_H)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((10, 8), poc_id, fill="black", font=font)
    draw.text((10, 30), "BEFORE", fill="#555", font=font)
    draw.text((THUMB[0] + 20, 30), "AFTER", fill="#555", font=font)
    y = 52
    for name in names:
        draw.text((10, y + 3), name, fill="#222", font=font)
        y += LABEL_H
        sheet.paste(_thumb(before.get(name)), (10, y))
        sheet.paste(_thumb(after.get(name)), (THUMB[0] + 20, y))
        y += THUMB[1]
    return sheet


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, default=Path("docs/articles/assets/poc"))
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    for poc_id in SHORTLIST:
        sheet = make_sheet(poc_id, _manifest(args.before, poc_id), _manifest(args.after, poc_id))
        sheet.save(args.output / f"{poc_id}.jpg", quality=88, optimize=True)
        print(poc_id, sheet.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
