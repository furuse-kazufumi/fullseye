# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 小惑星イトカワの実形状モデルを **物理ベース**で描く(Hapke 反射則 + 太陽視直径 0.53° の
レイキャスト影 + 環境光ゼロ + 解像度を意識した地形レリーフ + 角張った岩)。記事の hero 画像は
この op 連鎖で作る。

実世界の問題(2026-09-03 の指摘、2 回目):
    1 回目の修正(Hapke + レイキャスト影)後も「粗すぎる、表面の凹凸が見えない」「点群の粗い
    部分と密な部分の使い分けが出来ていない」— 露出過多の白いジャガイモに数個のビー玉。実測した
    原因は 4 つ:
      (1) 形状モデル(Gaskell f0049152、km 単位)の面は辺長 2.6〜14 m(p5/中央/p95 =
          2.6/4.7/7.2 m)で **不均一**。2.5 m の fBm を頂点に載せても、密な所では解像し
          粗い所ではファセットノイズになる(= 見えていた「粗密の不一致」)。
      (2) 起伏が単一振幅 2.5 m(基本波長 ≈ 50 m)で、傾斜 rms が数度しかなく陰影に出ない。
      (3) 岩が D ≥ 5 m のなめらかな楕円体 252 個(ビー玉)。実際は N(>D) ∝ D^-3.1 で 1 m 級が
          数万個、角張った塊。
      (4) 位相角 30° で太陽がカメラ側 → 起伏の影が消える。露出は 99.5 % 点合わせで
          照らされた面の中央値が 0.74(白飛び寸前)。

fullseye op 連鎖(すべて ops3d に登録済み):
    mesh(STL 49,152 面、**間引きは一切しない**)
    → mesh_edge_lengths(解像度マップ: 頂点ごとの局所辺長)
    → mesh_subdivide(target_edge=1.5 m: 適応テッセレーション。幾何不変・面積体積厳密保存)
    → displacement_band_weights(元モデルの局所辺長で「実データが既に持つ波長」を測る →
       補集合 = 合成レリーフの重み。密な領域では 0、粗い領域では 1)
    → mesh_displace_spectrum(波長ごとに振幅を明示した変位。頂点ごとの帯域ゲートで
       2×局所辺長より短い波長は変位しない)
    → terrain_region_mask(海/高地) → mesh_scatter_boulders(shape='hull', べき則 -3.1、
       d_min 1 m → max_count で d_min を法則どおり引き上げ、30–60 % 埋没、ランダム姿勢、
       **変位後の面に置く**)
    → render_regolith(brdf_hapke + shadow_raycast + 環境光 0 + 一回反射近似 + 線形トーン、
       bump=変位できなかった短波長オクターブの補集合を陰影法線へ、exposure='median')

振幅スペクトル(設計値。実測ではない — 正直な前提):
    A(λ) = 3 m × (λ / 60 m)^0.77 :  60 m→3.0, 30→1.76, 15→1.03, 7.5→0.61, 3.75→0.36, 1.9→0.21 m。
    根拠は 2 つの拘束: (i) Hapke の巨視的粗さ θ̄ = 26°(Kitazato et al. 2008)は **未解像**の
    傾斜なので、解像される bump の rms 傾斜はそれを超えない(実測して表示)。(ii) 岩の
    べき則(Michikami et al. 2008)が数 m スケールの起伏の主因なので、変位の短波長側は
    岩に譲る。イトカワの粗さスペクトルそのものの文献値は引用していない。

GT(閉形式 / 幾何 / 統計):
    (a) 縁の明るさ  同じ法線で Lommel-Seeliger の縁帯 / 中央 比が Lambert より大きい。
    (b) 対向効果    Hapke の平均 I/F は位相角 2° が 20° の 1.3 倍超(B0=0.87, h=0.01)。
    (c) 硬い影      太陽 0.53° の半影画素は受光面の 1 % 未満、位相角 60° では影が存在。
    (d) 解像度      テッセレーション後の中央辺長 = target ± 10 %、最大辺 ≤ 2×target(辺上の
                    分割は ≤ 1.5×target、面内の Delaunay 接続が最長)、面積・体積は相対 1e-9
                    で不変、元モデルの粗い 10 % の合成重みは細かい 10 % より大きい。
    (e) 帯域        変位に使った各オクターブは、全頂点で「波長 ≥ 2×局所辺長」のときだけ重み > 0。
    (f) 岩          個数は(cap 後の)期待値の Poisson 4σ 内、埋没率は [0.3, 0.6]、海に岩ゼロ。
    (g) 露出        照らされた面の中央値 0.45 ± 0.02、クリップ画素 < 0.5 %。
    (h) レリーフ    高域(σ=2 px を引いた残差)の std / 中央値 ≥ 0.03(AMICA 実画像 0.037、
                    AMICA と同じ円盤画素数に縮小して比較)。
    (i) 決定的      render_regolith を 2 回呼んで画素完全一致。
    (j) bump        補集合オクターブ(λ ≤ 2×1.5 m)の陰影法線の rms 傾斜 < Hapke θ̄ = 26°
                    (未解像粗さと二重計上しない、「偽のサンドペーパー」でない)。

