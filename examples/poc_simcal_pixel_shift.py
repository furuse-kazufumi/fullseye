# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ピクセルシフトの 4 枚の「本当のずれ」と画素の開口を合わせる —— 縞しか写っていない所では、ずれは 1 方向にしか決まらない。

    py -3.11 examples/poc_simcal_pixel_shift.py

【問い】ピクセルシフト(撮像素子を 1 画素 / 半画素ずつ動かして撮る)の合成は、公称のずれを信じて枚を並べ替えるだけ
(``pixel_shift_merge``)。実機の圧電アクチュエータは公称から ±0.1 px 程度外れ、回り、露出も揃わない。解像の得は画素の
開口(開口率)とレンズの MTF で決まる。その誤差と係数を、撮れた画像から sim-to-real 較正(``simcal`` と ``multivar``)で
合わせられるか。合わせられないのはどこで、なぜか。順方向のモデルは ``pixel_shift_capture``(画素の開口の箱で厳密に
積分する撮像)。

  1. **計画とふるい(multivar)**: 縞の向きだけが違う 6 種の被写体で、同じ 4 つのつまみ(各フレームの dr・dc [画素]・
     回転 [mrad]・露出の比)を Morris のふるい(``simcal_screen``)にかける。2 次元の模様では 4 つとも「決まる」。縦縞では
     dr が「効かない」、横縞では dc が「効かない」、斜めの縞では dr と dc が「組でしか決まらない」(組の向きは縞を横切る
     向き)、何も無い板では露出だけが決まる。★これは開口問題(aperture problem)そのもので、縞に沿ったずれは画像を変えない。
  2. **±0.1 px の注入を回収する**: 3 枚のフレームに dr・dc ∈ ±0.1 px、回転 ±2 mrad、露出 ±2 % を乱数で注入し、物理の経路
     (電子のポアソン + 読み出し雑音 + 丸め、EMVA 1288 の線形カメラ)で撮る。真値の撮像は 1 画素 = 16 × 16 標本、合わせる
     モデルは 8 × 8 標本(同じ式の往復にしない)。門: 推定と真値の差の Fisher 距離の和が χ² 分布に従う(p ≥ 1e-3)、ずれの誤差は
     どれも Cramér-Rao 下界の 5 倍以内。★探針: 雑音を 1/4 に見誤ったモデルでは同じ門が p < 1e-3 で落ちる。
  3. **決まらない地図(見せ場)**: シーメンススター(放射状の縞)を 8 画素の升に区切り、升ごとに dr・dc を合わせる。
     星の腕の上では升の中の縞はほぼ放射状の 1 方向なので、ずれは**接線方向にしか決まらない**。simcal_fit が返す
     「決まる組」の向きは、升の位置から計算した接線の向きと、升が見込む角度の幅の中で揃う(閉形式の真値)。星の外の板では
     何も決まらない。Fisher 行列の楕円(Cramér-Rao の 1σ)は半径方向に伸びる。
     ★この章が simcal の誤りを 1 つ見つけた(2026-10-18): 決まる組の重みを、規格化した感度の列の大きさで**割って**いた
     (正しくは掛ける)。列の大きさが等しい組(利得 × 照明、薄膜の n·d)では同じ答えになるので試験が見逃し、星の升では
     組の向きが接線から 20〜40° 回っていた。直して 3° 台。回帰の門は ``tests/test_simcal.py``。
  4. **貧しいモデルを拒否する**: 3 mrad 回ったフレームを「平行移動だけ」のモデルで合わせると、数は返るが、残差 PCA
     (``simcal_discrepancy``)が構造を見つけ、過適合の門(``simcal_validate``)の絶対の門(χ² の上側確率)が落とす。回転を
     足したモデルは 6 つの門を全部通る。
  5. **解像の得を合わせた係数から出す**: 半画素シフト 4 枚(白黒)で、0.12〜0.9 cyc/px の正弦の和を撮る。つまみは開口率・
     レンズの Q = λN/p(回折の MTF)・3 枚のずれ(6 個)。合わせた開口率と Q を ``pixel_shift_resolution_budget`` の閉形式に
     入れて解像の得(折り返しを起こさず系の MTF が 0.1 以上の帯域の比)を出し、不確かさを Fisher の逆から伝える。門: 得は
     真値の係数での閉形式と 4σ 以内、Q = 2.5(Fiete 1999 の境目 Q = 2 より上)ではレンズ律速と判定し得は 1。
     ★拒否 2 つ: (a) 行の向きのアクチュエータが止まった 4 枚(公称は半画素、実際は 0)—— 合わせたずれの位相が行の向きで
     散らないので、半画素の格子が埋まらず、得の数を返さない。(b) 50 分の 1 の暗さ(信号 60 DN)—— 開口率のプロファイル尤度が
     両側で閉じず(Raue 2009)、開口率が決まらないので得を返さない(Q は決まる)。
  6. **実データの手順を合成で確かめる**: 実データにはシーンの真値が無いので、1 枚目そのものをシーンにする。斜めの公称の
     ずれ (±1, ±1) の組は G が G を見るので色の違いが入らない。G だけを 45° 回した格子に並べ、参照の格子を 3 次スプラインで
     補間して観測の格子を予測する simcal と、同じ格子の上の位相相関(``phase_correlation_fft`` を繰り返して副画素へ)の
     2 つで、升 8 個 × 2 組の注入したずれを偏りなく回収できることを先に確かめる(真値との差の t 検定)。★升の散らばりは
     下界の最大 1.8 倍 —— 下界は参照を雑音の無いシーンとみなすが、参照も雑音つきで、45° の格子は縞を折り返す。
     ★モザイク全体(R・B も白の釣り合いで灰色に見立てる)を参照にする模型は 0.002〜0.007 px 偏る(下界の 7〜8 倍)ので、
     ずれの数には使わず、色をまたぐ組の判定にだけ使う。
  R. **実データ**: PixelShift200(Qian ほか、arXiv:1905.02538、CC BY 4.0)の解像チャートの 4 枚の未加工 RAW(35 mm フルサイズ
     のミラーレス、センサシフト機)。G どうしの組 (1 枚目 → 3 枚目)・(2 枚目 → 4 枚目)のずれを、G の格子の升 16 個ごとに
     6 章と同じ G だけの simcal で合わせ、同じ升の位相相関と突き合わせる(升ごとの差の対応のある t 検定、p = 0.22 / 0.30)。
     雑音のモデルは、紙(明るい所)の G の組の差の分散から取る(光子の転送の 1 点、K = 0.363 DN/電子)。色をまたぐ組
     (1 枚目 → 2 枚目、G が R・B を見る)はモザイクの模型で χ²/自由度 31、dr が範囲の端に張りつき simcal が拒否する ——
     **2 つの組の間のずれは、この無彩色のチャートからは決まらない**(合成では同じ組が χ²/自由度 1.5 で合う)。ネットの無い
     CI では記録値を印字して飛ばす(取得とキャッシュは ``poc_pixel_shift`` と共有)。

【外部真値】合成の注入値(真値の撮像は細かい標本で、合わせるモデルと別の離散化)、閉形式の接線の向き、Cramér-Rao 下界
(雑音モデルから)、解像の得の閉形式(sinc × 回折の MTF、Fiete 1999 の Q)。実データは第 2 の方法(G の格子の位相相関)。
【学習】0。【較正】各フレームの dr・dc・回転・露出、開口率と Q(simcal)。

【来歴(実データ)】G. Qian, Y. Wang, J. Gu, C. Dong, W. Heidrich, B. Ghanem, J. S. Ren, "Rethinking Learning-based
Demosaicing, Denoising, and Super-Resolution Pipeline", ICCP 2022(arXiv:1905.02538)。データ PixelShift200
(https://huggingface.co/datasets/guochengqian/PixelShift200)、CC BY 4.0。場面 pixelshift_5 の 4 枚の行 2096〜2352・
列 3088〜4240(``poc_pixel_shift`` と同じ切り出し)。改変: 切り出し・白の釣り合い・拡大。repo にはデータを入れない。
rawpy は要らない(RAW の CFA は TIFF の IFD から Range 要求で読む)。

【来歴(方法)】Morris, Technometrics 33(2):161 (1991)(ふるい)/ Brun, Reichert and Künsch, Water Resour. Res. 37(4):1015
(2001)(交絡の指数)/ Raue et al., Bioinformatics 25(15):1923 (2009)(プロファイル尤度)/ Kennedy and O'Hagan, J. R. Stat.
Soc. B 63(3):425 (2001)(モデルの食い違い)/ Horn and Schunck, Artif. Intell. 17:185 (1981)(開口問題)/ Kuglin and Hines
(1975)(位相相関)/ Guizar-Sicairos, Thurman and Fienup, Opt. Lett. 33(2):156 (2008)(行列の DFT で相関の山を細かく読む)/
Fiete, Opt. Eng. 38(7):1229 (1999)(Q = λN/p)/ EMVA 1288 Release 4.0(雑音モデル)。

★正直に書いておくこと:
  * 回転はセンサの中心まわりの小さい角として、シーンの座標を回して与える。画素の箱そのものは回さない(2 次の効果)。
  * 5 章のレンズは収差の無い円形の瞳の回折だけ(MTF を正弦の振幅に掛ける。正弦の和の被写体なので厳密)。実機のレンズの
    収差・焦点ずれは入っていない。得の閉形式もこの模型の上の値。
  * 実データの参照は 1 枚目の画像そのもの(雑音つき)なので、残差の分散は 2 枚分(雑音モデルの K を 2 倍にする)。雑音の K は
    紙の明るさ 1 点から取った値で、画素ごとの感度のむら(PRNU)や暗い所の読み出し雑音は分けていない —— だから実データの
    χ²/自由度は 1 に戻らない(G の升の中央値 1.55 / 1.02、モザイクの模型 1.84)。実データの門は下界に頼らず、別の方法
    (位相相関)との升ごとの一致と、色をまたぐ組の拒否にしてある。
  * 位相相関の副画素は、山を行列の DFT で 1/200 画素まで細かく読み、その分だけ画像を戻してまた相関を取る(8 回)。
    1 回だけでは Hann の窓が山を 0 の側へ引く(既知のずれ 0.2 px が 0.13 px と出た)。白色化は 0(素の相互相関)にする
    —— 既定の 0.5 は雑音の多い高い周波数を持ち上げ、合成の 6 升のうち 3 升で 0.05〜0.3 px 外れた(白色化 0 では
    6 升とも 0.01 px 以内)。読みの刻みは 1/200 px なので、比べるときの不確かさに刻みの一様分布の分(0.005/√12)を足す。

EXTEND: 2 つの組の間のずれを決めるには、色のある被写体か、倍率色収差のモデル(R・B の倍率のつまみ)が要る。後者は
``simcal`` のつまみを 2 つ足すだけだが、無彩色のチャートでは交絡するはず(ふるいで確かめてから)。
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import chi2 as _chi2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
import pixelshift as PS  # noqa: E402
from filters_freq import phase_correlation_fft  # noqa: E402

L = fs.ledger
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
#: 門の有意水準(χ² の上側確率)。simcal_validate の既定と同じ。
ALPHA = 1e-3

#: 実機の巡り方(``poc_pixel_shift`` の実データの章が 96 通りから選んだ並び)。(dr, dc) [画素]。
NOMINAL = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, -1.0], [0.0, -1.0]])
#: 半画素シフト 4 枚(白黒、5 章)。``pixel_shift_pattern("half4")`` と同じ並び。
HALF = np.array([[0.0, 0.0], [0.0, 0.5], [0.5, 0.5], [0.5, 0.0]])
#: 色フィルタの感度(無彩色の被写体の R・G・B の比)。実データの紙の白の釣り合い(R × 2.29、B × 1.66)に近い値。
QE = np.array([0.45, 1.0, 0.6])
#: 線形カメラ(EMVA 1288): 0.5 DN/電子、暗雑音 6 電子、黒 64 DN、白い被写体で約 3000 DN。
K_DN, SIGMA_D, DARK, GAIN = 0.5, 6.0, 64.0, 3000.0
NOISE = {"kind": "emva", "K": K_DN, "sigma_d": SIGMA_D, "dark": DARK}
MARGIN = 2
#: 5 章の画素の大きさと波長(Q = λN/p から F 値を出すためだけに使う。Q が本体)。
PITCH_UM, WAVE_UM = 4.0, 0.55


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def fisher_distance(result, truth):
    """推定と真値の差の Fisher 距離 (θ̂ − θ*)ᵀ F (θ̂ − θ*) と自由度(値の出たつまみの数)。

    F は真値で計算した Fisher 情報(``simcal_identifiability(at=真値)``)。雑音モデルが正しく推定が効率的なら
    χ²(自由度) に従う —— 1 つずつ「3σ 以内か」を数えるより、つまみの間の相関まで含めて 1 つの p 値で判定できる。
    """
    idf = L.simcal_identifiability(result, at={k: v for k, v in truth.items()
                                               if k in [kn["name"] for kn in result["model"]["knobs"]]},
                                   profile=False)["identifiability"]
    names = [n for n in idf["knobs"] if n in result["theta_hat"]]
    ix = [idf["knobs"].index(n) for n in names]
    F = np.asarray(idf["fisher"], float)[np.ix_(ix, ix)]
    d = np.array([result["theta_hat"][n] - truth[n] for n in names])
    return float(d @ F @ d), len(names), idf


