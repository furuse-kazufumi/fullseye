# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""熱画像は温度画像ではない —— 放射率を取り違えたまま「温度」と呼ぶ。

赤外カメラが測るのは**帯域積分した放射輝度**です。温度はそこから
「放射率 ε・反射見かけ温度 T_refl・透過率 τ・大気温度 T_atm を知っている」
という仮定の上で**逆算**した量にすぎません。画面に出る 5 桁の数字と ℃ の
単位は、その仮定を隠します。この PoC は、前向きモデル

    L_meas = τ [ ε L_bb(T_obj) + (1−ε) L_bb(T_refl) ] + (1−τ) L_bb(T_atm)

に真値を植えてから、(a) 放射率の取り違え、(b) 反射項の落とし、(c) 透過率、
(d) カメラの雑音と量子化、を**別々に**測ります。そして本題は
**その不確かさが足し算にならない**こと —— 現場でよく使う独立 RSS の
「95 % 区間」が、実際には何 % しか真値を包まないかを数えます。

EXTEND: 実測の熱画像に差し替えるなら :func:`scene_truth` が返す
``(T_obj, ε)`` の 2 枚を実機のデータに置き換え、:class:`Camera` の
``a`` / ``b`` を黒体炉で引いた実測の校正係数に、:data:`NETD_K` を
機器の仕様値に置き換えます(生の DN が読めない機種なら、カメラが出す
「ε=1・τ=1 で逆算した見かけ温度」を :func:`BandTable.radiance` に通して
放射輝度へ戻すのが実務の入口)。撮り方は 1 行ずつ:
**黒体炉** = 開口を視野いっぱいに、放射率 0.99 以上の空洞を 5 点以上の
温度で(a・b と非直線性が出る)。**加熱板** = 面内の温度分布を熱電対で
別に測り、板の縁は熱が逃げるので中央だけ使う。**既知放射率試料** = 同じ
板の上に半分だけ艶消し黒塗料(ε≈0.95)を塗り、塗った所と地肌を**同時に**
撮る(同じ T_refl・同じ τ の下で ε だけが違う 2 領域が 1 枚に入る)。
★**この PoC の中心である「真の ε と比べる」は実データではできません** ——
放射率は材料・表面状態・角度・波長・温度で変わり、真値を測る手段が
「別の温度計で表面温度を測って逆算する」しかないからです(その別の
温度計の不確かさが、そのまま ε の不確かさになる)。実データでできるのは
§4 の**区間の包含率**を「熱電対の読みを真値とみなして」数えることと、
§2 の ε を振ったときの感度だけで、絶対誤差は出せません。

この PoC が示すこと(数字はすべて最終実行の実測値):

1. **往復は閉じる**。真値を植てて前向きに作った DN を、同じ ε・T_refl・τ で
   逆算すると Case-0 の誤差は **2.98e-08 K**(表引きの離散化だけ)。
   量子化を入れて 1.61e-03 K、NETD 30 mK を入れて 2.36e-02 K。
   **ここが床**です。以下の誤差はすべてこの床の 3 桁以上 上にあります。
2. ★**崖は測る前に閉形式で出せる**。帯域の実効 Planck 指数 n = c2/(λ_eff T)
   を使うと ΔT/T ≈ −(1/n)(Δε/ε)(1 − L_bb(T_refl)/L_bb(T_obj))。
   λ_eff を**放射輝度で重み付けた 1/λ の平均の逆数**に取ると、350 K・LWIR で
   予測 n = 4.169 に対し数値微分の実測 n = 4.286(差 2.7 %)。帯の中央
   (11 µm)を λ_eff にする素朴な取り方だと予測 3.737(差 12.8 %)——
   **どこを「実効波長」と呼ぶかで 1 割違います**。
3. ★★**予測を 1 つ外しました**。「低温ほど崖が急」と予測して印字しましたが、
   **絶対誤差では逆**でした。ΔT = (λ_eff T²/c2)·(Δε/ε)·(1−L_r/L_o) は
   **T の 2 乗**で増えるので、Δε/ε = 0.05 の同じ取り違えが LWIR で
   300 K → **1.87 K**、800 K → **16.60 K**。閉形式は最初から
   そう言っていて、**自分の式を読み違えていました**。
   ★ただし**物差しを変えると予測は当たります**: 現場が使うのは絶対温度でなく
   **周囲からの温度上昇 (T_obj − T_refl)** なので、その比で見ると
   305 K(上昇 10 K)で **19.3 %**、800 K(上昇 505 K)で **3.3 %** ——
   **低温ほど急**。同じ実験の同じ数字が、割る相手で逆の結論を出します。
4. **低放射率は無条件に急**。Δε = 0.02 の**同じ絶対誤差**が、塗装面
   (ε=0.95)では **0.35 K**、研磨金属(ε=0.10)では **6.79 K** ——
   **19.4 倍**。ε で割るので当たり前ですが、現場の ε は「表から拾った値」で、
   ε=0.1 の材料の表の値が ±0.02 で済む保証はどこにもありません。
5. **MWIR は放射率に強く、反射に弱い**。350 K で同じ Δε/ε = 0.05 の
   温度誤差は LWIR 2.54 K に対し MWIR **0.94 K**(n が 4.29 → 11.63 と
   大きいから)。ところが反射項の効きは逆で、T_refl を 10 K 取り違えた
   ときの誤差は LWIR 0.29 K に対し MWIR **0.14 K**……ではなく、
   ε=0.10 の面では LWIR 2.73 K / MWIR **1.87 K**。**帯を変えても
   「反射が効く」順位は変わりません**。
6. **ゼロ点 3 つはどれも失格**。350 K・ε=0.95 の塗装面で、DN をそのまま
   2 点校正で温度と呼ぶと **−9.24 K**、ε=1 固定(= 見かけ温度)で
   **−2.29 K**、反射項を落とすと **+0.60 K**。★いちばん質が悪いのは
   ε=1 固定です —— 絵は完全にもっともらしく、単位も ℃ で、**どこにも
   異常が出ません**。
7. ★★**独立 RSS の「95 % 区間」は 95 % を包みません**。ε と T_refl に
   相関 ρ=+0.7 を入れた現実(酸化した金属面 ε=0.60±0.05、T_refl=300±5 K)で
   20000 試行を数えると、包含率は **RSS 88.32 % / 相関つき MC 94.94 %**。
   ★**床を先に測ってあります**: ρ=0 の現実では RSS 94.95 % / MC 94.98 %
   —— **RSS は相関が無ければ正しい**ので、落ちた 6.6 ポイントは
   実装のバグではなく**相関を無視したこと**そのものです。
   ρ=−0.7 なら RSS は逆に **99.26 %** まで**過剰に**包みます
   (保守的だが、その区間で合否を切ると今度は落としすぎる)。
8. ★**外れ方は片側に寄ります**。ρ=+0.7 の RSS の取りこぼし 11.68 % の
   内訳は 下側 5.03 % / 上側 6.65 %。逆算が ε で割る非線形なので分布が
   歪み、**対称な ±k·u は歪んだ分布を対称に外しません**。
9. ★★**guard band(合否判定)で誤合格が 3.4 倍になります**。「表面温度
   ≤ 80 ℃ なら合格」を 40000 試行(真値は 65〜95 ℃ の一様分布)で判定すると、
   誤合格率は 不確かさ無視 **11.79 %** / RSS の guard band **3.36 %** /
   相関つき MC の guard band **1.87 %**。誤不合格率は逆に
   11.87 % / 22.73 % / **25.64 %**。★**誤合格を減らす唯一の代償が
   誤不合格**で、RSS はその交換レートを**間違った側に**倒します
   (安全なつもりで、実際には誤合格を 1.8 倍残している)。
10. ★**単位の取り違えは「例外で止まる」ものと「静かに間違う」ものに
    分かれます**。6 通り試して **例外 2 / 静かに 4**。止まったのは
    波長を µm のまま SI 式に入れた場合と、T_refl をセ氏の数値のまま
    入れた場合で、どちらも `fs.interp_linear(out_of_range='raise')` が
    校正表の外だと言って落ちます(fail-closed が効いた)。静かに間違うのは
    (a) DN を平均してから温度に直す(**+0.79 K** の偏り。L が T に凸なので
    Jensen の不等式ぶん必ず高く出る)、(b) 見かけ温度を表面温度と呼ぶ、
    (c) τ を二重に掛ける(**−1.86 K**)、(d) ΔT/T をセ氏で計算して n を出す
    (感度が **4.55 倍**)。**絵は 4 つとももっともらしいままです**。
11. ★**熱画像の上で「いちばん熱い所が いちばん冷たく見えます」**。
    塗装面(ε=0.95)の上に研磨したボルト(ε=0.10)があり、**両方とも
    375 K** の場面で、ε=1 の見かけ温度はボルトを **312.8 K** と表示します
    —— 周囲の塗装面 373.2 K より **60.4 K 低い**。絵の上ではボルトは
    「冷えている」ように見え、**そこだけ健全に見えます**。ε 地図を入れて
    補正すると 375.0 K に戻ります(残差 rms 0.121 K = 雑音の床)。
12. **道具の穴 —— この分野の op は 1 つもありません**。`fs.<name>` /
    `fs.op.<name>` / `fs.ledger.<name>` / `fs.op_find(語幹)` の 4 層すべてを
    引いて、``planck`` / ``emissiv`` / ``temperature`` / ``radiom`` /
    ``thermal`` / ``infrared`` / ``stefan`` / ``kelvin`` / ``atmos`` は
    **4 層とも 0 件**。★``blackbody`` は `op_find` が **4 件**返しますが
    中身は ``cv_blackhat`` / ``morph_blackhat3d`` などのモルフォロジで、
    **件数を見て「在る」と読むと外します**。``uncert`` の 1 件は
    ``photon_uncertainty``(Poisson の誤差棒。使いました)、``montecarlo``
    の 1 件は ``tolerance_analysis``(レンズ公差専用で、任意の測定モデルには
    使えない)。使えた op は `interp_linear` / `stat_covariance` /
    `stat_correlation` / `mat_eigh` / `stat_describe` / `stat_histogram` /
    `poly_fit` / `photon_uncertainty` / `noise_sigma` /
    `beer_lambert_transmittance`。★次に埋めるべき op は §7 に列挙しました。

【グラウンドトゥルース】Planck 則を**帯域で数値積分**したものを真値とし
(:func:`band_radiance_direct`、Simpson 513 節点)、逆変換は同じ積分から
作った単調な校正表(:class:`BandTable`、220–1400 K を 0.05 K 刻み)を
`fs.interp_linear` で引きます。表と直接積分の一致は §1 で測ってあります
(最大 3.1e-11 の相対差)。対照群は (a) ε=1 の見かけ温度、(b) 反射項を
落とした処理、(c) 相関 ρ=0 の現実、(d) MWIR 帯。

【来歴】放射定数は 2019 年 SI の**定義値**から出しています(h = 6.62607015e-34
J·s、c = 299792458 m/s、k = 1.380649e-23 J/K はすべて定義値なので、
c1L = 2hc² = 1.191042972e8 W·µm⁴·m⁻²·sr⁻¹ と c2 = hc/k = 1.4387768775e4 µm·K は
**測定値ではなく厳密値**)。帯域 8–14 µm / 3–5 µm は市販カメラの慣用の
区切りです。**放射率の値 0.95(艶消し塗装)/ 0.60(酸化金属)/ 0.10
(研磨金属)は代表値として置いた仮定で、出典のある定数ではありません** ——
実際の値は表面状態・角度・波長・温度で動きます。NETD 30 mK、14 bit、
合否閾値 80 ℃、ε と T_refl の相関 ρ=0.7 も、すべてこの PoC のために
置いた仮定です(ρ は「同じ参照面から ε と T_refl を同時に決める」現場の
手順から**あり得る**という理由で置いた値で、測った値ではありません)。
手法の出典は NIST IR 8098「Thermal-Imaging Calibration and Measurement
Procedures for High-Magnification Thermography」
<https://nvlpubs.nist.gov/nistpubs/ir/2016/NIST.IR.8098.pdf>、
NIST SP 250-43「Radiance Temperature Calibrations」
<https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication250-43.pdf>、
相関つき Monte Carlo の考え方は NIST Uncertainty Machine
<https://uncertainty.nist.gov/>(GUM Supplement 1)。**どの文献からも
数値は引いていません**(オフラインで完結させるため、取得もしていません)。
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

