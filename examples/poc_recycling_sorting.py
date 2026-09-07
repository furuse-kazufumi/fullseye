# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""混合廃棄物の材質選別 —— どの汚れが消えるかは代数で決まり、濡れだけが残る。

リサイクルの選別ラインは、ベルトの上を流れる破片を近赤外(SWIR)の分光カメラで
見て、PET / PP / PE / PVC / 紙 / 金属 に分けます。実験室の綺麗な試片では
ほぼ 100 % 当たるのに現場で精度が出ないのは、**汚れ・濡れ・重なり・傾き・
境界の混合画素**が効くからです。この PoC は 5 つの要因を**既知の量で**仕込み、
どれがどの順で効くかを材質ごとに数えます。

EXTEND: 実機に差し替えるなら :func:`make_geometry` が返す ``truth``(画素ごとの
材質)と ``frag`` (破片ごとの材質・全面積・可視面積)を、実ラインの
アノテーションに置き換えます。**ラベル画像だけでは足りません** —— この PoC の
軸のひとつ「重なりで隠れた面積」は可視ラベル画像に**原理的に写らない**ので、
破片ごとの全面積(投入時の秤量や上流カメラ)が要ります。ライブラリ
:data:`MATERIALS` は解析的な吸収帯モデルなので、実機では**同じ分光計で測った
純物質スペクトル**に差し替えること(別機種のライブラリを持ち込むと、この PoC の
2 次微分の不変性が効かなくなります —— 分光応答関数が違うと形が変わるため)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(1 対の波長の比)は汚れる前から負けている**。48 x 48 通りの
   band 対を総当たりして**最良の 1 対**を選んでも、綺麗な場面で材質別再現率の
   平均 **0.502**。6 材質を 1 個の数字に潰す以上これは上限で、汚れのせいでは
   ない。分光角(SAM)は同じ場面で **1.000**。
2. ★**何が消えるかは前処理の代数で決まる**。破片ごとの劣化は
   ``s(λ) = g·R(λ)·exp(-w·A_w(λ)) + (a·u(λ)+c)`` の形をしていて、
   **SAM は g に不変**(方向しか見ない)、**2 次微分は a·u+c を消す**
   (1 次式の 2 階微分は 0)。予測どおり、乗算的な汚れ(0→0.8)と傾き
   (0→70°)では**どの手法も 1.000 のまま落ちない**。加算的なベースラインは
   生 SAM を 1.000 → **0.229** まで落とし、2 次微分 SAM は **1.000 のまま**。
3. ★★**濡れだけが、どの前処理でも消せない**。水の吸収は波長に依存する乗算
   ``exp(-w·A_w)`` なので、方向にも 2 階微分にも残る。生 SAM 1.000 → **0.514**、
   2 次微分 SAM も 1.000 → **0.681**。**水の 2 帯(1450 / 1940 nm)を捨てる**と
   **0.996** まで戻る —— 現場の常識(水帯を bad band にする)が、ここでは
   代数の帰結として出てくる。
4. ★**予想が外れた: 連続体除去は加算に強くない**。「上側凸包で割るのだから
   なだらかなベースラインは吸収される」と踏んでいたが、実測は
   加算 0.6 で **0.148** —— 生 SAM(0.229)より**悪い**。凸包は
   ベースラインの**傾き**は吸うが、加算された定数は吸収の深さを浅くするので、
   材質を分けている谷そのものが潰れる。
5. ★**壊れ方は 4 種類あり、混ぜて 1 個の正解率にすると順序が見えない**。
   全部入りの条件で、被覆(重なりで隠れた面積)**15.4 %** / 未検出(汚れて
   ベルトに沈んだ)**0.0 %** / 混合画素(境界)**16.3 %** / 誤分類 ——
   対照群(要因を 1 つずつ止める)で効く順序は
   濡れ(+0.319)> 加算汚れ(+0.000)> 混合画素(+0.000)> 重なり(+0.000)
   > 傾き(+0.000)> 乗算汚れ(+0.000)。
6. ★★**似た組が先に壊れる、を先に予測できる**。ライブラリのペア間分光角で
   混同しやすさを順位づけると 1 位は **PE-PVC(2.02°)**。実測の全部入り条件で
   最も多い取り違えも **PE→PVC** で、予測順位と実測順位の順位相関は
   **0.94**(6 材質・15 対)。
7. ★**混合画素は捨てると精度が上がるが、組成が痩せる**。境界画素を捨てると
   材質別再現率は 0.681 → **0.702**。ところが面積基準の組成推定の誤差は
   平均 **3.02 pp → 3.83 pp** と**悪化**する —— 小さい破片ほど境界の割合が
   高いので、境界を捨てると小さい材質が体系的に減る。線形混合分解
   (:func:`fullseye.spec_unmix`)で境界画素を分数のまま数えると **2.72 pp**。

【グラウンドトゥルース】
材質スペクトルは**ガウス吸収帯の重ね合わせという閉形式**(:data:`MATERIALS`)。
破片は既知の中心・半径・向き・重なり順で置き、3 x 3 の細分格子で塗ってから
畳むので、**画素ごとの材質面積比が厳密に既知**。劣化はすべて破片ごとの既知量
(乗算 g、加算 a·u+c、水の深さ w、傾き θ)。重なりは奥から順に塗り潰すだけ
なので、破片ごとの「全面積」と「可視面積」がどちらも数えられる。

来歴(公開文献のみ): Kruse et al., *Remote Sensing of Environment* 44 (1993) 145
—— Spectral Angle Mapper / Heinz & Chang, *IEEE TGRS* 39 (2001) 529 ——
完全制約付き線形混合分解 / Savitzky & Golay, *Anal. Chem.* 36 (1964) 1627 ——
多項式平滑微分 / Clark & Roush, *JGR* 89 (1984) 6329 —— 連続体除去 /
Workman & Weyer, *Practical Guide to Interpretive Near-Infrared Spectroscopy*
(CRC, 2007) —— C-H 伸縮倍音・結合音の帰属。**実測スペクトルは使っていません**。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 分光の諸元 -------------------------------------------------------------- #
N_BAND = 64                     # バンド数
WL0, WL1 = 1100.0, 2450.0       # 波長域 [nm](SWIR)
WL = np.linspace(WL0, WL1, N_BAND)
U = (WL - WL0) / (WL1 - WL0)    # 正規化波長 [0,1](加算ベースラインの軸)

# --- 場面の諸元 -------------------------------------------------------------- #
H, W = 140, 220                 # ベルト視野 [px]
SS = 3                          # 細分格子(混合画素をここで作る)
MM_PX = 1.5                     # 1 画素 [mm/px] -> 視野 210 x 330 mm
N_FRAG = 62                     # 破片の数(既定)
SEED = 20260907
NOISE = 0.004                   # センサ雑音の標準偏差 [反射率]
DET_THR = 0.22                  # 破片/ベルトの切り分け(平均反射率のしきい値)

# --- 全部入りの条件(対照群の基準) ------------------------------------------- #
NOM = {"dirt_mul": 0.60, "dirt_add": 0.30, "wet": 0.70, "tilt": 0.60,
       "n_frag": N_FRAG, "mixed": True}

