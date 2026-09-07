# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""光切断で溶接ビードを走査する —— 最適な三角測量角は、測定量ごとに違う。

    py -3.11 examples/poc_weld_bead_scan_angle.py

すみ肉溶接の外観検査を、レーザー光切断センサ(ライン光 + 斜めカメラ)で
溶接線に沿って走査する仕事です。出す数字は **余盛(凸み)/ 脚長 左右 /
のど厚 / アンダーカット深さ 左右** の 6 つ。

三角測量角 θ(ライン光の面とカメラ光軸のなす角)を大きくすると高さ分解能は
``1/sin θ`` で良くなりますが、カメラ光線の傾き ``cot θ`` を超えて登る面は
自分の陰に入って**測れなくなります**。分解能と遮蔽は同じノブの表裏で、
**最適角が在る**はず —— それを幾何から先に予測し、掃引で突き合わせます。

【グラウンドトゥルース(閉形式)】
90 度すみ肉継手をセンサ座標で左 53 度・右 37 度に置く(母材面 ``h = tan53·x``
と ``h = -tan37·x``、交線 = 根 (0,0))。溶接面は両つま先を結ぶ弦に放物線の
凸みを載せた曲線、両つま先の外側にガウス形のアンダーカットを掘る。溶接線
方向 y には脚長 L1(y) / L2(y) / 凸み c(y) / 左アンダーカット深さ d1(y) を
既知の関数で変える。**脚長・凸み・アンダーカット深さは式で分かり、のど厚は
根から溶接面までの最短距離を細格子(1/40 画素)で解いて得る。**

撮像は ``col = M·x``、``row = row0 + M·sin θ·(h - h_ref)`` の正射モデル
(M = 20 px/mm)。光条はガウス、雑音・鏡面ローブ・飽和・校正誤差はすべて
既知量として入れる。

EXTEND: 実機に差し替えるなら :func:`render` を撮影画像に、``M`` と ``ROW0``
と θ を校正値に置き換え、:func:`bead_params` の戻り値を「その溶接部の設計
寸法」ではなく**マクロ断面の実測**にする(光切断の真値をレーザーで取っては
いけない —— 同じ誤差源を共有する)。この PoC が入れていない誤差源は 3 つ:
(i) 透視の前縮み(実センサは Scheimpflug で面外に振るので列も高さで少し動く)、
(ii) 測定レンジ ``IMG_H/(M sin θ)`` の頭打ち(分解能と**レンジ**も同じノブの
表裏で、ここでは常に収まる高さに取ってある)、(iii) レーザー側の影(ライン光を
鉛直に立てているので影はカメラ側だけ)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(光条の輝度が最大の画素をそのまま高さにする)は 1 桁負ける**。
   θ = 36 度・雑音 1.5 %・光条 1σ = 1.4 px で高さ RMS は 最大値 0.0251 mm /
   重心 0.0030 mm(8.5 倍)/ 対数放物線 0.0033 mm(7.5 倍)。fullseye の
   ``lines_gauss`` から列ごとに中心を取ると 0.0400 mm で**ゼロ点より悪い**
   —— HALCON の同名 op が返す「中心線 + 線幅」ではなく Frangi リッジの
   二値化なので、サブピクセルが出ない。
2. ★★**光条は細いほど良い —— ただし 0.7 px で床を打つ**。予想は「太いほど
   光量が増えて良い」だったが**逆**。重心の誤差は理論どおり √σ で増える
   (1σ を 0.7 → 2.8 px で 0.0021 → 0.0043 mm、実測比 2.03 対 予測 2.00)。
   細い側は 1σ = 0.5 px で 0.0038 mm へ跳ね返る(標本化の床)。
   ★3 点当てはめ(対数放物線)は幅への感度が桁違いで、同じ範囲で
   0.0011 → 0.0125 mm(**σ^1.83**)—— 幅を知らずに 3 点で済ませる推定量は、
   光条が太る現場で静かに壊れる。
3. ★★**遮蔽の崖は 2 種類あり、形がまるで違う**。幾何から予測: 左母材面は
   傾きが一定 tan53 = 1.327 なので **θ = 37.0 度で全部いっせいに背を向ける**
   (段差の崖)。左アンダーカットは溝の斜面が母材の傾きに上乗せされる分だけ
   早く、**θ = 20.7〜33.6 度から少しずつ欠ける**(なだらかな崖)。実測でも
   左側 4 量の「測れた率」は 36 度の 100 % から 40 度の 0 % へ落ちる。
4. ★★**いちばん深い欠陥がいちばん先に隠れる**。左アンダーカットの予測
   遮蔽開始角は深さ 0.43 mm の断面で 21.1 度、0.06 mm の断面で 32.7 度。
   深い溝ほど斜面が急なので早く陰に入る —— **通してはいけない欠陥から
   消える**。平均だけ見ていると「だいたい測れている」に見える。
5. ★★**最適角は測定量ごとに違い、1 つの角度で全部は取れない**。実測の
   最適角は 右アンダーカット 70 度 / 右脚長 70 度 / 凸み 36 度 /
   のど厚 36 度 / 左脚長 36 度 / 左アンダーカット 28 度。6 量を 1 つの
   平均誤差に畳むとその最適角は 36 度になるが、そこでの左アンダーカット
   誤差は左アンダーカット自身の最適角の 1.9 倍。
6. ★★**校正誤差(高さ倍率 +1 %)の効き方は量ごとに違い、しかも脚長と溝
   深さは同じ母材面で真逆**。予測は 脚長 = sin²(母材角)·ε、アンダーカット
   = cos²(母材角)·ε(**和がちょうど 1**)。左母材(53 度)なら脚長 0.638 % /
   溝 0.362 %、右母材(37 度)なら脚長 0.362 % / 溝 0.638 %。実測は
   0.638 / 0.361 / 0.362 / 0.639 % で予測どおり。「較正精度 1 %」だけでは
   どの量が何 % ずれるかを言えない。
7. ★**法線から描いた遮蔽の地図は、投げかけ影を落とす**。
   ``normals_from_depth`` の法線で「背を向けた面」を数えると θ = 45 度で
   43.9 %、水平線の規則で解いた本当の不可視は 45.1 %(差 1.2 pp = 投げかけ
   影)。★**しかも格子間隔が等方でないと黙って間違える** —— 正射版の
   ``normals_from_depth`` は 1 画素 = 1 単位と決め打つので、x 0.05 mm・
   y 0.5 mm の生の走査格子をそのまま渡すと傾きが 10 倍ずれる。
8. ★のど厚は 3-D の距離場でも測れる。溶接面の点群 → ``occupancy_grid``
   → ``esdf`` → 根の位置で ``query_distance``。閉形式との差は +0.0335 mm
   (ボクセル 0.05 mm の 0.67 個ぶん)で**符号が必ず正** —— 距離場は最近傍
   ボクセル**中心**までを測るので、薄い殻を張ると必ず遠めに出る。

来歴(公開文献のみ): Shirai & Suwa, *IJCAI* (1971) —— 光切断法 /
Trucco, Fisher, Fitzgibbon & Naidu, *Image Vision Comput.* 16 (1998) 99 ——
レーザーストライプの位置推定と自己検証 / Steger, *IEEE TPAMI* 20 (1998) 113
—— 曲線構造の中心線とその幅 / ISO 5817 —— 溶接部の不完全部の等級
(アンダーカットの許容値。本 PoC は等級付けを実装していない)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 継手(90 度すみ肉、センサから見て左 53 度 / 右 37 度)[mm] --------------- #
PLATE_L_DEG, PLATE_R_DEG = 53.0, 37.0
TL = float(np.tan(np.deg2rad(PLATE_L_DEG)))     # 1.327 —— 左母材面の傾き
TR = float(np.tan(np.deg2rad(PLATE_R_DEG)))     # 0.754 —— 右母材面の傾き
CL = float(np.cos(np.deg2rad(PLATE_L_DEG)))     # 0.602
CR = float(np.cos(np.deg2rad(PLATE_R_DEG)))     # 0.799

UC_W_L, UC_W_R = 1.8, 1.4          # アンダーカット溝の幅(つま先から外側へ)[mm]
UC_SPAN_L, UC_SPAN_R = 2.0, 1.6    # つま先から外側へこの範囲を溝とみなす [mm]
TAU = 0.05                         # つま先の判定しきい値(母材面からの落ち込み)

Y_MM = 30.0                        # 走査長 [mm]
N_Y = 16                           # 掃引で使う断面の本数
N_Y_FIG = 60                       # 図・地図で使う断面の本数(Δy = 0.5 mm)

# --- 撮像 -------------------------------------------------------------------- #
X_HALF = 8.0                       # 視野の半幅 [mm]
M_PX_MM = 20.0                     # 横倍率 [px/mm]
N_COL = int(2 * X_HALF * M_PX_MM)  # 320 列
IMG_H = 168                        # 画像の高さ [px]
ROW0 = 10.0                        # h = H_REF が写る行
H_REF = -10.75                     # 行の原点にする高さ [mm]
LINE_SIG = 1.4                     # 光条の 1σ [px]
BG = 0.03                          # 背景
NOISE = 0.015                      # 雑音の 1σ(フルスケール比)
DETECT = 0.25                      # この輝度に届かない列は「測れなかった」
THETA_REF = 36.0                   # 基準の三角測量角 [度]
PLATE_WIN = (6.5, 7.9)             # 母材面を当てはめる |x| の範囲 [mm]
SMOOTH = 7                         # 断面を測る前の平滑(列数 = 0.35 mm)
CHECK_IN, CHECK_DEV = 2.4, -1.0    # つま先の確認: 内側 2.4 mm に溶接金属が在るか

