# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 三角形メッシュから法線・表面積・平均曲率を測る (mesh properties).

実世界の問題:
    marching cubes や点群再構成が吐く「メッシュ(頂点 + 三角形の面)」は、そのままでは
    ただの座標の袋だ。レンダリングの陰影付け、CAD の面積見積り、形状検査(尖り/窪みの検出)
    には「各面がどっちを向くか(法線)」「全体でどれだけの表面積か」「各点がどれくらい曲がって
    いるか(曲率)」という幾何量が要る。点群 PCA 法線と違い、メッシュには**面の接続情報**が
    あるので、近傍探索も固有値分解もせず、面の巻き順と cotangent Laplacian だけで
    これらを一貫・正確に求められる。

原理(すべて mesh = (vertices, faces) 入力):
    - face_normals(mesh)    : 各三角形の単位法線 = 正規化した辺の外積(向きは巻き順で一意)。
    - vertex_normals(mesh)  : 面積重み付きで隣接面法線を集約した頂点法線(向きは面から一貫)。
    - mesh_area(mesh)       : 全三角形面積の総和(表面積)。
    - vertex_curvature(mesh): Meyer(2003)の離散 Laplace-Beltrami 作用素 |K|/2 = 平均曲率。

検証(GT):
    原点中心・半径 R の球メッシュ(icosphere)は解析解を持つ:
      1) 表面積 = 4πR²
      2) 平均曲率 = 1/R(全頂点で一定)
      3) 頂点法線は放射方向 p/|p| と一致(外向き)、面法線は面重心方向と一致
    これらと数値照合してアサートする(離散化誤差内)。

beat-the-null(下駄を履かせない基準):
    - 法線 : 符号未定(PCA のように向きが点ごとに任意)な法線は「外向き一致率」がコイン投げ
             ~0.5。面の巻き順から作った法線はほぼ全点(>0.99)が外向きにそろう。
    - 曲率 : 「平面だと思い込む(曲率=0)」素朴な基準は真値 1/R から誤差 1/R 丸ごと。
             実手法は 1/R を <0.1% 精度で復元する。
    - 面積 : 「頂点数 × 定数(平均辺長の正三角形 1 枚ぶん)」の素朴な数え上げは、閉メッシュでは
             面数 ≈ 2×頂点数 ゆえ真値の約半分(~50% 誤差)。実手法は実面積を <0.2% で復元。
    いずれも実手法が null を判別的に上回ることを assert する。

デモ描画:
    球(頂点法線の外向き矢印つき)と、トーラス(頂点曲率でカラーマップ = 外周の尾根が高曲率・
    内側の喉が低曲率)を並べ、右に「実手法 vs null の GT 誤差」棒グラフを添えて PNG 保存する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# このファイル名(examples_3d/mesh_props.py)はルートのモジュール mesh_props.py と同名なので、
# リポジトリルートを sys.path の**先頭**に置き、`import mesh_props` が例自身でなくルートの
# モジュールに解決されるようにする(PYTHONPATH=. で既にルートが末尾にある場合の先取りも兼ねる)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from mesh_props import (  # noqa: E402  (sys.path 調整後に import)
    face_normals,
    mesh_area,
    vertex_curvature,
    vertex_normals,
)


