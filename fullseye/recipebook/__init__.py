"""recipebook — 型で繋がる op の組み合わせ例(レシピ)を族ごとに網羅し、全部を実際に走らせる.

Fullseye ships ~3,600 operators in 56 documentation families (``docs/ops/<family>/``). ``recipes.py``
holds the 25 Studio sample pipelines (2-D registry ops only, ``(op, a, b)``). This package adds
**coverage recipes**: at least one per family, each one a typed chain whose every stage feeds the
next by the op graph's declared sorts, and each one executed by the test suite on a structured,
synthetic input with a known answer (``tests/test_recipebook.py``).

A recipe is plain data::

    {"name": "DEM — slope of a tilted plane",          # unique, business language first
     "family": "dem",                                   # docs/ops/<family> of one of its stage ops
     "task": "measure",                                 # short task word (as in recipes.py)
     "task_class": "measurement",                       # one of TASK_CLASSES
     "halcon": None,                                    # HALCON chapter it is typical of, or None
     "input_sort": "depth",                             # sort of the recipe input (None = generator first)
     "sample": "dem_tilted_plane",                      # name in SAMPLES (input + truth for the tests)
     "stages": [{"op": "dem_slope", "kw": {"cell_size": 1.0}}],
     "expect": [{"get": ["@median"], "approx": "slope_deg", "atol": 0.05}],
     "note": "..."}

Stage forms
-----------
* registry op (2-D ``ops.REGISTRY``): ``{"op": "gaussian", "a": 0.4, "b": 0.5}`` — run by
  ``api.apply(value, op, a, b, device="cpu")``, the same call MCP's ``fullseye_apply`` makes.
* ledger / module op: ``{"op": "dem_slope", "args": [...], "kw": {...}}`` — run by the op graph's
  executor (``fullseye/data/OP_GRAPH.json``: ``module.callable``). ``args`` defaults to
  ``["$prev"]`` (the previous stage's output; the recipe input for stage 1; nothing for a generator).

A ledger stage is called through ``fs.ledger.<op>`` (the call line of every op note; it returns the
declared sort). ``"call": "raw"`` (with a ``"call_reason"``) calls the OP_GRAPH executor instead — only
for stages whose ledger entry is broken; the reason is the finding.

References inside ``args`` / ``kw`` (strings starting with ``$``): ``$prev``, ``$in`` (recipe input),
``$s1`` .. ``$sN`` (output of stage k), ``$aux.<key>`` (an auxiliary value the sample provides, e.g. a
reference image or a known pose). ``$$text`` escapes a literal string starting with ``$``.

Expect forms (truth gates, evaluated on every sample variant)
-------------------------------------------------------------
``{"get": [...], "approx": "<truth key>" | number, "rtol": r, "atol": a}``,
``{"get": [...], "between": [lo, hi]}``, ``{"get": [...], "equals": "<truth key>" | value}``.
``get`` walks the final output (or ``"$sK"`` as first step for stage k): a string is a dict key or
attribute, an int is an index, and ``@len @sum @mean @median @max @min @abs @std @count @float
@ptp @argmax`` reduce.

Honest scope: the inputs are synthetic; a passing recipe proves the chain runs, its sorts connect and
(where an ``expect`` exists) that it recovers a closed-form truth on that input — not real-data accuracy.
"""
from __future__ import annotations

import importlib
import math
import os
from functools import lru_cache

import numpy as np

#: 典型の課題の分類(依頼の「検査・計測・3D・光学・センシング・前処理」+ 解析・模擬・可視化)。
TASK_CLASSES = ("inspection", "measurement", "3d", "optics", "sensing", "preprocess",
                "analysis", "simulation", "visualization")

#: 本の並び。足したらここに 1 行(読み込み順 = 索引の並び)。
BOOKS = ("book_2d", "book_measure", "book_3d", "book_optics", "book_misc")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))


