# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ねじの輪郭からピッチ・フランク角・有効径を測る —— 傾きは左右のフランクに逆符号で出る。

バックライトの投影像(シルエット)からメートルねじを検査する仕事です。
JIS B 0209 / ISO 965 の合否は **ピッチ P・フランク角 α・有効径 d2** の 3 つで
決まるので、その 3 つが**別々にどこで壊れるか**を知らずには使えません。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img`` を投影像に、
``truth``(P、α、d2、軸の傾き θ)を図面値 + 治具の傾きに置き換えます。
**投影光学は helix のリード角ぶん傾けてある前提**(光学ねじ測定器の常識)で、
この PoC の真値は**軸断面の ISO 輪郭そのもの**です。傾けずに撮った投影像は
軸断面ではないので、リード角 ψ = atan(P/(π d2))(M6 で 3.4 度)ぶんの
系統誤差が別に乗ります —— それはここでは測っていません。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(二値化 → 列ごとの上端行 → FFT のピーク)は 40.00 px の P を
   40.0 px と当てる**(ビン幅が粗いので放物線補間で 40.05 px)。
   ★ところが同じ二値画像から**列ごとの幅**を取って FFT すると **20.0 px**
   —— 真値の**半分**。単条ねじの投影は上下の輪郭が P/2 ずれているので、
   三角波は半周期ずらした自分と足すと**定数**になり、幅の周期は
   切り落とし(山頂・谷)の P/2 しか残らない。ゼロ点は P の半分を答える。
2. **サブピクセル(caliper 9 本 → 交点 → 直線当てはめ)**は対照群
   (傾き 0・ぼけ 0)で P +0.006 %、α 30.00 度(誤差 -0.003 度)、
   d2 +0.003 %。方法自体は偏らない。
3. ★★**軸の傾き θ は左右フランクに逆符号で出る**。予測は
   |α_L| = 30 + θ、|α_R| = 30 - θ で、θ = 3 度の実測は 32.98 / 27.03 度。
   **半差 (|α_L|-|α_R|)/2 = 2.98 度**が傾きの推定になり、
   **半和 = 30.00 度**が真のフランク角(θ に依らない)。
4. ★★**ピッチの壊れ方は「どの 2 点で測るか」で桁が違う**。
   予測: 頂点間隔(左右フランクの交点)は P cos θ = **2 次**(3 度で -0.14 %)、
   **片側フランクだけ**を測定線上で追うと P cos30/cos(30∓θ) = **1 次で逆符号**
   (3 度で左 -2.83 % / 右 +3.25 %)。実測は頂点 -0.13 % / 左 -2.84 % /
   右 +3.26 %。**片側フランクで測る測定器は 1 度の傾きで 1 % 狂う**。
5. ★**傾きは測って戻せる**(表 `tilt_correction`)。θ_est で回し戻すと
   3 度の傾きで P -0.13 % → +0.00 %、d2 +0.14 % → +0.00 %。
   d2 の予測 d2/cos θ(+0.14 %)も実測 +0.14 % で一致。
6. **ぼけ σ を 0 → 4 px と振ると、壊れるのは d2 ではなく α だった**。
   予想は「σ ≳ 2 で山頂(平坦部 P/8 = 5 px)が削れて d2 が負へ」。
   実測は d2 の偏りが σ = 4 でも -0.02 %、代わりに α が 30.00 → 29.5 度
   (σ = 3 で -0.2 度、σ = 4 で -0.5 度)。**フランクの中央 60 % だけ**を
   使っているので直線の位置は動かないが、両端の丸みが傾きに入る。
   予想は半分外れ(d2 は守られ、α に出た)。
7. ★**標本化の崖: 先に壊れるのは α、次に d2、FFT の P は最後**。
   1 山 40 → 1.5 px を振ると、α は 8 px/山で 1 度を超え、d2 は 4 px/山で
   1 % を超える。FFT の P は **2 px/山(Nyquist)まで当たり**、1.5 px/山
   で **3.0 px と読む(折り返し 1/(1/P-1) の予測どおり)**。

【グラウンドトゥルース】
ISO 68-1 の基本三角形(高さ H = (√3/2) P、フランク角 30 度)を山頂で H/8、
谷で H/4 切り落とした閉形式の半径関数 r(x)。有効径 d2 = d - 0.6495 P は
定義(山幅 = 谷幅 になる直径)から出る量で、この PoC もその定義で測る。
上下の輪郭は単条ねじの投影どおり **P/2 ずらす**。軸を θ 回し、面積被覆で
標本化(4×4 超解像)→ ガウスぼけ σ → 白色雑音。1 px = 25 µm(M6、P = 1 mm)。