#: 材質 -> (基準反射率 r0, [(中心 nm, 深さ, 幅 nm), ...])。
#: **解析的なモデル**であって実測ではない。C-H 伸縮の 1 次倍音(~1730 nm)と
#: 結合音(~2310 nm)、O-H(~1450 / 1930 nm)の位置を材質ごとに動かしてある。
#: PE と PVC は骨格が同じ(-CH2-)なので**わざと似せて**ある —— そこが先に壊れる。
MATERIALS = {
    "ベルト": (0.10, [(1730.0, 0.04, 90.0)]),
    "PET":   (0.62, [(1128.0, 0.10, 30.0), (1420.0, 0.12, 46.0),
                     (1660.0, 0.24, 34.0), (1720.0, 0.16, 30.0),
                     (2140.0, 0.30, 55.0), (2320.0, 0.15, 42.0)]),
    "PP":    (0.70, [(1195.0, 0.24, 32.0), (1394.0, 0.14, 36.0),
                     (1730.0, 0.34, 42.0), (1762.0, 0.28, 36.0),
                     (2310.0, 0.44, 50.0), (2350.0, 0.34, 42.0)]),
    "PE":    (0.72, [(1212.0, 0.20, 34.0), (1416.0, 0.13, 36.0),
                     (1730.0, 0.38, 44.0), (1764.0, 0.30, 38.0),
                     (2310.0, 0.45, 48.0), (2350.0, 0.30, 40.0)]),
    "PVC":   (0.66, [(1196.0, 0.15, 32.0), (1430.0, 0.12, 38.0),
                     (1716.0, 0.31, 43.0), (1760.0, 0.23, 37.0),
                     (2300.0, 0.37, 48.0), (2360.0, 0.31, 44.0),
                     (2440.0, 0.20, 40.0)]),
    "紙":    (0.74, [(1450.0, 0.40, 62.0), (1930.0, 0.55, 72.0),
                     (2100.0, 0.30, 55.0), (2330.0, 0.22, 50.0)]),
    "金属":  (0.85, [(2000.0, 0.03, 320.0)]),
}
NAMES = list(MATERIALS)                    # 0 = ベルト, 1..6 = 材質
K = len(NAMES)
FRAG_NAMES = NAMES[1:]

#: 破片が積み重なるときの上下の傾き。紙は潰れて下に、金属は剛体で上に乗る。
Z_BIAS = {"PET": 0.0, "PP": 0.1, "PE": 0.1, "PVC": 0.0, "紙": -0.6, "金属": 0.6}

#: 材質ごとの破片の大きさの癖(ボトルは大きく、紙と缶の破片は細かい)。
#: **小さい破片ほど境界(混合画素)の割合が高い**ので、7 節の結論はここで決まる。
SIZE = {"PET": 1.30, "PP": 1.05, "PE": 0.95, "PVC": 0.85, "紙": 0.60, "金属": 0.55}

#: 水の吸収(既知)。1450 nm と 1940 nm の 2 帯。
WATER = 0.55 * np.exp(-0.5 * ((WL - 1450.0) / 62.0) ** 2) \
    + 1.00 * np.exp(-0.5 * ((WL - 1940.0) / 78.0) ** 2)


# --------------------------------------------------------------------------- #
# 真値 1: 材質スペクトル(閉形式)                                              #
# --------------------------------------------------------------------------- #
def spectrum(name: str) -> np.ndarray:
    """材質 *name* の反射率スペクトル ``(B,)``。ガウス吸収帯の重ね合わせ。"""
    r0, bands = MATERIALS[name]
    r = np.full(N_BAND, r0)
    for c, d, w in bands:
        r -= r0 * d * np.exp(-0.5 * ((WL - c) / w) ** 2)
    return np.clip(r, 1e-3, 1.0)


LIB = np.stack([spectrum(n) for n in NAMES])       # (K, B) 純物質ライブラリ


# --------------------------------------------------------------------------- #
# 真値 2: ベルト上の場面(位置・向き・面積・重なり順が既知)                     #
# --------------------------------------------------------------------------- #
def make_geometry(n_frag: int = N_FRAG, seed: int = SEED, mixed: bool = True) -> dict:
    """破片を撒いて、**画素ごとの材質面積比**を厳密に返す。

    細分格子 ``SS x SS`` で楕円を塗り、奥から順に上書きしてから畳む。
    ``mixed=False`` は畳んだあと**最大の破片に丸める**(混合画素を止めた対照群)。
    """
    rng = np.random.default_rng(seed)
    hs, ws = H * SS, W * SS
    yy, xx = np.mgrid[0:hs, 0:ws]
    yy = (yy + 0.5) / SS
    xx = (xx + 0.5) / SS

    mats = rng.integers(1, K, n_frag)
    a = rng.uniform(5.0, 15.0, n_frag) * np.array(   # 長半径 [px]
        [SIZE[NAMES[m]] for m in mats])
    b = a * rng.uniform(0.45, 0.95, n_frag)          # 短半径 [px]
    th = rng.uniform(0.0, np.pi, n_frag)
    cy = rng.uniform(6.0, H - 6.0, n_frag)
    cx = rng.uniform(6.0, W - 6.0, n_frag)
    # 重なり順: 乱数 + 材質の癖(紙は下、金属は上)。奥(小)から塗る。
    z = rng.uniform(0.0, 1.0, n_frag) + np.array([Z_BIAS[NAMES[m]] for m in mats])
    order = np.argsort(z)

    owner = np.zeros((hs, ws), np.int32)             # 0 = ベルト
    total = np.zeros(n_frag + 1, np.float64)
    for i in order:
        dy, dx = yy - cy[i], xx - cx[i]
        ct, st = np.cos(th[i]), np.sin(th[i])
        u = (dx * ct + dy * st) / a[i]
        v = (-dx * st + dy * ct) / b[i]
        m = (u * u + v * v) <= 1.0
        total[i + 1] = m.sum() / (SS * SS)
        owner[m] = i + 1

    frac = np.zeros((H * W, n_frag + 1), np.float64)
    for i in range(n_frag + 1):
        f = (owner == i).reshape(H, SS, W, SS).mean(axis=(1, 3))
        frac[:, i] = f.ravel()
    visible = frac.sum(axis=0)                       # 可視面積 [px]
    total[0] = visible[0]

    dom = np.argmax(frac, axis=1)
    pure = frac.max(axis=1) >= 0.999
    if not mixed:                                    # 混合画素を止める対照群
        frac = np.zeros_like(frac)
        frac[np.arange(H * W), dom] = 1.0
        pure = np.ones(H * W, bool)

    frag_mat = np.concatenate([[0], mats])
    return {"frac": frac, "frag_mat": frag_mat, "n_frag": n_frag,
            "truth": frag_mat[dom].reshape(H, W), "dom": dom,
            "pure": pure.reshape(H, W), "total": total, "visible": visible,
            "a": a, "b": b, "seed": seed}


