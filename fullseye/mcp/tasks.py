# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""真値付きの課題を作り(``fullseye_make_task``)、組んだ処理を真値で採点する(``fullseye_score_pipeline``)。

LLM が組んだ処理は「型の門 → 実行」までは通せた。だが、もっともらしく間違った処理
(大域の二値化で照明むらを拾う、位相を展開し忘れる、しきい値の高さで端を測る)は型の門を通る。
この部品は、シミュレーションで真値の決まる課題を作り、組んだ処理の**出力**を真値と比べる。

設計の約束:

- **真値は呼び手に返さない。** 真値は :class:`TaskStore` に task_id で持ち、返り値には
  入力画像のハンドル・課題文・出力の型と単位・許容範囲だけを載せる。採点の返り値は
  指標ごとの誤差の**大きさ**(符号なし)と許容範囲と合否(``feedback`` で粗くできる)。
  誤差の符号は返さない(符号つきの誤差と自分の出力を足せば真値そのものになるため)。
- **真値の鍵は (kind, seed)。** 難度のつまみ(params)は入力を変えるが真値を変えない
  (どの族も真値を先に引き、つまみはその後で使う)。採点の回数はこの鍵ごとに数え、
  課題を作り直しても・追い出されても・期限が切れても戻さない(2026-11-10、独立レビュー F2)。
  雑音 0 の「双子」の課題は同じ鍵なので、回数を共有する。
- **2 つのモード。** 公開モード(既定)は ``SeedSequence([族の番号, seed])`` から乱数を作り、
  誰でも同じ課題を作り直せる(再現できる)。実験モードは環境変数 ``FULLSEYE_TASK_SECRET`` の
  秘密値を乱数の種と task_id に混ぜ、公開の生成器から真値を作り直せなくする(F4)。秘密値は
  記録にも返り値にも出さない。実験モードの既定の ``feedback`` は ``pass_fail``(F3)。
- **許容範囲は事前登録。** 値と根拠は :mod:`fullseye.mcp.task_tolerances` にあり、
  その表だけを先に commit してから実装・結果を足す(F8)。
- **fail-closed。** 知らない族・範囲外のつまみ・知らない task_id・期限切れ・試行の使い切り・
  型の門の不合格・実行時の例外・NaN / 空 / 定数の出力は、どれも合格を返さず、
  理由の符号(``reason``)と説明を返す。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .task_tolerances import RATIONALE, SCORING_VERSION, TOLERANCES

#: 課題の寿命(秒)。過ぎた task_id は ``task_expired`` で断る。
TASK_TTL_S = 3600.0
#: 1 つの真値(kind, seed)を採点できる回数。使い切ったら ``attempts_exhausted`` で断る。
TASK_MAX_ATTEMPTS = 32
#: 同時に持つ課題の数(古い順に捨てる。捨てた task_id は ``unknown_task``。採点の回数は捨てない)。
TASK_MAX_ITEMS = 64
#: 1 つの保管庫(= 1 セッション)で作れる真値の鍵の数。超えたら ``too_many_tasks`` で断る
#: (回数の表は追い出さないので、ここで大きさを抑える)。
TASK_MAX_TRUTH_KEYS = 4096
#: seed の上限(JSON の整数として安全な範囲に収める)。
MAX_SEED = 2 ** 31 - 1
TASK_PREFIX = "fullseye://task/"
#: 採点の返し方。詳しい順。
FEEDBACK_LEVELS = ("detailed", "coarse", "pass_fail")
#: ``coarse`` の段階(許容の何倍か)。
COARSE_BANDS = ((1.0, "<=1x"), (2.0, "<=2x"), (5.0, "<=5x"))
SECRET_ENV = "FULLSEYE_TASK_SECRET"
FEEDBACK_ENV = "FULLSEYE_TASK_FEEDBACK"
#: 実験モードの監査記録(JSON Lines)の場所。実験者だけが読める所に置く。採点の回数の表は
#: ``<AUDIT_PATH>.attempts.json`` に残す(セッションをまたいで数える)。
AUDIT_ENV = "FULLSEYE_TASK_AUDIT_PATH"
#: 秘密値の最低の長さ(2026-11-10、独立レビュー第 2 巡 N6)。task_id から辞書攻撃されない長さ。
MIN_SECRET_LEN = 32
#: 採点の回数の表のファイル lock を待つ上限(秒)。取れなければ fail-closed。
ATTEMPT_LOCK_TIMEOUT_S = 10.0


class TaskError(ValueError):
    """課題・採点の拒否。``reason`` は機械が読む符号。"""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


# --------------------------------------------------------------------------- #
# 族の定義                                                                       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Param:
    """族ごとの難度つまみ(真値を決めない量だけ。真値は seed から引く)。"""

    default: float
    lo: float
    hi: float
    doc: str


@dataclass(frozen=True)
class Family:
    kind: str
    index: int                       # 乱数の流れを族ごとに分ける番号(変えない)
    field: str                       # 分野
    shape: tuple[int, ...]           # 入力配列の形
    input_sort: str
    output_sorts: tuple[str, ...]    # 採点できる出力の型
    output_form: str                 # 出力の形の説明(LLM 向け)
    unit: str
    params: dict[str, Param]
    statement: str                   # 課題文(日本語)
    statement_en: str
    metrics: tuple[tuple[str, str], ...]   # (指標名, 単位)
    rationale: str                   # 許容範囲の根拠(task_tolerances.RATIONALE)
    generate: Callable[[np.random.Generator, dict[str, float]], tuple[np.ndarray, dict[str, Any]]]
    score: Callable[[Any, dict[str, Any], dict[str, float]], list[dict[str, Any]]]
    tolerance: Callable[[dict[str, float]], dict[str, float]]
    #: 分かっている弱さ(正誤の分け方など)。None なら無し。課題の返り値に注記として載せる。
    known_weakness: str | None = None


