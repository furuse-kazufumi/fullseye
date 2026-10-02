# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""金属積層造形の「工程中の熱画像」と「造形後の X 線 CT」を、既存の op だけでつなぐ。

    py -3.11 examples/poc_am_thermal_to_ct.py
    FULLSEYE_DATA_DIR=<データの置き場> py -3.11 examples/poc_am_thermal_to_ct.py   # 実データの門も足す

レーザー粉末床溶融(L-PBF)の検査は 2 つの装置に分かれています。**造形中**は高速カメラが
溶融池の明るさを撮り、**造形後**は X 線 CT が中身と表面を撮る。この PoC は、その両端を
Fullseye の既存語彙(連結成分 ``blob_label`` / ``blob_features``、3-D の ``vol_label`` /
``vol_boundary_points``、面からの符号つき距離 ``signed_surface_distance``、メッシュの断面
``mesh_slice_stack``、採点 ``seg_dice_jaccard`` / ``seg_boundary_f``)で測り、
**どの数字をどこまで言ってよいか**を門で固定します。

この PoC が測る主張(門 = 下の assert。データが無い CI では合成側だけ、有れば実データの門を足す):

1. **生信号を温度と呼ばない**。熱画像の値は 12 bit の DL(digital level)で、温度は放射率 ε を
   仮定して初めて出る。``dl_to_celsius`` は ε を**キーワード必須**にしてある(省くと TypeError)。
   4095 DL は ε=1 で約 1401 ℃、ε=0.3 で約 1641 ℃ —— 同じ画素が ε だけで 240 K 動く。
   飽和(4095)は「その温度**以上**」、0(閾値 100 DL 未満を 0 に置換済み)は「**測定なし**」で、
   冷却曲線はそこで切る(0 を式に通すと −204 ℃ という無意味な値が出る)。
   合成側では真温度が既知なので、ε を取り違えたときの誤差が**閉形式どおり**かを全画素で確かめる。
   ★ε を知らなくても言える量がある: 「ε=1 で液相線(1336 ℃)に当たる DL 以上」の領域は、
   ε ≤ 1 である限り**必ず液相線より熱い** —— 溶融池の**下限**として ε 抜きで測れる。
2. **時間軸の照合**。走査指令(XYPT)の laser-on 区間の本数と熱画像のバーストの本数が一致し、
   最後だけ長い間隔の比も一致する。それでも**周期は 2.3 % 合わない**(熱画像 30 kHz 名目 vs
   指令 10 µs/点 名目)—— 隠さず記録し、許容 3 % の門にする(原因は未解決)。
   合成側では 2.3 % のずれを**わざと注入**し、同じ道具がそれを 0.1 % 以内で検出できることを確かめる。
   画素ピッチは溶融池の先端の移動(px/コマ)と走査速度から逆算し、全条件で ±0.3 % に収まる。
3. **再現性**。同一条件 3 反復の溶融池(下限)の長さ・面積のばらつきは、出力・速度・スポット径を
   変えたときの差より小さい(条件間の標準偏差 > 3 × 反復内の標準偏差)。
4. **CT の面の荒れ**。設計形状(STL)と CT 表面の符号つき距離で、下向き面(オーバーハング)の
   はみ出し(ドロス)が上向き面より大きい。指標は「面に沿って 0.25 mm 角ごとの中央値を引いた残差の
   p95」。合成側で (a) 下向きだけにドロスを付けた形で差が出ること、(b) 向きに依らずドロスを付けた
   対照で差が出ない(比 0.8〜1.25)ことの**両向き**で確かめてから実データに当てる。
   ★最初は局所の中央値を引かず「帯全体の p95 − 中央値」で測り、下向き 328 µm / 上向き 53 µm と
   出た —— 穴の天井は場所ごとに垂れ方(形のずれ)が違い、帯の中で中央値がずれた集団を混ぜると
   その差が「はみ出し」に化ける。局所の中央値を引くと 63 µm / 32 µm(約 2 倍)に縮む。
   同じ傾き(ほぼ垂直、|n_z| 0.2〜0.37)どうしでは 1.16 倍しかなく、差の大半は天井側から来る。
   取得済みの CT(z ≈ 1.75〜4.16 mm)には水平に近い上向き面が無い。
   内部の空隙は検出下限と一緒に報告する。検出下限は合成で**実測**する(数える最小の塊 8 ボクセル
   ではなく、平滑化と部分体積で決まる 5.2 ボクセル)。実データで見つかる閉じた空気は全部表面から
   0.02 mm 以内(付着粉に閉じ込められた空気)で、内部の空隙はゼロ —— 「約 63 µm 未満は見えない」
   という意味のゼロ。
5. **断面の一致を採点**。CT の各断面マスクと設計断面を ``seg_dice_jaccard`` / ``seg_boundary_f``
   で採点する(合成側では、正しい位置合わせが 5 スライスずらした位置合わせより高得点であること)。

