# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_showcase_gifs — 「科学館の台座に載った作品」風のアニメ GIF ショーケース。

Fullseye の **実 op** だけで、生成メッシュ(SDF)/ 実データ点群(Itokawa 小惑星)/
実データボリューム(手骨 CT)をターンテーブル回転させ、``render_beauty`` の全品質層
(鏡面陰影・AO・接地影・トーンマップ・SSAA)で焼き込んで GIF 化する。Qiita 記事に
そのまま貼れる、映える・かつ「本物のレンダ」である短尺ループを作るのが目的。

作る GIF(``examples_3d/_gallery/`` へ):
  * ``showcase_turntable_pod.gif``      —— SDF 生成 hero pod を金属マテリアルで 1 回転。
  * ``showcase_turntable_itokawa.gif``  —— 小惑星 25143 Itokawa を岩石マテリアルで 1 回転。
  * ``showcase_turntable_skeleton.gif`` —— 手骨 CT を骨色マテリアルで 1 回転(骨格標本風)。
  * ``showcase_hue_cycle.gif``          —— pod を回しながら **表面アルベドの色相を 0→360**
                                           で回す(ユーザー発案「色相回し」の体験)。

honest: これは GT アサートのある op ではなく **視覚ショーケース**。ただし被写体は
すべて Fullseye の実 op が実データ / 生成メッシュから作った本物のレンダである。
決定的(乱数を使わない。AO / 影の下位 op は決定的サンプリング)。

技法メモ:
  * 速度: ``render_beauty`` の AO は **頂点ごと**の半球レイキャスト(頂点 × 方向 × 面)なので、
    メッシュは ``mesh_decimate.decimate_qem_manifold`` で ~2500 面へ QEM 減面してから描く
    (見た目のシルエットを保ったまま 1 フレーム ~5 秒に収める)。
  * ターンテーブル: 物体頂点を鉛直軸(Z)まわりに等角回転し、カメラと光源は世界固定。
    こうすると台座・接地影が動かず「回っているのは作品だけ」という展示台の見えになる。
    等角ステップ(0..360 を N 等分)なので継ぎ目なくループする。
  * 色相回し: 各フレームで HSV の hue を 0→360 に回した鮮やかなアルベドを ``render_beauty``
    へ渡す(hsv→rgb は numpy で honest に実装)。回転角と hue を同じ周期にしてループさせる。

numpy + scipy + imageio + PIL のみ(matplotlib は使わない)。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Callable, Optional

import numpy as np
from scipy.ndimage import binary_dilation, binary_fill_holes, gaussian_filter

# --- Fullseye 実 op(imgevolve ルートを PYTHONPATH に置いて実行)------------------
import sdf_ops
import render3d
import recon3d
import render_beauty as rb
import mesh_decimate

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_ASSETS = os.path.join(_ROOT, "studio_assets", "sample_3d")
_OUT_DIR = os.path.join(_ROOT, "examples_3d", "_gallery")