hero 画像: examples_3d/_gallery/itokawa_regolith_hero.png(既定 640 px・SSAA 2・位相角 55°・
太陽は左上)。``--fast`` で 256 px / ss=1(テスト用)。データ: JAXA はやぶさ / Gaskell 形状モデル
(public domain)。``fullseye samples download itokawa`` で data/sample_3d_cache/ に置く。
テッセレーション結果(決定的)は同じディレクトリに .npz でキャッシュする。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import mesh  # noqa: E402
import render3d  # noqa: E402
import render_beauty  # noqa: E402
import render_shade  # noqa: E402
import render_shadow  # noqa: E402

STL = _REPO_ROOT / "data" / "sample_3d_cache" / "itokawa_f0049152.stl"
HERO = _REPO_ROOT / "examples_3d" / "_gallery" / "itokawa_regolith_hero.png"

# Itokawa Hapke parameters (Kitazato et al. 2008, Icarus 194; S-type typical)
HAPKE = dict(w=0.42, g=-0.35, B0=0.87, h=0.01, roughness_deg=26.0)
#: 目標辺長 [km](1.5 m)。hero の画素は ~1.1 m なので 1 画素強。
TARGET_EDGE = 0.0015
#: 起伏の振幅スペクトル [km]: A(λ) = 3 m (λ/60 m)^0.77
WAVELENGTHS = np.array([60.0, 30.0, 15.0, 7.5, 3.75, 1.9]) * 1e-3
AMPLITUDES = 3.0e-3 * (WAVELENGTHS / 60e-3) ** 0.77
#: 岩: D ≥ 5 m が 1000 個/km²(前版と同じ前提)→ べき則 -3.1 で D ≥ 1 m は 5^3.1 倍。
BOULDER_DENSITY_1M = 1000.0 * 5.0 ** 3.1        # per km², D >= 1 m
BOULDER = dict(d_min=0.001, d_max=0.035, exponent=3.1, max_count=3000, burial=(0.3, 0.6))
SEED = 1
#: AMICA 実画像 st_2391934788_v.fit(位相 8.8°、円盤 30,489 px)の高域コントラスト(2026-09-03 実測)。
AMICA_RELIEF = 0.037
AMICA_DISK_PX = 30489


# --------------------------------------------------------------------------- #
# カメラ・太陽                                                                   #
# --------------------------------------------------------------------------- #
def camera_and_sun(V, size: int, phase_deg: float, cam_dir=(0.15, -1.0, 0.35),
                   sun_azimuth_deg: float = 135.0):
    """側面やや上からのカメラと、位相角 ``phase_deg`` だけカメラ方向から傾けた太陽方向。

    ``sun_azimuth_deg`` は画面内の太陽の方位(0 = 右、90 = 上、135 = 左上)。"""
    cen = 0.5 * (V.min(0) + V.max(0))
    rad = 0.5 * float(np.linalg.norm(V.max(0) - V.min(0)))
    cd = np.asarray(cam_dir, float)
    cd /= np.linalg.norm(cd)
    eye = cen + cd * rad * 3.2
    pose = render3d.look_at(eye, cen, up=(0.0, 0.0, 1.0))
    fov = 2.0 * np.degrees(np.arctan(0.85 / 3.2))
    K = render3d.intrinsics_from_fov(fov, size, size)
    # 画面の右・上をワールドで(pose の行 = カメラ軸)。
    R = pose[:3, :3]
    right, up = R[0], R[1]
    az = np.deg2rad(sun_azimuth_deg)
    ph = np.deg2rad(phase_deg)
    sun = np.cos(ph) * cd + np.sin(ph) * (np.cos(az) * right + np.sin(az) * up)
    return pose, K, sun / np.linalg.norm(sun)


