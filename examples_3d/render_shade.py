# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 法線マップに鏡面反射を足す静止 3D シェーディング (Phong / MatCap).

実世界の問題:
    既存のシェーダは拡散(Lambertian)だけで、``N·L`` に比例した滑らかな明暗しか作れない。
    金属・プラスチック・濡れた面の「テカリ(鏡面ハイライト)」が出せず、静止画で 3D が
    ぺたっと見える。ハイライトは素材感と立体感を一目で伝えるので、映える静止 3D には
    鏡面項が要る。

原理(すべて法線マップ (H,W,3) を入力):
    - phong_shade  : I = ambient + diffuse·max(N·L,0) + specular·max(R·V,0)^shininess。
                     R = 2(N·L)N − L(光源を法線で鏡面反射した理想反射方向)。ハイライトの
                     ピークは拡散最大(N=L)ではなく **半角方向** N = normalize(L+V) に立つ。
    - matcap_shade : 視空間法線 (nx,ny) を lit-sphere テクスチャ座標に写して双線形で引く。
                     ライト計算ゼロで素材の見えを任意形状に転写。

検証(GT, 解析的な滑らか球の法線マップで):
    - Phong 鏡面ハイライトの **ピーク画素** が、反射幾何から解析的に予測した画素
      (法線が半角方向 N=normalize(L+V) になる球面点の射影)と一致する。かつその画素で
      R·V ≈ 1(理想反射方向が視線に揃う)。← 予測は幾何のみ・測定は陰影のみ由来で非自明。
    - matcap は「線形ランプのテクスチャ」を法線→uv→双線形で引くと、a+b·u+c·v を各画素で
      **ほぼ厳密に**(双線形は線形関数を誤差なく再現)復元する。→ 座標写像と補間が正しい。

beat-the-null(素朴基準を判別的に上回る):
    - Lambertian(拡散のみ, 既存 render_lambertian)の最も明るい点は N=L にあり、真の反射方向
      N=normalize(L+V) から大きくずれる。「Lambertian の最輝点をハイライトとみなす」null は
      ハイライト位置を数十 px 外す。Phong は数 px 以内で当てる(位置誤差を桁で縮小)。
    - Phong の鏡面ローブは拡散の falloff より遥かに鋭い(明部面積が桁で小さい)。
    - 平坦法線(全画素 N=(0,0,1))を入れると鏡面像は空間変化ゼロ(ハイライトが立たない)=
      形状が無ければ効果も出ない(自明入力が効果を生まないことを確認)。
    - matcap の null は「法線を無視して平均色で塗った円盤」。GT ランプの再現誤差は
      実手法≈0 に対し null は大(形状情報を捨てているため)。

デモ描画(before/after を 1 枚に):
    上段 = Phong: Lambertian(before, ハイライト無し) vs Phong(after, 鋭いハイライト+
    解析反射方向マーカ) + 位置誤差の棒 + 実メッシュ(render3d)への適用。
    下段 = MatCap: 素材テクスチャ / 平均色の円盤(null, before) / matcap 転写(after) + 再現誤差の棒。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# このファイル名(examples_3d/render_shade.py)はルートのモジュール render_shade.py と同名。
# ルートを sys.path の先頭に置き、`import render_shade` が例自身でなくルートに解決されるように。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from render_shade import phong_shade, matcap_shade  # noqa: E402
from photometric import render_lambertian            # noqa: E402  (既存の拡散シェーダ=null)
import render3d                                       # noqa: E402  (実メッシュのラスタライズ土台)


# ═══════════════════════════════════════════════════════════════════════════
# GT を持つ入力の合成
# ═══════════════════════════════════════════════════════════════════════════
def sphere_normal_map(size: int = 400, radius_frac: float = 0.85):
    """正射影の滑らか球の法線マップを解析的に生成。→ (normals (H,W,3), mask, (cx,cy,r_px))。

    画素 (row,col) の中心からのずれ (dx,dy) を球半径 r_px で割り、nx=dx, ny=−dy(画面 y は
    下向き→世界 y は上向き)、nz=sqrt(1−nx²−ny²)。球外は長さ 0(背景)。正射影ゆえ各画素の
    法線が球面点の方向そのもので、狙った法線方向の射影画素を解析的に予測でき GT が厳密になる。
    """
    H = W = int(size)
    cx = (W - 1) / 2.0
    cy = (H - 1) / 2.0
    r_px = radius_frac * (min(H, W) / 2.0)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    dx = (xs - cx) / r_px
    dy = (ys - cy) / r_px
    nx = dx
    ny = -dy
    rho2 = nx * nx + ny * ny
    mask = rho2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - rho2, 0.0, None))
    normals = np.zeros((H, W, 3), np.float64)
    normals[..., 0] = np.where(mask, nx, 0.0)
    normals[..., 1] = np.where(mask, ny, 0.0)
    normals[..., 2] = np.where(mask, nz, 0.0)
    return normals, mask, (cx, cy, r_px)


