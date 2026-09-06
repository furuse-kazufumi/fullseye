# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_surface_roughness — 表面粗さパラメータ(Sa / Sq / Sz / Ssk / Sku)は
**どこまで標本化とカットオフに耐えるか**を、真値を自分で仕込んで数字にする PoC。

    py -3.11 examples/poc_surface_roughness.py

【この PoC が答える問い】
粗さの合否判定でいちばん素朴な問い —「同じ表面を測ったのに、装置を替えたら
Sz が 2 倍になった。どちらが正しいのか」。答えは「どちらも正しく、Sz が
**表面の性質ではなく測り方の性質**を大きく含んでいる」。それを、真値が分かって
いる合成表面で桁ごとに示す。

【グラウンドトゥルース(自分で仕込んだ真値)】
高さ場を **指定した PSD(パワースペクトル密度)から合成**する。各モードの振幅を
固定して位相だけ乱数にすると、Parseval からその実現の分散が **位相によらず
解析的に決まる**。つまり Sq の真値が計算で出る(1 節でその一致を確認する)。
そこへ以下を足して「現実の測定対象」にする:

  * 平面の傾き(取り付け誤差)      —— 粗さではない、除くべきもの
  * うねり(waviness、λ=256 µm)   —— 粗さではない、除くべきもの
  * 加工目(lay、λ=32 µm の周期)  —— 粗さ、残すべきもの
  * 孤立した深い傷(4 本、深さ 3 µm)—— 粗さ、残すべきもの。**片側に寄せてある**

乱数だけの高さ場にしないのは、Sz と Sku の弱点がガウス乱数では隠れるから。
周期成分は「カットオフのどちら側か」を、孤立した傷は「極値統計」と
「ロバストでない当てはめ」を叩く。

【節立て】
 1) 合成器の検算 —— 解析 Sq と実現 Sq が一致するか(ゼロ点その 0)
 2) ★ゼロ点 —— 生の rms をそのまま Sq と呼ぶとどれだけ間違うか
 3) ★標本間隔の掃引 —— どのパラメータが先に壊れるか(順位表)
 4) ★評価領域の掃引 —— Sz は「どれだけ長く見たか」を測っている
 5) カットオフ掃引(λc / λs)—— どちら側に何が居るか
 6) 傾き除去 —— 最小二乗平面 vs ロバスト(RANSAC)。傷が基準を汚す量
 7) 1-D と 2-D の食い違い —— Rz は断面の取り方で何倍振れるか
 8) 順位表と所見

【結果の要点(本文の print が正、以下は道しるべ)】
- 生の rms を Sq と呼ぶと 20 倍の過大(Sa は 27 倍、Sz は 6.4 倍、Ssk は
  -2.8 が +0.05 に反転)。平面だけ除いてもまだ 1.8 倍ずれる。**「粗さ」は
  帯域の宣言とセットでしか数字にならない** —— この PoC では真値そのものを
  「λc で切ったあとの粗さ」として定義している(そう定義しないと、正しい手順で
  測っても -23% ずれ、それが標本化の誤差と混ざる)。
- 標本間隔に弱い順は Sz ≪ Sa < Ssk ≈ Sku < Sq。**Sq が最も強い**のは
  エイリアシングがエネルギーを折り返すだけで 2 次モーメントを保つから。
  dx = 8 µm で Sa 誤差 -3.5% / Sz 誤差 -19.8% —— **同じデータで Sa は ±5%
  合格、Sz は不合格**になる。
- Sz は評価領域を広げると単調に増える。ガウス極値の 2√(2 ln M) は増え方を
  当てる(実測/予測が窓によらず 0.52 前後で一定)が、絶対値は 1.9 倍外す
  (面に相関があり独立標本数が点数より少ない)。**頭打ちにならないので
  「真の Sz」は存在しない。**
- 片側に寄せた傷は最小二乗平面を傾け、Sq を 1.9% 過小にする(RANSAC は
  0.33%)。ただし効くのは深さでなく**面積比**で、λc を後段に置くと差は消える。
- λs は「尖りだけ削る」という予想が外れた。雑音の無い面では比例して全部削る。
  白色雑音を足して初めて選択性(Sq +3.4% に対し Sz +20%)が出る。
- 加工目に直交する断面の Rq は平行な断面の 3.4 倍。Rz は断面 1 本で 23 倍
  振れ、面の Sz の 8 割に届くのは 128 本中 3 本。**Rz は断面 1 本では
  決まらない。**

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 合成表面の諸元(すべて µm)--------------------------------------------- #
N = 512                 # 画素数(正方)
DX = 1.0                # 標本間隔 µm
L = N * DX              # 評価領域の一辺 512 µm

HURST = 0.8             # 自己アフィン指数。PSD ∝ q^(-2(H+1))
Q_LO = 1.0 / 64.0       # PSD の下端(波長 64 µm)
Q_HI = 0.5              # PSD の上端(波長 2 µm = Nyquist)
SQ_PSD = 0.080          # PSD 成分だけの Sq

LAY_LAMBDA = 32.0       # 加工目の波長。行方向に走る溝(高さは y だけの関数)
LAY_AMP = 0.25          # 加工目の振幅(rms は AMP/√2 = 0.1768)

WAV_LAMBDA = 256.0      # うねりの波長(粗さではない)
WAV_AMP = 0.60

TILT_X, TILT_Y = 0.050, -0.025     # 取り付けの傾き(rad 相当の勾配)

SCRATCH_DEPTH = 3.0     # 孤立した傷の深さ
SCRATCH_HW = 4.0        # 傷の半値半幅 µm
LAMBDA_C = 80.0         # 既定の低域カットオフ(粗さ / うねりの境)
ALPHA = math.sqrt(math.log(2.0) / math.pi)   # ガウスフィルタの規約定数 0.46972
SEED = 20260906

PARAMS = ("Sa", "Sq", "Sz", "Ssk", "Sku")


# --------------------------------------------------------------------------- #
# 合成                                                                          #
# --------------------------------------------------------------------------- #
def synth_psd_surface(n, dx, hurst, q_lo, q_hi, seed):
    """指定した PSD から高さ場を合成する。戻り値 (高さ場, 解析 Sq)。

    各モードの **振幅を固定し位相だけ乱数**にするのが要点。位相を
    ``phi[-k] = -phi[k]`` に反対称化すると係数がエルミートになり、逆変換が
    厳密に実になる。このとき Parseval から

        <h²> = (1/n⁴) Σ_k A_k²

    が **位相の引き方によらず**成り立つ。つまり Sq の真値が乱数に依存しない。
    ここを「乱数を振って rms を測る」で済ませると、真値そのものが実現ごとに
    ばらついて、後の掃引の誤差と区別できなくなる。

    ★ 反対称化のしかたで一度間違えた(この PoC で最初に出たバグ)。
    ``phi = (u - u[-k]) / 2`` は確かに反対称だが、**位相が一様でなくなる**
    (三角分布になって 0 の近くに寄る)。すると全モードが原点で同位相に足され、
    高さ場に 1 本のスパイクが立つ。実測では range/rms = 56、尖度 87 —— 自己
    アフィン面なら 10 前後、3 前後になるはずの量。Sq は解析値と一致したまま
    なので、**Sq だけ見ていたら気づけなかった**。正しくは共役対の片方だけに
    一様乱数を引き、もう片方はその符号を反転して置く(下の実装)。
    """
    f = np.fft.fftfreq(n, d=dx)
    q = np.hypot(f[:, None], f[None, :])
    amp = np.zeros_like(q)
    band = (q >= q_lo) & (q <= q_hi)
    amp[band] = q[band] ** (-(hurst + 1.0))          # √PSD ∝ q^-(H+1)

    rng = np.random.default_rng(seed)
    raw = rng.uniform(-np.pi, np.pi, (n, n))
    neg = (-np.arange(n)) % n                        # k -> -k の添字写像
    ii, jj = np.mgrid[0:n, 0:n]
    ni, nj = neg[ii], neg[jj]
    # 共役対 (k, -k) の「片方だけ」を辞書式順序で選ぶ。等しい要素(k = -k)は
    # 自己共役なので係数が実でなければならず、位相を 0 に固定する。
    half = (ii < ni) | ((ii == ni) & (jj < nj))
    selfc = (ii == ni) & (jj == nj)
    phi = np.where(half, raw, -raw[ni, nj])
    phi[selfc] = 0.0

    coef = amp * np.exp(1j * phi)
    h = np.fft.ifft2(coef).real
    sq_analytic = float(np.sqrt(np.sum(amp ** 2)) / n ** 2)
    return h, sq_analytic


