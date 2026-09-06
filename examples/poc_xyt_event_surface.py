# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""到達時刻面を (x, y, t) の等値面として取り出す —— 2-D の動画を 1 つの 3-D の面として測る。

    py -3.11 examples/poc_xyt_event_surface.py

平面を伝わる波面(点源から広がる円、2 源が合流する)を高速度カメラで撮ると、
各画素は「ある時刻に明るくなる」。その**しきい値を超えた時刻** T(x, y) を並べた
ものが**到達時刻面**で、これは動画 (t, y, x) を 1 つの体積とみなしたときの
**等値面**そのものである。超音波の飛行時間、シュリーレン、放電、燃焼の火炎伝播、
イベントカメラの time surface —— 「いつ来たか」を面として扱う場面は多い。

EXTEND: 実測の高速度動画に差し替えるなら :func:`make_volume` の戻り値
``vol`` (T, H, W) を撮影スタックに、``t_true`` を**別に較正した真値**に置き換える。
真値が無いなら 6 章(速度の推定)だけが使える —— 到達時刻の絶対値は
しきい値の取り方で定数だけずれるが、**その定数は空間微分で消える**ので、
局所伝播速度は真値なしでも出る。逆に 3〜5 章の偏りは真値なしでは測れない。

【真値(閉形式)】
源 i の場は ``s_i = exp(-(r_i - c(t - t_i))^2 / 2w^2)``(振幅一定のガウス波面)。
観測は ``I = max_i s_i`` とする —— **和にしない**のは、和にすると合流付近で
2 つの半分が足し合わさってしきい値通過が早まり、真値が閉形式で書けなくなる
ため。その「早まる量」は 8 章で対照群として実測する。``I = max`` なら
しきい値 θ の初回通過時刻は厳密に

    T_i = t_i + (r_i - w*sqrt(2 ln(1/θ))) / c,      T = min_i T_i

で、丸め誤差以外の近似が入らない。**合流線**(どちらの源が先に届くかが
入れ替わる線)も閉形式で、``r_A - r_B = c (t_B - t_A)`` の双曲線 ——
つまり**壊れる場所は撮る前に紙の上で分かる**。

【この PoC が測って分かったこと(数字は実行時の実測値)】

1. ゼロ点(初めて超えたフレーム番号)の誤差はフレーム間隔にそのまま比例する
   (掃引の傾き 1.00)。Δt = 1.0 ms で RMS 0.568 ms、偏り +0.489 ms
   —— **偏りは Δt/2 で、枚数を増やしても消えない**。
2. 線形のサブフレーム補間で Δt = 1.0 ms の RMS が 0.0209 ms(**27 倍**)。
   誤差は Δt^2.26 で伸びる(ゼロ点は Δt^1.00)。
3. ★★**放物線補間は線形より悪い。しかもそれはしきい値の置き場所で反転する。**
   Δt = 1.0 ms で θ=0.5 なら線形 0.0209 / 放物線 0.0406(線形の勝ち)、
   θ=0.2 なら 0.0744 / 0.0205(放物線の勝ち)。理由は閉形式で言える ——
   ガウス波形の**変曲点**は θ = exp(-1/2) = 0.6065 にあり、そこでは 2 次の項が
   消えて波形が局所的に**いちばん直線に近い**。実測でも θ=0.6065 が線形の
   最良点(0.0108)で、放物線(0.0414)に **3.8 倍**の差をつける。
   「サブピクセル/サブフレームは放物線」という定石は、**しきい値を半値付近に
   置く限り成り立たない**。
4. ★3-D 等値面(:func:`fullseye.marching_cubes`)の**時間軸稜線の頂点は、
   線形補間そのもの**だった —— 両者の最大差 9.9e-07 ms(marching cubes が
   float32 で内挿するぶんだけ)。「等値面を切る」と「各画素で線形補間する」は
   同じ計算で、前者はそれを面として返す。等値面は**2 枚**(前縁と後縁)
   出るので、到達時刻に使うのは各柱の最小 t の側だけ。
5. ★速度は到達時刻面の**勾配の大きさの逆数**で出る。合流線から 4 px 以上
   離れた領域の中央値 2.9979 px/ms(真値 3.0、**-0.07 %**)。同じ面でも
   メッシュの頂点法線(:func:`fullseye.ledger.vertex_normals`)から出すと
   3.0933(**+3.11 %**、44 倍の偏り)—— 面積重み付き法線は隣の三角形と
   平均されるので、格子の勾配より広い範囲をならしている。
6. ★★**合流線の上では速度が発散する**(0 にはならない)。first-arrival 面は
   合流線で**尾根**になるので勾配が 0 に落ち、1/|∇T| が 1e12 まで飛ぶ。
   予測した双曲線から 2 px 以内で起き、4 px 離れれば消える。**対照群**として
   源を 1 つに減らすと、同じ推定器で最大 3.24 px/ms(発散しない)。
