# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: スーパーサンプリング(SSAA)でメッシュのエッジのジャギーを消す (render_ssaa).

実世界の問題:
    ``render3d.render_mesh`` は正直な z-buffer ラスタライザで、画素は「中心が三角形に入るか」
    の二値被覆しか持たない(ドキュメント通り *アンチエイリアスなし*)。斜めのシルエット境界は
    階段状のジャギーになり、ロボット把持のテンプレートや資料・記事に載せる「映える静止 3D」
    としては見栄えが悪い。SSAA は目標の ``ss`` 倍でレンダリングして面積平均で縮小するだけで、
    境界画素に被覆率(0〜1)の中間輝度を与え、階段を滑らかな勾配へ変える。

原理(すべて numpy + scipy):
    - antialias(hi, ss)          : 高解像画像を ss×ss ブロックの面積平均で縮小(box/gauss)。
    - supersample_mesh(V,F,...ss) : render_mesh を ss 倍で呼び陰影 → antialias で目標へ縮小。
    - edge_alias_energy(img)      : エッジのエイリアス量 = ラプラシアン RMS(小さいほど滑らか)。

検証(GT — 数値でアサート):
    1) antialias の正確さ: 既知のブロック平均(独立に reshape+mean で計算した参照)と、
       解析的な被覆率(半平面が占める既知の割合)へ機械精度で一致する。
    2) 陰影・縮小の忠実さ: 画面を埋める平面(法線 = +Z, 一定光源)を描くと、SSAA 出力は
       解析値 c = ambient + (1-ambient)·(n·L) の **一様画像**になる(ss に依らず std≈0,
       平均 = c)。エッジが無い所で SSAA が値を歪めないことを実レンダリングで示す。

beat-the-null(下駄を履かせない基準):
    無処理(ss=1)= render_mesh 生のエイリアス画像。SSAA(ss=4)がこれを判別的に上回る:
      - エッジのエイリアスエネルギー(ラプラシアン RMS)が有意に **減少**する。
      - 境界の **中間輝度画素**(被覆 0<α<1)が有意に **増加**する(ss=1 はほぼ皆無)。
      - ss を 1→2→3→4→6 と上げるとエイリアスエネルギーが **単調減少**する。
    いずれも実測してアサートする。

デモ描画:
    傾けた四角形(Z 軸まわりに回転 → 斜めのシルエットでジャギー最大化)を ss=1 と ss=4 で
    描き、フル画像とエッジ拡大(nearest 表示で実画素)を上下に並置。右列に ss スイープの
    エイリアスエネルギー曲線と、中間輝度画素率の棒グラフを添えて before/after を一目化。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/render_ssaa.py はルートの render_ssaa.py と同名。ルートを sys.path 先頭に置き、
# `import render_ssaa` が例自身でなくルートのモジュールへ解決されるようにする。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from render3d import auto_view, intrinsics_from_fov, look_at  # noqa: E402
from render_ssaa import antialias, edge_alias_energy, supersample_mesh  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# シーン合成
# ═══════════════════════════════════════════════════════════════════════════
def rotated_square(angle_deg: float = 22.0, r: float = 1.0):
    """z=0 平面の正方形(±r)を Z 軸まわりに angle_deg 回転 -> (V, F)。

    面内回転なので法線は +Z のまま(正面向き)= 陰影は一様。斜めになったシルエット境界だけが
    エイリアス源になるため、SSAA の効果を純粋に観察できる。巻き順は +Z から見て CCW。
    """
    c = np.array([(-r, -r), (r, -r), (r, r), (-r, r)], np.float64)
    th = np.deg2rad(angle_deg)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]], np.float64)
    xy = c @ R.T
    V = np.column_stack([xy, np.zeros(4)]).astype(np.float64)
    F = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    return V, F


def fullframe_quad(s: float = 10.0):
    """画面を完全に覆う大きな平面(±s, z=0)-> (V, F)。法線 = +Z(正面)。"""
    c = np.array([(-s, -s), (s, -s), (s, s), (-s, s)], np.float64)
    V = np.column_stack([c, np.zeros(4)]).astype(np.float64)
    F = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    return V, F


def midtone_fraction(img, lo: float = 0.2, hi: float = 0.8) -> float:
    """最大輝度で正規化した画像で、中間輝度(lo<val<hi)画素の割合。

    ジャギーのある二値エッジ(ss=1)は輝度が 0 か最大値に張り付き中間がほぼ無い。SSAA は
    境界に被覆率に応じた中間輝度を作るため、この割合が増える(= アンチエイリアスの直接指標)。
    """
    a = np.asarray(img, np.float64)
    m = float(a.max())
    if m <= 0.0:
        return 0.0
    n = a / m
    return float(np.mean((n > lo) & (n < hi)))


