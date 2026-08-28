# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""render_beauty — 「映える静止 3D」の総仕上げ(hero レンダラ)。

これまで個別に実装してきたレンダリング品質層 —— ラスタライズ(``render3d``)/ 鏡面陰影
(``render_shade``)/ アンビエントオクルージョン(``render_ao``)/ 接地影(``render_shadow``)/
スーパーサンプリング(``render_ssaa``)/ トーンマッピング(``render_tonemap``)—— を **1 本の
パイプラインに合成**し、メッシュを渡すだけで「科学館の台座に載った作品写真」のような 1 枚を
返す capstone op。各層は既に単体で検証済みなので、本モジュールは **再発明せず合成するだけ**。

パイプライン(``size*ss`` の高解像度でレンダ → 最後に ``antialias`` で ``size`` へ area 縮小):

  1. ``pose``/``intrinsics`` 未指定なら ``render3d.auto_view`` がメッシュを枠に収める。
  2. ``ground_shadow`` のとき、メッシュ真下に地面平面(quad 2 三角形)を足して同一シーンに合成
     (z バッファがオクルージョンとシルエットを解決 —— これで「台座に載る」見えになる)。
  3. ``render3d.render_mesh`` で depth / silhouette / 面法線を得る(高解像度)。
  4. 陰影: ``material='matcap'`` は ``render_shade.matcap_shade``、それ以外は ``render_shade.phong_shade``
     を ``clip=False``(HDR)で拡散ローブ・鏡面ローブに分けて評価し、素材ごとの反射色で合成。
     ``metal`` は鏡面を強く / 反射色を albedo 寄りに、``plastic`` は白いハイライト。
  5. ``ao=True``: ``render_ao.ambient_occlusion`` を環境光 + 拡散項へ乗算(凹部・接触が落ちる)。
  6. ``ground_shadow=True``: ``render_shadow.cast_shadow`` の可視性を直接光(拡散 + 鏡面)へ乗算
     (地面のメッシュ直下が暗くなる接地影)。環境光は影に残す(空光は遮蔽されない物理に合わせる)。
  7. シルエット外は ``background`` で合成、``tonemap``(none 以外)で HDR→[0,1]。
  8. ``render_ssaa.antialias`` で ``size`` へ area-downsample。

**決定的**: 乱数を使わない(``vertex_occlusion`` はフィボナッチ半球、``cast_shadow`` は
フィボナッチディスク、いずれも決定的)。同一入力は同一画素を返す。

honest な前提(証明していない能力は主張しない):
  * 面法線は ``render_mesh`` 由来の **フラット(面ごと)** —— 曲面はファセットが出る(SSAA と
    トーンマップで緩和されるが除去はしない)。鏡面ローブは経験的 ``cos^n``(GGX 等の物理ベース
    ではない)。AO・影は各下位 op の限界(モンテカルロ分散 / shadow map 解像度)をそのまま継ぐ。
  * 地面は水平パッチで、接地影と接地 AO を担う簡易ステージ。大域照明(相互反射)は無い。

numpy + scipy のみ(下位 op 経由)。fail-closed: メッシュ形状 / 非有限 / 空 / ``ss<1`` /
不正 ``material`` / 不正 ``tonemap`` / 不正な色・光・露出は ``ValueError``。
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

import render3d
import render_ao
import render_shade
import render_shadow
import render_ssaa
import render_tonemap

__all__ = ["render_beauty"]

#: 対応マテリアルのプリセット(拡散 / 鏡面 / 光沢 / 金属フラグ)。
_MATERIALS: dict[str, dict] = {
    # 誘電体(プラスチック): 拡散が主・ハイライトは白・中程度の光沢。
    "plastic": {"diffuse": 0.85, "specular": 0.45, "shininess": 32.0, "metal": False},
    # 金属: 拡散を抑え・鏡面を強く・ハイライトは素材色(albedo)で色付く・鋭い光沢。
    "metal": {"diffuse": 0.22, "specular": 0.95, "shininess": 90.0, "metal": True},
}
_TONEMAPS = ("reinhard", "aces", "none")

#: 地面(pedestal)の反射率と質感(ややマットな中間グレー)。
_GROUND_ALBEDO = np.array([0.55, 0.56, 0.58], np.float64)
_GROUND_SPECULAR = 0.06
_GROUND_SHININESS = 16.0


