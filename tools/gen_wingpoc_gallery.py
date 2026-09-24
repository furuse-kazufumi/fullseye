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
#: 総合案内。★既存の Qiita 枠がこのファイルを指しているので、名前を変えない ――
#: 外部リンク・LGTM・ストックはこの URL に付いている。館の入口に充てるのが筋。
OUT_ARTICLE = {"ja": os.path.join(_ROOT, "docs", "articles", "fullseye_poc_museum_qiita_ja.md"),
               "en": os.path.join(_ROOT, "docs", "articles", "fullseye_poc_museum_qiita_en.md")}
LEDGER = os.path.join(EXHIBITS, "exhibit_numbers.json")


def part_path(slug: str, lang: str) -> str:
    """棟 1 つの記事の置き場。"""
    return os.path.join(_ROOT, "docs", "articles",
                        "fullseye_poc_museum_%s_qiita_%s.md" % (slug, lang))


def _numbers() -> dict:
    """収蔵番号 ``id -> "2026.037"``。台帳が唯一の出どころ。"""
    with open(LEDGER, encoding="utf-8") as fh:
        return {k: v["no"] for k, v in json.load(fh)["issued"].items()}


def _qiita_items() -> dict:
    p = os.path.join(EXHIBITS, "qiita_items.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def _part_url(part: dict, lang: str, items: dict) -> str:
    """棟の記事 URL。投稿済みならその URL、まだなら GitHub の md。"""
    if part["kind"] == "external":
        key, rel = part["id"] + "." + lang, "docs/articles/" + part["article_" + lang]
    elif part["kind"] == "index":
        key, rel = lang, "docs/articles/fullseye_poc_museum_qiita_%s.md" % lang
    else:
        key = part["id"] + "." + lang
        rel = "docs/articles/fullseye_poc_museum_%s_qiita_%s.md" % (part["slug"], lang)
    return (items.get(key) or {}).get("url") or (GH + rel)

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


#: 1 展示に出す静止画の追加枚数。★2 枚固定をやめる(2026-09-24)
MORE_STATICS = 4


def _more_statics(figs, pick, second):
    """主図・2 枚目・動く図を除いた静止画から、間隔をあけて数枚選ぶ。

    ★先頭から詰めて取ると章の前半に偏るので、**等間隔に間引く** ——
    どの章からも 1 枚は出るようにするため。
    """
    rest = [g for g in figs
            if g is not pick and g is not second and not g.get("animated")]
    if len(rest) <= MORE_STATICS:
        return rest
    step = len(rest) / float(MORE_STATICS)
    return [rest[min(int(i * step), len(rest) - 1)] for i in range(MORE_STATICS)]


def _first_sentence(text: str, limit: int = 150) -> str:
    """説明の**最初の 1 文**だけを返す(記事の肥大を抑える)。"""
    t = (text or "").strip()
    for mark in ("。", ". "):
        i = t.find(mark)
        if 0 < i <= limit:
            return t[:i + len(mark)].strip()
    return t[:limit].rstrip() + ("…" if len(t) > limit else "")


def _thumb(poc_id: str, file: str) -> str:
    """幅 720 px の JPEG サムネを作り、ファイル名を返す(既にあれば作り直さない)。

    ★**動く図(.gif)はそのまま返す**。JPEG に落とすと 1 コマ目の静止画になり、
    記事では「クリックしないと動かない絵」になってしまう ―― 動きが主題の図で
    それをやると、展示の意味が消える(2026-09-09、回転の展示で気づいた)。
    静止の完成形は別の図として同じ展示に並んでいるので、静的な受け皿もある。
    """
    if file.lower().endswith(".gif"):
        return file

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


def _figures_line(poc_id: str, lang: str) -> str:
    """その PoC が作った図の**全部**へのリンクと枚数。

    ★展示ブロックに出るのは主図と測定の図だけで、残りは repo にあるのに
    記事から辿れなかった(実測: 1,165 枚中 317 枚しか参照されていない)。
    """
    d = os.path.join(ASSETS, poc_id)
    n = 0
    if os.path.isdir(d):
        n = len([f for f in os.listdir(d)
                 if f.lower().endswith((".png", ".gif"))
                 and not f.endswith("_720.jpg")])
    url = ("https://github.com/furuse-kazufumi/fullseye/tree/master/"
           "docs/articles/assets/poc/" + poc_id)
    if lang == "ja":
        return "この回が作った図は全部で **%d 枚**あります —— [全部見る](%s)" % (n, url)
    return "This run produced **%d figures** in total - [see them all](%s)" % (n, url)


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


def _exhibit_md(no: str, ex: dict, lang: str, pick: dict, thumb: str, byid: dict,
                second: dict | None = None, thumb2: str | None = None,
                extras: list | None = None, more: list | None = None) -> str:
    title = ex["title_" + lang]
    cap = ex["caption_" + lang]
    full = RAW + ex["id"] + "/" + pick["file"]
    th = RAW + ex["id"] + "/" + thumb
    run = ex.get("run") or ("py -3.11 examples/%s.py" % ex["id"])
    src = GH + "examples/%s.py" % ex["id"]
    lines = [
        # ★見出しは**収蔵番号**。順路番号(何番目か)は出さない —— 展示を 1 つ挟むだけで
        #   以降が全部ずれ、記事を分けるたびに番号が動くため(2026-09-25)。
        "## No.%s —— %s" % (no, title),
        "",
        "[![%s](%s)](%s)" % (title.replace("]", ")"), th, full),
        "",
        "*↑ **%s** ―― %s*" % (title, cap),
        "",
    ]
    if second is not None and thumb2 is not None:
        full2 = RAW + ex["id"] + "/" + second["file"]
        th2 = RAW + ex["id"] + "/" + thumb2
        # 図に説明が付いていなければ機械名(`auc_by_type` など)は出さない
        sub = (second.get("caption") or "").strip()
        alt = (sub[:120] if sub else ("測定の図" if lang == "ja" else "measurement")).replace("]", ")")
        if lang == "ja":
            cap_line = ("*↑ 測定の図 ―― %s*" % sub) if sub else "*↑ 測定の図*"
        else:
            tail = "(figure labels are in Japanese; the numbers are the same)"
            cap_line = ("*↑ The measurement ―― %s %s*" % (sub, tail)) if sub else ("*↑ The measurement %s*" % tail)
        lines += ["[![%s](%s)](%s)" % (alt, th2, full2), "", cap_line, ""]
    # 看板にも 2 枚目にも入らなかった**動く図**は全部出す —— GIF を落とすと「クリックしないと
    # 動かない絵」になり、動きが主題の展示ではそれで意味が消える(2026-09-21、GIF 2 本の展示で気づいた)。
    # ★追加の静止画。説明は 1 文に切る(枚数を増やすのが目的で、詳しい
    #   説明は主図と 2 枚目が持っている)。2026-09-24 に 2 枚固定をやめた。
    for fig in (more or []):
        full4 = RAW + ex["id"] + "/" + fig["file"]
        th4 = RAW + ex["id"] + "/" + _thumb(ex["id"], fig["file"])
        sub_ = _first_sentence(fig.get("caption") or "")
        alt = (sub_[:100] if sub_ else "図").replace("]", ")")
        cap_line = ("*↑ %s*" % sub_) if sub_ else "*↑ この回の図*"
        lines += ["[![%s](%s)](%s)" % (alt, th4, full4), "", cap_line, ""]
    for fig in (extras or []):
        full3 = RAW + ex["id"] + "/" + fig["file"]
        sub = (fig.get("caption") or "").strip()
        alt = (sub[:120] if sub else ("動く図" if lang == "ja" else "animation")).replace("]", ")")
        if lang == "ja":
            cap_line = ("*↑ 動く図 ―― %s*" % sub) if sub else "*↑ 動く図*"
        else:
            cap_line = ("*↑ The animation ―― %s*" % sub) if sub else "*↑ The animation*"
        lines += ["[![%s](%s)](%s)" % (alt, full3, full3), "", cap_line, ""]
    # 生成の内幕(サムネ URL・FULLSEYE_FIGURE_DIR・数字の出所)は記事に出さない
    # (ユーザー指示 2026-09-07「読者の ROI と関係ない独自ルールは書かない」)。
    lines += [
        ("```\n%s\n```" % run),
        "",
        ("ソース: [%s](%s)" % ("examples/%s.py" % ex["id"], src)) if lang == "ja"
        else ("Source: [%s](%s)" % ("examples/%s.py" % ex["id"], src)),
        "",
        # ★展示に載るのは 1 本あたり 2 枚ほど。PoC は中央値 6 枚・最大 25 枚
        #   作っているので、**残りへの道**を必ず出す(2026-09-24、ユーザー指摘
        #   「生成した数百枚はどこにあるのか記事からは分からない」)。
        _figures_line(ex["id"], lang),
        "",
        _ops_line(ex["id"], lang),
        "",
    ]
    return "\n".join(lines)


def _wing_sections(lang: str, cap: dict, byid: dict, nos: dict, wings: list) -> tuple[str, int]:
    """指定した翼の展示を並べる。``(markdown, 展示数)``。

    ★番号は台帳から引く。ここで数えないのは、数えた番号は**並びを変えると動く**からで、
    動く番号は読者の索引としても外部リンクの宛先としても使えない。
    """
    exhibits = cap["exhibits"]
    parts, n = [], 0
    for w in sorted(cap["wings"], key=lambda w: w["order"]):
        if w["id"] not in wings:
            continue
        exs = [e for e in exhibits if e["wing"] == w["id"]]
        if not exs:
            continue
        parts += ["### %s" % w["title_" + lang], "", w["placard_" + lang].strip(), ""]
        for ex in exs:
            n += 1
            pick, figs, second = _figure_for(ex)
            thumb = _thumb(ex["id"], pick["file"])
            thumb2 = _thumb(ex["id"], second["file"]) if second is not None else None
            more = _more_statics(figs, pick, second)
            extras = [g for g in figs if g.get("animated") and g is not pick and g is not second
                      and os.path.exists(os.path.join(ASSETS, ex["id"], g["file"]))]
            parts.append(_exhibit_md(nos[ex["id"]], ex, lang, pick, thumb, byid,
                                     second, thumb2, extras, more))
    return "\n".join(parts), n


def _switch(lang: str, url: str) -> str:
    return ("> **言語 / Language**: **日本語** · [English](%s)" % url if lang == "ja"
            else "> **Language**: [日本語](%s) · **English**" % url)


def build_wing_md(lang: str, cap: dict, byid: dict, nos: dict) -> str:
    """docs サイト用の翼ページ。**全部の展示**を 1 枚に並べる(収蔵目録に当たる)。"""
    all_wings = [w["id"] for w in cap["wings"]]
    body, _n = _wing_sections(lang, cap, byid, nos, all_wings)
    return "<!-- generated -->\n\n" + body + "\n"


def build_entrance(lang: str, cap: dict, byid: dict, nos: dict) -> str:
    """総合案内。**目次を持つのはここだけ**。

    各棟が全体の目次を持つと、棟を 1 つ足すたびに全部の記事を投稿し直すことになる。
    博物館と同じく、案内を 1 か所に置いて各棟からはそこへ 1 行返す。
    """
    ent, meta = cap["entrance"], cap["meta"]
    items = _qiita_items()
    other = "en" if lang == "ja" else "ja"
    title = ent.get("title_" + lang) or meta["title_" + lang]
    tldr = "\n".join("- " + t for t in ent["tldr_" + lang])
    gl = "\n".join("- **%s** —— %s" % (t, e) for t, e in ent["glossary_" + lang])
    latest = sorted(cap["exhibits"], key=lambda e: e["added"], reverse=True)[:8]
    lat = "\n".join(
        ("- %s — No.%s %s" % (e["added"], nos[e["id"]], e["title_" + lang])) for e in latest)
    hero_cap = ("*↑ 展示の場面図を 12 枚並べたもの。どれも PoC スクリプト自身の出力で、記事のために描いた絵は 1 枚もありません。*"
                if lang == "ja" else
                "*↑ Twelve exhibit scenes side by side. Every tile is the PoC script's own output; nothing was drawn for the article.*")
    # 棟の目次。★展示数は毎回数えて出す(手で書くと必ず古くなる)。
    counts = {}
    for e in cap["exhibits"]:
        counts[e["wing"]] = counts.get(e["wing"], 0) + 1
    rows = [("| 記事 | 展示室 | 展示数 |" if lang == "ja" else "| Article | Wings | Exhibits |"),
            "|---|---|---:|"]
    #: 目次に出す短い翼名。★区切りは ` / ` —— 翼名そのものに「・」が入るので
    #: (寸法・形状計測 / 医用・生物 / 色・分離)、「・」で繋ぐと境目が読めなくなる。
    def _short(w):
        t = w["title_" + lang].split(" ―― ")[0].split(" — ")[0].strip()
        for suffix in ("ウィング", " Wing", " wing"):
            if t.endswith(suffix):
                t = t[: -len(suffix)].strip()
        return t
    wt = {w["id"]: _short(w) for w in cap["wings"]}
    for p in meta["parts"]:
        if p["kind"] == "index":
            continue
        n = sum(counts.get(w, 0) for w in p["wings"])
        rows.append("| [%s](%s) | %s | %d |" % (p["title_" + lang], _part_url(p, lang, items),
                                                " / ".join(wt[w] for w in p["wings"]), n))
    index_note = ("この館は記事を分けています。**どの棟も単体で読めます** —— "
                  "下の表から入ってください。番号(`No.2026.037`)は**収蔵番号**で、"
                  "棟を移しても分けても変わりません。"
                  if lang == "ja" else
                  "The museum is split across several articles; **each wing reads on its own** — "
                  "pick one below. The numbers (`No.2026.037`) are accession numbers: they do not "
                  "change when an exhibit moves between articles or when an article is split.")
    parts = [
        _switch(lang, _part_url(meta["parts"][0], other, items)), "",
        "# " + title, "",
        "![%s](%s)" % ("PoC museum montage", RAW + _hero_montage(cap)), "", hero_cap, "",
        ("> 図と op の使い方は docs サイト [furuse.work](https://furuse.work/) と共通です。各展示の「使用 op」から op ノート(型契約・罠・図・Studio で走るプログラム)へ飛べます。AI に読ませるなら [AI_RAG_GUIDE](https://furuse.work/AI_RAG_GUIDE.html)。"
         if lang == "ja" else
         "> Figures and op usage are shared with the docs site [furuse.work](https://furuse.work/). The \"Ops used\" line under each exhibit jumps to the op notes (type contracts, pitfalls, figures, runnable Studio programs). For AI readers: [AI_RAG_GUIDE](https://furuse.work/AI_RAG_GUIDE.html)."), "",
        ("## TL;DR" if lang == "ja" else "## TL;DR"), "", tldr, "",
        *(([("## 版の更新(新しい順)" if lang == "ja" else "## Version updates (newest first)"), "",
            ent["news_" + lang].strip(), ""]) if "news_" + lang in ent else []),
        ("## 展示室の案内" if lang == "ja" else "## Where to go"), "", index_note, "",
        *rows, "",
        ("## 用語(先に読むと楽)" if lang == "ja" else "## Glossary (read this first)"), "", gl, "",
        ("## 展示館のテーゼ" if lang == "ja" else "## The museum's thesis"), "",
        ent["thesis_" + lang].strip(), "",
        ("## 最近の追加(新しい順)" if lang == "ja" else "## Recently added (newest first)"), "", lat, "",
    ]
    parts += _closing(ent, lang)
    return "\n".join(parts).rstrip() + "\n"


def build_part(part: dict, lang: str, cap: dict, byid: dict, nos: dict) -> str:
    """棟 1 つ。★**全体の目次は持たない** —— 案内へ 1 行返すだけ。

    棟どうしの「前 / 次」も置かない。間に棟を挿入すると両隣が壊れるため。
    """
    ent, meta, items = cap["entrance"], cap["meta"], _qiita_items()
    other = "en" if lang == "ja" else "ja"
    body, n = _wing_sections(lang, cap, byid, nos, part["wings"])
    home = _part_url(meta["parts"][0], lang, items)
    back = ("> **[紙面の計測館 総合案内](%s)** の一棟です。ほかの棟・用語・テーゼは案内にあります。"
            % home if lang == "ja" else
            "> One wing of **[A Metrology Museum on Paper — the entrance](%s)**, where the other "
            "wings, the glossary and the thesis live." % home)
    lead = (("この棟には **%d 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。"
             % n) if lang == "ja" else
            ("**%d exhibits** hang in this wing. The numbers are accession numbers: they do not "
             "change when an exhibit moves or when an article is split." % n))
    parts = [
        _switch(lang, _part_url(part, other, items)), "",
        "# " + part["title_" + lang], "",
        back, "", lead, "",
        ("> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。"
         if lang == "ja" else
         "> The \"Ops used\" line under each exhibit links to that op's note (type contract, pitfalls, figures, a runnable Studio program): [Operator catalogue](https://furuse.work/OP_CATALOG.html) / [Op notes index](https://furuse.work/ops/INDEX.html)."),
        "", body, "",
    ]
    parts += [ent.get("credits_" + lang, "").strip(), "",
              ent.get("cta_" + lang, "").strip(), ""]
    return "\n".join(parts).rstrip() + "\n"


def _closing(ent: dict, lang: str) -> list:
    """閉館部。JSON が howto/limits を別キーで持つ版と closing に見出し込みで持つ版の両方を受ける。"""
    closing = ent["closing_" + lang].strip()
    out = []
    if "howto_" + lang in ent:
        out += [("## 自分の問題に当てはめるには" if lang == "ja" else "## Bringing this to your own problem"),
                "", ent["howto_" + lang].strip(), ""]
    if "limits_" + lang in ent:
        out += [("## 正直に、まだ出来ないこと" if lang == "ja" else "## Honestly: what is not there yet"),
                "", ent["limits_" + lang].strip(), ""]
    if not re.match(r"^#+ ", closing):
        out += [("## 閉館の挨拶" if lang == "ja" else "## Closing"), ""]
    out += [closing, "", ent.get("credits_" + lang, "").strip(), "",
            ent.get("cta_" + lang, "").strip(), ""]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cap, byid = _load()
    nos = _numbers()
    missing = sorted(e["id"] for e in cap["exhibits"] if e["id"] not in nos)
    if missing:
        raise BuildError("収蔵番号が無い展示: %s(tools/gen_exhibit_numbers.py で発行する)"
                         % ", ".join(missing))
    stale = []
    for lang in ("ja", "en"):
        out = [(OUT_WING[lang], build_wing_md(lang, cap, byid, nos)),
               (OUT_ARTICLE[lang], build_entrance(lang, cap, byid, nos))]
        for p in cap["meta"]["parts"]:
            #: ★`external` の部(手書きの数学記事)は描かない。`index` は案内なので上で出した。
            if p["kind"] != "generated":
                continue
            out.append((part_path(p["slug"], lang), build_part(p, lang, cap, byid, nos)))
        for path, text in out:
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
    gen = [p for p in cap["meta"]["parts"] if p["kind"] == "generated"]
    print("wrote %d exhibits -> 案内 1 + 棟 %d(x2 言語)" % (len(cap["exhibits"]), len(gen)))
    for p in gen:
        n = sum(1 for e in cap["exhibits"] if e["wing"] in p["wings"])
        print("  %-18s %3d 展示  %s" % (p["slug"], n, os.path.basename(part_path(p["slug"], "ja"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