X = -X_HALF + (np.arange(N_COL) + 0.5) / M_PX_MM
KEYS = ("cv", "legL", "legR", "throat", "ucL", "ucR")
LABEL = {"cv": "余盛(凸み)", "legL": "脚長 左", "legR": "脚長 右",
         "throat": "のど厚", "ucL": "UC 深さ 左", "ucR": "UC 深さ 右"}
ANGLES = (15.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 45.0, 50.0, 57.0, 64.0, 70.0)
I_REF = ANGLES.index(THETA_REF)


# --------------------------------------------------------------------------- #
# 1. 真値 —— 溶接線に沿って寸法を変える                                         #
# --------------------------------------------------------------------------- #
def y_grid(n: int) -> np.ndarray:
    return (np.arange(n) + 0.5) * (Y_MM / n)


def bead_params(yv: np.ndarray) -> dict:
    """溶接線位置 y [mm] における断面の設計寸法(これが真値の素)。"""
    yv = np.asarray(yv, np.float64)
    return {"y": yv,
            "L1": 6.2 + 0.7 * np.sin(2 * np.pi * yv / 21.0),
            "L2": 6.0 - 0.9 * (yv / Y_MM),
            "cv": 0.85 + 0.35 * np.cos(2 * np.pi * yv / 17.0),
            "d1": 0.45 * (0.55 + 0.45 * np.sin(2 * np.pi * yv / 26.0 + 0.7)),
            "d2": np.full_like(yv, 0.14)}


def _toes(p: dict):
    """つま先の x 座標(左・右)と、そこでの高さ(= 母材面の値)。"""
    xl = -p["L1"][:, None] * CL
    xr = p["L2"][:, None] * CR
    return xl, xr, TL * xl, -TR * xr


def profile_h(x: np.ndarray, p: dict) -> np.ndarray:
    """断面の真値 h(x) [mm] を (n_y, n_x) で返す。**閉形式・C¹ 連続**。

    母材面(左 53 度 / 右 37 度)+ 両つま先の外側の溝(アンダーカット)+
    つま先どうしを結ぶ弦に放物線の凸みを載せた溶接面。

    ★溝は**有限台の sin²**(幅 UC_W、つま先から外側へ)にしてある。ガウスに
    すると裾がつま先まで残り、「母材面から TAU 以内の点」というつま先の規則が
    溝に飲まれて脚長が数 mm 外へ飛ぶ(最初にガウスで書いて踏んだ)。sin² なら
    つま先で値も傾きもちょうど 0 で、**深さの真値は台の中央でぴったり d**。
    """
    xg = np.asarray(x, np.float64)[None, :]
    xl, xr, zl, zr = _toes(p)
    base = np.where(xg <= 0.0, TL * xg, -TR * xg)
    ul = np.clip((xl - xg) / UC_W_L, 0.0, 1.0)
    ur = np.clip((xg - xr) / UC_W_R, 0.0, 1.0)
    nl = (p["d1"][:, None] / CL) * np.sin(np.pi * ul) ** 2
    nr = (p["d2"][:, None] / CR) * np.sin(np.pi * ur) ** 2
    outer = base - np.where(xg < xl, nl, 0.0) - np.where(xg > xr, nr, 0.0)
    s = (xg - xl) / (xr - xl)
    face = zl + s * (zr - zl) + 4.0 * p["cv"][:, None] * s * (1.0 - s)
    return np.where((xg >= xl) & (xg <= xr), face, outer)


def design_quantities(p: dict) -> dict:
    """設計寸法そのもの(のど厚だけ細格子で解く)—— **図面側の真値**。"""
    xl, xr, zl, zr = _toes(p)
    xf = np.linspace(-X_HALF, X_HALF, 40 * N_COL + 1)
    hf = profile_h(xf, p)
    inside = (xf[None, :] >= xl) & (xf[None, :] <= xr)
    throat = np.min(np.where(inside, np.hypot(xf[None, :], hf), np.inf), axis=1)
    s = (xf[None, :] - xl) / (xr - xl)
    chord = zl + s * (zr - zl)
    cosc = 1.0 / np.hypot(1.0, (zr - zl) / (xr - xl))
    cvx = np.max(np.where(inside, (hf - chord) * cosc, -np.inf), axis=1)
    return {"cv": cvx, "legL": p["L1"].copy(), "legR": p["L2"].copy(),
            "throat": throat, "ucL": p["d1"].copy(), "ucR": p["d2"].copy()}


# --------------------------------------------------------------------------- #
# 2. 撮像 —— 三角測量角 θ が分解能と遮蔽の両方を決める                          #
# --------------------------------------------------------------------------- #
def k_px_mm(theta_deg: float) -> float:
    """高さ感度 K = M·sin θ [px/mm]。**分解能は 1/sin θ で良くなる**。"""
    return M_PX_MM * float(np.sin(np.deg2rad(theta_deg)))


def visible(h: np.ndarray, theta_deg: float) -> np.ndarray:
    """カメラから見える列(水平線の規則)。

    カメラは +x 側の斜め上、鉛直から θ。点 (x, h) は ``x' > x`` のすべてで
    ``h(x') <= h(x) + (x'-x)·cot θ`` のとき見える。右から左への走査最大値
    1 本で判定できる(O(N))—— **自己遮蔽も投げかけ影も両方入る**。
    """
    cot = 1.0 / np.tan(np.deg2rad(theta_deg))
    g = h - X[None, :] * cot
    return np.maximum.accumulate(g[:, ::-1], axis=1)[:, ::-1] <= g + 1e-9


def dh_dx(h: np.ndarray) -> np.ndarray:
    return np.gradient(h, X, axis=1)


def render(p: dict, theta_deg: float, noise: float = NOISE, sigma: float = LINE_SIG,
           specular: float = 0.0, occlusion: bool = True, seed: int = 0):
    """光条の画像 (n_y, IMG_H, N_COL) と、光が返った列のマスクを返す。

    ``specular`` は鏡面ローブの強さ。鏡面条件は「法線がライン光とカメラを
    二等分する」= ``dh/dx = -tan(θ/2)`` の斜面 —— 近側(右)だけが飽和する。
    """
    rng = np.random.default_rng(seed)
    h = profile_h(X, p)
    row_c = ROW0 + k_px_mm(theta_deg) * (h - H_REF)
    amp = np.full(h.shape, 0.85)
    if specular > 0.0:
        phi0 = -np.tan(np.deg2rad(theta_deg) / 2.0)
        amp = amp + specular * np.exp(-((dh_dx(h) - phi0) ** 2) / (2 * 0.35 ** 2))
    vis = visible(h, theta_deg) if occlusion else np.ones(h.shape, bool)
    rows = np.arange(IMG_H)[None, :, None]
    img = amp[:, None, :] * np.exp(-((rows - row_c[:, None, :]) ** 2) / (2 * sigma ** 2))
    img = img * vis[:, None, :] + BG
    img = img + rng.normal(0.0, noise, img.shape)
    return np.clip(img, 0.0, 1.0), vis


# --------------------------------------------------------------------------- #
# 3. 光条の中心を取る —— ゼロ点と 3 つの対比                                    #
# --------------------------------------------------------------------------- #
def _peak(img):
    return img.argmax(axis=1), img.max(axis=1) > DETECT


def est_argmax(img):
    """★ゼロ点 —— 輝度が最大の画素の行をそのまま使う(整数精度)。"""
    k, ok = _peak(img)
    return np.where(ok, k.astype(np.float64), np.nan)


def _centroid(img, weight):
    k, ok = _peak(img)
    rows = np.arange(IMG_H)[None, :, None]
    w = weight(img, k, rows)
    s = w.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = (w * rows).sum(axis=1) / np.maximum(s, 1e-12)
    return np.where(ok & (s > 0), c, np.nan)


HALF_FIX = 8


def est_centroid_fix(img):
    """輝度重心・**固定窓**(±%d 行)。窓が固定なら Σ(r-c)² も固定で、
    分母 ΣI ∝ σ だけが伸びるので誤差は **1/σ** —— 太い光条ほど良い。"""
    return _centroid(img, lambda im, k, r: np.clip(im - BG, 0.0, None)
                     * (np.abs(r - k[:, None, :]) <= HALF_FIX))


def est_centroid_adapt(img, frac=0.25, half=12):
    """輝度重心・**幅に追従する窓**(山の %.0f %% 以上の画素だけ)。窓が σ に
    比例すると Σ(r-c)² ∝ σ³ で分母は σ² なので誤差は **√σ** —— 細いほど良い。"""
    pk = img.max(axis=1)

    def w(im, k, r):
        thr = (BG + frac * np.clip(pk - BG, 0.0, None))[:, None, :]
        return np.where((np.abs(r - k[:, None, :]) <= half) & (im >= thr),
                        np.clip(im - BG, 0.0, None), 0.0)

    return _centroid(img, w)


def est_centroid_raw(img):
    """★対照群 —— 固定窓のまま、**背景を 0 で切り上げない**(負の重みを許す)。

    ``clip(I-BG, 0, None)`` の 1 行は無害に見えるが、雑音の負側だけを捨てる
    ので整流になる。この対照群だけが 1/σ の法則にきれいに乗る(2 章)。
    """
    return _centroid(img, lambda im, k, r: (im - BG)
                     * (np.abs(r - k[:, None, :]) <= HALF_FIX))


est_centroid_fix.__doc__ = est_centroid_fix.__doc__ % HALF_FIX
est_centroid_adapt.__doc__ = est_centroid_adapt.__doc__ % 25
est_centroid = est_centroid_fix     # 以降の章で使う既定の推定量