def _load_books():
    from fullseye.recipebook.common import COMMON_SAMPLES
    recipes, samples, missing, where, failed = [], dict(COMMON_SAMPLES), [], {}, []
    # RECIPEBOOK_BOOK=book_3d で 1 冊だけ読む(本を書いている途中、他の本の壊れに巻き込まれないため)。
    only = os.environ.get("RECIPEBOOK_BOOK")
    for mod_name in BOOKS:
        if only and mod_name != only:
            continue
        try:
            mod = importlib.import_module("fullseye.recipebook." + mod_name)
        except ModuleNotFoundError as exc:          # 本が未だ無い(途中の状態)ことだけを許す
            if exc.name == "fullseye.recipebook." + mod_name:
                continue
            raise
        for r in getattr(mod, "RECIPES", ()):
            recipes.append(r)
            where[r["name"]] = mod_name
        for k, fn in getattr(mod, "SAMPLES", {}).items():
            if k in samples and samples[k] is not fn:
                raise ValueError("sample %r is defined twice (%s)" % (k, mod_name))
            samples[k] = fn
        missing.extend(dict(m, book=mod_name) for m in getattr(mod, "MISSING_OPS", ()))
        failed.extend(dict(f, book=mod_name) for f in getattr(mod, "FAILED_ATTEMPTS", ()))
    names = [r["name"] for r in recipes]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError("duplicate recipe names: %s" % dup)
    return recipes, samples, missing, where, failed


RECIPES, SAMPLES, MISSING_OPS, BOOK_OF, FAILED_ATTEMPTS = _load_books()


def names() -> list:
    return [r["name"] for r in RECIPES]


def get(name: str):
    return next((r for r in RECIPES if r["name"] == name), None)


# ---- the op graph ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _edges() -> dict:
    from fullseye.opsearch import _graph
    return {e["op"]: e for e in _graph()["edges"]}


def edge(op: str) -> dict | None:
    """OP_GRAPH の 1 辺(op の入出力の型・実行先)。無ければ None。"""
    return _edges().get(op)


def norm_sort(s):
    from fullseye.opsearch import normalize_sort
    return normalize_sort(s)


@lru_cache(maxsize=1)
def op_families() -> dict:
    """op 名 -> その op ノートがある docs/ops の族の集合(同名ノートが 2 族にある op が数個ある)。"""
    out = {}
    base = os.path.join(_ROOT, "docs", "ops")
    for fam in sorted(os.listdir(base)):
        fdir = os.path.join(base, fam)
        if fam.startswith("_") or not os.path.isdir(fdir):
            continue
        for cat in os.listdir(fdir):
            cdir = os.path.join(fdir, cat)
            if cat == "guides" or not os.path.isdir(cdir):
                continue
            for fn in os.listdir(cdir):
                if fn.endswith(".md"):
                    out.setdefault(fn[:-3], set()).add(fam)
    return out


@lru_cache(maxsize=1)
def families() -> tuple:
    """docs/ops の族(op ノートを 1 枚以上持つ最上位フォルダ)。網羅の分母。"""
    return tuple(sorted({f for fams in op_families().values() for f in fams}))


def _is_registry(op: str) -> bool:
    e = edge(op) or {}
    return (e.get("executor") or {}).get("kind") == "registry"


def _callable(op: str, raw: bool = False):
    """op の呼び口。**台帳の入口 ``fs.ledger.<op>`` が先**(op ノートの「呼び出し」行と同じ)。

    ★2026-11-03: 最初は OP_GRAPH の executor(生の関数)を直に呼んでいた。生の関数の多くは
    ``(値, 情報)`` のタプルを返し、宣言の型どおりに直すのは台帳の adapter(RESULT_ADAPTERS)の
    仕事なので、astrostack / piv / lightfield / specular の鎖が「宣言の嘘」に見えて組めなかった
    (book_optics の実測)。利用者が呼ぶのは台帳の入口なので、レシピもそこを通す。生の値が
    要る段は無い(要れば ``fs.ledger.<op>.raw`` を executor にした op を別に足すこと)。
    """
    e = edge(op)
    if e is None:
        raise KeyError("op %r is not in OP_GRAPH" % op)
    import fullseye
    led = getattr(fullseye.ledger, op, None)
    if callable(led) and not raw:
        return led
    tgt = e.get("executor") or e.get("runtime_target") or {}
    mod, fn = tgt.get("module"), tgt.get("callable")
    if not mod or not fn:
        # ★OP_GRAPH に実行先の無い辺が 20 本ある(fileio 14 など、2026-11-03 実測)。op ノートの
        #   「呼び出し」行が案内する台帳の入口 fs.ledger.<op> を引く(無ければ従来どおり拒否)。
        import fullseye
        obj = getattr(fullseye.ledger, op, None)
        if callable(obj):
            return obj
        raise KeyError("op %r has no python executor in OP_GRAPH (%r) nor fullseye.ledger" % (op, tgt))
    obj = importlib.import_module(mod)
    for part in fn.split("."):
        obj = getattr(obj, part)
    return obj


