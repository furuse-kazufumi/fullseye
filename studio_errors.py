# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_errors — 失敗を「原因・場所・次の行動」に分けて説明する(Studio の論理層、Qt を使わない)。

Studio の UX 案 ⑦(直せるエラー): 「ValueError: left/right must be equal-shape 2-D arrays」の 1 行ではなく、

    ステレオ処理を実行できません
    原因   : 入力の大きさが一致しません(left は 1920×1080、right は 1280×720)
    場所   : 段 3 / disparity_map
    次にできること : [入力を選び直す] [入力を並べて確認] [詳細ログ]

を返す。**提案だけを返し、何も実行しない**。特に、計測では意味が変わる「大きさを合わせて再実行」の類
(自動の修復)は、行動の種類(:data:`ACTION_KINDS`)に**存在しない**。門が 30 件の合成例外で
「許された種類の外が 1 つも無い」ことを数える。

* :func:`explain_failure` — 例外 + 場所 + 入力 → ``dict``(title / cause / place / evidence / actions / raw)
* :func:`format_failure`  — その dict を Problems 欄に出す複数行の文字列(ja / en)

文言は ``{"ja": ..., "en": ...}`` の対で持つ(Studio の i18n 表へ載せ替えやすいように ``title["key"]`` を付ける)。
標準ライブラリ + numpy のみ。入力が無くても、例外の型・文面だけで原因を言えるものは言う。
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable, Optional

import numpy as np

__all__ = [
    "explain_failure", "format_failure", "ACTION_KINDS", "FAILURE_CLASSES", "localize",
]

#: 提案できる行動の種類(これ以外は作らない。自動修復・自動リサイズの類は意図して無い)。
ACTION_KINDS = frozenset({
    "reselect_input", "show_inputs_side_by_side", "open_log", "edit_knob", "insert_stage",
})

#: 認識する失敗の種類(``title["key"]`` は ``err.<種類>``)。
FAILURE_CLASSES = (
    "dependency", "unknown_op", "shape_mismatch", "non_finite", "empty", "out_of_range",
    "dimension", "wrong_sort", "generic",
)

_TITLES = {
    "dependency": ("追加のライブラリが必要です", "An optional dependency is missing"),
    "unknown_op": ("op が見つかりません", "Operator not found"),
    "shape_mismatch": ("入力の大きさが一致しません", "Input sizes do not match"),
    "non_finite": ("入力に NaN / Inf が含まれます", "The input contains NaN / Inf"),
    "empty": ("入力が空です", "The input is empty"),
    "out_of_range": ("つまみの値が範囲の外です", "A knob value is out of range"),
    "dimension": ("入力の次元が合いません", "The input has the wrong number of dimensions"),
    "wrong_sort": ("入力の型が合いません", "The input type does not fit"),
    "generic": ("処理を実行できませんでした", "The step could not run"),
}


def localize(text: Any, lang: str = "ja") -> str:
    """``{"ja": ..., "en": ...}`` から ``lang`` の文を取る(無ければ en → ja)。文字列はそのまま返す。"""
    if isinstance(text, dict):
        return str(text.get(lang) or text.get("en") or text.get("ja") or "")
    return "" if text is None else str(text)


# --------------------------------------------------------------------------- #
# 入力の事実                                                                   #
# --------------------------------------------------------------------------- #
def _safe_text(exc: Any) -> str:
    """例外の文面。``str()`` が壊れた例外でも落とさない。``KeyError`` は引用符で包まれないよう第 1 引数を使う。"""
    try:
        if isinstance(exc, KeyError) and exc.args and isinstance(exc.args[0], str):
            return exc.args[0]
        return str(exc)
    except Exception:                                        # noqa: BLE001
        try:
            return repr(exc)
        except Exception:                                    # noqa: BLE001
            return "<unprintable %s>" % type(exc).__name__


