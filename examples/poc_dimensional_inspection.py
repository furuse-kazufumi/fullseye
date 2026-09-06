# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_dimensional_inspection — 産業部品の寸法検査(サブピクセルのエッジ計測)を、
**真値を自分で握った合成部品**で測り、同時に **repo に埋もれていた 1-D 測定モジュール
(``measuring1d`` / ``metrology``、6 + 8 = 14 関数)を実地評価**する PoC。

    py -3.11 examples/poc_dimensional_inspection.py

【この PoC が答える問い】
検査現場でいちばん素朴な問い —「この部品の幅は 50.50 画素だ、と言い切れるか」。
言い切るには (1) 偏り(いつも同じ方向にずれる分)と (2) 散らばり(撮るたびに
変わる分)を **別々に** 出さなければならない。検査の合否は偏りで決まり、
繰り返し精度は散らばりで決まる。1 つの「誤差」にまとめた瞬間に、どちらの
対策を打つべきかが分からなくなる。

【なぜ「埋もれた実装の実地評価」も兼ねるのか】
``measuring1d.py`` と ``metrology.py`` は 1-D キャリパー計測と 2-D 計測モデルの
中核だが、**``fullseye`` の公開経路のどこからも届かない**(``fs.`` にも
``fs.ledger`` にも無い。``fs.op`` に居る ``m1_*`` 5 本は別実装で、返すのは
**エッジの本数だけ**であり寸法を返さない)。テストは通っている。だが
「見えていなかったものには、見えていなかった理由がある場合がある」ので、
出す前に実地で測る。この PoC は 14 関数を全部叩いて、動く / 動かない /
規約が分からない を表にする。

【グラウンドトゥルース(自分で仕込んだ真値)】
部品の輪郭を **符号つき距離関数(SDF)で解析的に** 定義する:

  * 外形の平行 2 辺(上下面)      —— 真の幅 220.50 px
  * 段差(右半分で上面が 30.00 px 下がる)
  * 45 度の面取り(脚長 26.00 px)と丸み(半径 20.00 px)
  * 内側の平行 2 辺(スロット)   —— 真の幅 50.50 px
  * 円穴                          —— 真の直径 68.50 px
  * ボルト円(6 穴、半径 52.00 px の円上、穴径 10.50 px)
  * 傾いた右端面                  —— 鉛直から 12.000 度

SDF から **面積被覆率**(サブピクセル格子で解析的に)を作り、既知の PSF で
ぼかし、箱で畳んで画素積分にし、既知の雑音を足す。真値は px で握り、
物理単位は 1 px = 12.5 um(テレセントリック想定)で換算して併記する。
1 節で、この合成器そのものを解析式(誤差関数)と突き合わせて検算する。

【比較する 4 系】
  Z. 大津の整数幅        —— ゼロ点。二値化して画素を数える
  M. ``measuring1d``     —— 埋もれていたキャリパー実装
  T. ``metrology``       —— 埋もれていた 2-D 計測モデル(法線測定 + 再フィット)
  F. 自前 50% 交差       —— 平坦部の中点を線形補間(古典的で偏りが無いはずの基準)

【節立て】
 1) 合成器の検算 —— 解析式と画素値・エッジ位置が一致するか
 2) ★ゼロ点 —— 大津の整数幅はどれだけ間違うか
 3) ★寸法別・位置別の実測(偏りと散らばりを分ける)
 4) ★崖(a) —— エッジ間距離 / PSF 幅。干渉が始まる境界
 5) ★崖(b) —— 雑音。偏り(系統)と散らばり(繰り返し)の分離
 6) ★崖(c) —— 測定線が斜めのとき。cos 補正は入っているか
 7) ★崖(d) —— 照明の傾斜。閾値が動いて幅が偏るか
 8) ★崖(e) —— 面取り・丸みで「どこがエッジか」が定義依存になる量
 9) ★埋もれた 14 関数の実地評価表
10) 所見(道具の穴と、足すべき op)

【結果の要点(本文の print が正、以下は道しるべ)】
- ``measuring1d`` は **ゼロ点を 1 桁半上回る**。ただし偏りが消えるのは
  「エッジが十分離れていて、真の位置の小数部で平均したとき」だけ。
  **単発の測定には、真値の小数部に依存する周期誤差(S 字)が残る**。
- 崖は「PSF が大きいと壊れる」ではなく「**エッジ間距離 / PSF 幅** が小さいと
  壊れる」。境界はこの合成で w/sigma ~ 3 付近。
- 測定線が斜めのとき **cos 補正は入っていない**(そういう設計である)。
  測った幅に cos を掛ければ真値に戻る —— ただし戻るのは 30 度まで。
- 面取り 6 px は「エッジ」を 2 本に増やす。丸み半径 8 px は定義次第で
  0.87 x 半径 だけ答えが動く。**サブピクセルの 0.01 px を争う前に、
  縁の定義で 7 px 動いている。**
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs                                            # noqa: E402
import measuring1d as m1                                         # noqa: E402
import metrology as mt                                           # noqa: E402

# --- 撮像系 ----------------------------------------------------------------- #
PIX_UM = 12.5           # 1 px = 12.5 um(テレセントリック想定の換算)
G_PART, G_BG = 0.82, 0.12       # 部品(明)/ 背景(暗)。透過照明のシルエット
DG = G_PART - G_BG              # コントラスト 0.70
SEED = 20260906

# --- 部品の真値(すべて px、出力画素の中心座標系) ------------------------- #
H, W = 430, 680
SS = 4                  # 合成のサブピクセル分割数

R_TOP, R_TOP2, R_BOT = 96.30, 126.30, 316.80     # 上面 / 段差後の上面 / 下面
OUTER_W_LEFT = R_BOT - R_TOP                     # 220.50 外形幅(左半分)
OUTER_W_RIGHT = R_BOT - R_TOP2                   # 190.50 外形幅(右半分)
STEP_H = R_TOP2 - R_TOP                          # 30.00 段差高さ
C_LEFT, C_STEP = 52.00, 430.00                   # 左端面 / 段差の立面
FACE_TILT_DEG = 12.000                           # 右端面の鉛直からの傾き
FACE_ROW0, FACE_COL0 = R_BOT, 628.00             # 右端面が通る点
CHAMFER = 26.00                                  # 左上の 45 度面取りの脚長
FILLET = 20.00                                   # 左下の丸み半径
SLOT_R0, SLOT_R1 = 162.00, 272.00                # スロット(暗)の上下
SLOT_C0, SLOT_C1 = 300.15, 350.65                # スロットの左右 -> 幅 50.50
SLOT_W = SLOT_C1 - SLOT_C0
HOLE_R, HOLE_C, HOLE_RAD = 240.40, 500.75, 34.25         # 円穴 直径 68.50
BOLT_R, BOLT_C, BOLT_PCD, BOLT_RAD = 240.00, 178.00, 52.00, 5.25
BOLT_N, BOLT_PHASE = 6, math.radians(7.0)


def um(px):
    """px -> um。"""
    return px * PIX_UM


# --------------------------------------------------------------------------- #
# 解析的な真値: 誤差関数による「ぼけた段差の画素積分」                          #
# --------------------------------------------------------------------------- #
def _Phi(t):
    return 0.5 * (1.0 + erf(t / math.sqrt(2.0)))


def _psi(t):
    """Phi の原始関数。 d/dt [t*Phi(t) + phi(t)] = Phi(t)。"""
    return t * _Phi(t) + np.exp(-0.5 * t * t) / math.sqrt(2.0 * math.pi)


def step_pixels(k, e, sigma):
    """画素 k(範囲 [k-0.5, k+0.5])における「位置 e のぼけた段差」の画素積分。

    連続像は Phi((x-e)/sigma)。画素値はその区間積分なので
    ``sigma * (psi((k+0.5-e)/sigma) - psi((k-0.5-e)/sigma))`` で **厳密**に出る。
    ここが解析真値の土台 —— 標本化も補間も入っていない。
    """
    k = np.asarray(k, float)
    if sigma <= 0:
        return np.clip(k + 0.5 - e, 0.0, 1.0)
    return sigma * (_psi((k + 0.5 - e) / sigma) - _psi((k - 0.5 - e) / sigma))


def bar_profile(width_px, a, b, sigma, lo=G_BG, hi=G_PART):
    """位置 a で立ち上がり b で立ち下がる明るい帯の、**厳密な**画素積分プロファイル。"""
    k = np.arange(int(width_px), dtype=float)
    return lo + (hi - lo) * (step_pixels(k, a, sigma) - step_pixels(k, b, sigma))


def bar_image(width_px, a, b, sigma, height=64, lo=G_BG, hi=G_PART):
    """上の帯を行方向に並べた 2-D 画像(列方向だけの関数なので画素積分は厳密)。"""
    return np.tile(bar_profile(width_px, a, b, sigma, lo, hi)[None, :], (int(height), 1))


# --------------------------------------------------------------------------- #
# 部品の合成: SDF -> 面積被覆率 -> PSF -> 画素積分                              #
# --------------------------------------------------------------------------- #
def _sdf_box(rr, cc, r0, r1, c0, c1):
    dr = np.maximum(r0 - rr, rr - r1)
    dc = np.maximum(c0 - cc, cc - c1)
    return (np.hypot(np.maximum(dr, 0.0), np.maximum(dc, 0.0))
            + np.minimum(np.maximum(dr, dc), 0.0))