def _metric(name: str, error: float, tolerance: float, unit: str) -> dict[str, Any]:
    """指標 1 行。合否は丸める前の値で決め、表示用の値は 4 桁に丸める。符号は落とす。"""
    error = float(abs(error))
    tolerance = float(tolerance)
    passed = bool(math.isfinite(error) and error <= tolerance)
    ratio = error / tolerance if tolerance > 0 else (0.0 if error == 0 else math.inf)
    return {"name": name, "unit": unit, "error": _round(error), "tolerance": _round(tolerance),
            "ratio": _round(ratio) if math.isfinite(ratio) else None, "passed": passed}


def _round(x: float, digits: int = 4) -> float:
    if x == 0 or not math.isfinite(x):
        return float(x)
    return float(round(x, digits - 1 - int(math.floor(math.log10(abs(x))))))


def _table(kind: str) -> dict[str, float]:
    """事前登録の表(fringe_phase 以外は定数)。"""
    return {k: float(v) for k, v in TOLERANCES[kind].items()}


# ---- 1. 二値化と計数(照明むらのある板の上の粒) --------------------------------
def _gen_blob_count(rng: np.random.Generator, p: dict[str, float]):
    h, w = 128, 128
    n = int(rng.integers(11, 31))
    yy, xx = np.mgrid[:h, :w].astype(np.float64)
    background = 0.15 + p["illumination"] * (xx / (w - 1))
    blobs = np.zeros((h, w), dtype=np.float64)
    placed: list[tuple[float, float, float]] = []
    tries = 0
    while len(placed) < n:
        tries += 1
        if tries > 20000:                                   # 置けないのは生成器の誤り。黙って減らさない
            raise RuntimeError("blob_count: could not place %d blobs" % n)
        r = float(rng.uniform(3.0, 6.0))
        cy, cx = float(rng.uniform(r + 3, h - r - 4)), float(rng.uniform(r + 3, w - r - 4))
        if all(math.hypot(cy - y, cx - x) > r + q + 4.0 for y, x, q in placed):
            placed.append((cy, cx, r))
    for cy, cx, r in placed:
        d = np.hypot(yy - cy, xx - cx)
        blobs = np.maximum(blobs, np.clip(r + 0.5 - d, 0.0, 1.0))     # 縁 1 px の反エイリアス
    image = background + 0.35 * blobs + rng.normal(0.0, p["noise"], (h, w))
    return np.clip(image, 0.0, 1.0), {"count": n}


def _score_blob_count(value, truth, p):
    n = _scalar(value)
    return [_metric("count_error", n - truth["count"], _tol_blob_count(p)["count_error"], "objects")]


def _tol_blob_count(p):
    return _table("blob_count")


# ---- 2. サブピクセルの寸法(水平な帯の上端と下端) ------------------------------
def _gen_edge_subpixel(rng: np.random.Generator, p: dict[str, float]):
    from math import erf
    h, w = 96, 64
    y0 = float(rng.uniform(28.0, 40.0))
    y1 = y0 + float(rng.uniform(18.0, 34.0))
    sigma = math.sqrt(p["blur"] ** 2 + 1.0 / 12.0)          # 光学ぼけ + 画素の積分
    rows = np.arange(h, dtype=np.float64)
    phi = np.vectorize(lambda t: 0.5 * (1.0 + erf(t / math.sqrt(2.0))))
    profile = phi((rows - y0) / sigma) - phi((rows - y1) / sigma)
    image = 0.2 + 0.6 * np.repeat(profile[:, None], w, axis=1)
    image = image + rng.normal(0.0, p["noise"], (h, w))
    return np.clip(image, 0.0, 1.0), {"top": y0, "bottom": y1}


def _score_edge_subpixel(value, truth, p):
    pts = _points(value)
    rows = pts[:, 0]
    tol = _tol_edge_subpixel(p)
    return [_metric("top_edge_error", float(rows.min()) - truth["top"], tol["top_edge_error"], "px"),
            _metric("bottom_edge_error", float(rows.max()) - truth["bottom"], tol["bottom_edge_error"], "px")]


def _tol_edge_subpixel(p):
    return _table("edge_subpixel")


# ---- 3. キズの検出(加工目のある面の暗い打痕 1 つ) ------------------------------
def _gen_defect_inspect(rng: np.random.Generator, p: dict[str, float]):
    h, w = 128, 128
    yy, xx = np.mgrid[:h, :w].astype(np.float64)
    a, b = float(rng.uniform(5.0, 9.0)), float(rng.uniform(3.5, 6.0))
    theta = float(rng.uniform(0.0, math.pi))
    cy, cx = float(rng.uniform(24.0, h - 24.0)), float(rng.uniform(24.0, w - 24.0))
    ph1, ph2 = float(rng.uniform(0, 2 * math.pi)), float(rng.uniform(0, 2 * math.pi))
    texture = p["texture"] * (np.sin(2 * math.pi * xx / 7.0 + ph1) + 0.5 * np.sin(2 * math.pi * yy / 11.0 + ph2))
    background = 0.55 + 0.10 * (yy / (h - 1)) + texture
    u = (xx - cx) * math.cos(theta) + (yy - cy) * math.sin(theta)
    v = -(xx - cx) * math.sin(theta) + (yy - cy) * math.cos(theta)
    rho = np.sqrt((u / a) ** 2 + (v / b) ** 2)               # 1 が楕円の縁
    edge_px = (rho - 1.0) * min(a, b)                        # 縁からの符号つき距離(近似、px)
    mask = np.clip(0.5 - edge_px, 0.0, 1.0)
    image = background - p["contrast"] * mask + rng.normal(0.0, p["noise"], (h, w))
    # 真値のマスク = 画素の中心が楕円の内側(反エイリアスの重み 0.5 以上)。
    return np.clip(image, 0.0, 1.0), {"cy": cy, "cx": cx, "area": math.pi * a * b,
                                      "mask": np.asarray(edge_px <= 0.0, dtype=bool)}


