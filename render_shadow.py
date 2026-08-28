# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""キャスト影 / ソフトシャドウ(shadow mapping + 面光源のペナンブラ)。

``render3d.render_mesh`` は depth / silhouette / normal の**幾何バッファ**を返すが、
陰影(``match3d.render_shaded`` / ``photometric.render_lambertian``)は各点の法線と光源の
内積(直接光の強さ)しか見ておらず、**別の物体に遮られて光が届かない**という大域的な
可視性=影を一切扱わない。だから床の上に置いた球は「陰(self-shadow=法線が光に背く側)」は
出ても「接地影(cast shadow=球が床に落とす影)」が出ず、物体が宙に浮いて見える。ここはその
欠けている 1 ピースだけを埋める:

    光源から見た深度(shadow map)を基準に、受光面の各点が光源との間に別の面で
    遮られているか(shadow mapping; Williams 1978)を判定して可視性 [0,1] を返す。

**既存レンダ op との差(固有価値, honest)**:
  - ``render3d.render_mesh``        … 幾何バッファ(depth/silhouette/normal)。可視性=影は無い。
  - ``match3d.render_shaded`` /
    ``photometric.render_lambertian`` … Lambertian 直接光(法線·光源)。self-shadow のみ。
                                        物体間の遮蔽(cast shadow)は扱わない。
  - ``imgio.shaded_relief``          … 高さ場の傾斜による陰影(hillshade)。3D メッシュの
                                        投影影ではない。
  - **本モジュール** … *物体間の遮蔽* を光源空間の深度比較で解く唯一の op。``cast_shadow`` の
                       出力を上の陰影画像に乗算すれば接地影つきの「映える静止 3D」になる。

原理:
  * 光源をカメラに見立て ``render_mesh`` で light-space depth(shadow map)を取る
    (ラスタライザは再発明しない — 既存の z-buffer をそのまま流用)。
  * カメラ側の depth から受光面点をワールドへ逆投影(``unproject_to_world``)し、光源空間へ
    射影して深度比較する。手前に別の面があれば影。
  * ペナンブラ(半影)= 面光源の角半径。中心光源方向のまわり ``penumbra`` の円錐内へ
    複数方向をばらまき(Fibonacci ディスク)、各方向のハード影を平均する(面光源の近似)。
    光源が大きいほど半影帯が幾何学的に広がる — カーネル幅を手で決める PCF と違い、
    半影は幾何から**創発**する。

慣習(``render3d`` に合わせる):
  * ``pose``       4x4 の object->camera 行列(``render3d.look_at``)。
  * ``intrinsics`` 3x3 ピンホール ``K``(``render3d.intrinsics_from_fov``)。
  * ``light``      (3,) ベクトル。``directional=True``(既定)なら「シーンから光源へ向かう
                   単位方向」(平行光)。``directional=False`` ならワールド座標の点光源位置。
  * 返り値の shadow は (H, W) float64 ∈ [0,1]、**1=完全に照らされる / 0=完全な影**、
                   受光面が無い背景画素は 1.0(遮る相手がいない=影ではない)。

Honest limitations:
  * shadow map は有限解像度なので、影の縁は light 解像度 ``shadow_res`` に依存する
    (バイアスは傾斜スケールで自動設定するが、極端に斜めな受光面では acne / peter-panning が
    残りうる)。透明・屈折・多重反射・カラー影は扱わない(不透明な遮蔽のみ)。
  * 平行光は「十分遠い」点として近似する(既定 40×シーン半径)。厳密な無限遠平行ではない。

Reference (public):
  * L. Williams, "Casting Curved Shadows on Curved Surfaces", SIGGRAPH 1978(shadow mapping)。
  * W. Reeves, D. Salesin, R. Cook, "Rendering Antialiased Shadows with Depth Maps",
    SIGGRAPH 1987(PCF / 複数サンプル平均)。
