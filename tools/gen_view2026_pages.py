#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の案内ページ(論文の QR コードの行き先)を 7 言語ぶん生成する。

    py -3.11 tools/gen_view2026_pages.py           # 書く
    py -3.11 tools/gen_view2026_pages.py --check   # 書かずに、commit 済みと食い違えば exit 1

正本は ``docs/view2026/exhibits.json`` の 1 本だけ。展示を足す・数字を直すのはそこで 1 回。
数値と図の経路は全言語で共有し、文字列だけを訳す。出力:

* ``docs/view2026/index.md``        → https://furuse.work/view2026/      (ja、QR の行き先)
* ``docs/view2026/<lang>/index.md`` → https://furuse.work/view2026/<lang>/ (exhibits.json の langs の ja 以外)

ページの並び(スマートフォンで開かれる前提):

0. 触って見る —— ``viewers``(``docs/view2026/viewers/*.html``、``tools/build_view2026_viewers.py`` が各 PoC を
   走らせて作る自己完結の HTML)への 7 本。リンクは ``?lang=<そのページの言語>`` 付きで、ビューアが同じ言語で開く。
1. 見どころ —— 手で選んだ展示のサムネイルの格子(``exhibits``)。押すと動画・GIF・原寸の図。
2. シリーズ記事 —— 大きいタイル(``series``)。各シリーズの Qiita 記事(公開のもの)へ。
3. できること —— ``docs/capabilities/*.md`` の全件を分類ごとに。各行から説明のページと走る例へ。
   その下に PoC 以外の使用例の一覧(``examples/README.md``)へのリンクと本数。
   ★2026-10-11 まで PoC しか載せておらず、「生成 AI の画像の文字を直す」(fix-text-in-images)
   のような**PoC でない機能は案内ページから辿れなかった**(ユーザー指摘)。
4. ぜんぶ見る —— ``all`` の全部を群ごとの ``<details>``(閉じた状態)に。本数は生成時に数える。
   ★Chrome は閉じた ``<details>`` の中の ``loading="lazy"`` の画像も取りに行く(2026-10-11 に
   手元の HTTP サーバのログで確認)。だからここのサムネイルは ``data-src`` に置き、開いたときに
   小さな JS で ``src`` へ移す。JS が無ければサムネイルは出ないが、タイルの文字とリンクは働き、
   ギャラリーのページへの案内を ``<noscript>`` で出す。
4. 見どころの説明と、真値に対する数字。5. Fullseye とは / 試す / リンク / 論文情報(畳む)。

サムネイルは ``tools/gen_view2026_thumbs.py`` が作る。

動く 3-D(分類 ``anim3d``): 見どころの 1 本として ``media_path`` に自己完結の HTML
(``docs/view2026/anim3d/<id>.html``、``tools/anim3d_i18n.py --build`` が 8 言語で書く)を置く。
タイルと一覧のリンクは ``?lang=<そのページの言語>`` 付き(ビューアは ?lang が無ければブラウザの言語で開く)、
容量(MB)はファイルから数えてタイルと一覧に出す(スマートフォンで開く前に重さが分かるように)。
HTML が 8 言語そろっていない(``"langs"`` に足りない言語がある)なら止める。

★生成の前に検査して、通らなければ何も書かない(fail-closed):
  * 全言語の文字列がそろっている / 図・サムネイル・例のスクリプトが実在する
  * **説明文と数字に出てくる数の並びが、全言語で日本語と同じ**(訳で数字が化けない)
  * ``poc_captions.json`` の展示が 1 本残らず ``all`` に在る(新しい PoC を載せ忘れない)
  * ``docs/capabilities/*.md`` が 1 件残らず訳つきで載り、そこが挙げる例が実在する
  * シリーズの行き先は ``https://qiita.com/furuse-kazufumi/items/`` の公開記事だけ(``/private/`` を拒む)
  * 日本語以外のページに、印(``_(ja)_``)の無いかなが無い / Liquid の開き記号が無い
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
from exhibit_glossary import LEDGER as GLOSSARY_LEDGER, glossary_line, load_glossary

DOCS = ROOT / "docs"
BASE = DOCS / "view2026"
DATA = BASE / "exhibits.json"
GH_EXAMPLE = "%s/blob/master/examples/%s.py"
QIITA = "https://qiita.com/furuse-kazufumi/items/"
JA_MARK = "_(ja)_"                     # tools/i18n_status.py の印と同じ
PIXEL = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
_KANA = re.compile(r"[぀-ヿ]")
_GARBLE = re.compile(r"\ufffd|\?{3,}|(?<=\d)\?(?=\d)")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_LIQUID = re.compile(re.escape("{" + "{") + "|" + re.escape("{" + "%"))

STYLE = """<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
.vg.vs { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.vg a, .vser a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vg.vs span { font-size: 11px; }
.vser { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vser { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.vser img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 8px; background: #222; }
.vser strong { display: block; font-size: 14px; margin-top: 3px; line-height: 1.3; }
.vser span { display: block; font-size: 12px; line-height: 1.3; }
details.vall { margin: 6px 0; }
details.vall > summary { font-size: 15px; padding: 6px 0; cursor: pointer; }
.vl li { margin-bottom: 8px; }
</style>"""

#: 「ぜんぶ見る」の群を開いたときに data-src を src へ移す(全ページ)。無くても読める。
LAZY = """<script>
document.querySelectorAll("details.vall").forEach(function (d) {
  d.addEventListener("toggle", function () {
    if (!d.open) return;
    d.querySelectorAll("img[data-src]").forEach(function (i) {
      i.src = i.getAttribute("data-src"); i.removeAttribute("data-src");
    });
  });
});
</script>"""

#: ja の入口ページだけに置く。初回の訪問で、ブラウザの言語が ja 以外の言語なら 1 度だけそのページへ送る。
#: サイト内から来た(言語の切り替えを押した)ときと、2 回目以降は送らない。JS が無くても全部読める。
REDIRECT = """<script>
(function () {
  try {
    var k = "fullseye_view2026_lang";
    if (localStorage.getItem(k)) return;
    localStorage.setItem(k, "seen");
    if (document.referrer && document.referrer.indexOf(location.host) >= 0) return;
    var n = (navigator.language || "").toLowerCase(), t = "";
    if (n.indexOf("zh") === 0) t = /tw|hk|mo|hant/.test(n) ? "tw" : "zh";
    else if (/^(@LATIN@)/.test(n)) t = n.slice(0, 2);
    if (t) location.replace(t + "/");
  } catch (e) {}
})();
</script>"""

TRY_CMD = """```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```"""


def load(path: Path = DATA) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _glossary_inputs() -> tuple[dict, dict]:
    rows = json.loads(GLOSSARY_LEDGER.read_text(encoding="utf-8"))["exhibits"]
    return {row["id"]: row for row in rows}, load_glossary()


def _media_rel(d: dict, e: dict) -> str:
    """docs/ からの相対の図の経路。"""
    return e["media_path"] if e.get("media_path") else "%s/%s/%s" % (d["media_root"], e["id"], e["media"])


def _source(d: dict, e: dict) -> str:
    """ソースへのリンク(``source_url`` が在ればそれ。空文字ならリンクを出さない)。"""
    if "source_url" in e:
        return e["source_url"]
    return GH_EXAMPLE % (d["repo"], e["id"])


def _is_viewer(d: dict, e: dict) -> bool:
    """図の代わりに触って見る HTML(動く 3-D)か。"""
    return _media_rel(d, e).endswith(".html")


def _viewer_mb(d: dict, e: dict) -> str:
    """HTML の容量(MB、小数 1 桁、最小 0.1)。手で書かない。"""
    return "%.1f MB" % max(0.1, (DOCS / _media_rel(d, e)).stat().st_size / 1e6)


def _viewer_langs(path: Path) -> list[str]:
    """自己完結のビューア HTML に埋めた言語の一覧(``"langs":[...]``)。"""
    m = re.search(r'"langs":\[([^\]]*)\]', path.read_text(encoding="utf-8"))
    return re.findall(r'"([a-z]{2})"', m.group(1)) if m else []


def validate(d: dict) -> list[str]:
    """問題の一覧(空なら合格)。"""
    bad = []
    langs = d["langs"]
    if langs[0] != "ja":
        bad.append("langs の先頭は ja(QR の行き先)でなければならない")

    def full(name, tr, allow_empty=False):
        empty = [l for l in langs if not str(tr.get(l, "")).strip()]
        if allow_empty and len(empty) == len(langs):
            return
        if empty:
            bad.append("%s: 訳が無い言語 %s" % (name, empty))
        # ★2026-10-30: 2 つの展示の日本語が 10/27 から「???…」のまま載っていた(× と − も全言語で ? に)。
        #   文字コードの往復で失われた文字は ? か U+FFFD になる。どちらも訳として通さない。
        for l in langs:
            m = _GARBLE.search(str(tr.get(l, "")))
            if m:
                bad.append("%s [%s]: 文字化け(%r) —— 元の文字を復元すること" % (name, l, m.group(0)))

    for k, tr in d["ui"].items():
        if k in ("title_tr", "series_lang_note"):      # ja だけ空(日本語では要らない)
            full("ui." + k, {l: v for l, v in tr.items() if l != "ja"} | {"ja": "-"})
        else:
            full("ui." + k, tr)
    vw = d["viewers"]
    full("viewers.h", vw["h"])
    full("viewers.intro", vw["intro"])
    for it in vw["items"]:
        for field in ("title", "line"):
            missing = [l for l in ("ja", "en") if not str(it[field].get(l, "")).strip()]
            if missing:
                bad.append("viewers.%s.%s: 必須の訳が無い言語 %s" % (it["id"], field, missing))
        if not (BASE / "viewers" / (it["id"] + ".html")).is_file():
            bad.append("viewers.%s: ビューアが無い (docs/view2026/viewers/%s.html) —— "
                       "py -3.11 tools/build_view2026_viewers.py" % (it["id"], it["id"]))
        ref = Counter(_NUM.findall(vw["intro"]["ja"] + " " + it["line"]["ja"]))
        for l in langs[1:]:
            got = Counter(_NUM.findall(vw["intro"][l] + " " + it["line"].get(l, it["line"]["en"])))
            if got != ref:
                bad.append("viewers.%s [%s]: 数の並びが日本語と違う(日本語のみ %s / %s のみ %s)" % (
                    it["id"], l, sorted((ref - got).elements()), l, sorted((got - ref).elements())))
    cats = {c["id"] for c in d["categories"]}
    for c in d["categories"]:
        full("categories." + c["id"], c)
    groups = {g["id"] for g in d["groups"]}
    for g in d["groups"]:
        full("groups." + g["id"], g["name"])
    full("paper.abstract", d["paper"]["abstract"])

    ledger_rows = json.loads((ROOT / d["all_source"]).read_text(encoding="utf-8"))["exhibits"]
    ledger = {e["id"]: e for e in ledger_rows}
    ids = [e["id"] for e in d["exhibits"]]
    if len(ids) != len(set(ids)):
        bad.append("見どころの id が重複している")
    for e in d["exhibits"]:
        pid = e["id"]
        for f in ("label", "lead", "see"):
            full("%s.%s" % (pid, f), e[f])
        full("%s.num" % pid, e["num"], allow_empty=True)
        if "youtube_url" not in e:
            bad.append("%s: youtube_url 欄が無い(未公開なら空文字)" % pid)
        elif e["youtube_url"] and not re.match(r"^https://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+", e["youtube_url"]):
            bad.append("%s: youtube_url が YouTube の動画 URL でない: %s" % (pid, e["youtube_url"]))
        if e["category"] not in cats:
            bad.append("%s: category %r が categories に無い" % (pid, e["category"]))
        checks = [(DOCS / _media_rel(d, e), "図"), (BASE / "thumbs" / (pid + ".jpg"), "サムネイル")]
        if "source_url" not in e:
            checks.append((ROOT / "examples" / (pid + ".py"), "例のスクリプト"))
        for p, what in checks:
            if not p.is_file():
                bad.append("%s: %s が無い (%s)" % (pid, what, p.relative_to(ROOT).as_posix()))
        if _is_viewer(d, e) and (DOCS / _media_rel(d, e)).is_file():
            lack = [l for l in langs if l not in _viewer_langs(DOCS / _media_rel(d, e))]
            if lack:
                bad.append("%s: ビューアに無い言語 %s —— py -3.11 tools/anim3d_i18n.py --build %s --out docs/%s"
                           % (pid, lack, pid, _media_rel(d, e)))
        if "numbers_source" in e:
            src = ledger.get(pid)
            if src is None or src.get("numbers_source") != e["numbers_source"]:
                bad.append("%s: 台帳の numbers_source と一致しない —— build_view2026_featured_batch.py を再実行すること" % pid)
            else:
                for l in langs:
                    expected = src["caption_ja" if l == "ja" else "caption_en"]
                    got = e["see"][l] + e["num"][l]
                    # 英語のキャプションが日本語を引用している(路面標示など)行だけ、末尾の日本語の印を許す
                    if l != "ja" and _KANA.search(expected) and got == expected + " " + JA_MARK:
                        got = expected
                    if got != expected:
                        bad.append("%s [%s]: 台帳のキャプションと逐語一致しない —— build_view2026_featured_batch.py を再実行すること" % (pid, l))
        else:
            ref = Counter(_NUM.findall(e["see"]["ja"] + " " + e["num"]["ja"]))
            for l in langs[1:]:
                got = Counter(_NUM.findall(e["see"][l] + " " + e["num"][l]))
                if got != ref:
                    bad.append("%s [%s]: 数の並びが日本語と違う(日本語のみ %s / %s のみ %s)" % (
                        pid, l, sorted((ref - got).elements()), l, sorted((got - ref).elements())))

    for s in d["series"]:
        full("series.%s.label" % s["id"], s["label"])
        full("series.%s.desc" % s["id"], s["desc"])
        if not (BASE / "thumbs" / s["thumb"]).is_file():
            bad.append("series.%s: サムネイルが無い" % s["id"])
        for l, u in s["url"].items():
            if not u.startswith(QIITA) or "/private/" in u:
                bad.append("series.%s.url.%s: 公開の Qiita 記事 (%s…) でない: %s" % (s["id"], l, QIITA, u))
        if "ja" not in s["url"]:
            bad.append("series.%s: ja の URL が無い" % s["id"])

    aids = [e["id"] for e in d["all"]]
    if len(aids) != len(set(aids)):
        bad.append("all の id が重複している")
    for e in d["all"]:
        full("all.%s.label" % e["id"], e["label"])
        if e["group"] not in groups:
            bad.append("all.%s: group %r が groups に無い" % (e["id"], e["group"]))
        for p, what in ((DOCS / _media_rel(d, e), "図"), (BASE / "thumbs" / "all" / (e["id"] + ".jpg"), "サムネイル")):
            if not p.is_file():
                bad.append("all.%s: %s が無い (%s)" % (e["id"], what, p.relative_to(ROOT).as_posix()))
    caps = capabilities()
    tr = d["capabilities"]["titles"]
    cat_names = [c["ja"] for c in d["capabilities"]["categories"]]
    for c in d["capabilities"]["categories"]:
        full("capabilities.categories." + c["ja"], c)
    if len(caps) < 30:
        bad.append("docs/capabilities/ の件数が %d —— 探す場所が縮んでいないか" % len(caps))
    for c in caps:
        cid = c["id"]
        full("capabilities.%s" % cid, {"ja": c["ja"], "en": c["en"]} | tr.get(cid, {}))
        if c["category"] not in cat_names:
            bad.append("capabilities.%s: 分類 %r の訳が無い" % (cid, c["category"]))
        if not c["examples"]:
            bad.append("capabilities.%s: 例が 1 本も無い" % cid)
        for x in c["examples"]:
            if _example_path(x) is None:
                bad.append("capabilities.%s: 例 %s が examples/ にも examples_3d/ にも無い" % (cid, x))
    extra = sorted(set(tr) - {c["id"] for c in caps})
    if extra:
        bad.append("capabilities.titles に、もう無い説明の訳が残っている: %s" % extra)
    src = json.loads((ROOT / d["all_source"]).read_text(encoding="utf-8"))
    missing = sorted({x["id"] for x in src["exhibits"]} - set(aids))
    if missing:
        bad.append("%s の展示が all に無い(%d 本): %s" % (d["all_source"], len(missing), missing[:10]))
    return bad


def _media_kind(name: str) -> str:
    if name.endswith(".html"):
        return "kind_anim3d"
    return "kind_video" if name.endswith(".mp4") else "kind_gif" if name.endswith(".gif") else "kind_fig"


def _doc(name: str, lang: str) -> str:
    """その言語版が在ればそれを、無ければ英語版(ja は原文)。"""
    if lang != "ja":
        for cand in ("%s.%s.md" % (name, lang), "%s.en.md" % name):
            if (DOCS / cand).is_file():
                return cand
    return name + ".md"


CAP_DIR = DOCS / "capabilities"
EXAMPLE_DIRS = ("examples", "examples_3d")


def capabilities() -> list[dict]:
    """``docs/capabilities/*.md`` の前付け(id / title / title_en / category / examples)。"""
    rows = []
    for p in sorted(CAP_DIR.glob("*.md")):
        lines = p.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            raise ValueError("%s: 前付け(---)が無い" % p.name)
        fm = {}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
        ex = [x.strip() for x in fm.get("examples", "").strip("[]").split(",") if x.strip()]
        rows.append({"id": p.stem, "ja": fm.get("title", ""), "en": fm.get("title_en", ""),
                     "category": fm.get("category", ""), "examples": ex})
    return rows


def _example_path(name: str) -> str | None:
    """例の repo 内の経路(``examples/`` か ``examples_3d/``)。無ければ None。"""
    for sub in EXAMPLE_DIRS:
        if (ROOT / sub / (name + ".py")).is_file():
            return "%s/%s.py" % (sub, name)
    return None


def other_example_count() -> int:
    """PoC でない使用例の本数(``examples/*.py`` から ``poc_`` と ``_`` 始まりを除く)。手で書かない。"""
    return sum(1 for p in (ROOT / "examples").glob("*.py") if not p.name.startswith(("poc_", "_")))


def counts(d: dict) -> tuple[int, int]:
    """(PoC の本数, それ以外=ロボットの例(目・身体)の本数) を all から数える。手で書かない。"""
    n_poc = sum(1 for e in d["all"] if e["id"].startswith("poc_"))
    return n_poc, len(d["all"]) - n_poc


def build(d: dict, lang: str) -> str:
    ui = {k: v.get(lang, "") for k, v in d["ui"].items()}
    glossary_ledger, glossary = _glossary_inputs()
    up = "" if lang == "ja" else "../"            # ページから docs/view2026/ への相対
    docs = up + "../"                              # ページから docs/ への相対
    def media(e):                                  # 動く 3-D の HTML はそのページの言語で開く
        return docs + _media_rel(d, e) + ("?lang=" + lang if _is_viewer(d, e) else "")

    sw = []
    for l in d["langs"]:
        name = d["ui"]["lang_name"][l]
        sw.append("**%s**" % name if l == lang else
                  "[%s](%s)" % (name, up + ("index.md" if l == "ja" else l + "/index.md")))
    out = ['<div class="vlang" markdown="1">', "", " · ".join(sw), "", "</div>", "",
           "# Fullseye — ViEW2026", "", ui["tagline"], "", ui["tap"], "", STYLE, ""]
    if lang == "ja":
        # 送り先の言語は exhibits.json の langs から(zh / tw は上の行で別に分ける)。
        out += [REDIRECT.replace("@LATIN@", "|".join(
            l for l in d["langs"] if l not in ("ja", "zh", "tw"))), ""]

    # 0. 触って見る(docs/view2026/viewers/*.html。各ページは自分の言語で開く)
    vw = d["viewers"]
    out += ["## " + vw["h"][lang], "", vw["intro"][lang], ""]
    for it in vw["items"]:
        title = it["title"].get(lang, it["title"]["en"])
        line = it["line"].get(lang, it["line"]["en"])
        out.append("- **[%s](%sviewers/%s.html?lang=%s)**: %s" % (title, up, it["id"], lang, line))
    out.append("")

    # 1. 見どころ
    out += ["## " + ui["h_highlights"], ""]
    if lang != "ja" and any("numbers_source" in e for e in d["exhibits"]):
        out += [ui["poc_caption_lang_note"], ""]
    out += ['<div class="vg">']
    for e in d["exhibits"]:
        lab = e["label"][lang]
        mark = "<b>&#9654;</b>" if e["motion"] else ""
        cap = "%s · %s" % (lab, _viewer_mb(d, e)) if _is_viewer(d, e) else lab
        out.append('<a href="%s"><img src="%sthumbs/%s.jpg" alt="%s" loading="lazy" width="320" height="320">%s<span>%s</span></a>'
                   % (media(e), up, e["id"], lab, mark, cap))
    out += ["</div>", ""]

    # 2. シリーズ記事
    out += ["## " + ui["h_series"] + (" " + ui["series_lang_note"] if ui["series_lang_note"] else ""), "",
            '<div class="vser">']
    for s in d["series"]:
        url = s["url"]["ja"] if lang == "ja" else s["url"].get("en", s["url"]["ja"])
        out.append('<a href="%s"><img src="%sthumbs/%s" alt="%s" loading="lazy" width="480" height="270"><strong>%s</strong><span>%s</span></a>'
                   % (url, up, s["thumb"], s["label"][lang], s["label"][lang], s["desc"][lang]))
    out += ["</div>", ""]

    # 3. できること(docs/capabilities の全件)
    caps = capabilities()
    ja_note = "" if lang == "ja" else " " + JA_MARK      # 説明のページは日本語だけ
    out += ["## " + ui["h_caps"], "", ui["caps_intro"].format(n=len(caps)), "",
            '<div class="vl" markdown="1">', ""]
    for cat in d["capabilities"]["categories"]:
        rows = [c for c in caps if c["category"] == cat["ja"]]
        if not rows:
            continue
        out += ["**%s**" % cat[lang], ""]
        for c in rows:
            title = c[lang] if lang in ("ja", "en") else d["capabilities"]["titles"][c["id"]][lang]
            exs = " · ".join("[%s](%s/blob/master/%s)" % (x, d["repo"], _example_path(x)) for x in c["examples"])
            out.append("- %s: [%s](%scapabilities/%s.md)%s · %s %s" % (
                title, ui["caps_doc"], docs, c["id"], ja_note, ui["caps_ex"], exs))
        out.append("")
    out += ["</div>", "",
            "[%s](%s/blob/master/examples/README.md)" % (ui["other_examples"].format(n=other_example_count()), d["repo"]),
            ""]

    # 4. ぜんぶ見る
    n_poc, n_other = counts(d)
    out += ["## " + ui["h_all"], "", ui["all_count"].format(n=n_poc, m=n_other), "",
            '<noscript><p><a href="%s%s">%s</a></p></noscript>' % (docs, _doc("GALLERY", lang).replace(".md", ".html"),
                                                                   ui["all_nojs"]), ""]
    for g in d["groups"]:
        rows = [e for e in d["all"] if e["group"] == g["id"]]
        if not rows:
            continue
        cells = []
        for e in rows:
            lab = e["label"][lang]
            mark = "<b>&#9654;</b>" if e["motion"] else ""
            cells.append('<a href="%s"><img src="%s" data-src="%sthumbs/all/%s.jpg" alt="%s" width="200" height="200">%s<span>%s</span></a>'
                         % (media(e), PIXEL, up, e["id"], lab, mark, lab))
        out += ['<details class="vall"><summary><b>%s</b> (%d)</summary>' % (g["name"][lang], len(rows)),
                '<div class="vg vs">'] + cells + ["</div>", "</details>", ""]
    out += [LAZY, ""]

    # 5. 見どころの説明と数字
    out += ["## " + ui["h_list"], "", ui["list_intro"], "", '<div class="vl" markdown="1">', ""]
    for cat in d["categories"]:
        rows = [e for e in d["exhibits"] if e["category"] == cat["id"]]
        if not rows:
            continue
        out += ["**%s**" % cat[lang], ""]
        for e in rows:
            num = " **%s**" % e["num"][lang] if e["num"][lang].strip() else ""
            src = _source(d, e)
            link = " [%s](%s)" % (ui["source"], src) if src else ""
            kind = ui[_media_kind(_media_rel(d, e))]
            if _is_viewer(d, e):
                kind += ", " + _viewer_mb(d, e)
            youtube = " [YouTube](%s)" % e["youtube_url"] if e.get("youtube_url") else ""
            out.append("- [%s](%s) (%s): %s" % (
                e["label"][lang], media(e), kind, e["lead"][lang]))
            out.append("  %s%s%s" % (e["see"][lang], num, link + youtube))
            source_exhibit = glossary_ledger.get(e["id"])
            term_line = glossary_line(source_exhibit, lang, glossary) if source_exhibit else ""
            if term_line:
                out.append("  " + term_line)
        out.append("")
    out += ["</div>", "", "## " + ui["h_about"], "", ui["about"], ""]

    # 6. 畳む節
    out += ['<details markdown="1">', "<summary><b>%s</b> (Python 3.11)</summary>" % ui["try"], "",
            TRY_CMD, "", ui["try_after"], "", "</details>", ""]
    mcp_note = "" if lang == "ja" else " " + JA_MARK
    out += ['<details markdown="1">', "<summary><b>%s</b></summary>" % ui["links"], "",
            "- [%s](%s)" % (ui["gh"], d["repo"]),
            "- [%s](%s%s)" % (ui["gallery"], docs, _doc("GALLERY", lang)),
            "- [%s](%s%s) · [%s](%sMCP.md)%s" % (ui["rag"], docs, _doc("AI_RAG_GUIDE", lang), ui["mcp"], docs, mcp_note),
            "- [%s](%s%s)" % (ui["index"], docs, _doc("README", lang)),
            "", "</details>", ""]
    title = d["paper"]["title_ja"]
    if lang != "ja":
        title = "%s %s (%s)" % (title, JA_MARK, ui["title_tr"])
    out += ['<details markdown="1">', "<summary><b>%s</b></summary>" % ui["paper"], "",
            "- **%s**: %s" % (ui["f_title"], title),
            "- **%s**: %s" % (ui["f_author"], ui["author"]),
            "- **%s**: %s" % (ui["f_venue"], ui["venue"]),
            _pdf_line(d, ui, lang),
            "", "**%s**: %s" % (ui["f_abstract"], d["paper"]["abstract"][lang]),
            "", "</details>", ""]
    return "\n".join(out)


def _pdf_line(d, ui, lang):
    """論文 PDF の行。exhibits.json の paper.files {lang: 相対パス} のうち実在するものを言語名で並べる。
    日本語版は 2026-11-26 まで掲載しない(無ければ pdf_note の断り書き)。訳版(en/zh)は先に置ける。"""
    files = d["paper"].get("files", {})
    rel = "" if lang == "ja" else "../"
    avail = [(l, f) for l, f in files.items() if (BASE / f).is_file()]
    if not avail:
        return "- **%s**: %s" % (ui["f_pdf"], ui["pdf_note"])
    links = " · ".join("[%s](%s%s)" % (d["ui"]["lang_name"].get(l, l), rel, f) for l, f in avail)
    if "ja" not in dict(avail):
        links += "(%s: %s)" % (d["ui"]["lang_name"]["ja"], ui["pdf_note"])
    return "- **%s**: %s" % (ui["f_pdf"], links)


def page_path(lang: str) -> Path:
    return BASE / "index.md" if lang == "ja" else BASE / lang / "index.md"


def check_page(lang: str, text: str) -> list[str]:
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        if _LIQUID.search(line):
            bad.append("%s:%d Liquid の開き記号" % (lang, i))
        if lang != "ja" and _KANA.search(line) and JA_MARK not in line:
            bad.append("%s:%d 印の無いかな: %s" % (lang, i, line[:60]))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに、commit 済みと食い違えば exit 1")
    a = ap.parse_args(argv)
    d = load()
    bad = validate(d)
    pages = {l: build(d, l) for l in d["langs"]}
    for l, t in pages.items():
        bad += check_page(l, t)
    if bad:
        print("exhibits.json の検査に落ちた(何も書いていない):\n  " + "\n  ".join(bad), file=sys.stderr)
        return 1
    drift = []
    for l, t in pages.items():
        p = page_path(l)
        old = p.read_text(encoding="utf-8") if p.is_file() else None
        if old != t:
            drift.append(p.relative_to(ROOT).as_posix())
            if not a.check:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(t, encoding="utf-8", newline="\n")
    n_poc, n_other = counts(d)
    if a.check:
        if drift:
            print("生成物が古い: %s —— py -3.11 tools/gen_view2026_pages.py" % drift, file=sys.stderr)
            return 1
        print("ok: %d pages current (highlights %d, series %d, capabilities %d, all %d = PoC %d + %d)"
              % (len(pages), len(d["exhibits"]), len(d["series"]), len(capabilities()), len(d["all"]),
                 n_poc, n_other))
        return 0
    print("wrote %d / %d pages: %s" % (len(drift), len(pages), drift))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
