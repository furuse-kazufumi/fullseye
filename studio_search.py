# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_search — 「やりたいこと」から op を探し、今の入力に合うかで 3 群に分ける(Studio の論理層、Qt を使わない)。

Studio の UX 案 ①(目的検索): 利用者は正式な op 名を知らない。「小さい領域を消す」と打つと、
名前の一覧ではなく次の 3 群で返す。

* ``applicable``         — 今の入力の型(sort)のまま適用できる(台帳が宣言している、または
  :func:`opassist.accepted_sorts` の**実測**が ``works``)。
* ``needs_preprocessing`` — 型が合わないが、2 手以内の前処理(producers / consumers で繋ぐ op の列 = ``bridge``)で届く。
* ``other``              — 今の入力が分からない、または 2 手以内では届かない。

★設計の約束

* 検索そのものは :func:`fullseye.opsearch.search_ops` に任せ、**順位は作り直さない**
  (群の中の並びは検索の点数順 = 同点は ``search_ops`` の並びのまま)。
* :func:`opassist.accepted_sorts` は op を何度も走らせて測る高価な関数。**上位 k 件にだけ**、
  型が宣言と合わなかった台帳 op にだけ使い、op ごとに ``_ACCEPTED`` へ覚える(全レジストリには掛けない)。
* 型の語彙は 2 つある(台帳 = ``image2d`` / ``mask`` …、2-D レジストリ = ``image`` / ``region`` …)。
  同じものを指す対を :data:`SORT_ALIASES` で同一視してから比べる。
* このモジュールは**提案を返すだけ**。処理列へ追加も実行もしない(UI が「今のデータで試す」で一時試行する)。

