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

## 2026-09-15: 用途 → op 連鎖のレシピ欄

文書だけを渡した Codex / Copilot に op を選ばせたところ、両方が同じ所で迷った —
「ノート単体は正確だが、**用途から op へ辿る地図が無い**」。この索引がその地図の
はずだったのに、1 回目は両 AI とも**見つけられなかった**(`AI_RAG_GUIDE` から
辿れていなかった)。見つけた 2 回目でも、能力ノートには「使う op」の集合しか無く、
**どの順で繋ぐか・何に差し替えられるか・どこで壊れるか・画素を mm にどう戻すか**が
書かれていなかった。だから並行する新索引を作らず、**この様式に欄を足す**:

    inputs        利用者が最初に持っている型(sort)
    pipeline      **順序つき**の op 名。全部 `docs/OP_INDEX.json` に在り、型が繋がること
    alternatives  差し替え候補(実在は検査、型連鎖は検査しない)
    limits        1 行の限界(本文の ``## 限界`` 節に実測つきの詳細)
    calibration   1 行の実寸校正(本文の ``## 実寸校正`` 節に詳細。不要ならその理由)

型連鎖は :func:`pipeline_errors` が見る —— 各 op の宣言 in が、``inputs`` +
前段までの out から全部埋まること。族ごとに型名がずれる 4 組だけ
:data:`SORT_ALIASES` で同一視し、それ以外は「繋がらない」と判定する。
引数で渡す量(照合結果の row/col を測定線の位置に入れる等)は型連鎖の外なので、
生成 op(入力ゼロ)は前段が何であれ置ける。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(_ROOT, "docs", "capabilities")
OUT_JA = os.path.join(_ROOT, "docs", "CAPABILITIES.md")
OUT_EN = os.path.join(_ROOT, "docs", "CAPABILITIES.en.md")
OP_INDEX = os.path.join(_ROOT, "docs", "OP_INDEX.json")
DOCS_OPS = os.path.join(_ROOT, "docs", "ops")

#: 族をまたぐと同じ物に別の名が付いている型。**この 4 組だけ**同一視する
#: (それ以外の型名の違いは「繋がらない」。黙って緩めない)。
#:   * 2-D レジストリの ``image`` と台帳の ``image2d``(どちらも (H, W) float)
#:   * 2-D レジストリの ``region``(0/1 の (H, W))と blob 族の ``mask``
#:     (``blob_label`` が 2-D の ``otsu`` の返りをそのまま受ける —— 実測 2026-09-15)
#:   * 2-D レジストリの ``feature``(有限スカラ)と台帳の ``measurement``(float)と
#:     ``scalar``(int の index)—— 連鎖の中では「数 1 個」
SORT_ALIASES = {"image2d": "image", "mask": "region",
                "measurement": "scalar", "feature": "scalar"}

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

REQUIRED_KEYS = ("id", "title", "title_en", "category", "ops", "examples", "version",
                 "inputs", "pipeline", "alternatives", "limits", "calibration")
REQUIRED_HEADINGS = ("## できること", "## 向くところ / 向かないところ", "## 最初の 1 本",
                     "## 推奨パイプライン", "## 代替", "## 限界", "## 実寸校正")
#: 空でよい欄(``inputs`` は生成 op から始まる連鎖なら空、``alternatives`` は無くてもよい)。
MAY_BE_EMPTY = ("inputs", "alternatives")


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
        empty = [k for k in REQUIRED_KEYS if not meta[k] and k not in MAY_BE_EMPTY]
        if empty:
            raise CapabilityError("%s: front matter の %s が空" % (path, empty))
        for k in ("inputs", "pipeline", "alternatives", "ops", "examples"):
            if not isinstance(meta[k], list):
                raise CapabilityError("%s: %s は [a, b] のリストで書く" % (path, k))
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


# --------------------------------------------------------------------------- #
# 型連鎖(配布物 docs/OP_INDEX.json の側から引く)                             #
# --------------------------------------------------------------------------- #
_INDEX = None


def op_index() -> dict:
    """``{op 名: 行}``。登録ではなく**配布物**(``docs/OP_INDEX.json``)を正本にする。"""
    global _INDEX
    if _INDEX is None:
        with io.open(OP_INDEX, encoding="utf-8") as f:
            _INDEX = {r["name"]: r for r in json.load(f)["ops"]}
    return _INDEX


def canonical(sort: str) -> str:
    return SORT_ALIASES.get(sort, sort)


def op_ins(rec: dict) -> list:
    if rec.get("tier") == "ledger":
        return list(rec.get("in_sorts") or [])
    return [rec["in_sort"]] if rec.get("in_sort") else []


def op_dim(rec: dict) -> str:
    return rec.get("dim") or "2d"


def note_rel(name: str, base: str = DOCS_OPS) -> str | None:
    """``docs/ops/<dim>/<category>/<op>.md`` への、``base`` からの相対パス(無ければ None)。"""
    rec = op_index().get(name)
    if rec is None:
        return None
    hits = sorted(glob.glob(os.path.join(DOCS_OPS, op_dim(rec), "*", name + ".md")))
    hits = [h for h in hits if os.path.basename(os.path.dirname(h)) != "guides"]
    if not hits:
        return None
    return os.path.relpath(hits[0], base).replace(os.sep, "/")


def pipeline_errors(cap: dict) -> list:
    """レシピ欄の誤りを列挙する(空なら合格)。

    * ``pipeline`` の op は全部 ``docs/OP_INDEX.json`` に在ること(型の宣言が要るので、
      ファサードだけの関数は ``alternatives`` / ``ops`` に書く)。
    * 各 op の宣言 in が、``inputs`` + 前段までの out から全部埋まること。
    * 各 op のノートが ``docs/ops`` に在ること(索引からリンクするので)。
    """
    idx = op_index()
    errs = []
    cid = cap["id"]
    pool = {canonical(s) for s in cap.get("inputs", [])}
    for i, name in enumerate(cap.get("pipeline", []), 1):
        rec = idx.get(name)
        if rec is None:
            errs.append("%s: pipeline の %r は docs/OP_INDEX.json に無い(型が宣言されて"
                        "いない op は pipeline に置けない。alternatives か ops へ)" % (cid, name))
            continue
        if note_rel(name) is None:
            errs.append("%s: pipeline の %r のノートが docs/ops に無い" % (cid, name))
        for s in op_ins(rec):
            if s != "any" and canonical(s) not in pool:
                errs.append("%s: step %d %s の入力 %r がそれまでの型 %s に無い"
                            % (cid, i, name, s, sorted(pool)))
        if rec.get("out_sort"):
            pool.add(canonical(rec["out_sort"]))
    return errs


def all_pipeline_errors(caps: list[dict]) -> list:
    out = []
    for c in caps:
        out += pipeline_errors(c)
    return out


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
    # 課題名で引く表 —— 「用途 → op 連鎖」を 1 行ずつ。型連鎖は門が検査済み。
    if ja:
        L += ["## 課題から引く(推奨パイプライン)", "",
              "op 名は全部レジストリに実在し、**型(in → out)が前段から後段へ繋がる**ことを "
              "`tests/test_capabilities.py` が検査する。型の同一視は 4 組だけ "
              "(`image2d`=`image`、`mask`=`region`、`measurement`=`feature`=`scalar`)。"
              "引数で渡す量は型連鎖の外。詳細(代替・限界・実寸校正)は各項目へ。", "",
              "| 課題 | 推奨パイプライン(順序つき) | 動く例 |", "|---|---|---|"]
    else:
        L += ["## Look up by task (recommended pipeline)", "",
              "Every operator exists in the registry and the types connect from one step "
              "to the next (`tests/test_capabilities.py` checks both; only four sort "
              "names are treated as synonyms: `image2d`=`image`, `mask`=`region`, "
              "`measurement`=`feature`=`scalar`). Values passed as arguments are outside "
              "the type chain. Alternatives, limits and calibration are in each entry.", "",
              "| Task | Recommended pipeline (in order) | Runnable |", "|---|---|---|"]
    for c in sorted(caps, key=lambda x: x["id"]):
        title = c["title"] if ja else c["title_en"]
        L.append("| [%s](capabilities/%s) | %s | `%s` |"
                 % (title, c["_file"], " → ".join("`%s`" % o for o in c["pipeline"]),
                    c["examples"][0]))
    L.append("")
    for cat in _ordered_categories(caps):
        rows = [c for c in caps if c["category"] == cat]
        head = cat if ja else CATEGORY_EN.get(cat, cat)
        L += ["## %s (%d)" % (head, len(rows)), ""]
        for c in sorted(rows, key=lambda x: x["id"]):
            title = c["title"] if ja else c["title_en"]
            summary = c["_summary_ja"] if ja else (c["_summary_en"] or c["_summary_ja"])
            chain = " → ".join(_op_link(o, "docs") for o in c["pipeline"])
            alts = ", ".join(_op_link(o, "docs") for o in c["alternatives"]) or "—"
            L += ["### [%s](capabilities/%s)" % (title, c["_file"]), "",
                  summary, "",
                  "%s %s" % ("使う op:" if ja else "Operators:",
                             ", ".join("`%s`" % o for o in c["ops"])), "",
                  "%s %s" % ("推奨パイプライン:" if ja else "Pipeline:", chain), "",
                  "%s %s" % ("代替:" if ja else "Alternatives:", alts), ""]
            if ja:
                L += ["限界: %s" % c["limits"], "", "実寸校正: %s" % c["calibration"], ""]
            else:
                # 英語の索引に日本語を混ぜない —— 訳がある欄だけ出す(無ければ項目へ)。
                if c.get("limits_en"):
                    L += ["Limits: %s" % c["limits_en"], ""]
                if c.get("calibration_en"):
                    L += ["Calibration: %s" % c["calibration_en"], ""]
            L += ["%s %s" % ("動く例:" if ja else "Runnable:",
                             ", ".join("`%s`" % e for e in c["examples"])), ""]
    return "\n".join(L).rstrip("\n") + "\n"


def _op_link(name: str, base_dir: str) -> str:
    """索引(docs/ 直下)から op ノートへのリンク。ノートが無い(ファサードだけの
    関数)ならコードスパンのまま。"""
    rel = note_rel(name, os.path.join(_ROOT, base_dir))
    return "[`%s`](%s)" % (name, rel) if rel else "`%s`" % name


def build() -> dict:
    caps = load_all()
    errs = all_pipeline_errors(caps)
    if errs:
        raise CapabilityError("レシピ欄の誤り %d 件:\n  " % len(errs) + "\n  ".join(errs))
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
