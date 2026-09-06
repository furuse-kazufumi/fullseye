# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingpoc_gallery — PoC シリーズの「展示館」記事(ja / en)を**データから**組み立てる。

    py -3.11 tools/gen_wingpoc_gallery.py            # 翼 + 記事 + サムネを生成
    py -3.11 tools/gen_wingpoc_gallery.py --check    # 生成物が最新かだけ確かめる(exit 1 = 要再生成)

**単一真実源**は 2 つ:

1. ``docs/articles/exhibits/poc_captions.json`` —— 展示室(wing)・展示(exhibit)ごとの
   題とキャプション(ja / en)・数字の出所・追加日・使う図。**新しい PoC を足すときは
   ここに 1 エントリ足して再生成するだけ**(ユーザー方針 2026-09-07「PoC も記事も
   どんどん増やす。追加しやすい構成で」)。
2. ``docs/articles/assets/poc/<poc_id>/figures.json`` —— その PoC を
   ``FULLSEYE_FIGURE_DIR`` 付きで走らせたときの図(examplefig が書く)。**図は PoC
   スクリプト自身の出力**で、記事のために別に描かない(モックアップ禁止)。

生成物:

* ``docs/articles/exhibits/wingpoc.ja.md`` / ``wingpoc.en.md`` —— 展示館の翼(他の翼と同じ
  形式: ``## N. 題`` / 画像(サムネ → クリックで等倍)/ 斜体キャプション / 静止サムネと
  生成元の HTML コメント)。
* ``docs/articles/fullseye_poc_museum_qiita_ja.md`` / ``_en.md`` —— Qiita に出す記事本体
  (入口ホール + 「最近の追加」+ 翼 + 閉館の挨拶)。
* ``docs/articles/assets/poc/<poc_id>/<fig>_720.jpg`` —— 幅 720 px の JPEG サムネ(q92)。

規律(fail-closed): キャプションの無い展示・図の無い展示・存在しない PoC id・ローカルパス
が混ざれば生成せずに落ちる。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
ASSETS = os.path.join(_ROOT, "docs", "articles", "assets", "poc")
CAPTIONS = os.path.join(EXHIBITS, "poc_captions.json")
RAW = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/"
GH = "https://github.com/furuse-kazufumi/fullseye/blob/master/"
THUMB_W = 720
JPEG_Q = 92
OUT_WING = {L: os.path.join(EXHIBITS, "wingpoc.%s.md" % L) for L in ("ja", "en")}
OUT_ARTICLE = {"ja": os.path.join(_ROOT, "docs", "articles", "fullseye_poc_museum_qiita_ja.md"),
               "en": os.path.join(_ROOT, "docs", "articles", "fullseye_poc_museum_qiita_en.md")}

_LOCAL = re.compile(r"[A-Za-z]:\\\\|/c/dev/|/Users/|AppData")


class BuildError(SystemExit):
    pass


def _load():
    with open(CAPTIONS, encoding="utf-8") as f:
        cap = json.load(f)
    import examples2d as E
    byid = {e["id"]: e for e in E.EXAMPLES}
    for ex in cap["exhibits"]:
        if ex["id"] not in byid:
            raise BuildError("poc_captions.json: %r は examples2d.EXAMPLES に無い" % ex["id"])
        for k in ("wing", "title_ja", "title_en", "caption_ja", "caption_en", "added"):
            if not ex.get(k):
                raise BuildError("poc_captions.json: %s に %s が無い" % (ex["id"], k))
        for k in ("caption_ja", "caption_en", "title_ja", "title_en"):
            if _LOCAL.search(ex[k]):
                raise BuildError("ローカルパスが混ざっている: %s.%s" % (ex["id"], k))
    wings = {w["id"]: w for w in cap["wings"]}
    for ex in cap["exhibits"]:
        if ex["wing"] not in wings:
            raise BuildError("%s の wing %r が wings に無い" % (ex["id"], ex["wing"]))
    return cap, byid