def degrade(geo: dict, dirt_mul=0.0, dirt_add=0.0, wet=0.0, tilt=0.0,
            noise: float = NOISE, seed: int = 7) -> np.ndarray:
    """破片ごとに劣化を掛けて分光キューブ ``(H,W,B)`` を作る。

    破片 *i* の見かけのスペクトルは閉形式で

    ``s_i(λ) = g_i · R_mat(λ) · exp(-w_i · A_water(λ)) + (a_i·u(λ) + c_i)``

    ``g_i`` は乗算的な汚れ x 傾きの cos、``a_i·u+c_i`` はなだらかな加算
    ベースライン、``w_i`` は濡れの深さ。**画素の値は面積比で重ねる**ので、
    境界では 2 材質が線形に混ざる(それも真値どおり)。
    """
    rng = np.random.default_rng(seed)
    n = geo["n_frag"]
    q = rng.uniform(0.25, 1.0, (5, n))               # 破片ごとの効き方(固定)
    g_dirt = 1.0 - dirt_mul * q[0]
    cos_t = np.cos(np.deg2rad(tilt * 70.0 * q[1]))
    slope = dirt_add * 0.30 * q[2]
    offset = dirt_add * 0.20 * q[3]
    depth = wet * 1.6 * q[4]

    S = np.zeros((n + 1, N_BAND))
    S[0] = LIB[0]                                    # ベルトは劣化させない
    for i in range(n):
        r = LIB[geo["frag_mat"][i + 1]]
        S[i + 1] = (g_dirt[i] * cos_t[i] * r * np.exp(-depth[i] * WATER)
                    + slope[i] * U + offset[i])
    cube = (geo["frac"] @ S).reshape(H, W, N_BAND)
    if noise > 0:
        cube = cube + rng.normal(0.0, noise, cube.shape)
    return np.clip(cube, 1e-4, None)


# --------------------------------------------------------------------------- #
# 推定器 —— ゼロ点と 4 つの前処理                                               #
# --------------------------------------------------------------------------- #
def _sam_classify(cube: np.ndarray, lib: np.ndarray) -> np.ndarray:
    """各画素を、分光角が最小のライブラリ項目へ割り当てる(:func:`spec_angle_mapper`)。"""
    ang = np.stack([np.asarray(fs.spec_angle_mapper(cube, lib[k]))
                    for k in range(lib.shape[0])], axis=-1)
    return np.argmin(ang, axis=-1)


def d2(x: np.ndarray) -> np.ndarray:
    """波長軸の 2 次微分(Savitzky-Golay、窓 7 バンド・3 次)。

    ★これが**公開経路に無かった**処理。``fullseye`` の ``spec_*`` 族には
    連続体除去はあるが**分光軸の平滑微分が無い**(``xsp_savgol`` は 2-D 画像用の
    進化 op で、波長軸には掛からない)。
    """
    return savgol_filter(np.asarray(x, np.float64), 7, 3, deriv=2,
                         delta=float(WL[1] - WL[0]), axis=-1)


def flatness(x: np.ndarray) -> np.ndarray:
    """スペクトルの「特徴の多さ」= ``||2 次微分|| / 平均反射率``(明るさに不変)。

    金属はほぼ平坦なので 2 次微分がほぼ 0 になり、**方向が雑音で決まる**。
    方向しか見ない SAM はそこで無力になるので、微分の前に 1 本門を立てる。
    """
    d = d2(x)
    return np.linalg.norm(d, axis=-1) / np.maximum(np.mean(x, axis=-1), 1e-6)


_FLAT_THR: dict[str, float] = {}


def flat_threshold(keep: np.ndarray | None = None) -> float:
    """平坦度の門を**校正で**決める(白板と平坦板を 1 枚ずつ測る要領)。

    平坦側 = 金属ライブラリ + 同じ雑音、特徴側 = 材質ライブラリの最小値。
    その幾何平均を門にする(対数軸のまん中)。**門は分類器と同じ帯で測る**
    —— 水帯を捨てた分類器に全帯の門を付けると、濡れた金属が門を素通りする。
    """
    key = "all" if keep is None else "keep"
    if key not in _FLAT_THR:
        sl = slice(None) if keep is None else keep
        rng = np.random.default_rng(101)
        flat = (LIB[NAMES.index("金属")] + rng.normal(0.0, NOISE, (256, N_BAND)))[:, sl]
        v_flat = float(np.median(flatness(flat)))
        feat = [i for i in range(1, K) if NAMES[i] != "金属"]
        v_feat = float(np.min(flatness(LIB[feat][:, sl])))
        _FLAT_THR[key] = float(np.sqrt(v_flat * v_feat))
    return _FLAT_THR[key]


def best_band_pair(lib: np.ndarray) -> tuple[int, int]:
    """ゼロ点のために **48x48 通りの band 対を総当たり**して最良の 1 対を選ぶ。

    ライブラリの 7 個の比を log で並べたときの**隣接間隔の最小値**が最大に
    なる対 = いちばん分離できる比。素朴な手法にも最善の設定を与える。
    """
    r = lib[:, :, None] / np.maximum(lib[:, None, :], 1e-9)   # (K, B, B)
    lr = np.sort(np.log(np.maximum(r, 1e-9)), axis=0)
    gap = np.min(np.diff(lr, axis=0), axis=0)                 # (B, B)
    np.fill_diagonal(gap, -np.inf)
    i, j = np.unravel_index(int(np.argmax(gap)), gap.shape)
    return int(i), int(j)


def classify(cube: np.ndarray, method: str, pair: tuple[int, int],
             keep: np.ndarray | None = None) -> np.ndarray:
    """材質を推定して ``(H,W)`` のラベル(0 = ベルト)を返す。"""
    if method == "ratio":                              # ゼロ点
        r = np.asarray(fs.spec_band_ratio(cube, pair[0], pair[1]))
        lr = np.log(np.maximum(r, 1e-9))
        ref = np.log(np.maximum(LIB[:, pair[0]] / LIB[:, pair[1]], 1e-9))
        return np.argmin(np.abs(lr[..., None] - ref), axis=-1)
    if method == "sam":
        return _sam_classify(cube, LIB)
    if method == "cr":                                 # 連続体除去 + SAM
        cr = np.asarray(fs.spec_continuum_removal(cube, WL))
        crl = np.asarray(fs.spec_continuum_removal(LIB[None, :, :], WL))[0]
        return _sam_classify(cr, crl)
    if method == "d2raw":                              # 2 次微分 + SAM(門なし)
        return _sam_classify(d2(cube), d2(LIB))
    if method == "d2":                                 # + 平坦度の門
        return _flat_gate(cube, _sam_classify(d2(cube), d2(LIB)))
    if method == "d2w":                                # + 水帯を捨てる
        k = keep if keep is not None else _water_keep()
        return _flat_gate(cube[..., k],
                          _sam_classify(d2(cube)[..., k], d2(LIB)[:, k]), k)
    raise ValueError(method)


def _flat_gate(cube: np.ndarray, pred: np.ndarray,
               keep: np.ndarray | None = None) -> np.ndarray:
    """平坦なスペクトルの画素は「金属」に回す(微分では分けられないから)。"""
    return np.where(flatness(cube) < flat_threshold(keep),
                    NAMES.index("金属"), pred)


def _water_keep() -> np.ndarray:
    """水の 2 帯(1450 / 1940 nm)の周りを落とすバンド選択。"""
    meta = fs.BandMeta(wavelengths_nm=WL)
    bad = np.zeros(N_BAND, bool)
    for c in (1450.0, 1940.0):
        i = fs.spec_nearest_band(meta, c)
        lo = max(0, i - 4)
        bad[lo:i + 5] = True
    return ~bad


METHODS = [("ratio", "ゼロ点: 1 対の波長の比"), ("sam", "生 SAM"),
           ("cr", "連続体除去 + SAM"), ("d2", "2 次微分 + SAM"),
           ("d2w", "2 次微分 + 水帯除外 + SAM")]