def _score_defect_inspect(value, truth, p):
    mask = _region(value)
    area = float(mask.sum())
    ys, xs = np.nonzero(mask)
    cy, cx = float(ys.mean()), float(xs.mean())
    gt = truth["mask"]
    iou = float(np.logical_and(mask, gt).sum()) / float(np.logical_or(mask, gt).sum())
    tol = _tol_defect_inspect(p)
    return [_metric("centroid_error", math.hypot(cy - truth["cy"], cx - truth["cx"]),
                    tol["centroid_error"], "px"),
            _metric("area_rel_error", (area - truth["area"]) / truth["area"],
                    tol["area_rel_error"], "ratio"),
            _metric("mask_iou_deficit", 1.0 - iou, tol["mask_iou_deficit"], "1-IoU")]


def _tol_defect_inspect(p):
    return _table("defect_inspect")


# ---- 4. 3-D 計測(4 歩の位相シフト縞から連続位相) --------------------------------
#: 視野の横幅あたりの縞の本数。真値(位相の傾き)を決めるので難度のつまみにしない
#: (2026-11-10: つまみだったとき、本数を変えた課題は同じ seed でも真値が違い、
#: 「真値の鍵は (kind, seed)」が成り立たなかった。テストが見つけた)。
_FRINGES = 4.0


def _gen_fringe_phase(rng: np.random.Generator, p: dict[str, float]):
    h, w = 64, 96
    yy, xx = np.mgrid[:h, :w].astype(np.float64)
    bump = float(rng.uniform(1.0, 3.0))
    r0, c0 = float(rng.uniform(20.0, h - 20.0)), float(rng.uniform(25.0, w - 25.0))
    s = float(rng.uniform(8.0, 16.0))
    phase = (2 * math.pi * _FRINGES * xx / w
             + bump * np.exp(-((yy - r0) ** 2 + (xx - c0) ** 2) / (2 * s * s)))
    phase = phase - float(np.mean(phase))                  # 位相の原点は任意。中央を 0 付近へ
    frames = np.stack([0.5 + p["modulation"] * np.cos(phase - 2 * math.pi * k / 4) for k in range(4)])
    frames = frames + rng.normal(0.0, p["noise"], frames.shape)
    return np.clip(frames, 0.0, 1.0), {"phase": phase}


def _score_fringe_phase(value, truth, p):
    est = _image(value, truth["phase"].shape)
    d = est - truth["phase"]
    m = round(float(np.median(d)) / (2 * math.pi))          # 許すのは 2πm のずれだけ
    rms = float(np.sqrt(np.mean((d - 2 * math.pi * m) ** 2)))
    return [_metric("phase_rms_error", rms, _tol_fringe_phase(p)["phase_rms_error"], "rad")]


def _tol_fringe_phase(p):
    rule = TOLERANCES["fringe_phase"]["phase_rms_error"]
    sigma = p["noise"] / (p["modulation"] * math.sqrt(4 / 2.0))   # 4 歩の位相雑音の理論値
    return {"phase_rms_error": max(float(rule["floor"]), float(rule["sigma_multiple"]) * sigma)}


#: 比較実験(LLM+Fullseye / LLM だけ / 人)に使える族。正誤の分け方が弱いと分かっている族は外す
#: (2026-11-10: defect_inspect を外した。known_weakness を参照)。tests が一覧を固定する。
COMPARISON_FAMILIES: frozenset[str] = frozenset({"blob_count", "edge_subpixel", "fringe_phase"})

