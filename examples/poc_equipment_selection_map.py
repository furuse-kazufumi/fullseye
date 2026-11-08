# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 機材選びの事前試験 —— 照明 × カメラ × レンズの 60 通りで同じ傷を「撮り」、何 µm から見つかるかの地図を作る。

【問い】外観検査の機材は、照明・カメラ・レンズを別々のブースで、それぞれ最良の条件で見せられて選ぶことが多い。
けれど知りたいのは**組み合わせ**で、「この傷はどの組なら何 µm から 90 % 見つかるか」「安い組で足りるのはどこか、
高い機材でも駄目なのはどこか」である。同じ部品・同じ傷を、

  * 照明 6 種: 同軸落射 / ドーム / リング高角 70° / リング低角 30° / 暗視野 10° / 縞照明(位相シフトの偏向法、
    デフレクトメトリ: 細かい縞と粗い縞 × x と y × 4 位相 = 16 コマ。粗い縞で次数を決める)
  * カメラ 5 種: モノクロ / カラー(Bayer)/ 偏光(画素上の 4 方位、DoFP)/ SWIR(InGaAs、VGA 相当)/ ハイパースペクトル
    (SWIR のラインスキャン分光、950〜1650 nm を 10 nm おき 71 帯)
  * レンズ 2 種: 物体側テレセントリック / 通常(作動距離に置いたピンホール相当、視野の端で主光線が傾く)

の 60 通りで撮り、題材ごとに MIL-HDBK-1823A の手順(``fs.ledger.pod_ahat_fit`` → ``pod_from_ahat``)で a90/95 を出す。
題材は 3 つ(4 種の欠陥): S1 切削アルミの線傷(研磨の筋と平行、幅 2〜200 µm)、S2 塗装パネルの浅い凹み(ゆず肌つき、
深さ 0.5〜300 µm)、S3 白い樹脂(PP)の 0.25 mm 下の (a) 黒い焼け・(b) 白い PE の破片(径)。

★比べ方をそろえる(どれも初版のレビューで指摘された所):
  * **誤検出はマスごとに 1 %**: 判定閾値は、そのマスの採点に使う試験の無欠陥の部位の順序統計(越えるのが ⌊0.01 n⌋ 部位)。
    同じ誤検出率で a90/95 を比べるための定義で、門はその作り方を確かめるだけ。学習側で決めた閾値を持ち込んだ場合の
    誤検出は別に数える(全回を合わせて 3 % 以内を門にし、マスごとの最大も印字する)。
  * **露光の上限をそろえる**: 視野 1 枚 10 ms。面のカメラは 1 コマ(縞照明は 16 コマで分ける)、ラインスキャンの分光は
    1 ラインの露光の上限 = 10 ms / ライン数。露光は無欠陥の地の 99.9 % 点が満杯の 70 % になる値と上限の小さい方で、上限に
    当たったマスは全部印字する。★光子の数をそろえたのではない(地が早く満ちるマスは上限を使い切らず、同じ時間に何コマも
    足すことはしていない)。10 ms で視野を送るラインスキャンの分光は数十 kHz のライン速度で、実機(数百 Hz)では届かない
    —— 章 5 で上限を 100 ms・1 s にした表と、1 コマ 10 ms まで待つ表を出す。
  * **予算で変わる主張は full の予算でだけ門にする**: 線傷の低角 30° リング(どの種の組でも見つかる)と、浅い凹みの斜光
    (暗視野 10°、10 マス全部で見つかる)。縮小版(CI)では部位が少なく種の組で × と入れ替わるので、門にせず数を印字する。
    実データの門 3 件はデータがあるときだけ。
  * **揺れを出す**: 部位の種の組を変えて回し(full 3 組、縮小版 2 組)、各マスに中央値と最小〜最大を書く。「見つかる」は
    どの組でも 90 % に届くこと。黄枠(最良)はどの組でもその組の最良の 1.25 倍以内のマスだけ、橙枠(安くて足りる)は
    どの組でも最良の 1.5 倍以内で価格帯の目安が黄枠より安いマスだけ(種の組で入れ替わる枠は付けない)。
  * **設定で決まる所は掃引して見せる**(章 5): 同軸の拡散面の大きさ(地図は視野の 2 倍、表に 1・1.5 倍)、分光の露光の
    上限(10 ms・100 ms・1 s)と 1 コマ 10 ms まで待つ場合、分光の重みを学習せず帯を足すだけにした場合、ゆず肌を 1/5 に
    した場合、ドームの塊が視野の位置で出たり消えたりすること。

★作り方の要点(門は閉形式か別の実装):
  * **光源は形で持つ**: 照明を「部品の点から見て光る方向の領域」(円板・球帯・円筒の帯)として幾何で持ち、どれも
    「高さ h・半径 R の円の内側を通る光線」の差で書ける。鏡面のローブ(微小面の傾きの広がりとレンズの開口)を tan 空間の
    2 次元ガウスと置くと、照明に入る割合は非心 χ² の分布関数の差(``scipy.special.chndtr``)。縞照明は画面の上でローブが
    ぼかす分だけ縞の振幅が exp(−2π²(hσ/p)²) に落ちる。門: 照度は 6 照明とも閉形式と 0.5 % 以内、ローブの割合は乱数の
    光線 20 万本と 0.006 以内、縞の位相は傾けた鏡の閉形式 −2π h tan 2θ / p と一致。
  * **カメラは波長の鎖で持つ**: 光源の分光(白色 LED は 5000 K の黒体を IR カットで切った近似、SWIR はハロゲン 3000 K、
    どちらも帯域内の照度 200 W/m²)× 物体側の étendue π NA² p² × 露光 × フィルタ × QE × λ/hc。門: SWIR の鎖は
    ``spectralrad.hyperspectral_band_weights``(像側の F 値で書いた別の実装)と 1e-6 以内。雑音は光子 + 読み出し + 量子化。
  * **判定は全カメラ同じ手順**: チャンネルの重みは学習用の部位の半分で一般化固有値(欠陥の散らばり / 無欠陥の共分散、
    縮小 0.2)から決め、空間の検出器(線傷 = 幅の分からない縦の帯の整合フィルタの束、凹み = 凹みの大きさでならした円内の
    RMS、異物 = ガウスの整合フィルタ)を通した â で、別の部位を使って POD を測る。縞照明は位相の残差 2 枚がチャンネル。
  * **実データの裏取り(章 4)**: 支えるのは「カメラの帯で樹脂を分けられるか」の軸だけで、画素ごとの AUC(照明・レンズ・
    µm の値は支えない)。樹脂の破片(RODARE 3390)と豚バラの上の樹脂片(Zenodo 17242553)、どちらも CC BY 4.0。
    取得物は poc_hyperspectral_foreign_matter が作る写しを SHA-256 で照合して読む(違えば例外、無ければ記録値)。
    実データの門の閾値は、実データを一度見てから置いた。

★正直に書いておくこと: 面・傷・塗装・樹脂は**合成**で、材料の値のうち分光の吸収帯と Al の反射率以外は推定(E)。
特に S3b の「可視のカメラは PE を見つけない」は、材料表で PP と PE の可視の吸収を同じに置いた入力そのもので、
発見ではない(実データの破片はモノクロでも AUC 0.6 台で分かれる)。光は幾何光学(回折はレンズのぼけのガウス近似だけ)、
樹脂の中の散乱は Kubelka–Munk の 2 層と横方向のガウスのぼけ。照明の明るさ(放射輝度)は 6 種とも同じと置き、価格帯は
推定の序列。地図の µm の値は、この合成の試験の中での比べ合いに使い、実機の性能値として読まない。

走らせ方: ``py -3.11 examples/poc_equipment_selection_map.py``(既定は縮小版で数分)。展示の図と数字は
``FULLSEYE_POC_BUDGET=full``(手元で 20 分前後)で、図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage, special

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fringe  # noqa: E402
import fullseye as fs  # noqa: E402
import materials as MT  # noqa: E402
import realdata  # noqa: E402
import spectralrad as SR  # noqa: E402

#: 既定は縮小版(数分)。full(種の組 3・部位 2.3 倍、手元で 20 分前後)は FULLSEYE_POC_BUDGET=full のときだけ ——
#: PoC を走らせる門(tests/test_poc_scripts_run.py、1 本 600 秒)は CI を立てずに走らせるので、既定を full にすると落ちる。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced") != "full"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# =========================================================================== #
# 1. 光源: 「点 p から見て光る方向」を円の差で持つ
# =========================================================================== #
#: 照明の表示名と順番(地図の列)。fringe = 縞照明(位相シフトの偏向法、デフレクトメトリ)。
LIGHT_KEYS = ("coax", "dome", "ring70", "ring30", "dark10", "fringe")
LIGHT_NAMES = {"coax": "同軸落射", "dome": "ドーム", "ring70": "リング高角 70°", "ring30": "リング低角 30°",
               "dark10": "暗視野 10°", "fringe": "縞照明(偏向法)"}
DOME_HOLE_DEG, DOME_RIM_DEG = 12.0, 85.0       # ドームの天頂のカメラ穴と裾
RING_HALF_DEG = 3.0                           # リングの拡散板の上下の半幅(原点から見た仰角)
#: ★同軸落射の拡散面の半径 / 視野の幅は、地図では現場で選べる大きさ(視野の 2 倍)にする。1 倍だと通常レンズでは視野の端で
#: 地が暗くなり、「明視野にはテレセンが要る」はこの大きさで決まる(再レビューの指摘)。1 倍と 1.5 倍は章 5 の掃引の表に残す。
COAX_SCALE = 2.0
#: 縞照明の画面の半径 / 視野の幅。画面は同軸と同じくハーフミラーで光軸に折り、鏡像をカメラの高さに置く。
FRINGE_SCREEN_SCALE = 1.5


def make_lights(scale_mm: float, wd_mm: float, coax_scale: float = None) -> dict:
    """照明 6 種を、部品の大きさ *scale_mm*(視野の幅)と作動距離 *wd_mm* に合わせて置く。

    各照明は ``[(符号, 高さ h, 半径 R), ...]`` —— 「高さ h の水平な円(半径 R)の内側を通る光線」の集合の
    符号つきの和が、その照明の光る方向の領域になる。
      * 同軸落射: ハーフミラーで光軸に折った拡散面。鏡像はカメラと同じ高さ(作動距離)、半径は視野の幅 × *coax_scale*。
      * ドーム: 半径 *R_d* の半球の、天頂角 12°(カメラの穴)〜85° の帯 = 85° の円の内側 − 12° の円の内側。
      * リング(仰角 e、半幅 3°): 半径 R_r の円筒の、高さ R_r tan(e − 3°)〜R_r tan(e + 3°) の帯 =
        下の円の内側 − 上の円の内側(上向きの光線は低い円を先に横切る)。
      * 縞照明: 同軸と同じ置き方の画面(半径 = 視野の幅 × 1.5)。明るさの平均は 0.5、縞の形は ``render_bases`` が足す。
    """
    cs = COAX_SCALE if coax_scale is None else float(coax_scale)
    rd = 1.5 * scale_mm + 60.0
    rr = 1.5 * scale_mm
    out = {"coax": [(+1.0, wd_mm, cs * scale_mm)],
           "dome": [(+1.0, rd * math.cos(math.radians(DOME_RIM_DEG)), rd * math.sin(math.radians(DOME_RIM_DEG))),
                    (-1.0, rd * math.cos(math.radians(DOME_HOLE_DEG)), rd * math.sin(math.radians(DOME_HOLE_DEG)))],
           "fringe": [(+1.0, wd_mm, FRINGE_SCREEN_SCALE * scale_mm)]}
    for key, e in (("ring70", 70.0), ("ring30", 30.0), ("dark10", 10.0)):
        lo = rr * math.tan(math.radians(e - RING_HALF_DEG))
        hi = rr * math.tan(math.radians(e + RING_HALF_DEG))
        out[key] = [(+1.0, lo, rr), (-1.0, hi, rr)]
    return out


def p_inside(px, py, tx, ty, sig, h, R):
    """点 (px, py, 0) から出る光線の向き(tan 空間で N((tx, ty), sig² I))が、高さ h の円(半径 R)の内側を通る確率。

    光線 p + s·(t, 1) が高さ h で |p_xy + h t| ≤ R ⇔ |t − c| ≤ ρ、c = −p_xy/h、ρ = R/h。
    ガウスの中心からの距離が非心 χ²(自由度 2)になるので P = chndtr(ρ²/σ², 2, |t₀ − c|²/σ²)。
    """
    cx, cy = -px / h, -py / h
    rho = R / h
    s2 = np.maximum(sig, 1e-9) ** 2
    nc = ((tx - cx) ** 2 + (ty - cy) ** 2) / s2
    return special.chndtr(rho * rho / s2, 2.0, nc)


def specular_fraction(light, px, py, tx, ty, sig):
    """鏡面のローブ(tan 空間のガウス)が照明の光る領域に入る割合。"""
    out = 0.0
    for sgn, h, R in light:
        out = out + sgn * p_inside(px, py, tx, ty, sig, h, R)
    return np.clip(out, 0.0, 1.0)


def hit_directions(light, px, py, dirs):
    """点 (px, py, 0) から方向 *dirs* (N,3)(上向き)へ出た光線が照明に当たるか(0/1)。"""
    tz = np.maximum(dirs[:, 2], 1e-12)
    t = dirs[:, :2] / tz[:, None]
    out = np.zeros(len(dirs))
    for sgn, h, R in light:
        x = px + h * t[:, 0]
        y = py + h * t[:, 1]
        out += sgn * (x * x + y * y <= R * R)
    return np.clip(out, 0.0, 1.0)


def _fibonacci_hemisphere(n):
    i = np.arange(n) + 0.5
    z = 1.0 - i / n                                   # 天頂の余弦が等間隔 = 等面積
    r = np.sqrt(1.0 - z * z)
    ph = i * math.pi * (3.0 - math.sqrt(5.0))
    return np.stack([r * np.cos(ph), r * np.sin(ph), z], 1)


HEMI = _fibonacci_hemisphere(8192)
HEMI_W = 2.0 * math.pi / len(HEMI)
#: 拡散の照度を表にする法線の格子(勾配 gx, gy)
NG = np.linspace(-0.6, 0.6, 13)