# --------------------------------------------------------------------------- #
# 被写体(解析的な無彩色の模様)と撮像                                           #
# --------------------------------------------------------------------------- #
def texture(kind: str):
    """無彩色の被写体 f(y, x) [画素の座標] → 0..1。縞の周期は 8 画素前後(ナイキストの手前)。"""
    tau = 2.0 * math.pi
    if kind == "2d":
        return lambda y, x: (0.5 + 0.18 * np.sin(tau * 0.11 * x + 1.0) + 0.18 * np.sin(tau * 0.13 * y + 2.0)
                             + 0.1 * np.sin(tau * (0.07 * x - 0.09 * y)))
    if kind == "vbars":
        return lambda y, x: 0.5 + 0.35 * np.sin(tau * 0.12 * x) + 0.0 * y
    if kind == "hbars":
        return lambda y, x: 0.5 + 0.35 * np.sin(tau * 0.12 * y) + 0.0 * x
    if kind == "diag":
        return lambda y, x: 0.5 + 0.35 * np.sin(tau * 0.12 * (x + y) / math.sqrt(2.0))
    if kind == "adiag":
        return lambda y, x: 0.5 + 0.35 * np.sin(tau * 0.12 * (x - y) / math.sqrt(2.0))
    if kind == "flat":
        return lambda y, x: 0.6 + 0.0 * x + 0.0 * y
    raise ValueError("unknown texture %r" % kind)


def star(n_px: int, spokes: int = 24, radius_frac: float = 0.42):
    """シーメンススター(正弦の腕 *spokes* 本、半径 radius_frac × n_px、外は灰の板へ滑らかに落とす)。"""
    c = n_px / 2.0
    R = radius_frac * n_px

    def f(y, x):
        dy, dx = y - c, x - c
        r = np.hypot(dy, dx)
        w = np.clip((R + 4.0 - r) / 4.0, 0.0, 1.0)
        w = w * w * (3.0 - 2.0 * w)
        return 0.5 + 0.4 * w * np.sin(spokes * np.arctan2(dy, dx))
    return f, c, R


def capture(fn, factor, n, shift, rot_mrad=0.0, expo=1.0, origin=(0.0, 0.0)):
    """センサ n × n 画素で 1 枚撮る(RGGB の生の値、0..1 の感度の単位)。

    センサの画素 p はシーンの c + R(θ)(p − c) + s を見る(c = センサの中心、s = ずれ)。被写体は解析的な関数なので、
    回転は細かい標本の座標を回して与える。積分は ``pixel_shift_capture``(画素の開口の箱、1 画素 = factor² 標本)。
    *origin* は大きな被写体の中の、このセンサの左上の位置(升ごとの当てはめ用)。
    """
    m = MARGIN
    nh, nw = (n, n) if np.isscalar(n) else (int(n[0]), int(n[1]))
    qy = (np.arange((nh + 2 * m) * factor) + 0.5) / factor
    qx = (np.arange((nw + 2 * m) * factor) + 0.5) / factor
    Y, X = np.meshgrid(qy, qx, indexing="ij")
    th = float(rot_mrad) * 1e-3
    cy, cx = (nh + 2 * m) / 2.0 + shift[0], (nw + 2 * m) / 2.0 + shift[1]
    dy, dx = Y - cy, X - cx
    yy = cy + math.cos(th) * dy - math.sin(th) * dx - m + origin[0]
    xx = cx + math.sin(th) * dy + math.cos(th) * dx - m + origin[1]
    rgb = fn(yy, xx)[..., None] * QE
    return float(expo) * PS.pixel_shift_capture(rgb, factor, [[shift[0], shift[1]]], "RGGB", margin=m)[0]


def physical(mu, seed):
    """物理の経路: 電子のポアソン + 読み出し雑音 + 丸め(分散の式は使わない)。"""
    rng = np.random.default_rng(seed)
    e = rng.poisson(np.maximum(mu - DARK, 0.0) / K_DN)
    return np.round(K_DN * (e + SIGMA_D * rng.standard_normal(mu.shape)) + DARK)


def shoot(fn, n, frame, truth, seed, origin=(0.0, 0.0)):
    """真値の撮像(1 画素 = 16 × 16 標本)を物理の経路で撮る。"""
    s = (NOMINAL[frame][0] + truth["dr"], NOMINAL[frame][1] + truth["dc"])
    mu = GAIN * capture(fn, 16, n, s, truth.get("rot", 0.0), truth.get("expo", 1.0), origin) + DARK
    return physical(mu, seed)


KNOBS = [{"name": "dr", "lo": -0.3, "hi": 0.3, "init": 0.0, "unit": "px"},
         {"name": "dc", "lo": -0.3, "hi": 0.3, "init": 0.0, "unit": "px"},
         {"name": "rot", "lo": -5.0, "hi": 5.0, "init": 0.0, "unit": "mrad"},
         {"name": "expo", "lo": 0.9, "hi": 1.1, "init": 1.0, "scale": "log"}]


def _knobs(fixed):
    out = []
    for k in KNOBS:
        d = dict(k, step=0, arg=k["name"])
        if k["name"] in fixed:
            d["fixed"] = fixed[k["name"]]
        out.append(d)
    return out


def frame_model(fn, n, frame, fixed=None, origin=(0.0, 0.0), noise=None, label="frame"):
    """1 枚のフレームの simmodel(つまみ dr・dc・回転・露出。合わせる側の撮像は 1 画素 = 8 × 8 標本)。"""

    def frame_op(dr=0.0, dc=0.0, rot=0.0, expo=1.0):
        return capture(fn, 8, n, (NOMINAL[frame][0] + dr, NOMINAL[frame][1] + dc), rot, expo, origin)

    return L.simcal_model(chain=[{"op": frame_op}, {"op": "stage:gain_offset", "args": {"gain": GAIN, "offset": DARK}}],
                          knobs=_knobs(dict(fixed or {})), noise=noise or NOISE, label=label)


# --------------------------------------------------------------------------- #
# 1. 計画とふるい                                                               #
# --------------------------------------------------------------------------- #
KINDS = [("2d", "2 次元の模様"), ("vbars", "縦縞"), ("hbars", "横縞"), ("diag", "右上がりの縞"), ("adiag", "右下がりの縞"),
         ("flat", "何も無い板")]
EXPECT = {"2d": {"dr": "determined", "dc": "determined"}, "vbars": {"dr": "no_influence", "dc": "determined"},
          "hbars": {"dr": "determined", "dc": "no_influence"}, "diag": {"dr": "combination", "dc": "combination"},
          "adiag": {"dr": "combination", "dc": "combination"}, "flat": {"dr": "no_influence", "dc": "no_influence"}}


def chapter_screen():
    print("\n1. 計画とふるい —— 同じ 4 つのつまみが、縞の向きで「決まる / 組でしか決まらない / 効かない」に分かれる")
    n = 32
    truth = {"dr": 0.06, "dc": -0.04, "rot": 1.0, "expo": 1.01}
    rows = {}
    for kind, label in KINDS:
        fn = texture(kind)
        mo = L.simcal_observe(frame_model(fn, n, 2), [shoot(fn, n, 2, truth, 11)])
        scr = L.simcal_screen(mo, size=6)
        r = L.simcal_fit(mo, allow_undetermined=True)
        combo = r["determined_combos"][0] if r["determined_combos"] else None
        rows[kind] = {"label": label, "class": scr["class"], "mu": scr["mu_star_whitened"], "theta": r["theta_hat"],
                      "combo": combo, "dims": scr["output_dims"], "img": mo["observed"]["images"][0], "result": r}
        print("   %-8s ふるい: dr %-12s dc %-12s rot %-12s expo %-10s | 当てはめ %s%s"
              % (label, scr["class"]["dr"], scr["class"]["dc"], scr["class"]["rot"], scr["class"]["expo"],
                 ", ".join("%s = %.4f" % (k, v) for k, v in r["theta_hat"].items()),
                 ("、決まる組 " + combo["combination"]) if combo else ""))
    ok = all(rows[k]["class"][j] == v for k, e in EXPECT.items() for j, v in e.items())
    gate("ふるいの分類が縞の向きどおり(縦縞 → dr は効かない、横縞 → dc は効かない、斜め → 組、板 → どちらも効かない、"
         "2 次元 → 両方決まる)", ok)

    def sign(kind):
        w = rows[kind]["combo"]["weights"] if rows[kind]["combo"] else {"dr": 0.0, "dc": 0.0}
        return float(np.sign(w["dr"] * w["dc"]))
    gate("斜めの縞の「決まる組」は縞を横切る向き: 右上がりの縞は dr + dc、右下がりの縞は dr − dc(重みの積の符号 %+d / %+d)"
         % (sign("diag"), sign("adiag")), sign("diag") > 0 > sign("adiag"))
    # 板では dr・dc・回転が効かないので Fisher 行列が特異 —— それらを固定して露出だけの下界を出す
    fn = texture("flat")
    rf = L.simcal_fit(L.simcal_observe(frame_model(fn, n, 2, fixed={"dr": 0.0, "dc": 0.0, "rot": 0.0}),
                                       [shoot(fn, n, 2, truth, 11)]))
    ex = rf["theta_hat"]["expo"]
    sd = L.simcal_identifiability(rf, profile=False)["identifiability"]["crlb"]["expo"]
    gate("何も無い板でも露出の比は決まる(%.4f ± %.4f、真値 1.01 と %.1fσ < 4σ)。ずれと回転は効かない"
         % (ex, sd, abs(ex - 1.01) / sd), abs(ex - 1.01) < 4.0 * sd and rows["flat"]["class"]["rot"] == "no_influence")
    return rows