def _normalise_inputs(inputs: Any) -> list:
    """入力を ``[{"label", "value", "file"}]`` にそろえる。

    ``inputs`` は ``None`` / 値のリスト / ``{ラベル: 値}``。値は配列でも、``{"value": 配列, "file": "left.png"}``
    の形(ファイル名つき)でもよい。★1 つの表(dict)を直接渡すとラベルの dict と読まれるので、リストで包むこと。
    """
    if inputs is None:
        return []
    if isinstance(inputs, dict):
        items = list(inputs.items())
    elif isinstance(inputs, (list, tuple)):
        items = [("input %d" % (i + 1), v) for i, v in enumerate(inputs)]
    else:
        items = [("input 1", inputs)]
    out = []
    for label, v in items:
        file = None
        if isinstance(v, dict) and "value" in v and set(v) <= {"value", "file", "path", "label"}:
            file = v.get("file") or v.get("path")
            label = v.get("label") or label
            v = v["value"]
        out.append({"label": str(label), "value": v, "file": os.path.basename(str(file)) if file else None})
    return out


def _size_text(shape: tuple) -> str:
    """画像らしい形(2 次元、または最後の軸が 4 以下の 3 次元)は 幅×高さ、他は軸を × でつなぐ。"""
    if len(shape) == 2 or (len(shape) == 3 and shape[2] <= 4):
        return "%d×%d" % (shape[1], shape[0])
    return "×".join(str(int(s)) for s in shape) if shape else "scalar"


def _fact_of(item: dict) -> dict:
    """入力 1 つの事実: 形・型・有限の数・値域・最初の非有限の位置・ファイル名。壊れた入力でも落とさない。"""
    v = item["value"]
    row: dict = {"kind": "input", "input": item["label"], "file": item["file"], "type": type(v).__name__,
                 "shape": None, "size_text": None, "dtype": None, "sort": None,
                 "finite": None, "nonfinite": None, "first_nonfinite_index": None, "min": None, "max": None}
    try:
        from studio_search import current_sort_of
        row["sort"] = current_sort_of(v)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        if isinstance(v, np.ndarray):
            row["shape"] = tuple(int(s) for s in v.shape)
            row["size_text"] = _size_text(row["shape"])
            row["dtype"] = str(v.dtype)
            if v.dtype.kind in "fc" and v.size:
                bad = ~np.isfinite(v)
                nb = int(bad.sum())
                row["nonfinite"] = nb
                row["finite"] = int(v.size - nb)
                if nb:
                    row["first_nonfinite_index"] = tuple(int(i) for i in np.unravel_index(int(np.argmax(bad)), v.shape))
                good = v[~bad]
                if good.size:
                    num = np.abs(good) if v.dtype.kind == "c" else good
                    row["min"], row["max"] = float(num.min()), float(num.max())
            elif v.dtype.kind in "biu" and v.size:
                row["nonfinite"], row["finite"] = 0, int(v.size)
                row["min"], row["max"] = float(v.min()), float(v.max())
        elif isinstance(v, dict):
            row["n_fields"] = len(v)
        elif isinstance(v, (list, tuple)):
            row["length"] = len(v)
        elif isinstance(v, (int, float, np.number)) and not isinstance(v, bool):
            row["min"] = row["max"] = float(v)
    except Exception:                                        # noqa: BLE001 - 事実が取れなくても説明は続ける
        pass
    return row


# --------------------------------------------------------------------------- #
# 文面の読み取り                                                               #
# --------------------------------------------------------------------------- #
_SHAPE_RE = re.compile(
    r"equal[- ]shape|same (?:shape|size)|shapes? .{0,40}(?:mismatch|differ|do not match|don't match|!=|not aligned)"
    r"|(?:mismatch|differ).{0,30}shape|could not be broadcast|size mismatch|length mismatch|dimension mismatch"
    r"|must (?:have|share) the same|shape \([^)]*\) != ", re.I)
