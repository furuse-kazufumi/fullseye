# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: アンビエントオクルージョン(AO)で「触れ合う所・窪む所」に柔らかい影を落とす。

実世界の問題:
    法線と光源だけの Lambertian 陰影(render_shaded / render_lambertian)は、面の *向き* しか
    見ていない。だから平面に載った球の接触部や、溝の底のような「周囲の面に空を遮られて暗くなる
    場所」の影が出ず、CG がのっぺり平坦に見える。写実的な静止画で立体感を決めるのは、この
    「凹んだ所・触れ合う所に自然に溜まる柔らかい環境影」= アンビエントオクルージョンだ。

原理(物体空間 AO):
    各頂点から外向き法線まわりの半球へ多数のレイを飛ばし、``max_dist`` 以内でメッシュ自身に
    当たった割合(cos 重み)を遮蔽率とし、``AO = 1 - 遮蔽率`` を [0,1] で返す(1=露出/0=遮蔽)。
    これは拡散 AO の定義 ``AO = 1 - (1/π)∫ V(ω) cosθ dω`` の半球一様サンプリング近似。
    画像化(ambient_occlusion)は render3d.render_mesh の depth/silhouette を土台に、頂点 AO を
    可視面へ逆投影補間して焼き込む(ラスタライズは再発明しない)。

検証(GT — 解析的に自明な到達性順序):
    (A) 平面に載る球:接触部(下)は平面に半球を遮られて AO→0、頂上(上)は開空で AO→1。
        高さと AO は強く単調(頂点の z と AO の Spearman 相関 ≈ 1)。
    (B) 波状の溝(cos 波高フィールド)の谷は凹、尾根は凸。谷 AO < 尾根 AO。
        振幅(=溝の深さ)を上げると谷 AO は単調に低下する(深いほど暗い)。

beat-the-null(下駄を履かせない基準):
    一様照明 = AO を 1 一定にした基準は、凹凸のコントラストを一切持たない。
      - 球:頂上−接触部の AO 差 = 0(実手法は >0.5)。高さとの相関も定義できない(定数)。
      - 溝:谷−尾根の AO 差 = 0(実手法は深い溝で >0.3)、深さに対する単調性も無い。
    実手法が「凹部 < 凸部」という既知順序を有意マージンで判別的に再現することを assert する。

デモ描画(before/after):
    平面に載る球を、(1) 無処理の Lambertian(接触影が無く平坦)と (2) Lambertian×AO
    (接触部にリング状の柔らかい影)で並置。加えて AO マップそのものと、溝の深さ掃引の
    「谷 AO は深いほど下がる(実手法) vs 一定(null)」曲線を 1 枚の PNG に保存する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# このファイル名(examples_3d/render_ao.py)はルートのモジュール render_ao.py と同名なので、
# リポジトリルートを sys.path 先頭へ置き `import render_ao` がルート側に解決されるようにする。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import render3d  # noqa: E402
from render_ao import ambient_occlusion, vertex_occlusion  # noqa: E402

try:
    from match3d import render_shaded  # noqa: E402
except Exception:  # フォールバック(向き→拡散のみの簡易版)
    def render_shaded(normals_img, light=(0, 0, 1), ambient=0.1):
        n = np.asarray(normals_img, float)
        L = np.asarray(light, float)
        L = L / np.linalg.norm(L)
        ndl = np.clip((n * L).sum(-1), 0, 1)
        return np.clip(ambient + (1 - ambient) * ndl, 0, 1)


# ═══════════════════════════════════════════════════════════════════════════
# GT を持つメッシュの合成
# ═══════════════════════════════════════════════════════════════════════════
def icosphere(radius: float = 1.0, subdiv: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """原点中心・半径 radius の球メッシュ(icosahedron を subdiv 回細分)。巻き順は外向き。"""
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
    return verts * float(radius), faces


def grid_plane(ext: float, n: int, z: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """z 高さの正方形パッチ(格子)メッシュ。巻き順は上向き(+z)法線。"""
    xs = np.linspace(-ext, ext, n)
    X, Y = np.meshgrid(xs, xs)
    V = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, float(z))])
    f = []
    for i in range(n - 1):
        for j in range(n - 1):
            a, b = i * n + j, i * n + j + 1
            c, d = (i + 1) * n + j + 1, (i + 1) * n + j
            f += [[a, b, c], [a, c, d]]                 # CCW → +z 法線
    return V, np.asarray(f, np.int64)


