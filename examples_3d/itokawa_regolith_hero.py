# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 小惑星イトカワの実形状モデルを **物理ベース**で描く(Hapke 反射則 + 太陽視直径 0.53° の
レイキャスト影 + 環境光ゼロ + 地形レリーフ)。記事の hero 画像はこの op 連鎖で作る。

実世界の問題(2026-09-03 の指摘):
    記事のイトカワは「影が不自然」「表面がなめらかすぎてジャガイモ」だった。原因は
    (1) Lambert 拡散 + 環境光 0.13 + 台座つき shadow map(スタジオの照明)で、レゴリスの
    測光(縁まで明るい Lommel-Seeliger、対向効果、粗さの影で鋭い明暗境界、影は真っ黒)に
    なっていなかったこと、(2) 3000 点の点群を 72³ ボクセルで丸めた 2,600 面のメッシュを
    使っていて、起伏も岩も無かったこと。

fullseye op 連鎖(すべて ops3d に登録済み):
    mesh(STL 49,152 面) → terrain_region_mask(海/高地) → mesh_displace_fbm(数 m の起伏)
    → mesh_scatter_boulders(べき則 N(>D) ∝ D^-3.1 の岩、Michikami et al. 2008)
    → render_regolith(brdf_hapke + shadow_raycast + 環境光 0 + 一回反射近似 + 線形トーン)

GT(閉形式 / 幾何 / 統計):
    (a) 縁の明るさ  同じ法線で Lommel-Seeliger の縁帯 / 中央 比が Lambert より大きい。
    (b) 対向効果    Hapke の平均 I/F は位相角 2° が 20° の 1.5 倍超(B0=0.87, h=0.01)。
    (c) 硬い影      太陽 0.53° の半影画素は受光面の 1 % 未満、位相角 60° では影が存在。
    (d) レリーフ    変位は振幅以内 / 岩の個数は Poisson 4σ 内 / 海(weight 0)に岩ゼロ。
    (e) 決定的      render_regolith を 2 回呼んで画素完全一致。

hero 画像: examples_3d/_gallery/itokawa_regolith_hero.png(既定 640 px・SSAA 2・位相角 30°)。
``--fast`` で 256 px / ss=1(テスト用)。データ: JAXA はやぶさ / Gaskell 形状モデル(public
domain)。``fullseye samples download itokawa`` で data/sample_3d_cache/ に置く。
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
# relief in km (the STL is in km): 2.5 m fBm, boulders >= 5 m with 1000 / km^2 (~400 on 0.4 km^2)
RELIEF = dict(fbm_amplitude=0.0025, boulder_density=1000.0, boulder_d_min=0.005, seed=1)


def _rot_z(deg: float) -> np.ndarray:
    t = np.deg2rad(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])


def camera_and_sun(V, size: int, phase_deg: float, cam_dir=(0.15, -1.0, 0.35)):
    """側面やや上からのカメラと、カメラ方向を z 軸まわりに位相角だけ回した太陽方向。"""
    cen = 0.5 * (V.min(0) + V.max(0))
    rad = 0.5 * float(np.linalg.norm(V.max(0) - V.min(0)))
    cd = np.asarray(cam_dir, float)
    cd /= np.linalg.norm(cd)
    eye = cen + cd * rad * 3.2
    pose = render3d.look_at(eye, cen, up=(0.0, 0.0, 1.0))
    fov = 2.0 * np.degrees(np.arctan(0.85 / 3.2))
    K = render3d.intrinsics_from_fov(fov, size, size)
    sun = _rot_z(phase_deg) @ cd
    return pose, K, sun


def build_relief_mesh(V, F):
    """op 連鎖: 海/高地マスク → fBm 変位 → 岩の散布。戻り値 (V, F, weights, boulder sample)。"""
    w = render3d.terrain_region_mask(V, F, smooth_fraction=0.3, method="neck")
    Vd, Fd = render3d.mesh_displace_fbm(V, F, RELIEF["fbm_amplitude"], seed=RELIEF["seed"])
    smp = render3d.sample_boulders(Vd, Fd, density=RELIEF["boulder_density"],
                                   d_min=RELIEF["boulder_d_min"], seed=RELIEF["seed"] + 2,
                                   region_weights=w)
    Vb, Fb = render3d.mesh_scatter_boulders(Vd, Fd, density=RELIEF["boulder_density"],
                                            d_min=RELIEF["boulder_d_min"],
                                            seed=RELIEF["seed"] + 2, region_weights=w)
    return Vb, Fb, w, smp


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