def irradiance_table(light, px, py):
    """点 (px, py) で、法線の勾配の格子 (gx, gy) ごとの照度 E / L₀(半球の Fibonacci 積分)。"""
    hit = hit_directions(light, px, py, HEMI) * HEMI_W
    GX, GY = np.meshgrid(NG, NG, indexing="ij")
    n = np.stack([-GX.ravel(), -GY.ravel(), np.ones(GX.size)], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    return (np.clip(n @ HEMI.T, 0.0, None) @ hit).reshape(len(NG), len(NG))


def irradiance_at(table, gx, gy):
    """表を勾配で双一次補間(範囲の外は端に詰める)。"""
    step = NG[1] - NG[0]
    u = (np.clip(gx, NG[0], NG[-1]) - NG[0]) / step
    v = (np.clip(gy, NG[0], NG[-1]) - NG[0]) / step
    i = np.clip(np.floor(u).astype(int), 0, len(NG) - 2)
    j = np.clip(np.floor(v).astype(int), 0, len(NG) - 2)
    fu, fv = u - i, v - j
    return ((1 - fu) * (1 - fv) * table[i, j] + fu * (1 - fv) * table[i + 1, j]
            + (1 - fu) * fv * table[i, j + 1] + fu * fv * table[i + 1, j + 1])


def closed_form_irradiance(light):
    """原点の水平な面の照度 E / L₀ = π Σ 符号 · sin²(atan(R/h))(円の内側を通る方向 = 天頂角 atan(R/h) の円錐)。"""
    return sum(sgn * math.pi * math.sin(math.atan2(R, h)) ** 2 for sgn, h, R in light)


# =========================================================================== #
# 2. 反射: Fresnel と、鏡面のローブの中心
# =========================================================================== #
def fresnel_rs_rp(cos_i, n_complex):
    """Fresnel の反射率 (Rs, Rp)。*n_complex* は複素屈折率(誘電体なら実数)。"""
    ci = np.clip(np.asarray(cos_i, dtype=np.float64), 1e-9, 1.0)
    n = complex(n_complex)
    si2 = 1.0 - ci * ci
    ct = np.sqrt(n * n - si2 + 0j)
    rs = (ci - ct) / (ci + ct)
    rp = (n * n * ci - ct) / (n * n * ci + ct)
    return np.abs(rs) ** 2, np.abs(rp) ** 2


def reflect_tan(nx, ny, nz, vx, vy, vz):
    """視線 v(点 → カメラ)を法線 n で鏡映した向き r と、その tan 空間の座標、入射角の余弦、s 偏光の方位。"""
    d = nx * vx + ny * vy + nz * vz
    rx, ry, rz = 2 * d * nx - vx, 2 * d * ny - vy, 2 * d * nz - vz
    rz = np.maximum(rz, 1e-6)
    # s 偏光の向き = 入射面の法線 = r × v(像面へ射影した方位)
    sx = ry * vz - rz * vy
    sy = rz * vx - rx * vz
    phi = np.arctan2(sy, sx)
    return rx / rz, ry / rz, np.clip(d, 0.0, 1.0), phi


# =========================================================================== #
# 3. カメラ: 波長の鎖
# =========================================================================== #
WL = np.arange(400.0, 1701.0, 5.0)
E_VIS_W_M2 = 200.0       # 可視の照明: 白板の照度 200 W/m²(約 6 万 lx、E)
E_SWIR_W_M2 = 200.0      # SWIR の照明: ハロゲン、950〜1650 nm の照度も同じ 200 W/m²(帯域内の照度をそろえる、E)
T_REF_S = 1e-3
T_MAX_S = 10e-3
LENS_T = 0.9


def _on_grid(pairs, left=0.0, right=0.0):
    p = np.asarray(pairs, dtype=np.float64)
    return np.interp(WL, p[:, 0], p[:, 1], left=left, right=right)


def source_radiance(kind):
    """単位の照明(L₀)の分光放射輝度 [W m⁻² sr⁻¹ nm⁻¹]: 全天から L₀ が来ると白板の帯域内の照度が E になる。"""
    if kind == "vis":
        bb = _on_grid(SR.blackbody_spectrum(5000.0, 380.0, 1720.0, 669))
        cut = _on_grid(SR.bandpass_spectrum(540.0, 280.0, 1.0, 6, 0.0, 380.0, 1720.0, 669))   # IR カット 400〜680 nm
        s = bb * cut
        band = (WL >= 400.0) & (WL <= 700.0)
        E = E_VIS_W_M2
    else:
        s = _on_grid(SR.blackbody_spectrum(3000.0, 380.0, 1720.0, 669))
        band = (WL >= 950.0) & (WL <= 1650.0)
        E = E_SWIR_W_M2
    dl = np.gradient(WL)
    return s * E / (math.pi * float(np.sum(s[band] * dl[band])))


QE_SI = _on_grid(SR.silicon_photodiode_qe(3.0, 0.0, 0.04, 300.0, 1150.0, 171))
QE_INGAAS = _on_grid(SR.ingaas_photodiode_qe(1700.0, wl_min_nm=400.0, wl_max_nm=1700.0, n_points=261))
HSI_CENTERS = np.arange(950.0, 1651.0, 10.0)


def channel_weights(src, qe, filters, na, pixel_um, t_s=T_REF_S):
    """電子数 = Σ_λ w(λ)·(放射輝度率)の重み w [電子 / (L₀ の倍率)]。

    w = L_src(λ) · π NA² p² · t · T_lens · F(λ) · QE(λ) · λ/hc · Δλ —— 物体側の étendue で書いた形。
    """
    L = source_radiance(src)
    G = math.pi * na * na * (pixel_um * 1e-6) ** 2
    dl = np.gradient(WL)
    ph = WL * 1e-9 / (SR.PLANCK_H * SR.LIGHT_C)
    base = L * G * t_s * LENS_T * qe * ph * dl
    return np.stack([base * f for f in filters])


def bayer_filters():
    out = []
    for c, w in ((610.0, 90.0), (535.0, 90.0), (460.0, 90.0)):             # R, G, B
        out.append(_on_grid(SR.bandpass_spectrum(c, w, 0.9, 2, 0.02, 380.0, 1720.0, 669)))
    return out


#: カメラの表(地図の行)。k = 物体側の画素の、モノクロに対する倍率(同じ視野を写す画素数の比)。
CAMERAS = {
    "mono": {"name": "モノクロ", "src": "vis", "k": 1, "fw": 10500.0, "read": 2.5, "bits": 12},
    "color": {"name": "カラー", "src": "vis", "k": 1, "fw": 10500.0, "read": 2.5, "bits": 12},
    "polar": {"name": "偏光", "src": "vis", "k": 2, "fw": 10500.0, "read": 2.5, "bits": 12},
    "swir": {"name": "SWIR", "src": "swir", "k": 4, "fw": 40000.0, "read": 40.0, "bits": 14},
    "hsi": {"name": "ハイパースペクトル", "src": "swir", "k": 8, "fw": 40000.0, "read": 30.0, "bits": 14},
}
CAM_KEYS = tuple(CAMERAS)
POL_T_PAR, POL_T_PERP = 0.80, 0.008              # 画素上のワイヤグリッド(消光比 100)
LENS_KEYS = ("tele", "normal")
LENS_NAMES = {"tele": "テレセン", "normal": "通常"}


def camera_weights(cam, na, pixel_um):
    """カメラ *cam* のチャンネルごとの重み w (C, L)。偏光は強度の重み(偏光子は後で掛ける)。"""
    c = CAMERAS[cam]
    p = pixel_um * c["k"]
    if cam in ("mono", "polar"):
        return channel_weights("vis", QE_SI, [np.ones_like(WL)], na, p)
    if cam == "color":
        return channel_weights("vis", QE_SI, bayer_filters(), na, p)
    if cam == "swir":
        return channel_weights("swir", QE_INGAAS, [np.ones_like(WL)], na, p)
    sig = 10.0 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    filt = [np.exp(-0.5 * ((WL - cc) / sig) ** 2) for cc in HSI_CENTERS]
    return channel_weights("swir", QE_INGAAS, filt, na, p)


# =========================================================================== #
# 4. 材料の分光
# =========================================================================== #
def al_reflectance():
    """切削アルミの垂直反射率 R(λ)。Al の鏡面の表の値(Rakić 1995 の桁: 可視 0.92、830 nm の谷 0.87、SWIR 0.96)に、
    切削面の酸化膜と目の影響として 0.8 を掛けた(E)。"""
    pts = np.array([[400, .92], [600, .91], [750, .89], [830, .87], [900, .89], [1000, .93], [1300, .95], [1700, .96]])
    return 0.8 * np.interp(WL, pts[:, 0], pts[:, 1])


def paint_albedo():
    """濃色(ガンメタ系)の塗装の下地の拡散反射率。可視 0.05〜0.07、近赤外で有機顔料が透けて 0.35 へ(E)。"""
    pts = np.array([[400, .06], [500, .05], [600, .055], [700, .07], [800, .15], [950, .30], [1200, .35], [1700, .36]])
    return np.interp(WL, pts[:, 0], pts[:, 1])


ALPHA_VIS_PER_MM = 0.002     # 無着色の PP / PE の可視の吸収係数(ほぼ透明、E)。可視で両者を分ける値は表に無い。


def resin_k_s(material, carbon_black=0.0):
    """樹脂の K(λ) = 2α と S [1/mm](材料表の近赤外の吸収帯 + 可視の一定の小さな吸収 + カーボンブラック)。"""
    a = np.full(WL.shape, ALPHA_VIS_PER_MM)
    nir = MT.material_nir_absorption(material, 900.0, 1700.0, 161)
    a[WL >= 900.0] += np.interp(WL[WL >= 900.0], nir[:, 0], nir[:, 1])
    if carbon_black > 0:
        cb = MT.carbon_black_absorption(carbon_black, 400.0, 1700.0, 261)
        a += np.interp(WL, cb[:, 0], cb[:, 1])
    info = MT.nir_model_info(material)
    return 2.0 * a, float(info["scattering_per_mm"]), float(info["n_nir"])


def km(K, S, X, Rg):
    """Kubelka–Munk の 2 層(``spectralrad._km_reflectance``、X = None で無限厚)。"""
    return SR._km_reflectance(K, S, X, Rg)


def saunderson(r_km, n, ri=0.6):
    """界面の補正(Saunderson 1942)から**鏡面反射を除いた**体の拡散分(鏡面はレンダラが幾何で足す)。"""
    rs = ((n - 1.0) / (n + 1.0)) ** 2
    return (1.0 - rs) * (1.0 - ri) * r_km / (1.0 - ri * r_km)


DEPTH_MM = 0.25


def resin_spectra():
    """S3 の分光: PP の地、黒い焼けの上(PP 0.25 mm の下)、PE の破片の上。"""
    Kp, Sp, n = resin_k_s("PP")
    r_pp = km(Kp, Sp, None, 0.0)
    Kb, Sb, _ = resin_k_s("PP", carbon_black=0.02)
    r_black = km(Kb, Sb, None, 0.0)
    Ke, Se, _ = resin_k_s("PE")
    r_pe = km(Ke, Se, None, 0.0)
    return {"pp": saunderson(r_pp, n),
            "black": saunderson(km(Kp, Sp, DEPTH_MM, r_black), n),
            "pe": saunderson(km(Kp, Sp, DEPTH_MM, r_pe), n),
            "S": Sp, "n": n}


RESIN = resin_spectra()


# =========================================================================== #
# 5. 題材と、部位の描画
# =========================================================================== #
#: 題材の表。px = モノクロの物体側の画素 [µm]、fov = 視野の幅 [mm]、wd = 作動距離 [mm]、na = 物体側の NA。
SUBJECTS = {
    "S1": {"name": "切削アルミの線傷", "unit": "幅", "px": 16.0, "fov": 40.0, "wd": 200.0, "na": 0.02,
           "nx": 48, "ny": 16, "ss": 2, "size": (2.0, 200.0)},
    "S2": {"name": "塗装パネルの浅い凹み", "unit": "深さ", "px": 80.0, "fov": 196.0, "wd": 600.0, "na": 0.015,
           "nx": 48, "ny": 48, "ss": 1, "size": (0.5, 300.0)},
    "S3a": {"name": "樹脂の中の黒い焼け", "unit": "径", "px": 40.0, "fov": 98.0, "wd": 400.0, "na": 0.02,
            "nx": 32, "ny": 32, "ss": 1, "size": (15.0, 1500.0)},
    "S3b": {"name": "樹脂の中の PE 片", "unit": "径", "px": 40.0, "fov": 98.0, "wd": 400.0, "na": 0.02,
            "nx": 32, "ny": 32, "ss": 1, "size": (60.0, 6000.0)},
}
SUBJ_KEYS = tuple(SUBJECTS)
SLOPE_DEG, SLOPE_SD = 10.0, 1.5                  # 線傷の斜面
FACET_DEG = {"S1": 1.5, "S1_flank": 6.0, "S2": 0.3, "S3": 3.0}   # 微小面の傾きの広がり(1σ、E)
#: 線傷の斜面のうち、むしれ・バリで微小面があらゆる向きを向く割合(E)。そこでは鏡面の Fresnel 分が拡散に回る
#: (``illumdesign._radiance`` の rough と同じ扱い: 反射率 F + (1 − F)ρ の Lambert 面)—— 暗視野が傷を光らせる仕組み。
FLANK_ROUGH = 0.3
#: 地の面(切削目)のむしれの割合の平均と、その斑(対数正規、E)。暗視野で切削目が光る分。
SURF_ROUGH, SURF_ROUGH_SPREAD = 0.04, 0.8
DENT_SIGMA_MM = 1.6
#: 塗装のゆず肌の傾きの RMS [deg](E)。章 5 でこれを 1/5 にして、凹みの検出の床かどうかを確かめる。
PEEL_DEG = 0.10
#: 縞照明の縞の周期は、面のローブのぼけ(画面の上で h σ)で縞の振幅が exp(−2π²/16) = 0.29 残る p = 4 h σ に選ぶ。
FRINGE_BLUR_RATIO = 0.25


def _smooth_field(rng, shape, cell):
    g = rng.standard_normal((max(shape[0] // cell, 2) + 3, max(shape[1] // cell, 2) + 3))
    z = ndimage.zoom(g, (shape[0] / (g.shape[0] - 3), shape[1] / (g.shape[1] - 3)), order=3)
    return z[:shape[0], :shape[1]]


def _hairline_field(rng, shape, step_mm):
    """ヘアライン(研磨の筋)の高さの勾配 (gx, gy) と、むしれの筋の強さ z(平均 0・分散 1)。

    細い筋がたくさん並び、筋ごとに少しずつ蛇行しながら走る: 白色雑音を y に長く(相関 0.6 mm)・x に細く
    (相関 12 µm)ぼかし、横ずれの場(振幅 30 µm、y に相関 1 mm・x に相関 40 µm)で横へずらす。筋の濃さにも
    ゆるい斑を掛ける。傾きの RMS は 2°(``poc_pod_lighting`` の正弦の和と同じ大きさ)。正弦の和だと全高を
    真っ直ぐ走る数本の縞になり、実物の研磨痕に見えなかった(レビューの指摘、2026-11-08)。
    """
    ny, nx = shape
    pad = 16
    z = rng.standard_normal((ny + 2 * pad, nx + 2 * pad))
    z = ndimage.gaussian_filter(z, (0.6 / step_mm, max(0.6, 0.012 / step_mm)), mode="wrap")
    yy = np.arange(ny + 2 * pad, dtype=np.float64)[:, None] * np.ones((1, nx + 2 * pad))
    xx = np.ones((ny + 2 * pad, 1)) * np.arange(nx + 2 * pad, dtype=np.float64)[None, :]
    # 横ずれの場は y にゆっくり(相関 1 mm)、x にも筋の間隔ほど(相関 40 µm)で変える —— 筋ごとに別の曲がり方になる。
    # (初版の作り直しでは横ずれが y だけの関数で、全部の筋が一斉に同じ S 字に曲がった。再レビューの指摘)
    sh = ndimage.gaussian_filter(rng.standard_normal(yy.shape), (1.0 / step_mm, max(0.6, 0.04 / step_mm)), mode="wrap")
    sh *= (0.03 / step_mm) / max(float(np.std(sh)), 1e-12)
    z = ndimage.map_coordinates(z, [yy, xx + sh], order=1, mode="wrap")
    z *= 1.0 + 0.5 * ndimage.gaussian_filter(rng.standard_normal(z.shape), 1.0 / step_mm, mode="wrap") \
        / max(float(np.std(ndimage.gaussian_filter(rng.standard_normal(z.shape), 1.0 / step_mm, mode="wrap"))), 1e-12)
    z = z[pad:-pad, pad:-pad]
    gy, gx = np.gradient(z, step_mm)
    k = math.tan(math.radians(2.0)) / max(float(np.std(np.hypot(gx, gy))), 1e-12)
    r = z / max(float(z.std()), 1e-12)
    return gx * k, gy * k, r


def _view(lens, X, Y, wd):
    """点 → カメラの単位ベクトルと、周辺光量の cos⁴。テレセンは光軸に平行、通常は作動距離のピンホールへ。"""
    if lens == "tele":
        o = np.zeros_like(X)
        return o, o, np.ones_like(X), np.ones_like(X)
    vx, vy, vz = -X, -Y, np.full_like(X, wd)
    nn = np.sqrt(vx * vx + vy * vy + vz * vz)
    vz = vz / nn
    return vx / nn, vy / nn, vz, vz ** 4


def _lobe_sigma(facet_deg, na):
    """鏡映した光線の広がり(tan 空間の 1σ): 微小面の傾き σ_f は光線を 2σ_f 振り、開口(半角 β の一様な円)は β/2。"""
    return math.hypot(2.0 * math.tan(math.radians(facet_deg)), math.asin(na) / 2.0)


def fringe_period(key):
    """題材 *key* の縞の周期 [mm](画面の上)。"""
    cfg = SUBJECTS[key]
    sig = _lobe_sigma(FACET_DEG["S3" if key.startswith("S3") else key], cfg["na"])
    return cfg["wd"] * sig / FRINGE_BLUR_RATIO


class SiteSet:
    """同じ題材の部位の集まり。sizes > 0 が欠陥、0 が無欠陥。視野の中の位置は一様に散らす。"""

    def __init__(self, key, n_flaw, n_clean, seed):
        self.key = key
        cfg = SUBJECTS[key]
        rng = np.random.default_rng(seed)
        lo, hi = cfg["size"]
        self.sizes = np.r_[np.exp(rng.uniform(math.log(lo), math.log(hi), n_flaw)), np.zeros(n_clean)]
        self.n = self.sizes.size
        self.n_flaw = n_flaw
        half = cfg["fov"] / 2.0
        self.fx = rng.uniform(-half, half, self.n)          # 視野の中の位置 [mm]
        self.fy = rng.uniform(-0.8 * half, 0.8 * half, self.n)
        self.seeds = rng.integers(1 << 62, size=self.n)
        self.jit = rng.uniform(-0.5, 0.5, self.n)           # 欠陥の中心の画素内の位置
        self.slopes = rng.normal(SLOPE_DEG, SLOPE_SD, self.n)


def _footprint(nx, ny, px, d_mm, jit):
    """樹脂の中の異物の足あと: 径 d の円板(4x4 の副標本で面積を配る)を、深さと平均自由行程のぼけで広げる。"""
    if d_mm <= 0:
        return np.zeros((ny, nx))
    c4 = (np.arange(nx * 4) + 0.5) / 4 * px - nx * px / 2 - jit * px
    r4 = (np.arange(ny * 4) + 0.5) / 4 * px - ny * px / 2
    y4, x4 = np.meshgrid(r4, c4, indexing="ij")
    sub = (np.hypot(x4, y4) <= d_mm / 2).astype(np.float64)
    frac = sub.reshape(ny, 4, nx, 4).mean(axis=(1, 3))
    return ndimage.gaussian_filter(frac, math.hypot(DEPTH_MM, 1.0 / RESIN["S"]) / px, mode="constant")


_IRR_CACHE: dict = {}
_TEX_CACHE: dict = {}
BASIS_NAMES = ("D", "Sw", "Sb", "Q", "U", "Dm", "Cxw", "Cxb", "Cyw", "Cyb", "Kxw", "Kxb", "Kyw", "Kyb")
#: 粗い縞の周期 / 細かい縞の周期。細かい縞は感度が高いぶん、凹みの斜面で位相が π を越えて巻き込む —— 粗い縞で
#: 次数を決めて(``fringe.absolute_phase``、既存の poc_phase_measuring_deflectometry と同じ 2 周波)巻き込みを解く。
FRINGE_COARSE = 16.0


def render_bases(sites, light_key, lens, lights, coax_tag=""):
    """部位ごとの**基底の地図**(モノクロの画素の格子)。

    電子数はカメラのチャンネル c ごとに ``Σ 基底 × 係数_c`` で組む(材料の分光とカメラの重みは後で掛ける)。
    名前: ``D``(拡散の照度 E/πL₀)、``Sw``(鏡面のうち波長に平坦な分)、``Sb``(金属の f0 に掛かる分)、
    ``Q``・``U``(鏡面の直線偏光、Stokes の比)、``Dm``(むしれた面の Lambert 分、金属の反射率が掛かる)、
    ``Cxw``・``Cxb``・``Cyw``・``Cyb``(縞照明だけ: 鏡面の縞の複素振幅 = 鏡面の係数 × 振幅の残り × e^{i2πu/p}。
    x と y の縞、平坦な分と f0 の分)、``Kxw``…(同じく粗い縞、周期 16 p)、``frac``(欠陥の占める割合)。
    """
    cfg = SUBJECTS[sites.key]
    key = sites.key
    light = lights[light_key]
    fr = light_key == "fringe"
    nx, ny, ss = cfg["nx"], cfg["ny"], cfg["ss"]
    px = cfg["px"] / 1000.0
    na = cfg["na"]
    out = {k: np.zeros((sites.n, ny, nx), dtype=np.complex128 if k[0] in "CK" else np.float64)
           for k in BASIS_NAMES if fr or k[0] not in "CK"}
    out["frac"] = np.zeros((sites.n, ny, nx))
    cs = (np.arange(nx * ss) + 0.5) / ss * px - nx * px / 2
    rs = (np.arange(ny * ss) + 0.5) / ss * px - ny * px / 2
    yy, xx = np.meshgrid(rs, cs, indexing="ij")
    pc = (np.arange(nx) + 0.5) * px - nx * px / 2
    pr = (np.arange(ny) + 0.5) * px - ny * px / 2
    YY, XX = np.meshgrid(pr, pc, indexing="ij")
    metal = key == "S1"
    n_c = complex(0.96, 6.69) if metal else (RESIN["n"] if key.startswith("S3") else 1.5)
    sig_s = _lobe_sigma(FACET_DEG["S3" if key.startswith("S3") else key], na)
    sig_f = _lobe_sigma(FACET_DEG["S1_flank"], na)
    p_fr = fringe_period(key)
    h_fr = light[0][1]
    for i in range(sites.n):
        r = np.random.default_rng(sites.seeds[i])
        fx, fy = sites.fx[i], sites.fy[i]
        step = cfg["fov"] / 8.0
        cell = (key, light_key, coax_tag, round(fx / step), round(fy / step))   # 照度の表は視野の 1/8 ごと
        if cell not in _IRR_CACHE:
            _IRR_CACHE[cell] = irradiance_table(light, cell[3] * step, cell[4] * step)
        tab = _IRR_CACHE[cell]

        def shade(gx, gy, X, Y, sig, rough=0.0):
            n = np.stack([-gx, -gy, np.ones_like(gx)], 0)
            n /= np.linalg.norm(n, axis=0, keepdims=True)
            vx, vy, vz, vig = _view(lens, X + fx, Y + fy, cfg["wd"])
            tx, ty, ci, phi = reflect_tan(n[0], n[1], n[2], vx, vy, vz)
            P = specular_fraction(light, X + fx, Y + fy, tx, ty, sig)
            E = irradiance_at(tab, gx, gy) / math.pi
            Rs, Rp = fresnel_rs_rp(ci, n_c)
            if metal:
                c5 = (1.0 - ci) ** 5
                sw, sb = P * c5, P * (1.0 - c5)
            else:
                sw, sb = P * 0.5 * (Rs + Rp), np.zeros_like(P)
            q = P * 0.5 * (Rs - Rp) * np.cos(2 * phi)
            u = P * 0.5 * (Rs - Rp) * np.sin(2 * phi)
            dm = np.zeros_like(E)
            if np.any(np.asarray(rough) > 0):
                # むしれた部分: 鏡面の代わりに Fresnel 分(金属の反射率)を Lambert で返す
                sw, sb, q, u = sw * (1 - rough), sb * (1 - rough), q * (1 - rough), u * (1 - rough)
                dm = rough * E
            vals = {"D": E, "Sw": sw, "Sb": sb, "Q": q, "U": u, "Dm": dm}
            if fr:
                # 画面は明るさの平均 0.5 の縞: 平均の分は 0.5 倍、縞の分は ローブで均した振幅 × 位相の複素数
                att = np.exp(-2.0 * np.pi ** 2 * (h_fr * sig / p_fr) ** 2)
                cx = att * np.exp(2j * np.pi * (X + fx + h_fr * tx) / p_fr)
                cy = att * np.exp(2j * np.pi * (Y + fy + h_fr * ty) / p_fr)
                pc_ = FRINGE_COARSE * p_fr
                ac = np.exp(-2.0 * np.pi ** 2 * (h_fr * sig / pc_) ** 2)
                kx = ac * np.exp(2j * np.pi * (X + fx + h_fr * tx) / pc_)
                ky = ac * np.exp(2j * np.pi * (Y + fy + h_fr * ty) / pc_)
                vals = {"D": 0.5 * E, "Sw": 0.5 * sw, "Sb": 0.5 * sb, "Q": 0.0 * q, "U": 0.0 * u, "Dm": 0.5 * dm,
                        "Cxw": 0.5 * sw * cx, "Cxb": 0.5 * sb * cx, "Cyw": 0.5 * sw * cy, "Cyb": 0.5 * sb * cy,
                        "Kxw": 0.5 * sw * kx, "Kxb": 0.5 * sb * kx, "Kyw": 0.5 * sw * ky, "Kyb": 0.5 * sb * ky}
            return {k: v * vig for k, v in vals.items()}

        def down(a):
            return a.reshape(ny, ss, nx, ss).mean(axis=(1, 3)) if ss > 1 else a

        if key == "S1":
            # ヘアラインは線傷と**平行**(y に沿う筋): 研磨の向きに沿った傷がいちばん見つけにくい(列の平均で筋が消えない)
            tk = (sites.seeds[i], xx.shape)                      # 面の目は照明・レンズに依らない: 部位ごとに 1 回作る
            if tk not in _TEX_CACHE:
                _TEX_CACHE[tk] = _hairline_field(r, xx.shape, px / ss)
            gx, gy, zr = _TEX_CACHE[tk]
            rough = np.clip(SURF_ROUGH * np.exp(SURF_ROUGH_SPREAD * zr - SURF_ROUGH_SPREAD ** 2 / 2), 0.0, 0.5)
            surf = {k: down(v) for k, v in shade(gx, gy, xx, yy, sig_s, rough).items()}
            w = sites.sizes[i] / 1000.0
            x0 = sites.jit[i] * px
            xl, xr = pc - px / 2, pc + px / 2
            fl = np.clip(np.minimum(xr, x0) - np.maximum(xl, x0 - w / 2), 0, None) / px
            frr = np.clip(np.minimum(xr, x0 + w / 2) - np.maximum(xl, x0), 0, None) / px
            fl, frr = np.broadcast_to(fl, (ny, nx)), np.broadcast_to(frr, (ny, nx))
            if w > 0:
                g2x, g2y = down(gx), down(gy)
                t = math.tan(math.radians(sites.slopes[i]))
                left = shade(g2x - t, g2y, XX, YY, sig_f, FLANK_ROUGH)        # 左の斜面は +x を向く
                right = shade(g2x + t, g2y, XX, YY, sig_f, FLANK_ROUGH)
            else:
                left = right = surf
            vals = {k: (1 - fl - frr) * surf[k] + fl * left[k] + frr * right[k] for k in surf}
            out["frac"][i] = fl + frr
        elif key == "S2":
            # ゆず肌: 波長 2〜4 mm、傾きの RMS PEEL_DEG のうねり(E)+ ガウス形の凹み
            h = _smooth_field(r, (ny, nx), 3) + 0.6 * _smooth_field(r, (ny, nx), 6)
            gy0, gx0 = np.gradient(h, px)
            k = math.tan(math.radians(PEEL_DEG)) / max(float(np.std(np.hypot(gx0, gy0))), 1e-12)
            gx0, gy0 = gx0 * k, gy0 * k
            d = sites.sizes[i] / 1000.0
            s2 = DENT_SIGMA_MM ** 2
            xc, yc = XX - sites.jit[i] * px, YY
            bump = np.exp(-(xc ** 2 + yc ** 2) / (2 * s2))
            gx = gx0 + d * bump * xc / s2                          # 高さ −d·bump の勾配
            gy = gy0 + d * bump * yc / s2
            vals = shade(gx, gy, XX, YY, sig_s)
            out["frac"][i] = bump if d > 0 else 0.0
        else:
            h = _smooth_field(r, (ny, nx), 2)
            gy0, gx0 = np.gradient(h, px)
            k = math.tan(math.radians(0.5)) / max(float(np.std(np.hypot(gx0, gy0))), 1e-12)
            vals = shade(gx0 * k, gy0 * k, XX, YY, sig_s)
            out["frac"][i] = _footprint(nx, ny, px, sites.sizes[i] / 1000.0, sites.jit[i])
        for name in out:
            if name != "frac":
                out[name][i] = vals[name]
    return out


# =========================================================================== #
# 6. 撮像(雑音つき)と検査時間
# =========================================================================== #
#: ★この PoC は露光の上限(視野 1 枚 10 ms)をそろえただけで、光子の数はそろえていない(地が早く満ちるマスは上限を使い
#: 切らず、同じ時間に何コマも足して雑音を下げることはしていない)。露光の上限は視野 1 枚あたりで、面のカメラは 1 コマの露光をこの値
#: まで、縞照明は 16 コマで分け、ラインスキャンの分光は視野を 1 ラインずつ送るので 1 ラインの上限は これ / ライン数。10 ms で視野を送るラインスキャンの分光は数十 kHz のライン速度になり、実機(数百 Hz)では届かない
#: —— 章 5 で上限を 100 ms・1 s に変えた表も出す。
TAKT_S = 10e-3
FRINGE_STEPS = 4


def material_coefs(key, W):
    """基底に掛ける係数(チャンネルごと): 拡散は Σ w ρ、鏡面は Σ w(と Σ w f0)。"""
    Wsum = W.sum(axis=1)
    if key == "S1":
        al = W @ al_reflectance()
        return {"D": W @ np.full(WL.shape, 0.03), "Sw": Wsum, "Sb": al, "Dm": al}
    if key == "S2":
        return {"D": W @ paint_albedo(), "Sw": Wsum, "Sb": np.zeros(len(W))}
    return {"D": W @ RESIN["pp"], "Dx": W @ RESIN["pe" if key == "S3b" else "black"], "Sw": Wsum,
            "Sb": np.zeros(len(W))}


def clean_electrons(bases, key, cam, W, frame=None):
    """雑音前の電子数(露光 T_REF)。戻り (n, ny, nx, C)。偏光は 4 方位の強度。

    *frame* = ``("x" | "y", δ, "C" | "K")`` は縞照明の 1 コマ(画面の明るさ 0.5(1 + cos(2πu/p − δ))、C = 細かい縞、
    K = 粗い縞)。
    """
    co = material_coefs(key, W)
    if key.startswith("S3"):
        f = bases["frac"][..., None]
        diff = bases["D"][..., None] * ((1 - f) * co["D"] + f * co["Dx"])
    else:
        diff = bases["D"][..., None] * co["D"]
    e = diff + bases["Sw"][..., None] * co["Sw"] + bases["Sb"][..., None] * co["Sb"]
    if "Dm" in co:
        e = e + bases["Dm"][..., None] * co["Dm"]
    if frame is not None:
        d, delta, lv = frame
        ph = np.exp(-1j * delta)
        e = e + np.real(ph * (bases["%s%sw" % (lv, d)][..., None] * co["Sw"]
                              + bases["%s%sb" % (lv, d)][..., None] * co["Sb"]))
    if cam != "polar":
        return e
    # 偏光: 4 方位 θ の透過 = T̄·S0 + ΔT·(Q cos2θ + U sin2θ)
    tb, dt = 0.5 * (POL_T_PAR + POL_T_PERP), 0.5 * (POL_T_PAR - POL_T_PERP)
    s0 = e[..., 0]
    q = bases["Q"] * co["Sw"][0]
    u = bases["U"] * co["Sw"][0]
    return np.stack([tb * s0 + dt * (q * math.cos(2 * a) + u * math.sin(2 * a))
                     for a in np.radians([0.0, 45.0, 90.0, 135.0])], -1)


def sample_camera(e, cam):
    """モノクロの格子の電子数 → カメラの画素の格子(Bayer はモザイク、偏光は 2x2 の超画素、SWIR/HSI は k x k)。"""
    k = CAMERAS[cam]["k"]
    n, ny, nx, C = e.shape
    if cam == "color":
        mosaic = np.zeros((n, ny, nx))
        mosaic[:, 0::2, 0::2] = e[:, 0::2, 0::2, 0]          # R
        mosaic[:, 0::2, 1::2] = e[:, 0::2, 1::2, 1]          # G
        mosaic[:, 1::2, 0::2] = e[:, 1::2, 0::2, 1]          # G
        mosaic[:, 1::2, 1::2] = e[:, 1::2, 1::2, 2]          # B
        return mosaic
    if cam == "polar":
        sup = np.zeros((n, ny // 2, nx // 2, 4))
        for j, (dy, dx) in enumerate(((0, 0), (0, 1), (1, 1), (1, 0))):     # 0°, 45°, 90°, 135°
            sup[..., j] = e[:, dy::2, dx::2, j]
        return sup
    if k == 1:
        return e
    # 物体側で k 倍の画素は面積で積分する。重み W は k 倍の画素で作ってあるので、ここは平均。
    return e.reshape(n, ny // k, k, nx // k, k, C).mean(axis=(2, 4))


def demosaic(mos):
    """Bayer の双一次の補間(正規化畳み込み)。"""
    n, ny, nx = mos.shape
    masks = np.zeros((3, ny, nx))
    masks[0, 0::2, 0::2] = 1
    masks[1, 0::2, 1::2] = 1
    masks[1, 1::2, 0::2] = 1
    masks[2, 1::2, 1::2] = 1
    ker = np.array([[0.25, 0.5, 0.25], [0.5, 1.0, 0.5], [0.25, 0.5, 0.25]])
    out = np.zeros((n, ny, nx, 3))
    for c in range(3):
        num = ndimage.convolve(mos * masks[c][None], ker[None], mode="mirror")
        den = ndimage.convolve(np.broadcast_to(masks[c], mos.shape).astype(np.float64), ker[None], mode="mirror")
        out[..., c] = num / den
    return out


def capture(e_ref, cam, t_s, seed):
    """露光 t で撮る: Poisson(電子) + 読み出し + 飽和 + ADC。戻り: 電子数に戻した浮動小数(カメラの格子、(n,h,w,C))。"""
    c = CAMERAS[cam]
    rng = np.random.default_rng(seed)
    lam = np.clip(e_ref * (t_s / T_REF_S), 0.0, None)
    x = rng.poisson(lam).astype(np.float64) + rng.normal(0.0, c["read"], lam.shape)
    g = c["fw"] / (2 ** c["bits"] - 1)
    x = np.clip(np.round(x / g), 0, 2 ** c["bits"] - 1) * g
    if cam == "color":
        x = demosaic(x)
    if x.ndim == 3:
        x = x[..., None]
    return x


def capture_sum(e_ref, cam, t_s, seed):
    """縞照明の位相に使う強度: チャンネルを足した電子数を 1 回で撮る(チャンネルごとに撮って足すのと分布が同じ:
    独立な Poisson の和は和の Poisson、読み出し雑音の分散は C 倍)。露光は各チャンネルが満杯の 70 % を越えない値で、
    飽和は起きない。Bayer はモザイクのまま(1 画素 1 色の生の値で位相を読む)。偏光は 4 方位の画素の和。"""
    c = CAMERAS[cam]
    rng = np.random.default_rng(seed)
    e = e_ref if e_ref.ndim == 3 else e_ref.sum(-1)
    nch = 1 if e_ref.ndim == 3 else e_ref.shape[-1]
    if cam == "hsi":
        nch = len(HSI_CENTERS)                 # 帯を足した重みで作った 1 本でも、読み出しは 71 帯ぶん
    lam = np.clip(e * (t_s / T_REF_S), 0.0, None)
    return rng.poisson(lam).astype(np.float64) + rng.normal(0.0, c["read"] * math.sqrt(nch), lam.shape)


def exposure_cap(key, cam, n_frames, mode="takt"):
    """1 コマの露光の上限 [s]。mode = "takt": 視野 1 枚の上限 TAKT_S をコマ数で割る(ラインスキャンの分光はさらに
    ライン数で割る)。mode = "fullwell": 1 コマ 10 ms まで待てる(井戸が満ちるまで露光する比べ方)。"""
    if mode == "fullwell":
        return T_MAX_S
    cap = TAKT_S / n_frames
    if cam == "hsi":
        cfg = SUBJECTS[key]
        cap /= cfg["fov"] / (cfg["px"] * CAMERAS[cam]["k"] / 1000.0)
    return cap


def exposure_for(e_cam, cam, clean, cap):
    """無欠陥の部位の 99.9 % 点が満杯の 70 % になる露光(上限 *cap*)。戻り (t, 上限に当たったか)。"""
    q = float(np.percentile(e_cam[clean], 99.9))
    if q <= 0:
        return cap, True
    t = T_REF_S * 0.7 * CAMERAS[cam]["fw"] / q
    return min(t, cap), t >= cap


def _wrapped_residual(phi):
    """巻き込み位相 (n, h, w) から、部位ごとの円の平均を引いた残り(−π〜π)。"""
    z = np.exp(1j * phi)
    ref = np.sum(z, axis=(1, 2))
    return np.angle(z * np.conj(ref / np.maximum(np.abs(ref), 1e-30))[:, None, None])


def _phase_residual(r0):
    """次数を決めた位相の残り (n, h, w) から、平面(縞の傾き)を最小二乗で外した残り [rad]。"""
    n, h, w = r0.shape
    yy, xx = np.mgrid[0:h, 0:w]
    A = np.stack([np.ones(h * w), (xx.ravel() - w / 2) / w, (yy.ravel() - h / 2) / h], 1)
    coef = np.linalg.lstsq(A, r0.reshape(n, -1).T, rcond=None)[0]
    return r0 - (A @ coef).T.reshape(n, h, w)


def measure_sites(btr, bte, key, cam, light_key, W, seed, mode="takt", clean_tr=None):
    """学習と試験の部位を撮って、判定の入力(チャンネルの残差)を返す。

    縞照明は細かい縞と粗い縞を x と y に 4 位相ずつ(16 コマ)撮り、チャンネルを足した強度から
    ``fringe.wrapped_phase``(repo の op)で巻き込み位相を出し、粗い縞で次数を決め(``fringe.absolute_phase``)、
    位相の残差 2 枚(x, y)をチャンネルにする。戻り (res_tr, res_te, t, capped, e_tr)。
    """
    if light_key != "fringe":
        etr = sample_camera(clean_electrons(btr, key, cam, W), cam)
        ete = sample_camera(clean_electrons(bte, key, cam, W), cam)
        t, capped = exposure_for(etr, cam, clean_tr, exposure_cap(key, cam, 1, mode))
        xtr = capture(etr, cam, t, seed)
        xte = capture(ete, cam, t, seed + 50000)
        return residuals(xtr, key), residuals(xte, key), t, capped, etr
    deltas = 2 * np.pi * np.arange(FRINGE_STEPS) / FRINGE_STEPS
    frames = [(d, dl, lv) for lv in ("C", "K") for d in ("x", "y") for dl in deltas]
    Wf = W
    if cam == "hsi":
        # 位相は帯を足した強度で読むので、16 コマは帯を足した重み 1 本で作る(71 帯 × 16 コマを持たない)。露光は
        # 帯ごとの電子数で決める: 平均の像と最初のコマを帯ごとに作り、その 99.9 % 点(各帯が満杯の 70 % を越えない)。
        Wf = W.sum(axis=0, keepdims=True)
        probe = [sample_camera(clean_electrons(btr, key, cam, W, f), cam) for f in (None, frames[0])]
        q = float(max(np.percentile(s[clean_tr], 99.9) for s in probe))
    etr_f = [sample_camera(clean_electrons(btr, key, cam, Wf, f), cam) for f in frames]
    ete_f = [sample_camera(clean_electrons(bte, key, cam, Wf, f), cam) for f in frames]
    stack = np.stack(etr_f)
    if cam != "hsi":
        q = float(max(np.percentile(s[clean_tr], 99.9) for s in stack))
    cap = exposure_cap(key, cam, len(frames), mode)
    t_fill = T_REF_S * 0.7 * CAMERAS[cam]["fw"] / max(q, 1e-30)
    t, capped = min(t_fill, cap), t_fill >= cap
    out = []
    for j, ef in enumerate((etr_f, ete_f)):
        ims = [capture_sum(e, cam, t, seed + 50000 * j + 7 * m) for m, e in enumerate(ef)]
        chans = []
        nst = FRINGE_STEPS
        for d in range(2):
            fine = np.stack(ims[nst * d:nst * d + nst])                         # (4, n, h, w) 細かい縞
            coarse = np.stack(ims[nst * (2 + d):nst * (2 + d) + nst])           # 粗い縞
            n, h, w = fine.shape[1:]
            wf = _wrapped_residual(fringe.wrapped_phase(fine.reshape(nst, n * h, w)).reshape(n, h, w))
            wc = _wrapped_residual(fringe.wrapped_phase(coarse.reshape(nst, n * h, w)).reshape(n, h, w))
            ab = fringe.absolute_phase(wf.reshape(n * h, w), (FRINGE_COARSE * wc).reshape(n * h, w)).reshape(n, h, w)
            chans.append(_phase_residual(ab))
        out.append(residuals(np.stack(chans, -1), key))
    return out[0], out[1], t, capped, stack.mean(0)


# =========================================================================== #
# 7. 判定: チャンネルの重み → 空間の検出器 → â
# =========================================================================== #
S1_CENTRAL_PX, S1_GUARD_PX = 8, 12


def _central_cols(w, side=False):
    """線傷が乗りうる列(モノクロの中央 ±8 画素に重なるカメラの列)と、地に使う列(中央 ±12 画素の外だけ)。"""
    nx = SUBJECTS["S1"]["nx"]
    k = nx // w
    lo, hi = np.arange(w) * k, (np.arange(w) + 1) * k            # カメラの列が覆うモノクロの列 [lo, hi)
    if side:
        return np.flatnonzero((hi <= nx // 2 - S1_GUARD_PX) | (lo >= nx // 2 + S1_GUARD_PX))
    return np.flatnonzero((hi > nx // 2 - S1_CENTRAL_PX) & (lo < nx // 2 + S1_CENTRAL_PX))


def residuals(img, key):
    """部位ごとに地を引いた残差。S1 は列の平均の残差 (n, w, C)、ほかは画素 (n, h, w, C)。"""
    if key == "S1":
        col = img.mean(axis=1)
        side = _central_cols(col.shape[1], side=True)
        return col - np.median(col[:, side], axis=1)[:, None]
    n, h, w, C = img.shape
    b = max(1, min(h, w) // 8)
    ring = np.ones((h, w), bool)
    ring[b:-b, b:-b] = False
    return img - np.median(img[:, ring], axis=1)[:, None, None]


def _disk_radius_px(key, w):
    """空間の検出器の円の半径(カメラの画素)。"""
    cfg = SUBJECTS[key]
    if key == "S2":
        return 1.5 * DENT_SIGMA_MM * 1000.0 / cfg["px"] * w / cfg["nx"]
    return max(1.0, 1.5 * math.hypot(DEPTH_MM, 1.0 / RESIN["S"]) * 1000.0 / cfg["px"] * w / cfg["nx"])


def _units(res, key, flaw):
    """一般化固有値の学習に使う「欠陥の単位」と「無欠陥の単位」(チャンネルのベクトルの集まり)。"""
    C = res.shape[-1]
    if key == "S1":
        return (res[flaw][:, _central_cols(res.shape[1])].reshape(-1, C),
                res[~flaw][:, _central_cols(res.shape[1])].reshape(-1, C))
    n, h, w, _ = res.shape
    yy, xx = np.mgrid[0:h, 0:w]
    disk = np.hypot(yy - (h - 1) / 2, xx - (w - 1) / 2) <= _disk_radius_px(key, w)
    return res[flaw][:, disk].reshape(-1, C), res[~flaw].reshape(-1, C)


SHRINK = 0.2


def channel_weight(res, key, flaw):
    """欠陥の単位の散らばり Sd と無欠陥の共分散 S0 の一般化固有値問題 Sd w = λ S0 w の最大の w(wᵀ S0 w = 1)。"""
    from scipy.linalg import eigh
    d, c = _units(res, key, flaw)
    C = res.shape[-1]
    mu = c.mean(axis=0)
    S0 = np.atleast_2d(np.cov((c - mu).T))
    # 縮小(Ledoit–Wolf の形の固定比 SHRINK): 帯の数が学習の単位に比べて多いと、雑音の向きに合わせた重みになる
    S0 = (1 - SHRINK) * S0 + SHRINK * np.eye(C) * max(float(np.trace(S0)) / C, 1e-30)
    if C == 1:
        return np.array([1.0 / math.sqrt(float(S0[0, 0]))])
    Sd = (d - mu).T @ (d - mu) / max(len(d), 1)
    _vals, vecs = eigh(Sd, S0)
    w = vecs[:, -1]
    return w / math.sqrt(float(w @ S0 @ w))


def ahat_of(res, key, w):
    """â(雑音の σ の単位): 重みで 1 チャンネルにして、題材ごとの空間の検出器を通す。"""
    y = res @ w
    if key == "S1":
        # 幅の分からない縦の帯への整合フィルタの束: 連続する L 列の和 / √L の最大(L = 1, 2, 4, …)。
        # 1 列の最大だと、平行なヘアラインの細い暗線と幅のある傷の区別がつかない。
        cen = _central_cols(y.shape[1])
        best = np.zeros(len(y))
        L = 1
        while L <= len(cen):
            c = np.cumsum(np.pad(y[:, cen], ((0, 0), (1, 0))), axis=1)
            box = (c[:, L:] - c[:, :-L]) / math.sqrt(L)
            best = np.maximum(best, np.max(np.abs(box), axis=1))
            L *= 2
        return best
    n, h, ww = y.shape
    yy, xx = np.mgrid[0:h, 0:ww]
    rr = np.hypot(yy - (h - 1) / 2, xx - (ww - 1) / 2)
    r = _disk_radius_px(key, ww)
    if key == "S2":
        # 凹みの模様(照明で明暗の出方が変わる)は形を決めずに、凹みの大きさ(σ/2)でならしてから円の中の RMS。
        # ならさずに RMS を取ると、画素が細かいカメラほど 1 画素の雑音をそのまま拾って損をする。
        sm = DENT_SIGMA_MM * 1000.0 / SUBJECTS["S2"]["px"] * ww / SUBJECTS["S2"]["nx"] / 2.0
        ys = ndimage.gaussian_filter(y, (0, sm, sm), mode="nearest")
        return np.sqrt(np.mean(ys[:, rr <= r] ** 2, axis=1))
    s = max(0.5, r / 1.5)
    g = np.exp(-rr ** 2 / (2 * s * s))
    g /= math.sqrt(float(np.sum(g * g)))
    return np.abs(np.sum(y * g, axis=(1, 2)))


PFP_TARGET = 0.01


def _order_threshold(noise):
    """無欠陥の â の順序統計で閾値: 越えるのがちょうど k = ⌊0.01 n⌋ 部位になる値(補間した分位は 1 部位多く越えうる)。"""
    s = np.sort(np.asarray(noise, dtype=np.float64))
    k = int(math.floor(PFP_TARGET * len(s) + 1e-9))
    return float(s[len(s) - k - 1])


def pod_for(train, test, key, w=None):
    """学習 (res, sizes) でチャンネルの重み、試験で POD。

    ★判定閾値は**マスごとに同じ誤検出率**にそろえる: 試験の無欠陥の部位の â の順序統計で、越えるのがちょうど
    ⌊0.01 n⌋ 部位になる値(無欠陥 100 部位で 1 部位 = 1 %)。比べたいのは同じ誤検出率での a90/95 なので、閾値を学習側から持ち込むと
    マスごとに実際の誤検出が 0.6〜8 % に散って比べられなかった(初版、レビューの指摘)。学習側の無欠陥で決めた
    閾値が試験でどれだけ外れるか(汎化)は ``pfp_heldout`` として別に数える。
    *w* を渡すとチャンネルの重みを学習せずにそれを使う(帯を足し合わせただけの比べ方)。
    """
    res_tr, a_tr = train
    res_te, a_te = test
    half = np.arange(len(a_tr)) % 2 == 0
    flaw_tr = a_tr > 0
    if w is None:
        w = channel_weight(res_tr[half], key, flaw_tr[half])
    h_tr = np.maximum(ahat_of(res_tr[~half], key, w), 1e-6)
    h_te = np.maximum(ahat_of(res_te, key, w), 1e-6)
    ftr = flaw_tr[~half]
    fl = a_te > 0
    a_dec = _order_threshold(h_te[~fl])
    rec = float(np.median(h_tr[~ftr]))
    out = {"w": w, "a_dec": a_dec, "rec": rec, "ahat": h_te, "a": a_te}
    out["pfp"] = float(fs.ledger.pod_false_call(h_te[~fl], a_dec, log_response=True)["pfp_empirical"])
    out["n_clean"] = int((~fl).sum())
    a_dec_tr = _order_threshold(h_tr[~ftr])
    out["pfp_heldout"] = float(np.mean(h_te[~fl] > a_dec_tr))
    big = a_te[fl] >= np.percentile(a_te[fl], 80)
    out["hit_big"] = float(np.mean(h_te[fl][big] > a_dec))
    try:
        f = fs.ledger.pod_ahat_fit({"a": a_te[fl], "ahat": h_te[fl]}, log_size=True, log_response=True,
                                   censor_low=rec)
        p = fs.ledger.pod_from_ahat(f, a_dec)
        out.update({"fit": f, "pod": p, "a90": float(p["a90"]), "a90_95": float(p["a90_95"]),
                    "beyond": bool(p["a90_95_beyond_data"]), "refused": None})
    except ValueError as exc:
        out.update({"fit": None, "pod": None, "a90": float("inf"), "a90_95": float("inf"), "beyond": True,
                    "refused": str(exc)})
    return out


# =========================================================================== #
# 8. 章 1: 物理の門
# =========================================================================== #
N_LOBE_RAYS = 200000


def chapter_physics():
    print("\n1. 物理の門(光源の形・鏡面のローブ・縞照明の位相・波長の鎖・Fresnel・同軸と通常レンズの視野の端)")
    L = make_lights(40.0, 200.0)
    worst = 0.0
    for k, light in L.items():
        e = float(np.sum(hit_directions(light, 0.0, 0.0, HEMI) * HEMI[:, 2]) * HEMI_W)
        cf = closed_form_irradiance(light)
        worst = max(worst, abs(e / cf - 1.0))
    NUMBERS["irr_worst_rel"] = worst
    gate("拡散の照度(半球 8192 方向の積分)は 6 照明とも閉形式 π Σ ±sin²ζ と 0.5 % 以内", worst < 0.005,
         "最大 %.2f %%" % (100 * worst))
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(12):
        k = LIGHT_KEYS[rng.integers(len(LIGHT_KEYS))]
        px_, py_ = rng.uniform(-15, 15, 2)
        tx, ty = rng.uniform(-0.6, 0.6, 2)
        sig = rng.uniform(0.02, 0.3)
        cf = float(specular_fraction(L[k], px_, py_, tx, ty, sig))
        g = rng.standard_normal((N_LOBE_RAYS, 2)) * sig + [tx, ty]
        d = np.stack([g[:, 0], g[:, 1], np.ones(len(g))], 1)
        mc = float(np.mean(hit_directions(L[k], px_, py_, d)))
        worst = max(worst, abs(cf - mc))
    NUMBERS["lobe_mc_worst"] = worst
    gate("ローブが照明に入る割合: 非心 χ² の閉形式と乱数の光線 %d 本の差 < 0.006(12 通り)" % N_LOBE_RAYS, worst < 0.006,
         "最大 %.4f" % worst)
    # 縞照明: 平らな鏡を θ 傾ける(+x へ登る面)と反射は −x へ 2θ 曲がり、画面の上で −h tan 2θ ずれる → 位相は −2π h tan(2θ) / p。
    # 縞の振幅はローブのぼけで exp(−2π²(hσ/p)²) に落ちる。描画 → fringe.wrapped_phase の位相と振幅を閉形式と比べる。
    key = "S2"
    cfg = SUBJECTS[key]
    lt = make_lights(cfg["fov"], cfg["wd"])
    p = fringe_period(key)
    worst_ph, worst_amp = 0.0, 0.0
    for th_deg in (0.0, 0.05, 0.2, 0.5):
        s = SiteSet(key, 1, 0, 1)
        s.sizes[:] = 0.0
        s.fx[:] = 0.0
        s.fy[:] = 0.0
        sig = _lobe_sigma(FACET_DEG[key], cfg["na"])
        h = cfg["wd"]
        t2 = math.tan(2 * math.radians(th_deg))
        cx = np.exp(-2 * np.pi ** 2 * (h * sig / p) ** 2) * np.exp(-2j * np.pi * h * t2 / p)
        deltas = 2 * np.pi * np.arange(FRINGE_STEPS) / FRINGE_STEPS
        frames = 0.5 * (1.0 + np.real(np.exp(-1j * deltas)[:, None, None] * cx * np.ones((1, 4, 4))))
        phi = fringe.wrapped_phase(frames)
        amp = fringe.modulation(frames)
        # 描画側(render_bases の式)で同じ量: 傾いた平らな鏡の部位 1 つを描いて、x の縞の複素振幅の角度と大きさ
        gx = np.full((4, 4), math.tan(math.radians(th_deg)))
        n = np.stack([-gx, np.zeros_like(gx), np.ones_like(gx)], 0)
        n /= np.linalg.norm(n, axis=0, keepdims=True)
        tx, _ty, _ci, _phi = reflect_tan(n[0], n[1], n[2], 0.0, 0.0, 1.0)
        rendered = np.angle(np.exp(2j * np.pi * h * tx / p))
        worst_ph = max(worst_ph, float(np.max(np.abs(np.angle(np.exp(1j * (phi - rendered)))))))
        worst_amp = max(worst_amp, abs(float(np.mean(amp)) / abs(cx) - 1.0) if abs(cx) > 0 else 0.0)
    NUMBERS["fringe_phase_worst"] = worst_ph
    gate("縞照明: 傾けた平らな鏡の位相(fringe.wrapped_phase)= 閉形式 −2π h tan 2θ / p、振幅 = exp(−2π²(hσ/p)²)",
         worst_ph < 1e-9 and worst_amp < 0.05, "位相の差 %.1e rad、振幅の比の差 %.3f(θ = 0〜0.5°)"
         % (worst_ph, worst_amp))
    N, pix, t = 2.0, 25.0, 1e-3
    sel = WL >= 900.0
    wl = WL[sel]
    ref = SR.hyperspectral_band_weights(wl, (1100.0, 1300.0, 1500.0), 20.0, 3000.0, 1000.0, N, pix, t,
                                        optics_thickness_mm=0.0, qe_cutoff_nm=1700.0)
    bb = SR.blackbody_spectrum(3000.0, 900.0, 2500.0, 1601)
    Lsrc = np.interp(wl, *np.asarray(SR.blackbody_spectrum(3000.0, 900.0, 1700.0, 161)).T)
    Lsrc = Lsrc * 1000.0 / SR.spectral_integral(bb) / math.pi
    qe = np.interp(wl, *np.asarray(SR.ingaas_photodiode_qe(1700.0, wl_min_nm=float(wl[0]), wl_max_nm=float(wl[-1]),
                                                           n_points=int(wl.size))).T)
    sig = 20.0 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    na = 1.0 / (2.0 * N)
    mine = np.stack([Lsrc * math.pi * na * na * (pix * 1e-6) ** 2 * t * qe * wl * 1e-9 / (SR.PLANCK_H * SR.LIGHT_C)
                     * np.gradient(wl) * np.exp(-0.5 * ((wl - c) / sig) ** 2) for c in (1100.0, 1300.0, 1500.0)])
    rel = float(np.max(np.abs(mine.sum(1) / ref.sum(1) - 1.0)))
    NUMBERS["chain_rel"] = rel
    gate("波長の鎖: 物体側の étendue π NA² p² で書いた電子数 = ``hyperspectral_band_weights``(像側 π/4N²)", rel < 1e-6,
         "相対差 %.1e(3 帯)" % rel)
    rs0, rp0 = fresnel_rs_rp(1.0, 1.5)
    rsb, rpb = fresnel_rs_rp(math.cos(math.atan(1.5)), 1.5)
    ok = abs(float(rs0) - 0.04) < 1e-12 and abs(float(rp0) - 0.04) < 1e-12 and float(rpb) < 1e-20
    gate("Fresnel: 垂直入射 ((n−1)/(n+1))² = 0.04、Brewster 角で Rp = 0", ok, "Rp(θB) = %.1e" % float(rpb))
    light = make_lights(40.0, 200.0, coax_scale=1.0)["coax"]
    xs = np.linspace(0.0, 30.0, 601)
    vx, vy, vz, _ = _view("normal", xs, np.zeros_like(xs), 200.0)
    tx, ty, _ci, _phi = reflect_tan(np.zeros_like(xs), np.zeros_like(xs), np.ones_like(xs), vx, vy, vz)
    P = specular_fraction(light, xs, np.zeros_like(xs), tx, ty, 1e-4)
    x_img = float(xs[np.argmin(np.abs(P - 0.5))])
    x_cf = light[0][2] / (1.0 + light[0][1] / 200.0)
    NUMBERS["coax_edge_mm"] = x_img
    gate("同軸 + 通常レンズ: 平らな鏡が暗くなる視野の位置 = 閉形式 R/(1 + h/WD)(同軸の半径 = 視野の幅のとき視野の半幅)",
         abs(x_img - x_cf) < 0.1, "%.2f mm(閉形式 %.2f mm、視野の半幅 20 mm)" % (x_img, x_cf))
    # 材料表の入力そのもの(結果ではない): PE と PP の可視の反射率の差、SWIR の 1 帯を通した差
    vis = (WL >= 400) & (WL <= 700)
    dv = float(np.max(np.abs(RESIN["pe"][vis] / RESIN["pp"][vis] - 1.0)))
    Wsw = camera_weights("swir", 0.02, 40.0)
    dsw = float((Wsw @ RESIN["pe"])[0] / (Wsw @ RESIN["pp"])[0] - 1.0)
    Whs = camera_weights("hsi", 0.02, 40.0)
    dhs = float(np.max(np.abs((Whs @ RESIN["pe"]) / (Whs @ RESIN["pp"]) - 1.0)))
    NUMBERS.update({"pe_pp_vis_diff": dv, "pe_pp_swir1_diff": dsw, "pe_pp_hsi_band_max": dhs})
    print("   入力の確認(PP の 0.25 mm 下の PE 片 対 PP の地): 可視の反射率の差 最大 %.1e(材料表で可視の吸収を同じに置いた)、"
          "SWIR 1 帯を通すと %+.2f %%、分光の 1 帯では最大 %.1f %%" % (dv, 100 * dsw, 100 * dhs))


# =========================================================================== #
# 9. 章 2: 地図(種の組を変えて揺れの幅も出す)
# =========================================================================== #
COST = {"coax": 2, "dome": 2, "ring70": 1, "ring30": 1, "dark10": 1, "fringe": 3,
        "mono": 1, "color": 1, "polar": 2, "swir": 3, "hsi": 4, "tele": 2, "normal": 1}


def budget():
    if REDUCED:
        return {"train": (26, 80), "test": (36, 100), "seeds": (0, 1)}
    return {"train": (60, 180), "test": (90, 200), "seeds": (0, 1, 2)}


def run_cell_set(key, seed_set, lights, lks=None, cams=None, lenses=None, mode="takt", coax_tag="", band_sum=False):
    """1 つの種の組で、題材 *key* の (照明, レンズ, カメラ) を撮って POD を出す。戻り {(lk, lens, cam): r}。"""
    b = budget()
    cfg = SUBJECTS[key]
    tr = SiteSet(key, *b["train"], seed=100 + SUBJ_KEYS.index(key) + 1000 * seed_set)
    te = SiteSet(key, *b["test"], seed=200 + SUBJ_KEYS.index(key) + 1000 * seed_set)
    out = {}
    for lk in (lks or LIGHT_KEYS):
        for lens in (lenses or LENS_KEYS):
            btr = render_bases(tr, lk, lens, lights, coax_tag)
            bte = render_bases(te, lk, lens, lights, coax_tag)
            for cam in (cams or CAM_KEYS):
                W = camera_weights(cam, cfg["na"], cfg["px"])
                seed = (1000 * SUBJ_KEYS.index(key) + 100 * LIGHT_KEYS.index(lk) + 10 * LENS_KEYS.index(lens)
                        + CAM_KEYS.index(cam) + 100000 * seed_set)
                res_tr, res_te, t, capped, etr = measure_sites(btr, bte, key, cam, lk, W, seed, mode, tr.sizes == 0)
                w = None
                if band_sum:
                    w = np.ones(res_tr.shape[-1]) / math.sqrt(res_tr.shape[-1])
                    sd = float(np.std(ahat_of(res_tr[tr.sizes == 0], key, w)))
                    w = w / max(sd, 1e-30)
                r = pod_for((res_tr, tr.sizes), (res_te, te.sizes), key, w=w)
                r.update({"t": t, "capped": capped, "lo": cfg["size"][0], "hi": cfg["size"][1],
                          "fx": te.fx, "fy": te.fy})
                clean = etr[tr.sizes == 0]
                pix_mm = cfg["px"] * CAMERAS[cam]["k"] / 1000.0
                nch = 1 if cam == "color" else clean.shape[-1]        # Bayer はモザイク(1 画素 1 色)
                r["e_per_mm2"] = float(np.mean(clean) * (t / T_REF_S) * nch / pix_mm ** 2)
                out[(lk, lens, cam)] = r
    return out


def chapter_map():
    b = budget()
    print("\n2. 地図: 題材 4 × 照明 %d × レンズ 2 × カメラ 5 = %d 通り × 種の組 %d(学習 %d+%d 部位、試験 %d+%d 部位)"
          % (len(LIGHT_KEYS), 4 * len(LIGHT_KEYS) * 10, len(b["seeds"]), *b["train"], *b["test"]))
    print("   露光の上限は視野 1 枚 %.0f ms(1 コマ。縞照明は 16 コマで分け、ラインスキャンの分光は 1 ラインずつ)。"
          "判定閾値はマスごとに試験の無欠陥の部位で誤検出 1 %%。同軸の拡散面は視野の %.0f 倍。" % (1000 * TAKT_S, COAX_SCALE))
    grid = {}
    for key in SUBJ_KEYS:
        cfg = SUBJECTS[key]
        lights = make_lights(cfg["fov"], cfg["wd"])
        t0 = time.time()
        for s in b["seeds"]:
            for k3, r in run_cell_set(key, s, lights).items():
                grid.setdefault((key,) + k3, []).append(r)
        print("   %s %-16s %.0f 秒" % (key, cfg["name"], time.time() - t0))
        print_table(grid, key)
    return grid


def summary(rs):
    """種の組ごとの結果 → dict(n 見つけた組の数, N, med 中央値, lo, hi(見つけた組の a90/95 の最小・最大))。"""
    vals = [r["a90_95"] for r in rs if found(r)]
    out = {"n": len(vals), "N": len(rs), "lo": rs[0]["lo"], "hi_size": rs[0]["hi"]}
    if vals:
        out.update({"med": float(np.median(vals)), "min": float(min(vals)), "max": float(max(vals))})
    return out


def robust(s):
    """どの種の組でも見つけた(揺れても × にならない)マス。"""
    return s["n"] == s["N"]


def cell_text(rs, short=False):
    """地図の 1 マス: 全部の種の組で見つけたら 中央値(最小〜最大)、一部だけなら △k/N、どれでもなければ ×。"""
    s = summary(rs)
    if s["n"] == 0:
        return "×"
    if not robust(s):
        return "△%d/%d" % (s["n"], s["N"])
    f = (lambda v: "%.0f" % v if v >= 10 else "%.1f" % v)
    if short:
        return f(s["med"])
    return "%s(%s〜%s)" % (f(s["med"]), f(s["min"]), f(s["max"]))


def um(rs, short=True):
    """マスの文字に単位を付ける(× と △ には付けない —— 「× µm」と印字されていた、4 回目の確認)。"""
    t = cell_text(rs, short)
    return t if t.startswith(("×", "△")) else t + " µm"


def found(r):
    return r["refused"] is None and not r["beyond"] and math.isfinite(r["a90_95"])


def print_table(grid, key):
    cfg = SUBJECTS[key]
    print("   %s(a90/95 [µm]、%s %g〜%g µm を試した。中央値(最小〜最大)、△ = 一部の種の組だけ、× = どの組でも届かない)"
          % (cfg["name"], cfg["unit"], cfg["size"][0], cfg["size"][1]))
    print("   %-18s " % "カメラ / レンズ" + "".join("%-17s" % LIGHT_NAMES[lk][:8] for lk in LIGHT_KEYS))
    for cam in CAM_KEYS:
        for lens in LENS_KEYS:
            row = [cell_text(grid[(key, lk, lens, cam)]) for lk in LIGHT_KEYS]
            print("   %-18s " % (CAMERAS[cam]["name"] + "/" + LENS_NAMES[lens]) + "".join("%-17s" % c for c in row))


def cheapest(grid, key, slack=1.5):
    """種の組で安定な「最良」と「安くて足りる」マス(どちらも無ければ None)。

    ★枠は種の組で入れ替わらないときだけ付ける(再レビュー: 黄枠・橙枠が種の組で入れ替わっていた)。
      * 黄枠(最良): **どの種の組でも**、そのマスの a90/95 がその組の最良(全マスの最小)の 1.25 倍以内。そういうマスが
        複数あれば中央値が最小のもの。無ければ付けない(最良は種の組で入れ替わる)。
      * 橙枠(安くて足りる): どの種の組でも、そのマスの a90/95 がその組の最良の *slack* 倍以内で、価格帯の目安(COST の和)
        が黄枠より安い(黄枠が無いときは、全マスの最小の価格帯より安いかを問わず最安のもの)。
    """
    cells = {k: rs for k, rs in grid.items() if k[0] == key and robust(summary(rs))}
    if not cells:
        return None, None
    nseed = len(next(iter(cells.values())))
    best_per_seed = [min(rs[i]["a90_95"] for rs in cells.values()) for i in range(nseed)]

    def within(rs, f):
        return all(rs[i]["a90_95"] <= f * best_per_seed[i] for i in range(nseed))
    cost = lambda k: COST[k[1]] + COST[k[2]] + COST[k[3]]
    tops = [k for k, rs in cells.items() if within(rs, 1.25)]
    bk = min(tops, key=lambda k: summary(cells[k])["med"]) if tops else None
    ok = [(cost(k), summary(rs)["med"], k) for k, rs in cells.items() if within(rs, slack)
          and (bk is None or cost(k) < cost(bk))]
    ok.sort()
    return (ok[0][2] if ok else None), bk


# =========================================================================== #
# 10. 章 5: 設定で決まっている所(同軸の大きさ・露光の上限・検査時間・ドームの塊)
# =========================================================================== #
def chapter_design(grid):
    global PEEL_DEG, TAKT_S
    print("\n5. 設定で決まっている所")
    capped = sorted({k for k, rs in grid.items() for r in rs if r["capped"]})
    NUMBERS["n_capped"] = len(capped)
    print("   (a) 露光の上限(視野 1 枚 %.0f ms をコマ数で割った値)に当たったマス %d 個 —— 光が足りないので、"
          "照明を明るくするか上限を延ばせば変わる:" % (1000 * TAKT_S, len(capped)))
    for k in capped:
        print("       %s / %s / %s / %s" % (k[0], LIGHT_NAMES[k[1]], LENS_NAMES[k[2]], CAMERAS[k[3]]["name"]))
    # (b) 同軸の大きさの掃引
    b = budget()
    key = "S1"
    cfg = SUBJECTS[key]
    sweep = {}
    scales = (1.0,) if REDUCED else (1.0, 1.5)                # 2.0 は地図の同軸のマスそのもの
    for ln in LENS_KEYS:
        sweep[(COAX_SCALE, ln)] = grid[(key, "coax", ln, "mono")]
    for cs in scales:
        lights = make_lights(cfg["fov"], cfg["wd"], coax_scale=cs)
        for s in b["seeds"]:
            for k3, r in run_cell_set(key, s, lights, lks=("coax",), cams=("mono",), coax_tag="c%.1f" % cs).items():
                sweep.setdefault((cs, k3[1]), []).append(r)
    print("   (b) 同軸の拡散面の半径(視野の幅の倍数)を変える —— 線傷・モノクロ、a90/95 と大きい方 2 割の検出率:")
    for cs in scales + (COAX_SCALE,):
        row = []
        for lens in LENS_KEYS:
            rs = sweep[(cs, lens)]
            row.append("%s %s / 検出 %.2f" % (LENS_NAMES[lens], cell_text(rs), float(np.mean([r["hit_big"] for r in rs]))))
        print("       半径 %.1f × 視野: %s" % (cs, "、".join(row)))
    out = {"sweep": sweep, "capped": capped}
    # (c) ラインスキャンの分光: 視野 1 枚の露光の上限を 10 ms / 100 ms / 1 s に変える、1 コマ 10 ms(井戸が満ちるまで)、
    #     そのうえで帯を足しただけの重み
    cmp_cells = (("S2", "dark10", "tele"), ("S3b", "dome", "normal"), ("S1", "ring30", "tele"))
    out["takt_vs_full"] = {}
    takts = (0.01, 0.1, 1.0)
    saved_t = TAKT_S
    for key2, lk, lens in cmp_cells:
        cfg2 = SUBJECTS[key2]
        lights = make_lights(cfg2["fov"], cfg2["wd"])
        res = {}
        runs = [("takt", False, tk) for tk in takts] + [("fullwell", False, saved_t), ("fullwell", True, saved_t)]
        for mode, bs, tk in runs:
            TAKT_S = tk
            try:
                if mode == "takt" and tk == saved_t:
                    rs = grid[(key2, lk, lens, "hsi")]
                else:
                    rs = [run_cell_set(key2, s, lights, lks=(lk,), cams=("hsi",), lenses=(lens,), mode=mode,
                                       band_sum=bs)[(lk, lens, "hsi")] for s in b["seeds"]]
            finally:
                TAKT_S = saved_t
            res[(mode, bs, tk)] = rs
        res[("takt", False)] = res[("takt", False, saved_t)]
        res[("fullwell", False)] = res[("fullwell", False, saved_t)]
        res[("fullwell", True)] = res[("fullwell", True, saved_t)]
        out["takt_vs_full"][(key2, lk, lens)] = res
        n_lines = cfg2["fov"] / (cfg2["px"] * CAMERAS["hsi"]["k"] / 1000.0)
        print("   (c) %s / %s / %s / 分光(視野 %.0f ライン): 視野 1 枚の露光の上限 %s、1 コマ 10 ms まで待つ %s、"
              "そのうえで帯を足すだけの重み %s" % (
                  key2, LIGHT_NAMES[lk], LENS_NAMES[lens], n_lines,
                  "、".join("%g s(ライン速度 %.0f Hz)→ %s" % (tk, n_lines / tk, cell_text(res[("takt", False, tk)]))
                           for tk in takts),
                  cell_text(res[("fullwell", False)]), cell_text(res[("fullwell", True)])))
    # (e) 凹みの床はゆず肌か: ゆず肌の傾きを 1/5 にして、縞照明・モノクロ・テレセンを撮り直す
    cfg2 = SUBJECTS["S2"]
    lights = make_lights(cfg2["fov"], cfg2["wd"])
    peel = {}
    saved = PEEL_DEG
    for pd in (saved, saved / 5.0):
        PEEL_DEG = pd
        try:
            peel[pd] = [run_cell_set("S2", s, lights, lks=("fringe",), cams=("mono",), lenses=("tele",))
                        [("fringe", "tele", "mono")] for s in b["seeds"]]
        finally:
            PEEL_DEG = saved
    out["peel"] = peel
    print("   (e) 浅い凹み・縞照明・モノクロ・テレセン: ゆず肌の傾き %.2f° → %s、%.2f° → %s"
          % (saved, um(peel[saved], False), saved / 5.0, um(peel[saved / 5.0], False)))
    # (d) ドームの塊: 凹みの斜面にドームの穴の縁が映る位置だけで光る
    rs = grid[("S2", "dome", "tele", "mono")]
    radii, hits = [], []
    for r in rs:
        fl = r["a"] > 0
        big = fl & (r["a"] >= np.percentile(r["a"][fl], 60))
        radii.append(np.hypot(r["fx"], r["fy"])[big])
        hits.append(r["ahat"][big] > r["a_dec"])
    radii, hits = np.concatenate(radii), np.concatenate(hits)
    edges = np.quantile(radii, [0.0, 1 / 3, 2 / 3, 1.0])
    rows = []
    for i in range(3):
        m = (radii >= edges[i]) & (radii <= edges[i + 1])
        rows.append((edges[i], edges[i + 1], float(np.mean(hits[m]))))
    out["dome_bins"] = rows
    print("   (d) 浅い凹み・ドーム・テレセン・モノクロ: 深い方 4 割の凹みの検出率を、視野の中心からの距離で 3 つに分ける: "
          + "、".join("%.0f〜%.0f mm %.2f" % r for r in rows))
    return out


# =========================================================================== #
# 11. 章 4: 実データで裏を取る(公開の分光画像、CC BY 4.0)
# =========================================================================== #
#: CI(データ無し)で印字する記録値(2026-11-08 の手元の実行)。
RECORDED: dict[str, float] = {
    "real_poly_auc_mono": 0.626, "real_poly_auc_color": 0.637, "real_poly_auc_swir": 0.631,
    "real_poly_auc_hsi_1650": 0.882, "real_poly_auc_hsi_top": 0.754,
    "real_pork_auc_swir_1band": 0.493, "real_pork_auc_swir_2band": 0.937, "real_pork_auc_swir_6band": 0.959,
    "real_pork_auc_hsi_full": 0.994, "real_pork_det_hsi_full": 0.943,
}
#: 実データの取得物(poc_hyperspectral_foreign_matter が作る写し)の SHA-256。違えば読まない(fail-closed)。
REAL_SHA256 = {
    "pork_val_mosaics.npz": "2551ffeac00bcae0a406e262b798e5b7f620fe5e1b648d972c712168f9e72ae4",
    "Polymers 1.0/Test/test_scene_fixed.hdr": "90cea5161a8e55ff542e138b835b02ea36a93ef99aee8c3e648f0b489aa21623",
    "Polymers 1.0/Test/test_scene_fixed.dat": "1237e50d51702973a4bc8da5f243eae34ee08d4a36a7865495ebd9012221246f",
    "Polymers 1.0/Test/Test_GT.png": "2f74bd95072624330087c665b9847249d7656ce5648b8aa814dfe0f381af039c",
}
CREDIT_POLY = ("E. Arbash, A. de Lima Ribeiro, A. Rizaldy, M. Fuchs, P. Ghamisi, P. Scheunders, R. Gloaguen, "
               "\"Polymers Hyperspectral Imaging\", RODARE (HZDR), doi:10.14278/rodare.3390, CC BY 4.0")
CREDIT_PORK = ("V. G. Ghimpeteanu, H. Rajani, J. Quintana, R. Garcia, \"A Hyperspectral Image Dataset for Identifying "
               "Foreign Objects on Pork Belly\", Zenodo, doi:10.5281/zenodo.17242553, CC BY 4.0")


def _hsi_dir():
    return os.path.join(os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye"),
                        "poc_hyperspectral_foreign_matter")


def _verified(names):
    """取得物が在り、SHA-256 が記録と一致するか。在るのに違えば例外(差し替え・破損を黙って使わない)。"""
    import hashlib
    for n in names:
        p = os.path.join(_hsi_dir(), n)
        if not os.path.exists(p):
            return False
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        if h.hexdigest() != REAL_SHA256[n]:
            raise ValueError("SHA-256 が記録と違う(破損か差し替え): %s" % p)
    return True


def _auc(pos, neg):
    s = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(s, kind="mergesort"), kind="mergesort") + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _fisher2(Xtr, ytr, Xte, ridge=1e-3):
    """2 クラスの Fisher 判別(学習の共分散に縮小)。戻り: (試験の得点, 学習の得点)。"""
    m1, m0 = Xtr[ytr].mean(0), Xtr[~ytr].mean(0)
    S = np.atleast_2d(np.cov(Xtr.T) if Xtr.shape[1] > 1 else np.var(Xtr))
    S = S + np.eye(len(S)) * ridge * float(np.trace(S)) / len(S)
    w = np.linalg.solve(S, m1 - m0)
    return Xte @ w, Xtr @ w


def _fisher_cv(Xtr, ytr, Xte, ridges=(1e-3, 1e-2, 1e-1, 1.0, 10.0), k=5, seed=0):
    """縮小の強さを学習側だけの k 分割の交差検証(AUC)で選んでから、学習全体で当てて試験を採点する。"""
    rng = np.random.default_rng(seed)
    fold = rng.permutation(len(ytr)) % k
    best, br = -1.0, ridges[0]
    for rg in ridges:
        sc = []
        for f in range(k):
            a, b = fold != f, fold == f
            if ytr[b].all() or (~ytr[b]).all():
                continue
            st, _ = _fisher2(Xtr[a], ytr[a], Xtr[b], rg)
            sc.append(max(_auc(st[ytr[b]], st[~ytr[b]]), 1e-9))
        m = float(np.mean(sc)) if sc else 0.0
        if m > best:
            best, br = m, rg
    st, sr = _fisher2(Xtr, ytr, Xte, br)
    return st, sr, br


def _bin_bands(R, wl, lo, hi, width=20.0):
    """lo〜hi nm を幅 width の帯に平均して束ねる(学習の画素に比べて帯が多すぎると判別が雑音に合う)。"""
    edges = np.arange(lo, hi + 1e-9, width)
    cols, cen = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (wl >= a) & (wl < b)
        if m.any():
            cols.append(R[..., m].mean(-1))
            cen.append(0.5 * (a + b))
    return np.stack(cols, -1), np.array(cen)


def _camera_emulations(wl):
    """実データの波長 wl の帯に掛けるカメラの重み(QE × 光源 × フィルタ、和で 1 チャンネル)。"""
    qe_si = np.interp(wl, WL, QE_SI)
    qe_in = np.interp(wl, WL, QE_INGAAS)
    vis = np.interp(wl, WL, source_radiance("vis"))
    sw = np.interp(wl, WL, source_radiance("swir"))
    bay = [np.interp(wl, WL, f) for f in bayer_filters()]
    return {"mono": [vis * qe_si], "color": [vis * qe_si * f for f in bay], "swir": [sw * qe_in]}


def chapter_real():
    print("\n4. 実データで裏を取る(公開の分光画像 2 つ、どちらも CC BY 4.0)")
    print("   ★支えるのは「カメラの帯(可視 / SWIR 1 帯 / 数帯 / 全帯)で樹脂を分けられるか」の軸だけで、画素ごとの AUC。"
          "照明・レンズの軸、線傷・凹み・焼け、地図の µm の値は実データで支えていない。")
    out = {}
    poly = ["Polymers 1.0/Test/test_scene_fixed.hdr", "Polymers 1.0/Test/test_scene_fixed.dat", "Polymers 1.0/Test/Test_GT.png"]
    if _verified(poly):
        import specops as SP
        from PIL import Image
        root = os.path.join(_hsi_dir(), "Polymers 1.0")
        cube, meta = SP.read_envi(os.path.join(root, "Test", "test_scene_fixed.hdr"))
        wl = np.asarray(SP._meta_wavelengths(meta), float)
        R = np.asarray(cube, np.float64) / 65535.0
        gt = np.array(Image.open(os.path.join(root, "Test", "Test_GT.png"))).astype(int)
        realdata.mark_read("rodare3390-polymers-hsi")
        m = np.isin(gt, (1, 6))
        H_, W_ = gt.shape
        left = np.zeros_like(m)
        left[:, :W_ // 2] = True
        y = (gt == 1).ravel()                                       # PP = 正、PE = 負
        tr, te = (m & left).ravel(), (m & ~left).ravel()
        em = _camera_emulations(wl)
        feats = {cam: np.log(np.clip(np.stack([np.tensordot(R, w, axes=([2], [0])) for w in em[cam]], -1), 1e-9, None))
                 for cam in ("mono", "color", "swir")}
        wl_top = float(wl[-1])
        f1, c1 = _bin_bands(R, wl, 950.0, 1650.0)
        f2, c2 = _bin_bands(R, wl, 950.0, wl_top)
        feats["hsi_1650"] = np.log(np.clip(f1, 1e-4, None))
        feats["hsi_top"] = np.log(np.clip(f2, 1e-4, None))
        res, ridge = {}, {}
        for name, F in feats.items():
            X = F.reshape(-1, F.shape[-1])
            st, sr, rg = _fisher_cv(X[tr], y[tr], X[te])
            sgn = 1.0 if sr[y[tr]].mean() >= sr[~y[tr]].mean() else -1.0
            res[name] = _auc(sgn * st[y[te]], sgn * st[~y[te]])
            ridge[name] = rg
        out["poly"] = res
        out["poly_meta"] = {"n_pp": int((y & tr).sum()), "n_pe": int((~y & tr).sum()), "wl_top": wl_top,
                            "bands_1650": len(c1), "bands_top": len(c2)}
        NUMBERS.update({"real_poly_auc_%s" % k: v for k, v in res.items()})
        NUMBERS["real_poly_wl_top"] = wl_top
        print("   樹脂の破片(%s)" % CREDIT_POLY)
        print("     %d x %d px、%d 帯 %.0f〜%.0f nm。PP と PE の画素を左半分で学び(PP %d・PE %d 画素)右半分で採点。分光は 20 nm に"
              "束ね(950〜1650 nm で %d 帯、950〜%.0f nm で %d 帯)、縮小の強さは学習側の 5 分割の交差検証で選ぶ"
              % (H_, W_, len(wl), wl[0], wl_top, out["poly_meta"]["n_pp"], out["poly_meta"]["n_pe"], len(c1), wl_top, len(c2)))
        print("     AUC: " + "、".join("%s %.3f(縮小 %g)" % (k, v, ridge[k]) for k, v in res.items()))
        print("     ★20 nm に束ねることと 950〜1650 nm の窓は、実データを一度見てから選んだ(学習 110 画素で帯が多すぎると"
              "判別が雑音に合うため)。信頼区間は出していない。")
    else:
        print("   樹脂の破片(RODARE 3390)は手元に無い(poc_hyperspectral_foreign_matter の取得で入る)。記録値: "
              + ", ".join("%s %.3f" % kv for kv in RECORDED.items() if kv[0].startswith("real_poly")))
    if _verified(["pork_val_mosaics.npz"]):
        z = np.load(os.path.join(_hsi_dir(), "pork_val_mosaics.npz"))
        realdata.mark_read("zenodo17242553-pork-hsi")
        wl = 942.0 + (1723.0 - 942.0) / 223.0 * np.arange(20, 204)
        caps = sorted(k[5:] for k in z.files if k.startswith("cube_"))
        rng = np.random.default_rng(5)

        def pix(names, n_neg):
            X, Y = [], []
            for k in names:
                c, lab = z["cube_" + k], z["lab_" + k]
                pos = np.flatnonzero(np.isin(lab, (0, 3)).ravel())          # 樹脂の異物: PA-PP と PEHD
                neg = np.flatnonzero(np.isin(lab, (10, 11)).ravel())        # 肉と脂
                neg = rng.choice(neg, min(n_neg, len(neg)), replace=False)
                flat = c.reshape(-1, c.shape[-1])
                X += [flat[pos], flat[neg]]
                Y += [np.ones(len(pos), bool), np.zeros(len(neg), bool)]
            return np.concatenate(X).astype(np.float64), np.concatenate(Y)
        Xtr, ytr = pix(caps[:2], 30000)
        Xte, yte = pix(caps[2:], 60000)
        qe = np.interp(wl, WL, QE_INGAAS) * np.interp(wl, WL, source_radiance("swir"))
        L_tr, L_te = np.log(np.clip(Xtr, 1e-4, None)), np.log(np.clip(Xte, 1e-4, None))
        res = {"swir_1band": _fisher2(np.log(np.clip(Xtr @ qe, 1e-9, None))[:, None], ytr,
                                      np.log(np.clip(Xte @ qe, 1e-9, None))[:, None])}
        sel = []
        for _ in range(6):
            best, bj = -1.0, None
            for j in range(len(wl)):
                if j in sel:
                    continue
                st, _sr = _fisher2(L_tr[:, sel + [j]], ytr, L_tr[:, sel + [j]])
                d = (st[ytr].mean() - st[~ytr].mean()) ** 2 / (st[ytr].var() + st[~ytr].var())
                if d > best:
                    best, bj = d, j
            sel.append(bj)
            if len(sel) in (2, 6):
                res["swir_%dband" % len(sel)] = _fisher2(L_tr[:, sel], ytr, L_te[:, sel])
        res["hsi_full"] = _fisher2(L_tr, ytr, L_te)
        aucs, det = {}, {}
        for k, (st, sr) in res.items():
            sgn = 1.0 if sr[ytr].mean() >= sr[~ytr].mean() else -1.0
            st, sr = sgn * st, sgn * sr
            aucs[k] = _auc(st[yte], st[~yte])
            thr = float(np.quantile(sr[~ytr], 0.99))
            det[k] = (float(np.mean(st[yte] > thr)), float(np.mean(st[~yte] > thr)))
        out["pork"] = {"auc": aucs, "det": det, "bands": [float(wl[j]) for j in sel]}
        NUMBERS.update({"real_pork_auc_%s" % k: v for k, v in aucs.items()})
        NUMBERS.update({"real_pork_det_%s" % k: v[0] for k, v in det.items()})
        print("   豚バラの上の樹脂片(%s)" % CREDIT_PORK)
        print("     InGaAs の分光ラインスキャン、%d 帯 %.0f〜%.0f nm、学び %s / 採点 %s、PA-PP と PEHD の破片 対 肉・脂"
              % (len(wl), wl[0], wl[-1], caps[:2], caps[2:]))
        print("     選んだ帯(学びの撮影だけ): %s nm" % ", ".join("%.0f" % b for b in out["pork"]["bands"]))
        for k in aucs:
            print("     %-11s AUC %.3f、誤報 1 %% の閾値で検出 %.3f(試験の誤報 %.3f)" % (k, aucs[k], det[k][0], det[k][1]))
    else:
        print("   豚バラ(Zenodo 17242553)は手元に無い。記録値: "
              + ", ".join("%s %.3f" % kv for kv in RECORDED.items() if kv[0].startswith("real_pork")))
    return out


# =========================================================================== #
# 12. 章 3: 地図から読めること(どの主張も「どの種の組でも」で固定する)
# =========================================================================== #
def _cells(grid, key, lks=None, lenses=None, cams=None):
    return {k: summary(rs) for k, rs in grid.items() if k[0] == key and (lks is None or k[1] in lks)
            and (lenses is None or k[2] in lenses) and (cams is None or k[3] in cams)}


def chapter_findings(grid, design):
    print("\n3. 地図から読めること(「見つかる」= どの種の組でも曲線が立って 90 % に届く、数は中央値)")
    pf = np.array([r["pfp"] for rs in grid.values() for r in rs])
    ph = [(r["pfp_heldout"], r["n_clean"]) for rs in grid.values() for r in rs]
    pooled_ho = sum(p * n for p, n in ph) / max(sum(n for _p, n in ph), 1)
    NUMBERS.update({"pfp_max": float(pf.max()), "pfp_heldout_pooled": pooled_ho})
    ho = np.array([p for p, _n in ph])
    NUMBERS["pfp_heldout_max"] = float(ho.max())
    gate("閾値の作り方の確認(結果ではない): 閾値は採点に使う試験の無欠陥の部位そのもので決めるので、全 %d 回で誤検出は"
         " ⌊0.01 n⌋/n ≤ 1 %% になる(最大 %.3f)—— a90/95 を同じ誤検出率で比べるための定義" % (len(pf), pf.max()),
         pf.max() <= PFP_TARGET + 1e-12)
    gate("汎化の確認: 学習側の無欠陥で決めた閾値を試験に当てた誤検出は、全回を合わせて %.3f(狙い 1 %%、≤ 3 %%)。"
         "ただしマスごとには最大 %.2f まで散る —— 実機で閾値を学習側から持ち込むなら、マスによって誤検出が 1 %% から外れる"
         % (pooled_ho, ho.max()), pooled_ho <= 0.03)
    out = {}
    # ---- S1 線傷 ----
    s1 = _cells(grid, "S1")
    low = {k: s for k, s in s1.items() if k[1] == "dark10" and k[3] == "mono"}
    r30 = {k: s for k, s in s1.items() if k[1] == "ring30" and k[3] == "mono"}
    n30 = sum(robust(s_) for s_ in r30.values())
    NUMBERS["s1_ring30_robust"] = n30
    NUMBERS["s1_ring30_med"] = min((s_["med"] for s_ in r30.values() if robust(s_)), default=float("inf"))
    print("   S1 低角 30°・モノクロ(予算 %s、種の組 %d): %s —— どの組でも見つかるのは 2 マス中 %d マス"
          % ("縮小版" if REDUCED else "full", len(next(iter(grid.values()))),
             "、".join("%s %s" % (LENS_NAMES[k[2]], cell_text(grid[k])) for k in r30), n30))
    if not REDUCED:
        # ★線傷の低角 30° リングは full の予算でだけ門にする: 部位の少ない縮小版では、種の組によって × と入れ替わる
        #   (どの組でも見つかるマスの数を予算と並べて印字する)。
        gate("S1(full の予算): 低角 30° もモノクロでテレセン・通常どちらでも、どの種の組でも見つかる(%s)"
             % "、".join("%s %s" % (LENS_NAMES[k[2]], cell_text(grid[k], True)) for k in r30), n30 == len(r30))
    bright_normal = {k: s for k, s in s1.items() if k[1] in ("dome", "ring70") and k[2] == "normal"
                     and k[3] == "mono"}
    s1_low = min(s["med"] for s in low.values() if robust(s)) if any(robust(s) for s in low.values()) else float("inf")
    NUMBERS["s1_lowangle_mono"] = s1_low
    gate("S1 線傷: 暗視野 10° はモノクロでテレセン・通常どちらでも、どの種の組でも見つかる(最良の中央値 %.0f µm)"
         % s1_low, all(robust(s) for s in low.values()))
    gate("S1: ドーム・高角 70° + 通常レンズ + モノクロは、どの種の組でも 90 % に届かない(平行な研磨の筋の暗線)",
         all(s["n"] == 0 for s in bright_normal.values()))
    sw = design["sweep"]
    hb = {(cs, ln): float(np.mean([r["hit_big"] for r in sw[(cs, ln)]])) for cs in (1.0, COAX_SCALE) for ln in LENS_KEYS}
    s20n, s20t = summary(sw[(COAX_SCALE, "normal")]), summary(sw[(COAX_SCALE, "tele")])
    NUMBERS.update({"coax_hitbig_1_tele": hb[(1.0, "tele")], "coax_hitbig_1_normal": hb[(1.0, "normal")],
                    "coax2_normal_med": s20n.get("med", float("inf")), "coax2_tele_med": s20t.get("med", float("inf"))})
    gate("★S1 同軸(地図は拡散面 = 視野の 2 倍)はテレセン・モノクロで %s、暗視野のモノクロ(%.0f µm)より良い"
         % (um(sw[(COAX_SCALE, "tele")]), s1_low), robust(s20t) and s20t["med"] < s1_low)
    gate("★S1「明視野にはテレセンが要る」は同軸の大きさで決まる: 拡散面 = 視野の幅では通常レンズの大きい傷の検出率 %.2f"
         "(テレセン %.2f)、視野の 2 倍なら通常レンズでもどの種の組でも見つかる(%s、テレセン %s)"
         % (hb[(1.0, "normal")], hb[(1.0, "tele")], um(sw[(COAX_SCALE, "normal")]), um(sw[(COAX_SCALE, "tele")])),
         hb[(1.0, "normal")] < hb[(1.0, "tele")] and robust(s20n))
    pairs = [(s1[k], s1[(k[0], k[1], k[2], "mono")]) for k in s1 if k[3] == "hsi" and s1[k]["n"] > 0]
    s1_1s = summary(design["takt_vs_full"][("S1", "ring30", "tele")][("takt", False, 1.0)])
    gate("S1: ラインスキャンの分光は、一部の種の組でも見つけるマス(%d 個、0 個なら不成立)で、同じ照明・レンズのモノクロより"
         "悪く(見つけた組の中央値で比べる)、低角 30°・テレセンでは露光の上限を 1 s に延ばしても見つけない(物体側の画素 128 µm "
         "が線傷に粗すぎる)" % len(pairs),
         len(pairs) >= 1 and all(m["n"] > 0 and h["med"] > m["med"] for h, m in pairs) and not robust(s1_1s))
    # ---- S2 凹み ----
    s2 = _cells(grid, "S2")
    per_light = {lk: [s for k, s in s2.items() if k[1] == lk] for lk in LIGHT_KEYS}
    n_rob = {lk: sum(robust(s) for s in v) for lk, v in per_light.items()}
    NUMBERS.update({"s2_robust_%s" % lk: v for lk, v in n_rob.items()})
    best = {lk: min((s["med"] for s in v if robust(s)), default=float("inf")) for lk, v in per_light.items()}
    NUMBERS.update({"s2_best_%s" % lk: v for lk, v in best.items()})
    print("   S2 照明ごとの「どの種の組でも見つかる」マスの数(10 マス中): "
          + "、".join("%s %d" % (LIGHT_NAMES[lk], n_rob[lk]) for lk in LIGHT_KEYS))
    gate("S2 浅い凹み: 同軸・ドーム・低角 30° はどのカメラ・レンズでもどの種の組でも見つからない",
         all(n_rob[lk] == 0 for lk in ("coax", "dome", "ring30")))
    gate("S2: 縞照明(偏向法)は 10 マス全部(カメラ 5 × レンズ 2)でどの種の組でも見つかる(最良 %.0f µm)。高角 70° は %d マス"
         % (best["fringe"], n_rob["ring70"]), n_rob["fringe"] == 10 and n_rob["ring70"] <= 2)
    NUMBERS["s2_dark_over_fringe"] = best["dark10"] / best["fringe"]
    print("   S2 斜光(暗視野 10°、予算 %s): %d マスでどの組でも見つかる(最良 %.0f µm、縞照明 %.0f µm)"
          % ("縮小版" if REDUCED else "full", n_rob["dark10"], best["dark10"], best["fringe"]))
    if not REDUCED:
        gate("S2(full の予算): 斜光(暗視野 10°)も 10 マス全部でどの種の組でも見つかる(最良 %.0f µm、縞照明の %.1f 倍)"
             % (best["dark10"], best["dark10"] / best["fringe"]), n_rob["dark10"] == 10)
    pe = design["peel"]
    p0, p1 = sorted(pe)[::-1]
    s0, s1_ = summary(pe[p0]), summary(pe[p1])
    NUMBERS.update({"s2_peel_full": s0.get("med", float("inf")), "s2_peel_fifth": s1_.get("med", float("inf"))})
    gate("★S2: 縞照明の床はゆず肌: 傾きを %.2f° → %.2f° にすると a90/95 が %s → %s(2 倍以上よくなる)"
         % (p0, p1, um(pe[p0]), um(pe[p1])),
         robust(s0) and robust(s1_) and s1_["med"] < s0["med"] / 2)
    tv = design["takt_vs_full"][("S2", "dark10", "tele")]
    st, sf, sb = summary(tv[("takt", False)]), summary(tv[("fullwell", False)]), summary(tv[("fullwell", True)])
    NUMBERS.update({"s2_hsi_takt": st.get("med", float("inf")), "s2_hsi_full": sf.get("med", float("inf")),
                    "s2_hsi_full_bandsum": sb.get("med", float("inf"))})
    gate("★S2 斜光・テレセンの分光: 露光の上限 10 ms では %s、1 コマ 10 ms まで待つと %s、そのうえで帯を足すだけ"
         "(分光を使わない)でも %s —— 待てば勝つのは電子数のせいで、分光のせいではない"
         % (um(tv[("takt", False)]), um(tv[("fullwell", False)]), um(tv[("fullwell", True)])),
         robust(sf) and robust(sb) and (not robust(st) or st["med"] > 3 * sf["med"])
         and abs(math.log(sb["med"] / sf["med"])) < math.log(1.25))
    rows = design["dome_bins"]
    span = max(r[2] for r in rows) - min(r[2] for r in rows)
    NUMBERS["s2_dome_span"] = span
    gate("S2 ドームの明るい塊は凹みの斜面に映ったドームの穴の縁で、視野の位置で出たり消えたりする(深い凹みの検出率が"
         "距離の 3 区間で %s、差 %.2f)" % (" / ".join("%.2f" % r[2] for r in rows), span), span >= 0.2)
    # ---- S3a 焼け ----
    s3a = _cells(grid, "S3a", cams=("mono",))
    nonfr = [s for k, s in s3a.items() if k[1] != "fringe"]
    NUMBERS["s3a_mono_max"] = max(s["med"] for s in nonfr if robust(s)) if nonfr else float("inf")
    gate("S3a 黒い焼け: モノクロは縞照明以外の 10 通り全部でどの種の組でも見つかる(中央値の最大 %.0f µm)。"
         "縞照明は面の傾きを測るので中の異物は見えない" % NUMBERS["s3a_mono_max"],
         all(robust(s) for s in nonfr) and all(s["n"] == 0 for k, s in s3a.items() if k[1] == "fringe"))
    # ---- S3b PE 片 ----
    s3b = _cells(grid, "S3b")
    vis = [s for k, s in s3b.items() if k[3] in ("mono", "color", "polar")]
    gate("S3b PE の破片: 可視の 3 カメラ(36 通り)はどれも見つけない —— これは発見ではなく入力: 材料表で可視の吸収を"
         "PP と PE で同じに置いたので、可視の反射率の差は %.1e(実データの破片はモノクロでも AUC 0.6 台で分かれる)"
         % NUMBERS["pe_pp_vis_diff"], all(s["n"] == 0 for s in vis) and NUMBERS["pe_pp_vis_diff"] < 1e-12)
    swir = [s for k, s in s3b.items() if k[3] == "swir"]
    gate("S3b: SWIR の 1 帯もどの組でも見つけない —— 1195 / 1215 nm の谷の差は、帯を通すと %+.2f %%(分光の 1 帯なら最大 %.1f %%)"
         % (100 * NUMBERS["pe_pp_swir1_diff"], 100 * NUMBERS["pe_pp_hsi_band_max"]), all(s["n"] == 0 for s in swir))
    hs = {k: s for k, s in s3b.items() if k[3] == "hsi" and robust(s)}
    NUMBERS["s3b_hsi_n"] = len(hs)
    NUMBERS["s3b_hsi_best"] = min((s["med"] for s in hs.values()), default=float("inf"))
    print("   S3b 分光がどの種の組でも見つけるマス: "
          + ("、".join("%s/%s %s" % (LIGHT_NAMES[k[1]], LENS_NAMES[k[2]], um(grid[k])) for k in hs) or "なし"))
    gate("S3b: 分光(10 nm × 71 帯)だけが見つける。ただし露光の上限 10 ms では見つかるのは拡散光の多いドームなど一部の照明だけ"
         "(%d マス、最良 %.0f µm)" % (len(hs), NUMBERS["s3b_hsi_best"]), 1 <= len(hs) <= 6)
    for key in SUBJ_KEYS:
        out[key] = cheapest(grid, key)
    print("   種の組で安定な最良(どの組でもその組の最良の 1.25 倍以内)と、安くて足りる組(どの組でも最良の 1.5 倍以内):")
    nm = lambda k: "%s/%s/%s(%s µm)" % (LIGHT_NAMES[k[1]], CAMERAS[k[3]]["name"], LENS_NAMES[k[2]], cell_text(grid[k]))
    for key in SUBJ_KEYS:
        ck, bk = out[key]
        print("     %-16s 最良 %s、安くて足りる組 %s" % (
            SUBJECTS[key]["name"], "なし(種の組で入れ替わる)" if bk is None else nm(bk),
            "なし" if ck is None else nm(ck)))
    return out


# =========================================================================== #
# 13. 図と動画
# =========================================================================== #
HERO = {"S1": ({"nx": 128, "ny": 96}, 60.0), "S2": ({"nx": 96, "ny": 96}, 80.0),
        "S3a": ({"nx": 96, "ny": 96}, 500.0), "S3b": ({"nx": 96, "ny": 96}, 1500.0)}


#: 見本の表示: 地(中央値)で割った濃淡を、題材ごとに同じ倍率で広げる(0.5 + G·(I/地 − 1))。画像ごとに引き伸ばさない
#: ので、照明の間で濃淡の大きさを比べられる。斜光の凹みの陰影は数 % なので、凹みと焼けの行は倍率を上げる。
HERO_GAIN = {"S1": 0.35, "S2": 80.0, "S3a": 3.0, "S3b": 3.0}
#: 縞照明の見本は縞そのものの濃淡が大きいので、倍率を下げる(飽和させない)。
HERO_GAIN_FRINGE = 0.5
LAST_GAIN = [1.0]       # 直前の見本の表示倍率(分光で下げたときに見出しへ書く)


def fringe_hero_zoom(key):
    """縞照明の見本で、縞が 2 周期以上入るように視野を広げる倍率(10 倍まで)。"""
    dims, _ = HERO[key]
    field = dims["nx"] * SUBJECTS[key]["px"] / 1000.0
    return int(min(10, max(1, math.ceil(2.0 * fringe_period(key) / field))))


def hero_capture(key, lk, lens, cam, seed=3, band_ratio=False):
    """題材の見本の 1 枚(大きめの部位に代表の大きさの欠陥 1 つ)をカメラで撮った画像(地で割った表示用の [0,1])。
    縞照明は細かい x の縞の 1 コマ(δ = 0)を、縞が見えるよう視野を広げて見せる。露光は地図と同じ決め方。
    ★見本は視野の中心の近く(中心から 0.1 視野)に置く: 初版の作り直しは 0.3 視野に置き、浅い凹みでドームの穴の縁が
    斜面に映る位置に当たって、地図(ドームは ×)と逆の印象を与えた(再レビュー)。"""
    dims, size = HERO[key]
    cfg = SUBJECTS[key]
    zoom = fringe_hero_zoom(key) if lk == "fringe" else 1
    dims = dict(dims, px=cfg["px"] * zoom)
    s = SiteSet(key, 1, 0, seed)
    s.sizes[:] = size
    s.fx[:] = 0.1 * cfg["fov"]
    s.fy[:] = 0.05 * cfg["fov"]
    s.jit[:] = 0.0
    s.slopes[:] = SLOPE_DEG
    saved = dict(SUBJECTS[key])
    SUBJECTS[key].update(dims)
    try:
        b = render_bases(s, lk, lens, make_lights(cfg["fov"], cfg["wd"]), "hero")
    finally:
        SUBJECTS[key].clear()
        SUBJECTS[key].update(saved)
    W = camera_weights(cam, cfg["na"], cfg["px"])
    frame = ("x", 0.0, "C") if lk == "fringe" else None
    e = sample_camera(clean_electrons(b, key, cam, W, frame), cam)
    t, _ = exposure_for(e, cam, np.array([True]), exposure_cap(key, cam, 16 if lk == "fringe" else 1))
    x = capture(e, cam, t, seed)[0]
    if cam == "polar":
        x = x.mean(-1, keepdims=True)
    elif cam == "hsi" and band_ratio:
        # 分光: 1210 nm の帯を両隣(1150 / 1270 nm)の平均で割る(C-H の吸収の深さ)。PE と PP の差はこの帯に出る
        bi = lambda c: int(np.argmin(np.abs(HSI_CENTERS - c)))
        x = x[..., [bi(1210.0)]] / np.maximum(0.5 * (x[..., [bi(1150.0)]] + x[..., [bi(1270.0)]]), 1e-9)
    elif cam == "hsi":
        x = x[..., [int(np.argmin(np.abs(HSI_CENTERS - 1210.0)))]]
    if key == "S2" and lk != "fringe":
        # 凹みの行は判定と同じ大きさ(凹みの σ/2)でならして見せる: ならさない 1 画素の雑音は凹みの陰影より大きく、
        # どの照明も同じ砂嵐に見えて、地図(斜光は見つける)と食い違って見えた(再レビュー)。
        sm = DENT_SIGMA_MM * 1000.0 / (cfg["px"] * CAMERAS[cam]["k"]) / 2.0
        x = ndimage.gaussian_filter(x, (sm, sm, 0), mode="nearest")
    med = np.maximum(np.median(x.reshape(-1, x.shape[-1]), axis=0), 1e-9)
    gain = HERO_GAIN_FRINGE if lk == "fringe" else HERO_GAIN[key]
    rel = x / med                                             # 地で割った値(カラーは白の釣り合いもここで取れる)
    lum = rel.mean(-1, keepdims=True)
    if cam == "hsi":
        # 分光の 1 帯は 1 ラインの露光が短く雑音が大きい: 99 % の画素が表示の幅に入るまで倍率を下げる(下げた倍率は見出しに)
        spread = float(np.percentile(np.abs(lum - 1.0), 99))
        gain = min(gain, 0.45 / max(spread, 1e-9))
    disp = 0.5 + gain * (lum - 1.0)
    img = np.clip(disp * (rel / np.maximum(lum, 1e-9)) if rel.shape[-1] == 3 else disp, 0.0, 1.0)
    # カラーは輝度にだけ倍率を掛け、色(チャンネルの比)は広げない —— 色の雑音まで広げると虹色の砂嵐になった(3 回目の確認)
    if img.shape[-1] == 1:
        img = img[..., 0]
    LAST_GAIN[0] = gain
    return img, CAMERAS[cam]["k"]


def hero_shade(key, lk, lens, cam, seed=3):
    """見本の欠陥が地に対して何割の濃淡を作るか(雑音なし)。欠陥あり と 欠陥なし(大きさ 1e-6 µm = 実質 0)の
    同じ部位を雑音を足す前の電子数で撮り、差の最大を地の中央値で割る。★凹みの見本は 80 倍に広げ判定の大きさで
    ならして見せるので、目で見える濃さを実際より強く見せる —— その実際の大きさを見本の下に書くための数(7 回目の確認)。"""
    dims, size = HERO[key]
    cfg = SUBJECTS[key]
    out = []
    for sz in (size, 1e-6):
        st = SiteSet(key, 1, 0, seed)
        st.sizes[:] = sz
        st.fx[:] = 0.1 * cfg["fov"]
        st.fy[:] = 0.05 * cfg["fov"]
        st.jit[:] = 0.0
        st.slopes[:] = SLOPE_DEG
        saved = dict(SUBJECTS[key])
        SUBJECTS[key].update(dict(dims, px=cfg["px"]))
        try:
            b = render_bases(st, lk, lens, make_lights(cfg["fov"], cfg["wd"]), "hero")
        finally:
            SUBJECTS[key].clear()
            SUBJECTS[key].update(saved)
        W = camera_weights(cam, cfg["na"], cfg["px"])
        out.append(np.asarray(sample_camera(clean_electrons(b, key, cam, W, None), cam), float))
    return float(np.abs(out[0] - out[1]).max() / max(float(np.median(out[1])), 1e-12))


def _font(size, bold=False):
    from PIL import ImageFont
    p = figs._japanese_font_path(bold=bold, fail_closed=False) or figs._japanese_font_path(fail_closed=False)
    return ImageFont.truetype(str(p), size)


def _text(d, xy, s, size=20, fill=(235, 240, 245), bold=False, box=None):
    f = _font(size, bold)
    if box is not None:
        bb = d.multiline_textbbox(xy, s, font=f)
        assert bb[0] >= box[0] and bb[1] >= box[1] and bb[2] <= box[2] and bb[3] <= box[3], (s, bb, box)
    d.multiline_text(xy, s, font=f, fill=fill)


def _to_rgb8(img, k=1, size=None):
    """[0,1] の灰 / RGB を uint8 に。k > 1 は整数倍の最近傍(画素の粗さを見せるための拡大、図に明記する)。"""
    a = np.asarray(img)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, -1)
    if k > 1:
        a = np.repeat(np.repeat(a, k, 0), k, 1)
    a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    if size is not None:
        from PIL import Image
        a = np.asarray(Image.fromarray(a).resize(size, Image.Resampling.LANCZOS))
    return a


def _cell_color(s, best):
    """中央値の、題材の最良に対する比で塗る(固定の尺度: 1 倍 = 濃い青 〜 10 倍以上 = 淡い)。△ は灰青、× は灰。"""
    if s["n"] == 0:
        return (70, 74, 80)
    if not robust(s):
        return (92, 104, 124)
    x = min(max(math.log10(s["med"] / best), 0.0), 1.0)
    c0, c1 = np.array([24, 92, 168]), np.array([196, 214, 232])
    return tuple(int(v) for v in c0 + (c1 - c0) * x)


def draw_map_panel(d, grid, key, x0, y0, cw=92, ch=30, reveal=None, marks=None, font=15, lw=150, short=False):
    """題材 1 つの地図(行 = カメラ × レンズ、列 = 照明)を (x0, y0) から描く。reveal = 見せる (照明, レンズ) の集合。"""
    cells = {k: summary(rs) for k, rs in grid.items() if k[0] == key}
    best = min((s["med"] for s in cells.values() if robust(s)), default=1.0)
    names = {"coax": "同軸", "dome": "ドーム", "ring70": "R高70°", "ring30": "R低30°", "dark10": "暗視野", "fringe": "縞"}
    for j, lk in enumerate(LIGHT_KEYS):
        _text(d, (x0 + lw + j * cw + 4, y0), names[lk], size=font - 1)
    for i, (cam, lens) in enumerate([(c, ln) for c in CAM_KEYS for ln in LENS_KEYS]):
        yy = y0 + 24 + i * ch
        _text(d, (x0, yy + 5), "%s/%s" % (CAMERAS[cam]["name"].replace("ハイパースペクトル", "分光"), LENS_NAMES[lens]),
              size=font - 1)
        for j, lk in enumerate(LIGHT_KEYS):
            xx = x0 + lw + j * cw
            s = cells[(key, lk, lens, cam)]
            show = reveal is None or (lk, lens) in reveal
            d.rectangle((xx, yy, xx + cw - 3, yy + ch - 3), fill=_cell_color(s, best) if show else (32, 38, 46))
            if show:
                t = cell_text(grid[(key, lk, lens, cam)], short)
                fsz = font - (0 if short else 2)
                if d.textlength(t, font=_font(fsz)) > cw - 8:          # 最大値と閉じ括弧が切れないよう、入らなければ中央値だけ
                    t = cell_text(grid[(key, lk, lens, cam)], True)
                pale = robust(s) and math.log10(s["med"] / best) > 0.55
                _text(d, (xx + 4, yy + 4), t, size=font - (0 if short else 2),
                      fill=(20, 24, 30) if pale else (250, 250, 250))
            if marks and (lk, lens, cam) in marks:
                d.rectangle((xx - 1, yy - 1, xx + cw - 2, yy + ch - 2), outline=marks[(lk, lens, cam)], width=3)
    return x0 + lw + len(LIGHT_KEYS) * cw, y0 + 24 + 10 * ch


def _marks(cheap_k):
    ck, bk = cheap_k
    m = {}
    if bk is not None:
        m[(bk[1], bk[2], bk[3])] = (255, 214, 102)
    if ck is not None:
        m[(ck[1], ck[2], ck[3])] = (230, 159, 0)
    return m


def make_map_figure(grid, cheap):
    from PIL import Image, ImageDraw
    nseed = len(next(iter(grid.values())))
    W_, H_ = 1780, 900
    im = Image.new("RGB", (W_, H_), (14, 18, 24))
    d = ImageDraw.Draw(im)
    _text(d, (16, 10), "機材選びの地図: 90 %% 見つかる大きさ a90/95 [µm] —— 中央値(種の組 %d つの最小〜最大)、"
          "どのマスも誤検出 1 %%、露光の上限 %.0f ms" % (nseed, 1000 * TAKT_S), size=22, bold=True)
    pos = {"S1": (16, 56), "S2": (906, 56), "S3a": (16, 476), "S3b": (906, 476)}
    for key in SUBJ_KEYS:
        x0, y0 = pos[key]
        cfg = SUBJECTS[key]
        _text(d, (x0, y0), "%s %s(%s %g〜%g µm を試した)" % (key, cfg["name"], cfg["unit"], *cfg["size"]), size=18,
              bold=True)
        draw_map_panel(d, grid, key, x0, y0 + 30, cw=122, ch=30, marks=_marks(cheap[key]), font=16, lw=140)
    _text(d, (16, H_ - 52), "塗り = 中央値の、その題材の最良に対する比(濃い青 1 倍 → 淡い 10 倍以上、固定の尺度)。△k/N = N 組のうち k 組"
          "だけ見つけた(揺れで × と入れ替わる)、× = どの組でも 90 % に届かない。", size=15)
    _text(d, (16, H_ - 28), "黄枠 = どの種の組でも最良の 1.25 倍以内(最良が組で入れ替わるなら付けない)。橙枠 = どの組でも最良の 1.5 倍"
          "以内で価格帯の目安(推定)が黄枠より安い。同軸は拡散面 = 視野の 2 倍。合成の試験。", size=15)
    figs.save("equipment_map", np.asarray(im),
              "4 種の欠陥を、照明 6(同軸落射・ドーム・リング高角 70°・低角 30°・暗視野 10°・縞照明)× カメラ 5 × レンズ 2 で"
              "撮った合成の試験の a90/95(MIL-HDBK-1823A の â vs a)。どのマスも判定閾値を試験の無欠陥の部位で誤検出 1 %% に"
              "そろえ、露光の上限は視野 1 枚 %.0f ms(縞照明は 16 コマで分け、ラインスキャンの分光は 1 ラインずつ。光子の数を"
              "そろえたのではない)。同軸の拡散面は視野の 2 倍。部位の種の組を %d つ変えて回し、中央値と最小〜最大を書いた。"
              % (1000 * TAKT_S, nseed))


def _mark(d, x0, y0, w, h):
    """欠陥の位置(見本の中心)を、画像の上下の縁の外側の小さな三角で示す(画像の上には描かない)。"""
    c = x0 + w // 2
    col = (230, 159, 0)
    d.polygon([(c - 7, y0 - 9), (c + 7, y0 - 9), (c, y0 - 1)], fill=col)
    d.polygon([(c - 7, y0 + h + 9), (c + 7, y0 + h + 9), (c, y0 + h + 1)], fill=col)


#: 図 02 で撮った見本の絵と表示倍率(正方形の見本の図が同じ絵を使う)。
GLANCE_TILES = {}
#: 凹みの見本の陰影(雑音なし、地に対する割合)。図 02 の見本の下と図の説明に書く。
GLANCE_SHADE = {}


def glance_gain_label(key, gain):
    """見本の表示倍率の札。★凹みは「80 倍に広げ判定の大きさでならした」ことと、陰影の実際の大きさを必ず添える
    (雑音がほぼ消えて、凹みが実際よりはっきり見える。7 回目の確認)。"""
    if key == "S2":
        if key not in GLANCE_SHADE:
            lk, lens, cam, _r = GLANCE_SHOW[key]
            GLANCE_SHADE[key] = hero_shade(key, lk, lens, cam)
        return "表示 ×%.3g・判定の大きさでならした\n(凹みの陰影は最大 %.1f %%、目ではまず見えない)" % (
            gain, 100.0 * GLANCE_SHADE[key])
    return "表示 ×%.3g(地で割った濃淡を広げた)" % gain


#: 媒体の図の見本: 傷が目で分かる組(最良とは限らない。モノクロで撮れる題材はモノクロ)。
GLANCE_SHOW = {"S1": ("coax", "tele", "mono", False), "S2": ("dark10", "tele", "mono", False),
               "S3a": ("ring30", "normal", "mono", False), "S3b": ("dome", "tele", "hsi", True)}


def _hatched(d, box, fill, line, dashed=False):
    """全長の棒: 灰色に斜線(見つからない)か、破線の枠(一部の種の組だけ)。"""
    x0, y0, x1, y1 = box
    if dashed:
        for xx in range(int(x0), int(x1), 12):
            d.line((xx, y0, min(xx + 6, x1), y0), fill=line, width=2)
            d.line((xx, y1, min(xx + 6, x1), y1), fill=line, width=2)
        return
    d.rectangle(box, fill=fill)
    for xx in range(int(x0) - int(y1 - y0), int(x1), 10):
        a, b = max(xx, x0), min(xx + (y1 - y0), x1)
        if b > a:
            d.line((a, y1 - (a - xx), b, y1 - (b - xx)), fill=line, width=1)


def make_glance_figure(grid):
    """ViEW の媒体: 題材ごとに、傷が目で分かる見本 1 枚と、照明 6 種それぞれで最良のカメラ・レンズの a90/95。

    ★棒は短いほど小さい傷まで見つかる。見つからない照明は**全長の灰色の斜線の棒**(試した範囲の上限より大)、一部の種の
    組だけ見つかる照明は**破線の全長の棒** —— 空の溝にすると、いちばん短い(= 最良)に見えた(5 回目の確認)。
    見本は大きく、文字は少なく(200 px のサムネイルでも何の絵か分かるように)。"""
    from PIL import Image, ImageDraw
    W_, H_ = 1440, 1120
    im = Image.new("RGB", (W_, H_), (14, 18, 24))
    d = ImageDraw.Draw(im)
    _text(d, (20, 12), "同じ傷を照明 6 × カメラ 5 × レンズ 2 で撮ると、どの組なら何 µm から見つかるか", size=26, bold=True)
    cam_s = {"mono": "モノクロ", "color": "カラー", "polar": "偏光", "swir": "SWIR", "hsi": "分光"}
    l_s = {"coax": "同軸", "dome": "ドーム", "ring70": "高角70°", "ring30": "低角30°", "dark10": "暗視野", "fringe": "縞"}
    blocks = {"S1": (20, 60), "S2": (730, 60), "S3a": (20, 580), "S3b": (730, 580)}
    S = 340                                                    # 見本の一辺
    for key in SUBJ_KEYS:
        x0, y0 = blocks[key]
        cfg = SUBJECTS[key]
        cells = sorted([(summary(rs)["med"], k, summary(rs)) for k, rs in grid.items() if k[0] == key
                        and robust(summary(rs))], key=lambda c: c[0])
        _text(d, (x0, y0), cfg["name"], size=22, bold=True)
        lk, lens, cam, ratio = GLANCE_SHOW[key]
        img, k = hero_capture(key, lk, lens, cam, band_ratio=ratio)
        t = _to_rgb8(img, k=k)
        t = np.asarray(Image.fromarray(t).resize((S, S * t.shape[0] // t.shape[1]), Image.Resampling.LANCZOS))
        im.paste(Image.fromarray(t), (x0, y0 + 38))
        _mark(d, x0, y0 + 38, t.shape[1], t.shape[0])
        gain = LAST_GAIN[0]
        GLANCE_TILES[key] = (t, gain)
        lab = "分光 1210 nm ÷ 両隣" if ratio else "%s・%s" % (l_s[lk], cam_s[cam])
        lines = ["見本: %s(%s %g µm)" % (lab, cfg["unit"], HERO[key][1]), glance_gain_label(key, gain)]
        _text(d, (x0, y0 + 38 + t.shape[0] + 10), "\n".join(lines), size=15, fill=(200, 208, 218),
              box=(x0, y0 + 38, x0 + S + 14, y0 + 518))
        bx0, bx1 = x0 + S + 20, x0 + 690
        lo, hi = math.log10(cfg["size"][0]), math.log10(cfg["size"][1])
        xp = lambda v: bx0 + (math.log10(min(max(v, cfg["size"][0]), cfg["size"][1])) - lo) / (hi - lo) * (bx1 - bx0)
        best_all = cells[0][0] if cells else None
        for i, lkk in enumerate(LIGHT_KEYS):
            yy = y0 + 40 + i * 64
            mine = [c for c in cells if c[1][1] == lkk]
            box = (bx0, yy + 24, bx1, yy + 44)
            if mine:
                med, k3, sm = mine[0]
                gold = med == best_all
                _text(d, (bx0, yy), "%s %s・%s" % (l_s[lkk], cam_s[k3[3]], LENS_NAMES[k3[2]]), size=15)
                d.rectangle(box, fill=(32, 40, 52))
                d.rectangle((bx0, yy + 24, xp(med), yy + 44), fill=(240, 190, 80) if gold else (64, 140, 210))
                d.line((xp(sm["min"]), yy + 34, xp(sm["max"]), yy + 34), fill=(240, 244, 248), width=2)
                _text(d, (bx1 - 70, yy), ("%.0f" % med if med >= 10 else "%.1f" % med) + " µm", size=15,
                      fill=(255, 214, 102) if gold else (235, 240, 245))
            else:
                part = any(summary(rs)["n"] > 0 for kk, rs in grid.items() if kk[0] == key and kk[1] == lkk)
                if part:
                    _hatched(d, box, None, (150, 160, 172), dashed=True)
                    _text(d, (bx0, yy), "%s 種の組で揺れる" % l_s[lkk], size=15, fill=(160, 170, 182))
                else:
                    _hatched(d, box, (52, 56, 62), (96, 102, 110))
                    _text(d, (bx0, yy), "%s 見つからない(> %g µm)" % (l_s[lkk], cfg["size"][1]), size=15,
                          fill=(160, 170, 182))
        _text(d, (bx0, y0 + 40 + 6 * 64 + 2), "%g〜%g µm(対数)" % cfg["size"], size=13, fill=(150, 160, 172))
    _text(d, (20, H_ - 34), "棒が短いほど小さい傷まで見つかる(a90/95 の中央値、白線 = 種の組の最小〜最大、黄 = 最良)。"
          "斜線 = 試した範囲で見つからない、破線 = 種の組で揺れる。合成の試験。", size=15, fill=(190, 200, 212))
    figs.save("equipment_at_a_glance", np.asarray(im),
              "ViEW の入口用: 題材ごとに、傷が目で分かる見本 1 枚と、照明 6 種のそれぞれで最良のカメラ・レンズの a90/95"
              "(種の組 3 つの中央値と最小〜最大。どの組でも見つかるものだけ)。見つからない照明は灰色の斜線の全長の棒、"
              "種の組で揺れる照明は破線の全長の棒。線傷は同軸(視野の 2 倍)+テレセン、浅い凹みは縞照明と斜光、黒い焼けは縞照明"
              "以外のどの照明でも、白い PE 片は分光だけ。見本の表示は図 03 と同じ(地で割った濃淡を題材ごとに同じ倍率で広げ、"
              "倍率は見本の下に書いた。PE 片は分光の 1210 nm の帯を両隣で割った吸収の深さ)。凹みの見本は %.3g 倍に広げて"
              "判定の大きさでならしたので、実際よりはっきり見える(雑音なしの陰影は最大 %.1f %%)。"
              % (GLANCE_TILES["S2"][1], 100.0 * GLANCE_SHADE["S2"]))


def make_glance_square():
    """ViEW のサムネイル用の正方形の図: 図 02 の見本 4 枚を 2×2 に。★横長の図 02 を真ん中で正方形に切ると、線傷の
    見本は右の端しか残らず傷の線が消えた(7 回目の確認)。絵は図 02 と同じもの(表示倍率も同じ、札に書く)。"""
    from PIL import Image, ImageDraw
    T, L, B = 392, 16, 58                                      # 枠の一辺、上の三角の帯、下の札の帯(名前と札の 2 行)
    W_ = 2 * T + 24
    im = Image.new("RGB", (W_, W_), (14, 18, 24))
    d = ImageDraw.Draw(im)
    for n, key in enumerate(SUBJ_KEYS):
        t, gain = GLANCE_TILES[key]
        x0, y0 = 8 + (n % 2) * (T + 8), 8 + (n // 2) * (T + 8)
        h = T - L - B
        # 枠を覆う大きさに縮めて、はみ出した側を中央で切る(欠陥は絵の中心。横長の線傷の絵も枠いっぱいに)
        sc = max(T / t.shape[1], h / t.shape[0])
        u = np.asarray(Image.fromarray(t).resize((max(T, round(t.shape[1] * sc)), max(h, round(t.shape[0] * sc))),
                                                 Image.Resampling.LANCZOS))
        cy, cx = (u.shape[0] - h) // 2, (u.shape[1] - T) // 2
        u = u[cy:cy + h, cx:cx + T]
        im.paste(Image.fromarray(u), (x0, y0 + L))
        c = x0 + T // 2                                        # 欠陥の位置(絵の中心)を上の帯の三角で示す
        d.polygon([(c - 9, y0 + 1), (c + 9, y0 + 1), (c, y0 + L - 1)], fill=(230, 159, 0))
        _text(d, (x0 + 4, y0 + L + h + 2), SUBJECTS[key]["name"], size=22, bold=True, box=(x0, y0, x0 + T, y0 + T))
        # ★凹みは広げてならした絵なので、陰影の実際の大きさを札に必ず添える(8 回目の確認)
        tag = "×%.3g" % gain + ("・ならし・陰影%.1f%%" % (100.0 * GLANCE_SHADE[key]) if key == "S2" else "")
        _text(d, (x0 + 4, y0 + L + h + 30), tag, size=18, fill=(255, 214, 102), box=(x0, y0, x0 + T, y0 + T))
    figs.save("equipment_samples_square", np.asarray(im),
              "ViEW のサムネイル用: 図 02 の見本 4 枚(線傷・浅い凹み・黒い焼け・白い PE 片)を 2×2 に並べた。札の × は"
              "地で割った濃淡の表示倍率。凹みは %.3g 倍に広げ判定の大きさでならした(雑音なしの陰影は最大 %.1f %%)。"
              "PE 片は分光の 1210 nm の帯を両隣で割った吸収の深さ。合成の試験。"
              % (GLANCE_TILES["S2"][1], 100.0 * GLANCE_SHADE["S2"]))


def make_hero_figure():
    from PIL import Image, ImageDraw
    tiles = []
    for key in SUBJ_KEYS:
        row = []
        for lk in LIGHT_KEYS:
            img, _k = hero_capture(key, lk, "tele", "mono")
            row.append(_to_rgb8(img, size=(200, 200 * img.shape[0] // img.shape[1])))
        tiles.append(row)
    h = max(t.shape[0] for r in tiles for t in r)
    W_ = 160 + 6 * 208
    im = Image.new("RGB", (W_, 50 + len(tiles) * (h + 24)), (14, 18, 24))
    d = ImageDraw.Draw(im)
    for j, lk in enumerate(LIGHT_KEYS):
        _text(d, (160 + j * 208 + 2, 8), LIGHT_NAMES[lk].replace("(偏向法)", ""), size=17)
    zooms = {key: fringe_hero_zoom(key) for key in SUBJ_KEYS}
    for i, (key, row) in enumerate(zip(SUBJ_KEYS, tiles)):
        y = 50 + i * (h + 24)
        _text(d, (8, y + 6), SUBJECTS[key]["name"].replace("の", "の\n", 1)
              + "\n%s %g µm" % (SUBJECTS[key]["unit"], HERO[key][1])
              + ("\n縞は視野 ×%d" % zooms[key] if zooms[key] > 1 else ""), size=16)
        for j, t in enumerate(row):
            im.paste(Image.fromarray(t), (160 + j * 208, y))
            _mark(d, 160 + j * 208, y, t.shape[1], t.shape[0])
    figs.save("same_part_six_lights", np.asarray(im),
              "同じ部位を照明だけ変えてモノクロ・テレセンで撮った見本(上から 幅 60 µm の線傷、深さ 80 µm の凹み、"
              "0.25 mm 下の径 500 µm の黒い焼け、径 1.5 mm の PE の破片。橙の三角 = 欠陥の位置、見本は視野の中心の近く)。"
              "光子・読み出しの雑音つき。表示は地(中央値)で割った濃淡を行ごとに同じ倍率で広げた(線傷 0.35 倍、凹み 80 倍、"
              "焼けと PE 3 倍、縞照明 0.5 倍。画像ごとの引き伸ばしはしない)ので、照明の間で濃淡の大きさを比べられる。凹みの行は"
              "判定と同じ大きさ(凹みの σ/2)でならして表示した —— 凹みの陰影は暗視野で最大 %.1f %% で、目ではまず見えない。縞照明は 16 コマのうちの 1 コマで、縞が 2 周期入るように視野を"
              "広げた(行の見出しの視野 ×k。線傷と樹脂は 10 倍に広げても縞の周期の方が長い)。線傷は同軸と高角リングでは研磨の筋と同じ暗線に、低角と"
              "暗視野では明るい線になる。凹みは斜光でかすかな陰影、縞照明で縞の曲がりとして見える。ドームは視野の中心の近くでは"
              "凹みを写さない —— 斜面にドームの穴の縁が映る位置(中心から 60〜80 mm)でだけ明るい塊になるので、視野全体の POD は"
              "90 %% に届かない(章 5 の (d))。PE の破片は可視ではどの照明でも写らない。"
              % (100.0 * hero_shade("S2", "dark10", "tele", "mono")))


def make_camera_figure():
    from PIL import Image, ImageDraw
    best_light = {"S1": "dark10", "S2": "dark10", "S3a": "dome", "S3b": "dome"}
    W_ = 170 + 5 * 228
    im = Image.new("RGB", (W_, 50 + 4 * 268), (14, 18, 24))
    d = ImageDraw.Draw(im)
    for j, cam in enumerate(CAM_KEYS):
        lab = CAMERAS[cam]["name"] + ("(画素 ×%d)" % CAMERAS[cam]["k"] if CAMERAS[cam]["k"] > 1 else "")
        _text(d, (170 + j * 228 + 2, 8), lab.replace("ハイパースペクトル", "分光 1210 nm"), size=16)
    for i, key in enumerate(SUBJ_KEYS):
        y = 50 + i * 268
        _text(d, (8, y + 6), SUBJECTS[key]["name"].replace("の", "の\n", 1) + "\n" + LIGHT_NAMES[best_light[key]], size=16)
        for j, cam in enumerate(CAM_KEYS):
            img, k = hero_capture(key, best_light[key], "tele", cam)
            t = _to_rgb8(img, k=k)
            t = np.asarray(Image.fromarray(t).resize((220, 220 * t.shape[0] // t.shape[1]), Image.Resampling.LANCZOS))
            im.paste(Image.fromarray(t), (170 + j * 228, y))
            _mark(d, 170 + j * 228, y, t.shape[1], t.shape[0])
            if cam == "hsi":
                # この絵だけの表示倍率を、絵のすぐ下(三角の下)に書く(行の見出しに書くと行全体の倍率と読まれた)
                _text(d, (170 + j * 228 + 120, y + t.shape[0] + 4), "この絵は ×%.2g" % LAST_GAIN[0], size=14,
                      fill=(255, 214, 102))
    figs.save("same_part_five_cameras", np.asarray(im),
              "同じ部位・同じ照明をカメラ 5 種で撮った見本(テレセン、露光の上限 10 ms)。偏光は 4 方位の平均の強度、"
              "ハイパースペクトルは 1210 nm の帯。表示は地で割った濃淡を行ごとに同じ倍率で広げた(カラーは輝度にだけ掛け、"
              "色の比は広げない。分光の帯は雑音が大きく、99 % の画素が表示の幅に入るまで倍率を下げ、その絵の下に書いた)。"
              "粗い画素は整数倍の最近傍で同じ大きさに並べた(画素 ×k)。PE の破片は 1210 nm の帯でも目ではほとんど見えない"
              "(帯の差は数 %)—— 見つけるのは帯の組み合わせ(学習した重み)で、1 枚の帯の絵ではない。")


def make_pod_figure(grid):
    """線傷・モノクロ・テレセンで、照明ごとの POD(a)(種の組 1 つ目の曲線と、その曲線自身の a90)。

    どの種の組でも見つかるマスから、a90 の最小・最大と、どちらとも 1.3 倍以上離れた中間を 1 本(3 本まで)選ぶ ——
    ほぼ重なる 2 本を選ぶと見分けられない(4 回目の確認)。ラベルと題の倍率は曲線そのものの a90(地図の a90/95 の
    中央値とは別の量で、題に明記する)。"""
    cand = []
    for lk in LIGHT_KEYS:
        rs = grid[("S1", lk, "tele", "mono")]
        if robust(summary(rs)) and rs[0]["pod"] is not None and math.isfinite(rs[0]["a90"]):
            cand.append((rs[0]["a90"], lk, rs[0]))
    cand.sort()
    pick = [cand[0], cand[-1]] if len(cand) >= 2 else cand
    mids = [c for c in cand[1:-1] if c[0] > 1.3 * cand[0][0] and c[0] < cand[-1][0] / 1.3]
    if mids:
        pick.insert(1, mids[len(mids) // 2])
    ser, cols = [], []
    for (a90, lk, r), col in zip(pick, ["right", "emphasis", "wrong"]):
        p = r["pod"]
        ser.append(("%s(この曲線の a90 %.0f µm)" % (LIGHT_NAMES[lk], a90), np.log10(p["a"]), p["pod"]))
        cols.append(col)
    ratio = pick[-1][0] / pick[0][0] if len(pick) >= 2 else float("nan")
    figs.save_plot("s1_pod_curves", ser, xlabel="log10 線傷の幅 [µm]", ylabel="POD", colors=cols,
                   title="線傷・モノクロ・テレセン: 照明だけで a90 が %.1f 倍違う(種の組 1 の曲線)" % ratio, size=(720, 440),
                   caption="同じ傷・同じ誤検出(1 %)で照明だけを変えた POD(a)。曲線とラベルは種の組 1 つ目の結果(地図の数は"
                           "種の組 3 つの a90/95 の中央値で、別の量)。どの種の組でも見つかる照明から、a90 の最小・最大と、どちらとも"
                           " 1.3 倍以上離れた中間を選んだ。")


def make_real_table(real):
    rows = []
    if "pork" in real:
        p = real["pork"]
        for k, nm in (("swir_1band", "SWIR 1 帯(InGaAs のモノクロ)"), ("swir_2band", "SWIR 2 帯(学びで選ぶ)"),
                      ("swir_6band", "SWIR 6 帯"), ("hsi_full", "分光 184 帯(全部)")):
            rows.append(["豚バラの上の樹脂片", nm, "%.3f" % p["auc"][k], "%.3f" % p["det"][k][0]])
    if "poly" in real:
        q = real["poly"]
        top = real["poly_meta"]["wl_top"]
        for k, nm in (("mono", "モノクロ(514〜700 nm)"), ("color", "カラー"), ("swir", "SWIR 1 帯"),
                      ("hsi_1650", "分光 950〜1650 nm(20 nm に束ねる)"), ("hsi_top", "分光 950〜%.0f nm(同)" % top)):
            rows.append(["樹脂の破片 PP 対 PE", nm, "%.3f" % q[k], "—"])
    if rows:
        figs.save_table("real_data_ladder", ["実データ", "カメラを模した帯", "AUC", "誤報 1 % での検出"], rows,
                        title="実データ: SWIR 1 帯では分けられず、分光で分かれる(樹脂の画素、AUC)",
                        caption="公開の分光画像 2 つの画素を、カメラの帯の重みで束ねて同じ手順で分けた。豚バラは撮影を分けて"
                                "学び・採点、樹脂の破片は場面の左半分で学び右半分で採点(学習は PP 57・PE 53 画素なので分光は 20 nm に"
                                "束ね、縮小の強さは学習側の交差検証で選んだ。それでも 2231 nm まで広げると 1650 nm までより下がる —— "
                                "画素が少なすぎて、帯を増やした分を学べていない)。支えているのは帯の軸だけで、照明・レンズ・µm の値は"
                                "支えていない。出典: " + CREDIT_PORK + "。" + CREDIT_POLY + "。改変: 帯を束ねて重みで足した。")


def make_video(grid, cheap):
    """約 60 秒: 何を入れ → 何を比べ → 何が分かった。960x540、8 fps。"""
    from PIL import Image, ImageDraw
    W_, H_ = 960, 540
    frames = []

    def base(title, sub):
        im = Image.new("RGB", (W_, H_), (12, 16, 22))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W_, 44), fill=(24, 32, 44))
        d.rectangle((0, H_ - 40, W_, H_), fill=(24, 32, 44))
        _text(d, (14, 8), title, size=22, bold=True, box=(0, 0, W_, 44))
        _text(d, (14, H_ - 33), sub, size=18, box=(0, H_ - 40, W_, H_))
        return im, d

    def card(title, lines, n):
        im, d = base(title, "")
        for i, ln in enumerate(lines):
            _text(d, (40, 90 + 44 * i), ln, size=22, box=(0, 60, W_, H_ - 44))
        frames.extend([np.asarray(im)] * n)

    card("機材選びの事前試験", ["入れるもの: 同じ部品・同じ傷(4 種)を", "  照明 6 × カメラ 5 × レンズ 2 = 60 通りで「撮る」",
                          "比べるもの: 90 % 見つかる大きさ a90/95(MIL-HDBK-1823A)",
                          "  どのマスも誤検出 1 %・露光の上限 10 ms、種の組を変えて揺れも出す",
                          "★ブースの 1 製品ではなく、組み合わせの地図を作る(合成の試験)"], 28)
    for key in SUBJ_KEYS:
        cfg = SUBJECTS[key]
        reveal = set()
        for lk in LIGHT_KEYS:
            for lens in LENS_KEYS:
                reveal.add((lk, lens))
                img, _ = hero_capture(key, lk, lens, "mono")
                t = _to_rgb8(img, size=(400, 400 * img.shape[0] // img.shape[1]))
                im, d = base("%s %s" % (key, cfg["name"]),
                             "入れる: %s / %s / モノクロ → 右の地図の列を埋める" % (LIGHT_NAMES[lk], LENS_NAMES[lens]))
                im.paste(Image.fromarray(t), (14, 60))
                _text(d, (14, 60 + t.shape[0] + 6), "%s・%s・モノクロ(見本: %s %g µm)"
                      % (LIGHT_NAMES[lk], LENS_NAMES[lens], cfg["unit"], HERO[key][1]), size=15)
                assert 430 + 120 + 6 * 66 <= W_ - 8
                draw_map_panel(d, grid, key, 430, 56, cw=66, ch=40, reveal=reveal, font=14, lw=120, short=True)
                frames.extend([np.asarray(im)] * 5)
        im, d = base("%s %s —— 分かったこと" % (key, cfg["name"]), "数 = 中央値、△ = 揺れで × と入れ替わる。黄枠 = 最良、橙枠 = 安くて足りる")
        draw_map_panel(d, grid, key, 430, 56, cw=66, ch=40, marks=_marks(cheap[key]), font=14, lw=120, short=True)
        for i, ln in enumerate(FINDING_LINES[key]):
            _text(d, (14, 70 + 34 * i), ln, size=18, box=(0, 60, 425, H_ - 44))
        frames.extend([np.asarray(im)] * 28)
    card("何が分かったか(合成の試験。実データは帯の軸だけ)", FINAL_LINES, 36)
    figs.save_video("equipment_map_explained", frames, fps=8.0, gif_every=2, gif_width=480,
                    caption="同じ 4 種の欠陥を照明 6 × レンズ 2 で撮った見本を左に、その組の a90/95(種の組の中央値)を右の地図に"
                            "埋めていく。最後に題材ごとに分かったことと、最良・安くて足りる組を枠で示す。")
    _audit(frames)
    return len(frames)


def _audit(frames):
    root = os.environ.get("FULLSEYE_AUDIT_DIR", "").strip()
    if not root:
        return
    from PIL import Image
    out = os.path.join(root, "poc_equipment_selection_map")
    os.makedirs(out, exist_ok=True)
    for fn, i in (("f000.png", 0), ("f_mid.png", len(frames) // 2), ("f_end.png", len(frames) - 1)):
        Image.fromarray(frames[i]).save(os.path.join(out, fn))
    ids = np.linspace(0, len(frames) - 1, 12).round().astype(int)
    sheet = Image.new("RGB", (1280, 540), (10, 15, 22))
    for n, i in enumerate(ids):
        th = Image.fromarray(frames[i]).resize((320, 180), Image.Resampling.LANCZOS)
        sheet.paste(th, ((n % 4) * 320, (n // 4) * 180))
    sheet.save(os.path.join(out, "contact.png"))


FINDING_LINES: dict = {}
FINAL_LINES: list = []


def _short(k):
    """枠の組の短い名前(札に入る長さ)。"""
    nm = {"coax": "同軸", "dome": "ドーム", "ring70": "高角", "ring30": "低角", "dark10": "斜光", "fringe": "縞"}
    cam = {"mono": "モノクロ", "color": "カラー", "polar": "偏光", "swir": "SWIR", "hsi": "分光"}
    return "%s・%s・%s" % (nm[k[1]], cam[k[3]], LENS_NAMES[k[2]])


def _finding_lines(grid, cheap):
    """題材ごとの札と最後の札(どれも実行の値と枠から組み立てる。札の幅に入る長さで)。"""
    f = lambda v: ("%.0f" % v) if math.isfinite(v) else "—"
    ck = {key: cheap[key][0] for key in SUBJ_KEYS}
    bk = {key: cheap[key][1] for key in SUBJ_KEYS}
    cheap_line = lambda key: ("安くて足りる: " + _short(ck[key])) if ck[key] is not None else "安くて足りる組は決まらない"
    best_line = lambda key: ("最良: " + _short(bk[key])) if bk[key] is not None else "最良は種の組で入れ替わる"
    FINDING_LINES["S1"] = ["同軸(視野の 2 倍)+テレセン", "で %s µm、暗視野のモノクロ %s µm" % (
        f(NUMBERS["coax2_tele_med"]), f(NUMBERS["s1_lowangle_mono"])), best_line("S1"), cheap_line("S1"),
        "同軸 2 倍なら通常レンズでも見つかる", "(%s µm、テレセンの %.1f 倍)" % (
            f(NUMBERS["coax2_normal_med"]), NUMBERS["coax2_normal_med"] / NUMBERS["coax2_tele_med"])]
    r = NUMBERS["s2_dark_over_fringe"]
    dark_line = ("斜光も %d マスで見つかり、縞の %.1f 倍" % (NUMBERS["s2_robust_dark10"], r)
                 if math.isfinite(r) else "斜光は種の組で揺れる")
    FINDING_LINES["S2"] = ["同軸・ドーム・低角 30° は全滅", "縞 %s µm・斜光 %s µm" % (
        f(NUMBERS["s2_best_fringe"]), f(NUMBERS["s2_best_dark10"])), dark_line, "(斜光の照明は縞の画面より安い)",
        "床はゆず肌: 1/5 で %s→%s µm" % (f(NUMBERS["s2_peel_full"]), f(NUMBERS["s2_peel_fifth"]))]
    FINDING_LINES["S3a"] = ["黒い焼けは縞照明以外の", "どの組でも見つかる", "(モノクロで %s µm 以下)" % f(NUMBERS["s3a_mono_max"]),
                            best_line("S3a"), cheap_line("S3a")]
    FINDING_LINES["S3b"] = ["可視で見えないのは入力どおり", "(材料表で可視の差を 0 に置いた)", "SWIR 1 帯は差 %.2f %%"
                            % (100 * NUMBERS["pe_pp_swir1_diff"]), "分光だけ(上限 10 ms では", "ドームの %d マス)" % NUMBERS["s3b_hsi_n"]]
    s2c = ("、安くて足りる: " + _short(ck["S2"])) if ck["S2"] is not None else ""
    FINAL_LINES[:] = ["線傷: 同軸(視野の 2 倍)+テレセン %s µm、暗視野・モノクロ %s µm" % (
                          f(NUMBERS["coax2_tele_med"]), f(NUMBERS["s1_lowangle_mono"])),
                      "  低角 30°・モノクロ %s(full の予算でどの組でも)" % (
                          (f(NUMBERS["s1_ring30_med"]) + " µm") if NUMBERS["s1_ring30_robust"] == 2 else "は種の組で揺れる"),
                      "同軸が視野と同じ大きさならテレセンが要る。",
                      "  2 倍なら通常レンズでも見つかる(%s µm、テレセンの %.1f 倍)" % (
                          f(NUMBERS["coax2_normal_med"]), NUMBERS["coax2_normal_med"] / NUMBERS["coax2_tele_med"]),
                      "凹み: 同軸・ドーム・低角は全滅。縞 %s µm・斜光 %s µm" % (
                          f(NUMBERS["s2_best_fringe"]), f(NUMBERS["s2_best_dark10"])),
                      "  斜光でも %d マスで見つかり縞の %.1f 倍 —— 照明は安い%s" % (
                          NUMBERS["s2_robust_dark10"], NUMBERS["s2_dark_over_fringe"], "(" + s2c[1:] + ")" if s2c else ""),
                      "分光が要る: 白い樹脂の中の PE。実データでも SWIR 1 帯は当て推量",
                      "数は合成の試験の中央値と揺れ。材料・照明の明るさ・価格帯は推定"]


# =========================================================================== #
# 14. main
# =========================================================================== #
def main():
    # ★CPU の門は PoC 自身の計算量を見るためのもの: 行列積のスレッドが他の負荷と取り合うと CPU 時間が膨らむ(並行実行で
    # 694 秒、3 回目の確認)。threadpoolctl があれば BLAS を 1 スレッドに絞って測る(poc_reproducible_icp と同じ道具)。
    try:
        from threadpoolctl import threadpool_limits
        _limits = threadpool_limits(limits=1)
    except ImportError:                                         # 無ければ絞らずに測る(門は同じ)
        _limits = None
    try:
        _main()
    finally:
        if _limits is not None:
            _limits.restore_original_limits()


def _main():
    t0 = time.time()
    c0 = time.process_time()
    print("=" * 78)
    print("PoC: 機材選びの事前試験 —— 照明 × カメラ × レンズの地図(予算 %s)" % ("reduced" if REDUCED else "full"))
    print("=" * 78)
    chapter_physics()
    grid = chapter_map()
    design = chapter_design(grid)
    cheap = chapter_findings(grid, design)
    real = chapter_real()
    print("   ★実データの門の閾値は、実データを一度見てから置いた(記録値 0.493 / 0.937 / 0.994 / 0.882 の周り)。")
    if "pork" in real:
        p = real["pork"]["auc"]
        gate("★実データ(豚バラの上の樹脂片): SWIR の 1 帯は当て推量(AUC %.3f)、帯を増やすと 2 帯 %.3f → 6 帯 %.3f → 全 184 帯 %.3f"
             % (p["swir_1band"], p["swir_2band"], p["swir_6band"], p["hsi_full"]),
             p["swir_1band"] < 0.6 and p["swir_2band"] > 0.85 and p["hsi_full"] > 0.97
             and p["swir_1band"] < p["swir_2band"] < p["swir_6band"] < p["hsi_full"])
        gate("実データの帯の選び方(学びの撮影だけ)は C-H の 2 次倍音 1195〜1230 nm の帯を含む(184 帯のうち 13 帯がこの窓に"
             "入るので弱い証拠)", any(1190.0 <= b <= 1235.0 for b in real["pork"]["bands"]),
             ", ".join("%.0f" % b for b in real["pork"]["bands"]))
    if "poly" in real:
        q = real["poly"]
        gate("★実データ(PP 対 PE の破片): 分光 950〜1650 nm の AUC %.3f は、モノクロ・カラー・SWIR 1 帯(%.3f / %.3f / %.3f)"
             "より 0.15 以上高い" % (q["hsi_1650"], q["mono"], q["color"], q["swir"]),
             q["hsi_1650"] > max(q["mono"], q["color"], q["swir"]) + 0.15)
    _finding_lines(grid, cheap)
    cpu = time.process_time() - c0
    wall = time.time() - t0
    print("\n所要 %.0f 秒(CPU %.0f 秒。threadpoolctl があれば BLAS を 1 スレッドに絞って測る)" % (wall, cpu))
    if REDUCED:
        # 門はこの PoC 自身の計算量(プロセスの CPU 時間)で見る。壁時計は同じ機械の他の負荷まで数えるので併記だけ。
        gate("所要(CI の縮小版、CPU)< 400 秒", cpu < 400.0, "CPU %.0f 秒(壁時計 %.0f 秒)" % (cpu, wall))
    if not REDUCED and figs.target_dir() is not None:
        make_map_figure(grid, cheap)
        make_glance_figure(grid)
        make_hero_figure()
        make_camera_figure()
        make_pod_figure(grid)
        make_real_table(real)
        n = make_video(grid, cheap)
        print("動画 %d コマ" % n)
        make_glance_square()                                   # 08: 番号を動かさないよう最後に
    assert not figs.errors(), figs.errors()
    print("\n門 %d 件中 NG %d 件" % (len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + " / ".join(FAILS))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
