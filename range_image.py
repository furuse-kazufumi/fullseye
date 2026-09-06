# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
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

    ``u`` は列番号 (0..W-1)、``v`` は行番号 (0..H-1)。``fx``・``fy`` は画素単位の焦点距離、
    ``cx``・``cy`` は主点で、省略時は画像中心 ``((W-1)/2, (H-1)/2)``。``fx`` と ``fy`` の
    どちらか一方でも None なら正射モードになり、``cx``・``cy`` は無視される。正射モードでは
    x, y が画素座標そのままなので、深度の単位(mm 等)と x, y の単位(画素)が混在する点に
    注意。透視モードでは 3 成分とも深度と同じ単位になる。深度 0 や NaN はそのまま伝播する
    (0 の画素は x=y=0 の原点に集まる)ため、無効画素の除外は呼び出し側で行う。返り値は
    float64 の ``(H,W,3)``、第 3 軸は (x, y, z) で x は右、y は下、z は奥行き(画像座標系)。
    入力検証は無く、2-D 以外は ``d.shape`` の展開で失敗する。``normals_from_depth`` は
    この関数の出力を内部で使う。
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

    計算は ``depth_to_organized_points`` で 3-D 点 ``P`` を作り、``np.gradient`` の列方向
    差分 ``dPx`` と行方向差分 ``dPy`` の外積 ``dPx × dPy`` を単位長にする(端は片側差分)。
    ``orient_to_camera=True`` では ``n·(-P) < 0`` の画素を反転し、法線が原点(カメラ)を向く
    よう揃える。正射モード(``fx`` か ``fy`` が None)では ``P=(u,v,d)`` なので原点は画像
    左上の深度 0 の位置になり、「カメラ向き」の意味が透視モードと異なる点に注意。``cx``・
    ``cy`` 省略時は画像中心。深度の段差(遮蔽エッジ)をまたぐ画素では外積が段差の向きを
    拾って法線が壊れるので、``occlusion_edges`` で境界画素を除いてから使う。深度 0 / NaN の
    画素は検証せず、法線も不定になる。返り値は float32 の ``(H,W,3)``。
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

    ``direction`` が "down"/"up" なら行方向(axis=0)、"right"/"left" なら列方向(axis=1)の
    ``np.gradient``(中心差分、端は片側差分)で隣接深度差 Δd を取り、"up"/"left" では符号を
    反転する。角度は ``degrees(atan2(Δd, 1))`` なので値域は (-90, 90) 度、平坦面で 0、走査
    方向に遠ざかる面で正。格子間隔を 1 としているため、深度の単位が画素と違う(mm 等)場合
    は幾何学的な入射角そのものではなく「深度単位あたりの傾き」の角になる。上記 4 語以外の
    ``direction`` は列方向・符号そのままとして扱われ、エラーにはならない。返り値は float32
    の ``(H,W)``。深度の段差では ±90 度近くまで振れるので遮蔽の目安にもなるが、段差と斜面
    を区別するには ``occlusion_edges`` を使う。入力検証は無い。
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