FAMILIES: dict[str, Family] = {f.kind: f for f in (
    Family(
        kind="blob_count", index=1, field="segmentation / counting",
        shape=(128, 128), input_sort="image", output_sorts=("feature",),
        output_form="スカラー 1 つ(粒の数)", unit="objects",
        params={"noise": Param(0.02, 0.0, 0.05, "画素雑音の標準偏差(値域 0..1)"),
                "illumination": Param(0.35, 0.0, 0.6, "左から右への照明むらの振幅")},
        statement=("照明むらのある板の上に、明るい丸い粒が離れて並んでいる。粒の数を数えよ。"
                   "出力は最終段がスカラー 1 つ(feature)になる処理。"),
        statement_en=("Bright round particles lie apart on a plate under uneven illumination. "
                      "Count them. The last stage must output one scalar (feature)."),
        metrics=(("count_error", "objects"),),
        rationale=RATIONALE["blob_count"],
        generate=_gen_blob_count, score=_score_blob_count, tolerance=_tol_blob_count),
    Family(
        kind="edge_subpixel", index=2, field="dimensional metrology (sub-pixel)",
        shape=(96, 64), input_sort="image", output_sorts=("contour", "points", "matrix"),
        output_form="端の点列 [row, col](contour / points / matrix)。最小の row を上端、最大の row を下端とみなす",
        unit="px",
        params={"noise": Param(0.01, 0.0, 0.03, "画素雑音の標準偏差"),
                "blur": Param(1.2, 0.6, 3.0, "光学ぼけの標準偏差(px)")},
        statement=("水平な明るい帯が 1 本ある(左右に一様)。帯の上端と下端の行座標を"
                   "サブピクセルで測れ(行座標は画素中心が整数)。出力は端の点列 [row, col]"
                   "(contour / points / matrix)で、最小の row を上端、最大の row を下端とみなす。"),
        statement_en=("One horizontal bright band (uniform along columns). Measure the row "
                      "coordinates of its top and bottom edges to sub-pixel precision (pixel "
                      "centres are integers). Output edge points [row, col] as contour / points / "
                      "matrix; the smallest row is the top edge, the largest the bottom edge."),
        metrics=(("top_edge_error", "px"), ("bottom_edge_error", "px")),
        rationale=RATIONALE["edge_subpixel"],
        generate=_gen_edge_subpixel, score=_score_edge_subpixel, tolerance=_tol_edge_subpixel),
    Family(
        kind="defect_inspect", index=3, field="surface inspection",
        shape=(128, 128), input_sort="image", output_sorts=("region",),
        output_form="領域(region、入力と同じ形の真偽配列)", unit="px",
        params={"noise": Param(0.015, 0.0, 0.05, "画素雑音の標準偏差"),
                "texture": Param(0.06, 0.0, 0.12, "加工目(縞)の振幅"),
                "contrast": Param(0.18, 0.08, 0.4, "打痕の暗さ")},
        statement=("加工目と緩い照明むらのある金属面に、暗い打痕が 1 つある。打痕の領域を返せ。"
                   "出力は最終段が region(入力と同じ形)。重心の位置・面積・真値のマスクとの IoU で採点する。"),
        statement_en=("A machined metal surface with tool marks and mild shading has one dark "
                      "dent. Return the dent as a region (same shape as the input). Scored on "
                      "centroid position, area and IoU with the true mask."),
        metrics=(("centroid_error", "px"), ("area_rel_error", "ratio"), ("mask_iou_deficit", "1-IoU")),
        rationale=RATIONALE["defect_inspect"],
        generate=_gen_defect_inspect, score=_score_defect_inspect, tolerance=_tol_defect_inspect,
        known_weakness=("正誤の分け方が弱い: 加工目を処理しない処理(反転 → 最大エントロピーの二値化 → "
                        "最大の領域)が seed 0〜49 で 20/50、seed 50〜249 で 78/200 合格する"
                        "(IoU を足しても変わらなかった)。比較実験には使わない。作り直しは v2 で、"
                        "新しい seed の範囲で事前登録してから測る。")),
    Family(
        kind="fringe_phase", index=4, field="3-D measurement (phase-shifting profilometry)",
        shape=(4, 64, 96), input_sort="seq<image>", output_sorts=("image", "depth"),
        output_form="連続(展開済み)位相の画像 (64, 96)、rad。大域の 2πm のずれは許す", unit="rad",
        params={"noise": Param(0.005, 0.0, 0.02, "画素雑音の標準偏差"),
                "modulation": Param(0.3, 0.15, 0.45, "縞の振幅 B(I = 0.5 + B cos(φ - δ))")},
        statement=("4 歩の位相シフト縞 I_k = A + B cos(φ - 2πk/4)(k = 0..3)が 4 枚ある。"
                   "物体の凹凸を含む連続位相 φ(展開済み、rad)の画像を返せ。"
                   "大域の 2πm のずれは許す。出力は最終段が image か depth。"),
        statement_en=("Four phase-shifted fringe images I_k = A + B cos(phi - 2 pi k / 4), "
                      "k = 0..3. Return the continuous (unwrapped) phase phi in rad as an image "
                      "or depth map; a global 2 pi m offset is allowed."),
        metrics=(("phase_rms_error", "rad"),),
        rationale=RATIONALE["fringe_phase"],
        generate=_gen_fringe_phase, score=_score_fringe_phase, tolerance=_tol_fringe_phase),
)}


# --------------------------------------------------------------------------- #
# 出力の取り出し(形が違えば TaskError。推測で合わせない)                           #
# --------------------------------------------------------------------------- #
def _scalar(value) -> float:
    arr = np.asarray(value, dtype=np.float64) if not isinstance(value, dict) else None
    if arr is None or arr.size != 1:
        raise TaskError("output_shape_mismatch", "スカラー 1 つが要る(%s)" % _describe(value))
    x = float(arr.reshape(-1)[0])
    if not math.isfinite(x):
        raise TaskError("invalid_output", "出力が有限でない(%r)" % x)
    return x


def _points(value) -> np.ndarray:
    if isinstance(value, dict) and isinstance(value.get("cs"), (list, tuple)):
        parts = [np.asarray(c, dtype=np.float64).reshape(-1, 2) for c in value["cs"] if np.size(c)]
        pts = np.concatenate(parts) if parts else np.zeros((0, 2))
    else:
        try:
            pts = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError):
            raise TaskError("output_shape_mismatch", "点列 [row, col] が要る(%s)" % _describe(value)) from None
        if pts.ndim != 2 or pts.shape[1] < 2:
            raise TaskError("output_shape_mismatch", "点列は (n, 2) が要る(%s)" % _describe(value))
        pts = pts[:, :2]
    if len(pts) == 0:
        raise TaskError("empty_output", "点が 1 つも無い")
    if len(pts) < 2:
        raise TaskError("output_shape_mismatch", "上端と下端の 2 点以上が要る(%d 点)" % len(pts))
    if not np.isfinite(pts).all():
        raise TaskError("invalid_output", "点列に NaN / Inf がある")
    return pts