_NONFINITE_RE = re.compile(r"non-?finite|nan\s*/\s*inf|\bNaN\b|contains? (?:nan|inf)|has no finite|非有限", re.I)
_KNOB_FINITE_RE = re.compile(r"^\W*(?:\w+[.:]\s*)?(?:[A-Za-z_]\w*)\s+must be finite", re.I)
_EMPTY_RE = re.compile(r"\bis empty\b|\bempty\b|zero-size|size 0\b|non-empty|no (?:data|samples|pixels)|空", re.I)
_RANGE_CUE_RE = re.compile(
    r"must (?:be|lie)\s+(?:strictly\s+)?(?:in\b|within|between|>=|<=|>|<|at least|at most|positive|non-?negative"
    r"|odd|even|one of|an? \w+ in\b)|must lie|out of range|\boutside\b|\bin \[|\bin \(|\d\s*\.\.\s*\d", re.I)
_DIM_RE = re.compile(r"must be (?:a )?(\d)-D|expected (\d)-?D|(\d)-D (?:array|input) (?:required|expected)", re.I)
_UNKNOWN_OP_RE = re.compile(r"unknown (?:operator|op)\b|not in any ledger|no such (?:operator|op)\b", re.I)
_DEP_RE = re.compile(r"optional (?:dependency|backend)|pip install|not installed|is not available here"
                     r"|No module named|failed to load", re.I)
_EXPECT_TABLE_RE = re.compile(r"(?:expected|must be|requires?|needs?)\s+(?:a |an |the )?(?:table|dict|mapping)"
                              r"|expected the dict|must be the dict|returned by", re.I)
_ARG_RE = re.compile(r"(?:^|[\s:(])([A-Za-z_]\w*)(?:\s*\([^)]*\))?\s+(?:must|should|has to)\b")
_GOT_RE = re.compile(r"\bgot\s+(?:[A-Za-z_]\w*=)?([^\s,;)]+)", re.I)
_INTERVAL_RE = re.compile(r"([\[(])\s*(-?\d+(?:\.\d+)?(?:e-?\d+)?)\s*,\s*(-?\d+(?:\.\d+)?(?:e-?\d+)?|inf)\s*([\])])", re.I)
_DOTS_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)")
_BETWEEN_RE = re.compile(r"between\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)", re.I)
_REL_RE = re.compile(r"must be\s+(?:an? \w+\s+)?(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)", re.I)
_GENERIC_WORDS = frozenset({"it", "this", "that", "which", "value", "input", "there", "and", "or", "all", "each"})


def _range_of(msg: str) -> Optional[dict]:
    """文面から許される範囲を取る: 区間 ``[a, b]`` / ``a..b`` / ``between a and b`` / ``>= a`` / ``one of …``。無ければ None。"""
    m = _INTERVAL_RE.search(msg)
    if m:
        lo, hi = float(m.group(2)), (float("inf") if m.group(3).lower() == "inf" else float(m.group(3)))
        return {"text": "%s%s, %s%s" % (m.group(1), m.group(2), m.group(3), m.group(4)), "lo": lo, "hi": hi,
                "lo_open": m.group(1) == "(", "hi_open": m.group(4) == ")"}
    m = _DOTS_RE.search(msg)
    if m:
        return {"text": "%s..%s" % (m.group(1), m.group(2)), "lo": float(m.group(1)), "hi": float(m.group(2)),
                "lo_open": False, "hi_open": False}
    m = _BETWEEN_RE.search(msg)
    if m:
        strict = "strictly" in msg.lower() or "lie strictly" in msg.lower()
        return {"text": "%s < x < %s" % (m.group(1), m.group(2)) if strict else "%s..%s" % (m.group(1), m.group(2)),
                "lo": float(m.group(1)), "hi": float(m.group(2)), "lo_open": strict, "hi_open": strict}
    m = _REL_RE.search(msg)
    if m:
        v = float(m.group(2))
        op = m.group(1)
        d = {"text": "%s %s" % (op, m.group(2)), "lo": None, "hi": None, "lo_open": False, "hi_open": False}
        if op in (">", ">="):
            d["lo"], d["lo_open"] = v, op == ">"
        else:
            d["hi"], d["hi_open"] = v, op == "<"
        return d
    m = re.search(r"one of\s+(.+?)(?:,\s*got\b|$)", msg, re.I)
    if m:
        return {"text": "one of " + m.group(1).strip(), "lo": None, "hi": None, "lo_open": False, "hi_open": False}
    return None


