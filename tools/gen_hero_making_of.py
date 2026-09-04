# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事 1 枚目 hero の「改善の過程」モンタージュ(2026-09-04、ユーザー「過程も載せると作ってる感が分かる」)。
パネル: ①旧 640px フラット法線(ファセット)②smooth 法線でも残る格子バンディング(拡大)
③SDF 勾配法線(拡大)④被写体が「ジャガイモ」だった 1280px ⑤最終: SDF/CSG 静物。
素材は tools/_making_of/ に置く(git 管理)。Run: py -3.11 tools/gen_hero_making_of.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "_making_of"
OUT = ROOT / "docs" / "articles" / "assets" / "hero_making_of.png"
PANELS = [
    ("01_old_640_flat.png", "① 旧: 640px・フラット法線\nファセットと四角いハイライト"),
    ("02_smooth_banding_crop.png", "② smooth 法線でも格子由来の\n等高線バンディングが残る(拡大)"),
    ("03_sdf_normals_crop.png", "③ SDF 勾配を法線に → 消えた\n(場を持っているなら場を微分)"),
    ("04_potato_1280.png", "④ 1280px にしたが「ジャガイモ」\n※左のはウ○コではありません"),
    ("05_final_still_life.png", "⑤ 被写体を SDF/CSG の静物に\n格子球(鋼)・結び目(金)・歯車(黒鉄)"),
]
def main() -> int:
    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 22)
    tile, cap_h, pad = 420, 70, 14
    avail = [(f, c) for f, c in PANELS if (SRC / f).exists()]
    W = pad + len(avail) * (tile + pad); H = pad + tile + cap_h + pad
    canvas = Image.new("RGB", (W, H), (18, 20, 24)); d = ImageDraw.Draw(canvas)
    for i, (f, cap) in enumerate(avail):
        im = Image.open(SRC / f).convert("RGB"); im.thumbnail((tile, tile), Image.LANCZOS)
        x = pad + i * (tile + pad); y = pad + (tile - im.height) // 2
        canvas.paste(im, (x + (tile - im.width) // 2, y))
        d.multiline_text((x, pad + tile + 8), cap, font=font, fill=(235, 235, 235), spacing=4)
    OUT.parent.mkdir(parents=True, exist_ok=True); canvas.save(OUT, optimize=True)
    print(f"[making-of] {OUT} {canvas.size} panels={len(avail)}"); return 0
if __name__ == "__main__":
    sys.exit(main())