# --------------------------------------------------------------------------- #
# fail-closed 入力検証                                                          #
# --------------------------------------------------------------------------- #
def _validate_mesh(V, F) -> tuple[np.ndarray, np.ndarray]:
    """``(V, F)`` を float64 (N,3) 頂点 + int64 (M,3) 面へ検証。fail-closed。"""
    Vv = np.asarray(V, np.float64)
    if Vv.ndim != 2 or Vv.shape[1] != 3:
        raise ValueError(f"V must be (N, 3), got shape {Vv.shape}")
    if Vv.shape[0] == 0:
        raise ValueError("mesh has no vertices")
    if not np.isfinite(Vv).all():
        raise ValueError("V contains non-finite values")
    Ff = np.asarray(F)
    if Ff.ndim != 2 or Ff.shape[1] != 3:
        raise ValueError(f"F must be (M, 3) triangles, got shape {Ff.shape}")
    Ff = Ff.astype(np.int64)
    if Ff.shape[0] == 0:
        raise ValueError("mesh has no faces")
    lo, hi = int(Ff.min()), int(Ff.max())
    if lo < 0 or hi >= Vv.shape[0]:
        raise ValueError(f"face index {hi if hi >= Vv.shape[0] else lo} "
                         f"out of range for {Vv.shape[0]} vertices")
    return Vv, Ff


def _as_color(x, name: str) -> np.ndarray:
    """長さ 3 の色/反射率を [0, ∞) の float64 (3,) へ検証(有限・非負)。fail-closed。"""
    c = np.asarray(x, np.float64).reshape(-1)
    if c.shape != (3,):
        raise ValueError(f"{name} must be a length-3 RGB triple, got shape {c.shape}")
    if not np.isfinite(c).all():
        raise ValueError(f"{name} contains non-finite values")
    if np.any(c < 0.0):
        raise ValueError(f"{name} must be non-negative, got {x!r}")
    return c


def _as_light(x) -> np.ndarray:
    """光源方向(シーン→光源)を単位化した float64 (3,) へ検証。fail-closed。"""
    d = np.asarray(x, np.float64).reshape(-1)
    if d.shape != (3,):
        raise ValueError(f"light must be a length-3 vector, got shape {d.shape}")
    if not np.isfinite(d).all():
        raise ValueError("light contains non-finite values")
    n = float(np.linalg.norm(d))
    if n < 1e-12:
        raise ValueError("light is a zero-length vector (undefined direction)")
    return d / n


# --------------------------------------------------------------------------- #
# 地面(pedestal)ステージ                                                       #
# --------------------------------------------------------------------------- #
def _ground_quad(Vmesh: np.ndarray, light_world: np.ndarray, drop: float,
                 span_scale: float, subdiv: int = 12
                 ) -> tuple[np.ndarray, np.ndarray, float, float]:
    """メッシュ真下の水平地面 grid(``subdiv``×``subdiv`` セル, +Z 法線)を作る。

    地面の高さはメッシュ最下点のわずか下、広さはメッシュ XY 半径 × ``span_scale``。影が落ちる
    側(光と反対の XY 方向)へ中心をずらして、接地影が枠内の地面に確実に載るようにする。細分割
    することで AO(接地の柔らかい暗化リング)が頂点間で滑らかに補間され、2 三角形のときの
    まだら模様を避ける。返り値 ``(Vg, Fg, ground_z, eps_ground)``。"""
    lo = Vmesh.min(axis=0)
    hi = Vmesh.max(axis=0)
    center_xy = 0.5 * (lo[:2] + hi[:2])
    radius_xy = float(np.linalg.norm(hi[:2] - lo[:2])) * 0.5 + 1e-6
    ext = float(hi[2] - lo[2])
    scene = max(float(np.linalg.norm(hi - lo)), 1e-6)
    ground_z = float(lo[2]) - drop * max(ext, radius_xy)
    half = radius_xy * span_scale
    # 影方向(光の XY 逆)へ中心をオフセット(片側に伸ばして影を受ける)。
    lxy = light_world[:2]
    ln = float(np.linalg.norm(lxy))
    shift = (-lxy / ln) * half * 0.45 if ln > 1e-9 else np.zeros(2)
    cx, cy = center_xy + shift
    n = max(int(subdiv), 1) + 1                          # 頂点数 = セル数 + 1
    xs = np.linspace(cx - half, cx + half, n)
    ys = np.linspace(cy - half, cy + half, n)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Vg = np.column_stack([X.ravel(), Y.ravel(),
                          np.full(X.size, ground_z, np.float64)])
    faces = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            b = i * n + (j + 1)
            c = (i + 1) * n + (j + 1)
            d = (i + 1) * n + j
            faces.append([a, b, c])                     # CCW(上から見て) → +Z 外向き
            faces.append([a, c, d])
    Fg = np.asarray(faces, np.int64)
    eps_ground = 1e-4 * scene
    return Vg, Fg, ground_z, eps_ground