def corrugated(amp: float, lam: float = 1.0, n: int = 34, ext: float = 4.0
               ) -> tuple[np.ndarray, np.ndarray]:
    """波状の溝(高フィールド z = -amp·cos(2πx/λ))。x が λ の整数倍で谷(z=-amp)、
    半整数倍で尾根(z=+amp)。amp が深さ。巻き順は上向き法線。"""
    xs = np.linspace(-ext, ext, n)
    X, Y = np.meshgrid(xs, xs)
    Z = -amp * np.cos(2.0 * np.pi * X / lam)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    f = []
    for i in range(n - 1):
        for j in range(n - 1):
            a, b = i * n + j, i * n + j + 1
            c, d = (i + 1) * n + j + 1, (i + 1) * n + j
            f += [[a, b, c], [a, c, d]]
    return V, np.asarray(f, np.int64)


def combine(m1, m2):
    (V1, F1), (V2, F2) = m1, m2
    return np.vstack([V1, V2]), np.vstack([F1, F2 + len(V1)])


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


def render_gallery(before, after, ao_img, sweep, out_path: Path) -> bool:
    """無処理 Lambertian / Lambertian×AO / AO マップ / 深さ掃引曲線を 1 枚に描く。"""
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
        t_title = "render_ao: アンビエントオクルージョンで接触影・窪み影を落とす(GT=球+溝)"
        t_before = "無処理 Lambertian\n(向きのみ → 接触影が無く平坦)"
        t_after = "Lambertian × AO(本op)\n(接触部にリング状の柔らかい影)"
        t_ao = "AO マップ(本op出力)\n暗いほど遮蔽・明るいほど露出"
        t_sweep = "beat-the-null: 溝が深いほど谷は暗い(実) vs 一定(null)"
        t_xlabel = "溝の深さ(振幅)"
        t_ylabel = "AO(1=露出)"
        s_valley, s_ridge, s_null = "谷 AO(凹・実手法)", "尾根 AO(凸・実手法)", "null(一様=1)"
    else:
        t_title = "render_ao: ambient occlusion adds contact / cavity shadows (GT=sphere+groove)"
        t_before = "plain Lambertian\n(orientation only -> flat, no contact shadow)"
        t_after = "Lambertian x AO (this op)\n(soft ring shadow at the contact)"
        t_ao = "AO map (op output)\ndark = occluded, bright = exposed"
        t_sweep = "beat-the-null: deeper groove -> darker valley (real) vs constant (null)"
        t_xlabel = "groove depth (amplitude)"
        t_ylabel = "AO (1 = exposed)"
        s_valley, s_ridge, s_null = "valley AO (concave, real)", "ridge AO (convex, real)", "null (uniform=1)"

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9.6))
    fig.suptitle(t_title, fontsize=13, fontweight="bold")

    ax = axes[0, 0]
    ax.imshow(before, cmap="gray", vmin=0.0, vmax=1.0)
    ax.set_title(t_before, fontsize=10)
    ax.set_axis_off()

    ax = axes[0, 1]
    ax.imshow(after, cmap="gray", vmin=0.0, vmax=1.0)
    ax.set_title(t_after, fontsize=10)
    ax.set_axis_off()

    ax = axes[1, 0]
    im = ax.imshow(ao_img, cmap="magma", vmin=0.0, vmax=1.0)
    ax.set_title(t_ao, fontsize=10)
    ax.set_axis_off()
    cb = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.02)
    cb.set_label("AO", fontsize=9)

    ax = axes[1, 1]
    amps, valley, ridge = sweep
    ax.plot(amps, ridge, "-o", color="#2c7fb8", label=s_ridge, linewidth=2)
    ax.plot(amps, valley, "-o", color="#d95f0e", label=s_valley, linewidth=2)
    ax.axhline(1.0, ls="--", color="#555555", label=s_null, linewidth=1.5)
    ax.fill_between(amps, valley, ridge, color="#d95f0e", alpha=0.10)
    ax.set_xlabel(t_xlabel, fontsize=10)
    ax.set_ylabel(t_ylabel, fontsize=10)
    ax.set_ylim(0.0, 1.05)
    ax.set_title(t_sweep, fontsize=10)
    ax.legend(fontsize=9, loc="lower left")
    ax.grid(alpha=0.3)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
def _mask_background(shade: np.ndarray, sil: np.ndarray, bg: float = 0.85) -> np.ndarray:
    out = shade.copy()
    out[sil <= 0] = bg
    return out


