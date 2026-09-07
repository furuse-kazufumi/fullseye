# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のステレオ写真で測る —— 合成では絶対に出ない 3 つの躓き。

この repo の PoC は**自分で真値を仕込む**規律で書いてあります。合成なら答えが
データの外に無く、崖も対照群も設計できるからです。ただし合成は
**自分が知っている壊れ方しか作れない**。そこでこの 1 本だけは、実写の
ステレオ対(Middlebury 2014 の motorcycle、真値視差つき)を通します。
狙いは「うちの手法は実写でも強い」ではなく、**合成では出ない型の躓きを
3 つ拾うこと**です。

* **真値の穴は NaN だと書いてあるが、実際は +inf** —— 配布元の注記が違う。
  ``np.nanmedian`` は inf を除いてくれないので、中央視差を 42.55 px でなく
  **44.97 px** と答える。
* **既定値が実写の目盛りに届かない** —— ``max_disp=16`` の既定は、真値が
  7.33〜59.91 px あるこの場面で bad2 **95.06 %**。ほぼ全滅。
* ★★**距離に落とすところで形が反り返る** —— ``depth_from_disparity`` に
  主点オフセット ``doffs`` が無かった。実写の校正値(31.086 px)を無視すると
  距離は 1.519〜5.243 倍にばらけ、**単一のスケールでは直らない**。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **配布元の注記より、自分で数えた型を信じる**。真値の穴は NaN が 0 個、
   +inf が 15,927 個(切り出した 240x741 の 9.0 %)。``np.isfinite`` で
   数えれば正しく 42.55 px、``np.nanmedian`` は **44.97 px** を返す。
   nan 系は inf を除かない —— 「欠測は NaN」という思い込みが 2.4 px の
   偏りになる。★一方 ``fill_disparity`` と ``apply_cmap`` は ``isfinite``
   で判定しているので **+inf を正しく穴として扱った**(埋めた後の非有限 0 個、
   既知画素は 1 つも動かない)。同じ repo の中で流儀が分かれていない側は強い。
2. ★**既定値には崖がある**。``max_disp`` を振ると bad2 は 16 -> 95.06 %、
   32 -> 71.47 %、48 -> 46.79 %、64 -> 26.75 %、80 -> 27.11 %。真の最大視差
   59.91 px を**下回る設定はすべて前景を丸ごと失う**ので、崖は 48 と 64 の
   間に立つ —— これは測る前に幾何から言える(探索範囲に無い視差は表現できない)。
   80 で少し悪くなるのは、余分な探索範囲が偽の一致を拾うから。
3. **ゼロ点は 94 %**。定数視差(探索範囲の中央 32 px)で bad2 95.62 %、
   真値の中央値を知っていて定数で置いても 94.04 %。つまり bad2 26.75 % の
   ブロックマッチングは**ゼロ点を 67 ポイント上回っている**。
4. **手法の順位は実写で入れ替わる**(max_disp=64)。SGM 15.81 % <
   NCC 21.47 % < subpixel 26.28 % ≈ SSD 26.39 % ≈ SAD 26.75 % <
   census 48.62 %。★census が最下位なのは実装が悪いのではなく **64 bit に
   詰める都合で窓が 7 で頭打ち**だから —— 3/5/7 で 75.27 / 48.62 / 35.44 % と
   伸び続けている途中で、9x9(80 近傍)は ``ValueError`` で拒否される。
   ブロックマッチングは同じ 64 で 21 まで広げられて 23.59 % まで下がる。
   **「census は弱い」ではなく「この実装では窓を伸ばせない」**。
5. ★★**信頼度は本物**。``disparity_confidence`` の下位を捨てると
   bad2 は 26.75 -> 14.58(2 割捨て)-> **6.80 %**(4 割捨て)-> 4.33 %
   (6 割)-> 2.99 %(8 割)。4 割捨てるだけで誤りが 4 分の 1 になる ——
   密度と正しさは**別々に報告するもの**で、1 つの数字にまとめてはいけない。