7. ★もう 1 つの「到達」の定義 —— 最急上昇(:func:`fullseye.vol_edge_probe`)は
   振幅に依らない代わりに、**平滑化の量だけ時刻が前へずれる**。ずれの予測
   sqrt(σ_t² + σ_smooth²) は向きと桁を当てる(σ=2 で予測 -1.000 / 実測
   -1.056 ms)が、σ=0 でも -0.196 ms の残差があり、それを引いても σ=3 で
   15 % ずれる。しきい値の定義はオフセットが閉形式、最急上昇の定義は
   **較正が要る**。
8. 干渉(``I = s_A + s_B``)にすると合流線の上で到達が **0.54 ms 早まる**
   (Δt の半分より大きい)。合流付近だけ系統的に早い —— 速度を勾配で出すと
   この偏りが**速度の嘘**に化ける。

来歴(公開文献のみ): Lorensen & Cline, *SIGGRAPH* 87 (1987) 163 —— marching
cubes / Sethian, *Level Set Methods and Fast Marching Methods* (Cambridge, 1999)
—— 到達時刻面 T が |∇T| = 1/c(eikonal 方程式)を満たすこと /
Lagorce et al., *IEEE TPAMI* 39 (2017) 1346 —— イベントカメラの time surface。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 144                    # 視野 [px]
C_TRUE = 3.0               # 伝播速度 [px/ms]
W_FRONT = 4.5              # 波面の 1σ 厚み [px] -> 時間幅 σ_t = W/C = 1.5 ms
TH = 0.5                   # しきい値(ピーク比)
SRC_A = (72.0, 36.0)       # 源 A (row, col)、点火 t=0
SRC_B = (72.0, 108.0)      # 源 B、点火 t=T_FIRE_B
T_FIRE_B = 4.0             # [ms]
R_MIN = 16.0               # 源のごく近傍は評価しない(波面がまだ立っていない)
DT_BASE = 1.0              # 基準のフレーム間隔 [ms]

_YY, _XX = np.mgrid[0:N, 0:N].astype(np.float64)
_RA = np.hypot(_YY - SRC_A[0], _XX - SRC_A[1])
_RB = np.hypot(_YY - SRC_B[0], _XX - SRC_B[1])
#: 合流線からの符号つき距離のもと。0 の等高線が予測した双曲線。
_MERGE = _RA - _RB - C_TRUE * T_FIRE_B
#: 源に近すぎる画素を外した評価領域
_FIELD = (_RA > R_MIN) & (_RB > R_MIN)


def _offset(th: float) -> float:
    """しきい値 ``th`` の初回通過が波面の中心より何 px 手前に来るか。"""
    return W_FRONT * np.sqrt(2.0 * np.log(1.0 / th))


def true_arrival(th: float = TH) -> np.ndarray:
    """到達時刻の真値 T(x, y) [ms](閉形式)。"""
    off = _offset(th)
    ta = (_RA - off) / C_TRUE
    tb = T_FIRE_B + (_RB - off) / C_TRUE
    return np.minimum(ta, tb)