# --------------------------------------------------------------------------- #
# 2. ±0.1 px の注入を回収する                                                    #
# --------------------------------------------------------------------------- #
def chapter_recovery():
    print("\n2. ±0.1 px の注入を回収する —— 3 枚のフレームに乱数のずれ・回転・露出を入れ、物理の経路で撮って合わせる")
    n = 32 if REDUCED else 40
    trials = 2 if REDUCED else 5
    fn = texture("2d")
    rng = np.random.default_rng(20261015)
    truths = []
    for _ in range(trials):
        for fr in (1, 2, 3):
            truths.append((fr, {"dr": float(rng.uniform(-0.1, 0.1)), "dc": float(rng.uniform(-0.1, 0.1)),
                                "rot": float(rng.uniform(-2.0, 2.0)), "expo": float(rng.uniform(0.98, 1.02))}))

    def score(noise):
        d2, dof, ratio, rows = 0.0, 0, [], []
        for i, (fr, tr) in enumerate(truths):
            m = frame_model(fn, n, fr, noise=noise)
            mo = L.simcal_observe(m, [shoot(fn, n, fr, tr, 500 + i)])
            r = L.simcal_fit(mo, allow_undetermined=True)
            q, k, idf = fisher_distance(r, tr)
            d2, dof = d2 + q, dof + k
            crlb = idf["crlb"]
            ratio += [abs(r["theta_hat"][j] - tr[j]) / crlb[j] for j in ("dr", "dc")]
            rows.append((fr, tr, r["theta_hat"], crlb))
        return d2, dof, np.asarray(ratio), rows

    d2, dof, ratio, rows = score(NOISE)
    p = float(_chi2.sf(d2, dof))
    for fr, tr, th, cr in rows[:6]:
        print("   フレーム %d: 真値 dr %+.4f dc %+.4f rot %+.2f expo %.4f → 推定 dr %+.4f dc %+.4f rot %+.2f expo %.4f"
              "(σ_CRLB dr %.4f px、rot %.3f mrad)" % (fr, tr["dr"], tr["dc"], tr["rot"], tr["expo"], th["dr"], th["dc"],
                                                   th["rot"], th["expo"], cr["dr"], cr["rot"]))
    err = np.array([[abs(th[j] - tr[j]) for j in ("dr", "dc")] for _f, tr, th, _c in rows])
    NUMBERS.update({"rec_max_err_px": float(err.max()), "rec_fisher_p": p, "rec_max_ratio": float(ratio.max())})
    gate("注入した ±0.1 px のずれを %d 枚で回収: 誤差の最大 %.4f px、どれも Cramér-Rao 下界の 5 倍以内(最大 %.2f 倍)"
         % (len(truths), err.max(), ratio.max()), bool(ratio.max() < 5.0))
    gate("推定と真値の差の Fisher 距離の和 %.1f は χ²(%d) に従う(上側確率 p = %.3f ≥ %g)—— 推定は下界どおりに散る"
         % (d2, dof, p, ALPHA), p >= ALPHA)
    nz = dict(NOISE, K=K_DN / 4.0, sigma_d=SIGMA_D)
    d2b, dofb, _r, _rows = score(nz)
    pb = float(_chi2.sf(d2b, dofb))
    NUMBERS["rec_fisher_p_wrong_noise"] = pb
    gate("★探針: 雑音を 1/4 に見誤ったモデル(K を 1/4)では同じ門が落ちる(Fisher 距離の和 %.1f、χ²(%d) の p = %.1e < %g)"
         % (d2b, dofb, pb, ALPHA), pb < ALPHA)
    return {"rows": rows, "d2": d2, "dof": dof, "ratio": ratio}


# --------------------------------------------------------------------------- #
# 3. 決まらない地図: シーメンススター                                           #
# --------------------------------------------------------------------------- #
def _ellipse_axes(C2):
    """2 × 2 の共分散(Fisher の逆の dr・dc の部分)→ (長軸の σ, 短軸の σ, 長軸の向き (dr, dc))。"""
    w, v = np.linalg.eigh(0.5 * (C2 + C2.T))
    w = np.maximum(w, 0.0)
    return math.sqrt(w[1]), math.sqrt(w[0]), v[:, 1]


def chapter_map():
    print("\n3. 決まらない地図 —— シーメンススターを 8 画素の升に区切り、升ごとにずれを合わせる")
    npx, spokes = (96, 24) if REDUCED else (128, 32)
    tile = 8
    fn, c, R = star(npx, spokes=spokes)
    truth = {"dr": 0.05, "dc": -0.03, "rot": 0.0, "expo": 1.0}
    nt = npx // tile
    cls = np.empty((nt, nt), dtype=object)
    cov = np.full((nt, nt, 2, 2), np.nan)
    tiles = []
    for i in range(nt):
        for j in range(nt):
            org = (i * tile, j * tile)
            m = frame_model(fn, tile, 2, fixed={"rot": 0.0}, origin=org)
            mo = L.simcal_observe(m, [shoot(fn, tile, 2, truth, 9000 + i * nt + j, origin=org)])
            r = L.simcal_fit(mo, allow_undetermined=True)
            und = r["undetermined"]
            if "dr" not in und and "dc" not in und:
                k = "determined"
            elif "no_influence" in (und.get("dr", "") + und.get("dc", "")):
                k = "no_influence"
            else:
                k = "combination"
            cls[i, j] = k
            idf = L.simcal_identifiability(r, at={"dr": truth["dr"], "dc": truth["dc"], "expo": 1.0},
                                           profile=False)["identifiability"]
            names = list(idf["knobs"])
            F = np.asarray(idf["fisher"], float)
            yc, xc = (i + 0.5) * tile, (j + 0.5) * tile
            rad = math.hypot(yc - c, xc - c)
            t = {"i": i, "j": j, "class": k, "rad": rad, "psi": math.atan2(yc - c, xc - c),
                 # 升が星の中心から見込む角度の半分 = 升の中で接線・半径の向きが振れる幅(閉形式の許容)
                 "span_deg": math.degrees(math.atan2(tile / math.sqrt(2.0), max(rad, 1e-9))),
                 "theta": r["theta_hat"], "combo": r["determined_combos"][0] if r["determined_combos"] else None}
            if k != "no_influence" and np.linalg.cond(F) < 1e12:
                C = np.linalg.inv(F)
                ia, ib = names.index("dr"), names.index("dc")
                cov[i, j] = C[np.ix_([ia, ib], [ia, ib])]
                t["F2"] = np.linalg.inv(cov[i, j])
            tiles.append(t)
    counts = {k: int((cls == k).sum()) for k in ("determined", "combination", "no_influence")}
    print("   升 %d × %d(星の半径 %.0f px、腕 %d 本): 両方決まる %d、組でしか決まらない %d、効かない %d"
          % (nt, nt, R, spokes, counts["determined"], counts["combination"], counts["no_influence"]))
    # (a) 組の向き = 接線の向き(閉形式)、(b) 組の値 = 真値の組(線形化の標準偏差で)
    comb, zc = [], []
    for t in tiles:
        if t["class"] != "combination" or not t["combo"] or set(t["combo"]["weights"]) - {"dr", "dc", "expo"}:
            continue
        if t["rad"] > R - 4.0:
            # 星の縁(灰の板へ落とす帯)にかかる升: 縞は半径の向きに変わるので、決まる組は接線ではない(数えない)
            continue
        w = t["combo"]["weights"]
        v = np.array([w.get("dr", 0.0), w.get("dc", 0.0)])
        tang = np.array([math.cos(t["psi"]), -math.sin(t["psi"])])         # (dr, dc) で見た接線
        ang = math.degrees(math.acos(min(1.0, abs(float(v @ tang)) / (np.linalg.norm(v) + 1e-300))))
        comb.append((ang, t["span_deg"]))
        if abs(w.get("expo", 0.0)) == 0.0 and "sum" in t["combo"]["value"] and t["combo"]["std_linearised"] > 0:
            want = w.get("dr", 0.0) * truth["dr"] + w.get("dc", 0.0) * truth["dc"]
            zc.append((t["combo"]["value"]["sum"] - want) / t["combo"]["std_linearised"])
    comb = np.array(comb) if comb else np.zeros((0, 2))
    zc = np.array(zc)
    # (c) 楕円の長軸 = 半径の向き(腕の上で、細長い升だけ)
    elong = []
    for t in tiles:
        C2 = cov[t["i"], t["j"]]
        if not np.isfinite(C2).all() or not (0.25 * R < t["rad"] < R - 4.0):
            continue
        a, b, v = _ellipse_axes(C2)
        if a > 3.0 * b:
            radial = np.array([math.sin(t["psi"]), math.cos(t["psi"])])
            elong.append((t["rad"], a / b, math.degrees(math.acos(min(1.0, abs(float(v @ radial))))), t["span_deg"]))
    elong = np.array(elong) if elong else np.zeros((0, 4))
    print("   組でしか決まらない升 %d: 組の向きと接線の差 最大 %.1f°(升が見込む角度の半分は %.1f〜%.1f°)。細長い楕円"
          "(長軸 > 3 × 短軸)の升 %d: 長軸と半径の向きの差 中央値 %.1f°・最大 %.1f°"
          % (len(comb), comb[:, 0].max() if len(comb) else float("nan"), comb[:, 1].min() if len(comb) else float("nan"),
             comb[:, 1].max() if len(comb) else float("nan"), len(elong),
             np.median(elong[:, 2]) if len(elong) else float("nan"), elong[:, 2].max() if len(elong) else float("nan")))
    NUMBERS.update({"map_combination": len(comb), "map_combo_angle_max": float(comb[:, 0].max()) if len(comb) else -1.0,
                    "map_elong": len(elong), "map_elong_angle_max": float(elong[:, 2].max()) if len(elong) else -1.0})
    gate("★星の腕の上(縁の帯より内側)の %d 升は「組でしか決まらない」。simcal_fit の返す決まる組の向きは、升の位置から計算した接線と最大 "
         "%.1f° —— どの升も、升が星の中心から見込む角度の半分(閉形式の許容)以内" % (
             len(comb), comb[:, 0].max() if len(comb) else float("nan")),
         len(comb) >= 4 and bool((comb[:, 0] <= comb[:, 1]).all()),
         "2026-10-18 に直す前の simcal では 20〜40° 回っていた(組の重みを列の大きさで割っていた)")
    pz = float(_chi2.sf(float((zc ** 2).sum()), len(zc))) if len(zc) else 0.0
    gate("決まる組の値は真値の組と合う: %d 升の (値 − 真値)/線形化の標準偏差 の 2 乗和 %.1f、χ²(%d) の p = %.3f ≥ %g"
         % (len(zc), float((zc ** 2).sum()), len(zc), pz, ALPHA), len(zc) >= 3 and pz >= ALPHA)
    gate("Cramér-Rao の楕円が細長い升 %d 升で、長軸(決まらない向き)は半径の向きと最大 %.1f° —— どの升も見込む角度の半分以内"
         % (len(elong), elong[:, 2].max() if len(elong) else float("nan")),
         len(elong) >= 8 and bool((elong[:, 2] <= elong[:, 3]).all()))
    outside = [t for t in tiles if t["rad"] > R + 6.0 + tile]
    gate("星の外の板の升(%d 升)はずれが効かない" % len(outside),
         len(outside) >= 4 and all(t["class"] == "no_influence" for t in outside))
    det = [t for t in tiles if t["class"] == "determined" and "F2" in t]
    q = sum(float(np.array([t["theta"]["dr"] - truth["dr"], t["theta"]["dc"] - truth["dc"]])
                  @ t["F2"] @ np.array([t["theta"]["dr"] - truth["dr"], t["theta"]["dc"] - truth["dc"]])) for t in det)
    pd = float(_chi2.sf(q, 2 * len(det))) if det else 0.0
    NUMBERS["map_det_p"] = pd
    gate("両方決まる升 %d 升の推定は下界どおりに散る(Fisher 距離の和 %.1f、χ²(%d) の p = %.3f ≥ %g)—— 腕の端の升は誤差が"
         "大きいが、下界も同じだけ大きい" % (len(det), q, 2 * len(det), pd, ALPHA), len(det) >= 8 and pd >= ALPHA)
    return {"fn": fn, "npx": npx, "tile": tile, "cls": cls, "cov": cov, "c": c, "R": R, "comb": comb, "elong": elong,
            "tiles": tiles}


