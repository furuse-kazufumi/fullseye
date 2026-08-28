# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: HDR レンダを [0,1] へトーンマップして白飛びを階調として残す (HDR tone mapping).

実世界の問題:
    物理ベースの陰影付け(拡散 + 鏡面ハイライト + 環境光)は、鏡面の芯で容易に**値 > 1 の
    放射輝度**を生む。これをディスプレイに出すには [0,1] へ収める必要があり、素朴な方法は
    画素ごとの ``min(x, 1)`` クリップだ。だがクリップは値 > 1 の域を一律 1.0 に潰し、鏡面の
    ハイライト内部の**明暗の順序(階調)を完全に失う**——白い塊にしか見えなくなる。
    トーンマッピングは全域を滑らかに [0,1] へ写す**単調写像**なので、暗部のコントラストを
    保ちつつハイライトの階調も残す。「映える静止 3D」を仕上げる最後の一手。

土台(ラスタライズは再発明しない):
    render3d.render_mesh(V, F) で球メッシュの法線マップ・シルエットを得(z-buffer ラスタライザ)、
    その法線から Phong 風の HDR 陰影(ambient + 拡散 + 強い鏡面)を合成する。鏡面係数を大きく
    とるので芯の放射輝度は ~5 に達し、値 > 1 のハイライト域が生まれる。

実装(render_tonemap の 2 op):
    - tonemap_reinhard(hdr, exposure) : x/(1+x)。[0,∞)→[0,1) の狭義単調写像(クリップしない)。
    - tonemap_aces(hdr, exposure)     : ACES filmic 近似。フィルム的 S 字で見栄えを出す。

検証(GT、グレースケール HDR で厳密に):
    1) 値域   : どちらの出力も [0,1] に収まる。
    2) 単調性 : 入力と出力の Spearman 順位相関 = 1(階調の順序を全域で保存)。
    3) 圧縮   : 入力にはハイライト(max > 1)が在り、出力の max <= 1(ダイナミックレンジ圧縮)。
    4) ハイライト保存: 素朴クリップが潰す域(hdr > 1)でも、トーンマップは順位相関 ≈ 1 を保つ。

beat-the-null(下駄を履かせない基準):
    null = 素朴クリップ min(x,1)。ハイライト域(hdr > 1)では全画素が 1.0 に潰れ、
      **分散 ≈ 0・相異なる値は 1 種類だけ**=階調の順序情報が消える。
    実手法(トーンマップ)は同じ域で**順位相関 ≈ 1**を保ち、数千段の順序関係を残す。
    実手法が null を判別的に上回ること(クリップ分散 ≈ 0 かつトーンマップ順位相関 > 0.999)を assert。

デモ描画:
    同じ球の**カラー HDR** レンダを [クリップ(before, 白飛び)/ Reinhard(after)/ ACES(after)] で
    並置し、鏡面の芯を通る走査線プロファイルを重ねる。クリップは芯で 1.0 に頭打ち(plateau=情報喪失)、
    トーンマップは芯の起伏(階調)を [0,1] 内に残すことが一目で分かる。PNG を _gallery に保存。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

# このファイル名(examples_3d/render_tonemap.py)はルートのモジュール render_tonemap.py と
# 同名なので、リポジトリルートを sys.path の**先頭**に置き、`import render_tonemap` が
# 例自身でなくルートのモジュールへ解決されるようにする(import 循環回避)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from render_tonemap import tonemap_aces, tonemap_reinhard  # noqa: E402
from render3d import render_mesh  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# GT を持つジオメトリ(球)と HDR 陰影の合成
# ═══════════════════════════════════════════════════════════════════════════
def icosphere(radius: float = 1.0, subdiv: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """原点中心・半径 radius の球メッシュ(icosahedron を subdiv 回細分し球面へ射影)。"""
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
            idx = len(vl) - 1
            cache[key] = idx
            return idx

        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        verts = np.asarray(vl, dtype=np.float64)
        faces = np.asarray(new_faces, dtype=np.int64)
    return verts * float(radius), faces


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v), 1e-12)