def make_volume(dt: float, t_end: float, mode: str = "max",
                single: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """``(t, y, x)`` の体積を作る。``ts`` [ms] と ``vol`` (T, H, W) を返す。

    ``mode="max"`` は 2 つの波面の**大きいほう**(真値が閉形式)。
    ``mode="sum"`` は干渉(8 章の対照群、真値は閉形式でなくなる)。
    ``single=True`` は源 A だけ(6 章の対照群)。
    """
    ts = np.arange(0.0, t_end + dt, dt)
    vol = np.empty((ts.size, N, N), np.float64)
    two_ww = 2.0 * W_FRONT * W_FRONT
    for k, t in enumerate(ts):
        sa = np.exp(-((_RA - C_TRUE * t) ** 2) / two_ww)
        if single:
            vol[k] = sa
            continue
        sb = np.exp(-((_RB - C_TRUE * (t - T_FIRE_B)) ** 2) / two_ww)
        vol[k] = np.maximum(sa, sb) if mode == "max" else np.minimum(sa + sb, 1.0)
    return ts, vol


# --------------------------------------------------------------------------- #
# 到達時刻の推定器 —— ゼロ点 / 線形 / 放物線                                    #
# --------------------------------------------------------------------------- #
def estimate_arrival(ts: np.ndarray, vol: np.ndarray, th: float = TH) -> dict:
    """3 つの推定量と有効画素マスクを返す。

    ``"frame"`` = 初めて ``th`` を超えたフレームの時刻(**ゼロ点**)。
    ``"linear"`` = その前後 2 点の線形内挿。
    ``"parabola"`` = 前後 3 点に 2 次を当てて ``I(t) = th`` を解く。
    """
    dt = float(ts[1] - ts[0])
    above = vol >= th
    k = np.argmax(above, axis=0)
    ok = above.any(axis=0) & (k > 0) & (k < ts.size - 1)
    kc = np.clip(k, 1, ts.size - 2)

    def at(idx):
        return np.take_along_axis(vol, idx[None], 0)[0]

    i0, i1, i2 = at(kc - 1), at(kc), at(kc + 1)
    t1 = ts[kc]
    # 線形: 交差点は k-1 と k のあいだ。rel は k からの相対 [-1, 0]。
    rel_lin = -(i1 - th) / np.maximum(i1 - i0, 1e-12)
    # 放物線: a*x^2 + b*x + (I1-th) = 0(x は k からの相対、単位 dt)
    a = 0.5 * (i0 - 2.0 * i1 + i2)
    b = 0.5 * (i2 - i0)
    disc = b * b - 4.0 * a * (i1 - th)
    with np.errstate(divide="ignore", invalid="ignore"):
        sq = np.sqrt(np.maximum(disc, 0.0))
        r1 = (-b + sq) / (2.0 * a)
        r2 = (-b - sq) / (2.0 * a)
    rel_par = np.where(np.abs(r1 - rel_lin) < np.abs(r2 - rel_lin), r1, r2)
    # 退化(2 次の係数が消える・根が無い・1 フレーム以上飛ぶ)は線形へ落とす。
    bad = (disc < 0) | (np.abs(a) < 1e-14) | ~np.isfinite(rel_par) \
        | (np.abs(rel_par - rel_lin) > 1.0)
    rel_par = np.where(bad, rel_lin, rel_par)
    return {"frame": t1, "linear": t1 + dt * rel_lin,
            "parabola": t1 + dt * rel_par, "ok": ok,
            "degenerate": float(np.mean(bad[ok])) if ok.any() else 0.0}


def _err(est: np.ndarray, truth: np.ndarray, mask: np.ndarray) -> tuple:
    """(偏り, 散らばり, RMS)。1 本に畳まないで返す。"""
    e = (est - truth)[mask]
    return float(e.mean()), float(e.std()), float(np.sqrt(np.mean(e * e)))


# =========================================================================== #
def section1_scene() -> np.ndarray:
    print("=" * 78)
    print("1) 場面と真値の検算 —— 閉形式の到達時刻は体積と一致するか")
    print("=" * 78)
    truth = true_arrival()
    print("  視野 %d x %d px / 速度 %.1f px/ms / 波面 1σ %.1f px "
          "(= 時間幅 σ_t %.2f ms)" % (N, N, C_TRUE, W_FRONT, W_FRONT / C_TRUE))
    print("  源 A (%.0f,%.0f) 点火 0 ms / 源 B (%.0f,%.0f) 点火 %.1f ms"
          % (*SRC_A, *SRC_B, T_FIRE_B))
    print("  到達時刻の真値: %.2f 〜 %.2f ms(評価領域 r > %.0f px = 全体の %.1f %%)"
          % (truth[_FIELD].min(), truth[_FIELD].max(), R_MIN, 100 * _FIELD.mean()))
    print("  合流線 r_A - r_B = %.1f px の双曲線。|_MERGE| < 2 px の画素 %d 個。"
          % (C_TRUE * T_FIRE_B, int(np.sum(_FIELD & (np.abs(_MERGE) < 2.0)))))

    # 検算: 非常に細かい Δt で刻めば、初回通過フレームは真値へ収束するはず。
    ts, vol = make_volume(0.02, float(truth.max()) + 6.0)
    est = estimate_arrival(ts, vol)
    m = _FIELD & est["ok"]
    bias, sd, rms = _err(est["frame"], truth, m)
    print("  Δt = 0.02 ms で刻んだ初回通過: 偏り %+.5f ms / 散らばり %.5f ms"
          % (bias, sd))
    print("     → 量子化の理論値は偏り +Δt/2 = +0.010 / 散らばり Δt/√12 = 0.006。"
          " %s" % ("一致(真値として使える)" if rms < 0.02 else "★不一致"))
    print("  ※ ここだけ Δt を細かく取っている。以降は Δt = %.1f ms。" % DT_BASE)
    return truth


def section2_zero_point(truth: np.ndarray) -> dict:
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「初めてしきい値を超えたフレーム番号」")
    print("=" * 78)
    ts, vol = make_volume(DT_BASE, float(truth.max()) + 6.0)
    est = estimate_arrival(ts, vol)
    m = _FIELD & est["ok"]
    print("  Δt = %.1f ms(フレーム %d 枚)。時間分解能はフレーム間隔で頭打ち。"
          % (DT_BASE, ts.size))
    print()
    print("  %-10s %12s %12s %12s %10s" % ("手法", "偏り ms", "散らばり ms",
                                           "RMS ms", "ゼロ点比"))
    print("  " + "-" * 60)
    base = None
    for name, key in [("フレーム", "frame"), ("線形", "linear"), ("放物線", "parabola")]:
        bias, sd, rms = _err(est[key], truth, m)
        if base is None:
            base = rms
        print("  %-10s %12.4f %12.4f %12.4f %10s"
              % (name, bias, sd, rms,
                 "—" if key == "frame" else "%.1f 倍" % (base / max(rms, 1e-12))))
    print()
    print("  → ゼロ点の偏り +%.3f ms はほぼ Δt/2。**片側にしか出ない量子化**なので、"
          % _err(est["frame"], truth, m)[0])
    print("     何枚撮っても平均では消えない(乱数ではない)。")
    print("     ★放物線がここで線形に負けている。理由は 4 章。")
    return {"ts": ts, "vol": vol, "est": est, "mask": m}


def section3_dt_sweep(truth: np.ndarray) -> None:
    print()
    print("=" * 78)
    print("3) ★フレーム間隔を粗くしたときの誤差の伸び方")
    print("=" * 78)
    dts = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    rows = {"frame": [], "linear": [], "parabola": []}
    print("  %8s %8s | %11s %11s %11s" % ("Δt ms", "枚数", "フレーム", "線形", "放物線"))
    print("  " + "-" * 56)
    for dt in dts:
        ts, vol = make_volume(dt, float(truth.max()) + 6.0)
        est = estimate_arrival(ts, vol)
        m = _FIELD & est["ok"]
        vals = []
        for key in ("frame", "linear", "parabola"):
            rms = _err(est[key], truth, m)[2]
            rows[key].append(rms)
            vals.append(rms)
        print("  %8.2f %8d | %11.4f %11.4f %11.4f" % (dt, ts.size, *vals))
    lx = np.log10(dts)
    print()
    print("  両対数の傾き(= 誤差 ∝ Δt^p の p):")
    for key, label in [("frame", "フレーム"), ("linear", "線形"), ("parabola", "放物線")]:
        p = float(np.polyfit(lx, np.log10(rows[key]), 1)[0])
        print("    %-8s p = %.2f" % (label, p))
    print()
    print("  → ゼロ点は p = 1.00 ちょうど(量子化そのもの)。線形は p = 2.3 で、")
    print("     Δt を半分にすると誤差は 5 分の 1 になる。**サブフレーム補間は")
    print("     フレームレートを上げるより安い** —— ただし 4 章の条件つき。")
    figs.save_plot("dt_sweep",
                   [("フレーム(ゼロ点)", lx, np.log10(rows["frame"])),
                    ("線形", lx, np.log10(rows["linear"])),
                    ("放物線", lx, np.log10(rows["parabola"]))],
                   xlabel="log10 フレーム間隔 [ms]", ylabel="log10 RMS 誤差 [ms]",
                   title="到達時刻の誤差 vs フレーム間隔",
                   caption="両対数。傾きがゼロ点 1.0 / 線形 2.3 / 放物線 2.7。"
                           "放物線は傾きが急でも切片が悪く、Δt≧0.75 ms では線形に負ける。")


def section4_threshold(truth_unused: np.ndarray) -> None:
    print()
    print("=" * 78)
    print("4) ★★どちらの補間が勝つかは、しきい値が変曲点のどちら側かで決まる")
    print("=" * 78)
    print("  ガウス波面 exp(-u²/2σ²) の**変曲点**は u = σ、つまり")
    print("  θ = exp(-1/2) = %.4f。そこでは 2 次の項が消えるので、波形は" % np.exp(-0.5))
    print("  局所的に**いちばん直線に近い**。放物線を当てる根拠が消える。")
    print()
    print("  %8s %10s | %11s %11s %11s %8s"
          % ("θ", "u/σ", "フレーム", "線形", "放物線", "勝者"))
    print("  " + "-" * 66)
    ths = [0.20, 0.35, 0.50, float(np.exp(-0.5)), 0.75, 0.90]
    lin_r, par_r = [], []
    for th in ths:
        truth = true_arrival(th)
        ts, vol = make_volume(DT_BASE, float(truth.max()) + 6.0)
        est = estimate_arrival(ts, vol, th)
        m = _FIELD & est["ok"]
        rz = _err(est["frame"], truth, m)[2]
        rl = _err(est["linear"], truth, m)[2]
        rp = _err(est["parabola"], truth, m)[2]
        lin_r.append(rl)
        par_r.append(rp)
        print("  %8.4f %10.3f | %11.4f %11.4f %11.4f %8s"
              % (th, np.sqrt(2 * np.log(1 / th)), rz, rl, rp,
                 "線形" if rl < rp else "放物線"))
    print()
    print("  → θ = 0.6065(変曲点)で線形が最良 %.4f ms、放物線 %.4f ms ——"
          % (lin_r[3], par_r[3]))
    print("     **線形が %.1f 倍勝つ**。逆に θ = 0.20 では放物線が %.1f 倍勝つ。"
          % (par_r[3] / lin_r[3], lin_r[0] / par_r[0]))
    print("     入れ替わりは θ ≈ 0.35 と θ ≈ 0.75 の 2 か所にある。")
    print("     ★「サブピクセルは放物線」という定石は、**半値でしきい値を切る限り")
    print("     成り立たない**。しかも半値付近は傾きが最大で雑音に最も強い場所")
    print("     なので、実務でいちばん選ばれるしきい値がちょうど放物線の苦手な場所。")
    figs.save_plot("threshold_crossover",
                   [("線形", np.array(ths), np.array(lin_r)),
                    ("放物線", np.array(ths), np.array(par_r))],
                   xlabel="しきい値 θ(ピーク比)", ylabel="RMS 誤差 [ms]",
                   title="補間の勝敗はしきい値で入れ替わる(Δt = 1.0 ms)",
                   caption="変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では"
                           "放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。")


def section5_isosurface(state: dict, truth: np.ndarray) -> np.ndarray:
    print()
    print("=" * 78)
    print("5) ★3-D 等値面 —— 面の時間軸稜線の頂点は、線形補間そのもの")
    print("=" * 78)
    ts, vol = state["ts"], state["vol"]
    t0 = time.perf_counter()
    verts, faces = fs.marching_cubes(vol, TH)
    dt_mc = time.perf_counter() - t0
    print("  fs.marching_cubes(vol, %.2f): 頂点 %d / 三角形 %d (%.2f 秒)"
          % (TH, len(verts), len(faces), dt_mc))
    print("  頂点は**ボクセル index 空間** (t_index, y, x)。時間軸だけ単位が違うので")
    print("  呼び手が Δt を掛ける(等方 spacing しか渡せない。9 章 (b))。")

    yv, xv = verts[:, 1], verts[:, 2]
    on_t_edge = (np.abs(yv - np.round(yv)) < 1e-9) & (np.abs(xv - np.round(xv)) < 1e-9)
    print("  うち**時間軸の稜線**を切った頂点 %d 個(%.1f %%)—— これらは y,x が整数。"
          % (int(on_t_edge.sum()), 100.0 * on_t_edge.mean()))

    dt = float(ts[1] - ts[0])
    iy = np.round(yv[on_t_edge]).astype(int)
    ix = np.round(xv[on_t_edge]).astype(int)
    tv = verts[on_t_edge, 0] * dt
    t_mc = np.full((N, N), np.inf)
    np.minimum.at(t_mc, (iy, ix), tv)          # 各柱の最小 t = 前縁のシート
    seen = np.isfinite(t_mc)
    m = state["mask"] & seen
    lin = state["est"]["linear"]
    print("  各柱の**最小 t** を取ると到達時刻面になる(前縁のシート)。")
    print("  線形補間との最大差: %.3e ms —— 同じ計算(marching cubes の内挿は"
          % float(np.max(np.abs(t_mc - lin)[m])))
    print("  float32 なので、差はその丸めぶん)。")
    print("  真値との RMS: %.4f ms(線形 %.4f ms と一致)"
          % (_err(t_mc, truth, m)[2], _err(lin, truth, m)[2]))
    n_sheets = np.zeros((N, N), int)
    np.add.at(n_sheets, (iy, ix), 1)
    print("  1 柱あたりの交点数: 中央値 %d 個 —— **等値面は 2 枚**(前縁と後縁)。"
          % int(np.median(n_sheets[m])))
    print("  到達時刻に使えるのは前縁だけで、面を丸ごと渡すと後縁が混ざる。")
    return t_mc


def section6_speed(state: dict, truth: np.ndarray) -> dict:
    print()
    print("=" * 78)
    print("6) ★速度 = 到達時刻面の勾配の大きさの逆数(eikonal |∇T| = 1/c)")
    print("=" * 78)
    lin = state["est"]["linear"]
    gy, gx = np.gradient(lin)
    grad = np.hypot(gy, gx)
    with np.errstate(divide="ignore"):
        c_grad = 1.0 / np.maximum(grad, 1e-12)
    far = state["mask"] & (np.abs(_MERGE) > 4.0)
    print("  合流線から 4 px 以上離れた %d 画素:" % int(far.sum()))
    print("    勾配から:  中央値 %.4f px/ms(真値 %.1f、%+.2f %%)"
          % (np.median(c_grad[far]), C_TRUE,
             100 * (np.median(c_grad[far]) / C_TRUE - 1)))

    # メッシュの頂点法線から: 面 t = T(y,x) の法線は (1, -T_y, -T_x) に比例。
    verts, faces = fs.marching_cubes(state["vol"], TH)
    nrm = np.asarray(fs.ledger.vertex_normals((verts, faces)))
    dt = float(state["ts"][1] - state["ts"][0])
    yv, xv = verts[:, 1], verts[:, 2]
    on_t = (np.abs(yv - np.round(yv)) < 1e-9) & (np.abs(xv - np.round(xv)) < 1e-9)
    iy = np.round(yv).astype(int)
    ix = np.round(xv).astype(int)
    lead = on_t & (np.abs(verts[:, 0] * dt - lin[iy, ix]) < 0.05) \
        & state["mask"][iy, ix]
    nn = nrm[lead]
    # (n_t/dt, n_y, n_x) -> |∇T| = hypot(n_y, n_x) / |n_t/dt|
    c_norm = np.abs(nn[:, 0] / dt) / np.maximum(np.hypot(nn[:, 1], nn[:, 2]), 1e-12)
    d_lead = np.abs(_MERGE)[iy[lead], ix[lead]]
    sel = d_lead > 4.0
    print("    頂点法線から: 中央値 %.4f px/ms(%+.2f %%、前縁の頂点 %d 個)"
          % (np.median(c_norm[sel]), 100 * (np.median(c_norm[sel]) / C_TRUE - 1),
             int(sel.sum())))
    print("  → 法線のほうが 1 桁悪い。頂点法線は**面積重み付きで隣の三角形と")
    print("     平均**されるので、格子の勾配より広い範囲をならしている。")
    print("     面が要る用途(可視化・レイキャスト)には法線、量が要る用途には勾配。")
    return {"c_grad": c_grad, "c_norm": c_norm, "d_lead": d_lead}


def section7_merge_line(state: dict, speed: dict) -> None:
    print()
    print("=" * 78)
    print("7) ★★合流線の上で速度が発散する —— 壊れる場所は撮る前に分かる")
    print("=" * 78)
    print("  first-arrival 面 T = min(T_A, T_B) は、合流線で**尾根**になる")
    print("  (両側から時刻が増えて、そこで折れる)。折れ目では中心差分の勾配が")
    print("  打ち消して 0 に落ちるので、1/|∇T| が発散する。**0 にはならない**。")
    print()
    c = speed["c_grad"]
    d = np.abs(_MERGE)
    print("  %14s %8s %12s %12s %12s"
          % ("合流線から px", "画素数", "中央値", "最大", "c>2c_true 率"))
    print("  " + "-" * 62)
    bins = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 32.0), (32.0, 400.0)]
    prof_x, prof_y = [], []
    for lo, hi in bins:
        s = state["mask"] & (d >= lo) & (d < hi)
        if not s.any():
            continue
        frac = float(np.mean(c[s] > 2 * C_TRUE))
        print("  %14s %8d %12.3f %12.3g %12.3f"
              % ("%.0f - %.0f" % (lo, hi), int(s.sum()), np.median(c[s]),
                 c[s].max(), frac))
        prof_x.append(0.5 * (lo + min(hi, 40.0)))
        prof_y.append(np.median(c[s]))
    print()
    # 対照群: 源を 1 つにする
    truth1 = (_RA - _offset(TH)) / C_TRUE
    ts1, vol1 = make_volume(DT_BASE, float(truth1.max()) + 6.0, single=True)
    est1 = estimate_arrival(ts1, vol1)
    m1 = (_RA > R_MIN) & est1["ok"]
    gy1, gx1 = np.gradient(est1["linear"])
    c1 = 1.0 / np.maximum(np.hypot(gy1, gx1), 1e-12)
    print("  ★対照群(源 1 つ、合流線が存在しない):")
    print("     同じ推定器で c の中央値 %.4f / 99 %% 点 %.3f / **最大 %.3f**"
          % (np.median(c1[m1]), np.percentile(c1[m1], 99), c1[m1].max()))
    print("     → 発散は推定器の欠陥ではなく、**面が折れているから**起きる。")
    print("     合流線は r_A - r_B = c·Δt_点火 の双曲線なので、撮影前に紙の上で")
    print("     引ける。「ここは測れない」を先に地図にしておける、という意味。")
    # 法線から出した速度も同じ場所で壊れるか
    near = speed["d_lead"] < 2.0
    if near.any():
        print("     頂点法線から出した速度も同じ場所で壊れる(最大 %.3g px/ms)。"
              % speed["c_norm"][near].max())

    if figs.enabled():
        series = [("勾配から(中央値)", np.array(prof_x), np.array(prof_y)),
                  ("真値 c", np.array(prof_x), np.full(len(prof_x), C_TRUE))]
        figs.save_plot("merge_line_speed", series,
                       xlabel="予測した合流線からの距離 [px]",
                       ylabel="推定した伝播速度 [px/ms]",
                       title="合流線に近づくと速度が壊れる",
                       caption="各帯の中央値。最も内側の帯(0-2 px)では最大 1e12 px/ms"
                               "まで飛ぶので、図は中央値だけを描いている。")


