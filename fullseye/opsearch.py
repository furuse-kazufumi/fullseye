# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Find operators by what they do, in any of six languages -> ranked rows.

意味で op を引く検索(RAG の入口)。``fullseye.search_ops("ノイズ除去")`` /
``fullseye-rag search "remove noise"`` / MCP ``fullseye_find_ops`` が同じ関数を呼ぶ。

**なぜ要るか(2026-10-07 実測)**: 知識層のノート ``docs/ops`` は本文が日本語なので、grep は
「Rauschen」「降噪」「잡음」で 0 件、「vanishing point」でも 0 件だった。op 名の部分一致
(MCP ``fullseye_search_ops``)は名前を知っている人にしか効かない。一方で全 op の要約は
``docs/i18n/op_summary.json`` に en / zh / tw / ko / de の訳がある —— それを検索面にする。

**何を照合するか**: op 名(``_`` で区切った語)・HALCON 名・族 / 分類・入出力の型と、
要約の 6 言語(ja 原文 + 5 訳)。順位は BM25(語の希少さで重み付け)。

**語の切り方**(依存ゼロ・決定的): ラテン文字は語ごと(6 文字を超える語は先頭 6 文字に
縮めて ``denoise`` / ``denoising``、``segment`` / ``segmentation`` を同じ語にする)、漢字・仮名・
ハングルは 2 文字ずつ(分かち書きが無い言語でも部分一致が効く)。埋め込みは使わない ——
同義語(「ぼかし」と「平滑化」)は拾えないので、0 件なら別の言い方を試す(``hint`` に出す)。

**索引** ``fullseye/data/OP_SEARCH.json`` は ``tools/gen_mcp_data.py`` が書き、wheel に同梱する
(``pip install fullseye`` だけで動く)。checkout でも同じ複製を読む —— 生成物と正本の一致は
``regen_all --check`` が CI で数える。
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter

__all__ = ["search_ops", "load_index", "tokenize", "detect_lang", "LANGS", "main"]

#: 要約を持つ言語(ja = 原文)。表示言語の既定は問い合わせの文字種から決める(:func:`detect_lang`)。
LANGS = ("ja", "en", "zh", "tw", "ko", "de")
PKG_SEARCH = "OP_SEARCH.json"
_STEM = 6
_K1, _B = 1.2, 0.75
#: 場ごとの重み: 名前に入っている語は要約の語より強い手掛かり
_W_NAME, _W_HALCON, _W_META, _W_SUMMARY = 3, 2, 1, 1

_LATIN = re.compile(r"[0-9a-zß-ɏ]+")
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")
_HANGUL = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]+")
_KANA = re.compile(r"[぀-ヿ]")
_GERMAN = re.compile(r"[äöüß]|\b(?:der|die|das|und|nicht|mit|eines?|bild|kante|rauschen)\b")

_CACHE: dict = {}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").lower()


def tokenize(text: str) -> list[str]:
    """検索語に切る: ラテン文字は語(長い語は先頭 6 文字)、漢字・仮名・ハングルは 2 文字ずつ。"""
    t = _norm(text).replace("_", " ")
    out: list[str] = []
    for w in _LATIN.findall(t):
        out.append(w[:_STEM] if len(w) > _STEM else w)
    for rx in (_CJK, _HANGUL):
        for run in rx.findall(t):
            if len(run) == 1:
                out.append(run)
            else:
                out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


def detect_lang(query: str) -> str:
    """問い合わせの文字種から表示言語を推す: ハングル → ko、仮名 → ja、漢字だけ → zh、
    ドイツ語の印(ウムラウト・ß・よく出る語)→ de、それ以外 → en。tw は推せないので ``lang="tw"`` で。"""
    q = _norm(query)
    if _HANGUL.search(q):
        return "ko"
    if _KANA.search(q):
        return "ja"
    if _CJK.search(q):
        return "zh"
    if _GERMAN.search(q):
        return "de"
    return "en"