def main() -> int:
    fast = "--fast" in sys.argv
    t0 = time.time()
    if not STL.exists():
        raise FileNotFoundError(f"Itokawa shape model missing: {STL} (fullseye samples download itokawa)")
    V, F = mesh.read_mesh(str(STL))
    print(f"[data] {STL.name}: 頂点 {len(V)} / 面 {len(F)} (km 単位)")

    # ── (d) レリーフ ─────────────────────────────────────────────────────────
    Vr, Fr, wts, smp = build_relief_mesh(V, F)
    Vd, _ = render3d.mesh_displace_fbm(V, F, RELIEF["fbm_amplitude"], seed=RELIEF["seed"])
    disp_max = float(np.linalg.norm(Vd - V, axis=1).max())
    n_b = int(smp["diameter"].size)
    lam = float(smp["expected"])
    sea_faces = int((wts == 0).sum())
    # 海に岩が無い: 岩の中心に最も近い面が海でないことを面重心の最近傍で確認
    fc = V[F].mean(axis=1)
    from scipy.spatial import cKDTree
    _, near = cKDTree(fc).query(smp["centre"])
    n_in_sea = int((wts[near] == 0).sum())
    print(f"[d] fBm 変位 max {disp_max*1000:.2f} m (振幅 {RELIEF['fbm_amplitude']*1000:.1f} m) ; "
          f"岩 {n_b} 個 (期待 {lam:.0f}, 4σ={4*np.sqrt(lam):.0f}) ; 海 {sea_faces} 面, 海の岩 {n_in_sea} ; "
          f"最大岩 {smp['diameter'].max()*1000:.0f} m")

    # ── (a)(b)(c) 測光と影(160 px、実メッシュ)────────────────────────────
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
    print(f"[c] 太陽 0.53°: 半影画素 {partial*100:.2f} % of 受光面 ; 位相 60° の影画素 {shadowed*100:.1f} %")

    # ── (e) 決定的 ────────────────────────────────────────────────────────
    hp, hK, hsun = camera_and_sun(Vr, 96, 30.0)
    im1 = render_beauty.render_regolith(Vr, Fr, pose=hp, intrinsics=hK, size=96, ss=1, sun=hsun,
                                        ao_samples=16, shadow_samples=1, **HAPKE)
    im2 = render_beauty.render_regolith(Vr, Fr, pose=hp, intrinsics=hK, size=96, ss=1, sun=hsun,
                                        ao_samples=16, shadow_samples=1, **HAPKE)
    det = bool(np.array_equal(im1, im2))
    print(f"[e] render_regolith 決定的: {det}, 値域 [{im1.min():.3f}, {im1.max():.3f}]")
    print(f"[time] GT {time.time() - t0:.1f}s")

    # ═══ アサーション ═════════════════════════════════════════════════════
    assert disp_max <= RELIEF["fbm_amplitude"] + 1e-12, "(d) 変位が振幅を超えた"
    assert abs(n_b - lam) < 4 * np.sqrt(lam), f"(d) 岩の個数 {n_b} が期待 {lam:.0f} の 4σ 外"
    assert n_in_sea == 0, f"(d) 海に岩 {n_in_sea} 個"
    assert limb_ls > limb_lam + 0.05, "(a) Lommel-Seeliger の縁が Lambert より明るくない"
    assert opp > 1.5, f"(b) 対向効果が弱い: {opp:.2f}"
    assert partial < 0.01, f"(c) 太陽 0.53° なのに半影が {partial*100:.2f} %"
    assert shadowed > 0.005, "(c) 位相 60° で影が出ない"
    assert det, "(e) 決定的でない"

    # ═══ hero ════════════════════════════════════════════════════════════
    size, ss = (256, 1) if fast else (int(os.environ.get("FULLSEYE_HERO_SIZE", "640")), 2)
    th = time.time()
    hp, hK, hsun = camera_and_sun(Vr, size, 30.0)
    hero = render_beauty.render_regolith(Vr, Fr, pose=hp, intrinsics=hK, size=size, ss=ss, sun=hsun,
                                         sun_angular_diameter_deg=0.53, shadow_samples=4,
                                         ao_samples=32, self_illumination=1.0,
                                         albedo_variation=0.12, tint=(1.0, 0.97, 0.93), **HAPKE)
    saved = save_png(hero, HERO)
    print(f"[hero] {hero.shape} 位相角 30° 保存={saved} {HERO} ({time.time() - th:.1f}s)")
    assert saved and HERO.exists()

    print(
        f"PASS: イトカワ実形状 {len(F)} 面 + 起伏 {RELIEF['fbm_amplitude']*1000:.1f} m + 岩 {n_b} 個"
        f"(べき則 -3.1, 海は岩ゼロ)を Hapke(w={HAPKE['w']}, θ̄={HAPKE['roughness_deg']}°)+ "
        f"太陽 0.53° のレイキャスト影(半影 {partial*100:.2f} %)+ 環境光 0 で描画。"
        f"縁/中央 LS {limb_ls:.2f} vs Lambert {limb_lam:.2f}、対向効果 {opp:.2f}×、決定的={det}。"
        f"hero → {HERO.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
