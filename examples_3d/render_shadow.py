# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: メッシュのキャスト影 / ソフトシャドウで「接地影」を落とす (cast / soft shadow).

実世界の問題:
    合成した 3D シーンを 2D に落として「映える静止画」にしたいとき、法線と光源の内積だけで
    陰影(``render_shaded`` / ``render_lambertian``)を付けても、物体が**別の物体に落とす影**
    (cast shadow)が出ない。床の上に置いた球は、球自身の陰(光に背く面)は暗くなっても、
    床に落ちる**接地影**が無いので宙に浮いて見える。接地影は「物が地面に載っている」という
    最強の奥行き手がかりで、これが 1 枚あるだけで静止画の説得力が跳ね上がる。

原理(shadow mapping; Williams 1978):
    - ``render_shadow.cast_shadow(V, F, light, ...)`` :
        1) 光源をカメラに見立て ``render3d.render_mesh`` で light-space depth(shadow map)を取る
           (既存 z-buffer を再利用、ラスタライザは再発明しない)。
        2) カメラ側 depth から受光面点をワールドへ逆投影し、光源空間へ射影して深度比較。
           手前に別の面があれば「光が届かない=影」。可視性 [0,1] を返す(1=lit, 0=影)。
        3) 半影(penumbra)= 面光源の角半径。中心光源方向のまわりの円錐へ複数方向をばらまき、
           各ハード影を平均する(面光源の近似)。光源が大きいほど半影帯が幾何学的に広がる。

検証(GT):
    床(z=0 の平面)の上に半径 R の球を載せ、平行光 ``ldir`` を当てる。平行光では球の投影影は
    「軸=(球中心, 方向 ldir)・半径 R の円柱」と床の交わり(だ円)で、床の点 S が影に入る条件は
    **中心から直線 (S, ldir) までの垂直距離 <= R**(解析解)。この解析影マスクと、``cast_shadow``
    の暗部(hard, 影<0.5)の **IoU** と**重心位置**を照合する。さらに penumbra を上げると半影
    (0.05<影<0.95 の中間画素)が単調に広がることを確認する。

beat-the-null(下駄を履かせない基準):
    - 影なし(全面 lit = 従来の陰影のみ)は床が一様で、接地影をどこにも作れない → 解析影との
      IoU は 0(暗部が空集合)。``cast_shadow`` は幾何投影と一致する暗部を作り IoU ~0.98 と
      判別的に上回る。
    - 半影: ハード影(penumbra=0)の中間画素はほぼ 0。面光源(penumbra>0)は中間画素が数百〜
      千画素に増え、角半径とともに単調に広がる(素朴なハード影を上回る滑らかさ)。

デモ描画(before/after):
    左=影なし(球が床から浮いて見える)、中=ソフトシャドウ(接地影で床に載って見える)を並置。
    右上=解析 GT だ円の輪郭を ``cast_shadow`` の暗部に重ねて一致を可視化、右下=beat-null
    (接地影 IoU: 実手法 vs 影なし=0)と半影幅(ハード vs 面光源)の棒グラフ。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# このファイル名(examples_3d/render_shadow.py)はルートのモジュール render_shadow.py と
# 同名なので、リポジトリルートを sys.path の**先頭**に置き、`import render_shadow` が例自身
# ではなくルートのモジュールへ解決されるようにする(循環 import 回避)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import render3d  # noqa: E402  (sys.path 調整後に import)
from render_shadow import cast_shadow, unproject_to_world  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# GT を持つシーンの合成(床平面 + その上に載せた球)
# ═══════════════════════════════════════════════════════════════════════════
def icosphere(radius: float = 1.0, subdiv: int = 3,
              center=(0.0, 0.0, 0.0)) -> tuple[np.ndarray, np.ndarray]:
    """原点中心・半径 radius の球メッシュ(icosahedron を subdiv 回細分)を center へ平行移動。"""
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
    verts /= np.linalg.norm(verts, axis=1, keepdims=True)
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
            m /= np.linalg.norm(m)
            vl.append(tuple(m))
            cache[key] = len(vl) - 1
            return cache[key]

        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        verts = np.asarray(vl, dtype=np.float64)
        faces = np.asarray(new_faces, dtype=np.int64)
    return verts * float(radius) + np.asarray(center, np.float64), faces


