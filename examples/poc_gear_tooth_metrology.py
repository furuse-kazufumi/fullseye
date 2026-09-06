# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""歯車の歯形を測る —— 偏心は 1 次、歯は z 次。歯が 1 枚欠けると両方が混ざる。

平歯車の検査(JIS B 1702 / ISO 1328 の歯車精度)を画像でやる、という仕事です。
輪郭を **インボリュート曲線の閉形式** で描くので、ピッチ円直径・歯厚・隣接ピッチ・
歯先円直径・偏心は **式そのものが真値** になります。

EXTEND: 実物に差し替えるなら :func:`make_scene` の返す ``img``(観測画像)と
``truth``(設計諸元 + 与えた偏心)の対を、実写画像と図面値に置き換えます。
**「別の測定器で測った値」を真値にするのは不可** —— 三次元測定機の歯溝振れと
画像の歯先振れは別の量で、規約が違うと 0.01 mm 級の差が説明できなくなります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(2 値化 → 輪郭点 → 最小二乗円)からは「歯車の直径」が出ない**。
   当てはめた円の直径 **47.278 mm** は、ピッチ円 48.000 / 歯先円 52.000 /
   歯底円 43.000 mm の **どれでもない** —— 歯先と歯底のあいだの、歯の
   デューティ比で決まる中間値です。**正直に言うと偏心だけは当たります**
   (0.200 mm → 0.1954 mm、-2.3 %)。ゼロ点が無能なのではない。
   ★★壊れるのは **歯が 1 枚欠けたとき**で、同じ偏心 0.050 mm が
   **0.1285 mm(+157 %)** になる。円 1 個には「歯が 1 枚無い」を表す
   自由度が無いので、欠けは丸ごと中心のずれに化けます。
2. **極座標展開 R(θ) の中央値がピッチ円半径**。デューティ 50 % の半径が
   ピッチ円である、という定義がそのまま「中央値」なので素朴だが厳密です
   (閉形式の検算: デューティ(ピッチ円) = 0.500000)。実測 23.9870 mm
   (真値 24.000、**-0.054 %**)、歯先円半径 26.0027 mm(**+0.011 %**)。
   ★同じプロファイルから出した歯厚は **3.1254 mm(真値 3.1416、-0.516 %)**
   —— 歯先円の **47 倍**ずれます。傾いた歯面をしきい値で切ると縁が面に
   沿って流れるためで、**「よく当たっている」を 1 つの量で代表させられない**。
3. ★**偏心は 1 次成分、歯形は z=24 次成分**なので周波数で切り分かる。偏心
   0.025〜0.200 mm を振ると 1 次振幅は -3.5 %〜-0.5 % で当たり(0.200 mm →
   0.1990 mm)、24 次成分は 2.612 → 2.595 mm とほとんど動きません。
4. ★★**歯が 1 枚欠けると、欠けは全周波数に漏れる**。偏心ゼロの歯車から
   1 枚落としただけで 1 次振幅が **0.1851 mm** 立つ —— 実在する偏心
   0.050 mm の **3.7 倍**。偏心 0.050 mm の歯車で測ると 0.0483 →
   **0.2251 mm(+350 %)**。欠けは局所的な穴で、周期 z の系列には収まりません。
5. ★**歯ごとに 1 標本だけ読むと直る**。歯 1 枚につき歯先半径を 1 個(振れの
   伝統的な測り方)にすると、高次の歯形をそもそも標本化しないので、欠けは
   **標本が 1 個減るだけ**になります。歯欠けありで **0.0501 mm(+0.2 %)**、
   方向も 24.4 deg(真値 25.0)。★対照群として置いた「中央値テンプレートの
   残差」は **0.0558 mm(+11.5 %)で負けました** —— 偏心は歯を角度方向にも
   動かすので、急な歯面に (dR/dθ)·(e/r) ≈ 0.19 mm の残差が立ち、欠けの穴と
   同じ大きさになって分離できない。**「歯形を引き算する」より
   「歯形を標本化しない」ほうが強い**。
6. ★★**照明の傾斜は偏心のふりをする**。偏心は本当にゼロなのに、左右 ±30 %
   の傾斜で **見かけの偏心 0.2101 mm**。対照群(傾斜ゼロ)は 0.0011 mm なので、
   これは全部が照明由来です。**勾配最大の縁**に変えると 0.0320 mm まで
   下がります(それでもゼロではない)。
7. ★**予想が外れた**: 「基準の軸穴も同じ向きへ流れるから打ち消すだろう」と
   踏んでいました。実測は **軸を実測 0.2101 mm > 軸を真値に固定 0.1846 mm**
   —— 打ち消すどころか **1.14 倍**。符号を見ると理由が分かります:
   外形の中心は **+0.1846 mm(明るい側へ)**、軸穴の中心は
   **-0.0265 mm(暗い側へ)** で **逆向き**。どちらの縁も「明るい側では外へ、
   暗い側では内へ」動くのに、穴は内外が裏返っているので中心のずれが反転し、
   基準と対象の差が広がります。
8. ★**偏心は隣接ピッチ誤差を捏造する**。歯の割り出しは設計どおり完璧なのに、
   偏心 0.100 mm で隣接ピッチ誤差の最大 0.0320 mm、その **1 次振幅 0.0272 mm**
   は理論値 2e·sin(π/z) = 0.0261 mm と **4 %** で一致します。逆に本物の
   割り出し誤差 0.050 mm は最大 0.0538 mm・1 次振幅 0.0011 mm(= 局所的)で、
   **1 次振幅を見れば振れと割り出しを分けられる**。分けずに報告すると
   歯切り盤の割り出しを疑うことになります。