def section8_steepest_rise(state: dict) -> None:
    print()
    print("=" * 78)
    print("8) ★もう 1 つの「到達」の定義 —— 最急上昇(fs.vol_edge_probe)")
    print("=" * 78)
    print("  しきい値の定義は振幅が変わると時刻が動く。**最急上昇**(dI/dt の極大)")
    print("  なら振幅に依らない。真値は u = σ、つまり t = (r - w)/c。")
    print("  代わりに**平滑化した量だけ時刻が手前へずれる**: 実効幅は")
    print("  σ_eff = sqrt(σ_t² + σ_smooth²) で、ピークは t_peak - σ_eff に来る。")
    print()
    ts, vol = state["ts"], state["vol"]
    dt = float(ts[1] - ts[0])
    # 源 A の波面だけが先に届く帯(row=20 の列 20〜78)。合流の向こう側を
    # 混ぜると「最初の立ち上がり」が源 B のものになり、真値の式が変わる。
    row, cols = 20, np.arange(20, 80, 3)
    assert np.all(_MERGE[row, cols] < 0.0), "源 B が先に届く列が混ざった"
    sigma_t = W_FRONT / C_TRUE / dt      # フレーム単位
    print("  probe は row=%d の列 %d〜%d(源 A が先に届く帯)。%d 本。"
          % (row, cols[0], cols[-1], cols.size))
    print()
    print("  %10s | %13s %13s %13s"
          % ("平滑 σ", "予測ずれ ms", "実測ずれ ms", "散らばり ms"))
    print("  " + "-" * 56)
    base = None
    for sg in [0.0, 0.5, 1.0, 2.0, 3.0]:
        got, want = [], []
        for cx in cols:
            edges = fs.vol_edge_probe(vol, (0, row, cx), (ts.size - 1, row, cx),
                                      sigma=sg, threshold=0.05)
            rise = [e for e in edges if e["polarity"] > 0]
            if not rise:
                continue
            got.append(rise[0]["t_mm"] * dt)
            want.append((_RA[row, cx] - W_FRONT) / C_TRUE)
        d = np.asarray(got) - np.asarray(want)
        s_eff = np.sqrt(sigma_t ** 2 + sg ** 2)
        pred = -(s_eff - sigma_t) * dt
        if base is None:
            base = float(d.mean())
        print("  %10.1f | %13.4f %13.4f %13.4f"
              % (sg, pred, d.mean(), d.std()))
    print()
    print("  → 平滑を強めるほど時刻が手前へずれ、**向きも桁も予測どおり**")
    print("     (σ=2 で予測 -1.000 / 実測 -1.056)。")
    print("     ただし σ=0 でも %+.3f ms 残る —— 3 点放物線をガウス微分の" % base)
    print("     ローブに当てているぶんの偏りで、これは平滑では説明できない。")
    print("     この残差を引いてから比べても、σ=3 で予測 -1.854 / 実測 -1.570 と")
    print("     15 % ずれる。**式は当たりを付けるためのもので、較正の代わりに")
    print("     はならない**。")
    print("     ★しきい値の定義はオフセットが閉形式、最急上昇の定義は較正が要る。")
    print("     振幅不変と引き換えに、時刻の絶対値を捨てている。")


