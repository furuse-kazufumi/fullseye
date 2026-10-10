# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Find operators by what they do, in any of the supported languages -> ranked rows.

意味で op を引く検索(RAG の入口)。``fullseye.search_ops("ノイズ除去")`` /
``fullseye-rag search "remove noise"`` / MCP ``fullseye_find_ops`` が同じ関数を呼ぶ。

**なぜ要るか(2026-10-07 実測)**: 知識層のノート ``docs/ops`` は本文が日本語なので、grep は
「Rauschen」「降噪」「잡음」で 0 件、「vanishing point」でも 0 件だった。op 名の部分一致
(MCP ``fullseye_search_ops``)は名前を知っている人にしか効かない。一方で全 op の要約は
``docs/i18n/op_summary.json`` に en / zh / tw / ko / de の訳がある —— それを検索面にする。

**何を照合するか**: op 名(``_`` で区切った語)・HALCON 名・族 / 分類・入出力の型と、
要約の多言語訳(ja 原文 + en / zh / tw / ko / de / hi)。順位は BM25(語の希少さで重み付け)。

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
LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi")
PKG_SEARCH = "OP_SEARCH.json"
_STEM = 6
_K1, _B = 1.2, 0.75
#: 場ごとの重み: 名前に入っている語は要約の語より強い手掛かり
_W_NAME, _W_HALCON, _W_META, _W_SUMMARY = 3, 2, 1, 1

_LATIN = re.compile(r"[0-9a-zß-ɏ]+")
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")
_HANGUL = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]+")
_KANA = re.compile(r"[぀-ヿ]")
#: デーヴァナーガリー(ヒンディー語)。語は空白で区切られるので語ごとに切る(母音記号・virama も語の内側)
_DEVANAGARI = re.compile(r"[ऀ-ॿ꣠-ꣿ]+")
_GERMAN = re.compile(r"[äöüß]|\b(?:der|die|das|und|nicht|mit|eines?|bild|kante|rauschen)\b")

_CACHE: dict = {}

#: 同じ言語の中の言い換え(手で書いた表、2026-10-07)。要約の 6 言語は**言語をまたぐ**対応は持っているが、
#: 同じ言語の別の言い方(「檢測」と「偵測」、「校正」と「キャリブレーション」)は持たない。問い合わせにどれかが
#: あれば残りを弱い重み(:data:`_W_SYNONYM`)で足す。表に無い言い換えは拾わない(``hint`` で案内する)。
SYNONYMS: tuple = (
    ("ノイズ除去", "雑音除去", "デノイズ", "ノイズ低減"), ("平滑化", "ぼかし", "スムージング"),
    ("二値化", "しきい値", "閾値"), ("校正", "較正", "キャリブレーション"), ("エッジ", "縁"),
    ("検出", "抽出"), ("点群", "ポイントクラウド"), ("位置合わせ", "レジストレーション", "整列"),
    ("去噪", "降噪", "除噪"), ("边缘", "边沿"), ("二值化", "阈值"), ("标定", "校准"), ("检测", "提取"),
    ("檢測", "偵測"), ("雜訊", "噪聲", "噪訊"), ("邊緣", "邊沿"), ("校正", "標定", "校準"), ("閾值", "臨界值"),
    ("잡음", "노이즈"), ("에지", "엣지"), ("검출", "탐지", "추출"), ("보정", "교정", "캘리브레이션"),
    ("이진화", "임계값"), ("평활화", "스무딩", "블러"),
    ("kante", "kanten"), ("rauschen", "entrauschen", "rauschunterdruckung"), ("glattung", "glatten", "weichzeichnen"),
    ("kalibrierung", "kalibrieren"), ("schwellwert", "schwelle", "binarisierung"),
    ("denoise", "noise", "despeckle"), ("blur", "smooth", "smoothing"), ("threshold", "binarize", "binarization"),
    ("calibration", "calibrate"), ("edge", "edges"), ("detect", "detection"),
    ("registration", "align", "alignment"),
)
_W_SYNONYM = 0.6

#: ヒンディー語の機能語(後置詞・助動詞・代名詞)。どの要約にも出るので、残すと「का」1 語で 1,000 op が当たる
#: (2026-10-07 実測: 「किनारे का पता लगाना」が 1,226 件・上位は無関係)。索引と問い合わせの両方から外す。
_HI_STOP = frozenset("""के का की को में से पर है हैं था थे थी और या एक यह वह ये वे जो तो भी ही
    कर करता करती करते करें करना किया होता होती होते होना हो गया गई गए वाला वाली वाले लिए साथ तक द्वारा
    इस उस इन उन कि नहीं न अपने अपना अपनी लगाना पता""".split())

#: ヒンディー語の日常語 → 英語の術語(訳の方針で術語は英語のまま書いたので、日常語で引いても当たるように)。
#: 言語をまたぐ組はこの表だけ(他の言語は要約自体が訳語で書かれている)。
HI_TERMS: tuple = (
    ("किनारा", "किनारे", "किनारों", "edge"), ("शोर", "noise"), ("पहचान", "पहचानना", "detect"),
    ("धुंधला", "blur"), ("चिकना", "smooth"), ("रंग", "color", "colour"), ("सीमा", "threshold"),
    ("कोना", "कोने", "corner"), ("गहराई", "depth"), ("मापना", "माप", "measure"), ("आकार", "shape"),
    ("बिंदु", "point"), ("रेखा", "line"), ("वृत्त", "circle"), ("प्रकाश", "light"), ("कैमरा", "camera"),
)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").lower()