# --------------------------------------------------------------------------- #
# 4. 貧しいモデルの拒否                                                         #
# --------------------------------------------------------------------------- #
def chapter_poor():
    print("\n4. 貧しいモデルを拒否する —— 3 mrad 回ったフレームを、平行移動だけのモデルで合わせる")
    n = 40 if REDUCED else 48
    fn = texture("2d")
    truth = {"dr": 0.04, "dc": 0.07, "rot": 3.0, "expo": 1.0}
    tr = shoot(fn, n, 2, truth, 31)
    ho = shoot(fn, n, 2, truth, 32)
    out = {}
    for name, fixed in (("translation", {"rot": 0.0}), ("full", {})):
        m = frame_model(fn, n, 2, fixed=fixed, label=name)
        r = L.simcal_fit(L.simcal_observe(m, [tr]))
        r = L.simcal_discrepancy(r)
        v = L.simcal_validate(r, L.simcal_observe(m, [ho], split="holdout"))
        out[name] = {"v": v, "fit": r}
        th = r["theta_hat"]
        g6 = v["validation"]["gates"]["fit_consistent_with_noise"]
        print("   %-11s dr %+.4f dc %+.4f%s、χ²/自由度 %.2f(学習の p %.1e、ホールドアウトの p %.1e)、残差 PCA %s(%d 成分)、"
              "門 %s → %s"
              % ("平行移動だけ" if name == "translation" else "回転も", th["dr"], th["dc"],
                 ("" if name == "translation" else "、rot %+.3f mrad" % th["rot"]), v["fit"]["chi2_red"],
                 g6["train"]["p"], g6["holdout"]["p"], v["discrepancy"]["verdict"], v["discrepancy"]["n_structural"],
                 "6 つ全部通過" if v["validation"]["passed"] else "落ちた: %s" % v["validation"]["failed"],
                 "数を返す" if v["theta_hat"] else "数を取り下げる"))
    t, f = out["translation"]["v"], out["full"]["v"]
    NUMBERS.update({"poor_chi2": t["fit"]["chi2_red"], "full_chi2": f["fit"]["chi2_red"]})
    gate("平行移動だけのモデルは拒否される(残差 PCA が構造、絶対の門 fit_consistent_with_noise が落ちる、χ²/自由度 %.2f)"
         % t["fit"]["chi2_red"],
         t["discrepancy"]["verdict"] == "structure" and "fit_consistent_with_noise" in t["validation"]["failed"]
         and not t["theta_hat"],
         "★ずれ (dr, dc) そのものは平行移動だけでも真値に近い(回転は中心まわりなので平均で消える)。"
         "拒否は「数が違う」からではなく「残差に説明できない形がある」から")
    rot_sd = L.simcal_identifiability(out["full"]["fit"], profile=False)["identifiability"]["crlb"]["rot"]
    gate("回転を足したモデルは 6 つの門を全部通り、回転 %.3f ± %.3f mrad(真値 3、%.1fσ < 4σ)"
         % (f["theta_hat"]["rot"], rot_sd, abs(f["theta_hat"]["rot"] - 3.0) / rot_sd),
         f["validation"]["passed"] and f["discrepancy"]["verdict"] == "white"
         and abs(f["theta_hat"]["rot"] - 3.0) < 4.0 * rot_sd)
    return {"translation": out["translation"], "full": out["full"], "obs": tr}


# --------------------------------------------------------------------------- #
# 5. 解像の得: 半画素シフト + 開口率 + レンズの MTF                                #
# --------------------------------------------------------------------------- #
#: 正弦の和の被写体: (cyc/px, 向き [rad], 位相)。0.12〜0.9 cyc/px(1 枚のナイキスト 0.5 の上下)、向き 3 つずつ。
SINES = [(f, math.radians(a + 17.0 * f), 0.5 * math.pi * f) for f in (0.12, 0.3, 0.45, 0.6, 0.75, 0.9)
         for a in (0.0, 60.0, 120.0)]


def _mtf_diff(x):
    """収差の無い円形の瞳の回折の MTF(x = f·Q、1 で 0)。``pixelshift`` の閉形式と同じ式。"""
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(x) - x * np.sqrt(1.0 - x * x))


def sine_scene(n, factor, Q, amp=0.035):
    """白黒の被写体(正弦の和)を、レンズの MTF を掛けて細かい標本で描く。正弦の和なので MTF は振幅に掛けるだけで厳密。"""
    q = (np.arange((n + 4) * factor) + 0.5) / factor - 2.0
    Y, X = np.meshgrid(q, q, indexing="ij")
    img = np.full(Y.shape, 0.5)
    for f, a, ph in SINES:
        img += amp * _mtf_diff(f * Q) * np.cos(2.0 * math.pi * f * (X * math.cos(a) + Y * math.sin(a)) + ph)
    return img


def half_capture(n, factor, Q, fill, shift):
    return PS.pixel_shift_capture(sine_scene(n, factor, Q), factor, [list(shift)], None, fill_factor=fill, margin=2)[0]


def half_shoot(n, truth, frame, actual, seed, gain=GAIN):
    """真値の撮像(1 画素 = 16 × 16 標本)。*actual* は (4, 2) の実際のずれ。"""
    mu = gain * half_capture(n, 16, truth["Q"], truth["fill"], actual[frame]) + DARK
    return physical(mu, seed)


SHIFT_KNOBS = ("dr1", "dc1", "dr2", "dc2", "dr3", "dc3")


def half_model(n, gain=GAIN, shift_range=0.15, init=None, label="half4"):
    """半画素シフト 4 枚の simmodel: つまみは Q(log)・開口率・3 枚のずれ。1 枚 = 1 つの条件。"""

    def half_op(frame=0, Q=1.0, fill=0.9, dr1=0.0, dc1=0.0, dr2=0.0, dc2=0.0, dr3=0.0, dc3=0.0):
        d = ((0.0, 0.0), (dr1, dc1), (dr2, dc2), (dr3, dc3))[int(frame)]
        return half_capture(n, 8, Q, fill, HALF[int(frame)] + np.array(d))

    init = dict(init or {})
    knobs = [{"name": "Q", "lo": 0.3, "hi": 3.0, "scale": "log", "init": init.get("Q", 1.5)},
             {"name": "fill", "lo": 0.3, "hi": 1.0, "init": init.get("fill", 0.65)}]
    for nm in SHIFT_KNOBS:
        knobs.append({"name": nm, "lo": -shift_range, "hi": shift_range, "init": init.get(nm, 0.0), "unit": "px"})
    for k in knobs:
        k.update(step=0, arg=k["name"])
    return L.simcal_model(chain=[{"op": half_op}, {"op": "stage:gain_offset", "args": {"gain": gain, "offset": DARK}}],
                          knobs=knobs, conditions=[{0: {"frame": i}} for i in range(4)], noise=NOISE, label=label)


def budget(Q, fill):
    """解像の予算の閉形式(``pixel_shift_resolution_budget``)。Q = λN/p から F 値を作って渡す。"""
    return PS.pixel_shift_resolution_budget(PITCH_UM, Q * PITCH_UM / WAVE_UM, WAVE_UM, fill, 0.5)


def gain_with_sd(result, cov_names, cov):
    """合わせた Q・開口率での得と、その標準偏差(Fisher の逆を数値微分で伝える)。"""
    Q, fill = result["theta_hat"]["Q"], result["theta_hat"]["fill"]
    g0 = budget(Q, fill)["gain"]
    grad = []
    for nm, h in (("Q", 1e-4 * Q), ("fill", 1e-4)):
        a = dict(Q=Q, fill=fill)
        b = dict(Q=Q, fill=fill)
        a[nm] += h
        b[nm] -= h
        grad.append((budget(a["Q"], a["fill"])["gain"] - budget(b["Q"], b["fill"])["gain"]) / (2 * h))
    ix = [cov_names.index("Q"), cov_names.index("fill")]
    C = cov[np.ix_(ix, ix)]
    g = np.array(grad)
    return g0, float(math.sqrt(max(float(g @ C @ g), 0.0)))


def gain_if_determined(result, n_grid=7):
    """得が決まるか: Q と開口率の両方に点推定があれば、その値での得。片方が決まらなくても、得がその範囲の全体で
    変わらない(関数が決まらない向きに平ら)なら、その一定値を返す。どちらでもなければ ``None``(数を返さない)。

    例: レンズ律速(Q ≥ 2 の側)では使える帯域がレンズの遮断で決まり、開口率によらないので、開口率が決まらなくても
    得は 1 と言える。画素律速では開口率で帯域が動くので、開口率が決まらなければ得も決まらない。
    """
    th = result["theta_hat"]
    if "Q" not in th:
        return None, "Q が決まらない"
    if "fill" in th:
        return budget(th["Q"], th["fill"])["gain"], "Q と開口率の点推定から"
    k = next(k for k in result["model"]["knobs"] if k["name"] == "fill")
    vals = [budget(th["Q"], f)["gain"] for f in np.linspace(k["lo"], k["hi"], n_grid)]
    if max(vals) - min(vals) <= 1e-12:
        return vals[0], "開口率は決まらないが、得は開口率の範囲 %.2f〜%.2f の全体で %.3f のまま" % (k["lo"], k["hi"], vals[0])
    return None, "開口率が決まらず、得は開口率の範囲で %.3f〜%.3f と動く" % (min(vals), max(vals))


def phase_spread(shifts):
    """各軸で、ずれの位相(1 画素で割った余り)が最も離れた 2 枚の円周上の距離 [画素]。半画素の格子なら 0.5。"""
    out = []
    for ax in (0, 1):
        ph = np.mod(np.asarray(shifts)[:, ax], 1.0)
        d = np.abs(ph[:, None] - ph[None, :])
        out.append(float(np.minimum(d, 1.0 - d).max()))
    return out