# --------------------------------------------------------------------------- #
# 陰影ヘルパー                                                                  #
# --------------------------------------------------------------------------- #
def _lobes(normals: np.ndarray, view_cam: np.ndarray, light_cam: np.ndarray,
           shininess: float) -> tuple[np.ndarray, np.ndarray]:
    """法線マップから拡散ローブ ``max(N·L,0)`` と鏡面ローブ ``max(R·V,0)^n`` を HDR で得る。

    ``render_shade.phong_shade`` を係数を分離して 2 回呼ぶ(``clip=False``)。背景(長さ0法線)は 0。
    """
    diff = render_shade.phong_shade(normals, view=view_cam, light=light_cam,
                                    ambient=0.0, diffuse=1.0, specular=0.0,
                                    shininess=shininess, clip=False)
    spec = render_shade.phong_shade(normals, view=view_cam, light=light_cam,
                                    ambient=0.0, diffuse=0.0, specular=1.0,
                                    shininess=shininess, clip=False)
    return diff, spec


# --------------------------------------------------------------------------- #
# hero レンダラ                                                                 #
# --------------------------------------------------------------------------- #
def render_beauty(V, F, *, pose=None, intrinsics=None, size: int = 512, ss: int = 2,
                  light: Sequence[float] = (0.3, 0.4, 1.0),
                  albedo: Sequence[float] = (0.8, 0.8, 0.85),
                  material: str = "plastic", matcap=None, ambient: float = 0.12,
                  ao: bool = True, ground_shadow: bool = True,
                  tonemap: str = "reinhard",
                  background: Sequence[float] = (0.10, 0.11, 0.13),
                  exposure: float = 1.0, shininess: Optional[float] = None,
                  ao_samples: int = 32, shadow_res: int = 512,
                  penumbra: float = 2.5, shadow_samples: int = 12) -> np.ndarray:
    """メッシュを全品質層合成で「映える静止 3D」1 枚に描く → RGB ``(size, size, 3)`` float [0,1]。

    引数:
      * ``V, F``        頂点 (N,3) と三角形 (M,3)。
      * ``pose``        4x4 object->camera(``render3d.look_at``)。None で ``auto_view``。
      * ``intrinsics``  3x3 ピンホール ``K``(**目標 ``size`` 用**、内部で ``ss`` 倍にスケール)。
      * ``size``        出力の一辺(正方)。``ss``  スーパーサンプリング倍率(整数 >= 1)。
      * ``light``       **ワールド座標**の光源方向(シーン→光源)。陰影と接地影で共有。
      * ``albedo``      物体の反射色 RGB。``material``  ``'plastic'`` | ``'metal'`` | ``'matcap'``。
      * ``matcap``      ``material='matcap'`` のとき必須の lit-sphere テクスチャ ``(h,w[,C])``。
      * ``ambient``     環境光係数。``ao``  アンビエントオクルージョンを掛けるか。
      * ``ground_shadow`` 地面平面 + 接地影を焼き込むか。
      * ``tonemap``     ``'reinhard'`` | ``'aces'`` | ``'none'``。``background``  背景色 RGB。
      * ``exposure``    トーンマップ前の露出。``shininess``  光沢(None でマテリアル既定)。
      * ``ao_samples`` / ``shadow_res`` / ``penumbra`` / ``shadow_samples``
                        品質・速度のチューニング(接地影のソフトさ等)。

    fail-closed: 形状不正・非有限・空・``ss<1``・不正 ``material``/``tonemap``・不正な色/光/露出は
    ``ValueError``。決定的(乱数なし)。"""
    # --- 検証 ---------------------------------------------------------------
    Vv, Ff = _validate_mesh(V, F)
    if isinstance(ss, bool) or not isinstance(ss, (int, np.integer)) or int(ss) < 1:
        raise ValueError(f"ss must be an integer >= 1, got {ss!r}")
    ss = int(ss)
    sz = int(size)
    if sz <= 0:
        raise ValueError(f"size must be positive, got {size!r}")
    if float(sz * ss) * float(sz * ss) > render3d.MAX_PIXELS:
        raise ValueError(f"supersampled render {sz*ss}x{sz*ss} exceeds "
                         f"render3d.MAX_PIXELS ({render3d.MAX_PIXELS}) — lower size or ss")
    if material not in _MATERIALS and material != "matcap":
        raise ValueError(f"material must be one of plastic|metal|matcap, got {material!r}")
    if tonemap not in _TONEMAPS:
        raise ValueError(f"tonemap must be one of {_TONEMAPS}, got {tonemap!r}")
    albedo = _as_color(albedo, "albedo")
    background = _as_color(background, "background")
    light_world = _as_light(light)
    ka = float(ambient)
    if not np.isfinite(ka) or ka < 0.0:
        raise ValueError(f"ambient must be finite and >= 0, got {ambient!r}")
    exp = float(exposure)
    if not np.isfinite(exp) or exp <= 0.0:
        raise ValueError(f"exposure must be a positive finite scalar, got {exposure!r}")
    if material == "matcap" and matcap is None:
        raise ValueError("material='matcap' requires a matcap texture (got None)")

    hs = sz * ss                                         # 高解像度の一辺

    # --- カメラ(目標 size 用 K を ss 倍して高解像度で描く)-------------------
    if pose is None or intrinsics is None:
        dpose, dK = render3d.auto_view(Vv, margin=1.25, width=sz, height=sz)
    P = dpose if pose is None else render3d._check_pose(pose)
    Kt = dK if intrinsics is None else render3d._check_intrinsics(intrinsics)
    Khi = Kt.astype(np.float64).copy()
    Khi[:2, :] *= ss                                     # 目標基準 K を高解像度へ

    # --- シーン合成(必要なら地面を足す)------------------------------------
    if ground_shadow:
        Vg, Fg, ground_z, eps_ground = _ground_quad(
            Vv, light_world, drop=0.01, span_scale=2.4)
        n_mesh = Vv.shape[0]
        V_all = np.vstack([Vv, Vg])
        F_all = np.vstack([Ff, Fg + n_mesh])
    else:
        V_all, F_all = Vv, Ff
        ground_z, eps_ground = None, None

    # --- 幾何バッファ(depth / silhouette / 面法線)-------------------------
    view = render3d.render_mesh(V_all, F_all, pose=P, intrinsics=Khi,
                                width=hs, height=hs)
    normals = view["normals"]                            # (hs, hs, 3) camera space
    sil = view["silhouette"]                             # (hs, hs)
    depth = view["depth"]
    fg = sil > 0                                         # 前景(メッシュ or 地面)

    # 地面画素の判定(ワールド z が地面高さに一致)。
    if ground_shadow:
        Pw = render_shadow.unproject_to_world(depth, P, Khi)     # (hs,hs,3), 背景 NaN
        with np.errstate(invalid="ignore"):
            is_ground = fg & np.isfinite(Pw[..., 2]) & \
                (np.abs(Pw[..., 2] - ground_z) < eps_ground)
    else:
        is_ground = np.zeros_like(fg)
    is_object = fg & ~is_ground

    # --- 光源をカメラ空間へ(法線はカメラ空間)------------------------------
    R = P[:3, :3]
    light_cam = R @ light_world
    view_cam = np.array([0.0, 0.0, 1.0], np.float64)     # カメラは -Z を見る → 視線は +Z

    # --- マテリアル -------------------------------------------------------
    if material == "matcap":
        mat = _MATERIALS["plastic"]                      # 光沢の既定値のみ流用(未使用)
    else:
        mat = _MATERIALS[material]
    sh = float(mat["shininess"]) if shininess is None else float(shininess)
    if not np.isfinite(sh) or sh <= 0.0:
        raise ValueError(f"shininess must be a finite positive number, got {shininess!r}")

    # --- AO / 影のマップ ---------------------------------------------------
    if ao:
        ao_map = render_ao.ambient_occlusion(V_all, F_all, pose=P, intrinsics=Khi,
                                             width=hs, height=hs, n_dirs=int(ao_samples),
                                             background=1.0)
    else:
        ao_map = np.ones((hs, hs), np.float64)
    if ground_shadow:
        shadow_map = render_shadow.cast_shadow(
            V_all, F_all, light_world, pose=P, intrinsics=Khi, width=hs, height=hs,
            directional=True, penumbra=float(penumbra), samples=int(shadow_samples),
            shadow_res=int(shadow_res))
    else:
        shadow_map = np.ones((hs, hs), np.float64)

    # --- HDR 合成 ----------------------------------------------------------
    hdr = np.zeros((hs, hs, 3), np.float64)
    if material == "matcap":
        col = render_shade.matcap_shade(normals, matcap)         # (hs,hs) or (hs,hs,C)
        col = np.asarray(col, np.float64)
        if col.ndim == 2:
            col = np.repeat(col[..., None], 3, axis=2)
        elif col.shape[2] == 1:
            col = np.repeat(col, 3, axis=2)
        elif col.shape[2] >= 3:
            col = col[..., :3]
        # matcap は「素材の見え」を丸ごと持つ → AO で環境遮蔽、影は環境光の床を残して減光。
        shade_scale = ao_map * (ka + (1.0 - ka) * shadow_map)
        hdr = col * shade_scale[..., None]
        # 地面は matcap を貼らずマット拡散で(pedestal の質感)。
        if ground_shadow and is_ground.any():
            diff, _ = _lobes(normals, view_cam, light_cam, _GROUND_SHININESS)
            gcol = _GROUND_ALBEDO[None, None, :] * (
                ka * ao_map[..., None]
                + diff[..., None] * shadow_map[..., None] * ao_map[..., None])
            hdr = np.where(is_ground[..., None], gcol, hdr)
    else:
        diff, spec = _lobes(normals, view_cam, light_cam, sh)
        kd = float(mat["diffuse"])
        ks = float(mat["specular"])
        is_metal = bool(mat["metal"])

        # 物体の反射色・鏡面色(金属は鏡面が素材色、誘電体は白)。
        obj_albedo = albedo[None, None, :]
        obj_spec_tint = obj_albedo if is_metal else np.ones((1, 1, 3), np.float64)

        # per-画素で物体/地面のマテリアルを切替。
        alb_map = np.broadcast_to(obj_albedo, (hs, hs, 3)).copy()
        kd_map = np.full((hs, hs), kd, np.float64)
        ks_map = np.full((hs, hs), ks, np.float64)
        spec_tint = np.broadcast_to(obj_spec_tint, (hs, hs, 3)).copy()
        if ground_shadow and is_ground.any():
            alb_map[is_ground] = _GROUND_ALBEDO
            kd_map[is_ground] = 0.9
            ks_map[is_ground] = _GROUND_SPECULAR
            spec_tint[is_ground] = 1.0

        # 環境光(AO で遮蔽・影には残す)+ 拡散(AO と影)+ 鏡面(影)。
        ambient_rgb = ka * alb_map * ao_map[..., None]
        diffuse_rgb = (kd_map * diff)[..., None] * alb_map \
            * ao_map[..., None] * shadow_map[..., None]
        specular_rgb = (ks_map * spec)[..., None] * spec_tint * shadow_map[..., None]
        hdr = ambient_rgb + diffuse_rgb + specular_rgb

    hdr = np.where(fg[..., None], hdr, 0.0)              # 背景は 0(後で背景色を合成)
    hdr = np.clip(hdr, 0.0, None)                        # 数値上の微小負値を除去

    # --- トーンマップ(前景のみ)------------------------------------------
    if tonemap == "reinhard":
        ldr = render_tonemap.tonemap_reinhard(hdr, exposure=exp)
    elif tonemap == "aces":
        ldr = render_tonemap.tonemap_aces(hdr, exposure=exp)
    else:                                                # none: 素朴クリップ
        ldr = np.clip(hdr * exp, 0.0, 1.0)

    # --- 背景合成(表示空間)→ SSAA 縮小 ----------------------------------
    out_hi = np.where(fg[..., None], ldr, background[None, None, :])
    out = render_ssaa.antialias(out_hi, ss, filter="box")
    return np.clip(out, 0.0, 1.0).astype(np.float64)