来歴(公開文献のみ): ISO 1328-1:2013 *Cylindrical gears — ISO system of flank
tolerance classification* / JIS B 1702-1 / Buckingham, *Analytical Mechanics of
Gears* (Dover, 1988) —— インボリュート関数 inv(φ)=tan φ − φ と歯厚の式 /
Coope, *J. Optim. Theory Appl.* 76 (1993) 381 —— 円の最小二乗当てはめ。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 歯車の諸元(ここが真値)--------------------------------------------------- #
MODULE_MM = 2.0          # モジュール m [mm]
Z_TEETH = 24             # 歯数 z
ALPHA_DEG = 20.0         # 圧力角 α [deg]
BORE_MM = 8.0            # 軸穴の半径 [mm](= 測定基準)
PX_MM = 0.14             # 画素の大きさ [mm/px]
N_PIX = 448              # 視野 [px]
SS = 3                   # 面積被覆のための細分割(1 画素を SS x SS で数える)
N_ANG = 720              # 極座標展開の角度分割
FG, BG = 0.78, 0.16      # 歯車と背景の明るさ
PSF_SIGMA = 1.2          # 撮像系のぼけ [px]
NOISE = 0.004            # 撮像ノイズ(1σ)
TH0 = 0.0                # 1 番目の歯の中心角 [rad]
ECC_DEG = 25.0           # 偏心の向き [deg](真値)

# 派生量(すべて閉形式)
R_PITCH = MODULE_MM * Z_TEETH / 2.0                  # ピッチ円半径 24.000 mm
R_TIP = R_PITCH + MODULE_MM                          # 歯先円半径 26.000 mm
R_ROOT = R_PITCH - 1.25 * MODULE_MM                  # 歯底円半径 21.500 mm
R_BASE = R_PITCH * np.cos(np.radians(ALPHA_DEG))     # 基礎円半径 22.553 mm
PITCH_ANG = 2.0 * np.pi / Z_TEETH                    # 角ピッチ [rad]
PITCH_MM = np.pi * MODULE_MM                         # 円ピッチ [mm]
THICK_MM = np.pi * MODULE_MM / 2.0                   # ピッチ円上の歯厚 [mm]

_LAB = fs.ledger         # blob 族の公開経路


# --------------------------------------------------------------------------- #
# 1. インボリュート歯形 —— 真値は式そのもの                                     #
# --------------------------------------------------------------------------- #
def inv(phi):
    """インボリュート関数 inv(φ) = tan φ − φ。"""
    return np.tan(phi) - phi


def half_tooth_angle(r_mm):
    """半径 ``r`` における **歯の半角** ψ(r) [rad](閉形式)。

    ψ(r) = ψ_p + inv(α) − inv(φ(r)),  cos φ(r) = r_b / r

    ψ_p = π/(2z) はピッチ円上の半角(標準歯車、バックラッシ 0)。基礎円より
    内側(歯底 ≤ r < 基礎円)は **半径直線** で近似する —— 実際はトロコイドだが、
    この PoC が測る量(ピッチ円より外)には効かない。定義域の外は ``nan``。
    """
    r = np.asarray(r_mm, np.float64)
    psi_p = np.pi / (2.0 * Z_TEETH)
    inv_a = inv(np.radians(ALPHA_DEG))
    out = np.full(r.shape, np.nan)
    band_root = (r >= R_ROOT) & (r < R_BASE)
    out[band_root] = psi_p + inv_a
    band = (r >= R_BASE) & (r <= R_TIP)
    phi = np.arccos(np.clip(R_BASE / np.where(band, r, R_BASE), -1.0, 1.0))
    out[band] = psi_p + inv_a - inv(phi[band])
    return out