def pc_init(frames):
    """位相相関で 1 枚目に対する各フレームのずれの当たりを付ける(simcal の初期値。公称からの差 δ)。"""
    init = {}
    for i, (r_, c_) in zip((1, 2, 3), (("dr1", "dc1"), ("dr2", "dc2"), ("dr3", "dc3"))):
        mv = pc_subpixel(frames[0], frames[i])
        s = -mv                                            # B(p) = A(p + s) → 中身の動きは −s
        init[r_] = float(np.clip(s[0] - HALF[i][0], -0.55, 0.55))
        init[c_] = float(np.clip(s[1] - HALF[i][1], -0.55, 0.55))
    return init


def chapter_resolution():
    print("\n5. 解像の得 —— 半画素シフト 4 枚で開口率とレンズの Q を合わせ、閉形式の予算から解像の得を出す")
    n = 32
    truth = {"Q": 1.0, "fill": 0.8, "dr1": 0.03, "dc1": -0.04, "dr2": -0.05, "dc2": 0.02, "dr3": 0.01, "dc3": 0.06}
    out = {}

    def actual_of(tr):
        return HALF + np.array([[0.0, 0.0]] + [[tr[a], tr[b]] for a, b in (("dr1", "dc1"), ("dr2", "dc2"), ("dr3", "dc3"))])

    def run(tr, seed, label, gain=GAIN, shift_range=0.15, init_from_pc=False, fix=None):
        act = actual_of(tr)
        imgs = [half_shoot(n, tr, i, act, seed + i, gain) for i in range(4)]
        init = pc_init(imgs) if init_from_pc else None
        m = half_model(n, gain=gain, shift_range=shift_range, init=init, label=label)
        r = L.simcal_fit(L.simcal_observe(m, imgs), fix=fix, allow_undetermined=True)
        return r, imgs, act

    # (a) 画素律速: Q = 1、開口率 0.8
    r, imgs, act = run(truth, 100, "pixel-limited")
    d2, k, idf = fisher_distance(r, truth)
    p = float(_chi2.sf(d2, k))
    idf_hat = L.simcal_identifiability(r, profile=False)["identifiability"]
    cov = np.linalg.inv(np.asarray(idf_hat["fisher"], float))
    names = idf_hat["knobs"]
    g_hat, g_sd = gain_with_sd(r, names, cov)
    b_true = budget(truth["Q"], truth["fill"])
    b_hat = budget(r["theta_hat"]["Q"], r["theta_hat"]["fill"])
    th = r["theta_hat"]
    print("   画素律速(真値 Q = 1.00、開口率 0.80): 合わせた Q = %.3f ± %.3f、開口率 %.3f ± %.3f、ずれ %s"
          % (th["Q"], idf["crlb"]["Q"], th["fill"], idf["crlb"]["fill"],
             " ".join("%s %+.3f" % (s, th[s]) for s in SHIFT_KNOBS)))
    print("   解像の得: 合わせた係数で %.3f ± %.3f、真値の係数の閉形式 %.3f(使える帯域 1 枚 %.3f → 半画素 %.3f cyc/px、%s)"
          % (g_hat, g_sd, b_true["gain"], b_true["usable_band_single"], b_true["usable_band_shifted"], b_true["regime"]))
    NUMBERS.update({"res_gain_hat": g_hat, "res_gain_sd": g_sd, "res_gain_true": b_true["gain"], "res_fisher_p": p})
    gate("開口率・Q・ずれ 6 個の推定は下界どおりに散る(Fisher 距離 %.1f、χ²(%d) の p = %.3f ≥ %g)" % (d2, k, p, ALPHA),
         p >= ALPHA and r["status"] == "accepted")
    gate("合わせた係数から出した解像の得 %.3f ± %.3f は、真値の係数の閉形式 %.3f と %.1fσ(< 4σ)"
         % (g_hat, g_sd, b_true["gain"], abs(g_hat - b_true["gain"]) / max(g_sd, 1e-12)),
         g_sd > 0 and abs(g_hat - b_true["gain"]) < 4.0 * g_sd and b_hat["regime"] == b_true["regime"])
    sp = phase_spread(HALF + np.array([[0, 0]] + [[th[a], th[b]] for a, b in (("dr1", "dc1"), ("dr2", "dc2"),
                                                                              ("dr3", "dc3"))]))
    out["pixel"] = {"r": r, "g": (g_hat, g_sd), "b_true": b_true, "b_hat": b_hat, "spread": sp, "imgs": imgs}
    # (b) レンズ律速: Q = 2.5(遮断 0.4 cyc/px < 1 枚のナイキスト 0.5)。ずれは (a) と同じ手順で別に合わせたものとして固定
    fixd = {sname: truth[sname] for sname in SHIFT_KNOBS}
    tl = dict(truth, Q=2.5)
    rl, _i, _a = run(tl, 120, "lens-limited", fix=fixd)
    rl = L.simcal_identifiability(rl, profile=True)
    bl_true = budget(tl["Q"], tl["fill"])
    gl, why_l = gain_if_determined(rl)
    regime_l = budget(rl["theta_hat"]["Q"], 0.65)["regime"] if "Q" in rl["theta_hat"] else None
    print("   レンズ律速(真値 Q = 2.5): Q = %s、開口率 %s → %s、得 %s(%s)。閉形式 %s、得 %.3f"
          % (_f(rl["theta_hat"].get("Q")), _f(rl["theta_hat"].get("fill")), regime_l, _f(gl), why_l,
             bl_true["regime"], bl_true["gain"]))
    gate("Q = 2.5 ではレンズ律速と判定し、得は 1(Fiete 1999 の境目 Q = 2 より上: 0.5 cyc/px より上に信号が無く、"
         "シフトしても帯域は増えない)", regime_l == "lens_limited" and gl == 1.0 and bl_true["gain"] == 1.0)
    out["lens"] = {"r": rl, "b_true": bl_true, "gain": gl}
    # (c) 退化したずれ: 行の向きのアクチュエータが止まった(行の実際のずれ 0、公称は半画素)
    ts = dict(truth, dr2=-0.5 + 0.02, dr3=-0.5 - 0.03)
    rs, imgs_s, act_s = run(ts, 140, "stuck rows", shift_range=0.6, init_from_pc=True)
    ths = rs["theta_hat"]
    if all(s in ths for s in SHIFT_KNOBS):
        sh = HALF + np.array([[0, 0]] + [[ths[a], ths[b]] for a, b in (("dr1", "dc1"), ("dr2", "dc2"), ("dr3", "dc3"))])
        sp_s = phase_spread(sh)
        refused = min(sp_s) < 0.25
    else:
        sh, sp_s, refused = None, None, True
    print("   ★行が止まった 4 枚: 合わせたずれの位相の広がり 行 %s・列 %s 画素(半画素の格子なら 0.5)→ %s"
          % ("-" if sp_s is None else "%.3f" % sp_s[0], "-" if sp_s is None else "%.3f" % sp_s[1],
             "得を返さない(半画素の格子が埋まらない)" if refused else "得を返す"))
    gate("★退化したずれは拒否: 行の向きのずれの位相が 0.25 画素も散らない(%s)ので、半画素の格子が行の向きで埋まらず、"
         "解像の得の数を返さない。正常な 4 枚では行・列とも %.3f / %.3f"
         % ("-" if sp_s is None else "%.3f" % sp_s[0], sp[0], sp[1]),
         refused and min(sp) >= 0.25 and sp_s is not None and abs(sh[2][0] - act_s[2][0]) < 0.05)
    out["stuck"] = {"r": rs, "spread": sp_s, "actual": act_s, "shifts": sh}
    # (d) 暗すぎる: 信号 60 DN(50 分の 1)。ずれは正しく分かっているとして固定し、Q と開口率だけを合わせる
    rd, _i, _a = run(truth, 160, "dim", gain=60.0, fix=fixd)          # 雑音で決まらない例(数は返さない側)
    rdi = L.simcal_identifiability(rd, profile=True)
    prof = rdi["identifiability"]["profile"]
    gd, why_d = gain_if_determined(rdi)
    can = gd is not None
    print("   ★暗い 4 枚(信号 60 DN): Q のプロファイル %s(%s〜%s)、開口率のプロファイル %s → %s"
          % (prof["Q"]["class"], _f(prof["Q"]["lower"]), _f(prof["Q"]["upper"]), prof["fill"]["class"],
             ("得 %.3f を返す" % gd) if can else "得を返さない(%s)" % why_d))
    gate("★雑音で決まらなければ拒否: 信号 60 DN では開口率のプロファイル尤度が両側で閉じず(%s)、開口率の点推定が取り下げ"
         "られるので、解像の得を返さない。Q は決まる(%s)" % (prof["fill"]["class"], prof["Q"]["class"]),
         (not can) and prof["fill"]["class"] != "determined" and prof["Q"]["class"] == "determined")
    out["dim"] = {"r": rdi}
    return out


def _f(v):
    return "-" if v is None else "%.3f" % v


# --------------------------------------------------------------------------- #
# 6 と R の共通: 1 枚目を参照にした模型と、G の格子の位相相関                      #
# --------------------------------------------------------------------------- #
def cfa_index(shape):
    """RGGB の色の番号(0 = R、1 = G、2 = B)。"""
    c = np.ones(shape, dtype=np.int64)
    c[0::2, 0::2] = 0
    c[1::2, 1::2] = 2
    return c


def reference_model(ref_raw, obs_raw, wb, frame_ref, frame_obs, noise, roi, label):
    """参照フレーム *ref_raw* の白の釣り合いの像を 3 次スプラインで補間し、*frame_obs* の生の値を予測する simmodel。

    予測 = expo × wb(p)⁻¹ × I_ref(c + R(rot)(p − c) + Δs + δ)。Δs = 公称のずれの差、δ = (dr, dc)。値は黒を引いた DN。
    """
    H, W = ref_raw.shape
    cfa = cfa_index((H, W))
    spl = ndi.spline_filter(ref_raw * wb[cfa], order=3)
    inv = 1.0 / wb[cfa]
    ds = NOMINAL[frame_obs] - NOMINAL[frame_ref]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0

    def ref_op(dr=0.0, dc=0.0, rot=0.0, expo=1.0):
        th = float(rot) * 1e-3
        dy, dx = yy - cy, xx - cx
        qy = cy + math.cos(th) * dy - math.sin(th) * dx + ds[0] + dr
        qx = cx + math.sin(th) * dy + math.cos(th) * dx + ds[1] + dc
        return float(expo) * inv * ndi.map_coordinates(spl, [qy, qx], order=3, prefilter=False, mode="nearest")

    m = L.simcal_model(chain=[{"op": ref_op}], knobs=_knobs({}), noise=noise, label=label)
    return L.simcal_observe(m, [obs_raw], roi=roi)


def g_lattice(raw, r0, c0, n):
    """G の画素だけを 45° 回した格子に並べる(u, v → 行 r0 + u − v、列 c0 + u + v。r0 + c0 は奇数 = RGGB の G)。"""
    u, v = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    return raw[r0 + u - v, c0 + u + v]


def _upsampled_peak(corr, up=200, span=1.0):
    """``phase_correlation_fft`` の相関面の山を、行列の DFT で 1/up 画素まで細かく読む(Guizar-Sicairos ら 2008)。"""
    Rf = np.fft.fft2(corr)
    M, N = Rf.shape
    i, j = np.unravel_index(int(np.argmax(corr)), corr.shape)
    i0 = i - M if i > M // 2 else i
    j0 = j - N if j > N // 2 else j
    ys = i0 + np.arange(-span, span + 1e-9, 1.0 / up)
    xs = j0 + np.arange(-span, span + 1e-9, 1.0 / up)
    U = (np.exp(2j * np.pi * np.outer(ys, np.fft.fftfreq(M))) @ Rf
         @ np.exp(2j * np.pi * np.outer(np.fft.fftfreq(N), xs))).real
    a, b = np.unravel_index(int(np.argmax(U)), U.shape)
    return np.array([ys[a], xs[b]])