"""
from __future__ import annotations

import numpy as np

import render3d

__all__ = ["cast_shadow", "unproject_to_world"]

_EPS = 1e-12


def _resolve_view(V, pose, intrinsics, width: int, height: int):
    """pose / intrinsics のどちらかが None なら render3d.auto_view で補完し具体行列にする。"""
    if pose is None or intrinsics is None:
        dpose, dK = render3d.auto_view(V, margin=1.2, width=width, height=height)
    P = dpose if pose is None else np.asarray(pose, np.float64)
    K = dK if intrinsics is None else np.asarray(intrinsics, np.float64)
    if P.shape != (4, 4):
        raise ValueError("pose must be 4x4, got %r" % (P.shape,))
    if K.shape != (3, 3):
        raise ValueError("intrinsics must be 3x3, got %r" % (K.shape,))
    if not (np.all(np.isfinite(P)) and np.all(np.isfinite(K))):
        raise ValueError("pose / intrinsics contain non-finite values")
    return P, K


def unproject_to_world(depth, pose, intrinsics) -> np.ndarray:
    """深度画像 (H,W) を **ワールド座標の点群** (H,W,3) へ逆投影する。

    ``render3d.render_mesh`` の depth(camera 前方の距離、背景は非有限)と、そのときの
    ``pose`` (object->camera 4x4) / ``intrinsics`` (3x3) から各画素の 3D 位置を復元する。
    背景(非有限 depth)や光源背後(depth<=0)の画素は NaN。ピクセル中心は ``render_mesh`` と
    同じ ``+0.5`` を使う。fail-closed: 形状不正・非有限行列は ``ValueError``。"""
    d = np.asarray(depth, np.float64)
    if d.ndim != 2:
        raise ValueError("depth must be 2-D (H,W), got %r" % (d.shape,))
    P = np.asarray(pose, np.float64)
    K = np.asarray(intrinsics, np.float64)
    if P.shape != (4, 4) or K.shape != (3, 3):
        raise ValueError("pose must be 4x4 and intrinsics 3x3")
    if not (np.all(np.isfinite(P)) and np.all(np.isfinite(K))):
        raise ValueError("pose / intrinsics contain non-finite values")

    h, w = d.shape
    fx, fy, cx, cy = float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])
    if abs(fx) < _EPS or abs(fy) < _EPS:
        raise ValueError("intrinsics focal length is degenerate (fx or fy ~ 0)")

    cols = np.arange(w, dtype=np.float64) + 0.5
    rows = np.arange(h, dtype=np.float64) + 0.5
    u, v = np.meshgrid(cols, rows)                       # (H, W)

    valid = np.isfinite(d) & (d > 0.0)
    dd = np.where(valid, d, np.nan)
    # render_mesh の投影: su = fx*Xc/(-Zc)+cx, sv = cy-fy*Yc/(-Zc), depth = -Zc.
    Xc = (u - cx) * dd / fx
    Yc = -(v - cy) * dd / fy
    Zc = -dd
    Pc = np.stack([Xc, Yc, Zc], axis=-1)                 # (H, W, 3) camera space

    R = P[:3, :3]
    t = P[:3, 3]
    # Vc = R @ Vw + t  ->  Vw = R^T (Vc - t) ; 行ベクトルでは (Vc - t) @ R
    Pw = (Pc - t) @ R
    Pw[~valid] = np.nan
    return Pw


def _light_camera(center, radius, ldir_or_pos, directional: bool, shadow_res: int,
                  margin: float = 1.3):
    """光源を「シーンを枠に収めるカメラ」として pose / K / 光源方向 / 距離を作る。"""
    center = np.asarray(center, np.float64).reshape(3)
    if directional:
        ldir = np.asarray(ldir_or_pos, np.float64).reshape(3)
        n = np.linalg.norm(ldir)
        if not np.isfinite(n) or n < _EPS:
            raise ValueError("light direction must be finite and non-zero")
        ldir = ldir / n
        dist = 40.0 * radius                             # 平行光近似(十分遠い点)
        eye = center + ldir * dist
    else:
        eye = np.asarray(ldir_or_pos, np.float64).reshape(3)
        if not np.all(np.isfinite(eye)):
            raise ValueError("light position must be finite")
        v = center - eye
        dist = float(np.linalg.norm(v))
        if dist < _EPS:
            raise ValueError("point light coincides with the scene centre")
        ldir = -v / dist                                  # シーンから光源へ向かう方向
    # look_at の up は視線と平行だと退化する。世界 up が視線とほぼ平行なら別軸に逃がす。
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(ldir @ up)) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    pose = render3d.look_at(eye, center, up=up)
    fov = 2.0 * np.degrees(np.arctan((radius * margin) / max(dist, _EPS)))
    fov = float(np.clip(fov, 1e-2, 179.0))
    K = render3d.intrinsics_from_fov(fov, shadow_res, shadow_res)
    return pose, K, ldir, dist


def _sample_dirs(ldir, penumbra_rad: float, samples: int):
    """中心方向 ldir のまわり、角半径 penumbra_rad の円錐内へ Fibonacci ディスクで方向をばらまく。"""
    if penumbra_rad <= 0.0 or samples <= 1:
        return ldir.reshape(1, 3)
    # ldir に直交する正規直交基底 (t1, t2)
    a = np.array([1.0, 0.0, 0.0]) if abs(ldir[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    t1 = np.cross(ldir, a)
    t1 = t1 / max(np.linalg.norm(t1), _EPS)
    t2 = np.cross(ldir, t1)
    i = np.arange(samples, dtype=np.float64) + 0.5
    r = np.sqrt(i / samples) * np.tan(penumbra_rad)      # ディスク半径 = tan(角半径)
    theta = i * np.pi * (3.0 - np.sqrt(5.0))             # 黄金角
    dx = r * np.cos(theta)
    dy = r * np.sin(theta)
    dirs = ldir[None, :] + dx[:, None] * t1[None, :] + dy[:, None] * t2[None, :]
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    return dirs


def cast_shadow(V, F, light, *, pose=None, intrinsics=None, width: int = 256,
                height: int = 256, directional: bool = True, penumbra: float = 0.0,
                samples: int = 16, shadow_res: int = 512, bias=None) -> np.ndarray:
    """メッシュのキャスト影 / ソフトシャドウを計算し、可視性マップ (H,W) ∈ [0,1] を返す。

    ``1=完全に照らされる`` / ``0=完全な影``。受光面が無い背景画素は ``1.0``。

    引数:
      * ``V, F``        頂点 (N,3) と三角形 (M,3)。空メッシュは影を落とせないので拒否。
      * ``light``       (3,) ベクトル。``directional=True`` なら平行光の方向(シーン→光源)、
                        ``False`` なら点光源のワールド位置。
      * ``pose``/``intrinsics`` カメラ。省略時は ``render3d.auto_view`` で補完。
      * ``penumbra``    面光源の**角半径(度)**。0 でハード影、増やすほど半影が広がる。
      * ``samples``     半影サンプル数(``penumbra>0`` のときのみ使用、Fibonacci ディスク)。
      * ``shadow_res``  shadow map の一辺解像度。
      * ``bias``        影判定の深度バイアス(ワールド単位)。``None`` なら texel サイズと
                        傾斜から自動設定(acne / peter-panning を抑制)。

    手法は shadow mapping(Williams 1978): 光源から ``render_mesh`` で深度を取り、カメラ側の
    受光面点を光源空間へ射影して深度比較する。fail-closed: 退化メッシュ・不正光源・非正の
    サイズ/解像度は ``ValueError``。"""
    Vv = np.asarray(V, np.float64)
    Ff = np.asarray(F, np.int64)
    if Vv.ndim != 2 or Vv.shape[1] != 3:
        raise ValueError("V must be (N,3), got %r" % (Vv.shape,))
    if Ff.ndim != 2 or Ff.shape[1] != 3:
        raise ValueError("F must be (M,3), got %r" % (Ff.shape,))
    if Ff.shape[0] == 0:
        raise ValueError("empty face set: nothing can cast a shadow")
    if Ff.min() < 0 or Ff.max() >= Vv.shape[0]:
        raise ValueError("face index out of range (degenerate mesh)")
    if not np.all(np.isfinite(Vv)):
        raise ValueError("V contains non-finite coordinates")
    w = int(width)
    h = int(height)
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive, got %dx%d" % (w, h))
    sres = int(shadow_res)
    if sres <= 1:
        raise ValueError("shadow_res must be > 1, got %d" % (sres,))
    pen = float(penumbra)
    if not np.isfinite(pen) or pen < 0.0:
        raise ValueError("penumbra must be finite and >= 0 (degrees), got %r" % (penumbra,))
    ns = int(samples)
    if ns < 1:
        raise ValueError("samples must be >= 1, got %d" % (samples,))

    light = np.asarray(light, np.float64).reshape(-1)
    if light.size != 3 or not np.all(np.isfinite(light)):
        raise ValueError("light must be a finite length-3 vector")

    pose, K = _resolve_view(Vv, pose, intrinsics, w, h)

    # --- カメラ側: 受光面点(ワールド)と法線(ワールド)を用意 ---
    view = render3d.render_mesh(Vv, Ff, pose=pose, intrinsics=K, width=w, height=h)
    depth = view["depth"]
    n_cam = view["normals"]                              # camera space, 空は 0 ベクトル
    Pw = unproject_to_world(depth, pose, K)              # (H,W,3), 背景は NaN
    surf = np.all(np.isfinite(Pw), axis=-1)             # 受光面がある画素
    n_world = n_cam @ pose[:3, :3]                       # camera->world: n_row @ R

    # --- シーン範囲と光源カメラ ---
    lo, hi = Vv.min(axis=0), Vv.max(axis=0)
    center = 0.5 * (lo + hi)
    radius = float(np.linalg.norm(Vv - center, axis=1).max())
    if not np.isfinite(radius) or radius <= 0.0:
        raise ValueError("mesh has zero spatial extent")

    # 中心光源方向(バイアスの傾斜スケールと半影の中心軸に使う)
    if directional:
        ldir_c = light / max(np.linalg.norm(light), _EPS)
    else:
        v = center - light
        nv = float(np.linalg.norm(v))
        if nv < _EPS:
            raise ValueError("point light coincides with the scene centre")
        ldir_c = -v / nv

    # texel のワールドサイズ(平行光近似の枠から)と傾斜スケールのバイアス。
    # 光源カメラの縦視野は fov=2*atan(radius*margin/dist) なので枠の縦幅は
    # 2*dist*tan(fov/2) = 2*radius*margin。texel = それ / shadow_res。
    margin_L = 1.3
    texel_world = 2.0 * radius * margin_L / sres
    if bias is None:
        # 傾斜(法線と光の角)に比例して増やす。受光面が斜めなほど texel 内の深度変化が大きい。
        ndl = np.abs(np.einsum("ijk,k->ij", n_world, ldir_c))
        ndl = np.clip(ndl, 1e-3, 1.0)
        slope = np.sqrt(np.clip(1.0 - ndl * ndl, 0.0, 1.0)) / ndl   # tan(角)
        bias_world = texel_world * (1.5 + 2.5 * np.clip(slope, 0.0, 12.0))
    else:
        b = float(bias)
        if not np.isfinite(b) or b < 0.0:
            raise ValueError("bias must be finite and >= 0")
        bias_world = np.full((h, w), b, np.float64)

    # --- 光源方向をサンプルして各ハード影を平均(面光源=半影) ---
    dirs = _sample_dirs(ldir_c, np.deg2rad(pen), ns)

    occ_count = np.zeros((h, w), np.float64)
    n_used = 0
    for k in range(dirs.shape[0]):
        d_k = dirs[k]
        if directional:
            light_k = d_k                                # 方向そのもの
        else:
            # 点光源: 中心位置を円錐に対応する円盤上へずらす(面光源近似)
            offset = (d_k - ldir_c)
            light_k = np.asarray(light, np.float64) - offset * dist_c
        Lpose, LK, _, _ = _light_camera(center, radius, light_k, directional, sres)
        lview = render3d.render_mesh(Vv, Ff, pose=Lpose, intrinsics=LK,
                                     width=sres, height=sres)
        sm = lview["depth"]                              # 光源から見た最近面(背景 inf)

        R_L = Lpose[:3, :3]
        t_L = Lpose[:3, 3]
        fx, fy = float(LK[0, 0]), float(LK[1, 1])
        cx, cy = float(LK[0, 2]), float(LK[1, 2])

        Pc = (Pw.reshape(-1, 3) @ R_L.T + t_L).reshape(h, w, 3)
        dL = -Pc[..., 2]
        front = surf & (dL > _EPS)
        dsafe = np.where(front, dL, np.nan)
        uL = fx * (Pc[..., 0] / dsafe) + cx
        vL = cy - fy * (Pc[..., 1] / dsafe)
        iu = np.floor(uL).astype(np.int64)
        iv = np.floor(vL).astype(np.int64)
        inb = front & (iu >= 0) & (iu < sres) & (iv >= 0) & (iv < sres)
        iu_c = np.clip(iu, 0, sres - 1)
        iv_c = np.clip(iv, 0, sres - 1)
        sm_d = sm[iv_c, iu_c]                            # 光源空間の最近面深度
        blocked = inb & np.isfinite(sm_d) & (sm_d < (dL - bias_world))
        occ_count += blocked.astype(np.float64)
        n_used += 1

    occ_frac = occ_count / max(n_used, 1)
    shadow = 1.0 - occ_frac                              # 1=lit, 0=shadow
    shadow[~surf] = 1.0                                  # 背景は影ではない
    return np.clip(shadow, 0.0, 1.0)
