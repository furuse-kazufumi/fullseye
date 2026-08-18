"""evis 歩行知覚 — Fullseye を駆使して「どこに・安全に踏めるか」を視覚から計画する.

evis の歩行(脚・物理・torque-twin)は gaitlab / hillco 側。Fullseye はその「目」=知覚:
デプス/LiDAR で見た地形 → 高さ場 → 踏破可能性 → 踏み場候補 → 支持多角形/COM 安定余裕。
本デモは Fullseye の歩行知覚 facade(fs.terrain / fs.locomotion)を一気通貫で回し、
gaitlab に渡せる「踏み場プラン」を出す。物理歩行そのものは回さない(別プロジェクト)。

  PYTHONPATH=. py -3.11 spikes/evis_walk_perception.py          # 2D パネル + 3D(.ply)+ 踏み場 JSON
  PYTHONPATH=. py -3.11 spikes/evis_walk_perception.py --show   # + Open3D 対話 3D
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np

warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
for _jp in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if _jp in {f.name for f in font_manager.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _jp
        break
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt  # noqa: E402

import fullseye as fs  # noqa: E402

_OUT = os.path.join(os.path.dirname(__file__), "out_gallery")
CELL = 0.03


def evis_terrain(seed=0):
    """evis のデプス/LiDAR が見る地形の点群: 平地 + 段差(curb)+ 傾斜 + 障害物。"""
    rng = np.random.default_rng(seed)
    xs, ys = np.meshgrid(np.linspace(0, 2, 140), np.linspace(0, 2, 140))
    z = np.zeros_like(xs)
    z[xs > 1.2] += 0.12                       # 段差 0.12m(またぐ/登る対象)
    z += ys * 0.05                            # ゆるい傾斜
    z += 0.01 * np.sin(xs * 8) * (xs < 1.2)   # 微細な凹凸
    ground = np.column_stack([xs.ravel(), ys.ravel(), z.ravel()])
    obs = rng.normal([0.55, 1.5, 0.3], [0.05, 0.05, 0.15], (250, 3))   # 障害物(踏めない)
    return np.vstack([ground + rng.normal(0, 0.003, ground.shape), obs])


def perceive(cloud):
    """Fullseye 歩行知覚チェーン: 点群 → 高さ場 → slope/rough/normals → traversability →
    foothold → obstacles/step-edges → 踏み場候補。"""
    grid, extent = fs.elevation_map(cloud, cell=CELL, agg="max")
    slope = fs.slope_map(grid, cell=CELL)
    rough = fs.roughness_map(grid, window=3)
    trav = fs.traversability(grid, cell=CELL, max_step=0.08, max_slope=0.5)
    score = fs.foothold_score(grid, cell=CELL)
    obst_mask, _ = fs.detect_obstacles(grid, cell=CELL, clearance=0.1, extent=extent)
    edge_mask, _ = fs.step_edges(grid, cell=CELL, min_rise=0.05)
    cands = fs.foothold_candidates(grid, cell=CELL, extent=extent,
                                   min_score=0.55, min_dist=0.18, max_n=16)
    return dict(grid=grid, extent=extent, slope=slope, rough=rough, trav=trav,
                score=score, obst=obst_mask, edges=edge_mask, cands=cands)


def plan_stance(cands):
    """踏み場候補から 4 本足の安定な立脚を選び、支持多角形と COM 余裕を計算(fs.locomotion)。"""
    if len(cands) < 4:
        return None
    pts = np.array([[c["xy"][0], c["xy"][1], 0.0] for c in cands])
    # x が近い 4 点(前後左右に広がる立脚)を重心近くから選ぶ
    ctr = pts[:, :2].mean(0)
    order = np.argsort(np.hypot(pts[:, 0] - ctr[0], pts[:, 1] - ctr[1]))
    feet = pts[order[:4]]
    com = feet[:, :2].mean(0)
    sp = fs.support_polygon(feet)
    margin = fs.com_support_margin(com, feet)
    return dict(feet=feet, com=com, support=sp, margin=float(margin))


def panels(P, stance, path):
    """2D 歩行知覚パネル(HDevelop 風の見て確かめる層)。"""
    ext = P["extent"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    show = lambda ax, img, t, cmap="viridis", **k: (
        ax.imshow(np.asarray(img), origin="lower", extent=ext, cmap=cmap, **k),
        ax.set_title(t, fontsize=10))
    show(axes[0, 0], P["grid"], "① 高さ場 elevation_map(点群→2.5D)", "terrain")
    show(axes[0, 1], P["slope"], "② 傾斜 slope_map[deg]", "magma")
    show(axes[0, 2], P["trav"].astype(float), "③ 踏破可能 traversability(明=歩ける)", "Greens")
    ax = axes[1, 0]
    show(ax, P["score"], "④ 踏み場スコア foothold_score + 候補", "cividis", vmin=0, vmax=1)
    for c in P["cands"]:
        ax.plot(c["xy"][0], c["xy"][1], "o", color="red", ms=6, mec="white")
    ax = axes[1, 1]
    haz = np.zeros((*P["obst"].shape, 3))
    haz[np.asarray(P["obst"], bool)] = (1, 0.2, 0.1)      # 障害物=赤
    haz[np.asarray(P["edges"], bool)] = (1, 0.8, 0.1)     # 段差エッジ=黄
    ax.imshow(haz, origin="lower", extent=ext)
    ax.set_title("⑤ 危険 detect_obstacles(赤)+ step_edges(黄)", fontsize=10)
    ax = axes[1, 2]
    ax.imshow(P["grid"], origin="lower", extent=ext, cmap="terrain", alpha=0.6)
    if stance:
        f = stance["feet"]; v = np.asarray(stance["support"]["vertices"])
        ax.fill(v[:, 0], v[:, 1], alpha=0.3, color="cyan", label="支持多角形")
        ax.plot(f[:, 0], f[:, 1], "s", color="blue", ms=10, label="立脚(4 足)")
        ax.plot(*stance["com"], "*", color="magenta", ms=18, label="COM")
        ok = "安定" if stance["margin"] > 0 else "不安定"
        ax.set_title(f"⑥ 立脚 support_polygon + COM 余裕 {stance['margin']:+.2f}m({ok})", fontsize=10)
        ax.legend(fontsize=8, loc="upper right")
    for a in axes.ravel():
        a.set_xlabel("x[m]", fontsize=8); a.set_ylabel("y[m]", fontsize=8)
    fig.suptitle("evis 歩行知覚 — Fullseye が視覚から『どこに安全に踏めるか』を計画", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    return path


def export_plan(P, stance, path):
    """gaitlab / 歩行制御へ渡す踏み場プラン(JSON)。"""
    plan = {
        "cell": CELL, "extent": list(P["extent"]),
        "footholds": [{"xy": list(c["xy"]), "score": round(c["score"], 3)} for c in P["cands"]],
        "traversable_fraction": round(float(np.asarray(P["trav"]).mean()), 3),
        "stance": None if stance is None else {
            "feet_xy": stance["feet"][:, :2].tolist(), "com_xy": stance["com"].tolist(),
            "support_area": round(float(stance["support"]["area"]), 4),
            "com_margin": round(stance["margin"], 4),
            "stable": bool(stance["margin"] > 0)},
        "note": "Fullseye 知覚が生成。物理歩行(踏み替え/torque)は gaitlab/hillco が実行。",
    }
    json.dump(plan, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return path


def show_3d(cloud, P, stance):
    import viewer3d as v3d
    if not v3d.available():
        return False
    geoms = v3d.to_geometries(cloud, "point_cloud")
    for c in P["cands"]:                                  # 踏み場候補=緑の球
        import open3d as o3d
        s = o3d.geometry.TriangleMesh.create_sphere(radius=0.03)
        s.translate([c["xy"][0], c["xy"][1], 0.02]); s.paint_uniform_color([0.1, 0.9, 0.2])
        geoms.append(s)
    if stance:
        for f in stance["feet"]:
            import open3d as o3d
            b = o3d.geometry.TriangleMesh.create_box(0.06, 0.06, 0.02)
            b.translate([f[0] - 0.03, f[1] - 0.03, 0]); b.paint_uniform_color([0.1, 0.3, 0.9])
            geoms.append(b)
    return v3d.show_interactive(geoms, title="evis 歩行知覚 — 地形 + 踏み場(緑)+ 立脚(青)")


def main():
    os.makedirs(_OUT, exist_ok=True)
    print("== evis 歩行知覚(Fullseye)==")
    cloud = evis_terrain()
    print(f"地形点群(evis のデプス/LiDAR 相当): {len(cloud)} 点")
    P = perceive(cloud)
    print(f"知覚: 高さ場 {P['grid'].shape} / 踏破可能 {float(np.asarray(P['trav']).mean())*100:.0f}% / "
          f"踏み場候補 {len(P['cands'])} / 障害物セル {int(np.asarray(P['obst']).sum())}")
    stance = plan_stance(P["cands"])
    if stance:
        print(f"立脚: 支持面積 {stance['support']['area']:.3f}m^2 / COM 余裕 {stance['margin']:+.3f}m "
              f"({'安定' if stance['margin']>0 else '不安定'})")
    png = panels(P, stance, os.path.join(_OUT, "evis_walk_perception.png"))
    print(f"[2D パネル] {png}")
    js = export_plan(P, stance, os.path.join(_OUT, "evis_foothold_plan.json"))
    print(f"[踏み場プラン JSON] {js}  ← gaitlab/歩行制御へ渡す")
    if "--show" in sys.argv:
        print("Open3D 3D を起動(地形 + 踏み場緑 + 立脚青、mouse ナビ)…")
        print("  ->", "OK" if show_3d(cloud, P, stance) else "起動失敗(desktop GL 要)")
    else:
        print("対話 3D: PYTHONPATH=. py -3.11 spikes/evis_walk_perception.py --show")


if __name__ == "__main__":
    main()
