# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: メッシュ簡略化 (mesh decimation, QEM edge-collapse) — 境界保存・多様体厳格な変種
``decimate_qem_manifold`` を、素朴なランダム間引き **と** 既存の姉妹 op
``meshrepair.decimate_qem`` の両方に対して実測比較する。

実世界の問題:
    3D スキャン・CAD・marching cubes 出力は面数が膨大で、そのままでは描画・物理・
    伝送が重い。「形をできるだけ保ったまま面数を落とす」簡略化(decimation)が要る。
    素朴に「面をランダムに間引いて数だけ合わせる」と、表面に穴(hole)が開き、
    境界がほつれて非多様体(non-manifold)になり、形が壊れる。

原理:
    mesh_decimate.decimate_qem_manifold は Garland & Heckbert (1997) の quadric error metric を
    使い、「その頂点をこれまで消してきた面の平面からどれだけ離すか」の二乗誤差 Q が最小に
    なる辺から順に縮約(edge-collapse)する。縮約の可否は link condition(Dey 1999)で判定し、
    非多様体を生む縮約は拒否する。だから穴を開けず、元表面への距離を小さく保って面数だけ落とせる。

    ★重複ではなく変種であることの明示(honest disclosure):fullseye には既に
    ``meshrepair.decimate_qem``(= ``fullseye.decimate_qem``、公開・テスト済み)という
    「実用(practical)」水準の QEM edge-collapse 簡略化 op がある。本例が使う
    ``decimate_qem_manifold`` はそれを置き換える新規 op ではなく、``decimate_qem`` が
    **明示的に持たない**「境界エッジ拘束(boundary term)/ link condition による厳密 2-manifold /
    4×4 拘束解 / 外れ位置棄却」を足した **姉妹 op** である。本例の Scene B はこの差が実在することを
    両者の実測比較で裏付ける(prose だけの主張にしない)。

検証(GT)= 2 シーン:
  Scene A(閉じた球・beat-the-null vs ランダム間引き):
      半径 R=1 の球を細分した高ポリ icosphere(1280 面)を目標 384 面(30%)へ簡略化し、
        1) 面数が目標付近に収まるか
        2) 簡略化メッシュの各頂点が球面上に残るか(半径 ≈ R)
        3) 元メッシュへの対称 Hausdorff / Chamfer 距離が R の数%以内か
        4) watertight(境界エッジ 0・全エッジが 2 面共有)を保つか
      を確認し、同じ面数まで面をランダム間引く null を Hausdorff / watertight 性で判別的に上回る。
      (閉曲面には境界が無いので、ここでは境界 term は不活性=``decimate_qem`` との差は出ない。)
  Scene B(開いた半球・beat-the-sibling vs decimate_qem):
      開半球(円い rim を持つ開メッシュ)を同じ面数まで ``decimate_qem_manifold`` と
      ``meshrepair.decimate_qem`` の双方で簡略化し、
        * ``decimate_qem_manifold`` は境界頂点を元の rim 曲線の上に保つ(rim への距離 ≈ 0)、
        * ``decimate_qem``(境界 term 無し)は rim 頂点を内側へ引き込む(rim への距離が桁違いに大)
      ことを実測して、境界保存 term が生む差が実在することを assert する。

beat-the-null / beat-the-sibling(下駄を履かせない基準):
    Scene A の null=ランダム間引きは表面に穴を開けるので、元メッシュへの Hausdorff が桁違いに
    悪化し、境界エッジが数百本になる。Scene B の baseline=姉妹 op ``decimate_qem`` は境界 term を
    持たないので開 rim を保てない。どちらも「QEM を名乗るが本 op より弱いもの」であり、本 op が
    判別的に上回ることを assert する。

出力:
    Scene A(before / qem_manifold / random-null)と Scene B(input rim / qem_manifold /
    decimate_qem)を trisurf で 2 行 3 列に並置した PNG を
    examples_3d/_gallery/mesh_decimate.png に保存する。
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

from match3d import mesh_to_points                # noqa: E402  (sys.path 調整後に import)
from mesh_decimate import decimate_qem_manifold    # noqa: E402  (本 op:境界保存・多様体厳格)
from meshrepair import decimate_qem                # noqa: E402  (姉妹 op:境界 term 無しの実用 QEM)
from scipy.spatial import cKDTree                  # noqa: E402


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


