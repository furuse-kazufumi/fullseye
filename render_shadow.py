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

__all__ = ["cast_shadow", "unproject_to_world", "shadow_raycast"]

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
    背景(非有限 depth)や光源背後(depth<=0)の画素は NaN。fail-closed: 形状不正・
    非有限行列は ``ValueError``。

    ピクセル中心は ``camera`` / ``render3d`` と同じ **整数**(画素 ``(r, c)`` の中心が
    連続座標 ``(u, v) = (c, r)``)。2026-09-02 まではここだけが ``+0.5`` を足しており、
    しかも docstring は「``render_mesh`` と同じ ``+0.5``」と**逆のことを書いていた**
    ―― ``render_mesh`` は 0.5 を足さないと明記している側である。

    症状は「半画素ずれる」では済まない。逆投影の誤差は**深度に比例**するので、
    実測(96x96・画角 40 度・距離 ~5)では地面の画素が真の平面から
    **1.3e-2 〜 3.4e-2 ずれ、一部は平面より下に落ちていた**。そのため
    ``examples_3d/render_beauty.py`` の接地影の検査は「地面の画素が 1 つも無い」と
    判定して失敗し続けており、**記事の hero 画像は検証つきでは再生成できない状態**
    だった。:func:`cast_shadow` もここで得た世界座標を光源カメラへ投げ直すので、
    影の参照そのものが同じだけずれていた。"""
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

    cols = np.arange(w, dtype=np.float64)        # 画素中心 = 整数(0.5 を足さない)
    rows = np.arange(h, dtype=np.float64)
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
                samples: int = 16, shadow_res: int = 512, bias=None,
                pcf: int = 0) -> np.ndarray:
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
      * ``pcf``         shadow map を引くときに混ぜる近傍の**半径 [texel]**。
                        ``0``(既定)は最近傍 1 点 = 従来どおり。``1`` なら 3x3 の
                        **判定を平均**する(深度を平均するのではない —— 深度の平均は
                        手前と奥をならして存在しない面を作る)。境目が texel に
                        量子化されて階段になるのを、shadow map を上げずに緩和する。

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
    pcf_r = int(pcf)
    if pcf_r < 0 or pcf_r > 8:
        raise ValueError("pcf must be a texel radius in [0, 8], got %r" % (pcf,))

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
        dist_c = nv                                   # 光源→中心の距離(点光源の面光源近似で使う)

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
            # 点光源(面光源近似): 光源を「中心→光源」軸まわりの角半径 penumbra の円錐に沿って
            # 光源距離 dist_c の球帽上へばらまく。penumbra=0 では d_k=ldir_c なので light_k=light
            # (元の点光源)に戻る。dist_c は上の else 分岐で光源→中心距離として定義済み。
            light_k = center + d_k * dist_c
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
        with np.errstate(invalid="ignore", divide="ignore"):
            dsafe = np.where(front, dL, np.nan)
            uL = fx * (Pc[..., 0] / dsafe) + cx
            vL = cy - fy * (Pc[..., 1] / dsafe)
            # NaN(非受光/光源背後)は下の inb マスクで捨てるので、cast 前に有限値へ置換。
            iu = np.floor(np.where(np.isfinite(uL), uL, -1.0)).astype(np.int64)
            iv = np.floor(np.where(np.isfinite(vL), vL, -1.0)).astype(np.int64)
        inb = front & (iu >= 0) & (iu < sres) & (iv >= 0) & (iv < sres)
        if pcf_r == 0:
            iu_c = np.clip(iu, 0, sres - 1)
            iv_c = np.clip(iv, 0, sres - 1)
            sm_d = sm[iv_c, iu_c]                        # 光源空間の最近面深度
            blocked = (inb & np.isfinite(sm_d)
                       & (sm_d < (dL - bias_world))).astype(np.float64)
        else:
            # PCF: 1 点の最近傍判定だと、影の境目が shadow map の texel に量子化
            # されて階段になる。近傍 (2r+1)^2 texel の**判定を平均**すると、
            # texel より細かい階調が出る(深度を平均するのではない —— 深度の
            # 平均は物体の手前と奥をならして存在しない面を作る)。
            acc = np.zeros_like(dL, dtype=np.float64)
            for du in range(-pcf_r, pcf_r + 1):
                for dv in range(-pcf_r, pcf_r + 1):
                    uu = np.clip(iu + du, 0, sres - 1)
                    vv = np.clip(iv + dv, 0, sres - 1)
                    d_t = sm[vv, uu]
                    acc += (np.isfinite(d_t) & (d_t < (dL - bias_world))).astype(np.float64)
            blocked = inb.astype(np.float64) * (acc / float((2 * pcf_r + 1) ** 2))
        occ_count += blocked
        n_used += 1

    occ_frac = occ_count / max(n_used, 1)
    shadow = 1.0 - occ_frac                              # 1=lit, 0=shadow
    shadow[~surf] = 1.0                                  # 背景は影ではない
    return np.clip(shadow, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# レイキャスト影(太陽の視直径つき、shadow map を使わない厳密な可視性)          #
# --------------------------------------------------------------------------- #
# shadow map(上の cast_shadow)は texel 量子化の階段・バイアス由来の acne /
# peter-panning・解像度依存が構造的に残る。ここでは受光面の各画素からメッシュへ
# 直接レイを飛ばし、Möller-Trumbore で三角形と交差判定する。加速は「光源方向に
# 直交する平面へ全三角形を射影し 2-D 格子に入れる」方式: 平行光ではレイは全部
# 平行なので、各レイは 1 セルの三角形だけ調べれば良い(光源空間の 2-D binning)。
# 太陽の視直径(0.53°)は方向を円盤内でばらまいて平均する = 半影の幅は幾何どおり
# 「遮蔽物までの距離 × tan(視直径/2)」になる(テストで固定)。
_GRID_MAX = 512
#: (ray, triangle) ペアを一度にメモリへ展開する上限(``_occluded_parallel``)。
_PAIR_CHUNK = 2_000_000


def auto_grid(n_faces: int) -> int:
    """面数に応じた光源空間 2-D 格子の一辺セル数(1 セルあたり ~6 面が目安、[16, 512])。"""
    return int(np.clip(int(np.sqrt(max(int(n_faces), 1) / 6.0)), 16, _GRID_MAX))


def _rays_hit_dir(O: np.ndarray, d: np.ndarray, A: np.ndarray, e1: np.ndarray,
                  e2: np.ndarray, tmin: float, tmax: float = np.inf) -> np.ndarray:
    """原点群 ``O`` (K,3) から共通方向 ``d`` のレイが三角形群 (M,3) のどれかに ``t∈(tmin,tmax)`` で当たるか (K,) bool。"""
    pvec = np.cross(d[None, :], e2)                          # (M,3)
    det = np.einsum("md,md->m", e1, pvec)                    # (M,)
    nz = np.abs(det) > 1e-14
    inv = np.zeros_like(det)
    inv[nz] = 1.0 / det[nz]
    tvec = O[:, None, :] - A[None, :, :]                     # (K,M,3)
    u = np.einsum("kmd,md->km", tvec, pvec) * inv[None, :]
    qvec = np.cross(tvec, e1[None, :, :])                    # (K,M,3)
    v = np.einsum("kmd,d->km", qvec, d) * inv[None, :]
    t = np.einsum("kmd,md->km", qvec, e2) * inv[None, :]
    hit = (nz[None, :] & (u >= -1e-9) & (u <= 1.0 + 1e-9) & (v >= -1e-9)
           & (u + v <= 1.0 + 1e-9) & (t > tmin) & (t < tmax))
    return hit.any(axis=1)


def _occluded_parallel(O: np.ndarray, d: np.ndarray, A: np.ndarray, B: np.ndarray,
                       C: np.ndarray, tmin: float, grid: int,
                       tmax: float = np.inf) -> np.ndarray:
    """平行光方向 ``d`` について原点群 ``O`` (K,3) が遮蔽されるか (K,) bool(2-D 格子加速)。"""
    K = O.shape[0]
    if K == 0:
        return np.zeros(0, bool)
    a = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    t1 = np.cross(d, a)
    t1 /= max(np.linalg.norm(t1), _EPS)
    t2 = np.cross(d, t1)
    # 三角形の 2-D 射影と格子
    P2 = np.stack([np.stack([A @ t1, A @ t2], 1), np.stack([B @ t1, B @ t2], 1),
                   np.stack([C @ t1, C @ t2], 1)], axis=1)   # (M,3,2)
    lo = P2.min(axis=(0, 1))
    hi = P2.max(axis=(0, 1))
    span = np.maximum(hi - lo, 1e-12)
    G = int(grid)
    cell = span / G
    tmin2 = P2.min(axis=1)
    tmax2 = P2.max(axis=1)
    c0 = np.clip(np.floor((tmin2 - lo) / cell).astype(np.int64), 0, G - 1)   # (M,2)
    c1 = np.clip(np.floor((tmax2 - lo) / cell).astype(np.int64), 0, G - 1)
    nx = c1[:, 0] - c0[:, 0] + 1
    ny = c1[:, 1] - c0[:, 1] + 1
    counts = nx * ny
    total = int(counts.sum())
    tri_id = np.repeat(np.arange(A.shape[0]), counts)
    offs = np.repeat(np.cumsum(counts) - counts, counts)
    k = np.arange(total) - offs
    ny_r = np.repeat(ny, counts)
    ix = k // ny_r
    iy = k % ny_r
    cell_t = (np.repeat(c0[:, 0], counts) + ix) * G + (np.repeat(c0[:, 1], counts) + iy)
    order_t = np.argsort(cell_t, kind="stable")
    cell_t = cell_t[order_t]
    tri_id = tri_id[order_t]
    t_start = np.searchsorted(cell_t, np.arange(G * G + 1))
    # レイの 2-D 位置と格子
    O2 = np.stack([O @ t1, O @ t2], 1)
    cr = np.floor((O2 - lo) / cell).astype(np.int64)
    inside = (cr[:, 0] >= 0) & (cr[:, 0] < G) & (cr[:, 1] >= 0) & (cr[:, 1] < G)
    occ = np.zeros(K, bool)
    ray_idx = np.nonzero(inside)[0]
    if ray_idx.size == 0:
        return occ
    cell_r = cr[ray_idx, 0] * G + cr[ray_idx, 1]
    # ---- (ray, triangle) ペアの一括判定(2026-09-03) ---------------------------
    # 以前はセルごとに Python ループで ``_rays_hit_dir``(K×M の総当たり)を回して
    # いた。格子を細かくするほどセル数 = ループ回数が増えるので、100 万面の細分
    # メッシュでは格子を細かくできず(64² で 1 セル 250 面)、逆に 1 方向 20 秒近く
    # かかった。ここでは各レイに「そのセルの三角形リスト」を展開した平坦な
    # (ray, tri) ペア列を作り、Möller-Trumbore をペア全体に一括適用する(ペア数で
    # チャンク)。Python ループはチャンク数だけ。結果は同じ(交差判定は同式)。
    n_per_ray = t_start[cell_r + 1] - t_start[cell_r]
    keep_r = n_per_ray > 0
    ray_idx = ray_idx[keep_r]
    cell_r = cell_r[keep_r]
    n_per_ray = n_per_ray[keep_r]
    if ray_idx.size == 0:
        return occ
    e1_all = B - A
    e2_all = C - A
    pvec_all = np.cross(d[None, :], e2_all)                  # (M,3)
    det_all = np.einsum("md,md->m", e1_all, pvec_all)
    nz_all = np.abs(det_all) > 1e-14
    inv_all = np.zeros_like(det_all)
    inv_all[nz_all] = 1.0 / det_all[nz_all]
    cum = np.cumsum(n_per_ray)
    start = 0
    n_r = ray_idx.size
    while start < n_r:
        base = cum[start - 1] if start > 0 else 0
        end = int(np.searchsorted(cum, base + _PAIR_CHUNK, side="right"))
        end = min(max(end, start + 1), n_r)
        cnt = n_per_ray[start:end]
        total = int(cnt.sum())
        rr = np.repeat(ray_idx[start:end], cnt)
        offs = np.repeat(np.cumsum(cnt) - cnt, cnt)
        k = np.arange(total, dtype=np.int64) - offs
        tt = tri_id[np.repeat(t_start[cell_r[start:end]], cnt) + k]
        Op = O[rr]
        tvec = Op - A[tt]
        inv = inv_all[tt]
        u = np.einsum("kd,kd->k", tvec, pvec_all[tt]) * inv
        qvec = np.cross(tvec, e1_all[tt])
        v = np.einsum("kd,d->k", qvec, d) * inv
        t = np.einsum("kd,kd->k", qvec, e2_all[tt]) * inv
        hit = (nz_all[tt] & (u >= -1e-9) & (u <= 1.0 + 1e-9) & (v >= -1e-9)
               & (u + v <= 1.0 + 1e-9) & (t > tmin) & (t < tmax))
        if hit.any():
            occ[rr[hit]] = True
        start = end
    return occ


def shadow_raycast(V, F, light, *, pose=None, intrinsics=None, width: int = 256,
                   height: int = 256, angular_diameter_deg: float = 0.0,
                   samples: int = 1, grid=None, bias=None) -> np.ndarray:
    """メッシュへ直接レイを飛ばして太陽光の可視性 (H,W) ∈ [0,1] を返す(shadow map 不使用)。

    ``1=完全に照らされる`` / ``0=完全な影``。背景画素は 1.0。``light`` は平行光の方向
    (シーン→太陽)。``angular_diameter_deg`` は光源の視直径(太陽 = 0.53°)で、0 なら
    ハード影、正なら角半径の円盤内へ ``samples`` 方向をばらまいて平均する ―― 半影の幅は
    「遮蔽物までの距離 × tan(視直径/2)」の幾何どおり(小惑星スケールでは数 cm = 硬い影)。
    法線が光に背く画素(自己陰)は 0。``bias`` はレイ原点を法線方向へ浮かせる量(既定 =
    シーン対角 × 1e-5、自己交差の回避)。``grid`` は光源空間の 2-D 格子の一辺セル数
    (既定 ``None`` = 面数から :func:`auto_grid`。結果は格子に依らず同じ、速度だけ変わる)。

    honest: 交差は Möller-Trumbore(両面)、加速は 2-D binning(平行光専用。点光源は
    ``cast_shadow`` を使う)。透明・多重反射・カラー影は扱わない。
    fail-closed: 退化メッシュ・不正光源・非正サイズ・負の視直径/サンプル数は ``ValueError``。"""
    Vv = np.asarray(V, np.float64)
    Ff = np.asarray(F, np.int64)
    if Vv.ndim != 2 or Vv.shape[1] != 3:
        raise ValueError("V must be (N,3), got %r" % (Vv.shape,))
    if Ff.ndim != 2 or Ff.shape[1] != 3 or Ff.shape[0] == 0:
        raise ValueError("F must be a non-empty (M,3) array")
    if Ff.min() < 0 or Ff.max() >= Vv.shape[0]:
        raise ValueError("face index out of range (degenerate mesh)")
    if not np.all(np.isfinite(Vv)):
        raise ValueError("V contains non-finite coordinates")
    w, h = int(width), int(height)
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive, got %dx%d" % (w, h))
    diam = float(angular_diameter_deg)
    if not np.isfinite(diam) or diam < 0.0 or diam >= 180.0:
        raise ValueError("angular_diameter_deg must be in [0, 180), got %r" % (angular_diameter_deg,))
    ns = int(samples)
    if ns < 1:
        raise ValueError("samples must be >= 1, got %d" % (samples,))
    G = auto_grid(Ff.shape[0]) if grid is None else int(grid)
    if G < 1 or G > _GRID_MAX:
        raise ValueError("grid must be in [1, %d], got %r" % (_GRID_MAX, grid))
    light = np.asarray(light, np.float64).reshape(-1)
    if light.size != 3 or not np.all(np.isfinite(light)) or np.linalg.norm(light) < _EPS:
        raise ValueError("light must be a finite non-zero length-3 vector")
    ldir = light / np.linalg.norm(light)

    pose, K = _resolve_view(Vv, pose, intrinsics, w, h)
    view = render3d.render_mesh(Vv, Ff, pose=pose, intrinsics=K, width=w, height=h)
    Pw = unproject_to_world(view["depth"], pose, K)
    surf = np.all(np.isfinite(Pw), axis=-1)
    n_world = view["normals"] @ pose[:3, :3]
    scale = float(np.linalg.norm(Vv.max(axis=0) - Vv.min(axis=0)))
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("mesh has zero spatial extent")
    if bias is None:
        eps = 1e-5 * scale
    else:
        eps = float(bias)
        if not np.isfinite(eps) or eps < 0.0:
            raise ValueError("bias must be finite and >= 0")

    ys, xs = np.nonzero(surf)
    P0 = Pw[ys, xs]
    N0 = n_world[ys, xs]
    O = P0 + N0 * eps
    A, B, C = Vv[Ff[:, 0]], Vv[Ff[:, 1]], Vv[Ff[:, 2]]
    dirs = _sample_dirs(ldir, np.deg2rad(diam / 2.0), ns)
    occ = np.zeros(P0.shape[0], np.float64)
    for k in range(dirs.shape[0]):
        d = dirs[k]
        facing = (N0 @ d) > 0.0
        blocked = ~facing                                # 光に背く面は自己陰
        idx = np.nonzero(facing)[0]
        if idx.size:
            blocked[idx] = _occluded_parallel(O[idx], d, A, B, C, eps, G)
        occ += blocked
    vis = np.ones((h, w), np.float64)
    vis[ys, xs] = 1.0 - occ / dirs.shape[0]
    return np.clip(vis, 0.0, 1.0)