def make_components(seed=SEED):
    """表面を成分ごとに作って返す(足し合わせるのは呼び出し側)。"""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64) * DX

    psd, sq_an = synth_psd_surface(N, DX, HURST, Q_LO, Q_HI, seed)
    psd *= SQ_PSD / psd.std()                        # 目標 Sq へ規格化

    # 加工目: 高さは y だけの関数 = 溝が行方向(x 方向)に走る。
    # 「断面をどの向きで取るか」で答えが変わる状況を作るためにわざと異方にする。
    lay = LAY_AMP * np.cos(2.0 * np.pi * yy / LAY_LAMBDA)

    # 孤立した深い傷 —— 4 本、すべて x > 0.55 L の側に寄せる。
    # 片側に寄せるのは「最小二乗平面が傷に引かれる」を見るため。
    scratch = np.zeros((N, N))
    for (x0, y0, x1, y1) in ((300.0, 60.0, 430.0, 300.0),
                             (340.0, 340.0, 470.0, 460.0),
                             (390.0, 40.0, 400.0, 380.0),
                             (300.0, 430.0, 480.0, 400.0)):
        d = _dist_to_segment(xx, yy, x0, y0, x1, y1)
        scratch -= SCRATCH_DEPTH * np.exp(-0.5 * (d / SCRATCH_HW) ** 2)

    wav = WAV_AMP * np.cos(2.0 * np.pi * xx / WAV_LAMBDA + 0.7) \
        + 0.35 * WAV_AMP * np.cos(2.0 * np.pi * yy / WAV_LAMBDA)
    tilt = TILT_X * xx + TILT_Y * yy
    return dict(psd=psd, lay=lay, scratch=scratch, wav=wav, tilt=tilt,
                sq_analytic=sq_an, xx=xx, yy=yy)


def _dist_to_segment(xx, yy, x0, y0, x1, y1):
    """格子点から線分 (x0,y0)-(x1,y1) までの距離。"""
    vx, vy = x1 - x0, y1 - y0
    ln = vx * vx + vy * vy
    t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / ln, 0.0, 1.0)
    return np.hypot(xx - (x0 + t * vx), yy - (y0 + t * vy))


# --------------------------------------------------------------------------- #
# フィルタ(ガウス、透過率 exp(-π (α λ f)²))                                   #
# --------------------------------------------------------------------------- #
def _transmission(q, lam):
    return np.exp(-np.pi * (ALPHA * lam * q) ** 2)


def areal_filter(h, dx, lam, kind):
    """面のガウスフィルタ。kind="high" が粗さ抽出、"low" が λs 側。

    循環畳み込み(FFT)なので、**呼ぶ前に傾きを除いておく**こと。傾きが残った
    まま掛けると端で巻き込みが起きて、フィルタの性質ではなく端の性質を測る。
    """
    n0, n1 = h.shape
    fy = np.fft.fftfreq(n0, dx)[:, None]
    fx = np.fft.rfftfreq(n1, dx)[None, :]
    t = _transmission(np.hypot(fy, fx), lam)
    coef = np.fft.rfft2(h)
    coef = coef * (t if kind == "low" else (1.0 - t))
    return np.fft.irfft2(coef, s=h.shape)


def profile_filter(p, dx, lam, kind):
    """1-D 断面のガウスフィルタ(規約は面と同じ)。"""
    f = np.fft.rfftfreq(p.size, dx)
    t = _transmission(f, lam)
    coef = np.fft.rfft(p)
    coef = coef * (t if kind == "low" else (1.0 - t))
    return np.fft.irfft(coef, n=p.size)


# --------------------------------------------------------------------------- #
# パラメータ                                                                    #
# --------------------------------------------------------------------------- #
def areal_params(z):
    """Sa / Sq / Sz / Ssk / Sku。z は平均を引いてから評価する。"""
    z = np.asarray(z, dtype=np.float64)
    z = z - z.mean()
    sq = float(np.sqrt(np.mean(z ** 2)))
    return {"Sa": float(np.mean(np.abs(z))),
            "Sq": sq,
            "Sz": float(z.max() - z.min()),
            "Ssk": float(np.mean(z ** 3) / sq ** 3),
            "Sku": float(np.mean(z ** 4) / sq ** 4)}


def profile_params(p):
    """Ra / Rq / Rz。**Rz はここでは評価長さ全体の最大高低差**(= Rt)とする。

    ISO 4287 の Rz は基準長さ 5 区間の平均だが、それだと Sz(評価面全体の
    最大高低差)と定義が揃わず「1-D と 2-D の食い違い」が定義差なのか
    標本化差なのか分からなくなる。**揃えたうえで比べる**。
    """
    p = np.asarray(p, dtype=np.float64)
    p = p - p.mean()
    return {"Ra": float(np.mean(np.abs(p))),
            "Rq": float(np.sqrt(np.mean(p ** 2))),
            "Rz": float(p.max() - p.min())}


def rel_err(val, truth):
    return (val - truth) / abs(truth)


def fmt_row(label, d, width=12):
    return f"  {label:<26}" + "".join(f"{d[k]:>{width}.4f}" for k in PARAMS)


def head(width=12):
    return f"  {'':<26}" + "".join(f"{k:>{width}}" for k in PARAMS)


def head_err(width=12):
    return f"  {'':<26}" + "".join(f"{k + ' err%':>{width}}" for k in PARAMS)