# --------------------------------------------------------------------------- #
# 幾何ヘルパー(決定的)                                                         #
# --------------------------------------------------------------------------- #
def _rot_z(theta: float) -> np.ndarray:
    """Z 軸まわり回転行列 (3,3)。"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], np.float64)


def _center(V: np.ndarray) -> np.ndarray:
    """頂点を bbox 中心が原点に来るよう平行移動。"""
    lo, hi = V.min(axis=0), V.max(axis=0)
    return V - 0.5 * (lo + hi)


def _orbit_camera(V: np.ndarray, *, size: int, elev_deg: float,
                  azim_deg: float = 0.0, margin: float = 1.30,
                  fov_deg: float = 40.0):
    """物体の bounding sphere を枠に収める固定カメラ ``(pose, K)`` を作る。

    距離は ``dist = margin * r / tan(fov/2)`` で画素サイズに依らず一定。カメラは
    仰角 ``elev_deg`` ・方位 ``azim_deg`` から中心を見下ろす(up = 世界 +Z)。全フレームで
    同じ ``(pose, K)`` を使い、回転は物体側で行う(= 揺れないターンテーブル)。"""
    center = 0.5 * (V.min(axis=0) + V.max(axis=0))
    radius = float(np.linalg.norm(V - center, axis=1).max())
    radius = max(radius, 1e-6)
    K = render3d.intrinsics_from_fov(fov_deg, size, size)
    dist = margin * radius / np.tan(np.deg2rad(fov_deg) * 0.5)
    e = np.deg2rad(elev_deg)
    a = np.deg2rad(azim_deg)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], np.float64)
    eye = center + dist * d
    pose = render3d.look_at(eye, center, up=(0.0, 0.0, 1.0))
    return pose, K, center


def _hsv_to_rgb(h_deg: float, s: float, v: float) -> tuple[float, float, float]:
    """単一色の HSV(hue は度)→ RGB [0,1]。honest な numpy 実装(乱数なし)。"""
    h = (float(h_deg) % 360.0) / 60.0
    c = v * s
    x = c * (1.0 - abs((h % 2.0) - 1.0))
    m = v - c
    if h < 1:
        r, g, b = c, x, 0.0
    elif h < 2:
        r, g, b = x, c, 0.0
    elif h < 3:
        r, g, b = 0.0, c, x
    elif h < 4:
        r, g, b = 0.0, x, c
    elif h < 5:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return (r + m, g + m, b + m)


def _decimate(V: np.ndarray, F: np.ndarray, target_faces: int):
    """QEM 減面(面数が既に少なければそのまま)。AO のレイキャスト負荷を下げるため。"""
    if F.shape[0] <= target_faces:
        return V.astype(np.float64), F.astype(np.int64)
    Vd, Fd = mesh_decimate.decimate_qem_manifold(V, F, int(target_faces))
    return Vd.astype(np.float64), Fd.astype(np.int64)


def _orient_outward(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """面の巻き方向を **外向き** に揃える(必要なら全面を反転)→ 揃えた F を返す。

    ``render_mesh`` の陰影法線は毎ピクセルでカメラ向きに反転されるため巻き方向に依らないが、
    ``render_ao`` の頂点半球は面の巻き方向由来の頂点法線で決まる。巻きが内向きだと半球が物体
    内部を向き、全レイが即命中して AO≈0(=真っ黒)になる。skimage marching cubes の巻きは
    場の符号規約(SDF=内負 / occupancy=内正)で反転しうるので、面重心が bbox 中心から外を
    向くか(面積重み付き符号和)で判定して内向きなら反転する。凸に近い閉曲面で確実。"""
    c = 0.5 * (V.min(axis=0) + V.max(axis=0))
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A)                            # 面積重み付き法線(未正規化)
    fc = (A + B + C) / 3.0 - c[None, :]
    signed = float(np.einsum("ij,ij->i", n, fc).sum())   # >0 = 多数が外向き
    if signed < 0.0:
        return F[:, ::-1].copy()
    return F


# --------------------------------------------------------------------------- #
# 被写体メッシュの構築(すべて Fullseye 実 op)                                   #
# --------------------------------------------------------------------------- #
def build_pod(res: int = 72, target_faces: int = 2600):
    """SDF プリミティブ(球 + 球の smooth-union に翼の box)→ marching cubes で hero pod。

    ``sdf_ops`` の解析 SDF を ``grid_coords`` 上で評価し ``sdf_smooth_union`` で合成、
    ``render3d.marching_cubes`` で三角形化する(すべて Fullseye 実 op)。Z が鉛直(頭が上)。"""
    g, _ = sdf_ops.grid_coords(((-1.6, 1.6),) * 3, res)
    body = sdf_ops.sphere_sdf(g, (0.0, 0.0, -0.05), 0.90)
    head = sdf_ops.sphere_sdf(g, (0.0, 0.0, 0.82), 0.55)
    pod = sdf_ops.sdf_smooth_union(body, head, 0.35)
    wing = sdf_ops.box_sdf(g, (0.0, 0.0, -0.35), (1.15, 0.10, 0.30))
    pod = sdf_ops.sdf_smooth_union(pod, wing, 0.22)
    nose = sdf_ops.sphere_sdf(g, (0.0, 0.55, 0.82), 0.16)     # 「目」の張り出し
    pod = sdf_ops.sdf_smooth_union(pod, nose, 0.10)
    V, F = render3d.marching_cubes(pod, level=0.0)
    F = _orient_outward(V, F)
    V = _center(V)
    return _decimate(V, F, target_faces)


def _pointcloud_to_occupancy_mesh(P: np.ndarray, *, res: int = 72,
                                  dilate: int = 2, sigma: float = 1.5):
    """疎な表面点群 → 等方 voxel 占有 → 穴埋め → 平滑 → ``render3d.marching_cubes``。

    Itokawa の点群は 3000 点と疎で、``recon3d.poisson_lite`` / ``alpha_shape_mesh`` は
    watertight 化に失敗して同心二重殻や断片群へ縮退する(点間隔 > voxel でシェルが塞がらない
    ため。poisson_lite の docstring が述べる honest な縮退)。そこで点を等方格子へ splat し、
    ``binary_dilation`` で点間を橋渡しして watertight にしてから ``binary_fill_holes`` で中実化、
    ガウス平滑して単一等値面を ``render3d.marching_cubes`` で抜く。実データ点群 → 実 op メッシュ。"""
    lo, hi = P.min(axis=0), P.max(axis=0)
    span = hi - lo
    vs = float(span.max()) / max(res - 1, 1)                 # 等方 voxel サイズ
    pad = 4
    dims = np.maximum(np.ceil(span / vs).astype(int) + 1 + 2 * pad, 8)
    idx = np.rint((P - lo) / vs).astype(int) + pad
    idx = np.clip(idx, 0, dims - 1)
    grid = np.zeros(tuple(dims), bool)
    grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    grid = binary_fill_holes(binary_dilation(grid, iterations=int(dilate)))
    field = gaussian_filter(grid.astype(np.float64), float(sigma))
    field /= max(float(field.max()), 1e-12)
    V, F = render3d.marching_cubes(field, level=0.5)
    V = V * vs                                               # voxel index → 元スケールへ
    return V, F


def build_itokawa(target_faces: int = 2600):
    """Itokawa 実点群 (N,3) → 水密メッシュ → 外向き整列 → 減面。戻り値 (V, F, method)。

    honest: 疎点群のため ``poisson_lite`` / ``alpha_shape_mesh`` は二重殻/断片へ縮退する
    (実測で確認)。占有 voxel + 穴埋め + ``render3d.marching_cubes`` で確実に単一の水密殻を得る。"""
    P = np.load(os.path.join(_ASSETS, "itokawa_points.npy")).astype(np.float64)
    V, F = _pointcloud_to_occupancy_mesh(P, res=72, dilate=2, sigma=1.5)
    F = _orient_outward(V, F)
    V = _center(V)
    Vd, Fd = _decimate(V, F, target_faces)
    method = "occupancy voxelize + fill_holes -> render3d.marching_cubes"
    return Vd, Fd, method


def build_skeleton(target_faces: int = 2600):
    """手骨 CT ボリューム (D,H,W) → marching cubes で骨表面メッシュ。

    境界で表面が開かないよう 0 パディングしてから ``level=0.5`` で等値面抽出。指の長軸
    (元 axis1)を鉛直 Z に向け直し(列を [0,2,1] に並べ替え)、骨格標本のように立たせる。
    戻り値 (V, F, method)。"""
    vol = np.load(os.path.join(_ASSETS, "skeleton_ct.npy")).astype(np.float64)
    volp = np.pad(vol, 1, mode="constant", constant_values=0.0)
    level = 0.5
    V, F = render3d.marching_cubes(volp, level=level)
    V = V[:, [0, 2, 1]]                                       # 指の長軸を鉛直(Z)へ
    F = _orient_outward(V, F)
    V = _center(V)
    Vd, Fd = _decimate(V, F, target_faces)
    return Vd, Fd, f"marching_cubes(level={level}, padded)"


# --------------------------------------------------------------------------- #
# フレーム生成 & GIF 書き出し                                                    #
# --------------------------------------------------------------------------- #
def _to_u8(img: np.ndarray) -> np.ndarray:
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)


def render_turntable(V: np.ndarray, F: np.ndarray, *, frames: int, size: int,
                     ss: int, material: str, albedo, light, background,
                     elev_deg: float, azim_deg: float = 0.0, tonemap: str = "aces",
                     ao_samples: int = 16, shadow_samples: int = 8,
                     albedo_fn: Optional[Callable[[int], tuple]] = None,
                     log: Callable[[str], None] = print) -> list[np.ndarray]:
    """物体を Z 軸まわりに等角 1 回転させ、各角度で ``render_beauty`` で 1 枚描く。

    ``albedo_fn(i)`` を渡すと i 番目フレームのアルベドをそれで上書き(色相回し用)。
    カメラ・光源は世界固定(``_orbit_camera`` の pose/K を全フレーム共用)。"""
    pose, K, _ = _orbit_camera(V, size=size, elev_deg=elev_deg, azim_deg=azim_deg)
    out: list[np.ndarray] = []
    t_sum = 0.0
    for i in range(frames):
        theta = 2.0 * np.pi * i / frames
        Vr = V @ _rot_z(theta).T                             # 物体を回す(世界カメラ固定)
        alb = albedo_fn(i) if albedo_fn is not None else albedo
        t0 = time.time()
        img = rb.render_beauty(
            Vr, F, pose=pose, intrinsics=K, size=size, ss=ss,
            material=material, albedo=alb, light=light, background=background,
            tonemap=tonemap, ao=True, ground_shadow=True,
            ao_samples=ao_samples, shadow_samples=shadow_samples)
        dt = time.time() - t0
        t_sum += dt
        out.append(_to_u8(img))
        if i == 0 or (i + 1) % 8 == 0 or i == frames - 1:
            log(f"    frame {i + 1}/{frames}  {dt:.2f}s")
    log(f"    mean {t_sum / max(frames, 1):.2f}s/frame ({frames} frames, {t_sum:.1f}s)")
    return out


def save_gif(frames_u8: list[np.ndarray], path: str, *, fps: int,
             max_bytes: int = 4_000_000, log: Callable[[str], None] = print) -> int:
    """PIL でループ GIF を書き出す。4MB 目安を超えたら色数を段階的に落として再エンコード。

    戻り値 = 実ファイルサイズ(bytes)。決定的(MEDIANCUT パレット)。"""
    from PIL import Image
    duration = int(round(1000.0 / max(fps, 1)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    size_bytes = -1
    for colors in (256, 224, 192, 160, 128, 96):
        pil = [Image.fromarray(f, "RGB").convert(
                   "P", palette=Image.ADAPTIVE, colors=colors) for f in frames_u8]
        pil[0].save(path, save_all=True, append_images=pil[1:], duration=duration,
                    loop=0, disposal=2, optimize=True)
        size_bytes = os.path.getsize(path)
        if size_bytes <= max_bytes:
            log(f"    saved {os.path.basename(path)}  colors={colors}  "
                f"{size_bytes / 1e6:.2f} MB")
            return size_bytes
        log(f"    {os.path.basename(path)} {size_bytes / 1e6:.2f} MB > budget at "
            f"colors={colors}, retrying with fewer colors")
    log(f"    WARNING: {os.path.basename(path)} still {size_bytes / 1e6:.2f} MB "
        f"after reducing colors (kept last encode)")
    return size_bytes


def verify_gif(path: str, log: Callable[[str], None] = print) -> tuple[int, tuple]:
    """imageio で開き直してフレーム数と 1 フレームの形状を実測(捏造しない検証)。"""
    import imageio.v2 as imageio
    reader = imageio.get_reader(path)
    n = 0
    shape = None
    for frame in reader:
        if shape is None:
            shape = tuple(np.asarray(frame).shape)
        n += 1
    reader.close()
    if n <= 1:
        raise RuntimeError(f"{path}: GIF has {n} frame(s) — expected an animation")
    log(f"    verify {os.path.basename(path)}: {n} frames, frame shape {shape}")
    return n, shape


# --------------------------------------------------------------------------- #
# 個々のショーケース                                                             #
# --------------------------------------------------------------------------- #
def _report(kind: str, path: str, frames: int, size_bytes: int,
            n_check: int, shape, extra: str, log: Callable[[str], None]):
    log(f"[done] {kind}: {path}")
    log(f"       frames={frames} verified={n_check} shape={shape} "
        f"size={size_bytes / 1e6:.2f}MB  {extra}")


def gen_all(*, frames: int, size: int, ss: int, fps: int, out_dir: str,
            subjects: set[str], log: Callable[[str], None] = print) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    results: dict[str, dict] = {}

    # --- 1. hero pod ターンテーブル(金属)-----------------------------------
    if "pod" in subjects or "hue" in subjects:
        log("[build] pod (SDF -> marching_cubes)")
        Vp, Fp = build_pod()
        log(f"    pod mesh V{Vp.shape} F{Fp.shape}")

    if "pod" in subjects:
        log("[render] showcase_turntable_pod.gif  (metal)")
        frames_pod = render_turntable(
            Vp, Fp, frames=frames, size=size, ss=ss, material="metal",
            albedo=(0.85, 0.60, 0.24), light=(0.45, 0.55, 0.90),
            background=(0.07, 0.08, 0.10), elev_deg=18.0, tonemap="aces", log=log)
        p = os.path.join(out_dir, "showcase_turntable_pod.gif")
        sb = save_gif(frames_pod, p, fps=fps, log=log)
        n, shp = verify_gif(p, log=log)
        results["pod"] = dict(path=p, frames=frames, bytes=sb, n=n, shape=shp,
                              info="SDF pod, metal, aces tonemap, AO+ground shadow")
        _report("turntable_pod", p, frames, sb, n, shp,
                "subject=SDF pod / material=metal", log)

    # --- 2. Itokawa ターンテーブル(岩石)------------------------------------
    if "itokawa" in subjects:
        log("[build] itokawa (point cloud -> mesh)")
        Vi, Fi, method_i = build_itokawa()
        log(f"    itokawa mesh V{Vi.shape} F{Fi.shape}  via {method_i}")
        log("[render] showcase_turntable_itokawa.gif  (rock/plastic)")
        frames_i = render_turntable(
            Vi, Fi, frames=frames, size=size, ss=ss, material="plastic",
            albedo=(0.46, 0.43, 0.39), light=(0.55, 0.35, 0.80),
            background=(0.02, 0.02, 0.04), elev_deg=12.0, tonemap="aces", log=log)
        p = os.path.join(out_dir, "showcase_turntable_itokawa.gif")
        sb = save_gif(frames_i, p, fps=fps, log=log)
        n, shp = verify_gif(p, log=log)
        results["itokawa"] = dict(path=p, frames=frames, bytes=sb, n=n, shape=shp,
                                  info=f"Itokawa point cloud via {method_i}, plastic")
        _report("turntable_itokawa", p, frames, sb, n, shp,
                f"subject=Itokawa asteroid / mesh via {method_i}", log)

    # --- 3. 手骨 CT ターンテーブル(骨色)------------------------------------
    if "skeleton" in subjects:
        log("[build] skeleton (CT volume -> marching_cubes)")
        Vs, Fs, method_s = build_skeleton()
        log(f"    skeleton mesh V{Vs.shape} F{Fs.shape}  via {method_s}")
        log("[render] showcase_turntable_skeleton.gif  (bone)")
        frames_s = render_turntable(
            Vs, Fs, frames=frames, size=size, ss=ss, material="plastic",
            albedo=(0.87, 0.83, 0.72), light=(0.40, 0.45, 0.85),
            background=(0.06, 0.07, 0.09), elev_deg=6.0, tonemap="reinhard", log=log)
        p = os.path.join(out_dir, "showcase_turntable_skeleton.gif")
        sb = save_gif(frames_s, p, fps=fps, log=log)
        n, shp = verify_gif(p, log=log)
        results["skeleton"] = dict(path=p, frames=frames, bytes=sb, n=n, shape=shp,
                                   info=f"hand-bone CT via {method_s}, bone plastic")
        _report("turntable_skeleton", p, frames, sb, n, shp,
                f"subject=hand-bone CT / mesh via {method_s}", log)

    # --- 4. 色相回し(pod、回転 + アルベド hue 0->360)-----------------------
    if "hue" in subjects:
        log("[render] showcase_hue_cycle.gif  (pod, plastic, albedo hue 0->360)")

        def albedo_fn(i: int):
            return _hsv_to_rgb(360.0 * i / frames, s=0.85, v=0.95)

        frames_h = render_turntable(
            Vp, Fp, frames=frames, size=size, ss=ss, material="plastic",
            albedo=(0.8, 0.8, 0.8), light=(0.45, 0.55, 0.90),
            background=(0.06, 0.07, 0.09), elev_deg=18.0, tonemap="reinhard",
            albedo_fn=albedo_fn, log=log)
        p = os.path.join(out_dir, "showcase_hue_cycle.gif")
        sb = save_gif(frames_h, p, fps=fps, log=log)
        n, shp = verify_gif(p, log=log)
        results["hue"] = dict(path=p, frames=frames, bytes=sb, n=n, shape=shp,
                              info="SDF pod, plastic, HSV hue 0->360 on albedo + spin")
        _report("hue_cycle", p, frames, sb, n, shp,
                "subject=SDF pod / albedo hue 0->360", log)

    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fullseye 3D showcase GIF generator")
    ap.add_argument("--subjects", default="pod,itokawa,skeleton,hue",
                    help="comma list of pod,itokawa,skeleton,hue (default all)")
    ap.add_argument("--frames", type=int, default=40, help="frames per GIF (default 40)")
    ap.add_argument("--size", type=int, default=480, help="output square size (default 480)")
    ap.add_argument("--ss", type=int, default=2, help="supersampling factor (default 2)")
    ap.add_argument("--fps", type=int, default=20, help="playback fps (default 20)")
    ap.add_argument("--out", default=_OUT_DIR, help="output dir (default examples_3d/_gallery)")
    args = ap.parse_args(argv)

    subjects = {s.strip() for s in args.subjects.split(",") if s.strip()}
    valid = {"pod", "itokawa", "skeleton", "hue"}
    bad = subjects - valid
    if bad:
        print(f"unknown subjects: {sorted(bad)} (valid: {sorted(valid)})", file=sys.stderr)
        return 2

    def log(m):
        print(m, flush=True)

    t0 = time.time()
    log(f"=== Fullseye showcase GIFs: subjects={sorted(subjects)} "
        f"frames={args.frames} size={args.size} ss={args.ss} fps={args.fps} ===")
    results = gen_all(frames=args.frames, size=args.size, ss=args.ss, fps=args.fps,
                      out_dir=args.out, subjects=subjects, log=log)
    log(f"=== all done in {time.time() - t0:.1f}s: "
        f"{len(results)} GIF(s) -> {args.out} ===")
    for k, r in results.items():
        log(f"  {k}: {r['path']}  {r['n']} frames  {r['bytes'] / 1e6:.2f}MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