def section9_interference(state: dict, truth: np.ndarray) -> None:
    print()
    print("=" * 78)
    print("9) 干渉(和)の対照群 —— 合流線の上だけ到達が早まる")
    print("=" * 78)
    ts, vol_sum = make_volume(DT_BASE, float(truth.max()) + 6.0, mode="sum")
    est_s = estimate_arrival(ts, vol_sum)
    lin_max = state["est"]["linear"]
    m = state["mask"] & est_s["ok"]
    d = np.abs(_MERGE)
    print("  I = s_A + s_B にすると、合流付近では 2 つの半分が足し合わさって")
    print("  しきい値を早く超える。max との差を距離帯ごとに:")
    print()
    print("  %14s %8s %14s %14s" % ("合流線から px", "画素数", "ずれ中央値 ms", "最大 ms"))
    print("  " + "-" * 54)
    for lo, hi in [(0, 3), (3, 6), (6, 12), (12, 25), (25, 400)]:
        s = m & (d >= lo) & (d < hi)
        if not s.any():
            continue
        dd = (est_s["linear"] - lin_max)[s]
        print("  %14s %8d %14.4f %14.4f"
              % ("%d - %d" % (lo, hi), int(s.sum()), float(np.median(dd)),
                 float(dd[np.argmax(np.abs(dd))])))
    print()
    print("  → 合流線の上で **%.2f ms 早い**(Δt = %.1f ms の半分より大きい)。"
          % (abs(float(np.median((est_s["linear"] - lin_max)[m & (d < 3)]))), DT_BASE))
    print("     12 px 離れれば 0.003 ms 以下。**局所的で系統的な偏り**なので、")
    print("     速度を勾配で出すとこの偏りが「速度の嘘」に化ける。")
    print("     この PoC が I = max を選んだのは、真値を閉形式に保つため。")
    print("     実測の波では和のほうが正しいので、**合流付近の到達時刻は")
    print("     そもそも定義できない**と考えるのが正しい。")


