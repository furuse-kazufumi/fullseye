# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""docs/capabilities/*.md(単一真実源)→ docs/CAPABILITIES.md / .en.md(索引)。

なぜ要るか(2026-09-08、ユーザー「fullseye で出来ることに関して、github に説明を
貯められる仕組みと、トップページからそれらの一覧を管理するページへのリンクを
はじめの方に載せておくほうが良いね」):

* **op ノート**(`docs/ops/`、1,900 本超)は「その op が何をするか」を書く場所。
* **PoC 展示**(`docs/articles/exhibits/`)は「真値つきで実問題を解いた記録」。
* どちらでもない「**Fullseye で何ができるか**」——ライブラリ全体の能力の説明は、
  README の散文・族ガイド・GALLERY に散っていて、**貯まる場所が無かった**。

ここがその場所。1 能力 = 1 ファイルで、**必ず実在する op と実行できる例に紐づく**
(裏づけの無い能力書きを増やさないため、`tests/test_capabilities.py` が
op 名を 4 層に、例をファイルの実在に照らして落とす)。

生成物は **コミットして門で突き合わせる**(docs の他の生成物と同じ drift 検査)。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(_ROOT, "docs", "capabilities")
OUT_JA = os.path.join(_ROOT, "docs", "CAPABILITIES.md")
OUT_EN = os.path.join(_ROOT, "docs", "CAPABILITIES.en.md")

#: 索引での並び順。ここに無いカテゴリは後ろに五十音で続く(落とさない)。
CATEGORY_ORDER = [
    "測る", "見つける", "形にする", "光と色", "波と信号", "組み立てる", "見せる",
]

#: 区分の英語名。★英語版でも見出しだけ日本語のままだった(実測 7 行)——
#: 中身は `title_en` / `_summary_en` で訳してあるのに、見出しを訳し忘れていて
#: 「切り替えたのに日本語が混ざる」の典型になっていた。ここに無い区分は
#: 原文のまま出す(勝手に訳を作らない)。
CATEGORY_EN = {
    "測る": "Measure", "見つける": "Detect", "形にする": "Shape",
    "光と色": "Light and colour", "波と信号": "Waves and signals",
    "組み立てる": "Compose", "見せる": "Show",
}

REQUIRED_KEYS = ("id", "title", "title_en", "category", "ops", "examples", "version")
REQUIRED_HEADINGS = ("## できること", "## 向くところ / 向かないところ", "## 最初の 1 本")


class CapabilityError(RuntimeError):
    """能力ノートの書式が壊れている(fail-closed: 索引を作らずに止める)。"""


def _split_front_matter(text: str, path: str):
    if not text.startswith("---\n"):
        raise CapabilityError("%s: YAML front matter (--- で始まる) が無い" % path)
    end = text.find("\n---\n", 4)
    if end < 0:
        raise CapabilityError("%s: front matter が閉じていない" % path)
    return text[4:end], text[end + 5:]


def _parse_front_matter(raw: str, path: str) -> dict:
    """必要なだけの極小パーサ(依存を増やさない)。値はスカラかリテラル配列。"""
    meta: dict = {}
    for line in raw.split("\n"):
        line = line.split("  #", 1)[0].rstrip()
        if not line.strip():
            continue
        if ":" not in line:
            raise CapabilityError("%s: front matter の行に ':' が無い: %r" % (path, line))
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            body = v[1:-1].strip()
            meta[k] = [x.strip() for x in body.split(",") if x.strip()] if body else []
        else:
            meta[k] = v
    return meta


def load_all() -> list[dict]:
    """`docs/capabilities/*.md` を読み、front matter + 本文を返す(id 順)。"""
    if not os.path.isdir(SRC_DIR):
        raise CapabilityError("%s が無い" % SRC_DIR)
    out = []
    for name in sorted(os.listdir(SRC_DIR)):
        if not name.endswith(".md") or name.startswith("_"):
            continue
        path = os.path.join(SRC_DIR, name)
        text = io.open(path, encoding="utf-8").read()
        raw, body = _split_front_matter(text, path)
        meta = _parse_front_matter(raw, path)
        missing = [k for k in REQUIRED_KEYS if k not in meta]
        if missing:
            raise CapabilityError("%s: front matter に %s が無い" % (path, missing))
        if meta["id"] != os.path.splitext(name)[0]:
            raise CapabilityError("%s: id %r とファイル名が違う" % (path, meta["id"]))
        for head in REQUIRED_HEADINGS:
            if head not in body:
                raise CapabilityError("%s: 見出し %r が無い" % (path, head))
        if "```python" not in body:
            raise CapabilityError("%s: 「最初の 1 本」に python のコード塊が無い" % path)
        meta["_path"] = path
        meta["_file"] = name
        meta["_body"] = body
        meta["_summary_ja"] = _first_paragraph(body, "## できること", path)
        meta["_summary_en"] = _first_paragraph(body, "## What it does", path, required=False)
        out.append(meta)
    if not out:
        raise CapabilityError("%s に能力ノートが 1 本も無い" % SRC_DIR)
    return out