# --------------------------------------------------------------------------- #
# 放射定数 —— 2019 年 SI の定義値から出す(測定値ではない)                      #
# --------------------------------------------------------------------------- #
#: Planck 定数 [J·s](2019 年 SI の定義値)。
H_PLANCK = 6.62607015e-34
#: 真空中の光速 [m/s](定義値)。
C_LIGHT = 299792458.0
#: Boltzmann 定数 [J/K](定義値)。
K_BOLTZ = 1.380649e-23

#: 第 1 放射定数(放射輝度形)[W·µm⁴·m⁻²·sr⁻¹] = 2hc²。λ を **µm** で使う形。
C1L_UM = 2.0 * H_PLANCK * C_LIGHT ** 2 * 1.0e24
#: 第 2 放射定数 [µm·K] = hc/k。**λ を µm で使う**ときはこちら。
C2_UM = H_PLANCK * C_LIGHT / K_BOLTZ * 1.0e6
#: 同じ定数の **SI(m·K)版**。§5 で「取り違えると何が起きるか」に使う。
C2_M = H_PLANCK * C_LIGHT / K_BOLTZ

#: 帯域 ``(λ下限, λ上限)`` [µm]。市販カメラの慣用の区切り。
BANDS = {"LWIR": (8.0, 14.0), "MWIR": (3.0, 5.0)}

#: 帯域積分の Simpson 節点数(奇数)。§1 で収束を測る。
N_LAMBDA = 513

#: 校正表の温度範囲 [K] と刻み。逆変換(L → T)はこの表を引く。
TAB_LO, TAB_HI, TAB_STEP = 220.0, 1400.0, 0.05

#: 放射率の代表値(**出典のある定数ではなく、この PoC のための仮定**)。
EPS_PAINT, EPS_OXIDE, EPS_POLISH = 0.95, 0.60, 0.10

#: 場面の既定値: 反射見かけ温度 / 大気温度 [K]。
T_REFL_REF, T_ATM_REF = 300.0, 293.15

#: 大気の消散係数 [1/mm] と光路長 [mm]。σ は**この PoC のために置いた仮定**
#: (実際の大気の消散は帯域・水蒸気量・エアロゾルで決まる)。
ATM_SIGMA_PER_MM, ATM_PATH_MM = 2.6e-5, 2000.0

#: 大気透過率。定数を書き写さず :func:`fullseye.beer_lambert_transmittance` で出す。
TAU_REF = float(fs.beer_lambert_transmittance(ATM_PATH_MM, ATM_SIGMA_PER_MM))

#: カメラの雑音等価温度差 [K] と量子化ビット数(仕様値として置いた仮定)。
NETD_K, ADC_BITS = 0.030, 14

#: 合否の閾値 [℃]。「表面温度 ≤ 80 ℃ なら合格」。
GUARD_LIMIT_C = 80.0

#: 摂氏 → ケルビンの下駄。
T0_C = 273.15


# --------------------------------------------------------------------------- #
# Planck 則 —— 真値はここから作る                                               #
# --------------------------------------------------------------------------- #
def planck_spectral(lam_um, t_k):
    """分光放射輝度 [W·m⁻²·sr⁻¹·µm⁻¹]。``lam_um`` は **µm**、``t_k`` は **K**。

    L_λ = c1L / (λ⁵ (exp(c2/(λT)) − 1))。``expm1`` を使うのは、λT が大きい
    (= 帯の長波側・高温側)ときに ``exp(x) − 1`` が 1 − 1 の桁落ちを起こす
    ため。ここは Rayleigh–Jeans 側で普通に踏む。
    """
    lam = np.asarray(lam_um, np.float64)
    t = np.asarray(t_k, np.float64)
    x = C2_UM / (lam * t)
    return C1L_UM / (lam ** 5 * np.expm1(x))


def _simpson_nodes(lo: float, hi: float, n_nodes: int = N_LAMBDA):
    """Simpson の節点と重み。``n_nodes`` は奇数(区間数が偶数になる)。"""
    if n_nodes % 2 == 0:
        raise ValueError("Simpson は奇数の節点数が要る: %d" % n_nodes)
    lam = np.linspace(lo, hi, n_nodes)
    w = np.ones(n_nodes, np.float64)
    w[1:-1:2] = 4.0
    w[2:-1:2] = 2.0
    return lam, w * (hi - lo) / (n_nodes - 1) / 3.0


def band_radiance_direct(band: str, t_k, n_nodes: int = N_LAMBDA):
    """帯域積分した放射輝度 [W·m⁻²·sr⁻¹]。**真値はこれ**(表は近似)。

    ``t_k`` は任意形状。λ 軸を最後に足すので、``(..., n_nodes)`` の一時配列を
    作る —— 大きな ``t_k`` を渡すときは呼び手側で分割すること(§1 の表作りは
    そうしている)。
    """
    lo, hi = BANDS[band]
    lam, w = _simpson_nodes(lo, hi, n_nodes)
    t = np.asarray(t_k, np.float64)
    li = planck_spectral(lam, t[..., None])
    return np.tensordot(li, w, axes=([-1], [0]))


def band_effective_lambda(band: str, t_k: float) -> float:
    """実効波長 [µm] = **放射輝度で重み付けた 1/λ の平均の逆数**。

    n = c2/(λ_eff T) という形に落とすなら、重みは λ ではなく **1/λ** で
    取らねばならない —— 温度微分が dL_λ/dT ∝ L_λ·(c2/(λT²))·e^x/(e^x−1) で
    **1/λ に比例**するから。帯の中央を λ_eff と呼ぶ素朴な取り方との差は
    §2 で測る。
    """
    lo, hi = BANDS[band]
    lam, w = _simpson_nodes(lo, hi)
    li = planck_spectral(lam, float(t_k))
    return float(np.dot(li, w) / np.dot(li / lam, w))


def band_index_predicted(band: str, t_k: float, lam_eff: float | None = None) -> float:
    """実効 Planck 指数の**予測** n = c2/(λ_eff·T)。測る前に印字する量。"""
    lam = band_effective_lambda(band, t_k) if lam_eff is None else float(lam_eff)
    return C2_UM / (lam * float(t_k))


def band_index_numeric(band: str, t_k: float, rel_h: float = 1e-4) -> float:
    """同じ指数の**実測** n = d ln L_bb / d ln T(中心差分)。"""
    t = float(t_k)
    h = rel_h * t
    lo = float(band_radiance_direct(band, t - h))
    hi = float(band_radiance_direct(band, t + h))
    return (math.log(hi) - math.log(lo)) / (math.log(t + h) - math.log(t - h))


class BandTable:
    """1 つの帯域の ``T ↔ L`` 校正表。逆変換は `fs.interp_linear` で引く。

    Planck の帯域積分は T について**厳密に単調増加**なので、同じ表を
    ``(T→L)`` と ``(L→T)`` の両方向に使える。範囲外は既定で **例外**
    (`out_of_range='raise'`)—— 校正範囲の外を黙って外挿した値は、
    もっともらしい顔をした嘘になる。§5 の単位の取り違えは、この門が捕まえる。
    """

    def __init__(self, band: str, lo: float = TAB_LO, hi: float = TAB_HI,
                 step: float = TAB_STEP):
        self.band = band
        self.t_grid = np.arange(lo, hi + 0.5 * step, step, dtype=np.float64)
        # λ 軸を持つ一時配列が大きくなるので、T をまとめて 4000 点ずつ処理する。
        chunks = [band_radiance_direct(band, self.t_grid[i:i + 4000])
                  for i in range(0, self.t_grid.size, 4000)]
        self.l_grid = np.concatenate(chunks)
        if not np.all(np.diff(self.l_grid) > 0.0):
            raise ValueError("校正表が単調でない: %s" % band)

    def radiance(self, t_k):
        """T [K] → 帯域放射輝度 [W·m⁻²·sr⁻¹](表引き)。"""
        return fs.interp_linear(self.t_grid, self.l_grid, np.asarray(t_k, np.float64))

    def temperature(self, l_w, allow_out: bool = False):
        """帯域放射輝度 → T [K]。``allow_out=True`` なら範囲外を NaN で返す。

        既定は **fail-closed**(範囲外は `fs.interp_linear` が例外を投げる)。
        Monte Carlo では「逆算が物理的に破綻した試行」を数えたいので、
        そのときだけ ``allow_out=True`` にしてマスクで抜く。
        """
        arr = np.asarray(l_w, np.float64)
        if not allow_out:
            return fs.interp_linear(self.l_grid, self.t_grid, arr)
        ok = np.isfinite(arr) & (arr >= self.l_grid[0]) & (arr <= self.l_grid[-1])
        out = np.full(arr.shape, np.nan)
        if ok.any():
            out[ok] = fs.interp_linear(self.l_grid, self.t_grid, arr[ok])
        return out


# --------------------------------------------------------------------------- #
# 前向きモデルと逆変換 —— 現場の式そのまま                                       #
# --------------------------------------------------------------------------- #
def forward_radiance(tab: BandTable, t_obj, eps, t_refl, tau, t_atm):
    """L_meas = τ[ε L(T_obj) + (1−ε) L(T_refl)] + (1−τ) L(T_atm)。"""
    lo = tab.radiance(t_obj)
    lr = tab.radiance(t_refl)
    la = tab.radiance(t_atm)
    return tau * (eps * lo + (1.0 - eps) * lr) + (1.0 - tau) * la


def invert_radiance(tab: BandTable, l_meas, eps, t_refl, tau, t_atm,
                    drop_reflection: bool = False, allow_out: bool = False):
    """L_meas と**仮定した** ε・T_refl・τ・T_atm から T_obj を逆算 [K]。

    ``drop_reflection=True`` は「反射項を落とす」ゼロ点 —— (1−ε)L(T_refl) を
    引かずに ε で割るだけ。現場のいちばん多い手抜きで、**ε が小さいほど
    致命的**になる。
    """
    lr = 0.0 if drop_reflection else (1.0 - eps) * tab.radiance(t_refl)
    la = (1.0 - tau) * tab.radiance(t_atm)
    l_obj = ((np.asarray(l_meas, np.float64) - la) / tau - lr) / eps
    return tab.temperature(l_obj, allow_out=allow_out)


class Camera:
    """線形校正 ``DN = a·L + b`` + 量子化 + NETD の赤外カメラ。

    ``a`` / ``b`` は「``t_lo``〜``t_hi`` を 14 bit のフルスケールに割り当てる」
    という設計から決める(実機の測定レンジ切替に相当)。NETD は **温度で**
    与えられた仕様値なので、``t_ref`` での dL/dT を掛けて放射輝度の σ に直す
    —— **ここが仕様書と信号処理をつなぐ地点**で、レンジを変えると DN での
    σ が変わる。
    """

    def __init__(self, tab: BandTable, t_lo: float, t_hi: float,
                 netd_k: float = NETD_K, bits: int = ADC_BITS,
                 dn_lo: float = 200.0, t_ref: float = 320.0):
        self.tab = tab
        self.dn_max = float(2 ** bits - 1)
        self.dn_lo = float(dn_lo)
        l_lo = float(tab.radiance(t_lo))
        l_hi = float(tab.radiance(t_hi))
        self.a = (self.dn_max - self.dn_lo) / (l_hi - l_lo)
        self.b = self.dn_lo - self.a * l_lo
        self.t_lo, self.t_hi = float(t_lo), float(t_hi)
        # NETD [K] → 放射輝度 [W m^-2 sr^-1] → DN。dL/dT は中心差分で実測。
        h = 0.01
        dldt = (float(tab.radiance(t_ref + h)) - float(tab.radiance(t_ref - h))) / (2 * h)
        self.sigma_l = float(netd_k) * dldt
        self.sigma_dn = self.a * self.sigma_l
        self.t_ref, self.dldt_ref = float(t_ref), dldt

    def to_dn(self, l_w, rng=None, quantize: bool = True):
        """放射輝度 → DN。``rng`` を渡すと NETD 相当の雑音を足す。"""
        dn = self.a * np.asarray(l_w, np.float64) + self.b
        if rng is not None:
            dn = dn + rng.normal(0.0, self.sigma_dn, size=np.shape(dn))
        if quantize:
            dn = np.clip(np.rint(dn), 0.0, self.dn_max)
        return dn

    def to_radiance(self, dn, a=None, b=None):
        """DN → 放射輝度。``a`` / ``b`` を渡すと**取り違えた校正係数**で戻す。

        ``a`` / ``b`` は配列でもよい(Monte Carlo で試行ごとに校正係数を
        振るため)—— ここを ``float()`` で受けていて 1 度落ちた。
        """
        aa = self.a if a is None else np.asarray(a, np.float64)
        bb = self.b if b is None else np.asarray(b, np.float64)
        return (np.asarray(dn, np.float64) - bb) / aa


