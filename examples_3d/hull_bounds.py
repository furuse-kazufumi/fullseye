# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 点群を「囲む」プリミティブ — 凸包 / OBB / AABB / 最小包含球 (hull & bounds).

実世界の問題:
    ロボットの把持計画や衝突判定・検査では、まず「その物体はどこに・どんな向きで・
    どれだけの大きさで存在するか」を粗く一発で掴みたい。テンプレートも学習も要らず、
    生の点群 (N,3) だけから「囲む形」を返す 4 つの基本メトロロジーを検証する:

      - convex_hull_3d(points)        -> (verts, faces)         凸包メッシュ
      - oriented_bounding_box(points) -> {center,axes,extents,corners}  向き付き箱(OBB)
      - aabb(points)                  -> {min,max}              軸整列箱(AABB)
      - min_enclosing_sphere(points)  -> {center,radius}        最小包含球

なぜ検証できるか(GT):
    - 単位立方体の 8 頂点の凸包は「一辺 1 の立方体」そのもの。体積=1.0・頂点=8・三角面=12 が
      幾何だけで厳密に決まる(メッシュから独立に体積を再計算して確かめる)。
    - 既知寸法 (a,b,c) の箱を既知回転 R で回した点群なら、OBB が復元する extents(ソート後)は
      (a,b,c) のソートに一致し、中心も箱中心に一致するはずだ。
    - 既知の球面上の点なら、最小包含球の半径は球半径 r0(= 直径/2)に一致し、全点を内包する。

beat-the-null(下駄を履かせない基準):
    - OBB vs AABB: 座標軸に対して**傾いた**箱では、軸整列の AABB は必ず過大になる。OBB は
      物体の向きに追従して密着するので、OBB 体積 < AABB 体積 を判別的に示す(向き適合の効き)。
    - 最小包含球 vs 素朴球: 「重心中心 + 最遠点半径」の素朴球は、重心が密集塊に引かれる非対称な
      点群(塊 + 遠い外れ点)では中心が偏り半径が過大になる。最小包含球は中心を寄せて半径を詰める
      (常に素朴球以下、かつ全点内包)。さらに「重心中心 + 平均距離半径」の“詰めすぎ”素朴球は
      外れ点を**取りこぼす**(内包に失敗)ことを示し、安全側での優位も確かめる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hull3d import (  # noqa: E402  (sys.path 調整後に import)
    aabb,
    convex_hull_3d,
    min_enclosing_sphere,
    oriented_bounding_box,
)


# ═══════════════════════════════════════════════════════════════════════════
# シーン生成ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def euler_rotation(rx: float, ry: float, rz: float) -> np.ndarray:
    """既知の Euler 角 (rx,ry,rz) から回転行列 R (3,3) を作る(Z@Y@X の順)。"""
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def box_grid(dims, R, center, per_axis=(7, 6, 5)) -> np.ndarray:
    """寸法 dims=(a,b,c) の直方体を格子点で満たし、回転 R・並進 center を掛けた点群を返す。

    各軸を -半幅..+半幅 で等間隔にサンプルする(端点=8 隅を必ず含む)。格子は箱中心について
    対称なので共分散が箱フレームで対角になり、PCA が箱の主軸を厳密に復元できる(GT の要)。
    """
    a, b, c = dims
    na, nb, nc = per_axis
    xs = np.linspace(-a / 2, a / 2, na)
    ys = np.linspace(-b / 2, b / 2, nb)
    zs = np.linspace(-c / 2, c / 2, nc)
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    local = np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()])
    return local @ R.T + np.asarray(center, float)


def unit_cube_corners() -> np.ndarray:
    """単位立方体 [0,1]^3 の 8 隅 (8,3)。"""
    return np.array([[x, y, z] for x in (0.0, 1.0)
                     for y in (0.0, 1.0) for z in (0.0, 1.0)], dtype=float)


