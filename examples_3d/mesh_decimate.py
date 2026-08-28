# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 高ポリの球メッシュを面数 30% へ簡略化する (mesh decimation, QEM edge-collapse).

実世界の問題:
    3D スキャン・CAD・marching cubes 出力は面数が膨大で、そのままでは描画・物理・
    伝送が重い。「形をできるだけ保ったまま面数を落とす」簡略化(decimation)が要る。
    素朴に「面をランダムに間引いて数だけ合わせる」と、表面に穴(hole)が開き、
    境界がほつれて非多様体(non-manifold)になり、形が壊れる。

原理:
    mesh_decimate.decimate_mesh は Garland & Heckbert (1997) の quadric error metric を
    使い、「その頂点をこれまで消してきた面の平面からどれだけ離すか」の二乗誤差 Q が最小に
    なる辺から順に縮約(edge-collapse)する。縮約の可否は link condition で判定し、非多様体を
    生む縮約は拒否する。だから穴を開けず、元表面への距離を小さく保って面数だけ落とせる。

検証(GT):
    半径 R=1 の球を細分した高ポリ icosphere(1280 面)を目標 384 面(30%)へ簡略化し、
      1) 面数が目標付近(exact〜数%)に収まるか
      2) 簡略化メッシュの各頂点が球面上に残るか(半径 ≈ R)
      3) 元メッシュへの対称 Hausdorff / Chamfer 距離が R の数%以内か
      4) watertight(境界エッジ 0・全エッジが 2 面共有)を保つか
    を確認する。

beat-the-null(下駄を履かせない基準):
    同じ面数(384)まで **面をランダムに間引く** null を並べる。ランダム間引きは表面に
    穴を開けるので、
      * 元メッシュへの Hausdorff 距離が桁違いに悪化(穴の縁が最遠点になる)、
      * 境界エッジが数百本(=穴だらけ・非多様体)になる。
    QEM がこの null を Hausdorff でも watertight 性でも判別的に上回ることを assert する。

出力:
    高ポリ(before)/ QEM 簡略化(after)/ ランダム間引き null を trisurf で 3 面並置し、
    面数と Hausdorff を注記した PNG を examples_3d/_gallery/mesh_decimate.png に保存する。
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
# この例ファイルは import 対象モジュール mesh_decimate.py と同名(basename 衝突)。
# スクリプト実行時 sys.path[0] は examples_3d/ になり自分自身を import してしまうため、
# リポジトリルートを無条件で最前へ挿入して root 側 mesh_decimate.py を優先させる。
sys.path.insert(0, str(_REPO_ROOT))

from match3d import mesh_to_points          # noqa: E402  (sys.path 調整後に import)
from mesh_decimate import decimate_mesh      # noqa: E402
from scipy.spatial import cKDTree            # noqa: E402


