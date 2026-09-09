# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""docs/hardening/*.md(単一真実源)→ docs/HARDENING.md / .en.md(索引)。

なぜ要るか(2026-09-08、ユーザー「PoC はそれなりに fullseye の堅牢性を上げてるから、
それも同じような形で貯められる方が良い」):

PoC は展示であると同時に **不具合発見器**として働いてきた —— `dem_viewshed` の
自己遮蔽、`frame_align` の賛成率、`op_find` の和文盲目、`carve_look_at` の登録漏れ、
`dem_ecef_to_geodetic` が緯度 180 度を返していた件。ところがその記録は
`docs/KNOWN_ISSUES.md` の散文・`CHANGELOG.md`・commit 本文に散っていて、
**「PoC で何件直ったか」を数えられなかった**。数えられないものは、増えたか
減ったかも言えない。

ここがその台帳。1 件 = 1 ファイルで、**どの PoC が見つけ、どこを直し、
どの門で再発を止めたか**を書く。門(`tests/test_capabilities.py`)が
`found_by` を実在する PoC に、`ops` を 4 層に、`gate` を実在するテスト関数に、
`where` を実在するファイルに照らすので、**書いただけの武勇伝は残らない**。

生成物はコミットして drift 検査に掛ける(docs の他の生成物と同じ)。
"""
from __future__ import annotations

import argparse
import io
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(_ROOT, "docs", "hardening")
OUT_JA = os.path.join(_ROOT, "docs", "HARDENING.md")
OUT_EN = os.path.join(_ROOT, "docs", "HARDENING.en.md")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_capabilities_index import (  # noqa: E402
    CapabilityError, _first_paragraph, _parse_front_matter, _split_front_matter,
)

REQUIRED_KEYS = ("id", "date", "found_by", "kind", "severity", "where", "ops",
                 "gate", "status")
REQUIRED_HEADINGS = ("## 症状", "## なぜ門が通したか", "## 直し")

#: 種別。**「門が無かった」と「門は在ったが場所が違った」を分ける** —— 後者の
#: ほうが多く、そして危ない(記録も検査も在るのに現実から取り残されている)。
KINDS = {
    "implementation-bug": "実装の誤り",
    "silent-wrong": "静かに間違う(例外が出ない)",
    "discoverability": "在るのに引けない",
    "doc-hole": "説明の穴(片道の参照・古い数字)",
    "gate-gap": "門が事故の起きる場所に立っていなかった",
    "missing-op": "道具そのものが無かった",
}
KINDS_EN = {
    "implementation-bug": "Implementation defect",
    "silent-wrong": "Silently wrong (no exception)",
    "discoverability": "Present but unreachable",
    "doc-hole": "Documentation hole (one-way reference, stale number)",
    "gate-gap": "The gate did not stand where the accident happens",
    "missing-op": "The tool itself was missing",
}
KIND_ORDER = ["silent-wrong", "implementation-bug", "gate-gap", "discoverability",
              "doc-hole", "missing-op"]
SEVERITIES = ("high", "medium", "low")
STATUSES = ("fixed", "mitigated", "open")


def load_all() -> list[dict]:
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
        if meta["kind"] not in KINDS:
            raise CapabilityError("%s: kind %r は %s のどれか"
                                  % (path, meta["kind"], sorted(KINDS)))
        if meta["severity"] not in SEVERITIES:
            raise CapabilityError("%s: severity %r は %s のどれか"
                                  % (path, meta["severity"], list(SEVERITIES)))
        if meta["status"] not in STATUSES:
            raise CapabilityError("%s: status %r は %s のどれか"
                                  % (path, meta["status"], list(STATUSES)))
        for head in REQUIRED_HEADINGS:
            if head not in body:
                raise CapabilityError("%s: 見出し %r が無い" % (path, head))
        # ★status=fixed なのに門が無いのは通さない —— 直したという記録だけが
        #   残って再発を止められない状態を、この台帳自身が作らないため。
        if meta["status"] == "fixed" and not meta["gate"]:
            raise CapabilityError("%s: status=fixed なのに gate が空 —— "
                                  "再発を止める試験の名前を書くこと" % path)
        meta["_path"] = path
        meta["_file"] = name
        meta["_body"] = body
        meta["_title"] = _title_of(body, path)
        meta["_symptom"] = _first_paragraph(body, "## 症状", path)
        out.append(meta)
    if not out:
        raise CapabilityError("%s に記録が 1 本も無い" % SRC_DIR)
    return out


def _title_of(body: str, path: str) -> str:
    for line in body.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    raise CapabilityError("%s: 「# タイトル」の行が無い" % path)


def _render(rows: list[dict], lang: str) -> str:
    ja = lang == "ja"
    by_poc: dict[str, int] = {}
    for r in rows:
        by_poc[r["found_by"]] = by_poc.get(r["found_by"], 0) + 1
    fixed = sum(1 for r in rows if r["status"] == "fixed")
    L: list[str] = []
    if ja:
        L += [
            "# PoC が上げた堅牢性 —— 見つけて直した記録",
            "",
            "**Language:** [日本語](HARDENING.md) · [English](HARDENING.en.md)",
            "",
            "PoC は展示であると同時に **不具合発見器**です。ここはその台帳 ——",
            "**どの PoC が見つけ、どこを直し、どの門で再発を止めたか**を 1 件 1 ファイルで貯めます。",
            "",
            "門(`tests/test_capabilities.py`)が `found_by` を実在する PoC に、",
            "`ops` を 4 層(`fs.` / `fs.op.` / `fs.ledger.` / `op_find`)に、`gate` を",
            "実在する試験関数に、`where` を実在するファイルに照らします。",
            "**`status: fixed` なのに `gate` が空の記録は、そもそも索引を作らせません** ——",
            "「直した」という記録だけが残って再発を止められない状態を、この台帳自身が作らないため。",
            "",
            "* できることから引くなら → [CAPABILITIES.md](CAPABILITIES.md)",
            "* 詳しい経緯と数字は → [KNOWN_ISSUES.md](KNOWN_ISSUES.md)",
            "",
            "**%d 件(うち直したもの %d 件)。見つけた PoC は %d 本。**"
            % (len(rows), fixed, len(by_poc)),
            "",
        ]
    else:
        L += [
            "# What the PoCs hardened — found, fixed, and gated",
            "",
            "**Language:** [日本語](HARDENING.md) · [English](HARDENING.en.md)",
            "",
            "The PoCs are exhibits, but they are also defect finders. This is the ledger:",
            "which PoC found it, what was changed, and which gate now stops it coming back —",
            "one file per finding.",
            "",
            "A gate (`tests/test_capabilities.py`) checks `found_by` against the PoC files,",
            "`ops` against all four public tiers, `gate` against the test functions that exist,",
            "and `where` against the files on disk. An entry marked `status: fixed` with an",
            "empty `gate` refuses to build the index at all — so that this ledger cannot itself",
            "become a place where 'we fixed it' is recorded with nothing stopping a relapse.",
            "",
            "* Organised by what you want to do → [CAPABILITIES.en.md](CAPABILITIES.en.md)",
            "* Full narrative and numbers → [KNOWN_ISSUES.md](KNOWN_ISSUES.md)",
            "",
            "**%d findings (%d fixed), from %d PoCs.**" % (len(rows), fixed, len(by_poc)),
            "",
        ]

    L += ["## %s" % ("種別ごと" if ja else "By kind"), "", ]
    L += ["| %s | %s | %s |" % (("種別", "件数", "直した") if ja
                                else ("Kind", "Findings", "Fixed")),
          "|---|---:|---:|"]
    for k in KIND_ORDER:
        sel = [r for r in rows if r["kind"] == k]
        if not sel:
            continue
        L.append("| %s | %d | %d |" % ((KINDS if ja else KINDS_EN)[k], len(sel),
                                       sum(1 for r in sel if r["status"] == "fixed")))
    L += [""]

    L += ["## %s" % ("見つけた PoC ごと" if ja else "By the PoC that found it"), "",
          "| %s | %s |" % (("PoC", "件数") if ja else ("PoC", "Findings")), "|---|---:|"]
    for poc, n in sorted(by_poc.items(), key=lambda kv: (-kv[1], kv[0])):
        L.append("| [`%s`](../examples/%s.py) | %d |" % (poc, poc, n))
    L += [""]

    L += ["## %s" % ("記録" if ja else "The findings"), ""]
    for k in KIND_ORDER:
        sel = sorted([r for r in rows if r["kind"] == k], key=lambda x: (x["date"], x["id"]))
        if not sel:
            continue
        L += ["### %s" % (KINDS if ja else KINDS_EN)[k], ""]
        for r in sel:
            # ★リンク先(`docs/hardening/*.md`)は日本語で書かれている。英題に
            #   差し替えるのは嘘になるので、題はそのまま出して `(ja)` を添える ——
            #   非日本語版の読者に要るのは「訳された題」ではなく「これは読めない」
            #   という事実。印は `tools/i18n_status.py` が数える形に固定する。
            _mark = "" if ja else " _(ja)_"
            L += ["#### [%s](hardening/%s)%s" % (r["_title"], r["_file"], _mark), "",
                  r["_symptom"] + _mark, "",
                  "%s `%s` / %s %s / %s %s / %s %s"
                  % ("見つけた PoC:" if ja else "Found by:", r["found_by"],
                     "直した所:" if ja else "Changed:",
                     ", ".join("`%s`" % w for w in r["where"]) or "—",
                     "門:" if ja else "Gate:",
                     ", ".join("`%s`" % g for g in r["gate"]) or "—",
                     "状態:" if ja else "Status:", r["status"]), ""]
    return "\n".join(L).rstrip("\n") + "\n"


def build() -> dict:
    rows = load_all()
    return {OUT_JA: _render(rows, "ja"), OUT_EN: _render(rows, "en")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    try:
        pages = build()
    except CapabilityError as e:
        print("hardening: %s" % e, file=sys.stderr)
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
            print("stale: %s — run `py -3.11 tools/gen_hardening_index.py`"
                  % ", ".join(stale), file=sys.stderr)
            return 1
        print("hardening index is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
