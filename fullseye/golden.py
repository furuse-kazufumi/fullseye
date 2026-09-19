# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.golden — 基準画像(ゴールデン)との比較で欠陥を測る(検査ワークフロー層 #3)。

現場の「良品と比べて違うところを見つける」を 1 回の呼び出しにする。新アルゴリズムは無く、

    位置合わせ(filters_freq.phase_correlation_fft、整数並進)
      → 差分 |image − golden|(任意で両方をガウス平滑してから)
      → 閾値 → 連結成分(scipy.ndimage.label)→ 面積で足切り
      → 計測 dict {shift_row, shift_col, ssim, psnr, max_diff, mean_diff, defect_area, defect_count, ...}

の配線。計測 dict は :func:`fullseye.judge.judge` にそのまま渡せ、:func:`golden_measure` で
:func:`fullseye.inspect_batch.inspect_batch` の ``measure`` になる(ロット全体をゴールデン比較)。

**約束(fail-closed)**:

- 形が違う・2-D でない・非有限を含む画像は ``ValueError``(黙って 0 欠陥にしない)。
- 並進が ``max_shift`` を超えたら**合わせない**で ``align_ok=False`` と生の shift を返す
  (大きくずれた品はそれ自体が異常。spec の ``shift_row/shift_col`` の範囲で ng にできる)。
- 位置合わせで画像の外から巻き込んだ縁は ``valid`` から除き、欠陥にも計測にも数えない。
- ``mask``(検査領域、True=見る)は golden と同じ形。領域外は欠陥に数えない。

**限界**: 整数並進のみ(回転・スケール・サブピクセルは扱わない —— それは ``frame_align`` /
``ncc_locate`` / 形状マッチの仕事)。照明差は ``blur`` と閾値では吸収しきれない(前処理レシピで
正規化してから渡す)。周期構造の位相相関は格子 1 個ぶんずれた答えを返しうる(``max_shift`` で縛る)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["compare_to_golden", "golden_measure", "golden_spec", "GOLDEN_KEYS"]

#: :func:`compare_to_golden` が返す計測 dict のキー(spec を書くときの語彙)。
GOLDEN_KEYS = ("shift_row", "shift_col", "align_ok", "ssim", "psnr", "max_diff", "mean_diff",
               "defect_area", "defect_count", "defect_area_max", "valid_fraction")


def _as_image(x, name: str) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("golden: %s must be a 2-D image, got shape %s" % (name, a.shape))
    if a.size == 0:
        raise ValueError("golden: %s is empty" % name)
    if not np.isfinite(a).all():
        raise ValueError("golden: %s contains non-finite values" % name)
    return a


def _shift_with_valid(img: np.ndarray, dr: int, dc: int):
    """整数並進(np.roll)と、巻き込んだ縁を除いた valid マスク。"""
    out = np.roll(np.roll(img, dr, axis=0), dc, axis=1)
    valid = np.ones(img.shape, dtype=bool)
    h, w = img.shape
    if dr > 0:
        valid[:dr, :] = False
    elif dr < 0:
        valid[h + dr:, :] = False
    if dc > 0:
        valid[:, :dc] = False
    elif dc < 0:
        valid[:, w + dc:] = False
    return out, valid