def _arg_of(msg: str, op_name: Optional[str]) -> Optional[str]:
    """文面の ``<名前> must …`` から引数名を取る。op の引数に実在すればそれを優先して確かめる。"""
    names = []
    for m in _ARG_RE.finditer(msg):
        n = m.group(1)
        if n.lower() not in _GENERIC_WORDS:
            names.append(n)
    if not names:
        return None
    if op_name:
        try:
            import opassist
            known = {sp["name"] for sp in opassist.param_spec(op_name)}
            for n in names:
                if n in known:
                    return n
        except Exception:                                    # noqa: BLE001 - 台帳に無い op(2-D レジストリ)など
            pass
    return names[0]


def _extra_of(exc: BaseException, msg: str) -> tuple[Optional[str], Optional[str]]:
    """欠けた依存の (パッケージ名, extra 名)。``fullseye[xxx]`` の記述 → ``ops.OPTIONAL_DEPS`` → 文面の順。"""
    extra = None
    m = re.search(r"fullseye\[([^\]]+)\]", msg)
    if m:
        extra = m.group(1)
    pkg = getattr(exc, "name", None) if isinstance(exc, ImportError) else None
    if not pkg:
        m = re.search(r"No module named '([\w.]+)'", msg)
        pkg = m.group(1).split(".")[0] if m else None
    if not pkg:
        m = re.search(r"optional (?:dependency|backend)\s+([\w\-]+)", msg, re.I)
        pkg = m.group(1) if m else None
    if not pkg:
        m = re.search(r"pip install\s+(?!\")([\w\-.]+)", msg)
        pkg = m.group(1) if m else None
    if pkg and extra is None:
        try:
            import ops
            dep = ops.OPTIONAL_DEPS.get(pkg.split(".")[0])
            if dep:
                pkg, extra = dep[0], dep[1]
        except Exception:                                    # noqa: BLE001
            pass
    return pkg, extra


# --------------------------------------------------------------------------- #
# 分類                                                                         #
# --------------------------------------------------------------------------- #
def _declared_in_sort(op_name: Optional[str]) -> Optional[str]:
    """op の宣言された先頭入力の型(索引の i 欄)。分からなければ None。"""
    if not op_name:
        return None
    try:
        from studio_search import _first_sort, _row_of
        row = _row_of(op_name)
        return _first_sort(row.get("i"))[0] if row else None
    except Exception:                                        # noqa: BLE001
        return None


def _sort_mismatch(op_name: Optional[str], facts: list) -> Optional[tuple]:
    """(想定の型, 渡された型) か None。台帳/索引が宣言する先頭入力の型と、先頭の入力の型が合わないとき。"""
    exp = _declared_in_sort(op_name)
    if not exp or not facts or exp == "any":
        return None
    given = facts[0].get("sort")
    if not given:
        return None
    from studio_search import canonical_sort
    if canonical_sort(exp) == canonical_sort(given):
        return None
    return exp, given