def _round_and(da, db, r):
    """2 つの半平面(外側が正)の共通部分を半径 r で丸めた SDF。

    ``sdRoundBox`` の一般化。深く内側では ``max(da, db)`` に、角の外側では
    ``hypot(...) - r`` に退化する(丸み付き角の厳密な距離)。
    """
    return (np.hypot(np.maximum(da + r, 0.0), np.maximum(db + r, 0.0))
            + np.minimum(np.maximum(da + r, db + r), 0.0) - r)


def part_sdf(rr, cc):
    """部品の符号つき距離(外側が正)。すべて解析式 —— ここが真値の出どころ。"""
    th = math.radians(FACE_TILT_DEG)
    d = _round_and(rr - R_BOT, C_LEFT - cc, FILLET)              # 左下の丸み
    d = np.maximum(d, R_TOP - rr)                                # 上面
    d = np.maximum(d, -math.sin(th) * (rr - FACE_ROW0)
                      + math.cos(th) * (cc - FACE_COL0))         # 傾いた右端面
    d = np.maximum(d, (CHAMFER - ((rr - R_TOP) + (cc - C_LEFT))) / math.sqrt(2.0))
    d = np.maximum(d, -_sdf_box(rr, cc, R_TOP - 300.0, R_TOP2, C_STEP, 1e4))   # 段差
    d = np.maximum(d, -_sdf_box(rr, cc, SLOT_R0, SLOT_R1, SLOT_C0, SLOT_C1))   # スロット
    d = np.maximum(d, -(np.hypot(rr - HOLE_R, cc - HOLE_C) - HOLE_RAD))        # 円穴
    for k in range(BOLT_N):
        a = BOLT_PHASE + 2.0 * math.pi * k / BOLT_N
        d = np.maximum(d, -(np.hypot(rr - (BOLT_R + BOLT_PCD * math.sin(a)),
                                     cc - (BOLT_C + BOLT_PCD * math.cos(a))) - BOLT_RAD))
    return d


def bolt_hole_centers():
    out = []
    for k in range(BOLT_N):
        a = BOLT_PHASE + 2.0 * math.pi * k / BOLT_N
        out.append((BOLT_R + BOLT_PCD * math.sin(a), BOLT_C + BOLT_PCD * math.cos(a), a))
    return out


def _render_sdf(sdf_fn, height, width, psf_sigma, ss=SS):
    """SDF -> 面積被覆率(サブピクセル)-> ガウス PSF -> 箱畳み込みで画素積分。

    被覆率は ``clip(0.5 - d/h, 0, 1)``(h = サブ画素間隔)。直線エッジに対しては
    サブ画素内で厳密に線形なので、面積被覆率の一次近似になる。残差は 1 節で測る。
    """
    h = 1.0 / ss
    r = (np.arange(height * ss, dtype=np.float64) + 0.5) * h - 0.5
    c = (np.arange(width * ss, dtype=np.float64) + 0.5) * h - 0.5
    img = np.empty((height * ss, width * ss), dtype=np.float32)
    blk = 64 * ss
    for i0 in range(0, height * ss, blk):
        i1 = min(i0 + blk, height * ss)
        cc, rr = np.meshgrid(c, r[i0:i1])
        img[i0:i1] = np.clip(0.5 - sdf_fn(rr, cc) / h, 0.0, 1.0).astype(np.float32)
    if psf_sigma > 0:
        img = gaussian_filter(img, psf_sigma * ss, mode="nearest")
    cov = img.reshape(height, ss, width, ss).mean(axis=(1, 3)).astype(np.float64)
    return G_BG + DG * cov


def render_part(psf_sigma, noise_sigma=0.0, illum_grad=0.0, seed=SEED):
    """部品画像。``illum_grad`` は列方向の乗法的な照明傾斜(片側が暗い)。"""
    img = _render_sdf(part_sdf, H, W, psf_sigma)
    if illum_grad:
        x = (np.arange(W) - (W - 1) / 2.0) / (W - 1)
        img = img * (1.0 + illum_grad * x)[None, :]
    if noise_sigma > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise_sigma, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 系 F: 自前サブピクセルエッジ(50% 交差、線形補間)                            #
# --------------------------------------------------------------------------- #
def edges_50(prof, det_sigma=1.0, min_amp=0.10, plateau=None):
    """|勾配| の極大でエッジを見つけ、その両側の平坦部の中点を線形補間で横切る位置。

    平坦部は片側 3 標本の平均で取る(1 標本だと雑音がそのまま真値の推定を汚す)。
    対称な PSF に対して 50% 交差は偏らない —— 4 系のなかで唯一「理屈の上では
    偏りゼロ」の基準として置く。
    """
    prof = np.asarray(prof, float)
    n = len(prof)
    sm = gaussian_filter1d(prof, det_sigma, mode="nearest") if det_sigma > 0 else prof
    ag = np.abs(np.gradient(sm))
    m = int(math.ceil(2.5 * (plateau if plateau else det_sigma))) + 2
    out = []
    for i in range(1, n - 1):
        if not (ag[i] >= ag[i - 1] and ag[i] > ag[i + 1]):
            continue
        lo, hi = max(0, i - m), min(n - 1, i + m)
        a = float(np.mean(sm[max(0, lo - 1):lo + 2]))
        b = float(np.mean(sm[hi - 1:min(n, hi + 2)]))
        if abs(b - a) < min_amp:
            continue
        mid = 0.5 * (a + b)
        s = 1.0 if b > a else -1.0
        d = (sm[lo:hi + 1] - mid) * s
        j = np.where(np.diff(np.sign(d)) != 0)[0]
        if not len(j):
            continue
        jj = int(j[np.argmin(np.abs(j + lo - i))])
        f = d[jj] / (d[jj] - d[jj + 1]) if d[jj] != d[jj + 1] else 0.0
        out.append({"pos": float(lo + jj + f), "amplitude": float(b - a),
                    "polarity": "positive" if b > a else "negative"})
    ded = []
    for e in out:
        if ded and abs(e["pos"] - ded[-1]["pos"]) < 1.0 and e["polarity"] == ded[-1]["polarity"]:
            if abs(e["amplitude"]) > abs(ded[-1]["amplitude"]):
                ded[-1] = e
            continue
        ded.append(e)
    return ded


def pairs_50(prof, det_sigma=1.0, min_amp=0.10, plateau=None):
    ed = edges_50(prof, det_sigma, min_amp, plateau)
    out, i = [], 0
    while i < len(ed) - 1:
        if ed[i]["polarity"] != ed[i + 1]["polarity"]:
            out.append({"first": ed[i]["pos"], "second": ed[i + 1]["pos"],
                        "width": ed[i + 1]["pos"] - ed[i]["pos"]})
            i += 2
        else:
            i += 1
    return out


def line_samples(image, r0, c0, phi, n):
    """(r0, c0) から向き ``phi``(col 軸から row 軸へ)に **厳密に 1 px 間隔**で n 点。

    ``fs.line_profile`` は端点 2 つと点数しか取らないので、間隔をちょうど 1 px に
    したいときは終点を自分で作るしかない(所見 (C))。
    """
    r1 = r0 + (n - 1) * math.sin(phi)
    c1 = c0 + (n - 1) * math.cos(phi)
    return fs.line_profile(image, (r0, c0), (r1, c1), num=n)


# --------------------------------------------------------------------------- #
# 系 Z: 大津の整数幅(ゼロ点)                                                  #
# --------------------------------------------------------------------------- #
def otsu_runs(image, row, c0, c1):
    """大津で二値化し、行 ``row`` の [c0, c1) にある明/暗の連(整数長)を返す。"""
    mask = np.asarray(fs.op.otsu(image), float) > 0.5
    seg = mask[int(round(row)), int(c0):int(c1)]
    runs, start = [], 0
    for i in range(1, len(seg) + 1):
        if i == len(seg) or seg[i] != seg[start]:
            runs.append({"value": bool(seg[start]), "start": int(c0) + start,
                         "length": i - start})
            start = i
    return runs


def otsu_bright_run_len(image, row, c0, c1):
    r = [x for x in otsu_runs(image, row, c0, c1) if x["value"]]
    return max((x["length"] for x in r), default=0)


def otsu_dark_run_len(image, row, c0, c1):
    r = [x for x in otsu_runs(image, row, c0, c1) if not x["value"]]
    return max((x["length"] for x in r), default=0)


# --------------------------------------------------------------------------- #
# 節の見出し                                                                    #
# --------------------------------------------------------------------------- #
def head(n, title):
    print(f"\n{'=' * 78}\n {n}) {title}\n{'=' * 78}")


def sub(title):
    print(f"\n  --- {title} ---")


# 埋もれた 14 関数の評価台帳(節を進めながら埋める)
LEDGER = []


def note(module, fn, status, contract, remark=""):
    LEDGER.append({"module": module, "fn": fn, "status": status,
                   "contract": contract, "remark": remark})


