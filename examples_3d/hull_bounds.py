# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 点群を「囲む」プリミティブ — 新規 op = 最小包含球 (hull & bounds).

正直な新規性の開示(重要):
    点群の外接プリミティブの大半は、既に fullseye の公開 API として存在する。この事例が
    実際に検証する**新規 op は最小包含球 ``min_enclosing_sphere`` の 1 本だけ**であり、
    残りの外接プリミティブは既存の公開関数をそのまま呼んで「家族の文脈」として並べて示す
    (新規ではないことを明示する):

      - convex_hull(points)  = fs.convex_hull(実体 meshrepair.convex_hull)  ★既存公開op
      - aabb(points)         = fs.aabb(実体 pcseg.aabb)                       ★既存公開op
      - obb(points)          = fs.obb(実体 pcseg.obb)                         ★既存公開op
      - min_enclosing_sphere(points) -> {center,radius}   ← ★この事例で足す唯一の新規 op

    「全点を内包する最小の球」(minimum enclosing ball, MEB)は、既存の
    ``match3d.fit_sphere_3d``(点が球**面上**にある前提の最小二乗フィット)や
    ``ransac_sphere`` / ``match3d.hough_sphere_3d``(球の検出)とは**別の最適化問題**で、
    repo に不在だった。把持前クリアランス・衝突球・視錐台カリング等、「取りこぼしゼロで
    最小の余白」を欲しい場面に対応する。

なぜ検証できるか(GT):
    - [新規 op] 既知の球面上の点なら、最小包含球の半径は球半径 r0(= 直径/2)に一致し、
      全点を内包する。さらに「中心からの最遠点対」で測った直径の半分は理論下界
      (r >= 直径/2)であり、近似解がこの下界のごく近傍にあることで「ほぼ最小」を裏付ける
      (弱い素朴基準に勝つだけの見せかけでないことを示す)。
    - [既存 op(参考)] 単位立方体の 8 頂点の凸包は「一辺 1 の立方体」(体積=1・頂点8・面12)。
      既知寸法 (a,b,c) を既知回転で回した点群なら OBB extents(全幅・ソート後)は (a,b,c) に、
      中心は箱中心に一致する。

beat-the-null(新規 op に下駄を履かせない基準):
    - 最小包含球 vs 素朴球: 「重心中心 + 最遠点半径」の素朴球は、重心が密集塊に引かれる
      非対称な点群(塊 + 遠い外れ点)では中心が偏り半径が過大になる。最小包含球は中心を
      寄せて半径を詰める(常に素朴球以下、かつ全点内包)。優位が本物である証拠として、
      最小包含球の半径が **直径/2(理論下界)のごく近傍=ほぼ最小**である一方、素朴球は
      その 1.7 倍以上に膨らむことを判別的に示す。さらに「重心中心 + 平均距離半径」の
      “詰めすぎ”素朴球は外れ点を**取りこぼす**(内包に失敗)ことを示し、安全側の優位も確かめる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- 新規 op(この事例の検証対象)-------------------------------------------
from hull3d import min_enclosing_sphere  # noqa: E402
# --- 既存の公開 op(新規ではない。家族の文脈として実体モジュールから直接呼ぶ)-----
from meshrepair import convex_hull  # noqa: E402  = fs.convex_hull(外向き面付き上位互換)
from pcseg import aabb, obb          # noqa: E402  = fs.aabb / fs.obb


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


def obb_corners_bitorder(center, axes_cols, half_extents) -> np.ndarray:
    """pcseg.obb の {center, axes(列=主軸), extents(半幅)} → ビット順の 8 隅 (8,3)。

    box_edges / aabb_corners と同じ ±順序(index の各ビットが x/y/z の符号)に揃えるので、
    OBB と AABB を同じ辺接続で描ける。世界座標 = center + (signs*half) @ axes.T。
    """
    center = np.asarray(center, float)
    axes_cols = np.asarray(axes_cols, float)          # 列 k = 主軸 k
    half = np.asarray(half_extents, float)
    signs = np.array([[sx, sy, sz]
                      for sx in (-1.0, 1.0)
                      for sy in (-1.0, 1.0)
                      for sz in (-1.0, 1.0)])          # (8,3) ビット順
    return center + (signs * half) @ axes_cols.T


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


def double_farthest_diameter(P: np.ndarray) -> float:
    """点群の直径(最遠点対距離)の下界近似: 任意点→最遠点→さらに最遠点。

    全ペア(O(N^2))を避けた 2 パス近似。真の直径以下だが最小包含球の理論下界
    (r >= 直径/2)を評価するのに十分(下界を過大評価しない安全側)。
    """
    d0 = np.linalg.norm(P - P[0], axis=1)
    j = int(np.argmax(d0))
    dj = np.linalg.norm(P - P[j], axis=1)
    k = int(np.argmax(dj))
    return float(np.linalg.norm(P[j] - P[k]))


