# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvtrack —— 線形カルマンフィルタの 1 周期と、画素ごとのカルマン背景推定。

背景のモデルは dict で、どの op も入力のモデルを書き換えず新しいモデルを返す。
出典: R. E. Kalman, J. Basic Eng. 82(1), 35-45 (1960);
C. Ridder, O. Munkelt, H. Kirchner, Proc. ICRAM 1995, 193-199。
"""
from __future__ import annotations

import numpy as np


def _matrix(value, rows, cols, name, op):
    a = np.asarray(value, dtype=np.float64)
    if a.ndim == 0 and rows == cols:
        a = np.eye(rows) * float(a)
    if a.shape != (rows, cols) or not np.isfinite(a).all():
        raise ValueError("%s: %s must be a finite %dx%d array, got shape %r"
                         % (op, name, rows, cols, a.shape))
    return a


def filter_kalman(x, P, z, F, H, Q, R):
    """線形カルマンフィルタの予測と更新を 1 周期ぶん計算する。

    ``x' = F x``、``P' = F P F^T + Q`` で予測し、観測 ``z`` で更新する。共分散は対称性の崩れに
    強い Joseph 形で更新する。``z`` が None なら更新を省く(観測の欠けたコマ)。
    空の入力(``x`` が 0 要素)は ValueError。

    Args:
        x: 状態 (n,)。
        P: 状態の共分散 (n, n)。
        z: 観測 (m,)。None で予測だけ。
        F: 遷移行列 (n, n)。
        H: 観測行列 (m, n)。
        Q: 過程の雑音の共分散 (n, n)(スカラーは対角へ広げる)。
        R: 観測の雑音の共分散 (m, m)(スカラーは対角へ広げる)。

    Returns:
        ``x``、``P``、``gain``、``innovation``、``nis``(正規化した新息の 2 乗)を持つ dict。
        観測が無いコマの ``gain`` と ``innovation`` は 0、``nis`` は NaN。
    """
    op = "filter_kalman"
    xv = np.asarray(x, dtype=np.float64).ravel()
    if xv.size == 0:
        raise ValueError("%s: x is empty — pass at least one state" % op)
    if not np.isfinite(xv).all():
        raise ValueError("%s: x has NaN/inf" % op)
    n = xv.size
    Pm = _matrix(P, n, n, "P", op)
    Fm = _matrix(F, n, n, "F", op)
    Qm = _matrix(Q, n, n, "Q", op)
    Hm = np.atleast_2d(np.asarray(H, dtype=np.float64))
    if Hm.shape[1] != n or not np.isfinite(Hm).all():
        raise ValueError("%s: H must be a finite m x %d array" % (op, n))
    m = Hm.shape[0]
    Rm = _matrix(R, m, m, "R", op)
    xp = Fm @ xv
    Pp = Fm @ Pm @ Fm.T + Qm
    if z is None:
        return {"x": xp, "P": Pp, "gain": np.zeros((n, m)), "innovation": np.zeros(m),
                "nis": float("nan")}
    zv = np.asarray(z, dtype=np.float64).ravel()
    if zv.size != m or not np.isfinite(zv).all():
        raise ValueError("%s: z must be finite with %d entries" % (op, m))
    S = Hm @ Pp @ Hm.T + Rm
    try:
        Sinv = np.linalg.inv(S)
    except np.linalg.LinAlgError as exc:
        raise ValueError("%s: the innovation covariance is singular" % op) from exc
    K = Pp @ Hm.T @ Sinv
    nu = zv - Hm @ xp
    IKH = np.eye(n) - K @ Hm
    return {"x": xp + K @ nu, "P": IKH @ Pp @ IKH.T + K @ Rm @ K.T, "gain": K,
            "innovation": nu, "nis": float(nu @ Sinv @ nu)}


def _bg_image(image, op, shape=None):
    raw = np.asarray(image)
    if raw.size == 0:
        raise ValueError("%s: image is empty — pass at least one pixel" % op)
    # ★2026-11-09 点検: 既定の threshold=0.1・measurement_noise=1e-3 は [0, 1] の画素値の尺度。
    #   uint8 の静止場面(±2 DN の雑音だけ)をそのまま渡すと前景率 79 % を黙って返した。
    if raw.dtype.kind in "iu":
        raise ValueError("%s: image has integer dtype %s — the background model works on [0, 1] "
                         "float pixels (threshold and noise variances are on that scale); convert "
                         "first, e.g. img.astype(np.float64) / 255.0" % (op, raw.dtype))
    a = np.asarray(raw, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError("%s: image must be a finite 2-D array" % op)
    if a.min() < -1e-9 or a.max() > 1.0 + 1e-9:
        raise ValueError("%s: image values span [%g, %g] — the background model expects [0, 1] "
                         "(threshold and noise variances are on that scale); rescale first"
                         % (op, float(a.min()), float(a.max())))
    if shape is not None and a.shape != tuple(shape):
        raise ValueError("%s: image shape %r differs from the model %r" % (op, a.shape, tuple(shape)))
    return a


def _bg_model(model, op):
    need = ("background", "variance", "process_noise", "measurement_noise", "threshold",
            "foreground_gain")
    if not isinstance(model, dict) or any(k not in model for k in need):
        raise ValueError("%s: model must come from create_bg_esti" % op)
    return model


def create_bg_esti(image, process_noise=1e-4, measurement_noise=1e-3, threshold=0.1,
                   foreground_gain=0.05):
    """最初の画像から画素ごとのカルマン背景モデルを作る。

    各画素の背景はランダムウォークと見なし、過程の雑音 ``process_noise`` と観測の雑音
    ``measurement_noise`` の分散からゲインが決まる。前景と判定された画素はゲインに
    ``foreground_gain`` を掛けて弱く更新し、通過する物体を背景に取り込まない。
    画素値は **[0, 1] の float**(``threshold`` と雑音の分散も同じ尺度)。整数 dtype の画像と
    [0, 1] の外の値は ValueError(uint8 は ``/ 255`` してから渡す)。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: 最初の画像 (H, W)。
        process_noise: 過程の雑音の分散(> 0)。
        measurement_noise: 観測の雑音の分散(> 0)。
        threshold: 前景と判定する残差の絶対値(> 0)。
        foreground_gain: 前景の画素のゲイン倍率(0..1)。

    Returns:
        背景 ``background`` と分散 ``variance`` を持つモデルの dict。
    """
    op = "create_bg_esti"
    a = _bg_image(image, op)
    q, r, t, g = float(process_noise), float(measurement_noise), float(threshold), float(foreground_gain)
    if not np.isfinite([q, r, t, g]).all() or q <= 0 or r <= 0 or t <= 0 or not 0 <= g <= 1:
        raise ValueError("%s: noise and threshold must be positive, foreground_gain in [0, 1]" % op)
    return {"background": a.copy(), "variance": np.full(a.shape, r), "process_noise": q,
            "measurement_noise": r, "threshold": t, "foreground_gain": g, "frames": 0}


def _kalman_step(model, image, weight):
    """画素ごとの重み ``weight`` でゲインを弱めた 1 歩を計算する。"""
    p = model["variance"] + model["process_noise"]
    k = p / (p + model["measurement_noise"])
    gain = k * weight
    out = dict(model)
    out["background"] = model["background"] + gain * (image - model["background"])
    out["variance"] = (1.0 - gain) ** 2 * p + gain * gain * model["measurement_noise"]
    out["frames"] = int(model["frames"]) + 1
    return out


def run_bg_esti(model, image):
    """画像 1 枚で背景を更新し、前景の領域を返す。

    背景との差の絶対値が ``threshold`` を超える画素を前景にする。入力の ``model`` は書き換えず、
    更新後のモデルを ``model`` の鍵で返す。画素値は :func:`create_bg_esti` と同じ [0, 1] の float
    (整数 dtype と範囲外は ValueError)。空の入力(``image`` が 0 要素)は ValueError。

    Args:
        model: :func:`create_bg_esti` の返り。
        image: 現在の画像(モデルと同じ形)。

    Returns:
        ``model``(更新後)と ``foreground``(bool 配列)を持つ dict。
    """
    op = "run_bg_esti"
    m = _bg_model(model, op)
    a = _bg_image(image, op, m["background"].shape)
    fg = np.abs(a - m["background"]) > m["threshold"]
    weight = np.where(fg, m["foreground_gain"], 1.0)
    return {"model": _kalman_step(m, a, weight), "foreground": fg}


def give_bg_esti(model):
    """モデルの現在の背景の画像を返す(コピー)。

    空の入力は無い(モデルは ``create_bg_esti`` が必ず 1 画素以上で作る)。形の違う値は ValueError。

    Args:
        model: :func:`create_bg_esti` の返り。

    Returns:
        背景の float 画像。
    """
    return _bg_model(model, "give_bg_esti")["background"].copy()


def update_bg_esti(model, image, update_region):
    """指定した領域の画素だけ、画像で背景を更新する(領域の外は分散も動かない)。

    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        model: :func:`create_bg_esti` の返り。
        image: 現在の画像(モデルと同じ形)。
        update_region: 更新する画素の bool 配列(同じ形)。

    Returns:
        更新後のモデルの dict。
    """
    op = "update_bg_esti"
    m = _bg_model(model, op)
    a = _bg_image(image, op, m["background"].shape)
    reg = np.asarray(update_region) > 0
    if reg.shape != a.shape:
        raise ValueError("%s: update_region shape %r differs from the image" % (op, reg.shape))
    out = _kalman_step(m, a, np.ones(a.shape))
    out["background"] = np.where(reg, out["background"], m["background"])
    out["variance"] = np.where(reg, out["variance"], m["variance"])
    return out
