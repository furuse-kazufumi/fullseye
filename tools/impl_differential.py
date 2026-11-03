# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ処理の別実装を**互いに**突き合わせる(differential testing、2026-11-03)。

## なぜ要るか

Fullseye には、同じ処理が実装ごとに別の名前の op として並んでいる組がある ——
``canny`` / ``cv_canny`` / ``sk_canny`` / ``xkor_canny``、``gaussian`` / ``cv_gaussian`` /
``xkor_gaussian``。命名整理 第 2 段(リポジトリ外の改名案の資料)はこれらを
「1 つの名前 + ``impl`` 引数」にまとめる計画だが、**まとめてよいのは本当に同じ処理だけ**で、
それを確かめた表がどこにも無かった。golden(過去の自分の出力)との比較は「昨日と同じか」しか
問わない。ここは**実装どうし**を同じ入力・同じつまみで走らせ、食い違いを数える。

## 組の数え方(:func:`find_groups`)

``docs/OP_INDEX.json`` の op 名を ``<接頭辞>_<語幹>`` に割り、**語幹が同じで接頭辞だけ違う**
名前の集まりを 1 組とする(接頭辞なしの素の名前も組に入る)。接頭辞は「実装・由来を表すもの」
だけを :data:`IMPL_PREFIXES` に列挙する —— ``vol_`` / ``mesh_`` / ``piv_`` のような**分野**の
接頭辞は入れない(``vol_boundary`` は ``boundary`` の別実装ではなく 3-D 版)。選び方は
「その接頭辞の op の大半が 1 つの backend モジュールに住む」(実測は :func:`prefix_census`)。

``tb_X`` は型付き台帳の関数 ``X`` を ``op(v, a, b)`` 規約へ橋渡ししたもの(``backends_typed.py``)。
同じ関数の別の入口なので、ここでは**引数の写し方の標本**(つまみが既定値の何倍に写るか)だけを見る
(:func:`check_tb_bridge`)。

## 比べ方(:func:`compare_outputs`)

* 画像: 端 :data:`BORDER` 画素を除いた内部の ``max|A-B|`` を、両者の内部の振れ幅(ptp)の大きい方で割る。
* 二値(region): 内部の**食い違い画素 / 和集合の画素**(= 1 − IoU)。一致率(食い違い / 全画素)も記録するが、
  エッジのように疎な出力では一致率は背景で水増しされるので、分類には使わない。
* スカラー: ``|a-b| / max(|a|, |b|)``。ベクトル(match)は成分ごとの最大。
* 輪郭: 点を画素へ丸めて二値化し、二値と同じ 1 − IoU。

入力は ``op_probe`` の構造画像(48 / 64 px)・線分の断片・雑音入り・一様乱数の 5 枚、つまみ
(a, b)は :data:`KNOBS` の 3 点。値域は契約どおりの 0〜1 と、**契約外**の 0〜255(float、そのまま
渡す)の両方。分類は 0〜1 の最悪値で決め、0〜255 は別の欄(実装が値域を仮定しているかの手掛かり)。

## 分類(:func:`classify`)

一致(< 5e-3)/ 近い(< 5e-2)/ 違う / 片方が落ちる / 未検証(optional 依存が無い)/ 比較不能
(入出力の型が違う = 名前が衝突しているだけの別の処理)。

**異常に良い一致**: 差がきっかり 0 の組は、両方が同じ下位関数を呼んでいるだけのことがある。
``impl_differential_table.SHARED_BACKEND`` に「同じ下位関数」を書いた組は表で「独立でない」と明記し、独立な実装どうしの
一致と区別する(``test_impl_differential.py`` が、差 0 なのに理由の無い組を赤にする)。

## 違ってよい理由(``impl_differential_table.REASONS``)

一致しない組ごとに、原因を**中身を読んで**特定した 1 行を持つ。理由の無い食い違いが増えたら
``tests/test_impl_differential.py`` が赤になる。「差はつまみの写し方だけ」という見立ては
``impl_differential_table.ALIGNED`` でつまみを揃えて確かめる(これも門)。

## 使い方

    py -3.11 tools/impl_differential.py --measure   # 実測して docs/impl_differential.json を書く(手で回す)
    py -3.11 tools/impl_differential.py             # JSON から docs/IMPL_DIFFERENTIAL.md を書く(regen_all の段)