def tokenize(text: str) -> list[str]:
    """検索語に切る: ラテン文字は語(長い語は先頭 6 文字)、漢字・仮名・ハングルは 2 文字ずつ。"""
    t = _norm(text).replace("_", " ")
    out: list[str] = []
    for w in _LATIN.findall(t):
        out.append(w[:_STEM] if len(w) > _STEM else w)
    out.extend(w for w in _DEVANAGARI.findall(t) if w not in ("।", "॥") and w not in _HI_STOP)
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
    if _DEVANAGARI.search(q):
        return "hi"
    if _HANGUL.search(q):
        return "ko"
    if _KANA.search(q):
        return "ja"
    if _CJK.search(q):
        return "zh"
    if _GERMAN.search(q):
        return "de"
    return "en"


def _fold(text: str) -> str:
    """言い換え表の照合用: NFKC・小文字・ウムラウトを落とす(Glättung → glattung)。"""
    t = unicodedata.normalize("NFKD", _norm(text))
    return "".join(c for c in t if not unicodedata.combining(c)).replace("ß", "ss")


def _synonym_tokens(query: str, have: set) -> list[str]:
    """問い合わせに含まれる言い換え表の語について、同じ組の他の語の検索語(既にあるものは除く)。"""
    fq = _fold(query)
    out: list[str] = []
    for group in SYNONYMS + HI_TERMS:
        if any(_fold(w) in fq for w in group):
            for w in group:
                for tok in tokenize(w):
                    if tok not in have and tok not in out:
                        out.append(tok)
    return out


def _pick_lang(query: str, qtok: list, top_rows: list) -> str:
    """表示言語: ハングル → ko、仮名 → ja は文字で決まる。それ以外(漢字だけ・ラテン文字)は
    文字種では ja / zh / tw、en / de を分けられないので、**上位の op の要約のうち問い合わせの語を
    いちばん多く含む言語**を採る(同点は :func:`detect_lang` の推定を優先)。"""
    guess = detect_lang(query)
    if guess in ("ko", "ja", "hi") or not top_rows:
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
    names, aliases = _name_tables(rows)
    built = {"rows": rows, "docs": docs, "lens": lens, "avg": avg, "idf": idf, "names": names,
             "aliases": aliases,
             "n_ops": n, "languages": raw.get("languages") or list(LANGS)}
    _CACHE[key] = built
    return built


def _name_tables(rows: list) -> tuple[dict, dict]:
    """完全一致で先頭に上げる表を 2 枚: op 名そのもの → 行、HALCON 別名 → 行。

    ★2026-10-11: 1 枚の表に op 名と別名を「先に出た行が勝つ」で混ぜていたので、
    ``gauss_filter`` を問うと、その名前を**別名として**名乗る前の行 ``cv_gaussian`` が先頭に
    来た(op ``gauss_filter`` 自身は 4 位)。38 op が自分の名前で引けなかった。
    名前は op 名の表を先に引き、別名は ``api.find_op`` の規則(完全一致 → ``name == halcon``
    → ``_ALIAS_CANONICAL``)が選ぶ op —— ``fullseye.apply(x, 別名)`` が実際に走らせる op —— に
    だけ与える。registry に無い別名(他の層)は従来どおり先に出た行。
    """
    names: dict = {}
    for i, r in enumerate(rows):
        names.setdefault(_norm(r["n"]), i)
    try:
        import api as _api
        find_op = _api.find_op
    except Exception:  # noqa: BLE001 - the index must stay usable without the facade
        find_op = None
    aliases: dict = {}
    for i, r in enumerate(rows):
        h = r.get("h")
        if not h:
            continue
        key = _norm(h)
        if key in aliases:
            continue
        canon = None
        if find_op is not None:
            try:
                op = find_op(h)
            except Exception:  # noqa: BLE001
                op = None
            if op is not None:
                canon = names.get(_norm(op.name))
        if canon is None:
            canon = i
        aliases[key] = canon
    return names, aliases


def search_ops(query: str, k: int = 10, *, lang: str | None = None, in_sort: str | None = None,
               out_sort: str | None = None, dim: str | None = None, index_path: str | None = None) -> dict:
    """``query``(:data:`LANGS` のどの言語でも)に合う op を順位つきで返す。

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
    extra = _synonym_tokens(query, set(q))
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
    for tok in extra:
        w = idf.get(tok)
        if w is None:
            continue
        for i, tf in enumerate(docs):
            f = tf.get(tok)
            if f:
                scores[i] = scores.get(i, 0.0) + _W_SYNONYM * w * f * (_K1 + 1) / (
                    f + _K1 * (1 - _B + _B * lens[i] / avg))
    # 語を多く含む op を上に(一般語 1 つだけで当たった op が、語を全部含む op を追い越さない)。
    # 言い換えだけで当たった op も 0 にはしない(問い合わせの語が索引に無い言い方でも引けるように)
    for i in scores:
        scores[i] *= max(matched[i], 0.5) / max(len(q), 1)
    key = _norm(query.strip()).replace(" ", "_")
    exact = ix["names"].get(key)                                       # op 名そのものが先
    if exact is None:
        exact = ix.get("aliases", {}).get(key)                         # 次に、apply が走らせる別名先
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
                                 description="Find Fullseye operators by what they do (ja/en/zh/tw/ko/de/hi).")
    ap.add_argument("query", nargs="+", help="what you want to do, in any supported language")
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