# --------------------------------------------------------------------------- #
# 1. 場面と往復 —— 床を測る                                                     #
# --------------------------------------------------------------------------- #
def section_scene():
    print("=== 1. 前向きモデルと往復 —— まず床を測る ===")
    tabs = {name: BandTable(name) for name in BANDS}
    # (a) 校正表 vs 直接積分。表は近似なので、どれだけ近いかを数字で出す。
    probe = np.array([250.0, 300.0, 350.0, 450.0, 800.0, 1200.0])
    print(f"  {'帯域':>6}{'節点':>7}{'L(300K)':>14}{'L(800K)':>14}"
          f"{'表 vs 直接積分(相対)':>24}")
    conv, tab_gap = {}, 0.0
    for name, tab in tabs.items():
        direct = band_radiance_direct(name, probe)
        via_tab = np.asarray(tab.radiance(probe), np.float64)
        rel = float(np.max(np.abs(via_tab / direct - 1.0)))
        tab_gap = max(tab_gap, rel)
        print(f"  {name:>6}{N_LAMBDA:>7}{float(direct[1]):>14.5f}"
              f"{float(direct[4]):>14.3f}{rel:>24.3e}")
        # Simpson の節点数を振って、積分そのものが収束していることを見る。
        ref = float(band_radiance_direct(name, 350.0, 1025))
        conv[name] = [(n, abs(float(band_radiance_direct(name, 350.0, n)) / ref - 1.0))
                      for n in (33, 129, 513)]
        print("        Simpson 節点 33/129/513 の相対差: "
              + " / ".join("%.2e" % e for _, e in conv[name]))
    # (b) Case-0 往復。真値を植えて前向き → 同じ仮定で逆算。
    tab = tabs["LWIR"]
    cam = Camera(tab, 250.0, 450.0)
    t_true, eps = 350.0, EPS_PAINT
    print(f"  カメラ: {cam.t_lo:.0f}–{cam.t_hi:.0f} K を {ADC_BITS} bit に割当 → "
          f"a = {cam.a:.3f} DN/(W m^-2 sr^-1)、b = {cam.b:+.2f} DN")
    print(f"        NETD {NETD_K*1000:.0f} mK = {cam.sigma_dn:.3f} DN"
          f"(dL/dT({cam.t_ref:.0f} K) = {cam.dldt_ref:.4f})、"
          f"量子化 1 DN = {1.0/cam.a/cam.dldt_ref*1000:.1f} mK")
    # (b') 大気の透過率は定数を書き写さず、Beer–Lambert の op から出す。
    dists_m = np.array([0.5, 2.0, 10.0, 30.0])
    taus = np.asarray(fs.beer_lambert_transmittance(dists_m * 1000.0,
                                                    ATM_SIGMA_PER_MM), np.float64)
    tau_err = [float(invert_radiance(tab, forward_radiance(tab, 350.0, eps,
                                                           T_REFL_REF, tv, T_ATM_REF),
                                     eps, T_REFL_REF, 1.0, T_ATM_REF)) - 350.0
               for tv in taus]
    print("  大気透過率(fs.beer_lambert_transmittance、σ = "
          f"{ATM_SIGMA_PER_MM:.1e} /mm): "
          + " / ".join(f"{d:.1f} m → τ={t:.4f}" for d, t in zip(dists_m, taus)))
    print("        τ を 1 と仮定したときの温度誤差: "
          + " / ".join(f"{e:+.2f} K" for e in tau_err))
    l_true = float(forward_radiance(tab, t_true, eps, T_REFL_REF, TAU_REF, T_ATM_REF))
    rng = np.random.default_rng(20260908)
    cases = []
    for label, quant, noise in (("Case-0 雑音も量子化も無し", False, False),
                                ("量子化のみ", True, False),
                                ("NETD のみ", False, True),
                                ("量子化 + NETD", True, True)):
        n = 20000
        dn = cam.to_dn(np.full(n, l_true), rng if noise else None, quantize=quant)
        got = np.asarray(invert_radiance(tab, cam.to_radiance(dn), eps,
                                         T_REFL_REF, TAU_REF, T_ATM_REF), np.float64)
        err = float(np.sqrt(np.mean((got - t_true) ** 2)))
        cases.append((label, err))
        print(f"  {label:<24} 往復誤差 rms = {err:.3e} K")
    # NETD が本当に仕様どおり効いているか、`fs.noise_sigma` で逆に測り返す。
    flat = cam.to_dn(np.full((64, 64), l_true), rng, quantize=True)
    sig = float(fs.noise_sigma(flat.astype(np.float64), method="mad"))
    print(f"  平坦面 64x64 の DN 雑音を fs.noise_sigma(MAD) で測り返すと "
          f"{sig:.3f} DN(注入 {cam.sigma_dn:.3f} DN、量子化 +1/√12 込みで整合)")
    print("  → **ここが床**。以下で見る誤差はすべてこの 3 桁以上 上にある。")
    figs.save_table(
        "floor", ["条件", "往復誤差 rms [K]"],
        [(lab, "%.3e" % e) for lab, e in cases],
        title="床 —— 真値を知っていれば往復は閉じる",
        caption=f"LWIR・{t_true:.0f} K・ε={eps}。校正表と直接積分の相対差は"
                f"最大 {tab_gap:.1e}。以下の誤差はすべてこの床の上。")
    return {"tabs": tabs, "cam": cam, "cases": dict(cases), "tab_gap": tab_gap,
            "conv": conv, "l_true": l_true, "netd_measured": sig}


# --------------------------------------------------------------------------- #
# 2. 崖 —— 閉形式で予測してから測る                                             #
# --------------------------------------------------------------------------- #
def predict_dt_from_eps(tab: BandTable, band: str, t_obj: float, eps: float,
                        rel_deps: float, t_refl: float = T_REFL_REF,
                        lam_eff: float | None = None) -> float:
    """放射率を **相対** ``rel_deps`` だけ取り違えたときの温度誤差 [K](予測)。

    ε₀ = ε(1+δ) と仮定して逆算すると、L_bb(T̂) = L_bb(T_o)(1 − δ(1 − L_r/L_o))
    まで 1 次で落ちる。n = d ln L/d ln T を使うと

        ΔT = −(T/n)·δ·(1 − L_bb(T_refl)/L_bb(T_obj))

    第 2 因子は**反射がある分だけ崖が緩む**という意味で、T_refl → T_obj では
    ゼロになる(全部が同じ温度なら ε は効かない)。逆に T_refl > T_obj では
    符号が反転する —— **周囲が対象より熱いと、放射率の取り違えは逆向きに効く**。
    """
    n = band_index_predicted(band, t_obj, lam_eff)
    ratio = float(tab.radiance(t_refl)) / float(tab.radiance(t_obj))
    return -(t_obj / n) * rel_deps * (1.0 - ratio)


def measure_dt_from_eps(tab: BandTable, t_obj: float, eps: float, rel_deps: float,
                        t_refl: float = T_REFL_REF) -> float:
    """同じ量の実測 [K]。前向きに作って、ε₀=ε(1+δ) で逆算するだけ。"""
    lm = forward_radiance(tab, t_obj, eps, t_refl, 1.0, T_ATM_REF)
    got = invert_radiance(tab, lm, eps * (1.0 + rel_deps), t_refl, 1.0, T_ATM_REF)
    return float(got) - t_obj