def uv_sphere(radius: float = 1.0, n_lat: int = 48, n_lon: int = 96):
    """緯度経度グリッドの球メッシュ (V, F)。render3d.render_mesh の実入力(faceted)用。"""
    lat = np.linspace(0.0, np.pi, n_lat)
    lon = np.linspace(0.0, 2.0 * np.pi, n_lon, endpoint=False)
    th, ph = np.meshgrid(lat, lon, indexing="ij")
    x = radius * np.sin(th) * np.cos(ph)
    y = radius * np.cos(th)                       # 極は ±Y(上下)
    z = radius * np.sin(th) * np.sin(ph)
    V = np.column_stack([x.ravel(), y.ravel(), z.ravel()])

    def vid(i, j):
        return i * n_lon + (j % n_lon)

    faces = []
    for i in range(n_lat - 1):
        for j in range(n_lon):
            a, b, c, d = vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)
            faces.append([a, b, c])
            faces.append([a, c, d])
    return V, np.asarray(faces, np.int64)


def linear_ramp_matcap(mh: int = 256, mw: int = 256, a=0.15, b=0.6, c=0.5):
    """線形ランプのグレースケール matcap: tex[j,i] = a + b·(i/(mw−1)) + c·(j/(mh−1))。

    双線形補間は線形関数を誤差なく再現するので、これを matcap_shade に通すと各画素で
    a + b·(nx+1)/2 + c·(1−ny)/2 を厳密に復元できる(座標写像+補間の正しさの GT)。
    """
    jj, ii = np.mgrid[0:mh, 0:mw].astype(np.float64)
    return a + b * (ii / (mw - 1)) + c * (jj / (mh - 1))


def metal_matcap(mh: int = 512, mw: int = 512):
    """映える金属風のカラー lit-sphere matcap(手続き生成)。→ (mh,mw,3)。"""
    jj, ii = np.mgrid[0:mh, 0:mw].astype(np.float64)
    u = ii / (mw - 1) * 2.0 - 1.0                  # −1(左)..+1(右)
    vy = 1.0 - jj / (mh - 1) * 2.0                 # +1(上)..−1(下)
    rad2 = u * u + vy * vy
    disc = rad2 <= 1.0
    base = 0.22 + 0.34 * np.clip(vy * 0.5 + 0.5, 0.0, 1.0)   # 上ほど明るい地
    dot = np.exp(-(((u + 0.35) ** 2 + (vy - 0.55) ** 2) / (2.0 * 0.11 ** 2)))  # 鏡面点(左上)
    rim = np.clip((rad2 - 0.68) / 0.32, 0.0, 1.0) * 0.45     # 縁のリムライト
    val = base + 0.95 * dot + rim
    color = np.stack([val * 0.74, val * 0.82, val * 1.00], axis=-1)   # 青みのある鋼色
    color[~disc] = 0.06
    return np.clip(color, 0.0, None)


# ═══════════════════════════════════════════════════════════════════════════
# 幾何ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def _unit(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


def _predicted_px(T, cx, cy, r_px):
    """狙った法線方向 T(前面, Tz>0)の球面点が写る画素 (row, col) を解析予測。"""
    T = _unit(T)
    px = cx + T[0] * r_px
    py = cy - T[1] * r_px
    return np.array([py, px], np.float64)


def _peak_rc(img, mask):
    """前景内の最大値画素 (row, col)。"""
    m = np.where(mask, img, -np.inf)
    r, c = np.unravel_index(int(np.argmax(m)), m.shape)
    return np.array([r, c], np.float64)


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