出典(実データを使うとき。図とキャプションにも載せる):
Source: National Institute of Standards and Technology (NIST) —
Deisenroth, Mekhontsev, Weaver, Lane (2022), AM Bench 2022 AMB2022-03 in-situ thermography and
scan strategy, doi:10.18434/mds2-2716 / Praniewicz, Lane, Kim, Saldana (2020), XCT data of AMMT
parts: Overhang Part X4, doi:10.18434/mds2-2291(**測定は Georgia Institute of Technology の
Precision Machining Research Consortium で行われた**旨がデータセット説明にある)。
2026-10-02 に部分抽出(グループ・スライスの選択のみ、画素値は無改変)し、この PoC で
しきい値処理・切り出し・疑似カラー化した(改変物)。NIST は "AS IS" で提供
(https://www.nist.gov/open/license)。

EXTEND: 自分の装置のデータに差し替えるなら、熱画像は ``(コマ, 行, 列)`` の uint16 と
校正係数 (a, b, c) を :func:`real_thermal` の代わりに渡し、CT は二値化前の 3-D 配列と
設計形状の判定関数 :func:`design_inside` を差し替えます。★放射率の真値は実データでは
分かりません —— 熱電対など別の温度計で表面温度を測って逆算するしか無く、その温度計の
不確かさが ε の不確かさになります。
"""
from __future__ import annotations

import glob
import math
import os
import sys
import time
from pathlib import Path

import numpy as np


def _repo_root() -> Path:
    """examples/ の 1 つ上(本来の置き場)。外で走らせるときは FULLSEYE_REPO を見る。"""
    here = Path(__file__).resolve().parents[1]
    if (here / "examplefig.py").is_file():
        return here
    env = os.environ.get("FULLSEYE_REPO", "").strip()
    if env and (Path(env) / "examplefig.py").is_file():
        return Path(env)
    raise SystemExit("fullseye のリポジトリが見つからない(examples/ に置くか FULLSEYE_REPO を指定)")


sys.path.insert(0, str(_repo_root()))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger

# --------------------------------------------------------------------------- #
# 定数                                                                          #
# --------------------------------------------------------------------------- #
#: 熱画像の校正係数(mds2-2716 の HDF5 属性 Calibration/ThermalCal と同じ値)。
#: 合成側も「同じ校正のカメラ」として使う。実データでは**ファイルから読み直して**一致を確かめる。
CAL = {"a": 0.9655, "b": 197.2, "c": 43920000.0}
#: 校正式の第 2 放射定数相当 [µm·K]。属性の Model 文字列 "T(x) = 14388/a/log((c*e/x+1)-b/a;" は
#: 括弧が閉じておらず e が未定義 —— ``T = 14388/(a·ln(c·e/x + 1)) − b/a``(e = 放射率)と**推定して**読む。
C2 = 14388.0
FPS = 30000.0                 # 熱画像の名目フレームレート(属性 frame_rate)
DL_SAT, DL_FLOOR = 4095, 100  # 12 bit の上限 / 0 に置換済みの閾値(属性 threshold_level)
#: In718 の液相線 [℃]。一般に知られた融解範囲 1260–1336 ℃ の上端(**この PoC の仮定**。文献から取得はしていない)。
T_LIQ = 1336.0
#: 設計形状(mds2-2291 の OverhangPart_9x5x5mm.STL と同じ寸法 mm): 9 × 5 × 5 の箱、
#: x∈[0,3] に半径 2 の横穴(軸 = x、中心 y=z=2.5)、x∈[6,9] に 45° の切り欠き(三角形 (y,z)=(1,1),(5,1),(5,5))。
BOX = (9.0, 5.0, 5.0)
HOLE_R, HOLE_C = 2.0, 2.5
#: CT の空隙として数える最小のボクセル数(= 等価直径 約 2.5 ボクセル)。これ未満は雑音と区別しない。
VOID_MIN_VOX = 8
#: 形のずれを外す局所の中央値のマスの大きさ [mm](面に沿って)。
CELL_MM = 0.25
SEED = 20261002
CREDIT = ("Source: National Institute of Standards and Technology (NIST), doi:10.18434/mds2-2716 "
          "(thermography) and doi:10.18434/mds2-2291 (XCT, measured at Georgia Tech); subsets extracted "
          "2026-10-02, thresholded/cropped/false-coloured here (modified). Provided AS IS, "
          "https://www.nist.gov/open/license")
CREDIT_JA = ("出典: 米国国立標準技術研究所(NIST)、doi:10.18434/mds2-2716(熱画像)・doi:10.18434/mds2-2291"
             "(X 線 CT、Georgia Tech で測定)。2026-10-02 に部分抽出し、しきい値処理・切り出し・疑似カラー化した(改変)。")


# =========================================================================== #
# §1 放射: DL ⇄ ℃                                                              #
# =========================================================================== #
def _check_eps(eps) -> float:
    e = float(eps)
    if not (0.0 < e <= 1.0) or not math.isfinite(e):
        raise ValueError("放射率 eps は 0 < eps <= 1(来たのは %r)" % (eps,))
    return e


def dl_to_celsius(dl, *, eps, cal=CAL):
    """DL → 放射率補正済み温度 [℃]。**eps はキーワード必須**(省くと TypeError)。

    0 以下(閾値未満を 0 に置換した画素)は「測定なし」で NaN を返す —— 式に通すと −b/a ≈ −204 ℃
    という意味の無い値になるため。飽和(4095)の画素は値を返すが、それは**下限**である
    (:func:`read_signal` が印を付ける)。
    """
    e = _check_eps(eps)
    x = np.asarray(dl, np.float64)
    out = np.full(x.shape, np.nan)
    ok = x > 0
    out[ok] = C2 / (cal["a"] * np.log(cal["c"] * e / x[ok] + 1.0)) - cal["b"] / cal["a"]
    return out


def celsius_to_dl(t_c, *, eps, cal=CAL):
    """温度 [℃] → 理想(量子化前・飽和前)の DL。:func:`dl_to_celsius` の逆関数。"""
    e = _check_eps(eps)
    t = np.asarray(t_c, np.float64)
    return cal["c"] * e / (np.exp(C2 / (cal["a"] * (t + cal["b"] / cal["a"]))) - 1.0)


def wrong_eps_closed_form(t_true, eps_true, eps_used, cal=CAL):
    """真温度 t_true・真放射率で出た DL を eps_used で読んだときの温度(閉形式)。"""
    beta = cal["b"] / cal["a"]
    k = C2 / cal["a"]
    g = (eps_used / eps_true) * (np.exp(k / (np.asarray(t_true, float) + beta)) - 1.0) + 1.0
    return k / np.log(g) - beta


def read_signal(dl, *, eps, cal=CAL):
    """DL → {温度, 下限の印(飽和), 測定なしの印(0)}。"""
    x = np.asarray(dl)
    return {"t": dl_to_celsius(x, eps=eps, cal=cal), "lower_bound": x >= DL_SAT, "no_measure": x <= 0}


def digitise(dl_ideal):
    """理想 DL → カメラが出す値(四捨五入・4095 で飽和・100 未満は 0)。"""
    q = np.clip(np.rint(dl_ideal), 0, DL_SAT)
    q[q < DL_FLOOR] = 0
    return q.astype(np.uint16)


# =========================================================================== #
# 合成の熱画像: 楕円ガウスの溶融池が行方向に動く                                    #
# =========================================================================== #
SYN_EPS = 0.35          # 合成の真の放射率
SYN_PITCH_UM = 21.3     # 合成の真の画素ピッチ
SYN_T0 = 600.0          # 溶融池の外の温度 [℃](DL にすると 100 未満 → 0)
SYN_CONDITIONS = {      # 条件 → (ΔT [K], σ_前 [px], σ_後 [px], σ_横 [px], 速度 mm/s)
    "P245 v960": (1750.0, 5.2, 14.0, 3.6, 960.0),
    "P285 v960": (2000.0, 5.6, 16.0, 3.8, 960.0),
    "P325 v960": (2250.0, 6.0, 18.0, 4.0, 960.0),
    "P285 v800": (2100.0, 5.8, 17.2, 3.9, 800.0),
    "P285 v1200": (1900.0, 5.4, 14.6, 3.7, 1200.0),
}


def synth_track(cond, rep, n_frames=260, H=560, W=56, noise_dl=6.0, ideal=False):
    """合成の 1 トラック。返り値 (frames uint16, 真値の dict)。

    温度場 T = T0 + ΔT·exp(−dr²/2σr² − dc²/2σc²)、σr は前方 σ_前 / 後方 σ_後(尾を引く)。
    反復ごとに ΔT と σ_後 を 1 % だけ揺らす(装置の再現性の代わり)。
    """
    dT, sf, sb, sc, v = SYN_CONDITIONS[cond]
    rng = np.random.default_rng(SEED + 97 * rep + int(dT))
    if rep >= 0:
        dT *= 1.0 + 0.01 * rng.standard_normal()
        sb *= 1.0 + 0.01 * rng.standard_normal()
    ppf = v / FPS / (SYN_PITCH_UM * 1e-3)                  # px / コマ
    r0 = 30.0 + 0.37 * rep                                  # 開始位置(反復ごとに少しずらす)
    c0 = W / 2.0 + 0.3
    rr = np.arange(H, dtype=float)[:, None]
    cc = np.arange(W, dtype=float)[None, :]
    frames = np.zeros((n_frames, H, W), np.uint16)
    tt = np.zeros((n_frames, H, W), np.float32) if ideal else None
    for k in range(n_frames):
        rc = r0 + k * ppf
        dr = rr - rc
        s = np.where(dr > 0, sf, sb)
        t = SYN_T0 + dT * np.exp(-0.5 * (dr / s) ** 2 - 0.5 * ((cc - c0) / sc) ** 2)
        dl = celsius_to_dl(t, eps=SYN_EPS)
        if not ideal:
            dl = dl + noise_dl * rng.standard_normal(dl.shape)
        frames[k] = digitise(dl)
        if ideal:
            tt[k] = t
    truth = {"dT": dT, "sf": sf, "sb": sb, "sc": sc, "v": v, "ppf": ppf, "r0": r0, "T": tt}
    return frames, truth


def pool_length_closed_form(truth, t_thr):
    """温度 t_thr の等温線で切った溶融池の行方向の長さ [px](閉形式)。"""
    ratio = truth["dT"] / (t_thr - SYN_T0)
    if ratio <= 1.0:
        return 0.0
    return (truth["sf"] + truth["sb"]) * math.sqrt(2.0 * math.log(ratio))


# =========================================================================== #
# 溶融池の測り方(合成と実データで同じ関数)                                          #
# =========================================================================== #
def pool_series(frames, dl_thr):
    """各コマで DL >= dl_thr の最大連結成分を測る(``blob_label`` → ``blob_select_largest`` → ``blob_features``)。

    返り値 dict: ``k``(コマ番号)、``front``(行方向の先端 = bbox の下端、行)、``length``(行の数)、
    ``area``(px)、``width``(列の数)。成分が無いコマは飛ばす。
    """
    out = {key: [] for key in ("k", "front", "length", "area", "width")}
    for k in range(frames.shape[0]):
        m = frames[k] >= dl_thr
        rows = np.nonzero(m.any(axis=1))[0]
        if rows.size == 0:
            continue
        cols = np.nonzero(m.any(axis=0))[0]
        r0, c0 = max(rows[0] - 1, 0), max(cols[0] - 1, 0)
        crop = m[r0:rows[-1] + 2, c0:cols[-1] + 2]
        big = L.blob_select_largest(L.blob_label(crop, connectivity=8), 1)
        f = L.blob_features(big)
        if f["n"] == 0:
            continue
        out["k"].append(k)
        out["front"].append(r0 + int(f["bbox_r1"][0]) - 1)
        out["length"].append(int(f["bbox_r1"][0] - f["bbox_r0"][0]))
        out["area"].append(float(f["area"][0]))
        out["width"].append(int(f["bbox_c1"][0] - f["bbox_c0"][0]))
    return {key: np.asarray(v, float) for key, v in out.items()}


def steady(ps, margin=40):
    """立ち上がりと終わりの過渡を落とした「定常」コマの選択。"""
    k = ps["k"]
    if k.size < 2 * margin + 10:
        raise ValueError("定常区間が短すぎる(%d コマ)" % k.size)
    return (k > k.min() + margin) & (k < k.max() - margin)


def pitch_from_track(ps, v_mm_s, fps=FPS):
    """先端の行位置をコマ番号に 1 次回帰 → px/コマ → 画素ピッチ [µm]。"""
    sel = steady(ps)
    slope = float(np.polyfit(ps["k"][sel], ps["front"][sel], 1)[0])
    return v_mm_s / fps / abs(slope) * 1000.0, slope


def repro_stats(table):
    """{条件: [反復の値, ...]} → (反復内の標準偏差(プール), 条件平均の標準偏差, 比)。"""
    means = np.array([np.mean(v) for v in table.values()])
    within = math.sqrt(np.mean([np.var(v, ddof=1) for v in table.values()]))
    between = float(np.std(means, ddof=1))
    return within, between, between / max(within, 1e-12)


# =========================================================================== #
# §2 時間軸: 指令の laser-on 区間と熱画像のバースト                                  #
# =========================================================================== #
def runs(on):
    """bool 列 → (開始, 終了[排他]) の配列。"""
    on = np.asarray(on, bool).astype(np.int8)
    d = np.diff(np.r_[0, on, 0])
    return np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]


def time_axis_compare(cmd_power, cmd_dt_s, sat_counts, fps=FPS):
    """指令(P > 0 の区間)と熱画像(飽和画素のあるコマの塊)を並べる。"""
    cs, ce = runs(np.asarray(cmd_power) > 0)
    ts, te = runs(np.asarray(sat_counts) > 0)
    res = {"n_cmd": len(cs), "n_thermal": len(ts)}
    if len(cs) < 3 or len(ts) < 3:
        return res
    pc = np.diff(cs).astype(float)
    pt = np.diff(ts).astype(float)
    # 周期 = 最後の 1 間隔(だけ長い)を除いた平均。熱画像はコマ単位に量子化されるので中央値でなく平均
    per_c = float(np.mean(pc[:-1])) * cmd_dt_s
    per_t = float(np.mean(pt[:-1])) / fps
    res.update({"period_cmd_s": per_c, "period_thermal_s": per_t, "mismatch": per_t / per_c - 1.0,
                "last_ratio_cmd": float(pc[-1] / np.mean(pc[:-1])), "last_ratio_thermal": float(pt[-1] / np.mean(pt[:-1])),
                "on_pts": int(np.median(ce - cs)), "burst_frames": int(np.median(te - ts)),
                "periods_thermal": pt, "periods_cmd": pc})
    return res


def synth_time_axis(mismatch=0.023):
    """24 本のハッチ(522 点 on / 周期 1047 点、最後だけ 1361 点)の指令と、時計が mismatch だけ
    ずれたカメラの飽和画素数の列を作る。"""
    dt = 10e-6
    starts = [0]
    for i in range(23):
        starts.append(starts[-1] + (1361 if i == 22 else 1047))
    n = starts[-1] + 522 + 500
    p = np.zeros(n)
    for s in starts:
        p[s:s + 522] = 285.0
    # カメラ: 実際のコマ間隔 = 1/(FPS·(1+mismatch))(名目 30 kHz より速い時計 = 1 周期に入るコマが多い)
    t_on = [(s * dt, (s + 522) * dt) for s in starts]
    nf = int(n * dt * FPS * (1 + mismatch)) + 10
    tk = np.arange(nf) / (FPS * (1 + mismatch))
    sat = np.zeros(nf, int)
    for a, b in t_on:
        sat[(tk >= a + 3e-5) & (tk < b + 2.2e-4)] = 150          # 立ち上がりの遅れ・冷えるまでの尾
    return p, dt, sat


# =========================================================================== #
# §4 設計形状と CT                                                              #
# =========================================================================== #
def design_inside(z, y, x):
    """設計形状の内側か(mm)。箱 − 横穴(x<3)− 45° の切り欠き(x>6, z>=1, z<=y)。"""
    inbox = (x >= 0) & (x <= BOX[0]) & (y >= 0) & (y <= BOX[1]) & (z >= 0) & (z <= BOX[2])
    hole = (x < 3.0) & ((y - HOLE_C) ** 2 + (z - HOLE_C) ** 2 < HOLE_R ** 2)
    notch = (x > 6.0) & (z >= 1.0) & (z <= y)
    return inbox & ~hole & ~notch


def design_surface(zlo, zhi, h=0.008):
    """設計面の標本点・外向き法線・面の種類(0 穴 / 1 斜面 / 2 側壁)。各面は辺から 0.1 mm 内側だけ。"""
    pts, nrm, cat = [], [], []
    xs = np.arange(0.1, 2.9, h)
    th = np.arange(0.0, 2 * np.pi, h / HOLE_R)
    X, TH = np.meshgrid(xs, th, indexing="ij")
    P = np.c_[X.ravel(), HOLE_C + HOLE_R * np.cos(TH.ravel()), HOLE_C + HOLE_R * np.sin(TH.ravel())]
    N = np.c_[np.zeros(P.shape[0]), -np.cos(TH.ravel()), -np.sin(TH.ravel())]  # 材料の外 = 穴の中心向き
    pts.append(P); nrm.append(N); cat.append(np.zeros(P.shape[0]))
    X, T = np.meshgrid(np.arange(6.1, 8.9, h), np.arange(1.1, 4.9, h), indexing="ij")
    P = np.c_[X.ravel(), T.ravel(), T.ravel()]
    pts.append(P); nrm.append(np.tile([0.0, 1 / math.sqrt(2), -1 / math.sqrt(2)], (P.shape[0], 1)))
    cat.append(np.ones(P.shape[0]))
    for y0, xmax, ny in ((0.0, 8.9, -1.0), (5.0, 5.9, 1.0)):
        X, Z = np.meshgrid(np.arange(0.1, xmax, h), np.arange(max(zlo - 0.1, 0.1), min(zhi + 0.1, 4.9), h), indexing="ij")
        P = np.c_[X.ravel(), np.full(X.size, y0), Z.ravel()]
        pts.append(P); nrm.append(np.tile([0.0, ny, 0.0], (P.shape[0], 1))); cat.append(np.full(P.shape[0], 2.0))
    P, N, C = np.vstack(pts), np.vstack(nrm), np.concatenate(cat)
    keep = (P[:, 2] > zlo - 0.15) & (P[:, 2] < zhi + 0.15)
    return P[keep], N[keep], C[keep]


def ct_to_mm(k, r, c, reg):
    """CT の (スライス, 行, 列) → 設計座標 (x, y, z) [mm]。"""
    p = reg["p"]
    return np.c_[(np.asarray(c) - reg["c0"]) * p, (reg["r0"] - np.asarray(r)) * p, (np.asarray(k) - reg["s0"]) * p]


def design_masks(shape, reg, ks):
    """CT の格子での設計断面(bool)を指定スライスについて。"""
    H, W = shape[1:]
    X, Y = np.meshgrid((np.arange(W) - reg["c0"]) * reg["p"], (reg["r0"] - np.arange(H)) * reg["p"])
    return [design_inside((k - reg["s0"]) * reg["p"], Y, X) for k in ks]


def _dice_reg(mask, reg, ks, step=1):
    H, W = mask.shape[1:]
    X, Y = np.meshgrid((np.arange(0, W, step) - reg["c0"]) * reg["p"], (reg["r0"] - np.arange(0, H, step)) * reg["p"])
    inter = tot = 0
    for k in ks:
        d = design_inside((k - reg["s0"]) * reg["p"], Y, X)
        m = mask[k, ::step, ::step]
        inter += int((d & m).sum())
        tot += int(d.sum() + m.sum())
    return 2.0 * inter / max(tot, 1)


def register_ct(mask, k_offset=0):
    """二値の CT を設計形状に合わせる: 外形の bbox で x・y の原点とピッチ、Dice の探索で z の原点。

    向きは (x = +列, y = −行, z = +スライス) を既定とし、残り 3 通りの反転も Dice で比べて報告する
    (反転の判定は 9 × 5 の外形ではなく、穴と切り欠きの位置で決まる)。``k_offset`` は配列の 0 番が
    元のスライス番号の何番か(実データは 121 番から)。
    """
    cols = np.nonzero(mask.mean(axis=(0, 1)) > 0.2)[0]
    rows = np.nonzero(mask.mean(axis=(0, 2)) > 0.2)[0]
    px = BOX[0] / (cols[-1] - cols[0] + 1)
    py = BOX[1] / (rows[-1] - rows[0] + 1)
    p = 0.5 * (px + py)
    ks = np.arange(0, mask.shape[0], max(mask.shape[0] // 25, 1))
    base = {"c0": cols[0] - 0.5, "r0": rows[-1] + 0.5, "p": p}
    best = (-1.0, None)
    for s_start in np.arange(-0.3 / p, 3.5 / p, 3.0):   # z(配列 0 番) を 0.3〜3.5 mm で粗く探す
        reg = dict(base, s0=-s_start)
        v = _dice_reg(mask, reg, ks, step=2)
        if v > best[0]:
            best = (v, reg)
    reg = dict(best[1])
    score = _dice_reg(mask, reg, ks)
    for _ in range(3):
        for key, steps in (("s0", (-2, -1, -0.5, 0.5, 1, 2)), ("c0", (-1, -0.5, 0.5, 1)), ("r0", (-1, -0.5, 0.5, 1))):
            for st in steps:
                q = dict(reg)
                q[key] += st
                v = _dice_reg(mask, q, ks)
                if v > score:
                    score, reg = v, q
    # 向きの別解(x 反転・y 反転)を同じ探索幅で比べる: 鏡映が勝たないことを確かめる
    flips = {}
    for name, fx, fy in (("x 反転", True, False), ("y 反転", False, True), ("両方反転", True, True)):
        m2 = mask[:, ::-1 if fy else 1, ::-1 if fx else 1]
        b2 = -1.0
        for s_start in np.arange(-0.3 / p, 3.5 / p, 3.0):
            b2 = max(b2, _dice_reg(m2, dict(base, s0=-s_start), ks, step=2))
        flips[name] = b2
    reg["dice"] = score
    reg["flips"] = flips
    reg["s0_orig"] = reg["s0"] - k_offset          # 元の番号で書いた z 原点
    reg["z_range"] = ((0 - reg["s0"]) * p, (mask.shape[0] - 1 - reg["s0"]) * p)
    reg["z_sens"] = {ds: _dice_reg(mask, dict(reg, s0=reg["s0"] + ds), ks) for ds in (-5, 5)}
    return reg


def binarise_ct(vol):
    """CT の灰色値 → 材料マスク: ``vol_gaussian``(σ=1 ボクセル)→ 大津(``sk_otsu``、全体で 1 つの閾値)。"""
    g = fs.apply(np.asarray(vol, np.float32), "vol_gaussian", a=(1.0 - 0.3) / 2.7)
    m = fs.apply(g.reshape(-1, g.shape[2]), "sk_otsu").reshape(g.shape) > 0.5
    return m, g


def find_voids(mask, reg):
    """外に通じない空気の成分(``vol_label``、6 近傍)= 空隙。VOID_MIN_VOX 未満は数えない。"""
    air = ~mask
    lab = L.vol_label(air.astype(np.uint8), connectivity=6)
    border = np.zeros(mask.shape, bool)
    border[[0, -1]] = True
    border[:, [0, -1]] = True
    border[:, :, [0, -1]] = True
    ext = set(np.unique(lab[border & air]).tolist())
    sizes = np.bincount(lab.ravel())
    internal = [i for i in range(1, sizes.size) if i not in ext and sizes[i] > 0]
    small = sum(1 for i in internal if sizes[i] < VOID_MIN_VOX)
    voids = []
    if internal:
        keep = [i for i in internal if sizes[i] >= VOID_MIN_VOX]
        if keep:
            sel = np.where(np.isin(lab, keep), lab, 0)
            props = L.vol_region_props(sel)
            for pr in props:
                if pr["label"] not in keep:
                    continue
                z, y, x = pr["centroid"]
                n = int(pr["voxel_count"])
                voids.append({"label": int(pr["label"]), "voxels": n,
                              "eq_diam_mm": (6.0 * n / math.pi) ** (1 / 3) * reg["p"],
                              "xyz": ct_to_mm([z], [y], [x], reg)[0]})
    return voids, small


def surface_deviation(mask, reg, zpad=0.05, max_d=0.5, stride=1):
    """CT 表面(``vol_boundary_points``)→ 設計面への符号つき距離(``signed_surface_distance``、外向き正)。

    面の種類と法線の z 成分は、最寄りの設計面標本から取る。x の境目(0,3,6,9 mm の ±0.15)と
    スタックの上下端(±zpad)は面の種類が曖昧なので落とす。
    """
    from scipy.spatial import cKDTree

    pts = L.vol_boundary_points(mask.astype(np.uint8), spacing=(1.0, 1.0, 1.0), connectivity=6)
    if stride > 1:
        pts = pts[::stride]
    Q = ct_to_mm(pts[:, 0], pts[:, 1], pts[:, 2], reg)
    zlo, zhi = reg["z_range"]
    xm = np.min(np.abs(Q[:, 0][:, None] - np.array([0.0, 3.0, 6.0, 9.0])[None, :]), axis=1)
    keep = (Q[:, 2] > zlo + zpad) & (Q[:, 2] < zhi - zpad) & (xm > 0.15)
    Q = Q[keep]
    S, N, C = design_surface(zlo, zhi)
    dd, ii = cKDTree(S).query(Q, k=1)
    ok = dd < max_d
    Q, ii = Q[ok], ii[ok]
    d = L.signed_surface_distance(Q, S, surface_normals=N, k=1)
    d = np.asarray(d)
    Sn, cat = S[ii], C[ii]
    # 形のずれ(穴が全体に小さい・天井が垂れる等)を局所の中央値で外す: 面に沿って 0.25 mm 角のマスごと
    u = np.where(cat == 0, np.arctan2(Sn[:, 2] - HOLE_C, Sn[:, 1] - HOLE_C) * HOLE_R,
                 np.where(cat == 1, Sn[:, 1] * math.sqrt(2.0), Sn[:, 2]))
    key = (cat.astype(np.int64) * 10 ** 8 + np.floor(Sn[:, 0] / CELL_MM).astype(np.int64) * 10 ** 4
           + np.floor((u + 50.0) / CELL_MM).astype(np.int64))
    r = d - group_median(key, d)
    return {"d": d, "r": r, "nz": N[ii, 2], "cat": cat, "q": Q, "s": Sn}


def group_median(key, val):
    """同じ key の値の中央値を各要素に配る(並べ替え 1 回)。"""
    order = np.lexsort((val, key))
    k, v = key[order], val[order]
    starts = np.r_[0, np.nonzero(np.diff(k))[0] + 1]
    ends = np.r_[starts[1:], k.size]
    med = 0.5 * (v[(starts + ends - 1) // 2] + v[(starts + ends) // 2])
    out = np.empty_like(val)
    out[order] = np.repeat(med, ends - starts)
    return out


def protrusion(d):
    """はみ出しの指標 = 上側の裾 p95 − 中央値 [mm]。``d`` には局所の中央値を引いた残差(``dev["r"]``)を渡す。"""
    d = np.asarray(d)
    return float(np.percentile(d, 95) - np.median(d)) if d.size >= 50 else float("nan")


def facing_bands(dev):
    """面の向きで分けた指標。"""
    nz, cat, d, r = dev["nz"], dev["cat"], dev["d"], dev["r"]
    bands = {
        "up (hole, n_z >= +0.2)": (cat == 0) & (nz >= 0.2),
        "down (hole, n_z <= -0.2)": (cat == 0) & (nz <= -0.2),
        "hole crown (n_z <= -0.7)": (cat == 0) & (nz <= -0.7),
        "up, same angle (+0.2..+0.37)": (cat == 0) & (nz >= 0.2) & (nz <= 0.37),
        "down, same angle (-0.37..-0.2)": (cat == 0) & (nz <= -0.2) & (nz >= -0.37),
        "45 deg overhang (notch)": cat == 1,
        "vertical walls": cat == 2,
    }
    return {k: {"n": int(m.sum()), "prot": protrusion(r[m]), "median": float(np.median(d[m])) if m.any() else float("nan")}
            for k, m in bands.items()}


def synth_ct(dross_where="down", p=0.025, zlim=(1.7, 4.2), noise=1500.0):
    """設計形状 + 粗さ + ドロス(付着粒)+ 既知の空隙を入れた合成 CT(灰色値)。

    dross_where = "down"(下向き面 n_z <= -0.3 だけ)/ "all"(向きに依らず同じ密度 = 対照)。
    返り値 (vol, 真値 dict)。座標の向きは実データと同じ(列 = +x、行 = −y、スライス = +z)。
    """
    rng = np.random.default_rng(SEED + (1 if dross_where == "all" else 0))
    pad = 8
    W = int(round(BOX[0] / p)) + 2 * pad
    H = int(round(BOX[1] / p)) + 2 * pad
    nz = int(round((zlim[1] - zlim[0]) / p))
    c0, r0, s0 = pad - 0.5, H - pad - 0.5, -zlim[0] / p
    reg = {"c0": c0, "r0": r0, "s0": s0, "p": p}
    x = (np.arange(W) - c0) * p
    y = (r0 - np.arange(H)) * p
    z = (np.arange(nz) - s0) * p
    Z, Y, X = np.meshgrid(z, y, x, indexing="ij")
    # 粗さ: 滑らかな乱数場で面を前後に揺らす(相関長 0.06 mm、振幅 10 µm)
    from scipy import ndimage

    g = ndimage.gaussian_filter(rng.standard_normal(Z.shape).astype(np.float32), 0.06 / p / 2)
    g /= g.std()
    sh = 0.010 * g
    mat = design_inside(Z, Y + sh, X + sh)          # 面の位置を揺らす(全向き同じ振幅)
    # ドロス: 面の外側にほぼ乗っているだけの付着粉の塊(半径 30〜60 µm、中心は面から 0.9 r 外)
    S, N, _ = design_surface(zlim[0] + 0.1, zlim[1] - 0.1, h=0.02)
    if dross_where == "down":
        cand = np.nonzero(N[:, 2] <= -0.2)[0]
    elif dross_where == "none":
        cand = np.arange(0)
    else:
        cand = np.arange(S.shape[0])
    area_per = 0.02 * 0.02
    n_part = int(rng.poisson(len(cand) * area_per * 40.0))   # 40 塊 / mm²(半径 30〜60 µm の付着粉の塊)
    pick = rng.choice(cand, size=min(n_part, len(cand)), replace=False)
    for i in pick:
        r = rng.uniform(0.030, 0.060)
        c = S[i] + N[i] * r * 0.9
        ix = slice(max(int((c[0] - r) / p + c0), 0), int((c[0] + r) / p + c0) + 2)
        iy = slice(max(int(r0 - (c[1] + r) / p), 0), int(r0 - (c[1] - r) / p) + 2)
        iz = slice(max(int((c[2] - r) / p + s0), 0), int((c[2] + r) / p + s0) + 2)
        sub = (X[iz, iy, ix] - c[0]) ** 2 + (Y[iz, iy, ix] - c[1]) ** 2 + (Z[iz, iy, ix] - c[2]) ** 2 <= r * r
        mat[iz, iy, ix] |= sub
    # 既知の空隙(中実の区間 x∈[3,6] の中)。直径 20〜170 µm を並べて、検出下限を**実測**する
    radii = [0.010, 0.020, 0.030, 0.040, 0.050, 0.065, 0.085]
    centres = []
    for j, r in enumerate(radii):
        c = np.array([3.4 + 0.37 * j, 0.9 + 0.5 * j, zlim[0] + 0.4 + 0.25 * j])
        centres.append(c)
        mat &= ~((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2 <= r * r)
    vol = np.where(mat, 35400.0, 26600.0).astype(np.float32)
    vol = ndimage.gaussian_filter(vol, 0.8) + noise * rng.standard_normal(vol.shape).astype(np.float32)
    truth = {"reg": reg, "voids": list(zip(radii, centres)), "n_dross": len(pick), "dross_where": dross_where}
    return vol, truth


# =========================================================================== #
# 実データ                                                                      #
# =========================================================================== #
def find_data():
    """FULLSEYE_DATA_DIR/nist_ammt を探す。足りなければ理由を印字して None。"""
    root = os.environ.get("FULLSEYE_DATA_DIR", "").strip()
    if not root:
        print("[data] FULLSEYE_DATA_DIR が未設定 → 合成データの門だけ走らせる")
        return None
    d = Path(root) / "nist_ammt"
    need = {
        "thermo": d / "thermography" / "AMB2022-03-718-AMMT-StaringCamera_Signal_SUBSET.h5",
        "xypt": d / "thermography" / "AMB2022-03-AMMT-718-Pad_XYPT.h5",
        "stl": d / "ct" / "OverhangPart_9x5x5mm.STL",
    }
    missing = [str(p) for p in need.values() if not p.is_file()]
    tifs = sorted(glob.glob(str(d / "ct" / "Part1_Cropped" / "*" / "*Cropped0*.tif")))
    if len(tifs) < 20:
        missing.append(str(d / "ct" / "Part1_Cropped" / "*" / "*.tif"))
    try:
        import h5py  # noqa: F401
        import tifffile  # noqa: F401
    except ImportError as exc:
        missing.append("python package: %s" % exc.name)
    if missing:
        print("[data] %s に足りないもの → 合成データの門だけ: %s" % (d, "; ".join(missing)))
        return None
    need["tifs"] = tifs
    need["root"] = d
    return need


def ct_contiguous_run(tifs):
    """番号が連続した最長の区間(端の確認用の 1 枚・440 枚目を除く)。"""
    nums = [int(Path(t).stem[-4:]) for t in tifs]
    best, cur = (0, 0), (0, 0)
    for i in range(1, len(nums) + 1):
        if i == len(nums) or nums[i] != nums[i - 1] + 1:
            if i - cur[0] > best[1] - best[0]:
                best = (cur[0], i)
            cur = (i, i)
    return [tifs[i] for i in range(*best)], nums[best[0]]


# =========================================================================== #
# 図                                                                            #
# =========================================================================== #
def dl_frame_rgb(frame):
    """DL のコマ → 疑似カラー。0(測定なし)は濃紺、4095(飽和 = 下限)はマゼンタで別に塗る。"""
    f = np.asarray(frame, float)
    rgb = np.asarray(fs.colorize_depth(np.clip((f - DL_FLOOR) / (DL_SAT - DL_FLOOR), 0, 1), vmin=0.0, vmax=1.0), float)[..., :3]
    rgb[f <= 0] = (0.03, 0.03, 0.18)
    rgb[f >= DL_SAT] = (1.0, 0.0, 1.0)
    return rgb


def ct_slice_rgb(gray, design, lo=24000.0, hi=38000.0):
    g = np.clip((np.asarray(gray, float) - lo) / (hi - lo), 0, 1)
    rgb = np.repeat(g[..., None], 3, axis=2)
    edge = design ^ np.roll(design, 1, 0) | design ^ np.roll(design, 1, 1)
    rgb[edge] = (1.0, 0.15, 0.1)
    return rgb


# =========================================================================== #
# 本体                                                                          #
# =========================================================================== #
def section_radiometry(rows):
    print("\n== 1. 生信号を温度と呼ばない ==")
    try:
        dl_to_celsius(4095)                                   # type: ignore[call-arg]
        raised = False
    except TypeError:
        raised = True
    assert raised, "eps を省いたのに dl_to_celsius が通った"
    t1 = float(dl_to_celsius(4095, eps=1.0))
    t03 = float(dl_to_celsius(4095, eps=0.3))
    floor1 = float(dl_to_celsius(DL_FLOOR, eps=1.0))
    with np.errstate(divide="ignore"):
        naive_zero = float(C2 / (CAL["a"] * np.log(CAL["c"] * 1.0 / np.float64(0.0) + 1.0)) - CAL["b"] / CAL["a"])
    dl_liq1 = float(celsius_to_dl(T_LIQ, eps=1.0))
    print("eps を省くと TypeError(門)。4095 DL = %.1f ℃(ε=1)/ %.1f ℃(ε=0.3)、差 %.1f K。100 DL = %.1f ℃(ε=1)"
          % (t1, t03, t03 - t1, floor1))
    print("0 DL を式に通すと %.1f ℃ に張り付く(→ NaN = 測定なしとして返す)。液相線 %.0f ℃ は ε=1 で %.0f DL"
          % (naive_zero, T_LIQ, dl_liq1))
    assert abs(t1 - 1401.5) < 0.2 and abs(t03 - 1640.8) < 0.2, (t1, t03)
    assert np.isnan(dl_to_celsius(0, eps=0.5))
    # 合成: 真温度が既知のトラックで ε を取り違えた誤差を閉形式と比べる
    frames, tr = synth_track("P285 v960", rep=-1, ideal=True, n_frames=120)
    T = tr["T"]
    valid = (frames > 0) & (frames < DL_SAT)
    worst = {}
    for e_used in (1.0, 0.6, SYN_EPS, 0.25):
        got = dl_to_celsius(frames[valid], eps=e_used)
        cf = wrong_eps_closed_form(T[valid], SYN_EPS, e_used)
        # 量子化(±0.5 DL)ぶんの温度幅を画素ごとに出して、それで割った最大値が 1 以下なら閉形式どおり
        slope = np.abs(dl_to_celsius(frames[valid] + 0.5, eps=e_used) - dl_to_celsius(frames[valid] - 0.5, eps=e_used))
        ratio = float(np.max(np.abs(got - cf) / np.maximum(slope, 1e-9)))
        bias = float(np.median(got - T[valid]))
        worst[e_used] = (ratio, bias)
        print("  合成 ε_真=%.2f を ε=%.2f で読む: 真値との差の中央値 %+7.1f K、閉形式との差 / 量子化幅 の最大 %.3f"
              % (SYN_EPS, e_used, bias, ratio))
        assert ratio <= 1.0 + 1e-6, (e_used, ratio)
    assert abs(worst[SYN_EPS][1]) < 1.0 and worst[1.0][1] < -100.0 and worst[0.25][1] > 30.0, worst
    sat = frames >= DL_SAT
    lb = float(dl_to_celsius(DL_SAT - 0.5, eps=SYN_EPS))      # 四捨五入で 4095 になる最小の理想 DL
    print("  合成: 飽和 %d 画素は全部 真温度 >= 下限 %.1f ℃(最大 %.0f ℃ = 下限より %.0f K 上)"
          % (int(sat.sum()), lb, float(T[sat].max()), float(T[sat].max()) - lb))
    assert np.all(T[sat] >= lb - 1e-3)
    zero = frames == 0
    lim0 = float(dl_to_celsius(DL_FLOOR - 0.5, eps=SYN_EPS))
    assert np.all(T[zero] < lim0 + 1e-3)
    # ε 抜きの下限: DL >= dl_liq1 の画素は ε<=1 なら液相線以上
    lbpool = frames >= dl_liq1
    t_lb = float(dl_to_celsius(dl_liq1, eps=SYN_EPS))
    assert np.all(T[lbpool] >= T_LIQ), "下限の溶融池に液相線より冷たい画素がある"
    print("  合成: 「ε=1 で液相線に当たる DL 以上」の %d 画素は全部 真温度 >= %.0f ℃(ε=%.2f なら実は %.0f ℃ 以上の領域)"
          % (int(lbpool.sum()), T_LIQ, SYN_EPS, t_lb))
    rows.append(("4095 DL at eps=1 / 0.3", "%.1f / %.1f C" % (t1, t03), "eps is a required argument"))
    rows.append(("eps-free lower bound of the melt pool", ">= %.0f DL" % dl_liq1, "liquidus %.0f C at eps=1" % T_LIQ))
    return {"t1": t1, "t03": t03, "dl_liq1": dl_liq1, "naive_zero": naive_zero, "worst": worst}


def section_synthetic_pool(rows, dl_liq1):
    print("\n== 2・3(合成). 画素ピッチと再現性 —— 真値の分かる溶融池で道具を確かめる ==")
    lengths, areas, pitches, cf_err = {}, {}, {}, []
    t_lb = float(dl_to_celsius(dl_liq1, eps=SYN_EPS))
    for cond in SYN_CONDITIONS:
        for rep in range(3):
            frames, tr = synth_track(cond, rep)
            ps = pool_series(frames, dl_liq1)
            sel = steady(ps)
            pitch, slope = pitch_from_track(ps, tr["v"])
            pitches.setdefault(cond, []).append(pitch)
            lengths.setdefault(cond, []).append(float(ps["length"][sel].mean()))
            areas.setdefault(cond, []).append(float(ps["area"][sel].mean()))
            lcf = pool_length_closed_form(tr, t_lb)
            cf_err.append(lengths[cond][-1] - lcf)
            assert abs(cf_err[-1]) < 0.6, (cond, rep, lengths[cond][-1], lcf)
        print("  %-11s 長さ %s px(閉形式との差 %s)、ピッチ %s µm(真 %.1f)"
              % (cond, " / ".join("%.2f" % v for v in lengths[cond]), " / ".join("%+.2f" % v for v in cf_err[-3:]),
                 " / ".join("%.3f" % v for v in pitches[cond]), SYN_PITCH_UM))
    allp = np.concatenate([np.asarray(v) for v in pitches.values()])
    dev = float(np.max(np.abs(allp / SYN_PITCH_UM - 1.0)))
    assert dev < 0.003, dev
    rep_conds = [c for c in SYN_CONDITIONS if c.endswith("v960")]
    wl, bl, rl = repro_stats({c: lengths[c] for c in rep_conds})
    wa, ba, ra = repro_stats({c: areas[c] for c in rep_conds})
    print("  ピッチは真値から最大 %.2f %% 。出力 3 条件 × 3 反復: 長さ 反復内 %.2f px / 条件間 %.2f px(%.0f 倍)、"
          "面積 %.1f / %.1f px²(%.0f 倍)" % (100 * dev, wl, bl, rl, wa, ba, ra))
    assert rl > 3.0 and ra > 3.0, (rl, ra)
    rows.append(("synthetic: pitch from pool front", "max %.2f %% off" % (100 * dev), "< 0.3 %"))
    rows.append(("synthetic: pool length vs closed form", "max %.2f px" % max(abs(e) for e in cf_err), "< 0.6 px"))
    rows.append(("synthetic: between/within SD, length / area", "%.0f x / %.0f x" % (rl, ra), "> 3"))
    return {"pitch_dev": dev, "repro_len": rl, "repro_area": ra}


def section_synthetic_time(rows):
    print("\n== 2(合成). 時間軸 —— 2.3 % のずれを注入して、同じ道具で読めるか ==")
    p, dt, sat = synth_time_axis(0.023)
    r = time_axis_compare(p, dt, sat)
    print("  指令 %d 本 / 熱画像 %d 本、周期のずれ %+.2f %%(注入 +2.30 %%)、最後の間隔の比 %.3f / %.3f"
          % (r["n_cmd"], r["n_thermal"], 100 * r["mismatch"], r["last_ratio_cmd"], r["last_ratio_thermal"]))
    assert r["n_cmd"] == r["n_thermal"] == 24
    assert abs(r["mismatch"] - 0.023) < 0.001, r["mismatch"]
    pz, dtz, satz = synth_time_axis(0.0)
    r0 = time_axis_compare(pz, dtz, satz)
    assert abs(r0["mismatch"]) < 0.001, r0["mismatch"]
    print("  対照(ずれ 0 を注入): 読みは %+.2f %%" % (100 * r0["mismatch"]))
    rows.append(("synthetic: injected 2.3 % clock mismatch", "%+.2f %%" % (100 * r["mismatch"]), "reads back within 0.1 %"))
    return r


def section_synthetic_ct(rows):
    print("\n== 4・5(合成). CT —— 下向き面だけにドロスを付けた形と、向きに依らず付けた対照 ==")
    out = {}
    for where in ("down", "all"):
        vol, tr = synth_ct(where)
        mask, _ = binarise_ct(vol)
        reg = register_ct(mask)
        t = tr["reg"]
        err = (abs(reg["c0"] - t["c0"]), abs(reg["r0"] - t["r0"]), abs(reg["s0"] - t["s0"]))
        dev = surface_deviation(mask, reg)
        bands = facing_bands(dev)
        up, down = bands["up (hole, n_z >= +0.2)"]["prot"], bands["down (hole, n_z <= -0.2)"]["prot"]
        out[where] = {"reg": reg, "err": err, "bands": bands, "ratio": down / up, "mask": mask, "vol": vol, "truth": tr, "dev": dev}
        print("  ドロス=%-4s 粒 %4d、位置合わせ Dice %.4f(真の原点との差 列 %.1f / 行 %.1f / スライス %.1f ボクセル)、"
              "はみ出し 下向き %.1f µm / 上向き %.1f µm(比 %.2f)"
              % (where, tr["n_dross"], reg["dice"], err[0], err[1], err[2], 1e3 * down, 1e3 * up, down / up))
        assert max(err) <= 1.5, err
    assert out["down"]["ratio"] > 1.5, out["down"]["ratio"]
    assert 0.8 < out["all"]["ratio"] < 1.25, out["all"]["ratio"]
    # 空隙: 検出下限より大きい 5 個は見つかり、半径 10 µm の 1 個は見つからない(下限として報告)
    s = out["down"]
    voids, small = find_voids(s["mask"], s["reg"])
    truth = s["truth"]["voids"]
    p = s["reg"]["p"]
    found = []
    for r, c in truth:
        near = [v for v in voids if np.linalg.norm(v["xyz"] - c) < max(2 * r, 3 * p)]
        found.append((r, near[0]["eq_diam_mm"] if near else None))
    det = [f for f in found if f[1] is not None]
    hit = [f[1] is not None for f in found]
    first = hit.index(True) if any(hit) else len(hit)
    lim_d = 2 * found[first][0] if first < len(found) else float("nan")
    print("  空隙: 真値 %d 個(直径 %s µm)→ 検出 %d 個。数える最小の塊 %d ボクセル(直径 %.0f µm 相当)、"
          "それ未満の内部の空気 %d 塊" % (len(truth), "/".join("%.0f" % (2e3 * r) for r, _ in truth), len(voids),
                                         VOID_MIN_VOX, 1e3 * (6 * VOID_MIN_VOX / math.pi) ** (1 / 3) * p, small))
    for r, dfound in found:
        print("    真の直径 %5.0f µm → %s" % (2e3 * r, "検出 %.0f µm(差 %+.1f ボクセル)" % (1e3 * dfound, (dfound - 2 * r) / p)
                                             if dfound else "検出されない"))
    print("  → **実測の検出下限は直径 %.0f µm = %.1f ボクセル**(平滑化 σ=1 と部分体積で小さな空隙は消える。"
          "数える最小の塊の規則 %.1f ボクセルより大きい)" % (1e3 * lim_d, lim_d / p, (6 * VOID_MIN_VOX / math.pi) ** (1 / 3)))
    assert all(hit[first:]) and not any(hit[:first]), found          # 一度見えたら、それより大きいものは全部見える
    assert first < len(found) and lim_d / p <= 6.0, (found, lim_d)
    assert all(abs(f[1] - 2 * f[0]) < 2.0 * p for f in found[first:]), found
    assert len(voids) == sum(hit), (len(voids), hit)                # 余計な空隙(雑音の誤検出)が無い
    # §5 採点: 正しい位置合わせ vs 5 スライスずらした位置合わせ
    sc = seg_scores(s["mask"], s["reg"])
    sc_bad = seg_scores(s["mask"], dict(s["reg"], s0=s["reg"]["s0"] + 5))
    print("  断面の採点(合成): Dice %.4f / 境界 F(τ=2 px)%.3f、5 スライスずらすと Dice %.4f / F %.3f"
          % (sc["dice"], sc["bf"], sc_bad["dice"], sc_bad["bf"]))
    assert sc["dice"] > sc_bad["dice"] and sc["bf"] > sc_bad["bf"] + 0.02, (sc, sc_bad)
    rows.append(("synth CT: Dice / boundary F, right vs 5 slices off",
                 "%.3f/%.2f vs %.3f/%.2f" % (sc["dice"], sc["bf"], sc_bad["dice"], sc_bad["bf"]), "right scores higher"))
    rows.append(("synth CT: protrusion down/up, dross only down", "%.2f" % out["down"]["ratio"], "> 1.5"))
    rows.append(("synth CT: same, dross everywhere (control)", "%.2f" % out["all"]["ratio"], "0.8 .. 1.25"))
    rows.append(("synth CT: voids found / detection limit", "%d of %d / %.1f vox" % (len(voids), len(truth), lim_d / p),
                 "no false voids, limit <= 6 vox"))
    out["voids"] = (voids, small, found)
    out["void_limit_vox"] = lim_d / p
    out["seg"] = (sc, sc_bad)
    return out


def seg_scores(mask, reg, n=10, tau=2.0):
    """断面ごとの Dice と境界 F(``seg_dice_jaccard`` / ``seg_boundary_f``)の平均。"""
    ks = np.linspace(2, mask.shape[0] - 3, n).astype(int)
    des = design_masks(mask.shape, reg, ks)
    dice, bf = [], []
    for k, d in zip(ks, des):
        a = mask[k].astype(np.int32)
        b = d.astype(np.int32)
        dice.append(float(L.seg_dice_jaccard(a, b)["dice"]))
        bf.append(float(L.seg_boundary_f(a, b, tau=tau)["f"]))
    return {"dice": float(np.mean(dice)), "bf": float(np.mean(bf)), "per_dice": dice, "per_bf": bf, "ks": ks}


# --------------------------------------------------------------------------- #
# 実データの節                                                                    #
# --------------------------------------------------------------------------- #
def real_thermal(data, rows, dl_liq1):
    import h5py

    print("\n== 1〜3(実データ). NIST AMMT の熱画像(mds2-2716)==")
    out = {}
    with h5py.File(data["thermo"], "r") as f:
        attrs = f["Calibration/ThermalCal"].attrs
        cal = {"a": float(attrs["Coeff_a"][0]), "b": float(attrs["Coeff_b"][0]), "c": float(attrs["Coeff_c"][0])}
        assert all(abs(cal[k] - CAL[k]) < 1e-9 * max(1.0, abs(CAL[k])) for k in CAL), cal
        fps = float(f["ThermalData"].attrs["frame_rate"][0])
        assert fps == FPS
        t1 = float(dl_to_celsius(4095, eps=1.0, cal=cal))
        t03 = float(dl_to_celsius(4095, eps=0.3, cal=cal))
        print("校正係数はファイルの属性と一致(a=%.4f b=%.1f c=%.4g)。4095 DL = %.1f ℃(ε=1)/ %.1f ℃(ε=0.3)"
              "  ※式の読みは推定" % (cal["a"], cal["b"], cal["c"], t1, t03))
        tracks = {}
        for name in sorted(f["ThermalData"]):
            if not name.startswith("Line"):
                continue
            g = f["ThermalData"][name]
            cond = "P%.0f v%.0f d%.0f" % (g.attrs["laser_power"][0], g.attrs["scan_speed"][0], g.attrs["spot_size"][0])
            a = g["Signal"][...]
            ps = pool_series(a, dl_liq1)
            sel = steady(ps)
            pitch, _ = pitch_from_track(ps, float(g.attrs["scan_speed"][0]))
            tracks[name] = {"cond": cond, "pitch": pitch, "len": float(ps["length"][sel].mean()),
                            "area": float(ps["area"][sel].mean()), "ps": ps,
                            "n_sat": int((a == DL_SAT).sum()), "n_zero_frac": float((a == 0).mean())}
            if name == "Line_0_1":
                out["frames_0_1"] = a
            if name == "Line_3_1_1":
                out["frames_hot"] = a
        # 冷却曲線: Line_0_1 の走査線の中央 1 画素
        a = out["frames_0_1"]
        col = int(np.argmax((a == DL_SAT).sum(axis=(0, 1))))
        sig = a[:, 300, col].astype(int)
        s = read_signal(sig, eps=0.3, cal=cal)
        k_sat = np.nonzero(s["lower_bound"])[0]
        k_last = int(k_sat[-1]) if k_sat.size else int(np.argmax(sig))
        after = np.nonzero(s["no_measure"][k_last:])[0]
        k_cut = k_last + int(after[0]) if after.size else len(sig)
        valid = np.arange(k_last + 1, k_cut)
        print("冷却曲線(Line_0_1、行 300・列 %d): 飽和 %d コマ(= 下限)、その後 %d コマが測定値、%d コマ目で 0 → 曲線を切る"
              "(0 を通すと %.0f ℃)" % (col, k_sat.size, valid.size, k_cut, -cal["b"] / cal["a"]))
        assert k_sat.size > 0 and valid.size > 3
        out["cool"] = {"sig": sig, "k_sat": k_sat, "valid": valid, "k_cut": k_cut, "col": col,
                       "t_e1": dl_to_celsius(sig, eps=1.0, cal=cal), "t_e03": dl_to_celsius(sig, eps=0.3, cal=cal)}
        # Y pad: 飽和画素のあるコマ(ブロックで読む)
        ds = f["ThermalData/Y_pad1/Signal"]
        n = ds.shape[0]
        sat = np.zeros(n, int)
        for k0 in range(0, n, 400):
            b = ds[k0:k0 + 400]
            sat[k0:k0 + b.shape[0]] = (b == DL_SAT).sum(axis=(1, 2))
    with h5py.File(data["xypt"], "r") as g:
        P = g["XYPT/Ypad/P"][0]
    # 指令の 1 点 = 10 µs と仮定(属性なし)
    r = time_axis_compare(P, 10e-6, sat)
    print("時間軸: 指令の laser-on %d 本 / 熱画像のバースト %d 本、周期 指令 %.3f ms(10 µs/点 と仮定)/ 熱画像 %.3f ms"
          "(30 kHz 名目)= ずれ %+.2f %%、最後の間隔の比 %.3f / %.3f"
          % (r["n_cmd"], r["n_thermal"], 1e3 * r["period_cmd_s"], 1e3 * r["period_thermal_s"], 100 * r["mismatch"],
             r["last_ratio_cmd"], r["last_ratio_thermal"]))
    assert r["n_cmd"] == r["n_thermal"] == 24
    assert abs(r["last_ratio_cmd"] - r["last_ratio_thermal"]) < 0.005
    assert abs(r["mismatch"]) < 0.03, "時間軸のずれが許容 3 % を超えた"
    out["time"] = r
    out["pad_sat"] = sat
    out["pad_cmd"] = P
    # ピッチ
    pitches = np.array([t["pitch"] for t in tracks.values()])
    med = float(np.median(pitches))
    dev = float(np.max(np.abs(pitches / med - 1.0)))
    print("画素ピッチ(先端の移動 ÷ 走査速度、%d 本 %d 条件): 中央値 %.3f µm/px、最大のずれ %.2f %%(速度 800/960/1200 mm/s)"
          % (len(pitches), len({t["cond"] for t in tracks.values()}), med, 100 * dev))
    assert dev < 0.003, dev
    # 再現性
    by_len, by_area = {}, {}
    for t in tracks.values():
        by_len.setdefault(t["cond"], []).append(t["len"])
        by_area.setdefault(t["cond"], []).append(t["area"])
    wl, bl, rl = repro_stats(by_len)
    wa, ba, ra = repro_stats(by_area)
    print("溶融池(下限、DL >= %.0f)%d 条件 × 3 反復:" % (dl_liq1, len(by_len)))
    for c in sorted(by_len):
        print("  %-18s 長さ %s px  面積 %s px²" % (c, " / ".join("%.1f" % v for v in by_len[c]),
                                                  " / ".join("%.0f" % v for v in by_area[c])))
    print("  長さ: 反復内 %.2f px / 条件間 %.2f px(%.1f 倍)、面積: %.1f / %.1f px²(%.1f 倍)" % (wl, bl, rl, wa, ba, ra))
    assert rl > 3.0 and ra > 3.0, (rl, ra)
    rows.append(("NIST: laser-on runs / thermal bursts", "%d / %d" % (r["n_cmd"], r["n_thermal"]), "equal"))
    rows.append(("NIST: period mismatch (unresolved)", "%+.2f %%" % (100 * r["mismatch"]), "recorded, |x| < 3 %"))
    rows.append(("NIST: pixel pitch, 21 tracks", "%.2f um, max %.2f %% off" % (med, 100 * dev), "< 0.3 %"))
    rows.append(("NIST: pool length between/within SD", "%.1f x" % rl, "> 3"))
    rows.append(("NIST: pool area between/within SD", "%.1f x" % ra, "> 3"))
    out.update({"tracks": tracks, "pitch_med": med, "pitch_dev": dev, "repro": (wl, bl, rl, wa, ba, ra),
                "by_len": by_len, "by_area": by_area, "cal": cal})
    return out


def real_ct(data, rows, void_limit_vox):
    import tifffile

    print("\n== 4・5(実データ). NIST AMMT の X 線 CT(mds2-2291)と設計形状(STL)==")
    tifs, first = ct_contiguous_run(data["tifs"])
    vol = np.stack([tifffile.imread(t) for t in tifs]).astype(np.float32)
    mask, g = binarise_ct(vol)
    print("CT: 連続 %d 枚(元の番号 %d〜%d)、%d × %d px。ボクセルの実寸はファイルに無い → 設計の 9 × 5 mm から逆算"
          % (len(tifs), first, first + len(tifs) - 1, vol.shape[1], vol.shape[2]))
    # 設計形状(解析式)が STL と一致するか(mesh_slice_stack で断面を作って比べる)
    from mesh import read_mesh

    V, F = read_mesh(str(data["stl"]))
    ppm, lay = 40.0, 0.25
    st = L.mesh_slice_stack((V, F), layer_mm=lay, px_per_mm=ppm, bounds=(0.0, 0.0, BOX[0], BOX[1]))
    xs = (np.arange(st.shape[2]) + 0.5) / ppm
    ys = (np.arange(st.shape[1]) + 0.5) / ppm
    X, Y = np.meshgrid(xs, ys)
    dices = []
    for k in range(st.shape[0]):
        zc = (k + 0.5) * lay
        des = design_inside(zc, Y, X)
        dices.append(float(L.seg_dice_jaccard(st[k].astype(np.int32), des.astype(np.int32))["dice"]))
    stl_dice = float(np.min(dices))
    print("設計形状の解析式 vs STL の断面(mesh_slice_stack、%d 層): Dice の最小 %.4f" % (st.shape[0], stl_dice))
    assert stl_dice > 0.995, stl_dice
    reg = register_ct(mask, k_offset=first)
    print("位置合わせ: ピッチ %.2f µm/ボクセル(等方と仮定)、Dice %.4f、向き = 列 +x / 行 −y / スライス +z。"
          "鏡映の別解は Dice %s。z の原点 ±5 スライスで Dice %.4f / %.4f"
          % (1e3 * reg["p"], reg["dice"], " / ".join("%s %.3f" % kv for kv in reg["flips"].items()),
             reg["z_sens"][-5], reg["z_sens"][5]))
    nz_up_max = max(0.0, (HOLE_C - reg["z_range"][0]) / HOLE_R)
    print("  → スライス %d〜%d は z = %.2f〜%.2f mm(造形方向)。この範囲に水平に近い上向き面は無い"
          "(上向きは穴の下側だけで n_z ≤ +%.2f = 垂直から %.0f° しか傾いていない)"
          % (first, first + len(tifs) - 1, reg["z_range"][0], reg["z_range"][1], nz_up_max,
             math.degrees(math.asin(min(nz_up_max, 1.0)))))
    assert reg["dice"] > 0.97 and max(reg["flips"].values()) < reg["dice"] - 0.1, reg
    dev = surface_deviation(mask, reg)
    bands = facing_bands(dev)
    print("面の向き別のはみ出し(0.25 mm 角ごとの中央値を引いた残差の p95)と形のずれ(生の距離の中央値):")
    for k, b in bands.items():
        print("  %-34s n=%7d  はみ出し %6.1f µm  中央値 %+6.1f µm" % (k, b["n"], 1e3 * b["prot"], 1e3 * b["median"]))
    up, down = bands["up (hole, n_z >= +0.2)"]["prot"], bands["down (hole, n_z <= -0.2)"]["prot"]
    wall = bands["vertical walls"]["prot"]
    same_up, same_dn = bands["up, same angle (+0.2..+0.37)"]["prot"], bands["down, same angle (-0.37..-0.2)"]["prot"]
    print("  → 下向き / 上向き = %.2f、下向き / 垂直壁 = %.1f。★同じ傾き(|n_z| 0.2〜0.37、ほぼ垂直)どうしでは %.2f しかない"
          " —— 差の大半は天井側(n_z が −1 に近い所)から来る" % (down / up, down / wall, same_dn / same_up))
    print("  ★形のずれ: 穴の下側(上向き)は設計より %+.0f µm 穴の内側に出ている(穴が小さい/中心がずれている/z の原点が"
          "ずれている のどれかで未解決。z の原点を ±5 スライス動かしても Dice は %.4f しか変わらない)"
          % (1e3 * bands["up (hole, n_z >= +0.2)"]["median"], reg["dice"] - min(reg["z_sens"].values())))
    assert down > up, (down, up)
    # 同じ傾き(ほぼ垂直)どうしの比は報告だけ(門にしない): 実データを見る前に決めていない比較なので
    voids, small = find_voids(mask, reg)
    from scipy.spatial import cKDTree

    depth = []
    if voids:
        surf = cKDTree(dev["q"])
        depth = [float(surf.query(v["xyz"])[0]) for v in voids]
    deep = [v for v, dd in zip(voids, depth) if dd > 0.1]
    lim_um = 1e3 * (6 * VOID_MIN_VOX / math.pi) ** (1 / 3) * reg["p"]
    lim_meas_um = 1e3 * void_limit_vox * reg["p"]
    print("空隙(外に通じない空気、>= %d ボクセル = 直径 %.0f µm 相当以上): %d 個(うち表面から 0.1 mm より深い %d 個)、"
          "それ未満の塊 %d" % (VOID_MIN_VOX, lim_um, len(voids), len(deep), small))
    for v, dd in zip(voids, depth):
        print("    直径 %4.0f µm  位置 (%.2f, %.2f, %.2f) mm  表面から %.3f mm" % (1e3 * v["eq_diam_mm"], *v["xyz"], dd))
    if voids and not deep:
        print("  → 見つかった %d 個はすべて表面から 0.02 mm 以内(斜面・穴の天井の付着粉に閉じ込められた空気)で、内部の空隙ではない"
              % len(voids))
    if not deep:
        print("  ★内部の空隙はゼロ —— ただし「合成で実測した検出下限 %.1f ボクセル = 直径 約 %.0f µm(実データのぼけが合成と"
              "同程度なら)未満は見えない」という意味のゼロ。実データで直径 %.0f µm の表面の空気が見えているので、"
              "実際の下限は %.0f〜%.0f µm の間" % (void_limit_vox, lim_meas_um,
                                             1e3 * min(v["eq_diam_mm"] for v in voids) if voids else lim_um,
                                             1e3 * min(v["eq_diam_mm"] for v in voids) if voids else lim_um, lim_meas_um))
    sc = seg_scores(mask, reg, n=12, tau=2.0)
    sc4 = seg_scores(mask, reg, n=12, tau=4.0)
    print("断面の採点(seg_dice_jaccard / seg_boundary_f、%d 断面): Dice %.4f、境界 F τ=2 px(%.0f µm)%.3f / τ=4 px %.3f"
          % (len(sc["ks"]), sc["dice"], 2e3 * reg["p"], sc["bf"], sc4["bf"]))
    assert sc["dice"] > 0.97
    rows.append(("NIST CT: analytic design vs STL sections", "min Dice %.4f" % stl_dice, "> 0.995"))
    rows.append(("NIST CT: registration Dice (mirror)", "%.4f (%.3f)" % (reg["dice"], max(reg["flips"].values())), "> 0.97"))
    rows.append(("NIST CT: protrusion down / up", "%.0f / %.0f um" % (1e3 * down, 1e3 * up), "down > up"))
    rows.append(("NIST CT: same tilt |n_z| 0.2-0.37 down / up", "%.0f / %.0f um" % (1e3 * same_dn, 1e3 * same_up), "reported only"))
    rows.append(("NIST CT: enclosed air >= 8 vox (deeper than 0.1 mm)", "%d (%d)" % (len(voids), len(deep)),
                 "limit ~%.0f um (synthetic)" % lim_meas_um))
    rows.append(("NIST CT: section Dice / boundary F(2 px)", "%.4f / %.3f" % (sc["dice"], sc["bf"]), "Dice > 0.97"))
    return {"vol": vol, "mask": mask, "reg": reg, "bands": bands, "dev": dev, "voids": voids, "small": small,
            "deep": deep, "seg": sc, "seg4": sc4, "stl_dice": stl_dice, "first": first, "lim_um": lim_meas_um}


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def draw_figures(rad, syn_ct, th, ct, rows, real):
    src = (" " + CREDIT) if real else " (synthetic data, no NIST data used)"
    # ① 溶融池のコマ送り(実データが有ればそれ、無ければ合成)
    if th is not None:
        a = th["frames_hot"]
        col = int(np.argmax((a == DL_SAT).sum(axis=(0, 1))))
        c0 = max(col - 40, 0)
        ks = np.nonzero((a == DL_SAT).any(axis=(1, 2)))[0]
        frames = [np.rot90(dl_frame_rgb(a[k, 0:600, c0:c0 + 80]), 1) for k in range(int(ks[0]), int(ks[-1]) + 40, 2)]
        cap = ("NIST Line_3_1_1 (325 W, 960 mm/s): raw signal in DL, false colour; magenta = saturated 4095 DL "
               "(a lower bound, >= %.0f C at eps=1), navy = 0 (below 100 DL, no measurement). Every 2nd frame of 30 kHz." % rad["t1"])
    else:
        a, _ = synth_track("P325 v960", 0)
        frames = [np.rot90(dl_frame_rgb(a[k, :, :]), 1) for k in range(0, a.shape[0], 2)]
        cap = "synthetic melt pool (elliptic Gaussian, eps=%.2f): magenta = saturated (lower bound), navy = 0 (no measurement)" % SYN_EPS
    big = [np.kron(f, np.ones((2, 2, 1))) for f in frames]
    figs.save_video("melt_pool_frames", big, caption=cap + src, fps=15.0, gif_width=960)
    # ② DL → ℃ の曲線(ε 3 本)
    dl = np.arange(DL_FLOOR, DL_SAT + 1, 5.0)
    figs.save_plot("dl_to_celsius", [("eps = 1.0", dl, dl_to_celsius(dl, eps=1.0)),
                                     ("eps = 0.5", dl, dl_to_celsius(dl, eps=0.5)),
                                     ("eps = 0.3", dl, dl_to_celsius(dl, eps=0.3)),
                                     ("liquidus %.0f C" % T_LIQ, dl, np.full_like(dl, T_LIQ))],
                   xlabel="signal (DL, 100 .. 4095)", ylabel="temperature (C)",
                   title="the same DL is a different temperature for every emissivity",
                   caption="calibration T = 14388/(a ln(c eps/x + 1)) - b/a (reading of the file's model string is our assumption). "
                           "4095 DL = %.0f C at eps=1, %.0f C at eps=0.3. Pixels >= %.0f DL are above the liquidus for any eps <= 1."
                           % (rad["t1"], rad["t03"], rad["dl_liq1"]) + src)
    # ③ 冷却曲線(実データ)
    if th is not None:
        c = th["cool"]
        k = np.arange(len(c["sig"]))
        lo, hi = max(int(c["k_sat"][0]) - 5, 0), min(c["k_cut"] + 15, len(k))
        kk = k[lo:hi]
        sel_v = np.isin(kk, c["valid"])
        figs.save_plot("cooling_curve", [("measured, eps=0.3", kk[sel_v] / FPS * 1e3, c["t_e03"][kk][sel_v]),
                                         ("measured, eps=1", kk[sel_v] / FPS * 1e3, c["t_e1"][kk][sel_v]),
                                         ("saturated: lower bound (eps=0.3)", c["k_sat"] / FPS * 1e3, c["t_e03"][c["k_sat"]])],
                       kinds=["line", "line", "scatter"], xlabel="time (ms)", ylabel="temperature (C)",
                       title="one pixel: lower bound while saturated, cut where the signal hits 0",
                       caption="Line_0_1, row 300: %d saturated frames are only a lower bound; the curve stops at frame %d where "
                               "the camera reports 0 (below 100 DL) instead of falling to -204 C." % (c["k_sat"].size, c["k_cut"]) + src)
        # ④ 時間軸
        sat = th["pad_sat"].astype(float)
        P = th["pad_cmd"]
        # 両方とも最初の立ち上がりを 0 に揃える(ずれは周期ごとに積もって右端で見える)
        t_th = (np.arange(sat.size) - int(np.argmax(sat > 0))) / FPS * 1e3
        t_cmd = (np.arange(P.size) - int(np.argmax(P > 0))) * 10e-3
        figs.save_plot("time_axis", [("command laser power / 285 W (10 us/point assumed)", t_cmd, P / 285.0),
                                     ("thermal saturated pixels / max (30 kHz)", t_th, sat / max(sat.max(), 1))],
                       xlabel="time (ms, nominal clocks)", ylabel="normalised", size=(760, 320),
                       title="24 laser-on runs = 24 thermal bursts, but the periods differ by %+.1f %%" % (100 * th["time"]["mismatch"]),
                       caption="Y pad: the command (XYPT, no time step stored) and the staring camera agree on the count "
                               "and on the long last interval, yet drift apart by %.1f %% per period; unresolved."
                               % (100 * th["time"]["mismatch"]) + src)
        # ⑤ 再現性
        conds = sorted(th["by_len"])
        series = []
        for i, cnd in enumerate(conds):
            v = np.asarray(th["by_len"][cnd]) * th["pitch_med"]
            series.append((cnd, np.full(v.size, i, float), v))
        figs.save_plot("pool_repeatability", series, kinds=["scatter"] * len(series), xlabel="condition (index)",
                       xlim=(-0.5, 10.5), size=(720, 360),
                       ylabel="lower-bound melt pool length (um)",
                       title="3 repeats per condition: spread within << difference between",
                       caption="mean length of the region >= %.0f DL (above liquidus for any eps <= 1) over steady frames; "
                               "power 245/285/325 W, speed 800/960/1200 mm/s, spot 49/67/82 um." % rad["dl_liq1"] + src)
    # ⑥ CT のスライス送り(設計断面の輪郭を重ねる)
    if ct is not None:
        vol, reg = ct["vol"], ct["reg"]
        ks = list(range(0, vol.shape[0], 6))
        des = design_masks(vol.shape, reg, ks)
        frames = [ct_slice_rgb(vol[k], d) for k, d in zip(ks, des)]
        figs.save_video("ct_slices", frames, fps=6.0, gif_width=640,
                        caption="XCT slices %d..%d (z = %.2f..%.2f mm, build direction) with the STL cross-section in red. "
                                "Note the powder/dross hanging under the hole crown and the 45 deg notch."
                                % (ct["first"], ct["first"] + vol.shape[0] - 1, *reg["z_range"]) + src)
        # 下向き面の拡大(穴の天井付近)
        k_top = int(np.argmin(np.abs((np.arange(vol.shape[0]) - reg["s0"]) * reg["p"] - 4.0)))
        dsl = design_masks(vol.shape, reg, [k_top])[0]
        figs.save("ct_hole_crown", ct_slice_rgb(vol[k_top], dsl)[:, : int(reg["c0"] + 3.2 / reg["p"])],
                  caption="slice at z = %.2f mm just below the crown of the 4 mm hole: particles hang into the hole "
                          "from the down-facing surface; red = design." % ((k_top - reg["s0"]) * reg["p"]) + src)
    else:
        s = syn_ct["down"]
        vol, reg = s["vol"], s["reg"]
        ks = list(range(0, vol.shape[0], 3))
        des = design_masks(vol.shape, reg, ks)
        frames = [ct_slice_rgb(vol[k], d) for k, d in zip(ks, des)]
        figs.save_video("ct_slices", frames, fps=8.0, caption="synthetic XCT (dross on down-facing surfaces, 6 known voids) "
                                                              "with the design cross-section in red" + src)
    # ⑦ 向き別のはみ出し(n_z の区間ごと)
    dev = ct["dev"] if ct is not None else syn_ct["down"]["dev"]
    edges = np.array([-1.0, -0.8, -0.6, -0.4, -0.2, 0.2, 0.4, 0.6, 0.8, 1.0])
    xs_, ys_ = [], []
    for lo_, hi_ in zip(edges[:-1], edges[1:]):
        m = (dev["cat"] == 0) & (dev["nz"] >= lo_) & (dev["nz"] < hi_)
        if m.sum() >= 200:
            xs_.append(0.5 * (lo_ + hi_))
            ys_.append(1e3 * protrusion(dev["r"][m]))
    m45 = dev["cat"] == 1
    walls = dev["cat"] == 2
    figs.save_plot("protrusion_by_facing", [("4 mm hole, by n_z bin", np.array(xs_), np.array(ys_)),
                                            ("45 deg notch", np.array([-1 / math.sqrt(2)]), np.array([1e3 * protrusion(dev["r"][m45])])),
                                            ("vertical walls", np.array([0.0]), np.array([1e3 * protrusion(dev["r"][walls])]))],
                   kinds=["line", "scatter", "scatter"], size=(640, 360),
                   xlabel="n_z of the design surface (-1 = facing down, +1 = facing up)",
                   ylabel="protrusion (um)", title="overhangs grow dross",
                   caption=("XCT vs STL: " if ct is not None else "synthetic XCT (dross only on down-facing surfaces): ")
                   + "protrusion = p95 of the signed distance (outward positive) after subtracting the median of each 0.25 mm surface cell (form error); "
                     "line = the 4 mm hole per n_z bin (bins with >= 200 points), dots = 45 deg notch and vertical walls." + src)
    figs.save_table("numbers", ["quantity", "value", "bar"], rows, title="AM thermal -> CT: every number and its bar",
                    caption="synthetic gates always run; NIST gates only when FULLSEYE_DATA_DIR has nist_ammt." + src)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.perf_counter()
    print("=" * 78)
    print("金属 AM: 工程中の熱画像 → 造形後の X 線 CT を既存 op でつなぐ")
    print("=" * 78)
    rows = []
    rad = section_radiometry(rows)
    syn_pool = section_synthetic_pool(rows, rad["dl_liq1"])
    syn_time = section_synthetic_time(rows)
    syn_ct = section_synthetic_ct(rows)
    t_syn = time.perf_counter() - t0
    print("\n(合成の門 %.1f s)" % t_syn)
    data = find_data()
    th = ct = None
    if data is not None:
        print("\n" + CREDIT_JA)
        th = real_thermal(data, rows, rad["dl_liq1"])
        ct = real_ct(data, rows, syn_ct["void_limit_vox"])
    if figs.enabled():
        draw_figures(rad, syn_ct, th, ct, rows, data is not None)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
    elapsed = time.perf_counter() - t0
    print("\n== 結果 ==")
    for name, val, bar in rows:
        print("  %-52s %-26s %s" % (name, val, bar))
    print("\n== 正直に書く ==")
    print(" * 校正式は属性の Model 文字列(括弧が閉じない)を T = 14388/(a ln(c e/x+1)) − b/a と読んだ推定。")
    print(" * 液相線 1336 ℃ は一般に知られた In718 の融解範囲の上端で、この PoC の仮定(取得した文献値ではない)。")
    print(" * 時間軸の 2.3 % のずれは未解決(指令の 1 点 = 10 µs も属性が無く仮定)。")
    print(" * CT のボクセル寸法はファイルに無く、設計の 9 × 5 mm から逆算した(等方と仮定)。")
    print(" * 取得した CT は z = 1.7〜4.2 mm の 200 枚だけで、水平に近い上向き面(z=1 の床・z=5 の天面)を含まない。")
    print(" * 空隙の検出下限は合成で実測した値をボクセル数のまま実データに当てた(実データのぼけが合成と同程度という仮定)。")
    print(" * 溶融池は「ε=1 で液相線に当たる DL 以上」の下限の領域で、真の溶融池はそれより大きい(ε が分からない限り上限は言えない)。")
    print("\n所要 %.1f s(合成 %.1f s)" % (elapsed, t_syn))
    if data is not None:
        print("\nPASS: 合成と NIST 実データの門をすべて通過 —— 4095 DL は ε=1 で %.0f ℃ / ε=0.3 で %.0f ℃、"
              "指令 %d 本 = バースト %d 本(周期のずれ %+.1f %% は未解決として記録)、ピッチ %.2f µm(最大 %.2f %%)、"
              "溶融池の条件間/反復内 %.0f 倍、CT のはみ出し 下向き %.0f µm > 上向き %.0f µm、内部の空隙 %d 個(検出下限 約 %.0f µm)、断面 Dice %.3f"
              % (rad["t1"], rad["t03"], th["time"]["n_cmd"], th["time"]["n_thermal"], 100 * th["time"]["mismatch"],
                 th["pitch_med"], 100 * th["pitch_dev"], th["repro"][2],
                 1e3 * ct["bands"]["down (hole, n_z <= -0.2)"]["prot"], 1e3 * ct["bands"]["up (hole, n_z >= +0.2)"]["prot"],
                 len(ct["deep"]), ct["lim_um"], ct["seg"]["dice"]))
    else:
        print("\nPASS: 合成データの門をすべて通過(実データなし)—— ε 必須・閉形式どおりの誤差、注入した 2.3 %% のずれを "
              "%+.2f %% で検出、ピッチ誤差 %.2f %%、条件間/反復内 %.0f 倍、ドロス比 %.2f(対照 %.2f)、空隙 %d/%d 検出(下限 %.1f ボクセル)"
              % (100 * syn_time["mismatch"], 100 * syn_pool["pitch_dev"], syn_pool["repro_len"],
                 syn_ct["down"]["ratio"], syn_ct["all"]["ratio"], len(syn_ct["voids"][0]), len(syn_ct["voids"][2]),
                 syn_ct["void_limit_vox"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