def _figure_for(ex):
    """展示に使う図(ファイル名, キャプション元)。``figure`` で名前か添字を指定できる。"""
    d = os.path.join(ASSETS, ex["id"])
    mp = os.path.join(d, "figures.json")
    if not os.path.exists(mp):
        raise BuildError("%s: 図が無い(FULLSEYE_FIGURE_DIR=%s で走らせる)" % (ex["id"], d))
    with open(mp, encoding="utf-8") as f:
        figs = json.load(f)
    if not figs:
        raise BuildError("%s: figures.json が空" % ex["id"])
    want = ex.get("figure")
    if want is None:
        pick = figs[0]
    elif isinstance(want, int):
        pick = figs[want]
    else:
        m = [g for g in figs if g["name"] == want or g["file"] == want]
        if not m:
            raise BuildError("%s: 図 %r が無い(%s)" % (ex["id"], want, [g["name"] for g in figs]))
        pick = m[0]
    if not os.path.exists(os.path.join(d, pick["file"])):
        raise BuildError("%s: %s が無い" % (ex["id"], pick["file"]))
    return pick, figs


def _thumb(poc_id: str, file: str) -> str:
    """幅 720 px の JPEG サムネを作り、ファイル名を返す(既にあれば作り直さない)。"""
    from PIL import Image

    src = os.path.join(ASSETS, poc_id, file)
    name = os.path.splitext(file)[0] + "_720.jpg"
    dst = os.path.join(ASSETS, poc_id, name)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        im = Image.open(src).convert("RGB")
        if im.width > THUMB_W:
            im = im.resize((THUMB_W, max(1, round(im.height * THUMB_W / im.width))), Image.LANCZOS)
        im.save(dst, "JPEG", quality=JPEG_Q, optimize=True)
    return name


def _exhibit_md(n: int, ex: dict, lang: str, pick: dict, thumb: str, byid: dict) -> str:
    title = ex["title_" + lang]
    cap = ex["caption_" + lang]
    full = RAW + ex["id"] + "/" + pick["file"]
    th = RAW + ex["id"] + "/" + thumb
    run = ex.get("run") or ("py -3.11 examples/%s.py" % ex["id"])
    src = GH + "examples/%s.py" % ex["id"]
    lines = [
        "## %d. %s" % (n, title),
        "",
        "[![%s](%s)](%s)" % (title.replace("]", ")"), th, full),
        "",
        "*↑ **%s** ―― %s*" % (title, cap),
        "",
        "<!-- 静止サムネ: %s -->" % th,
        "<!-- 生成: examples/%s.py (FULLSEYE_FIGURE_DIR) / %s / %s / numbers: %s / added %s -->"
        % (ex["id"], pick["file"], pick.get("caption", "")[:80].replace("--", "—"),
           ex.get("numbers_source", "docstring"), ex["added"]),
        "",
        ("```\n%s\n```" % run),
        "",
        ("ソース: [%s](%s)" % ("examples/%s.py" % ex["id"], src)) if lang == "ja"
        else ("Source: [%s](%s)" % ("examples/%s.py" % ex["id"], src)),
        "",
    ]
    return "\n".join(lines)