def render_gallery(panels, out_path: Path) -> bool:
    """Phong(上段)と MatCap(下段)の before/after を 1 枚に描く。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
    except Exception as exc:
        print(f"[note] matplotlib が無いため PNG をスキップ: {exc}")
        return False

    jp = _use_jp_font(fm, plt)
    T = (lambda ja, en: ja if jp else en)

    lamb = panels["lamb"]
    phong = panels["phong"]
    peakH = panels["pred_H_px"]
    peakL = panels["lamb_peak"]
    mesh_phong = panels["mesh_phong"]
    matcap_tex = panels["matcap_tex"]
    null_disc = panels["null_disc"]
    matcap_img = panels["matcap_img"]
    loc_err = panels["loc_err"]      # (real_px, null_px)
    mc_err = panels["mc_err"]        # (real, null)

    fig = plt.figure(figsize=(20.0, 9.6))
    fig.suptitle(
        T("render_shade: 法線マップに鏡面反射を足す(Phong / MatCap)— 拡散だけでは出せないハイライト",
          "render_shade: adding specular to normal maps (Phong / MatCap) — highlights diffuse can't make"),
        fontsize=15, fontweight="bold")

    # --- 上段: Phong ---
    ax = fig.add_subplot(2, 4, 1)
    ax.imshow(lamb, cmap="gray", vmin=0, vmax=1)
    ax.set_title(T("before: Lambertian(拡散のみ)\nテカリ無し・のっぺり",
                   "before: Lambertian (diffuse only)\nno highlight, flat look"), fontsize=10)
    ax.set_axis_off()

    ax = fig.add_subplot(2, 4, 2)
    ax.imshow(phong, cmap="gray", vmin=0, vmax=1)
    ax.plot(peakH[1], peakH[0], "o", mfc="none", mec="#39d0ff", mew=2.0, ms=18,
            label=T("解析反射方向 N=norm(L+V)", "analytic reflection N=norm(L+V)"))
    ax.plot(peakL[1], peakL[0], "x", color="#ff5d5d", mew=2.2, ms=13,
            label=T("拡散最大 N·L", "diffuse max N·L"))
    ax.set_title(T("after: Phong(拡散+鏡面)\n反射方向に鋭いハイライト",
                   "after: Phong (diffuse+specular)\nsharp highlight at reflection dir"), fontsize=10)
    ax.legend(fontsize=7.5, loc="lower center", framealpha=0.85)
    ax.set_axis_off()

    ax = fig.add_subplot(2, 4, 3)
    labels = [T("Phong", "Phong"), T("Lambertian(null)", "Lambertian(null)")]
    vals = [loc_err[0], loc_err[1]]
    bars = ax.bar(labels, vals, color=["#2c7fb8", "#d95f0e"])
    ax.set_ylabel(T("ハイライト位置誤差(px, 小さいほど良)", "highlight loc error (px, lower=better)"),
                  fontsize=9)
    ax.set_title(T("beat-null: 反射方向を当てる精度", "beat-null: hitting the reflection dir"),
                 fontsize=10)
    for rect, val in zip(bars, vals):
        ax.annotate(f"{val:.1f}px", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(vals) * 1.2 + 1)

    ax = fig.add_subplot(2, 4, 4)
    ax.imshow(mesh_phong, cmap="magma", vmin=0, vmax=1)
    ax.set_title(T("Phong を実メッシュへ\n(render3d の法線出力に直適用)",
                   "Phong on a real mesh\n(applied to render3d normals)"), fontsize=10)
    ax.set_axis_off()

    # --- 下段: MatCap ---
    ax = fig.add_subplot(2, 4, 5)
    ax.imshow(np.clip(matcap_tex, 0, 1))
    ax.set_title(T("素材(lit-sphere matcap)\n= 1 枚に焼いた金属の見え",
                   "material (lit-sphere matcap)\n= metal look baked to 1 image"), fontsize=10)
    ax.set_axis_off()

    ax = fig.add_subplot(2, 4, 6)
    ax.imshow(np.clip(null_disc, 0, 1))
    ax.set_title(T("before(null): 平均色の円盤\n法線を無視=立体感ゼロ",
                   "before(null): flat mean-color disc\nignores normals = no depth"), fontsize=10)
    ax.set_axis_off()

    ax = fig.add_subplot(2, 4, 7)
    ax.imshow(np.clip(matcap_img, 0, 1))
    ax.set_title(T("after: matcap 転写\n素材の見えが球に乗る",
                   "after: matcap applied\nmaterial wraps the sphere"), fontsize=10)
    ax.set_axis_off()

    ax = fig.add_subplot(2, 4, 8)
    labels = [T("matcap", "matcap"), T("平均色(null)", "mean color(null)")]
    vals = [mc_err[0], mc_err[1]]
    floor = 1e-6
    disp = [max(v, floor) for v in vals]
    bars = ax.bar(labels, disp, color=["#2c7fb8", "#d95f0e"])
    ax.set_yscale("log")
    ax.set_ylabel(T("ランプ再現の平均誤差(小さいほど良)", "ramp reproduction MAE (lower=better)"),
                  fontsize=9)
    ax.set_title(T("beat-null: 法線→uv→補間の正しさ", "beat-null: normal→uv→interp correctness"),
                 fontsize=10)
    for rect, val in zip(bars, vals):
        ax.annotate(f"{val:.2g}", (rect.get_x() + rect.get_width() / 2, max(val, floor)),
                    ha="center", va="bottom", fontsize=8.5)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=115)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # --- 入力(解析的な滑らか球) ---
    SIZE = 400
    normals, mask, (cx, cy, r_px) = sphere_normal_map(SIZE, radius_frac=0.85)

    # 退化入力チェック(偽の成功を出さない)
    if normals.shape != (SIZE, SIZE, 3):
        raise ValueError(f"normals 形状不正: {normals.shape}")
    if int(mask.sum()) < 1000:
        raise ValueError("球のマスクが小さすぎる(退化入力)")

    V = np.array([0.0, 0.0, 1.0])            # 視点方向(render3d の視点=+Z)
    L = _unit([0.55, 0.40, 0.72])            # 光源方向(前面・右上)
    H = _unit(L + V)                          # 半角方向 = 鏡面ハイライトが立つ法線
    print(f"[GT] L={L.round(3)}, V={V}, 半角 H=norm(L+V)={H.round(3)}")

    KA, KD, KS, SH = 0.08, 0.80, 0.90, 60.0

    # --- 実手法 ---
    phong = phong_shade(normals, view=V, light=L, ambient=KA, diffuse=KD,
                        specular=KS, shininess=SH, clip=True)          # 表示用
    phong_raw = phong_shade(normals, view=V, light=L, ambient=KA, diffuse=KD,
                            specular=KS, shininess=SH, clip=False)     # argmax 用(飽和させない)
    spec_only = phong_shade(normals, view=V, light=L, ambient=0.0, diffuse=0.0,
                            specular=1.0, shininess=SH, clip=False)    # 鏡面ローブ単体

    # --- null(既存の拡散シェーダ) ---
    lamb = render_lambertian(normals, 1.0, L, ambient=0.0).astype(np.float64)  # N·L

    # ═══ GT 1: 鏡面ハイライトのピーク位置 = 解析反射方向 ═══
    pred_H = _predicted_px(H, cx, cy, r_px)          # 幾何のみから予測
    peak_phong = _peak_rc(phong_raw, mask)           # 陰影のみから測定
    dist_real = float(np.linalg.norm(peak_phong - pred_H))

    # ピーク画素の R·V が ≈1(反射方向が視線に揃う)
    pr, pc = int(peak_phong[0]), int(peak_phong[1])
    Np = normals[pr, pc]
    Np = Np / np.linalg.norm(Np)
    Rp = 2.0 * float(Np @ L) * Np - L
    rdv_peak = float(np.clip(Rp @ V, 0.0, 1.0))

    # ═══ GT 2 / null: Lambertian の最輝点は反射方向を外す ═══
    peak_lamb = _peak_rc(lamb, mask)
    pred_L = _predicted_px(L, cx, cy, r_px)
    dist_lamb_at_L = float(np.linalg.norm(peak_lamb - pred_L))     # Lambert 最輝点 = N=L の確認
    dist_null = float(np.linalg.norm(peak_lamb - pred_H))          # それを「ハイライト」とみなす誤差
    peak_sep = float(np.linalg.norm(peak_phong - peak_lamb))

    # ═══ beat-null: 鏡面ローブの鋭さ(明部面積) ═══
    spec_bright = int(((spec_only > 0.5 * spec_only.max()) & mask).sum())
    lamb_bright = int(((lamb > 0.5 * lamb.max()) & mask).sum())
    sharp_ratio = spec_bright / max(lamb_bright, 1)

    # ═══ beat-null: 自明入力(平坦法線)は鏡面像が空間変化しない ═══
    flat = np.zeros_like(normals)
    flat[..., 2] = 1.0
    spec_flat = phong_shade(flat, view=V, light=L, ambient=0.0, diffuse=0.0,
                            specular=1.0, shininess=SH, clip=False)
    flat_std = float(spec_flat.std())
    sphere_spec_std = float(spec_only[mask].std())

    print(f"[measure] Phong ピーク={peak_phong.astype(int)} 予測 H={pred_H.round(1)} "
          f"→ 誤差 {dist_real:.2f}px, R·V={rdv_peak:.4f}")
    print(f"[measure] Lambert ピーク={peak_lamb.astype(int)} 予測 L={pred_L.round(1)} "
          f"→ 誤差 {dist_lamb_at_L:.2f}px")
    print(f"[null] Lambert 最輝点を鏡面とみなす誤差 = {dist_null:.2f}px(ピーク間 {peak_sep:.1f}px 離間)")
    print(f"[measure] 鏡面明部 {spec_bright}px / 拡散明部 {lamb_bright}px "
          f"= 鋭さ比 {sharp_ratio:.4f}")
    print(f"[null] 平坦法線の鏡面像 std={flat_std:.2e}(≈0)vs 球の鏡面像 std={sphere_spec_std:.3f}")

    # ═══ MatCap GT: 線形ランプの厳密再現 ═══
    ramp = linear_ramp_matcap(256, 256, a=0.15, b=0.6, c=0.5)
    mc_out = matcap_shade(normals, ramp)
    u_norm = (normals[..., 0] * 0.5 + 0.5)
    v_norm = (0.5 - normals[..., 1] * 0.5)
    expected = 0.15 + 0.6 * u_norm + 0.5 * v_norm
    err_real = float(np.abs(mc_out[mask] - expected[mask]).mean())
    mean_val = float(expected[mask].mean())
    null_disc_gray = np.where(mask, mean_val, 0.0)                 # 法線無視の平均色
    err_null = float(np.abs(mean_val - expected[mask]).mean())
    print(f"[measure] matcap ランプ再現 MAE(実)={err_real:.2e} / (null=平均色)={err_null:.4f}")

    # ═══ MatCap GT: 単点テクスチャ → 予測画素にハイライト ═══
    dx0, dy0 = 0.35, 0.30
    dot_tex = np.zeros((256, 256), np.float64)
    ui = int(round((dx0 * 0.5 + 0.5) * 255))
    vj = int(round((0.5 - dy0 * 0.5) * 255))
    dot_tex[vj, ui] = 1.0
    from scipy.ndimage import gaussian_filter
    dot_tex = gaussian_filter(dot_tex, 3.0)
    mc_dot = matcap_shade(normals, dot_tex)
    peak_dot = _peak_rc(mc_dot, mask)
    pred_dot = _predicted_px([dx0, dy0, np.sqrt(1 - dx0 ** 2 - dy0 ** 2)], cx, cy, r_px)
    dist_dot = float(np.linalg.norm(peak_dot - pred_dot))
    print(f"[measure] matcap 単点ハイライト ピーク={peak_dot.astype(int)} 予測={pred_dot.round(1)} "
          f"→ 誤差 {dist_dot:.2f}px")

    # ═══ render3d 実メッシュへの適用(faceted な実法線出力を消費) ═══
    Vm, Fm = uv_sphere(1.0, n_lat=48, n_lon=96)
    view = render3d.render_mesh(Vm, Fm, width=260, height=260)
    mesh_n = view["normals"]
    mesh_mask = view["silhouette"] > 0
    mesh_phong = phong_shade(mesh_n, view=V, light=L, ambient=KA, diffuse=KD,
                             specular=KS, shininess=SH, clip=True)
    mesh_spec = phong_shade(mesh_n, view=V, light=L, ambient=0.0, diffuse=0.0,
                            specular=1.0, shininess=SH, clip=False)
    mesh_hi = int(((mesh_spec > 0.5 * mesh_spec.max()) & mesh_mask).sum())
    mesh_frac = mesh_hi / max(int(mesh_mask.sum()), 1)
    print(f"[measure] 実メッシュ: シルエット {int(mesh_mask.sum())}px, "
          f"鏡面明部 {mesh_hi}px(占有 {mesh_frac:.3%})")

    # ── GT アサーション ────────────────────────────────────────────────
    assert dist_real < 4.0, f"Phong ハイライトが反射方向から外れた: {dist_real:.2f}px"
    assert rdv_peak > 0.999, f"ピークで R·V が 1 に届かない: {rdv_peak:.4f}"
    assert dist_lamb_at_L < 4.0, f"Lambert 最輝点が N=L から外れた: {dist_lamb_at_L:.2f}px"
    assert err_real < 1e-6, f"matcap ランプ再現が不正確(線形は厳密のはず): {err_real:.2e}"
    assert dist_dot < 4.0, f"matcap 単点ハイライトが予測から外れた: {dist_dot:.2f}px"

    # ── beat-null アサーション(素朴基準を判別的に上回る) ──────────────
    # (1) Lambert 最輝点を鏡面とみなす null は反射方向を大きく外す。Phong は桁で精確。
    assert dist_null > 40.0, f"null(Lambert 最輝点)の誤差が小さすぎ基準にならない: {dist_null:.1f}px"
    assert dist_real < dist_null / 10.0, \
        f"Phong が null を桁で上回れていない: {dist_real:.2f}px vs {dist_null:.1f}px"
    assert peak_sep > 30.0, f"Phong と Lambert のピークが離れていない: {peak_sep:.1f}px"
    # (2) 鏡面ローブは拡散 falloff より遥かに鋭い(明部面積が桁で小)。
    assert sharp_ratio < 0.15, f"鏡面ローブが拡散より鋭くない: 面積比 {sharp_ratio:.3f}"
    # (3) 自明入力(平坦法線)は鏡面像が空間変化しない=ハイライトが立たない。
    assert flat_std < 1e-9, f"平坦法線で鏡面像が変化してしまった: std={flat_std:.2e}"
    assert sphere_spec_std > 1e-2, f"球の鏡面像に変化が無い(実装破綻?): std={sphere_spec_std:.3f}"
    # (4) matcap は形状を復元、平均色 null は復元できない(誤差が桁で違う)。
    assert err_null > 0.05, f"matcap null が易しすぎ基準にならない: {err_null:.4f}"
    assert err_real < err_null / 100.0, \
        f"matcap が平均色 null を桁で上回れていない: {err_real:.2e} vs {err_null:.4f}"
    # (5) 実メッシュ(render3d)でハイライトが局所的に立つ。
    assert mesh_spec.max() > 0.5, f"実メッシュで鏡面ハイライトが立たない: max={mesh_spec.max():.3f}"
    assert 0.0 < mesh_frac < 0.30, f"実メッシュの鏡面明部が局所でない: 占有 {mesh_frac:.3%}"

    # ── デモ PNG ───────────────────────────────────────────────────────
    matcap_tex = metal_matcap(512, 512)
    matcap_img = matcap_shade(normals, matcap_tex)
    null_disc_color = np.zeros_like(matcap_img)
    mean_color = matcap_img[mask].mean(axis=0)
    null_disc_color[mask] = mean_color
    panels = {
        "lamb": np.clip(lamb, 0, 1),
        "phong": phong,
        "pred_H_px": pred_H,
        "lamb_peak": peak_lamb,
        "mesh_phong": mesh_phong,
        "matcap_tex": matcap_tex,
        "null_disc": null_disc_color,
        "matcap_img": matcap_img,
        "loc_err": (dist_real, dist_null),
        "mc_err": (err_real, err_null),
    }
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "render_shade.png"
    render_gallery(panels, out_png)

    print(
        f"PASS: Phong 鏡面ハイライトのピークが解析反射方向 N=norm(L+V) と誤差 {dist_real:.2f}px で一致"
        f"(ピークで R·V={rdv_peak:.3f})。"
        f"beat-null: 拡散のみ(Lambertian)の最輝点は反射方向を {dist_null:.0f}px 外し、Phong は {dist_real:.1f}px"
        f"(約 {dist_null/max(dist_real,1e-9):.0f} 倍精確・ピーク間 {peak_sep:.0f}px 離間)。"
        f"鏡面ローブは拡散より鋭く明部面積比 {sharp_ratio:.3f}、平坦法線ではハイライト非生成(std {flat_std:.0e})。"
        f"matcap は線形ランプを MAE {err_real:.0e} で厳密再現(平均色 null は {err_null:.3f}=約"
        f"{err_null/max(err_real,1e-12):.0e} 倍の誤差)、単点は予測画素へ {dist_dot:.1f}px。"
        f"render3d 実メッシュにも直適用しハイライト占有 {mesh_frac:.2%}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