def est_log_parabola(img):
    """背景を引いてから対数を取り、山の 3 点に放物線を当てる(ガウス当てはめ)。"""
    k, ok = _peak(img)
    kk = np.clip(k, 1, IMG_H - 2)
    ny, nx = kk.shape
    iy = np.arange(ny)[:, None]
    ix = np.arange(nx)[None, :]
    v = np.clip(img - BG, 1e-9, None)
    lg = [np.log(v[iy, kk + d, ix]) for d in (-1, 0, 1)]
    den = lg[0] - 2.0 * lg[1] + lg[2]
    with np.errstate(invalid="ignore", divide="ignore"):
        dd = np.where(np.abs(den) > 1e-12, 0.5 * (lg[0] - lg[2]) / den, 0.0)
    return np.where(ok, kk + np.clip(dd, -1.0, 1.0), np.nan)


def est_lines_gauss(img):
    """fullseye の ``lines_gauss`` op(Frangi リッジの二値化)から列ごとの中心。

    HALCON の同名 op は「線の中心線 + 線幅」をサブピクセルで返すが、fullseye の
    代役はリッジ強調のしきい値化なので**輪郭画素の集合**しか返らない。
    列ごとに行の平均を取ってサブピクセルの代わりにしている。
    """
    out = np.full(img.shape[0:1] + img.shape[2:], np.nan)
    for i in range(img.shape[0]):
        res = fs.apply(img[i], "lines_gauss", a=0.35)
        acc = np.zeros(N_COL)
        cnt = np.zeros(N_COL)
        for c in res.get("cs", []):
            a = np.asarray(c, np.float64)
            if a.size == 0:
                continue
            np.add.at(acc, a[:, 1].astype(int), a[:, 0])
            np.add.at(cnt, a[:, 1].astype(int), 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[i] = np.where(cnt > 0, acc / np.maximum(cnt, 1e-9), np.nan)
    return out


ESTIMATORS = [("ゼロ点 最大値", est_argmax), ("重心 固定窓", est_centroid_fix),
              ("重心 切上無", est_centroid_raw), ("重心 追従窓", est_centroid_adapt),
              ("対数放物線", est_log_parabola), ("op lines_gauss", est_lines_gauss)]


def to_height(rows, theta_deg: float, k_scale: float = 1.0) -> np.ndarray:
    """光条の行 → 高さ [mm]。``k_scale`` は校正誤差(高さ倍率のずれ)。"""
    return H_REF + (np.asarray(rows, np.float64) - ROW0) / (k_px_mm(theta_deg) * k_scale)


def _rms(v) -> float:
    v = np.asarray(v, np.float64)
    v = v[np.isfinite(v)]
    return float(np.sqrt(np.mean(v * v))) if v.size else float("nan")


# --------------------------------------------------------------------------- #
# 4. 断面 → 6 つの計測量                                                        #
# --------------------------------------------------------------------------- #
def fit_plates(h: np.ndarray, yv: np.ndarray):
    """走査全体から左右の母材**面**を当てる(:func:`fullseye.ledger.fit_plane_3d`)。

    1 断面ずつ直線を当てるのではなく、走査全体を 1 枚の平面に当てる ——
    実機の溶接部検査でも母材は平面なので、こちらのほうが雑音に強い。
    NaN(測れなかった列)は :func:`fit_plane_3d` が落としてくれないので、
    **呼び手が先に外す**。返りは断面ごとの直線係数 (a, b[]) の対。
    """
    out = []
    for sgn in (-1.0, +1.0):
        sel = (np.abs(X) >= PLATE_WIN[0]) & (np.abs(X) <= PLATE_WIN[1]) & (np.sign(X) == sgn)
        hh = h[:, sel]
        xx = np.broadcast_to(X[sel][None, :], hh.shape)
        yy = np.broadcast_to(np.asarray(yv)[:, None], hh.shape)
        m = np.isfinite(hh)
        if int(m.sum()) < 40:
            out.append(None)
            continue
        c, n, _res = fs.ledger.fit_plane_3d(np.stack([xx[m], yy[m], hh[m]], axis=1))
        if abs(float(n[2])) < 1e-6:
            out.append(None)
            continue
        a = -float(n[0]) / float(n[2])
        b = float(c[2]) + (float(n[0]) * float(c[0])
                           + float(n[1]) * (float(c[1]) - np.asarray(yv))) / float(n[2])
        out.append({"c": np.asarray(c, float), "n": np.asarray(n, float),
                    "a": a, "b": np.atleast_1d(b)})
    return out[0], out[1]


def root_line(pl: dict, pr: dict, yv: np.ndarray):
    """2 枚の母材面の交線 = **根**(:func:`fullseye.ledger.intersect_planes`)。

    根は溶接金属の下に隠れていて**直接は見えない** —— 脚長ものど厚もここを
    基準にするので、遠側の面が 1 枚見えなくなると近側の脚長まで出せなくなる。
    """
    res = fs.ledger.intersect_planes(pl["c"], pl["n"], pr["c"], pr["n"])
    if res is None:
        return None
    p0, d = np.asarray(res[0], float), np.asarray(res[1], float)
    if abs(d[1]) < 1e-9:
        return None
    t = (np.asarray(yv, float) - p0[1]) / d[1]
    return p0[0] + t * d[0], p0[2] + t * d[2]


def _smooth_masked(v, ok):
    """移動平均。**窓が丸ごと有効な列だけ**返し、それ以外は NaN。

    ★欠測を飛ばして「見えている分だけ平均」にすると、遮蔽の**境界の列**で
    片側だけの平均になり、値が内側へ引っ張られる。最初にそう書いたら、溝が
    ちょうど陰に入る角度でつま先の判定がしきい値を割り、脚長が **1.7 mm**
    外へ飛んだ(16 断面のうち 1 本)。境界の列は素直に捨てるほうが安全。
    """
    num = uniform_filter1d(np.where(ok, v, 0.0), SMOOTH)
    den = uniform_filter1d(ok.astype(float), SMOOTH)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = num / den
    return np.where(ok & (den > 0.999), s, np.nan)


def _cross_tau(x, d, i, j):
    """``d`` が ``-TAU`` を横切る位置を線形内挿(i = 内側、j = その隣)。

    ★内挿は必ず 2 列のあいだに**留める**。2 点の差が雑音なみに小さいと
    傾きの逆数が発散して、つま先が視野の外(4 mm 先)へ飛ぶ(16 断面の 1 本で
    実際に起きた)。外挿を許す 1 行が、まれに桁違いの外れ値を作る。
    """
    if not (np.isfinite(d[i]) and np.isfinite(d[j])) or d[i] == d[j]:
        return float(x[i])
    v = float(x[i] + (d[i] + TAU) * (x[j] - x[i]) / (d[i] - d[j]))
    return float(np.clip(v, min(x[i], x[j]), max(x[i], x[j])))


def quantities_one(h, lineL, lineR, root) -> dict:
    """1 断面 → 6 量。``h`` は NaN 込み(NaN = 測れなかった列)。

    つま先は「母材面からの落ち込みが %0.2f mm 以内の**いちばん内側**の点」。
    外側は溝で深く落ちているので、この規則は溝を飛び越して溶接の縁に着く。

    **出せる量だけ出す**: 溝深さは片側の母材面とつま先だけで出せるが、脚長と
    のど厚は**根**が要り、根は 2 枚の面の交点なので片側が見えないと出せない。
    """
    out = {k: float("nan") for k in KEYS}
    out.update({"m_" + k: 1.0 for k in KEYS})
    out["xtl"] = out["xtr"] = float("nan")
    ok = np.isfinite(h)
    if ok.sum() < 40:
        return out
    toe, dev = {}, {}
    for side, ln, span, inner in (("L", lineL, UC_SPAN_L, -0.4),
                                  ("R", lineR, UC_SPAN_R, +0.4)):
        if ln is None:
            continue
        a, b = ln
        s = _smooth_masked(h - (a * X + b), ok)
        c = np.nonzero(np.isfinite(s)
                       & ((X < inner) if side == "L" else (X > inner))
                       & (s >= -TAU))[0]
        # ★候補は「母材面の高さに戻った点」なので、**溝の外の平らな母材**も
        #   全部候補になる。内側 CHECK_IN mm に溶接金属(母材面から
        #   CHECK_DEV 以上の落ち込み)が在ることを確かめて初めてつま先と認める
        #   —— この門が無いと候補が母材へ滑り落ちて脚長が 1.7 mm 外へ飛ぶ。
        #   ★門の深さは**いちばん深い溝より深く**取ること。最初 -0.6 mm に
        #   したら、深さ 0.45 mm(垂直では 0.74 mm)の溝が門を通ってしまい、
        #   16 断面のうち 1 本で 2.2 mm 外れた。
        step = int(round(CHECK_IN * M_PX_MM)) * (1 if side == "L" else -1)
        raw = h - (a * X + b)
        cand = [k for k in (c[::-1] if side == "L" else c)
                if 0 <= k + step < N_COL and np.isfinite(raw[k + step])
                and raw[k + step] < CHECK_DEV]
        if not cand:
            continue
        i = int(cand[0])
        j = min(i + 1, N_COL - 1) if side == "L" else max(i - 1, 0)
        xt = _cross_tau(X, s, i, j)
        toe[side] = (xt, a * xt + b, a)
        dev[side] = s
        out["xtl" if side == "L" else "xtr"] = xt
        sel = ((X >= xt - span) & (X < xt)) if side == "L" else \
              ((X > xt) & (X <= xt + span))
        key = "ucL" if side == "L" else "ucR"
        out["m_" + key] = float(1.0 - ok[sel].mean()) if sel.any() else 1.0
        m = sel & np.isfinite(s)
        if m.any():
            out[key] = float(max(0.0, -np.min(s[m])) / np.hypot(1.0, a))
    if "L" in toe and "R" in toe and not (toe["L"][0] < 0.0 < toe["R"][0]):
        return out
    if root is not None:
        x_root, z_root = root
        for side, key in (("L", "legL"), ("R", "legR")):
            if side in toe:
                out[key] = abs(toe[side][0] - x_root) * np.hypot(1.0, toe[side][2])
                lo, hi = sorted((toe[side][0], x_root))
                sel = (X >= lo) & (X <= hi)
                out["m_" + key] = float(1.0 - ok[sel].mean()) if sel.any() else 1.0
    if "L" not in toe or "R" not in toe:
        return out
    (xtl, ztl, _al), (xtr, ztr, _ar) = toe["L"], toe["R"]
    span = (X >= xtl) & (X <= xtr)
    out["m_cv"] = out["m_throat"] = float(1.0 - ok[span].mean()) if span.any() else 1.0
    face = ok & span
    if int(face.sum()) < 8:
        return out
    xf, hf = X[face], h[face]
    sl = (ztr - ztl) / (xtr - xtl)
    out["cv"] = float(np.max((hf - (ztl + (xf - xtl) * sl)) / np.hypot(1.0, sl)))
    if root is not None:
        out["throat"] = float(np.min(np.hypot(xf - root[0], hf - root[1])))
    return out


quantities_one.__doc__ = quantities_one.__doc__ % TAU


def measure_all(h: np.ndarray, yv: np.ndarray) -> dict:
    """走査 (n_y, n_x) → 6 量 × n_y の配列。母材面は走査全体から当てる。"""
    pl, pr = fit_plates(h, yv)
    root = root_line(pl, pr, yv) if (pl is not None and pr is not None) else None
    ks = list(KEYS) + ["m_" + k for k in KEYS] + ["xtl", "xtr"]
    out = {k: np.full(h.shape[0], np.nan) for k in ks}
    for i in range(h.shape[0]):
        lL = None if pl is None else (pl["a"], float(pl["b"][min(i, pl["b"].size - 1)]))
        lR = None if pr is None else (pr["a"], float(pr["b"][min(i, pr["b"].size - 1)]))
        rt = None if root is None else (float(root[0][i]), float(root[1][i]))
        q = quantities_one(h[i], lL, lR, rt)
        for k in ks:
            out[k][i] = q[k]
    return out


def score(est: dict, tru: dict) -> dict:
    """量ごとに「測れた率」「区間の欠測率」「測れたところの平均 |誤差|」を**分けて**。

    ★「測れた率 100 %」でも、その量を出す区間に欠測が混じっていれば値は嘘に
    なりうる —— だから **2 つの欠け方を別々に数える**。
    """
    out = {}
    for k in KEYS:
        e, t = np.asarray(est[k], float), np.asarray(tru[k], float)
        m = np.isfinite(e) & np.isfinite(t)
        mm = np.asarray(est.get("m_" + k, np.full(e.shape, np.nan)), float)
        out[k] = {"got": float(np.isfinite(e).mean()),
                  "miss": float(np.nanmean(mm[np.isfinite(e)])) if m.any() else 1.0,
                  "mae": float(np.mean(np.abs(e[m] - t[m]))) if m.any() else float("nan"),
                  "bias": float(np.mean(e[m] - t[m])) if m.any() else float("nan"),
                  # ★生き残った断面だけの真値の平均。集計から何が抜けたかを見る。
                  "tmean": float(np.mean(t[m])) if m.any() else float("nan")}
    return out


# =========================================================================== #
# 章                                                                           #
# =========================================================================== #
def section1_scene(p: dict, design: dict, tru: dict) -> None:
    print("=" * 78)
    print("1) 場面と真値の検算")
    print("=" * 78)
    print("  継手: 90 度すみ肉。センサ座標で左母材 %.0f 度(傾き %.3f)/ "
          "右母材 %.0f 度(傾き %.3f)" % (PLATE_L_DEG, TL, PLATE_R_DEG, TR))
    print("  走査: 幅 %.0f mm x 長さ %.0f mm、%d 列 x %d 断面(1 列 = %.3f mm)"
          % (2 * X_HALF, Y_MM, N_COL, len(p["y"]), 1.0 / M_PX_MM))
    print("  撮像: M = %.0f px/mm、θ = %.0f 度 -> K = %.2f px/mm(1 px = %.4f mm)"
          % (M_PX_MM, THETA_REF, k_px_mm(THETA_REF), 1.0 / k_px_mm(THETA_REF)))
    print()
    print("  %-12s %16s %16s %10s" % ("量", "図面の真値 [mm]", "定義の真値 [mm]", "定義の床"))
    print("  " + "-" * 60)
    for k in KEYS:
        print("  %-12s %7.3f 〜 %6.3f %7.3f 〜 %6.3f %+10.4f"
              % (LABEL[k], design[k].min(), design[k].max(),
                 np.nanmin(tru[k]), np.nanmax(tru[k]),
                 float(np.nanmean(tru[k] - design[k]))))
    print()
    print("  ★「定義の真値」= **撮像を通さない真値の断面に、同じ測り方を当てた値**。")
    print("     つま先を「母材面から %.2f mm 落ちた点」と決めた時点で図面値から"
          % TAU)
    print("     ずれる(脚長 %+.3f mm)。以降の誤差はこちらを基準にする ——"
          % float(np.nanmean(tru["legL"] - design["legL"])))
    print("     そうしないと**定義の床と撮像の誤差が混ざる**。")
    img, _ = render(p, THETA_REF, noise=0.0, occlusion=False)
    err = np.abs(to_height(est_log_parabola(img), THETA_REF) - profile_h(X, p))
    print("  検算(雑音 0・遮蔽なし): 高さの最大誤差 %.3e mm -> %s"
          % (float(np.nanmax(err)),
             "撮像モデルと逆写像が整合" if np.nanmax(err) < 1e-9 else "★不整合"))


def section2_estimators(p: dict) -> dict:
    print()
    print("=" * 78)
    print("2) ★ゼロ点(最大値の画素)と 3 つの対比 —— 光条の幅を振る")
    print("=" * 78)
    print("  θ = %.0f 度・雑音 %.1f %%・遮蔽なし。高さの RMS [mm]。" % (THETA_REF, 100 * NOISE))
    print("  ★予想: 「重心」は 1 つの推定量ではなく、**窓の決め方まで含めて**")
    print("     初めて決まる。重心の分散 = σ_n²·Σ(r-c)²/(ΣI)²、ΣI ∝ A·σ なので")
    print("     ・固定窓 : Σ(r-c)² が一定 -> 誤差 ∝ **1/σ**(太いほど良い)")
    print("     ・追従窓 : Σ(r-c)² ∝ σ³   -> 誤差 ∝ **√σ**(細いほど良い)")
    print("     同じ「重心」で**傾きの符号が逆**になるはず。")
    print()
    pe = bead_params(y_grid(4))
    h_true = profile_h(X, pe)
    widths = [0.5, 0.7, 1.0, 1.4, 2.0, 2.8]
    table = {name: [] for name, _ in ESTIMATORS}
    bias = {name: [] for name, _ in ESTIMATORS}
    for w in widths:
        img, _ = render(pe, THETA_REF, sigma=w, occlusion=False, seed=3)
        im0, _ = render(pe, THETA_REF, sigma=w, occlusion=False, noise=0.0, seed=3)
        for name, fn in ESTIMATORS:
            table[name].append(_rms(to_height(fn(img), THETA_REF) - h_true))
            bias[name].append(_rms(to_height(fn(im0), THETA_REF) - h_true))
    for title, tb in (("RMS(雑音あり)", table),
                      ("RMS(雑音ゼロ = 標本化の偏りだけ)", bias)):
        print("  " + title)
        print("  %8s |" % "光条 1σ", end="")
        for name, _ in ESTIMATORS:
            print(" %14s" % name, end="")
        print()
        print("  " + "-" * (10 + 15 * len(ESTIMATORS)))
        for i, w in enumerate(widths):
            print("  %8.1f |" % w, end="")
            for name, _ in ESTIMATORS:
                print(" %14.5f" % tb[name][i], end="")
            print()
        print()
    i14, i07, i28 = widths.index(1.4), widths.index(0.7), widths.index(2.8)
    base = table["ゼロ点 最大値"][i14]
    print("  1σ = %.1f px でのゼロ点比: " % widths[i14]
          + " / ".join("%s %.1f 倍" % (n, base / table[n][i14]) for n, _ in ESTIMATORS[1:]))
    ratio = np.log(widths[i28] / widths[i07])
    print()
    print("  1σ %.1f -> %.1f px の指数 σ^n(**雑音成分だけ**を取り出して):"
          % (widths[i07], widths[i28]))
    pred_n = {"重心 固定窓": -1.0, "重心 切上無": -1.0, "重心 追従窓": +0.5}
    expo = {}
    for name in ("重心 固定窓", "重心 切上無", "重心 追従窓", "対数放物線"):
        v = [float(np.sqrt(max(table[name][i] ** 2 - bias[name][i] ** 2, 1e-24)))
             for i in (i07, i28)]
        expo[name] = float(np.log(v[1] / v[0]) / ratio)
        print("    %-12s %.5f -> %.5f mm  σ^%+.2f  (予測 %s)"
              % (name, v[0], v[1], expo[name],
                 "σ%+.2f" % pred_n[name] if name in pred_n else "—"))
    print()
    print("  → ★★**同じ「重心」で幅への向きが逆**: 固定窓は σ^%+.2f(太いほど良い)、"
          % expo["重心 固定窓"])
    print("     追従窓は σ^%+.2f(細いほど良い)。窓の決め方を書かずに「重心を"
          % expo["重心 追従窓"])
    print("     使った」と言っても、光条が太る現場で良くなるのか悪くなるのかが決まらない。")
    print("  → ★★対照群が予測とのずれを説明した: 固定窓の実測 σ^%+.2f は予測 σ^-1.00 と"
          % expo["重心 固定窓"])
    print("     食い違うが、**背景を 0 で切り上げるのをやめる**だけで σ^%+.2f まで戻る。"
          % expo["重心 切上無"])
    print("     `clip(I-BG, 0, None)` の 1 行が雑音を片側に整流して、法則を曲げていた。")
    print("  → ★偏りと雑音は別物: 追従窓は雑音ゼロでも %.5f mm 残る(しきい値が"
          % bias["重心 追従窓"][i14])
    print("     副画素位置で跳ぶ標本化の偏り)。固定窓は %.5f mm でほぼ偏り無し ——"
          % bias["重心 固定窓"][i14])
    print("     1 つの RMS に畳むと、この 2 つの直し方(窓を広げる / 光量を上げる)を取り違える。")
    print("  → ★3 点当てはめ(対数放物線)は幅への感度が桁違い(σ^%+.2f)。"
          % expo["対数放物線"])
    print("     3 点しか見ない推定量は、光条が太ると山の曲率が消えて壊れる。")
    print("  → ★op の `lines_gauss` は Frangi リッジの**二値化**で、中心を")
    print("     サブピクセルで返さない(%.4f mm = ゼロ点の %.1f 倍)。"
          % (table["op lines_gauss"][i14], table["op lines_gauss"][i14] / base))
    return {"widths": widths, "table": table, "bias": bias, "expo": expo}


def section3_quantities(p: dict, tru: dict) -> None:
    print()
    print("=" * 78)
    print("3) 6 つの計測量(θ = %.0f 度・遮蔽なし・重心)" % THETA_REF)
    print("=" * 78)
    img, _ = render(p, THETA_REF, occlusion=False, seed=7)
    sc = score(measure_all(to_height(est_centroid(img), THETA_REF), p["y"]), tru)
    print("  %-12s %12s %10s %11s %8s" % ("量", "定義の真値", "偏り", "平均|誤差|", "測れた"))
    print("  " + "-" * 56)
    for k in KEYS:
        print("  %-12s %12.4f %+10.4f %11.4f %7.0f %%"
              % (LABEL[k], float(np.nanmean(tru[k])), sc[k]["bias"], sc[k]["mae"],
                 100 * sc[k]["got"]))
    print()
    print("  → 遮蔽が無ければ 6 量とも 平均|誤差| %.4f mm 以下。壊れるのは 5 章から。"
          % max(sc[k]["mae"] for k in KEYS))


def section4_predict() -> dict:
    print()
    print("=" * 78)
    print("4) ★★崖を先に予測する —— 幾何だけで、撮る前に")
    print("=" * 78)
    print("  カメラ光線の傾きは cot θ。**傾き cot θ を超えて登る面は自分の陰**。")
    print("  だから遮蔽の始まる角は θ_crit = arctan(1 / 最大割線傾斜)。")
    print()
    pf = bead_params(y_grid(N_Y_FIG))
    xf = np.linspace(-X_HALF, X_HALF, 3 * N_COL + 1)
    hf = profile_h(xf, pf)
    xl, xr, _zl, _zr = _toes(pf)

    def onset(mask):
        """その区間の点が最初に隠れる θ [度](最大割線傾斜から)。"""
        best = np.zeros(hf.shape[0])
        for i in range(hf.shape[0]):
            idx = np.nonzero(mask[i])[0]
            s = 0.0
            for j in idx[::3]:
                s = max(s, float(np.max((hf[i, j + 1:] - hf[i, j]) / (xf[j + 1:] - xf[j]))))
            best[i] = s
        return np.degrees(np.arctan(1.0 / np.maximum(best, 1e-9)))

    xg = xf[None, :]
    o_uc = onset((xg >= xl - UC_SPAN_L) & (xg < xl))
    o_pl = onset((xg >= -X_HALF + 0.2) & (xg < xl - UC_SPAN_L))
    o_fc = onset((xg >= xl) & (xg <= xr))
    print("  予測(遮蔽が始まる θ):")
    print("    左母材面(溝の外) %.1f 度 —— 傾きが一定 tan53 = %.3f なので"
          % (float(np.median(o_pl)), TL))
    print("                            **全部いっせいに**背を向ける(段差の崖)")
    print("    左アンダーカット   %.1f 〜 %.1f 度 —— 溝の斜面が上乗せされる分だけ早い"
          % (float(o_uc.min()), float(o_uc.max())))
    print("    溶接面             %.1f 度" % float(np.median(o_fc)))
    print("    右側(近側)       遮蔽なし —— 傾きが負(カメラを向いている)")
    print()
    deep, shal = pf["d1"] > 0.40, pf["d1"] < 0.10
    print("  ★★**深い溝ほど先に隠れる**: 深さ %.2f mm の断面で %.1f 度、"
          % (float(pf["d1"][deep].mean()), float(o_uc[deep].mean())))
    print("     深さ %.2f mm の断面で %.1f 度。いちばん通してはいけない欠陥が"
          % (float(pf["d1"][shal].mean()), float(o_uc[shal].mean())))
    print("     いちばん先に消える。")
    return {"uc": o_uc, "plate": o_pl, "face": o_fc, "d1": pf["d1"]}


def geometric_only(p: dict, tru: dict) -> dict:
    """撮像を通さず、**遮蔽だけ**を入れた誤差(予測の骨)。"""
    out = {k: {"mae": [], "got": []} for k in KEYS}
    h_true = profile_h(X, p)
    for a in ANGLES:
        sc = score(measure_all(np.where(visible(h_true, a), h_true, np.nan), p["y"]), tru)
        for k in KEYS:
            out[k]["mae"].append(sc[k]["mae"])
            out[k]["got"].append(sc[k]["got"])
    return out


def section5_angle_sweep(p: dict, tru: dict) -> dict:
    print()
    print("=" * 78)
    print("5) ★★三角測量角の掃引 —— 分解能は 1/sinθ、遮蔽は cotθ")
    print("=" * 78)
    print("  対照群 3 つ: (a) 遮蔽なし (b) 遮蔽あり (c) 遮蔽 + 鏡面反射(飽和)。")
    print("  誤差は**量ごと**に、しかも「測れた率」と分けて数える。")
    print()
    groups = [("a 遮蔽なし", dict(occlusion=False, specular=0.0)),
              ("b 遮蔽あり", dict(occlusion=True, specular=0.0)),
              ("c 遮蔽+鏡面", dict(occlusion=True, specular=4.0))]
    seeds = (21, 47, 83)
    res = {g: {k: {"mae": [], "got": [], "miss": [], "tmean": []} for k in KEYS} for g, _ in groups}
    hgt = {g: [] for g, _ in groups}
    sat, sat_bias, unsat_bias = [], [], []
    h_true = profile_h(X, p)
    for gname, kw in groups:
        for a in ANGLES:
            acc = {k: {"mae": [], "got": [], "miss": [], "tmean": []} for k in KEYS}
            hh_rms = []
            for sd in seeds:
                img, vis = render(p, a, seed=sd, **kw)
                hh = to_height(est_centroid(img), a)
                good = np.isfinite(hh) & vis
                hh_rms.append(_rms((hh - h_true)[good]))
                if gname.startswith("c") and sd == seeds[0]:
                    hot = (img >= 0.999).any(axis=1)          # 飽和画素を含む列
                    sat.append(float((img >= 0.999).mean()))
                    sat_bias.append(float(np.mean((hh - h_true)[good & hot]))
                                    if (good & hot).any() else np.nan)
                    unsat_bias.append(float(np.mean((hh - h_true)[good & ~hot])))
                sc = score(measure_all(hh, p["y"]), tru)
                for k in KEYS:
                    for f in ("mae", "got", "miss", "tmean"):
                        acc[k][f].append(sc[k][f])
            hgt[gname].append(float(np.mean(hh_rms)))
            for k in KEYS:
                for f in ("mae", "got", "miss", "tmean"):
                    res[gname][k][f].append(float(np.nanmean(acc[k][f]))
                                            if np.any(np.isfinite(acc[k][f]))
                                            else float("nan"))

    c0 = hgt["a 遮蔽なし"][I_REF] * np.sin(np.deg2rad(THETA_REF))
    print("  高さそのものの RMS [mm](予測 = %.4f/sin θ、θ=%.0f 度で 1 点だけ合わせた)"
          % (c0, THETA_REF))
    print("  %6s %12s %12s %12s %12s"
          % ("θ", "予測 1/sinθ", "a 遮蔽なし", "b 遮蔽あり", "c 遮蔽+鏡面"))
    for i, a in enumerate(ANGLES):
        print("  %6.0f %12.4f %12.4f %12.4f %12.4f"
              % (a, c0 / np.sin(np.deg2rad(a)), hgt["a 遮蔽なし"][i],
                 hgt["b 遮蔽あり"][i], hgt["c 遮蔽+鏡面"][i]))
    dev = max(abs(hgt["a 遮蔽なし"][i] * np.sin(np.deg2rad(a)) / c0 - 1.0)
              for i, a in enumerate(ANGLES))
    print("  → 遮蔽なしの高さ RMS は 1/sin θ に**最大 %.1f %% で乗る**。"
          "分解能の側は予測どおり。" % (100 * dev))
    print()
    print("  ★鏡面反射は**平均で見ると「良く」なる**(飽和画素 平均 %.2f %%、"
          % (100 * float(np.mean(sat))))
    print("     高さ RMS %.4f -> %.4f mm) —— 鏡面ローブは光量を足すので SNR が上がる。"
          % (hgt["b 遮蔽あり"][I_REF], hgt["c 遮蔽+鏡面"][I_REF]))
    print("     壊れているのは**飽和した列だけ**なので、そこを分けて数える:")
    print("     θ=%.0f 度で 飽和列の偏り %+.4f mm / 非飽和列 %+.4f mm(%.0f 倍)。"
          % (THETA_REF, sat_bias[I_REF], unsat_bias[I_REF],
             abs(sat_bias[I_REF] / unsat_bias[I_REF])))
    print("     ★飽和の起きる場所は θ とともに動く(鏡面条件 dh/dx = -tan(θ/2))ので、")
    print("     θ=%.0f 度では溶接面、θ=%.0f 度では近側の母材面が光る。"
          % (ANGLES[1], ANGLES[-1]))
    print()

    for title, field, fmt in (("測れた率 [%]", "got", "%11.0f "),
                              ("その量の区間の欠測率 [%](測れた断面の平均)",
                               "miss", "%11.0f "),
                              ("平均|誤差| [mm](3 種の乱数の平均)", "mae", "%12s")):
        print("  " + title)
        print("  %6s" % "θ", end="")
        for k in KEYS:
            print(" %12s" % LABEL[k], end="")
        print()
        for i, a in enumerate(ANGLES):
            print("  %6.0f" % a, end="")
            for k in KEYS:
                v = res["b 遮蔽あり"][k][field][i]
                if field == "mae":
                    print(fmt % ("—" if not np.isfinite(v) else "%.4f" % v), end="")
                else:
                    print(fmt % (100 * v), end="")
            print()
        print()
    ucl = res["b 遮蔽あり"]["ucL"]
    i3 = 3
    print("  → ★★**測れた率は 100 % のまま、値だけが静かに浅くなる**。左溝は")
    print("     θ=%.0f 度でまだ全断面が「測れた」が、区間の %.0f %% が欠測していて、"
          % (ANGLES[i3], 100 * ucl["miss"][i3]))
    print("     誤差は %.4f mm(生き残った断面の真値 平均 %.3f mm の %.0f %%)。"
          % (ucl["mae"][i3], ucl["tmean"][i3],
             100 * ucl["mae"][i3] / ucl["tmean"][i3]))
    print("     **警報を出せるのは欠測率だけ**で、測れた率でも値そのものでもない。")
    print("  → ★★もっと悪いのは**生存者バイアス**。θ を上げると深い溝の断面から")
    print("     「測れない」に落ちるので、生き残った断面の真値の平均が")
    print("     %s mm と**浅いほうへ流れる**。"
          % " -> ".join("%.3f" % ucl["tmean"][i] for i in (0, 3, 4, 5)))
    print("     平均誤差だけを見ると %s mm と「良くなった」ように見えるが、"
          % " -> ".join("%.4f" % ucl["mae"][i] for i in (0, 3, 4, 5)))
    print("     **測れなくなった断面がいちばん危ない断面**なので、これは改善ではない。")
    print()
    return {"res": res, "hgt": hgt, "c0": c0, "sat": sat}


def section6_optimum(sw: dict, geo: dict) -> dict:
    print("=" * 78)
    print("6) ★★最適角 —— 予測と実測を量ごとに突き合わせる")
    print("=" * 78)
    print("  予測 = 「遮蔽だけの誤差(撮像を通さない)」と「雑音だけの誤差")
    print("  (θ=%.0f 度で 1 点合わせて 1/sin θ で伸ばす)」の二乗和。" % THETA_REF)
    print("  どちらの側も**その量に固有**なので、最適角も量ごとに別になるはず。")
    print("  ★2 つの基準を分けて出す: **全断面が測れる中での最小**(検査で使える角)と、")
    print("  **測れた断面だけでの最小**(論文に載せると良く見える角)。")
    print()
    res = sw["res"]["b 遮蔽あり"]
    ang = np.asarray(ANGLES)
    rows, out = [], {}
    print("  %-12s %8s %8s %11s | %8s %11s %8s"
          % ("量", "予測 θ*", "実測 θ*", "|誤差|", "甘い θ*", "|誤差|", "測れた"))
    print("  " + "-" * 72)
    for k in KEYS:
        gm = np.asarray(geo[k]["mae"], float)
        gg = np.asarray(geo[k]["got"], float)
        n0 = sw["res"]["a 遮蔽なし"][k]["mae"][I_REF] * np.sin(np.deg2rad(THETA_REF))
        pred = np.sqrt(np.nan_to_num(gm, nan=1e3) ** 2 + (n0 / np.sin(np.deg2rad(ang))) ** 2)
        pred = np.where(gg > 0.999, pred, np.inf)
        mae = np.nan_to_num(np.asarray(res[k]["mae"], float), nan=np.inf)
        got = np.asarray(res[k]["got"], float)
        meas = np.where(got > 0.999, mae, np.inf)       # 全断面が測れる角だけ
        loose = np.where(got > 0.0, mae, np.inf)        # 測れた断面だけで最小
        ip, im, il = int(np.argmin(pred)), int(np.argmin(meas)), int(np.argmin(loose))
        out[k] = (ang[ip], ang[im], meas[im], mae[il], ang[il], got[il])
        rows.append([LABEL[k], "%.0f" % ang[ip], "%.0f" % ang[im], "%.4f" % meas[im],
                     "%.0f" % ang[il], "%.4f" % mae[il], "%.0f %%" % (100 * got[il])])
        print("  %-12s %7.0f度 %7.0f度 %11.4f | %7.0f度 %11.4f %7.0f %%"
              % (LABEL[k], ang[ip], ang[im], meas[im], ang[il], mae[il], 100 * got[il]))
    print()
    gap = max(KEYS, key=lambda k: (out[k][2] / out[k][3]) if out[k][3] > 0 else 0)
    print("  → ★★「誤差が最小の角度」と「全断面が測れる角度」は別物。%s は"
          % LABEL[gap])
    print("     %.0f 度で |誤差| %.4f mm と**見た目いちばん良い**が、そこで測れて"
          % (out[gap][4], out[gap][3]))
    print("     いるのは %.0f %% の断面だけ。全断面が要るなら %.0f 度(%.4f mm、%.1f 倍)。"
          % (100 * out[gap][5], out[gap][1], out[gap][2], out[gap][2] / out[gap][3]))
    print("     ★甘いほうを報告すると、**測れなかった断面を黙って捨てた数字**になる。")
    allm = []
    for i in range(len(ANGLES)):
        v = [res[k]["mae"][i] if res[k]["got"][i] > 0.999 else np.nan for k in KEYS]
        allm.append(float(np.mean(v)) if np.all(np.isfinite(v)) else np.nan)
    allm = np.asarray(allm, float)
    ia = int(np.argmin(np.where(np.isfinite(allm), allm, np.inf)))
    print()
    print("  ★★6 量の平均に畳むと最適角は %.0f 度。そこは**壊れやすい 1 量に"
          % ang[ia])
    print("     引きずられた角度**で、他の量にとっては最良でない:")
    for k in KEYS:
        v = res[k]["mae"][ia]
        if np.isfinite(v) and np.isfinite(out[k][2]) and out[k][2] > 0:
            print("       %-12s %.0f 度で %.4f mm = 自分の最適角(%.0f 度)の %.1f 倍"
                  % (LABEL[k], ang[ia], v, out[k][1], v / out[k][2]))
    print("     **1 つの角度で 6 量を同時に最良にはできない。**")
    print("     しかも 1 つに畳んだ指標は「測れなかった量」を隠す —— %.0f 度以上では"
          % ANGLES[6])
    print("     右溝しか残っていないのに、平均はその 1 量だけで出せてしまう。")
    print("  ★近側の脚長まで %.0f 度で消えるのが効いている: 脚長も のど厚も"
          % ANGLES[6])
    print("     **根**(2 枚の母材面の交線)が基準で、根は溶接金属の下に隠れている。")
    print("     遠側の面が 1 枚見えなくなると、**手前の量まで道連れ**になる。")
    return {"rows": rows, "all": allm, "best_all": ang[ia], "per": out}


def section7_calibration(p: dict, tru: dict, design: dict) -> dict:
    print()
    print("=" * 78)
    print("7) ★★校正誤差(高さ倍率 +1 %)—— 脚長と溝深さは同じ面で真逆に効く")
    print("=" * 78)
    print("  高さだけが (1+ε) 倍になると、母材面の傾き a も (1+ε) 倍になる。")
    print("   ・つま先の x と根の x は**動かない**(比が変わらないから)")
    print("   ・脚長 = |Δx|·√(1+a²)  → d/dε = a²/(1+a²) = **sin²(母材角)**")
    print("   ・溝深さ = Δz/√(1+a²) → d/dε = 1 - sin² = **cos²(母材角)**")
    print("   ・つまり同じ母材面で**脚長と溝深さの感度は足して 1**。")
    print()
    s2L = np.sin(np.deg2rad(PLATE_L_DEG)) ** 2
    s2R = np.sin(np.deg2rad(PLATE_R_DEG)) ** 2
    # のど厚: 最近点での高さ差の寄与 (Δz/d)^2
    xl, xr, _a, _b = _toes(p)
    xf = np.linspace(-X_HALF, X_HALF, 8 * N_COL + 1)
    hf = profile_h(xf, p)
    ins = (xf[None, :] >= xl) & (xf[None, :] <= xr)
    dd = np.where(ins, np.hypot(xf[None, :], hf), np.inf)
    j = np.argmin(dd, axis=1)
    dz = np.abs(hf[np.arange(hf.shape[0]), j])
    pr_thr = float(np.mean((dz / design["throat"]) ** 2))
    sl = float(np.mean(((_toes(p)[3] - _toes(p)[2]) / (_toes(p)[1] - _toes(p)[0]))))
    predict = {"cv": 1.0 / (1.0 + sl ** 2), "ucL": 1.0 - s2L, "ucR": 1.0 - s2R,
               "legL": s2L, "legR": s2R, "throat": pr_thr}
    eps = 0.01
    img, _ = render(p, THETA_REF, occlusion=False, noise=0.0, seed=9)
    q0 = measure_all(to_height(est_centroid(img), THETA_REF), p["y"])
    q1 = measure_all(to_height(est_centroid(img), THETA_REF, k_scale=1.0 / (1.0 + eps)),
                     p["y"])
    rows, gotv = [], {}
    print("  %-12s %14s %14s" % ("量", "予測 [%]", "実測 [%]"))
    print("  " + "-" * 44)
    for k in KEYS:
        g = float(np.nanmean((q1[k] - q0[k]) / q0[k]) / eps)
        gotv[k] = g
        pv = predict[k]
        ps = "—" if not np.isfinite(pv) else "%.3f" % (100 * pv * eps)
        rows.append([LABEL[k], ps, "%.3f" % (100 * g * eps)])
        print("  %-12s %14s %14.3f" % (LABEL[k], ps, 100 * g * eps))
    lo, hi = min(gotv.values()), max(gotv.values())
    print()
    print("  → ★同じ 1 %% の校正ずれが %.3f 〜 %.3f %% の幅(**%.1f 倍**)で出る。"
          % (100 * lo * eps, 100 * hi * eps, hi / lo))
    print("     左母材(53 度)は 脚長 %.3f + 溝 %.3f = %.3f、"
          % (gotv["legL"], gotv["ucL"], gotv["legL"] + gotv["ucL"]))
    print("     右母材(37 度)は 脚長 %.3f + 溝 %.3f = %.3f —— **どちらも 1**。"
          % (gotv["legR"], gotv["ucR"], gotv["legR"] + gotv["ucR"]))
    print("     「較正精度 1 %」だけでは、どの量が何 % ずれるかを言えない。")
    # ★凸みだけ予測から外れた。原因はつま先の這い(τ が絶対値のしきい値だから)。
    dxl = float(np.nanmean(q1["xtl"] - q0["xtl"])) / eps
    dxr = float(np.nanmean(q1["xtr"] - q0["xtr"])) / eps
    extra = (abs(TL * dxl) + abs(TR * dxr)) / 2.0 / float(np.nanmean(tru["cv"]))
    print()
    print("  → ★凸みだけ予測(cos²(弦の傾き) = %.3f)より大きい(実測 %.3f)。"
          % (predict["cv"], gotv["cv"]))
    print("     対照群で切り分けた: つま先の位置が %+.4f / %+.4f mm(左/右、ε=1 あたり)"
          % (dxl, dxr))
    print("     だけ**外へ這う** —— つま先の規則 τ = %.2f mm が**絶対値**なので、" % TAU)
    print("     高さが (1+ε) 倍に伸びると同じ τ に届く点が外へずれる。這った分だけ")
    print("     弦の両端が母材面を下り、凸みは +%.3f 増える。%.3f + %.3f = %.3f で"
          % (extra, predict["cv"], extra, predict["cv"] + extra))
    print("     実測 %.3f とほぼ一致する。同じ這いは脚長の実測が予測より"
          % gotv["cv"])
    print("     %.3f 大きいことも説明する。" % (gotv["legL"] - predict["legL"]))
    return {"rows": rows, "got": gotv, "predict": predict}


def section8_occlusion_map(pf: dict) -> dict:
    print()
    print("=" * 78)
    print("8) ★遮蔽の地図 —— 法線から描くと投げかけ影が落ちる")
    print("=" * 78)
    h = profile_h(X, pf)
    step = 10                                    # 列を 10 本おき -> Δx = 0.5 mm
    dy = Y_MM / h.shape[0]
    dx = step / M_PX_MM
    assert abs(dx - dy) < 1e-9, (dx, dy)
    depth = (-h[:, ::step]) / dx                 # ★等方格子・1 画素 = 1 単位へ
    nrm = np.asarray(fs.ledger.normals_from_depth(depth))
    n = nrm / np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-12)
    n = n * np.sign(-n[..., 2:3] + 1e-15)        # 高さ方向(+h)を向くよう揃える
    nx, nz = n[..., 0], -n[..., 2]
    print("  %6s %16s %16s %10s" % ("θ", "法線で背向き", "水平線で不可視", "差"))
    print("  " + "-" * 52)
    rows = []
    for a in (25.0, 35.0, 45.0, 55.0, 65.0):
        th = np.deg2rad(a)
        back = float(((nx * np.sin(th) + nz * np.cos(th)) < 0.0).mean())
        hid = float((~visible(h, a))[:, ::step].mean())
        rows.append((a, back, hid))
        print("  %6.0f %15.1f %% %15.1f %% %9.1f pp"
              % (a, 100 * back, 100 * hid, 100 * (hid - back)))
    print()
    print("  → 法線は**自己遮蔽(背を向けた面)**しか見ない。水平線の規則は")
    print("     **投げかけ影**(手前の盛り上がりが奥を隠す)も入るので必ず多い。")
    print("  → ★格子間隔が等方でないと正射版 `normals_from_depth` は黙って")
    print("     間違える(1 画素 = 1 単位と決め打つ)。生の走査格子は")
    print("     Δx = %.3f mm・Δy = %.3f mm なので、10 列おきに間引いて"
          % (1.0 / M_PX_MM, dy))
    print("     Δx = Δy = %.1f mm に揃えてから渡している。" % dx)
    return {"rows": rows, "n": n}