# ---- static analysis: how the stages connect -------------------------------------------------
def _ref_stage(ref, i):
    """参照文字列が指す段番号(0 = レシピ入力)。段を指さない参照は None。"""
    if not isinstance(ref, str) or not ref.startswith("$") or ref.startswith("$$"):
        return None
    if ref == "$prev":
        return i - 1
    if ref == "$in":
        return 0
    if ref[:2] == "$s" and ref[2:].isdigit():
        return int(ref[2:])
    return None


def stage_args(stage: dict, i: int) -> list:
    """段 *i*(1 始まり)の位置引数の参照列。既定は ``["$prev"]``(生成器 = 入力 0 本の op は ``[]``)。"""
    if "args" in stage:
        return list(stage["args"])
    e = edge(stage["op"]) or {}
    if _is_registry(stage["op"]):
        return ["$prev"]
    return ["$prev"] if e.get("inputs") else []


def connections(recipe: dict) -> list:
    """段の間の型の繋がり。1 行 = (段, 引数位置, 来る型, 受ける型, 繋がるか)。

    「来る型」は参照先の段の宣言した出力型(``any``/``poly`` は受けた型を通す)、段 0 はレシピの
    ``input_sort``。受ける型は OP_GRAPH の ``inputs[j]``。どちらかが ``any``/``poly`` なら繋がる。
    """
    rows, out_sorts = [], {0: norm_sort(recipe.get("input_sort"))}
    for i, st in enumerate(recipe["stages"], 1):
        e = edge(st["op"])
        if e is None:
            rows.append((i, 0, None, None, False))
            out_sorts[i] = None
            continue
        ins = [norm_sort(x) for x in e.get("inputs", [])]
        first_actual = None
        for j, ref in enumerate(stage_args(st, i)):
            k = _ref_stage(ref, i)
            if k is None:
                continue
            got = out_sorts.get(k)
            want = ins[j] if j < len(ins) else None
            if j == 0:
                first_actual = got
            ok = (want in ("any", "poly") or got in ("any", "poly") or (got is not None and got == want))
            rows.append((i, j, got, want, ok))
        o = norm_sort(e.get("output"))
        out_sorts[i] = first_actual if o in ("any", "poly") and first_actual else o
    return rows


def type_cuts(recipe: dict) -> int:
    """型の切れ目の数(宣言の型が段の間で合わない箇所)。0 が目標。"""
    return sum(1 for r in connections(recipe) if not r[4])


def output_sort(recipe: dict):
    rows_out = {0: norm_sort(recipe.get("input_sort"))}
    for i, st in enumerate(recipe["stages"], 1):
        e = edge(st["op"]) or {}
        o = norm_sort(e.get("output"))
        if o in ("any", "poly"):
            refs = [r for r in stage_args(st, i) if _ref_stage(r, i) is not None]
            o = rows_out.get(_ref_stage(refs[0], i)) if refs else o
        rows_out[i] = o
    return rows_out[len(recipe["stages"])]


def is_mcp_runnable(recipe: dict) -> bool:
    """MCP の ``fullseye_pipeline`` でそのまま走る形か(全段が MCP 検証済みの登録 op で a/b だけ)。"""
    for st in recipe["stages"]:
        e = edge(st["op"]) or {}
        if not (_is_registry(st["op"]) and e.get("verified_executable")):
            return False
        if set(st) - {"op", "a", "b"}:
            return False
    return recipe.get("input_sort") is not None


# ---- execution -------------------------------------------------------------------------------
def _resolve(v, outs: dict, aux: dict, i: int):
    if isinstance(v, str) and v.startswith("$"):
        if v.startswith("$$"):
            return v[1:]
        k = _ref_stage(v, i)
        if k is not None:
            if k not in outs:
                raise KeyError("stage %d refers to %s, which has not run" % (i, v))
            return outs[k]
        if v.startswith("$aux."):
            key = v[5:]
            if key not in aux:
                raise KeyError("stage %d needs aux %r; the sample gives %s" % (i, key, sorted(aux)))
            return aux[key]
        raise ValueError("unknown reference %r in stage %d" % (v, i))
    if isinstance(v, list):
        return [_resolve(x, outs, aux, i) for x in v]
    if isinstance(v, tuple):
        return tuple(_resolve(x, outs, aux, i) for x in v)
    if isinstance(v, dict):
        return {k: _resolve(x, outs, aux, i) for k, x in v.items()}
    return v