def duty_at(r_mm: float) -> float:
    """半径 ``r`` の円周のうち **歯が占める割合**(閉形式)。ピッチ円で厳密に 0.5。"""
    psi = float(half_tooth_angle(np.asarray([r_mm]))[0])
    if not np.isfinite(psi):
        return 1.0 if r_mm < R_ROOT else 0.0
    return float(np.clip(Z_TEETH * psi / np.pi, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 2. 場面を作る —— 面積被覆で塗ってからぼかす                                   #
# --------------------------------------------------------------------------- #
def make_scene(ecc_mm: float = 0.0, ecc_deg: float = ECC_DEG, missing: tuple = (),
               pitch_off_mm: float = 0.0, pitch_off_tooth: int = 6,
               illum: float = 0.0, seed: int = 7) -> dict:
    """歯車 1 個の観測画像と真値を返す。

    ``ecc_mm`` は **歯の並びの中心を軸穴からずらす量**(= 偏心・振れ)。軸穴は
    つねに画像中心にあり、**測定基準は軸穴**。``missing`` は歯を落とす番号の列、
    ``pitch_off_mm`` は 1 枚だけ円周方向にずらす量(割り出し誤差)。
    ``illum`` は左右方向の照明傾斜(±illum の乗算)。
    """
    rng = np.random.default_rng(seed)
    cen = (N_PIX - 1) / 2.0                                # 軸(= 軸穴)の中心 [px]
    dy_g = ecc_mm / PX_MM * np.sin(np.radians(ecc_deg))    # 歯の並びの中心のずれ
    dx_g = ecc_mm / PX_MM * np.cos(np.radians(ecc_deg))

    # 細分割した標本点(1 画素を SS x SS で被覆率として数える)
    off = (np.arange(SS) + 0.5) / SS - 0.5
    base = np.arange(N_PIX, dtype=np.float64)
    yy = (base[:, None] + off[None, :]).ravel()
    xx = yy
    gy = yy[:, None] - cen - dy_g
    gx = xx[None, :] - cen - dx_g
    r_g = np.hypot(gy, gx) * PX_MM                          # 歯の中心からの半径 [mm]
    th = np.arctan2(gy, gx)

    # 歯の番号と、その歯の中心から測った角度
    a = (th - TH0) / PITCH_ANG
    k = np.rint(a).astype(np.int32)
    u = (a - k) * PITCH_ANG
    kk = np.mod(k, Z_TEETH)
    if pitch_off_mm:
        offs = np.zeros(Z_TEETH)
        offs[pitch_off_tooth % Z_TEETH] = pitch_off_mm / R_PITCH   # 弧長 -> 角度
        u = u - offs[kk]

    psi = half_tooth_angle(r_g)
    tooth = np.isfinite(psi) & (np.abs(u) <= psi) & (r_g > R_ROOT)
    if missing:
        tooth &= ~np.isin(kk, np.asarray(missing, np.int32))
    solid = (r_g <= R_ROOT) | tooth

    # 軸穴(基準)—— 画像中心にあり、歯の並びとは別の中心を持つ
    ay = yy[:, None] - cen
    ax = xx[None, :] - cen
    r_a = np.hypot(ay, ax) * PX_MM
    solid &= r_a > BORE_MM

    cov = solid.reshape(N_PIX, SS, N_PIX, SS).mean(axis=(1, 3))
    img = BG + (FG - BG) * cov
    if illum:
        ramp = 1.0 + illum * ((np.arange(N_PIX) - cen) / (N_PIX / 2.0))
        img = img * ramp[None, :]
    # 撮像系のぼけ。★2-D のガウスぼかしは σ を直に渡す口が無く、進化 op の
    #   つまみ a から σ = 0.3 + 2.7 a を逆算して渡す(末尾「道具の穴」(c))。
    img = np.asarray(fs.apply(img, "gauss_filter", a=(PSF_SIGMA - 0.3) / 2.7))
    img = img + rng.normal(0.0, NOISE, img.shape)
    return {"img": np.clip(img, 0.0, 1.2), "axis": (cen, cen),
            "gear_center": (cen + dy_g, cen + dx_g), "ecc_mm": ecc_mm,
            "ecc_deg": ecc_deg, "missing": tuple(missing),
            "pitch_off_mm": pitch_off_mm, "pitch_off_tooth": pitch_off_tooth,
            "illum": illum}


# --------------------------------------------------------------------------- #
# 3. 縁を取る —— 2 つの規約(固定しきい値 / 勾配最大)                          #
# --------------------------------------------------------------------------- #
def _subpixel_threshold(prof, s_mm, thr):
    """外側から見て最初に ``thr`` を下回る位置を線形補間で返す [mm]。"""
    above = prof >= thr
    idx = np.nonzero(above)[0]
    if idx.size == 0:
        return np.nan
    i = int(idx[-1])
    if i + 1 >= prof.size:
        return float(s_mm[i])
    f = (prof[i] - thr) / (prof[i] - prof[i + 1] + 1e-12)
    return float(s_mm[i] + f * (s_mm[i + 1] - s_mm[i]))


def _subpixel_gradient(prof, s_mm):
    """勾配が最も急に落ちる位置を放物線当てはめで返す [mm]。"""
    g = np.diff(prof)
    i = int(np.argmin(g))
    if i <= 0 or i + 2 >= prof.size:
        return float(0.5 * (s_mm[i] + s_mm[i + 1]))
    y0, y1, y2 = g[i - 1], g[i], g[i + 1]
    den = y0 - 2.0 * y1 + y2
    d = 0.0 if abs(den) < 1e-12 else 0.5 * (y0 - y2) / den
    d = float(np.clip(d, -1.0, 1.0))
    step = s_mm[1] - s_mm[0]
    return float(0.5 * (s_mm[i] + s_mm[i + 1]) + d * step)


def radial_profile(img, centre, rule: str = "threshold", n_ang: int = N_ANG) -> np.ndarray:
    """``centre``(row, col)[px] を極として、角度ごとの外形半径 R(θ) [mm] を返す。

    半径方向は :func:`fullseye.line_profile`(双一次補間)で 0.25 px 刻みに
    掃く。``rule`` は縁の規約: ``threshold``(固定しきい値 (FG+BG)/2)か
    ``gradient``(勾配最大)。
    """
    cy, cx = centre
    r0 = (R_ROOT - 2.0) / PX_MM
    r1 = (R_TIP + 2.0) / PX_MM
    n = int((r1 - r0) / 0.25) + 1
    s_mm = np.linspace(r0, r1, n) * PX_MM
    thr = 0.5 * (FG + BG)
    th = np.arange(n_ang) * (2.0 * np.pi / n_ang)
    out = np.empty(n_ang)
    for i, t in enumerate(th):
        p0 = (cy + r0 * np.sin(t), cx + r0 * np.cos(t))
        p1 = (cy + r1 * np.sin(t), cx + r1 * np.cos(t))
        prof = np.asarray(fs.line_profile(img, p0, p1, num=n))
        out[i] = (_subpixel_threshold(prof, s_mm, thr) if rule == "threshold"
                  else _subpixel_gradient(prof, s_mm))
    return out


def bore_centre(img) -> dict:
    """軸穴(基準)の中心と半径を、穴の輪郭に円を当てて求める。

    穴は「暗いのに視野の縁に触れていない連結成分」。``blob_*`` 族で切り出し、
    その内側輪郭に :func:`fullseye.fit_circle` を当てる。
    """
    dark = np.asarray(img) < 0.5 * (FG + BG)
    lab = _LAB.blob_label(dark)
    f = _LAB.blob_features(lab)
    inside = np.nonzero(~np.asarray(f["touches_border"], bool))[0]
    if inside.size == 0:
        raise RuntimeError("軸穴が見つからない")
    j = int(inside[np.argmax(np.asarray(f["area"])[inside])])
    bnd = _LAB.blob_boundaries(_LAB.blob_region(lab, j + 1).astype(np.int32))
    pts = np.column_stack(np.nonzero(np.asarray(bnd)))
    c = fs.fit_circle(pts.astype(np.float64))
    return {"cy": float(c["cy"]), "cx": float(c["cx"]),
            "r_mm": float(c["r"]) * PX_MM, "rms_px": float(c["rms"])}


# --------------------------------------------------------------------------- #
# 4. 周波数で分ける —— 1 次 = 偏心、z 次 = 歯                                   #
# --------------------------------------------------------------------------- #
def harmonics(prof) -> np.ndarray:
    """R(θ) の各次数の振幅 [mm](0 次は平均半径)。"""
    n = prof.size
    c = np.fft.rfft(prof) / n
    amp = 2.0 * np.abs(c)
    amp[0] = np.abs(c[0])
    return amp


def fit_orders(prof, keep, orders) -> dict:
    """指定した次数だけの最小二乗当てはめ(角度の一部を捨てられる)。

    ``keep`` は使う角度の bool マスク。歯が欠けた角度を外して当てるために要る
    —— 全周の FFT は捨てた区間を扱えない(0 で埋めると別の漏れを作る)。
    """
    n = prof.size
    th = np.arange(n) * (2.0 * np.pi / n)
    cols = [np.ones(n)]
    names = ["dc"]
    for o in orders:
        cols += [np.cos(o * th), np.sin(o * th)]
        names += ["c%d" % o, "s%d" % o]
    a = np.column_stack(cols)[keep]
    coef, *_ = np.linalg.lstsq(a, prof[keep], rcond=None)
    out = {"dc": float(coef[0])}
    for i, o in enumerate(orders):
        out[o] = float(np.hypot(coef[1 + 2 * i], coef[2 + 2 * i]))
    out["_names"] = names
    return out


# --------------------------------------------------------------------------- #
# 5. 歯ごとの量 —— 歯厚・隣接ピッチ・歯先半径                                   #
# --------------------------------------------------------------------------- #
def tooth_table(prof, r_ref_mm: float) -> dict:
    """``r_ref`` を横切る区間から、歯ごとの角幅・中心角・歯先半径を出す。

    立ち上がり(内→外)と立ち下がり(外→内)を線形補間で拾い、**各立ち上がり
    の直後に来る立ち下がり**を対にする。周回を跨ぐ 1 枚を落とさないよう、
    差はすべて mod 2π で取る。
    """
    n = prof.size
    th = np.arange(n) * (2.0 * np.pi / n)
    above = prof >= r_ref_mm
    nxt = np.roll(above, -1)
    ri = np.nonzero(~above & nxt)[0]
    fi = np.nonzero(above & ~nxt)[0]
    if ri.size == 0 or ri.size != fi.size:
        return {"n": 0}
    rise = np.asarray([_cross(th, prof, i, (i + 1) % n, r_ref_mm) for i in ri])
    fall = np.asarray([_cross(th, prof, i, (i + 1) % n, r_ref_mm) for i in fi])
    width = np.asarray([np.mod(fall - r, 2.0 * np.pi).min() for r in rise])
    centre = np.mod(rise + 0.5 * width, 2.0 * np.pi)
    order = np.argsort(centre)
    centre, width = centre[order], width[order]
    tip = np.asarray([prof[np.abs(np.mod(th - c + np.pi, 2 * np.pi) - np.pi)
                           < 0.35 * PITCH_ANG].max() for c in centre])
    step = np.diff(np.append(centre, centre[0] + 2.0 * np.pi))
    return {"n": int(centre.size), "centre": centre, "width": width, "tip": tip,
            "pitch_mm": step * r_ref_mm}


def median_tooth(prof, n_teeth: int = Z_TEETH):
    """**歯 1 枚ぶんの中央値テンプレート**と、そこからの残差を返す。

    R(θ) を ``n_teeth`` 個の扇形に折り畳み、位相ごとに中央値を取る。偏心
    ``e cos(θ−φ)`` は 24 個の等間隔な角度で中央値を取ると打ち消えるので、
    テンプレートには **歯形だけ** が残る。残差 = R − テンプレート は
    「偏心 + 欠けた歯の穴」になり、両者は大きさが 1 桁違うので分けられる。
    """
    n = prof.size
    if n % n_teeth:
        raise ValueError("角度分割 %d は歯数 %d で割り切れること" % (n, n_teeth))
    np_ = n // n_teeth
    tmpl = np.median(prof.reshape(n_teeth, np_), axis=0)
    return tmpl, prof - np.tile(tmpl, n_teeth)


def runout_per_tooth(prof) -> dict:
    """**歯 1 枚につき 1 個の半径**(歯先)から 1 次成分を出す。

    これが歯車振れの伝統的な測り方(歯溝にボールを当てて 1 周ぶん読む)。
    高次の歯形成分をそもそも標本化しないので、**欠けた歯は「1 標本落ちる」
    だけ** になり、残りの 23 枚で 1 次を当てられる。
    """
    tt = tooth_table(prof, R_PITCH)
    if tt["n"] < 5:
        return {"ecc": float("nan"), "deg": float("nan"), "n": tt.get("n", 0)}
    th, r = tt["centre"], tt["tip"]
    a = np.column_stack([np.ones_like(th), np.cos(th), np.sin(th)])
    c, *_ = np.linalg.lstsq(a, r, rcond=None)
    return {"ecc": float(np.hypot(c[1], c[2])),
            "deg": float(np.degrees(np.arctan2(c[2], c[1])) % 360.0),
            "n": int(tt["n"])}


def runout_template(prof, n_teeth: int = Z_TEETH, k_mad: float = 6.0) -> dict:
    """中央値テンプレートの残差から 1 次成分を出す(**対照群**)。

    残差の中央絶対偏差で外れ値を拾い、その前後 0.7 ピッチを捨ててから
    ``{1, 2 次}`` を当てる。捨てた区間を 0 で埋めないのは、そこに本来ある
    偏心成分まで消してしまうから。
    """
    n = prof.size
    _, resid = median_tooth(prof, n_teeth)
    mad = 1.4826 * float(np.median(np.abs(resid - np.median(resid)))) + 1e-9
    bad = np.abs(resid - np.median(resid)) > k_mad * mad
    th = np.arange(n) * (2.0 * np.pi / n)
    keep = np.ones(n, bool)
    if bad.any():
        for c in th[bad]:
            keep &= np.abs(np.mod(th - c + np.pi, 2 * np.pi) - np.pi) > 0.7 * PITCH_ANG
    if keep.sum() < 0.4 * n:                       # 捨てすぎたら諦めて全周を使う
        keep = np.ones(n, bool)
    f = fit_orders(resid, keep, [1, 2])
    return {"ecc": f[1], "n_bad": int(bad.sum()), "kept": float(keep.mean()),
            "resid": resid, "keep": keep}


def _cross(th, prof, i, j, level):
    """標本 i, j のあいだで ``level`` を横切る角度(線形補間、周回を跨いでよい)。"""
    t0, t1 = th[i], th[j]
    if t1 < t0:
        t1 += 2.0 * np.pi
    f = (level - prof[i]) / (prof[j] - prof[i] + 1e-12)
    return float(np.mod(t0 + np.clip(f, 0.0, 1.0) * (t1 - t0), 2.0 * np.pi))


# --------------------------------------------------------------------------- #
# 節 1. ゼロ点 —— 2 値化 + 輪郭 + 最小二乗円                                    #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 2 値化 -> 外形の輪郭点 -> 最小二乗円")
    print("=" * 78)

    print("   偏心 [mm]  歯欠け   当てはめ円の直径 [mm]   中心の軸からの距離 [mm]"
          "   偏心の誤差")
    rows = []
    keep = None
    cen = (N_PIX - 1) / 2.0
    for ecc, miss in ((0.0, ()), (0.050, ()), (0.200, ()), (0.050, (11,))):
        sc = make_scene(ecc_mm=ecc, missing=miss)
        img = sc["img"]
        lab = _LAB.blob_label(img >= 0.5 * (FG + BG))
        big = _LAB.blob_select_largest(lab, 1)
        bnd = np.asarray(_LAB.blob_boundaries(big))
        # 外形の輪郭だけ(軸穴の縁は基準半径より内側なので落とす)
        pts = np.column_stack(np.nonzero(bnd)).astype(np.float64)
        rr = np.hypot(pts[:, 0] - cen, pts[:, 1] - cen) * PX_MM
        outer = pts[rr > 0.5 * (BORE_MM + R_ROOT)]
        c = fs.fit_circle(outer)
        dia = 2.0 * float(c["r"]) * PX_MM
        run = np.hypot(float(c["cy"]) - cen, float(c["cx"]) - cen) * PX_MM
        err = "  --   " if ecc == 0 else "%+7.2f %%" % (100 * (run - ecc) / ecc)
        rows.append((ecc, bool(miss), dia, run))
        print("     %.3f      %s          %.3f                 %.4f            %s"
              % (ecc, "有" if miss else "無", dia, run, err))
        if keep is None:
            keep = (sc, big)

    print("\n  真値: ピッチ円 %.3f / 歯先円 %.3f / 歯底円 %.3f mm" % (
        2 * R_PITCH, 2 * R_TIP, 2 * R_ROOT))
    print("  ★当てはめ円の直径 %.3f mm は、この 3 つの **どれでもない** ——"
          " 歯先と歯底のあいだの、歯のデューティ比で決まる中間値。"
          % rows[0][2])
    print("     「歯車の直径」と書いて出せる数字がここには無い。")
    print("  正直に: **偏心だけは当たる**。歯が揃っていれば当てはめ円の中心は歯の"
          "並びの中心に来るので、\n     軸(軸穴)から測れば %.4f mm(真値 %.3f、"
          "%+.1f %%)。ゼロ点が無能なのではない。"
          % (rows[2][3], rows[2][0], 100 * (rows[2][3] - rows[2][0]) / rows[2][0]))
    print("  ★★壊れるのは歯が 1 枚欠けたとき: 同じ偏心 %.3f mm が %.4f mm"
          "(%+.0f %%)になる。" % (rows[3][0], rows[3][3],
                                  100 * (rows[3][3] - rows[3][0]) / rows[3][0]))
    print("     円 1 個には「歯が 1 枚無い」を表す自由度が無いので、"
          "欠けは丸ごと中心のずれに化ける。")

    sc, big = keep
    figs.save_grid("scene",
                   [sc["img"], _LAB.blob_overlay(sc["img"], big)],
                   ["観測画像 m=%.1f z=%d a=%.0f" % (MODULE_MM, Z_TEETH, ALPHA_DEG),
                    "2 値化した歯車(軸穴が基準)"],
                   title="インボリュート歯車 1 px = %.2f mm" % PX_MM)
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 節 2. 極座標展開 —— 中央値がピッチ円                                          #
# --------------------------------------------------------------------------- #
def section_polar() -> dict:
    print("\n" + "=" * 78)
    print("2) 極座標展開 R(θ) —— 中央値 = ピッチ円半径(デューティ 50 %)")
    print("=" * 78)

    sc = make_scene(ecc_mm=0.0)
    b = bore_centre(sc["img"])
    cen = (N_PIX - 1) / 2.0
    print("  軸穴: 中心の誤差 %.4f px / 半径 %.4f mm(真値 %.3f)/ 当てはめ残差 %.3f px"
          % (np.hypot(b["cy"] - cen, b["cx"] - cen), b["r_mm"], BORE_MM, b["rms_px"]))

    prof = radial_profile(sc["img"], (b["cy"], b["cx"]))
    r_pitch = float(np.median(prof))
    r_tip = float(np.percentile(prof, 99.0))
    tt = tooth_table(prof, R_PITCH)
    thick = tt["width"] * R_PITCH
    print("  デューティ 50 %% の半径(= 中央値) %.4f mm  真値 %.3f  (%+.3f %%)"
          % (r_pitch, R_PITCH, 100 * (r_pitch - R_PITCH) / R_PITCH))
    print("  歯先円半径(99 パーセンタイル)   %.4f mm  真値 %.3f  (%+.3f %%)"
          % (r_tip, R_TIP, 100 * (r_tip - R_TIP) / R_TIP))
    print("  歯の数 %d(真値 %d)" % (tt["n"], Z_TEETH))
    print("  ピッチ円上の歯厚 %.4f ± %.4f mm  真値 %.4f  (%+.3f %%)"
          % (thick.mean(), thick.std(), THICK_MM,
             100 * (thick.mean() - THICK_MM) / THICK_MM))
    print("  隣接ピッチ %.4f ± %.4f mm  真値 %.4f、誤差の最大 %.4f mm"
          % (tt["pitch_mm"].mean(), tt["pitch_mm"].std(), PITCH_MM,
             np.abs(tt["pitch_mm"] - PITCH_MM).max()))
    print("  検算(閉形式): デューティ(ピッチ円) = %.6f / (歯先円) = %.6f"
          % (duty_at(R_PITCH), duty_at(R_TIP - 1e-9)))

    th_deg = np.degrees(np.arange(N_ANG) * 2 * np.pi / N_ANG)
    m = th_deg < 3.2 * np.degrees(PITCH_ANG)
    truth = np.asarray([_truth_radius(t) for t in np.radians(th_deg[m])])
    figs.save_plot("profile",
                   [("真値(閉形式)", th_deg[m], truth),
                    ("実測 R(θ)", th_deg[m], prof[m]),
                    ("ピッチ円", th_deg[m], np.full(m.sum(), R_PITCH))],
                   xlabel="角度 [deg]", ylabel="半径 [mm]",
                   title="歯 3 枚ぶんの極座標展開(真値と実測)")
    return {"prof": prof, "bore": b, "r_pitch": r_pitch, "r_tip": r_tip,
            "thick": thick, "tt": tt}


def _truth_radius(theta: float) -> float:
    """角度 θ における外形半径の **閉形式**(真値、偏心なし)。"""
    u = ((theta - TH0 + np.pi / Z_TEETH) % PITCH_ANG) - np.pi / Z_TEETH
    r = np.linspace(R_ROOT, R_TIP, 4001)
    psi = half_tooth_angle(r)
    ok = np.isfinite(psi) & (psi >= abs(u))
    return float(r[ok].max()) if ok.any() else R_ROOT


# --------------------------------------------------------------------------- #
# 節 3-5. 偏心を振る / 歯を欠けさせる / 外して測り直す                          #
# --------------------------------------------------------------------------- #
def section_eccentricity() -> dict:
    print("\n" + "=" * 78)
    print("3) 偏心を振る —— 1 次成分が偏心、z 次成分が歯")
    print("=" * 78)
    print("   偏心 [mm]   1 次 [mm]   誤差      2 次 [mm]   %d 次 [mm]  %d 次 [mm]"
          % (Z_TEETH, 2 * Z_TEETH))

    eccs, est = [], []
    spec_keep = None
    for e in (0.000, 0.025, 0.050, 0.100, 0.200):
        sc = make_scene(ecc_mm=e)
        b = bore_centre(sc["img"])
        prof = radial_profile(sc["img"], (b["cy"], b["cx"]))
        amp = harmonics(prof)
        eccs.append(e)
        est.append(float(amp[1]))
        err = "  --   " if e == 0 else "%+6.2f %%" % (100 * (amp[1] - e) / e)
        print("    %.3f      %.4f    %s    %.4f      %.4f      %.4f"
              % (e, amp[1], err, amp[2], amp[Z_TEETH], amp[2 * Z_TEETH]))
        if e == 0.050:
            spec_keep = amp
    print("  ★1 次は偏心を当てる。%d 次(歯)は偏心を変えてもほとんど動かない。"
          % Z_TEETH)
    return {"ecc": eccs, "est": est, "spec": spec_keep}


def section_missing_tooth() -> dict:
    print("\n" + "=" * 78)
    print("4-5) ★★歯が 1 枚欠けると全周波数に漏れる / 外して測り直すと戻る")
    print("=" * 78)

    print("   偏心 [mm]  歯欠け  検出した歯   FFT の 1 次   歯ごと 1 標本   "
          "中央値テンプレート(対照)")
    rows = []
    figs_keep = {}
    for ecc in (0.000, 0.050):
        for miss in ((), (11,)):
            sc = make_scene(ecc_mm=ecc, missing=miss)
            b = bore_centre(sc["img"])
            prof = radial_profile(sc["img"], (b["cy"], b["cx"]))
            amp = harmonics(prof)
            pt = runout_per_tooth(prof)
            tm = runout_template(prof)
            rows.append((ecc, bool(miss), pt["n"], float(amp[1]), pt["ecc"],
                         tm["ecc"], pt["deg"]))
            print("     %.3f      %s       %2d 枚      %.4f mm     %.4f mm      "
                  "%.4f mm" % (ecc, "有" if miss else "無", pt["n"], amp[1],
                               pt["ecc"], tm["ecc"]))
            if ecc == 0.050:
                figs_keep["miss" if miss else "ok"] = (sc, prof, amp, tm)

    e0_miss = rows[1][3]
    e5_ok, e5_miss, e5_pt, e5_tm = rows[2][3], rows[3][3], rows[3][4], rows[3][5]
    print("\n  ★★偏心ゼロの歯車から 1 枚落としただけで、FFT の 1 次が %.4f mm 立つ"
          "(実在する偏心 0.050 mm の %.1f 倍)。" % (e0_miss, e0_miss / 0.050))
    print("     欠けは局所的な穴なので、周期 z の系列には収まらず **全次数へ漏れる**"
          " —— その一部が 1 次に落ちる。")
    print("  ★直し方: 歯 1 枚につき歯先半径を 1 個だけ読む(振れの伝統的な測り方)。")
    print("     高次の歯形をそもそも標本化しないので、欠けは **標本が 1 個減るだけ**"
          "になる。")
    print("     偏心 0.050 mm の歯車: 欠け無し FFT %.4f mm (%+.1f %%) -> 欠け有り "
          "FFT %.4f mm (%+.0f %%) -> 歯ごと 1 標本 %.4f mm (%+.1f %%)。"
          % (e5_ok, 100 * (e5_ok - 0.05) / 0.05, e5_miss,
             100 * (e5_miss - 0.05) / 0.05, e5_pt, 100 * (e5_pt - 0.05) / 0.05))
    print("     方向も出る: 推定 %.1f deg(真値 %.1f deg)。"
          % (rows[3][6], ECC_DEG))
    print("  対照群(中央値テンプレート): %.4f mm (%+.1f %%)。こちらは **効きが悪い** "
          "—— 偏心は歯を角度方向にも動かすので、\n     急な歯面では"
          "(dR/dθ)·(e/r) ≈ %.2f mm の残差が立ち、欠けの穴と同じ大きさになって"
          "分離できない。" % (e5_tm, 100 * (e5_tm - 0.05) / 0.05,
                              0.050 / R_PITCH * (R_TIP - R_ROOT) / 0.05))

    sc_ok, prof_ok, amp_ok, rr_ok = figs_keep["ok"]
    sc_ms, prof_ms, amp_ms, rr_ms = figs_keep["miss"]
    n_show = 3 * Z_TEETH + 2
    k = np.arange(n_show)
    # 歯の次数(24/48/72)は 2.6 mm あって縦軸を潰すので、**呼び手が 0.35 mm で
    # 切ってから**渡す(切ったことは題に書く)。
    cap = 0.35
    figs.save_plot("spectrum",
                   [("歯欠け無し", k[1:], np.minimum(amp_ok[1:n_show], cap)),
                    ("歯欠け有り", k[1:], np.minimum(amp_ms[1:n_show], cap))],
                   xlabel="次数(1 = 偏心、%d = 歯)" % Z_TEETH,
                   ylabel="振幅 [mm](%.2f mm で切って表示)" % cap,
                   title="1 枚の歯欠けは全次数に漏れる(偏心 0.050 mm)",
                   caption="歯の次数 24/48/72 は 2.6 mm あるので %.2f mm で切った"
                           % cap)
    figs.save_grid("missing",
                   [sc_ok["img"], sc_ms["img"], sc_ms["img"] - sc_ok["img"]],
                   ["歯 24 枚", "1 枚欠け", "差"],
                   title="歯欠けの場面(偏心 0.050 mm)", ncols=3,
                   signed=[False, False, True])
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 節 6-7. 照明の傾斜 —— 偏心のふりをする / 基準も一緒に動く                     #
# --------------------------------------------------------------------------- #
def section_illumination() -> dict:
    print("\n" + "=" * 78)
    print("6-7) ★★照明の傾斜は偏心のふりをする(対照群つき)")
    print("=" * 78)
    print("   傾斜     規約        軸を実測    軸を真値に固定")

    gs, thr_meas, thr_true, grad_meas = [], [], [], []
    bore_dx, outer_dx = [], []
    cen = (N_PIX - 1) / 2.0
    for g in (0.0, 0.10, 0.20, 0.30):
        sc = make_scene(ecc_mm=0.0, illum=g)
        b = bore_centre(sc["img"])
        p_meas = radial_profile(sc["img"], (b["cy"], b["cx"]))
        p_true = radial_profile(sc["img"], (cen, cen))
        a_meas = harmonics(p_meas)[1]
        a_true = harmonics(p_true)[1]
        a_grad = harmonics(radial_profile(sc["img"], (b["cy"], b["cx"]),
                                          rule="gradient"))[1]
        # 符号つきで見る: 外形の中心はどちらへ、軸穴の中心はどちらへ動いたか
        th = np.arange(N_ANG) * (2.0 * np.pi / N_ANG)
        out_dx = 2.0 * float(np.mean(p_true * np.cos(th)))     # +列 = 明るい側
        gs.append(g)
        thr_meas.append(float(a_meas))
        thr_true.append(float(a_true))
        grad_meas.append(float(a_grad))
        bore_dx.append((b["cx"] - cen) * PX_MM)
        outer_dx.append(out_dx)
        print("   %.2f    固定しきい値  %.4f mm    %.4f mm    | 勾配最大 %.4f mm"
              % (g, a_meas, a_true, a_grad))

    print("\n  符号つきの内訳(+ = 明るい側 = +列 の向き):")
    for g, bx, ox in zip(gs, bore_dx, outer_dx):
        print("     傾斜 %.2f : 外形の中心 %+.4f mm / 軸穴の中心 %+.4f mm"
              % (g, ox, bx))
    print("\n  ★偏心は本当にゼロなのに、傾斜 %.0f %% で %.4f mm の「偏心」が出る。"
          % (100 * gs[-1], thr_meas[-1]))
    print("    対照群(傾斜ゼロ)は %.4f mm なので、これは照明が作った値。"
          % thr_meas[0])
    print("  ★予想が外れた: 「軸穴の中心も同じ向きへ流れて打ち消す」と踏んでいたが、")
    print("    軸を実測 %.4f mm > 軸を真値に固定 %.4f mm —— **打ち消すどころか "
          "%.2f 倍**。" % (thr_meas[-1], thr_true[-1], thr_meas[-1] / thr_true[-1]))
    print("    符号を見ると理由が分かる: 外形は %+.4f mm(明るい側へ)、"
          "軸穴は %+.4f mm(暗い側へ)—— **逆向き**。"
          % (outer_dx[-1], bore_dx[-1]))
    print("    どちらの縁も「明るい側では外へ、暗い側では内へ」動くが、"
          "穴は内外が裏返っているので中心のずれが反転する。")
    print("    基準がずれた分だけ差が広がるので、打ち消しではなく上乗せになる。")
    print("  ★勾配最大の縁に変えると %.4f mm まで下がる(それでもゼロではない)。"
          % grad_meas[-1])

    figs.save_plot("illumination",
                   [("固定しきい値(軸は実測)", np.asarray(gs) * 100, thr_meas),
                    ("固定しきい値(軸は真値)", np.asarray(gs) * 100, thr_true),
                    ("勾配最大(軸は実測)", np.asarray(gs) * 100, grad_meas)],
                   xlabel="照明の傾斜 [%]", ylabel="見かけの偏心 [mm]",
                   title="偏心は 0 —— 出ている値は全部が照明由来")
    return {"g": gs, "thr_meas": thr_meas, "thr_true": thr_true, "grad": grad_meas}


# --------------------------------------------------------------------------- #
# 節 8. 偏心は隣接ピッチ誤差を捏造する                                          #
# --------------------------------------------------------------------------- #
def section_pitch_error() -> dict:
    print("\n" + "=" * 78)
    print("8) ★偏心は隣接ピッチ誤差を捏造する(割り出しは完璧なのに)")
    print("=" * 78)
    print("   偏心 [mm]  与えた割出誤差 [mm]   誤差の最大 [mm]   1 次振幅 [mm]"
          "   理論 2e·sin(pi/z)")

    rows = []
    for ecc, off in ((0.000, 0.000), (0.050, 0.000), (0.100, 0.000),
                     (0.000, 0.050), (0.000, 0.100)):
        sc = make_scene(ecc_mm=ecc, pitch_off_mm=off)
        b = bore_centre(sc["img"])
        prof = radial_profile(sc["img"], (b["cy"], b["cx"]))
        tt = tooth_table(prof, R_PITCH)
        err = tt["pitch_mm"] - PITCH_MM
        # 誤差の列の 1 次成分(= 振れ由来の分)。歯の中心角を横軸に取る
        thk = tt["centre"]
        a = np.column_stack([np.ones_like(thk), np.cos(thk), np.sin(thk)])
        c, *_ = np.linalg.lstsq(a, err, rcond=None)
        amp1 = float(np.hypot(c[1], c[2]))
        theo = 2.0 * ecc * np.sin(np.pi / Z_TEETH)
        rows.append((ecc, off, float(np.abs(err).max()), amp1, theo))
        print("     %.3f        %.3f              %.4f            %.4f"
              "          %.4f" % (ecc, off, np.abs(err).max(), amp1, theo))

    print("\n  ★割り出しが完璧(与えた誤差 0)でも、偏心 %.3f mm で隣接ピッチ誤差の"
          "最大が %.4f mm 出る。" % (rows[2][0], rows[2][2]))
    print("    その 1 次振幅 %.4f mm は理論値 2e·sin(π/z) = %.4f mm と %.0f %% で"
          "一致 —— これは歯切り盤の割り出しではなく **振れ**。"
          % (rows[2][3], rows[2][4],
             100 * abs(rows[2][3] - rows[2][4]) / rows[2][4]))
    print("    (最大値のほうが理論より大きいのは、偏心ゼロでも %.4f mm の"
          "雑音床があるため。)" % rows[0][2])
    print("  ★与えた割出誤差 %.3f mm は最大 %.4f mm として検出され、しかも"
          "1 次振幅は %.4f mm しか無い(= 局所的で振れではない)。"
          % (rows[3][1], rows[3][2], rows[3][3]))

    figs.save_table("summary",
                    ["量", "真値", "推定", "誤差"],
                    [["ピッチ円直径 [mm]", "%.3f" % (2 * R_PITCH), "-", "節 2 参照"],
                     ["歯先円直径 [mm]", "%.3f" % (2 * R_TIP), "-", "節 2 参照"],
                     ["歯厚(ピッチ円)[mm]", "%.4f" % THICK_MM, "-", "節 2 参照"],
                     ["隣接ピッチ [mm]", "%.4f" % PITCH_MM, "-", "節 8 参照"],
                     ["偏心 0.100 -> 疑似ピッチ誤差", "0", "%.4f" % rows[2][2],
                      "%.4f (理論)" % (0.100 * PITCH_ANG)],
                     ["割出誤差 0.050 -> 検出", "0.0500", "%.4f" % rows[3][2], "本物"],
                     ["割出誤差 0.100 -> 検出", "0.1000", "%.4f" % rows[4][2], "本物"]],
                    title="歯車計測のまとめ(m=%.1f, z=%d, α=%.0f deg)"
                          % (MODULE_MM, Z_TEETH, ALPHA_DEG))
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 節 9. 道具の穴                                                                #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で fullseye を使ってみて)")
    print("=" * 78)

    # (a) 極座標変換 op は中心も半径も指定できない
    import ops
    reg = {o.name: o for o in ops.REGISTRY}
    assert "polar_trans_image" in reg, "op が消えた"
    assert not hasattr(fs, "polar_trans_image") and not hasattr(fs.ledger, "polar_trans_image")
    doc = reg["polar_trans_image"].doc or ""
    assert "中心と半径は画像サイズから自動的に決まり" in doc, doc[:120]
    print("  (a) polar_trans_image は **中心を渡せない**(画像中心・半径 min(H,W)/2"
          " 固定)。振れの測定は基準中心を選べないと成り立たないので、この PoC は"
          "line_profile で自前に展開している。")

    # (b) 円形統計(角度の平均・分散)が 3 層のどこにも無い
    for name in ("circular_mean", "circmean", "von_mises", "runout"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (b) 円形統計(角度の平均/分散、フォン・ミーゼス)が facade にも台帳にも"
          "無い。歯の中心角の平均を取るのに自前で書いた。")

    # (c) σ を直に渡す 2-D ガウスぼかしが公開経路に無い
    assert not hasattr(fs, "gauss_filter") and not hasattr(fs.ledger, "gauss_filter")
    assert "0.3+2.7*a" in (reg["gauss_filter"].doc or "")
    print("  (c) 2-D ガウスぼかしは進化 op しか無く、σ は a から "
          "σ=0.3+2.7a を逆算して渡すしかない(この PoC の PSF がそれ)。"
          "σ を引数に取る公開関数は 3-D の vol_gaussian_psf 側にしかない。")

    # (d) 1-D の周波数分解(調和成分)を出す口が無い
    assert not hasattr(fs, "harmonic_amplitudes") and not hasattr(fs, "fourier_series")
    assert hasattr(fs.ledger, "elliptic_fourier")     # 形状記述子はある(別物)
    print("  (d) 1-D の周期関数を次数ごとの振幅に分ける口が無い。"
          "elliptic_fourier は輪郭の形状記述子で、R(θ) の次数分解とは別物。"
          "真円度・円筒度(JIS B 0621 の調和分解)を扱うなら要る。")

    # (e) blob_boundaries は int32 のラベル画像しか受けない(bool を渡すと落ちる)
    m = np.zeros((20, 20), bool)
    m[5:15, 5:15] = True
    try:
        _LAB.blob_boundaries(m)
        raise AssertionError("bool を受けるようになった(この節を書き換えること)")
    except ValueError:
        pass
    print("  (e) blob_boundaries / blob_features は bool マスクを拒む(ラベル画像"
          "だけ)。1 個しか無いと分かっている領域でも blob_label を挟む必要がある。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("歯車の歯形を測る —— 偏心は 1 次、歯は z 次")
    print("m = %.1f mm / z = %d / α = %.0f deg -> ピッチ円 %.3f / 歯先円 %.3f / "
          "歯底円 %.3f mm" % (MODULE_MM, Z_TEETH, ALPHA_DEG, 2 * R_PITCH,
                              2 * R_TIP, 2 * R_ROOT))
    print("視野 %d px x %.2f mm/px = %.1f mm 角 / 軸穴の半径 %.1f mm"
          % (N_PIX, PX_MM, N_PIX * PX_MM, BORE_MM))
    print("=" * 78)

    section_zero_point()
    section_polar()
    section_eccentricity()
    section_missing_tooth()
    section_illumination()
    section_pitch_error()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 当てはめ円 1 個から出る「直径」はピッチ円でも歯先円でも歯底円でもない。"
          "偏心だけは当たる。")
    print("  * 偏心 = 1 次、歯 = z 次。ただし歯が 1 枚欠けると分離は成り立たない ——"
          " 歯ごとに 1 標本だけ読む。")
    print("  * 照明の傾斜は偏心のふりをする。しかも外形と軸穴の中心が **逆向き** に"
          "動くので、基準の側から上乗せされる。")
    print("  * 隣接ピッチ誤差を報告する前に振れ(1 次)を分離する。"
          "振れは 2e·sin(π/z) のピッチ誤差を捏造する。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