def _first_paragraph(body: str, heading: str, path: str, required: bool = True) -> str:
    """見出し直下の最初の段落を 1 行に畳んで返す(索引の要約に使う)。"""
    i = body.find(heading)
    if i < 0:
        if required:
            raise CapabilityError("%s: %r が無い" % (path, heading))
        return ""
    rest = body[i + len(heading):].lstrip("\n")
    para = rest.split("\n\n", 1)[0].strip()
    if not para:
        raise CapabilityError("%s: %r の直下が空" % (path, heading))
    return re.sub(r"\s+", " ", para.replace("\n", " ")).strip()


def _ordered_categories(caps: list[dict]) -> list[str]:
    seen = {c["category"] for c in caps}
    head = [c for c in CATEGORY_ORDER if c in seen]
    tail = sorted(seen - set(head))
    return head + tail


def _render(caps: list[dict], lang: str) -> str:
    ja = lang == "ja"
    L: list[str] = []
    if ja:
        L += [
            "# Fullseye でできること",
            "",
            "**Language:** [日本語](CAPABILITIES.md) · [English](CAPABILITIES.en.md)",
            "",
            "「どの op を呼ぶか」ではなく「**何ができるか**」から引く索引です。",
            "1 項目 = 1 ファイル(`docs/capabilities/`)で、**すべて実在する op と、",
            "その場で走る例に紐づいています** —— 裏づけの無い能力書きが混ざらないよう、",
            "`tests/test_capabilities.py` が op 名を 4 層に、例をファイルの実在に",
            "照らして落とします。",
            "",
            "* op を名前で探すなら → [オペレータ索引](README.md#オペレータを探す)",
            "* 真値つきで実問題を解いた記録なら → [PoC 展示館](README.md)",
            "* 5 分で動かすなら → [GETTING_STARTED.md](GETTING_STARTED.md)",
            "",
            "**足すには**: `docs/capabilities/<id>.md` を 1 本書いて",
            "`py -3.11 tools/gen_capabilities_index.py` を実行するだけです",
            "(この索引は生成物なので直接編集しないでください)。",
            "",
        ]
    else:
        L += [
            "# What Fullseye can do",
            "",
            "**Language:** [日本語](CAPABILITIES.md) · [English](CAPABILITIES.en.md)",
            "",
            "An index organised by *what you want to do*, not by operator name.",
            "One entry is one file under `docs/capabilities/`, and every entry is tied",
            "to operators that exist and to an example that actually runs —",
            "`tests/test_capabilities.py` checks each operator name against all four",
            "public tiers and each example against the files on disk, so a capability",
            "claim with nothing behind it cannot survive.",
            "",
            "* Looking for an operator by name → [operator index](README.en.md)",
            "* Worked problems with planted ground truth → [the PoC museum](README.en.md)",
            "* Five-minute start → [GETTING_STARTED.md](GETTING_STARTED.md)",
            "",
            "**To add one**: write `docs/capabilities/<id>.md` and run",
            "`py -3.11 tools/gen_capabilities_index.py` (this index is generated —",
            "do not edit it by hand).",
            "",
        ]
    L += ["**%s %d %s**" % ("収録" if ja else "Currently", len(caps),
                            "項目" if ja else "capabilities"), ""]
    for cat in _ordered_categories(caps):
        rows = [c for c in caps if c["category"] == cat]
        head = cat if ja else CATEGORY_EN.get(cat, cat)
        L += ["## %s (%d)" % (head, len(rows)), ""]
        for c in sorted(rows, key=lambda x: x["id"]):
            title = c["title"] if ja else c["title_en"]
            summary = c["_summary_ja"] if ja else (c["_summary_en"] or c["_summary_ja"])
            L += ["### [%s](capabilities/%s)" % (title, c["_file"]), "",
                  summary, "",
                  "%s %s" % ("使う op:" if ja else "Operators:",
                             ", ".join("`%s`" % o for o in c["ops"])), "",
                  "%s %s" % ("動く例:" if ja else "Runnable:",
                             ", ".join("`%s`" % e for e in c["examples"])), ""]
    return "\n".join(L).rstrip("\n") + "\n"


def build() -> dict:
    caps = load_all()
    return {OUT_JA: _render(caps, "ja"), OUT_EN: _render(caps, "en")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="書かずに、コミット済みの索引と一致するかだけ見る")
    a = ap.parse_args()
    try:
        pages = build()
    except CapabilityError as e:
        print("capabilities: %s" % e, file=sys.stderr)
        return 2
    stale = []
    for path, text in pages.items():
        cur = io.open(path, encoding="utf-8").read() if os.path.isfile(path) else None
        if a.check:
            if cur != text:
                stale.append(os.path.relpath(path, _ROOT))
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(text)
        print("wrote %s (%d bytes)" % (os.path.relpath(path, _ROOT), len(text)))
    if a.check:
        if stale:
            print("stale: %s — run `py -3.11 tools/gen_capabilities_index.py`"
                  % ", ".join(stale), file=sys.stderr)
            return 1
        print("capabilities index is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