def run(recipe: dict, value=None, aux: dict | None = None, *, trace: list | None = None):
    """レシピを *value*(``input_sort`` の値)に走らせ、最終段の出力を返す。

    *trace* に list を渡すと、段ごとに ``{"stage", "op", "out"}`` を積む(テストが型と中身を見る)。
    例外は握りつぶさない(どの段で何が起きたかを添えて投げ直す)。
    """
    import api
    aux = dict(aux or {})
    outs = {0: value}
    for i, st in enumerate(recipe["stages"], 1):
        op = st["op"]
        try:
            if _is_registry(op) and not (set(st) - {"op", "a", "b", "args"}):
                # 登録 op は api.apply 一本。入力 2 本以上(n 項 op: abs_diff_image 等)は args の list で渡す。
                args = [_resolve(r, outs, aux, i) for r in stage_args(st, i)]
                x = args[0] if len(args) == 1 else args
                out = api.apply(x, op, float(st.get("a", 0.5)), float(st.get("b", 0.5)), device="cpu")
            else:
                fn = _callable(op, raw=st.get("call") == "raw")
                args = [_resolve(r, outs, aux, i) for r in stage_args(st, i)]
                kw = _resolve(dict(st.get("kw", {})), outs, aux, i)
                out = fn(*args, **kw)
        except Exception as exc:  # noqa: BLE001 - 段の番号と op 名を添えて投げ直す
            raise RecipeStageError("%s: stage %d (%s) raised %s: %s"
                                   % (recipe["name"], i, op, type(exc).__name__, exc)) from exc
        outs[i] = out
        if trace is not None:
            trace.append({"stage": i, "op": op, "out": out})
    return outs[len(recipe["stages"])], outs


class RecipeStageError(RuntimeError):
    """レシピのある段が例外を出した(段番号と op 名つき)。"""


# ---- reading results -------------------------------------------------------------------------
_REDUCE = {
    "@len": len, "@sum": lambda v: float(np.sum(v)), "@mean": lambda v: float(np.nanmean(v)),
    "@median": lambda v: float(np.nanmedian(v)), "@max": lambda v: float(np.nanmax(v)),
    "@min": lambda v: float(np.nanmin(v)), "@abs": lambda v: np.abs(v), "@std": lambda v: float(np.nanstd(v)),
    "@count": lambda v: int(np.count_nonzero(v)), "@float": float,
    "@ptp": lambda v: float(np.nanmax(v) - np.nanmin(v)), "@argmax": lambda v: int(np.nanargmax(v)),
}


def get_path(value, path, outs=None):
    """``get`` の道筋をたどる(``"$sK"`` で始めると段 K の出力から)。"""
    v = value
    for step in path or []:
        if isinstance(step, str) and step.startswith("$s") and step[2:].isdigit() and outs is not None:
            v = outs[int(step[2:])]
        elif isinstance(step, str) and step in _REDUCE:
            v = _REDUCE[step](np.asarray(v) if step not in ("@len", "@float") else v)
        elif isinstance(step, int):
            v = v[step]
        elif isinstance(v, dict):
            v = v[step]
        else:
            v = getattr(v, step)
    return v