def shade_hdr(normals: np.ndarray, sil: np.ndarray, *,
              light=(0.5, 0.65, 0.9), ambient=0.08, kd=0.9,
              ks=4.5, shininess=48.0,
              albedo=(1.0, 1.0, 1.0), light_color=(1.0, 1.0, 1.0),
              bg_top=(0.02, 0.03, 0.06), bg_bot=(0.0, 0.0, 0.0)) -> np.ndarray:
    """法線マップ(H,W,3)+ シルエットから Phong 風の **HDR** 陰影を合成。→ (H,W,3) float64 >=0。

    view = +Z(カメラ向き)。鏡面 ``ks`` を大きく取るので芯の放射輝度が > 1 に達し、
    値 > 1 のハイライト域(素朴クリップが潰す域)が生まれる。背景は暗い縦グラデ(< 1)。
    ``albedo``/``light_color`` をグレーにすればグレースケール相当(全チャンネル同一)。
    """
    h, w, _ = normals.shape
    N = normals.copy()
    L = np.asarray(_unit(np.asarray(light, float)))
    V = np.array([0.0, 0.0, 1.0])                 # カメラは -Z を見る → 手前向き=+Z
    Hh = _unit(L + V)                              # ハーフベクトル(Blinn-Phong)

    ndl = np.clip(np.einsum("ijk,k->ij", N, L), 0.0, 1.0)
    ndh = np.clip(np.einsum("ijk,k->ij", N, Hh), 0.0, 1.0)
    spec = ndh ** float(shininess)

    alb = np.asarray(albedo, float).reshape(1, 1, 3)
    lc = np.asarray(light_color, float).reshape(1, 1, 3)
    diffuse = alb * (ambient + kd * ndl[..., None])
    specular = ks * spec[..., None] * lc
    fg = diffuse + specular                        # 前景 HDR(芯で > 1)

    # 背景: 暗い縦グラデ(映え用、全域 < 1 なのでハイライト域を汚さない)
    tv = np.linspace(0.0, 1.0, h)[:, None, None]
    bg = (np.asarray(bg_top, float).reshape(1, 1, 3) * (1 - tv)
          + np.asarray(bg_bot, float).reshape(1, 1, 3) * tv)
    bg = np.broadcast_to(bg, (h, w, 3))

    mask = (sil > 0)[..., None]
    hdr = np.where(mask, fg, bg)
    return np.maximum(hdr, 0.0)                    # 放射輝度は非負


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