def section10_figures(truth: np.ndarray, state: dict, t_mc: np.ndarray) -> None:
    if not figs.enabled():
        return
    lin = state["est"]["linear"]
    m = state["mask"]
    show_t = np.where(m, truth, 0.0)
    show_e = np.where(m, lin - truth, 0.0)
    # 差分は合流線の近くだけ大きいので分位点で切る(caption に明記)。
    lim = float(np.percentile(np.abs(show_e[m]), 99.0))
    figs.save_grid("arrival_surface",
                   [show_t, np.where(m, lin, 0.0), np.clip(show_e, -lim, lim)],
                   ["真値 T", "線形補間", "差"], ncols=3,
                   signed=[False, False, True],
                   title="到達時刻面(源 2 つ、合流線あり)",
                   caption="差は上下 99 %% 分位(±%.4f ms)で切った。同心円の縞は"
                           "**フレーム格子に同期した系統誤差**(サブピクセルの"
                           "peak locking と同じ型)。" % lim)
    assert t_mc is not None


def section11_tool_gaps(state: dict) -> None:
    print()
    print("=" * 78)
    print("10) 道具の穴(3-D の等値面・法線・勾配を (t,y,x) に使ってみて)")
    print("=" * 78)

    # (a) 「体積から到達時刻面を出す」口は無い。等値面はあるが、面から
    #     各柱の最小 t を拾うところは呼び手が書く。
    for nm in ("arrival_time", "isochrone", "first_crossing", "threshold_time"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (a) 体積 (t,y,x) から**到達時刻面**を返す op が無い"
          "(arrival_time / isochrone / first_crossing のどれも 3 層に無い)。")
    print("      marching_cubes → 時間軸稜線の頂点 → 柱ごとの最小 t、は毎回自前。")

    # (b) marching_cubes は等方 index 空間しか返さない(spacing を渡せない)。
    import inspect
    sig = inspect.signature(fs.marching_cubes)
    assert list(sig.parameters) == ["vol", "level"], sig
    print("  (b) fs.marching_cubes(vol, level) は **spacing を受け取らない**。")
    print("      (t,y,x) のように軸で単位が違う体積では、呼び手が頂点へ Δt を")
    print("      掛ける。掛け忘れても例外にならず、法線と速度だけが静かにずれる。")

    # (c) 台帳の 3-D 勾配も等方。時間軸だけ別の spacing を渡せない。
    sig3 = str(inspect.signature(fs.ledger.gradient3d))
    assert "spacing" not in sig3, sig3
    assert not hasattr(fs, "gradient3d"), "ファサードに出た(この節を書き換える)"
    print("  (c) fs.ledger.gradient3d も spacing 引数が無く、しかも**ファサードに")
    print("      出ていない**(fs.gradient3d は無い)。vol_gradient_magnitude は")
    print("      両方に在るのに大きさしか返さない —— ベクトルが要ると台帳へ降りる。")

    # (d) vol_edge_probe の返り値のキーが物理単位に固定されている。
    ts, vol = state["ts"], state["vol"]
    e = fs.vol_edge_probe(vol, (0, N // 2, 30), (ts.size - 1, N // 2, 30),
                          sigma=1.0, threshold=0.05)
    assert e and "t_mm" in e[0], list(e[0]) if e else e
    print("  (d) fs.vol_edge_probe の返り値のキーが **`t_mm`**。時間軸に当てると")
    print("      単位名が嘘になる(値は ms)。`t` か `abscissa` にしてほしい。")

    # (e) 等値面のシートを分ける口が無い(前縁/後縁)。
    for nm in ("mesh_split_sheets", "surface_sheets", "mesh_components"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (e) 閉じた等値面を**連結成分に割る**口が無い(2-D の blob_label に")
    print("      当たるものがメッシュ側に無い)。前縁と後縁が 1 つのメッシュで返る。")

    # (f) 1/|∇T| = 速度、という eikonal の口も無い(自前 2 行だが名前が要る)。
    assert not hasattr(fs, "eikonal_speed") and not hasattr(fs.ledger, "eikonal_speed")
    print("  (f) |∇T| から局所速度を出す op(eikonal の逆問題)が無い。2 行だが、")
    print("      **0 割りの扱い**をどこかに 1 つ決めておかないと、7 章の発散が")
    print("      呼び手ごとに違う値(inf / 1e12 / clip)になる。")

    # (g) 在って助かったもの(見落とし防止に明記)
    assert hasattr(fs, "time_surface") and hasattr(fs, "spatiotemporal_gaussian")
    assert hasattr(fs, "temporal_gradient")
    print("  (g) 在って助かった: marching_cubes / ledger.vertex_normals /")
    print("      ledger.gradient3d / vol_edge_probe / vol_profile_line /")
    print("      time_surface / spatiotemporal_gaussian / temporal_gradient。")
    print("      **(t,y,x) を体積として扱う道具は一通り在る** —— 足りないのは")
    print("      「時間軸だけ単位が違う」という契約と、到達時刻という出口。")


def main() -> None:
    t0 = time.perf_counter()
    print("poc_xyt_event_surface — 到達時刻面を (x, y, t) の等値面として取り出す")
    print("(2-D の場面を時系列に変化させて 3-D にする。真値は閉形式)")
    print()
    truth = section1_scene()
    state = section2_zero_point(truth)
    section3_dt_sweep(truth)
    section4_threshold(truth)
    t_mc = section5_isosurface(state, truth)
    speed = section6_speed(state, truth)
    section7_merge_line(state, speed)
    section8_steepest_rise(state)
    section9_interference(state, truth)
    section10_figures(truth, state, t_mc)
    section11_tool_gaps(state)
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