def main() -> int:
    try:
        from scipy.stats import spearmanr
    except Exception as exc:                          # scipy は必須依存だが念のため
        raise RuntimeError(f"scipy.stats が必要: {exc}")

    rng = np.random.default_rng(0)
    R = 1.0
    gap = 0.05 * R                                    # 接触ちょうどの退化を避ける微小隙間

    # ── シーン A: 平面に載る球 ───────────────────────────────────────
    Vs, Fs = icosphere(R, subdiv=3)
    Vs = Vs.copy()
    Vs[:, 2] += R + gap                               # 底が z=gap、平面 z=0 に載る
    plane = grid_plane(ext=3.0 * R, n=26, z=0.0)
    n_sph = len(Vs)
    V, F = combine((Vs, Fs), plane)

    # 入力健全性(退化で偽の成功を出さない)
    tri = V[F]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    if not np.all(area > 0):
        raise ValueError("ゼロ面積の三角形がある(退化入力)")

    ao = vertex_occlusion(V, F, n_dirs=64, max_dist=2.5 * R)
    if ao.shape != (len(V),):
        raise ValueError(f"vertex_occlusion 形状 {ao.shape} != {(len(V),)}")
    if not np.all((ao >= -1e-9) & (ao <= 1.0 + 1e-9)):
        raise ValueError("AO が [0,1] の外に出た")

    ao_sph = ao[:n_sph]
    zc = Vs[:, 2]                                     # 球頂点の高さ(GT 順序)
    top_mask = zc > (zc.max() - 0.20 * R)
    bot_mask = zc < (zc.min() + 0.20 * R)
    top_ao = float(ao_sph[top_mask].mean())
    bot_ao = float(ao_sph[bot_mask].mean())
    real_margin = top_ao - bot_ao
    real_rho = float(spearmanr(zc, ao_sph).correlation)

    # 平面側の副次 GT: 球直下ほど暗く、遠いほど明るい(半径方向に単調)
    ao_pln = ao[n_sph:]
    Vp = V[n_sph:]
    rad = np.linalg.norm(Vp[:, :2], axis=1)
    near = rad < 1.3 * R
    far = (rad > 2.0 * R) & (rad < 2.8 * R)
    pln_near = float(ao_pln[near].mean())
    pln_far = float(ao_pln[far].mean())

    print(f"[GT-A] 球+平面: 頂点 {len(V)} / 面 {len(F)}")
    print(f"[measure-A] 球 頂上AO={top_ao:.3f}  接触部AO={bot_ao:.3f}  差={real_margin:.3f}")
    print(f"[measure-A] Spearman(高さ, AO)={real_rho:.3f}  AO範囲=[{ao.min():.3f},{ao.max():.3f}]")
    print(f"[measure-A] 平面 球直下AO={pln_near:.3f}  遠方AO={pln_far:.3f}")

    # ── シーン B: 溝の深さ掃引(谷 AO の単調性 GT) ─────────────────────
    amps = np.array([0.08, 0.20, 0.35, 0.55, 0.80])
    lam = 1.0
    valley_aos, ridge_aos = [], []
    for amp in amps:
        Vg, Fg = corrugated(amp, lam=lam, n=34, ext=4.0)
        aog = vertex_occlusion(Vg, Fg, n_dirs=48, max_dist=2.5)
        interior = (np.abs(Vg[:, 0]) < 3.0) & (np.abs(Vg[:, 1]) < 3.0)
        # 谷 = x が λ の整数倍(cos=1 → z 最小)、尾根 = 半整数倍
        valley = interior & (np.abs(((Vg[:, 0] + 0.5) % lam) - 0.5) < 0.10)
        ridge = interior & (np.abs((Vg[:, 0] % lam) - 0.5) < 0.10)
        valley_aos.append(float(aog[valley].mean()))
        ridge_aos.append(float(aog[ridge].mean()))
    valley_aos = np.asarray(valley_aos)
    ridge_aos = np.asarray(ridge_aos)
    deep_margin = float(ridge_aos[-1] - valley_aos[-1])

    print(f"[GT-B] 溝 深さ掃引 谷AO = {np.array2string(valley_aos, precision=3)}")
    print(f"[GT-B]           尾根AO = {np.array2string(ridge_aos, precision=3)}")
    print(f"[measure-B] 最深部 尾根−谷 = {deep_margin:.3f}")

    # ── beat-the-null(AO=1 一定は凹凸を判別できない) ──────────────────
    null_ao = np.ones_like(ao_sph)
    null_margin = float(null_ao[top_mask].mean() - null_ao[bot_mask].mean())   # = 0
    null_deep_margin = 0.0                             # 谷も尾根も 1 → 差 0
    print(f"[null] 球 頂上−接触 = {null_margin:.3f}(一様=判別不能)")
    print(f"[null] 溝 尾根−谷   = {null_deep_margin:.3f}(一様=判別不能)")

    # ── GT アサーション ─────────────────────────────────────────────
    assert real_margin > 0.5, f"球の頂上−接触 AO 差が小さい: {real_margin:.3f}"
    assert bot_ao < 0.35, f"接触部が暗くなっていない: {bot_ao:.3f}"
    assert top_ao > 0.9, f"頂上が露出していない: {top_ao:.3f}"
    assert real_rho > 0.8, f"高さと AO の単調性が弱い: {real_rho:.3f}"
    assert pln_near < pln_far - 0.1, \
        f"平面の球直下が遠方より暗くなっていない: near {pln_near:.3f} vs far {pln_far:.3f}"
    # 溝: 谷 AO が深さに対し単調減少(意味あるステップで)、かつ谷 < 尾根
    dv = np.diff(valley_aos)
    assert np.all(dv < -0.01), f"谷 AO が深さに単調減少していない: diff={np.array2string(dv, precision=3)}"
    assert deep_margin > 0.3, f"最深部の尾根−谷マージンが小さい: {deep_margin:.3f}"
    assert np.all(valley_aos < ridge_aos), "谷 AO が尾根 AO を下回っていない"

    # ── beat-the-null アサーション(既知順序を判別的に上回る) ──────────
    assert abs(null_margin) < 1e-9, f"null 球マージンが 0 でない: {null_margin}"
    assert real_margin > null_margin + 0.4, \
        f"球で null を判別的に上回れていない: {real_margin:.3f} vs {null_margin:.3f}"
    assert deep_margin > null_deep_margin + 0.3, \
        f"溝で null を判別的に上回れていない: {deep_margin:.3f} vs {null_deep_margin:.3f}"
    # null は定数ゆえ順序相関が定義できない(Spearman=NaN)→ 実手法の相関が有意。
    # 定数入力の ConstantInputWarning は「相関が定義できない」= まさに beat-null の証拠なので抑制。
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        null_rho = spearmanr(zc, null_ao).correlation
    assert not np.isfinite(null_rho) or abs(null_rho) < 0.1, \
        f"null が高さ順序と相関してしまっている: {null_rho}"
    assert real_rho - (0.0 if not np.isfinite(null_rho) else abs(null_rho)) > 0.7, \
        "実手法の順序相関が null を明確に上回れていない"

    # ── デモ PNG(球+平面の before/after + AO マップ + 溝掃引) ──────────
    eye = np.array([2.6, -3.6, 2.9])
    pose = render3d.look_at(eye, [0.0, 0.0, 0.55], up=(0.0, 0.0, 1.0))
    Kmat = render3d.intrinsics_from_fov(42.0, 340, 260)
    view = render3d.render_mesh(V, F, pose, Kmat, 340, 260)
    normals, sil = view["normals"], view["silhouette"]
    light = (0.35, -0.35, 0.9)
    shade = render_shaded(normals, light=light, ambient=0.28)
    ao_img = ambient_occlusion(V, F, pose=pose, intrinsics=Kmat, width=340,
                               height=260, n_dirs=64, max_dist=2.5 * R)
    before = _mask_background(shade, sil, bg=0.85)
    after = _mask_background(shade * ao_img, sil, bg=0.85)

    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "render_ao.png"
    render_gallery(before, after, _mask_background(ao_img, sil, bg=1.0),
                   (amps, valley_aos, ridge_aos), out_png)

    print(
        f"PASS: 物体空間 AO を実装。平面に載る球で 頂上AO {top_ao:.2f} / 接触部AO {bot_ao:.2f}"
        f"(差 {real_margin:.2f}, 高さとの Spearman {real_rho:.2f})と接触影を再現、"
        f"溝は深さに対し谷AOが {valley_aos[0]:.2f}→{valley_aos[-1]:.2f} と単調に低下(最深部で尾根−谷 {deep_margin:.2f})。"
        f"beat-null: 一様AO=1 は 球マージン {null_margin:.2f}・溝マージン {null_deep_margin:.2f}・順序相関 定義不能"
        f"で凹凸を判別できず、実手法が既知の到達性順序を有意マージンで判別的に再現"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