def sphere_surface(n, radius, center, seed=0) -> np.ndarray:
    """半径 radius・中心 center の球面上に (n,3) 点をフィボナッチ球でほぼ一様に生成。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    theta = np.pi * (1.0 + np.sqrt(5.0)) * i
    unit = np.column_stack([np.sin(phi) * np.cos(theta),
                            np.sin(phi) * np.sin(theta),
                            np.cos(phi)])
    return radius * unit + np.asarray(center, float)


def cluster_with_outlier(seed=1) -> np.ndarray:
    """密集塊 + 遠い外れ点。重心が塊へ引かれ、素朴な外接球が過大/取りこぼしになる構成。"""
    rng = np.random.default_rng(seed)
    cluster = rng.normal(0.0, 0.35, (300, 3))
    outlier = np.array([[10.0, 0.0, 0.0]])
    return np.vstack([cluster, outlier])


# ═══════════════════════════════════════════════════════════════════════════
# 幾何ユーティリティ(GT 検証・描画用、op には依存しない独立実装)
# ═══════════════════════════════════════════════════════════════════════════
def mesh_volume(verts: np.ndarray, faces: np.ndarray) -> float:
    """三角形メッシュの囲む体積を faces から独立に再計算(発散定理・面を外向きに整えて総和)。

    凸多面体なので重心は内部。各三角面の法線が重心から外を向くよう頂点順を整え、原点起点の
    符号付き四面体体積 dot(v0, v1×v2)/6 を総和する(向きが一貫すれば原点位置に依らない)。
    """
    ctr = verts.mean(axis=0)
    vol = 0.0
    for a, b, c in faces:
        v0, v1, v2 = verts[a], verts[b], verts[c]
        n = np.cross(v1 - v0, v2 - v0)
        face_ctr = (v0 + v1 + v2) / 3.0
        if np.dot(n, face_ctr - ctr) < 0.0:      # 外向きに揃える
            v1, v2 = v2, v1
        vol += np.dot(v0, np.cross(v1, v2)) / 6.0
    return abs(float(vol))


def box_edges(corners: np.ndarray):
    """8 隅 (8,3) → 12 辺の (始点, 終点) 対リスト。隅 index が 1 ビットだけ違う対を結ぶ。"""
    edges = []
    for i in range(8):
        for j in range(i + 1, 8):
            if bin(i ^ j).count("1") == 1:
                edges.append((corners[i], corners[j]))
    return edges


def aabb_corners(mn: np.ndarray, mx: np.ndarray) -> np.ndarray:
    """AABB の min/max → 8 隅 (8,3)(OBB corners と同じ ±順序)。"""
    return np.array([[mx[0] if bx else mn[0],
                      mx[1] if by else mn[1],
                      mx[2] if bz else mn[2]]
                     for bx in (0, 1) for by in (0, 1) for bz in (0, 1)], float)


def vol3(extents) -> float:
    """3 辺長の積 = 箱体積。"""
    e = np.asarray(extents, float)
    return float(e[0] * e[1] * e[2])


# ═══════════════════════════════════════════════════════════════════════════
# 描画(matplotlib Agg、無ければスキップ)
# ═══════════════════════════════════════════════════════════════════════════
def render_png(path: Path, box_pts, obb, ab, hull_verts, hull_faces,
               clu_pts, mes, naive_c, naive_r) -> bool:
    """凸包 / OBB vs AABB / 最小包含球 vs 素朴球 の 3 パネル図を保存。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: F401
    except Exception:
        return False

    fig = plt.figure(figsize=(16.5, 5.4))

    # --- パネル A: 凸包メッシュ(回転箱の点群 → 8 隅の凸包)---
    axA = fig.add_subplot(1, 3, 1, projection="3d")
    axA.scatter(box_pts[:, 0], box_pts[:, 1], box_pts[:, 2],
                s=6, c="#3b6ea5", alpha=0.35, label="点群 (N=%d)" % len(box_pts))
    axA.plot_trisurf(hull_verts[:, 0], hull_verts[:, 1], hull_verts[:, 2],
                     triangles=hull_faces, color="#e08a1e", alpha=0.28,
                     edgecolor="#b5670c", linewidth=0.6)
    axA.set_title("convex_hull_3d\n凸包 = 頂点 %d・三角面 %d(内部点を除外)"
                  % (len(hull_verts), len(hull_faces)), fontsize=10)
    axA.legend(loc="upper left", fontsize=8)

    # --- パネル B: OBB(密着)vs AABB(過大)---
    axB = fig.add_subplot(1, 3, 2, projection="3d")
    axB.scatter(box_pts[:, 0], box_pts[:, 1], box_pts[:, 2],
                s=6, c="#3b6ea5", alpha=0.5)
    for p, q in box_edges(ab_corners := aabb_corners(ab["min"], ab["max"])):
        axB.plot(*zip(p, q), c="#9aa7b0", lw=1.0, ls="--")
    for p, q in box_edges(obb["corners"]):
        axB.plot(*zip(p, q), c="#c0392b", lw=2.0)
    axB.set_title("oriented_bounding_box vs aabb\nOBB 体積 %.2f  <  AABB 体積 %.2f"
                  % (vol3(obb["extents"]),
                     vol3(ab["max"] - ab["min"])), fontsize=10)
    axB.plot([], [], c="#c0392b", lw=2.0, label="OBB(密着)")
    axB.plot([], [], c="#9aa7b0", lw=1.0, ls="--", label="AABB(過大)")
    axB.legend(loc="upper left", fontsize=8)

    # --- パネル C: 最小包含球(密着)vs 素朴球(過大)---
    axC = fig.add_subplot(1, 3, 3, projection="3d")
    axC.scatter(clu_pts[:, 0], clu_pts[:, 1], clu_pts[:, 2],
                s=7, c="#3b6ea5", alpha=0.6)
    u = np.linspace(0, 2 * np.pi, 28)
    v = np.linspace(0, np.pi, 16)
    su = np.outer(np.cos(u), np.sin(v))
    sv = np.outer(np.sin(u), np.sin(v))
    sw = np.outer(np.ones_like(u), np.cos(v))
    mc, mr = np.asarray(mes["center"]), float(mes["radius"])
    axC.plot_wireframe(mc[0] + mr * su, mc[1] + mr * sv, mc[2] + mr * sw,
                       color="#27865a", linewidth=0.5, rstride=2, cstride=2)
    axC.plot_wireframe(naive_c[0] + naive_r * su, naive_c[1] + naive_r * sv,
                       naive_c[2] + naive_r * sw, color="#9aa7b0",
                       linewidth=0.4, rstride=3, cstride=3)
    axC.set_title("min_enclosing_sphere vs 素朴球\n最小 r=%.2f  <  素朴 r=%.2f"
                  % (mr, naive_r), fontsize=10)
    axC.plot([], [], c="#27865a", label="最小包含球")
    axC.plot([], [], c="#9aa7b0", label="素朴球(重心+最遠)")
    axC.legend(loc="upper left", fontsize=8)

    fig.suptitle("hull3d — 凸包・バウンディングボリューム(点群を囲む基本メトロロジー)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# メイン: GT 検証 + beat-null + 描画
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # ---- 入力の健全性(退化データで偽の成功を出さない)----
    cube = unit_cube_corners()
    if cube.shape != (8, 3):
        raise ValueError("単位立方体の生成に失敗(退化入力)。")

    # ============================================================
    # (1) convex_hull_3d — 単位立方体の凸包 = 立方体(体積1・頂点8・面12)
    # ============================================================
    hv, hf = convex_hull_3d(cube)
    if hv.ndim != 2 or hv.shape[1] != 3 or hf.ndim != 2 or hf.shape[1] != 3:
        raise ValueError(f"凸包メッシュの形が不正: verts {hv.shape}, faces {hf.shape}")
    hull_vol = mesh_volume(hv, hf)                       # メッシュから独立に体積再計算
    # 返された 8 頂点が立方体の 8 隅集合と一致するか(集合として)
    corner_set = {tuple(np.round(p, 9)) for p in cube}
    hv_set = {tuple(np.round(p, 9)) for p in hv}

    print(f"[GT] convex_hull_3d(unit cube): verts={len(hv)} faces={len(hf)} "
          f"mesh_volume={hull_vol:.10f}")

    assert len(hv) == 8, f"凸包頂点数が 8 でない: {len(hv)}"
    assert len(hf) == 12, f"凸包三角面数が 12 でない: {len(hf)}"
    assert hv_set == corner_set, "凸包頂点が立方体 8 隅と一致しない"
    assert abs(hull_vol - 1.0) < 1e-9, f"凸包体積が 1.0 でない: {hull_vol:.10f}"

    # ============================================================
    # (2) OBB — 既知寸法の箱を既知回転で回した点群から寸法・中心を復元
    # ============================================================
    dims = (4.0, 2.5, 1.2)
    R = euler_rotation(0.6, 0.4, 0.3)
    center_true = np.array([5.0, 3.0, 2.0])
    box_pts = box_grid(dims, R, center_true, per_axis=(7, 6, 5))

    obb = oriented_bounding_box(box_pts)
    ext_sorted = np.sort(obb["extents"])
    dims_sorted = np.sort(dims)
    ext_err = float(np.max(np.abs(ext_sorted - dims_sorted)))
    center_err = float(np.linalg.norm(obb["center"] - center_true))
    obb_vol = vol3(obb["extents"])

    print(f"[GT] OBB extents(sorted)={np.round(ext_sorted, 6)} "
          f"true(sorted)={np.round(dims_sorted, 6)} max_err={ext_err:.2e}")
    print(f"[GT] OBB center={np.round(obb['center'], 6)} "
          f"true={center_true} err={center_err:.2e}  volume={obb_vol:.4f} "
          f"(true {vol3(dims):.4f})")

    # OBB の隅が全点を内包(バウンディングボリュームの定義)
    axes = obb["axes"]
    proj = (box_pts - obb["center"]) @ axes.T            # 主軸系へ射影
    half = obb["extents"] / 2.0
    obb_contains = bool(np.all(np.abs(proj) <= half[None, :] + 1e-9))

    assert ext_err < 1e-6, f"OBB extents 復元誤差が大きい: {ext_err:.2e}"
    assert center_err < 1e-6, f"OBB center 復元誤差が大きい: {center_err:.2e}"
    assert abs(obb_vol - vol3(dims)) < 1e-6, f"OBB 体積が真値と不一致: {obb_vol:.6f}"
    assert obb_contains, "OBB が全点を内包していない"

    # 凸包の beat-null(おまけ): 回転箱 210 点でも凸包頂点は 8(内部点を除外)。
    # 「全点が境界」という素朴基準(N 頂点)を判別的に下回る。
    hv2, _ = convex_hull_3d(box_pts)
    print(f"[GT] convex_hull_3d(rotated box, N={len(box_pts)}) -> hull verts={len(hv2)}")
    assert len(hv2) == 8, f"回転箱の凸包頂点が 8 でない: {len(hv2)}"
    assert len(hv2) < len(box_pts), "凸包が内部点を除外できていない(全点が頂点)"

    # ============================================================
    # (3) AABB + beat-null: 回転箱では AABB 体積 > OBB 体積(軸整列は過大)
    # ============================================================
    ab = aabb(box_pts)
    aabb_ext = ab["max"] - ab["min"]
    aabb_vol = vol3(aabb_ext)
    # AABB は自明に全点内包(定義)/ OBB より緩いことを判別的に示す
    aabb_contains = bool(np.all(box_pts >= ab["min"] - 1e-9) and
                         np.all(box_pts <= ab["max"] + 1e-9))
    print(f"[null] AABB extents={np.round(aabb_ext, 4)} volume={aabb_vol:.4f}")
    print(f"[beat] OBB volume {obb_vol:.4f}  <  AABB volume {aabb_vol:.4f}  "
          f"(比 {obb_vol / aabb_vol:.3f})")

    assert aabb_contains, "AABB が全点を内包していない(実装バグ)"
    assert obb_vol < aabb_vol, \
        f"OBB が AABB より小さくない(beat-null 失敗): {obb_vol:.4f} vs {aabb_vol:.4f}"
    assert obb_vol < 0.9 * aabb_vol, \
        f"OBB の AABB に対する優位が小さすぎる: 比 {obb_vol / aabb_vol:.3f}"

    # ============================================================
    # (4) min_enclosing_sphere — 既知球で半径復元 + 全点内包
    # ============================================================
    r0 = 3.0
    sph_center = np.array([1.0, 2.0, 3.0])
    sph_pts = sphere_surface(800, r0, sph_center, seed=0)
    mes_s = min_enclosing_sphere(sph_pts)
    ms_c, ms_r = np.asarray(mes_s["center"]), float(mes_s["radius"])
    ds = np.linalg.norm(sph_pts - ms_c, axis=1)
    all_in_s = bool(np.all(ds <= ms_r + 1e-9))
    diam = 0.0
    # 直径(最遠点対)は球面サンプルでは ~2*r0。r <= 直径/2 * (1+微小) で「≈直径/2」を確認。
    # 全ペアは重いので、最小球中心からの最遠点とそのまた最遠点で近似(下界として十分)。
    j = int(np.argmax(ds)); k = int(np.argmax(np.linalg.norm(sph_pts - sph_pts[j], axis=1)))
    diam = float(np.linalg.norm(sph_pts[j] - sph_pts[k]))
    print(f"[GT] min_enclosing_sphere(sphere r0={r0}): center={np.round(ms_c, 4)} "
          f"(true {sph_center}) r={ms_r:.5f}  diam/2={diam / 2:.5f}  all_inside={all_in_s}")

    assert all_in_s, "最小包含球が全点を内包していない(球面 GT)"
    assert np.linalg.norm(ms_c - sph_center) < 5e-3, \
        f"最小包含球の中心が球中心とずれている: {np.linalg.norm(ms_c - sph_center):.4f}"
    assert abs(ms_r - r0) < 1e-2, f"最小包含球の半径が r0 と不一致: {ms_r:.5f} vs {r0}"
    # 直径/2 は理論下界(r >= 直径/2)。近似解が下界の (1+1%) 以内 = ほぼ最小(≈直径/2)。
    assert ms_r <= diam / 2.0 * 1.01, \
        f"半径が直径/2 を有意に超過(過大): r={ms_r:.5f} > diam/2={diam / 2:.5f}"

    # ============================================================
    # (5) 最小包含球の beat-null: 非対称点群で素朴球より小さく、かつ安全側
    # ============================================================
    clu = cluster_with_outlier(seed=1)
    mes_c = min_enclosing_sphere(clu)
    mc, mr = np.asarray(mes_c["center"]), float(mes_c["radius"])
    dc = np.linalg.norm(clu - mc, axis=1)
    mes_all_in = bool(np.all(dc <= mr + 1e-9))

    # null-1(過大): 重心中心 + 最遠点半径。全点内包はするが半径が過大。
    naive_c = clu.mean(axis=0)
    naive_r = float(np.linalg.norm(clu - naive_c, axis=1).max())
    # null-2(取りこぼし): 重心中心 + 平均距離半径。詰めすぎて外れ点を内包できない。
    tight_r = float(np.linalg.norm(clu - naive_c, axis=1).mean())
    tight_uncovered = int(np.sum(np.linalg.norm(clu - naive_c, axis=1) > tight_r + 1e-9))

    print(f"[beat] cluster+outlier: MES r={mr:.4f} (all_in={mes_all_in})  "
          f"素朴(重心+最遠) r={naive_r:.4f}  素朴(重心+平均) r={tight_r:.4f} "
          f"取りこぼし {tight_uncovered} 点")

    assert mes_all_in, "最小包含球が全点を内包していない(非対称 GT)"
    assert mr < naive_r, \
        f"最小包含球が素朴球(重心+最遠)を上回れていない: {mr:.4f} vs {naive_r:.4f}"
    assert mr <= naive_r, "最小包含球は素朴球以下であるべき(理論)"
    assert tight_uncovered > 0, \
        "詰めすぎ素朴球が取りこぼしを起こす構成になっていない(シーン設計を見直す)"

    # ============================================================
    # 描画(結果を PNG に)
    # ============================================================
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "hull_bounds.png"
    box_hull_v, box_hull_f = convex_hull_3d(box_pts)     # 回転箱の凸包メッシュ(描画用)
    drew = render_png(out_png, box_pts, obb, ab,
                      box_hull_v, box_hull_f, clu, mes_c, naive_c, naive_r)
    if drew:
        print(f"[draw] gallery PNG 保存: {out_png}")
    else:
        print("[draw] matplotlib 不在のため PNG はスキップ(GT アサートは全て実施済み)")

    print(
        "PASS: 単位立方体の凸包=体積 %.4f・頂点 %d・面 %d を厳密復元。"
        "回転箱で OBB extents 誤差 %.1e・中心誤差 %.1e、"
        "OBB 体積 %.2f が AABB 体積 %.2f を判別的に下回った(比 %.2f)。"
        "球面から最小包含球 r=%.3f(真値 %.1f・全点内包)。"
        "非対称点群で最小包含球 r=%.3f が素朴球 r=%.3f を下回り(beat-null 差 %.3f)、"
        "詰めすぎ素朴球は %d 点を取りこぼした。"
        % (hull_vol, len(hv), len(hf), ext_err, center_err,
           obb_vol, aabb_vol, obb_vol / aabb_vol,
           ms_r, r0, mr, naive_r, naive_r - mr, tight_uncovered)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