Qt 非依存・標準ライブラリ + numpy のみ(``opassist`` / ``fullseye.opsearch`` は同梱)。
"""
from __future__ import annotations

import difflib
from collections import Counter
from typing import Any, Optional

import numpy as np

__all__ = [
    "current_sort_of", "search_grouped", "search_zero_results_help",
    "SORT_ALIASES", "canonical_sort", "clear_caches",
]

#: 台帳の型名 → 2-D レジストリの型名(同じものを指す対)。比べる前にこれで寄せる。
SORT_ALIASES = {
    "image2d": "image", "mask": "region", "rgbimage": "color", "rgb": "color", "voxel": "volume",
}

#: 群の名前(この順に並べる)
GROUPS = ("applicable", "needs_preprocessing", "other")

#: ``accepted_sorts`` の実測結果を op ごとに覚える(高価なので。テストは :func:`clear_caches` で空にする)
_ACCEPTED: dict = {}
_EDGE_CACHE: dict = {}
_BRIDGE_CACHE: dict = {}
_NAME_CACHE: dict = {}


def clear_caches() -> None:
    """実測・型グラフ・名前表の覚えを捨てる(テストと、台帳が変わった後の再計算用)。"""
    _ACCEPTED.clear()
    _EDGE_CACHE.clear()
    _BRIDGE_CACHE.clear()
    _NAME_CACHE.clear()


def canonical_sort(sort: Optional[str]) -> Optional[str]:
    """型名を台帳・レジストリ共通の代表名に寄せる(``image2d`` → ``image``、``mask`` → ``region`` …)。"""
    if sort is None:
        return None
    return SORT_ALIASES.get(sort, sort)


# --------------------------------------------------------------------------- #
# 今の値 → 型                                                                  #
# --------------------------------------------------------------------------- #
def _is_binary(a: np.ndarray) -> bool:
    """値が 0/1 だけ(``studio._is_binary`` と同じ規則)。"""
    if a.dtype == bool:
        return True
    b = np.asarray(a, dtype=np.float64) if a.dtype.kind in "iu" else a
    u = np.unique(b[np.isfinite(b)]) if b.size else b
    return u.size <= 2 and set(np.round(u, 6).tolist()).issubset({0.0, 1.0})


def _looks_like_labels(a: np.ndarray) -> bool:
    """整数の 2 次元で、0.. の密な番号が付いた**ラベル画像**らしいか(ヒューリスティック)。

    8 ビット画像は階調が多いので、値の種類が 16 以下のときだけラベルとみなす。
    曖昧な値は呼び出し側が ``current_sort`` で上書きする。
    """
    if a.dtype.kind not in "iu" or a.ndim != 2 or a.size == 0:
        return False
    if int(a.min()) < 0:
        return False
    u = np.unique(a)
    n = int(u.size)
    if n < 3:
        return False
    if a.dtype == np.uint8 and n > 16:
        return False
    return n <= max(16, a.size // 64) and n >= 0.9 * (int(u.max()) - int(u.min()) + 1)


def current_sort_of(value: Any) -> Optional[str]:
    """実際の値から、台帳の型(sort)名を推す。分からなければ ``None``。

    * 2 次元: 二値 → ``mask``、ラベルらしい整数 → ``labels2d``、複素 → ``cimage``、他 → ``image2d``
    * 3 次元: ``(2, h, w)`` の実数 → ``flow2d``、最後の軸が 3 → ``rgbimage``、4 → ``rgba``、1 → ``image2d``、他 → ``voxel``
    * 1 次元の数列・数の列 → ``signal``、``(N, 3)``(N ≥ 4, 実数)→ ``points``
    * ``cs`` を持つ dict → ``contour``、他の dict → ``table``、数 → ``scalar``、文字列 → ``text``

    ★``(N, 3)`` は 3 画素幅の画像とも読めるが、実用上は点群が圧倒的なので ``points`` に倒す。
    推定は :func:`studio.inspect_result` の ``kind`` と矛盾しない(門が同じ見本で照合する)。
    """
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_, int, float, np.number)):
        return "scalar"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        return "contour" if "cs" in value else "table"
    if hasattr(value, "cs") and not isinstance(value, np.ndarray):
        return "contour"
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        if all(isinstance(v, dict) for v in value):
            return "table"
        if all(isinstance(v, (int, float, np.number)) and not isinstance(v, bool) for v in value):
            return "signal"
        if all(isinstance(v, np.ndarray) and v.ndim == 2 and v.shape == value[0].shape for v in value):
            return "images"
        return None
    if not isinstance(value, np.ndarray):
        return None
    a = value
    if a.size == 0 or a.dtype.kind not in "biufc":
        return None
    if a.ndim == 0:
        return "scalar"
    if a.ndim == 1:
        return "signal"
    if a.ndim == 2:
        if a.dtype.kind == "c":
            return "cimage"
        if a.shape[1] == 3 and a.shape[0] >= 4 and a.dtype.kind == "f":
            return "points"
        if _is_binary(a):
            return "mask"
        if _looks_like_labels(a):
            return "labels2d"
        return "image2d"
    if a.ndim == 3:
        if a.shape[0] == 2 and a.shape[1] >= 2 and a.shape[2] >= 2 and a.shape[2] not in (3, 4) \
                and a.dtype.kind in "biuf":
            return "flow2d"
        if a.shape[2] == 3:
            return "rgbimage"
        if a.shape[2] == 4:
            return "rgba"
        if a.shape[2] == 1:
            return "image2d"
        return "voxel"
    if a.ndim == 4:
        return "rgbvideo" if a.shape[3] == 3 else "volseq"
    return None


# --------------------------------------------------------------------------- #
# 索引と台帳の表                                                               #
# --------------------------------------------------------------------------- #
def _index() -> dict:
    from fullseye import opsearch
    return opsearch.load_index()


def _row_of(name: str) -> Optional[dict]:
    ix = _index()
    i = ix["names"].get(name.lower())
    return ix["rows"][i] if i is not None else None


def _first_sort(in_sort: Optional[str]) -> tuple[Optional[str], list]:
    """``"image2d × mask"`` → (``"image2d"``, [``"mask"``])。入力が無ければ (None, [])。"""
    if not in_sort:
        return None, []
    parts = [p.strip() for p in in_sort.split("×") if p.strip()]
    return (parts[0] if parts else None), parts[1:]


def _ledger_names() -> frozenset:
    if "ledger" not in _NAME_CACHE:
        import opassist
        _NAME_CACHE["ledger"] = frozenset(opassist.known_ops())
    return _NAME_CACHE["ledger"]


def _is_registry(name: str) -> bool:
    import api
    return api.find_op(name) is not None


def _tier(name: str) -> str:
    """どの層の op か: ``registry``(単入力の 2-D レジストリ)/ ``ledger``(型付き台帳)/ ``nary``(複数入力の 2-D)/
    ``z_algo``(汎用アルゴリズム)/ ``unavailable``。索引に在るのにこの環境では登録されていない op
    (任意の依存が無い CI の一部の殻など)は ``unavailable`` —— 検索には出すが、UI は走らせられない印にする。"""
    if _is_registry(name):
        return "registry"
    if name in _ledger_names():
        return "ledger"
    if "tiers" not in _NAME_CACHE:
        import api
        _NAME_CACHE["tiers"] = {d["name"]: d["tier"] for d in api.list_ops(include_ledger=True, include_algo=True)}
    return _NAME_CACHE["tiers"].get(name, "unavailable")


def _edges() -> dict:
    """単入力 op の辺 ``{名前: (入力の代表型, 出力の代表型)}``。索引の i / o 欄が正本(台帳 + レジストリ)。"""
    if "edges" not in _EDGE_CACHE:
        edges = {}
        for r in _index()["rows"]:
            i, o = r.get("i"), r.get("o")
            if not i or not o or "×" in i or "×" in o:
                continue
            edges[r["n"]] = (canonical_sort(i), canonical_sort(o))
        _EDGE_CACHE["edges"] = edges
    return _EDGE_CACHE["edges"]


def _class_members(cls: str) -> list:
    """代表型 ``cls`` に寄る台帳側の型名(``producers`` / ``consumers`` に渡せるもの)。"""
    import opassist
    known = set(opassist.known_sorts())
    return [s for s in known if canonical_sort(s) == cls]


def _consuming(cls: str) -> set:
    """代表型 ``cls`` を単独の入力に取る op の名前(台帳は ``opassist.consumers``、レジストリは索引)。"""
    import opassist
    edges = _edges()
    found = {n for n, (i, _o) in edges.items() if i == cls}
    for s in _class_members(cls):
        found |= {n for n in opassist.consumers(s) if n in edges and edges[n][0] == cls}
    return found


def _producing(cls: str) -> set:
    """代表型 ``cls`` を単入力から作る op の名前(台帳は ``opassist.producers``)。"""
    import opassist
    edges = _edges()
    found = {n for n, (_i, o) in edges.items() if o == cls}
    for s in _class_members(cls):
        found |= {n for n in opassist.producers(s) if n in edges and edges[n][1] == cls}
    return found


def _required_knobs(name: str) -> int:
    """必須のつまみ(データ以外で既定値の無い引数)の数。台帳 op だけ数え、他は 0。"""
    if "req" not in _NAME_CACHE:
        _NAME_CACHE["req"] = {}
    memo = _NAME_CACHE["req"]
    if name not in memo:
        try:
            import opassist
            memo[name] = sum(1 for sp in opassist.param_spec(name)
                             if sp.get("kind") != "data" and sp.get("required"))
        except Exception:                                    # noqa: BLE001 - 数えられない op は 0 とみなす
            memo[name] = 0
    return memo[name]


def _bridge_rank(name: str) -> tuple:
    """橋渡し op の選び方: この環境で動く → 既定のまま走る(必須のつまみが少ない)→ レジストリの基本 op → 名前の短い順 → 辞書順(決定的)。"""
    return (1 if _tier(name) == "unavailable" else 0, _required_knobs(name), 0 if _is_registry(name) else 1,
            len(name), name)


def _bridge(cur: Optional[str], target: Optional[str], exclude: str = "") -> list:
    """現在の型 ``cur`` から ``target`` へ繋ぐ**最短の op の列**(0 手は無い。2 手まで。無ければ ``[]``)。"""
    if cur is None or target is None or cur == target:
        return []
    key = (cur, target, exclude)
    if key in _BRIDGE_CACHE:
        return list(_BRIDGE_CACHE[key])
    edges = _edges()
    prod = _producing(target) - {exclude}
    cons = _consuming(cur) - {exclude}
    one = sorted(prod & cons, key=_bridge_rank)
    if one:
        res = [one[0]]
    else:
        res = []
        by_mid: dict = {}
        for a in cons:
            mid = edges[a][1]
            if mid in (cur, target):
                continue
            by_mid.setdefault(mid, []).append(a)
        best = None
        for mid in sorted(by_mid):
            second = sorted(prod & _consuming(mid), key=_bridge_rank)
            if not second:
                continue
            first = sorted(by_mid[mid], key=_bridge_rank)[0]
            cand = (_bridge_rank(first), _bridge_rank(second[0]), [first, second[0]])
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best is not None:
            res = best[2]
    _BRIDGE_CACHE[key] = tuple(res)
    return list(res)


# --------------------------------------------------------------------------- #
# 適合の判定                                                                   #
# --------------------------------------------------------------------------- #
def _fits_declared(in_sort: Optional[str], cur: Optional[str]) -> bool:
    """宣言された先頭入力の型が今の型と同じ(別名を寄せて比較)。``any`` は何でも通る。入力の無い op は False。"""
    first, _rest = _first_sort(in_sort)
    if first is None or cur is None:
        return False
    return first == "any" or canonical_sort(first) == cur


def _measured_works(name: str, cur_sort: str) -> bool:
    """台帳 op が宣言外の今の型も**実測で通す**か(``accepted_sorts`` の ``works``)。結果は op ごとに覚える。"""
    import opassist
    if name not in _ACCEPTED:
        try:
            _ACCEPTED[name] = opassist.accepted_sorts(name)
        except Exception:                                    # noqa: BLE001 - 測れない op は「通すとは言わない」
            _ACCEPTED[name] = {}
    got = _ACCEPTED[name]
    names = [cur_sort] + [s for s, c in SORT_ALIASES.items() if c == canonical_sort(cur_sort)]
    return any(got.get(s) in ("declared", "works") for s in names)


# --------------------------------------------------------------------------- #
# 当たった理由                                                                 #
# --------------------------------------------------------------------------- #
def _why(query: str, row: dict) -> list:
    """問い合わせのどの欄に当たったか: ``name`` / ``alias`` / ``summary`` / ``synonym`` / ``context`` / ``meta``。"""
    from fullseye import opsearch as so
    q = set(so.tokenize(query))
    extra = set(so._synonym_tokens(query, set(q)))
    if not q and not extra:
        return []
    name_t = set(so.tokenize(row["n"]))
    alias_t = set(so.tokenize(row.get("h") or ""))
    summ_t: set = set()
    for txt in (row.get("s") or {}).values():
        summ_t |= set(so.tokenize(txt))
    ctx_t: set = set()
    for txt in list(row.get("t") or ()) + list(row.get("te") or ()):
        ctx_t |= set(so.tokenize(txt))
    meta_t = set(so.tokenize(" ".join(x for x in (row.get("d"), row.get("c"), row.get("i"), row.get("o")) if x)))
    out = []
    if (q & name_t) or so._norm(query.strip()).replace(" ", "_") == so._norm(row["n"]):
        out.append("name")
    if q & alias_t:
        out.append("alias")
    if q & summ_t:
        out.append("summary")
    if extra & (name_t | alias_t | summ_t | ctx_t | meta_t):
        out.append("synonym")
    if q & ctx_t:
        out.append("context")
    if q & meta_t and not out:
        out.append("meta")
    return out


def _label(hit: dict) -> str:
    """表示名: 表示言語の要約の 1 行目。無ければ op 名。"""
    s = (hit.get("summary") or "").strip().splitlines()
    return s[0].strip() if s else hit["name"]


# --------------------------------------------------------------------------- #
# 本体                                                                         #
# --------------------------------------------------------------------------- #
def search_grouped(query: str, current_value: Any = None, current_sort: Optional[str] = None,
                   k: int = 20, lang: Optional[str] = None) -> dict:
    """「やりたいこと」で探し、今の入力に合うかで 3 群に分けて返す。

    Parameters
    ----------
    query : 検索語(:data:`fullseye.opsearch.LANGS` のどの言語でも)。
    current_value : 今の入力の値。型は :func:`current_sort_of` が推す。
    current_sort : 型を呼び出し側が分かっているときはこれが優先(推定を上書き)。
    k : 検索で取る件数の上限。``accepted_sorts`` の実測も**高々 k 回**。
    lang : 表示言語(既定は問い合わせから推す)。

    Returns
    -------
    ``{"query", "lang", "current_sort", "total", "applicable", "needs_preprocessing", "other", "help"}``。
    各行は ``{"name", "label", "in_sort", "out_sort", "score", "why", "tier", "fit", "bridge", "extra_inputs"}``。
    ``fit`` は ``declared`` / ``measured`` / ``bridge`` / ``none`` / ``unknown``(今の型が分からない)/ ``no_input``。
    該当が 0 件のときだけ ``help``(:func:`search_zero_results_help`)が入る。

    ★群の中の並びは ``search_ops`` の点数順のまま。今の型が分からなければ全部 ``other`` で、並びは
    ``search_ops`` と 1 対 1 に一致する。
    """
    from fullseye import opsearch
    if not isinstance(query, str) or not query.strip():
        raise ValueError("search_grouped: query must be a non-empty string")
    res = opsearch.search_ops(query, k, lang=lang)
    cur_raw = current_sort if current_sort is not None else current_sort_of(current_value)
    cur = canonical_sort(cur_raw)
    groups: dict = {g: [] for g in GROUPS}
    for rank, hit in enumerate(res["ops"]):
        row_idx = _row_of(hit["name"])
        first, rest = _first_sort(hit["in_sort"])
        entry = {
            "name": hit["name"], "label": _label(hit), "in_sort": hit["in_sort"], "out_sort": hit["out_sort"],
            "score": hit["score"], "why": _why(query, row_idx) if row_idx else [], "tier": _tier(hit["name"]),
            "fit": "unknown", "bridge": [], "extra_inputs": rest, "_rank": rank,
        }
        if cur is None:
            group = "other"
        elif first is None:
            entry["fit"] = "no_input"
            group = "other"
        elif _fits_declared(hit["in_sort"], cur):
            entry["fit"] = "declared"
            group = "applicable"
        elif entry["tier"] == "ledger" and _measured_works(hit["name"], cur_raw):
            entry["fit"] = "measured"
            group = "applicable"
        else:
            br = _bridge(cur, canonical_sort(first), exclude=hit["name"])
            entry["bridge"] = br
            entry["fit"] = "bridge" if br else "none"
            group = "needs_preprocessing" if br else "other"
        groups[group].append(entry)
    for g in GROUPS:
        groups[g].sort(key=lambda e: (-e["score"], e["_rank"]))
        for e in groups[g]:
            e.pop("_rank", None)
    out = {"query": query, "lang": res["lang"], "current_sort": cur_raw, "total": res["total"], **groups, "help": None}
    if not res["ops"]:
        out["help"] = search_zero_results_help(query, res["lang"])
    return out


def _op_names() -> list:
    if "names" not in _NAME_CACHE:
        _NAME_CACHE["names"] = sorted(r["n"] for r in _index()["rows"])
    return _NAME_CACHE["names"]


def nearest_op_names(name: str, n: int = 5) -> list:
    """綴りの近い op 名(``difflib`` の類似度順)。無ければ空。壊れた/未知の op 名の案内に使う。"""
    if not isinstance(name, str) or not name.strip():
        return []
    return difflib.get_close_matches(name.strip().lower(), _op_names(), n=n, cutoff=0.5)


def search_zero_results_help(query: str, lang: Optional[str] = None) -> dict:
    """検索が 0 件のときの**立て直しの手掛かり**(空の一覧で終わらせない)。

    返り: ``{"query", "unknown_terms", "nearest_terms", "nearest_ops", "categories", "sorts", "hint"}``。

    * ``nearest_terms`` — 索引に無い語ごとに、綴りの近い索引の語と、言い換え表(``SYNONYMS``)の同じ組の語
    * ``nearest_ops``   — 問い合わせ全体に綴りの近い op 名
    * ``categories``    — 近い op のカテゴリ(無ければ索引で多いカテゴリ)
    * ``sorts``         — 近い op の入出力の型(無ければ索引で多い型)
    * ``hint``          — 利用者向けの 1 文(``lang`` が ``en`` 以外なら日本語)
    """
    from fullseye import opsearch as so
    ix = _index()
    toks = list(dict.fromkeys(so.tokenize(query))) if isinstance(query, str) else []
    idf = ix["idf"]
    unknown = [t for t in toks if t not in idf]
    vocab = sorted(idf)
    nearest_terms: dict = {}
    for t in unknown:
        near = difflib.get_close_matches(t, vocab, n=5, cutoff=0.6)
        if near:
            nearest_terms[t] = near
    fq = so._fold(query) if isinstance(query, str) else ""
    syn = []
    for group in so.SYNONYMS:
        if any(so._fold(w) in fq for w in group):
            syn.extend(w for w in group if so._fold(w) not in fq)
    if syn:
        nearest_terms["<synonym>"] = list(dict.fromkeys(syn))
    q_name = (query or "").strip().lower().replace(" ", "_")
    ops = difflib.get_close_matches(q_name, _op_names(), n=5, cutoff=0.5) if q_name else []
    rows = [r for r in (_row_of(n) for n in ops) if r]
    cats = Counter(r.get("c") for r in rows if r.get("c"))
    sorts = Counter(s for r in rows for s in (r.get("i"), r.get("o")) if s)
    if not cats:
        cats = Counter(r.get("c") for r in ix["rows"] if r.get("c"))
    if not sorts:
        sorts = Counter(s for r in ix["rows"] for s in (r.get("i"), r.get("o")) if s and "×" not in s)
    use_en = lang in (None, "en", "de")
    hint = ("No operator matched. Try another wording, an English term, or part of an operator name; "
            "the categories and types below show what exists."
            if use_en else
            "該当する op がありません。別の言い方・英語・op 名の一部を試すか、下のカテゴリと型から探してください。")
    return {"query": query, "unknown_terms": unknown, "nearest_terms": nearest_terms, "nearest_ops": ops,
            "categories": [c for c, _ in cats.most_common(8)], "sorts": [s for s, _ in sorts.most_common(8)],
            "hint": hint}