def _classify(exc: Any, msg: str, op_name: Optional[str], facts: list) -> str:
    low_types = {c.__name__ for c in type(exc).__mro__}
    if isinstance(exc, ImportError) or "MissingBackendError" in low_types or _DEP_RE.search(msg):
        if not _UNKNOWN_OP_RE.search(msg) or isinstance(exc, ImportError) or "MissingBackendError" in low_types \
                or re.search(r"pip install|not installed|optional (?:dependency|backend)", msg, re.I):
            return "dependency"
    if _UNKNOWN_OP_RE.search(msg) and ("KeyError" in low_types or "ValueError" in low_types or "LookupError" in low_types):
        return "unknown_op"
    if _SHAPE_RE.search(msg):
        return "shape_mismatch"
    knob_finite = bool(re.search(r"\b[A-Za-z_]\w*\s+must be finite", msg))
    has_nonfinite_input = any((f.get("nonfinite") or 0) > 0 for f in facts)
    if (_NONFINITE_RE.search(msg) and not knob_finite) or (has_nonfinite_input and not _RANGE_CUE_RE.search(msg)
                                                          and not _SHAPE_RE.search(msg)):
        return "non_finite"
    if knob_finite or _RANGE_CUE_RE.search(msg):
        return "out_of_range"
    if _EMPTY_RE.search(msg) or any(f.get("shape") is not None and 0 in f["shape"] for f in facts):
        return "empty"
    if _DIM_RE.search(msg):
        return "dimension"
    mism = _sort_mismatch(op_name, facts)
    if (_EXPECT_TABLE_RE.search(msg) and facts and facts[0].get("sort") not in (None, "table", "contour")) or \
            (mism is not None and low_types & {"TypeError", "IndexError", "AttributeError", "ValueError", "KeyError"}):
        return "wrong_sort"
    return "generic"


# --------------------------------------------------------------------------- #
# 文の組み立て                                                                 #
# --------------------------------------------------------------------------- #
def _pair(ja: str, en: str) -> dict:
    return {"ja": ja, "en": en}


def _act(kind: str, ja: str, en: str, **extra: Any) -> dict:
    assert kind in ACTION_KINDS, kind
    d = {"kind": kind, "label": _pair(ja, en)}
    d.update(extra)
    return d


def _name(f: dict) -> str:
    return f["input"] + ("(%s)" % f["file"] if f.get("file") else "")


def explain_failure(exc: Any, *, op_name: Optional[str] = None, stage_index: Optional[int] = None,
                    inputs: Any = None) -> dict:
    """例外を「原因・場所・次の行動」に分けて説明する(**提案だけ。何も実行・変更しない**)。

    Parameters
    ----------
    exc : 起きた例外(例外でない値も文字列として受ける)。
    op_name : 失敗した op の名前(分かれば)。
    stage_index : 失敗した段の番号(0 始まり。表示は +1)。
    inputs : その op に渡した入力。リスト、または ``{ラベル: 値}``。値は配列か、
        ``{"value": 配列, "file": "left.png"}``(ファイル名つき)。

    Returns
    -------
    ``{"class", "title": {"key","ja","en"}, "cause": {"ja","en"}, "place": {"stage","op","arg"},
    "evidence": [...], "actions": [{"kind","label":{"ja","en"}}], "raw", "exc_type"}``。

    * ``evidence`` — 入力ごとの事実(形・型・有限の数・値域・最初の非有限の位置・ファイル名)と、
      種類ごとの追加の事実(範囲・欠けた依存と extra・近い op 名)。
    * ``actions`` の ``kind`` は :data:`ACTION_KINDS` の 5 種類だけ。
    * 例外の文面が壊れていても、分類が失敗しても、``generic`` で場所と ``raw`` を埋めて返す(落とさない)。
    """
    try:
        return _explain(exc, op_name, stage_index, inputs)
    except Exception as inner:                               # noqa: BLE001 - 説明の失敗で本来のエラーを隠さない
        return _fallback(exc, op_name, stage_index, "internal: %s" % type(inner).__name__)