# ═══════════════════════════════════════════════════════════════════════════
# 描画(matplotlib Agg、無ければスキップ)
# ═══════════════════════════════════════════════════════════════════════════
def render_png(path: Path, box_pts, obb_d, ab_min, ab_max, hull_verts, hull_faces,
               clu_pts, mes, naive_c, naive_r) -> bool:
    """凸包 / OBB vs AABB / 最小包含球 vs 素朴球 の 3 パネル図を保存。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
    except Exception:
        return False

    # 日本語フォントを選ぶ(無ければ既定のまま=英字は出る)。tofu(□)回避。
    have = {f.name for f in fm.fontManager.ttflist}
    for cand in ("Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP", "Malgun Gothic"):
        if cand in have:
            plt.rcParams["font.family"] = cand
            break
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(16.5, 5.4))

    obb_full = 2.0 * np.asarray(obb_d["extents"])   # pcseg.obb は半幅 → 全幅
    obb_c8 = obb_corners_bitorder(obb_d["center"], obb_d["axes"], obb_d["extents"])

    # --- パネル A: 凸包メッシュ(既存 fs.convex_hull)---
    axA = fig.add_subplot(1, 3, 1, projection="3d")
    axA.scatter(box_pts[:, 0], box_pts[:, 1], box_pts[:, 2],
                s=6, c="#3b6ea5", alpha=0.35, label="点群 (N=%d)" % len(box_pts))
    axA.plot_trisurf(hull_verts[:, 0], hull_verts[:, 1], hull_verts[:, 2],
                     triangles=hull_faces, color="#e08a1e", alpha=0.28,
                     edgecolor="#b5670c", linewidth=0.6)
    axA.set_title("fs.convex_hull(既存)\n凸包 = 頂点 %d・三角面 %d(内部点を除外)"
                  % (len(hull_verts), len(hull_faces)), fontsize=10)
    axA.legend(loc="upper left", fontsize=8)

    # --- パネル B: OBB(密着)vs AABB(過大)いずれも既存 op ---
    axB = fig.add_subplot(1, 3, 2, projection="3d")
    axB.scatter(box_pts[:, 0], box_pts[:, 1], box_pts[:, 2],
                s=6, c="#3b6ea5", alpha=0.5)
    for p, q in box_edges(aabb_corners(ab_min, ab_max)):
        axB.plot(*zip(p, q), c="#9aa7b0", lw=1.0, ls="--")
    for p, q in box_edges(obb_c8):
        axB.plot(*zip(p, q), c="#c0392b", lw=2.0)
    axB.set_title("fs.obb vs fs.aabb(いずれも既存)\nOBB 体積 %.2f  <  AABB 体積 %.2f"
                  % (vol3(obb_full), vol3(ab_max - ab_min)), fontsize=10)
    axB.plot([], [], c="#c0392b", lw=2.0, label="OBB(密着)")
    axB.plot([], [], c="#9aa7b0", lw=1.0, ls="--", label="AABB(過大)")
    axB.legend(loc="upper left", fontsize=8)

    # --- パネル C: ★新規 min_enclosing_sphere(密着)vs 素朴球(過大)---
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
    axC.set_title("★min_enclosing_sphere(新規)vs 素朴球\n最小 r=%.2f  <  素朴 r=%.2f"
                  % (mr, naive_r), fontsize=10)
    axC.plot([], [], c="#27865a", label="最小包含球(新規)")
    axC.plot([], [], c="#9aa7b0", label="素朴球(重心+最遠)")
    axC.legend(loc="upper left", fontsize=8)

    fig.suptitle("hull3d — 新規 op = 最小包含球(既存の凸包/OBB/AABB を文脈として併置)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# メイン: 新規 op の GT + beat-null(load-bearing)+ 既存 op の文脈提示 + 描画
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # ============================================================
    # ★(1) 新規 op — min_enclosing_sphere: 既知球で半径復元 + 全点内包 + ほぼ最小
    # ============================================================
    r0 = 3.0
    sph_center = np.array([1.0, 2.0, 3.0])
    sph_pts = sphere_surface(800, r0, sph_center, seed=0)
    mes_s = min_enclosing_sphere(sph_pts)
    ms_c, ms_r = np.asarray(mes_s["center"]), float(mes_s["radius"])
    ds = np.linalg.norm(sph_pts - ms_c, axis=1)
    all_in_s = bool(np.all(ds <= ms_r + 1e-9))
    diam_s = double_farthest_diameter(sph_pts)      # 理論下界 r >= diam/2 の評価用
    print(f"[GT] min_enclosing_sphere(sphere r0={r0}): center={np.round(ms_c, 4)} "
          f"(true {sph_center}) r={ms_r:.5f}  diam/2={diam_s / 2:.5f}  all_inside={all_in_s}")

    assert all_in_s, "最小包含球が全点を内包していない(球面 GT)"
    assert np.linalg.norm(ms_c - sph_center) < 5e-3, \
        f"最小包含球の中心が球中心とずれている: {np.linalg.norm(ms_c - sph_center):.4f}"
    assert abs(ms_r - r0) < 1e-2, f"最小包含球の半径が r0 と不一致: {ms_r:.5f} vs {r0}"
    # 直径/2 は理論下界(r >= 直径/2)。近似解が下界の (1+1%) 以内 = ほぼ最小(見せかけでない)。
    assert ms_r <= diam_s / 2.0 * 1.01, \
        f"半径が直径/2 を有意に超過(過大): r={ms_r:.5f} > diam/2={diam_s / 2:.5f}"
    assert ms_r >= diam_s / 2.0 * 0.999, \
        f"半径が直径/2(理論下界)を下回った=全点内包に矛盾: r={ms_r:.5f} < diam/2={diam_s / 2:.5f}"

    # ============================================================
    # ★(2) 新規 op の beat-null — 非対称点群で素朴球より小さく・ほぼ最小・安全側
    # ============================================================
    clu = cluster_with_outlier(seed=1)
    mes_c = min_enclosing_sphere(clu)
    mc, mr = np.asarray(mes_c["center"]), float(mes_c["radius"])
    dc = np.linalg.norm(clu - mc, axis=1)
    mes_all_in = bool(np.all(dc <= mr + 1e-9))
    diam_c = double_farthest_diameter(clu)          # 理論下界

    # null-1(過大): 重心中心 + 最遠点半径。全点内包はするが半径が過大。
    naive_c = clu.mean(axis=0)
    naive_r = float(np.linalg.norm(clu - naive_c, axis=1).max())
    # null-2(取りこぼし): 重心中心 + 平均距離半径。詰めすぎて外れ点を内包できない。
    tight_r = float(np.linalg.norm(clu - naive_c, axis=1).mean())
    tight_uncovered = int(np.sum(np.linalg.norm(clu - naive_c, axis=1) > tight_r + 1e-9))

    print(f"[beat] cluster+outlier: MES r={mr:.4f} (all_in={mes_all_in}) "
          f"diam/2={diam_c / 2:.4f}  素朴(重心+最遠) r={naive_r:.4f}  "
          f"素朴(重心+平均) r={tight_r:.4f} 取りこぼし {tight_uncovered} 点")
    print(f"[beat] MES/素朴(最遠) 比={mr / naive_r:.3f}  MES/(直径/2)={mr / (diam_c / 2):.4f}")

    assert mes_all_in, "最小包含球が全点を内包していない(非対称 GT)"
    # (a) 素朴球より判別的に小さい(僅差でなく明確なマージン)
    assert mr < 0.7 * naive_r, \
        f"最小包含球の素朴球(重心+最遠)に対する優位が小さすぎる: 比 {mr / naive_r:.3f}"
    # (b) その勝利が「弱い相手に勝っただけ」でない証拠: MES は理論下界(直径/2)のごく近傍=ほぼ最小
    assert mr <= diam_c / 2.0 * 1.01, \
        f"MES が直径/2(理論下界)を有意に超過し最小といえない: r={mr:.4f} > {diam_c / 2:.4f}"
    assert mr >= diam_c / 2.0 * 0.999, \
        f"MES が直径/2(理論下界)未満=全点内包に矛盾: r={mr:.4f} < {diam_c / 2:.4f}"
    # (c) 素朴球は下界から明確に膨らんでいる(strawman でなく、詰める余地が実在した)
    assert naive_r >= diam_c / 2.0 * 1.5, \
        f"素朴球が下界近傍で、詰める余地が無い=beat-null が無意味: {naive_r:.4f} vs {diam_c / 2:.4f}"
    # (d) 詰めすぎ素朴球は安全側でない(外れ点を取りこぼす)
    assert tight_uncovered > 0, \
        "詰めすぎ素朴球が取りこぼしを起こす構成になっていない(シーン設計を見直す)"

    # ============================================================
    # (3) 既存の公開 op(参考・新規ではない)— 凸包 / OBB / AABB を GT で健全性確認
    #     ※ min_enclosing_sphere の家族の文脈として併置するだけで、この事例の貢献ではない。
    # ============================================================
    # 3a. fs.convex_hull(= meshrepair.convex_hull): 単位立方体 → 体積1・頂点8・面12
    cube = unit_cube_corners()
    hv, hf = convex_hull(cube)
    hull_vol = mesh_volume(hv, hf)
    corner_set = {tuple(np.round(p, 9)) for p in cube}
    hv_set = {tuple(np.round(p, 9)) for p in hv}
    print(f"[ref] fs.convex_hull(unit cube): verts={len(hv)} faces={len(hf)} "
          f"mesh_volume={hull_vol:.10f}  (既存公開 op)")
    assert len(hv) == 8 and len(hf) == 12, f"既存 convex_hull 健全性: verts {len(hv)} faces {len(hf)}"
    assert hv_set == corner_set, "既存 convex_hull 頂点が立方体 8 隅と不一致"
    assert abs(hull_vol - 1.0) < 1e-9, f"既存 convex_hull 体積が 1.0 でない: {hull_vol:.10f}"

    # 3b. fs.obb / fs.aabb: 既知寸法の回転箱で寸法・中心を復元、OBB < AABB(既存 op の性質)
    dims = (4.0, 2.5, 1.2)
    R = euler_rotation(0.6, 0.4, 0.3)
    center_true = np.array([5.0, 3.0, 2.0])
    box_pts = box_grid(dims, R, center_true, per_axis=(7, 6, 5))

    obb_d = obb(box_pts)
    obb_full = 2.0 * np.asarray(obb_d["extents"])     # pcseg.obb は半幅 → 全幅
    ext_sorted = np.sort(obb_full)
    dims_sorted = np.sort(dims)
    ext_err = float(np.max(np.abs(ext_sorted - dims_sorted)))
    center_err = float(np.linalg.norm(np.asarray(obb_d["center"]) - center_true))
    obb_vol = vol3(obb_full)

    ab_min, ab_max = aabb(box_pts)
    aabb_ext = ab_max - ab_min
    aabb_vol = vol3(aabb_ext)

    print(f"[ref] fs.obb extents(全幅,sorted)={np.round(ext_sorted, 6)} "
          f"true={np.round(dims_sorted, 6)} err={ext_err:.2e} center_err={center_err:.2e}  (既存公開 op)")
    print(f"[ref] fs.obb 体積 {obb_vol:.4f}  <  fs.aabb 体積 {aabb_vol:.4f}  "
          f"(比 {obb_vol / aabb_vol:.3f}) — 既存 op の性質(軸整列は傾いた箱で過大)")
    assert ext_err < 1e-6, f"既存 obb extents 復元誤差: {ext_err:.2e}"
    assert center_err < 1e-6, f"既存 obb center 復元誤差: {center_err:.2e}"
    assert obb_vol < aabb_vol, f"既存 obb < aabb でない: {obb_vol:.4f} vs {aabb_vol:.4f}"

    # ============================================================
    # 描画(結果を PNG に)
    # ============================================================
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "hull_bounds.png"
    box_hull_v, box_hull_f = convex_hull(box_pts)     # 回転箱の凸包メッシュ(描画用・既存 op)
    drew = render_png(out_png, box_pts, obb_d, ab_min, ab_max,
                      box_hull_v, box_hull_f, clu, mes_c, naive_c, naive_r)
    if drew:
        print(f"[draw] gallery PNG 保存: {out_png}")
    else:
        print("[draw] matplotlib 不在のため PNG はスキップ(GT アサートは全て実施済み)")

    print(
        "PASS: 新規 op min_enclosing_sphere を検証 — 球面から r=%.3f(真値 %.1f・全点内包・"
        "直径/2=%.3f のごく近傍でほぼ最小)。非対称点群で r=%.3f が素朴球 r=%.3f を "
        "比 %.3f で判別的に下回り(理論下界 直径/2=%.3f のほぼ上、素朴は下界の %.2f 倍)、"
        "詰めすぎ素朴球は %d 点を取りこぼした。"
        "参考として既存公開 op も併置: fs.convex_hull(立方体 体積 %.4f・頂点 %d・面 %d)、"
        "fs.obb 体積 %.2f < fs.aabb 体積 %.2f(比 %.2f)。"
        % (ms_r, r0, diam_s / 2,
           mr, naive_r, mr / naive_r, diam_c / 2, naive_r / (diam_c / 2), tight_uncovered,
           hull_vol, len(hv), len(hf), obb_vol, aabb_vol, obb_vol / aabb_vol)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