# --------------------------------------------------------------------------- #
def main():
    t_all = time.perf_counter()
    C = make_components()
    psd, lay, scratch, wav, tilt = (C["psd"], C["lay"], C["scratch"],
                                    C["wav"], C["tilt"])

    # 「粗さ」と呼ぶべき成分(真値の定義)。傾きとうねりは含めない。
    rough_true = psd + lay + scratch
    surface = rough_true + wav + tilt          # 測定器が実際に見る面
    # ★真値は **帯域を宣言したうえで** 定義する。粗さ成分そのものではなく、
    #   「λc で切ったあとの粗さ成分」が真値。ここを生の rough_true にすると、
    #   正しい手順で測っても -23% ずれ、その 23% が標本化の誤差と混ざる。
    #   帯域を含まない「粗さの真値」は存在しない —— これが 2 節の主張でもある。
    rough_band = areal_filter(rough_true, DX, LAMBDA_C, "high")
    truth = areal_params(rough_band)

    # ---------------------------------------------------------------- 1 --- #
    print("=== 1. 合成器の検算 —— PSD の積分と実現の rms は一致するか ===")
    psd_raw, sq_an = synth_psd_surface(N, DX, HURST, Q_LO, Q_HI, SEED)
    sq_real = float(psd_raw.std())
    print(f"  解析 Sq(Σ A² / n⁴ の平方根) = {sq_an:.12e}")
    print(f"  実現 Sq(配列の rms)        = {sq_real:.12e}")
    print(f"  相対差                       = {abs(sq_real / sq_an - 1):.3e}"
          "  ← 位相の乱数に依存しない。これがこの PoC の真値の根拠")
    # 位相の種を変えても解析値は動かない(振幅固定なので当然だが、確かめる)
    spread = [synth_psd_surface(N, DX, HURST, Q_LO, Q_HI, s)[0].std()
              for s in (1, 2, 3, 4, 5)]
    print(f"  種を 5 通り振った実現 Sq の幅 = {max(spread) - min(spread):.3e}"
          f"(平均 {np.mean(spread):.6e})")

    # `radial_power_spectrum` の正規化規約は docstring に書かれていない。
    # H を 2 通り仕込んで傾きを測れば、どちらの規約かが実験で決まる。
    print("\n  `fs.radial_power_spectrum` の規約を実験で決める(docstring に無い)")
    print(f"  {'仕込んだ H':>10}{'面 PSD 予想':>13}{'動径 PSD 予想':>14}"
          f"{'実測の傾き':>12}{'戻した H':>10}{'H の誤差':>10}")
    slope, h_err = None, {}
    for h_true in (0.5, HURST):
        raw_h, _ = synth_psd_surface(N, DX, h_true, Q_LO, Q_HI, SEED)
        freqs, power = fs.radial_power_spectrum(raw_h)
        band = (freqs >= 2.0 * Q_LO * DX) & (freqs <= 0.4) & (power > 0)
        sl = float(np.polyfit(np.log(freqs[band]), np.log(power[band]), 1)[0])
        h_back = -sl / 2.0 - 1.0
        h_err[h_true] = h_back - h_true
        if h_true == HURST:
            slope = sl
        print(f"  {h_true:>10.2f}{-2 * (h_true + 1):>13.3f}"
              f"{-2 * (h_true + 1) + 1:>14.3f}{sl:>12.3f}{h_back:>10.3f}"
              f"{h_back - h_true:>+10.3f}")
    print("  → 傾きは **面 PSD(環内の |F|² の平均)の規約**に乗る。動径 1-D PSD"
          "(+1 したもの)ではない。つまり H = -傾き/2 - 1 で読める。")
    print(f"     ただし戻した H は真値より一律 {abs(h_err[HURST]):.3f} 低い"
          f"({100 * abs(h_err[HURST]) / HURST:.1f}%)。当てはめ帯域を狭めても"
          "動かないので統計誤差ではなく、環平均の離散化による系統誤差。")
    print("     **規約が書いてあれば較正なしで読める** —— 書いていないので"
          "毎回この検算をやる羽目になる(所見 (C))。")

    print("\n  成分の内訳(それぞれ単独の rms / 最大高低差、µm)")
    print(f"  {'成分':<20}{'rms':>12}{'max-min':>12}   扱い")
    for name, arr, role in (("PSD(自己アフィン)", psd, "粗さ"),
                            ("加工目 λ=32µm", lay, "粗さ"),
                            ("孤立した傷 4 本", scratch, "粗さ"),
                            ("うねり λ=256µm", wav, "うねり(除く)"),
                            ("取り付けの傾き", tilt, "形状(除く)")):
        print(f"  {name:<20}{arr.std():>12.4f}{arr.max() - arr.min():>12.4f}   {role}")
    print(f"  {'粗さ = 上 3 つの和':<20}{rough_true.std():>12.4f}"
          f"{rough_true.max() - rough_true.min():>12.4f}")
    print(f"  {'  を λc=%.0fµm で切る' % LAMBDA_C:<20}{rough_band.std():>12.4f}"
          f"{rough_band.max() - rough_band.min():>12.4f}   ← これが真値")
    print("  ※ 帯域を宣言しない『粗さの真値』は存在しない。切る前と後で rms が"
          f" {100 * (rough_band.std() / rough_true.std() - 1):+.0f}% 違う。")

    print("\n  真値(帯域を正しく切ったときの答え)")
    print(head())
    print(fmt_row("真値 Sa/Sq/Sz/Ssk/Sku", truth))
    print("  Ssk が負・Sku が大きいのは 4 本の深い傷のせい。ガウス乱数だけの面なら"
          " Ssk≈0, Sku≈3 で、この 2 つは何も言わない指標になってしまう。")
    # 高さは符号つきの量なので発散 LUT で塗る(0 = 平均面がどこかが分かる)。
    figs.save_grid("surface_components", [surface, rough_band, wav + tilt],
                   ["測定器が見る面(Sq %.3f µm)" % surface.std(),
                    "粗さの真値 = λc %.0fµm で切った後(Sq %.3f)"
                    % (LAMBDA_C, rough_band.std()),
                    "除くべき うねり + 傾き(Sq %.3f)" % (wav + tilt).std()],
                   title="同じ面から「粗さ」を取り出す", ncols=3, signed=True,
                   caption="左の面をそのまま rms すると真値の %.0f 倍になる。"
                           "帯域を宣言しない粗さの数字は存在しない。"
                           % (surface.std() / rough_band.std()))

    # ---------------------------------------------------------------- 2 --- #
    print("\n=== 2. ★ゼロ点 —— 生の rms をそのまま Sq と呼ぶとどうなるか ===")
    zero_rows = []
    zero_rows.append(("(0) 生の高さ場そのまま", areal_params(surface)))
    # 最小二乗平面(傷を含む全点)で傾きだけ除去
    resid_ls = _plane_removed(surface, C["xx"], C["yy"], robust=False)[0]
    zero_rows.append(("(1) 最小二乗平面を除去", areal_params(resid_ls)))
    # 平面 + λc ハイパス = 正しい手順
    rough_meas = areal_filter(resid_ls, DX, LAMBDA_C, "high")
    zero_rows.append((f"(2) + λc={LAMBDA_C:.0f}µm ハイパス", areal_params(rough_meas)))
    zero_rows.append(("真値", truth))
    print(head())
    for lab, d in zero_rows:
        print(fmt_row(lab, d))
    print(head_err())
    for lab, d in zero_rows[:-1]:
        cells = "".join(f"{100 * rel_err(d[k], truth[k]):>12.1f}" for k in PARAMS)
        print(f"  {lab:<26}{cells}")
    print(f"  → 生 rms は Sq を {areal_params(surface)['Sq'] / truth['Sq']:.0f} 倍に、"
          f"平面だけ除いても {areal_params(resid_ls)['Sq'] / truth['Sq']:.1f} 倍に見せる。")
    print(f"     Ssk は真値 {truth['Ssk']:+.2f}(深い傷のある面)に対し生の面では "
          f"{areal_params(surface)['Ssk']:+.2f}、Sku は {truth['Sku']:.1f} に対し "
          f"{areal_params(surface)['Sku']:.1f}。**符号も桁も変わる** —— うねりと傾きが"
          "支配すると分布は一様に近づき、傷の情報が完全に消える。")
    print("     いちばん派手に外すのは Sa(+2650%)で、いちばん小さいのは Sku。"
          "つまり **『どれを見れば安全か』という逃げ道は無い** —— 帯域を宣言"
          "しないまま出した数字は、パラメータの選び方では救えない。")

    # ---------------------------------------------------------------- 3 --- #
    print("\n=== 3. ★標本間隔の掃引 —— どれが先に壊れるか ===")
    print("  手順は毎回同じ: 生の面を間引く → 傾きを厳密に除く → λc ハイパス → 評価。")
    print("  『点で拾う』(間引き)と『面で平均する』(ビン平均 = 有限スポット)を並べる。")
    factors = (1, 2, 4, 8, 16)
    samp = {"point": {}, "box": {}}
    print("\n  [点標本化] " + head()[2:])
    for f in factors:
        s = _decimate(surface, f, "point")
        d = areal_params(_pipeline(s, DX * f))
        samp["point"][f] = d
        print(fmt_row(f"dx={DX * f:>4.0f}µm  n={N // f}²", d))
    print(head_err())
    for f in factors:
        d = samp["point"][f]
        cells = "".join(f"{100 * rel_err(d[k], truth[k]):>12.1f}" for k in PARAMS)
        print(f"  {'dx=%.0fµm' % (DX * f):<26}{cells}")

    print("\n  [面平均(ビン平均)] " + head_err()[2:])
    for f in factors:
        s = _decimate(surface, f, "box")
        d = areal_params(_pipeline(s, DX * f))
        samp["box"][f] = d
        cells = "".join(f"{100 * rel_err(d[k], truth[k]):>12.1f}" for k in PARAMS)
        print(f"  {'dx=%.0fµm' % (DX * f):<26}{cells}")

    # 崖 = |相対誤差| が 10% を超える最初の間引き率
    cliff = {}
    for k in PARAMS:
        hit = [f for f in factors if abs(rel_err(samp["point"][f][k], truth[k])) > 0.10]
        cliff[k] = hit[0] if hit else None
    order = sorted(PARAMS, key=lambda k: (cliff[k] is None, cliff[k] or 99))
    print("\n  崖(|相対誤差| が 10% を超える最初の標本間隔、点標本化)")
    print(f"  {'順位':<6}{'パラメータ':<12}{'崩れる dx':>12}{'そこでの誤差':>16}")
    for i, k in enumerate(order, 1):
        if cliff[k] is None:
            print(f"  {i:<6}{k:<12}{'崩れず':>12}"
                  f"{100 * rel_err(samp['point'][factors[-1]][k], truth[k]):>15.1f}%"
                  f"  (dx=16µm でも)")
        else:
            print(f"  {i:<6}{k:<12}{'%.0f µm' % (DX * cliff[k]):>12}"
                  f"{100 * rel_err(samp['point'][cliff[k]][k], truth[k]):>15.1f}%")
    # 5 本を 1 枚に載せると「先に落ちるのは Sz」が線の分かれ方で見える。
    dx_ax = np.array([DX * f for f in factors])
    figs.save_plot("sampling_cliff",
                   [(k, dx_ax,
                     np.array([100 * rel_err(samp["point"][f][k], truth[k])
                               for f in factors])) for k in PARAMS],
                   xlabel="標本間隔 [µm]", ylabel="相対誤差 [%]",
                   title="標本間隔の掃引 —— 先に落ちるのは Sz",
                   caption="dx=8 µm では Sa が ±5 % 合格で Sz が不合格。"
                           "同じデータでも見るパラメータで結論が反転する。")
    print("  → 弱い順に並べると " + " < ".join(order) + " (左ほど早く壊れる)。")
    print("     Sz が先に落ちるのは、深い傷の底が『たまたま標本点に乗るか』で"
          "決まる**極値**だから。Sa は面全体の積分なので鈍い。")

    # 「Sa は合格、Sz は不合格」になる条件
    tol_sa, tol_sz = 0.05, 0.05
    both = [f for f in factors
            if abs(rel_err(samp["point"][f]["Sa"], truth["Sa"])) < tol_sa
            and abs(rel_err(samp["point"][f]["Sz"], truth["Sz"])) > tol_sz]
    print(f"\n  ★同じデータで Sa が ±5% 合格・Sz が ±5% 不合格になる標本間隔: "
          + (", ".join("%.0f µm" % (DX * f) for f in both) if both else "無し"))
    if both:
        f = both[0]
        print(f"     dx={DX * f:.0f}µm で Sa 誤差 "
              f"{100 * rel_err(samp['point'][f]['Sa'], truth['Sa']):+.1f}% に対し "
              f"Sz 誤差 {100 * rel_err(samp['point'][f]['Sz'], truth['Sz']):+.1f}%。"
              "  **どちらの数字を見たかで結論が反転する。**")

    # ---------------------------------------------------------------- 4 --- #
    print("\n=== 4. ★評価領域の掃引 —— Sz は『どれだけ長く見たか』を測っている ===")
    print("  同じ標本間隔(1 µm)のまま、評価する窓の大きさだけ変える。")
    print("  傷ありの面と、傷を抜いた面の両方でやる(極値統計と外れ値を分けるため)。")
    rough_with = _pipeline(surface, DX)
    rough_without = _pipeline(rough_true - scratch + wav + tilt, DX)
    ratios = {}
    sz_curve = {}                       # 図用: 窓の大きさ -> Sz 平均 / 極値則の予測
    for tag, fld in (("傷あり", rough_with), ("傷なし", rough_without)):
        print(f"\n  [{tag}]  {'窓':>8}{'窓数':>7}{'Sz 平均':>11}{'Sz 最小':>11}"
              f"{'Sz 最大':>11}{'Sq 平均':>11}{'2√(2lnM)·Sq':>14}{'実測/予測':>11}")
        ratios[tag] = []
        for w in (32, 64, 128, 256, 512):
            wins = [fld[i:i + w, j:j + w]
                    for i in range(0, N, w) for j in range(0, N, w)]
            szs = np.array([float(v.max() - v.min()) for v in wins])
            sqs = np.array([float(v.std()) for v in wins])
            pred = 2.0 * math.sqrt(2.0 * math.log(w * w)) * float(sqs.mean())
            ratios[tag].append(float(szs.mean() / pred))
            sz_curve.setdefault(tag, []).append((w, float(szs.mean()), pred))
            print(f"  {'':8}{w:>8}{len(wins):>7}{szs.mean():>11.4f}{szs.min():>11.4f}"
                  f"{szs.max():>11.4f}{sqs.mean():>11.4f}{pred:>14.4f}"
                  f"{szs.mean() / pred:>11.3f}")
    rr = np.array(ratios["傷なし"])
    print("\n  → 傷なしなら Sz 平均は窓 32→512 で単調に増える。ガウス極値の"
          " 2√(2 ln M) は **増え方は当てるが絶対値を外す**: 実測/予測は"
          f" {rr.min():.3f}〜{rr.max():.3f} でほぼ一定"
          f"(ばらつき ±{100 * (rr.max() - rr.min()) / rr.mean() / 2:.0f}%)。")
    print("     一定倍率でずれるのは、面に相関があって**独立な標本の数が点数 M"
          "より少ない**から。log の中の M を実効値に直せば合う —— つまり"
          "「Sz は領域の対数でしか増えない」という形は正しい。")
    sz_small = float(np.mean([np.ptp(rough_without[i:i + 32, j:j + 32])
                              for i in range(0, N, 32) for j in range(0, N, 32)]))
    sz_full = float(np.ptp(rough_without))
    print(f"     結果として、領域を 256 倍(32²→512²)に広げても Sz は "
          f"{100 * (sz_full / sz_small - 1):.0f}% しか増えない —— "
          "が、確実に増える。**頭打ちにならないので『真の Sz』は存在しない。**")
    w = 64
    wins = [rough_with[i:i + w, j:j + w] for i in range(0, N, w) for j in range(0, N, w)]
    szs = np.array([float(v.max() - v.min()) for v in wins])
    hit = szs > 1.5 * np.median(szs)
    print(f"  → 傷ありは違う。窓 64 で {len(szs)} 個のうち {int(hit.sum())} 個"
          f"({100 * hit.mean():.0f}%)だけが傷を掴み、その窓の Sz は"
          f" {szs[hit].mean():.3f}、掴まなかった窓は {szs[~hit].mean():.3f}"
          f"({szs[hit].mean() / szs[~hit].mean():.1f} 倍)。")
    print("     分布が二山になっているので、Sz の平均も標準偏差も"
          "『表面の代表値』としての意味を失う。**Sz を報告するなら窓の大きさと"
          "窓の数を必ず添える。**")
    # 横軸は log2。極値則が「対数でしか増えない」形なので、この軸なら直線になる。
    figs.save_plot(
        "sz_vs_window",
        [("傷なし 実測", np.log2([v[0] for v in sz_curve["傷なし"]]),
          np.array([v[1] for v in sz_curve["傷なし"]])),
         ("傷なし 予測 2√(2lnM)·Sq", np.log2([v[0] for v in sz_curve["傷なし"]]),
          np.array([v[2] for v in sz_curve["傷なし"]])),
         ("傷あり 実測", np.log2([v[0] for v in sz_curve["傷あり"]]),
          np.array([v[1] for v in sz_curve["傷あり"]]))],
        xlabel="log2 窓の一辺 [px]", ylabel="Sz [µm]",
        title="Sz は「どれだけ長く見たか」を測っている",
        caption="頭打ちにならないので『真の Sz』は存在しない。"
                "極値則は増え方を当てるが絶対値は一定倍率で外す。")

    # ---------------------------------------------------------------- 5 --- #
    print("\n=== 5. カットオフ掃引 —— どちら側に何が居るか ===")
    print(f"  仕込んだ波長: 加工目 {LAY_LAMBDA:.0f}µm(粗さ側)/ "
          f"うねり {WAV_LAMBDA:.0f}µm(除く側)/ PSD は 2〜64µm。")
    print(f"  正しい λc はこの間、つまり 64〜128 µm。既定は {LAMBDA_C:.0f}µm。")
    base = _plane_removed(surface, C["xx"], C["yy"], robust=False)[0]
    print("\n  [λc 掃引(低域カットオフ / ハイパス)]")
    print(head())
    lam_c_tab = {}
    for lam in (16.0, 32.0, 64.0, 80.0, 128.0, 256.0, 512.0):
        d = areal_params(areal_filter(base, DX, lam, "high"))
        lam_c_tab[lam] = d
        print(fmt_row(f"λc = {lam:>5.0f} µm", d))
    print(fmt_row("真値", truth))
    print(f"  → λc を 16 µm まで下げると加工目(λ=32µm)が落ちて Sq が"
          f" {100 * rel_err(lam_c_tab[16.0]['Sq'], truth['Sq']):+.0f}%。")
    print(f"     λc を 256 µm まで上げるとうねり(λ=256µm)が漏れ込んで"
          f" {100 * rel_err(lam_c_tab[256.0]['Sq'], truth['Sq']):+.0f}%。")
    print("     **λc を 1 段(2 倍)動かすだけで合否が変わる。**"
          " どちら側にも壊れるので『安全側の λc』は存在しない。")
    lams = sorted(lam_c_tab)
    figs.save_plot("lambda_c_sweep",
                   [(k, np.log2(lams),
                     np.array([100 * rel_err(lam_c_tab[x][k], truth[k])
                               for x in lams])) for k in ("Sa", "Sq", "Sz")],
                   xlabel="log2 λc [µm]", ylabel="真値からの相対誤差 [%]",
                   title="λc は両側に壊れる —— 谷は 64〜128 µm しかない",
                   caption="左は加工目(λ=32µm)を落として過小、右はうねり"
                           "(λ=256µm)が漏れて過大。安全側の λc は無い。")

    print("\n  [λs 掃引(高域カットオフ / ローパス、λc=80µm の後に掛ける)]")
    print("  ★ここは予想が外れた側。「λs は尖りの指標(Sz/Sku)だけを選択的に削る」"
          "と思っていたが、雑音の無い面ではほぼ**比例して全部**削る。")
    print(head())
    lam_s_tab = {}
    rough80 = areal_filter(base, DX, LAMBDA_C, "high")
    for lam in (0.0, 2.0, 4.0, 8.0, 16.0):
        z = rough80 if lam == 0.0 else areal_filter(rough80, DX, lam, "low")
        d = areal_params(z)
        lam_s_tab[lam] = d
        print(fmt_row("λs = 無し" if lam == 0.0 else f"λs = {lam:>5.0f} µm", d))
    r_sq = rel_err(lam_s_tab[8.0]["Sq"], lam_s_tab[0.0]["Sq"])
    r_sz = rel_err(lam_s_tab[8.0]["Sz"], lam_s_tab[0.0]["Sz"])
    print(f"  → λs=8µm で Sq {100 * r_sq:+.1f}%、Sz {100 * r_sz:+.1f}%、"
          f"Sku {100 * rel_err(lam_s_tab[8.0]['Sku'], lam_s_tab[0.0]['Sku']):+.1f}%。"
          f"Sz の落ち方は Sq の {abs(r_sz / r_sq):.1f} 倍でしかない。")
    print("     理由は仕込んだ形にある。いちばん尖った特徴(傷、半値半幅 4 µm)でも"
          " λs=8 µm より広い。**λs が効くのは λs と同じ大きさの特徴があるときだけ。**")

    print("\n  [λs 掃引・白色雑音(σ=0.05 µm)を足した面] —— λs 本来の用途")
    print("  ここは **傷を抜いた面**で見る。傷があると Sz が最初から 6 µm あって"
          "測定雑音の寄与が埋もれ、λs の役目が見えない。")
    rng_n = np.random.default_rng(4242)
    clean = rough_without
    noisy = clean + rng_n.normal(0.0, 0.05, clean.shape)
    print(head())
    lam_s_noise = {0.0: areal_params(noisy)}
    print(fmt_row("参考: 雑音なし", areal_params(clean)))
    print(fmt_row("λs = 無し(雑音入り)", lam_s_noise[0.0]))
    for lam in (2.0, 4.0, 8.0):
        d = areal_params(areal_filter(noisy, DX, lam, "low"))
        lam_s_noise[lam] = d
        print(fmt_row(f"λs = {lam:>5.0f} µm", d))
    base_clean = areal_params(clean)
    n_sq = rel_err(lam_s_noise[0.0]["Sq"], base_clean["Sq"])
    n_sz = rel_err(lam_s_noise[0.0]["Sz"], base_clean["Sz"])
    print(f"  → σ=0.05 µm(Sq の {100 * 0.05 / base_clean['Sq']:.0f}%)の白色雑音は "
          f"Sq を {100 * n_sq:+.1f}% しか動かさないのに Sz を {100 * n_sz:+.1f}% "
          f"押し上げる({abs(n_sz / n_sq):.0f} 倍の選択性)。")
    print(f"     λs=4 µm を掛けると Sz は {100 * rel_err(lam_s_noise[4.0]['Sz'], lam_s_noise[0.0]['Sz']):+.1f}%、"
          f"Sq は {100 * rel_err(lam_s_noise[4.0]['Sq'], lam_s_noise[0.0]['Sq']):+.1f}% 戻り、"
          f"雑音なしとの Sz 差は {100 * abs(n_sz):.0f}% から "
          f"{100 * abs(rel_err(lam_s_noise[4.0]['Sz'], base_clean['Sz'])):.0f}% になる。")
    print("     **Sz は測定雑音を測る。λs はその雑音を落とすためにある** —— つまり"
          "『λs を掛けたかどうか』は、Sz を報告するときだけ結論を変える。")

    # ---------------------------------------------------------------- 6 --- #
    print("\n=== 6. 傾き除去 —— 最小二乗平面 vs ロバスト(RANSAC)===")
    print("  傷 4 本はすべて x > 0.55L の側に寄せてある。傾きの基準に傷が乗る状況。")
    print("  うねりも λc も外し、**傾きの当てはめだけ**を誤差源にする"
          "(2 つの誤差源を同じ表で混ぜない)。真値はこの節だけ帯域無しの"
          "`rough_true` そのもの。")
    surf_tilt = rough_true + tilt          # うねり無し。傾きだけを除く問題に絞る
    truth6 = areal_params(rough_true)
    res_ls, pl_ls = _plane_removed(surf_tilt, C["xx"], C["yy"], robust=False)
    t0 = time.perf_counter()
    res_rs, pl_rs = _plane_removed(surf_tilt, C["xx"], C["yy"], robust=True)
    t_rs = time.perf_counter() - t0
    print(f"\n  {'除去のしかた':<26}{'勾配 x':>12}{'勾配 y':>12}"
          f"{'余計に除いた傾きの rms':>22}")
    for lab, pl in (("真値(仕込んだ値)", (TILT_X, TILT_Y)),
                    ("最小二乗平面 fit_plane", _slopes(pl_ls)),
                    ("ロバスト fit_plane_ransac", _slopes(pl_rs))):
        gx, gy = pl
        # 余計に除いた平面 = (gx-TILT_X)x + (gy-TILT_Y)y。一様格子上の rms は
        # sqrt((dgx² + dgy²) L² / 12)。
        left = math.sqrt(((gx - TILT_X) ** 2 + (gy - TILT_Y) ** 2) * L ** 2 / 12.0)
        print(f"  {lab:<26}{gx:>12.6f}{gy:>12.6f}{left:>22.4f}")
    print(f"    (RANSAC {t_rs * 1000:.0f} ms / {N * N} 点)")
    print("\n  " + head()[2:])
    print(fmt_row("真値(厳密に傾きだけ除去)", truth6))
    for lab, z in (("最小二乗平面", res_ls), ("ロバスト RANSAC", res_rs)):
        print(fmt_row(lab, areal_params(z)))
    print(head_err())
    for lab, z in (("最小二乗平面", res_ls), ("ロバスト RANSAC", res_rs)):
        d = areal_params(z)
        cells = "".join(f"{100 * rel_err(d[k], truth6[k]):>12.2f}" for k in PARAMS)
        print(f"  {lab:<26}{cells}")
    e_ls = abs(rel_err(areal_params(res_ls)["Sq"], truth6["Sq"]))
    e_rs = abs(rel_err(areal_params(res_rs)["Sq"], truth6["Sq"]))
    print(f"  → 傷が面積の {100 * float((scratch < -0.5).mean()):.1f}% しか無くても、"
          f"最小二乗平面は勾配を "
          f"{abs(_slopes(pl_ls)[0] - TILT_X):.2e} 傾け、Sq を {100 * e_ls:.2f}% "
          f"**過小**にする。RANSAC は {100 * e_rs:.2f}%"
          f"({e_ls / max(e_rs, 1e-12):.1f} 倍の改善)。")
    print("     符号が過小なのは、最小二乗が『傷が片側に寄っていることによる"
          "本物の非対称』まで平面として吸い上げてしまうから。"
          "**除きすぎるほうに壊れる。**")
    # この節の答えが λc の後にも残るかを確かめる(残らないなら気にする必要が無い)
    aft_ls = areal_params(areal_filter(res_ls, DX, LAMBDA_C, "high"))
    aft_rs = areal_params(areal_filter(res_rs, DX, LAMBDA_C, "high"))
    aft_tr = areal_params(areal_filter(rough_true, DX, LAMBDA_C, "high"))
    print(f"  ★ただし λc={LAMBDA_C:.0f}µm ハイパスを後段に置くと差は消える"
          f"(Sq 誤差 LS {100 * rel_err(aft_ls['Sq'], aft_tr['Sq']):+.2f}% / "
          f"RANSAC {100 * rel_err(aft_rs['Sq'], aft_tr['Sq']):+.2f}%)。")
    print("     余計に除いた平面は純粋な長波長なので、ハイパスが同じものを"
          "もう一度捨てるだけ。**当てはめのロバスト性が効くのは、λc を掛けない"
          "運用(形状偏差・平面度)のとき。** 粗さだけを見るなら順序で救える。")
    print("\n     効き方が小さいのは傷が『深いが細い』から。**深さでなく面積比が"
          "効く**ので、傷が広がるほど最小二乗は速く壊れる —— 面積比を振って確認:")
    print(f"  {'傷の半値半幅':<26}{'面積比':>10}{'LS の Sq 誤差':>16}{'RANSAC の Sq 誤差':>20}")
    for hw in (4.0, 12.0, 24.0, 40.0):
        s2 = _scratch_field(C["xx"], C["yy"], hw)
        rt2 = psd + lay + s2
        tr2 = areal_params(rt2)
        surf2 = rt2 + tilt
        r_ls = areal_params(_plane_removed(surf2, C["xx"], C["yy"], False)[0])
        r_rs = areal_params(_plane_removed(surf2, C["xx"], C["yy"], True)[0])
        print(f"  {'%.0f µm' % hw:<26}{100 * float((s2 < -0.5).mean()):>9.1f}%"
              f"{100 * rel_err(r_ls['Sq'], tr2['Sq']):>15.2f}%"
              f"{100 * rel_err(r_rs['Sq'], tr2['Sq']):>19.2f}%")

    # ---------------------------------------------------------------- 7 --- #
    print("\n=== 7. 1-D(Ra/Rq/Rz)と 2-D(Sa/Sq/Sz)の食い違い ===")
    print("  加工目は行方向(x)に走らせてある。つまり『目に平行な断面』は"
          "加工目を一切見ない。Rz はここでは評価長さ全体の最大高低差(= Rt)で、"
          "Sz と定義を揃えてある。")

    def sections(fld, step=4):
        rows = np.array([[profile_params(
            profile_filter(fld[i, :], DX, LAMBDA_C, "high"))[k]
            for k in ("Ra", "Rq", "Rz")] for i in range(0, N, step)])
        cols = np.array([[profile_params(
            profile_filter(fld[:, j], DX, LAMBDA_C, "high"))[k]
            for k in ("Ra", "Rq", "Rz")] for j in range(0, N, step)])
        # 斜め断面は `fs.line_profile`(双一次補間)で取る。1 標本 = √2 画素。
        diag = []
        for off in range(0, N - 32, 16):
            p = fs.line_profile(fld, (0.0, float(off)),
                                (float(N - 1 - off), float(N - 1)), num=N)
            diag.append([profile_params(profile_filter(
                p, DX * math.sqrt(2.0), LAMBDA_C, "high"))[k]
                for k in ("Ra", "Rq", "Rz")])
        return rows, cols, np.array(diag)

    print("\n  [7a] 向きの依存 —— 傷を抜いた面(加工目 + PSD だけ)で見る。")
    print("       傷が入ると外れ値が Rq を支配して、向きの効果が見えなくなるため。")
    r0, c0, d0 = sections(rough_without)
    print(f"  {'断面の向き':<24}{'本数':>6}{'Ra 平均':>11}{'Rq 平均':>11}{'Rz 平均':>11}")
    for lab, a in (("目に平行(行)", r0), ("目に直交(列)", c0),
                   ("斜め 45°(line_profile)", d0)):
        print(f"  {lab:<24}{len(a):>6}{a[:, 0].mean():>11.4f}"
              f"{a[:, 1].mean():>11.4f}{a[:, 2].mean():>11.4f}")
    s0 = areal_params(rough_without)
    print(f"  {'2-D(面全体)':<24}{1:>6}{s0['Sa']:>11.4f}{s0['Sq']:>11.4f}"
          f"{s0['Sz']:>11.4f}")
    ratio = c0[:, 1].mean() / r0[:, 1].mean()
    print(f"  → 目に直交する断面の Rq は平行な断面の {ratio:.1f} 倍"
          f"(Ra なら {c0[:, 0].mean() / r0[:, 0].mean():.1f} 倍)。"
          "**同じ表面、同じ装置、向きが違うだけ。**")
    print(f"     斜め 45° は両者の中間({d0[:, 1].mean():.4f})。加工目の向きが"
          "分からない面では、Rq の値そのものが走査方向の記録なしには再現しない。")

    print("\n  [7b] Rz のばらつき —— 傷ありの面で、断面 1 本がどれだけ当てにならないか。")
    rows, cols, diag = sections(rough_with)
    fld = rough_with
    s2d = areal_params(fld)
    print(f"  {'断面の向き':<24}{'本数':>6}{'Rz 平均':>11}{'Rz 最小':>11}"
          f"{'Rz 最大':>11}{'最大/最小':>11}{'Sz の 8 割超':>14}")
    for lab, a in (("目に平行(行)", rows), ("目に直交(列)", cols),
                   ("斜め 45°(line_profile)", diag)):
        n_hit = int((a[:, 2] > 0.8 * s2d["Sz"]).sum())
        print(f"  {lab:<24}{len(a):>6}{a[:, 2].mean():>11.4f}{a[:, 2].min():>11.4f}"
              f"{a[:, 2].max():>11.4f}{a[:, 2].max() / a[:, 2].min():>11.1f}"
              f"{'%d / %d' % (n_hit, len(a)):>14}")
    print(f"  {'2-D(面全体)Sz':<24}{1:>6}{s2d['Sz']:>11.4f}")
    worst = max(rows[:, 2].max() / rows[:, 2].min(), cols[:, 2].max() / cols[:, 2].min())
    print(f"\n  → 断面 1 本の Rz は同じ面の中で最大 {worst:.0f} 倍振れる。"
          f"面の Sz({s2d['Sz']:.3f})の 8 割に届く断面は、行で"
          f" {int((rows[:, 2] > 0.8 * s2d['Sz']).sum())}/{len(rows)} 本しかない。")
    print("     『Rz を数本取って最大値を報告する』運用は、**本数と向きを"
          "書かないと再現しない**。Rq は数本で足りるが Rz は足りない —— "
          "同じ 1-D 断面でも、パラメータごとに必要な本数が違う。")

    # ---------------------------------------------------------------- 8 --- #
    print("\n=== 8. まとめ —— 標本化・帯域に対する頑健さの順位 ===")
    print(f"  {'':<6}{'パラメータ':<10}{'標本間隔':>12}{'評価領域':>12}"
          f"{'λc':>12}{'測定雑音':>12}   総合")
    rob = {}
    for k in PARAMS:
        d_samp = abs(rel_err(samp["point"][8][k], truth[k]))                  # dx=8µm
        d_lam_c = abs(rel_err(lam_c_tab[128.0][k], lam_c_tab[80.0][k]))       # λc 1 段
        d_lam_s = abs(rel_err(lam_s_noise[0.0][k], base_clean[k]))            # 雑音 σ0.05
        rob[k] = (d_samp, d_lam_c, d_lam_s)
    # 評価領域感度 = 窓 128 と 512 の差
    area_sens = {}
    for k in PARAMS:
        w = 128
        wins = [rough_with[i:i + w, j:j + w]
                for i in range(0, N, w) for j in range(0, N, w)]
        v = float(np.mean([areal_params(x)[k] for x in wins]))
        area_sens[k] = abs(rel_err(v, areal_params(rough_with)[k]))
    score = {k: rob[k][0] + area_sens[k] + rob[k][1] + rob[k][2] for k in PARAMS}
    for i, k in enumerate(sorted(PARAMS, key=lambda x: score[x]), 1):
        tag = "強い" if score[k] < 0.15 else ("普通" if score[k] < 0.6 else "弱い")
        print(f"  {i:<6}{k:<10}{100 * rob[k][0]:>11.1f}%{100 * area_sens[k]:>11.1f}%"
              f"{100 * rob[k][1]:>11.1f}%{100 * rob[k][2]:>11.1f}%   {tag}"
              f"(合計 {100 * score[k]:.0f}%)")
    print("  列の意味: 標本間隔 = dx 1→8 µm、評価領域 = 全面 → 128² 窓の平均、")
    print("            λc = 80→128 µm(1 段)、測定雑音 = 白色 σ=0.05 µm の追加。")
    print("            いずれも |相対変化|。合計はその単純和(重み付けはしない —— "
          "どの軸が効くかは工程で違うので、まとめる側が決めること)。")

    print("\n所見(想定と違ったこと / 途中で自分が間違えたこと):")
    print("  (a) ★合成器を一度壊した。位相を `(u - u[-k])/2` で反対称化すると"
          "エルミートにはなるが位相が一様でなくなり、全モードが原点で同位相に"
          "足されて **1 本のスパイク**が立った(range/rms = 56、尖度 87)。"
          "**Sq は解析値と 1e-16 で一致したままだった** —— 分散だけ見ていたら"
          "気づけない種類の壊れ方で、Sz と Sku を並べて初めて出た。")
    print("  (b) λs(高域カットオフ)は『尖りの指標だけを選択的に削る』と思って"
          f"いたが、雑音の無い面では Sz は Sq の {abs(r_sz / r_sq):.1f} 倍しか"
          "動かない。λs が効くのは **λs と同じ大きさの特徴があるとき** —— "
          f"白色雑音(σ=0.05 µm)を足すと Sq {100 * n_sq:+.1f}% に対し Sz "
          f"{100 * n_sz:+.1f}% となって、そこで初めて {abs(n_sz / n_sq):.0f} 倍の"
          "選択性が出る(5 節後半)。予想が正しかったのは条件つきだった。")
    print("  (c) 傷が最小二乗平面を汚す量は、最初の見積もりより小さかった"
          f"(深さ 3 µm・面積 5.6% で Sq 誤差 {100 * e_ls:.1f}%)。効くのは"
          "深さではなく面積比で、半値半幅を 10 倍にして初めて二桁 % になる。"
          "**『深い傷 = ロバスト必須』は早合点で、正しくは『広い外れ値 = "
          "ロバスト必須』。**さらに λc を後段に置くと差はほぼ消える。")
    print("  (d) 標本化に対して **Sq が最も強く、Sa がむしろ弱い**のは意外だった。"
          "エイリアシングはエネルギーを折り返すだけなので Sq(2 次モーメント)は"
          "保存されるが、Sa は分布の形が変わると動く。dx=16 µm で Sku が"
          "半分になり、それに連れて Sa/Sq 比がガウスの 0.798 に近づく。")
    print("  (e) 面の Sz に届く 1-D 断面はごく少数だが、加工目に直交する向きなら"
          "Rq は安定して出る。**Rz と Rq は断面 1 本に対する要求が全く違う。**")

    print("\n所見(fullseye の穴 —— この PoC で塞げなかったもの):")
    print("  (A) **粗さパラメータの op が 1 つも無い。** Sa/Sq/Sz/Sp/Sv/Ssk/Sku も、"
          "1-D の Ra/Rq/Rz/Rsk/Rku も、`dir(fullseye)` に存在しない"
          "(`roughness_map` は局所標準偏差の画像で、面のパラメータではない)。"
          "この PoC は全部自前で書いた。")
    print("  (B) **帯域を切る道具が無い。** ISO 流のガウスフィルタ"
          "(透過率 exp(-π(αλf)²), α=√(ln2/π))が無いので、粗さ / うねり / 形状の"
          "分離が自前 FFT になる。`vol_fft_highpass` は 3-D 体積向けで、"
          "2-D 高さ場のカットオフ波長指定には使えない。")
    print("  (C) `fs.radial_power_spectrum` は正規化の規約が docstring に無い。"
          "1 節で H を 2 通り仕込んで実験で決めた結果、**面 PSD(環内の |F|² の"
          f"平均)の規約**だと分かった(実測傾き {slope:+.3f} 対 予想 "
          f"{-2 * (HURST + 1):+.3f})。使えないわけではないが、規約が書いて"
          f"いないので毎回この検算が要る。戻した H には一律 {h_err[HURST]:+.3f} の"
          "系統誤差(環平均の離散化)があり、docstring に注記が欲しい。")
    print("  (D) **PSD からの高さ場合成器が無い。** 真値の分かる粗さ面を作る"
          "唯一の実用的な方法なのに、`fringe`/`interferometry`/`dem` のどこにも無い。"
          "この PoC の `synth_psd_surface` がそのまま op になる。")
    print("  (E) `fs.fit_plane` / `fs.fit_plane_ransac` は (N,3) 点群を要求するので、"
          "高さ場(2-D 配列)を毎回 `column_stack` で展開する必要がある"
          f"({N}² = {N * N} 点で {N * N * 3 * 8 / 1e6:.1f} MB)。"
          "格子を格子のまま受ける口が無い。")
    print("  (F) `fs.line_profile` は num を指定しても **物理的な標本間隔を返さない**。"
          "斜め断面では 1 標本が √2 画素になるので、波長指定のフィルタを掛ける側が"
          "自分で dx を計算して渡すしかない(この PoC の 7 節がそれ)。取り違えると"
          "λc が 41% ずれる。")

    print("\n足すべき op の提案(名前と引数まで):")
    print("  1. `surface_params(z, dx=1.0, dy=None) -> dict`"
          "  … Sa/Sq/Sp/Sv/Sz/Ssk/Sku/Sdq/Sdr。**帯域を切っていない配列を"
          "渡されたら拒否**するのが本筋(2 節のゼロ点が示すとおり、生 rms の"
          "Sq は 20 倍間違う)。少なくとも `assume_filtered=False` を既定にして"
          "警告を返す。")
    print("  2. `profile_params(p, dx=1.0, n_sampling=5) -> dict`"
          "  … Ra/Rq/Rz/Rt/Rsk/Rku/Rp/Rv。Rz は基準長さ分割の平均、Rt は全体、"
          "**両方返して定義差を消す**。")
    print("  3. `surface_filter(z, dx, lambda_c=None, lambda_s=None, "
          "kind=\"gaussian\", end_effect=\"reject\") -> (roughness, waviness)`"
          "  … ISO 16610-21 のガウス。`end_effect` は循環畳み込みの端を"
          "捨てるか鏡像で延ばすか(この PoC は端を無視している = 穴)。")
    print("  4. `surface_form_remove(z, dx, order=1, method=\"ls\"|\"ransac\", "
          "thresh=None) -> (residual, coeffs)`"
          "  … 格子のまま平面 / 二次曲面を除く。6 節の (N,3) 展開が要らなくなる。")
    print("  5. `surface_synth_psd(n, dx, hurst, lambda_lo, lambda_hi, sq, seed) "
          "-> (z, sq_analytic)`"
          "  … 1 節の合成器。**解析 Sq を一緒に返す**のが肝で、これが無いと"
          "粗さの検査に真値を用意できない。")
    print("  6. `surface_psd(z, dx, kind=\"areal\"|\"radial\") -> (q, C)`"
          "  … 規約を引数で明示した PSD。(C) の曖昧さを消し、Hurst 推定を"
          "検算可能にする。")

    # ------------------------------------------------------------- assert -- #
    # 1) 合成器: 解析 Sq と実現 Sq が倍精度で一致する
    assert abs(sq_real / sq_an - 1.0) < 1e-10, "PSD 合成の解析値と実現値が不一致"
    # 合成器は分散だけでなく形も正しいこと(位相の反対称化を壊すと尖度が跳ねる)
    kurt = float(np.mean((psd_raw - psd_raw.mean()) ** 4) / psd_raw.std() ** 4)
    assert 2.5 < kurt < 3.5, f"合成面の尖度が {kurt:.1f} —— 位相の引き方が壊れている"
    # `radial_power_spectrum` は面 PSD の規約(H が ±0.05 以内で戻る)
    assert all(abs(v) < 0.05 for v in h_err.values()), \
        f"H が戻らない = 規約の読みが違う: {h_err}"
    # 2) ゼロ点: 生 rms は Sq を 10 倍以上に見せる / 正しい手順は 10% 以内
    assert areal_params(surface)["Sq"] > 10.0 * truth["Sq"]
    assert abs(rel_err(areal_params(rough_meas)["Sq"], truth["Sq"])) < 0.10
    # 3) 標本化の順位: Sz は Sa より早く壊れる(崖の位置で)
    assert cliff["Sz"] is not None, "Sz が dx=16 µm まで崩れない = 仕込みが弱い"
    assert cliff["Sa"] is None or cliff["Sa"] > cliff["Sz"], "Sa が Sz より早く壊れた"
    assert abs(rel_err(samp["point"][8]["Sa"], truth["Sa"])) * 3.0 \
        < abs(rel_err(samp["point"][8]["Sz"], truth["Sz"])), \
        "dx=8µm で Sz の壊れ方が Sa の 3 倍に届かない"
    # エイリアシングはエネルギーを折り返すだけ = 2 次モーメントは保たれる
    assert abs(rel_err(samp["point"][16]["Sq"], truth["Sq"])) < 0.05, \
        "dx=16µm で Sq が 5% を超えた —— Sq の頑健さの根拠が崩れている"
    # 4) 評価領域: 傷なし面で Sz は窓の大きさに対し単調増加
    mono = []
    for w in (32, 64, 128, 256, 512):
        wins = [rough_without[i:i + w, j:j + w]
                for i in range(0, N, w) for j in range(0, N, w)]
        mono.append(float(np.mean([v.max() - v.min() for v in wins])))
    assert all(b > a for a, b in zip(mono, mono[1:])), f"Sz が単調増加しない: {mono}"
    assert mono[-1] / mono[0] > 1.3, "評価領域による Sz の増加が小さすぎる"
    # 極値則の予測倍率(2√(2 ln M))に対し、実測/予測は窓によらずほぼ一定
    rr_chk = np.array(ratios["傷なし"])
    assert (rr_chk.max() - rr_chk.min()) / rr_chk.mean() < 0.10, \
        f"実測/予測が窓の大きさで動く = 極値則の形が合っていない: {rr_chk}"
    # 5) カットオフ: λc を両側へ動かすと Sq が両側に壊れる
    assert lam_c_tab[16.0]["Sq"] < truth["Sq"] * 0.9, "λc=16µm で加工目が落ちていない"
    assert lam_c_tab[256.0]["Sq"] > truth["Sq"] * 1.1, "λc=256µm でうねりが漏れていない"
    # 6) λs の選択性は「雑音のあるときだけ」出る(予想が外れた側を固定する)
    #    雑音なし: Sz の動きは Sq の 2 倍未満 = 選択性は無いに等しい
    assert abs(rel_err(lam_s_tab[8.0]["Sz"], lam_s_tab[0.0]["Sz"])) \
        < 2.0 * abs(rel_err(lam_s_tab[8.0]["Sq"], lam_s_tab[0.0]["Sq"])), \
        "雑音なしで λs に選択性が出た = 仕込みが変わっている"
    #    雑音あり: Sz の動きは Sq の 3 倍超
    assert abs(n_sz) > 3.0 * abs(n_sq), \
        f"白色雑音でも Sz が選択的に上がらない: Sz{n_sz:+.3f} Sq{n_sq:+.3f}"
    # 7) ロバスト当てはめは最小二乗より真の勾配に近い(広い外れ値のとき)
    s_wide = _scratch_field(C["xx"], C["yy"], 40.0)
    rt_w = psd + lay + s_wide
    e_ls_w = abs(rel_err(areal_params(_plane_removed(rt_w + tilt, C["xx"], C["yy"],
                                                     False)[0])["Sq"],
                         areal_params(rt_w)["Sq"]))
    e_rs_w = abs(rel_err(areal_params(_plane_removed(rt_w + tilt, C["xx"], C["yy"],
                                                     True)[0])["Sq"],
                         areal_params(rt_w)["Sq"]))
    assert e_rs_w < e_ls_w, f"広い外れ値でも RANSAC が勝てない: {e_rs_w} vs {e_ls_w}"
    # 8) 1-D: 加工目に直交する断面の Rq は平行な断面より大きい
    assert ratio > 1.5, f"加工目の異方性が出ていない: {ratio}"
    assert rows[:, 2].max() / rows[:, 2].min() > 1.5, "Rz の断面ばらつきが小さすぎる"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    dt = time.perf_counter() - t_all
    print(f"\n総所要 {dt:.1f} 秒")
    assert dt < 60.0, f"60 秒を超えた: {dt:.1f} 秒"
    print(f"PASS: 真値 Sq={truth['Sq']:.4f} / Sz={truth['Sz']:.4f} µm に対し、"
          f"正しい手順(平面除去 + λc={LAMBDA_C:.0f}µm)で Sq 誤差 "
          f"{100 * rel_err(areal_params(rough_meas)['Sq'], truth['Sq']):+.1f}%。"
          f"標本間隔 {DX * cliff['Sz']:.0f} µm で Sz が先に崩れ、Sa は "
          f"{'最後まで崩れず' if cliff['Sa'] is None else 'dx=%.0fµm で崩れる' % (DX * cliff['Sa'])}。")
    return True


