# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""継承条件つき(CC BY-SA など)のデータから作った図の帰属表示の門。

判定は作者が図ごとに書く文言ではなく、``tools/share_alike.py`` の台帳(データセットの名前・使う PoC・
コマの画素を含まない図)から行う。数える向きは配布物の側から:

1. 全 ``figures.json`` の出典・説明に台帳のデータセットの名前が出る PoC は、台帳に載っていること
   (載せ忘れた PoC を黙って通さない)。
2. 台帳の PoC の図の置き場の画像(縮小・story GIF を含む)と ViEW の縮小が、NOTICE に全部あること。
   NOTICE に書いたファイルは実在すること。件数に下限を置く(空の一覧で通さない)。
3. ViEW の案内ページ(全言語)で、その展示のタイルにライセンスの表記があり、ページにライセンスと
   出典へのリンクがあること。
4. 展示館の記事(ja/en と Qiita の写し)で、継承条件つきの図の直後にライセンスの表記があること。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import share_alike  # noqa: E402

ASSETS = ROOT / "docs" / "articles" / "assets"
VIEW = ROOT / "docs" / "view2026"


def _notice_paths() -> set[str]:
    text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    return {m.group(0) for m in re.finditer(r"docs/[\w./-]+\.(?:png|jpg|jpeg|gif)", text)}


def test_every_poc_that_names_a_share_alike_dataset_is_in_the_ledger():
    unknown = []
    hits = 0
    for fj in sorted(ASSETS.rglob("figures.json")):
        items = json.loads(fj.read_text(encoding="utf-8"))
        if isinstance(items, dict):
            items = items.get("figures", [])
        for it in items:
            for ds in share_alike.mentions("%s %s" % (it.get("source") or "", it.get("caption") or "")):
                hits += 1
                if fj.parent.name not in ds["pocs"]:
                    unknown.append((fj.parent.name, ds["name"], it.get("file")))
    assert hits > 0, "台帳のデータセットの名前がどの図にも出ない(数え方が壊れた?)"
    assert not unknown, "継承条件つきのデータを使う図が台帳(tools/share_alike.py)に無い: %s" % unknown


def test_share_alike_files_are_listed_in_notice():
    need = set(share_alike.share_alike_files())
    assert len(need) >= 12, "継承条件つきの図が少なすぎる(数え方が壊れた?): %s" % sorted(need)
    missing = sorted(need - _notice_paths())
    assert not missing, "継承条件つきの図が NOTICE に無い: %s" % missing


def test_notice_lists_only_existing_files():
    listed = _notice_paths()
    assert listed, "NOTICE に図の一覧が無い"
    gone = sorted(p for p in listed if not (ROOT / p).is_file())
    assert not gone, "NOTICE に書いた図が無い: %s" % gone


def _pages() -> list[Path]:
    # ja/en の継承条件つきの展示は、本ページに載らなければおまけページ(more.md)に載る。
    return ([VIEW / "index.md", VIEW / "more.md"] + sorted(VIEW.glob("*/index.md"))
            + sorted(VIEW.glob("*/more.md")))


def test_view2026_pages_show_the_attribution():
    pages = _pages()
    assert len(pages) >= 10
    checked = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for ds in share_alike.DATASETS:
            for poc in ds["pocs"]:
                tiles = re.findall(r'<a href="[^"]*%s[^"]*">.*?</a>' % re.escape(poc), text)
                if not tiles:
                    continue
                checked += 1
                bare = [t for t in tiles if ds["license"] not in t]
                assert not bare, "%s: %s のタイルにライセンスの表記が無い" % (page.relative_to(ROOT), poc)
                assert ds["license_url"] in text and ds["source_url"] in text, \
                    "%s: %s のライセンスと出典へのリンクが無い" % (page.relative_to(ROOT), poc)
                # 2026-11-09: 改変の内容は NOTICE に書いてあるので、ViEW のページからも NOTICE へ辿れること(記事側の門と揃える)。
                assert share_alike.NOTICE_URL in text, \
                    "%s: %s の帰属表示から NOTICE へのリンクが無い" % (page.relative_to(ROOT), poc)
    assert checked >= 8, "ViEW のページで継承条件つきの展示を 1 つも確かめていない(%d)" % checked


def test_gallery_articles_label_every_share_alike_figure():
    raw = "docs/articles/assets/poc/"
    checked = 0
    for md in sorted((ROOT / "docs" / "articles").rglob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            for m in re.finditer(re.escape(raw) + r"([\w-]+)/([\w.-]+\.(?:png|jpg|jpeg|gif))\)\]", line):
                poc, name = m.group(1), m.group(2)
                if not share_alike.is_share_alike_file(poc, name):
                    continue
                checked += 1
                ds = share_alike.dataset_for(poc)
                after = "\n".join(lines[i + 1:i + 6])
                assert ds["license"] in after and ds["license_url"] in after and ds["source_url"] in after                     and share_alike.NOTICE_URL in after,                     "%s:%d: %s の下にライセンス・ライセンスの URL・出典の URL のどれかが無い" % (md.relative_to(ROOT), i + 1, name)
    assert checked >= 4, "記事で継承条件つきの図を 1 つも確かめていない(%d)" % checked