def section_cliff(scene):
    print("\n=== 2. 崖 —— 閉形式を先に印字してから測る ===")
    tabs = scene["tabs"]
    print("  予測: ΔT = −(T/n)·(Δε/ε)·(1 − L(T_refl)/L(T_obj))、n = c2/(λ_eff·T)")
    print(f"  {'帯域':>6}{'T [K]':>8}{'λ_eff [µm]':>12}{'λ中央':>8}"
          f"{'n(予測)':>10}{'n(中央)':>10}{'n(実測)':>10}{'差':>9}")
    idx_rows, worst_eff, worst_mid = [], 0.0, 0.0
    for band in BANDS:
        lo, hi = BANDS[band]
        for t in (300.0, 350.0, 800.0):
            lam_eff = band_effective_lambda(band, t)
            n_pred = band_index_predicted(band, t)
            n_mid = band_index_predicted(band, t, 0.5 * (lo + hi))
            n_num = band_index_numeric(band, t)
            worst_eff = max(worst_eff, abs(n_pred / n_num - 1.0))
            worst_mid = max(worst_mid, abs(n_mid / n_num - 1.0))
            idx_rows.append((band, f"{t:.0f}", f"{lam_eff:.3f}", f"{0.5*(lo+hi):.1f}",
                             f"{n_pred:.3f}", f"{n_mid:.3f}", f"{n_num:.3f}",
                             f"{100*(n_pred/n_num-1):+.1f} %"))
            print(f"  {band:>6}{t:>8.0f}{lam_eff:>12.3f}{0.5*(lo+hi):>8.1f}"
                  f"{n_pred:>10.3f}{n_mid:>10.3f}{n_num:>10.3f}"
                  f"{100*(n_pred/n_num-1):>8.1f}%")
    print(f"  → 放射輝度で重み付けた 1/λ の平均を λ_eff にすると誤差 "
          f"{100*worst_eff:.1f} % 以内。帯の中央を使うと {100*worst_mid:.1f} % "
          f"—— **どこを実効波長と呼ぶかで 1 割違う**。")
    figs.save_table("planck_index",
                    ["帯域", "T [K]", "λ_eff [µm]", "λ 中央", "n(予測)",
                     "n(中央で予測)", "n(実測)", "予測の誤差"], idx_rows,
                    title="実効 Planck 指数 —— 重みを 1/λ で取る",
                    caption="n = d ln L_bb/d ln T。温度微分が 1/λ に比例するので、"
                            "重みも 1/λ で取らないと 1 割ずれる。")

    # ---- 予測を印字してから、温度・帯域・放射率を振って実測する ---------------
    print("\n  ★予測(印字してから測る): 崖は **低温ほど急** —— のはず。")
    print("     根拠として書いたのは「n = c2/(λT) は低温ほど大きく…」だった。")
    print(f"  {'帯域':>6}{'T [K]':>8}{'ε':>7}{'Δε/ε':>8}{'予測 ΔT':>11}"
          f"{'実測 ΔT':>11}{'差':>9}{'上昇比 |ΔT|/(T−T_r)':>22}")
    rows, worst_pred, rise_ratio, abs_dt = [], 0.0, {}, {}
    worst_rel, worst_where = 0.0, ""
    for band in ("LWIR", "MWIR"):
        tab = tabs[band]
        for t in (305.0, 350.0, 400.0, 800.0):
            for eps in (EPS_PAINT, EPS_POLISH):
                delta = 0.05
                pred = predict_dt_from_eps(tab, band, t, eps, delta)
                meas = measure_dt_from_eps(tab, t, eps, delta)
                worst_pred = max(worst_pred, abs(pred - meas))
                if abs(pred / meas - 1.0) > worst_rel:
                    worst_rel = abs(pred / meas - 1.0)
                    worst_where = f"{band} {t:.0f} K ε={eps:.2f}"
                rise = abs(meas) / (t - T_REFL_REF)
                if eps == EPS_PAINT:
                    rise_ratio[(band, t)] = rise
                    abs_dt[(band, t)] = abs(meas)
                rows.append((band, f"{t:.0f}", f"{eps:.2f}", f"{delta:.2f}",
                             f"{pred:+.3f}", f"{meas:+.3f}", f"{meas-pred:+.4f}",
                             f"{100*rise:.1f} %"))
                print(f"  {band:>6}{t:>8.0f}{eps:>7.2f}{delta:>8.2f}{pred:>11.3f}"
                      f"{meas:>11.3f}{meas-pred:>9.4f}{100*rise:>21.1f} %")
    print(f"  → 予測と実測の差は最大 {worst_pred:.4f} K、相対では "
          f"{100*worst_rel:.1f} %({worst_where})。**1 次展開なので、"
          f"ΔT が大きい所ほど当たらない**。")
    print("  → ★★**予測を外した**: 絶対誤差は **高温ほど大きい**。")
    print(f"     LWIR・ε=0.95 で 300 K 級 {abs_dt[('LWIR', 305.0)]:.2f} K → "
          f"800 K {abs_dt[('LWIR', 800.0)]:.2f} K。")
    print("     ΔT = (λ_eff T²/c2)·(Δε/ε)·(1−L_r/L_o) は **T の 2 乗**で増える ——")
    print("     閉形式は最初からそう言っていて、自分の式を読み違えていた。")
    print("  → ★ただし**物差しを変えると予測は当たる**: 現場が使うのは絶対温度でなく")
    print(f"     周囲からの上昇 (T−T_refl) で、その比は "
          f"{100*rise_ratio[('LWIR', 305.0)]:.1f} %(305 K)→ "
          f"{100*rise_ratio[('LWIR', 800.0)]:.1f} %(800 K)で**低温ほど急**。")
    # 「T の 2 乗で増える」を主張のまま置かず、傾きを実測する(fs.poly_fit)。
    ts_fit = np.linspace(310.0, 900.0, 25)
    dt_fit = np.array([abs(measure_dt_from_eps(tabs["LWIR"], t, EPS_PAINT, 0.05))
                       for t in ts_fit])
    coef, cond = fs.poly_fit(np.log(ts_fit), np.log(dt_fit), 1)
    slope = float(np.asarray(coef)[0])
    print(f"  → 「T² で増える」を主張のまま置かない: log|ΔT| を log T に "
          f"fs.poly_fit(次数 1)で当てると **傾き {slope:.3f}**"
          f"(条件数 {float(cond):.1f})。")
    print("     厳密に 2 でないのは λ_eff が温度とともに短波側へ動くから ——")
    print("     ΔT = (λ_eff(T)·T²/c2)·δ·(1−L_r/L_o) の λ_eff(T) の分だけ 2 を下回る。")
    figs.save_table("emissivity_cliff",
                    ["帯域", "T [K]", "ε", "Δε/ε", "予測 ΔT [K]", "実測 ΔT [K]",
                     "差", "|ΔT|/(T−T_refl)"], rows,
                    title="放射率 5 % の取り違えが温度に化ける量",
                    caption="予測は測る前に印字した閉形式。絶対誤差は高温ほど大きく、"
                            "周囲からの上昇に対する比は低温ほど大きい —— "
                            "同じ数字が割る相手で逆の結論を出す。")

    # ---- 同じ絶対誤差 Δε=0.02 を ε 別に(低放射率の崖) -----------------------
    tab = tabs["LWIR"]
    print(f"\n  同じ **絶対** 誤差 Δε = 0.02 を ε 別に(LWIR・350 K):")
    abs_rows, by_eps = [], {}
    for eps in (EPS_PAINT, EPS_OXIDE, EPS_POLISH):
        meas = measure_dt_from_eps(tab, 350.0, eps, 0.02 / eps)
        by_eps[eps] = abs(meas)
        abs_rows.append((f"{eps:.2f}", f"{0.02/eps:.4f}", f"{meas:+.3f}"))
        print(f"    ε = {eps:.2f}(Δε/ε = {0.02/eps:.3f}): ΔT = {meas:+.3f} K")
    ratio = by_eps[EPS_POLISH] / by_eps[EPS_PAINT]
    print(f"  → 研磨金属は塗装面の **{ratio:.1f} 倍**。ε で割るので当たり前だが、")
    print("     現場の ε は「表から拾った値」で、±0.02 で済む保証はどこにもない。")

    # ---- 反射見かけ温度の取り違え -------------------------------------------
    print("\n  反射見かけ温度 T_refl を 10 K 取り違えたとき(LWIR / MWIR・350 K):")
    refl_rows = {}
    for band in ("LWIR", "MWIR"):
        tb = tabs[band]
        for eps in (EPS_PAINT, EPS_POLISH):
            lm = forward_radiance(tb, 350.0, eps, T_REFL_REF, 1.0, T_ATM_REF)
            got = float(invert_radiance(tb, lm, eps, T_REFL_REF + 10.0, 1.0, T_ATM_REF))
            refl_rows[(band, eps)] = got - 350.0
            print(f"    {band} ε={eps:.2f}: ΔT = {got-350.0:+.3f} K")
    print("  → ★**帯を変えても「反射が効く」順位は変わらない**。MWIR は放射率には")
    print("     強い(n が 2.7 倍)が、(1−ε) の重みは帯に依らない。")

    if figs.enabled():
        deltas = np.linspace(-0.30, 0.30, 61)
        series = []
        for eps in (EPS_PAINT, EPS_OXIDE, EPS_POLISH):
            ys = np.array([measure_dt_from_eps(tab, 350.0, eps, d) for d in deltas])
            series.append((f"ε = {eps:.2f}", deltas, ys))
        figs.save_plot("cliff_curves", series,
                       xlabel="放射率の相対誤差 Δε/ε", ylabel="温度の誤差 ΔT [K]",
                       title="崖 —— 同じ相対誤差でも ε が小さいほど落ちる",
                       caption="LWIR・T_obj = 350 K・T_refl = 300 K。傾きは "
                               "−(T/n)(1−L_r/L_o)/1。3 本は原点で交わるが、"
                               "傾きが ε に依らないのは**相対**誤差で見たときだけ ——"
                               "現場で表から拾う ε の誤差は**絶対**値で来る。")
        ts = np.linspace(300.0, 900.0, 61)
        pred = np.array([abs(predict_dt_from_eps(tab, "LWIR", t, EPS_PAINT, 0.05))
                         for t in ts])
        meas = np.array([abs(measure_dt_from_eps(tab, t, EPS_PAINT, 0.05)) for t in ts])
        rise = np.array([abs(measure_dt_from_eps(tab, t, EPS_PAINT, 0.05))
                         / (t - T_REFL_REF) * 100.0 for t in ts])
        figs.save_plot("cliff_vs_temperature",
                       [("|ΔT| [K](左の物差し)", ts, meas),
                        ("閉形式の予測 [K]", ts, pred),
                        ("|ΔT|/(T−T_refl) [%]", ts, rise)],
                       xlabel="対象の温度 T_obj [K]",
                       ylabel="温度の誤差(K と % を重ねて描いている)",
                       title="物差しを変えると「低温ほど危ない」が反転する",
                       caption="Δε/ε = 5 % 固定。絶対誤差(青・橙)は T² で増え、"
                               "周囲からの上昇に対する比(緑)は低温ほど大きい。"
                               "★どちらも同じ実験の同じ数字。")
    return {"idx_rows": idx_rows, "worst_pred": worst_pred, "worst_eff": worst_eff,
            "worst_mid": worst_mid, "by_eps": by_eps, "ratio": ratio,
            "rise": rise_ratio, "abs_dt": abs_dt, "refl": refl_rows}


# --------------------------------------------------------------------------- #
# 3. ゼロ点と対照群                                                             #
# --------------------------------------------------------------------------- #
def section_nulls(scene):
    print("\n=== 3. ゼロ点 —— DN をそのまま温度と呼ぶ / ε=1 固定 / 反射を落とす ===")
    tab, cam = scene["tabs"]["LWIR"], scene["cam"]
    print(f"  {'処理':>28}{'ε=0.95 塗装':>14}{'ε=0.60 酸化':>14}{'ε=0.10 研磨':>14}")
    rows, out = [], {}
    # 2 点校正(DN を温度に線形に読み替える)の基準点。実務のバーチェック相当。
    t_cal = (300.0, 400.0)
    dn_cal = [float(cam.to_dn(forward_radiance(tab, t, 1.0, T_REFL_REF, 1.0, T_ATM_REF),
                              quantize=False)) for t in t_cal]
    slope = (t_cal[1] - t_cal[0]) / (dn_cal[1] - dn_cal[0])
    for label in ("DN を線形に温度と呼ぶ", "ε=1 固定(見かけ温度)",
                  "反射項を落とす", "全部正しく入れる(対照群)"):
        vals = []
        for eps in (EPS_PAINT, EPS_OXIDE, EPS_POLISH):
            lm = forward_radiance(tab, 350.0, eps, T_REFL_REF, TAU_REF, T_ATM_REF)
            dn = cam.to_dn(lm, quantize=False)
            if label.startswith("DN"):
                got = t_cal[0] + slope * (float(dn) - dn_cal[0])
            elif label.startswith("ε=1"):
                got = float(invert_radiance(tab, cam.to_radiance(dn), 1.0,
                                            T_REFL_REF, TAU_REF, T_ATM_REF))
            elif label.startswith("反射"):
                got = float(invert_radiance(tab, cam.to_radiance(dn), eps,
                                            T_REFL_REF, TAU_REF, T_ATM_REF,
                                            drop_reflection=True))
            else:
                got = float(invert_radiance(tab, cam.to_radiance(dn), eps,
                                            T_REFL_REF, TAU_REF, T_ATM_REF))
            vals.append(got - 350.0)
        out[label] = vals
        rows.append((label, *[f"{v:+.3f} K" for v in vals]))
        print(f"  {label:>28}" + "".join(f"{v:>+13.3f} K" for v in vals))
    print("  → DN の線形読みは校正 2 点の間ですら外す(L が T に対して凸だから)。")
    print("  → ★いちばん質が悪いのは **ε=1 固定**。絵は完全にもっともらしく、")
    print("     単位も ℃ で、**どこにも異常が出ない**。ε=0.10 では "
          f"{out['ε=1 固定(見かけ温度)'][2]:+.1f} K。")
    print("  → 反射項を落とすと ε=0.95 では小さいが、ε=0.10 では "
          f"{out['反射項を落とす'][2]:+.1f} K —— (1−ε) の重みがそのまま出る。")
    figs.save_table("nulls", ["処理", "ε=0.95 塗装", "ε=0.60 酸化", "ε=0.10 研磨"],
                    rows, title="ゼロ点 3 つ —— どれも失格、質の悪さの順は別",
                    caption="LWIR・T_obj = 350 K・T_refl = 300 K・τ = 0.95。"
                            "対照群(全部正しく入れる)は量子化も雑音も無しなので"
                            "床のまま。")
    return out


# --------------------------------------------------------------------------- #
# 4. 不確かさ —— RSS と 相関つき MC、そして包含率                                #
# --------------------------------------------------------------------------- #
#: 不確かさ予算の入力。``(名前, 公称値, 標準不確かさ)``。
#: **すべてこの PoC のために置いた仮定**(機器仕様・現場の相場からの想定値)。
def budget_inputs(eps: float, u_eps: float, sigma_dn: float, u_refl: float = 5.0):
    return [("ε", eps, u_eps),
            ("T_refl [K]", T_REFL_REF, u_refl),
            ("τ", TAU_REF, 0.02),
            ("T_atm [K]", T_ATM_REF, 3.0),
            ("a(校正利得, 相対)", 1.0, 0.005),
            ("b(校正切片, DN)", 0.0, 2.0),
            ("DN 雑音(NETD, DN)", 0.0, sigma_dn)]