def _fallback(exc: Any, op_name: Optional[str], stage_index: Optional[int], note: str = "") -> dict:
    msg = _safe_text(exc)
    title = _TITLES["generic"]
    return {
        "class": "generic", "title": {"key": "err.generic", "ja": title[0], "en": title[1]},
        "cause": _pair("原因を特定できませんでした: %s" % (msg[:160] or type(exc).__name__),
                       "The cause could not be identified: %s" % (msg[:160] or type(exc).__name__)),
        "place": {"stage": stage_index, "op": op_name, "arg": None},
        "evidence": [{"kind": "note", "text": note}] if note else [],
        "actions": [_act("open_log", "詳細ログを開く", "Open the detailed log")],
        "raw": msg, "exc_type": type(exc).__name__,
    }


def _explain(exc: Any, op_name: Optional[str], stage_index: Optional[int], inputs: Any) -> dict:
    msg = _safe_text(exc)
    items = _normalise_inputs(inputs)
    facts = [_fact_of(it) for it in items]
    cls = _classify(exc, msg, op_name, facts)
    arg: Optional[str] = None
    evidence: list = list(facts)
    actions: list = []
    open_log = _act("open_log", "詳細ログを開く", "Open the detailed log")
    reselect = _act("reselect_input", "入力を選び直す", "Choose the input again")
    side = _act("show_inputs_side_by_side", "入力を並べて確認する", "Compare the inputs side by side")
    op_txt = op_name or "?"

    if cls == "dependency":
        pkg, extra = _extra_of(exc, msg)
        pkg_txt = pkg or "?"
        cause = _pair("%s に必要なオプションのライブラリ %s が入っていません。" % (op_txt, pkg_txt)
                      + (("(extra: %s)" % extra) if extra else ""),
                      "%s needs the optional package %s, which is not installed." % (op_txt, pkg_txt)
                      + ((" (extra: %s)" % extra) if extra else ""))
        install = ('pip install "fullseye[%s]"' % extra) if extra else ("pip install %s" % pkg_txt if pkg else None)
        evidence = [{"kind": "dependency", "package": pkg, "extra": extra, "install": install}]
        actions = [open_log]
    elif cls == "unknown_op":
        m = re.search(r"['\"]([^'\"]+)['\"]", msg)
        bad = m.group(1) if m else (op_name or "")
        try:
            from studio_search import nearest_op_names
            near = nearest_op_names(bad)
        except Exception:                                    # noqa: BLE001
            near = []
        cause = _pair("op 名 %r は登録されていません。" % bad, "The operator name %r is not registered." % bad)
        evidence = [{"kind": "nearest_ops", "query": bad, "names": near}]
        if near:
            actions = [_act("insert_stage", "近い op から選び直す: " + ", ".join(near[:3]),
                            "Pick a near operator instead: " + ", ".join(near[:3]), candidates=near[:3])]
        actions.append(open_log)
    elif cls == "shape_mismatch":
        shaped = [f for f in facts if f.get("shape") is not None]
        distinct: list = []
        for f in shaped:
            if all(f["shape"] != g["shape"] for g in distinct):
                distinct.append(f)
        if len(distinct) >= 2:
            a, b = distinct[0], distinct[1]
            cause = _pair("入力の大きさが一致しません: %s は %s、%s は %s です。" % (_name(a), a["size_text"], _name(b), b["size_text"]),
                          "Input sizes differ: %s is %s, %s is %s." % (_name(a), a["size_text"], _name(b), b["size_text"]))
        else:
            cause = _pair("入力の形が一致しません(%s)。" % msg[:100], "Input shapes do not match (%s)." % msg[:100])
        actions = [reselect, side, open_log]
    elif cls == "non_finite":
        bad = [f for f in facts if (f.get("nonfinite") or 0) > 0]
        if bad:
            f = bad[0]
            cause = _pair("入力 %s に NaN / Inf が %d 個あります(最初の位置 %s)。" % (_name(f), f["nonfinite"], list(f["first_nonfinite_index"])),
                          "Input %s has %d NaN / Inf value(s) (first at %s)." % (_name(f), f["nonfinite"], list(f["first_nonfinite_index"])))
        else:
            cause = _pair("入力に NaN / Inf が含まれます。", "The input contains NaN / Inf.")
        actions = [reselect, side, open_log]
    elif cls == "empty":
        e = [f for f in facts if f.get("shape") is not None and 0 in f["shape"]]
        if e:
            cause = _pair("入力 %s が空です(形 %s)。" % (_name(e[0]), list(e[0]["shape"])),
                          "Input %s is empty (shape %s)." % (_name(e[0]), list(e[0]["shape"])))
        else:
            cause = _pair("入力が空です。", "The input is empty.")
        actions = [reselect, open_log]
    elif cls == "out_of_range":
        arg = _arg_of(msg, op_name)
        rng = _range_of(msg)
        gm = _GOT_RE.search(msg)
        val = gm.group(1) if gm else None
        arg_txt = arg or "?"
        ja = "つまみ %s の値%s が許される範囲の外です" % (arg_txt, (" " + val) if val else "")
        en = "The value%s of knob %s is outside the allowed range" % ((" " + val) if val else "", arg_txt)
        if rng:
            ja += "(許される範囲: %s)。" % rng["text"]
            en += " (allowed: %s)." % rng["text"]
        else:
            ja += "。"
            en += "."
        cause = _pair(ja, en)
        evidence = facts + [{"kind": "knob", "arg": arg, "value": val, "range": rng}]
        actions = [_act("edit_knob", "つまみ %s を範囲内に直す" % arg_txt, "Set knob %s inside the range" % arg_txt, arg=arg), open_log]
    elif cls == "dimension":
        m = _DIM_RE.search(msg)
        want = next((g for g in (m.groups() if m else ()) if g), "?")
        f0 = facts[0] if facts else None
        have = len(f0["shape"]) if f0 and f0.get("shape") is not None else None
        cause = _pair("%s 次元の入力が必要ですが、%s 次元が渡されました。" % (want, have if have is not None else "別の"),
                      "A %s-D input is required, but %s was given." % (want, ("a %d-D array" % have) if have is not None else "another shape"))
        actions = [reselect, side, open_log]
    elif cls == "wrong_sort":
        mism = _sort_mismatch(op_name, facts)
        exp = mism[0] if mism else ("table" if _EXPECT_TABLE_RE.search(msg) else "?")
        given = mism[1] if mism else (facts[0].get("sort") if facts else None) or "?"
        cause = _pair("%s は %s 型の入力を想定しますが、%s 型が渡されました。" % (op_txt, exp, given),
                      "%s expects a %s input, but a %s input was given." % (op_txt, exp, given))
        evidence = facts + [{"kind": "sorts", "expected": exp, "given": given}]
        actions = [reselect]
        try:
            from studio_search import _bridge, canonical_sort
            br = _bridge(canonical_sort(given), canonical_sort(exp))
        except Exception:                                    # noqa: BLE001
            br = []
        if br:
            actions.append(_act("insert_stage", "型をつなぐ op を前に足す案: " + " → ".join(br),
                                "Proposal: add the op(s) that bridge the types: " + " → ".join(br), candidates=br))
        actions.append(open_log)
    else:
        cls = "generic"
        first = msg.strip().splitlines()[0] if msg.strip() else type(exc).__name__
        cause = _pair("実行中にエラーが起きました: %s" % first[:200], "An error occurred while running: %s" % first[:200])
        arg = _arg_of(msg, op_name)
        actions = ([side] if len(facts) >= 2 else []) + [open_log]
    ti = _TITLES[cls]
    return {
        "class": cls, "title": {"key": "err." + cls, "ja": ti[0], "en": ti[1]}, "cause": cause,
        "place": {"stage": stage_index, "op": op_name, "arg": arg}, "evidence": evidence,
        "actions": actions, "raw": msg, "exc_type": type(exc).__name__,
    }