def _region(value) -> np.ndarray:
    arr = np.asarray(value) if isinstance(value, np.ndarray) else None
    if arr is None or arr.ndim != 2 or arr.shape != FAMILIES["defect_inspect"].shape:
        raise TaskError("output_shape_mismatch", "入力と同じ形 %s の region が要る(%s)"
                        % (FAMILIES["defect_inspect"].shape, _describe(value)))
    if arr.dtype.kind == "f" and not np.isfinite(arr).all():
        raise TaskError("invalid_output", "region に NaN / Inf がある")
    mask = arr.astype(bool)
    if not mask.any():
        raise TaskError("empty_output", "region が空(1 画素も無い)")
    if mask.all():
        raise TaskError("constant_output", "region が全面(定数)")
    return mask


def _image(value, shape) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64) if isinstance(value, np.ndarray) else None
    if arr is None or arr.shape != tuple(shape):
        raise TaskError("output_shape_mismatch", "形 %s の画像が要る(%s)" % (tuple(shape), _describe(value)))
    if not np.isfinite(arr).all():
        raise TaskError("invalid_output", "画像に NaN / Inf がある(%d 画素)" % int((~np.isfinite(arr)).sum()))
    if float(np.ptp(arr)) == 0.0:
        raise TaskError("constant_output", "画像が定数")
    return arr


def _describe(value) -> str:
    if isinstance(value, np.ndarray):
        return "ndarray shape=%s dtype=%s" % (list(value.shape), value.dtype)
    if isinstance(value, dict):
        return "dict keys=%s" % sorted(map(str, value))[:6]
    return type(value).__name__


