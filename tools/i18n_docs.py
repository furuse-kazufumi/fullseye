# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""散文ドキュメントの翻訳台帳 —— **訳が日本語側から古びていないか**を数える。

`docs/` 直下の手書き散文(README のような生成物は除く)を日本語を正本とし、
翻訳は並行ファイル `X.<lang>.md` に置く。問題は**日本語を直したとき訳が黙って
古びる**こと。だから各訳ファイルの先頭に、訳した時点の日本語の指紋を埋める:

    <!-- i18n-source-sha: <日本語本文の SHA-256 先頭 12 桁> -->

この道具は各訳の指紋を現在の日本語本文と突き合わせ、fresh / stale / missing を
数える。`tests/test_i18n_docs.py` が **stale をゼロに保つ**(訳が古びたら CI が
落ちる。古い訳は無訳より悪い —— 読み手は「その言語の最新」と思って読む)。

★生成物(CHAIN で作り直す文書)は対象外。それらは**生成器の側**で訳す
(並行ファイルを置くと再生成で上書きされる)。

    py -3.11 tools/i18n_docs.py            # 台帳を表示
    py -3.11 tools/i18n_docs.py --stale    # stale / missing があれば exit 1
    py -3.11 tools/i18n_docs.py --stamp docs/GETTING_STARTED.en.md
                                           # 指紋を現在の日本語本文で打ち直す
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCS = os.path.join(_ROOT, "docs")

LANGS = ("en", "zh", "tw", "ko", "de")

#: 生成物。並行訳を置かず、生成器の側で多言語化する(置くと再生成で消える)。
#: CHAIN(tools/regen_all.py)が作る docs/ 直下のファイルと一致させること。
GENERATED = {
    "README", "CAPABILITIES", "HARDENING", "DESIGN_NOTES",
    "OP_CATALOG", "EXAMPLES_3D",
}

_SHA_RE = re.compile(r"<!--\s*i18n-source-sha:\s*([0-9a-f]{12})\s*-->")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def prose_docs() -> dict:
    """stem -> {lang: path}。生成物と、それ自体が翻訳のファイルは stem に畳む。"""
    out: dict[str, dict] = {}
    for p in sorted(glob.glob(os.path.join(_DOCS, "*.md"))):
        name = os.path.basename(p)[:-3]
        parts = name.split(".")
        stem, lang = parts[0], (parts[1] if len(parts) > 1 else "ja")
        if stem in GENERATED:
            continue
        if lang != "ja" and lang not in LANGS:
            continue                      # `foo.bar.md` のような非言語サフィックスは触らない
        out.setdefault(stem, {})[lang] = p
    return {k: v for k, v in out.items() if "ja" in v}


def status():
    """(rows, fresh, stale, missing)。rows = [(stem, lang, state), ...]。"""
    docs = prose_docs()
    rows = []
    fresh = stale = missing = 0
    for stem, langs in sorted(docs.items()):
        ja_sha = _sha(open(langs["ja"], encoding="utf-8", errors="replace").read())
        for lang in LANGS:
            p = langs.get(lang)
            if not p:
                rows.append((stem, lang, "missing"))
                missing += 1
                continue
            m = _SHA_RE.search(open(p, encoding="utf-8", errors="replace").read())
            if m and m.group(1) == ja_sha:
                rows.append((stem, lang, "fresh"))
                fresh += 1
            else:
                rows.append((stem, lang, "stale" if m else "no-stamp"))
                stale += 1
    return rows, fresh, stale, missing


def stamp(path: str) -> None:
    """訳ファイルの指紋を、対応する日本語本文の現在値で打ち直す。"""
    name = os.path.basename(path)[:-3]
    stem = name.split(".")[0]
    ja = os.path.join(_DOCS, stem + ".md")
    if not os.path.isfile(ja):
        raise SystemExit("日本語の正本が無い: %s" % ja)
    ja_sha = _sha(open(ja, encoding="utf-8", errors="replace").read())
    body = open(path, encoding="utf-8", errors="replace").read()
    stampline = "<!-- i18n-source-sha: %s -->" % ja_sha
    if _SHA_RE.search(body):
        body = _SHA_RE.sub(stampline, body, count=1)
    else:
        body = stampline + "\n" + body
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print("stamped %s <- %s (%s)" % (os.path.basename(path), stem + ".md", ja_sha))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stale", action="store_true",
                    help="stale / no-stamp があれば exit 1(missing は数えるが止めない)")
    ap.add_argument("--stamp", metavar="FILE", help="訳ファイルの指紋を打ち直す")
    a = ap.parse_args(argv)

    if a.stamp:
        stamp(a.stamp)
        return 0

    rows, fresh, stale, missing = status()
    docs = prose_docs()
    print("散文ドキュメント %d 本 × %d 言語 = %d 訳スロット"
          % (len(docs), len(LANGS), len(docs) * len(LANGS)))
    print("  fresh %d / stale・no-stamp %d / missing %d" % (fresh, stale, missing))
    bad = [(s, l, st) for s, l, st in rows if st in ("stale", "no-stamp")]
    if bad:
        print("\n★古い訳(日本語が変わったのに追随していない):")
        for s, l, st in bad:
            print("   %-22s %s  [%s]" % (s, l, st))
    done = sorted({s for s, l, st in rows if st == "fresh"})
    if done:
        print("\n訳あり(fresh):", ", ".join(done))

    if a.stale and bad:
        print("\n★stale/no-stamp が %d 件 —— 訳を直して `--stamp` で指紋を打ち直すこと" % len(bad))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