def check_expect(recipe: dict, out, outs: dict, truth: dict) -> list:
    """``expect`` の門を評価し、外れた行の説明を返す(空 = 全部通った)。"""
    bad = []
    for ex in recipe.get("expect", ()):
        try:
            got = get_path(out, ex.get("get"), outs)
        except Exception as exc:  # noqa: BLE001
            bad.append("expect %r: cannot read %s (%s)" % (ex, ex.get("get"), exc))
            continue

        def want_of(key):
            return truth[key] if isinstance(key, str) else key
        if "approx" in ex:
            want = want_of(ex["approx"])
            g = float(np.asarray(got, dtype=float))
            tol = float(ex.get("atol", 0.0)) + float(ex.get("rtol", 0.0)) * abs(float(want))
            if not (math.isfinite(g) and abs(g - float(want)) <= tol):
                bad.append("expect %s ≈ %r ± %.3g, got %r" % (ex.get("get"), want, tol, g))
        elif "between" in ex:
            lo, hi = (want_of(x) for x in ex["between"])
            g = float(np.asarray(got, dtype=float))
            if not (lo <= g <= hi):
                bad.append("expect %s in [%r, %r], got %r" % (ex.get("get"), lo, hi, g))
        elif "equals" in ex:
            want = want_of(ex["equals"])
            if not np.array_equal(np.asarray(got), np.asarray(want)):
                bad.append("expect %s == %r, got %r" % (ex.get("get"), want, got))
        else:
            bad.append("expect %r has no approx/between/equals" % (ex,))
    return bad


def numeric_leaves(v, _depth=0) -> list:
    """出力の数値の葉を 1-D float 配列の列にする(dict / list / tuple / dataclass を辿る)。"""
    if _depth > 6 or v is None:
        return []
    if isinstance(v, (bool, np.bool_)):
        return [np.array([float(v)])]
    if isinstance(v, (int, float, np.integer, np.floating)):
        return [np.array([float(v)])]
    if isinstance(v, complex) or (isinstance(v, np.ndarray) and v.dtype.kind == "c"):
        a = np.asarray(v)
        return [np.abs(a).ravel().astype(float), np.angle(a).ravel().astype(float)]
    if isinstance(v, np.ndarray):
        if v.dtype.kind in "biuf":
            return [v.astype(float).ravel()]
        if v.dtype == object:
            return [x for item in v.ravel()[:4096] for x in numeric_leaves(item, _depth + 1)]
        return []
    if hasattr(v, "detach") and hasattr(v, "cpu"):                  # torch.Tensor
        return numeric_leaves(v.detach().cpu().numpy(), _depth)
    if isinstance(v, dict):
        return [x for k in sorted(v, key=str) for x in numeric_leaves(v[k], _depth + 1)]
    if isinstance(v, (list, tuple)):
        return [x for item in list(v)[:4096] for x in numeric_leaves(item, _depth + 1)]
    if hasattr(v, "__dict__"):
        return [x for k in sorted(vars(v)) if not k.startswith("_") for x in numeric_leaves(vars(v)[k], _depth + 1)]
    return []


def fingerprint(v) -> np.ndarray:
    """出力の数値の指紋(葉を連結。有限でない値は落とさずに 0 へ — 比較用)。"""
    leaves = numeric_leaves(v)
    if not leaves:
        return np.zeros(0)
    a = np.concatenate(leaves)
    return np.where(np.isfinite(a), a, 0.0)


def degeneracy(v) -> str | None:
    """判定不能な出力なら理由を返す(None = 中身がある)。

    数値の葉が無い / 有限な値が無い / 1 個より多い値が全部同じ(定数)のとき。単独のスカラは
    それ自体では定数か判定できないので、テストは**別の標本でも走らせて値が動くか**を併せて見る。
    """
    leaves = numeric_leaves(v)
    if not leaves:
        return "no numeric content (%s)" % type(v).__name__
    a = np.concatenate(leaves)
    fin = a[np.isfinite(a)]
    if fin.size == 0:
        return "no finite value (%d values)" % a.size
    if fin.size > 1 and float(fin.max() - fin.min()) == 0.0:
        return "constant output (%d values, all %r)" % (fin.size, float(fin[0]))
    return None


def sample(recipe: dict, variant: int = 0) -> dict:
    """レシピの標本(``{"value", "aux", "truth"}``)を作る。"""
    fn = SAMPLES.get(recipe["sample"])
    if fn is None:
        raise KeyError("recipe %r names sample %r, which no book defines" % (recipe["name"], recipe["sample"]))
    s = fn(variant)
    s.setdefault("aux", {})
    s.setdefault("truth", {})
    return s


__all__ = ["RECIPES", "SAMPLES", "MISSING_OPS", "FAILED_ATTEMPTS", "BOOK_OF", "TASK_CLASSES", "names", "get", "run", "sample",
           "families", "op_families", "edge", "connections", "type_cuts", "output_sort", "is_mcp_runnable",
           "check_expect", "degeneracy", "fingerprint", "get_path", "RecipeStageError"]
