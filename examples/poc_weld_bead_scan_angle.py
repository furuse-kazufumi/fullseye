# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""光切断で溶接ビードを走査する —— 最適な三角測量角は、測定量ごとに違う。

    py -3.11 examples/poc_weld_bead_scan_angle.py

すみ肉溶接の外観検査を、レーザー光切断センサ(ライン光 + 斜めカメラ)で
溶接線に沿って走査する仕事です。出す数字は **余盛(凸み)/ 脚長 左右 /
のど厚 / アンダーカット深さ 左右** の 6 つ。

三角測量角 θ(ライン光の面とカメラ光軸のなす角)を大きくすると高さ分解能は
``1/sin θ`` で良くなりますが、カメラ光線の傾き ``cot θ`` を超える斜面は
自分自身の陰に入って**測れなくなります**。分解能と遮蔽は同じノブの表裏で、
**最適角が在る**はず —— それを幾何から先に予測し、掃引で突き合わせます。

【グラウンドトゥルース(閉形式)】
90 度すみ肉継手をセンサ座標で左 53 度・右 37 度に置く(母材面 ``h = tan53·x``
と ``h = -tan37·x``、交線 = 根 (0,0))。溶接面は両つま先を結ぶ弦に放物線の
凸みを載せた曲線、両つま先の外側にガウス形のアンダーカットを掘る。溶接線
方向 y には脚長 L1(y) / L2(y) / 凸み c(y) / 左アンダーカット深さ d1(y) を
既知の関数で変える。**脚長・凸み・アンダーカット深さは式で分かり、のど厚は
根から溶接面までの最短距離を細格子で解いて 1e-4 mm 精度で得る。**

撮像は ``col = M·x``、``row = row0 + M·sin θ·(h - h_ref)`` の正射モデル
(M = 20 px/mm)。光条はガウス(1σ = 1.4 px)、雑音・鏡面ローブ・飽和・
校正誤差はすべて既知量として入れる。

EXTEND: 実機に差し替えるなら :func:`render` を撮影画像に、``M`` と ``ROW0``
と θ を校正値に置き換え、:func:`bead_params` の戻り値を「その溶接部の設計
寸法」ではなく**マクロ断面の実測**にする(光切断の真値をレーザーで取っては
いけない —— 同じ誤差源を共有する)。この PoC が入れていない誤差源は 3 つ:
(i) 透視の前縮み(実センサは Scheimpflug で面外に振るので列も高さで少し動く)、
(ii) 測定レンジ ``IMG_H/(M sin θ)`` の頭打ち(分解能と**レンジ**も同じノブの
表裏で、ここでは常に収まる高さに取ってある)、(iii) レーザー側の影(ライン光を
鉛直に立てているので影はカメラ側だけ)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(光条の輝度が最大の画素をそのまま高さにする)は θ に関係なく
   1 桁負ける**。θ = 36 度・雑音 1.5 % で高さ RMS は 最大値 0.0369 mm /
   重心 0.0040 mm / 対数放物線 0.0044 mm、fullseye の ``lines_gauss``
   (Frangi リッジの二値化)から列ごとに重心を取ると 0.1155 mm。
   ★**op として在る線検出はサブピクセルを返さない** —— 光切断でいちばん
   要る「列ごとの中心をサブピクセルで」が公開経路に無い。
2. ★**光条を太らせると精度は上がる**(1σ = 0.8 → 2.4 px で重心の RMS が
   0.0089 → 0.0025 mm)。3 画素しか照らさない細い光条ではサブピクセルの
   足場が無い。ただし太らせるほど**遮蔽の境界がなまる**ので、測れた/
   測れないの境目が 1σ ぶん内側へ食い込む。
3. ★★**遮蔽の崖は 2 種類あり、形がまるで違う**。幾何から予測: 左母材面は
   傾き tan53 = 1.327 なので **θ > 37.0 度でいっせいに背を向ける**(段差の
   崖)。左アンダーカットは溝の斜面が母材の傾きに上乗せされるので
   **θ > 21.9〜34.8 度(溝が深いほど早い)から少しずつ欠ける**(なだらかな
   崖)。実測もそのとおりで、左側の 4 量は 36 度と 40 度のあいだで
   「測れた 100 %」から「測れた 0 %」へ落ちる。
4. ★★**いちばん深い欠陥がいちばん先に隠れる**。左アンダーカットの
   予測遮蔽開始角は深さ 0.45 mm で 21.9 度、0.05 mm で 34.8 度 ——
   **深い溝ほど斜面が急なので早く陰に入る**。浅い溝は最後まで見えている
   ので、平均だけ見ていると「だいたい測れている」に見える。
5. ★★**最適角は測定量ごとに違い、1 つの角度で全部は取れない**。予測は
   右アンダーカット 70 度 / 右脚長 70 度 / のど厚 36 度 / 左脚長 36 度 /
   凸み 36 度 / 左アンダーカット 28 度。実測の最適角もほぼ同じで、
   左アンダーカットだけ 32 度(予測 28 度)。6 量の誤差を 1 つに畳んだ
   「平均誤差」の最適角は 36 度だが、そこでの左アンダーカット誤差は
   最適角の 2.3 倍になる。
6. ★**校正誤差(高さ倍率の 1 %)の効き方は量ごとに 3 倍違う**。予測は
   高さ系(凸み・アンダーカット)が 1.00 %、脚長が sin²(母材角)倍で
   左 0.638 % / 右 0.362 %、のど厚 0.556 %。実測は 1.00 / 0.63 / 0.36 /
   0.55 % で予測どおり。★**同じ校正のずれが、同じ図面の中で 3 倍違う
   大きさで出る** —— 「較正精度 1 %」だけでは不合格判定の裏づけにならない。
7. ★**法線から描いた遮蔽の地図は、投げかけ影を落とす**。
   ``normals_from_depth`` の法線で「背を向けた面」を数えると θ = 45 度で
   43.6 %、水平線の規則で解いた本当の不可視は 44.9 %(差 1.3 pp = 投げかけ
   影)。★**しかも格子間隔が等方でないと黙って間違える** —— 正射モデルの
   ``normals_from_depth`` は 1 画素 = 1 単位と決め打つので、x 0.05 mm・
   y 0.5 mm の生の走査格子をそのまま渡すと傾きが 10 倍ずれる。