def ground_plane(size: float, z: float = 0.0,
                 n: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """z=const の正方形の床メッシュ(n×n セル → 2n² 三角形)。受光面(shadow を受ける側)。"""
    xs = np.linspace(-size, size, n + 1)
    ys = np.linspace(-size, size, n + 1)
    V = []
    idx = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            idx[(i, j)] = len(V)
            V.append((x, y, z))
    F = []
    for i in range(n):
        for j in range(n):
            a, b, c, d = idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]
            F += [[a, b, c], [a, c, d]]
    return np.asarray(V, np.float64), np.asarray(F, np.int64)


def analytic_ground_shadow(Pw, ground_mask, sphere_center, radius, ldir) -> np.ndarray:
    """平行光での球の投影影(床上)の解析マスク。中心から直線 (S, ldir) への距離 <= R。"""
    w = sphere_center[None, None, :] - Pw
    proj = np.einsum("ijk,k->ij", w, ldir)
    perp = w - proj[..., None] * ldir[None, None, :]
    dist = np.linalg.norm(perp, axis=-1)
    return ground_mask & (dist <= radius)


def analytic_ground_shadow_point(Pw, ground_mask, sphere_center, radius,
                                 light_pos) -> np.ndarray:
    """点光源での球の投影影(床上, umbra)の解析マスク。

    平行光 GT (``analytic_ground_shadow``) の点光源版。光源 ``L`` から床点 ``S`` への線分が
    球(中心 ``C``, 半径 ``R``)を貫き、かつ球が ``L`` と ``S`` の間にあるとき ``S`` は影。
    判定は光線と球の交差(点→直線の垂直距離 <= R かつ入射点が線分内)で、shadow-mapping
    アルゴリズムとは独立に導く。点光源なので影は透視投影で拡大・シフトする(平行光と別解)。"""
    L = np.asarray(light_pos, np.float64).reshape(3)
    C = np.asarray(sphere_center, np.float64).reshape(3)
    d = Pw - L[None, None, :]                             # L -> S
    seg = np.linalg.norm(d, axis=-1)                      # |S - L|
    with np.errstate(invalid="ignore", divide="ignore"):
        u = d / seg[..., None]                            # 単位方向(背景 NaN)
    w = C - L                                             # L -> C(全画素共通)
    s = np.einsum("ijk,k->ij", u, w)                     # L から最近接点までの距離
    perp = np.linalg.norm(w[None, None, :] - s[..., None] * u, axis=-1)
    half = np.sqrt(np.clip(radius * radius - perp * perp, 0.0, None))
    t_near = s - half                                     # 球への入射点(L からの距離)
    hit = np.isfinite(perp) & (perp <= radius) & (s > 0.0) & (t_near < seg)
    return ground_mask & hit


# ═══════════════════════════════════════════════════════════════════════════
# デモ描画
# ═══════════════════════════════════════════════════════════════════════════
def _use_jp_font(fm, plt) -> bool:
    candidates = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans CJK JP",
                  "Noto Sans JP", "BIZ UDGothic", "Yu Mincho", "MS Mincho"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return True
    return False


def _shade_rgb(view, pose, ldir, ground_mask, sphere_mask, shadow, ambient=0.30):
    """法線 Lambertian + キャスト影を合成して RGB (H,W,3) を作る。背景は空色。"""
    normals = view["normals"]
    surf = view["silhouette"] > 0
    light_cam = pose[:3, :3] @ ldir                        # 光源をカメラ空間へ
    ndotl = np.clip(np.einsum("ijk,k->ij", normals, light_cam), 0.0, 1.0)
    albedo = np.where(ground_mask, 0.88, 0.0)
    albedo = np.where(sphere_mask, 0.62, albedo)
    albedo = np.where(surf & (albedo == 0.0), 0.75, albedo)   # 念のための既定
    direct = albedo * (0.22 + 0.78 * ndotl)
    comp = ambient + (1.0 - ambient) * np.clip(shadow, 0.0, 1.0)   # 影で直接光を減衰
    val = np.clip(direct * comp, 0.0, 1.0)
    tint = np.array([1.0, 0.985, 0.945])                    # ほんのり暖色
    rgb = np.ones((*val.shape, 3), np.float64) * np.array([0.90, 0.93, 0.975])  # 空色
    surf_rgb = np.clip(val[..., None] * tint[None, None, :], 0.0, 1.0)
    rgb[surf] = surf_rgb[surf]
    return rgb