# --------------------------------------------------------------------------- #
# レリーフ op 連鎖                                                               #
# --------------------------------------------------------------------------- #
def tessellate_cached(V, F, target_edge: float, cache_dir: Path):
    """mesh_subdivide(target_edge) の結果を .npz にキャッシュ(決定的なので再利用可)。"""
    cache = cache_dir / f"{STL.stem}_tess{int(round(target_edge * 1e6))}mm.npz"
    if cache.exists():
        z = np.load(cache)
        if z["V"].shape[0] > 0 and z["F"].shape[0] > 0:
            return z["V"], z["F"], True
    Vs, Fs = render3d.mesh_subdivide(V, F, target_edge=target_edge)
    try:
        np.savez_compressed(cache, V=Vs, F=Fs)
    except OSError as exc:                                 # pragma: no cover
        print(f"[note] キャッシュ保存に失敗: {exc}")
    return Vs, Fs, False


def build_relief_mesh(V, F, *, target_edge=TARGET_EDGE, cache_dir=None, boulders=True):
    """op 連鎖: 解像度マップ → 適応テッセレーション → 帯域ゲート付き変位 → 海/高地 → 岩。

    戻り値 ``(V, F, info)``。``info`` に各段の実測(辺長ヒストグラム、合成重み、岩)を入れる。"""
    info = {}
    e_orig = render3d.mesh_edge_lengths(V, F, per="vertex")            # 解像度マップ
    info["edge_before"] = render3d.mesh_edge_lengths(V, F, per="edge")
    t0 = time.time()
    if cache_dir is None:
        Vs, Fs = render3d.mesh_subdivide(V, F, target_edge=target_edge)
        cached = False
    else:
        Vs, Fs, cached = tessellate_cached(V, F, target_edge, cache_dir)
    info["tess_time"] = time.time() - t0
    info["tess_cached"] = cached
    info["edge_after"] = render3d.mesh_edge_lengths(Vs, Fs, per="edge")
    # 元モデルが既に持つ波長(局所辺長の Nyquist)→ 補集合 = 合成レリーフの重み。
    from scipy.spatial import cKDTree
    e_at = e_orig[cKDTree(V).query(Vs, k=1)[1]]
    carried = render3d.displacement_band_weights(Vs, Fs, WAVELENGTHS, local_edge=e_at)
    synth_w = 1.0 - carried                                            # (K, N)
    info["synth_weight"] = synth_w
    info["e_orig_at"] = e_at
    gate_post = render3d.displacement_band_weights(Vs, Fs, WAVELENGTHS)
    info["gate_post"] = gate_post
    Vd, Fd = render3d.mesh_displace_spectrum(Vs, Fs, WAVELENGTHS, AMPLITUDES, seed=SEED,
                                             weights=synth_w)
    info["disp"] = np.linalg.norm(Vd - Vs, axis=1)
    if not boulders:
        return Vd, Fd, info
    w = render3d.terrain_region_mask(Vd, Fd, smooth_fraction=0.3, method="neck")
    info["sea_faces"] = int((w == 0).sum())
    Vb, Fb, binfo = render3d.mesh_scatter_boulders(
        Vd, Fd, density=BOULDER_DENSITY_1M, d_min=BOULDER["d_min"], d_max=BOULDER["d_max"],
        exponent=BOULDER["exponent"], seed=SEED + 2, region_weights=w, shape="hull",
        orientation="random", burial=BOULDER["burial"], max_count=BOULDER["max_count"],
        return_info=True)
    binfo["in_sea"] = int((w[binfo["face"]] == 0).sum())
    info["boulders"] = binfo
    info["n_faces_terrain"] = int(Fd.shape[0])
    return Vb, Fb, info