8. ★のど厚は 3-D の距離場でも測れる。溶接面の点群 →``occupancy_grid``
   → ``esdf`` → 根の位置で ``query_distance``。閉形式との差は +0.032 mm
   (ボクセル 0.06 mm の約 0.5 個ぶん、符号は必ず正)—— 距離場は最近傍
   **ボクセル中心**までを測るので、薄い殻を張ると必ず遠めに出る。

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

UC_OFF_L, UC_SIG_L = 0.85, 0.40    # 左アンダーカット: つま先からの距離 / 1σ
UC_OFF_R, UC_SIG_R = 0.70, 0.30    # 右アンダーカット
UC_SPAN_L, UC_SPAN_R = 2.0, 1.6    # つま先から外側へこの範囲を溝とみなす [mm]
TAU = 0.05                         # つま先の判定しきい値(母材面からの落ち込み)

Y_MM = 30.0                        # 走査長 [mm]
N_Y = 16                           # 掃引で使う断面の本数
N_Y_FIG = 60                       # 図・地図で使う断面の本数(Δy = 0.5 mm)

# --- 撮像 -------------------------------------------------------------------- #
X_HALF = 7.5                       # 視野の半幅 [mm]
M_PX_MM = 20.0                     # 横倍率 [px/mm]
N_COL = int(2 * X_HALF * M_PX_MM)  # 300 列
IMG_H = 152                        # 画像の高さ [px]
ROW0 = 10.0                        # h = H_REF が写る行
H_REF = -10.1                      # 行の原点にする高さ [mm]
LINE_SIG = 1.4                     # 光条の 1σ [px]
BG = 0.03                          # 背景
NOISE = 0.015                      # 雑音の 1σ(フルスケール比)
DETECT = 0.25                      # この輝度に届かない列は「測れなかった」
THETA_REF = 36.0                   # 基準の三角測量角 [度]
PLATE_WIN = (5.4, 7.4)             # 母材面を当てはめる |x| の範囲 [mm]

X = -X_HALF + (np.arange(N_COL) + 0.5) / M_PX_MM
KEYS = ("cv", "legL", "legR", "throat", "ucL", "ucR")
LABEL = {"cv": "余盛(凸み)", "legL": "脚長 左", "legR": "脚長 右",
         "throat": "のど厚", "ucL": "UC 深さ 左", "ucR": "UC 深さ 右"}


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
    """つま先の x 座標(左・右)と、そこでの高さ(溝の裾を含む)。"""
    xl = -p["L1"][:, None] * CL
    xr = p["L2"][:, None] * CR
    nl0 = (p["d1"][:, None] / CL) * np.exp(-(UC_OFF_L * CL) ** 2 / (2 * UC_SIG_L ** 2))
    nr0 = (p["d2"][:, None] / CR) * np.exp(-(UC_OFF_R * CR) ** 2 / (2 * UC_SIG_R ** 2))
    return xl, xr, TL * xl - nl0, -TR * xr - nr0


def profile_h(x: np.ndarray, p: dict) -> np.ndarray:
    """断面の真値 h(x) [mm] を (n_y, n_x) で返す。**閉形式・連続**。

    母材面(左 53 度 / 右 37 度)+ 両つま先の外側のガウス溝 + つま先どうしを
    結ぶ弦に放物線の凸みを載せた溶接面。溶接面の端点は**溝を掘ったあとの
    高さ**に合わせてあるので、つま先で段差が出ない。
    """
    xg = np.asarray(x, np.float64)[None, :]
    xl, xr, zl, zr = _toes(p)
    base = np.where(xg <= 0.0, TL * xg, -TR * xg)
    nl = (p["d1"][:, None] / CL) * np.exp(
        -((xg - (xl - UC_OFF_L * CL)) ** 2) / (2 * UC_SIG_L ** 2))
    nr = (p["d2"][:, None] / CR) * np.exp(
        -((xg - (xr + UC_OFF_R * CR)) ** 2) / (2 * UC_SIG_R ** 2))
    outer = base - np.where(xg < xl, nl, 0.0) - np.where(xg > xr, nr, 0.0)
    s = (xg - xl) / (xr - xl)
    face = zl + s * (zr - zl) + 4.0 * p["cv"][:, None] * s * (1.0 - s)
    return np.where((xg >= xl) & (xg <= xr), face, outer)


def true_quantities(p: dict) -> dict:
    """設計寸法から 6 つの計測量の真値を作る(のど厚だけ細格子で解く)。"""
    xl, xr, zl, zr = _toes(p)
    xf = np.linspace(-X_HALF, X_HALF, 40 * N_COL + 1)
    hf = profile_h(xf, p)
    inside = (xf[None, :] >= xl) & (xf[None, :] <= xr)
    d = np.hypot(xf[None, :], hf)                  # 根 (0,0) からの距離
    throat = np.min(np.where(inside, d, np.inf), axis=1)
    # 凸み = 弦からの垂直距離の最大(溶接面のみ)
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
        amp = amp + specular * np.exp(-((dh_dx(h) - phi0) ** 2) / (2 * 0.16 ** 2))
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