実測を手回しに分けるのは、数値が optional 依存の版(OpenCV / kornia / torch)と OS で桁の下の方が
揺れるから。表の生成は commit した JSON だけから決まるので ``regen_all --check`` はバイト一致する。
今の実装が JSON の分類から外れていないかは、テストが毎回**実際に走らせて**確かめる。
"""
from __future__ import annotations

import argparse
import collections
import inspect
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_TOOLS = os.path.join(_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import impl_differential_table as T  # noqa: E402  (手で書く表: 理由・揃えた点・独立でない組・段 2 の判定)

JSON_PATH = os.path.join(_ROOT, "docs", "impl_differential.json")
MD_PATH = os.path.join(_ROOT, "docs", "IMPL_DIFFERENTIAL.md")

#: 実装・由来を表す接頭辞 → 何の実装か。分野の接頭辞(vol_ / mesh_ / piv_ …)は入れない。
IMPL_PREFIXES = {
    "tb": "型付き台帳の関数の橋渡し(backends_typed)",
    "hx": "HALCON 拡張(backends_halcon_ext)",
    "cv": "OpenCV(backends)",
    "sk": "scikit-image(backends)",
    "xcv": "OpenCV 追加(backends_extra)",
    "xcv2": "OpenCV 追加 2(backends_cv2b)",
    "xcv3": "OpenCV 追加 3(backends_r3)",
    "xsk": "scikit-image 追加(backends_extra)",
    "xsk2": "scikit-image 追加 2(backends_ski2)",
    "xsk3": "scikit-image 追加 3(backends_r3)",
    "xkor": "kornia / torch(backends_kornia)",
    "xsitk": "SimpleITK(backends_r3)",
    "xpil": "Pillow(backends_pil)",
    "xmh": "mahotas(backends_r3)",
    "xsp": "SciPy(backends_scipy)",
    "xwt": "PyWavelets(backends_r3)",
    "xg": "XLD 幾何(backends_xldgeom)",
    "r2": "領域 第 2 回(backends_regions2)",
    "r3": "領域 第 3 回(backends_regions3)",
    "f2": "フィルタ 第 2 回(backends_filters2)",
    "it": "画像道具(backends_imgtools)",
    "dc": "分解(backends_decomp)",
    "sg": "分割 第 2 回(backends_segment2)",
    "tf": "変換 第 2 回(backends_transform2)",
    "iv": "逆問題(backends_inverse)",
    "ph": "物理(backends_physics)",
    "sp": "サブピクセル(backends_subpix)",
    "m1": "1-D 計測(backends_measure1d)",
    "tm": "断層(backends_tomo)",
    "dl": "torch 実装(backends_dl)",
    "macro": "自己拡張マクロ(backends_macro)",
    "deform": "変形(backends_deform)",
}

#: 内部とみなす前に捨てる端の幅(画素)。σ = 3 のガウシアンの半径 4σ = 12 には足りないが、
#: 48 px の画像で内部 32×32 を残す妥協。端の扱いの違いはこの帯の中に閉じ込める。
BORDER = 8
#: 比べるつまみ(a, b)。既定(0.5, 0.5)と、その両側。
KNOBS = ((0.5, 0.5), (0.25, 0.75), (0.75, 0.25))
#: 分類のしきい値。
TOL_MATCH = 5e-3
TOL_NEAR = 5e-2

CLASSES = ("一致", "近い", "違う", "片方が落ちる", "未検証", "比較不能")


# --------------------------------------------------------------------------- #
# 組を数える
# --------------------------------------------------------------------------- #
def load_index():
    with open(os.path.join(_ROOT, "docs", "OP_INDEX.json"), encoding="utf-8") as f:
        return json.load(f)["ops"]


def split_prefix(name: str):
    """``(接頭辞, 語幹)``。実装の接頭辞でなければ ``(None, name)``。"""
    head, sep, rest = name.partition("_")
    if sep and head in IMPL_PREFIXES and rest:
        return head, rest
    return None, name


def prefix_census(index=None):
    """接頭辞ごとの op 数と、住んでいるモジュール(:data:`IMPL_PREFIXES` を選んだ根拠)。"""
    index = load_index() if index is None else index
    out = collections.defaultdict(collections.Counter)
    for o in index:
        p, _ = split_prefix(o["name"])
        if p:
            out[p][o.get("module") or o["tier"]] += 1
    return {p: dict(c) for p, c in sorted(out.items())}


def find_groups(index=None):
    """語幹 → 組の op 名(2 個以上)。素の名前も組に入る。"""
    index = load_index() if index is None else index
    names = {o["name"] for o in index}
    groups = collections.defaultdict(set)
    for n in names:
        p, stem = split_prefix(n)
        if p:
            groups[stem].add(n)
    for stem in list(groups):
        if stem in names:
            groups[stem].add(stem)
    return {s: sorted(m) for s, m in sorted(groups.items()) if len(m) >= 2}


def split_groups(groups):
    """``(橋渡しだけの組, 実装どうしの組)``。前者は ``tb_X`` と ``X`` だけからなる組。"""
    tb, impl = {}, {}
    for s, m in groups.items():
        if all(x == s or x.startswith("tb_") for x in m):
            tb[s] = m
        else:
            impl[s] = m
    return tb, impl


def pairs_of(members):
    return [(members[i], members[j]) for i in range(len(members)) for j in range(i + 1, len(members))]


# --------------------------------------------------------------------------- #
# 入力
# --------------------------------------------------------------------------- #
def image_inputs():
    """名前 → 0〜1 の 2-D 画像。乱数は種を固定。"""
    import op_probe                                       # noqa: PLC0415
    rng = np.random.default_rng(20261103)
    s48 = op_probe.structured_image(48)
    noisy = np.clip(s48 + rng.normal(0.0, 0.05, s48.shape), 0.0, 1.0)
    from scipy import ndimage                             # noqa: PLC0415
    smooth = ndimage.gaussian_filter(rng.random((48, 48)), 2.0)
    smooth = (smooth - smooth.min()) / max(1e-12, float(np.ptp(smooth)))
    return {
        "structured48": s48,
        "structured64": op_probe.structured_image(64),
        "fragments48": op_probe.structured_fragments(48),
        "noisy48": noisy,
        "smooth_random48": smooth,
    }


def region_inputs():
    import op_probe                                       # noqa: PLC0415
    from scipy import ndimage                             # noqa: PLC0415
    rng = np.random.default_rng(20261103)
    blobs = (ndimage.gaussian_filter(rng.random((48, 48)), 2.5) > 0.5).astype(np.float64)
    return {"structured_region48": op_probe.structured_region(48), "blobs48": blobs}


def contour_inputs():
    import ops                                            # noqa: PLC0415
    prod = ops._BY_NAME.get("sk_find_contours")
    if prod is None:
        return {}
    out = {}
    for k, v in region_inputs().items():
        out[k + "_contour"] = prod.fn(v, 0.5, 0.5)
    return out


def inputs_for(sort):
    if sort == "image":
        return image_inputs()
    if sort == "region":
        return region_inputs()
    if sort == "contour":
        return contour_inputs()
    return {}


# --------------------------------------------------------------------------- #
# 比べ方
# --------------------------------------------------------------------------- #
def _interior(x, border=BORDER):
    x = np.asarray(x, np.float64)
    if x.ndim >= 2 and min(x.shape[:2]) > 2 * border + 4:
        return x[border:-border, border:-border]
    return x


def _raster(contour):
    shape = tuple(int(s) for s in contour.get("shape", (0, 0)))[:2]
    m = np.zeros(shape, bool)
    for c in contour.get("cs", []):
        c = np.asarray(c, np.float64)
        if c.ndim != 2 or len(c) == 0:
            continue
        r = np.clip(np.round(c[:, 0]).astype(int), 0, shape[0] - 1)
        q = np.clip(np.round(c[:, 1]).astype(int), 0, shape[1] - 1)
        m[r, q] = True
    return m


def compare_outputs(A, B, out_sort):
    """``(差の大きさ, 補助の数値 dict)``。差は分類に使う量(小さいほど同じ)。"""
    if out_sort == "contour":
        if not (isinstance(A, dict) and isinstance(B, dict)):
            return float("inf"), {"why": "contour でない返り"}
        ma, mb = _raster(A), _raster(B)
        union = int((ma | mb).sum())
        diff = int((ma ^ mb).sum())
        return (0.0 if union == 0 else diff / union), {
            "n_contours": [len(A.get("cs", [])), len(B.get("cs", []))]}
    if out_sort in ("feature", "match"):
        a = np.atleast_1d(np.asarray(A, np.float64)).ravel()
        b = np.atleast_1d(np.asarray(B, np.float64)).ravel()
        if a.shape != b.shape:
            return float("inf"), {"why": "形が違う %s / %s" % (a.shape, b.shape)}
        if not (np.isfinite(a).all() and np.isfinite(b).all()):
            return float("inf"), {"why": "非有限"}
        den = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-12)
        rel = np.abs(a - b) / den
        rel[(np.abs(a) < 1e-12) & (np.abs(b) < 1e-12)] = 0.0
        return float(rel.max()), {"values": [float(a[0]), float(b[0])]}
    A = np.asarray(A, np.float64)
    B = np.asarray(B, np.float64)
    if A.shape != B.shape:
        return float("inf"), {"why": "形が違う %s / %s" % (A.shape, B.shape)}
    if not (np.isfinite(A).all() and np.isfinite(B).all()):
        return float("inf"), {"why": "非有限"}
    ia, ib = _interior(A), _interior(B)
    if out_sort == "region":
        ma, mb = ia > 0.5, ib > 0.5
        union = int((ma | mb).sum())
        diff = int((ma ^ mb).sum())
        return (0.0 if union == 0 else diff / union), {
            "agree": 1.0 - diff / max(1, ma.size), "fg": [int(ma.sum()), int(mb.sum())]}
    den = max(float(np.ptp(ia)), float(np.ptp(ib)))
    d = float(np.max(np.abs(ia - ib))) if ia.size else 0.0
    score = (0.0 if d == 0.0 else float("inf")) if den <= 1e-12 else d / den
    extra = {"ptp": [float(np.ptp(ia)), float(np.ptp(ib))], "max_abs": d}
    # 差が「定数倍 + ずれ」だけかを見る(正規化・値域の違いの手掛かり)
    if den > 1e-12 and float(np.ptp(ib)) > 1e-12:
        X = np.stack([ib.ravel(), np.ones(ib.size)], 1)
        coef, *_ = np.linalg.lstsq(X, ia.ravel(), rcond=None)
        res = float(np.max(np.abs(ia.ravel() - X @ coef)))
        extra["affine_resid"] = res / den
        extra["affine_scale"] = float(coef[0])
        extra["affine_offset"] = float(coef[1])
        extra["corr"] = float(np.corrcoef(ia.ravel(), ib.ravel())[0, 1]) if np.ptp(ia) > 1e-12 else 0.0
    return score, extra


def _full_score(A, B):
    """端を含む画像全体の ``max|A−B|`` ÷ 全体の振れ幅(端の扱いの違いを見る欄)。"""
    A = np.asarray(A, np.float64)
    B = np.asarray(B, np.float64)
    if A.shape != B.shape or not (np.isfinite(A).all() and np.isfinite(B).all()):
        return float("inf")
    den = max(float(np.ptp(A)), float(np.ptp(B)))
    d = float(np.max(np.abs(A - B))) if A.size else 0.0
    return (0.0 if d == 0.0 else float("inf")) if den <= 1e-12 else d / den


def classify(score):
    if score is None or not np.isfinite(score):
        return "違う"
    if score < TOL_MATCH:
        return "一致"
    if score < TOL_NEAR:
        return "近い"
    return "違う"


# --------------------------------------------------------------------------- #
# 走らせる
# --------------------------------------------------------------------------- #
def _registry():
    import ops                                            # noqa: PLC0415
    return ops._BY_NAME


def run_op(name, v, a, b):
    """レジストリの op を**fail-closed** で走らせる(劣化した代替値を比べない)。"""
    import fullseye                                       # noqa: PLC0415
    return fullseye.apply(v, name, a, b, on_error="raise", device="cpu", fast=False)


def _same_function(x, y):
    """2 つの op の実体(ガードを剥がした関数)が同じオブジェクトか。"""
    reg = _registry()
    fx, fy = reg[x].fn, reg[y].fn
    while hasattr(fx, "__wrapped__"):
        fx = fx.__wrapped__
    while hasattr(fy, "__wrapped__"):
        fy = fy.__wrapped__
    return fx is fy


def measure_pair(x, y, index_by_name):
    """1 組を測る。返り値は JSON に書く dict。"""
    ox, oy = index_by_name[x], index_by_name[y]
    rec = {"a": x, "b": y,
           "sorts": ["%s->%s" % (ox["in_sort"], ox["out_sort"]), "%s->%s" % (oy["in_sort"], oy["out_sort"])],
           "tiers": [ox["tier"], oy["tier"]]}
    reg = _registry()
    if (ox["tier"] != "registry" or oy["tier"] != "registry"
            or ox["in_sort"] != oy["in_sort"] or ox["out_sort"] != oy["out_sort"]):
        rec["class"] = "比較不能"
        return rec
    missing = [n for n in (x, y) if n not in reg and index_by_name[n]["tier"] == "registry"]
    if missing:
        rec["class"] = "未検証"
        rec["missing"] = missing
        rec["requires"] = sorted(set(sum((index_by_name[n].get("requires") or [] for n in missing), [])))
        return rec
    in_sort, out_sort = ox["in_sort"], ox["out_sort"]
    rec["same_function_object"] = _same_function(x, y)
    worst, worst_at, default = 0.0, None, None
    worst255, worst_full, rows, failures = 0.0, 0.0, [], []
    t0 = time.perf_counter()
    for inp_name, v in inputs_for(in_sort).items():
        scales = (1.0, 255.0) if in_sort == "image" else (1.0,)
        for scale in scales:
            for (a, b) in KNOBS:
                outs = []
                for n in (x, y):
                    try:
                        outs.append(run_op(n, v * scale if isinstance(v, np.ndarray) else v, a, b))
                    except Exception as e:                # noqa: BLE001 - recorded as a failure
                        outs.append(None)
                        failures.append({"op": n, "input": inp_name, "scale": scale, "knobs": [a, b],
                                         "error": "%s: %s" % (type(e).__name__, str(e)[:160])})
                if outs[0] is None or outs[1] is None:
                    continue
                s, extra = compare_outputs(outs[0], outs[1], out_sort)
                if scale == 1.0 and out_sort == "image":
                    worst_full = max(worst_full, _full_score(outs[0], outs[1]))
                row = {"input": inp_name, "scale": scale, "knobs": [a, b], "score": s}
                row.update({k: v_ for k, v_ in extra.items() if k in ("affine_resid", "affine_scale", "corr",
                                                                    "agree", "fg", "values", "why")})
                rows.append(row)
                if scale == 1.0:
                    if s > worst or worst_at is None:
                        worst, worst_at = max(worst, s), row
                    if inp_name == "structured48" and (a, b) == (0.5, 0.5):
                        default = row
                else:
                    worst255 = max(worst255, s)
    rec["seconds"] = round(time.perf_counter() - t0, 2)
    ok_rows = [r for r in rows if r["scale"] == 1.0]
    if any(f["scale"] == 1.0 for f in failures):
        rec["class"] = "片方が落ちる"
    else:
        rec["class"] = classify(worst)
    rec["worst"] = _clean(worst)
    rec["worst_at"] = _clean_row(worst_at)
    rec["default"] = _clean_row(default)
    rec["worst_0_255"] = _clean(worst255) if in_sort == "image" else None
    rec["worst_full"] = _clean(worst_full) if out_sort == "image" else None
    rec["failures"] = failures[:6]
    rec["n_failures"] = len(failures)
    rec["exact_zero"] = bool(ok_rows) and all(r["score"] == 0.0 for r in ok_rows)
    return rec


def _clean(x):
    if x is None:
        return None
    x = float(x)
    if not np.isfinite(x):
        return "inf"
    return float("%.3g" % x)


def _clean_row(r):
    if r is None:
        return None
    out = {}
    for k, v in r.items():
        if isinstance(v, float):
            out[k] = _clean(v)
        elif isinstance(v, list):
            out[k] = [_clean(t) if isinstance(t, float) else t for t in v]
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------- #
# つまみを揃えた点(「差はつまみの写し方だけ」の検算)
# --------------------------------------------------------------------------- #
def aligned_score(x, kx, y, ky, expect):
    """``x(·, *kx)`` と ``y(·, *ky)`` を全ての 0〜1 画像で比べ、期待の量の最悪値を返す。"""
    kind, _limit = expect
    worst = 0.0
    for v in image_inputs().values():
        A = np.asarray(run_op(x, v, *kx), np.float64)
        B = np.asarray(run_op(y, v, *ky), np.float64)
        s, extra = compare_outputs(A, B, "image")
        if kind == "score":
            q = s
        elif kind == "affine":
            q = 0.0 if s == 0.0 else extra.get("affine_resid", float("inf"))
        elif kind == "max_abs":
            q = extra.get("max_abs", float("inf"))
        else:
            raise ValueError("unknown expectation %r" % (kind,))
        worst = max(worst, float(q))
    return worst


def measure_aligned():
    out = []
    for (x, y), points in sorted(T.ALIGNED.items()):
        for kx, ky, expect in points:
            q = aligned_score(x, kx, y, ky, expect)
            out.append({"a": x, "b": y, "knobs_a": [round(t, 6) for t in kx],
                        "knobs_b": [round(t, 6) for t in ky], "expect": [expect[0], expect[1]],
                        "value": _clean(q), "ok": bool(q <= expect[1])})
    return out


# --------------------------------------------------------------------------- #
# tb_ の橋渡しの標本
# --------------------------------------------------------------------------- #
def _bridge_parts(op):
    """橋の ``_run`` のクロージャから ``(kwargs, tunable, ranges, call_time)``。"""
    fn = op.fn
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    cv = inspect.getclosurevars(fn).nonlocals
    return cv.get("kwargs", {}), cv.get("tunable", []), cv.get("ranges", {}), cv.get("call_time")


def _as_array(x):
    """比較用の配列(複素数は複素数のまま —— float64 に落とすと虚部が黙って消える)。"""
    if isinstance(x, float):
        return np.asarray(x, np.float64)
    a = np.asarray(x)
    return a if a.dtype.kind == "c" else a.astype(np.float64)


def check_tb_bridge(stem, index_by_name=None):
    """``tb_<stem>`` のつまみが文書どおりの値に写るかの標本。

    つまみ ``k`` は、範囲表(``OP_KNOB_RANGE``)に無い引数では ``既定 × (0.25 + 1.75k)``、
    ある引数では ``lo + (hi - lo)k``(``backends_typed`` の docstring)。ここでは k = 0 / 3/7 / 1
    (既定の 1/4 倍・1 倍・2 倍)で、**台帳の関数を自分で呼んだ値**と橋の出力を比べる。
    入出力の加工(adapter / call-time 束縛)がある op は、加工を通した関数を呼ぶ必要があり
    独立な検算にならないので「標本外」とする。
    """
    import backends_typed as bt                            # noqa: PLC0415
    import op_probe                                        # noqa: PLC0415
    import typed_catalog                                   # noqa: PLC0415
    reg = _registry()
    name = "tb_" + stem
    rec = {"op": name}
    if index_by_name is not None and stem in index_by_name and index_by_name[stem]["tier"] != "ledger":
        # 索引の名前は一意なので、台帳の stem と同名のレジストリ op があると索引には後者が載る
        rec["registry_name_collision"] = "%s(%s → %s)" % (
            stem, index_by_name[stem]["in_sort"], index_by_name[stem]["out_sort"])
    op = reg.get(name)
    if op is None:
        rec.update(result="未検証", why="レジストリに居ない(既定では入力 sort が新設のものだけ橋を架ける)")
        return rec
    entry = next((e for e in typed_catalog.catalog() if e[0] == stem), None)
    if entry is None:
        rec.update(result="比較不能", why="台帳に同名の関数が無い")
        return rec
    fn = entry[4]
    kwargs, tunable, ranges, call_time = _bridge_parts(op)
    rec["tunable"] = [p for p, _ in tunable]
    if (stem in typed_catalog.ADAPTERS or stem in bt.INPUT_ADAPTERS
            or stem in bt.OUTPUT_ADAPTERS_WITH_INPUT or call_time is not None):
        rec.update(result="標本外", why="入出力の加工つき(adapter / call-time 束縛)")
        return rec
    override = op_probe.OP_PROBE_OVERRIDE.get(name)
    v = (override[0]() if override is not None
         else op_probe.sample_input(op.in_sort, np.random.default_rng(0), structured=True))
    if v is None:
        rec.update(result="未検証", why="入力 %s の代表値が作れない" % op.in_sort)
        return rec
    worst = 0.0
    for k in (0.0, 3.0 / 7.0, 1.0):
        kw = dict(kwargs)
        for pname, default in tunable:
            if pname in ranges:
                lo, hi = ranges[pname]
                val = lo + (hi - lo) * k
                kw[pname] = int(np.floor(val + 0.5)) if isinstance(default, int) else val
            else:
                val = default * {0.0: 0.25, 1.0: 2.0}.get(k, 1.0)
                kw[pname] = max(1, int(round(val))) if isinstance(default, int) else val
        try:
            want = bt._coerce(fn(v, **kw), op.out_sort)
            with _strict():
                got = op.fn(v, k, k)
        except Exception as e:                            # noqa: BLE001
            rec.update(result="片方が落ちる", why="%s: %s" % (type(e).__name__, str(e)[:120]))
            return rec
        w, g = _as_array(want), _as_array(got)
        if w.shape != g.shape:
            rec.update(result="違う", why="形が違う %s / %s" % (w.shape, g.shape))
            return rec
        if w.size == 0:
            continue
        if not (np.isfinite(w).all() and np.isfinite(g).all()):
            import backend_safe                            # noqa: PLC0415
            by_design = name in backend_safe.NONFINITE_BY_DESIGN
            same_nan = bool(np.array_equal(np.isnan(w), np.isnan(g)))
            m = np.isfinite(w) & np.isfinite(g)
            if not (same_nan or by_design) or not m.any():
                rec.update(result="違う", why="非有限の位置が違う")
                return rec
            if by_design:
                # 台帳の関数は NaN を返し、橋は sort の代替値に置き換える(backend_safe.NONFINITE_BY_DESIGN、
                # docstring に書いてある意図した差)。有限の位置だけを比べる。
                rec["note"] = "NaN の位置は橋が代替値に置き換える(NONFINITE_BY_DESIGN)。有限の位置だけ比べた"
            w, g = w[m], g[m]
        d = float(np.max(np.abs(w - g)))
        den = max(float(np.max(np.abs(w))), 1e-12)
        worst = max(worst, d / den)
    rec.update(result="一致" if worst < 1e-9 else "違う", worst=_clean(worst))
    return rec


def _strict():
    import backend_safe                                    # noqa: PLC0415
    return backend_safe.strict_mode(True)


# --------------------------------------------------------------------------- #
# 主処理
# --------------------------------------------------------------------------- #
def environment():
    env = {"numpy": np.__version__}
    for mod in ("scipy", "skimage", "cv2", "torch", "kornia", "SimpleITK", "mahotas"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:                                 # noqa: BLE001
            env[mod] = None
    return env


def measure(verbose=True):
    index = load_index()
    by = {o["name"]: o for o in index}
    groups = find_groups(index)
    tb, impl = split_groups(groups)
    pairs = []
    for stem, members in impl.items():
        for x, y in pairs_of(members):
            t0 = time.perf_counter()
            rec = measure_pair(x, y, by)
            rec["stem"] = stem
            pairs.append(rec)
            if verbose:
                print("%-28s %-26s %-6s worst=%s (%.1fs)" % (x, y, rec["class"], rec.get("worst"),
                                                              time.perf_counter() - t0), flush=True)
    bridges = [check_tb_bridge(stem, by) for stem in tb]
    return {
        "generated_by": "tools/impl_differential.py --measure",
        "environment": environment(),
        "platform": sys.platform,
        "border": BORDER, "knobs": [list(k) for k in KNOBS],
        "tol": {"match": TOL_MATCH, "near": TOL_NEAR},
        "inputs": {"image": sorted(image_inputs()), "region": sorted(region_inputs()),
                   "contour": sorted(contour_inputs())},
        "counts": {"groups": len(groups), "bridge_groups": len(tb), "impl_groups": len(impl),
                   "impl_pairs": len(pairs)},
        "prefix_census": prefix_census(index),
        "impl_groups": impl,
        "bridge_groups": tb,
        "pairs": pairs,
        "aligned": measure_aligned(),
        "bridges": bridges,
    }


# --------------------------------------------------------------------------- #
# 表(docs/IMPL_DIFFERENTIAL.md)
# --------------------------------------------------------------------------- #
def _fmt(x):
    if x is None:
        return "—"
    if x == "inf":
        return "∞"
    x = float(x)
    if x == 0.0:
        return "0"
    return ("%.2g" % x) if (abs(x) < 1e-2 or abs(x) >= 100) else ("%.3f" % x).rstrip("0").rstrip(".")


def pair_key(rec):
    return (rec["a"], rec["b"])


def render_md(data):
    """``docs/impl_differential.json`` と手で書く表から Markdown を組む(決定的)。"""
    pairs = data["pairs"]
    by_stem = collections.OrderedDict()
    for p in pairs:
        by_stem.setdefault(p["stem"], []).append(p)
    aligned = collections.defaultdict(list)
    for r in data.get("aligned", []):
        aligned[(r["a"], r["b"])].append(r)
    cls_count = collections.Counter(p["class"] for p in pairs)
    verdict_count = collections.Counter(T.MERGE_VERDICT.get(s, ("(未判定)", ""))[0] for s in by_stem)
    mergeable = [s for s in by_stem if T.MERGE_VERDICT.get(s, ("",))[0] in T.VERDICTS[:3]]
    c = data["counts"]
    L = []
    L.append("# 同じ処理の別実装の突き合わせ(differential testing)")
    L.append("")
    L.append("> 生成物 —— 手で直さない。生成器 `tools/impl_differential.py`(表は "
             "`docs/impl_differential.json` と `tools/impl_differential_table.py` から)。"
             "測り直しは `py -3.11 tools/impl_differential.py --measure`、門は `tests/test_impl_differential.py`。")
    L.append("")
    L.append("同じ処理が実装ごとに別の名前で並んでいる組(`canny` / `cv_canny` / `sk_canny` / `xkor_canny` など)を、"
             "**同じ入力・同じつまみ (a, b)** で走らせて出力を比べた表。golden(過去の自分)ではなく**実装どうし**を比べる。"
             "命名整理 第 2 段(1 つの名前 + `impl` 引数)でまとめてよいかの前提になる。")
    L.append("")
    L.append("## 数え方")
    L.append("")
    L.append("`docs/OP_INDEX.json` の op 名を `<接頭辞>_<語幹>` に割り、**語幹が同じで接頭辞だけ違う**名前を 1 組にした"
             "(接頭辞の無い素の名前も組に入る)。接頭辞は実装・由来を表すもの %d 種だけ(`vol_` `mesh_` `piv_` のような"
             "分野の接頭辞は数えない。一覧は末尾)。" % len(data["prefix_census"]))
    L.append("")
    L.append("| | 件数 |")
    L.append("|---|---:|")
    L.append("| 語幹が同じ組(全部) | %d |" % c["groups"])
    L.append("| うち `tb_X` と台帳の `X` だけの組(同じ関数の別の入口、つまみの写し方の標本だけ見る) | %d |" % c["bridge_groups"])
    L.append("| うち実装どうしの組 | %d |" % c["impl_groups"])
    L.append("| 実装どうしの対(3 実装の組は 3 対、4 実装は 6 対) | %d |" % c["impl_pairs"])
    L.append("")
    L.append("依頼時の目安は 172 組だったが、その数え方は再現できていない(ここの数え方では %d = %d + %d)。"
             "`tb_` の %d 組のうち 150 組は `naming_phase2/rename_plan.json` の B と同じで、残り 4 組は"
             "台帳の `X` と同名の別の関数がレジストリにある名前の衝突(下の「`tb_` の橋渡しの標本」)。" % (
                 c["groups"], c["bridge_groups"], c["impl_groups"], c["bridge_groups"]))
    L.append("")
    L.append("## 比べ方")
    L.append("")
    L.append("- 入力: 2-D は %s(0〜1)。region は %s、contour はその輪郭(`sk_find_contours`)。" % (
        "・".join("`%s`" % n for n in data["inputs"]["image"]), "・".join("`%s`" % n for n in data["inputs"]["region"])))
    L.append("- つまみ (a, b): %s。" % "・".join("(%g, %g)" % tuple(k) for k in data["knobs"]))
    L.append("- 画像: 端 %d 画素を除いた内部の `max|A−B|` ÷ 両者の内部の振れ幅(ptp)の大きい方。"
             "**端を含む差**も別の欄に出す。" % data["border"])
    L.append("- 二値(region)と輪郭: 内部の食い違い画素 ÷ 和集合(= 1 − IoU)。疎なエッジでは一致率が背景で水増しされるので使わない。")
    L.append("- スカラー・ベクトル: `|a−b| / max(|a|, |b|)`。")
    L.append("- 値域: 契約の 0〜1 で分類し、**契約外の 0〜255**(float のまま渡す)を別の欄に出す(実装が値域を仮定しているかの手掛かり)。")
    L.append("- 分類: 一致 < %g ≤ 近い < %g ≤ 違う。片方が例外で落ちたら「片方が落ちる」、optional 依存が無ければ「未検証」、"
             "入出力の型が違えば「比較不能」。" % (data["tol"]["match"], data["tol"]["near"]))
    L.append("")
    L.append("## 結果の件数")
    L.append("")
    L.append("| 分類 | 対の数 |")
    L.append("|---|---:|")
    for k in CLASSES:
        L.append("| %s | %d |" % (k, cls_count.get(k, 0)))
    L.append("")
    L.append("| 段 2 での扱い(組ごと) | 組の数 |")
    L.append("|---|---:|")
    for k in T.VERDICTS:
        L.append("| %s | %d |" % (k, verdict_count.get(k, 0)))
    L.append("")
    L.append("**1 つの名前 + `impl` 引数にまとめてよい組(前の 3 種)= %d 組**: %s。" % (
        len(mergeable), "、".join("`%s`" % s for s in mergeable)))
    L.append("")
    L.append("## 組ごとの表")
    L.append("")
    L.append("「内部」「端込み」「0〜255」は 0〜1 の全入力・全つまみでの最悪値。「揃えると」はつまみを揃えた点(下の節)の値。")
    L.append("")
    L.append("| 語幹 | 対 | 分類 | 内部 | 端込み | 0〜255 | 揃えると | 原因 | 段 2 |")
    L.append("|---|---|---|---:|---:|---:|---:|---|---|")
    for stem, ps in by_stem.items():
        verdict = T.MERGE_VERDICT.get(stem, ("(未判定)", ""))
        for i, p in enumerate(ps):
            key = pair_key(p)
            kind, text = T.REASONS.get(key, (None, ""))
            if p["class"] == "一致":
                shared = T.SHARED_BACKEND.get(key)
                trivial = T.TRIVIAL_MATCH.get(key)
                cause = (("独立でない: " + shared) if shared else ("独立・自明: " + trivial) if trivial
                         else "独立な実装どうしの一致")
            else:
                cause = ("%s: %s" % (T.KINDS[kind], text)) if kind else "(理由なし)"
            al = aligned.get(key, [])
            al_s = "<br>".join("%s %s" % (_fmt(r["value"]), "✓" if r["ok"] else "✗") for r in al) if al else "—"
            L.append("| %s | `%s` / `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
                ("`%s`" % stem) if i == 0 else "", p["a"], p["b"], p["class"],
                _fmt(p.get("worst")), _fmt(p.get("worst_full")), _fmt(p.get("worst_0_255")), al_s,
                cause.replace("|", "\\|"),
                ("**%s** —— %s" % verdict) if i == 0 else ""))
    L.append("")
    L.append("## つまみを揃えた点")
    L.append("")
    L.append("「差はつまみの写し方だけ」という見立てを、つまみを揃えて確かめた点。期待の量は score(内部の振れ幅比)/ "
             "affine(定数倍とずれを除いた残り)/ max_abs(内部の絶対差)。門(`tests/test_impl_differential.py`)が毎回確かめる。")
    L.append("")
    L.append("| 対 | a 側の (a, b) | b 側の (a, b) | 期待 | 実測 | |")
    L.append("|---|---|---|---|---:|---|")
    for r in data.get("aligned", []):
        L.append("| `%s` / `%s` | (%s) | (%s) | %s ≤ %s | %s | %s |" % (
            r["a"], r["b"], ", ".join("%g" % t for t in r["knobs_a"]), ", ".join("%g" % t for t in r["knobs_b"]),
            r["expect"][0], _fmt(r["expect"][1]), _fmt(r["value"]), "✓" if r["ok"] else "✗"))
    L.append("")
    L.append("## 異常に良い一致の内訳")
    L.append("")
    L.append("差がきっかり 0 の組は、両方が同じ下位関数を呼んでいるだけのことがある。独立な実装どうしの一致と区別する。")
    L.append("")
    for p in pairs:
        if p.get("exact_zero"):
            k = pair_key(p)
            why = (("独立でない —— " + T.SHARED_BACKEND[k]) if k in T.SHARED_BACKEND
                   else ("独立・自明 —— " + T.TRIVIAL_MATCH[k]) if k in T.TRIVIAL_MATCH else "(内訳なし)")
            L.append("- `%s` / `%s`: %s" % (p["a"], p["b"], why))
    indep = [p for p in pairs if p["class"] == "一致" and not p.get("exact_zero")]
    L.append("")
    L.append("独立な実装どうしで一致した対(差が 0 でない = 別々に計算して同じ値になった): %s。" % (
        "、".join("`%s` / `%s`(%s)" % (p["a"], p["b"], _fmt(p["worst"])) for p in indep) or "なし"))
    L.append("")
    L.append("## `tb_` の橋渡しの標本")
    L.append("")
    br = data.get("bridges", [])
    bc = collections.Counter(b["result"] for b in br)
    L.append("`tb_X` は台帳の関数 `X` を `op(v, a, b)` に写した入口。つまみ k = 0 / 3/7 / 1(既定の 1/4・1・2 倍、範囲表の引数は "
             "lo + (hi−lo)k)で、台帳の関数を自分で呼んだ値と比べた。")
    L.append("")
    L.append("| 結果 | 件数 |")
    L.append("|---|---:|")
    for k in ("一致", "違う", "片方が落ちる", "標本外", "未検証", "比較不能"):
        if bc.get(k):
            L.append("| %s | %d |" % (k, bc[k]))
    L.append("")
    out_of = [b["op"] for b in br if b["result"] == "標本外"]
    if out_of:
        L.append("標本外(入出力の加工つきで独立な検算にならない): %s。" % "、".join("`%s`" % n for n in out_of))
        L.append("")
    bad = [b for b in br if b["result"] not in ("一致", "標本外")]
    for b in bad:
        L.append("- `%s`: %s —— %s" % (b["op"], b["result"], b.get("why", "")))
    coll = [b for b in br if b.get("registry_name_collision")]
    if coll:
        L.append("")
        L.append("**名前の衝突**(台帳の `X` と同名の、**別の関数**のレジストリ op がある。`tb_X` は台帳の方と同じ関数): %s。"
                 "段 1 の C2(`signal_*` へ)と同じ組。" % "、".join(
                     "`%s` ↔ レジストリ `%s`" % (b["op"], b["registry_name_collision"]) for b in coll))
    L.append("")
    L.append("## 接頭辞(実装・由来を表すもの)")
    L.append("")
    L.append("| 接頭辞 | 何の実装か | op 数 | 住んでいるモジュール |")
    L.append("|---|---|---:|---|")
    for p, mods in data["prefix_census"].items():
        L.append("| `%s_` | %s | %d | %s |" % (p, IMPL_PREFIXES.get(p, ""), sum(mods.values()),
                                              "、".join("`%s` %d" % (m, n) for m, n in sorted(mods.items()))))
    L.append("")
    L.append("## 測った環境")
    L.append("")
    env = data.get("environment", {})
    L.append("%s。値は optional 依存の版と OS で下の桁が揺れるので、測り直しは手で回す(この表の生成は JSON だけから決まる)。" % (
        "、".join("%s %s" % (k, v) for k, v in sorted(env.items()) if v) + "(" + data.get("platform", "") + ")"))
    L.append("")
    return "\n".join(L)


def load_json(path=JSON_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--measure", action="store_true", help="実測して docs/impl_differential.json を書く(手で回す)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
    if args.measure:
        data = measure(verbose=not args.quiet)
        with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        print("wrote", os.path.relpath(JSON_PATH, _ROOT))
    text = render_md(load_json())
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if not args.quiet:
        print("wrote", os.path.relpath(MD_PATH, _ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