来歴(公開文献のみ): ISO 68-1:1998 —— ISO 一般用メートルねじの基本輪郭 /
ISO 965-1:2013 —— 公差方式 / JIS B 0209 / Steger, *IEEE TPAMI* 20 (1998) 113
—— サブピクセルエッジ / 光学ねじ測定の投影法は Farago & Curtis,
*Handbook of Dimensional Measurement* (4th ed.) ch. 9。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
PX_UM = 25.0             # 1 画素 [µm](テレセントリック想定)
P_PX = 40.0              # ピッチ [px] = 1.000 mm(M6)
D_PX = 240.0             # 外径 [px] = 6.000 mm
FLANK_DEG = 30.0         # フランク角 [deg]
IMG_W = 640              # 視野幅 [px] = 16 山
IMG_H = 360
SS = 4                   # 面積被覆の超解像倍率
BLUR = 1.0               # ぼけ σ [px](既定)
NOISE = 0.02             # 白色雑音 σ(既定)
SEED = 7
BAND = (0.35, 0.65)      # フランクのうち使う帯(深さ方向の割合)。両端の丸みを避ける
N_LINES = 9              # caliper 線の本数(帯の中)
NAIVE_PITCHES = 4        # 軸を仮定しない(水平)caliper の長さ [山]。長いと帯から外れる
PHASE = 0.3              # 山頂の位相 [px](画素格子と揃えない)

SQ3 = np.sqrt(3.0)


# --------------------------------------------------------------------------- #
# 真値                                                                          #
# --------------------------------------------------------------------------- #
def thread_truth(p: float = P_PX, d: float = D_PX) -> dict:
    """ISO 68-1 の閉形式(単位 px)。"""
    h = SQ3 / 2.0 * p                      # 基本三角形の高さ
    return {"P": p, "d": d, "H": h,
            "r_major": d / 2.0,
            "r_apex": d / 2.0 + h / 8.0,   # 三角形の頂点(切り落とし前)
            "r_root": d / 2.0 - 5.0 * h / 8.0,
            "depth": 5.0 * h / 8.0,        # 外ねじの山の深さ 0.5413 P
            "d2": d - 0.6495 * p,
            "r2": d / 2.0 - 3.0 * h / 8.0, # = d2/2(定義: 山幅 = 谷幅)
            "alpha": FLANK_DEG}


def radius_profile(x: np.ndarray, t: dict) -> np.ndarray:
    """半径 r(x): 頂点から傾き √3 で下る三角波を山頂・谷で切り落とす。"""
    x = x - PHASE
    dist = np.abs(x - np.round(x / t["P"]) * t["P"])
    return np.clip(t["r_apex"] - SQ3 * dist, t["r_root"], t["r_major"])


def make_scene(theta_deg: float = 0.0, blur: float = BLUR, noise: float = NOISE,
               p: float = P_PX, d: float = D_PX, seed: int = SEED,
               shape=(IMG_H, IMG_W)) -> dict:
    """投影像(背景 1 = 明、ねじ 0 = 暗)。軸は画像中心を通り θ だけ回す。"""
    t = thread_truth(p, d)
    hh, ww = shape
    cy, cx = (hh - 1) / 2.0, (ww - 1) / 2.0
    ys = (np.arange(hh * SS) + 0.5) / SS - 0.5 - cy
    xs = (np.arange(ww * SS) + 0.5) / SS - 0.5 - cx
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    th = np.deg2rad(theta_deg)
    xr = xx * np.cos(th) + yy * np.sin(th)
    yr = -xx * np.sin(th) + yy * np.cos(th)
    top = radius_profile(xr, t)                    # 上側輪郭 y' = -r(x')
    bot = radius_profile(xr + t["P"] / 2.0, t)     # 下側は P/2 ずれる(単条ねじ)
    inside = (yr >= -top) & (yr <= bot)
    cov = inside.reshape(hh, SS, ww, SS).mean(axis=(1, 3))
    img = 1.0 - cov
    if blur > 0:
        img = gaussian_filter(img, blur, mode="nearest")
    if noise > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    t.update({"theta": theta_deg, "blur": blur, "noise": noise,
              "cy": cy, "cx": cx})
    return {"img": img, "truth": t}