# --------------------------------------------------------------------------- #
# Problems 欄の文面                                                            #
# --------------------------------------------------------------------------- #
_HEADERS = {
    "ja": {"cause": "原因", "place": "場所", "facts": "入力の事実", "next": "次にできること", "raw": "詳細",
           "stage": "段 %d", "arg": "引数 %s", "note": "(提案だけです。入力も設定も書き換えていません)"},
    "en": {"cause": "Cause", "place": "Place", "facts": "Facts about the inputs", "next": "What you can do next",
           "raw": "Detail", "stage": "stage %d", "arg": "argument %s",
           "note": "(Proposals only. Nothing was changed in your inputs or settings.)"},
}


def _cell(v: Any) -> str:
    return "-" if v is None else str(v)


def format_failure(info: dict, lang: str = "ja") -> str:
    """:func:`explain_failure` の結果を Problems 欄用の複数行にする(``ja`` / ``en``)。

    見出しは 原因 / 場所 / 次にできること(en は Cause / Place / What you can do next)。
    入力の事実は表にする。**自動で直す類の文言は出さない**(行動は提案のみ)。
    """
    lg = "en" if lang == "en" else "ja"
    h = _HEADERS[lg]
    lines = [localize(info["title"], lg), "", h["cause"], "  " + localize(info["cause"], lg), "", h["place"]]
    pl = info.get("place") or {}
    parts = []
    if pl.get("stage") is not None:
        parts.append(h["stage"] % (int(pl["stage"]) + 1))
    if pl.get("op"):
        parts.append(str(pl["op"]))
    if pl.get("arg"):
        parts.append(h["arg"] % pl["arg"])
    lines.append("  " + (" / ".join(parts) if parts else "-"))
    inputs = [e for e in info.get("evidence", []) if e.get("kind") == "input"]
    extras = [e for e in info.get("evidence", []) if e.get("kind") != "input"]
    if inputs or extras:
        lines += ["", h["facts"]]
    if inputs:
        head = ("入力", "ファイル", "大きさ", "型", "有限/非有限", "値域") if lg == "ja" else \
               ("input", "file", "size", "dtype", "finite/non-finite", "range")
        rows = [head]
        for e in inputs:
            rng = "[%.6g, %.6g]" % (e["min"], e["max"]) if e.get("min") is not None else "-"
            fin = "%s/%s" % (_cell(e.get("finite")), _cell(e.get("nonfinite")))
            rows.append((e["input"], _cell(e.get("file")), _cell(e.get("size_text")), _cell(e.get("dtype") or e.get("type")), fin, rng))
        w = [max(len(r[i]) for r in rows) for i in range(len(head))]
        for r in rows:
            lines.append("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip())
    for e in extras:
        k = e.get("kind")
        if k == "knob":
            rg = (e.get("range") or {}).get("text")
            lines.append("  %s = %s%s" % (e.get("arg") or "?", _cell(e.get("value")), ("   [%s]" % rg) if rg else ""))
        elif k == "nearest_ops":
            lines.append("  " + ("近い名前: " if lg == "ja" else "nearest names: ") + (", ".join(e.get("names") or []) or "-"))
        elif k == "dependency":
            lines.append("  %s%s" % (e.get("install") or "-", ("  (extra: %s)" % e["extra"]) if e.get("extra") else ""))
        elif k == "sorts":
            lines.append("  " + ("想定 %s / 実際 %s" if lg == "ja" else "expected %s / given %s") % (e.get("expected"), e.get("given")))
    lines += ["", h["next"]]
    for i, a in enumerate(info.get("actions", []), 1):
        lines.append("  %d. %s" % (i, localize(a["label"], lg)))
    lines.append("  " + h["note"])
    if info.get("raw"):
        lines += ["", h["raw"], "  " + str(info["raw"]).replace("\n", "\n  ")]
    return "\n".join(lines)