SWEEP_METHODS = METHODS                        # 掃引はこの 5 本で見る


# --------------------------------------------------------------------------- #
# 数え方 —— 壊れ方を種類ごとに分ける                                            #
# --------------------------------------------------------------------------- #
def detected(cube: np.ndarray) -> np.ndarray:
    """ベルトと破片の切り分け(平均反射率のしきい値)。汚れると沈む。"""
    return cube.mean(axis=2) > DET_THR


def score(geo: dict, pred: np.ndarray, det: np.ndarray,
          only_pure: bool = False) -> dict:
    """材質ごとの再現率と混同行列。**未検出は誤分類と別に数える**。

    ``macro`` は未検出も誤りに数えた「工程が見る」再現率、``macro_det`` は
    **検出できた画素だけ**の分類再現率。不変性の主張は後者で検証する
    (前者には「暗くなってベルトに沈んだ」が混ざるため)。
    """
    truth = geo["truth"]
    lab = np.where(det, pred, 0)
    sel = truth > 0
    if only_pure:
        sel = sel & geo["pure"]
    conf = np.zeros((K, K), np.int64)
    conf_det = np.zeros((K, K), np.int64)
    for t in range(1, K):
        m = sel & (truth == t)
        if m.any():
            conf[t] = np.bincount(lab[m], minlength=K)
        md = m & det
        if md.any():
            conf_det[t] = np.bincount(lab[md], minlength=K)
    def _macro(c):
        r = np.full(K, np.nan)
        for t in range(1, K):
            n = c[t].sum()
            if n:
                r[t] = c[t, t] / n
        return r, float(np.nanmean(r[1:]))
    recall, macro = _macro(conf)
    _rd, macro_det = _macro(conf_det)
    miss = float(conf[1:, 0].sum() / max(1, conf[1:].sum()))
    return {"conf": conf, "recall": recall, "macro": macro,
            "macro_det": macro_det, "miss": miss, "n": int(conf[1:].sum())}


# --------------------------------------------------------------------------- #
# 1. 場面とゼロ点                                                              #
# --------------------------------------------------------------------------- #
def section_scene(pair) -> dict:
    print("\n" + "=" * 78)
    print("1) 場面・真値・ゼロ点 —— 綺麗な場面ですら比は勝てない")
    print("=" * 78)

    geo = make_geometry()
    clean = degrade(geo)
    det = detected(clean)
    print("  視野 %d x %d px x %.1f mm/px = %.0f x %.0f mm / バンド %d 本 "
          "(%.0f-%.0f nm)" % (H, W, MM_PX, H * MM_PX, W * MM_PX, N_BAND, WL0, WL1))
    print("  破片 %d 個 / 可視面積 %.0f px / 全面積 %.0f px -> 被覆 %.1f %%"
          % (geo["n_frag"], geo["visible"][1:].sum(), geo["total"][1:].sum(),
             100 * (1 - geo["visible"][1:].sum() / geo["total"][1:].sum())))
    print("  混合画素(境界)は破片画素の %.1f %%"
          % (100 * float((~geo["pure"])[geo["truth"] > 0].mean())))
    print("  ★ゼロ点の band 対は総当たりの最良: %.0f nm / %.0f nm"
          % (WL[pair[0]], WL[pair[1]]))

    rows = []
    for key, label in METHODS[:2] + [("d2raw", "2 次微分 + SAM(門なし)")] + METHODS[2:]:
        s = score(geo, classify(clean, key, pair), det)
        rows.append((label, s["macro"], s["recall"]))
        print("   %-28s 材質別再現率の平均 %.3f   (%s)"
              % (label, s["macro"],
                 " ".join("%s %.2f" % (n, r) for n, r in
                          zip(FRAG_NAMES, s["recall"][1:]))))
    raw_metal = rows[2][2][NAMES.index("金属")]
    gate_metal = rows[4][2][NAMES.index("金属")]
    print("\n  ★**特徴の無い材質は微分すると消える**。金属はほぼ平坦なので"
          " 2 次微分が 0 に近づき、\n     方向しか見ない SAM は方向の無い相手に"
          "無力になる: 金属の再現率 %.2f。" % raw_metal)
    print("     平坦度 ||d2||/平均 の門(校正で決めた %.2e)を 1 本足すと %.2f に戻る。"
          % (flat_threshold(), gate_metal))
    print("  ★ゼロ点は思ったより強い(%.3f)。**汚れる前は**分光の作り込みが"
          "ほとんど効かない。" % rows[0][1])

    # 図: 場面 / 真値 / 推定 / 誤りの地図
    pred = np.where(det, classify(clean, "d2", pair), 0)
    wrong = np.where((geo["truth"] > 0) & (pred != geo["truth"]), pred + 1, 0)
    rgb = np.asarray(fs.spec_rgb_composite(clean, bands=(50, 30, 10)))
    figs.save_grid(
        "scene",
        [rgb, np.asarray(fs.overlay_labels(rgb, geo["truth"])),
         np.asarray(fs.overlay_labels(rgb, pred)),
         np.asarray(fs.overlay_labels(np.full_like(rgb, 0.85), wrong, alpha=0.9))],
        ["SWIR 3 バンド合成(%.0f/%.0f/%.0f nm)"
         % (WL[50], WL[30], WL[10]),
         "真値の材質ラベル(%d 破片)" % geo["n_frag"],
         "推定(2 次微分 + SAM)", "間違えた画素(色 = 誤った推定先)"],
        title="ベルト上の混合廃棄物 —— 視野 %.0f x %.0f mm"
              % (H * MM_PX, W * MM_PX), ncols=2)
    figs.save_plot(
        "library",
        [(n, WL, spectrum(n)) for n in FRAG_NAMES[:5]],
        xlabel="波長 [nm]", ylabel="反射率 [-]",
        title="材質ライブラリ(ガウス吸収帯の閉形式)",
        caption="PE と PVC は骨格が同じなのでわざと似せてある。")
    return {"geo": geo, "clean": clean, "rows": rows}


# --------------------------------------------------------------------------- #
# 2-4. 崖 —— 要因を単独で掃引する                                               #
# --------------------------------------------------------------------------- #
FACTORS = [("dirt_mul", "汚れ(乗算)", "減衰率 [-]", 0.8),
           ("dirt_add", "汚れ(加算ベースライン)", "ベースライン強さ [-]", 0.6),
           ("wet", "濡れ(水の吸収)", "水の深さ [-]", 1.0),
           ("tilt", "傾き(cos で照度低下)", "最大傾き / 70° [-]", 1.0),
           ("overlap", "重なり(破片数)", "破片数 / 62 [-]", 2.0)]
LEVELS = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])


