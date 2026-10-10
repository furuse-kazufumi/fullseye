#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の案内ページ(論文の QR コードの行き先)を 7 言語ぶん生成する。

    py -3.11 tools/gen_view2026_pages.py           # 書く
    py -3.11 tools/gen_view2026_pages.py --check   # 書かずに、commit 済みと食い違えば exit 1

正本は ``docs/view2026/exhibits.json`` の 1 本だけ。展示を足す・数字を直すのはそこで 1 回。
数値と図の経路は全言語で共有し、文字列だけを訳す。出力:

* ``docs/view2026/index.md``        → https://furuse.work/view2026/      (ja、QR の行き先)
* ``docs/view2026/<lang>/index.md`` → https://furuse.work/view2026/<lang>/ (en zh tw ko de hi)

スマートフォンで開かれる前提で、先頭はサムネイルの格子だけにする(サムネイルは
``tools/gen_view2026_thumbs.py`` が作る 320 px の JPEG)。重い動画・GIF・原寸の図は
タイルを押したときに初めて読む —— 各 PoC が ``docs/articles/assets/poc/`` に出している既存の図。

★生成の前に検査して、通らなければ何も書かない(fail-closed):
  * 全言語の文字列がそろっている / 図・サムネイル・例のスクリプトが実在する
  * **説明文と数字に出てくる数の並びが、全言語で日本語と同じ**(訳で数字が化けない)
  * 日本語以外のページに、印(``_(ja)_``)の無いかなが無い
  * Jekyll が Liquid と読む開き記号が無い
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = DOCS / "view2026"
DATA = BASE / "exhibits.json"
GH_EXAMPLE = "%s/blob/master/examples/%s.py"
JA_MARK = "_(ja)_"                     # tools/i18n_status.py の印と同じ
_KANA = re.compile(r"[぀-ヿ]")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_LIQUID = re.compile(re.escape("{" + "{") + "|" + re.escape("{" + "%"))

STYLE = """<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.vg a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vl li { margin-bottom: 8px; }
</style>"""

#: ja の入口ページだけに置く。初回の訪問で、ブラウザの言語が ja 以外の 6 言語なら 1 度だけそのページへ送る。
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
    else if (/^(en|ko|de|hi)/.test(n)) t = n.slice(0, 2);
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


def validate(d: dict) -> list[str]:
    """問題の一覧(空なら合格)。"""
    bad = []
    langs = d["langs"]
    if langs[0] != "ja":
        bad.append("langs の先頭は ja(QR の行き先)でなければならない")

    def full(name, tr):
        miss = [l for l in langs if not str(tr.get(l, "")).strip()]
        if miss:
            bad.append("%s: 訳が無い言語 %s" % (name, miss))

    for k, tr in d["ui"].items():
        if k != "title_tr":
            full("ui." + k, tr)
    for i, c in enumerate(d["categories"]):
        full("categories[%d]" % i, c)
    full("paper.abstract", d["paper"]["abstract"])
    ids = [e["id"] for e in d["exhibits"]]
    if len(ids) != len(set(ids)):
        bad.append("展示の id が重複している")
    for e in d["exhibits"]:
        pid = e["id"]
        for f in ("label", "see", "num"):
            full("%s.%s" % (pid, f), e[f])
        for p, what in ((DOCS / d["media_root"] / pid / e["media"], "図"),
                        (BASE / "thumbs" / (pid + ".jpg"), "サムネイル"),
                        (ROOT / "examples" / (pid + ".py"), "例のスクリプト")):
            if not p.is_file():
                bad.append("%s: %s が無い (%s)" % (pid, what, p.relative_to(ROOT).as_posix()))
        if not 0 <= e["category"] < len(d["categories"]):
            bad.append("%s: category が範囲外" % pid)
        ref = Counter(_NUM.findall(e["see"]["ja"] + " " + e["num"]["ja"]))
        for l in langs[1:]:
            got = Counter(_NUM.findall(e["see"][l] + " " + e["num"][l]))
            if got != ref:
                bad.append("%s [%s]: 数の並びが日本語と違う(日本語のみ %s / %s のみ %s)" % (
                    pid, l, sorted((ref - got).elements()), l, sorted((got - ref).elements())))
    return bad


def _media_kind(name: str) -> str:
    return "kind_video" if name.endswith(".mp4") else "kind_gif" if name.endswith(".gif") else "kind_fig"


def _doc(name: str, lang: str) -> str:
    """その言語版が在ればそれを、無ければ英語版(ja は原文)。"""
    if lang != "ja":
        for cand in ("%s.%s.md" % (name, lang), "%s.en.md" % name):
            if (DOCS / cand).is_file():
                return cand
    return name + ".md"


def build(d: dict, lang: str) -> str:
    ui = {k: v.get(lang, "") for k, v in d["ui"].items()}
    up = "" if lang == "ja" else "../"            # ページから docs/view2026/ への相対
    docs = up + "../"                              # ページから docs/ への相対
    media = lambda e: "%s%s/%s/%s" % (docs, d["media_root"], e["id"], e["media"])  # noqa: E731

    sw = []
    for l in d["langs"]:
        name = d["ui"]["lang_name"][l]
        if l == lang:
            sw.append("**%s**" % name)
        else:
            sw.append("[%s](%s)" % (name, up + ("index.md" if l == "ja" else l + "/index.md")))
    out = ['<div class="vlang" markdown="1">', "", " · ".join(sw), "", "</div>", "",
           "# Fullseye — ViEW2026", "", ui["tagline"], "", ui["tap"], "", STYLE, ""]
    if lang == "ja":
        out += [REDIRECT, ""]

    out.append('<div class="vg">')
    for e in d["exhibits"]:
        lab = e["label"][lang]
        mark = "<b>&#9654;</b>" if e["motion"] else ""
        out.append('<a href="%s"><img src="%sthumbs/%s.jpg" alt="%s" loading="lazy" width="320" height="320">%s<span>%s</span></a>'
                   % (media(e), up, e["id"], lab, mark, lab))
    out += ["</div>", "", "## " + ui["h_list"], "", ui["list_intro"], "", '<div class="vl" markdown="1">', ""]
    for ci, cat in enumerate(d["categories"]):
        rows = [e for e in d["exhibits"] if e["category"] == ci]
        if not rows:
            continue
        out += ["**%s**" % cat[lang], ""]
        for e in rows:
            out.append("- [%s](%s) (%s): %s **%s** [%s](%s)" % (
                e["label"][lang], media(e), ui[_media_kind(e["media"])], e["see"][lang], e["num"][lang],
                ui["source"], GH_EXAMPLE % (d["repo"], e["id"])))
        out.append("")
    out += ["</div>", "", "## " + ui["h_about"], "", ui["about"], ""]

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
            "- **%s**: %s" % (ui["f_pdf"], ui["pdf_note"]),
            "", "**%s**: %s" % (ui["f_abstract"], d["paper"]["abstract"][lang]),
            "", "</details>", ""]
    return "\n".join(out)


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
    if a.check:
        if drift:
            print("生成物が古い: %s —— py -3.11 tools/gen_view2026_pages.py" % drift, file=sys.stderr)
            return 1
        print("ok: %d pages current" % len(pages))
        return 0
    print("wrote %d / %d pages: %s" % (len(drift), len(pages), drift))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