#: 位相相関の読みの刻み [画素]。``_upsampled_peak`` の 1/up。
PC_STEP = 1.0 / 200.0


def pc_subpixel(A, B, iters=8):
    """B の中身が A に対してどれだけ動いたか(副画素)。相関の山を細かく読み、その分 B を戻して繰り返す。"""
    m = np.zeros(2)
    for _ in range(iters):
        Bc = ndi.shift(B, -m, order=3, mode="nearest")
        m = m - _upsampled_peak(phase_correlation_fft(A, Bc, whitening=0.0)["correlation"])
    return m


def pc_diagonal_pair(raw_ref, raw_obs, ds=(1.0, -1.0), n=124, starts=(3, 259, 515, 771), r0=128):
    """斜めの公称のずれ *ds* = (±1, ±1) の組の δ = (dr, dc) を、G の格子の位相相関で(升ごと)。

    行 r0 + u − v・列 c0 + u + v の格子では、(dr, dc) の動きは (du, dv) = ((dr + dc)/2, (dc − dr)/2)。公称の分を
    整数の格子の添字でずらしてから、残り δ を副画素で読む。
    """
    # 参照の画素 q と同じ点を見る観測の画素は q − ds。格子では (u, v) → (u − (ds_r + ds_c)/2, v + (ds_r − ds_c)/2)
    ou, ov = -int(round((ds[0] + ds[1]) / 2.0)), int(round((ds[0] - ds[1]) / 2.0))
    out = []
    for c0 in starts:
        c0 = c0 if (r0 + c0) % 2 == 1 else c0 + 1
        A = g_lattice(raw_ref, r0, c0, n)
        big = g_lattice(raw_obs, r0, c0 - 2, n + 2)                   # big[U, V] = 格子の (U − 1, V − 1)
        B = big[1 + ou:1 + ou + n, 1 + ov:1 + ov + n]
        mv = pc_subpixel(A, B)
        du, dv = -mv                                             # B(x) = A(x + δ格子) → 中身の動きは −δ格子
        out.append((du - dv, du + dv))
    return np.array(out)


# --------------------------------------------------------------------------- #
# 6. 実データの手順を合成で確かめる                                             #
# --------------------------------------------------------------------------- #
def synth_strip(truths, h=256, w=520, seed=0):
    """無彩色のチャート風の帯(右へ細かくなる縦縞 + 横縞、0.04〜0.30 cyc/px)を 4 枚撮る(物理の経路、黒を引いた DN)。"""
    tau = 2.0 * math.pi

    def f(y, x):
        return 0.5 + 0.25 * np.sin(tau * (0.04 + 0.00025 * x) * x) + 0.15 * np.sin(tau * 0.08 * y + 0.5)
    frames = []
    for i in range(4):
        s = (NOMINAL[i][0] + truths[i][0], NOMINAL[i][1] + truths[i][1])
        mu = GAIN * capture(f, 4, (h, w), s) + DARK
        frames.append(physical(mu, seed + i) - DARK)
    return np.stack(frames)


def _sd_of(result, names=("dr", "dc")):
    cr = L.simcal_identifiability(result, profile=False)["identifiability"]["crlb"]
    return np.array([cr[n] for n in names])


def chapter_reference_synthetic():
    print("\n6. 実データの手順を合成で確かめる —— 1 枚目をシーンにして、G どうしの斜めの組のずれを升ごとに回収する")
    truths = [(0.0, 0.0), (0.03, -0.05), (-0.04, 0.06), (0.05, 0.02)]
    fr = synth_strip(truths, seed=77)
    nz = {"kind": "emva", "K": 2 * K_DN, "sigma_d": SIGMA_D / math.sqrt(2.0), "dark": 0.0}
    tiles = [(r0, 3 + 128 * j) for r0 in (64, 192) for j in range(4)]
    from scipy.stats import t as _t
    p_all, ratio = [], []
    for a, b in ((0, 2), (1, 3)):
        ds = tuple(NOMINAL[b] - NOMINAL[a])
        want = np.array(truths[b]) - np.array(truths[a])
        got, pcs, sds = [], [], []
        for r0, c0 in tiles:
            c0 = c0 if (r0 + c0) % 2 == 1 else c0 + 1
            r = L.simcal_fit(lattice_model(fr[a], fr[b], r0, c0, ds, REAL_TILE_N, nz, "synthetic %d->%d" % (a, b)),
                             allow_undetermined=True)
            got.append((r["theta_hat"]["dr"], r["theta_hat"]["dc"]))
            sds.append(_sd_of(r))
            pcs.append(pc_diagonal_pair(fr[a], fr[b], ds=ds, n=REAL_TILE_N, starts=(c0,), r0=r0)[0])
        got, pcs, sds = np.array(got), np.array(pcs), np.array(sds)
        nt = len(tiles)
        res = {}
        for lab, est in (("simcal", got), ("位相相関", pcs)):
            e = est - want
            tt = e.mean(0) / (e.std(0, ddof=1) / math.sqrt(nt))
            pv = 2.0 * _t.sf(np.abs(tt), nt - 1)
            p_all += list(pv)
            res[lab] = (est.mean(0), est.std(0, ddof=1), pv)
        ratio += list(got.std(0, ddof=1) / np.median(sds, axis=0))
        print("   組 %d → %d(公称 %+d, %+d): 注入 δ = (%+.3f, %+.3f) px → 升 %d 個の平均 simcal (%+.4f, %+.4f)・"
              "位相相関 (%+.4f, %+.4f)。真値との差の t 検定 p = %.2f / %.2f(simcal)、%.2f / %.2f(位相相関)。simcal の升の"
              "散らばり (%.4f, %.4f) は下界の %.1f / %.1f 倍"
              % (a + 1, b + 1, ds[0], ds[1], want[0], want[1], nt, *res["simcal"][0], *res["位相相関"][0],
                 *res["simcal"][2], *res["位相相関"][2], *res["simcal"][1],
                 *(got.std(0, ddof=1) / np.median(sds, axis=0))))
    NUMBERS.update({"syn_lattice_p_min": float(min(p_all)), "syn_lattice_crlb_ratio": float(max(ratio))})
    gate("合成: G だけの simcal と G の格子の位相相関(どちらも実データの章と同じ手順)は、升 %d 個 × 2 組で注入したずれを"
         "偏りなく回収する(真値との差の平均は升の散らばりの中で 0、t 検定の p の最小 %.3f ≥ %g)" % (len(tiles), min(p_all), ALPHA),
         min(p_all) >= ALPHA,
         "★升の散らばりは Cramér-Rao 下界の最大 %.1f 倍 —— 下界は参照の画像を雑音の無い真のシーンとみなす。参照も雑音つき"
         "で、45° の G の格子は縞を折り返すので、補間の誤差が升ごとに違う向きに出る。だから実データの比べ方も、下界でなく"
         "升の散らばり(対応のある t 検定)にしてある" % max(ratio))
    # モザイク全体を参照にした模型(実データの章で、色をまたぐ組を判定する側)
    cfa = cfa_index(fr.shape[1:])
    wb = np.array([1.0 / QE[0], 1.0, 1.0 / QE[2]])
    roi = (cfa == 1)
    roi[:8] = roi[-8:] = False
    roi[:, :8] = roi[:, -8:] = False
    rm = {}
    for a, b in ((0, 2), (0, 1)):
        rm[(a, b)] = L.simcal_fit(reference_model(fr[a], fr[b], wb, a, b, nz, roi, "synthetic mosaic %d->%d" % (a, b)),
                                  fix={"rot": 0.0}, allow_undetermined=True)
    for (a, b), r in rm.items():
        want = np.array(truths[b]) - np.array(truths[a])
        print("   モザイク全体を参照にした模型 %d → %d: 注入 (%+.3f, %+.3f) → (%+.4f, %+.4f)、χ²/自由度 %.2f、状態 %s"
              % (a + 1, b + 1, want[0], want[1], r["theta_hat"].get("dr", np.nan), r["theta_hat"].get("dc", np.nan),
                 r["fit"]["chi2_red"], r["status"]))
    rc = rm[(0, 1)]
    NUMBERS["syn_cross_chi2"] = rc["fit"]["chi2_red"]
    gate("合成: 倍率色収差の無い世界では、色をまたぐ組 1 → 2 もモザイクの模型で値が返り(状態 %s)、χ²/自由度 %.2f < 2"
         "(実データでは 31 —— 違いは模型に無い物理の分)" % (rc["status"], rc["fit"]["chi2_red"]),
         rc["status"] == "accepted" and rc["fit"]["chi2_red"] < 2.0,
         "★モザイクの模型の値は 0.002〜0.007 px 偏る(下界の 7〜8 倍): 補間したモザイクはシーンそのものではない(R・B の"
         "画素を白の釣り合いで灰色に見立てた像)。だから実データのずれの数は G だけの模型で出し、モザイクの模型は色を"
         "またぐ組の判定にだけ使う")
    return {"fr": fr}


# --------------------------------------------------------------------------- #
# R. 実データ                                                                   #
# --------------------------------------------------------------------------- #
#: 2026-10-18 の実測(ネットの無い CI では印字して飛ばす。門には使わない)。
REAL_RECORDED = ("紙の G の組の差から K = 0.363 DN/電子(光子の転送の 1 点)。G の格子の升 16 個ごとの G だけの simcal: "
                 "斜めの組 1 → 3 は升の平均 (−0.018, +0.048) px、位相相関との升ごとの差の平均 (+0.002, −0.001) px"
                 "(t 検定 p = 0.66 / 0.22)。組 2 → 4 は (−0.003, +0.029) px、差 (+0.002, −0.001) px(p = 0.48 / 0.30)。"
                 "色をまたぐ組 1 → 2 はモザイクの模型で χ²/自由度 31(斜めの組 1.84)、dr が範囲の端に張りつき simcal が拒否")