# --------------------------------------------------------------------------- #
# 補助                                                                          #
# --------------------------------------------------------------------------- #
def _scratch_field(xx, yy, half_width):
    s = np.zeros_like(xx)
    for (x0, y0, x1, y1) in ((300.0, 60.0, 430.0, 300.0),
                             (340.0, 340.0, 470.0, 460.0),
                             (390.0, 40.0, 400.0, 380.0),
                             (300.0, 430.0, 480.0, 400.0)):
        d = _dist_to_segment(xx, yy, x0, y0, x1, y1)
        s -= SCRATCH_DEPTH * np.exp(-0.5 * (d / half_width) ** 2)
    return s


def _plane_removed(z, xx, yy, robust):
    """`fs.fit_plane` / `fs.fit_plane_ransac` で平面を除く。戻り値 (残差, 平面)。

    どちらも (N,3) 点群を要求するので毎回展開が要る(所見 (E))。
    法線の向きは +z 側に揃える —— 揃えないと `height_above_plane` の符号が
    反転して Ssk の符号が逆になる。
    """
    pts = np.column_stack([xx.ravel(), yy.ravel(), z.ravel()])
    if robust:
        # thresh は「傷を外れ値と見なす距離」。粗さ Sq の数倍、傷の深さ未満に取る。
        plane, _ = fs.fit_plane_ransac(pts, thresh=0.6, iters=200, seed=7)
    else:
        plane = fs.fit_plane(pts)
    plane = np.asarray(plane, dtype=np.float64)
    if plane[2] < 0:
        plane = -plane
    resid = fs.height_above_plane(pts, plane).reshape(z.shape) / plane[2]
    return resid, plane


def _slopes(plane):
    """平面 [a,b,c,d] を z = gx*x + gy*y + c0 の勾配に直す。"""
    a, b, c, _ = plane
    return (-a / c, -b / c)


def _decimate(z, factor, how):
    if factor == 1:
        return z.copy()
    if how == "point":
        return z[::factor, ::factor].copy()
    n = z.shape[0] // factor
    return z[:n * factor, :n * factor].reshape(n, factor, n, factor).mean(axis=(1, 3))


def _pipeline(z, dx):
    """測定側の標準手順: 傾きを厳密に除く → λc ハイパス。

    ここで傾きを『厳密に』除くのは、6 節で当てはめ方の影響を別に測るため。
    2 つの誤差源を同じ表で混ぜない。
    """
    n = z.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * dx
    z = z - (TILT_X * xx + TILT_Y * yy)
    return areal_filter(z, dx, LAMBDA_C, "high")


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