# ═══════════════════════════════════════════════════════════════════════════
# デモ描画(matplotlib があれば PNG を保存、無ければ静かにスキップ)
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


def _edge_window(img, win: int = 30):
    """勾配最大の位置を中心にした正方窓 (r0, r1, c0, c1) を返す(エッジ拡大用)。"""
    from scipy.ndimage import sobel

    a = np.asarray(img, np.float64)
    g = np.hypot(sobel(a, axis=0, mode="nearest"), sobel(a, axis=1, mode="nearest"))
    H, W = a.shape
    r, c = np.unravel_index(int(np.argmax(g)), g.shape)
    half = win // 2
    r0 = int(np.clip(r - half, 0, H - win))
    c0 = int(np.clip(c - half, 0, W - win))
    return r0, r0 + win, c0, c0 + win


def render_gallery(img1, img4, ss_list, energies, mids, out_path: Path) -> bool:
    """before(ss=1)/after(ss=4)のフル画像 + エッジ拡大 + ss スイープ + 中間輝度率 を 1 枚に。"""
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
        t_title = ("render_ssaa: スーパーサンプリング(SSAA)で斜めエッジのジャギーを消す "
                   "(左=無処理 ss=1 / 中=SSAA ss=4)")
        t_full1, t_zoom1 = "無処理 (ss=1)\nエイリアスあり", "エッジ拡大: 階段状ジャギー"
        t_full4, t_zoom4 = "SSAA (ss=4)\nアンチエイリアス", "エッジ拡大: 中間輝度で滑らか"
        t_sweep_t = "beat-null①: エイリアスエネルギー\n(ラプラシアン RMS)は ss で単調減少"
        t_sweep_x, t_sweep_y = "スーパーサンプル倍率 ss", "エイリアスエネルギー(小=滑らか)"
        t_mid_t = "beat-null②: 中間輝度画素率\n(被覆 0<α<1)が増加"
        t_mid_y = "中間輝度画素の割合"
        lab1, lab4 = "無処理 ss=1", "SSAA ss=4"
    else:
        t_title = ("render_ssaa: supersampling (SSAA) removes diagonal-edge jaggies "
                   "(left=raw ss=1 / mid=SSAA ss=4)")
        t_full1, t_zoom1 = "raw (ss=1)\naliased", "edge zoom: staircase jaggies"
        t_full4, t_zoom4 = "SSAA (ss=4)\nanti-aliased", "edge zoom: smooth mid-tones"
        t_sweep_t = "beat-null #1: alias energy\n(Laplacian RMS) drops with ss"
        t_sweep_x, t_sweep_y = "supersample factor ss", "alias energy (low=smooth)"
        t_mid_t = "beat-null #2: mid-tone pixel\nfraction (coverage 0<a<1) rises"
        t_mid_y = "mid-tone pixel fraction"
        lab1, lab4 = "raw ss=1", "SSAA ss=4"

    r0, r1, c0, c1 = _edge_window(img1, win=30)
    fig = plt.figure(figsize=(15.5, 8.2))
    fig.suptitle(t_title, fontsize=13, fontweight="bold")
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.15],
                          hspace=0.28, wspace=0.24)

    def _show(ax, im, title, box=None):
        ax.imshow(im, cmap="gray", vmin=0.0, vmax=1.0, interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
        if box is not None:
            import matplotlib.patches as mp
            rr0, rr1, cc0, cc1 = box
            ax.add_patch(mp.Rectangle((cc0 - 0.5, rr0 - 0.5), cc1 - cc0, rr1 - rr0,
                                      fill=False, edgecolor="crimson", linewidth=1.4))

    ax = fig.add_subplot(gs[0, 0]); _show(ax, img1, t_full1, box=(r0, r1, c0, c1))
    ax = fig.add_subplot(gs[0, 1]); _show(ax, img1[r0:r1, c0:c1], t_zoom1)
    ax = fig.add_subplot(gs[1, 0]); _show(ax, img4, t_full4, box=(r0, r1, c0, c1))
    ax = fig.add_subplot(gs[1, 1]); _show(ax, img4[r0:r1, c0:c1], t_zoom4)

    # 右上: ss スイープの単調減少曲線
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(ss_list, energies, "o-", color="#2c7fb8", linewidth=1.8, markersize=6)
    ax.set_title(t_sweep_t, fontsize=10)
    ax.set_xlabel(t_sweep_x, fontsize=9)
    ax.set_ylabel(t_sweep_y, fontsize=9)
    ax.set_xticks(ss_list)
    ax.grid(True, alpha=0.3)
    for x, y in zip(ss_list, energies):
        ax.annotate(f"{y:.4f}", (x, y), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=7.5)

    # 右下: 中間輝度画素率(ss=1 vs ss=4)
    ax = fig.add_subplot(gs[1, 2])
    b = ax.bar([lab1, lab4], [mids[0] * 100, mids[1] * 100],
               color=["#d95f0e", "#2c7fb8"], width=0.55)
    ax.set_title(t_mid_t, fontsize=10)
    ax.set_ylabel(t_mid_y + " [%]", fontsize=9)
    for rect, val in zip(b, mids):
        ax.annotate(f"{val*100:.2f}%", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(mids) * 100 * 1.35 + 0.5)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=125)
    plt.close(fig)
    print(f"[note] デモ PNG を保存: {out_path}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    SIZE = 128

    # ── GT 1: antialias(面積平均)の正確さ ─────────────────────────────
    rng = np.random.default_rng(0)
    hi = rng.random((12, 16))                     # H=12, W=16, ss=4 -> 3x4
    box = antialias(hi, 4, filter="box")
    ref = hi.reshape(3, 4, 4, 4).mean(axis=(1, 3))    # 独立に計算した参照
    if box.shape != (3, 4):
        raise ValueError(f"antialias 形状 {box.shape} != (3,4)")
    aa_err = float(np.max(np.abs(box - ref)))
    # 解析的な被覆率: 1 ブロック(4x4)の左 3 列=1, 右 1 列=0 -> 面積平均 = 3/4
    cov_blk = np.array([[1, 1, 1, 0]] * 4, np.float64)
    cov_val = float(antialias(cov_blk, 4, filter="box")[0, 0])
    print(f"[GT1] antialias 面積平均: reshape-mean との最大差 {aa_err:.2e}, "
          f"半平面被覆 3/4 の復元 {cov_val:.6f}")
    assert aa_err < 1e-12, f"antialias が面積平均と一致しない: {aa_err:.2e}"
    assert abs(cov_val - 0.75) < 1e-12, f"半平面被覆率が 0.75 でない: {cov_val}"

    # ── GT 2: 陰影・縮小の忠実さ(画面を埋める平面 -> 一様な解析値 c) ──
    Vq, Fq = fullframe_quad(s=10.0)
    K = intrinsics_from_fov(45.0, SIZE, SIZE)
    pose_q = look_at(eye=(0.0, 0.0, 3.0), target=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    light = np.array([0.3, 0.2, 1.0], np.float64)      # カメラ空間光源
    ambient = 0.15
    ndl = 1.0 / np.linalg.norm(light)                  # 法線=(0,0,1) なので n.L = Lz/|L|
    c_gt = ambient + (1.0 - ambient) * ndl
    for ss in (1, 4):
        img = supersample_mesh(Vq, Fq, pose_q, K, size=SIZE, ss=ss,
                               light=light, ambient=ambient)
        if img.shape != (SIZE, SIZE):
            raise ValueError(f"supersample_mesh 形状 {img.shape} != {(SIZE, SIZE)}")
        std = float(img.std())
        mean_err = abs(float(img.mean()) - c_gt)
        cov = float(np.mean(img > 0))
        print(f"[GT2] 全面平面 ss={ss}: 被覆率 {cov:.3f}, std {std:.2e}, "
              f"平均 {img.mean():.6f} (解析値 c={c_gt:.6f}, 誤差 {mean_err:.2e})")
        assert cov > 0.999, f"平面が画面を覆っていない(ss={ss}): 被覆率 {cov:.3f}"
        assert std < 1e-9, f"一様なはずの平面が均一でない(ss={ss}): std {std:.2e}"
        assert mean_err < 1e-9, f"陰影/縮小が解析値からずれる(ss={ss}): {mean_err:.2e}"

    # ── AA 本体: 傾けた四角形(斜めシルエット = ジャギー最大) ─────────
    Vs, Fs = rotated_square(angle_deg=22.0, r=1.0)
    if Vs.shape != (4, 3) or Fs.shape != (2, 3):
        raise ValueError("傾き四角形メッシュの形状が不正(退化入力)")
    pose_s, Ks = auto_view(Vs, width=SIZE, height=SIZE)
    axial = (0.0, 0.0, 1.0)                             # 軸光源 -> 表面は一様輝度、エッジのみ変化
    img1 = supersample_mesh(Vs, Fs, pose_s, Ks, size=SIZE, ss=1, light=axial, ambient=0.1)
    img4 = supersample_mesh(Vs, Fs, pose_s, Ks, size=SIZE, ss=4, light=axial, ambient=0.1)

    e1 = edge_alias_energy(img1)
    e4 = edge_alias_energy(img4)
    mid1 = midtone_fraction(img1)
    mid4 = midtone_fraction(img4)
    print(f"[measure] エイリアスエネルギー: ss=1 {e1:.5f} -> ss=4 {e4:.5f} "
          f"(比 {e4/e1:.3f})")
    print(f"[measure] 中間輝度画素率:      ss=1 {mid1*100:.3f}% -> ss=4 {mid4*100:.3f}%")

    # ── beat-null: ss スイープでエイリアスエネルギーが単調減少 ─────────
    ss_list = [1, 2, 3, 4, 6]
    energies = []
    for ss in ss_list:
        im = supersample_mesh(Vs, Fs, pose_s, Ks, size=SIZE, ss=ss,
                              light=axial, ambient=0.1)
        energies.append(edge_alias_energy(im))
    print("[measure] ss スイープ energies: "
          + ", ".join(f"ss={s}:{e:.5f}" for s, e in zip(ss_list, energies)))

    # ── beat-null アサーション ─────────────────────────────────────────
    # ① SSAA はエイリアスエネルギーを判別的に減らす(ss=4 が ss=1 の 0.7 倍未満)
    assert e4 < 0.7 * e1, f"SSAA がエイリアスを十分減らせていない: {e4:.5f} vs {e1:.5f}"
    # ② 中間輝度画素: 無処理はほぼ皆無、SSAA で明確に増える
    assert mid1 < 0.005, f"無処理 null の中間輝度が想定より多い(基準にならない): {mid1:.4f}"
    assert mid4 > 0.005, f"SSAA の中間輝度が少なすぎる: {mid4:.4f}"
    assert mid4 > 4.0 * max(mid1, 1e-6), \
        f"中間輝度の増加が null を明確に上回れていない: {mid4:.4f} vs {mid1:.4f}"
    # ③ ss を上げるとエイリアスエネルギーが単調減少(下駄のない一貫した改善)
    diffs = np.diff(energies)
    assert np.all(diffs < 1e-9), f"ss でエイリアスが単調減少しない: {energies}"
    assert energies[-1] < 0.65 * energies[0], \
        f"ss スイープでの改善が弱い: {energies[-1]:.5f} vs {energies[0]:.5f}"

    # ── fail-closed の確認(退化/不正入力を拒否) ──────────────────────
    for bad in (0, -1, 2.5):
        try:
            antialias(np.zeros((8, 8)), bad)
            raise AssertionError(f"antialias が不正 ss={bad!r} を拒否しなかった")
        except ValueError:
            pass
    try:
        antialias(np.zeros((7, 8)), 4)                 # 7 は 4 で割り切れない
        raise AssertionError("antialias が割り切れないサイズを拒否しなかった")
    except ValueError:
        pass
    try:
        supersample_mesh(Vs, Fs, pose_s, Ks, size=SIZE, ss=0)
        raise AssertionError("supersample_mesh が ss=0 を拒否しなかった")
    except ValueError:
        pass
    print("[fail-closed] 不正 ss / 割り切れないサイズ を正しく拒否")

    # ── デモ PNG ───────────────────────────────────────────────────────
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "render_ssaa.png"
    render_gallery(img1, img4, ss_list, energies, (mid1, mid4), out_png)

    print(
        f"PASS: 傾き22°四角形で SSAA(ss=4)が無処理(ss=1)を判別的に改善。"
        f"エイリアスエネルギー(ラプラシアン RMS)を {e1:.4f}->{e4:.4f}({e4/e1:.2f}倍)へ削減、"
        f"中間輝度画素率を {mid1*100:.2f}%->{mid4*100:.2f}% へ増加、"
        f"ss=1..6 で {energies[0]:.4f}->{energies[-1]:.4f} と単調減少。"
        f"GT: 面積平均は reshape-mean と最大差 {aa_err:.1e}・半平面被覆 {cov_val:.3f}、"
        f"全面平面は解析値 c={c_gt:.4f} を std<1e-9 の一様画像で復元"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