# --------------------------------------------------------------------------- #
# 課題の生成と保管                                                               #
# --------------------------------------------------------------------------- #
def resolve_params(kind: str, params: dict | None) -> dict[str, float]:
    """つまみを既定値で埋め、範囲と型を検査する(知らない名前・範囲外は TaskError)。"""
    fam = FAMILIES.get(kind)
    if fam is None:
        raise TaskError("unknown_kind", "知らない族: %r(あるのは %s)" % (kind, sorted(FAMILIES)))
    params = dict(params or {})
    unknown = sorted(set(params) - set(fam.params))
    if unknown:
        raise TaskError("unknown_param", "%s に無いつまみ: %s(あるのは %s)" % (kind, unknown, sorted(fam.params)))
    out: dict[str, float] = {}
    for name, spec in fam.params.items():
        value = params.get(name, spec.default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise TaskError("bad_param", "%s.%s は有限の数: %r" % (kind, name, value))
        value = float(value)
        if not spec.lo <= value <= spec.hi:
            raise TaskError("bad_param", "%s.%s=%g は範囲 [%g, %g] の外" % (kind, name, value, spec.lo, spec.hi))
        out[name] = value
    return out


def _secret_digest(secret: str | None) -> bytes:
    """秘密値の要約(秘密値そのものはどこにも残さない)。空・None は公開モード。"""
    if not secret:
        return b""
    return hashlib.sha256(b"fullseye-task-secret|" + secret.encode("utf-8")).digest()


def task_id_of(kind: str, seed: int, params: dict[str, float], secret: str | None = None) -> str:
    key = json.dumps({"kind": kind, "seed": int(seed), "params": params, "v": SCORING_VERSION},
                     sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256(key.encode("utf-8"))
    h.update(_secret_digest(secret))
    return TASK_PREFIX + h.hexdigest()[:16]


def generate(kind: str, seed: int, params: dict | None = None, *,
             secret: str | None = None) -> tuple[np.ndarray, dict[str, Any], dict[str, float]]:
    """``(入力配列, 真値, 解決済みのつまみ)``。同じ引数(と同じ秘密値)なら同じバイト列。"""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise TaskError("bad_seed", "seed は 0..%d の整数: %r" % (MAX_SEED, seed))
    resolved = resolve_params(kind, params)
    fam = FAMILIES[kind]
    entropy = [fam.index, int(seed)]
    digest = _secret_digest(secret)
    if digest:                                             # 実験モード: 秘密値の要約を種に混ぜる
        entropy += [int.from_bytes(digest[i:i + 4], "little") for i in range(0, 32, 4)]
    rng = np.random.default_rng(np.random.SeedSequence(entropy))
    arr, truth = fam.generate(rng, resolved)
    arr = np.ascontiguousarray(arr, dtype=np.float64)
    if arr.shape != fam.shape or not np.isfinite(arr).all():
        raise RuntimeError("generator %s broke its contract: shape=%s" % (kind, arr.shape))
    return arr, truth, resolved


@dataclass
class TaskRecord:
    task_id: str
    kind: str
    seed: int
    params: dict[str, float]
    input: np.ndarray
    truth: dict[str, Any]
    created: float
    attempts: int = 0          # 表示用の写し。正本は TaskStore の (kind, seed) ごとの表


class TaskStore:
    """真値を task_id で持つ。MCP の返り値には決して載せない(このクラスに出口は無い)。

    採点の回数は (kind, seed) ごとの表に持ち、課題の追い出し・期限切れ・作り直しでは戻さない。
    ``secret`` が None なら環境変数 ``FULLSEYE_TASK_SECRET`` を読む(空 = 公開モード)。
    ``feedback_cap`` は採点で返してよい最も詳しい段階(既定: 公開 = detailed、実験 = pass_fail。
    環境変数 ``FULLSEYE_TASK_FEEDBACK`` で上書き)。
    実験モードは秘密値が ``MIN_SECRET_LEN`` 文字以上で、``audit_path``(``FULLSEYE_TASK_AUDIT_PATH``)が
    あるときだけ作れる(無ければ ValueError = fail-closed)。回数は ``<audit_path>.attempts.json`` にも残し、
    セッションをまたいで数える。
    """

    def __init__(self, *, ttl_s: float = TASK_TTL_S, max_attempts: int = TASK_MAX_ATTEMPTS,
                 max_items: int = TASK_MAX_ITEMS, max_truth_keys: int = TASK_MAX_TRUTH_KEYS,
                 clock: Callable[[], float] = time.monotonic, secret: str | None = None,
                 feedback_cap: str | None = None, audit_path: str | None = None):
        self.ttl_s = float(ttl_s)
        self.max_attempts = int(max_attempts)
        self.max_items = int(max_items)
        self.max_truth_keys = int(max_truth_keys)
        self.clock = clock
        self._secret = os.environ.get(SECRET_ENV, "") if secret is None else secret
        self.mode = "secret" if self._secret else "public"
        if self._secret and len(self._secret) < MIN_SECRET_LEN:
            # 秘密値そのものは文に入れない
            raise ValueError("%s が短すぎる(%d 文字以上が要る)" % (SECRET_ENV, MIN_SECRET_LEN))
        path = os.environ.get(AUDIT_ENV, "") if audit_path is None else audit_path
        self.audit_path = os.path.abspath(path) if path else None
        if self.mode == "secret" and not self.audit_path:
            raise ValueError("実験モード(%s)には %s(実験者だけが読む監査記録の場所)が要る"
                             % (SECRET_ENV, AUDIT_ENV))
        #: 実験モードでは採点の回数をファイルに残す(セッションをまたいで数える。独立レビュー第 2 巡 N4)
        self.attempts_path = (self.audit_path + ".attempts.json") if self.mode == "secret" else None
        cap = feedback_cap if feedback_cap is not None else os.environ.get(
            FEEDBACK_ENV, "pass_fail" if self._secret else "detailed")
        if cap not in FEEDBACK_LEVELS:
            raise ValueError("%s=%r は %s のどれか" % (FEEDBACK_ENV, cap, FEEDBACK_LEVELS))
        self.feedback_cap = cap
        self._items: OrderedDict[str, TaskRecord] = OrderedDict()
        self._attempts: dict[tuple[str, int], int] = {}        # 追い出さない(正本)
        self._lock = threading.RLock()

    @property
    def scoring_version(self) -> str:
        return SCORING_VERSION + ("+secret" if self.mode == "secret" else "")

    # ---- 採点の回数をファイルに残す(実験モード) ------------------------------------
    def _file_key(self, key: tuple[str, int]) -> str:
        return "%s|%s|%d" % (_secret_digest(self._secret).hex()[:16], key[0], key[1])

    def _file_lock(self):
        """``<attempts>.lock`` に OS のファイル lock(Windows は ``msvcrt.locking``、他は ``fcntl.flock``)を取る。

        ★2026-11-10(独立レビュー第 4 巡): 以前は O_EXCL で作る lock ファイルで、30 秒より古いものを消していた。
        古い lock を 2 つのプロセスが続けて消すと、後の方が先の方の新しい lock を消してしまい、回数が 1 つ
        減った。OS の lock は持ち主のプロセスが落ちれば OS が外すので、古い lock を消す判断そのものが要らない。
        取れなければ ``ATTEMPT_LOCK_TIMEOUT_S`` 秒待って ``attempt_store_unavailable``(fail-closed)。
        返すのは開いたファイル(:meth:`_file_unlock` に渡す)。文にファイルの場所は入れない。
        """
        lock = self.attempts_path + ".lock"
        try:
            os.makedirs(os.path.dirname(self.attempts_path) or ".", exist_ok=True)
            fh = open(lock, "a+b")
        except OSError as exc:
            raise TaskError("attempt_store_unavailable",
                            "採点の回数の表の lock を開けない(%s)" % type(exc).__name__) from None
        deadline = time.monotonic() + ATTEMPT_LOCK_TIMEOUT_S
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fh
            except OSError:
                if time.monotonic() > deadline:
                    fh.close()
                    raise TaskError("attempt_store_unavailable",
                                    "採点の回数の表の lock が取れない(%g 秒)" % ATTEMPT_LOCK_TIMEOUT_S) from None
                time.sleep(0.01)

    @staticmethod
    def _file_unlock(fh) -> None:
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            fh.close()

    def _read_file(self) -> dict[str, int]:
        try:
            with open(self.attempts_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:                  # 文に場所を入れない(OSError の文はパスを含む)
            raise TaskError("attempt_store_unavailable",
                            "採点の回数の表が読めない(%s)" % type(exc).__name__) from None
        if not isinstance(data, dict):
            raise TaskError("attempt_store_unavailable", "採点の回数の表の形が違う")
        out: dict[str, int] = {}
        for k, v in data.items():
            # 壊れた値(数でない・負・小数)は fail-closed。回数を小さく読み違えると上限が緩むので推測しない
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise TaskError("attempt_store_unavailable", "採点の回数の表の値が壊れている(%r)" % (k,))
            out[str(k)] = v
        return out

    def _write_file(self, data: dict[str, int]) -> None:
        """書けなければ ``attempt_store_unavailable``(fail-closed)。文にファイルの場所は入れない。

        ★2026-11-10(独立レビュー第 4 巡): 以前は OSError がそのまま外へ出て、その文に回数ファイルの
        フルパスが入っていた。
        """
        tmp = self.attempts_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.attempts_path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, sort_keys=True)
            os.replace(tmp, self.attempts_path)
        except OSError as exc:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise TaskError("attempt_store_unavailable",
                            "採点の回数の表に書けない(%s)" % type(exc).__name__) from None

    def _count(self, key: tuple[str, int]) -> int:
        if self.attempts_path is None:
            return self._attempts.get(key, 0)
        lock = self._file_lock()                          # 読むときも持つ(書き手の os.replace と重ねない)
        try:
            return max(self._attempts.get(key, 0), self._read_file().get(self._file_key(key), 0))
        finally:
            self._file_unlock(lock)

    def attempts_of(self, kind: str, seed: int) -> int:
        with self._lock:
            return self._count((kind, int(seed)))

    def audit(self, record: dict[str, Any]) -> None:
        """詳しい採点の記録を監査ファイル(JSON Lines)にだけ書く。場所が無ければ書かない。"""
        if not self.audit_path:
            return
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with self._lock:
            os.makedirs(os.path.dirname(self.audit_path) or ".", exist_ok=True)
            with open(self.audit_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def alternate(self, rec: "TaskRecord") -> "TaskRecord":
        """隠れた双子の課題: 同じ族・同じつまみで、真値の違う隠れた seed の課題(実行時の検査用)。

        双子の seed の決め方: ``sha256("alt|kind|seed|k|" + 秘密値の要約 [+ "|attempt=n"])`` の先頭 4 バイトを
        seed の範囲に畳み、k = 1, 2, … の順に、真値が元の課題と**どの鍵でも違う**最初の seed を使う
        (計数がたまたま同じだと、固定の答えが両方に合格してしまうため)。
        - 公開モード: 秘密値が空なので、公開の生成器から計算できる(公開モードは比較実験に使わない)。
          試行の番号は混ぜない(同じ課題なら同じ双子)。
        - 実験モード: 秘密値と**試行の番号**(``rec.attempts``)を混ぜ、試行ごとに双子を替える
          (独立レビュー第 4 巡: 同じ双子だと、合否だけでも本体と双子の探索を分けて進められた)。
        呼び手には返さない。
        """
        attempt = rec.attempts if self.mode == "secret" else 0
        cache = getattr(rec, "_alternates", None)
        if cache is None:
            cache = rec._alternates = {}
        if attempt in cache:
            return cache[attempt]
        digest = _secret_digest(self._secret)
        suffix = ("|attempt=%d" % attempt).encode("utf-8") if self.mode == "secret" else b""
        for k in range(1, 64):
            h = hashlib.sha256(("alt|%s|%d|%d|" % (rec.kind, rec.seed, k)).encode("utf-8") + digest + suffix).digest()
            alt_seed = int.from_bytes(h[:4], "little") % (MAX_SEED + 1)
            arr, truth, resolved = generate(rec.kind, alt_seed, rec.params, secret=self._secret)
            if all(not np.array_equal(np.asarray(truth[key]), np.asarray(rec.truth[key])) for key in truth):
                alt = TaskRecord(rec.task_id + "#hidden", rec.kind, alt_seed, resolved, arr, truth, rec.created)
                cache[attempt] = alt
                return alt
        raise RuntimeError("alternate: no seed with a different truth for %s" % rec.kind)

    def alternate_input(self, rec: "TaskRecord") -> np.ndarray:
        """:meth:`alternate` の入力だけ。"""
        return self.alternate(rec).input

    def make(self, kind: str, seed: int, params: dict | None = None) -> TaskRecord:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
            raise TaskError("bad_seed", "seed は 0..%d の整数: %r" % (MAX_SEED, seed))
        resolved = resolve_params(kind, params)
        tid = task_id_of(kind, seed, resolved, self._secret)
        key = (kind, int(seed))                     # 真値の鍵(params は真値を変えない)
        with self._lock:
            if key is not None and key not in self._attempts and len(self._attempts) >= self.max_truth_keys:
                raise TaskError("too_many_tasks", "このセッションで作れる真値の数(%d)を超えた" % self.max_truth_keys)
            rec = self._items.get(tid)
            if rec is not None and self.clock() - rec.created <= self.ttl_s:
                self._items.move_to_end(tid)
                rec.attempts = self._count(key)
                return rec
        arr, truth, resolved = generate(kind, seed, params, secret=self._secret)
        with self._lock:
            self._attempts.setdefault(key, 0)
            rec = TaskRecord(tid, kind, int(seed), resolved, arr, truth, self.clock(), self._count(key))
            self._items[tid] = rec
            self._items.move_to_end(tid)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
            return rec

    def peek(self, task_id: str) -> TaskRecord:
        """採点の回数を取らずに課題を読む(:meth:`claim` と同じ検査: 知らない・期限切れ・使い切りは TaskError)。

        ★2026-11-13(報告 11): 型の門で落ちた試行(1 段も走らせず、真値に触れない)も 1 回に数えていて、
        型の誤りを直しているだけで 32 回の枠を使い切った。走らせる前の検査は peek で、走らせる直前に claim する。"""
        if not isinstance(task_id, str) or not task_id.startswith(TASK_PREFIX):
            raise TaskError("unknown_task", "task_id は %s<16 hex> の形: %r" % (TASK_PREFIX, task_id))
        with self._lock:
            rec = self._items.get(task_id)
            if rec is None:
                raise TaskError("unknown_task", "知らない task_id(作っていない / 捨てられた): %s" % task_id)
            if self.clock() - rec.created > self.ttl_s:
                self._items.pop(task_id, None)
                raise TaskError("task_expired", "task_id の期限(%g 秒)が切れた: %s —— fullseye_make_task で作り直す"
                                "(採点の回数は戻らない)" % (self.ttl_s, task_id))
            key = (rec.kind, rec.seed)
            data = self._read_file() if self.attempts_path else None
            used = max(self._attempts.get(key, 0), (data or {}).get(self._file_key(key), 0))
            rec.attempts = used
            if used >= self.max_attempts:
                raise TaskError("attempts_exhausted", "この真値(%s seed=%d)の採点の回数(%d 回)を使い切った"
                                "(つまみを変えた課題・作り直した課題・別のセッションも同じ回数を数える)"
                                % (rec.kind, rec.seed, self.max_attempts))
            return rec

    def claim(self, task_id: str) -> TaskRecord:
        """採点 1 回ぶんを取る。知らない・期限切れ・使い切りは TaskError。"""
        if not isinstance(task_id, str) or not task_id.startswith(TASK_PREFIX):
            raise TaskError("unknown_task", "task_id は %s<16 hex> の形: %r" % (TASK_PREFIX, task_id))
        with self._lock:
            rec = self._items.get(task_id)
            if rec is None:
                raise TaskError("unknown_task", "知らない task_id(作っていない / 捨てられた): %s" % task_id)
            if self.clock() - rec.created > self.ttl_s:
                self._items.pop(task_id, None)
                raise TaskError("task_expired", "task_id の期限(%g 秒)が切れた: %s —— fullseye_make_task で作り直す"
                                "(採点の回数は戻らない)" % (self.ttl_s, task_id))
            key = (rec.kind, rec.seed)
            lock = self._file_lock() if self.attempts_path else None
            try:
                data = self._read_file() if lock else None
                used = max(self._attempts.get(key, 0), (data or {}).get(self._file_key(key), 0))
                if used >= self.max_attempts:
                    rec.attempts = used
                    raise TaskError("attempts_exhausted", "この真値(%s seed=%d)の採点の回数(%d 回)を使い切った"
                                    "(つまみを変えた課題・作り直した課題・別のセッションも同じ回数を数える)"
                                    % (rec.kind, rec.seed, self.max_attempts))
                if lock:
                    data[self._file_key(key)] = used + 1
                    self._write_file(data)
                self._attempts[key] = used + 1
                rec.attempts = used + 1
                return rec
            finally:
                if lock:
                    self._file_unlock(lock)


def public_task(rec: TaskRecord, ttl_s: float, max_attempts: int) -> dict[str, Any]:
    """LLM に見せる課題の記述(真値を含まない)。"""
    fam = FAMILIES[rec.kind]
    tol = fam.tolerance(rec.params)
    return {"task_id": rec.task_id, "kind": rec.kind, "field": fam.field, "seed": rec.seed,
            "params": dict(rec.params), "statement": fam.statement, "statement_en": fam.statement_en,
            "input": {"sort": fam.input_sort, "shape": list(fam.shape), "dtype": "float64",
                      "value_range": [0.0, 1.0]},
            "output": {"sorts": list(fam.output_sorts), "form": fam.output_form, "unit": fam.unit},
            "metrics": [{"name": n, "unit": u, "tolerance": _round(tol[n])} for n, u in fam.metrics],
            "tolerance_rationale": fam.rationale,
            "comparison_ready": rec.kind in COMPARISON_FAMILIES,
            "known_weakness": fam.known_weakness,
            "expires_in_s": ttl_s, "max_attempts": max_attempts}


def score_output(rec: TaskRecord, value: Any) -> list[dict[str, Any]]:
    """最終段の出力を真値と比べ、指標の行を返す(形が違えば TaskError)。"""
    fam = FAMILIES[rec.kind]
    return fam.score(value, rec.truth, rec.params)


def explain(metrics: list[dict[str, Any]]) -> list[str]:
    """外れ方の説明(どの指標がどれだけ外れたか)。真値も誤差の符号も書かない。"""
    lines = []
    for m in metrics:
        if m["passed"]:
            lines.append("%s: 誤差 %g %s は許容 %g %s 以内" % (m["name"], m["error"], m["unit"], m["tolerance"], m["unit"]))
        else:
            lines.append("%s: 誤差 %g %s が許容 %g %s を超えた(%s 倍)" % (
                m["name"], m["error"], m["unit"], m["tolerance"], m["unit"],
                "∞" if m["ratio"] is None else "%g" % m["ratio"]))
    return lines


def _band(m: dict[str, Any]) -> str:
    if m["passed"]:
        return "<=1x"
    ratio = m["ratio"]
    for limit, label in COARSE_BANDS[1:]:
        if ratio is not None and ratio <= limit:
            return label
    return ">5x"


def render_feedback(metrics: list[dict[str, Any]], level: str) -> tuple[list[dict[str, Any]], list[str]]:
    """``feedback`` の段階に合わせて、返す指標の行と説明を作る(詳しい値はサーバ側の記録にだけ残す)。

    - ``detailed``: 指標ごとの誤差の大きさ・許容・倍率・合否(:func:`explain`)。
    - ``coarse``: 指標ごとの合否と、許容の何倍かの段階(<=1x / <=2x / <=5x / >5x)だけ。
    - ``pass_fail``: 指標の行も説明も返さない(全体の合否だけ)。
    """
    if level == "detailed":
        return metrics, explain(metrics)
    if level == "coarse":
        rows = [{"name": m["name"], "unit": m["unit"], "tolerance": m["tolerance"], "passed": m["passed"],
                 "band": _band(m)} for m in metrics]
        return rows, ["%s: %s(許容の %s)" % (r["name"], "許容内" if r["passed"] else "許容外", r["band"])
                      for r in rows]
    if level == "pass_fail":
        return [], []
    raise TaskError("bad_feedback", "feedback は %s のどれか: %r" % (FEEDBACK_LEVELS, level))


def effective_feedback(requested: str | None, cap: str) -> tuple[str, bool]:
    """求めた段階と上限から、実際に返す段階(詳しすぎる要求は上限まで粗くする)。"""
    requested = requested or cap
    if requested not in FEEDBACK_LEVELS:
        raise TaskError("bad_feedback", "feedback は %s のどれか: %r" % (FEEDBACK_LEVELS, requested))
    if FEEDBACK_LEVELS.index(requested) < FEEDBACK_LEVELS.index(cap):
        return cap, True
    return requested, False