def icosphere(level: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """単位球面上の icosphere メッシュ(正二十面体を level 回細分し球面へ射影)。

    正二十面体(20 面)を各三角形 4 分割で level 回細分するので面数 = 20·4^level。
    全頂点は原点中心・半径 1 の球面上に厳密に載る(GT に使える)。
    """
    t = (1.0 + 5.0 ** 0.5) / 2.0
    base = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
            (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
            (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [np.asarray(v, np.float64) / np.linalg.norm(v) for v in base]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
             (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    cache: dict[tuple[int, int], int] = {}

    def midpoint(a: int, b: int) -> int:
        key = (a, b) if a < b else (b, a)
        if key in cache:
            return cache[key]
        m = verts[a] + verts[b]
        m = m / np.linalg.norm(m)              # 球面へ射影
        verts.append(m)
        cache[key] = len(verts) - 1
        return cache[key]

    for _ in range(int(level)):
        new_faces = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    return np.asarray(verts, np.float64), np.asarray(faces, np.int64)


def boundary_edge_count(faces: np.ndarray) -> tuple[int, dict]:
    """境界エッジ数(1 面にしか属さないエッジ=穴の縁)と共有数ヒストグラムを返す。

    watertight な閉曲面では全エッジがちょうど 2 面に共有され境界エッジ 0。穴が開くと
    その縁が 1 面共有になり境界エッジが増える。非多様体では 3 面以上共有が現れる。
    """
    ec: Counter = Counter()
    for a, b, c in faces.tolist():
        for u, w in ((a, b), (b, c), (a, c)):
            ec[(u, w) if u < w else (w, u)] += 1
    hist = Counter(ec.values())
    return int(hist.get(1, 0)), dict(hist)


def symmetric_hausdorff_chamfer(mesh_a: tuple[np.ndarray, np.ndarray],
                                mesh_b: tuple[np.ndarray, np.ndarray],
                                samples: int = 40000) -> tuple[float, float]:
    """2 メッシュ表面の対称 Hausdorff と対称 Chamfer 距離を面積一様サンプルで推定。

    双方向の最近傍距離を測り、Hausdorff=両方向の最大の大きい方、Chamfer=両方向の平均の平均。
    片側に穴があると「穴の上の点の最近傍が遠い」ため Hausdorff が跳ね上がる。
    """
    Va, Fa = mesh_a
    Vb, Fb = mesh_b
    Pa = mesh_to_points(Va, Fa, samples=samples, seed=1)
    Pb = mesh_to_points(Vb, Fb, samples=samples, seed=2)
    da, _ = cKDTree(Pb).query(Pa)
    db, _ = cKDTree(Pa).query(Pb)
    hausdorff = float(max(da.max(), db.max()))
    chamfer = float(0.5 * (da.mean() + db.mean()))
    return hausdorff, chamfer


def render_png(before, qem, null, stats, path: Path) -> bool:
    """before / QEM after / null を trisurf で 3 面並置して PNG 保存。失敗時 False。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"[png] matplotlib 不在のため描画スキップ: {exc}")
        return False

    panels = [
        ("high-poly (before)\n{} faces".format(len(before[1])), before, "#4c72b0"),
        ("QEM decimate\n{} faces  Hausdorff {:.1f}% R".format(
            len(qem[1]), 100 * stats["qem_h"]), qem, "#55a868"),
        ("random-drop null\n{} faces  Hausdorff {:.1f}% R".format(
            len(null[1]), 100 * stats["null_h"]), null, "#c44e52"),
    ]
    fig = plt.figure(figsize=(15, 5.4))
    for i, (title, (V, F), color) in enumerate(panels, 1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        ax.plot_trisurf(V[:, 0], V[:, 1], V[:, 2], triangles=F,
                        color=color, edgecolor="black", linewidth=0.25,
                        alpha=0.9, shade=True)
        ax.set_title(title, fontsize=11)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        ax.view_init(elev=18, azim=35)
    fig.suptitle(
        "Mesh decimation (QEM edge-collapse): shape preserved & watertight, "
        "vs. random face-drop that punches holes", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"[png] 保存: {path}")
    return True


def main() -> int:
    R = 1.0
    ratio = 0.30

    # --- 高ポリ球(before)。全頂点は半径 1 の球面上(GT) ---
    Vh, Fh = icosphere(level=3)             # 1280 faces
    n_before = len(Fh)
    target = int(round(n_before * ratio))   # 384

    # 入力健全性(退化データで偽の成功を出さない)
    if Vh.ndim != 2 or Vh.shape[1] != 3 or Fh.ndim != 2 or Fh.shape[1] != 3:
        raise ValueError("icosphere が (N,3)/(M,3) を返していない(退化)")
    r_before = np.linalg.norm(Vh, axis=1)
    if not np.allclose(r_before, R, atol=1e-9):
        raise ValueError("高ポリ球の頂点が球面上にない(GT 前提が崩れている)")
    if target < 8 or target >= n_before:
        raise ValueError("target 面数の設定が不正(beat-null が意味を持たない)")

    print(f"[GT] before: {len(Vh)} verts / {n_before} faces  (unit sphere R={R})")
    print(f"[GT] target: {target} faces ({int(ratio*100)}%)")

    # --- 実手法: QEM edge-collapse ---
    Vd, Fd = decimate_mesh(Vh, Fh, target)
    n_qem = len(Fd)
    r_dec = np.linalg.norm(Vd, axis=1)
    qem_bd, qem_hist = boundary_edge_count(Fd)
    qem_h, qem_c = symmetric_hausdorff_chamfer((Vh, Fh), (Vd, Fd))

    print(f"[QEM ] faces={n_qem}  vert radius mean={r_dec.mean():.4f} "
          f"(min {r_dec.min():.4f}, max {r_dec.max():.4f})")
    print(f"[QEM ] boundary edges={qem_bd} (0=watertight), edge-share hist={qem_hist}")
    print(f"[QEM ] Hausdorff={qem_h:.4f} ({100*qem_h/R:.2f}% R)  "
          f"Chamfer={qem_c:.5f} ({100*qem_c/R:.3f}% R)")

    # --- beat-the-null: 同じ面数まで面をランダム間引き ---
    rng = np.random.default_rng(0)
    keep = rng.choice(n_before, size=target, replace=False)
    Vn, Fn = Vh, Fh[keep]
    null_bd, null_hist = boundary_edge_count(Fn)
    null_h, null_c = symmetric_hausdorff_chamfer((Vh, Fh), (Vn, Fn))

    print(f"[null] faces={len(Fn)}  boundary edges={null_bd} (holes!), "
          f"edge-share hist={null_hist}")
    print(f"[null] Hausdorff={null_h:.4f} ({100*null_h/R:.2f}% R)  "
          f"Chamfer={null_c:.5f} ({100*null_c/R:.3f}% R)")
    print(f"[cmp ] Hausdorff null/qem = {null_h/qem_h:.1f}x   "
          f"Chamfer null/qem = {null_c/qem_c:.1f}x")

    # --- PNG 描画(GT アサートには影響しない) ---
    render_png((Vh, Fh), (Vd, Fd), (Vn, Fn),
               {"qem_h": qem_h / R, "null_h": null_h / R},
               _REPO_ROOT / "examples_3d" / "_gallery" / "mesh_decimate.png")

    # ==================== GT アサーション ====================
    # (1) 面数が目標付近(QEM は多様体保存 collapse なので通常 exact、早期停止でも数%以内)
    assert abs(n_qem - target) <= max(2, int(0.05 * target)), \
        f"面数が目標から外れすぎ: {n_qem} vs target {target}"
    # (2) 簡略化後の頂点が球面上に残る(QEM 最適位置は接平面交点なので R 近傍・僅かに外側)
    assert r_dec.min() > 0.97 * R and r_dec.max() < 1.03 * R, \
        f"簡略化後の頂点が球面から離れた: r∈[{r_dec.min():.4f},{r_dec.max():.4f}]"
    # (3) 元メッシュへの Hausdorff / Chamfer が R の数%以内(形状保存)
    assert qem_h < 0.08 * R, f"QEM Hausdorff が大きすぎる: {qem_h:.4f} (>{0.08*R})"
    assert qem_c < 0.02 * R, f"QEM Chamfer が大きすぎる: {qem_c:.5f} (>{0.02*R})"
    # (4) watertight を保つ(境界エッジ 0・全エッジ 2 面共有=2-manifold)
    assert qem_bd == 0, f"QEM が穴を開けた(境界エッジ {qem_bd})"
    assert set(qem_hist.keys()) == {2}, \
        f"QEM が非多様体エッジを作った: hist={qem_hist}"

    # ---- beat-the-null: ランダム間引きは穴を開けて Hausdorff/watertight で劣る ----
    # null が実際に穴だらけ(多数の境界エッジ)であることを確認(null 設計の健全性)
    assert null_bd > 100, f"null に穴が十分できていない(境界エッジ {null_bd})"
    # QEM は null を Hausdorff で判別的に上回る(3 倍以上良い、かつ null は明確に悪い)
    assert null_h > 0.12 * R, f"null の Hausdorff が悪化していない: {null_h:.4f}"
    assert qem_h < null_h / 3.0, \
        f"QEM が null を Hausdorff で上回れていない: {qem_h:.4f} vs null {null_h:.4f}"
    # watertight 性でも判別的(QEM=0 穴 / null=数百穴)
    assert qem_bd == 0 and null_bd > 100 and null_bd > 50 * (qem_bd + 1), \
        f"watertight 差が不十分: qem_bd={qem_bd}, null_bd={null_bd}"
    # Chamfer でも上回る(平均距離。穴の分だけ null が悪い)
    assert qem_c < null_c, \
        f"QEM が null を Chamfer で上回れていない: {qem_c:.5f} vs {null_c:.5f}"

    print(
        f"PASS: 球メッシュ {n_before}面 → QEMで{n_qem}面(目標{target})に簡略化。"
        f"頂点は球面上(半径{r_dec.mean():.3f})・watertight維持(境界エッジ0)、"
        f"元表面へのHausdorff {100*qem_h/R:.1f}%R・Chamfer {100*qem_c/R:.2f}%R。"
        f"beat-null: 同数ランダム間引きは穴{null_bd}本・Hausdorff {100*null_h/R:.1f}%R "
        f"で、QEMがHausdorffで{null_h/qem_h:.1f}倍・watertight性で圧倒的に上回った")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