def build(lang: str, cap: dict, byid: dict) -> tuple[str, str]:
    """(翼 md, 記事 md)。"""
    wings = sorted(cap["wings"], key=lambda w: w["order"])
    exhibits = cap["exhibits"]
    n = 0
    wing_parts = []
    latest = sorted(exhibits, key=lambda e: e["added"], reverse=True)[:8]
    for w in wings:
        exs = [e for e in exhibits if e["wing"] == w["id"]]
        if not exs:
            continue
        wing_parts.append("### %s" % w["title_" + lang])
        wing_parts.append("")
        wing_parts.append(w["placard_" + lang].strip())
        wing_parts.append("")
        for ex in exs:
            n += 1
            pick, _figs = _figure_for(ex)
            thumb = _thumb(ex["id"], pick["file"])
            wing_parts.append(_exhibit_md(n, ex, lang, pick, thumb, byid))
    total = n
    head = ("<!-- tools/gen_wingpoc_gallery.py が自動生成(単一真実源 = docs/articles/exhibits/poc_captions.json "
            "+ 各 PoC の figures.json)。手で編集しない。 -->" if lang == "ja" else
            "<!-- generated by tools/gen_wingpoc_gallery.py from docs/articles/exhibits/poc_captions.json "
            "+ each PoC's figures.json. Do not edit by hand. -->")
    wing_md = head + "\n\n" + "\n".join(wing_parts)
    ent = cap["entrance"]
    other = "en" if lang == "ja" else "ja"
    switch = ("> **言語 / Language**: **日本語** · [English](%s)" % (GH + "docs/articles/fullseye_poc_museum_qiita_en.md")
              if lang == "ja" else
              "> **Language**: [日本語](%s) · **English**" % (GH + "docs/articles/fullseye_poc_museum_qiita_ja.md"))
    title = ent["title_" + lang]
    tldr = "\n".join("- " + t for t in ent["tldr_" + lang])
    gl = "\n".join("- **%s** —— %s" % (t, e) for t, e in ent["glossary_" + lang])
    lat = "\n".join("- %s — %s(%s)" % (e["added"], e["title_" + lang], e["id"]) if lang == "ja"
                    else "- %s — %s (%s)" % (e["added"], e["title_" + lang], e["id"]) for e in latest)
    parts = [
        switch, "", "# " + title, "",
        ("> この記事は生成物です。展示の追加・修正は `docs/articles/exhibits/poc_captions.json` と各 PoC の図(`FULLSEYE_FIGURE_DIR`)で行い、`py -3.11 tools/gen_wingpoc_gallery.py` で組み直します。"
         if lang == "ja" else
         "> This article is generated. Exhibits are added or edited in `docs/articles/exhibits/poc_captions.json` plus each PoC's figures (`FULLSEYE_FIGURE_DIR`), then rebuilt with `py -3.11 tools/gen_wingpoc_gallery.py`."),
        "",
        "## TL;DR" , "", tldr, "",
        ("## 用語(先に読むと楽)" if lang == "ja" else "## Glossary (read this first)"), "", gl, "",
        ("## 展示館のテーゼ" if lang == "ja" else "## The museum's thesis"), "", ent["thesis_" + lang].strip(), "",
        ("## 最近の追加(新しい順)" if lang == "ja" else "## Recently added (newest first)"), "", lat, "",
        ("## 展示室(全 %d 展示)" % total if lang == "ja" else "## The wings (%d exhibits)" % total), "",
        wing_md, "",
        ("## 自分の問題に当てはめるには" if lang == "ja" else "## Bringing this to your own problem"), "",
        ent["howto_" + lang].strip(), "",
        ("## 正直に、まだ出来ないこと" if lang == "ja" else "## Honestly: what is not there yet"), "",
        ent["limits_" + lang].strip(), "",
        ("## 閉館の挨拶" if lang == "ja" else "## Closing"), "", ent["closing_" + lang].strip(), "",
        ent.get("credits_" + lang, "").strip(), "",
    ]
    return wing_md + "\n", "\n".join(parts).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cap, byid = _load()
    stale = []
    for lang in ("ja", "en"):
        wing_md, art_md = build(lang, cap, byid)
        for path, text in ((OUT_WING[lang], wing_md), (OUT_ARTICLE[lang], art_md)):
            if _LOCAL.search(text):
                raise BuildError("ローカルパスが混ざっている: %s" % path)
            cur = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if cur != text:
                stale.append(path)
                if not a.check:
                    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    if a.check:
        if stale:
            print("stale:", *stale, sep="\n  ")
            return 1
        print("up to date")
        return 0
    print("wrote", len(cap["exhibits"]), "exhibits ->", *OUT_ARTICLE.values(), sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