# --------------------------------------------------------------------------- #
# 測光メトリクス(AMICA 実画像との比較に使うもの)                                  #
# --------------------------------------------------------------------------- #
def relief_metrics(img: np.ndarray, *, match_disk_px=None) -> dict:
    """黒背景の単体画像の (lit_median, clipped, relief_contrast, disk_px)。

    ``relief_contrast`` = 照らされた円盤(中央値の 50 % 以上、縁 3 px を除く)で σ=2 px の
    ガウシアンを引いた高域残差の std / 照らされた面の中央値。``match_disk_px`` を与えると
    円盤の画素数がそれに一致するよう縮小してから測る(AMICA 実画像と同じ画素スケール)。"""
    from scipy import ndimage as ndi
    I = np.asarray(img, np.float64)
    if I.ndim == 3:
        I = I.mean(axis=2)
    p = float(np.percentile(I, 99.5))
    disk = I > 0.04 * p
    if match_disk_px is not None and disk.sum() > 0:
        z = float(np.sqrt(match_disk_px / disk.sum()))
        I = ndi.zoom(I, z, order=1)
        p = float(np.percentile(I, 99.5))
        disk = I > 0.04 * p
    lab, n = ndi.label(disk)
    if n > 1:
        sizes = ndi.sum(disk, lab, range(1, n + 1))
        disk = lab == (1 + int(np.argmax(sizes)))
    disk = ndi.binary_fill_holes(disk)
    dist = ndi.distance_transform_edt(disk)
    vals = I[disk & (dist > 2.5)]
    L = float(np.median(vals[vals > 0.3 * p])) if vals.size else 0.0
    hp = I - ndi.gaussian_filter(I, 2.0)
    lit = disk & (I > 0.5 * L) & (dist > 3)
    contrast = float(hp[lit].std() / L) if lit.any() and L > 0 else 0.0
    clipped = float((I[disk] >= 1.0 - 1e-9).mean()) if disk.any() else 0.0
    return dict(lit_median=L, clipped=clipped, relief_contrast=contrast, disk_px=int(disk.sum()))


def save_png(img: np.ndarray, path: Path) -> bool:
    u8 = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        Image.fromarray(u8).save(path)
        return True
    except Exception as exc:                          # pragma: no cover
        print(f"[note] PNG 保存に失敗: {exc}")
        return False


def _pct(a, q):
    return float(np.percentile(a, q))