def est_centroid(img, half=5):
    """最大値のまわり ±``half`` 行の輝度重心(背景を引いてから)。"""
    k, ok = _peak(img)
    rows = np.arange(IMG_H)[None, :, None]
    w = np.clip(img - BG - 0.02, 0.0, None) * (np.abs(rows - k[:, None, :]) <= half)
    s = w.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = (w * rows).sum(axis=1) / np.maximum(s, 1e-12)
    return np.where(ok & (s > 0), c, np.nan)


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

    HALCON の同名 op は「線の中心線 + 幅」をサブピクセルで返すが、fullseye の
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
            cc = a[:, 1].astype(int)
            np.add.at(acc, cc, a[:, 0])
            np.add.at(cnt, cc, 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[i] = np.where(cnt > 0, acc / np.maximum(cnt, 1e-9), np.nan)
    return out


ESTIMATORS = [("ゼロ点 最大値", est_argmax), ("重心", est_centroid),
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
    返りは断面ごとの直線係数 (a, b) の対(見える点が足りなければ ``None``)。
    """
    out = []
    for lo_hi, sgn in ((PLATE_WIN, -1.0), (PLATE_WIN, +1.0)):
        sel = (np.abs(X) >= lo_hi[0]) & (np.abs(X) <= lo_hi[1]) & (np.sign(X) == sgn)
        hh = h[:, sel]
        xx = np.broadcast_to(X[sel][None, :], hh.shape)
        yy = np.broadcast_to(np.asarray(yv)[:, None], hh.shape)
        m = np.isfinite(hh)
        if int(m.sum()) < 40:
            out.append(None)
            continue
        pts = np.stack([xx[m], yy[m], hh[m]], axis=1)
        c, n, _res = fs.ledger.fit_plane_3d(pts)
        if abs(float(n[2])) < 1e-6:
            out.append(None)
            continue
        a = -float(n[0]) / float(n[2])
        b = float(c[2]) + (float(n[0]) * float(c[0])
                           + float(n[1]) * (float(c[1]) - np.asarray(yv))) / float(n[2])
        out.append((a, np.atleast_1d(b)))
    return out[0], out[1]


def _cross_tau(x, d, i, j):
    """``d`` が ``-TAU`` を横切る位置を線形内挿(i は内側、j は外側の隣)。"""
    if not np.isfinite(d[i]) or not np.isfinite(d[j]) or d[i] == d[j]:
        return float(x[i])
    return float(x[i] + (d[i] + TAU) * (x[j] - x[i]) / (d[i] - d[j]))


def quantities_one(h, aL, bL, aR, bR) -> dict:
    """1 断面 → 6 量。``h`` は NaN 込み(NaN = 測れなかった列)。"""
    out = {k: float("nan") for k in KEYS}
    ok = np.isfinite(h)
    if ok.sum() < 40 or not np.isfinite(aL) or not np.isfinite(aR):
        return out
    xr_root = (bR - bL) / (aL - aR)
    zroot = aL * xr_root + bL
    dL = h - (aL * X + bL)
    dR = h - (aR * X + bR)
    sm = uniform_filter1d(np.where(ok, dL, 0.0), 5) / np.maximum(
        uniform_filter1d(ok.astype(float), 5), 1e-9)
    smR = uniform_filter1d(np.where(ok, dR, 0.0), 5) / np.maximum(
        uniform_filter1d(ok.astype(float), 5), 1e-9)
    # --- 左つま先 = 根より左で「母材面から TAU 以内」の**いちばん内側** ---
    selL = np.nonzero(ok & (X < xr_root - 0.4) & (sm >= -TAU))[0]
    selR = np.nonzero(ok & (X > xr_root + 0.4) & (smR >= -TAU))[0]
    if selL.size == 0 or selR.size == 0:
        return out
    iL, iR = int(selL.max()), int(selR.min())
    xtl = _cross_tau(X, sm, iL, min(iL + 1, N_COL - 1))
    xtr = _cross_tau(X, smR, iR, max(iR - 1, 0))
    if not (xtl < xr_root < xtr):
        return out
    ztl, ztr = aL * xtl + bL, aR * xtr + bR
    out["legL"] = abs(xtl - xr_root) * np.hypot(1.0, aL)
    out["legR"] = abs(xtr - xr_root) * np.hypot(1.0, aR)
    # --- アンダーカット(母材面からの**垂直**距離)---
    for key, sel, dv, a in (("ucL", (X >= xtl - UC_SPAN_L) & (X < xtl), sm, aL),
                            ("ucR", (X > xtr) & (X <= xtr + UC_SPAN_R), smR, aR)):
        m = sel & ok
        if m.any():
            out[key] = float(max(0.0, -np.min(dv[m])) / np.hypot(1.0, a))
    # --- 溶接面 = つま先どうしの間 ---
    face = ok & (X >= xtl) & (X <= xtr)
    if int(face.sum()) < 8:
        return out
    xf, hf = X[face], h[face]
    sl = (ztr - ztl) / (xtr - xtl)
    chord = ztl + (xf - xtl) * sl
    out["cv"] = float(np.max((hf - chord) / np.hypot(1.0, sl)))
    out["throat"] = float(np.min(np.hypot(xf - xr_root, hf - zroot)))
    return out


def measure_all(h: np.ndarray, yv: np.ndarray) -> dict:
    """走査 (n_y, n_x) → 6 量 × n_y の配列。母材面は走査全体から当てる。"""
    pl, pr = fit_plates(h, yv)
    n = h.shape[0]
    out = {k: np.full(n, np.nan) for k in KEYS}
    if pl is None or pr is None:
        return out
    aL, bL = pl
    aR, bR = pr
    for i in range(n):
        q = quantities_one(h[i], aL, float(bL[i] if bL.size > 1 else bL[0]),
                           aR, float(bR[i] if bR.size > 1 else bR[0]))
        for k in KEYS:
            out[k][i] = q[k]
    return out


def score(est: dict, tru: dict) -> dict:
    """量ごとに「測れた率」と「測れたところの平均 |誤差|」を**分けて**返す。"""
    out = {}
    for k in KEYS:
        e, t = np.asarray(est[k], float), np.asarray(tru[k], float)
        m = np.isfinite(e)
        out[k] = {"got": float(m.mean()),
                  "mae": float(np.mean(np.abs(e[m] - t[m]))) if m.any() else float("nan"),
                  "bias": float(np.mean(e[m] - t[m])) if m.any() else float("nan")}
    return out


# =========================================================================== #
# 章                                                                           #
# =========================================================================== #
def section1_scene(p: dict, tru: dict) -> None:
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
    print("  真値の範囲(溶接線 %.0f mm のあいだで変わる):" % Y_MM)
    for k in KEYS:
        v = tru[k]
        print("    %-12s %6.3f 〜 %6.3f mm" % (LABEL[k], v.min(), v.max()))
    print()
    # 検算: 雑音 0・遮蔽なし・対数放物線 なら高さは機械精度で戻るはず
    img, _ = render(p, THETA_REF, noise=0.0, occlusion=False)
    h_est = to_height(est_log_parabola(img), THETA_REF)
    err = np.abs(h_est - profile_h(X, p))
    print("  検算(雑音 0・遮蔽なし): 高さの最大誤差 %.3e mm -> %s"
          % (float(np.nanmax(err)),
             "撮像モデルと逆写像が整合" if np.nanmax(err) < 1e-9 else "★不整合"))
    # 定義の床: 同じ推定器を真値の断面に直接かけたときの残り
    tr_meas = measure_all(profile_h(X, p), p["y"])
    print("  定義の床(真値の断面をそのまま測る = 撮像を通さない):")
    print("    " + " / ".join("%s %+.4f" % (LABEL[k], float(np.mean(tr_meas[k] - tru[k])))
                              for k in KEYS))
    print("    ★つま先を「母材面から %.2f mm 落ちた点」と決めているので、"
          "脚長は必ず外側へ出る。" % TAU)


def section2_estimators(p: dict) -> dict:
    print()
    print("=" * 78)
    print("2) ★ゼロ点(最大値の画素)と 3 つの対比 —— 光条の幅を振る")
    print("=" * 78)
    print("  θ = %.0f 度・雑音 %.1f %%・遮蔽なし。高さの RMS [mm]。" % (THETA_REF, 100 * NOISE))
    print()
    pe = bead_params(y_grid(4))
    h_true = profile_h(X, pe)
    widths = [0.8, 1.1, 1.4, 1.8, 2.4]
    print("  %8s |" % "光条 1σ", end="")
    for name, _ in ESTIMATORS:
        print(" %16s" % name, end="")
    print()
    print("  " + "-" * (10 + 17 * len(ESTIMATORS)))
    table = {name: [] for name, _ in ESTIMATORS}
    for w in widths:
        img, _ = render(pe, THETA_REF, sigma=w, occlusion=False, seed=3)
        print("  %8.1f |" % w, end="")
        for name, fn in ESTIMATORS:
            e = to_height(fn(img), THETA_REF) - h_true
            table[name].append(_rms(e))
            print(" %16.4f" % table[name][-1], end="")
        print()
    print()
    base = table["ゼロ点 最大値"][2]
    print("  1σ = %.1f px でのゼロ点比: " % widths[2]
          + " / ".join("%s %.1f 倍" % (n, base / table[n][2])
                       for n, _ in ESTIMATORS[1:]))
    print("  → ★光条を太らせるほど良くなる(重心 %.4f -> %.4f mm)。"
          % (table["重心"][0], table["重心"][-1]))
    print("     3 画素しか照らさない細い光条にはサブピクセルの足場が無い。")
    print("  → ★op の `lines_gauss` は Frangi リッジの**二値化**なので、"
          "中心をサブピクセルで返さない")
    print("     (%.4f mm = ゼロ点より悪い)。光切断でいちばん要る口が"
          "公開経路に無い。" % table["op lines_gauss"][2])
    return {"widths": widths, "table": table}


def section3_quantities(p: dict, tru: dict) -> None:
    print()
    print("=" * 78)
    print("3) 6 つの計測量(θ = %.0f 度・遮蔽なし・重心)" % THETA_REF)
    print("=" * 78)
    img, _ = render(p, THETA_REF, occlusion=False, seed=7)
    est = measure_all(to_height(est_centroid(img), THETA_REF), p["y"])
    sc = score(est, tru)
    print("  %-12s %10s %10s %10s %8s" % ("量", "真値 平均", "偏り", "平均|誤差|", "測れた"))
    print("  " + "-" * 54)
    for k in KEYS:
        print("  %-12s %10.4f %+10.4f %10.4f %7.0f %%"
              % (LABEL[k], float(np.mean(tru[k])), sc[k]["bias"], sc[k]["mae"],
                 100 * sc[k]["got"]))
    print()
    print("  → 遮蔽が無ければ 6 量とも 0.01 mm 台。壊れるのは 5 章から。")


def section4_predict() -> dict:
    print()
    print("=" * 78)
    print("4) ★★崖を先に予測する —— 幾何だけで、撮る前に")
    print("=" * 78)
    print("  カメラ光線の傾きは cot θ。**傾き cot θ を超えて登る面は自分の陰**。")
    print("  だから遮蔽の始まる角は θ_crit = arctan(1 / 最大割線傾斜)。")
    print()
    pf = bead_params(y_grid(N_Y_FIG))
    xf = np.linspace(-X_HALF, X_HALF, 6 * N_COL + 1)
    hf = profile_h(xf, pf)
    xl, xr, _zl, _zr = _toes(pf)

    def onset(mask):
        """その区間の点が最初に隠れる θ [度](最大割線傾斜から)。"""
        best = np.zeros(hf.shape[0])
        for i in range(hf.shape[0]):
            idx = np.nonzero(mask[i])[0]
            if idx.size == 0:
                continue
            s = 0.0
            for j in idx[::4]:
                dx = xf[j + 1:] - xf[j]
                s = max(s, float(np.max((hf[i, j + 1:] - hf[i, j]) / dx)))
            best[i] = s
        return np.degrees(np.arctan(1.0 / np.maximum(best, 1e-9)))

    m_uc = (xf[None, :] >= xl - UC_SPAN_L) & (xf[None, :] < xl)
    m_pl = (xf[None, :] >= -X_HALF) & (xf[None, :] < xl)
    m_fc = (xf[None, :] >= xl) & (xf[None, :] <= xr)
    o_uc, o_pl, o_fc = onset(m_uc), onset(m_pl), onset(m_fc)
    print("  予測(遮蔽が始まる θ):")
    print("    左母材面ぜんたい  %.1f 度  —— 傾きが一定 tan53 = %.3f なので"
          % (float(np.median(o_pl)), TL))
    print("                              **全部いっせいに**背を向ける(段差の崖)")
    print("    左アンダーカット  %.1f 〜 %.1f 度 —— 溝の斜面が上乗せされる分だけ早い"
          % (float(o_uc.min()), float(o_uc.max())))
    print("    溶接面(左側)    %.1f 度" % float(np.median(o_fc)))
    print("    右側(近側)      遮蔽なし —— 傾きが負(カメラを向いている)")
    print()
    deep = pf["d1"] > 0.40
    shal = pf["d1"] < 0.10
    print("  ★★**深い溝ほど先に隠れる**: 深さ %.2f mm の断面で %.1f 度、"
          % (float(pf["d1"][deep].mean()), float(o_uc[deep].mean())))
    print("     深さ %.2f mm の断面で %.1f 度。いちばん通してはいけない欠陥が"
          % (float(pf["d1"][shal].mean()), float(o_uc[shal].mean())))
    print("     いちばん先に消える。")
    return {"uc": o_uc, "plate": o_pl, "face": o_fc, "d1": pf["d1"]}


ANGLES = (15.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 45.0, 50.0, 57.0, 64.0, 70.0)


def geometric_only(p: dict, tru: dict) -> dict:
    """撮像を通さず、**遮蔽だけ**を入れた誤差(予測の骨)。"""
    out = {k: {"mae": [], "got": []} for k in KEYS}
    h_true = profile_h(X, p)
    for a in ANGLES:
        vis = visible(h_true, a)
        est = measure_all(np.where(vis, h_true, np.nan), p["y"])
        sc = score(est, tru)
        for k in KEYS:
            out[k]["mae"].append(sc[k]["mae"])
            out[k]["got"].append(sc[k]["got"])
    return out


def section5_angle_sweep(p: dict, tru: dict, pred: dict) -> dict:
    print()
    print("=" * 78)
    print("5) ★★三角測量角の掃引 —— 最適角は測定量ごとに違う")
    print("=" * 78)
    print("  対照群 3 つ: (a) 遮蔽なし (b) 遮蔽あり (c) 遮蔽 + 鏡面反射。")
    print("  誤差は**量ごと**に、しかも「測れた率」と分けて数える。")
    print()
    groups = [("a 遮蔽なし", dict(occlusion=False, specular=0.0)),
              ("b 遮蔽あり", dict(occlusion=True, specular=0.0)),
              ("c 遮蔽+鏡面", dict(occlusion=True, specular=3.0))]
    res = {g: {k: {"mae": [], "got": []} for k in KEYS} for g, _ in groups}
    hgt = {g: [] for g, _ in groups}
    h_true = profile_h(X, p)
    for gname, kw in groups:
        for a in ANGLES:
            img, vis = render(p, a, seed=21, **kw)
            hh = to_height(est_centroid(img), a)
            m = np.isfinite(hh) & (vis if kw["occlusion"] else np.ones_like(vis))
            hgt[gname].append(_rms((hh - h_true)[m]))
            sc = score(measure_all(hh, p["y"]), tru)
            for k in KEYS:
                res[gname][k]["mae"].append(sc[k]["mae"])
                res[gname][k]["got"].append(sc[k]["got"])

    print("  高さそのものの RMS [mm](予測 = %.4f/sin θ、θ=%.0f 度で合わせた)"
          % (hgt["a 遮蔽なし"][5] * np.sin(np.deg2rad(ANGLES[5])), ANGLES[5]))
    print("  %6s %10s %10s %10s" % ("θ", "予測 1/sinθ", "a 遮蔽なし", "b 遮蔽あり"))
    c0 = hgt["a 遮蔽なし"][5] * np.sin(np.deg2rad(ANGLES[5]))
    for i, a in enumerate(ANGLES):
        print("  %6.0f %10.4f %10.4f %10.4f"
              % (a, c0 / np.sin(np.deg2rad(a)), hgt["a 遮蔽なし"][i], hgt["b 遮蔽あり"][i]))
    dev = max(abs(hgt["a 遮蔽なし"][i] * np.sin(np.deg2rad(a)) / c0 - 1.0)
              for i, a in enumerate(ANGLES))
    print("  → 遮蔽なしの高さ RMS は 1/sin θ に**最大 %.1f %% で乗る**"
          "(分解能の側は予測どおり)。" % (100 * dev))
    print()

    print("  測れた率 [%] (b 遮蔽あり)")
    print("  %6s" % "θ", end="")
    for k in KEYS:
        print(" %12s" % LABEL[k], end="")
    print()
    for i, a in enumerate(ANGLES):
        print("  %6.0f" % a, end="")
        for k in KEYS:
            print(" %11.0f " % (100 * res["b 遮蔽あり"][k]["got"][i]), end="")
        print()
    print()
    print("  平均|誤差| [mm] (b 遮蔽あり、測れた断面だけ)")
    print("  %6s" % "θ", end="")
    for k in KEYS:
        print(" %12s" % LABEL[k], end="")
    print()
    for i, a in enumerate(ANGLES):
        print("  %6.0f" % a, end="")
        for k in KEYS:
            v = res["b 遮蔽あり"][k]["mae"][i]
            print(" %12s" % ("—" if not np.isfinite(v) else "%.4f" % v), end="")
        print()
    return {"res": res, "hgt": hgt, "c0": c0}


def section6_optimum(sw: dict, geo: dict, p: dict, tru: dict) -> dict:
    print()
    print("=" * 78)
    print("6) ★★最適角 —— 予測と実測を量ごとに突き合わせる")
    print("=" * 78)
    print("  予測 = 「遮蔽だけの誤差(撮像を通さない)」と「雑音だけの誤差")
    print("  (θ=%.0f 度で合わせて 1/sin θ で伸ばす)」の二乗和。" % THETA_REF)
    print()
    res = sw["res"]["b 遮蔽あり"]
    ang = np.asarray(ANGLES)
    rows = []
    for k in KEYS:
        gm = np.asarray(geo[k]["mae"], float)
        gg = np.asarray(geo[k]["got"], float)
        # 雑音だけの誤差: 遮蔽なし条件の基準角の値を 1/sinθ で伸ばす
        n0 = sw["res"]["a 遮蔽なし"][k]["mae"][5] * np.sin(np.deg2rad(ANGLES[5]))
        pred = np.sqrt(np.nan_to_num(gm, nan=1e3) ** 2 + (n0 / np.sin(np.deg2rad(ang))) ** 2)
        pred = np.where(gg < 0.999, np.inf, pred)
        meas = np.asarray(res[k]["mae"], float)
        got = np.asarray(res[k]["got"], float)
        meas = np.where(got < 0.999, np.inf, np.nan_to_num(meas, nan=np.inf))
        ip, im = int(np.argmin(pred)), int(np.argmin(meas))
        rows.append([LABEL[k], "%.0f" % ang[ip], "%.0f" % ang[im],
                     "%.4f" % meas[im], "%.4f" % meas[5],
                     "%.1f" % (meas[5] / meas[im])])
        print("  %-12s 予測 %2.0f 度 / 実測 %2.0f 度   最適角の誤差 %.4f mm   "
              "36 度では %.4f mm (%.1f 倍)"
              % (LABEL[k], ang[ip], ang[im], meas[im], meas[5], meas[5] / meas[im]))
    # 6 量を 1 つに畳んだら
    allm = []
    for i in range(len(ANGLES)):
        v = [res[k]["mae"][i] if res[k]["got"][i] > 0.999 else np.nan for k in KEYS]
        allm.append(np.nan if not np.all(np.isfinite(v)) else float(np.mean(v)))
    allm = np.asarray(allm, float)
    ia = int(np.nanargmin(np.where(np.isfinite(allm), allm, np.inf)))
    uc_at = res["ucL"]["mae"][ia]
    uc_best = min(v for v, g in zip(res["ucL"]["mae"], res["ucL"]["got"])
                  if g > 0.999 and np.isfinite(v))
    print()
    print("  ★6 量の平均に畳むと最適角は %.0f 度。そこでの左アンダーカット誤差は"
          % ang[ia])
    print("     %.4f mm で、左アンダーカット自身の最適角(%.4f mm)の **%.1f 倍**。"
          % (uc_at, uc_best, uc_at / uc_best))
    print("     **1 つの角度で 6 量を同時に最良にはできない。**")
    return {"rows": rows, "all": allm, "best_all": ang[ia]}


def section7_calibration(p: dict, tru: dict) -> dict:
    print()
    print("=" * 78)
    print("7) ★校正誤差(高さ倍率 +1 %)の効き方は量ごとに 3 倍違う")
    print("=" * 78)
    print("  高さだけが (1+ε) 倍になると:")
    print("   ・高さ系(凸み・アンダーカット)はそのまま 1.00·ε")
    print("   ・脚長は母材面の**傾きに応じて** sin²(母材角)·ε だけ動く")
    print("     (つま先の x は動かないが、根と z 方向の伸びが効く)")
    print("   ・のど厚はその中間")
    print()
    sL = np.sin(np.deg2rad(PLATE_L_DEG)) ** 2
    sR = np.sin(np.deg2rad(PLATE_R_DEG)) ** 2
    predict = {"cv": 1.0, "ucL": 1.0, "ucR": 1.0, "legL": sL, "legR": sR,
               "throat": np.nan}
    eps = 0.01
    img, _ = render(p, THETA_REF, occlusion=False, noise=0.0, seed=9)
    h0 = to_height(est_centroid(img), THETA_REF)
    h1 = to_height(est_centroid(img), THETA_REF, k_scale=1.0 / (1.0 + eps))
    q0 = measure_all(h0, p["y"])
    q1 = measure_all(h1, p["y"])
    rows = []
    print("  %-12s %12s %12s" % ("量", "予測 [%]", "実測 [%]"))
    print("  " + "-" * 40)
    for k in KEYS:
        got = float(np.mean((q1[k] - q0[k]) / q0[k]) / eps)
        pv = predict[k]
        rows.append([LABEL[k], "—" if not np.isfinite(pv) else "%.3f" % (100 * pv * eps),
                     "%.3f" % (100 * got * eps)])
        print("  %-12s %12s %12.3f"
              % (LABEL[k], "—" if not np.isfinite(pv) else "%.3f" % (100 * pv * eps),
                 100 * got * eps))
    print()
    print("  → ★同じ 1 % の校正ずれが、同じ図面の中で **%.2f 〜 %.2f %%** の")
    thr = float(np.mean((q1["throat"] - q0["throat"]) / q0["throat"]) / eps)
    lo = min(float(np.mean((q1[k] - q0[k]) / q0[k]) / eps) for k in KEYS)
    hi = max(float(np.mean((q1[k] - q0[k]) / q0[k]) / eps) for k in KEYS)
    print("     幅で出る(%.1f 倍)。のど厚は %.3f %%。"
          % (100 * lo * eps, 100 * hi * eps, hi / lo, 100 * thr * eps))
    print("     「較正精度 1 %」だけでは、どの量が何 % ずれるかを言えない。")
    return {"rows": rows, "throat": thr}


def section8_occlusion_map(pf: dict) -> dict:
    print()
    print("=" * 78)
    print("8) ★遮蔽の地図 —— 法線から描くと投げかけ影が落ちる")
    print("=" * 78)
    h = profile_h(X, pf)
    step = 10                                    # 列を 10 本おき -> Δx = 0.5 mm
    dy = Y_MM / h.shape[0]                       # Δy = 0.5 mm
    dx = step / M_PX_MM
    assert abs(dx - dy) < 1e-9, (dx, dy)
    depth = (-h[:, ::step]) / dx                 # ★等方格子・1 画素 = 1 単位へ
    nrm = np.asarray(fs.ledger.normals_from_depth(depth))
    n = nrm / np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-12)
    n = n * np.sign(-n[..., 2:3] + 1e-15)        # 高さ方向(+h)を向くよう揃える
    nx, nz = n[..., 0], -n[..., 2]
    print("  %6s %14s %14s %10s" % ("θ", "法線で背向き", "水平線で不可視", "差"))
    print("  " + "-" * 48)
    rows = []
    for a in (25.0, 35.0, 45.0, 55.0, 65.0):
        th = np.deg2rad(a)
        back = (nx * np.sin(th) + nz * np.cos(th)) < 0.0
        true_hid = ~visible(h, a)
        rows.append((a, float(back.mean()), float(true_hid[:, ::step].mean())))
        print("  %6.0f %13.1f %% %13.1f %% %9.1f pp"
              % (a, 100 * rows[-1][1], 100 * rows[-1][2],
                 100 * (rows[-1][2] - rows[-1][1])))
    print()
    print("  → 法線は**自己遮蔽(背を向けた面)**しか見ない。水平線の規則は")
    print("     **投げかけ影**(手前の盛り上がりが奥を隠す)も入るので必ず多い。")
    print("  → ★格子間隔が等方でないと `normals_from_depth`(正射)は黙って")
    print("     間違える。生の走査格子は Δx = %.3f mm・Δy = %.3f mm なので、"
          % (1.0 / M_PX_MM, dy))
    print("     10 列おきに間引いて Δx = Δy = %.1f mm に揃えてから渡している。" % dx)
    return {"rows": rows, "normals": n, "depth": depth}


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
    vx = 0.06
    bounds = ((-X_HALF, X_HALF), (0.0, Y_MM), (H_REF, 1.0))
    res = (int(2 * X_HALF / vx), int(Y_MM / 0.5), int((1.0 - H_REF) / vx))
    occ = np.asarray(fs.ledger.occupancy_grid(pts, bounds, res))
    vs = (2 * X_HALF / res[0], Y_MM / res[1], (1.0 - H_REF) / res[2])
    sdf = np.asarray(fs.ledger.esdf(occ, vs))
    roots = np.stack([np.zeros(h.shape[0]), y_grid(h.shape[0]), np.zeros(h.shape[0])], axis=1)
    d_esdf = np.asarray(fs.ledger.query_distance(sdf, bounds, res, roots))
    d_true = true_quantities(pf)["throat"]
    dd = d_esdf - d_true
    print("  占有ボクセル %d 個(%.3f x %.3f x %.3f mm)、根 %d 点で問い合わせ"
          % (int(occ.sum()), vs[0], vs[1], vs[2], len(roots)))
    print("  のど厚: 閉形式 平均 %.4f mm / ESDF 平均 %.4f mm"
          % (float(d_true.mean()), float(d_esdf.mean())))
    print("  差 平均 %+.4f mm(最小 %+.4f / 最大 %+.4f)= ボクセル %.2f 個ぶん"
          % (float(dd.mean()), float(dd.min()), float(dd.max()), float(dd.mean()) / vs[0]))
    print("  → 距離場は最近傍**ボクセル中心**までを測るので、薄い殻を張ると")
    print("     必ず遠めに出る(符号が片側)。y 方向を粗く(%.1f mm)しても"
          % vs[1])
    print("     のど厚は x-z 面内の量なので効かない —— 軸ごとの res が要る所。")
    return {"esdf": d_esdf, "true": d_true, "vs": vs}


def section10_tool_gaps() -> None:
    print()
    print("=" * 78)
    print("10) 道具の穴(光切断の走査を組んでみて)")
    print("=" * 78)
    # (a) 光条中心のサブピクセル抽出
    for nm in ("stripe_center", "light_section", "laser_stripe", "sheet_of_light"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (a) **列ごとの光条中心をサブピクセルで返す op が無い**。`lines_gauss`")
    print("      は在るが Frangi リッジの二値化(輪郭画素の集合)で、HALCON の")
    print("      同名 op が返す中心線 + 線幅は返らない(2 章で 1 桁負けた)。")
    # (b) 遮蔽の地図
    for nm in ("shadow_map", "visibility_map", "horizon_mask"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (b) 高さ場と視線角から**遮蔽の地図**を出す口が無い。法線("
          "`normals_from_depth`)")
    print("      では自己遮蔽しか出ず、投げかけ影は水平線の走査が要る(8 章、")
    print("      本 PoC の `visible` は 3 行)。地形の可視解析では標準の演算。")
    # (c) 名前の衝突
    import inspect
    sig_f = str(inspect.signature(fs.normals_from_depth))
    sig_l = str(inspect.signature(fs.ledger.normals_from_depth.__wrapped__
                                  if hasattr(fs.ledger.normals_from_depth, "__wrapped__")
                                  else fs.ledger.normals_from_depth))
    print("  (c) ★`normals_from_depth` が**ファサードと台帳で別の関数**。")
    print("      `fs.normals_from_depth%s` は K(内部行列)必須の透視版、" % sig_f)
    print("      `fs.ledger.normals_from_depth(...)` は K を取らない正射版。")
    print("      同じ名前で引数が違うので、片方の呼び方を覚えると他方で落ちる。")
    # (d) 1-D の外れ値に強い平滑 / 有効マスクの型
    assert not hasattr(fs, "median_filter_1d") and not hasattr(fs.ledger, "median_filter_1d")
    print("  (d) 「測れなかった」を値と一緒に運ぶ型が無く、(高さ, 有効マスク) の")
    print("      対を呼び手が持ち回るしかない。本 PoC は NaN を約束にしたが、")
    print("      `fit_plane_3d` は NaN を落とさないので**呼び手が先に外す**必要がある。")
    # (e) 在って助かったもの
    assert hasattr(fs.ledger, "fit_plane_3d") and hasattr(fs.ledger, "intersect_planes")
    print("  (e) 在って助かった: `fit_plane_3d`(走査全体から母材面を 1 枚で当てる)、")
    print("      `occupancy_grid`+`esdf`+`query_distance`(のど厚を距離場で、"
          "軸ごとの res)、")
    print("      `normals_from_depth`(等方格子に直せば背向き面の地図が 1 行)。")


# --------------------------------------------------------------------------- #
def make_figures(p, tru, pf, sw, geo, opt, est2, cal, occ, thr) -> None:
    if not figs.enabled():
        return
    h = profile_h(X, pf)
    vis45 = visible(h, 45.0)
    vis25 = visible(h, 25.0)
    figs.save_grid("scene",
                   [h, np.abs(dh_dx(h)), vis25.astype(float), vis45.astype(float)],
                   ["真値の高さ h(x,y) [mm]", "|dh/dx|(遮蔽を決める量)",
                    "見える列 θ=25 度", "見える列 θ=45 度"], ncols=2,
                   title="すみ肉溶接ビードの走査(幅 %.0f mm x 長さ %.0f mm)"
                         % (2 * X_HALF, Y_MM),
                   caption="上段: 左(遠側)の母材面ほど深い。下段: 明るい ="
                           " 測れる。θ=45 度では左母材面が**いっせいに**消える"
                           "(傾き tan53 がカメラ光線の傾き cot45 を超えるため)。")

    figs.save_grid("frames",
                   [render(pf, a, seed=31)[0][pf["y"].size // 2] for a in (25.0, 45.0, 65.0)],
                   ["θ = 25 度(K = %.1f px/mm)" % k_px_mm(25.0),
                    "θ = 45 度(K = %.1f px/mm)" % k_px_mm(45.0),
                    "θ = 65 度(K = %.1f px/mm)" % k_px_mm(65.0)], ncols=1,
                   title="光条の画像(1 断面、%d x %d px)" % (IMG_H, N_COL),
                   caption="θ を大きくすると高さの伸び(K)が増えて分解能は"
                           "上がるが、左半分の光条が消えていく。")

    j = pf["y"].size // 2
    xt = X
    for a, nm in ((28.0, "profile_28"), (50.0, "profile_50")):
        img, _v = render(pf, a, seed=31)
        hh = to_height(est_centroid(img), a)[j]
        figs.save_plot(nm,
                       [("真値", xt, h[j]),
                        ("測れた列", xt[np.isfinite(hh)], hh[np.isfinite(hh)])],
                       xlabel="x [mm]", ylabel="高さ h [mm]",
                       title="断面 y = %.1f mm、θ = %.0f 度" % (pf["y"][j], a),
                       caption="θ = %.0f 度。%s" % (
                           a, "左の母材面と溝がまだ見えている。" if a < 37 else
                           "左母材面が背を向け、左側の 4 量が測れない。"))

    ang = np.asarray(ANGLES)
    res = sw["res"]["b 遮蔽あり"]
    figs.save_plot("angle_sweep",
                   [("%s" % LABEL[k], ang,
                     [v if g > 0.999 and np.isfinite(v) else np.nan
                      for v, g in zip(res[k]["mae"], res[k]["got"])])
                    for k in ("ucL", "legL", "throat", "ucR", "legR")],
                   xlabel="三角測量角 θ [度]", ylabel="平均 |誤差| [mm]",
                   title="測定量ごとに最適角が違う(遮蔽あり)",
                   caption="線が切れているところは「測れなかった」。左側の量は"
                           " 37 度でいっせいに消え、左アンダーカットはその前から"
                           "少しずつ欠ける。")

    figs.save_plot("resolution_vs_occlusion",
                   [("高さ RMS(遮蔽なし)", ang, sw["hgt"]["a 遮蔽なし"]),
                    ("予測 1/sinθ", ang, sw["c0"] / np.sin(np.deg2rad(ang))),
                    ("測れた列の割合(左 UC)", ang,
                     np.asarray([g for g in res["ucL"]["got"]]) * 0.05)],
                   xlabel="三角測量角 θ [度]", ylabel="RMS [mm] / 測れた率 x 0.05",
                   title="分解能は 1/sinθ で良くなり、遮蔽は θ で悪くなる",
                   caption="同じノブの表裏。交点が最適角。")

    figs.save_table("optimum",
                    ["量", "予測 最適角", "実測 最適角", "最適角の |誤差| mm",
                     "36 度での |誤差| mm", "倍率"],
                    opt["rows"], title="最適角: 予測と実測(量ごと)",
                    caption="予測 = 遮蔽だけの誤差と 1/sinθ の雑音の二乗和。")

    figs.save_table("calibration", ["量", "予測 [%]", "実測 [%]"], cal["rows"],
                    title="高さ倍率 +1 % の校正誤差が各量に出る大きさ",
                    caption="脚長は sin²(母材角)倍に薄まる。同じずれが 3 倍違う"
                            "大きさで出る。")

    figs.save_plot("stripe_width",
                   [(n, est2["widths"], est2["table"][n]) for n, _ in ESTIMATORS],
                   xlabel="光条の 1σ [px]", ylabel="高さ RMS [mm]",
                   title="光条を太らせるほどサブピクセルが効く",
                   caption="ゼロ点(最大値の画素)は幅に関係なく 1 画素の階段。"
                           "op の lines_gauss はサブピクセルを返さない。")

    figs.save_grid("map_visibility",
                   [(~visible(h, a)).astype(float) for a in (25.0, 35.0, 45.0)]
                   + [(occ["normals"][..., 0] * np.sin(np.deg2rad(45.0))
                       - occ["normals"][..., 2] * np.cos(np.deg2rad(45.0)) < 0).astype(float)],
                   ["隠れた列 θ=25 度", "隠れた列 θ=35 度", "隠れた列 θ=45 度",
                    "法線だけで見た背向き θ=45 度(粗格子)"], ncols=2,
                   title="遮蔽の地図(明るい = 隠れている)",
                   caption="法線は自己遮蔽だけ。水平線の規則は投げかけ影も入る。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("poc_weld_bead_scan_angle — 光切断で溶接ビードを走査する")
    print("(分解能は 1/sinθ で上がり、遮蔽は cotθ を超えた面から始まる)")
    print()
    p = bead_params(y_grid(N_Y))
    tru = true_quantities(p)
    pf = bead_params(y_grid(N_Y_FIG))

    section1_scene(p, tru)
    est2 = section2_estimators(p)
    section3_quantities(p, tru)
    pred = section4_predict()
    geo = geometric_only(p, tru)
    sw = section5_angle_sweep(p, tru, pred)
    opt = section6_optimum(sw, geo, p, tru)
    cal = section7_calibration(p, tru)
    occ = section8_occlusion_map(pf)
    thr = section9_throat_esdf(pf)
    make_figures(p, tru, pf, sw, geo, opt, est2, cal, occ, thr)
    section10_tool_gaps()

    # --- 所見を固定する(壊れたら鳴る)------------------------------------- #
    res = sw["res"]["b 遮蔽あり"]
    assert res["ucL"]["got"][ANGLES.index(36.0)] > 0.99, "36 度で左 UC が測れない"
    assert res["ucL"]["got"][ANGLES.index(40.0)] < 0.01, "40 度で左 UC が残っている"
    assert res["ucR"]["got"][-1] > 0.99, "右 UC は最大角でも測れるはず"
    assert abs(float(np.median(pred["plate"])) - 37.0) < 0.5, "左母材の崖は 37 度"
    assert float(pred["uc"].min()) < 25.0 < float(pred["uc"].max()), "溝の崖は深さ依存"
    assert est2["table"]["重心"][0] > est2["table"]["重心"][-1], "太い光条のほうが良い"
    assert est2["table"]["op lines_gauss"][2] > est2["table"]["ゼロ点 最大値"][2], \
        "lines_gauss はゼロ点より悪い"

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 分解能(1/sinθ)と遮蔽(cotθ)は同じノブの表裏で、最適角が在る。")
    print("  * その最適角は**量ごとに違う**(実測 %s)。"
          % " / ".join("%s %s 度" % (r[0], r[2]) for r in opt["rows"]))
    print("  * 深いアンダーカットほど先に隠れる —— いちばん危ない欠陥から消える。")
    print("  * 校正誤差の効き方も量ごとに 3 倍違う。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
