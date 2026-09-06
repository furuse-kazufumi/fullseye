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
_SCENE = re.compile(r"scene|input|overlay|montage|frame|before|after|mask|image|map|panel|track|recon|render|stack|field|labels|segment|view")


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
        # 見た目重視: 「場面」の図(scene / input / overlay / montage …)があればそれを
        # 看板にし、測定のグラフは 2 枚目に回す。無ければ 1 枚目。
        scene = [g for g in figs if _SCENE.search(g["name"])]
        pick = scene[0] if scene else figs[0]
    elif isinstance(want, int):
        pick = figs[want]
    else:
        m = [g for g in figs if g["name"] == want or g["file"] == want]
        if not m:
            raise BuildError("%s: 図 %r が無い(%s)" % (ex["id"], want, [g["name"] for g in figs]))
        pick = m[0]
    if not os.path.exists(os.path.join(d, pick["file"])):
        raise BuildError("%s: %s が無い" % (ex["id"], pick["file"]))
    # 2 枚目 = 看板と違う最初の図(測定のグラフ)。「1 枚に纏めない」(ユーザー方針)。
    second = next((g for g in figs if g is not pick), None)
    return pick, figs, second


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


MONTAGE = "_hero_montage.jpg"
MONTAGE_TILE = (400, 267)     # 3:2 のタイル。4 × 3 = 1600 × 801 px
MONTAGE_GRID = (4, 3)


def _hero_montage(cap: dict) -> str:
    """看板画像: 各ウィング先頭の展示の「場面」図を中央クロップして 4 × 3 に並べる。
    素材は PoC 自身の出力(モックアップ禁止)。ウィングが 12 未満なら残りは追加日の新しい
    展示で埋める。返り値はファイル名(ASSETS 直下)。"""
    from PIL import Image

    tiles = list(cap["meta"].get("hero_tiles") or [])
    if not tiles:   # 指定が無ければ各ウィング先頭の展示の場面図、足りなければ新しい順
        wings = sorted(cap["wings"], key=lambda w: w["order"])
        order, seen = [], set()
        for w in wings:
            for e in cap["exhibits"]:
                if e["wing"] == w["id"]:
                    order.append(e); seen.add(e["id"]); break
        for e in sorted(cap["exhibits"], key=lambda e: e["added"], reverse=True):
            if e["id"] not in seen:
                order.append(e); seen.add(e["id"])
        tiles = [e["id"] + "/" + _figure_for(e)[0]["file"] for e in order]
    # 雑誌の見開き風: 行の高さを揃え、図を高さに合わせて縮めて左から詰める(隙間なし)。
    # 各図は切らずに入れ、行の右端にはみ出た分だけ切る。タイルが尽きたら先頭から繰り返す。
    cols, rows = MONTAGE_GRID
    tw, th = MONTAGE_TILE
    W = cols * tw
    sheet = Image.new("RGB", (W, rows * th), (24, 24, 28))
    ims = []
    for rel in tiles:
        src = os.path.join(ASSETS, rel.replace("/", os.sep))
        if not os.path.exists(src):
            raise BuildError("hero_tiles: %s が無い" % rel)
        im = Image.open(src).convert("RGB")
        ims.append(im.resize((max(1, round(im.width * th / im.height)), th), Image.LANCZOS))
    if not ims:
        raise BuildError("hero_tiles が空")
    k = 0
    for r in range(rows):
        x = 0
        while x < W:
            im = ims[k % len(ims)]
            k += 1
            sheet.paste(im.crop((0, 0, min(im.width, W - x), th)), (x, r * th))
            x += im.width + 2   # 2 px の黒い目地
    dst = os.path.join(ASSETS, MONTAGE)
    buf = io.BytesIO()
    sheet.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
    data = buf.getvalue()
    # 内容が同じなら書かない(mtime だけ動いて差分に見えるのを避ける)
    if not (os.path.exists(dst) and io.open(dst, "rb").read() == data):
        io.open(dst, "wb").write(data)
    return MONTAGE


_OP_URL = None


def _op_url_table() -> dict:
    """op 名 → docs サイトのノート URL(https://furuse.work/ops/<dim>/<cat>/<op>.html)。"""
    global _OP_URL
    if _OP_URL is not None:
        return _OP_URL
    sys.path.insert(0, os.path.join(_ROOT, "tools"))
    import opdocs as OD
    recs, _i, _f, _g = OD._records()
    tbl = {}
    for r in recs:
        p = OD._op_path(r).replace("\\", "/")
        rel = p[p.index("docs/ops/") + len("docs/"):-3] + ".html"
        tbl.setdefault(r["name"], "https://furuse.work/" + rel)
    _OP_URL = tbl
    return tbl


def _ops_used(poc_id: str) -> list:
    """PoC スクリプトが実際に呼んでいる op(例索引と同じ検出規則)。手で書かない。"""
    import op_example_index as OEI
    src = io.open(os.path.join(_ROOT, "examples", poc_id + ".py"), encoding="utf-8").read()
    tbl = _op_url_table()
    return sorted(n for n in tbl if len(n) >= 4 and OEI._called(n, src))


def _ops_line(poc_id: str, lang: str) -> str:
    """「使用 op」行。細かい説明は書かず、ノート(ヘルプの目録)へのリンクに任せる
    (ユーザー方針 2026-09-07「ヘルプの目録へのリンクを貼っておけば細かい説明はいらない」)。"""
    tbl = _op_url_table()
    names = _ops_used(poc_id)
    if not names:
        return ""
    links = " · ".join("[`%s`](%s)" % (n, tbl[n]) for n in names[:24])
    more = "" if len(names) <= 24 else (" …(他 %d)" % (len(names) - 24) if lang == "ja" else " … (+%d)" % (len(names) - 24))
    return ("使用 op(ノートへ): " if lang == "ja" else "Ops used (notes): ") + links + more