def open_hemisphere(level: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """上半分(z>=0)の面だけ残した開半球メッシュ。赤道付近に円い開境界(rim)を持つ。

    icosphere から z>=0 側の面のみを取り、参照頂点を詰め直す。結果は watertight でなく、
    「穴の縁」ならぬ「切り口の rim」= 境界エッジのループを持つ。境界保存 term の効果を
    測るための開メッシュ GT。
    """
    V, F = icosphere(level)
    keep = np.array([bool(np.all(V[f, 2] >= -1e-9)) for f in F])
    Fh = F[keep]
    used = np.unique(Fh)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used].astype(np.float64), remap[Fh].astype(np.int64)


def edge_share(faces: np.ndarray) -> Counter:
    """エッジ → それを共有する面数 の Counter。"""
    ec: Counter = Counter()
    for a, b, c in faces.tolist():
        for u, w in ((a, b), (b, c), (a, c)):
            ec[(u, w) if u < w else (w, u)] += 1
    return ec


def boundary_edge_count(faces: np.ndarray) -> tuple[int, dict]:
    """境界エッジ数(1 面にしか属さないエッジ=穴の縁/rim)と共有数ヒストグラムを返す。

    watertight な閉曲面では全エッジがちょうど 2 面に共有され境界エッジ 0。穴が開くと
    その縁が 1 面共有になり境界エッジが増える。非多様体では 3 面以上共有が現れる。
    """
    ec = edge_share(faces)
    hist = Counter(ec.values())
    return int(hist.get(1, 0)), dict(hist)


def boundary_vertices(faces: np.ndarray) -> list[int]:
    """境界エッジ(1 面共有)に属する頂点インデックスの一覧。"""
    ec = edge_share(faces)
    return sorted({v for e, n in ec.items() if n == 1 for v in e})


def sample_boundary_curve(V: np.ndarray, faces: np.ndarray,
                          per_edge: int = 12) -> np.ndarray:
    """境界エッジ列を密にサンプルした「元 rim 曲線」の点群(rim への距離計測用)。"""
    ec = edge_share(faces)
    pts = []
    for (u, w), n in ec.items():
        if n == 1:
            for tt in np.linspace(0.0, 1.0, per_edge):
                pts.append((1.0 - tt) * V[u] + tt * V[w])
    return np.asarray(pts, dtype=np.float64)


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


def rim_distance(V: np.ndarray, faces: np.ndarray,
                 rim_tree: cKDTree) -> tuple[float, float, int]:
    """簡略化メッシュの各境界頂点から「元 rim 曲線」への最近傍距離 (max, mean, 本数)。

    境界保存できていれば境界頂点は元 rim 上に残る(距離≈0)。境界 term を持たない手法は
    rim 頂点を内側へ引き込むので距離が大きくなる。境界が消滅していたら (inf, inf, 0)。
    """
    bv = boundary_vertices(faces)
    if not bv:
        return float("inf"), float("inf"), 0
    d, _ = rim_tree.query(V[bv])
    return float(d.max()), float(d.mean()), len(bv)