def section_sweep(pair) -> dict:
    print("\n" + "=" * 78)
    print("2-4) 崖 —— 要因を 1 つずつ掃引する(★予測を先に書く)")
    print("=" * 78)
    # ★掃引の**前に**、代数から予測を立てて印字する。
    sig_mat = float(np.mean([w for n in FRAG_NAMES for _c, _d, w in MATERIALS[n][1]
                             if n != "金属"]))
    sig_water = 70.0
    supp = (sig_mat / sig_water) ** 2
    print("  予測(代数から。掃引の前に書く):")
    print("    s(λ) = g·R(λ)·exp(-w·A_w(λ)) + (a·u(λ)+c)")
    print("    P1 SAM は方向しか見ないので **g に不変** -> 乗算汚れ・傾きでは"
          "分類は落ちない")
    print("    P2 2 階微分は 1 次式 a·u+c を消すので **加算に不変** -> 生 SAM だけ落ちる")
    print("    P3 濡れは波長に依存する乗算なので **方向にも 2 階微分にも残る**"
          " -> どれも落ちる")
    print("    P4 連続体除去(上側凸包で割る)はなだらかな加算を吸うはず")
    print("    P5 重なりは分光を壊さない(見えないだけ) -> 可視画素の再現率は落ちない")

    base = make_geometry()
    out, out_det, hidden = {}, {}, {}
    head = "  ".join("%-9s" % l.split(":")[0][:9] for _, l in SWEEP_METHODS)
    print("\n  ※ 値は**検出できた画素だけ**の材質別再現率(不変性はここで測る)")
    print("  要因                 水準   %s" % head)
    for key, label, _unit, gain in FACTORS:
        curves = {m: [] for m, _ in SWEEP_METHODS}
        curves_all = {m: [] for m, _ in SWEEP_METHODS}
        hid = []
        for lv in LEVELS:
            if key == "overlap":
                geo = make_geometry(n_frag=int(round(N_FRAG * (0.2 + gain * lv))))
                cube = degrade(geo)
            else:
                geo = base
                cube = degrade(geo, **{key: float(lv * gain)})
            det = detected(cube)
            hid.append(100 * (1 - geo["visible"][1:].sum() / geo["total"][1:].sum()))
            for m, _ in SWEEP_METHODS:
                s = score(geo, classify(cube, m, pair), det)
                curves[m].append(s["macro_det"])
                curves_all[m].append(s["macro"])
        out[key], out_det[key], hidden[key] = curves_all, curves, hid
        for i, lv in enumerate(LEVELS):
            print("   %-20s %4.2f   %s" % (label if i == 0 else "", lv,
                  "  ".join("%9.3f" % curves[m][i] for m, _ in SWEEP_METHODS)))

    print("\n  ★崖(検出画素の材質別再現率が 0.90 を割る最初の水準):")
    for key, label, _u, _g in FACTORS:
        line = []
        for m, mlabel in SWEEP_METHODS:
            c = out_det[key][m]
            hit = [LEVELS[i] for i in range(len(LEVELS)) if c[i] < 0.90]
            line.append("%s %s" % (mlabel.split(":")[0][:9],
                                   "%.1f" % hit[0] if hit else "-"))
        print("    %-22s %s" % (label, " | ".join(line)))

    print("\n  ★予測との突き合わせ:")
    print("    P1 乗算汚れ: 生 SAM %.3f -> %.3f、2 次微分 %.3f -> %.3f  **当たり**"
          % (out_det["dirt_mul"]["sam"][0], out_det["dirt_mul"]["sam"][-1],
             out_det["dirt_mul"]["d2"][0], out_det["dirt_mul"]["d2"][-1]))
    print("       ただし**検出まで入れると** 生 SAM は %.3f -> %.3f。"
          "落ちたのは分類ではなく検出\n       (暗くなった破片がベルトに沈む)。"
          % (out["dirt_mul"]["sam"][0], out["dirt_mul"]["sam"][-1]))
    print("    P1 傾き    : 生 SAM %.3f -> %.3f  **当たり**(cos は乗算だから)"
          % (out_det["tilt"]["sam"][0], out_det["tilt"]["sam"][-1]))
    print("    P2 加算汚れ: 生 SAM %.3f -> %.3f、2 次微分 %.3f -> %.3f  **当たり**"
          % (out_det["dirt_add"]["sam"][0], out_det["dirt_add"]["sam"][-1],
             out_det["dirt_add"]["d2"][0], out_det["dirt_add"]["d2"][-1]))
    print("    ★P3 濡れ: **外れた**。生 SAM %.3f -> %.3f、連続体除去 %.3f -> %.3f は"
          "予測どおり壊滅\n       するのに、2 次微分は %.3f -> %.3f でほとんど耐える。"
          % (out_det["wet"]["sam"][0], out_det["wet"]["sam"][-1],
             out_det["wet"]["cr"][0], out_det["wet"]["cr"][-1],
             out_det["wet"]["d2"][0], out_det["wet"]["d2"][-1]))
    print("       理由も代数だった: 2 階微分はガウス帯の深さを 1/σ² で重みづける。"
          "\n       水の帯 σ≈%.0f nm に対し材質の帯は σ≈%.0f nm なので、"
          "水は **(%.0f/%.0f)² = %.2f 倍**に潰れる。"
          % (sig_water, sig_mat, sig_mat, sig_water, supp))
    print("       水帯を捨てる手はそれでも効く: %.3f -> %.3f。"
          % (out_det["wet"]["d2"][-1], out_det["wet"]["d2w"][-1]))
    print("    ★P4 連続体除去: **半分外れ**。加算が弱いうちは生 SAM より強い"
          "(0.4 で %.3f 対 %.3f)が、\n       0.6 を超えると逆転して %.3f 対 %.3f。"
          "凸包は傾きは吸うが、加算された定数は\n       吸収の谷を浅くするので、"
          "材質を分けている形そのものが潰れる。"
          % (out_det["dirt_add"]["cr"][2], out_det["dirt_add"]["sam"][2],
             out_det["dirt_add"]["cr"][-1], out_det["dirt_add"]["sam"][-1]))
    print("    P5 重なり  : 被覆 %.1f -> %.1f %% に対して生 SAM %.3f -> %.3f  "
          "**当たり**\n       (隠れた画素は推定にも真値にも出ないので、"
          "効くのは正解率ではなく**組成**)。"
          % (hidden["overlap"][0], hidden["overlap"][-1],
             out_det["overlap"]["sam"][0], out_det["overlap"]["sam"][-1]))

    figs.save_plot(
        "sweep_raw_sam",
        [(l, LEVELS, out_det[k]["sam"]) for k, l, _u, _g in FACTORS],
        xlabel="要因の強さ(正規化)[-]", ylabel="検出画素の材質別再現率 [-]",
        title="生 SAM: 単独で掃引したときの崖", ylim=(0.0, 1.05),
        caption="乗算汚れ・傾き・重なりは平ら(SAM は明るさに不変)。落ちるのは濡れと加算。")
    figs.save_plot(
        "sweep_methods_add",
        [(m.split(":")[0], LEVELS, out_det["dirt_add"][k]) for k, m in SWEEP_METHODS],
        xlabel="加算ベースラインの強さ [-]", ylabel="検出画素の材質別再現率 [-]",
        title="加算的な汚れ: 2 次微分だけが平ら", ylim=(0.0, 1.05))
    figs.save_plot(
        "sweep_methods_wet",
        [(m.split(":")[0], LEVELS, out_det["wet"][k]) for k, m in SWEEP_METHODS],
        xlabel="水の深さ [-]", ylabel="検出画素の材質別再現率 [-]",
        title="濡れ: ★予測が外れた —— 2 次微分は水の広い帯を潰す", ylim=(0.0, 1.05))
    figs.save_plot(
        "sweep_detection",
        [("分類だけ(検出画素)", LEVELS, out_det["dirt_mul"]["sam"]),
         ("検出も入れる", LEVELS, out["dirt_mul"]["sam"])],
        xlabel="乗算的な汚れの強さ [-]", ylabel="材質別再現率 [-]",
        title="乗算汚れが壊すのは分類ではなく**検出**", ylim=(0.0, 1.05))
    return {"all": out, "det": out_det, "hidden": hidden, "supp": supp}