def _exhibit_md(n: int, ex: dict, lang: str, pick: dict, thumb: str, byid: dict,
                second: dict | None = None, thumb2: str | None = None) -> str:
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
    ]
    if second is not None and thumb2 is not None:
        full2 = RAW + ex["id"] + "/" + second["file"]
        th2 = RAW + ex["id"] + "/" + thumb2
        sub = second.get("caption") or second["name"]
        lines += [
            "[![%s](%s)](%s)" % (sub.replace("]", ")")[:120], th2, full2),
            "",
            ("*↑ 測定の図 ―― %s*" % sub if lang == "ja"
             else "*↑ The measurement ―― %s (figure labels are in Japanese; the numbers are the same)*" % sub),
            "",
        ]
    lines += [
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
        _ops_line(ex["id"], lang),
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
            pick, _figs, second = _figure_for(ex)
            thumb = _thumb(ex["id"], pick["file"])
            thumb2 = _thumb(ex["id"], second["file"]) if second is not None else None
            wing_parts.append(_exhibit_md(n, ex, lang, pick, thumb, byid, second, thumb2))
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
    title = ent.get("title_" + lang) or cap["meta"]["title_" + lang]
    tldr = "\n".join("- " + t for t in ent["tldr_" + lang])
    gl = "\n".join("- **%s** —— %s" % (t, e) for t, e in ent["glossary_" + lang])
    lat = "\n".join("- %s — %s(%s)" % (e["added"], e["title_" + lang], e["id"]) if lang == "ja"
                    else "- %s — %s (%s)" % (e["added"], e["title_" + lang], e["id"]) for e in latest)
    hero = RAW + _hero_montage(cap)
    hero_line = ("![%s](%s)" % ("PoC museum montage", hero))
    hero_cap = ("*↑ 展示の場面図を 12 枚並べたもの。どれも PoC スクリプト自身の出力で、記事のために描いた絵は 1 枚もありません。*"
                if lang == "ja" else
                "*↑ Twelve exhibit scenes side by side. Every tile is the PoC script's own output; nothing was drawn for the article.*")
    funnel = ("> 図と op の使い方は docs サイト [furuse.work](https://furuse.work/) と共通です。各展示の「使用 op」から op ノート(型契約・罠・図・Studio で走るプログラム)へ飛べます。AI に読ませるなら [AI_RAG_GUIDE](https://furuse.work/AI_RAG_GUIDE.html)。"
              if lang == "ja" else
              "> Figures and op usage are shared with the docs site [furuse.work](https://furuse.work/). The \"Ops used\" line under each exhibit jumps to the op notes (type contracts, pitfalls, figures, runnable Studio programs). For AI readers: [AI_RAG_GUIDE](https://furuse.work/AI_RAG_GUIDE.html).")
    parts = [
        switch, "", "# " + title, "",
        hero_line, "", hero_cap, "",
        funnel, "",
        ("> この記事は生成物です。展示の追加・修正は `docs/articles/exhibits/poc_captions.json` と各 PoC の図(`FULLSEYE_FIGURE_DIR`)で行い、`py -3.11 tools/gen_wingpoc_gallery.py` で組み直します。"
         if lang == "ja" else
         "> This article is generated. Exhibits are added or edited in `docs/articles/exhibits/poc_captions.json` plus each PoC's figures (`FULLSEYE_FIGURE_DIR`), then rebuilt with `py -3.11 tools/gen_wingpoc_gallery.py`."),
        "",
        "## TL;DR" , "", tldr, "",
        ("> 各展示の細かい説明は書きません。使っている op の**ヘルプの目録**(op ごとのノート・図・Studio で走るプログラム)へのリンクを付けてあります: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。"
         if lang == "ja" else
         "> Exhibits are not explained in detail on purpose. Each one links to the **help catalogue** for the ops it uses (per-op notes with figures and runnable Studio programs): [Operator catalogue](https://furuse.work/OP_CATALOG.html) / [Op notes index](https://furuse.work/ops/INDEX.html)."),
        "",
        ("## 用語(先に読むと楽)" if lang == "ja" else "## Glossary (read this first)"), "", gl, "",
        ("## 展示館のテーゼ" if lang == "ja" else "## The museum's thesis"), "", ent["thesis_" + lang].strip(), "",
        ("## 最近の追加(新しい順)" if lang == "ja" else "## Recently added (newest first)"), "", lat, "",
        ("## 展示室(全 %d 展示)" % total if lang == "ja" else "## The wings (%d exhibits)" % total), "",
        wing_md, "",
    ]
    # 閉館部: JSON が howto/limits を別キーで持つ版と、closing に「## 見出し」込みで
    # 持つ版の両方を受ける(closing に見出しがあればそのまま貼る)。
    closing = ent["closing_" + lang].strip()
    if "howto_" + lang in ent:
        parts += [("## 自分の問題に当てはめるには" if lang == "ja" else "## Bringing this to your own problem"), "",
                  ent["howto_" + lang].strip(), ""]
    if "limits_" + lang in ent:
        parts += [("## 正直に、まだ出来ないこと" if lang == "ja" else "## Honestly: what is not there yet"), "",
                  ent["limits_" + lang].strip(), ""]
    if not re.match(r"^#+ ", closing):
        parts += [("## 閉館の挨拶" if lang == "ja" else "## Closing"), ""]
    parts += [closing, "", ent.get("credits_" + lang, "").strip(), "",
              ent.get("cta_" + lang, "").strip(), ""]   # 招待リンク + いいね依頼(ユーザー指示 2026-09-07)
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