def _invert_with(tab: BandTable, cam: Camera, dn, vec, allow_out: bool = True):
    """入力ベクトル ``vec = (ε, T_refl, τ, T_atm, a係数, bずれ, DN雑音)`` で逆算 [K]。

    ``b ずれ``(校正の系統誤差)と ``DN 雑音``(NETD の偶然誤差)は数式では
    同じ場所に入るが、**予算表では別の行**にしておく —— 片方は日ごとに固定、
    片方は画素ごとに振れる量で、平均を取ったときの振る舞いが違うから。
    """
    eps, t_refl, tau, t_atm, a_rel, b_off, dn_noise = vec
    lm = cam.to_radiance(dn, a=cam.a * a_rel, b=cam.b + b_off + dn_noise)
    return invert_radiance(tab, lm, eps, t_refl, tau, t_atm, allow_out=allow_out)


def sensitivities(tab: BandTable, cam: Camera, dn: float, nominal, steps):
    """GUM の感度係数 c_i = ∂T/∂x_i(中心差分)。"""
    out = []
    for i, h in enumerate(steps):
        hi = list(nominal); hi[i] += h
        lo = list(nominal); lo[i] -= h
        out.append((float(_invert_with(tab, cam, dn, hi, False))
                    - float(_invert_with(tab, cam, dn, lo, False))) / (2.0 * h))
    return np.array(out, np.float64)


def correlated_draws(rng, u_vec, rho: float, n: int, pair=(0, 1)):
    """入力の偏差を引く。``pair`` の 2 つだけ相関 ``rho``、他は独立。

    相関行列の平方根は `fs.mat_eigh`(対称行列の固有分解)から作る ——
    Cholesky 分解の op は 4 層のどこにも無い(§7)。R = V diag(w) Vᵀ なので
    R^{1/2} = V diag(√w) Vᵀ。2x2 なら閉形式でも書けるが、**入力が 3 つ以上
    相関する現場**にそのまま伸びる形にしてある。
    """
    d = len(u_vec)
    corr = np.eye(d)
    corr[pair[0], pair[1]] = corr[pair[1], pair[0]] = float(rho)
    w, v = fs.mat_eigh(corr)
    root = v @ np.diag(np.sqrt(np.clip(np.asarray(w), 0.0, None))) @ v.T
    z = rng.normal(0.0, 1.0, size=(n, d))
    return (z @ root.T) * np.asarray(u_vec, np.float64)


def _propagate(tab, cam, dn, nominal, dev):
    """公称値 + 偏差 の束で逆算した T の分布 [K](NaN = 逆算が破綻した試行)。"""
    vec = [np.asarray(nominal[i], np.float64) + dev[:, i] for i in range(len(nominal))]
    return np.asarray(_invert_with(tab, cam, dn, vec, allow_out=True), np.float64)


def coverage_run(tab, cam, t_true, eps, u_eps, rho_reality, rho_assumed,
                 n_trials, seed, u_refl=5.0):
    """包含率を数える。**現実**は ``rho_reality``、**処理側の仮定**は ``rho_assumed``。

    手順は現場と同じ順序: (1) 処理側は公称値だけを持ち、感度と不確かさから
    区間を 1 回作る。(2) 現実は公称値のまわりに散らばる。(3) 区間が真値を
    包んだかを数える。★**区間は測定ごとに作り直さない** —— 現場の不確かさ
    予算は日ごと・機器ごとに 1 回作るものだから。
    """
    inputs = budget_inputs(eps, u_eps, cam.sigma_dn, u_refl)
    nominal = [v for _, v, _ in inputs]
    u_vec = [u for _, _, u in inputs]
    steps = [0.002, 0.5, 0.002, 0.5, 0.001, 1.0, 1.0]
    # 公称の測定(雑音・量子化なし)。区間の中心はここから。
    l_nom = forward_radiance(tab, t_true, eps, T_REFL_REF, TAU_REF, T_ATM_REF)
    dn_nom = float(cam.to_dn(l_nom, quantize=False))
    c = sensitivities(tab, cam, dn_nom, nominal, steps)
    u_rss = float(np.sqrt(np.sum((c * np.asarray(u_vec)) ** 2)))
    # 相関つきの合成標準不確かさ(GUM の 2 重和)。処理側が仮定する ρ を使う。
    cu = c * np.asarray(u_vec)
    u_corr = float(np.sqrt(np.sum(cu ** 2) + 2.0 * rho_assumed * cu[0] * cu[1]))
    # 処理側の MC 伝播(相関 rho_assumed)→ 区間の左右の張り出し。
    rng = np.random.default_rng(seed)
    dev_p = correlated_draws(rng, u_vec, rho_assumed, 40000)
    tp = _propagate(tab, cam, dn_nom, nominal, dev_p)
    tp = tp[np.isfinite(tp)]
    centre = float(np.median(tp))
    off_lo = float(np.percentile(tp, 2.5)) - centre
    off_hi = float(np.percentile(tp, 97.5)) - centre
    # --- 現実 ---------------------------------------------------------------
    dev_r = correlated_draws(rng, u_vec, rho_reality, n_trials)
    eps_t = eps + dev_r[:, 0]
    tr_t = T_REFL_REF + dev_r[:, 1]
    tau_t = TAU_REF + dev_r[:, 2]
    ta_t = T_ATM_REF + dev_r[:, 3]
    lm = forward_radiance(tab, t_true, eps_t, tr_t, tau_t, ta_t)
    # 現実: a_true = a₀(1+δa)、b_true = b₀ + δb、そこへ NETD の雑音が乗る。
    dn = cam.to_dn(lm * (1.0 + dev_r[:, 4]), None, quantize=False)
    dn = np.clip(np.rint(dn + dev_r[:, 5] + dev_r[:, 6]), 0.0, cam.dn_max)
    t_hat = np.asarray(invert_radiance(tab, cam.to_radiance(dn), eps,
                                       T_REFL_REF, TAU_REF, T_ATM_REF,
                                       allow_out=True), np.float64)
    good = np.isfinite(t_hat)
    k = 1.959963984540054                        # 正規分布の 95 % の k
    lo_rss, hi_rss = t_hat - k * u_rss, t_hat + k * u_rss
    lo_mc, hi_mc = t_hat + off_lo, t_hat + off_hi
    cov_rss = float(np.mean((lo_rss <= t_true) & (t_true <= hi_rss) & good))
    cov_mc = float(np.mean((lo_mc <= t_true) & (t_true <= hi_mc) & good))
    miss_lo = float(np.mean(good & (hi_rss < t_true)))
    miss_hi = float(np.mean(good & (lo_rss > t_true)))
    return {"u_rss": u_rss, "u_corr": u_corr, "c": c, "u_vec": np.asarray(u_vec),
            "cov_rss": cov_rss, "cov_mc": cov_mc, "miss_lo": miss_lo,
            "miss_hi": miss_hi, "half_rss": k * u_rss,
            "half_mc": 0.5 * (off_hi - off_lo), "off": (off_lo, off_hi),
            "n_bad": int(np.sum(~good)), "t_hat": t_hat, "prop": tp,
            "inputs": inputs, "n": n_trials, "dev_r": dev_r}


def section_uncertainty(scene):
    print("\n=== 4. 不確かさ —— 独立 RSS と 相関つき MC を、包含率で突き合わせる ===")
    tab, cam = scene["tabs"]["LWIR"], scene["cam"]
    t_true, eps, u_eps = 353.15, EPS_OXIDE, 0.05
    n_trials = 20000
    print(f"  対象: 酸化した金属面 ε = {eps:.2f} ± {u_eps:.2f}、T_obj = {t_true:.2f} K"
          f"({t_true-T0_C:.0f} ℃)、T_refl = {T_REFL_REF:.0f} ± 5 K")
    # --- 予算表(感度 × 不確かさ)------------------------------------------- #
    base = coverage_run(tab, cam, t_true, eps, u_eps, 0.0, 0.0, n_trials, 11)
    print(f"  {'入力':>20}{'公称':>10}{'u(x)':>10}{'感度 c':>14}"
          f"{'寄与 |c·u| [K]':>16}{'寄与²の割合':>14}")
    cu = base["c"] * base["u_vec"]
    rows = []
    for (name, val, u), ci, cui in zip(base["inputs"], base["c"], cu):
        share = cui ** 2 / float(np.sum(cu ** 2))
        rows.append((name, f"{val:g}", f"{u:g}", f"{ci:+.4g}", f"{abs(cui):.4f}",
                     f"{100*share:.1f} %"))
        print(f"  {name:>20}{val:>10g}{u:>10g}{ci:>+14.4g}{abs(cui):>16.4f}"
              f"{100*share:>13.1f} %")
    print(f"  → 独立 RSS の合成標準不確かさ u_c = {base['u_rss']:.4f} K、"
          f"95 % 区間の半幅 = {base['half_rss']:.4f} K")
    figs.save_table("budget", ["入力", "公称", "u(x)", "感度 c", "寄与 |c·u| [K]",
                               "寄与² の割合"], rows,
                    title="GUM の不確かさ予算(独立と仮定した場合)",
                    caption=f"LWIR・{t_true:.1f} K・ε = {eps}。感度は中心差分の実測。"
                            f"合成 u_c = {base['u_rss']:.4f} K。"
                            "★この表には**相関の行が無い**——そこが穴。")

    # --- 床を先に測る: ρ=0 なら RSS は正しいはず ----------------------------- #
    print(f"\n  ★**床を先に測る**({n_trials} 試行、ρ = 0 の現実):")
    print(f"    包含率 RSS {100*base['cov_rss']:.2f} % / "
          f"相関つき MC {100*base['cov_mc']:.2f} %"
          f"(理論 95 %、標本誤差 ±{100*1.96*math.sqrt(0.95*0.05/n_trials):.2f} 点)")
    print("    → **相関が無ければ RSS は正しい**。以下で落ちる分は実装ではなく")
    print("       「相関を無視したこと」そのもの。")

    # --- 相関を入れる -------------------------------------------------------- #
    print(f"\n  相関 ρ(ε, T_refl) を振る({n_trials} 試行ずつ、処理側は ρ=0 と仮定):")
    print(f"  {'ρ(現実)':>10}{'u_c(真, K)':>13}{'RSS 包含率':>13}"
          f"{'MC 包含率':>13}{'RSS 取りこぼし 下/上':>24}")
    sweep, rho_list = {}, (-0.9, -0.7, -0.4, 0.0, 0.4, 0.7, 0.9)
    for rho in rho_list:
        r = coverage_run(tab, cam, t_true, eps, u_eps, rho, rho, n_trials, 23)
        r0 = coverage_run(tab, cam, t_true, eps, u_eps, rho, 0.0, n_trials, 23)
        sweep[rho] = {"corr": r, "indep": r0}
        print(f"  {rho:>10.1f}{r['u_corr']:>13.4f}{100*r0['cov_rss']:>12.2f}%"
              f"{100*r['cov_mc']:>12.2f}%"
              f"{100*r0['miss_lo']:>13.2f}% /{100*r0['miss_hi']:>7.2f}%")
    head = sweep[0.7]
    print(f"  → ★★ρ=+0.7 の現実で、独立 RSS の「95 % 区間」は "
          f"**{100*sweep[0.7]['indep']['cov_rss']:.2f} %** しか包まない。")
    print(f"     相関つき MC は {100*head['corr']['cov_mc']:.2f} %。差は "
          f"{100*(head['corr']['cov_mc']-sweep[0.7]['indep']['cov_rss']):.2f} ポイント。")
    print(f"     真の合成不確かさ {head['corr']['u_corr']:.4f} K に対し RSS は "
          f"{base['u_rss']:.4f} K —— **区間が "
          f"{100*(1-base['u_rss']/head['corr']['u_corr']):.1f} % 狭い**。")
    print(f"  → ★取りこぼしは片側に寄る: 下側 "
          f"{100*sweep[0.7]['indep']['miss_lo']:.2f} % / 上側 "
          f"{100*sweep[0.7]['indep']['miss_hi']:.2f} %。逆算が ε で割る非線形なので")
    print("     分布が歪み、**対称な ±k·u は歪んだ分布を対称には外さない**。")
    print(f"  → ρ = −0.7 なら RSS は逆に "
          f"{100*sweep[-0.7]['indep']['cov_rss']:.2f} % と**過剰に**包む。")
    print("     保守的に見えるが、その区間で合否を切ると今度は落としすぎる(§4 後半)。")

    # --- MC が引いた相関が本当に入っているかを、op で測り返す ----------------- #
    dev = sweep[0.7]["corr"]["dev_r"][:, :2]
    cov = np.asarray(fs.stat_covariance(dev))
    cor = np.asarray(fs.stat_correlation(dev))
    print(f"  ★自分の乱数を測り返す(fs.stat_correlation): ρ_実測 = {cor[0,1]:.4f}"
          f"(注入 0.7)、u(ε)_実測 = {math.sqrt(cov[0,0]):.4f}(注入 {u_eps})")
    desc = fs.stat_describe(sweep[0.7]["corr"]["prop"])
    print(f"  ★伝播した T の分布(fs.stat_describe): 中央 {desc['percentiles']['p50']:.3f} K、"
          f"p5 {desc['percentiles']['p5']:.3f} / p95 {desc['percentiles']['p95']:.3f}、"
          f"std {desc['std']:.4f} K")

    if figs.enabled():
        rr = np.array(rho_list, float)
        figs.save_plot(
            "coverage_rho",
            [("独立 RSS の 95 % 区間", rr,
              np.array([100 * sweep[r]["indep"]["cov_rss"] for r in rho_list])),
             ("相関つき MC の 95 % 区間", rr,
              np.array([100 * sweep[r]["corr"]["cov_mc"] for r in rho_list])),
             ("名目の 95 %", rr, np.full(rr.size, 95.0))],
            xlabel="現実の相関 ρ(ε, T_refl)", ylabel="区間が真値を包んだ割合 [%]",
            title="「95 % 区間」が実際に包む割合",
            caption=f"{n_trials} 試行 / 点。ρ=0 では両方 95 %(=床)。"
                    "ρ>0 で RSS は足りず、ρ<0 では過剰。**どちらも 95 % ではない**。")
        hist, edges = fs.stat_histogram(sweep[0.7]["corr"]["prop"], bins=60)
        ctr = 0.5 * (np.asarray(edges)[:-1] + np.asarray(edges)[1:])
        gauss = (np.max(hist) * np.exp(-0.5 * ((ctr - float(desc["mean"]))
                                               / float(desc["std"])) ** 2))
        figs.save_plot("propagated", [("相関つき MC の分布", ctr, np.asarray(hist, float)),
                                      ("同じ σ の正規分布", ctr, gauss)],
                       xlabel="逆算した T_obj [K]", ylabel="度数",
                       title="伝播した分布は正規ではない(歪む)",
                       caption="ε で割る非線形が右に裾を作る。±k·u の対称な区間は"
                               "この歪みを対称には外さない —— 取りこぼしが片側に寄る。")

    # --- guard band(合否判定)----------------------------------------------- #
    guard = section_guard_band(tab, cam, eps, u_eps, base, sweep[0.7]["corr"])
    return {"base": base, "sweep": sweep, "head": head, "guard": guard,
            "corr_measured": float(cor[0, 1]), "desc": desc, "n_trials": n_trials}