def _pick_lang(query: str, qtok: list, top_rows: list) -> str:
    """表示言語: ハングル → ko、仮名 → ja は文字で決まる。それ以外(漢字だけ・ラテン文字)は
    文字種では ja / zh / tw、en / de を分けられないので、**上位の op の要約のうち問い合わせの語を
    いちばん多く含む言語**を採る(同点は :func:`detect_lang` の推定を優先)。"""
    guess = detect_lang(query)
    if guess in ("ko", "ja") or not top_rows:
        return guess
    cands = ("ja", "zh", "tw") if guess == "zh" else ("en", "de")
    qs = set(qtok)
    best, best_n = guess, -1
    for lang in sorted(cands, key=lambda x: x != guess):
        n = sum(len(qs & set(tokenize((r.get("s") or {}).get(lang, "")))) for r in top_rows)
        # 推定と違う言語へ乗り換えるのは**はっきり多い**ときだけ(語幹が同じ "skeleton" / "Skelett" で揺れない)
        if best_n < 0 or n > best_n * 1.5 + 1:
            best, best_n = lang, n
    return best


def load_index(path: str | None = None) -> dict:
    """同梱の索引を読んで BM25 の表を組む(1 プロセスで 1 回)。

    無ければ ``FileNotFoundError`` —— 空の索引で「該当なし」を返すと、検索層が自分の
    範囲について嘘をつく(``docs/AI_RAG_GUIDE.md`` の教訓)。"""
    key = path or "<package>"
    if key in _CACHE:
        return _CACHE[key]
    if path is None:
        from importlib.resources import files
        p = files("fullseye") / "data" / PKG_SEARCH
        if not p.is_file():
            raise FileNotFoundError(
                "fullseye/data/%s が無い。checkout なら `py -3.11 tools/gen_mcp_data.py` で作る" % PKG_SEARCH)
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    rows = raw.get("ops") or []
    if not rows:
        raise ValueError("%s に op が 0 件(生成が壊れている)" % PKG_SEARCH)
    docs: list[Counter] = []
    df: Counter = Counter()
    for r in rows:
        tf: Counter = Counter()
        for tok in tokenize(r["n"]):
            tf[tok] += _W_NAME
        for tok in tokenize(r.get("h") or ""):
            tf[tok] += _W_HALCON
        for tok in tokenize(" ".join(x for x in (r.get("d"), r.get("c"), r.get("i"), r.get("o")) if x)):
            tf[tok] += _W_META
        for txt in (r.get("s") or {}).values():
            for tok in tokenize(txt):
                tf[tok] += _W_SUMMARY
        docs.append(tf)
        df.update(tf.keys())
    lens = [sum(tf.values()) for tf in docs]
    avg = sum(lens) / len(lens)
    n = len(rows)
    idf = {t: math.log(1.0 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    names = {}
    for i, r in enumerate(rows):
        names.setdefault(_norm(r["n"]), i)
        if r.get("h"):
            names.setdefault(_norm(r["h"]), i)
    built = {"rows": rows, "docs": docs, "lens": lens, "avg": avg, "idf": idf, "names": names,
             "n_ops": n, "languages": raw.get("languages") or list(LANGS)}
    _CACHE[key] = built
    return built


def search_ops(query: str, k: int = 10, *, lang: str | None = None, in_sort: str | None = None,
               out_sort: str | None = None, dim: str | None = None, index_path: str | None = None) -> dict:
    """``query``(6 言語のどれでも)に合う op を順位つきで返す。

    返り: ``{"query", "lang", "total", "ops": [{"name", "dim", "category", "in_sort", "out_sort",
    "halcon", "note", "summary", "score"}], "hint"}``。``summary`` は ``lang``(既定は問い合わせから
    推した言語)の要約、無ければ en → ja。``total`` は語が 1 つでも当たった op の数。

    >>> r = search_ops("remove noise", k=3)
    >>> [o["name"] for o in r["ops"]]                       # doctest: +SKIP
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("search_ops: query must be a non-empty string")
    if lang is not None and lang not in LANGS:
        raise ValueError("search_ops: lang must be one of %s, got %r" % (LANGS, lang))
    if not (isinstance(k, int) and k > 0):
        raise ValueError("search_ops: k must be a positive int, got %r" % (k,))
    ix = load_index(index_path)
    q = list(dict.fromkeys(tokenize(query)))
    rows, docs, lens, avg, idf = ix["rows"], ix["docs"], ix["lens"], ix["avg"], ix["idf"]
    scores: dict[int, float] = {}
    matched: Counter = Counter()
    for tok in q:
        w = idf.get(tok)
        if w is None:
            continue
        for i, tf in enumerate(docs):
            f = tf.get(tok)
            if f:
                scores[i] = scores.get(i, 0.0) + w * f * (_K1 + 1) / (f + _K1 * (1 - _B + _B * lens[i] / avg))
                matched[i] += 1
    # 語を多く含む op を上に(一般語 1 つだけで当たった op が、語を全部含む op を追い越さない)
    for i in scores:
        scores[i] *= matched[i] / len(q)
    exact = ix["names"].get(_norm(query.strip()).replace(" ", "_"))
    if exact is not None:
        scores[exact] = scores.get(exact, 0.0) + 1e6                   # 名前そのものなら先頭
    hits = []
    for i, s in scores.items():
        r = rows[i]
        if in_sort and r.get("i") != in_sort:
            continue
        if out_sort and r.get("o") != out_sort:
            continue
        if dim and r.get("d") != dim:
            continue
        hits.append((-s, r["n"], i))
    hits.sort()
    show = lang or _pick_lang(query, q, [rows[i] for _, _, i in hits[:10]])
    out = []
    for neg, _, i in hits[:k]:
        r = rows[i]
        summ = r.get("s") or {}
        out.append({"name": r["n"], "dim": r.get("d"), "category": r.get("c"),
                    "in_sort": r.get("i"), "out_sort": r.get("o"), "halcon": r.get("h"),
                    "note": r.get("p"), "summary": summ.get(show) or summ.get("en") or summ.get("ja") or "",
                    "score": round(-neg, 3)})
    hint = None
    if not out:
        known = [t for t in q if t in idf]
        hint = ("どの語も索引に無い。別の言い方・英語・op 名の一部を試す" if not known else
                "語は当たったが絞り込み(in_sort / out_sort / dim)で 0 件")
    return {"query": query, "lang": show, "total": len(hits), "n_ops_indexed": ix["n_ops"],
            "ops": out, "hint": hint}


def _format(res: dict) -> str:
    lines = ["%d op が当たった(索引 %d op、表示言語 %s)" % (res["total"], res["n_ops_indexed"], res["lang"])]
    for j, o in enumerate(res["ops"], 1):
        sort = "%s -> %s" % (o["in_sort"], o["out_sort"]) if o["in_sort"] or o["out_sort"] else ""
        lines.append("%2d. %s  [%s/%s] %s" % (j, o["name"], o["dim"], o["category"], sort))
        if o["summary"]:
            s = o["summary"].replace("\n", " ")
            lines.append("    " + (s if len(s) <= 160 else s[:157] + "..."))
        if o["note"]:
            lines.append("    note: " + o["note"])
    if res.get("hint"):
        lines.append("hint: " + res["hint"])
    return "\n".join(lines)


def main(argv=None) -> int:
    """``fullseye-rag search <query>`` / ``py -m fullseye.opsearch <query>`` の本体。"""
    import argparse
    ap = argparse.ArgumentParser(prog="fullseye-rag search",
                                 description="Find Fullseye operators by what they do (ja/en/zh/tw/ko/de).")
    ap.add_argument("query", nargs="+", help="what you want to do, in any of the six languages")
    ap.add_argument("-k", type=int, default=10, help="how many rows (default 10)")
    ap.add_argument("--lang", choices=LANGS, default=None, help="summary language (default: from the query)")
    ap.add_argument("--in-sort", default=None)
    ap.add_argument("--out-sort", default=None)
    ap.add_argument("--dim", default=None, help="family, e.g. 2d / 3d / optics / piv")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)
    res = search_ops(" ".join(a.query), a.k, lang=a.lang, in_sort=a.in_sort, out_sort=a.out_sort, dim=a.dim)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        import sys
        text = _format(res)
        try:
            print(text)
        except UnicodeEncodeError:                      # cp932 等の端末: 落とさず置換して出す
            sys.stdout.buffer.write((text + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))
    return 0 if res["ops"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
