# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_segmentation — 2次元セグメンテーション演算子ファミリ総ざらい (task: segmentation)

    py -3.11 examples/gallery2d_segmentation.py

【平たく言うと】
このファミリは「画像 → 領域(region)」への分割演算子群。しきい値法(Otsu/Li/Yen/
Sauvola/Niblack…)、エッジ抽出(Canny/zero-crossing)、局所ピーク検出、
領域成長・分水嶺(watershed)・スーパーピクセル(SLIC/Felzenszwalb)・GMM/k-means・
グラフカット(GrabCut/normalized-cut)まで、画素を「前景/背景」や「区画」に切り分ける
道具箱。カテゴリ ["segmentation","segment","morphology/markers"] の全 op を対象にする。

【この例が検証するもの(GT = ground truth)】
1. 一般契約(全 op): 出力が有限(NaN/Inf 無し)/ 宣言 out_sort と一致
   (region → 2次元 float かつ値が {0,1} の二値、image → 2次元 float かつ [0,1])/
   決定的(同一入力 → ビット一致)。例外を投げた op は握りつぶさず大声で FAIL。
2. 効果が既知の代表 op には、より強い GT + beat-the-null を追加:
   - threshold : しきい値 a を上げると前景画素が単調に減る(勾配画像で 1728→576)。
   - otsu      : 二峰性画像で前景平均 > 背景平均(分離マージン大)+ 真円との IoU ≈ 1。
   - canny     : 鋭いエッジの近傍にだけ応答(平坦部の応答は 0)。
   - multiotsu : 多値化で二値 Otsu(2 値)より真に多い階調(≥3)を作る。
   - local_max : 明るいピークだけを検出し、平坦な背景は拾わない。

対象ファミリの **すべての op** を実際に呼び出し(登録重複を含め 64 回)、上記を検証する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import warnings

import numpy as np
import ops  # noqa: E402

# 各バックエンド(pywt/skimage 等)の境界警告は本題ではない。失敗の唯一の信号を
# assert に絞るため沈黙させる(conftest と同じ方針だが tests/ からは import しない)。
warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------- #
# 入力ファクトリ — conftest.image_bank の "normal" と同じ構成(tests/ に非依存)。 #
# このファミリの in_sort はすべて "image"(2次元 float in [0,1])。               #
# --------------------------------------------------------------------------- #
def input_for(in_sort: str, n: int = 48) -> np.ndarray:
    """in_sort に対応した妥当な入力を返す。本ファミリは全 op が in_sort='image'。"""
    if in_sort != "image":
        raise ValueError(f"unexpected in_sort for this family: {in_sort!r}")
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(20260812)
    return np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)


# --------------------------------------------------------------------------- #
# TARGET set — category ∈ {segmentation, segment, morphology/markers} の全 op。 #
# 明示的な文字列リテラル(op→example インデックス用に名前が字面で現れること)。   #
# 登録の重複(dyn_threshold / local_max は raw と _safe ラップの二重登録)を含め   #
# REGISTRY と同順・同数(= 64)。                                                 #
# --------------------------------------------------------------------------- #
OPS = [
    'threshold', 'otsu', 'dyn_threshold', 'canny',
    'local_max', 'adaptive_gauss_thresh', 'sk_otsu', 'sk_li',
    'sk_yen', 'sk_sauvola', 'sk_niblack', 'sk_canny',
    'sk_felzenszwalb', 'sk_slic', 'sk_chan_vese', 'sk_local_maxima',
    'sk_hysteresis', 'cv_otsu', 'cv_adaptive_mean', 'cv_adaptive_gauss',
    'cv_canny', 'h_threshold', 'binary_threshold', 'auto_threshold',
    'dyn_threshold', 'var_threshold', 'local_threshold', 'hysteresis_threshold',
    'edges_image', 'watersheds', 'watersheds_threshold', 'regiongrowing',
    'local_max', 'dual_threshold', 'segment_image_mser', 'regiongrowing_mean',
    'zero_crossing', 'local_min', 'bin_threshold', 'fast_threshold',
    'nonmax_suppression_amp', 'pouring', 'xsk_random_walker', 'xsk_flood',
    'xcv_grabcut', 'xcv_watershed_markers', 'xsk2_multiotsu', 'xsk2_h_maxima',
    'xcv2_meanshift', 'xmh_bernsen', 'xmh_regmin', 'xsk3_rank_otsu',
    'xsk3_h_minima', 'xsk3_threshold_local_median', 'xsk3_peak_local_max', 'xkor_canny',
    'it_region_to_bin', 'sg_slic_superpixels', 'sg_felzenszwalb', 'sg_gmm_segment',
    'sg_kmeans_intensity', 'sg_region_growing_seeded', 'sg_normalized_cut_2', 'sg_watershed_gradient',
]