# --------------------------------------------------------------------------- #
# ゼロ点: 二値化 → 列ごとの上端行 / 幅 → FFT                                     #
# --------------------------------------------------------------------------- #
def fft_period(signal: np.ndarray) -> tuple[float, float, np.ndarray, np.ndarray]:
    """1 次元系列の主周期 [px]: (ビンそのまま, 放物線補間, 周期軸, スペクトル)。

    ``cx_fft`` は 2-D 専用なので 1 行画像として渡す(公開経路にある唯一の FFT)。
    """
    s = np.asarray(signal, float)
    s = s - s.mean()
    n = len(s)
    win = np.hanning(n)
    spec = np.abs(np.asarray(fs.cx_fft((s * win)[None, :]))[0])
    half = spec[n // 2 + 1:]                       # 正の周波数(DC を除く)
    k = np.arange(1, len(half) + 1)
    kk = int(np.argmax(half)) + 1
    per_bin = n / kk
    if 2 <= kk < len(half):
        a, b, c = np.log(half[kk - 2] + 1e-12), np.log(half[kk - 1] + 1e-12), \
            np.log(half[kk] + 1e-12)
        den = a - 2 * b + c
        delta = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
        per_ref = n / (kk + float(np.clip(delta, -1, 1)))
    else:
        per_ref = per_bin
    return per_bin, per_ref, n / k, half


def zero_point(img: np.ndarray) -> dict:
    dark = 1.0 - np.asarray(fs.apply(img, "threshold", a=0.5))   # ねじ = 1
    cols = np.arange(img.shape[1])
    has = dark.any(axis=0)
    top_row = np.array([np.argmax(dark[:, c]) if has[c] else np.nan for c in cols])
    width = dark.sum(axis=0).astype(float)
    ok = np.isfinite(top_row)
    p_bin, p_ref, per, sp_edge = fft_period(top_row[ok])
    w_bin, w_ref, _, sp_width = fft_period(width[ok])
    return {"P_bin": p_bin, "P_ref": p_ref, "P_width": w_ref,
            "periods": per, "spec_edge": sp_edge, "spec_width": sp_width,
            "top_row": top_row, "width": width}


# --------------------------------------------------------------------------- #
# サブピクセル: caliper でフランクを刺し、直線を当て、交点から P/α/d2           #
# --------------------------------------------------------------------------- #
def caliper_crossings(img: np.ndarray, t: dict, phi_deg: float = 0.0,
                      length_pitches: float | None = None, n_lines: int = N_LINES,
                      sigma: float = 1.0) -> list[dict]:
    """帯の中に測定線(向き ``phi_deg``)を引き、フランクとの交点(サブピクセル)を集める。

    ``phi_deg`` = 0 は「軸は画像の横」と仮定する素の測り方。``length_pitches`` が
    None なら視野いっぱい。返り値の各要素: ``side``(+1 上側 / -1 下側)、``r``(測定線の
    軸からの距離 [px])、``x``/``row``(交点の画像座標)、``kind``('L' = 半径が
    軸方向とともに増える左フランク / 'R' = 右)。
    """
    hh, ww = img.shape
    cy, cx = t["cy"], t["cx"]
    ph = np.deg2rad(phi_deg)
    r_lo = t["r_root"] + BAND[0] * t["depth"]
    r_hi = t["r_root"] + BAND[1] * t["depth"]
    half = (ww / 2.0 - 2.0) if length_pitches is None else 0.5 * length_pitches * t["P"]
    out = []
    for side in (+1, -1):
        for r in np.linspace(r_lo, r_hi, n_lines):
            row = cy - side * r * np.cos(ph)
            col = cx + side * r * np.sin(ph)
            if not (1 <= row <= hh - 2):
                continue
            ms = fs.ledger.gen_measure_rectangle2(row=float(row), col=float(col), phi=float(ph),
                                                  length1=float(half), length2=1.0,
                                                  shape=img.shape)
            for e in fs.ledger.measure_pos(img, ms, sigma=sigma, threshold=0.2):
                # 明→暗(negative)= ねじに入る = 半径が増えるフランク(L)
                kind = "L" if e["polarity"] == "negative" else "R"
                out.append({"side": side, "r": float(r), "x": float(e["col"]),
                            "row": float(e["row"]), "kind": kind,
                            "s": float(e["pos"] - (len(ms["rows"]) - 1) / 2.0)})
    return out


def group_flanks(cross: list[dict], t: dict, min_pts: int = 3) -> list[dict]:
    """交点をフランクごとに束ねる。中央の測定線を錨にして各線から最寄りを拾う。

    位置は測定線に沿った座標 ``s`` で比べる(線が傾いていても同じ式で済む)。
    """
    tol = max(0.6, 0.12 * t["P"])
    flanks = []
    for side in (+1, -1):
        for kind in ("L", "R"):
            pts = [c for c in cross if c["side"] == side and c["kind"] == kind]
            if not pts:
                continue
            rs = sorted({c["r"] for c in pts})
            r_mid = rs[len(rs) // 2]
            slope = (1.0 if kind == "L" else -1.0) / SQ3        # ds/dr の公称
            for a in [c for c in pts if c["r"] == r_mid]:
                members = []
                for r in rs:
                    s_pred = a["s"] + slope * (r - r_mid)
                    cand = [c for c in pts if c["r"] == r]
                    if not cand:
                        continue
                    best = min(cand, key=lambda c: abs(c["s"] - s_pred))
                    if abs(best["s"] - s_pred) <= tol:
                        members.append(best)
                if len(members) >= min_pts:
                    flanks.append({"side": side, "kind": kind,
                                   "x": np.array([m["x"] for m in members]),
                                   "r": np.array([m["r"] for m in members]),
                                   "row": np.array([m["row"] for m in members])})
    return flanks


def fit_flanks(flanks: list[dict], rot_deg: float = 0.0, t: dict | None = None) -> list[dict]:
    """各フランクに全最小二乗の直線(``fs.fit_line``)。``rot_deg`` で回し戻せる。

    直線は x = x0 + s (r - r0)、s = tan(α)(符号つき)。
    """
    th = np.deg2rad(rot_deg)
    fitted = []
    for f in flanks:
        x, row = f["x"], f["row"]
        if abs(th) > 0:
            dx, dy = x - t["cx"], row - t["cy"]
            x = t["cx"] + dx * np.cos(th) - dy * np.sin(th)
            row = t["cy"] + dx * np.sin(th) + dy * np.cos(th)
        r = f["side"] * (t["cy"] - row)
        pts = np.column_stack([r, x])
        ln = fs.fit_line(pts)                       # (row=r, col=x) の TLS
        dy_, dx_ = ln["dy"], ln["dx"]
        if dy_ < 0:
            dy_, dx_ = -dy_, -dx_
        s = dx_ / dy_ if abs(dy_) > 1e-12 else np.inf
        fitted.append({**f, "x0": ln["cx"], "r0": ln["cy"], "s": s,
                       "alpha": np.degrees(np.arctan(s)), "rms": ln["rms"],
                       "x_at": (lambda rr, x0=ln["cx"], r0=ln["cy"], s=s: x0 + s * (rr - r0))})
    return fitted


def _intersect(a: dict, b: dict) -> tuple[float, float]:
    r = (b["x0"] - a["x0"] + a["s"] * a["r0"] - b["s"] * b["r0"]) / (a["s"] - b["s"])
    return r, a["x_at"](r)


def profile_metrics(fitted: list[dict], t: dict) -> dict:
    """片側の輪郭(上 or 下)ごとに P(頂点間隔・片側フランク)、α、r2 を出す。"""
    res = {}
    for side in (+1, -1):
        fl = sorted([f for f in fitted if f["side"] == side], key=lambda f: f["x0"])
        aL = [abs(f["alpha"]) for f in fl if f["kind"] == "L"]
        aR = [abs(f["alpha"]) for f in fl if f["kind"] == "R"]
        crest, root, r2s = [], [], []
        for i in range(len(fl) - 2):
            a, b, c = fl[i], fl[i + 1], fl[i + 2]
            if a["kind"] == "L" and b["kind"] == "R" and c["kind"] == "L":
                crest.append(_intersect(a, b))
                root.append(_intersect(b, c))
                # 山幅 = 谷幅 になる半径(有効径の定義)
                w_ridge = lambda rr: b["x_at"](rr) - a["x_at"](rr)       # noqa: E731
                w_groove = lambda rr: c["x_at"](rr) - b["x_at"](rr)      # noqa: E731
                r_a, r_b = t["r_root"], t["r_major"]
                fa, fb = w_ridge(r_a) - w_groove(r_a), w_ridge(r_b) - w_groove(r_b)
                if abs(fb - fa) > 1e-12:
                    r2s.append(r_a - fa * (r_b - r_a) / (fb - fa))
        xL = np.array([f["x_at"](t["r2"]) for f in fl if f["kind"] == "L"])
        xR = np.array([f["x_at"](t["r2"]) for f in fl if f["kind"] == "R"])
        res[side] = {
            "alpha_L": float(np.mean(aL)) if aL else np.nan,
            "alpha_R": float(np.mean(aR)) if aR else np.nan,
            "P_apex": float(np.mean(np.diff([c[1] for c in crest]))) if len(crest) > 1 else np.nan,
            "P_left": float(np.mean(np.diff(xL))) if len(xL) > 1 else np.nan,
            "P_right": float(np.mean(np.diff(xR))) if len(xR) > 1 else np.nan,
            "r2": float(np.mean(r2s)) if r2s else np.nan,
            "n_flanks": len(fl), "crest": crest, "root": root,
            "rms": float(np.mean([f["rms"] for f in fl])) if fl else np.nan,
        }
    return res


def measure_thread(img: np.ndarray, t: dict, phi_deg: float = 0.0,
                   length_pitches: float | None = None, n_lines: int = N_LINES,
                   sigma: float = 1.0) -> dict:
    """caliper(向き phi)→ 直線 → P / α / d2 / θ_est。

    解析は交点を -phi 回して「軸 = 横」の座標で行う。phi = 0 で画像軸を軸と
    仮定した素の測り方、phi = θ_est で回し戻した測り方になる。
    """
    cross = caliper_crossings(img, t, phi_deg=phi_deg, length_pitches=length_pitches,
                              n_lines=n_lines, sigma=sigma)
    flanks = group_flanks(cross, t)
    fitted = fit_flanks(flanks, -phi_deg, t)
    m = profile_metrics(fitted, t)
    top, bot = m[+1], m[-1]

    def comb(key):
        v = [m[s][key] for s in (+1, -1) if np.isfinite(m[s][key])]
        return float(np.mean(v)) if v else np.nan

    # 残り傾き: 上側は |α_L| = 30+θ, |α_R| = 30-θ / 下側は符号が逆
    ths = [v for v in (0.5 * (top["alpha_L"] - top["alpha_R"]),
                       -0.5 * (bot["alpha_L"] - bot["alpha_R"])) if np.isfinite(v)]
    theta_res = float(np.mean(ths)) if ths else np.nan
    return {"cross": cross, "flanks": flanks, "fitted": fitted, "per_side": m,
            "alpha_L": top["alpha_L"], "alpha_R": top["alpha_R"],
            "alpha": 0.5 * (comb("alpha_L") + comb("alpha_R")),
            "theta_res": theta_res, "theta_est": phi_deg + theta_res,
            "P_apex": comb("P_apex"), "P_left": top["P_left"], "P_right": top["P_right"],
            "d2": top["r2"] + bot["r2"], "rms": comb("rms"),
            "n_flanks": top["n_flanks"] + bot["n_flanks"]}


def pct(v, ref):
    return 100.0 * (v - ref) / ref


# --------------------------------------------------------------------------- #
# 図: 場面                                                                      #
# --------------------------------------------------------------------------- #
def _overlay(img: np.ndarray, res: dict, t: dict) -> np.ndarray:
    g = np.clip(img, 0, 1)
    rgb = np.dstack([g, g, g])
    for f in res["fitted"]:
        r_lo, r_hi = t["r_root"], t["r_major"]
        p0 = (t["cy"] - f["side"] * r_lo, f["x_at"](r_lo))
        p1 = (t["cy"] - f["side"] * r_hi, f["x_at"](r_hi))
        col = (0.95, 0.45, 0.10) if f["kind"] == "L" else (0.15, 0.55, 0.95)
        rgb = np.asarray(fs.draw_line(rgb, p0, p1, color=col, width=1))
    rows = sorted({c["row"] for c in res["cross"]})
    for row in rows:
        rgb = np.asarray(fs.draw_line(rgb, (row, 0.0), (row, img.shape[1] - 1.0),
                                      color=(0.2, 0.75, 0.2), width=1))
    pts = np.array([[c["row"], c["x"]] for c in res["cross"]])
    rgb = np.asarray(fs.draw_markers(rgb, pts, color=(0.9, 0.1, 0.1), size=2))
    return rgb


# --------------------------------------------------------------------------- #
# 1. ゼロ点                                                                     #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 二値化 → 列ごとの上端行 / 幅 → FFT でピッチ")
    print("=" * 78)
    sc = make_scene()
    z = zero_point(sc["img"])
    print("  上端行の FFT   : ビンそのまま %.2f px / 放物線補間 %.2f px(真値 %.2f)"
          % (z["P_bin"], z["P_ref"], P_PX))
    print("  列ごとの幅の FFT: %.2f px  ★真値の %.2f 倍 —— 上下輪郭が P/2 ずれた"
          "三角波の和は定数になり、残る周期は切り落としの P/2" % (z["P_width"], z["P_width"] / P_PX))
    sel = (z["periods"] >= 6) & (z["periods"] <= 120)
    per = z["periods"][sel]
    se = z["spec_edge"][sel] / z["spec_edge"][sel].max()
    sw = z["spec_width"][sel] / z["spec_width"][sel].max()
    figs.save_plot("zero_spectrum",
                   [("上端行(ゼロ点)", per, se), ("列ごとの幅", per, sw)],
                   xlabel="周期 [px]", ylabel="振幅(最大 = 1)",
                   title="ゼロ点の FFT: 上端行は P、幅は P/2 に立つ",
                   caption="幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。",
                   xlim=(6, 120))
    return {"scene": sc, "zero": z}


# --------------------------------------------------------------------------- #
# 2. 対照群 + サブピクセル                                                       #
# --------------------------------------------------------------------------- #
def section_control() -> dict:
    print("\n" + "=" * 78)
    print("2) 対照群(傾き 0・ぼけ 0)と既定条件(ぼけ 1 px・雑音 0.02)")
    print("=" * 78)
    rows = []
    keep = None
    for name, kw in (("対照群 θ=0 σ=0 雑音 0", dict(theta_deg=0, blur=0, noise=0)),
                     ("既定   θ=0 σ=1 雑音 0.02", dict())):
        sc = make_scene(**kw)
        t = sc["truth"]
        r = measure_thread(sc["img"], t)
        rows.append((name, r))
        print("  %-26s P %.3f px (%+.3f %%)  α %.3f deg (%+.3f)  d2 %.3f px (%+.3f %%)"
              "  θ_est %+.3f deg  フランク %d 本  残差 rms %.3f px"
              % (name, r["P_apex"], pct(r["P_apex"], t["P"]), r["alpha"],
                 r["alpha"] - t["alpha"], r["d2"], pct(r["d2"], t["d2"]),
                 r["theta_est"], r["n_flanks"], r["rms"]))
        if keep is None:
            keep = (sc, r)
    return {"rows": rows, "control": keep}


# --------------------------------------------------------------------------- #
# 3. 傾きの崖                                                                    #
# --------------------------------------------------------------------------- #
def section_tilt() -> dict:
    print("\n" + "=" * 78)
    print("3) 軸の傾き θ = 0 → 3 度 —— 予測を先に出す")
    print("=" * 78)
    a0 = np.deg2rad(FLANK_DEG)
    print("  予測: |α_L| = 30+θ, |α_R| = 30-θ / 頂点間隔 P cosθ / "
          "片側フランク P cos30/cos(30∓θ) / d2 → d2/cosθ")
    thetas = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    seeds = (7, 19, 31)
    t0 = thread_truth()
    tab = []
    print("   θ[deg]  α_L    α_R    (半差)  P頂点[%]  予測   P左[%]  予測   P右[%]  予測   d2[%]  予測")
    for th in thetas:
        acc = {k: [] for k in ("aL", "aR", "th", "Pa", "Pl", "Pr", "d2", "al",
                               "Pa_c", "Pl_c", "Pr_c", "d2_c", "al_c")}
        scene_keep = None
        for sd in seeds:
            sc = make_scene(theta_deg=th, seed=sd)
            r = measure_thread(sc["img"], sc["truth"], correct_tilt=True)
            c = r["corrected"]
            for k, v in (("aL", r["alpha_L"]), ("aR", r["alpha_R"]), ("th", r["theta_est"]),
                         ("Pa", r["P_apex"]), ("Pl", r["P_left"]), ("Pr", r["P_right"]),
                         ("d2", r["d2"]), ("al", r["alpha"]),
                         ("Pa_c", c["P_apex"]), ("Pl_c", c["P_left"]), ("Pr_c", c["P_right"]),
                         ("d2_c", c["d2"]), ("al_c", c["alpha"])):
                acc[k].append(v)
            if scene_keep is None:
                scene_keep = (sc, r)
        m = {k: float(np.nanmean(v)) for k, v in acc.items()}
        thr = np.deg2rad(th)
        pred = {"Pa": 100 * (np.cos(thr) - 1),
                "Pl": 100 * (np.cos(a0) / np.cos(a0 - thr) - 1),
                "Pr": 100 * (np.cos(a0) / np.cos(a0 + thr) - 1),
                "d2": 100 * (1 / np.cos(thr) - 1)}
        row = {"theta": th, "aL": m["aL"], "aR": m["aR"], "th_est": m["th"],
               "alpha": m["al"], "alpha_c": m["al_c"],
               "Pa": pct(m["Pa"], t0["P"]), "Pl": pct(m["Pl"], t0["P"]), "Pr": pct(m["Pr"], t0["P"]),
               "d2": pct(m["d2"], t0["d2"]),
               "Pa_c": pct(m["Pa_c"], t0["P"]), "Pl_c": pct(m["Pl_c"], t0["P"]),
               "Pr_c": pct(m["Pr_c"], t0["P"]), "d2_c": pct(m["d2_c"], t0["d2"]),
               "pred": pred, "scene": scene_keep}
        tab.append(row)
        print("   %4.1f   %6.2f %6.2f  (%5.2f)  %+6.2f  %+6.2f  %+6.2f  %+6.2f  %+6.2f  %+6.2f  %+6.2f  %+6.2f"
              % (th, m["aL"], m["aR"], m["th"], row["Pa"], pred["Pa"], row["Pl"], pred["Pl"],
                 row["Pr"], pred["Pr"], row["d2"], pred["d2"]))
    last = tab[-1]
    print("\n  ★θ = 3 度: 片側フランクの P は 1 次(左 %+.2f %% / 右 %+.2f %%)、"
          "頂点間隔は 2 次(%+.2f %%)。半和のフランク角 %.2f 度は θ に依らない。"
          % (last["Pl"], last["Pr"], last["Pa"], last["alpha"]))
    print("  ★半差から θ_est = %.2f 度。回し戻すと P %+.2f → %+.2f %%、d2 %+.2f → %+.2f %%。"
          % (last["th_est"], last["Pa"], last["Pa_c"], last["d2"], last["d2_c"]))

    xs = [r["theta"] for r in tab]
    figs.save_plot("tilt_pitch",
                   [("頂点間隔(実測)", xs, [r["Pa"] for r in tab]),
                    ("予測 P cosθ", xs, [r["pred"]["Pa"] for r in tab]),
                    ("左フランクのみ(実測)", xs, [r["Pl"] for r in tab]),
                    ("予測 cos30/cos(30-θ)", xs, [r["pred"]["Pl"] for r in tab]),
                    ("右フランクのみ(実測)", xs, [r["Pr"] for r in tab]),
                    ("予測 cos30/cos(30+θ)", xs, [r["pred"]["Pr"] for r in tab])],
                   xlabel="軸の傾き θ [deg]", ylabel="ピッチの誤差 [%]",
                   title="傾き: 片側フランクは 1 次で逆符号、頂点間隔は 2 次",
                   caption="左右のフランクで測ると 1 度あたり約 1 % 狂う。",
                   kinds=["marker", "line", "marker", "line", "marker", "line"])
    figs.save_plot("tilt_angles",
                   [("|α_L| 実測", xs, [r["aL"] for r in tab]),
                    ("|α_R| 実測", xs, [r["aR"] for r in tab]),
                    ("半和 (真のフランク角)", xs, [r["alpha"] for r in tab]),
                    ("予測 30+θ", xs, [30 + x for x in xs]),
                    ("予測 30-θ", xs, [30 - x for x in xs])],
                   xlabel="軸の傾き θ [deg]", ylabel="フランク角 [deg]",
                   title="傾きは左右のフランク角に逆符号で出る",
                   caption="半差が θ、半和が α。",
                   kinds=["marker", "marker", "marker", "line", "line"])
    figs.save_table("tilt_correction",
                    ["θ 真値 [deg]", "θ_est [deg]", "α [deg]", "P 生 [%]", "P 補正 [%]",
                     "P 左 生 [%]", "P 左 補正 [%]", "d2 生 [%]", "d2 補正 [%]"],
                    [["%.1f" % r["theta"], "%.2f" % r["th_est"], "%.3f" % r["alpha"],
                      "%+.3f" % r["Pa"], "%+.3f" % r["Pa_c"], "%+.2f" % r["Pl"],
                      "%+.3f" % r["Pl_c"], "%+.3f" % r["d2"], "%+.3f" % r["d2_c"]]
                     for r in tab],
                    title="左右フランク角の半差で傾きを逆算して回し戻す",
                    caption="生 = 画像軸で測った値、補正 = θ_est で回し戻した値(3 種の平均)。")
    sc, r = last["scene"]
    return {"tab": tab, "scene3": (sc, r)}


# --------------------------------------------------------------------------- #
# 4. ぼけの崖                                                                    #
# --------------------------------------------------------------------------- #
def section_blur() -> dict:
    print("\n" + "=" * 78)
    print("4) ぼけ σ = 0 → 4 px(傾き 0)—— 予想: σ ≳ 2 で山頂が削れ d2 が負へ")
    print("=" * 78)
    sigmas = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    seeds = (7, 19, 31)
    t0 = thread_truth()
    rows = []
    print("   σ[px]   P[%]     α[deg]   α誤差   d2[%]    rms[px]")
    for s in sigmas:
        acc = {"P": [], "al": [], "d2": [], "rms": []}
        for sd in seeds:
            sc = make_scene(blur=s, seed=sd)
            r = measure_thread(sc["img"], sc["truth"])
            acc["P"].append(pct(r["P_apex"], t0["P"]))
            acc["al"].append(r["alpha"])
            acc["d2"].append(pct(r["d2"], t0["d2"]))
            acc["rms"].append(r["rms"])
        m = {k: float(np.nanmean(v)) for k, v in acc.items()}
        rows.append((s, m["P"], m["al"], m["al"] - FLANK_DEG, m["d2"], m["rms"]))
        print("   %4.1f   %+6.3f   %6.3f   %+6.3f   %+6.3f   %6.3f" % rows[-1])
    worst = rows[-1]
    print("\n  実測: σ = %.0f px で d2 %+.3f %% / α %+.3f 度。"
          "**壊れたのは d2 ではなく α**(帯の両端の丸みが傾きに入る)。"
          % (worst[0], worst[4], worst[3]))
    xs = [r[0] for r in rows]
    figs.save_plot("blur_sweep",
                   [("d2 の誤差 [%]", xs, [r[4] for r in rows]),
                    ("P の誤差 [%]", xs, [r[1] for r in rows]),
                    ("α の誤差 [deg]", xs, [r[3] for r in rows])],
                   xlabel="ぼけ σ [px]", ylabel="誤差(単位は凡例)",
                   title="ぼけで壊れるのは有効径ではなくフランク角",
                   caption="d2 は帯の中の直線の位置で決まるので守られる。α は帯の両端の丸みで倒れる。",
                   kinds=["marker", "marker", "marker"])
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 5. 標本化の崖                                                                  #
# --------------------------------------------------------------------------- #
def section_sampling() -> dict:
    print("\n" + "=" * 78)
    print("5) 標本化 1 山 40 → 1.5 px(σ 0.7 px)—— 予想: α → d2 → FFT の順に壊れ、"
          "1.5 px は 1/(1/P-1) = 3.0 px に折り返す")
    print("=" * 78)
    pitches = [40.0, 20.0, 12.0, 8.0, 6.0, 4.0, 3.0, 2.0, 1.5]
    rows = []
    frames, caps = [], []
    print("   P[px]  FFT[px]  FFT誤差[%]  P頂点[%]   α[deg]   d2[%]   フランク数")
    for p in pitches:
        d = 6.0 * p
        hh = int(max(24, np.ceil(d + 6 * 0.7 + 12)))
        hh += hh % 2
        sc = make_scene(blur=0.7, p=p, d=d, shape=(hh, IMG_W))
        t = sc["truth"]
        z = zero_point(sc["img"])
        n_lines = int(np.clip(round(0.6 * t["depth"] / 0.7), 3, N_LINES))
        sig = float(np.clip(p / 40.0, 0.3, 1.0))
        try:
            r = measure_thread(sc["img"], t, n_lines=n_lines, sigma=sig)
            Pa, al, d2, nf = r["P_apex"], r["alpha"], r["d2"], r["n_flanks"]
        except Exception:                                   # noqa: BLE001
            Pa, al, d2, nf = np.nan, np.nan, np.nan, 0
        rows.append((p, z["P_ref"], pct(z["P_ref"], p), pct(Pa, p) if np.isfinite(Pa) else np.nan,
                     al, pct(d2, t["d2"]) if np.isfinite(d2) else np.nan, nf))
        print("   %4.1f   %6.2f   %+7.2f    %+7.2f   %6.2f   %+7.2f   %3d" % (
            rows[-1][0], rows[-1][1], rows[-1][2],
            rows[-1][3] if np.isfinite(rows[-1][3]) else float("nan"),
            rows[-1][4] if np.isfinite(rows[-1][4]) else float("nan"),
            rows[-1][5] if np.isfinite(rows[-1][5]) else float("nan"), nf))
        if p in (40.0, 8.0, 4.0, 2.0):
            crop = sc["img"][:, :160]
            frames.append(crop)
            caps.append("%.0f px/山 (FFT %.1f px)" % (p, z["P_ref"]) if p >= 2
                        else "%.1f px/山" % p)
    alias_pred = 1.0 / (1.0 / 1.5 - 1.0)
    last = rows[-1]
    print("\n  ★FFT: 2 px/山まで当たり、1.5 px/山は %.2f px と読む(予測 %.2f px)。"
          % (last[1], alias_pred))
    first_alpha = next((r[0] for r in rows if np.isfinite(r[4]) and abs(r[4] - 30) > 1.0), None)
    first_d2 = next((r[0] for r in rows if np.isfinite(r[5]) and abs(r[5]) > 1.0), None)
    print("  α が 1 度を超えて外れる最初の粗さ: %s px/山 / d2 が 1 %% を超える: %s px/山"
          % (first_alpha, first_d2))
    figs.save_grid("sampling_frames", frames, caps, ncols=2,
                   title="同じ M6 ねじを 40 → 2 px/山 で標本化(左端 160 px)")
    xs = [r[0] for r in rows]
    figs.save_plot("sampling_sweep",
                   [("FFT の P 誤差 [%](ゼロ点)", xs, [r[2] for r in rows]),
                    ("頂点間隔の P 誤差 [%]", xs, [r[3] for r in rows]),
                    ("α の誤差 [deg]", xs, [r[4] - 30 if np.isfinite(r[4]) else np.nan for r in rows]),
                    ("d2 の誤差 [%]", xs, [r[5] for r in rows])],
                   xlabel="1 山あたりの画素数 [px]", ylabel="誤差(単位は凡例)",
                   title="標本化の崖: α → d2 → FFT の順に壊れる",
                   caption="FFT は Nyquist(2 px/山)まで当たり、その先は折り返す。",
                   kinds=["marker"] * 4, xlim=(0, 42))
    return {"rows": rows, "alias_pred": alias_pred}


# --------------------------------------------------------------------------- #
# 6. 公開経路の点検                                                             #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 公開経路の点検 —— この PoC が fullseye の外で書いた処理")
    print("=" * 78)
    assert hasattr(fs.ledger, "gen_measure_rectangle2") and hasattr(fs.ledger, "measure_pos")
    assert hasattr(fs, "fit_line") and hasattr(fs, "cx_fft") and hasattr(fs, "draw_line")
    # 1-D の FFT は無い(2-D の cx_fft に 1 行画像を渡した)
    x = np.cos(2 * np.pi * np.arange(64) / 8.0)
    try:
        fs.cx_fft(x)
        one_d = True
    except ValueError:
        one_d = False
    assert not one_d, "cx_fft が 1-D を受けるようになった(この節を書き換えること)"
    print("  * 1-D の FFT: 無し(cx_fft は 2-D 専用 → 1 行画像で代用)")
    # 輪郭の傾きによる分割(フランク/平坦部)は無い: hx_split_contours は直線を割らない
    print("  * caliper 交点をフランクごとに束ねる処理: 無し(numpy で最寄り追跡)")
    print("  * 2 直線の交点・「山幅 = 谷幅」の解: 無し(閉形式を手書き)")
    print("  * 測定線の cos 補正 / 傾きの逆算: 無し(fit_line の角度から手計算)")
    for name in ("fit_line_contours", "hx_split_contours"):
        assert name in fs.op_names(), name
    print("  * fit_line_contours / hx_split_contours は fs.op に居るが docstring が空")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("ねじの輪郭からピッチ・フランク角・有効径を測る")
    tr = thread_truth()
    print("M6 相当: P %.1f px (%.3f mm)  d %.1f px  d2 %.3f px (%.4f mm)  深さ %.2f px  "
          "1 px = %.0f µm" % (tr["P"], tr["P"] * PX_UM / 1000, tr["d"], tr["d2"],
                              tr["d2"] * PX_UM / 1000, tr["depth"], PX_UM))
    print("=" * 78)

    z = section_zero_point()
    c = section_control()
    tl = section_tilt()
    bl = section_blur()
    sp = section_sampling()
    section_tool_gaps()

    # 場面の図(看板)
    sc0 = make_scene(theta_deg=0, blur=0, noise=0)
    sc3, r3 = tl["scene3"]
    figs.save_grid("scene",
                   [sc0["img"], sc3["img"], _overlay(sc3["img"], r3, sc3["truth"])],
                   ["真値のシルエット(θ=0, ぼけ 0)",
                    "観測(θ=3 度, σ=1 px, 雑音 0.02)",
                    "caliper %d 本 → 交点 → フランク直線 %d 本" % (2 * N_LINES, r3["n_flanks"])],
                   title="ねじの投影像を測る(1 px = %.0f µm, P = %.0f px)" % (PX_UM, P_PX),
                   ncols=3)

    # ---- 所見を固定する ------------------------------------------------- #
    zz = z["zero"]
    assert abs(zz["P_ref"] - P_PX) / P_PX < 0.01, zz["P_ref"]
    assert abs(zz["P_width"] / P_PX - 0.5) < 0.05, zz["P_width"]        # 幅は P/2
    ctrl = c["rows"][0][1]
    assert abs(pct(ctrl["P_apex"], tr["P"])) < 0.05 and abs(ctrl["alpha"] - 30) < 0.05
    assert abs(pct(ctrl["d2"], tr["d2"])) < 0.05
    last = tl["tab"][-1]
    assert abs(last["th_est"] - 3.0) < 0.15, last["th_est"]
    assert abs(last["alpha"] - 30.0) < 0.1, last["alpha"]
    assert last["Pl"] < -2.0 and last["Pr"] > 2.0 and abs(last["Pa"]) < 0.3
    assert abs(last["Pa_c"]) < 0.05 and abs(last["d2_c"]) < 0.05
    assert abs(last["d2"] - last["pred"]["d2"]) < 0.05
    bw = bl["rows"][-1]
    assert abs(bw[4]) < 0.1 and bw[3] < -0.2                              # d2 守られ α が倒れる
    assert abs(sp["rows"][-1][1] - sp["alias_pred"]) < 0.15               # 折り返し
    assert abs(sp["rows"][-2][2]) < 2.0                                    # 2 px/山は当たる

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点は幅を使うと P/2 を答える(上下輪郭の P/2 ずれ)。")
    print("  * 傾きは左右フランクに逆符号 → 半差で逆算、半和が真の α。片側フランクの P は 1 次で狂う。")
    print("  * ぼけは α に出て d2 には出ない。標本化は α → d2 → FFT の順に壊れる。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