def render_gallery(clip_rgb, reinhard_rgb, aces_rgb,
                   scan_hdr, scan_clip, scan_reinhard, scan_aces,
                   metrics, out_path: Path) -> bool:
    """クリップ(before)/ Reinhard / ACES(after)の 3 枚 + 走査線プロファイルを 1 枚に描く。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
        from matplotlib.gridspec import GridSpec
    except Exception as exc:
        print(f"[note] matplotlib が無いため PNG をスキップ: {exc}")
        return False

    jp = _use_jp_font(fm, plt)
    if jp:
        t_title = "render_tonemap: HDR→LDR トーンマップで白飛びを階調として残す(GT=球の鏡面ハイライト)"
        t_clip = "before: 素朴クリップ min(x,1)\n鏡面の芯が真っ白に潰れる(白飛び)"
        t_rein = "after: Reinhard  x/(1+x)\n芯の階調が残り立体感が出る"
        t_aces = "after: ACES filmic\nフィルム的 S 字で見栄え"
        t_scan_title = "鏡面の芯を通る走査線: クリップは 1.0 で頭打ち(情報喪失)/ トーンマップは起伏を保つ"
        t_xlabel = "走査線に沿った画素"
        t_ylabel_l = "表示値 [0,1]"
        t_ylabel_r = "HDR 放射輝度"
        lb_hdr = "HDR 入力(右軸, >1 あり)"
        lb_clip = "クリップ(頭打ち=階調喪失)"
        lb_rein = "Reinhard(階調保存)"
        lb_aces = "ACES(階調保存)"
    else:
        t_title = "render_tonemap: HDR->LDR tone mapping keeps highlight gradation (GT=specular sphere)"
        t_clip = "before: naive clip min(x,1)\nspecular core blows out to white"
        t_rein = "after: Reinhard  x/(1+x)\ncore gradation retained"
        t_aces = "after: ACES filmic\nfilmic S-curve look"
        t_scan_title = "scanline through specular core: clip flat-tops at 1.0 (lost) / tone maps keep the bump"
        t_xlabel = "pixel along scanline"
        t_ylabel_l = "display value [0,1]"
        t_ylabel_r = "HDR radiance"
        lb_hdr = "HDR input (right axis, >1)"
        lb_clip = "clip (flat-top = lost)"
        lb_rein = "Reinhard (retained)"
        lb_aces = "ACES (retained)"

    fig = plt.figure(figsize=(15.5, 8.6))
    fig.suptitle(t_title, fontsize=13, fontweight="bold")
    gs = GridSpec(2, 3, height_ratios=[1.35, 1.0], hspace=0.22, wspace=0.06,
                  left=0.045, right=0.985, top=0.9, bottom=0.09)

    for col, (img, title) in enumerate((
        (clip_rgb, t_clip), (reinhard_rgb, t_rein), (aces_rgb, t_aces))):
        ax = fig.add_subplot(gs[0, col])
        ax.imshow(np.clip(img, 0.0, 1.0), interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])

    ax = fig.add_subplot(gs[1, :])
    x = np.arange(scan_hdr.size)
    axr = ax.twinx()
    axr.plot(x, scan_hdr, color="0.55", lw=1.2, ls="--", label=lb_hdr, zorder=1)
    axr.axhline(1.0, color="0.75", lw=0.8, ls=":")
    ax.plot(x, scan_clip, color="#d95f0e", lw=2.0, label=lb_clip, zorder=3)
    ax.plot(x, scan_reinhard, color="#2c7fb8", lw=2.0, label=lb_rein, zorder=4)
    ax.plot(x, scan_aces, color="#31a354", lw=1.8, ls="-.", label=lb_aces, zorder=4)
    ax.set_title(t_scan_title, fontsize=10)
    ax.set_xlabel(t_xlabel, fontsize=9)
    ax.set_ylabel(t_ylabel_l, fontsize=9)
    axr.set_ylabel(t_ylabel_r, fontsize=9)
    ax.set_ylim(0.0, 1.06)
    axr.set_ylim(0.0, max(1.1, float(scan_hdr.max()) * 1.05))
    lines_l, labels_l = ax.get_legend_handles_labels()
    lines_r, labels_r = axr.get_legend_handles_labels()
    ax.legend(lines_r + lines_l, labels_r + labels_l, fontsize=8.5,
              loc="upper right", framealpha=0.9)

    # beat-null の数値を図中に注記
    txt = metrics
    ax.text(0.012, 0.955, txt, transform=ax.transAxes, fontsize=8.4,
            va="top", ha="left",
            bbox=dict(boxstyle="round", fc="white", ec="0.6", alpha=0.9))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec.709 輝度 (H,W,3)->(H,W)。"""
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    W = H = 384
    V, F = icosphere(radius=1.0, subdiv=4)
    view = render_mesh(V, F, width=W, height=H)
    normals = view["normals"]        # (H,W,3) camera-space, toward camera; 0 outside
    sil = view["silhouette"]         # (H,W) binary

    # --- 入力健全性チェック(退化描画で偽の成功を出さない) ---
    if normals.shape != (H, W, 3):
        raise ValueError(f"normals 形状不正: {normals.shape}")
    n_fg = int(np.count_nonzero(sil > 0))
    if n_fg < 0.05 * W * H:
        raise ValueError(f"シルエット面積が小さすぎる({n_fg}px)。カメラ枠を確認")

    # ── グレースケール HDR(GT/beat-null を曖昧さ無く測る) ──────────────
    gray = shade_hdr(normals, sil, albedo=(1, 1, 1), light_color=(1, 1, 1))
    hdr_g = gray[..., 0]              # 全チャンネル同一 → スカラー輝度
    if not np.all(np.isfinite(hdr_g)):
        raise ValueError("HDR に非有限値")

    hi_mask = hdr_g > 1.0            # 素朴クリップが潰す域(ハイライト)
    n_hi = int(np.count_nonzero(hi_mask))
    hdr_max = float(hdr_g.max())
    print(f"[GT] 球の HDR グレー: 前景 {n_fg}px, ハイライト(>1) {n_hi}px, "
          f"max={hdr_max:.3f}, min={hdr_g.min():.3f}")
    if n_hi < 50:
        raise ValueError(f"ハイライト域が小さすぎ({n_hi}px)。鏡面係数を確認")
    if hdr_max <= 1.0:
        raise ValueError("HDR にハイライト(>1)が無い — beat-null が成立しない")

    # ── 実手法(2 op)と null(素朴クリップ) ──────────────────────────
    rein_g = tonemap_reinhard(hdr_g, exposure=1.0)      # white=None → 全域単調
    aces_g = tonemap_aces(hdr_g, exposure=1.0)
    clip_g = np.clip(hdr_g, 0.0, 1.0)                    # null ベースライン

    # ── GT 1: 値域 [0,1] ────────────────────────────────────────────
    for name, img in (("reinhard", rein_g), ("aces", aces_g)):
        if img.min() < -1e-12 or img.max() > 1.0 + 1e-9:
            raise ValueError(f"{name} 出力が [0,1] 外: [{img.min()}, {img.max()}]")

    # ── GT 2: 全域単調(Spearman 順位相関 = 1) ──────────────────────
    rho_rein = float(spearmanr(hdr_g.ravel(), rein_g.ravel()).statistic)
    rho_aces = float(spearmanr(hdr_g.ravel(), aces_g.ravel()).statistic)

    # ── GT 3: ダイナミックレンジ圧縮 ────────────────────────────────
    rein_max = float(rein_g.max())
    aces_max = float(aces_g.max())

    # ── GT 4 / beat-null: ハイライト域の階調保存 ────────────────────
    hi_hdr = hdr_g[hi_mask]
    hi_rein = rein_g[hi_mask]
    hi_aces = aces_g[hi_mask]
    hi_clip = clip_g[hi_mask]

    clip_var = float(np.var(hi_clip))                   # null: ≈ 0(全部 1.0)
    clip_uniq = int(np.unique(np.round(hi_clip, 9)).size)
    rho_hi_rein = float(spearmanr(hi_hdr, hi_rein).statistic)   # real: ≈ 1
    rho_hi_aces = float(spearmanr(hi_hdr, hi_aces).statistic)
    rein_uniq = int(np.unique(np.round(hi_rein, 9)).size)

    print(f"[measure] 全域 Spearman: Reinhard={rho_rein:.6f}, ACES={rho_aces:.6f}")
    print(f"[measure] 出力 max: Reinhard={rein_max:.4f}, ACES={aces_max:.4f} "
          f"(入力 max={hdr_max:.3f} → 圧縮)")
    print(f"[measure] ハイライト域: Reinhard 順位相関={rho_hi_rein:.6f} "
          f"(相異なる値 {rein_uniq} 種), ACES={rho_hi_aces:.6f}")
    print(f"[null] クリップのハイライト域: 分散={clip_var:.3e}, "
          f"相異なる値 {clip_uniq} 種(全部 1.0 に潰れる)")

    # ── GT アサーション ─────────────────────────────────────────────
    assert rho_rein > 0.99999, f"Reinhard が全域単調でない: rho={rho_rein}"
    assert rho_aces > 0.99999, f"ACES が全域単調でない: rho={rho_aces}"
    assert rein_max <= 1.0 + 1e-9 and rein_max < hdr_max, \
        f"Reinhard がレンジ圧縮していない: {rein_max} vs 入力 {hdr_max}"
    assert aces_max <= 1.0 + 1e-9 and aces_max < hdr_max, \
        f"ACES がレンジ圧縮していない: {aces_max} vs 入力 {hdr_max}"
    assert rho_hi_rein > 0.999, f"Reinhard がハイライト階調を保存していない: {rho_hi_rein}"
    assert rho_hi_aces > 0.999, f"ACES がハイライト階調を保存していない: {rho_hi_aces}"

    # ── beat-null アサーション(素朴クリップを判別的に上回る) ────────
    # null は同じハイライト域で分散 ≈ 0・値 1 種(順序情報ゼロ)、実手法は順位相関 ≈ 1・数千種。
    assert clip_var < 1e-12, f"クリップ null の分散が 0 でなく基準にならない: {clip_var:.3e}"
    assert clip_uniq == 1, f"クリップ null が階調を潰しきっていない: {clip_uniq} 種"
    assert rein_uniq > 100, f"実手法がハイライト域で階調を残せていない: {rein_uniq} 種"
    assert rho_hi_rein - 0.0 > 0.999, "実手法の順位相関が null(=0)を上回れていない"

    # ── デモ用カラー HDR + 走査線プロファイル ──────────────────────
    color = shade_hdr(normals, sil, albedo=(0.95, 0.72, 0.55),
                      light_color=(1.0, 0.96, 0.9))
    clip_rgb = np.clip(color, 0.0, 1.0)
    rein_rgb = tonemap_reinhard(color, exposure=1.0)
    aces_rgb = tonemap_aces(color, exposure=1.0)

    # 鏡面の芯を通る走査線(グレー HDR の最大画素の行)
    r0, _c0 = np.unravel_index(int(np.argmax(hdr_g)), hdr_g.shape)
    scan_hdr = hdr_g[r0]
    scan_clip = clip_g[r0]
    scan_rein = rein_g[r0]
    scan_aces = aces_g[r0]

    metrics = (
        f"beat-null (highlight >1):\n"
        f" clip  var={clip_var:.1e}, {clip_uniq} level\n"
        f" Reinhard rho={rho_hi_rein:.4f}, {rein_uniq} levels\n"
        f" ACES     rho={rho_hi_aces:.4f}"
    )
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "render_tonemap.png"
    render_gallery(clip_rgb, rein_rgb, aces_rgb,
                   scan_hdr, scan_clip, scan_rein, scan_aces, metrics, out_png)

    print(
        f"PASS: 球の鏡面 HDR(max={hdr_max:.2f}, ハイライト {n_hi}px)を Reinhard/ACES で "
        f"[0,1] へ圧縮(出力 max {rein_max:.3f}/{aces_max:.3f})、全域 Spearman "
        f"{rho_rein:.5f}/{rho_aces:.5f} で単調性を保持。beat-null: 素朴クリップは "
        f"ハイライト域を分散 {clip_var:.1e}・{clip_uniq} 段に潰す(階調喪失)のに対し、"
        f"Reinhard は同域で順位相関 {rho_hi_rein:.4f}・{rein_uniq} 段の階調を保存し判別的に上回る"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