def main() -> int:
    fast = "--fast" in sys.argv
    t0 = time.time()
    if not STL.exists():
        raise FileNotFoundError(f"Itokawa shape model missing: {STL} (fullseye samples download itokawa)")
    V, F = mesh.read_mesh(str(STL))
    print(f"[data] {STL.name}: 頂点 {len(V)} / 面 {len(F)} (km 単位、間引きなし)")

    # ── (d)(e) 解像度とレリーフ ──────────────────────────────────────────────
    Vr, Fr, info = build_relief_mesh(V, F, cache_dir=STL.parent)
    eb, ea = info["edge_before"] * 1e3, info["edge_after"] * 1e3
    print(f"[d] 辺長 [m] before: p5 {_pct(eb, 5):.2f} / 中央 {_pct(eb, 50):.2f} / p95 {_pct(eb, 95):.2f} / "
          f"max {eb.max():.2f} (p95/p5 {_pct(eb, 95) / _pct(eb, 5):.2f})")
    print(f"[d] 辺長 [m] after : p5 {_pct(ea, 5):.2f} / 中央 {_pct(ea, 50):.2f} / p95 {_pct(ea, 95):.2f} / "
          f"max {ea.max():.2f} (p95/p5 {_pct(ea, 95) / _pct(ea, 5):.2f}) ; 面 {info['n_faces_terrain']} "
          f"(テッセレーション {info['tess_time']:.1f}s{', cache' if info['tess_cached'] else ''})")

    def area_vol(Vx, Fx):
        t = Vx[Fx]
        c = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        return 0.5 * float(np.linalg.norm(c, axis=1).sum()), float(np.einsum("ij,ij->i", t[:, 0], c).sum() / 6)

    a0, v0 = area_vol(V, F)
    # 面積/体積はテッセレーション直後(変位前)の幾何で検査する(キャッシュ済みの .npz)。
    z = np.load(STL.parent / f"{STL.stem}_tess{int(round(TARGET_EDGE * 1e6))}mm.npz")
    a1, v1 = area_vol(z["V"], z["F"])
    area_rel, vol_rel = abs(a1 - a0) / a0, abs(v1 - v0) / abs(v0)
    sw = info["synth_weight"]
    e_at = info["e_orig_at"] * 1e3
    e_lo, e_hi = _pct(e_at, 10), _pct(e_at, 90)
    coarse, fine = e_at >= e_hi, e_at <= e_lo
    k_fine = int(np.argmin(np.abs(WAVELENGTHS - 15e-3)))      # 元辺長 4〜7 m の Nyquist をまたぐ帯
    w_coarse = float(sw[k_fine][coarse].mean())
    w_fine = float(sw[k_fine][fine].mean())
    print(f"[d] 面積 rel {area_rel:.1e} / 体積 rel {vol_rel:.1e} ; 合成重み(λ=15 m): 元モデルの粗い 10 % "
          f"(局所辺長 ≥ {e_hi:.1f} m) {w_coarse:.2f} vs 細かい 10 % (≤ {e_lo:.1f} m) {w_fine:.2f}")
    print("[d] 合成重みの範囲 [min, max] / オクターブ: " + ", ".join(
        f"{lam * 1e3:.3g} m: [{sw[k].min():.2f}, {sw[k].max():.2f}]" for k, lam in enumerate(WAVELENGTHS)))
    print(f"[d] 変位 max {info['disp'].max() * 1e3:.2f} m (Σ振幅 {AMPLITUDES.sum() * 1e3:.2f} m)")
    gp = info["gate_post"]
    # (e) 帯域: 変位に使われた重みが > 0 の頂点は必ず λ ≥ 2×局所辺長(ゲート定義どおり)
    ea_v = render3d.mesh_edge_lengths(z["V"], z["F"], per="vertex")
    band_ok = all(bool(np.all(WAVELENGTHS[k] >= 2.0 * ea_v[gp[k] > 0])) for k in range(len(WAVELENGTHS)))
    bump_frac = [float((1.0 - gp[k]).mean()) for k in range(len(WAVELENGTHS))]
    print("[e] 帯域ゲート OK=" + str(band_ok) + " ; bump へ回る割合 / オクターブ: " + ", ".join(
        f"{lam * 1e3:.3g} m: {bf:.2f}" for lam, bf in zip(WAVELENGTHS, bump_frac)))

    # ── (f) 岩 ─────────────────────────────────────────────────────────────
    b = info["boulders"]
    n_b, lam = int(b["n_boulders"]), float(b["expected"])
    print(f"[f] 岩 {n_b} 個 (期待 {lam:.0f}, 4σ={4 * np.sqrt(lam):.0f}; d_min 1 m → cap {BOULDER['max_count']} で "
          f"d_min_eff {b['d_min_effective'] * 1e3:.2f} m) ; 最大 {b['diameter'].max() * 1e3:.1f} m ; "
          f"埋没 [{b['burial'].min():.2f}, {b['burial'].max():.2f}] ; 面/岩 中央 {int(np.median(b['faces_per_boulder']))} ; "
          f"海 {info['sea_faces']} 面, 海の岩 {b['in_sea']} ; 総面数 {len(Fr)}")

    # ── (a)(b)(c) 測光と影(160 px)───────────────────────────────────────
    gsz = 160
    pose, K, sun20 = camera_and_sun(V, gsz, 20.0)
    view = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=gsz, height=gsz)
    normals = view["normals"]
    sil = view["silhouette"] > 0
    R = pose[:3, :3]
    view_cam = np.array([0.0, 0.0, 1.0])
    ls = render_shade.brdf_lommel_seeliger(normals, light=R @ sun20, view=view_cam, w=HAPKE["w"])
    lam_img = render_shade.brdf_shade(normals, light=R @ sun20, view=view_cam, model="lambert", w=HAPKE["w"])
    from scipy import ndimage as ndi
    dist = ndi.distance_transform_edt(sil)
    limb = sil & (dist <= 3)
    core = sil & (dist >= 0.5 * dist.max())
    limb_ls = float(ls[limb].mean() / ls[core].mean())
    limb_lam = float(lam_img[limb].mean() / lam_img[core].mean())
    print(f"[a] 縁/中央 比: Lommel-Seeliger {limb_ls:.3f} vs Lambert {limb_lam:.3f}")
    _, _, sun2 = camera_and_sun(V, gsz, 2.0)
    hk2 = render_shade.brdf_hapke(normals, light=R @ sun2, view=view_cam, **HAPKE)
    hk20 = render_shade.brdf_hapke(normals, light=R @ sun20, view=view_cam, **HAPKE)
    opp = float(hk2[sil].mean() / hk20[sil].mean())
    print(f"[b] 対向効果: 平均 I/F 位相 2° / 20° = {opp:.2f}")
    _, _, sun60 = camera_and_sun(Vr, gsz, 60.0)
    vis = render_shadow.shadow_raycast(Vr, Fr, sun60, pose=pose, intrinsics=K, width=gsz,
                                       height=gsz, angular_diameter_deg=0.53, samples=8)
    surf = render3d.render_mesh(Vr, Fr, pose=pose, intrinsics=K, width=gsz, height=gsz)["silhouette"] > 0
    partial = float(((vis > 0.02) & (vis < 0.98) & surf).sum() / surf.sum())
    shadowed = float(((vis < 0.5) & surf).mean())
    print(f"[c] 太陽 0.53°: 半影画素 {partial * 100:.2f} % of 受光面 ; 位相 60° の影画素 {shadowed * 100:.1f} %")

    # ── (j) bump の rms 傾斜 ≤ Hapke θ̄(未解像粗さと二重計上しない)────────
    nb_n = np.zeros((96, 96, 3))
    nb_n[..., 2] = 1.0
    gx, gy = np.meshgrid(np.arange(96) * 0.0005, np.arange(96) * 0.0005, indexing="ij")   # 0.5 m/px
    nb_P = np.stack([gx, gy, np.zeros_like(gx)], axis=-1)
    bumped = render3d.bump_normals_fbm(nb_n, nb_P, WAVELENGTHS, AMPLITUDES, seed=SEED,
                                       local_edge=np.full((96, 96), TARGET_EDGE))   # 補集合のみ
    tilt = np.degrees(np.arccos(np.clip(bumped[..., 2], -1.0, 1.0)))
    rms_tilt = float(np.sqrt((tilt ** 2).mean()))
    print(f"[j] bump(補集合: λ ≤ 2×{TARGET_EDGE * 1e3:.1f} m)の rms 傾斜 {rms_tilt:.1f}° / max {tilt.max():.1f}° "
          f"(Hapke θ̄ = {HAPKE['roughness_deg']:.0f}° が上限)")

    # ── (i) 決定的(軽いメッシュで)────────────────────────────────────────
    # 前版の単一振幅 fBm(mesh_displace_fbm)を軽い参照メッシュとして使う(比較用の旧 op)。
    Vsm, Fsm = render3d.mesh_displace_fbm(V, F, 0.0025, seed=SEED)
    Vsm, Fsm = render3d.mesh_scatter_boulders(Vsm, Fsm, density=200.0, d_min=0.008, seed=3, shape="hull",
                                              orientation="random")
    hp_, hK_, hsun_ = camera_and_sun(Vsm, 96, 55.0)
    bump = dict(wavelengths=WAVELENGTHS, amplitudes=AMPLITUDES, seed=SEED, complement_edges=True)
    kw_det = dict(pose=hp_, intrinsics=hK_, size=96, ss=1, sun=hsun_, ao_samples=16, shadow_samples=1,
                  exposure="median", bump=bump, **HAPKE)
    im1 = render_beauty.render_regolith(Vsm, Fsm, **kw_det)
    im2 = render_beauty.render_regolith(Vsm, Fsm, **kw_det)
    det = bool(np.array_equal(im1, im2))
    print(f"[i] render_regolith 決定的: {det}, 値域 [{im1.min():.3f}, {im1.max():.3f}]")
    print(f"[time] GT {time.time() - t0:.1f}s")

    # ═══ アサーション(hero 前)═══════════════════════════════════════════
    assert ea.max() <= 2.0 * TARGET_EDGE * 1e3 + 1e-9, "(d) テッセレーション後の最大辺が 2×target を超えた"
    assert abs(_pct(ea, 50) - TARGET_EDGE * 1e3) < 0.1 * TARGET_EDGE * 1e3, "(d) 中央辺長が target から 10 % 以上ずれた"
    assert area_rel < 1e-9 and vol_rel < 1e-9, "(d) テッセレーションが面積/体積を変えた"
    assert w_coarse > w_fine, "(d) 合成重みが粗い領域で細かい領域より大きくない"
    assert band_ok, "(e) 帯域ゲートが 2×局所辺長より短い波長を変位した"
    assert abs(n_b - lam) < 4 * np.sqrt(lam), f"(f) 岩の個数 {n_b} が期待 {lam:.0f} の 4σ 外"
    assert b["burial"].min() >= 0.3 - 1e-12 and b["burial"].max() <= 0.6 + 1e-12, "(f) 埋没率が [0.3, 0.6] 外"
    assert b["in_sea"] == 0, f"(f) 海に岩 {b['in_sea']} 個"
    assert limb_ls > limb_lam + 0.05, "(a) Lommel-Seeliger の縁が Lambert より明るくない"
    assert opp > 1.3, f"(b) 対向効果が弱い: {opp:.2f}"
    assert partial < 0.01, f"(c) 太陽 0.53° なのに半影が {partial * 100:.2f} %"
    assert shadowed > 0.005, "(c) 位相 60° で影が出ない"
    assert det, "(i) 決定的でない"
    assert rms_tilt < HAPKE["roughness_deg"], f"(j) bump の rms 傾斜 {rms_tilt:.1f}° が θ̄ を超えた"

    # ═══ hero ════════════════════════════════════════════════════════════
    size, ss = (256, 1) if fast else (int(os.environ.get("FULLSEYE_HERO_SIZE", "640")), 2)
    phase = 55.0
    th = time.time()
    hp, hK, hsun = camera_and_sun(Vr, size, phase, sun_azimuth_deg=135.0)
    hero = render_beauty.render_regolith(Vr, Fr, pose=hp, intrinsics=hK, size=size, ss=ss, sun=hsun,
                                         sun_angular_diameter_deg=0.53, shadow_samples=4,
                                         ao_samples=16 if fast else 24, self_illumination=1.0,
                                         albedo_variation=0.12, tint=(1.0, 0.97, 0.93),
                                         exposure="median", exposure_target=0.45, bump=bump, **HAPKE)
    t_hero = time.time() - th
    saved = save_png(hero, HERO)
    m_nat = relief_metrics(hero)
    m_am = relief_metrics(hero, match_disk_px=AMICA_DISK_PX)
    rms_slope = None
    print(f"[hero] {hero.shape} 位相角 {phase:.0f}° 太陽=左上 面 {len(Fr)} 保存={saved} {HERO} ({t_hero:.1f}s)")
    print(f"[g] 露出: 照らされた面の中央値 {m_nat['lit_median']:.3f} (目標 0.45) ; クリップ {m_nat['clipped'] * 100:.2f} % (< 0.5 %)")
    print(f"[h] レリーフコントラスト: {size} px で {m_nat['relief_contrast']:.4f} ; AMICA と同じ円盤画素数"
          f"({AMICA_DISK_PX}) に縮小して {m_am['relief_contrast']:.4f} (AMICA 実画像 {AMICA_RELIEF:.3f}, 目標 ≥ 0.03)")
    assert saved and HERO.exists()
    if not fast:
        assert abs(m_nat["lit_median"] - 0.45) < 0.02, "(g) 照らされた面の中央値が 0.45 に来ていない"
        assert m_nat["clipped"] < 0.005, f"(g) クリップ画素 {m_nat['clipped'] * 100:.2f} % ≥ 0.5 %"
        assert m_am["relief_contrast"] >= 0.03, f"(h) レリーフコントラスト {m_am['relief_contrast']:.4f} < 0.03"

    print(
        f"PASS: イトカワ実形状 {len(F)} 面(間引きなし)→ 適応テッセレーション {info['n_faces_terrain']} 面"
        f"(辺長 p95/p5 {_pct(ea, 95) / _pct(ea, 5):.2f}, 面積/体積不変)+ 帯域ゲート付きスペクトル変位"
        f"(3 m@60 m → 0.21 m@1.9 m)+ 岩 {n_b} 個(角張った凸包、べき則 -3.1、d_min_eff {b['d_min_effective'] * 1e3:.1f} m、"
        f"埋没 30–60 %、海は岩ゼロ)を Hapke(w={HAPKE['w']}, θ̄={HAPKE['roughness_deg']}°)+ 太陽 0.53° の"
        f"レイキャスト影(半影 {partial * 100:.2f} %)+ 環境光 0 + bump 補集合で描画(位相角 {phase:.0f}°、"
        f"中央値 {m_nat['lit_median']:.2f}、クリップ {m_nat['clipped'] * 100:.2f} %、レリーフ {m_am['relief_contrast']:.3f} "
        f"vs AMICA {AMICA_RELIEF})。縁/中央 LS {limb_ls:.2f} vs Lambert {limb_lam:.2f}、対向効果 {opp:.2f}×、"
        f"決定的={det}。hero → {HERO.name} ({t_hero:.0f}s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