def render_gallery(before_rgb, after_rgb, overlay, iou_real, iou_null,
                   widths, out_path: Path) -> bool:
    """before/after + GT 重ね合わせ + beat-null 棒グラフを 1 枚に描く。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
    except Exception as exc:
        print(f"[note] matplotlib が無いため PNG をスキップ: {exc}")
        return False

    jp = _use_jp_font(fm, plt)
    if jp:
        t_title = "render_shadow: キャスト影/ソフトシャドウで接地影を落とす(GT=平行光の投影だ円)"
        t_before = "before: 影なし(法線陰影のみ)\n球が床から浮いて見える"
        t_after = "after: ソフトシャドウ\n接地影で床に載って見える"
        t_overlay = "検証: cast_shadow の暗部(灰)に\n解析 GT だ円の輪郭(赤)を重ねる"
        t_bar1 = "接地影の一致 IoU"
        t_bar2 = "半影の幅(中間画素数)"
        t_real, t_null = "実手法", "影なし(null)"
        t_wlab = ["ハード", "面光源(小)", "面光源(大)"]
    else:
        t_title = "render_shadow: cast / soft shadow — grounding shadow (GT = parallel-light ellipse)"
        t_before = "before: no shadow (shading only)\nsphere looks to float"
        t_after = "after: soft shadow\nsphere sits on the ground"
        t_overlay = "verify: cast_shadow dark region (gray)\nvs analytic GT ellipse outline (red)"
        t_bar1 = "grounding-shadow IoU"
        t_bar2 = "penumbra width (partial px)"
        t_real, t_null = "real", "no shadow (null)"
        t_wlab = ["hard", "area (small)", "area (large)"]

    fig = plt.figure(figsize=(14.5, 9.2))
    fig.suptitle(t_title, fontsize=13, fontweight="bold")

    ax1 = fig.add_subplot(2, 2, 1)
    ax1.imshow(before_rgb)
    ax1.set_title(t_before, fontsize=10)
    ax1.set_axis_off()

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.imshow(after_rgb)
    ax2.set_title(t_after, fontsize=10)
    ax2.set_axis_off()

    ax3 = fig.add_subplot(2, 2, 3)
    meas_img, gt_mask = overlay
    ax3.imshow(meas_img, cmap="gray", vmin=0.0, vmax=1.0)
    ax3.contour(gt_mask.astype(float), levels=[0.5], colors=["crimson"], linewidths=1.4)
    ax3.set_title(f"{t_overlay}  (IoU={iou_real:.3f})", fontsize=10)
    ax3.set_axis_off()

    ax4 = fig.add_subplot(2, 2, 4)
    # 左軸: IoU(実手法 vs null)/ 右軸: 半影幅
    xpos = np.array([0.0, 1.0])
    b1 = ax4.bar(xpos, [iou_real, iou_null], width=0.5,
                 color=["#2c7fb8", "#d95f0e"])
    ax4.set_ylabel(t_bar1, fontsize=9)
    ax4.set_ylim(0.0, 1.05)
    ax4.set_xticks(xpos)
    ax4.set_xticklabels([t_real, t_null], fontsize=9)
    for rect, val in zip(b1, [iou_real, iou_null]):
        ax4.annotate(f"{val:.2f}", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                     ha="center", va="bottom", fontsize=9)

    ax4b = ax4.twinx()
    xw = np.array([2.6, 3.6, 4.6])
    b2 = ax4b.bar(xw, widths, width=0.5, color="#6a51a3", alpha=0.85)
    ax4b.set_ylabel(t_bar2, fontsize=9)
    ax4b.set_ylim(0.0, max(widths) * 1.25 + 1.0)
    for rect, val in zip(b2, widths):
        ax4b.annotate(f"{int(val)}", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                      ha="center", va="bottom", fontsize=8)
    ax4.set_xlim(-0.6, 5.2)
    ax4.set_xticks(list(xpos) + list(xw))
    ax4.set_xticklabels([t_real, t_null] + t_wlab, fontsize=8, rotation=12)
    ax4.set_title("beat-the-null", fontsize=10)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=125)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # ── シーン: 床平面 + その上に載せた球 ─────────────────────────────
    R = 0.9
    Vp, Fp = ground_plane(4.0, z=0.0, n=2)
    center_sph = np.array([0.0, 0.0, R])                 # 床に接して載る
    Vs, Fs = icosphere(R, subdiv=3, center=center_sph)
    V = np.vstack([Vp, Vs])
    F = np.vstack([Fp, Fs + len(Vp)])

    # ── 入力健全性(退化入力で偽の成功を出さない)──────────────────────
    if V.ndim != 2 or V.shape[1] != 3 or F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("mesh shape invalid")
    if F.min() < 0 or F.max() >= len(V):
        raise ValueError("face index out of range(退化メッシュ)")

    # ── カメラ・光源 ─────────────────────────────────────────────────
    W, H = 420, 320
    eye = np.array([3.6, -4.2, 3.2])
    pose = render3d.look_at(eye, [0.15, 0.15, 0.45], up=(0.0, 0.0, 1.0))
    K = render3d.intrinsics_from_fov(46.0, W, H)
    ldir = np.array([0.4, 0.25, 1.0])
    ldir = ldir / np.linalg.norm(ldir)                   # シーン→光源(平行光)

    # ── cast_shadow(ハード / 面光源小 / 面光源大)───────────────────────
    sh_hard = cast_shadow(V, F, ldir, pose=pose, intrinsics=K, width=W, height=H,
                          directional=True, penumbra=0.0, shadow_res=512)
    sh_soft_s = cast_shadow(V, F, ldir, pose=pose, intrinsics=K, width=W, height=H,
                            directional=True, penumbra=3.0, samples=16, shadow_res=384)
    sh_soft_l = cast_shadow(V, F, ldir, pose=pose, intrinsics=K, width=W, height=H,
                            directional=True, penumbra=6.0, samples=16, shadow_res=384)

    if sh_hard.shape != (H, W):
        raise ValueError(f"shadow shape {sh_hard.shape} != {(H, W)}")
    if not (np.all(sh_hard >= 0.0) and np.all(sh_hard <= 1.0)):
        raise ValueError("shadow map の値域が [0,1] を外れた")

    # ── 幾何バッファと GT マスク ─────────────────────────────────────
    view = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=W, height=H)
    Pw = unproject_to_world(view["depth"], pose, K)
    surf = np.all(np.isfinite(Pw), axis=-1)
    ground = surf & (np.abs(Pw[..., 2]) < 0.05)          # 床(z≈0)の画素
    sphere = surf & ~ground                              # 球の画素
    gt = analytic_ground_shadow(Pw, ground, center_sph, R, ldir)

    meas_hard = ground & (sh_hard < 0.5)                 # 実手法の暗部(床上)
    inter = int((gt & meas_hard).sum())
    union = int((gt | meas_hard).sum())
    iou_real = inter / max(union, 1)
    fp = int((meas_hard & ~gt).sum())
    fn = int((gt & ~meas_hard).sum())

    def centroid2d(mask):
        pts = Pw[mask]
        return pts[:, :2].mean(axis=0) if mask.any() else np.array([np.nan, np.nan])

    gt_c = centroid2d(gt)
    meas_c = centroid2d(meas_hard)
    cdist = float(np.linalg.norm(gt_c - meas_c))

    # ── beat-null: 影なし(全面 lit)は接地影を作れない → IoU 0 ──────────
    null_shadow = np.ones((H, W), np.float64)
    null_meas = ground & (null_shadow < 0.5)             # = 空集合
    null_union = int((gt | null_meas).sum())
    iou_null = int((gt & null_meas).sum()) / max(null_union, 1)

    # ── 半影の幅(中間画素数)が角半径で単調に広がる ─────────────────────
    def partial_px(sh):
        return int((ground & (sh > 0.05) & (sh < 0.95)).sum())
    w_hard = partial_px(sh_hard)
    w_soft_s = partial_px(sh_soft_s)
    w_soft_l = partial_px(sh_soft_l)

    print(f"[GT] 床画素={int(ground.sum())} 球画素={int(sphere.sum())} "
          f"解析影(床)={int(gt.sum())} px")
    print(f"[measure] 接地影 IoU(hard vs GT) = {iou_real:.4f}  "
          f"(fp={fp}, fn={fn}, 重心ずれ={cdist:.4f} / R={R})")
    print(f"[measure] 半影の幅(中間画素) hard={w_hard}  面光源3°={w_soft_s}  面光源6°={w_soft_l}")
    print(f"[null] 影なしの接地影 IoU = {iou_null:.4f}(暗部が空集合 → 幾何影を全く当てられない)")

    # ── fail-closed の確認(退化入力を確実に拒否)─────────────────────
    for bad_call, desc in (
        (lambda: cast_shadow(V, np.zeros((0, 3), np.int64), ldir, pose=pose,
                             intrinsics=K, width=W, height=H), "空 face"),
        (lambda: cast_shadow(V, F, np.zeros(3), pose=pose, intrinsics=K,
                             width=W, height=H), "ゼロ光源ベクトル"),
    ):
        try:
            bad_call()
        except ValueError:
            pass
        else:
            raise AssertionError(f"fail-closed 破れ: {desc} が例外にならなかった")

    # ── GT アサーション ──────────────────────────────────────────────
    assert iou_real >= 0.90, f"接地影 IoU が低い(GT と不一致): {iou_real:.4f}"
    assert cdist < 0.25 * R, f"接地影の重心が GT からずれすぎ: {cdist:.4f} (R={R})"
    assert fp < 0.1 * max(int(gt.sum()), 1), f"床の偽影(acne)が多すぎ: fp={fp}"

    # ── beat-null アサーション(判別的に上回る)───────────────────────
    assert iou_null == 0.0, f"影なし null が接地影を当ててしまう(基準不成立): {iou_null:.4f}"
    assert iou_real - iou_null > 0.8, \
        f"接地影が影なし null を判別的に上回れていない: {iou_real:.3f} vs {iou_null:.3f}"

    # ── 半影が角半径で単調に広がる(ハードを上回る滑らかさ)──────────────
    assert w_hard <= 60, f"ハード影なのに中間画素が多すぎ(縁が甘い): {w_hard}"
    assert w_soft_s > max(5 * (w_hard + 1), 150), \
        f"面光源(小)で半影が十分広がっていない: {w_soft_s}"
    assert w_soft_l > w_soft_s, \
        f"半影が角半径で広がっていない: 6°={w_soft_l} <= 3°={w_soft_s}"

    # ═══════════════════════════════════════════════════════════════════
    # 点光源 (directional=False) の検証 — fixed した dist_c 経路を実際に走らせる
    #   directional=True しか叩いていなかったため、点光源の NameError が検出漏れしていた。
    #   ここで hard(penumbra=0)と面光源(penumbra>0)の両方を走らせ、透視投影の解析 GT
    #   (アルゴリズムとは独立)と照合し、beat-null と半影単調性まで確認する。
    # ═══════════════════════════════════════════════════════════════════
    Lpt = np.array([3.0, 2.0, 6.5])                      # 床の上方・斜めの点光源(位置)
    sh_pt_hard = cast_shadow(V, F, Lpt, pose=pose, intrinsics=K, width=W, height=H,
                             directional=False, penumbra=0.0, shadow_res=512)
    sh_pt_soft_s = cast_shadow(V, F, Lpt, pose=pose, intrinsics=K, width=W, height=H,
                               directional=False, penumbra=3.0, samples=16, shadow_res=384)
    sh_pt_soft_l = cast_shadow(V, F, Lpt, pose=pose, intrinsics=K, width=W, height=H,
                               directional=False, penumbra=6.0, samples=16, shadow_res=384)

    if sh_pt_hard.shape != (H, W):
        raise ValueError(f"point-light shadow shape {sh_pt_hard.shape} != {(H, W)}")
    if not (np.all(sh_pt_hard >= 0.0) and np.all(sh_pt_hard <= 1.0)):
        raise ValueError("point-light shadow map の値域が [0,1] を外れた")

    gt_pt = analytic_ground_shadow_point(Pw, ground, center_sph, R, Lpt)
    meas_pt = ground & (sh_pt_hard < 0.5)                # 点光源ハード影の暗部(床上)
    inter_pt = int((gt_pt & meas_pt).sum())
    union_pt = int((gt_pt | meas_pt).sum())
    iou_pt = inter_pt / max(union_pt, 1)
    fp_pt = int((meas_pt & ~gt_pt).sum())
    fn_pt = int((gt_pt & ~meas_pt).sum())
    gt_pt_c = centroid2d(gt_pt)
    meas_pt_c = centroid2d(meas_pt)
    cdist_pt = float(np.linalg.norm(gt_pt_c - meas_pt_c))

    # beat-null: 影なし(全面 lit)は点光源でも接地影を作れない → IoU 0(空集合)
    null_pt_meas = ground & (null_shadow < 0.5)
    iou_pt_null = int((gt_pt & null_pt_meas).sum()) / max(int((gt_pt | null_pt_meas).sum()), 1)

    # 判別性(透視投影が効いているか): 点光源方向を平行光として近似した GT では、点光源影
    # の拡大・シフトを再現できず一致が落ちる。点光源影は自分の点光源 GT の方をよく当てる。
    ldir_from_pt = (Lpt - center_sph) / np.linalg.norm(Lpt - center_sph)
    gt_pt_as_parallel = analytic_ground_shadow(Pw, ground, center_sph, R, ldir_from_pt)
    iou_pt_vs_par = int((gt_pt_as_parallel & meas_pt).sum()) / \
        max(int((gt_pt_as_parallel | meas_pt).sum()), 1)

    def partial_px_pt(sh):
        return int((ground & (sh > 0.05) & (sh < 0.95)).sum())
    wp_hard = partial_px_pt(sh_pt_hard)
    wp_soft_s = partial_px_pt(sh_pt_soft_s)
    wp_soft_l = partial_px_pt(sh_pt_soft_l)

    print(f"[point] 解析影(床,umbra)={int(gt_pt.sum())} px  IoU(hard vs 点光源GT)={iou_pt:.4f}  "
          f"(fp={fp_pt}, fn={fn_pt}, 重心ずれ={cdist_pt:.4f} / R={R})")
    print(f"[point] beat-null: 影なし IoU={iou_pt_null:.4f} / 平行光近似GTでの IoU={iou_pt_vs_par:.4f} "
          f"(< 点光源GT {iou_pt:.4f} = 透視投影を実際に計算)")
    print(f"[point] 半影の幅(中間画素) hard={wp_hard}  面光源3°={wp_soft_s}  面光源6°={wp_soft_l}")

    # ── 点光源 GT アサーション(独立 GT に対して判別的)─────────────────
    assert int(gt_pt.sum()) > 50, f"点光源の解析影が小さすぎ(シーン設定を確認): {int(gt_pt.sum())}"
    assert iou_pt >= 0.90, f"点光源の接地影 IoU が低い(GT と不一致): {iou_pt:.4f}"
    assert cdist_pt < 0.25 * R, f"点光源の接地影の重心が GT からずれすぎ: {cdist_pt:.4f} (R={R})"
    assert fp_pt < 0.1 * max(int(gt_pt.sum()), 1), f"点光源の床の偽影(acne)が多すぎ: fp={fp_pt}"
    assert iou_pt_null == 0.0, f"影なし null が点光源の接地影を当ててしまう: {iou_pt_null:.4f}"
    assert iou_pt - iou_pt_null > 0.8, \
        f"点光源の接地影が影なし null を判別的に上回れていない: {iou_pt:.3f} vs {iou_pt_null:.3f}"
    assert iou_pt > iou_pt_vs_par, \
        f"点光源影が平行光近似 GT と同等以上に一致(透視投影が効いていない疑い): " \
        f"点GT={iou_pt:.3f} 平行GT={iou_pt_vs_par:.3f}"

    # ── 点光源でも半影が角半径で単調に広がる ─────────────────────────────
    assert wp_hard <= 80, f"点光源ハード影なのに中間画素が多すぎ(縁が甘い): {wp_hard}"
    assert wp_soft_s > wp_hard, f"点光源(面光源小)で半影が広がっていない: {wp_soft_s} <= {wp_hard}"
    assert wp_soft_l > wp_soft_s, \
        f"点光源の半影が角半径で広がっていない: 6°={wp_soft_l} <= 3°={wp_soft_s}"

    # ── デモ PNG(before=影なし / after=ソフトシャドウ)────────────────
    before_rgb = _shade_rgb(view, pose, ldir, ground, sphere, null_shadow)
    after_rgb = _shade_rgb(view, pose, ldir, ground, sphere, sh_soft_l)
    # 検証パネル: 実手法の暗部を灰、GT だ円輪郭を赤で重ねる(床のみ)
    meas_img = np.ones((H, W)) * 0.97
    meas_img[ground] = 0.85
    meas_img[meas_hard] = 0.35
    overlay = (meas_img, gt)
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "render_shadow.png"
    render_gallery(before_rgb, after_rgb, overlay, iou_real, iou_null,
                   [w_hard, w_soft_s, w_soft_l], out_png)

    print(
        f"PASS: 球(R={R})を床に載せた平行光シーンで、cast_shadow のハード影が解析 GT だ円と "
        f"IoU {iou_real:.3f}(重心ずれ {cdist:.3f}, fp={fp}/fn={fn})で一致。"
        f"beat-null: 影なし(従来の陰影のみ)は接地影 IoU {iou_null:.2f}(暗部=空集合で幾何影を"
        f"全く当てられない)を、実手法は {iou_real:.2f} へ。"
        f"半影は角半径とともに中間画素 {w_hard}→{w_soft_s}→{w_soft_l} と単調に拡大。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