def compare_to_golden(image, golden, *, align=True, max_shift=None, mask=None,
                      threshold=0.1, min_area=1, blur=0.0, data_range=None) -> dict:
    """``image`` を基準画像 ``golden`` と比べ、欠陥の計測 dict と差分の絵を返す。

    ``align=True`` で位相相関の整数並進を合わせる(``max_shift`` px を超える推定は採用せず
    ``align_ok=False``)。``blur``>0 なら両画像をその σ でガウス平滑してから差分(ノイズと
    1 px の縁ずれを抑える)。``threshold`` を超えた差分画素を ``mask``・``valid`` 内で連結成分に
    し、``min_area`` 未満の成分は落とす。``data_range`` は SSIM/PSNR の値域(``None`` なら
    golden から推定、imgmetrics.data_range_of)。

    返り値::

        {"measurements": {shift_row, shift_col, align_ok(0/1), ssim, psnr, max_diff, mean_diff,
                          defect_area, defect_count, defect_area_max, valid_fraction},
         "diff": |aligned − golden| (2-D float, valid 外は 0),
         "defect_mask": bool 2-D, "labels": int 2-D (0=背景), "valid": bool 2-D,
         "aligned": 位置合わせ後の image}
    """
    img = _as_image(image, "image")
    ref = _as_image(golden, "golden")
    if img.shape != ref.shape:
        raise ValueError("golden: image %s and golden %s differ in shape" % (img.shape, ref.shape))
    if mask is not None:
        m = np.asarray(mask)
        if m.shape != ref.shape:
            raise ValueError("golden: mask %s must match golden %s" % (m.shape, ref.shape))
        m = m.astype(bool)
    else:
        m = np.ones(ref.shape, dtype=bool)
    if threshold < 0 or min_area < 1 or blur < 0:
        raise ValueError("golden: threshold >= 0, min_area >= 1, blur >= 0 required")

    from filters_freq import phase_correlation_fft
    dr = dc = 0
    align_ok = True
    if align:
        pc = phase_correlation_fft(ref, img)
        dr_est, dc_est = int(round(pc["row_shift"])), int(round(pc["col_shift"]))
        if max_shift is not None and max(abs(dr_est), abs(dc_est)) > max_shift:
            align_ok = False                                  # 合わせない: ずれ自体が異常
        else:
            dr, dc = dr_est, dc_est
        shift_row, shift_col = float(dr_est), float(dc_est)
    else:
        shift_row = shift_col = 0.0
    aligned, valid = _shift_with_valid(img, dr, dc)

    a, b = aligned, ref
    if blur > 0:
        from scipy.ndimage import gaussian_filter
        a = gaussian_filter(a, blur)
        b = gaussian_filter(b, blur)
    diff = np.abs(a - b)
    region = valid & m
    diff = np.where(region, diff, 0.0)

    from scipy.ndimage import label
    hot = (diff > threshold) & region
    labels, n = label(hot)
    areas = np.bincount(labels.ravel())[1:] if n else np.zeros(0, dtype=int)
    keep = np.zeros(n + 1, dtype=bool)
    if n:
        keep[1:] = areas >= min_area
    defect_mask = keep[labels]
    kept_areas = areas[areas >= min_area] if n else areas

    import imgmetrics
    dr_val = imgmetrics.data_range_of(ref, data_range=data_range)
    meas = {
        "shift_row": shift_row, "shift_col": shift_col, "align_ok": 1.0 if align_ok else 0.0,
        "ssim": float(imgmetrics.ssim(aligned, ref, data_range=dr_val)),
        "psnr": float(imgmetrics.psnr(aligned, ref, data_range=dr_val)),
        "max_diff": float(diff.max()) if region.any() else 0.0,
        "mean_diff": float(diff[region].mean()) if region.any() else 0.0,
        "defect_area": float(defect_mask.sum()),
        "defect_count": float(kept_areas.size),
        "defect_area_max": float(kept_areas.max()) if kept_areas.size else 0.0,
        "valid_fraction": float(region.mean()),
    }
    # 連結成分の番号を「残した成分だけ」で振り直す(落とした成分の番号が飛ばない)。
    if n:
        remap = np.zeros(n + 1, dtype=labels.dtype)
        remap[np.flatnonzero(keep)] = np.arange(1, int(keep.sum()) + 1)
        labels = remap[labels]
    return {"measurements": meas, "diff": diff, "defect_mask": defect_mask, "labels": labels,
            "valid": valid, "aligned": aligned}


def golden_measure(golden, **kw):
    """:func:`inspect_batch` の ``measure`` を作る: ``measure(image) -> measurements dict``。
    ``kw`` は :func:`compare_to_golden` にそのまま渡る(align / max_shift / mask / threshold /
    min_area / blur / data_range)。golden は作った時点で検証する(壊れた基準で 1 ロット回さない)。"""
    ref = _as_image(golden, "golden")
    if "mask" in kw and kw["mask"] is not None and np.asarray(kw["mask"]).shape != ref.shape:
        raise ValueError("golden_measure: mask must match golden shape %s" % (ref.shape,))

    def measure(image):
        return compare_to_golden(image, ref, **kw)["measurements"]

    measure.__doc__ = "compare_to_golden(image, golden, **%r)[\"measurements\"]" % (kw,)
    return measure


def golden_spec(*, max_defect_area=0.0, max_defect_count=None, min_ssim=None,
                max_shift=None, require_aligned=True) -> dict:
    """:func:`judge` 用の仕様 dict を組む(語彙は :data:`GOLDEN_KEYS`)。

    既定は「欠陥面積 0 かつ位置合わせ成功」。``max_shift`` を渡すと並進の許容 ±px、
    ``min_ssim`` で構造類似の下限、``max_defect_count`` で欠陥の個数上限。"""
    spec = {"defect_area": {"max": float(max_defect_area)}}
    if max_defect_count is not None:
        spec["defect_count"] = {"max": float(max_defect_count)}
    if min_ssim is not None:
        spec["ssim"] = {"min": float(min_ssim)}
    if max_shift is not None:
        spec["shift_row"] = {"nominal": 0.0, "tol": float(max_shift)}
        spec["shift_col"] = {"nominal": 0.0, "tol": float(max_shift)}
    if require_aligned:
        spec["align_ok"] = {"eq": 1.0}
    return spec