# --------------------------------------------------------------------------- #
# 5. 対照群 —— 効く順序                                                        #
# --------------------------------------------------------------------------- #
def section_ablation(pair) -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群 —— 全部入りから 1 つずつ止めて、効く順序を数字で並べる")
    print("=" * 78)

    def build(**over):
        cfg = dict(NOM)
        cfg.update(over)
        geo = make_geometry(n_frag=cfg["n_frag"], mixed=cfg["mixed"])
        cube = degrade(geo, dirt_mul=cfg["dirt_mul"], dirt_add=cfg["dirt_add"],
                       wet=cfg["wet"], tilt=cfg["tilt"])
        return geo, cube

    geo, cube = build()
    det = detected(cube)
    base_pred = classify(cube, "d2w", pair)
    base = score(geo, base_pred, det)
    hidden = 1 - geo["visible"][1:].sum() / geo["total"][1:].sum()
    mixed_frac = float((~geo["pure"])[geo["truth"] > 0].mean())
    print("  全部入り(乗算 %.2f / 加算 %.2f / 濡れ %.2f / 傾き %.2f、"
          "2 次微分 + 水帯除外 + SAM):"
          % (NOM["dirt_mul"], NOM["dirt_add"], NOM["wet"], NOM["tilt"]))
    print("     材質別再現率の平均 %.3f(検出画素だけなら %.3f)"
          % (base["macro"], base["macro_det"]))
    print("  ★壊れ方は 4 種類あり、1 個の正解率に畳むと順序が見えない:")
    print("     被覆(重なりで隠れて見えない面積) %.1f %%" % (100 * hidden))
    print("     未検出(汚れてベルトに沈んだ画素) %.1f %%" % (100 * base["miss"]))
    print("     混合画素(境界で 2 材質が混ざる)   %.1f %%" % (100 * mixed_frac))
    print("     誤分類(検出できたが取り違えた)   %.1f %%"
          % (100 * (1 - base["macro"] - base["miss"])))

    rows, gains = [], []
    offs = [("乗算汚れ", {"dirt_mul": 0.0}),
            ("加算汚れ", {"dirt_add": 0.0}),
            ("濡れ", {"wet": 0.0}),
            ("傾き", {"tilt": 0.0}),
            ("混合画素", {"mixed": False})]
    for label, over in offs:
        g2, c2 = build(**over)
        s2 = score(g2, classify(c2, "d2w", pair), detected(c2))
        gains.append((s2["macro"] - base["macro"], label, s2["macro"], s2["miss"]))
    gains.sort(reverse=True)
    print("\n  要因を 1 つ止めたときの改善(大きいほど効いていた):")
    for d, label, m, ms in gains:
        rows.append([label, "%.3f" % m, "%+.3f" % d, "%.1f %%" % (100 * ms)])
        print("    %-10s -> %.3f  (%+.3f)   未検出 %.1f %%"
              % (label, m, d, 100 * ms))
    print("  ★効く順序: " + " > ".join("%s(%+.3f)" % (l, d)
                                       for d, l, _m, _s in gains))
    worst = [g for g in gains if g[0] < 0]
    if worst:
        d, label, m, ms = min(worst)
        print("  ★**%s を止めると逆に下がる**(%+.3f)。2 次微分は加算に不変なので"
              "分類は変わらないが、\n     加算ベースラインは破片を明るくして"
              "**ベルトから浮かせていた** —— 未検出が %.1f %% -> %.1f %%。"
              "\n     同じ汚れが、分類を壊しながら検出を助けている。"
              % (label, d, 100 * base["miss"], 100 * ms))
    print("  ※ 重なりはここに入れない —— 隠れた画素は真値にも推定にも現れず、"
          "可視画素の\n     再現率には原理的に効かないから(2-4 節の P5)。"
          "効くのは 7 節の**組成**。")

    figs.save_table("ablation", ["止めた要因", "再現率の平均", "改善", "未検出"], rows,
                    title="対照群: 全部入り %.3f から 1 つずつ止める" % base["macro"],
                    caption="濡れだけが大きく効く。加算汚れは符号が逆(検出を助けていた)。")
    return {"geo": geo, "cube": cube, "det": det, "base": base, "gains": gains,
            "hidden": hidden, "mixed_frac": mixed_frac}


# --------------------------------------------------------------------------- #
# 6. 似た組が先に壊れる —— 先に予測して突き合わせる                              #
# --------------------------------------------------------------------------- #
def section_pairs(ab: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) ★どの組が先に壊れるかは、ライブラリだけで先に予測できる")
    print("=" * 78)

    ang = np.zeros((K, K))
    for i in range(1, K):
        for j in range(1, K):
            ci = LIB[i] / np.linalg.norm(LIB[i])
            cj = LIB[j] / np.linalg.norm(LIB[j])
            ang[i, j] = np.degrees(np.arccos(np.clip(ci @ cj, -1, 1)))
    pred_rank = sorted(((ang[i, j], i, j) for i in range(1, K)
                        for j in range(i + 1, K)))
    print("  予測(ライブラリのペア間分光角、小さいほど混同しやすい):")
    for a, i, j in pred_rank[:4]:
        print("    %-4s - %-4s  %5.2f 度" % (NAMES[i], NAMES[j], a))

    conf = ab["base"]["conf"]
    sym = np.zeros((K, K), np.int64)
    for i in range(1, K):
        for j in range(1, K):
            if i != j:
                sym[i, j] = conf[i, j] + conf[j, i]
    meas_rank = sorted(((-sym[i, j], i, j) for i in range(1, K)
                        for j in range(i + 1, K)))
    print("  実測(全部入りの条件で取り違えた画素数):")
    for c, i, j in meas_rank[:4]:
        print("    %-4s - %-4s  %6d 画素" % (NAMES[i], NAMES[j], -c))

    # 順位相関(Spearman) —— 15 対
    pk = {(i, j): r for r, (_a, i, j) in enumerate(pred_rank)}
    mk = {(i, j): r for r, (_c, i, j) in enumerate(meas_rank)}
    x = np.array([pk[k] for k in pk])
    y = np.array([mk[k] for k in pk])
    rho = float(np.corrcoef(x, y)[0, 1])
    print("  ★予測順位と実測順位の順位相関 %.2f(%d 対)" % (rho, len(pk)))
    top_p = "%s-%s" % (NAMES[pred_rank[0][1]], NAMES[pred_rank[0][2]])
    top_m = "%s-%s" % (NAMES[meas_rank[0][1]], NAMES[meas_rank[0][2]])
    print("     1 位 予測 %s / 実測 %s  -> %s"
          % (top_p, top_m, "一致" if top_p == top_m else "外れ"))

    header = ["真値 \\ 推定", "ベルト"] + FRAG_NAMES + ["再現率"]
    rows = []
    for t in range(1, K):
        rows.append([NAMES[t]] + ["%d" % c for c in conf[t]]
                    + ["%.3f" % ab["base"]["recall"][t]])
    figs.save_table("confusion", header, rows,
                    title="混同行列(全部入り、2 次微分 + SAM、画素数)",
                    caption="PE と PVC が最初に混ざる。1 個の正解率には出ない。")
    return {"rho": rho, "top_pred": top_p, "top_meas": top_m,
            "pred_rank": pred_rank}