# ═══════════════════════════════════════════════════════════════════════════
# GT を持つメッシュの合成(球 = 解析解 / トーラス = 曲率が変化する可視化用)
# ═══════════════════════════════════════════════════════════════════════════
def icosphere(radius: float = 1.0, subdiv: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """原点中心・半径 radius の球メッシュ(icosahedron を subdiv 回細分し球面へ射影)。

    正二十面体を出発点に各三角形を 4 分割 → 新頂点を球面へ射影、を繰り返す。ほぼ均一で
    非鈍角な三角形が得られ、面積・曲率の離散化誤差が小さい。面の巻き順は外向き(CCW)。
    球にするのが要点で、表面積 4πR²・平均曲率 1/R・外向き法線 p/|p| という解析解を GT にできる。
    """
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    verts = np.array([
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ], dtype=np.float64)
    faces = np.array([
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ], dtype=np.int64)
    verts /= np.linalg.norm(verts, axis=1, keepdims=True)     # 単位球面へ
    for _ in range(subdiv):
        cache: dict[tuple[int, int], int] = {}
        vl = [tuple(v) for v in verts]
        new_faces = []

        def midpoint(a: int, b: int) -> int:
            key = (a, b) if a < b else (b, a)
            hit = cache.get(key)
            if hit is not None:
                return hit
            m = (np.asarray(vl[a]) + np.asarray(vl[b])) / 2.0
            m /= np.linalg.norm(m)                             # 中点を球面へ射影
            vl.append(tuple(m))
            idx = len(vl) - 1
            cache[key] = idx
            return idx

        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        verts = np.asarray(vl, dtype=np.float64)
        faces = np.asarray(new_faces, dtype=np.int64)
    return verts * float(radius), faces


def torus_mesh(r_major: float = 1.0, r_minor: float = 0.35,
               n_u: int = 90, n_v: int = 45
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """トーラス(円環)メッシュを返す。(vertices, faces, tube_angle)。

    u = 中心軸まわりの角、v = チューブ断面の角。曲率が場所で変わる(外周の尾根で高く、内側の
    喉で低い)ので、``vertex_curvature`` のカラーマップ描画に向く。tube_angle は解析的な
    平均曲率の検算に使える(返すだけで assert はしない — GT アサートは球で行う)。
    """
    u = np.linspace(0.0, 2.0 * np.pi, n_u, endpoint=False)
    v = np.linspace(0.0, 2.0 * np.pi, n_v, endpoint=False)
    U, V = np.meshgrid(u, v, indexing="ij")
    x = (r_major + r_minor * np.cos(V)) * np.cos(U)
    y = (r_major + r_minor * np.cos(V)) * np.sin(U)
    z = r_minor * np.sin(V)
    verts = np.column_stack([x.ravel(), y.ravel(), z.ravel()])

    def vid(i: int, j: int) -> int:
        return (i % n_u) * n_v + (j % n_v)

    faces = []
    for i in range(n_u):
        for j in range(n_v):
            a, b, c, d = vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
    return verts, np.asarray(faces, dtype=np.int64), V.ravel()


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# ═══════════════════════════════════════════════════════════════════════════
# デモ描画(matplotlib があれば PNG を保存、無ければ静かにスキップ)
# ═══════════════════════════════════════════════════════════════════════════
def render_gallery(sphere, sph_vn, torus, tor_curv, bars, out_path: Path) -> bool:
    """球(法線矢印)+ トーラス(曲率カラーマップ)+ 誤差棒グラフを 1 枚に描く。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
    except Exception as exc:  # matplotlib 不在など
        print(f"[note] matplotlib が無いため PNG をスキップ: {exc}")
        return False

    # 日本語ラベルが tofu(□)にならないよう CJK フォントを選ぶ。無ければ英語ラベルへ退避。
    jp_ok = _use_jp_font(fm, plt)
    if jp_ok:
        t_title = "mesh_props: メッシュの法線・表面積・平均曲率(GT=球, 可視化=トーラス)"
        t_sphere = "球: 面の巻き順から\n一貫して外向きの頂点法線"
        t_torus = "トーラス: 頂点曲率\n(外周の尾根=高, 内側の喉=低)"
        t_cbar = "平均曲率 |H|"
        t_bar_title = "beat-the-null: 実手法は素朴基準を桁で凌駕"
        t_ylabel = "GT からの相対誤差(小さいほど良い)"
        t_real, t_null = "実手法", "null(素朴基準)"
        t_labels = ["表面積", "平均曲率", "法線向き"]
    else:
        t_title = "mesh_props: mesh normals / surface area / mean curvature (GT=sphere, viz=torus)"
        t_sphere = "Sphere: consistent outward\nvertex normals (from winding)"
        t_torus = "Torus: vertex curvature\n(outer ridge high, inner throat low)"
        t_cbar = "mean curvature |H|"
        t_bar_title = "beat-the-null: real method beats naive by orders"
        t_ylabel = "relative error vs GT (lower is better)"
        t_real, t_null = "real", "null (naive)"
        t_labels = ["area", "curvature", "normal dir"]

    Vs, Fs = sphere
    Vt, Ft = torus
    fig = plt.figure(figsize=(16.5, 5.4))
    fig.suptitle(t_title, fontsize=13, fontweight="bold")

    # --- 左: 球 + 一貫した外向き頂点法線 ---
    ax1 = fig.add_subplot(1, 3, 1, projection="3d")
    ax1.plot_trisurf(Vs[:, 0], Vs[:, 1], Vs[:, 2], triangles=Fs,
                     color=(0.62, 0.74, 0.90), alpha=0.55,
                     linewidth=0.0, antialiased=True)
    step = max(1, len(Vs) // 90)                     # 矢印は間引いて表示
    P = Vs[::step]
    Nn = sph_vn[::step]
    L = 0.42 * float(np.linalg.norm(Vs, axis=1).mean())
    ax1.quiver(P[:, 0], P[:, 1], P[:, 2], Nn[:, 0], Nn[:, 1], Nn[:, 2],
               length=L, color="crimson", linewidth=0.8, normalize=True)
    ax1.set_title(t_sphere, fontsize=10)
    _equal_3d(ax1, Vs)
    ax1.set_axis_off()

    # --- 中: トーラス、頂点曲率でカラーマップ(面ごとに頂点平均) ---
    ax2 = fig.add_subplot(1, 3, 2, projection="3d")
    face_scalar = tor_curv[Ft].mean(axis=1)
    collec = ax2.plot_trisurf(Vt[:, 0], Vt[:, 1], Vt[:, 2], triangles=Ft,
                              cmap="viridis", linewidth=0.0, antialiased=True)
    collec.set_array(face_scalar)
    cbar = fig.colorbar(collec, ax=ax2, shrink=0.62, pad=0.02)
    cbar.set_label(t_cbar, fontsize=9)
    ax2.set_title(t_torus, fontsize=10)
    _equal_3d(ax2, Vt)
    ax2.set_axis_off()

    # --- 右: 実手法 vs null の GT 誤差(対数軸、小さいほど良い) ---
    ax3 = fig.add_subplot(1, 3, 3)
    _, real_err, null_err = bars
    xpos = np.arange(len(t_labels))
    w = 0.38
    floor = 1e-5                                      # log 表示用の下駄(0 を潰さない)
    r_disp = np.maximum(real_err, floor)
    n_disp = np.maximum(null_err, floor)
    b1 = ax3.bar(xpos - w / 2, r_disp, w, label=t_real, color="#2c7fb8")
    b2 = ax3.bar(xpos + w / 2, n_disp, w, label=t_null, color="#d95f0e")
    ax3.set_yscale("log")
    ax3.set_ylabel(t_ylabel, fontsize=9)
    ax3.set_xticks(xpos)
    ax3.set_xticklabels(t_labels, fontsize=9)
    ax3.set_title(t_bar_title, fontsize=10)
    ax3.legend(fontsize=9, loc="upper left")
    for bars_, vals in ((b1, real_err), (b2, null_err)):
        for rect, val in zip(bars_, vals):
            ax3.annotate(f"{val*100:.2g}%", (rect.get_x() + rect.get_width() / 2,
                         max(rect.get_height(), floor)),
                         ha="center", va="bottom", fontsize=7.5)
    ax3.set_ylim(floor, 3.0)

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=125)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


def _equal_3d(ax, V: np.ndarray) -> None:
    """3D 軸のアスペクト比を等方にする(球/トーラスが歪まないように)。"""
    c = V.mean(axis=0)
    r = float(np.abs(V - c).max())
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    R = 2.5                       # 単位球でなく R≠1 にして「スケールに追随」を示す
    Vs, Fs = icosphere(radius=R, subdiv=4)
    sphere = (Vs, Fs)

    # --- 入力の健全性チェック(退化入力で偽の成功を出さない) ---
    if Vs.ndim != 2 or Vs.shape[1] != 3:
        raise ValueError(f"vertices must be (N,3), got {Vs.shape}")
    if Fs.ndim != 2 or Fs.shape[1] != 3:
        raise ValueError(f"faces must be (M,3), got {Fs.shape}")
    if Fs.min() < 0 or Fs.max() >= len(Vs):
        raise ValueError("face index out of range(退化メッシュ)")
    tri = Vs[Fs]
    face_area_chk = 0.5 * np.linalg.norm(
        np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    if not np.all(face_area_chk > 0):
        raise ValueError("ゼロ面積の三角形がある(退化入力)")

    n_v, n_f = len(Vs), len(Fs)
    area_gt = 4.0 * np.pi * R * R
    curv_gt = 1.0 / R
    print(f"[GT] 球 R={R}: 頂点数={n_v}, 面数={n_f}, "
          f"表面積={area_gt:.4f}, 平均曲率={curv_gt:.4f}")

    # ── 実手法(4 op)を実行 ──────────────────────────────────────────
    fn = face_normals(sphere)         # (M,3)
    vn = vertex_normals(sphere)       # (N,3)
    area = mesh_area(sphere)          # float
    curv = vertex_curvature(sphere)   # (N,)

    if fn.shape != (n_f, 3):
        raise ValueError(f"face_normals 形状 {fn.shape} != {(n_f, 3)}")
    if vn.shape != (n_v, 3):
        raise ValueError(f"vertex_normals 形状 {vn.shape} != {(n_v, 3)}")
    if curv.shape != (n_v,):
        raise ValueError(f"vertex_curvature 形状 {curv.shape} != {(n_v,)}")

    # ── GT 照合 ─────────────────────────────────────────────────────
    # 面法線 vs 面重心の外向き / 頂点法線 vs 位置方向の外向き
    face_centroid_dir = _unit(tri.mean(axis=1))
    face_dot = np.einsum("ij,ij->i", fn, face_centroid_dir)
    vert_dot = np.einsum("ij,ij->i", vn, _unit(Vs))
    face_outward = float(np.mean(face_dot > 0.99))
    vert_outward = float(np.mean(vert_dot > 0.99))

    area_relerr = abs(area - area_gt) / area_gt
    curv_med = float(np.median(curv))
    curv_relerr = abs(curv_med - curv_gt) / curv_gt
    curv_spread = float(np.std(curv) / curv_gt)          # 球なので一定に近いはず

    print(f"[measure] 表面積        = {area:.4f}  (GT {area_gt:.4f}, "
          f"相対誤差 {area_relerr:.4%})")
    print(f"[measure] 平均曲率 中央値= {curv_med:.5f} (GT {curv_gt:.5f}, "
          f"相対誤差 {curv_relerr:.4%}, ばらつき {curv_spread:.2%})")
    print(f"[measure] 面法線 外向き率= {face_outward:.4f}  "
          f"(内積>0.99, 平均内積 {face_dot.mean():.4f})")
    print(f"[measure] 頂点法線外向き率= {vert_outward:.4f} "
          f"(内積>0.99, 平均内積 {vert_dot.mean():.4f})")

    # ── beat-the-null 基準線 ────────────────────────────────────────
    # (1) 法線: 符号未定(向き任意)= 頂点法線をランダム符号反転 → 外向き率はコイン投げ
    rng = np.random.default_rng(0)
    flip = rng.integers(0, 2, size=n_v) * 2 - 1          # ±1
    vn_signless = vn * flip[:, None]
    null_vert_dot = np.einsum("ij,ij->i", vn_signless, _unit(Vs))
    null_outward = float(np.mean(null_vert_dot > 0.99))

    # (2) 曲率: 平面仮定 = 曲率 0 → 真値 1/R から誤差 1/R 丸ごと
    null_curv = 0.0
    null_curv_abserr = abs(null_curv - curv_gt)
    real_curv_abserr = abs(curv_med - curv_gt)

    # (3) 面積: 頂点数 × 定数(平均辺長の正三角形 1 枚ぶん)。閉メッシュは面≈2·頂点ゆえ約半分
    edges = np.unique(np.sort(np.vstack(
        [Fs[:, [0, 1]], Fs[:, [1, 2]], Fs[:, [2, 0]]]), axis=1), axis=0)
    mean_edge = float(np.linalg.norm(Vs[edges[:, 0]] - Vs[edges[:, 1]], axis=1).mean())
    null_area = n_v * (np.sqrt(3.0) / 4.0 * mean_edge ** 2)
    null_area_relerr = abs(null_area - area_gt) / area_gt

    print(f"[null] 面積(頂点数×正三角) = {null_area:.4f} (相対誤差 {null_area_relerr:.2%})")
    print(f"[null] 曲率(平面仮定=0)     = {null_curv:.4f} (相対誤差 100%)")
    print(f"[null] 法線(符号未定・任意) = 外向き率 {null_outward:.4f}(コイン投げ ~0.5)")

    # ── GT アサーション(離散化誤差内で真値に一致) ──────────────────
    assert area_relerr < 0.02, f"表面積の相対誤差が大: {area_relerr:.4%}"
    assert curv_relerr < 0.02, f"平均曲率(中央値)の相対誤差が大: {curv_relerr:.4%}"
    assert curv_spread < 0.05, f"球なのに曲率がばらつきすぎ: {curv_spread:.2%}"
    assert face_outward > 0.99, f"面法線の外向き率が低い: {face_outward:.4f}"
    assert vert_outward > 0.99, f"頂点法線の外向き率が低い: {vert_outward:.4f}"

    # ── beat-the-null アサーション(素朴基準を判別的に上回る) ────────
    # 面積: 実手法 <2% に対し null は >30% 誤差、かつ実手法が null を明確に下回る
    assert null_area_relerr > 0.30, f"面積 null が誤差不足で基準にならない: {null_area_relerr:.2%}"
    assert area_relerr < null_area_relerr / 10.0, \
        f"面積が null を桁で上回れていない: {area_relerr:.4%} vs {null_area_relerr:.2%}"
    # 曲率: 実手法の絶対誤差が平面仮定(=1/R)を桁で下回る
    assert real_curv_abserr < null_curv_abserr / 50.0, \
        f"曲率が平面仮定 null を上回れていない: {real_curv_abserr:.4g} vs {null_curv_abserr:.4g}"
    # 法線: 一貫外向き(>0.99)が符号未定 null(コイン投げ ~0.5)を明確に上回る
    assert 0.3 < null_outward < 0.7, f"法線 null がコイン投げ帯から外れ基準にならない: {null_outward:.3f}"
    assert vert_outward - null_outward > 0.4, \
        f"法線が符号未定 null を明確に上回れていない: {vert_outward:.3f} vs {null_outward:.3f}"

    # ── デモ PNG(トーラスは曲率が変化 → カラーマップが映える) ───────
    Vt, Ft, _theta = torus_mesh(r_major=1.0, r_minor=0.35, n_u=90, n_v=45)
    tor_curv = vertex_curvature((Vt, Ft))
    bars = (
        ["表面積", "平均曲率", "法線向き"],
        [area_relerr, curv_relerr, 1.0 - vert_outward],       # 実手法の誤差
        [null_area_relerr, 1.0, 1.0 - null_outward],          # null の誤差
    )
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "mesh_props.png"
    render_gallery(sphere, vn, (Vt, Ft), tor_curv, bars, out_png)

    print(
        f"PASS: 球(R={R})で表面積 {area:.3f}(GT {area_gt:.3f}, 誤差 {area_relerr:.3%})・"
        f"平均曲率 {curv_med:.4f}(GT {curv_gt:.4f}, 誤差 {curv_relerr:.3%})・"
        f"頂点法線外向き率 {vert_outward:.3f} を復元。"
        f"beat-null: 面積 null は {null_area_relerr:.1%} 誤差(実手法が約 {null_area_relerr/max(area_relerr,1e-9):.0f} 倍精確)、"
        f"曲率は平面仮定の誤差 {null_curv_abserr:.3f} を {real_curv_abserr:.2g} まで縮小、"
        f"法線は符号未定 null の外向き率 {null_outward:.2f} を {vert_outward:.2f} へ改善"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