# kornia backend (要 torch+kornia) 依存の任意 op。未インストール環境では registry から
# 静かに消える (backends_kornia.build が [] を返す) ため _BY_NAME 参照は KeyError になる。
# BASE = 常設分 = OPS から除いた分。
KORNIA_OPTIONAL = ['xkor_canny']
BASE_OPS = [n for n in OPS if n not in KORNIA_OPTIONAL]

# 演算子つまみ(a, b)は [0,1]。既定は中庸。全 op がこの入力/つまみで CPU 完走する。
KNOB = (0.5, 0.5)
EPS = 1e-9


def _assert_typed_finite(name: str, out, out_sort: str) -> None:
    """宣言 out_sort に対する一般契約: 有限・型・値域(+ region は二値)を検査。"""
    if out_sort in ("image", "region"):
        assert isinstance(out, np.ndarray), f"{name}: expected ndarray, got {type(out).__name__}"
        assert out.ndim == 2, f"{name}: expected 2-D {out_sort}, got ndim={out.ndim}"
        assert np.all(np.isfinite(out)), f"{name}: non-finite value in output (NaN/Inf)"
        lo, hi = float(np.min(out)), float(np.max(out))
        assert -EPS <= lo and hi <= 1.0 + EPS, f"{name}: {out_sort} out of [0,1]: min={lo}, max={hi}"
        if out_sort == "region":
            uniq = set(np.round(np.unique(out), 6).tolist())
            assert uniq <= {0.0, 1.0}, f"{name}: region must be binary, got levels {sorted(uniq)[:6]}"
    elif out_sort == "feature":
        arr = np.asarray(out, dtype=np.float64)
        assert np.all(np.isfinite(arr)), f"{name}: non-finite feature"
    elif out_sort == "contour":
        assert isinstance(out, dict) and "cs" in out, f"{name}: contour must be dict with 'cs'"
    else:
        raise AssertionError(f"{name}: unhandled out_sort {out_sort!r}")


def run_family() -> tuple[int, list[str]]:
    """全 op (利用可能集合) を呼び、一般契約(有限・型・値域・決定性)を検査する。

    kornia 不在で消えた KORNIA_OPTIONAL 分は正直に skip 表示し、対象から除く。
    戻り値は (検査した op 数, スキップした op 名一覧)。
    """
    live_names = set(ops._BY_NAME)
    skipped = sorted(n for n in KORNIA_OPTIONAL if n not in live_names)
    if skipped:
        print(f"skipped {len(skipped)} optional ops (kornia not installed): {', '.join(skipped)}")
    active_ops = [n for n in OPS if n not in skipped]

    exercised = 0
    for name in active_ops:
        op = ops._BY_NAME[name]                       # name→op(重複名は同じ実体へ解決)
        img = input_for(op.in_sort)
        try:
            out1 = op.fn(img.copy(), *KNOB)
            out2 = op.fn(img.copy(), *KNOB)           # 決定性: 同一入力 → ビット一致
        except Exception as exc:                       # 握りつぶさず大声で失敗させる
            raise AssertionError(f"{name}: raised {type(exc).__name__}: {exc}") from exc
        _assert_typed_finite(name, out1, op.out_sort)
        assert np.array_equal(out1, out2), f"{name}: non-deterministic (same input, different output)"
        exercised += 1
    expected = len(BASE_OPS) + (len(KORNIA_OPTIONAL) - len(skipped))
    assert exercised == len(active_ops) == expected, (
        f"exercised {exercised} != active_ops {len(active_ops)} != expected {expected}")
    return exercised, skipped