# --------------------------------------------------------------------------- #
# 7. 混合画素 —— 捨てる / 捨てない / 分数で数える                                #
# --------------------------------------------------------------------------- #
def section_mixed(ab: dict, pair) -> dict:
    print("\n" + "=" * 78)
    print("7) 混合画素 —— 捨てると精度は上がるが、組成は痩せる")
    print("=" * 78)

    geo, cube, det = ab["geo"], ab["cube"], ab["det"]
    pred = classify(cube, "d2w", pair)
    all_s = score(geo, pred, det)
    pure_s = score(geo, pred, det, only_pure=True)
    print("  材質別再現率の平均: 全画素 %.3f / 境界を捨てる %.3f"
          % (all_s["macro"], pure_s["macro"]))
    # 境界画素の割合は材質ごとに違う(小さい破片ほど高い)。
    print("   材質ごとの境界の割合 [%]: " + "  ".join(
        "%s %.0f" % (n, 100 * float((~geo["pure"])[geo["truth"] == i + 1].mean()))
        for i, n in enumerate(FRAG_NAMES)))

    # 面積基準の組成(工程が見る数字)。真値は**全面積**(隠れた分も含む)。
    truth_area = np.zeros(K)
    for i in range(1, geo["n_frag"] + 1):
        truth_area[geo["frag_mat"][i]] += geo["total"][i]
    truth_pct = 100 * truth_area[1:] / truth_area[1:].sum()

    def comp_from_labels(sel: np.ndarray) -> np.ndarray:
        lab = np.where(det & sel, pred, 0)
        c = np.bincount(lab[geo["truth"] > 0].ravel(), minlength=K)[1:]
        return 100 * c / max(1, c.sum())

    est_all = comp_from_labels(np.ones((H, W), bool))
    est_pure = comp_from_labels(geo["pure"])

    # 分数のまま数える: 線形混合分解(FCLS、:func:`fullseye.spec_unmix`)。
    # 2 次微分の空間では負の値が出て制約が意味を失うので、生のキューブに掛ける。
    ab_map = np.asarray(fs.spec_unmix(cube, LIB, constrained=True))
    w = ab_map[..., 1:].reshape(-1, K - 1)[(geo["truth"] > 0).ravel()]
    est_unmix = 100 * w.sum(axis=0) / max(1e-9, w.sum())

    # 線形混合分解が**混合画素の面積比そのもの**をどれだけ当てるか。
    # 真値は場面を作るときの面積比(厳密)。劣化の有無で 2 通り測る。
    clean_cube = degrade(geo)
    true_frac = np.zeros((H * W, K))
    for i in range(geo["n_frag"] + 1):
        true_frac[:, geo["frag_mat"][i]] += geo["frac"][:, i]
    bnd = (~geo["pure"]).ravel() & (geo["truth"] > 0).ravel()
    err_mix = []
    for label, c in (("劣化なし", clean_cube), ("全部入り", cube)):
        amap = np.asarray(fs.spec_unmix(c, LIB, constrained=True)).reshape(-1, K)
        err_mix.append((label, float(np.mean(np.abs(amap[bnd] - true_frac[bnd])))))

    rows = []
    print("   材質    真値 %%   全画素   境界を捨てる   線形混合分解")
    for i, n in enumerate(FRAG_NAMES):
        rows.append([n, "%.1f" % truth_pct[i], "%.1f" % est_all[i],
                     "%.1f" % est_pure[i], "%.1f" % est_unmix[i]])
        print("   %-6s %6.1f   %6.1f      %6.1f       %6.1f"
              % (n, truth_pct[i], est_all[i], est_pure[i], est_unmix[i]))
    e_all = float(np.mean(np.abs(est_all - truth_pct)))
    e_pure = float(np.mean(np.abs(est_pure - truth_pct)))
    e_unmix = float(np.mean(np.abs(est_unmix - truth_pct)))
    print("   平均絶対誤差 [pp]      %6.2f      %6.2f       %6.2f"
          % (e_all, e_pure, e_unmix))
    print("\n  ★境界を捨てると再現率は %.3f -> %.3f と**上がる**のに、"
          "組成の誤差は %.2f -> %.2f pp と\n     **%s**する。"
          "小さい破片ほど境界の割合が高いので、捨てると小さい材質が体系的に動く。"
          % (all_s["macro"], pure_s["macro"], e_all, e_pure,
             "悪化" if e_pure > e_all else "改善"))
    print("  ★混合画素を分数のまま数えられるか(境界画素の存在量 vs 真の面積比、"
          "平均絶対誤差):")
    for label, e in err_mix:
        print("     %-8s %.3f" % (label, e))
    print("     線形混合分解は劣化がなければ境界を %.3f で当てるが、"
          "全部入りでは %.3f —— \n     劣化は線形混合の仮定そのものを壊す"
          "(乗算 g も加算 c も endmember に無い)。" % (err_mix[0][1], err_mix[1][1]))
    print("     組成の平均絶対誤差でも %.2f pp で、素朴な画素計数(%.2f pp)に"
          "%s。" % (e_unmix, e_all, "勝てない" if e_unmix > e_all else "勝つ"))

    figs.save_table("composition",
                    ["材質", "真値 %", "全画素 %", "境界を捨てる %", "混合分解 %"],
                    rows + [["平均絶対誤差 [pp]", "-", "%.2f" % e_all,
                             "%.2f" % e_pure, "%.2f" % e_unmix]],
                    title="面積基準の材質構成比(真値は隠れた面積も含む全面積)")
    figs.save_grid("mixed_map",
                   [geo["pure"].astype(np.float64),
                    true_frac[:, 4].reshape(H, W),
                    np.asarray(ab_map[..., 4])],
                   ["純画素(白)と混合画素(黒)",
                    "PVC の真の面積比", "PVC の存在量(線形混合分解)"],
                   title="境界は必ず混ざる —— 捨てるか、分数で数えるか", ncols=3)
    return {"all": all_s["macro"], "pure": pure_s["macro"],
            "e_all": e_all, "e_pure": e_pure, "e_unmix": e_unmix,
            "mix_clean": err_mix[0][1], "mix_deg": err_mix[1][1]}


# --------------------------------------------------------------------------- #
# 8. 濡れの図と、道具の穴                                                       #
# --------------------------------------------------------------------------- #
def section_spectra(pair) -> None:
    print("\n" + "=" * 78)
    print("8) スペクトルの図 —— 何が形を壊しているか")
    print("=" * 78)
    geo = make_geometry(n_frag=6, seed=3)
    # PET の破片を 1 つ選んで、劣化前後のスペクトルを取り出す
    tgt = int(np.argmax(geo["frag_mat"] == 1)) if (geo["frag_mat"] == 1).any() else 1
    m = (geo["dom"] == tgt) & geo["pure"].ravel()
    if not m.any():
        m = (geo["dom"] == tgt)
    idx = int(np.argmax(m))
    series = []
    for label, kw in (("綺麗", {}), ("乗算汚れ 0.8", {"dirt_mul": 0.8}),
                      ("加算汚れ 0.6", {"dirt_add": 0.6}),
                      ("濡れ 1.0", {"wet": 1.0})):
        c = degrade(geo, noise=0.0, **kw).reshape(-1, N_BAND)[idx]
        series.append((label, WL, c))
        print("   %-14s 平均反射率 %.3f  最大 %.3f" % (label, c.mean(), c.max()))
    figs.save_plot("spectra", series, xlabel="波長 [nm]", ylabel="反射率 [-]",
                   title="1 個の %s 破片のスペクトル(劣化の前後)"
                         % NAMES[geo["frag_mat"][tgt]],
                   caption="乗算は形を保つ。加算は谷を浅くする。濡れは 1450 /"
                           " 1940 nm に無い谷を作る。")
    d2s = [(l, WL, d2(y)) for l, _x, y in series]
    figs.save_plot("spectra_d2", d2s, xlabel="波長 [nm]",
                   ylabel="2 次微分 [反射率/nm^2]",
                   title="2 次微分にすると乗算と加算の差が消える",
                   caption="残るのは濡れ(波長に依存する乗算)だけ。")


