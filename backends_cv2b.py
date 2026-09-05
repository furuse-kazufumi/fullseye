"""OpenCV incorporation (round 2) — distinctive functions not yet wrapped.

Log-polar warp, mean-shift filtering (pyrMeanShiftFiltering), hit-or-miss
morphology, the Laplacian-variance focus measure, and a FAST keypoint count.
`xcv2_` prefix; exception-safe; pipeline-convention outputs.
"""
from __future__ import annotations

import numpy as np


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        import cv2
    except Exception:
        return []

    def _u8(v):
        return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)

    def _logpolar(v, a, b):
        """対数極座標変換（ログポーラー変換）で画像を (半径, 角度) 平面に写像する。

        ``cv2.warpPolar`` の ``WARP_POLAR_LOG`` モードを使う。中心は画像中心、最大
        半径は ``min(H, W)/2``。出力の行方向が対数半径、列方向が角度に対応する。
        ``a``, ``b`` は未使用。拡大縮小・回転を新しい画像上の平行移動に変換できる
        ため、テンプレートマッチングの前処理（Fourier-Mellin 変換の要素技術）として
        使われる。HALCON に対応する単一オペレータは無い。
        """
        x = np.asarray(v, np.float32)
        h, w = x.shape
        return cv2.warpPolar(x, (w, h), (w / 2, h / 2), min(h, w) / 2,
                             cv2.WARP_POLAR_LOG + cv2.INTER_LINEAR).astype(np.float64)

    def _meanshift(v, a, b):
        """平均値シフト（mean-shift）フィルタリングで色/輝度を領域ごとに均す
        （``cv2.pyrMeanShiftFiltering``）。

        ``a`` は空間窓半径 ``sp`` を 5〜30 に振り（``sp = 5 + 25*a``）、``b`` は
        輝度（色）レンジ ``sr`` を 10〜50 に振る（``sr = 10 + 40*b``）。グレースケール
        画像を内部で 3ch BGR に複製してから処理し、結果を再びグレースケールへ
        戻す。エッジを保ったまま平坦な領域を単色化する前処理（減色・セグメンテー
        ション前処理）に向く。
        """
        bgr = cv2.cvtColor(_u8(v), cv2.COLOR_GRAY2BGR)
        out = cv2.pyrMeanShiftFiltering(bgr, sp=5 + 25 * a, sr=10 + 40 * b)
        return cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float64) / 255

    def _hitmiss(v, a, b):
        """ヒットオアミス変換で「中心は背景・上下左右は前景」という十字パターンを
        検出する（``cv2.MORPH_HITMISS``）。

        固定カーネル ``[[0,1,0],[1,-1,1],[0,1,0]]`` を使う（1=前景必須、-1=背景必須、
        0=不問）。``a``, ``b`` は未使用。前景に囲まれた 1 画素の窪み（孤立した背景
        画素）を拾うので、細線化後の欠け検出や形状のノッチ検出に使える。入力は
        しきい値 0.5 で二値化してから判定する。
        """
        m = (np.asarray(v) > 0.5).astype(np.uint8)
        ker = np.array([[0, 1, 0], [1, -1, 1], [0, 1, 0]], np.int8)
        return (cv2.morphologyEx(m, cv2.MORPH_HITMISS, ker) > 0).astype(np.float64)

    def _lap_var(v, a, b):
        """ラプラシアン分散によるフォーカス（ボケ）指標（``cv2.Laplacian`` の分散）。

        画像全体に Laplacian を掛けた結果の分散を計算し、``min(1.0, 分散*20)`` で
        [0,1] にクリップしたスカラーを返す。``a``, ``b`` は未使用。値が大きいほど
        エッジ/テクスチャが豊富＝合焦、小さいほどボケている可能性が高い、という
        古典的なオートフォーカス評価指標。倍率 20 は経験的なスケーリングで、
        絶対的なボケ量ではなく相対比較に向く。
        """
        lv = float(cv2.Laplacian(np.clip(np.asarray(v, np.float64), 0, 1), cv2.CV_64F).var())
        return np.float64(min(1.0, lv * 20))          # focus / blur measure

    def _fast_count(v, a, b):
        """FAST コーナー検出器が検出したキーポイントの個数（``cv2.FastFeatureDetector``）。

        ``a`` は検出しきい値を 5〜45 に振る（``threshold = int(5 + 40*a)``、大きい
        ほど検出されにくくなり数が減る）。``b`` は未使用。テクスチャの豊富さ・
        コーナーの多さを表す特徴量で、値が大きいほど局所的な輝度変化に富む画像
        であることを示す。
        """
        fast = cv2.FastFeatureDetector_create(threshold=int(5 + 40 * a))
        return np.float64(len(fast.detect(_u8(v), None)))

    defs = [
        ("xcv2_warp_logpolar", "geometry", "", IMAGE, IMAGE, _logpolar),
        ("xcv2_meanshift", "segmentation", "", IMAGE, IMAGE, _meanshift),
        ("xcv2_hitmiss", "region", "", REGION, REGION, _hitmiss),
        ("xcv2_lap_var", "features", "", IMAGE, FEATURE, _lap_var),
        ("xcv2_fast_count", "features", "", IMAGE, FEATURE, _fast_count),
    ]
    return [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in defs]
