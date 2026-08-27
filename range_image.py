"""range_image — organized(格子構造)深度画像の処理(深度センサ → 特徴の橋渡し)。

depth camera(RGB-D / ToF / structured-light)の出力は画素格子に整列した organized な
深度画像。非整列点群の kNN 法線推定より、隣接画素の外積で O(HW) に**向き付き**法線が出せる。
bearing-angle 画像・遮蔽エッジも range image 特有の古典特徴。すべて閉形式・GT 検証可能。

差別化: match3d.estimate_point_normals は unorganized 点群向け(kNN・符号曖昧)。ここは格子構造を
使い、視点向きに符号を確定する。Physical AI のナビ/把持で depth→法線→接触判定に直結。
"""
import numpy as np


def depth_to_organized_points(depth, fx=None, fy=None, cx=None, cy=None):
    """organized 深度画像 → 格子整列 3D 点 (H,W,3)。

    fx,fy 指定で透視逆投影 P=((u-cx)/fx*d, (v-cy)/fy*d, d)。未指定は正射(P=(x,y,depth), 格子間隔1)。
    """
    d = np.asarray(depth, float)
    H, W = d.shape
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    if fx is None or fy is None:
        return np.stack([uu.astype(float), vv.astype(float), d], axis=-1)
    if cx is None:
        cx = (W - 1) / 2.0
    if cy is None:
        cy = (H - 1) / 2.0
    x = (uu - cx) / fx * d
    y = (vv - cy) / fy * d
    return np.stack([x, y, d], axis=-1)


def normals_from_depth(depth, fx=None, fy=None, cx=None, cy=None, orient_to_camera=True):
    """organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。

    fx,fy 指定で透視、未指定で正射。orient_to_camera=True で法線をカメラ(原点)向きに符号統一。

    法線は隣接画素の外積で出すため両軸に近傍が要る。H<2 or W<2 は第2の接線方向が無く
    法線が定義できない(その軸の勾配を 0 とみなすと cross(dPx,0)=[0,0,0] の縮退法線を
    静かに返してしまう)。fail-closed で明示的に ValueError 拒否する。
    """
    d = np.asarray(depth, float)
    if d.ndim != 2:
        raise ValueError(f"normals_from_depth expects a 2D depth image, got shape {d.shape}")
    H, W = d.shape
    if H < 2 or W < 2:
        raise ValueError(
            f"normals_from_depth requires a depth image of at least 2x2 to estimate "
            f"surface normals via neighbor cross-products; got {H}x{W}. A single "
            f"row/column has no second tangent direction, so the normal is undefined."
        )
    P = depth_to_organized_points(d, fx, fy, cx, cy)
    dPy, dPx = np.gradient(P, axis=0), np.gradient(P, axis=1)  # (H,W,3) each
    n = np.cross(dPx, dPy)
    nrm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / (nrm + 1e-12)
    if orient_to_camera:
        # 視線 = 点→カメラ(原点)= -P。n·(-P) < 0 の画素を反転して視点向きに揃える。
        view = -P
        flip = np.sum(n * view, axis=-1) < 0
        n[flip] = -n[flip]
    return n.astype(np.float32)


def occlusion_edges(depth, rel_thresh=0.05):
    """深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。

    遮蔽エッジは深度の**不連続(step)**であって傾斜(slope)ではない。一様な傾斜面は
    連続で遮蔽を含まないため flag してはならない。一階勾配(=深度/画素)は傾斜そのもので、
    段差か斜面かを区別できない(かつ絶対深度の割合と比較するのは次元不整合)。

    そこで軸ごとの**二階差分(離散ラプラシアン相当)** ``d[i+1]-2*d[i]+d[i-1]`` を使う。
    一様傾斜(深度が近傍で線形)なら二階差分 ≈ 0、fronto-parallel な段差では両側で大きな値。
    これを局所深度で正規化した相対的な深度ジャンプが rel_thresh を超える画素を境界とする。
    """
    d = np.asarray(depth, float)
    if d.ndim != 2:
        raise ValueError(f"occlusion_edges expects a 2D depth image, got shape {d.shape}")
    # 軸ごとの二階差分。境界は中心差分が取れないので 0(=傾斜/平坦なら非エッジ)。
    lap_y = np.zeros_like(d)
    lap_x = np.zeros_like(d)
    lap_y[1:-1, :] = d[2:, :] - 2.0 * d[1:-1, :] + d[:-2, :]
    lap_x[:, 1:-1] = d[:, 2:] - 2.0 * d[:, 1:-1] + d[:, :-2]
    # いずれかの軸方向の不連続を拾う(和にすると角で符号相殺し得るため軸別の絶対値の最大)。
    jump = np.maximum(np.abs(lap_x), np.abs(lap_y))
    # 局所深度で正規化(相対的な深度ジャンプ)。無効/ゼロ深度は中央値でフォールバック。
    valid = np.isfinite(d) & (d > 0)
    med = np.median(d[valid]) if np.any(valid) else 1.0
    denom = np.where(valid & (np.abs(d) > 1e-12), np.abs(d), med)
    rel_jump = jump / denom
    return np.isfinite(rel_jump) & (rel_jump > rel_thresh)


def bearing_angle_image(depth, direction="down"):
    """bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。

    隣接深度差から局所傾斜角 atan2(Δdepth, step) を計算。斜面の向きに敏感で照明不変。
    direction ∈ {down,up,right,left}。
    """
    d = np.asarray(depth, float)
    if direction in ("down", "up"):
        diff = np.gradient(d, axis=0)
    else:
        diff = np.gradient(d, axis=1)
    if direction in ("up", "left"):
        diff = -diff
    ba = np.degrees(np.arctan2(diff, 1.0))
    return ba.astype(np.float32)


def valid_mask(depth, min_depth=1e-6):
    """有効深度マスク(0/NaN/負を除外)。→ bool HxW。"""
    d = np.asarray(depth, float)
    return np.isfinite(d) & (d > min_depth)