def section_guard_band(tab, cam, eps, u_eps, base, head, n_trials: int = 40000):
    print(f"\n  === guard band —— 「表面温度 ≤ {GUARD_LIMIT_C:.0f} ℃ なら合格」 ===")
    limit_k = GUARD_LIMIT_C + T0_C
    rng = np.random.default_rng(97)
    # 真値は閾値のまわり ±15 K の一様分布。**分母を明示する**。
    t_true = rng.uniform(limit_k - 15.0, limit_k + 15.0, n_trials)
    dev = correlated_draws(rng, [u for _, _, u in base["inputs"]], 0.7, n_trials)
    lm = forward_radiance(tab, t_true, eps + dev[:, 0], T_REFL_REF + dev[:, 1],
                          TAU_REF + dev[:, 2], T_ATM_REF + dev[:, 3])
    dn = cam.to_dn(lm * (1.0 + dev[:, 4]), None, quantize=False)
    dn = np.clip(np.rint(dn + dev[:, 5] + dev[:, 6]), 0.0, cam.dn_max)
    t_hat = np.asarray(invert_radiance(tab, cam.to_radiance(dn), eps, T_REFL_REF,
                                       TAU_REF, T_ATM_REF, allow_out=True), np.float64)
    ok = np.isfinite(t_hat)
    truly_bad = t_true > limit_k
    print(f"  試行 {n_trials}(真値は {GUARD_LIMIT_C-15:.0f}〜{GUARD_LIMIT_C+15:.0f} ℃ の"
          f"一様分布)。真に不合格な個体 {int(truly_bad.sum())} / "
          f"真に合格 {int((~truly_bad).sum())}、逆算破綻 {int((~ok).sum())} 件")
    print(f"  {'判定の仕方':>34}{'guard band [K]':>16}{'誤合格率':>12}"
          f"{'誤不合格率':>12}{'合格率':>10}")
    rules = [("不確かさを無視(T̂ ≤ 閾値)", 0.0),
             ("独立 RSS の guard band", base["half_rss"]),
             ("相関つき MC の guard band", -head["off"][0])]
    rows, out = [], {}
    for name, band in rules:
        passed = ok & (t_hat + band <= limit_k)
        fa = float(np.sum(passed & truly_bad)) / n_trials
        fr = float(np.sum(ok & ~passed & ~truly_bad)) / n_trials
        out[name] = {"band": band, "fa": fa, "fr": fr,
                     "pass_rate": float(np.mean(passed))}
        rows.append((name, f"{band:.3f}", f"{100*fa:.2f} %", f"{100*fr:.2f} %",
                     f"{100*np.mean(passed):.1f} %"))
        print(f"  {name:>34}{band:>16.3f}{100*fa:>11.2f}%{100*fr:>11.2f}%"
              f"{100*np.mean(passed):>9.1f}%")
    fa0 = out["不確かさを無視(T̂ ≤ 閾値)"]["fa"]
    fa1 = out["独立 RSS の guard band"]["fa"]
    fa2 = out["相関つき MC の guard band"]["fa"]
    print(f"  → ★★誤合格は {100*fa0:.2f} % → {100*fa1:.2f} % → {100*fa2:.2f} %。")
    print(f"     RSS の guard band は MC の {fa1/fa2:.1f} 倍の誤合格を残す —— ")
    print("     **安全なつもりで、区間が狭い分だけ通してしまっている**。")
    print("  → 代償は誤不合格: "
          + " → ".join(f"{100*out[n]['fr']:.2f} %" for n, _ in rules)
          + "。**誤合格を減らす唯一の代償が誤不合格**で、選べるのは交換レートだけ。")
    figs.save_table("guardband", ["判定の仕方", "guard band [K]", "誤合格率",
                                  "誤不合格率", "合格率"], rows,
                    title=f"合否判定 —— 「≤ {GUARD_LIMIT_C:.0f} ℃ なら合格」を "
                          f"{n_trials} 回",
                    caption=f"真値は閾値 ±15 K の一様分布(分母 {n_trials})。"
                            "ε=0.60±0.05、ρ(ε,T_refl)=0.7。guard band は"
                            "「合格と言う前に閾値から何 K 手前で切るか」。")
    if figs.enabled():
        ks = np.linspace(0.0, 3.0, 31)
        fa_r, fr_r, fa_m, fr_m = [], [], [], []
        for kk in ks:
            for band, fa_l, fr_l in ((kk * base["u_rss"], fa_r, fr_r),
                                     (kk * head["half_mc"] / 1.96, fa_m, fr_m)):
                p = ok & (t_hat + band <= limit_k)
                fa_l.append(100.0 * np.sum(p & truly_bad) / n_trials)
                fr_l.append(100.0 * np.sum(ok & ~p & ~truly_bad) / n_trials)
        figs.save_plot("guardband_tradeoff",
                       [("誤合格(RSS の u)", ks, np.array(fa_r)),
                        ("誤不合格(RSS の u)", ks, np.array(fr_r)),
                        ("誤合格(相関つき MC の u)", ks, np.array(fa_m)),
                        ("誤不合格(相関つき MC の u)", ks, np.array(fr_m))],
                       xlabel="guard band の広さ k(× 合成標準不確かさ)",
                       ylabel="率 [%]",
                       title="誤合格と誤不合格は交換するしかない",
                       caption="同じ k でも u が違えば切る位置が違う。"
                               "RSS の u は小さいので、同じ k の名目でも"
                               "実際には浅くしか切れていない。")
    return out


# --------------------------------------------------------------------------- #
# 5. 単位・規約の崖 —— 例外で止まるか、静かに間違うか                            #
# --------------------------------------------------------------------------- #
def section_units(scene):
    print("\n=== 5. 単位・規約の崖 —— 止まるものと、静かに間違うもの ===")
    tab, cam = scene["tabs"]["LWIR"], scene["cam"]
    rows, loud, quiet = [], 0, 0

    def record(name, kind, detail):
        nonlocal loud, quiet
        rows.append((name, kind, detail))
        print(f"  {kind:<10}{name:<34}{detail}")
        if kind == "例外で止まる":
            loud += 1
        else:
            quiet += 1

    # (1) 波長を µm のまま SI 式(c2 は m·K)に入れる。
    lam_um, t = 10.0, 350.0
    good = C1L_UM / (lam_um ** 5 * math.expm1(C2_UM / (lam_um * t)))
    bad_x = C2_M / (lam_um * t)                       # µm を m と取り違えた指数
    bad = C1L_UM / (lam_um ** 5 * math.expm1(bad_x))
    try:
        tab.temperature(np.array([bad * 6.0]))        # 帯域幅ぶん掛けて表を引く
        record("λ を µm のまま SI 式へ", "静かに間違う", "表を通ってしまった")
    except Exception as exc:                          # noqa: BLE001
        record("λ を µm のまま SI 式へ", "例外で止まる",
               f"{type(exc).__name__}(L が真値の {bad/good:.1e} 倍 → 校正表の外)")

    # (2) T_refl をセ氏の数値のまま入れる(22 ℃ を 22 K と読む)。
    try:
        invert_radiance(tab, forward_radiance(tab, 350.0, EPS_POLISH, T_REFL_REF,
                                              1.0, T_ATM_REF),
                        EPS_POLISH, 22.0, 1.0, T_ATM_REF)
        record("T_refl をセ氏の数値のまま", "静かに間違う", "通ってしまった")
    except Exception as exc:                          # noqa: BLE001
        record("T_refl をセ氏の数値のまま", "例外で止まる",
               f"{type(exc).__name__}(22 K は校正表 {TAB_LO:.0f}–{TAB_HI:.0f} K の外)")

    # (3) T_refl を「295 K のつもりで 295 ℃」と書く —— 範囲内なので通る。
    lm = forward_radiance(tab, 350.0, EPS_POLISH, T_REFL_REF, 1.0, T_ATM_REF)
    hot = float(invert_radiance(tab, lm, EPS_POLISH, 295.0 + T0_C, 1.0, T_ATM_REF))
    record("T_refl を 295 K のつもりで 295 ℃", "静かに間違う",
           f"{hot-350.0:+.1f} K ずれるが**例外は出ない**(568 K は表の中)")

    # (4) DN を平均してから温度に直す(Jensen の不等式)。
    grad = np.linspace(320.0, 400.0, 4096)
    l_pix = forward_radiance(tab, grad, EPS_PAINT, T_REFL_REF, 1.0, T_ATM_REF)
    dn_pix = cam.to_dn(l_pix, quantize=False)
    t_pix = np.asarray(invert_radiance(tab, cam.to_radiance(dn_pix), EPS_PAINT,
                                       T_REFL_REF, 1.0, T_ATM_REF), np.float64)
    t_of_mean = float(invert_radiance(tab, cam.to_radiance(float(np.mean(dn_pix))),
                                      EPS_PAINT, T_REFL_REF, 1.0, T_ATM_REF))
    jensen = t_of_mean - float(np.mean(t_pix))
    record("DN を平均してから温度に直す", "静かに間違う",
           f"{jensen:+.3f} K(L は T に凸なので**必ず高く出る**)")

    # (5) 見かけ温度(ε=1)を表面温度と呼ぶ。
    lm = forward_radiance(tab, 350.0, EPS_PAINT, T_REFL_REF, 1.0, T_ATM_REF)
    app = float(invert_radiance(tab, lm, 1.0, T_REFL_REF, 1.0, T_ATM_REF))
    record("見かけ温度を表面温度と呼ぶ", "静かに間違う",
           f"{app-350.0:+.3f} K。絵も単位も完全にもっともらしい")

    # (6) τ を二重に掛ける(大気と窓で 1 回ずつ引いたつもりが同じ量)。
    lm = forward_radiance(tab, 350.0, EPS_PAINT, T_REFL_REF, TAU_REF, T_ATM_REF)
    once = float(invert_radiance(tab, lm, EPS_PAINT, T_REFL_REF, TAU_REF, T_ATM_REF))
    twice = float(invert_radiance(tab, lm, EPS_PAINT, T_REFL_REF,
                                  TAU_REF ** 2, T_ATM_REF))
    record("τ を大気と窓で二重に掛ける", "静かに間違う",
           f"{twice-once:+.3f} K(正しい {once-350.0:+.3f} K に対して)")

    # (7) 感度 ΔT/T をセ氏で計算する。
    n_k = band_index_predicted("LWIR", 350.0)
    n_c = C2_UM / (band_effective_lambda("LWIR", 350.0) * (350.0 - T0_C))
    record("ΔT/T をセ氏で計算して n を出す", "静かに間違う",
           f"感度が {n_k/n_c:.2f} 倍(n が {n_k:.3f} → {n_c:.3f})")

    print(f"  → **例外で止まる {loud} 件 / 静かに間違う {quiet} 件**。")
    print("     止まったのはどちらも `fs.interp_linear(out_of_range='raise')` が")
    print("     「校正表の外だ」と言った場合 —— **fail-closed が効いた地点**。")
    print("     静かに間違う 4 件は、絵も単位も数字の桁も、全部もっともらしい。")
    figs.save_table("units", ["取り違え", "どうなるか", "実測"], rows,
                    title="単位・規約の崖 —— 止まる 2 件、静かに間違う 4 件",
                    caption="止まるのは校正表の範囲外に落ちたときだけ。"
                            "範囲内に収まる取り違えは、何の兆候も出さない。")
    return {"rows": rows, "loud": loud, "quiet": quiet, "jensen": jensen,
            "apparent": app - 350.0, "tau_twice": twice - once,
            "n_ratio": n_k / n_c}