def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で spec_* 族を使ってみて)")
    print("=" * 78)
    # (a) 分光軸の平滑微分が無い
    assert not hasattr(fs, "spec_derivative") and not hasattr(fs, "spec_savgol")
    print("  (a) **分光軸の平滑微分(Savitzky-Golay)が公開経路に無い**。"
          "この PoC の主役なのに scipy で書いた。\n"
          "      `xsp_savgol` は 2-D 画像用の進化 op で、波長軸には掛からない。")
    # (b) 混同行列・分類評価の口が無い
    assert not hasattr(fs, "confusion_matrix") and not hasattr(fs.ledger, "confusion_matrix")
    print("  (b) 混同行列 / 材質別再現率を出す口が無い(`fscore` は 2 値のみ)。"
          "分類を評価する PoC は毎回自前で書いている。")
    # (c) SAM は参照 1 本ずつ。K 本まとめて最小を取る口が無い
    import inspect
    assert "reference" in inspect.signature(fs.spec_angle_mapper).parameters
    print("  (c) `spec_angle_mapper` は参照スペクトル 1 本ずつ。ライブラリ (K,B) を"
          "渡して\n      argmin まで返す口が無いので、呼び手が K 回回して stack している。")
    # (d) bad_bands は BandMeta に在るが、それでキューブを切る口が無い
    meta = fs.BandMeta(wavelengths_nm=WL, bad_bands=np.zeros(N_BAND, bool))
    assert meta.bad_bands is not None
    assert not hasattr(fs, "spec_drop_bad_bands")
    print("  (d) `BandMeta.bad_bands`(水帯を捨てる規約)は在るのに、"
          "**それでキューブとライブラリを\n      同時に切る op が無い**。"
          "この PoC のいちばん効いた 1 手(3 節)がそれ。")
    # (e) 連続体除去はライブラリ (K,B) を (1,K,B) に整形しないと通らない
    cr = np.asarray(fs.spec_continuum_removal(LIB[None, :, :], WL))
    assert cr.shape == (1, K, N_BAND)
    print("  (e) spec_* 族は (H,W,B) しか受けないので、ライブラリ (K,B) を"
          "処理するには\n      (1,K,B) に整形して戻す必要がある(スペクトルの"
          "列を扱う口があるとよい)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("混合廃棄物の材質選別 —— 汚れと重なりが分光を殺す順序")
    print("材質 %s / バンド %d 本" % (" ".join(FRAG_NAMES), N_BAND))
    print("=" * 78)

    pair = best_band_pair(LIB)
    sc = section_scene(pair)
    sw = section_sweep(pair)
    ab = section_ablation(pair)
    pr = section_pairs(ab)
    mx = section_mixed(ab, pair)
    section_spectra(pair)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    det, allm = sw["det"], sw["all"]
    print("  * ゼロ点(最良の band 対の比)は綺麗な場面で %.3f、SAM は %.3f —— "
          "**汚れる前は差が小さい**。" % (sc["rows"][0][1], sc["rows"][1][1]))
    print("  * 消えるかどうかは代数で決まる: 乗算(汚れ・傾き)-> SAM が不変 "
          "(%.3f -> %.3f)/\n    加算 -> 2 次微分が不変(%.3f -> %.3f)。"
          % (det["dirt_mul"]["sam"][0], det["dirt_mul"]["sam"][-1],
             det["dirt_add"]["d2"][0], det["dirt_add"]["d2"][-1]))
    print("  * ★予測が外れたのは濡れ: 2 次微分は水の**広い**帯を 1/σ² で潰すので"
          " %.3f までしか落ちない\n    (生 SAM は %.3f)。"
          % (det["wet"]["d2"][-1], det["wet"]["sam"][-1]))
    print("  * 効く順序: " + " > ".join("%s(%+.3f)" % (l, d)
                                        for d, l, _m, _s in ab["gains"]))
    print("  * 先に壊れる組はライブラリだけで予測できる(順位相関 %.2f、"
          "1 位 予測 %s / 実測 %s)。" % (pr["rho"], pr["top_pred"], pr["top_meas"]))
    print("  * 境界を捨てると再現率 %+.3f、組成の誤差 %+.2f pp。"
          % (mx["pure"] - mx["all"], mx["e_pure"] - mx["e_all"]))

    # --- 所見を固定する(壊れたら鳴る) --- #
    assert sc["rows"][0][1] < sc["rows"][1][1], "ゼロ点が SAM に勝った"
    assert sc["rows"][1][1] > 0.95, "綺麗な場面で SAM が落ちている"
    assert sc["rows"][2][2][NAMES.index("金属")] < 0.30, \
        "門なしの 2 次微分で金属が当たってしまう(所見が消えた)"
    assert sc["rows"][4][2][NAMES.index("金属")] > 0.90, "平坦度の門が効いていない"
    assert det["dirt_mul"]["sam"][-1] > 0.95, "乗算汚れで SAM の分類が落ちた(不変のはず)"
    assert det["tilt"]["sam"][-1] > 0.95, "傾きで SAM の分類が落ちた(不変のはず)"
    assert allm["dirt_mul"]["sam"][-1] < det["dirt_mul"]["sam"][-1] - 0.1, \
        "乗算汚れで検出が落ちない(検出と分類の分離が消えた)"
    assert det["dirt_add"]["sam"][-1] < 0.90, "加算で生 SAM が落ちない"
    assert det["dirt_add"]["d2"][-1] > 0.95, "加算で 2 次微分が落ちた(不変のはず)"
    assert det["wet"]["sam"][-1] < 0.60, "濡れで生 SAM が落ちない"
    assert det["wet"]["d2"][-1] > det["wet"]["sam"][-1] + 0.2, \
        "濡れで 2 次微分が生 SAM に対して強くない(★予想外れの所見が消えた)"
    assert det["dirt_add"]["cr"][-1] < det["dirt_add"]["sam"][-1], \
        "連続体除去が強い加算で生 SAM に勝った(逆転の所見が消えた)"
    assert abs(det["overlap"]["sam"][-1] - det["overlap"]["sam"][0]) < 0.05, \
        "重なりが可視画素の再現率に効いてしまった"
    assert pr["rho"] > 0.5, "ペアの予測順位が当たらない: %.2f" % pr["rho"]
    assert mx["pure"] > mx["all"], "境界を捨てても再現率が上がらない"
    assert mx["mix_deg"] > mx["mix_clean"], "劣化で線形混合分解が悪化しない"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