def section9_throat_esdf(pf: dict) -> dict:
    print()
    print("=" * 78)
    print("9) のど厚を 3-D の距離場で測る(occupancy_grid -> esdf -> query_distance)")
    print("=" * 78)
    h = profile_h(X, pf)
    xl, xr, _a, _b = _toes(pf)
    face = (X[None, :] >= xl) & (X[None, :] <= xr)
    yy = np.broadcast_to(y_grid(h.shape[0])[:, None], h.shape)
    pts = np.stack([np.broadcast_to(X[None, :], h.shape)[face], yy[face], h[face]], axis=1)
    vx = 0.05
    bounds = ((-X_HALF, X_HALF), (0.0, Y_MM), (H_REF, 1.0))
    res = (int(2 * X_HALF / vx), int(Y_MM / 0.5), int((1.0 - H_REF) / vx))
    occ = np.asarray(fs.ledger.occupancy_grid(pts, bounds, res))
    vs = (2 * X_HALF / res[0], Y_MM / res[1], (1.0 - H_REF) / res[2])
    sdf = np.asarray(fs.ledger.esdf(occ, vs))
    roots = np.stack([np.zeros(h.shape[0]), y_grid(h.shape[0]), np.zeros(h.shape[0])], axis=1)
    d_esdf = np.asarray(fs.ledger.query_distance(sdf, bounds, res, roots))
    d_true = design_quantities(pf)["throat"]
    dd = d_esdf - d_true
    print("  占有ボクセル %d 個(%.3f x %.3f x %.3f mm、軸ごとの res)、根 %d 点で問い合わせ"
          % (int(occ.sum()), vs[0], vs[1], vs[2], len(roots)))
    print("  のど厚: 閉形式 平均 %.4f mm / ESDF 平均 %.4f mm"
          % (float(d_true.mean()), float(d_esdf.mean())))
    print("  差 平均 %+.4f mm(最小 %+.4f / 最大 %+.4f)= ボクセル %.2f 個ぶん"
          % (float(dd.mean()), float(dd.min()), float(dd.max()), float(dd.mean()) / vs[0]))
    print("  → 距離場は最近傍**ボクセル中心**までを測るので、薄い殻を張ると")
    print("     必ず遠めに出る(%d 断面すべてで符号が正: %s)。"
          % (len(dd), "はい" if np.all(dd > 0) else "いいえ"))
    print("  → y を粗く(%.1f mm)しても のど厚は x-z 面内の量なので効かない ——"
          % vs[1])
    print("     軸ごとの res が要るのはこういう所(立方に縛ると 6 倍のボクセル)。")
    return {"esdf": d_esdf, "true": d_true, "vs": vs}