6. ★★**距離に落とすところで形が反り返る**。この場面の真の距離は
   2110〜4999 mm(中央 2608 mm)。``doffs`` を無視した ``Z = f*B/d`` は
   3205〜26210 mm(中央 4513 mm)を返す。比は 1.519〜5.243 と**視差に
   よって違う**ので、後から 1 つの係数を掛けても直らない —— 最良の単一
   スケール 0.3733 を掛けてなお残差 **958.3 mm RMS**(奥行きレンジ
   2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm
   引き込まれる。**平面が平面でなくなる**。``doffs=31.086`` を渡せば
   閉形式と完全一致(最大差 0 mm)。この引数はこの PoC で追加した。
7. **実写の視差レンジで塗り分ける**。CIE L* の折返しは jet 3 / turbo 1 /
   viridis 0 / gray 0。隣接段の色差の中央値は jet 0.0157 > turbo 0.0117 >
   gray 0.0068 > viridis 0.0064 —— **jet は「よく分かれて見える」が
   分かれ方が場所によって違う**(最小 0.0129 / 最大 0.0222 で 1.7 倍)。
   turbo は折返し 1 回で済み、``colorize_disparity`` の既定になっている。
8. **uint8 をそのまま渡しても通るが、同じ数字は返らない**。float [0,1] で
   bad2 26.75 %、uint8 で 26.74 % —— 量子化のぶんだけ違う。落ちないので
   気づきにくい。**入力の型は測定条件**。

EXTEND: 自前の撮影に差し替えるなら ``realdata.stereo_pair()`` を
``(左, 右, 真値視差)`` を返す関数に置き換えます。真値が無い場合、2〜5 節は
そのまま(真値の要らない量 = 信頼度・左右整合・被覆率)で回せますが、
6 節の距離は **校正値 focal / baseline / doffs が要ります** ——
``doffs`` を 0 と決め打ちしていいのは、2 台の主点が一致するように直した
場合だけです。

出典: Middlebury 2014 stereo benchmark (motorcycle)、D. Scharstein et al.,
"High-resolution stereo datasets with subpixel-accurate ground truth", GCPR 2014。
研究・教育目的での利用。画像は ``scikit-image`` 同梱の 1/4 縮小版。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import imgio                                                     # noqa: E402
import realdata                                                  # noqa: E402

#: 切り出す行(全体 500 行は測るのに時間がかかるだけで、所見は変わらない)
ROWS = (130, 370)

#: Middlebury が配っているこの場面の校正値(1/4 縮小版に対して有効)
FOCAL_PX = 994.978
BASELINE_MM = 193.001
DOFFS_PX = 31.086

#: bad-N のしきい[px](この分野の慣習は 2.0)
BAD_THR = 2.0


def load():
    """実写のステレオ対を切り出して返す。無ければ fail-closed で落ちる。"""
    L, R, G = realdata.stereo_pair()
    a, b = ROWS
    return L[a:b], R[a:b], G[a:b]


def score(pred, gt, mask=None, thr=BAD_THR):
    """真値のある画素だけで bad-N / RMS / 偏り / 残った割合を返す。"""
    p = np.asarray(pred, np.float64)
    ok = np.isfinite(gt)
    m = ok & np.isfinite(p)
    if mask is not None:
        m = m & mask
    if not m.any():
        return dict(bad=float("nan"), rms=float("nan"), bias=float("nan"), keep=0.0)
    e = p[m] - gt[m]
    return dict(bad=100.0 * (np.abs(e) > thr).mean(),
                rms=float(np.sqrt((e ** 2).mean())),
                bias=float(e.mean()),
                keep=100.0 * m.sum() / ok.sum())


def lightness(rgb):
    """sRGB -> CIE L*(疑似カラーの明度が単調かを見るため)。"""
    a = np.asarray(rgb, np.float64)
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    e = 216.0 / 24389.0
    f = np.where(Y > e, np.cbrt(Y), (24389.0 / 27.0 * Y + 16.0) / 116.0)
    return 116.0 * f - 16.0


# --------------------------------------------------------------------------- #
# 1. 真値の穴は NaN ではなく +inf
# --------------------------------------------------------------------------- #
def section_holes(G):
    n_nan = int(np.isnan(G).sum())
    n_inf = int(np.isposinf(G).sum())
    ok = np.isfinite(G)
    out = dict(n_nan=n_nan, n_inf=n_inf, frac=100.0 * (~ok).mean(),
               med_true=float(np.median(G[ok])), med_nan=float(np.nanmedian(G)),
               lo=float(G[ok].min()), hi=float(G[ok].max()))
    # fill_disparity は isfinite で判定している = +inf を穴として扱えるか
    filled = np.asarray(fs.fill_disparity(G), np.float64)
    out["filled_nonfinite"] = int((~np.isfinite(filled)).sum())
    out["filled_drift"] = float(np.abs(filled[ok] - G[ok]).max())
    # apply_cmap も同じか(穴の色が有限側と衝突しないか)
    rgb = np.asarray(imgio.apply_cmap(G, "turbo"))
    hole_colors = np.unique(rgb[~ok].reshape(-1, 3), axis=0)
    fin_colors = np.unique(rgb[ok].reshape(-1, 3), axis=0)
    out["hole_colors"] = len(hole_colors)
    out["hole_collides"] = bool(
        (hole_colors[:, None, :] == fin_colors[None, :, :]).all(-1).any())
    return out


# --------------------------------------------------------------------------- #
# 2. 既定値の崖
# --------------------------------------------------------------------------- #
def section_cliff(L, R, G):
    rows = []
    for md in (16, 32, 48, 64, 80):
        s = score(fs.disparity_map(L, R, max_disp=md, block=7, method="sad"), G)
        rows.append((md, s["bad"], s["rms"], s["bias"]))
    return rows


# --------------------------------------------------------------------------- #
# 3. ゼロ点
# --------------------------------------------------------------------------- #
def section_null(L, G):
    ok = np.isfinite(G)
    out = {}
    for tag, val in (("探索範囲の中央 (32 px)", 32.0),
                     ("真値の中央値 (オラクル)", float(np.median(G[ok]))),
                     ("視差ゼロ (無限遠)", 0.0)):
        out[tag] = score(np.full_like(L, val), G)
    return out


# --------------------------------------------------------------------------- #
# 4. 手法と窓
# --------------------------------------------------------------------------- #
def section_methods(L, R, G):
    rows = []
    for tag, fn, kw in (
            ("SAD", fs.disparity_map, dict(max_disp=64, block=7, method="sad")),
            ("SSD", fs.disparity_map, dict(max_disp=64, block=7, method="ssd")),
            ("NCC", fs.disparity_map, dict(max_disp=64, block=7, method="ncc")),
            ("census w5", fs.disparity_census, dict(max_disp=64, window=5)),
            ("subpixel", fs.disparity_subpixel,
             dict(max_disp=64, block=7, method="ssd")),
            ("SGM", fs.disparity_sgm, dict(max_disp=64, window=5))):
        t = time.perf_counter()
        s = score(fn(L, R, **kw), G)
        rows.append((tag, s["bad"], s["rms"], time.perf_counter() - t))
    return rows


def section_windows(L, R, G):
    cen, blk = [], []
    for w in (3, 5, 7):
        cen.append((w, score(fs.disparity_census(L, R, max_disp=64, window=w),
                             G)["bad"]))
    # 9x9 は 80 近傍 > 64 bit で拒否される —— これは実装上の天井
    try:
        fs.disparity_census(L, R, max_disp=64, window=9)
        capped = None
    except ValueError as exc:
        capped = str(exc)
    for w in (3, 5, 7, 9, 11, 15, 21):
        blk.append((w, score(fs.disparity_map(L, R, max_disp=64, block=w,
                                              method="sad"), G)["bad"]))
    return cen, capped, blk


# --------------------------------------------------------------------------- #
# 5. 信頼度で切る
# --------------------------------------------------------------------------- #
def section_confidence(L, R, G):
    conf = np.asarray(fs.disparity_confidence(L, R, max_disp=64, block=7,
                                              method="ssd"), np.float64)
    d = np.asarray(fs.disparity_map(L, R, max_disp=64, block=7, method="sad"),
                   np.float64)
    fin = np.isfinite(conf)
    rows = []
    for q in (0.0, 0.2, 0.4, 0.6, 0.8):
        thr = float(np.quantile(conf[fin], q))
        s = score(d, G, mask=conf >= thr)
        rows.append((100.0 * q, thr, s["bad"], s["rms"], s["keep"]))
    return conf, d, rows


# --------------------------------------------------------------------------- #
# 6. 距離に落とす —— doffs
# --------------------------------------------------------------------------- #
def section_depth(G):
    ok = np.isfinite(G)
    d = G[ok]
    z_true = FOCAL_PX * BASELINE_MM / (d + DOFFS_PX)
    z_no = np.asarray(fs.depth_from_disparity(G, focal=FOCAL_PX,
                                              baseline=BASELINE_MM))[ok]
    z_fix = np.asarray(fs.depth_from_disparity(G, focal=FOCAL_PX,
                                               baseline=BASELINE_MM,
                                               doffs=DOFFS_PX))[ok]
    ratio = z_no / z_true
    scale = float((z_no * z_true).sum() / (z_no * z_no).sum())
    resid = scale * z_no - z_true
    far = d < np.quantile(d, 0.1)
    near = d > np.quantile(d, 0.9)
    return dict(
        z_true=(float(z_true.min()), float(z_true.max()), float(np.median(z_true))),
        z_no=(float(z_no.min()), float(z_no.max()), float(np.median(z_no))),
        ratio=(float(ratio.min()), float(ratio.max()), float(np.median(ratio))),
        scale=scale, rms=float(np.sqrt((resid ** 2).mean())),
        span=float(z_true.max() - z_true.min()),
        far=(float(np.median(z_true[far])), float(np.median(resid[far]))),
        near=(float(np.median(z_true[near])), float(np.median(resid[near]))),
        fix_err=float(np.abs(z_fix - z_true).max()))


# --------------------------------------------------------------------------- #
# 7. 実写のレンジで塗る
# --------------------------------------------------------------------------- #
def section_colour(G):
    ok = np.isfinite(G)
    lo, hi = float(G[ok].min()), float(G[ok].max())
    x = np.linspace(lo, hi, 256)[None, :]
    rows = []
    for nm in ("jet", "turbo", "viridis", "gray"):
        rgb = np.asarray(imgio.apply_cmap(x, nm, vmin=lo, vmax=hi))[0]
        Ls = lightness(rgb)
        dl = np.diff(Ls)
        rev = int((np.sign(dl[1:]) != np.sign(dl[:-1])).sum())
        step = np.sqrt((np.diff(rgb, axis=0) ** 2).sum(1))
        rows.append((nm, rev, float(np.median(step)), float(step.min()),
                     float(step.max())))
    return rows


# --------------------------------------------------------------------------- #
# 8. uint8 をそのまま渡す
# --------------------------------------------------------------------------- #
def section_dtype(L, R, G):
    d_f = np.asarray(fs.disparity_map(L, R, max_disp=64, block=7, method="sad"))
    d_u = np.asarray(fs.disparity_map((L * 255).astype(np.uint8),
                                      (R * 255).astype(np.uint8),
                                      max_disp=64, block=7, method="sad"))
    return score(d_f, G), score(d_u, G), bool(np.array_equal(d_f, d_u))


def main() -> None:
    t0 = time.perf_counter()
    L, R, G = load()
    ok = np.isfinite(G)
    print("実写ステレオ(Middlebury 2014 motorcycle、1/4 縮小、行 %d-%d)" % ROWS)
    print("  画像 %s / 真値のある画素 %.1f %%  視差 %.2f 〜 %.2f px(中央 %.2f)"
          % (L.shape, 100 * ok.mean(), G[ok].min(), G[ok].max(),
             np.median(G[ok])))

    # --- 1 ---------------------------------------------------------------- #
    h = section_holes(G)
    print("\n1. 真値の穴は NaN ではなく +inf")
    print("   NaN %d 個 / +inf %d 個(%.1f %%)"
          % (h["n_nan"], h["n_inf"], h["frac"]))
    print("   中央視差: isfinite で %.2f px、np.nanmedian は %.2f px "
          "(%.2f px ずれる)"
          % (h["med_true"], h["med_nan"], h["med_nan"] - h["med_true"]))
    print("   fill_disparity: 埋めた後の非有限 %d 個 / 既知画素のずれ %.3g"
          % (h["filled_nonfinite"], h["filled_drift"]))
    print("   apply_cmap: 穴の色 %d 種、有限側と衝突 %s"
          % (h["hole_colors"], "する" if h["hole_collides"] else "しない"))
    assert h["n_nan"] == 0 and h["n_inf"] > 0, (h["n_nan"], h["n_inf"])
    assert h["med_nan"] > h["med_true"] + 1.0, (h["med_nan"], h["med_true"])
    assert h["filled_nonfinite"] == 0 and h["filled_drift"] == 0.0, h
    assert not h["hole_collides"] and h["hole_colors"] == 1, h

    # --- 2 ---------------------------------------------------------------- #
    cliff = section_cliff(L, R, G)
    print("\n2. 既定値の崖(真の最大視差 %.2f px)" % G[ok].max())
    for md, bad, rms, bias in cliff:
        print("   max_disp=%3d  bad%.0f %6.2f %%  rms %5.2f px  偏り %+5.2f px"
              % (md, BAD_THR, bad, rms, bias))
    by_md = dict((m, b) for m, b, _r, _bi in cliff)
    assert by_md[16] > 90.0, by_md
    assert by_md[64] < 0.7 * by_md[48], by_md      # 48 -> 64 が崖
    assert by_md[80] >= by_md[64], by_md           # 広げすぎは戻らない

    # --- 3 ---------------------------------------------------------------- #
    null = section_null(L, G)
    print("\n3. ゼロ点")
    for tag, s in null.items():
        print("   %-24s bad%.0f %6.2f %%  rms %5.2f px"
              % (tag, BAD_THR, s["bad"], s["rms"]))
    best_null = min(s["bad"] for s in null.values())

    # --- 4 ---------------------------------------------------------------- #
    meth = section_methods(L, R, G)
    print("\n4. 手法(max_disp=64)")
    for tag, bad, rms, sec in meth:
        print("   %-10s bad%.0f %6.2f %%  rms %5.2f px  (%.1f 秒)"
              % (tag, BAD_THR, bad, rms, sec))
    by_m = dict((t, b) for t, b, _r, _s in meth)
    assert by_m["SGM"] < by_m["NCC"] < by_m["SAD"] < by_m["census w5"], by_m
    assert by_m["SGM"] < best_null - 60.0, (by_m["SGM"], best_null)

    cen, capped, blk = section_windows(L, R, G)
    print("   census の窓: " + " / ".join("%d->%.2f %%" % c for c in cen))
    print("   9x9 は拒否される: %s" % capped)
    print("   block の窓: " + " / ".join("%d->%.2f %%" % b for b in blk))
    assert capped is not None and "64 bits" in capped, capped
    assert cen[0][1] > cen[1][1] > cen[2][1], cen   # 伸びている途中で止まる
    assert blk[-1][1] < blk[0][1], blk

    # --- 5 ---------------------------------------------------------------- #
    conf, dmap, gate = section_confidence(L, R, G)
    print("\n5. 信頼度で切る(密度と正しさは別の数字)")
    for q, thr, bad, rms, keep in gate:
        print("   下位 %2.0f %% を捨てる (conf>=%.3f)  bad%.0f %6.2f %%  "
              "rms %5.2f px  残り %5.1f %%" % (q, thr, BAD_THR, bad, rms, keep))
    assert gate[2][2] < 0.4 * gate[0][2], gate      # 4 割捨てで大きく下がる
    assert gate[-1][2] < gate[0][2], gate

    # --- 6 ---------------------------------------------------------------- #
    dep = section_depth(G)
    print("\n6. 距離に落とす —— 主点オフセット doffs=%.3f px" % DOFFS_PX)
    print("   真の距離   %6.0f 〜 %6.0f mm(中央 %.0f)" % dep["z_true"])
    print("   doffs 無し %6.0f 〜 %6.0f mm(中央 %.0f)" % dep["z_no"])
    print("   比 %.3f 〜 %.3f(中央 %.3f)= 視差ごとに違う"
          % dep["ratio"])
    print("   最良の単一スケール %.4f を掛けても残差 %.1f mm RMS"
          "(奥行きレンジ %.0f mm の %.1f %%)"
          % (dep["scale"], dep["rms"], dep["span"],
             100 * dep["rms"] / dep["span"]))
    print("   遠い面 %.0f mm は %+.0f mm 押し出され、近い面 %.0f mm は "
          "%+.0f mm 引き込まれる" % (dep["far"][0], dep["far"][1],
                                     dep["near"][0], dep["near"][1]))
    print("   doffs を渡すと閉形式と最大差 %.3g mm" % dep["fix_err"])
    assert dep["ratio"][0] > 1.4 and dep["ratio"][1] > 4.0, dep["ratio"]
    assert dep["rms"] > 0.2 * dep["span"], dep      # 1 係数では直らない
    assert dep["far"][1] > 0.0 > dep["near"][1], dep  # 符号が反転 = 反り返り
    assert dep["fix_err"] == 0.0, dep["fix_err"]

    # --- 7 ---------------------------------------------------------------- #
    col = section_colour(G)
    print("\n7. 実写の視差レンジで塗る")
    for nm, rev, med, lo, hi in col:
        print("   %-8s L* 折返し %d 回  隣接段の色差 中央 %.4f "
              "(最小 %.4f / 最大 %.4f、比 %.2f)"
              % (nm, rev, med, lo, hi, hi / max(lo, 1e-9)))
    by_c = dict((n, (r, m, lo, hi)) for n, r, m, lo, hi in col)
    assert by_c["jet"][0] > by_c["turbo"][0] > by_c["viridis"][0], by_c
    assert by_c["jet"][3] / by_c["jet"][2] > 1.5, by_c["jet"]

    # --- 8 ---------------------------------------------------------------- #
    s_f, s_u, same = section_dtype(L, R, G)
    print("\n8. uint8 をそのまま渡す")
    print("   float [0,1]  bad%.0f %6.2f %%   uint8  bad%.0f %6.2f %%   "
          "完全一致 %s" % (BAD_THR, s_f["bad"], BAD_THR, s_u["bad"],
                           "する" if same else "しない"))
    assert not same, "uint8 と float が完全一致した(量子化が効いていない)"
    assert abs(s_f["bad"] - s_u["bad"]) < 1.0, (s_f["bad"], s_u["bad"])

    # --- 図 ---------------------------------------------------------------- #
    def norm(a, lo, hi):
        return np.clip((np.asarray(a, np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)

    lo, hi = float(G[ok].min()), float(G[ok].max())
    figs.save_grid(
        "scene",
        [L, R,
         np.asarray(imgio.colorize_disparity(G, vmin=lo, vmax=hi)),
         np.asarray(imgio.colorize_disparity(dmap, vmin=lo, vmax=hi))],
        ["左(実写)", "右(実写)", "真値視差(穴 = 黒)", "SAD max_disp=64"],
        title="実写ステレオ対と視差", ncols=2,
        caption="Middlebury 2014 motorcycle (Scharstein et al., GCPR 2014)。"
                "真値の穴は +inf で入っており、apply_cmap は invalid 色に落とす。")

    err = np.abs(dmap - G)
    thr40 = float(np.quantile(conf[np.isfinite(conf)], 0.4))
    figs.save_grid(
        "error",
        [norm(np.where(ok, err, 0.0), 0, 8), norm(conf, 0, 1),
         norm(np.where(ok & (conf >= thr40), err, 0.0), 0, 8)],
        ["誤差 |d - 真値| (0-8 px)", "信頼度 (0-1)",
         "信頼度で 4 割捨てた後の誤差"],
        title="誤差は信頼度の低いところに集まる", ncols=3,
        caption="下位 4 割を捨てると bad2 は %.2f %% -> %.2f %%。"
                % (gate[0][2], gate[2][2]))

    figs.save_plot(
        "cliff",
        [("bad%.0f [%%]" % BAD_THR, [c[0] for c in cliff],
          [c[1] for c in cliff])],
        xlabel="max_disp [px]", ylabel="bad%.0f [%%]" % BAD_THR,
        title="探索範囲の崖(真の最大視差 %.1f px)" % G[ok].max(),
        caption="真の最大視差を下回る設定は前景を丸ごと失う。")

    z_no_all = np.asarray(fs.depth_from_disparity(G, focal=FOCAL_PX,
                                                  baseline=BASELINE_MM))[ok]
    z_true_all = FOCAL_PX * BASELINE_MM / (G[ok] + DOFFS_PX)
    figs.save_plot(
        "depth_bend",
        [("doffs 無し / 真値", list(G[ok][::97]),
          list((z_no_all / z_true_all)[::97]))],
        xlabel="真値視差 [px]", ylabel="距離の比",
        title="doffs を無視すると比が視差で変わる = 形が反り返る",
        kinds=["scatter"],
        caption="単一のスケールでは直らない(最良でも残差 %.0f mm RMS)。"
                % dep["rms"])

    figs.save_table(
        "methods",
        ["手法", "bad%.0f [%%]" % BAD_THR, "RMS [px]", "秒"],
        [[t, "%.2f" % b, "%.2f" % r, "%.1f" % s] for t, b, r, s in meth],
        title="手法の順位は実写で入れ替わる",
        caption="census が最下位なのは窓が 64 bit で頭打ちだから。")

    print("\n所見")
    print("  * 真値の穴は NaN ではなく +inf。np.nanmedian は %.2f px と答える"
          "(正しくは %.2f px)。" % (h["med_nan"], h["med_true"]))
    print("  * 既定 max_disp=16 は bad%.0f %.2f %%。崖は 48 と 64 の間"
          "(真の最大 %.2f px)。" % (BAD_THR, by_md[16], G[ok].max()))
    print("  * ゼロ点 %.2f %% に対し SGM %.2f %%。信頼度で 4 割捨てると %.2f %%。"
          % (best_null, by_m["SGM"], gate[2][2]))
    print("  * doffs を無視すると距離が %.3f〜%.3f 倍にばらけ、単一係数で直らない"
          "(残差 %.0f mm RMS = レンジの %.1f %%)。"
          % (dep["ratio"][0], dep["ratio"][1], dep["rms"],
             100 * dep["rms"] / dep["span"]))
    print("  * uint8 でも通るが同じ数字は返らない(%.2f %% 対 %.2f %%)。"
          % (s_f["bad"], s_u["bad"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