def _load_sibling(name):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("_sib_" + name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


#: 実データの升(G の格子の 45° 回したひし形): 2 段 × 8 列、1 辺 60 の格子点。重ならない(列の間隔 128 > 2 × 60)。
REAL_TILES = [(r0, 3 + 128 * j) for r0 in (64, 192) for j in range(8)]
REAL_TILE_N = 60


def lattice_model(ref_raw, obs_raw, r0, c0, ds, n, noise, label):
    """G だけの模型: 参照の G の格子を 3 次スプラインで補間し、観測の G の格子を予測する(R・B を一切使わない)。

    観測の画素 p はシーンの p + s_obs、参照の画素 q は q + s_ref を見るので、obs(p) = ref(p + Δs + δ)。格子
    (行 r0 + u − v、列 c0 + u + v)では (u, v) → (u + (Δr + Δc + δr + δc)/2, v + (Δc − Δr + δc − δr)/2)。
    つまみは simcal の dr・dc(センサの行・列の向き)と露出の比。値は黒を引いた DN。
    """
    big = g_lattice(ref_raw, r0, c0 - 2, n + 2)                     # big[U, V] = 格子の (U − 1, V − 1)
    spl = ndi.spline_filter(big, order=3)
    obs = g_lattice(obs_raw, r0, c0, n)
    u, v = np.meshgrid(np.arange(n, dtype=np.float64), np.arange(n, dtype=np.float64), indexing="ij")
    au, av = (ds[0] + ds[1]) / 2.0, (ds[1] - ds[0]) / 2.0

    def lattice_op(dr=0.0, dc=0.0, rot=0.0, expo=1.0):
        qu = u + 1.0 + au + 0.5 * (dr + dc)
        qv = v + 1.0 + av + 0.5 * (dc - dr)
        return float(expo) * ndi.map_coordinates(spl, [qu, qv], order=3, prefilter=False, mode="nearest")

    roi = np.zeros((n, n), bool)
    roi[3:-3, 3:-3] = True
    m = L.simcal_model(chain=[{"op": lattice_op}], knobs=_knobs({"rot": 0.0}), noise=noise, label=label)
    return L.simcal_observe(m, [obs], roi=roi)


def chapter_real():
    pp = _load_sibling("poc_pixel_shift")
    print("\nR. 実データ —— ピクセルシフト 4 枚の未加工 RAW で、G どうしの組のずれを合わせる(%s)" % pp.REAL_SOURCE_SHORT)
    z, why = pp.real_fetch()
    if z is None:
        print("   [skip] %s。2026-10-18 の実測: %s" % (why, REAL_RECORDED))
        return None
    from scipy.stats import t as _t
    black = float(z["black"])
    fr = z["frames"].astype(np.float64) - black
    # 雑音: 紙(明るい所)の上で、同じ点を見る G の組(1 枚目と 3 枚目、斜め)の差の分散 / 2 を明るさで割る(光子の転送の 1 点)
    A = np.concatenate([g_lattice(fr[0], 128, c0, 124).ravel() for c0 in (3, 259, 515, 771)])
    B = np.concatenate([g_lattice(fr[2], 128, c0, 125)[:124, 1:125].ravel() for c0 in (3, 259, 515, 771)])
    M = 0.5 * (A + B)
    bright = M > np.quantile(M, 0.75)
    dd = (A - B)[bright]
    var = (1.4826 * np.median(np.abs(dd - np.median(dd)))) ** 2 / 2.0
    Keff = float(var / M[bright].mean())
    # 残差 = 観測の雑音 + 補間した参照の雑音 → 分散は 2 枚分(K を 2 倍、暗雑音は無視できる大きさ)
    nz = {"kind": "emva", "K": 2.0 * Keff, "sigma_d": 1.0, "dark": 0.0}
    print("   雑音: 紙の G の組の差から K = %.3f DN/電子(明るさ %.0f DN、分散 %.0f DN²)" % (Keff, M[bright].mean(), var))
    pairs = {}
    for a, b in ((0, 2), (1, 3)):
        ds = tuple(NOMINAL[b] - NOMINAL[a])
        rows = []
        for r0, c0 in REAL_TILES:
            c0 = c0 if (r0 + c0) % 2 == 1 else c0 + 1
            r = L.simcal_fit(lattice_model(fr[a], fr[b], r0, c0, ds, REAL_TILE_N, nz, "real %d->%d" % (a, b)),
                             allow_undetermined=True)
            pc = pc_diagonal_pair(fr[a], fr[b], ds=ds, n=REAL_TILE_N, starts=(c0,), r0=r0)[0]
            und = r["undetermined"]
            cls = {k: ("determined" if k not in und else und[k].split(":")[0]) for k in ("dr", "dc")}
            rows.append({"r0": r0, "c0": c0, "theta": r["theta_hat"], "pc": pc, "cls": cls, "chi2": r["fit"]["chi2_red"]})
        both = [w for w in rows if w["cls"]["dr"] == "determined" and w["cls"]["dc"] == "determined"]
        diff = np.array([[w["theta"]["dr"] - w["pc"][0], w["theta"]["dc"] - w["pc"][1]] for w in both])
        est = np.array([[w["theta"]["dr"], w["theta"]["dc"]] for w in both])
        nb = len(both)
        tstat = diff.mean(0) / (diff.std(0, ddof=1) / math.sqrt(nb)) if nb >= 3 else np.array([np.inf, np.inf])
        pt = 2.0 * _t.sf(np.abs(tstat), nb - 1) if nb >= 3 else np.array([0.0, 0.0])
        pairs[(a, b)] = {"rows": rows, "both": both, "diff": diff, "t": tstat, "p": pt, "est": est}
        print("   組 %d → %d(公称 %+d, %+d): 升 %d のうち dr・dc とも決まる %d(χ²/自由度 中央値 %.2f)。simcal の平均 "
              "(%+.4f, %+.4f) px、位相相関との升ごとの差の平均 (%+.4f, %+.4f) px(t = %.2f / %.2f、p = %.3f / %.3f)"
              % (a + 1, b + 1, ds[0], ds[1], len(rows), nb, float(np.median([w["chi2"] for w in rows])),
                 est[:, 0].mean(), est[:, 1].mean(), diff[:, 0].mean(), diff[:, 1].mean(), tstat[0], tstat[1], pt[0],
                 pt[1]))
        print("      升ごとの分類 dr: %s" % " ".join({"determined": "○", "no_influence": "・", "confounded": "△",
                                                     "at_bound": "×"}.get(w["cls"]["dr"], "?") for w in rows))
        print("      升ごとの分類 dc: %s" % " ".join({"determined": "○", "no_influence": "・", "confounded": "△",
                                                     "at_bound": "×"}.get(w["cls"]["dc"], "?") for w in rows))
    ok = all(len(pairs[k]["both"]) >= 6 and bool((pairs[k]["p"] >= ALPHA).all()) for k in pairs)
    NUMBERS.update({"real_K": Keff, "real_p_02": float(min(pairs[(0, 2)]["p"])), "real_p_13": float(min(pairs[(1, 3)]["p"]))})
    gate("実データ: G どうしの斜めの組 2 つのずれは、G だけの simcal と G の格子の位相相関(別の方法)で合う —— 升ごとの差の"
         "平均は 0 と区別できない(対応のある t 検定、p = %.3f / %.3f ≥ %g)"
         % (min(pairs[(0, 2)]["p"]), min(pairs[(1, 3)]["p"]), ALPHA), ok)
    # 色をまたぐ組: 1 枚目を参照にしたモザイク全体の模型(G が R・B を見る)
    cfa = cfa_index(fr.shape[1:])
    m4 = PS.pixel_shift_merge(fr / 8000.0, NOMINAL, "RGGB")
    Y = m4 @ np.array([0.299, 0.587, 0.114])
    ls = np.sqrt(np.maximum(ndi.uniform_filter(Y ** 2, 15) - ndi.uniform_filter(Y, 15) ** 2, 0))
    paper = (ls < 0.01 * Y.max()) & (Y > 0.6 * Y.max())
    wb = np.array([np.median(m4[..., 1][paper]) / np.median(m4[..., 0][paper]), 1.0,
                   np.median(m4[..., 1][paper]) / np.median(m4[..., 2][paper])])
    roi = (cfa == 1)
    roi[:8] = roi[-8:] = False
    roi[:, :8] = roi[:, -8:] = False
    res = {}
    for a, b in ((0, 2), (0, 1)):
        res[(a, b)] = L.simcal_fit(reference_model(fr[a], fr[b], wb, a, b, nz, roi, "real mosaic %d->%d" % (a, b)),
                                   fix={"rot": 0.0}, allow_undetermined=True)
    rc, rd = res[(0, 1)], res[(0, 2)]
    print("   モザイク全体を参照にした模型(白の釣り合い R × %.3f、B × %.3f): 斜めの組 1 → 3 は χ²/自由度 %.2f、"
          "色をまたぐ組 1 → 2 は χ²/自由度 %.1f・状態 %s・決まらない %s"
          % (wb[0], wb[2], rd["fit"]["chi2_red"], rc["fit"]["chi2_red"], rc["status"],
             {k: v.split(":")[0] for k, v in rc["undetermined"].items()}))
    NUMBERS.update({"real_chi2_diag_mosaic": rd["fit"]["chi2_red"], "real_chi2_cross": rc["fit"]["chi2_red"]})
    gate("★実データ: 色をまたぐ組 1 → 2(G が R・B を見る)は平行移動では説明できない —— simcal が値を取り下げ(状態 %s)、"
         "χ²/自由度 %.1f は同じ模型の斜めの組(%.2f)の 10 倍を超える。2 つの組の間のずれは無彩色のチャートからは決まらない"
         % (rc["status"], rc["fit"]["chi2_red"], rd["fit"]["chi2_red"]),
         rc["status"] != "accepted" and rc["fit"]["chi2_red"] > 10.0 * rd["fit"]["chi2_red"])
    return {"fr": fr, "wb": wb, "pairs": pairs, "cross": rc, "K": Keff}


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _zoom(img, k):
    return np.repeat(np.repeat(img, k, axis=0), k, axis=1)


def _raw_view(raw):
    """生の値(RGGB)を灰色の絵へ(白の釣り合い = QE の逆、黒を引いて 0..1)。"""
    cfa = cfa_index(raw.shape)
    g = (raw - DARK) / GAIN / QE[cfa]
    return np.clip(g, 0.0, 1.0)


CLASS_COLOUR = {"determined": (0.0, 0.62, 0.45), "combination": (0.90, 0.62, 0.0), "no_influence": (0.55, 0.55, 0.55)}
CLASS_JA = {"determined": "決まる", "combination": "組でしか決まらない", "no_influence": "効かない"}


def make_figures(screen, rec, mp, poor, resol, real):
    # 1. ふるい: 6 種の被写体と、dr・dc の分類
    tiles = []
    for kind, label in KINDS:
        row = screen[kind]
        im = np.repeat(_zoom(_raw_view(row["img"]), 8)[..., None], 3, -1)
        cl = row["class"]
        im = np.asarray(fs.text_box(im, "%s" % label, (6, 6), font_size=16))
        im = np.asarray(fs.text_box(im, "dr: %s" % CLASS_JA[cl["dr"]] if cl["dr"] in CLASS_JA else "dr: %s" % cl["dr"],
                                    (6, im.shape[0] - 80), font_size=14))
        im = np.asarray(fs.text_box(im, "dc: %s" % CLASS_JA[cl["dc"]] if cl["dc"] in CLASS_JA else "dc: %s" % cl["dc"],
                                    (6, im.shape[0] - 42), font_size=14))
        tiles.append(im)
    gap = np.ones((tiles[0].shape[0], 6, 3))
    top = np.concatenate([tiles[0], gap, tiles[1], gap, tiles[2]], 1)
    bot = np.concatenate([tiles[3], gap, tiles[4], gap, tiles[5]], 1)
    sheet = np.concatenate([top, np.ones((6, top.shape[1], 3)), bot], 0)
    figs.save("screen_by_stripe_direction", sheet,
              "【1 章】同じ 4 つのつまみ(フレームのずれ dr・dc・回転・露出)を、縞の向きだけが違う 6 種の被写体で Morris の"
              "ふるいにかけた。撮れた生の画像(32 × 32 画素を 8 倍、灰色は白の釣り合いを戻した値)と、dr・dc の分類。縦縞では"
              "縞に沿った dr が画像を変えず「効かない」、斜めの縞では dr と dc が縞を横切る組(右上がりは dr + dc、右下がりは dr − dc)"
              "でしか決まらない —— 開口問題。")
    # 2. 決まらない地図: 星 + 升の分類 + Cramér-Rao の楕円
    k = 8 if REDUCED else 6
    npx, tile, fn = mp["npx"], mp["tile"], mp["fn"]
    q = (np.arange(npx * k) + 0.5) / k
    Yq, Xq = np.meshgrid(q, q, indexing="ij")
    base = np.clip(fn(Yq, Xq), 0, 1)
    rgb = np.repeat(base[..., None], 3, -1) * 0.75 + 0.25
    for t in mp["tiles"]:
        col = np.array(CLASS_COLOUR[t["class"]])
        y0, x0 = t["i"] * tile * k, t["j"] * tile * k
        sl = (slice(y0, y0 + tile * k), slice(x0, x0 + tile * k))
        rgb[sl] = 0.72 * rgb[sl] + 0.28 * col
    rgb[::tile * k, :] = 1.0
    rgb[:, ::tile * k] = 1.0
    tt = np.linspace(0, 2 * np.pi, 64)
    for t in mp["tiles"]:
        C2 = mp["cov"][t["i"], t["j"]]
        if not np.isfinite(C2).all():
            continue
        w, v = np.linalg.eigh(0.5 * (C2 + C2.T))
        a, b = math.sqrt(max(w[1], 0)), math.sqrt(max(w[0], 0))
        scale = 0.42 * tile * k / max(a, 1e-300)                      # 升ごとに長軸を升の幅の 0.84 に揃える(形と向き)
        cy, cx = (t["i"] + 0.5) * tile * k, (t["j"] + 0.5) * tile * k
        pts_dr = a * np.cos(tt)[:, None] * v[:, 1][None, :] + b * np.sin(tt)[:, None] * v[:, 0][None, :]
        xs = cx + scale * pts_dr[:, 1]
        ys = cy + scale * pts_dr[:, 0]
        rgb = np.asarray(fs.draw_polyline(rgb, np.c_[xs, ys], color=(0.75, 0.1, 0.1), width=2, closed=True))
    figs.save("undetermined_map_star", rgb,
              "【3 章・見せ場】シーメンススター(腕 %d 本)を 8 画素の升に区切り、升ごとにフレームのずれ (dr, dc) を合わせた。"
              "升の色 = simcal_fit の分類(緑 = 両方決まる、橙 = 組でしか決まらない、灰 = 効かない)。赤い楕円 = Cramér-Rao の"
              "1σ(Fisher 行列の逆の dr・dc の部分)の形と向き(升ごとに長軸を升の幅の 0.84 に揃えた。大きさは升ごとに違う)。星の腕の上では縞が放射状の 1 方向なので、楕円は"
              "半径の向きに伸びる —— 縞に沿ったずれ(半径の向き)は画像を変えない。橙の升の「決まる組」は接線の向きと、升が見込む"
              "角度の半分以内で揃う(最大 %.1f°)。星の外の板は何も決まらない。"
              % (32 if not REDUCED else 24, NUMBERS["map_combo_angle_max"]))
    # 3. 回収: 真値と推定の差 / 下界
    rows = rec["rows"]
    zx = np.array([(th["dr"] - tr["dr"]) / cr["dr"] for _f, tr, th, cr in rows])
    zy = np.array([(th["dc"] - tr["dc"]) / cr["dc"] for _f, tr, th, cr in rows])
    ang = np.linspace(0, 2 * np.pi, 200)
    figs.save_plot("recovery_vs_crlb",
                   [("フレーム %d 枚の推定(dr, dc の誤差 / 下界)" % len(rows), zx, zy),
                    ("1σ", np.cos(ang), np.sin(ang)), ("3σ", 3 * np.cos(ang), 3 * np.sin(ang))],
                   xlabel="dr の誤差 / σ_CRLB", ylabel="dc の誤差 / σ_CRLB", kinds=["scatter", "line", "line"],
                   styles=[None, "dashed", "dotted"], colors=["emphasis", "reference", "reference"], aspect="equal",
                   title="注入した ±0.1 px のずれの回収: 誤差は Cramér-Rao 下界どおりに散る",
                   caption="【2 章】3 枚のフレームに dr・dc ∈ ±0.1 px、回転 ±2 mrad、露出 ±2 %% を注入し、物理の経路(ポアソン + "
                           "読み出し雑音 + 丸め)で撮って合わせた。軸は誤差を下界で割った値。全つまみの Fisher 距離の和は "
                           "%.1f(χ²(%d)、p = %.2f)。雑音を 1/4 に見誤ったモデルでは同じ門が p = %.0e で落ちる。"
                           % (rec["d2"], rec["dof"], NUMBERS["rec_fisher_p"], NUMBERS["rec_fisher_p_wrong_noise"]))
    # 4. 貧しいモデル: 正規化した残差の地図(平行移動だけ | 回転も)。符号つきで塗る(赤 = 正、青 = 負)
    panels = []
    for name in ("translation", "full"):
        r = poor[name]["fit"]
        sims = L.simcal_simulate(r["model"], r["theta_hat"])[0]
        resid = (poor["obs"] - sims) / np.sqrt(K_DN * np.maximum(sims - DARK, 0) + (K_DN * SIGMA_D) ** 2 + 1 / 12.0)
        panels.append(_zoom(ndi.uniform_filter(resid, 5), 8))
    figs.save("poor_model_residuals", np.concatenate([panels[0], np.zeros((panels[0].shape[0], 8)), panels[1]], 1),
              "【4 章】3 mrad 回ったフレームを 2 つのモデルで合わせた残差(雑音の標準偏差で割り、5 × 5 で平均、8 倍。赤 = 正、"
              "青 = 負)。左 = 平行移動だけ(χ²/自由度 %.2f、残差 PCA %s): 中心から離れるほど符号の揃った帯が残り(回転の分)、"
              "絶対の門(χ² の上側確率)と残差 PCA が拒否する。右 = 回転も(χ²/自由度 %.2f、%s): 残差は雑音だけ。"
              % (poor["translation"]["v"]["fit"]["chi2_red"], poor["translation"]["v"]["discrepancy"]["verdict"],
                 poor["full"]["v"]["fit"]["chi2_red"], poor["full"]["v"]["discrepancy"]["verdict"]), signed=True)
    # 5. 解像の得: 系の MTF(真値・合わせた係数)と帯域
    f = np.linspace(0.0, 1.0, 201)
    bt, bh = resol["pixel"]["b_true"], resol["pixel"]["b_hat"]
    th = resol["pixel"]["r"]["theta_hat"]
    sys_t = np.abs(np.sinc(f * 0.8)) * _mtf_diff(f * 1.0)
    sys_h = np.abs(np.sinc(f * th["fill"])) * _mtf_diff(f * th["Q"])
    sys_l = np.abs(np.sinc(f * 0.8)) * _mtf_diff(f * 2.5)
    figs.save_plot("resolution_budget",
                   [("系の MTF(真値: 開口率 0.8、Q = 1.0)", f, sys_t),
                    ("合わせた係数(開口率 %.3f、Q = %.3f)" % (th["fill"], th["Q"]), f, sys_h),
                    ("レンズ律速(Q = 2.5)", f, sys_l),
                    ("MTF 0.1", np.array([0, 1.0]), np.array([0.1, 0.1])),
                    ("1 枚のナイキスト 0.5", np.array([0.5, 0.5]), np.array([0, 1.0])),
                    ("使える帯域(半画素)%.3f" % bh["usable_band_shifted"],
                     np.array([bh["usable_band_shifted"]] * 2), np.array([0, 1.0]))],
                   xlabel="空間周波数 [cyc/px]", ylabel="MTF", ylim=(0, 1.02),
                   kinds=["line"] * 6, styles=["dashed", None, None, "dotted", "dotted", "dashed"],
                   colors=["reference", "emphasis", "wrong", "neutral", "neutral", "emphasis"],
                   title="解像の得 = 使える帯域の比: 合わせた係数で %.3f ± %.3f(閉形式 %.3f)"
                         % (resol["pixel"]["g"][0], resol["pixel"]["g"][1], bt["gain"]),
                   caption="【5 章】半画素シフト 4 枚(白黒)で、開口率・レンズの Q = λN/p・3 枚のずれを合わせ、"
                           "pixel_shift_resolution_budget の閉形式(|sinc(f·開口率)| × 回折の MTF)に入れた。使える帯域 = "
                           "折り返しを起こさず系の MTF が 0.1 以上の上限(1 枚はナイキスト 0.5 で頭打ち)。Q = 2.5 では"
                           " 0.4 cyc/px でレンズが遮断し、シフトしても帯域は増えない(得 1)。行のアクチュエータが止まった"
                           " 4 枚と、信号 60 DN の暗い 4 枚では得の数を返さない。")
    if real is not None:
        fr = real["fr"]
        pp = _load_sibling("poc_pixel_shift")
        cfa = cfa_index(fr.shape[1:])
        g = fr[0] * real["wb"][cfa]
        g = np.clip(g / np.quantile(g, 0.995), 0, 1) ** (1 / 2.2)
        im = np.repeat(g[..., None], 3, -1) * 0.8 + 0.1
        n = REAL_TILE_N
        for w in real["pairs"][(0, 2)]["rows"]:
            r0, c0 = w["r0"], w["c0"]
            # ひし形の 4 頂点(x = 列, y = 行): (u, v) = (0, 0), (n−1, 0), (n−1, n−1), (0, n−1)
            pts = np.array([[c0, r0], [c0 + n - 1, r0 + n - 1], [c0 + 2 * n - 2, r0], [c0 + n - 1, r0 - n + 1]], float)
            k = w["cls"]["dr"] if w["cls"]["dr"] != "determined" else w["cls"]["dc"]
            col = CLASS_COLOUR.get(k if k in CLASS_COLOUR else ("combination" if k == "confounded" else "no_influence"))
            im = np.asarray(fs.draw_polyline(im, pts, color=col, width=2, closed=True))
        im = _zoom(im, 2)
        figs.save("real_tiles", im,
                  "【実データ】ピクセルシフト 4 枚の未加工 RAW の 1 枚目(白の釣り合いを掛けたモザイクのまま、256 × 1152 画素を 2 倍)。"
                  "ひし形 = G の格子(45° 回した格子)の升 16 個。升ごとに 1 → 3 枚目のずれを G だけの simcal で合わせ、"
                  "dr・dc とも決まった升は緑、片方が決まらない升は橙 / 灰。決まった升では位相相関(別の方法)と升ごとの差の平均が "
                  "0 と区別できない(t 検定の p = %.2f / %.2f)。色をまたぐ組は χ²/自由度 %.0f で拒否。"
                  % (NUMBERS["real_p_02"], NUMBERS["real_p_13"], real["cross"]["fit"]["chi2_red"])
                  + pp.REAL_SOURCE_SHORT, source=pp.REAL_SOURCE)


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC ピクセルシフトのずれと開口を sim-to-real 較正で合わせる(予算 %s)" % ("reduced" if REDUCED else "full"))
    real = chapter_real()
    screen = chapter_screen()
    rec = chapter_recovery()
    mp = chapter_map()
    poor = chapter_poor()
    resol = chapter_resolution()
    chapter_reference_synthetic()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(screen, rec, mp, poor, resol, real)
    print("\n所要 %.1f s(CPU %.1f s)、門 %d 件中 NG %d 件" % (time.time() - t0, time.process_time() - c0, len(GATES),
                                                       len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