def render_png(scene_a, scene_b, path: Path) -> bool:
    """Scene A / Scene B を trisurf で 2 行 3 列に並置して PNG 保存。失敗時 False。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"[png] matplotlib 不在のため描画スキップ: {exc}")
        return False

    panels = scene_a + scene_b       # 6 panels: (title, (V,F), color, lim)
    fig = plt.figure(figsize=(15, 10))
    for i, (title, (V, F), color, lim) in enumerate(panels, 1):
        ax = fig.add_subplot(2, 3, i, projection="3d")
        ax.plot_trisurf(V[:, 0], V[:, 1], V[:, 2], triangles=F,
                        color=color, edgecolor="black", linewidth=0.25,
                        alpha=0.9, shade=True)
        ax.set_title(title, fontsize=10)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        ax.view_init(elev=18, azim=35)
    fig.suptitle(
        "Mesh decimation (QEM edge-collapse). "
        "Top: closed sphere vs random face-drop (holes). "
        "Bottom: open hemisphere — decimate_qem_manifold keeps the rim, "
        "sibling decimate_qem (no boundary term) erodes it.", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"[png] 保存: {path}")
    return True


def scene_a_closed_sphere() -> tuple[list, dict]:
    """Scene A: 閉じた球を QEM 簡略化し、同数ランダム間引き null に対し beat-the-null。"""
    R = 1.0
    ratio = 0.30
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

    print("=== Scene A: closed sphere (beat-the-null vs random face-drop) ===")
    print(f"[GT] before: {len(Vh)} verts / {n_before} faces  (unit sphere R={R})")
    print(f"[GT] target: {target} faces ({int(ratio*100)}%)")

    # --- 本 op: 境界保存・多様体厳格 QEM(閉曲面なので境界 term は不活性) ---
    Vd, Fd = decimate_qem_manifold(Vh, Fh, target)
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

    # ==================== GT アサーション(Scene A) ====================
    # (1) 面数が目標付近(多様体保存 collapse なので通常 exact、早期停止でも数%以内)
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
    assert null_bd > 100, f"null に穴が十分できていない(境界エッジ {null_bd})"
    assert null_h > 0.12 * R, f"null の Hausdorff が悪化していない: {null_h:.4f}"
    assert qem_h < null_h / 3.0, \
        f"QEM が null を Hausdorff で上回れていない: {qem_h:.4f} vs null {null_h:.4f}"
    assert qem_bd == 0 and null_bd > 100 and null_bd > 50 * (qem_bd + 1), \
        f"watertight 差が不十分: qem_bd={qem_bd}, null_bd={null_bd}"
    assert qem_c < null_c, \
        f"QEM が null を Chamfer で上回れていない: {qem_c:.5f} vs {null_c:.5f}"

    print(f"[PASS A] 球 {n_before}面 → {n_qem}面(目標{target})・頂点球面上(半径{r_dec.mean():.3f})"
          f"・watertight維持・Hausdorff {100*qem_h/R:.1f}%R。beat-null: ランダム間引きは穴{null_bd}本"
          f"・Hausdorff {100*null_h/R:.1f}%R で {null_h/qem_h:.1f}倍劣る")

    panels = [
        ("high-poly (before)\n{} faces".format(len(Fh)), (Vh, Fh), "#4c72b0", 1.0),
        ("qem_manifold\n{} faces  H {:.1f}% R".format(n_qem, 100 * qem_h / R),
         (Vd, Fd), "#55a868", 1.0),
        ("random-drop null\n{} faces  H {:.1f}% R".format(len(Fn), 100 * null_h / R),
         (Vn, Fn), "#c44e52", 1.0),
    ]
    stats = {"n_before": n_before, "n_qem": n_qem, "target": target,
             "qem_h": qem_h, "null_h": null_h, "null_bd": null_bd, "R": R}
    return panels, stats


def scene_b_open_hemisphere() -> tuple[list, dict]:
    """Scene B: 開半球で本 op vs 姉妹 op decimate_qem。境界保存 term の差を実測する。"""
    ratio = 0.35
    Vh, Fh = open_hemisphere(level=3)
    n_before = len(Fh)
    target = int(round(n_before * ratio))

    if n_before < 100:
        raise ValueError("開半球の面数が少なすぎる(比較が意味を持たない)")
    be_in, _ = boundary_edge_count(Fh)
    if be_in < 12:
        raise ValueError(f"開半球に十分な境界(rim)が無い(境界エッジ {be_in})")
    rim_tree = cKDTree(sample_boundary_curve(Vh, Fh))   # 元 rim 曲線

    print("\n=== Scene B: open hemisphere (beat-the-sibling vs decimate_qem) ===")
    print(f"[GT] before: {len(Vh)} verts / {n_before} faces  boundary edges(rim)={be_in}")
    print(f"[GT] target: {target} faces ({int(ratio*100)}%)")

    # --- 本 op(境界保存)vs 姉妹 op(境界 term 無し)を同じ面数で比較 ---
    Vm, Fm = decimate_qem_manifold(Vh, Fh, target)
    Vs, Fs = decimate_qem(Vh, Fh, target)
    m_rim_max, m_rim_mean, m_bv = rim_distance(Vm, Fm, rim_tree)
    s_rim_max, s_rim_mean, s_bv = rim_distance(Vs, Fs, rim_tree)
    m_bd, _ = boundary_edge_count(Fm)
    s_bd, _ = boundary_edge_count(Fs)

    print(f"[qem_manifold] faces={len(Fm)} boundary edges={m_bd}/{be_in} "
          f"rim-dist max={m_rim_max:.4f} mean={m_rim_mean:.4f} (bverts={m_bv})")
    print(f"[decimate_qem] faces={len(Fs)} boundary edges={s_bd}/{be_in} "
          f"rim-dist max={s_rim_max:.4f} mean={s_rim_mean:.4f} (bverts={s_bv})")
    ratio_mean = s_rim_mean / max(m_rim_mean, 1e-9)
    print(f"[cmp ] rim-dist sibling/manifold mean = {ratio_mean:.1f}x  "
          f"(boundary retained: manifold {m_bd/be_in:.0%} vs sibling {s_bd/be_in:.0%})")

    # ==================== GT アサーション(Scene B) ====================
    # 両者を同じ面数バジェットで比較していること(公平な beat)
    assert abs(len(Fm) - target) <= max(2, int(0.1 * target)), \
        f"qem_manifold の面数が目標から外れすぎ: {len(Fm)} vs {target}"
    assert abs(len(Fs) - len(Fm)) <= max(2, int(0.1 * target)), \
        f"両手法の面数バジェットが揃っていない: manifold={len(Fm)} sibling={len(Fs)}"
    # 本 op は境界頂点を元 rim 曲線の「上」に保つ(距離≈0)
    assert m_rim_max < 0.03, \
        f"qem_manifold が rim を保てていない: rim-dist max={m_rim_max:.4f}"
    # 姉妹 op(境界 term 無し)は rim を元曲線から明確に引き離す
    assert s_rim_mean > 0.05, \
        f"decimate_qem の rim 逸脱が出ていない(比較が退化): rim-dist mean={s_rim_mean:.4f}"
    # 判別的:本 op の rim 逸脱は姉妹 op より桁違いに小さい(下駄無し)
    assert m_rim_mean < s_rim_mean / 5.0, \
        f"境界保存の差が判別的でない: manifold {m_rim_mean:.4f} vs sibling {s_rim_mean:.4f}"
    # 本 op は rim(境界エッジ)を多く残し、姉妹 op はより多く失う
    assert m_bd >= 0.75 * be_in, \
        f"qem_manifold が境界を残せていない: {m_bd}/{be_in}"
    assert s_bd < m_bd, \
        f"姉妹 op が本 op と同等以上に境界を残した(差が出ていない): sibling={s_bd} manifold={m_bd}"

    print(f"[PASS B] 開半球で本 op は境界を rim 上に保持(rim-dist mean {m_rim_mean:.4f}・"
          f"境界 {m_bd/be_in:.0%} 維持)が、境界 term を持たない姉妹 op decimate_qem は rim を "
          f"内側へ引き込む(rim-dist mean {s_rim_mean:.4f}={ratio_mean:.0f}倍・境界 {s_bd/be_in:.0%})。"
          f"→ 重複ではなく境界保存の実効差を持つ別 op であることを実測で確認")

    panels = [
        ("open hemisphere (input)\n{} faces  rim {} edges".format(n_before, be_in),
         (Vh, Fh), "#4c72b0", 1.0),
        ("qem_manifold (rim kept)\n{} faces  rim-dist {:.3f}".format(len(Fm), m_rim_mean),
         (Vm, Fm), "#55a868", 1.0),
        ("decimate_qem (rim eroded)\n{} faces  rim-dist {:.3f}".format(len(Fs), s_rim_mean),
         (Vs, Fs), "#dd8452", 1.0),
    ]
    stats = {"target": target, "m_rim_mean": m_rim_mean, "s_rim_mean": s_rim_mean,
             "m_bd": m_bd, "s_bd": s_bd, "be_in": be_in, "ratio_mean": ratio_mean}
    return panels, stats


def main() -> int:
    panels_a, sa = scene_a_closed_sphere()
    panels_b, sb = scene_b_open_hemisphere()

    render_png(panels_a, panels_b,
               _REPO_ROOT / "examples_3d" / "_gallery" / "mesh_decimate.png")

    print(
        "\nPASS: mesh_decimate.decimate_qem_manifold は "
        "(A) 閉じた球で watertight を保ちランダム間引き null を Hausdorff で "
        f"{sa['null_h']/sa['qem_h']:.1f}倍上回り、"
        "(B) 開半球で境界保存 term により rim を元曲線上に保ち、境界 term を持たない既存の"
        f"姉妹 op decimate_qem を rim 逸脱で {sb['ratio_mean']:.0f}倍上回った。"
        "→ decimate_qem との重複ではなく、境界保存・多様体厳格の実効差を持つ別 op")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