# --------------------------------------------------------------------------- #
# 6. 熱画像の場面 —— いちばん熱い所が、いちばん冷たく見える                       #
# --------------------------------------------------------------------------- #
def scene_truth(h: int = 180, w: int = 240):
    """真の ``(T_obj [K], ε)`` の 2 枚。**実データに差し替えるのはここ**。

    塗装した配電盤のバスバー(ε=0.95)の上に、**研磨したボルト**(ε=0.10)が
    載っている場面。ボルトと周りの金具は**同じ温度**に置く —— 温度差ではなく
    放射率差だけで絵がどう化けるかを見るため。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    t = np.full((h, w), 305.0)
    # 発熱している接続部(なだらかな山)。
    t += 70.0 * np.exp(-(((xx - 120.0) / 46.0) ** 2 + ((yy - 92.0) / 34.0) ** 2))
    eps = np.full((h, w), EPS_PAINT)
    # 研磨ボルト 2 本。ひとつは発熱部の真上、もうひとつは冷えた縁の上。
    for cx, cy in ((120.0, 92.0), (36.0, 40.0)):
        eps[np.hypot(xx - cx, yy - cy) < 15.0] = EPS_POLISH
    return t, eps


def section_image(scene):
    print("\n=== 6. 熱画像 —— いちばん熱い所が、いちばん冷たく見える ===")
    tab, cam = scene["tabs"]["LWIR"], scene["cam"]
    t_true, eps_map = scene_truth()
    lm = forward_radiance(tab, t_true, eps_map, T_REFL_REF, TAU_REF, T_ATM_REF)
    rng = np.random.default_rng(4242)
    dn = cam.to_dn(lm, rng, quantize=True)
    # 光子検出器なら雑音は Poisson。`fs.photon_uncertainty` で 1σ を出して足す。
    sigma_shot = np.asarray(fs.photon_uncertainty(dn, zero_floor=1.0), np.float64)
    dn = np.clip(np.rint(dn + rng.normal(0.0, 0.05 * sigma_shot)), 0.0, cam.dn_max)
    l_hat = cam.to_radiance(dn)
    t_apparent = np.asarray(invert_radiance(tab, l_hat, 1.0, T_REFL_REF, TAU_REF,
                                            T_ATM_REF, allow_out=True), np.float64)
    t_corr = np.asarray(invert_radiance(tab, l_hat, eps_map, T_REFL_REF, TAU_REF,
                                        T_ATM_REF, allow_out=True), np.float64)
    bolt = np.zeros(t_true.shape, bool)
    yy, xx = np.mgrid[0:t_true.shape[0], 0:t_true.shape[1]].astype(np.float64)
    bolt[np.hypot(xx - 120.0, yy - 92.0) < 11.0] = True
    ring = (np.hypot(xx - 120.0, yy - 92.0) > 19.0) & (np.hypot(xx - 120.0,
                                                                yy - 92.0) < 26.0)
    print(f"  発熱部の真上のボルト(ε={EPS_POLISH}): 真 "
          f"{float(t_true[bolt].mean()):.1f} K / 見かけ(ε=1) "
          f"{float(t_apparent[bolt].mean()):.1f} K / 補正後 "
          f"{float(t_corr[bolt].mean()):.1f} K")
    print(f"  そのすぐ周りの塗装面(ε={EPS_PAINT}): 真 "
          f"{float(t_true[ring].mean()):.1f} K / 見かけ "
          f"{float(t_apparent[ring].mean()):.1f} K / 補正後 "
          f"{float(t_corr[ring].mean()):.1f} K")
    gap = float(t_apparent[ring].mean() - t_apparent[bolt].mean())
    print(f"  → ★**見かけの絵では、ボルトが周りより {gap:.1f} K 低く見える** ——")
    print("     実際には同じ温度なのに、絵の上では「そこだけ冷えている」= 健全に見える。")
    rms = float(np.sqrt(np.mean((t_corr - t_true) ** 2)))
    rms_app = float(np.sqrt(np.mean((t_apparent - t_true) ** 2)))
    print(f"  補正後の残差 rms = {rms:.3f} K(雑音の床)。見かけ温度の rms = "
          f"{rms_app:.3f} K。")
    # 領域平均の取り方(§5 (4) の Jensen をこの絵の上で数える)。
    hot = t_true > 340.0
    t_of_mean_dn = float(invert_radiance(tab, cam.to_radiance(float(dn[hot].mean())),
                                         EPS_PAINT, T_REFL_REF, TAU_REF, T_ATM_REF))
    mean_of_t = float(t_corr[hot].mean())
    print(f"  領域平均の取り方: DN を平均してから温度 {t_of_mean_dn:.3f} K / "
          f"温度にしてから平均 {mean_of_t:.3f} K(差 {t_of_mean_dn-mean_of_t:+.3f} K)")
    figs.save_grid("scene",
                   [t_true, t_apparent, t_corr, t_corr - t_true],
                   ["真の表面温度 [K]", "見かけ温度(ε=1)[K]",
                    "ε 地図で補正 [K]", "補正後の残差 [K](0 が中心)"],
                   ncols=2, signed=[False, False, False, True],
                   title="熱画像は温度画像ではない",
                   caption=f"塗装面(ε={EPS_PAINT})の上に研磨ボルト(ε={EPS_POLISH})。"
                           f"ボルトと周りは**同じ温度**なのに、見かけの絵では"
                           f"{gap:.0f} K 低く写る。補正後の残差 rms {rms:.3f} K。")
    if figs.enabled():
        row = t_true.shape[0] // 2
        xs = np.arange(t_true.shape[1], dtype=np.float64)
        figs.save_plot("scene_profile",
                       [("真の表面温度", xs, t_true[row]),
                        ("見かけ温度(ε=1)", xs, t_apparent[row]),
                        ("ε 地図で補正", xs, t_corr[row])],
                       xlabel="画素(中央の行を横切る)", ylabel="温度 [K]",
                       title="ボルトの所だけ、見かけの絵が谷になる",
                       caption="谷は温度の谷ではなく**放射率の谷**。"
                               "補正すると平らな山に戻る。")
    return {"gap": gap, "rms": rms, "rms_app": rms_app,
            "bolt_true": float(t_true[bolt].mean()),
            "bolt_app": float(t_apparent[bolt].mean()),
            "bolt_corr": float(t_corr[bolt].mean()),
            "ring_app": float(t_apparent[ring].mean()),
            "jensen_img": t_of_mean_dn - mean_of_t}


# --------------------------------------------------------------------------- #
# 7. 道具の穴 —— 4 層すべて引いてから「無い」と言う                              #
# --------------------------------------------------------------------------- #
def section_op_holes():
    print("\n=== 7. 道具の穴 —— fs / fs.op / fs.ledger / op_find の 4 層を引く ===")
    wanted = [
        ("planck", "Planck 則そのもの"),
        ("blackbody", "黒体の帯域放射輝度"),
        ("emissiv", "放射率の補正"),
        ("temperature", "放射輝度 ↔ 温度"),
        ("radiom", "放射測定(ラジオメトリ)"),
        ("thermal", "熱画像の処理"),
        ("infrared", "赤外の帯域"),
        ("stefan", "Stefan–Boltzmann"),
        ("kelvin", "温度の単位"),
        ("atmos", "大気の透過"),
        ("uncert", "測定の不確かさ"),
        ("montecarlo", "相関つき Monte Carlo 伝播"),
        ("guard", "guard band(合否判定)"),
    ]
    rows, holes = [], []
    for name, note in wanted:
        tiers = (hasattr(fs, name), hasattr(fs.op, name), hasattr(fs.ledger, name))
        hits = [d["op"] for d in fs.op_find(name)]
        # ★``op_find`` は語幹の部分一致で拾う。``blackbody`` は 4 件返すが中身は
        #   ``cv_blackhat`` などのモルフォロジで、**熱放射とは何の関係も無い**。
        #   件数を見て「在る」と読むと外す。**先頭の名前まで見てから**言う。
        top = hits[0] if hits else "—"
        rows.append((name, "○" if tiers[0] else "-", "○" if tiers[1] else "-",
                     "○" if tiers[2] else "-", f"{len(hits)} ({top})", note))
        print(f"  {name:<12} fs:{'○' if tiers[0] else '-'} "
              f"fs.op:{'○' if tiers[1] else '-'} "
              f"fs.ledger:{'○' if tiers[2] else '-'} "
              f"op_find:{len(hits):>2} 件 (先頭 {top:<22}) {note}")
        if not any(tiers) and name not in hits:
            holes.append(name)
    used = ["interp_linear", "stat_covariance", "stat_correlation", "mat_eigh",
            "stat_describe", "stat_histogram", "photon_uncertainty", "noise_sigma",
            "beer_lambert_transmittance", "poly_fit"]
    print("  使えた op: " + ", ".join(used))
    for name in used:
        assert hasattr(fs, name) or hasattr(fs.ledger, name), name
    print("  ★使おうとして**使えなかった**もの:")
    print("    * `tolerance_analysis` —— `op_find('montecarlo')` が返す唯一の op だが、")
    print("      **レンズの製造公差専用**(引数は radius_pct / thickness_mm / index …)。")
    print("      任意の測定モデルに対する GUM の伝播には使えない。名前だけ近い。")
    print("    * `photon_uncertainty` は Poisson の 1σ 地図は出すが、**そこから先**")
    print("      (感度 × 不確かさ → 合成 → 区間)を持つ op が無いので、§4 の予算表は")
    print("      全部この PoC の中で手で書いた。")
    print("    * `stat_covariance` / `mat_eigh` はあるが **Cholesky 分解が無い** ——")
    print("      相関つきの乱数を引くのに固有分解から平方根を作った(§4)。")
    print("      正定値行列なら Cholesky のほうが速く、数値的にも素直。")
    print("    * `beer_lambert_transmittance` は τ = exp(−σL) を出すが、**大気の**")
    print("      透過は帯域と水蒸気量で決まるので、σ をどこから取るかは自分で決めた。")
    print("  ★次に埋めるべき op(この PoC を書いていて欲しかった順):")
    print("    1. `planck_radiance(wavelength_um, temperature_k)` —— 分光放射輝度。")
    print("       λ の単位を**引数名で強制**する(§5 の例外 2 件はこれで消える)。")
    print("    2. `band_radiance(band, temperature_k)` / `radiance_to_temperature` ——")
    print("       帯域積分と、その単調な逆変換。校正範囲の外は fail-closed。")
    print("    3. `emissivity_correct(l_meas, eps, t_refl, tau, t_atm)` —— 現場の式。")
    print("       各自が書き写すと、必ずどこかで反射項か τ が落ちる(§3 のゼロ点)。")
    print("    4. `Quantity`(値 + 単位)と `Uncertainty`(値 + u + 分布)——")
    print("       §5 の静かな 4 件は、単位が型に乗っていれば全部 loud になる。")
    print("    5. `CovarianceGroup` —— 入力どうしの相関を**予算表の行として**持つ。")
    print("       §4 の予算表に相関の行が無いことが、そのまま 6.6 点の穴になった。")
    print("    6. `GuardBandDecision(estimate, uncertainty, limit, k)` —— 合否と、")
    print("       誤合格率・誤不合格率を同時に返す。判定を「>」1 文字で書かせない。")
    figs.save_table("op_holes", ["語幹", "fs", "fs.op", "fs.ledger",
                                 "op_find 件数(先頭)", "何が欲しかったか"], rows,
                    title="4 層すべて引いた結果 —— 熱放射測定の op は 1 つも無い",
                    caption="○ = 在る。件数が 0 でなくても中身は無関係"
                            "(blackbody → cv_blackhat のモルフォロジ)。"
                            "展示は 2 本あるのに、支える op がゼロ。")
    return {"rows": rows, "holes": holes, "used": used}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("熱画像は温度画像ではない —— 放射率を取り違えたまま「温度」と呼ぶ")
    print(f"LWIR {BANDS['LWIR'][0]:.0f}–{BANDS['LWIR'][1]:.0f} µm / "
          f"MWIR {BANDS['MWIR'][0]:.0f}–{BANDS['MWIR'][1]:.0f} µm / "
          f"NETD {NETD_K*1000:.0f} mK / {ADC_BITS} bit / 合否閾値 "
          f"{GUARD_LIMIT_C:.0f} ℃")
    print("=" * 78)

    scene = section_scene()
    cliff = section_cliff(scene)
    nulls = section_nulls(scene)
    unc = section_uncertainty(scene)
    units = section_units(scene)
    image = section_image(scene)
    holes = section_op_holes()

    print("\n" + "=" * 78)
    print("まとめ —— 何がどれだけ効いたか")
    print("=" * 78)
    head = unc["head"]
    indep07 = unc["sweep"][0.7]["indep"]
    rows = [
        ("床(量子化 + NETD の往復 rms)", f"{scene['cases']['量子化 + NETD']:.2e} K"),
        ("ゼロ点: DN を線形に温度と呼ぶ(ε=0.95)",
         f"{nulls['DN を線形に温度と呼ぶ'][0]:+.2f} K"),
        ("ゼロ点: ε=1 固定(ε=0.95 / 0.10)",
         f"{nulls['ε=1 固定(見かけ温度)'][0]:+.2f} / "
         f"{nulls['ε=1 固定(見かけ温度)'][2]:+.1f} K"),
        ("ゼロ点: 反射項を落とす(ε=0.10)",
         f"{nulls['反射項を落とす'][2]:+.2f} K"),
        ("Δε/ε=5 % の温度誤差(LWIR 305 K → 800 K)",
         f"{cliff['abs_dt'][('LWIR', 305.0)]:.2f} → "
         f"{cliff['abs_dt'][('LWIR', 800.0)]:.2f} K"),
        ("同(周囲からの上昇に対する比)",
         f"{100*cliff['rise'][('LWIR', 305.0)]:.1f} → "
         f"{100*cliff['rise'][('LWIR', 800.0)]:.1f} %"),
        ("Δε=0.02 の温度誤差(ε=0.95 / 0.10)",
         f"{cliff['by_eps'][EPS_PAINT]:.2f} / {cliff['by_eps'][EPS_POLISH]:.2f} K"),
        ("包含率(ρ=0 の床): RSS / MC",
         f"{100*unc['base']['cov_rss']:.2f} / {100*unc['base']['cov_mc']:.2f} %"),
        ("包含率(ρ=+0.7): RSS / MC",
         f"{100*indep07['cov_rss']:.2f} / {100*head['cov_mc']:.2f} %"),
        ("RSS の取りこぼし(下側 / 上側)",
         f"{100*indep07['miss_lo']:.2f} / {100*indep07['miss_hi']:.2f} %"),
        ("誤合格率(無視 / RSS / MC)",
         " / ".join(f"{100*unc['guard'][k]['fa']:.2f}" for k in unc["guard"]) + " %"),
        ("誤不合格率(無視 / RSS / MC)",
         " / ".join(f"{100*unc['guard'][k]['fr']:.2f}" for k in unc["guard"]) + " %"),
        ("単位の取り違え(例外 / 静かに間違う)",
         f"{units['loud']} / {units['quiet']} 件"),
        ("熱画像: 同温のボルトが周りより低く見える量", f"{image['gap']:.1f} K"),
    ]
    for name, val in rows:
        print(f"  {name:<44}{val:>22}")
    figs.save_table("summary", ["条件", "値"], rows,
                    title="熱放射測定 —— 何がどれだけ効くか",
                    caption="ゼロ点はどれも失格。★中心は包含率 ——「95 % 区間」が"
                            "95 % を包まないこと。")

    # --- 所見を固定する(穴が塞がったら鳴る)--------------------------------- #
    # 1. 床: 真値を知っていれば往復は閉じる。表は直接積分と一致する。
    assert scene["tab_gap"] < 1e-8, scene["tab_gap"]
    assert scene["cases"]["Case-0 雑音も量子化も無し"] < 1e-6, scene["cases"]
    assert scene["cases"]["量子化 + NETD"] < 0.05, scene["cases"]
    # Simpson は節点を増やすと収束する(33 → 513 で 3 桁以上)
    for band, conv in scene["conv"].items():
        assert conv[0][1] > conv[-1][1] * 100.0, (band, conv)
    # 2. 閉形式の予測: λ_eff を 1/λ 重みで取れば 5 % 以内、帯の中央だと外す
    assert cliff["worst_eff"] < 0.05, cliff["worst_eff"]
    assert cliff["worst_mid"] > 2.0 * cliff["worst_eff"], (cliff["worst_mid"],
                                                           cliff["worst_eff"])
    assert cliff["worst_pred"] < 0.6, cliff["worst_pred"]   # 1 次展開の残差
    # 3. ★外した予測: 絶対誤差は**高温ほど大きい**(T² で増える)
    assert cliff["abs_dt"][("LWIR", 800.0)] > 5.0 * cliff["abs_dt"][("LWIR", 305.0)]
    # ★物差しを変えると予測どおり(上昇に対する比は低温ほど大きい)
    assert cliff["rise"][("LWIR", 305.0)] > 3.0 * cliff["rise"][("LWIR", 800.0)]
    # 4. 低放射率は無条件に急(同じ絶対 Δε で 10 倍以上)
    assert cliff["ratio"] > 10.0, cliff["ratio"]
    # MWIR は放射率に強い(n が大きい)が、反射の効きは帯で消えない
    assert abs(cliff["refl"][("LWIR", EPS_POLISH)]) > 5.0 * abs(
        cliff["refl"][("LWIR", EPS_PAINT)])
    # 5. ゼロ点はどれも床の 100 倍以上外す。ε=1 固定は ε が小さいほど致命的
    for label in ("DN を線形に温度と呼ぶ", "ε=1 固定(見かけ温度)", "反射項を落とす"):
        assert abs(nulls[label][0]) > 100.0 * scene["cases"]["量子化 + NETD"], label
    assert abs(nulls["ε=1 固定(見かけ温度)"][2]) > 10.0 * abs(
        nulls["ε=1 固定(見かけ温度)"][0])
    assert abs(nulls["全部正しく入れる(対照群)"][0]) < 1e-6
    # 6. ★★包含率。床(ρ=0)では RSS も MC も 95 %、相関を入れると RSS が落ちる
    n = unc["n_trials"]
    tol = 4.0 * math.sqrt(0.95 * 0.05 / n)          # 4σ の標本誤差
    assert abs(unc["base"]["cov_rss"] - 0.95) < tol, unc["base"]["cov_rss"]
    assert abs(unc["base"]["cov_mc"] - 0.95) < tol, unc["base"]["cov_mc"]
    assert abs(unc["sweep"][0.7]["corr"]["cov_mc"] - 0.95) < 0.01, unc["sweep"][0.7]
    assert unc["sweep"][0.7]["indep"]["cov_rss"] < 0.92, unc["sweep"][0.7]
    assert unc["sweep"][-0.7]["indep"]["cov_rss"] > 0.98, unc["sweep"][-0.7]
    # 包含率は ρ に対して単調に下がる(相関が増えるほど RSS は足りなくなる)
    covs = [unc["sweep"][r]["indep"]["cov_rss"] for r in (-0.9, -0.7, -0.4, 0.0,
                                                          0.4, 0.7, 0.9)]
    assert all(a >= b - 1e-9 for a, b in zip(covs, covs[1:])), covs
    # 相関つきの真の不確かさは RSS より大きい
    assert unc["head"]["u_corr"] > 1.15 * unc["base"]["u_rss"], (unc["head"]["u_corr"],
                                                                 unc["base"]["u_rss"])
    # 自分の乱数を測り返して、狙った相関が本当に入っている
    assert abs(unc["corr_measured"] - 0.7) < 0.03, unc["corr_measured"]
    # 7. ★取りこぼしは片側に寄る(対称な ±k·u が歪んだ分布を外す)
    lo_m, hi_m = indep07["miss_lo"], indep07["miss_hi"]
    assert lo_m > 0.0 and hi_m > 0.0
    assert max(lo_m, hi_m) > 1.15 * min(lo_m, hi_m), (lo_m, hi_m)
    # 8. ★★guard band: 誤合格は 無視 > RSS > MC、誤不合格はその逆
    g = unc["guard"]
    keys = list(g)
    assert g[keys[0]]["fa"] > g[keys[1]]["fa"] > g[keys[2]]["fa"], g
    assert g[keys[0]]["fr"] < g[keys[1]]["fr"] < g[keys[2]]["fr"], g
    assert g[keys[1]]["fa"] > 1.3 * g[keys[2]]["fa"], g     # RSS は誤合格を残す
    # 率が 0 %/100 % に振り切れていない(振り切れたら分母か窓の取り方が悪い)
    for k in keys:
        assert 0.0 < g[k]["fa"] < 0.5, (k, g[k])
        assert 0.0 < g[k]["fr"] < 0.5, (k, g[k])
    # 9. 単位: 例外で止まるものと静かに間違うものが両方ある。静かのほうが多い
    assert units["loud"] >= 2, units["loud"]
    assert units["quiet"] > units["loud"], units
    assert units["jensen"] > 0.0, units["jensen"]           # Jensen は必ず正
    assert units["n_ratio"] > 4.0, units["n_ratio"]         # セ氏で計算すると桁違い
    # 10. 熱画像: 同じ温度のボルトが周りより低く見え、ε 地図で戻る
    assert image["gap"] > 30.0, image["gap"]
    assert abs(image["bolt_corr"] - image["bolt_true"]) < 0.5, image
    assert image["rms"] < 0.5 < image["rms_app"], image
    assert image["jensen_img"] > 0.0, image["jensen_img"]
    # 11. 道具の穴: 熱放射測定そのものの op は 4 層のどこにも無い
    for name in ("planck", "emissiv", "temperature", "radiom", "thermal",
                 "infrared", "stefan", "kelvin", "atmos", "guard"):
        assert name in holes["holes"], (name, holes["holes"])

    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