# --------------------------------------------------------------------------- #
# 1) 合成器の検算                                                               #
# --------------------------------------------------------------------------- #
def section_synth_check():
    head(1, "合成器の検算 —— 自分の真値を疑う")
    print("  SDF -> 被覆率 -> PSF -> 画素積分 の経路が、解析式(誤差関数)と")
    print("  一致するか。ここが合わなければ以下の全部の数字が意味を持たない。")

    edge_col = 61.37
    rows = 24

    def half_plane(rr, cc):
        return edge_col - cc                              # cc > edge_col が部品(明)

    print(f"\n  {'PSF sigma':>10} {'画素値の最大差':>14} {'RMS 差':>10} "
          f"{'エッジ位置差 [px]':>18}")
    worst_gray, worst_pos = 0.0, 0.0
    for s in (0.8, 1.5, 3.0):
        img = _render_sdf(half_plane, rows, 128, s)
        ana = G_BG + DG * step_pixels(np.arange(128, dtype=float), edge_col, s)
        d = np.abs(img[rows // 2] - ana)
        e_num = edges_50(img[rows // 2], det_sigma=1.0)
        e_ana = edges_50(ana, det_sigma=1.0)
        dp = abs(e_num[0]["pos"] - e_ana[0]["pos"]) if (e_num and e_ana) else float("nan")
        worst_gray = max(worst_gray, float(d.max()))
        worst_pos = max(worst_pos, dp)
        print(f"  {s:10.2f} {d.max():14.2e} {float(np.sqrt((d ** 2).mean())):10.2e} "
              f"{dp:18.5f}")

    print(f"\n  -> 合成器の画素値は解析式と最大 {worst_gray:.1e}(グレー単位)、")
    print(f"     エッジ位置は最大 {worst_pos:.5f} px しか違わない。真値として使える。")
    print("     (被覆率の一次近似が持ち込む誤差は、この水準に収まっている)")

    # 50% 交差そのものの検算: 解析プロファイルで真値を当てられるか
    sub("系 F(50% 交差)の素性 —— 解析プロファイルで真値を当てられるか")
    errs = []
    for ph in np.linspace(0.0, 1.0, 9)[:-1]:
        e = 60.0 + ph
        ana = G_BG + DG * step_pixels(np.arange(128, dtype=float), e, 1.5)
        errs.append(edges_50(ana, det_sigma=1.0)[0]["pos"] - e)
    errs = np.array(errs)
    print(f"  真値の小数部 8 点で: 偏り {errs.mean():+.5f} px / "
          f"振れ幅 {np.ptp(errs):.5f} px")
    print("  -> 50% 交差は(対称な PSF・孤立エッジなら)偏らない。以下ではこれを")
    print("     「理屈の上で正しい基準」として、他の 3 系と並べる。")
    return worst_gray, worst_pos


# --------------------------------------------------------------------------- #
# 2) ゼロ点                                                                     #
# --------------------------------------------------------------------------- #
def section_zero_point(img):
    head(2, "★ゼロ点 —— 大津で二値化して画素を数える")
    print("  検査の一番素朴な実装。整数しか出ないので、真値が整数でなければ")
    print("  必ず外れる。上回るべき相手をまず数字にする。")

    rows_slot = [200.0, 217.0, 240.0]
    print(f"\n  {'測る量':<22}{'真値 [px]':>11}{'大津 [px]':>11}"
          f"{'誤差 [px]':>11}{'誤差 [um]':>11}")
    recs = []
    for r in rows_slot:
        wz = otsu_dark_run_len(img, r, SLOT_C0 - 40, SLOT_C1 + 40)
        recs.append(wz - SLOT_W)
        print(f"  {'スロット幅 row=' + str(int(r)):<22}{SLOT_W:11.2f}{wz:11.0f}"
              f"{wz - SLOT_W:+11.2f}{um(wz - SLOT_W):+11.1f}")
    # 外形幅(列方向に数える)。穴・スロットを避けた列を選ぶ
    mask = np.asarray(fs.op.otsu(img), float) > 0.5
    for c, truth in ((250, OUTER_W_LEFT), (380, OUTER_W_LEFT), (560, OUTER_W_RIGHT)):
        col = mask[:, c]
        ln = int(col.sum())
        recs.append(ln - truth)
        print(f"  {'外形幅 col=' + str(c):<22}{truth:11.2f}{ln:11.0f}"
              f"{ln - truth:+11.2f}{um(ln - truth):+11.1f}")
    # 円穴: 面積から等価直径
    rr, cc = np.mgrid[0:H, 0:W]
    near = (np.hypot(rr - HOLE_R, cc - HOLE_C) < HOLE_RAD + 12)
    area = int((~mask & near).sum())
    d_eq = 2.0 * math.sqrt(area / math.pi)
    recs.append(d_eq - 2 * HOLE_RAD)
    print(f"  {'円穴の等価直径':<22}{2 * HOLE_RAD:11.2f}{d_eq:11.2f}"
          f"{d_eq - 2 * HOLE_RAD:+11.2f}{um(d_eq - 2 * HOLE_RAD):+11.1f}")

    z = float(np.sqrt(np.mean(np.array(recs) ** 2)))
    print(f"\n  -> ゼロ点の RMS 誤差 {z:.3f} px = {um(z):.1f} um。")
    print("     等価直径だけは面積を数えるぶん整数量子化が薄まって健闘する")
    print("     (数え方を変えると誤差が変わる = 「幅」の定義が測り方に依存する)。")
    return z


# --------------------------------------------------------------------------- #
# 3) 寸法別・位置別の実測                                                       #
# --------------------------------------------------------------------------- #
def measure_pair_width(img, row, c_center, half_len, det_sigma=1.0, thr=0.15, band=1):
    """``measuring1d`` で 1 本の水平測定線から最初のエッジ対を取る。"""
    ms = m1.gen_measure_rectangle2(row, c_center, 0.0, half_len, band, img.shape)
    pr = m1.measure_pairs(img, ms, sigma=det_sigma, threshold=thr)
    return ms, pr


def section_dimensions(img):
    head(3, "★寸法別・位置別の実測 —— 偏りと散らばりを分ける")
    print("  1 つの数字にまとめない。寸法ごと・位置ごとに割って、")
    print("  「いつも同じ方向にずれる分(偏り)」と「位置で振れる分」を別に出す。")

    # ---- (b) 平行 2 辺: スロット幅を 9 行で ---- #
    sub("(b) 内側の平行 2 辺(スロット幅、真値 50.50 px = 631.3 um)")
    rows = np.arange(175.0, 261.0, 10.0)
    res = {"M": [], "F": [], "Z": []}
    for r in rows:
        _, pr = measure_pair_width(img, r, (SLOT_C0 + SLOT_C1) / 2, 45)
        res["M"].append(pr[0]["width"] if pr else np.nan)
        prof = line_samples(img, r, SLOT_C0 - 45, 0.0, 136)
        p50 = pairs_50(prof, det_sigma=1.0)
        res["F"].append(p50[0]["width"] if p50 else np.nan)
        res["Z"].append(otsu_dark_run_len(img, r, SLOT_C0 - 40, SLOT_C1 + 40))
    print(f"  {'系':<26}{'偏り [px]':>11}{'散らばり(1s)':>14}"
          f"{'偏り [um]':>11}{'散らばり [um]':>14}")
    slot_bias = {}
    for key, name in (("Z", "Z 大津の整数幅"), ("M", "M measuring1d"), ("F", "F 自前 50% 交差")):
        v = np.array(res[key], float) - SLOT_W
        slot_bias[key] = float(np.nanmean(v))
        print(f"  {name:<26}{np.nanmean(v):+11.4f}{np.nanstd(v):14.4f}"
              f"{um(np.nanmean(v)):+11.2f}{um(np.nanstd(v)):14.2f}")

    # metrology の矩形当てはめ(スロットは軸平行の矩形)
    model = mt.create_metrology_model()
    mt.add_metrology_object_rectangle2_measure(
        model, (SLOT_R0 + SLOT_R1) / 2, (SLOT_C0 + SLOT_C1) / 2,
        math.pi / 2, (SLOT_R1 - SLOT_R0) / 2, SLOT_W / 2, n=60)
    rr = mt.apply_metrology_model(model, img, measure_length=8.0, sigma=1.0, threshold=0.15)[0]
    t_w = 2.0 * rr["params"]["l2"] if rr["params"] else float("nan")
    slot_bias["T"] = t_w - SLOT_W
    print(f"  {'T metrology(矩形)':<25}{t_w - SLOT_W:+11.4f}{'(単発)':>14}"
          f"{um(t_w - SLOT_W):+11.2f}{'':>14}")
    print(f"     -> 半辺長 l1={rr['params']['l1']:.3f}(真 {(SLOT_R1 - SLOT_R0) / 2:.2f}) "
          f"l2={rr['params']['l2']:.3f}(真 {SLOT_W / 2:.2f}) "
          f"rms={rr['rms']:.4f} px, エッジ点 {len(rr['edge_points'])} 点")

    # ---- (b2) 外形の平行 2 辺 ---- #
    sub("(b2) 外形の平行 2 辺(左半分 220.50 px / 右半分 190.50 px)")
    print(f"  {'測る量':<22}{'真値':>9}{'M':>10}{'誤差[px]':>10}{'誤差[um]':>10}")
    outer_err = []
    for c, truth in ((250.0, OUTER_W_LEFT), (380.0, OUTER_W_LEFT), (560.0, OUTER_W_RIGHT)):
        ms = m1.gen_measure_rectangle2((R_TOP + R_BOT) / 2, c, math.pi / 2, 140, 1, img.shape)
        pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.2)
        w = pr[0]["width"] if pr else float("nan")
        outer_err.append(w - truth)
        print(f"  {'外形幅 col=' + str(int(c)):<22}{truth:9.2f}{w:10.4f}"
              f"{w - truth:+10.4f}{um(w - truth):+10.2f}")
    print(f"  段差高さ(左右の差): 真 {STEP_H:.2f} px / 実測 "
          f"{(outer_err[1] + OUTER_W_LEFT) - (outer_err[2] + OUTER_W_RIGHT):.4f} px")

    # ---- (c) 円: 直径と中心 ---- #
    sub("(c) 円穴(真: 直径 68.50 px / 中心 row 240.40, col 500.75)")
    model = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(model, HOLE_R, HOLE_C, HOLE_RAD, n=72)
    rc = mt.apply_metrology_model(model, img, measure_length=8.0, sigma=1.0, threshold=0.15)[0]
    # measuring1d: 放射方向の測定矩形を 36 本
    pts = []
    for a in np.linspace(0, 2 * math.pi, 36, endpoint=False):
        r0 = HOLE_R + (HOLE_RAD - 9) * math.sin(a)
        c0 = HOLE_C + (HOLE_RAD - 9) * math.cos(a)
        ms = m1.gen_measure_rectangle2(r0 + 9 * math.sin(a), c0 + 9 * math.cos(a),
                                       a, 9, 1, img.shape)
        ed = m1.measure_pos(img, ms, sigma=1.0, threshold=0.2)
        if ed:
            e = min(ed, key=lambda x: abs(abs(math.hypot(x["row"] - HOLE_R,
                                                         x["col"] - HOLE_C)) - HOLE_RAD))
            pts.append((e["row"], e["col"]))
    fm = fs.fit_circle(np.array(pts))
    print(f"  {'系':<26}{'直径 [px]':>11}{'誤差 [px]':>11}{'中心誤差 [px]':>14}{'rms':>9}")
    for name, cy, cx, rad, rms in (
            ("T metrology(円)", rc["params"]["row"], rc["params"]["col"],
             rc["params"]["radius"], rc["rms"]),
            ("M measuring1d + fit_circle", fm["cy"], fm["cx"], fm["r"], fm["rms"])):
        de = 2 * rad - 2 * HOLE_RAD
        ce = math.hypot(cy - HOLE_R, cx - HOLE_C)
        print(f"  {name:<26}{2 * rad:11.4f}{de:+11.4f}{ce:14.4f}{rms:9.4f}")
    circ_err = 2 * rc["params"]["radius"] - 2 * HOLE_RAD

    # ---- (d) 角度 ---- #
    sub("(d) 傾いた右端面(真: 鉛直から 12.000 度)")
    model = mt.create_metrology_model()
    th = math.radians(FACE_TILT_DEG)
    p0 = (150.0, FACE_COL0 + math.tan(th) * (150.0 - FACE_ROW0) + 2.0)   # わざと 2 px ずらす
    p1 = (300.0, FACE_COL0 + math.tan(th) * (300.0 - FACE_ROW0) + 2.0)
    mt.add_metrology_object_line_measure(model, p0[0], p0[1], p1[0], p1[1], n=40)
    rl = mt.apply_metrology_model(model, img, measure_length=8.0, sigma=1.0, threshold=0.15)[0]
    pl = rl["params"]
    tilt_T = math.degrees(math.atan2(pl["col2"] - pl["col1"], pl["row2"] - pl["row1"]))
    # measuring1d: 行ごとに水平測定線
    pts = []
    for r in np.arange(150.0, 301.0, 6.0):
        c_exp = FACE_COL0 + math.tan(th) * (r - FACE_ROW0)
        ms = m1.gen_measure_rectangle2(r, c_exp, 0.0, 12, 1, img.shape)
        ed = m1.measure_pos(img, ms, sigma=1.0, threshold=0.2, transition="negative")
        if ed:
            pts.append((ed[0]["row"], ed[0]["col"]))
    fl = fs.fit_line(np.array(pts))
    tilt_M = math.degrees(math.atan2(fl["dx"], fl["dy"]))
    print(f"  {'系':<30}{'傾き [deg]':>12}{'誤差 [deg]':>12}{'rms [px]':>10}")
    print(f"  {'T metrology(直線)':<29}{tilt_T:12.4f}{tilt_T - FACE_TILT_DEG:+12.4f}"
          f"{rl['rms']:10.4f}")
    print(f"  {'M measuring1d + fit_line':<30}{tilt_M:12.4f}{tilt_M - FACE_TILT_DEG:+12.4f}"
          f"{fl['rms']:10.4f}")
    print(f"  (metrology の angle_deg フィールドは {pl['angle_deg']:.4f} —— これは")
    print("   col 軸からの角度で、鉛直からの傾きとは 90 度ずれる。規約の実測は 9 節)")

    note("metrology", "create_metrology_model", "OK",
         "引数なし -> dict {'objects': []}", "ハンドルではなく素の dict")
    note("metrology", "add_metrology_object_line_measure", "OK",
         "(model,row1,col1,row2,col2,n=25) -> index int", "端点は (row,col)")
    note("metrology", "add_metrology_object_circle_measure", "OK",
         "(model,row,col,radius,n=40) -> index int", "")
    note("metrology", "add_metrology_object_rectangle2_measure", "OK",
         "(model,row,col,phi,l1,l2,n=40) -> index int",
         "l1/l2 は半辺長。phi は col 軸から row 軸へ")
    note("metrology", "apply_metrology_model", "OK",
         "(model,image,measure_length=6,sigma=1,threshold=0.05) -> list[dict]",
         "dict: type/edge_points(M,2 row,col)/amplitudes/score/centroid/params/rms")
    note("measuring1d", "gen_measure_rectangle2", "OK",
         "(row,col,phi,length1,length2,shape) -> dict",
         "phi=0 は +col 方向。length1/2 は半長/半幅ではなく「半長」と「平均化幅」")
    note("measuring1d", "measure_pos", "OK",
         "list[dict] pos/dist/row/col/amplitude/polarity",
         "amplitude はグレー差(符号つき)、pos は測定開始点からの px")
    note("measuring1d", "measure_pairs", "OK",
         "list[dict] first/second/width/first_point/second_point/*_amplitude",
         "width は px。first/second は pos(画像座標ではない)")
    return slot_bias, circ_err, tilt_T - FACE_TILT_DEG, tilt_M - FACE_TILT_DEG


# --------------------------------------------------------------------------- #
# 4) 崖 (a) —— エッジ間距離 / PSF 幅                                            #
# --------------------------------------------------------------------------- #
def section_cliff_blur():
    head(4, "★崖 (a) —— エッジ間距離 / PSF 幅。隣のエッジとの干渉")
    print("  「ぼけると壊れる」ではない。壊れるのは **エッジ間距離 / PSF 幅** が")
    print("  小さいとき。真値の小数部 8 点で平均して、干渉の偏りと、位置の")
    print("  小数部に依存する周期誤差(S 字)を分けて出す。")

    w_true = 12.00
    phases = np.linspace(0.0, 1.0, 9)[:-1]
    print(f"\n  真の幅 w = {w_true:.2f} px 固定、PSF sigma を振る(検出 sigma は 1.0 固定)")
    print(f"  {'PSF s':>7}{'w/s':>7} | {'M 偏り':>9}{'M 周期誤差':>11}{'検出率':>7}"
          f" | {'F 偏り':>9}{'F 周期誤差':>11}")
    rows = []
    for ps in (0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0):
        mv, fv, nfound = [], [], 0
        for ph in phases:
            a = 40.0 + ph
            b = a + w_true
            img = bar_image(120, a, b, ps, height=24)
            ms = m1.gen_measure_rectangle2(12, 59.5, 0.0, 45, 1, img.shape)
            pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
            if pr:
                nfound += 1
                mv.append(pr[0]["width"] - w_true)
            p50 = pairs_50(img[12], det_sigma=1.0, plateau=max(1.0, ps))
            if p50:
                fv.append(p50[0]["width"] - w_true)
        mb = np.mean(mv) if mv else float("nan")
        mp = np.ptp(mv) if len(mv) > 1 else float("nan")
        fb = np.mean(fv) if fv else float("nan")
        fp = np.ptp(fv) if len(fv) > 1 else float("nan")
        rows.append((ps, w_true / ps, mb, mp, nfound / len(phases), fb, fp))
        print(f"  {ps:7.2f}{w_true / ps:7.2f} | {mb:+9.4f}{mp:11.4f}"
              f"{nfound / len(phases):7.0%} | {fb:+9.4f}{fp:11.4f}")

    # 崖の境界: |偏り| が 0.05 px を超える最初の w/sigma
    thr = 0.05
    edge_ratio = None
    for ps, ratio, mb, mp, det, fb, fp in rows:
        if np.isfinite(mb) and abs(mb) > thr:
            edge_ratio = ratio
    print(f"\n  -> ``measuring1d`` の幅の偏りが {thr} px を超えるのは "
          f"w/sigma <= {edge_ratio:.2f} から。")
    print("     つまり **PSF 幅の 3 倍より近いエッジ同士は、互いを引き寄せる**。")
    print("     周期誤差(S 字)は逆にぼけるほど小さくなる —— ぼけは敵ではない。")

    sub("同じ崖を逆から: PSF sigma = 1.5 固定で、エッジ間距離を詰める")
    print(f"  {'w':>7}{'w/s':>7} | {'M 偏り':>9}{'検出率':>7} | {'F 偏り':>9}")
    lost_at = None
    for w in (24.0, 16.0, 12.0, 9.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0):
        mv, fv, nfound = [], [], 0
        for ph in phases:
            a = 40.0 + ph
            img = bar_image(120, a, a + w, 1.5, height=24)
            ms = m1.gen_measure_rectangle2(12, 59.5, 0.0, 45, 1, img.shape)
            pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
            if pr:
                nfound += 1
                mv.append(pr[0]["width"] - w)
            p50 = pairs_50(img[12], det_sigma=1.0, plateau=1.5)
            if p50:
                fv.append(p50[0]["width"] - w)
        det = nfound / len(phases)
        if det < 1.0 and lost_at is None:
            lost_at = w
        print(f"  {w:7.2f}{w / 1.5:7.2f} | {np.mean(mv) if mv else float('nan'):+9.4f}"
              f"{det:7.0%} | {np.mean(fv) if fv else float('nan'):+9.4f}")
    print(f"\n  -> エッジ対を **見失う** のは w = {lost_at} px(= {lost_at / 1.5:.2f} sigma)から。")
    print("     見失う前に、まず偏る。検査で危ないのは「測れなかった」ではなく")
    print("     「測れたが 0.2 px 小さく出た」のほう。")
    return edge_ratio, lost_at


# --------------------------------------------------------------------------- #
# 5) 崖 (b) —— 雑音                                                             #
# --------------------------------------------------------------------------- #
def section_cliff_noise():
    head(5, "★崖 (b) —— 雑音。偏り(系統)と散らばり(繰り返し)を分ける")
    print("  同じ部品を 32 回撮り直す。平均のずれが偏り(校正で消せる)、")
    print("  ばらつきが繰り返し精度(消せない)。検査の合否には偏りが効く。")

    w_true, a = 40.50, 30.27
    base = bar_image(140, a, a + w_true, 1.5, height=48)
    rng = np.random.default_rng(SEED)
    print(f"\n  コントラスト {DG:.2f}(明 {G_PART} / 暗 {G_BG})、真の幅 {w_true} px")
    print(f"  {'雑音 s':>8}{'SNR':>7} | {'M 偏り':>9}{'M 1s':>8}{'成功':>6}"
          f" | {'F 偏り':>9}{'F 1s':>8} | {'Z 偏り':>9}{'Z 1s':>8}")
    out = []
    for ns in (0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10):
        mv, fv, zv, ok = [], [], [], 0
        n_rep = 32 if ns > 0 else 1
        for _ in range(n_rep):
            img = base + (rng.normal(0, ns, base.shape) if ns > 0 else 0.0)
            ms = m1.gen_measure_rectangle2(24, 69.5, 0.0, 60, 1, img.shape)
            pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
            if pr:
                ok += 1
                mv.append(pr[0]["width"] - w_true)
            p50 = pairs_50(img[24], det_sigma=1.0, plateau=1.5)
            if p50:
                fv.append(p50[0]["width"] - w_true)
            zv.append(otsu_bright_run_len(img, 24, 0, 140) - w_true)
        snr = DG / ns if ns > 0 else float("inf")
        out.append((ns, np.mean(mv) if mv else np.nan, np.std(mv) if mv else np.nan))
        print(f"  {ns:8.3f}{snr:7.0f} | {np.mean(mv) if mv else float('nan'):+9.4f}"
              f"{np.std(mv) if mv else float('nan'):8.4f}{ok / n_rep:6.0%}"
              f" | {np.mean(fv) if fv else float('nan'):+9.4f}"
              f"{np.std(fv) if fv else float('nan'):8.4f}"
              f" | {np.mean(zv):+9.4f}{np.std(zv):8.4f}")

    sub("幅方向の平均化(length2)は散らばりだけを下げるか")
    print(f"  {'length2':>8}{'M 偏り':>10}{'M 1s':>9}{'理論 1/sqrt(n)':>15}")
    ref = None
    for band in (1, 3, 9, 25):
        v = []
        for _ in range(24):
            img = base + rng.normal(0, 0.02, base.shape)
            ms = m1.gen_measure_rectangle2(24, 69.5, 0.0, 60, band, img.shape)
            pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
            if pr:
                v.append(pr[0]["width"] - w_true)
        s = float(np.std(v))
        if ref is None:
            ref = s
        print(f"  {band:8d}{np.mean(v):+10.4f}{s:9.4f}{ref / math.sqrt(band):15.4f}")
    print("  -> 平均化は散らばりを下げるが、偏りは動かない。**偏りは平均化では消えない**。")
    return out


# --------------------------------------------------------------------------- #
# 6) 崖 (c) —— 測定線が斜め                                                     #
# --------------------------------------------------------------------------- #
def section_cliff_angle():
    head(6, "★崖 (c) —— 測定線が輪郭に対して斜め。cos 補正は入っているか")
    print("  ``measure_pos`` は測定線に沿って測る。輪郭に対して alpha だけ傾ければ")
    print("  幅は 1/cos(alpha) に伸びる **はず**。入っているのは補正か、素の値か。")

    w_true, a = 30.50, 45.30
    img = bar_image(200, a, a + w_true, 1.5, height=260)
    print(f"\n  真の幅 {w_true} px、PSF sigma 1.5")
    print(f"  {'alpha':>7}{'1/cos':>8} | {'M 測定値':>10}{'測定/真':>9}"
          f"{'cos 補正後の誤差':>17} | {'F cos 補正後':>13}")
    corr = []
    for deg in (0.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 70.0):
        al = math.radians(deg)
        n = int(160 / max(math.cos(al), 1e-6))
        n = min(n, 300)
        r0 = 130.0 - 0.5 * n * math.sin(al)
        ms = m1.gen_measure_rectangle2(r0 + 0.5 * (n - 1) * math.sin(al),
                                       10.0 + 0.5 * (n - 1) * math.cos(al),
                                       al, (n - 1) / 2.0, 1, img.shape)
        pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
        wm = pr[0]["width"] if pr else float("nan")
        prof = line_samples(img, r0, 10.0, al, n)
        p50 = pairs_50(prof, det_sigma=1.0, plateau=1.5 / max(math.cos(al), 1e-6))
        wf = p50[0]["width"] if p50 else float("nan")
        corr.append(wm * math.cos(al) - w_true)
        print(f"  {deg:7.1f}{1 / math.cos(al):8.4f} | {wm:10.4f}{wm / w_true:9.4f}"
              f"{wm * math.cos(al) - w_true:+17.4f} | {wf * math.cos(al) - w_true:+13.4f}")
    print("\n  -> **cos 補正は入っていない**(測定/真 が 1/cos に一致)。設計どおりで、")
    print("     測定線の向きを知っているのは呼ぶ側だから正しい。ただし")
    print("     cos を掛けて戻せるのは 30 度まで —— それ以上は、測定線に沿った")
    print("     実効 PSF が sigma/cos に広がって干渉と補間誤差が効き始める。")
    return corr


# --------------------------------------------------------------------------- #
# 7) 崖 (d) —— 照明の傾斜                                                       #
# --------------------------------------------------------------------------- #
def section_cliff_illum():
    head(7, "★崖 (d) —— 照明の傾斜(片側が暗い)")
    print("  乗法的な照明傾斜を掛ける。大域しきい値はエッジを片側に流すはず。")
    print("  局所的に平坦部を取り直す方式(50% 交差)と、勾配極大方式はどうか。")

    w_true, a = 40.50, 45.27
    print(f"\n  真の幅 {w_true} px。傾斜 g は画像端で +-g/2 の乗法変化")
    print(f"  {'g':>7} | {'Z 偏り':>9} | {'M 偏り':>9} | {'F 偏り':>9}")
    zz, mm, ff = [], [], []
    for g in (0.0, 0.1, 0.2, 0.4, 0.8, 1.2):
        img = bar_image(140, a, a + w_true, 1.5, height=48)
        x = (np.arange(140) - 69.5) / 139.0
        img = img * (1.0 + g * x)[None, :]
        zw = otsu_bright_run_len(img, 24, 0, 140) - w_true
        ms = m1.gen_measure_rectangle2(24, 69.5, 0.0, 60, 1, img.shape)
        pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.15)
        mw = (pr[0]["width"] - w_true) if pr else float("nan")
        p50 = pairs_50(img[24], det_sigma=1.0, plateau=1.5)
        fw = (p50[0]["width"] - w_true) if p50 else float("nan")
        zz.append(zw); mm.append(mw); ff.append(fw)
        print(f"  {g:7.2f} | {zw:+9.4f} | {mw:+9.4f} | {fw:+9.4f}")
    print("\n  -> 大域しきい値(Z)は傾斜でまるごと流れる。勾配極大(M)と 50% 交差(F)は")
    print("     どちらも局所量なのでほとんど動かない。**照明の均一化に金をかける前に、")
    print("     しきい値を大域で持っていないかを見るほうが安い。**")
    return zz, mm, ff


# --------------------------------------------------------------------------- #
# 8) 崖 (e) —— 面取り・丸みで「どこがエッジか」                                 #
# --------------------------------------------------------------------------- #
def _front_lit_profile(width_px, centre, half_base, kind, size, psf, ss=16):
    """同軸照明・ランバート反射の「上面 -> 縁 -> 側面」の 1-D 画素積分プロファイル。

    面取り(45 度の平面)は明るさが cos45 = 0.707 の**一定**になるので、
    プロファイルは 2 段の階段になる。丸み(半径 rf の円筒面)は法線角 t が
    0 -> 90 度へ連続に回るので明るさは sqrt(1 - (x/rf)^2) の四分楕円になる。
    どちらも解析式なので、細かい格子で評価して PSF を掛け、箱で畳めば画素積分。
    """
    h = 1.0 / ss
    x = (np.arange(width_px * ss) + 0.5) * h - 0.5
    d = np.abs(x - centre)                       # 中心からの距離
    b = np.zeros_like(x)
    inner = half_base - size
    b[d <= inner] = 1.0
    band = (d > inner) & (d <= half_base)
    if kind == "chamfer":
        b[band] = math.cos(math.radians(45.0))
    else:                                        # fillet
        u = (d[band] - inner) / size
        b[band] = np.sqrt(np.maximum(0.0, 1.0 - u * u))
    prof = G_BG + DG * b
    if psf > 0:
        prof = gaussian_filter1d(prof, psf * ss, mode="nearest")
    return prof.reshape(width_px, ss).mean(axis=1)


def section_cliff_chamfer():
    head(8, "★崖 (e) —— 面取り・丸みで「どこがエッジか」が定義依存になる量")
    print("  透過照明のシルエットなら縁は 1 点に決まる。決まらないのは反射照明。")
    print("  同軸照明・ランバート反射で、45 度の面取りと半径 rf の丸みを合成する。")
    print("  真値は 2 つある: **上面の幅**(縁の始まり)と **底面の幅**(縁の終わり)。")

    width, centre, half_base, psf = 160, 79.5, 45.25, 1.2
    print(f"\n  底面の半幅 {half_base} px 固定、PSF sigma {psf}")
    print(f"  {'縁':>8}{'寸法':>7}{'上面幅(真)':>12}{'底面幅(真)':>12}"
          f"{'M エッジ数':>11}{'M 幅':>10}{'F 幅':>10}{'定義の幅':>10}")
    spread = {}
    for kind in ("chamfer", "fillet"):
        for size in (2.0, 4.0, 6.0, 8.0):
            prof = _front_lit_profile(width, centre, half_base, kind, size, psf)
            img = np.tile(prof[None, :], (24, 1))
            ms = m1.gen_measure_rectangle2(12, centre, 0.0, 70, 1, img.shape)
            ed = m1.measure_pos(img, ms, sigma=1.0, threshold=0.10)
            pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.10)
            wm = pr[0]["width"] if pr else float("nan")
            p50 = pairs_50(prof, det_sigma=1.0, plateau=max(1.2, size))
            wf = p50[0]["width"] if p50 else float("nan")
            w_top, w_base = 2 * (half_base - size), 2 * half_base
            spread[(kind, size)] = (wm, wf, w_top, w_base)
            print(f"  {kind:>8}{size:7.1f}{w_top:12.2f}{w_base:12.2f}"
                  f"{len(ed):11d}{wm:10.3f}{wf:10.3f}{w_base - w_top:10.2f}")

    print("\n  読み方:")
    print("  * 面取りは **エッジを 2 本に増やす**(上面/面取りの境と、面取り/側面の境)。")
    print("    キャリパーは最初の対を返すので、答えは黙って『上面の幅』側に寄る。")
    print("  * 丸みは 1 本のなだらかな遷移になり、50% 交差は 0.87 x 半径 の位置")
    print("    (sqrt(1-u^2) = 0.5 -> u = 0.866)に落ちる。上面幅でも底面幅でもない。")
    wm8, wf8, wt8, wb8 = spread[("fillet", 8.0)]
    print(f"  * 丸み rf=8 px の実例: 上面幅 {wt8:.2f} / 底面幅 {wb8:.2f} / "
          f"50% 交差 {wf8:.2f}。")
    print(f"    **定義を宣言しないと {wb8 - wt8:.1f} px = {um(wb8 - wt8):.0f} um 動く。**")
    print("    サブピクセルで 0.01 px を争う前に、ここで 3 桁大きい量が動いている。")
    return spread


# --------------------------------------------------------------------------- #
# 9) 埋もれた 14 関数の実地評価                                                 #
# --------------------------------------------------------------------------- #
def section_buried_api(img):
    head(9, "★埋もれた 14 関数の実地評価(measuring1d 6 + metrology 8)")

    # ---------- measuring1d: gen_measure_arc + measure_pairs ---------- #
    sub("gen_measure_arc —— ボルト円の 6 穴を円弧キャリパーで測る")
    ms = m1.gen_measure_arc(BOLT_R, BOLT_C, BOLT_PCD, 0.0, 2 * math.pi, 1, img.shape)
    pr = m1.measure_pairs(img, ms, sigma=1.0, threshold=0.20)
    # 真値: 半径 R の弧が半径 rho の穴を切る弧長 = R * 4 * asin(rho/(2R))
    arc_true = BOLT_PCD * 4.0 * math.asin(BOLT_RAD / (2.0 * BOLT_PCD))
    print(f"  サンプル数 {len(ms['rows'])}、spacing {ms['spacing']:.6f} px")
    print(f"  真の弧長幅 {arc_true:.4f} px(直径 {2 * BOLT_RAD:.2f} px の穴を "
          f"半径 {BOLT_PCD} px の弧で切る)")
    print(f"  検出した対: {len(pr)} 個 / 期待 {BOLT_N} 個")
    wids = [p["width"] for p in pr]
    if wids:
        e = np.array(wids) - arc_true
        print(f"  {'#':>3}{'幅 [px]':>10}{'誤差 [px]':>11}{'誤差 [um]':>11}")
        for i, w in enumerate(wids):
            print(f"  {i:3d}{w:10.4f}{w - arc_true:+11.4f}{um(w - arc_true):+11.2f}")
        print(f"  -> 偏り {e.mean():+.4f} px / 散らばり {e.std():.4f} px")
        arc_bias = float(e.mean())
    else:
        arc_bias = float("nan")
    note("measuring1d", "gen_measure_arc", "OK" if len(pr) == BOLT_N else "要注意",
         "(center_row,center_col,radius,angle_start,angle_extent,width,shape) -> dict",
         f"rows=cr+R*sin(ang), cols=cc+R*cos(ang)。spacing={ms['spacing']:.4f} != 1")

    # ---------- fuzzy_measure_pairing ---------- #
    sub("fuzzy_measure_pairing —— 想定幅に近い対を選べるか")
    row = BOLT_R + BOLT_PCD * math.sin(BOLT_PHASE)
    ms2 = m1.gen_measure_rectangle2(row, 290.0, 0.0, 90, 1, img.shape)
    plain = m1.measure_pairs(img, ms2, sigma=1.0, threshold=0.20)
    fz = m1.fuzzy_measure_pairing(img, ms2, sigma=1.0, threshold=0.20,
                                  pair_size=2 * BOLT_RAD)
    print(f"  素の measure_pairs の幅: {[round(p['width'], 3) for p in plain]}")
    print(f"  pair_size={2 * BOLT_RAD} を与えたときの上位: "
          f"{[(round(p['width'], 3), round(p['fuzzy_score'], 4)) for p in fz]}")
    fz_ok = bool(fz) and abs(fz[0]["width"] - 2 * BOLT_RAD) < 1.0
    print(f"  -> 想定幅に最も近い対が先頭に来たか: {fz_ok}")
    print("     ただし ``fuzzy_measure_pairing`` は **並べ替えるだけ**で、候補を")
    print("     落とさない。HALCON 系の名前から連想する『ファジィ集合で採否を決める』")
    print("     機能ではない(スコアは exp(-((w-s)/(0.5s))^2) の 1 個だけ)。")
    note("measuring1d", "fuzzy_measure_pairing", "OK(機能は限定)",
         "measure_pairs の結果に fuzzy_score を足して降順ソート",
         "pair_size=None だとただの measure_pairs。候補の棄却はしない")

    # ---------- translate_measure ---------- #
    sub("translate_measure —— 平行移動した測定オブジェクトは直接作ったものと一致するか")
    base = m1.gen_measure_rectangle2(200.0, 320.0, 0.0, 45, 1, img.shape)
    moved = m1.translate_measure(base, 17.0, 5.4)
    direct = m1.gen_measure_rectangle2(217.0, 325.4, 0.0, 45, 1, img.shape)
    dr = float(np.max(np.abs(moved["rows"] - direct["rows"])))
    dc = float(np.max(np.abs(moved["cols"] - direct["cols"])))
    pm = m1.measure_pairs(img, moved, sigma=1.0, threshold=0.15)
    pd = m1.measure_pairs(img, direct, sigma=1.0, threshold=0.15)
    same = (len(pm) == len(pd) and all(abs(x["width"] - y["width"]) < 1e-9
                                       for x, y in zip(pm, pd)))
    print(f"  座標の最大差 row {dr:.3e} / col {dc:.3e}、測定結果が一致: {same}")
    print(f"  スロット幅(平行移動した測定線から) {pm[0]['width']:.4f} px "
          f"(真 {SLOT_W:.2f})" if pm else "  対が取れなかった")
    print("  ★ 見つけた穴: **回転が無い**。``translate_measure`` はあるが")
    print("     ``rotate_measure`` / ``transform_measure``(アフィン)が無いので、")
    print("     部品の姿勢が変わる実運用では測定線を毎回作り直すことになる。")
    note("measuring1d", "translate_measure", "OK",
         "(measure,drow,dcol) -> 新しい dict(rows/cols/origin/center を移動)",
         "回転版が無い。't'/'dir'/'angles' は書き換えないが幾何は整合する")

    # ---------- metrology: ellipse / generic / align ---------- #
    sub("add_metrology_object_ellipse_measure —— 円を楕円として測ると何が返るか")
    model = mt.create_metrology_model()
    mt.add_metrology_object_ellipse_measure(model, HOLE_R, HOLE_C, 0.0,
                                            HOLE_RAD, HOLE_RAD, n=72)
    re_ = mt.apply_metrology_model(model, img, measure_length=8.0, sigma=1.0,
                                   threshold=0.15)[0]
    pe = re_["params"]
    print(f"  ra={pe['ra']:.4f} rb={pe['rb']:.4f}(真 {HOLE_RAD:.2f} / {HOLE_RAD:.2f})、"
          f"phi={math.degrees(pe['phi']):+.2f} deg, rms={re_['rms']:.4f}")
    print(f"  中心 row {pe['row']:.4f} col {pe['col']:.4f}"
          f"(真 {HOLE_R} / {HOLE_C})")
    print("  -> 真円を楕円として測ると ra/rb はほぼ一致するが phi は不定(真円だから")
    print("     当然)。楕円の当てはめが円退化で暴れないことは確認できた。")
    ell_err = max(abs(pe["ra"] - HOLE_RAD), abs(pe["rb"] - HOLE_RAD))
    note("metrology", "add_metrology_object_ellipse_measure", "OK",
         "(model,row,col,phi,ra,rb,n=40) -> index。params: row/col/phi/ra>=rb",
         "真円入力では phi は不定(ra=rb なので意味を持たない)")

    sub("add_metrology_object_generic —— 型付きの追加関数と同じ結果になるか")
    m_g = mt.create_metrology_model()
    mt.add_metrology_object_generic(m_g, "circle", (HOLE_R, HOLE_C, HOLE_RAD), n=72)
    rg = mt.apply_metrology_model(m_g, img, measure_length=8.0, sigma=1.0,
                                  threshold=0.15)[0]
    m_t = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(m_t, HOLE_R, HOLE_C, HOLE_RAD, n=72)
    rt = mt.apply_metrology_model(m_t, img, measure_length=8.0, sigma=1.0,
                                  threshold=0.15)[0]
    gen_same = abs(rg["params"]["radius"] - rt["params"]["radius"]) < 1e-12
    print(f"  generic の半径 {rg['params']['radius']:.6f} / "
          f"typed の半径 {rt['params']['radius']:.6f} -> 一致 {gen_same}")
    bad = None
    try:
        m_b = mt.create_metrology_model()
        mt.add_metrology_object_generic(m_b, "polygon", (1, 2, 3), n=8)
        mt.apply_metrology_model(m_b, img)
    except ValueError as ex:
        bad = str(ex)
    print(f"  未知の型を渡すと: ValueError({bad!r})")
    print("  -> 追加時ではなく **apply のときに** 落ちる。モデルを組んだ時点では")
    print("     間違いに気づけない(fail-closed だが、遅い)。")
    note("metrology", "add_metrology_object_generic", "OK",
         "(model,otype,params,n=40) -> index。otype は 'line'/'circle'/'ellipse'/'rect'",
         "未知の型は add では通り apply で ValueError。検証が遅い")

    sub("align_metrology_model —— ずらしたモデルを戻せるか")
    drow, dcol = 6.4, -4.7
    m_off = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(m_off, HOLE_R - drow, HOLE_C - dcol,
                                           HOLE_RAD, n=72)
    mt.add_metrology_object_line_measure(m_off, 150.0 - drow,
                                         FACE_COL0 + math.tan(math.radians(FACE_TILT_DEG))
                                         * (150.0 - FACE_ROW0) - dcol,
                                         300.0 - drow,
                                         FACE_COL0 + math.tan(math.radians(FACE_TILT_DEG))
                                         * (300.0 - FACE_ROW0) - dcol, n=40)
    r_off = mt.apply_metrology_model(m_off, img, measure_length=8.0, sigma=1.0,
                                     threshold=0.15)
    m_al = mt.align_metrology_model(m_off, drow, dcol)
    r_al = mt.apply_metrology_model(m_al, img, measure_length=8.0, sigma=1.0,
                                    threshold=0.15)
    print(f"  {'':<10}{'円 直径':>10}{'誤差':>9}{'円 rms':>9}{'直線 rms':>10}")
    for tag, rs in (("ずらす前", r_off), ("整列後", r_al)):
        d = 2 * rs[0]["params"]["radius"] if rs[0]["params"] else float("nan")
        lr = rs[1]["rms"]
        print(f"  {tag:<10}{d:10.4f}{d - 2 * HOLE_RAD:+9.4f}{rs[0]['rms']:9.4f}"
              f"{lr:10.4f}")
    align_ok = (abs(2 * r_al[0]["params"]["radius"] - 2 * HOLE_RAD)
                < abs(2 * r_off[0]["params"]["radius"] - 2 * HOLE_RAD))
    print(f"  -> 整列で改善したか: {align_ok}")
    print("  ★ 見つけた穴: **平行移動しか無い**。``align_metrology_model(model,")
    print("     drow, dcol)`` は回転・スケールを取らないので、部品が回った場合に")
    print("     モデルを合わせ直せない(2-D 計測の実務ではここが本体)。")
    note("metrology", "align_metrology_model", "OK(平行移動のみ)",
         "(model,drow,dcol) -> 新しい model", "回転・スケールが無い。姿勢変化に追随できない")

    # ---------- 公開経路からの到達性 ---------- #
    sub("公開経路から届くか(埋もれている度合いの実測)")
    names_m1 = ["gen_measure_rectangle2", "gen_measure_arc", "measure_pos",
                "measure_pairs", "fuzzy_measure_pairing", "translate_measure"]
    names_mt = ["create_metrology_model", "add_metrology_object_line_measure",
                "add_metrology_object_circle_measure",
                "add_metrology_object_rectangle2_measure",
                "add_metrology_object_ellipse_measure",
                "add_metrology_object_generic", "align_metrology_model",
                "apply_metrology_model"]
    d_fs, d_led, d_op = set(dir(fs)), set(dir(fs.ledger)), set(dir(fs.op))
    n_reach = sum(1 for n in names_m1 + names_mt
                  if n in d_fs or n in d_led or n in d_op)
    print(f"  14 関数のうち fs. / fs.ledger / fs.op から届くもの: {n_reach} / 14")
    print(f"  一方 fs.op には別実装の m1_* が居る: "
          f"{sorted(n for n in d_op if n.startswith('m1_'))}")
    probe = bar_image(120, 40.0, 52.0, 1.5, height=32)
    v_pairs = fs.op.m1_measure_pairs(probe, a=0.0, b=0.2)
    v_pos = fs.op.m1_measure_pos(probe, a=0.0, b=0.2)
    print(f"  m1_measure_pairs(帯 1 本の画像) -> {v_pairs!r}(型 {type(v_pairs).__name__})")
    print(f"  m1_measure_pos -> keys {sorted(v_pos)} / 点数 {len(v_pos['cs'])}")
    print("  -> ★ 公開されている m1_* が返すのは **本数と点**だけで、幅も直径も")
    print("     角度も返さない。寸法検査には使えない。使えるほうが埋もれている。")
    print(f"  (既定引数のまま呼ぶと a=0.5 = 縦方向の測定線になり、横に伸びた帯には")
    print(f"   直交して 0 本になる: m1_measure_pairs(probe) = {fs.op.m1_measure_pairs(probe)!r})")

    # 台帳に残り 2 本を記録
    note("measuring1d", "measure_pairs(transition)", "穴",
         "transition 引数を受け取らない",
         "暗い特徴(穴/溝)から測り始められない。測定窓の置き方で回避するしかない")
    return arc_bias, fz_ok, same, gen_same, align_ok, ell_err, n_reach


def print_ledger():
    sub("14 関数の実地評価表")
    print(f"  {'module':<12}{'関数':<40}{'判定':<14}")
    print(f"  {'-' * 12}{'-' * 40}{'-' * 14}")
    for r in LEDGER:
        print(f"  {r['module']:<12}{r['fn']:<40}{r['status']:<14}")
        print(f"  {'':<12}規約: {r['contract']}")
        if r["remark"]:
            print(f"  {'':<12}注意: {r['remark']}")


# --------------------------------------------------------------------------- #
# 10) 所見                                                                      #
# --------------------------------------------------------------------------- #
def section_findings():
    head(10, "所見 —— 道具の穴と、足すべき op")
    print("""  (A) ``measuring1d`` / ``metrology`` は **公開経路のどこからも届かない**。
      14 関数すべてを叩いて、寸法・直径・角度が実用精度で出ることは確認した。
      「見えていなかった理由」は今回は見つからなかった —— 動く。ただし穴はある。

  (B) ★ ``measure_pairs`` に ``transition`` が無い。``measure_pos`` は
      "all"/"positive"/"negative" を取るのに、対を作る側は取らない。
      結果、暗い特徴(穴・溝)の幅を測るには測定窓の始点を部品の内側に
      置いて偏光性の並びを合わせるしかない。引数を 1 つ通すだけで直る。

  (C) ★ 回転が無い。``translate_measure`` / ``align_metrology_model`` は
      平行移動だけ。2-D 計測の実務は「基準形状を見つけてモデルを姿勢ごと
      合わせる」ことなので、ここが無いと使いどころが半分になる。
      提案: ``rotate_measure(measure, row, col, angle)`` と
      ``align_metrology_model(model, row, col, phi)``(または 2x3 行列版)。

  (D) ``fs.line_profile(image, p0, p1, num)`` は端点と点数しか取らないので、
      「間隔ちょうど 1 px」や「幅方向 n 画素の平均」ができない。
      キャリパーの本体は幅方向平均なので、ここが無いと自前で書くことになる。
      提案: ``line_profile(..., spacing=1.0, band=1)``。

  (E) 大津の閾値そのものが公開経路に無い。``fs.op.otsu`` は
      **二値マスクを返す** op であって、しきい値を返さない。
      「この画像のしきい値はいくつか」を検査レポートに書けない。
      提案: ``otsu_threshold(image) -> float``(``fs.`` 直下)。

  (F) サブピクセルのエッジ抽出が公開経路に無い。``fs.op.threshold_sub_pix`` は
      op 形式(v,a,b)で、位置のリストを画像座標で返さない。
      提案: ``subpixel_edges(image, p0, p1, sigma=1.0, threshold=0.1)``
      —— つまり ``measuring1d.measure_pos`` をそのまま出せばよい。

  (G) 足すべき op(名前と引数の案):
      * ``caliper_width(image, row, col, phi, length, band=1, sigma=1.0,
        threshold=0.1, transition='all', pair_size=None) -> list[dict]``
        1 行で幅が出る入口。今は 2 行(gen -> measure)。
      * ``fit_parallel_lines(points_a, points_b) -> dict``
        平行 2 辺の距離。今は 2 本を別々に当てはめて距離を自分で計算する。
      * ``edge_definition_report(profile, psf_sigma) -> dict``
        8 節の量(上面幅 / 底面幅 / 50% 交差)を並べて返す。面取り・丸みのある
        縁で「どの定義か」を宣言させるための道具。
      * ``measurement_uncertainty(image, measure, n=32, noise=None) -> dict``
        偏りと散らばりを分けて返す。5 節でやったことの定型化。

  (H) 測り方の規律(この PoC で数字になったもの):
      1. 縁に面取り・丸みがあるなら、**定義を宣言してから** サブピクセルを語る。
         定義の差は 8 節で 8-16 px、サブピクセルの差は 0.01-0.05 px。3 桁違う。
      2. 偏りと散らばりを分ける。平均化(length2)で下がるのは散らばりだけ。
      3. エッジ間距離 / PSF 幅 を見る。3 を切ったら幅は系統的に縮む。
      4. 測定線が斜めなら cos を掛ける。掛けても戻るのは 30 度まで。""")


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    np.random.seed(SEED)
    print("=" * 78)
    print(" 産業部品の寸法検査 —— サブピクセルのエッジ計測と、")
    print(" 埋もれていた 1-D 測定モジュール(measuring1d / metrology)の実地評価")
    print("=" * 78)
    print(f" 画像 {H} x {W} px、1 px = {PIX_UM} um、コントラスト {DG:.2f}、seed {SEED}")

    worst_gray, worst_pos = section_synth_check()

    t = time.perf_counter()
    img = render_part(1.2)
    print(f"\n  (部品画像を合成: {time.perf_counter() - t:.2f} s, "
          f"PSF sigma 1.2, 雑音なし)")

    z_rms = section_zero_point(img)
    slot_bias, circ_err, tilt_T, tilt_M = section_dimensions(img)
    edge_ratio, lost_at = section_cliff_blur()
    noise_tab = section_cliff_noise()
    ang_corr = section_cliff_angle()
    zz, mm, ff = section_cliff_illum()
    spread = section_cliff_chamfer()
    (arc_bias, fz_ok, tr_same, gen_same, align_ok,
     ell_err, n_reach) = section_buried_api(img)
    print_ledger()
    section_findings()

    # ------------------------------------------------------------------ #
    head("結", "結論(assert で固定する)")
    print(f"  合成器の忠実度            画素値 {worst_gray:.1e} / 位置 {worst_pos:.5f} px")
    print(f"  ゼロ点(大津の整数幅)    RMS {z_rms:.3f} px = {um(z_rms):.1f} um")
    print(f"  measuring1d のスロット幅  偏り {slot_bias['M']:+.4f} px "
          f"= {um(slot_bias['M']):+.2f} um")
    print(f"  metrology のスロット幅    偏り {slot_bias['T']:+.4f} px")
    print(f"  自前 50% 交差             偏り {slot_bias['F']:+.4f} px")
    print(f"  円穴の直径(metrology)   誤差 {circ_err:+.4f} px")
    print(f"  角度(metrology/M)       誤差 {tilt_T:+.4f} / {tilt_M:+.4f} deg")
    print(f"  円弧キャリパー            偏り {arc_bias:+.4f} px")
    print(f"  干渉の崖                  w/sigma <= {edge_ratio:.2f} で偏り > 0.05 px")
    print(f"  対を見失う                w = {lost_at} px (= {lost_at / 1.5:.2f} sigma)")
    print(f"  公開経路からの到達性      {n_reach} / 14 関数")

    gain = abs(z_rms / slot_bias["M"]) if slot_bias["M"] else float("inf")
    print(f"\n  -> ゼロ点比 {gain:.0f} 倍(スロット幅の偏りで比較)。")

    # --- 固定する結論 --- #
    assert worst_gray < 5e-3, f"合成器が解析式と合わない: {worst_gray}"
    assert worst_pos < 0.01, f"合成器のエッジ位置がずれる: {worst_pos}"
    assert z_rms > 0.25, f"ゼロ点が良すぎる(整数量子化が効いていない): {z_rms}"
    assert abs(slot_bias["M"]) < 0.05, \
        f"measuring1d のスロット幅の偏りが大きい: {slot_bias['M']}"
    assert abs(slot_bias["M"]) < 0.5 * abs(slot_bias["Z"]), \
        "measuring1d がゼロ点を上回っていない"
    assert abs(slot_bias["T"]) < 0.10, f"metrology の矩形が甘い: {slot_bias['T']}"
    assert abs(circ_err) < 0.10, f"円穴の直径が合わない: {circ_err}"
    assert abs(tilt_T) < 0.05 and abs(tilt_M) < 0.05, \
        f"角度が合わない: {tilt_T} / {tilt_M}"
    assert abs(arc_bias) < 0.20, f"円弧キャリパーの偏りが大きい: {arc_bias}"
    assert edge_ratio is not None and edge_ratio <= 6.0, \
        f"干渉の崖が見つからない / 早すぎる: {edge_ratio}"
    assert abs(ang_corr[0]) < 0.05 and abs(ang_corr[4]) < 0.10, \
        f"cos 補正で戻らない: {ang_corr[:5]}"
    assert abs(zz[-1]) > 3 * max(abs(mm[-1]), abs(ff[-1])), \
        "照明傾斜で大域しきい値が崩れていない(崖が再現していない)"
    wm8, wf8, wt8, wb8 = spread[("fillet", 8.0)]
    assert (wb8 - wt8) > 20 * abs(slot_bias["M"]), \
        "縁の定義の幅がサブピクセル誤差を圧倒していない"
    assert tr_same and gen_same and align_ok and fz_ok, \
        f"埋もれた API の一致性: translate {tr_same} generic {gen_same} " \
        f"align {align_ok} fuzzy {fz_ok}"
    assert ell_err < 0.10, f"楕円当てはめが円で崩れる: {ell_err}"
    assert n_reach == 0, \
        f"14 関数のいずれかが公開経路から届くようになった(この PoC の前提が変わった): {n_reach}"
    assert "measure_pairs" not in dir(fs) and "measure_pairs" not in dir(fs.ledger)
    assert "m1_measure_pairs" in dir(fs.op)

    print(f"\n  総所要 {time.perf_counter() - t0:.1f} 秒")
    print("\nPASS")
    return True


if __name__ == "__main__":
    main()