# --------------------------------------------------------------------------- #
# 代表 op の強い GT + beat-the-null(「動く」ではなく「正しく効く」を測る)。       #
# --------------------------------------------------------------------------- #
def gt_checks() -> int:
    BY = ops._BY_NAME
    k = 0

    # GT1: threshold は (v > a)。しきい値 a を上げると前景が単調に減る(横勾配画像)。
    grad = np.tile(np.linspace(0, 1, 48), (48, 1))
    fg_lo = BY["threshold"].fn(grad.copy(), 0.25, 0.0)
    fg_hi = BY["threshold"].fn(grad.copy(), 0.75, 0.0)
    assert set(np.unique(fg_lo).tolist()) <= {0.0, 1.0}                     # 二値
    assert fg_lo.sum() > fg_hi.sum()                                       # 単調(beat-the-null)
    assert float(grad[fg_lo == 1].min()) > 0.25                            # 前景は必ず a 超
    k += 1

    # GT2: otsu は二峰性画像を谷で分離。前景平均 > 背景平均、真円との IoU ≈ 1。
    n = 48
    yy, xx = np.mgrid[0:n, 0:n]
    disk = ((yy - 24) ** 2 + (xx - 24) ** 2) < 12 ** 2
    rng = np.random.default_rng(1)
    bim = np.clip(np.where(disk, 0.8, 0.2) + 0.02 * rng.standard_normal((n, n)), 0, 1)
    reg = BY["otsu"].fn(bim.copy(), 0.0, 0.0)
    fg_mean, bg_mean = float(bim[reg == 1].mean()), float(bim[reg == 0].mean())
    iou = np.logical_and(reg == 1, disk).sum() / np.logical_or(reg == 1, disk).sum()
    assert fg_mean - bg_mean > 0.4                     # ランダム分割なら ≈0 → beat-the-null
    assert iou > 0.9                                   # 真の物体をほぼ復元
    k += 1

    # GT3: canny は鋭いエッジの近傍にだけ応答。平坦部の応答は 0。
    edge = np.full((48, 48), 0.1)
    edge[:, 24:] = 0.9
    ce = BY["canny"].fn(edge.copy(), 0.2, 0.2)
    band = float(ce[:, 22:27].sum())                   # 境界列の帯
    flat = float(ce[5:15, 3:13].sum())                 # 平坦パッチ
    assert band > 0 and flat == 0.0 and band > 10 * (flat + 1)
    k += 1

    # GT4: multiotsu は二値 Otsu より真に多い階調を作る(勾配画像で ≥3 レベル)。
    mo = BY["xsk2_multiotsu"].fn(grad.copy(), 0.5, 0.0)
    ob = BY["otsu"].fn(grad.copy(), 0.5, 0.0)
    assert len(np.unique(mo)) >= 3 and len(np.unique(mo)) > len(np.unique(ob))
    k += 1

    # GT5: local_max は明るいピークだけ検出、平坦背景は拾わない。
    peak = np.full((48, 48), 0.2)
    peak[24, 24] = 1.0
    lm = BY["local_max"].fn(peak.copy(), 0.3, 0.5)     # 閾値 = 0.3 + 0.4*0.5 = 0.5
    assert lm[24, 24] == 1.0                            # ピークは検出
    assert float(lm[0:10, 0:10].sum()) == 0.0          # 平坦背景は 0(beat-the-null)
    assert float(lm.sum()) < 5                          # 疎な検出
    k += 1

    return k


def main() -> int:
    n, skipped = run_family()
    k = gt_checks()
    uniq = len(set(OPS) - set(skipped))
    print(f"PASS: {n} ops exercised ({uniq} unique names), "
          f"all finite/typed/deterministic; {k} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