def section10_tool_gaps() -> None:
    print()
    print("=" * 78)
    print("10) 道具の穴(光切断の走査を組んでみて)")
    print("=" * 78)
    for nm in ("stripe_center", "light_section", "laser_stripe", "sheet_of_light"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (a) **列ごとの光条中心をサブピクセルで返す op が無い**。`lines_gauss`")
    print("      は在るが Frangi リッジの二値化(輪郭画素の集合)で、HALCON の")
    print("      同名 op が返す中心線 + 線幅は返らない(2 章でゼロ点より悪かった)。")
    for nm in ("shadow_map", "visibility_map", "horizon_mask"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (b) 高さ場と視線角から**遮蔽の地図**を出す口が無い。法線")
    print("      (`normals_from_depth`)では自己遮蔽しか出ず、投げかけ影には")
    print("      水平線の走査が要る(8 章、本 PoC の `visible` は 3 行)。")
    print("      地形の可視解析では標準の演算なので、族に入れる価値はある。")
    import inspect
    sig_f = str(inspect.signature(fs.normals_from_depth))
    print("  (c) ★`normals_from_depth` が**ファサードと台帳で別の関数**。")
    print("      `fs.normals_from_depth%s` は K(内部行列)必須の透視版、" % sig_f)
    print("      `fs.ledger.normals_from_depth(depth, ...)` は K を取らない正射版。")
    print("      同じ名前で必須引数が違うので、片方の呼び方を覚えると他方で落ちる。")
    assert not hasattr(fs, "median_filter_1d") and not hasattr(fs.ledger, "median_filter_1d")
    print("  (d) 「測れなかった」を値と一緒に運ぶ型が無い。`fit_plane_3d` は NaN を")
    print("      落としてくれないので、**呼び手が先に外す**必要がある(外し忘れると")
    print("      法線が NaN になって静かに全部が NaN になる)。")
    assert hasattr(fs.ledger, "fit_plane_3d") and hasattr(fs.ledger, "intersect_planes")
    print("  (e) 在って助かった: `fit_plane_3d`(走査全体から母材面を 1 枚で当てる)、")
    print("      `occupancy_grid`+`esdf`+`query_distance`(のど厚を距離場で、")
    print("      軸ごとの res)、`normals_from_depth`(等方格子に直せば背向きの地図)。")


# --------------------------------------------------------------------------- #
def _finite(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    m = np.isfinite(ys)
    return xs[m], ys[m]


def make_figures(pf, sw, geo, opt, est2, cal, occ) -> None:
    if not figs.enabled():
        return
    h = profile_h(X, pf)
    figs.save_grid("scene",
                   [h, np.abs(dh_dx(h)), visible(h, 25.0).astype(float),
                    visible(h, 45.0).astype(float)],
                   ["真値の高さ h(x,y) [mm]", "|dh/dx|(遮蔽を決める量)",
                    "見える列 θ=25 度", "見える列 θ=45 度"], ncols=2,
                   title="すみ肉溶接ビードの走査(幅 %.0f mm x 長さ %.0f mm、"
                         "左が遠側)" % (2 * X_HALF, Y_MM),
                   caption="上段: 左(遠側)の母材面ほど深い。下段: 明るい = "
                           "測れる。θ=45 度で左母材面が**いっせいに**消える"
                           "(傾き tan53 = 1.327 がカメラ光線の傾き cot45 = 1 を"
                           "超えるため)。")

    j = pf["y"].size // 2
    figs.save_grid("frames",
                   [render(pf, a, seed=31)[0][j] for a in (25.0, 45.0, 65.0)],
                   ["θ = 25 度(K = %.1f px/mm)" % k_px_mm(25.0),
                    "θ = 45 度(K = %.1f px/mm)" % k_px_mm(45.0),
                    "θ = 65 度(K = %.1f px/mm)" % k_px_mm(65.0)], ncols=1,
                   title="光条の画像(1 断面、%d x %d px)" % (IMG_H, N_COL),
                   caption="θ を大きくすると高さの伸び K が増えて分解能は上がる"
                           "(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。")

    for a, nm in ((28.0, "profile_28"), (50.0, "profile_50")):
        img, _v = render(pf, a, seed=31)
        hh = to_height(est_centroid(img), a)[j]
        figs.save_plot(nm, [("真値", X, h[j]), ("測れた列", *_finite(X, hh))],
                       xlabel="x [mm]", ylabel="高さ h [mm]",
                       title="断面 y = %.1f mm、θ = %.0f 度" % (pf["y"][j], a),
                       caption="θ = %.0f 度。%s" % (
                           a, "左の母材面と溝がまだ見えている(左側 4 量が出せる)。"
                           if a < 37 else
                           "左母材面が背を向け、左側 4 量が「測れない」に落ちる。"))

    ang = np.asarray(ANGLES)
    res = sw["res"]["b 遮蔽あり"]
    figs.save_plot("angle_sweep",
                   [(LABEL[k], *_finite(ang, [v if g > 0.999 else np.nan
                                              for v, g in zip(res[k]["mae"], res[k]["got"])]))
                    for k in ("ucL", "legL", "throat", "ucR", "legR")],
                   xlabel="三角測量角 θ [度]", ylabel="平均 |誤差| [mm]",
                   title="最適角は測定量ごとに違う(遮蔽あり)",
                   caption="線が途切れるところから先は「測れなかった」。左側の量は"
                           " 37 度でいっせいに消え、左アンダーカットはその前から"
                           "少しずつ欠けるので谷が手前にできる。")

    figs.save_plot("resolution_vs_occlusion",
                   [("高さ RMS(遮蔽なし)", ang, sw["hgt"]["a 遮蔽なし"]),
                    ("予測 1/sinθ", ang, sw["c0"] / np.sin(np.deg2rad(ang))),
                    ("左 UC: 遮蔽だけの誤差", *_finite(ang, geo["ucL"]["mae"])),
                    ("左 UC: 実測", *_finite(ang, [v if g > 0.999 else np.nan for v, g
                                                  in zip(res["ucL"]["mae"],
                                                         res["ucL"]["got"])]))],
                   xlabel="三角測量角 θ [度]", ylabel="誤差 [mm]",
                   title="分解能は 1/sinθ で良くなり、遮蔽は θ で悪くなる",
                   caption="同じノブの表裏。2 本が交わるあたりが最適角。")

    figs.save_table("optimum",
                    ["量", "予測 θ*", "実測 θ*(全断面)", "|誤差| mm",
                     "甘い θ*", "|誤差| mm", "測れた"], opt["rows"],
                    title="最適な三角測量角: 予測と実測(量ごと)",
                    caption="予測 = 遮蔽だけの誤差と 1/sinθ の雑音の二乗和。"
                            "「甘い θ*」= 測れた断面だけで数えたときの最小。")

    figs.save_table("calibration", ["量", "予測 [%]", "実測 [%]"], cal["rows"],
                    title="高さ倍率 +1 % の校正誤差が各量に出る大きさ",
                    caption="脚長は sin²(母材角)、溝深さは cos²(母材角) —— "
                            "同じ母材面で足すと 1。")

    figs.save_plot("stripe_width",
                   [(n, est2["widths"], est2["table"][n]) for n, _ in ESTIMATORS],
                   xlabel="光条の 1σ [px]", ylabel="高さ RMS [mm]",
                   title="光条は細いほど良い(ただし 0.7 px で床)",
                   caption="重心は √σ で増え、3 点当てはめはもっと速く増える。"
                           "ゼロ点(最大値の画素)は幅にほぼ無関係な 1 画素の階段。")

    th45 = np.deg2rad(45.0)
    back = (occ["n"][..., 0] * np.sin(th45) - occ["n"][..., 2] * np.cos(th45)) < 0.0
    figs.save_grid("map_visibility",
                   [(~visible(h, a)).astype(float) for a in (25.0, 35.0, 45.0)]
                   + [back.astype(float)],
                   ["隠れた列 θ=25 度", "隠れた列 θ=35 度", "隠れた列 θ=45 度",
                    "法線だけで見た背向き θ=45 度(等方の粗格子)"], ncols=2,
                   title="遮蔽の地図(明るい = 隠れている)",
                   caption="法線は自己遮蔽だけを見る。水平線の規則は投げかけ影も"
                           "入るので必ず広い。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("poc_weld_bead_scan_angle — 光切断で溶接ビードを走査する")
    print("(分解能は 1/sinθ で上がり、遮蔽は cotθ を超えた面から始まる)")
    print()
    p = bead_params(y_grid(N_Y))
    design = design_quantities(p)
    tru = measure_all(profile_h(X, p), p["y"])      # 定義の真値
    pf = bead_params(y_grid(N_Y_FIG))

    section1_scene(p, design, tru)
    est2 = section2_estimators(p)
    section3_quantities(p, tru)
    pred = section4_predict()
    geo = geometric_only(p, tru)
    sw = section5_angle_sweep(p, tru)
    opt = section6_optimum(sw, geo)
    cal = section7_calibration(p, tru, design)
    occ = section8_occlusion_map(pf)
    section9_throat_esdf(pf)
    make_figures(pf, sw, geo, opt, est2, cal, occ)
    section10_tool_gaps()

    # --- 所見を固定する(壊れたら鳴る)------------------------------------- #
    res = sw["res"]["b 遮蔽あり"]
    assert res["ucL"]["got"][I_REF] > 0.99, "36 度で左 UC が測れない"
    assert res["ucL"]["got"][ANGLES.index(40.0)] < 0.01, "40 度で左 UC が残っている"
    assert res["ucR"]["got"][-1] > 0.99, "右 UC は最大角でも測れるはず"
    assert abs(float(np.median(pred["plate"])) - 37.0) < 0.6, "左母材の崖は 37 度"
    assert float(pred["uc"].min()) < 25.0 < float(pred["uc"].max()), "溝の崖は深さ依存"
    tb = est2["table"]
    assert tb["重心 追従窓"][-1] > tb["重心 追従窓"][1], "★追従窓は太いほど悪い(√σ)"
    assert tb["重心 固定窓"][-1] < tb["重心 固定窓"][1], "★固定窓は太いほど良い(1/σ)"
    assert tb["重心 追従窓"][0] > tb["重心 追従窓"][1], "★細すぎる側にも床がある"
    assert tb["op lines_gauss"][3] > tb["ゼロ点 最大値"][3], "lines_gauss はゼロ点より悪い"
    assert abs(cal["got"]["legL"] + cal["got"]["ucL"] - 1.0) < 0.02, "sin²+cos²=1"
    assert opt["per"]["ucR"][1] > opt["per"]["ucL"][1], "近側の最適角のほうが大きい"

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 分解能(1/sinθ)と遮蔽(cotθ)は同じノブの表裏で、最適角が在る。")
    print("  * その最適角は**量ごとに違う**: %s。"
          % " / ".join("%s %.0f 度" % (LABEL[k], opt["per"][k][1]) for k in KEYS))
    print("  * 深いアンダーカットほど先に隠れる —— いちばん危ない欠陥から消える。")
    print("  * 校正誤差の効き方も量ごとに違い、脚長と溝深さは足して 1。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
