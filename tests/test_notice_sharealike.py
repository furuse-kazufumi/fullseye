# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""継承条件つき(CC BY-SA)のデータから作った図が、NOTICE に漏れなく列挙されているかの門。

図そのものが CC BY-SA 4.0 で配られる(repo の Apache-2.0 ではない)ので、NOTICE の一覧が配布物と
食い違えば、どのファイルが BY-SA かを読み手が知る手段が無くなる。数える向きは配布物の側から:
``docs/articles/assets`` の全 ``figures.json`` を読み、出典か説明に BY-SA と書かれた図(と、その
720 px の縮小・同じ PoC の story GIF・ViEW の縮小)が NOTICE に在ることを確かめる。逆に NOTICE に
書いたファイルは実在すること。空の一覧で通らないよう、件数の下限も置く。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets"
SHARE_ALIKE = re.compile(r"BY-SA|ShareAlike|Share-Alike", re.IGNORECASE)


def _notice_paths() -> set[str]:
    text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    return {m.group(0) for m in re.finditer(r"docs/[\w./-]+\.(?:png|jpg|jpeg|gif)", text)}


def _share_alike_files() -> set[str]:
    out: set[str] = set()
    for fj in sorted(ASSETS.rglob("figures.json")):
        items = json.loads(fj.read_text(encoding="utf-8"))
        if isinstance(items, dict):
            items = items.get("figures", [])
        d = fj.parent
        hit = False
        for it in items:
            text = "%s %s" % (it.get("source") or "", it.get("caption") or "")
            if not SHARE_ALIKE.search(text):
                continue
            # 数だけの図(グラフ・表)はコマの画素を含まないので対象外(出典に "no frame pixels" と書く)。
            # 対象 = 出典に "Frames shown" か「この図は CC BY-SA」と書いた図と、BY-SA と書いた GIF。
            low = text.lower()
            if "no frame pixels" in low:
                continue
            if "frames shown" not in low and "この図は CC BY-SA" not in text and not it["file"].endswith(".gif"):
                continue
            hit = True
            out.add((d / it["file"]).relative_to(ROOT).as_posix())
            thumb = d / (Path(it["file"]).stem + "_720.jpg")
            if thumb.exists():
                out.add(thumb.relative_to(ROOT).as_posix())
        if hit:
            for g in sorted(d.glob("story.*.gif")):
                out.add(g.relative_to(ROOT).as_posix())
            view = ROOT / "docs" / "view2026" / "thumbs" / "all" / (d.name + ".jpg")
            if view.exists():
                out.add(view.relative_to(ROOT).as_posix())
    return out


def test_share_alike_figures_are_listed_in_notice():
    need = _share_alike_files()
    assert len(need) >= 12, "BY-SA の図が見つからない(数え方が壊れた?): %s" % sorted(need)
    missing = sorted(need - _notice_paths())
    assert not missing, "BY-SA のコマを含む図が NOTICE に無い: %s" % missing


def test_notice_lists_only_existing_files():
    listed = _notice_paths()
    assert listed, "NOTICE に図の一覧が無い"
    gone = sorted(p for p in listed if not (ROOT / p).is_file())
    assert not gone, "NOTICE に書いた図が無い: %s" % gone
