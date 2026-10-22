# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 「解像度の式」は見つかる大きさを教えない —— 照明ごとの検出確率(MIL-HDBK-1823A)

ヘアライン仕上げの金属に、幅 ``a`` の V 字の傷(斜面およそ 10°)を入れ、
**同じカメラ・同じレンズ・同じ処理**で照明だけを 3 通りに変えて写す:

  * リング照明 仰角 70°(天頂から 20° = 斜面の 2 倍。斜面が光をカメラへ鏡面反射する角度)
  * リング照明 仰角 30°(暗視野寄り。斜面 10° では鏡面がカメラに届かない)
  * ドーム照明(全方向から拡散ぎみに当てる)

傷の応答 ``â`` を固定の古典処理(列方向の積分 = 縦線に合わせた整合フィルタ、
既知の位置の ±1 画素)で測り、MIL-HDBK-1823A の手順で POD(a) 曲線・a90・
**a90/95** と誤検出確率を出す。真値は**自分で入れた傷の幅**。

★★見せたいこと: 設計の式(``visiondesign.detectability_limit``)は「この光学系で
分解できる最小の大きさ」を **約 200 µm**(2 画素)と言う。だが検出の確率は
**照明で桁が変わる** —— 鏡面反射を拾う照明では画素より 1 桁小さい傷が 90 % 見つかり、
暗視野寄りの照明では試した範囲(〜300 µm)の傷がほとんど記録にすら残らない。その
回帰から出る a90/95 は試した最大の傷の 20 倍先の**外挿**で、op はその数に旗を付けて返す。
解像度は「形が分かるか」、POD は「在ることに気づくか」で、別の問いである。

真値と門(使った式で答え合わせをしない):

1. **描画は台帳の物理モデルそのもの**: ベクトル化した放射輝度を、照明ごとに
   ``illumdesign._radiance``(1 点ずつの正本)と突き合わせる(相対差 1e-12 以内)。
2. **面積の保存**: 傷の斜面が画素に占める割合の総和は ``幅 / 画素`` に厳密に一致。
3. **POD の主張を物理で確かめる**: 当てた a90 の大きさの傷を**新たに 200 本描き直し**、
   ``â > âdec`` となる割合が 0.9 の二項誤差の帯(±3σ)に入ること。モデル(対数の
   直線 + 正規の散らばり + 打ち切り)が物理に合っていなければここで落ちる。
4. **2 つの解析が同じ答え**: 同じ測定を「見つけた/見落とした」に落として 2 値の
   GLM で当てた a90 が、â vs a の a90 と標準誤差の 3 倍以内で一致。
5. **打ち切りが要る理由**: 記録閾値より下と飽和を無視した素朴な最小二乗は
   傾きを寝かせる(打ち切りつき最尤との差を標準誤差で数える)。
6. **ゼロ点**: 無欠陥の部位に**でたらめな大きさ**を割り振って同じ解析に通すと、
   応答は大きさと無関係なので op は ``ValueError`` で曲線を拒む(偽の曲線を描かない)。
   暗視野寄りの照明の a90/95 には「試した範囲の外」の旗が立つ。
7. 取引表: ``âdec`` を上げると誤検出は減り a90 は厳密に増える。

★正直に書いておくこと(合成であること):

  * 面は**合成**(ヘアラインは正弦波の和、傾き RMS 約 2°)、傷は理想的な V 字で
    斜面に 1.5° の個体差を入れた。実物の傷の断面・バリ・汚れは入っていない。
  * 光学は**幾何光学**(ベクトル化した GGX の鏡面 + ランバート)。幅が波長に近い
    傷(数 µm)では回折が効くはずだが入っていない。レンズのぼけは回折の
    ガウス近似(σ = 0.42 λN/m)だけ。
  * センサは 8 bit、背景を 40 DN に合わせた露出、ショット雑音 + 読み出し雑音 1.5 DN。
  * 1823A の手順(打ち切り回帰 → デルタ法)そのものは規格どおり。規格の
    例題データは PDF に載っていないので、**規格の数値とは突き合わせていない**
    (誤検出の表 G-I との一致は ``tests/test_pod.py`` が見る)。

走らせ方: ``py -3.11 examples/poc_pod_lighting.py``
(図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402,F401  (台帳の公開経路 fs.ledger を使う)
import illumdesign as ID  # noqa: E402
import visiondesign as VD  # noqa: E402

CHECKS = []

# ---- 光学系(設計の式と同じ数字で描く) ----------------------------------- #
FOCAL_MM, WD_MM, PITCH_UM, F_NUMBER, WAVE_UM = 25.0, 750.0, 3.45, 4.0, 0.55
GEO = VD.system_geometry(FOCAL_MM, WD_MM, PITCH_UM, 2448, 2048)
PX = GEO["um_per_pixel"] / 1000.0                    # 物体側の画素 [mm](約 0.1)
PSF_PX = 0.42 * WAVE_UM * F_NUMBER / GEO["magnification"] / GEO["um_per_pixel"]
NX, NY, SS = 16, 10, 2                                 # 1 部位の画素数と面内の副標本
SLOPE_DEG, SLOPE_SD = 10.0, 1.5
SURF = {"albedo": 0.1, "roughness": 0.25, "f0": 0.7}   # ヘアラインの金属(GGX)
SP = ID._surface_params(SURF)
CAM = np.array([0.0, 0.0, 300.0])
BG_DN, FULL, READ_DN, GAIN = 40.0, 255.0, 1.5, 4.0
REC_DN = 4.0                                           # 記録閾値(これ以下は左打ち切り)
CEIL_FRAC = 0.8                                        # 天井の 8 割より上は右打ち切り
A_DEC = 6.0                                            # 判定閾値 [DN]
N_FLAW, N_CLEAN = 120, 360                             # 無欠陥は欠陥の 3 倍
SIZE_UM = (2.0, 300.0)

LIGHTS = {
    "ring70": ("リング 仰角70°", ID.light_source("ring", radius_mm=60.0,
                                                 height_mm=60.0 * math.tan(math.radians(70)), n=24)),
    "ring30": ("リング 仰角30°", ID.light_source("ring", radius_mm=60.0,
                                                 height_mm=60.0 * math.tan(math.radians(30)), n=24)),
    "dome": ("ドーム", ID.light_source("dome", radius_mm=80.0, n=32)),
}


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


# --------------------------------------------------------------------------- #
# 描画: 台帳の放射輝度モデル(illumdesign._radiance)を多点で一度に
# --------------------------------------------------------------------------- #
def radiance_many(P, N, light):
    """``illumdesign._radiance``(点光源の和、面光源なし)をベクトル化したもの。"""
    E, D, I0, m = ID._check_light(light)
    out = np.empty(len(P))
    for s in range(0, len(P), 16384):
        p, n = P[s:s + 16384], N[s:s + 16384]
        V = E[None, :, :] - p[:, None, :]
        d2 = np.sum(V * V, axis=2)
        L = V / np.sqrt(d2)[:, :, None]
        cos_e = np.clip(np.sum(-L * D[None], axis=2), 0.0, None)
        ndl = np.sum(L * n[:, None, :], axis=2)
        vd = CAM[None, :] - p
        vd = vd / np.linalg.norm(vd, axis=1, keepdims=True)
        ndv = np.sum(n * vd, axis=1)
        H = L + vd[:, None, :]
        H = H / np.maximum(np.linalg.norm(H, axis=2, keepdims=True), 1e-300)
        ndh = np.sum(H * n[:, None, :], axis=2)
        vdh = np.sum(H * vd[:, None, :], axis=2)
        irr = I0 * cos_e ** m / d2
        fsp = ID._ggx(ndl, np.broadcast_to(ndv[:, None], ndl.shape), ndh, vdh,
                      SP["roughness"], SP["f0"])
        out[s:s + 16384] = np.sum((SP["albedo"] / np.pi + fsp) * irr * np.clip(ndl, 0.0, None),
                                  axis=1)
    return out


def _texture_grad(rng, x, y, k=10):
    """ヘアライン(y 方向に細かい溝が並ぶ)の高さの勾配。傾きの RMS は約 2°。"""
    gx = np.zeros_like(x)
    gy = np.zeros_like(x)
    pars = [(rng.uniform(0.08, 0.4), rng.uniform(0, 2 * np.pi), rng.uniform(0.5, 2.0),
             rng.uniform(0, 2 * np.pi)) for _ in range(k)]
    amp = math.tan(math.radians(2.0)) / math.sqrt(k / 2) / (2 * np.pi)
    for lam, ph, wl, wph in pars:
        w_ = 0.1 * np.sin(2 * np.pi * x / wl + wph)
        dw = 0.1 * np.cos(2 * np.pi * x / wl + wph) * 2 * np.pi / wl
        c = amp * lam * np.cos(2 * np.pi * y / lam + ph + w_)
        gy += c * 2 * np.pi / lam
        gx += c * dw
    return gx, gy


def _normals(gx, gy):
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def flank_fractions(width_mm, x0_mm):
    """各画素列に傷の左右の斜面が占める割合(面積を厳密に配る)。"""
    xl = (np.arange(NX) * PX - NX * PX / 2)
    xr = xl + PX
    half = width_mm / 2
    left = np.clip(np.minimum(xr, x0_mm) - np.maximum(xl, x0_mm - half), 0, None) / PX
    right = np.clip(np.minimum(xr, x0_mm + half) - np.maximum(xl, x0_mm), 0, None) / PX
    return left, right


def build_sites(widths_mm, seed):
    """部位ごとの面(副標本の点と法線)と、斜面の割合・法線。"""
    rng = np.random.default_rng(seed)
    n = widths_mm.size
    slopes = rng.normal(SLOPE_DEG, SLOPE_SD, n)
    x0s = rng.uniform(-PX / 2, PX / 2, n)
    cx = (np.arange(NX * SS) + 0.5) / SS * PX - NX * PX / 2
    cy = (np.arange(NY * SS) + 0.5) / SS * PX - NY * PX / 2
    yy, xx = np.meshgrid(cy, cx, indexing="ij")
    pxc = (np.arange(NX) + 0.5) * PX - NX * PX / 2
    pyc = (np.arange(NY) + 0.5) * PX - NY * PX / 2
    YY, XX = np.meshgrid(pyc, pxc, indexing="ij")
    Pf, Nf, Pc, NL, NR, fl, fr, flawed = [], [], [], [], [], [], [], []
    for i in range(n):
        r = np.random.default_rng(rng.integers(1 << 62))
        gx, gy = _texture_grad(r, xx, yy)
        Pf.append(np.stack([xx, yy, np.zeros_like(xx)], -1).reshape(-1, 3))
        Nf.append(_normals(gx, gy).reshape(-1, 3))
        l_, r_ = flank_fractions(widths_mm[i], x0s[i])
        fl.append(np.broadcast_to(l_, (NY, NX)))
        fr.append(np.broadcast_to(r_, (NY, NX)))
        if widths_mm[i] > 0:
            r2 = np.random.default_rng(rng.integers(1 << 62))
            gx2, gy2 = _texture_grad(r2, XX, YY)
            t = math.tan(math.radians(slopes[i]))
            Pc.append(np.stack([XX, YY, np.zeros_like(XX)], -1).reshape(-1, 3))
            NL.append(_normals(gx2 - t, gy2).reshape(-1, 3))     # 左の斜面は +x を向く
            NR.append(_normals(gx2 + t, gy2).reshape(-1, 3))
            flawed.append(i)
    return {"Pf": np.concatenate(Pf), "Nf": np.concatenate(Nf),
            "Pc": np.concatenate(Pc) if Pc else np.zeros((0, 3)),
            "NL": np.concatenate(NL) if NL else np.zeros((0, 3)),
            "NR": np.concatenate(NR) if NR else np.zeros((0, 3)),
            "fl": np.stack(fl), "fr": np.stack(fr), "flawed": np.array(flawed, dtype=int), "n": n}


def render(sites, light, gain=None, seed=0):
    """部位ごとの 8 bit 画像(背景 40 DN の露出、ぼけ、ショット + 読み出し雑音、飽和)。"""
    from scipy.ndimage import gaussian_filter1d
    n = sites["n"]
    flat = radiance_many(sites["Pf"], sites["Nf"], light).reshape(n, NY, SS, NX, SS).mean(axis=(2, 4))
    L = flat.copy()
    if sites["flawed"].size:
        k = sites["flawed"]
        Ll = radiance_many(sites["Pc"], sites["NL"], light).reshape(k.size, NY, NX)
        Lr = radiance_many(sites["Pc"], sites["NR"], light).reshape(k.size, NY, NX)
        fl, fr = sites["fl"][k], sites["fr"][k]
        L[k] = (1 - fl - fr) * flat[k] + fl * Ll + fr * Lr
    if gain is None:
        gain = BG_DN / float(np.median(flat))
    S = gaussian_filter1d(gain * L, PSF_PX, axis=2, mode="nearest")
    rng = np.random.default_rng(seed)
    dn = np.round(S + rng.normal(0.0, 1.0, S.shape) * np.sqrt(READ_DN ** 2 + S / GAIN))
    return np.clip(dn, 0, FULL), gain


def measure(dn):
    """固定の古典処理: 列平均(縦線への整合フィルタ)→ 両脇の中央値を引く → 中央 ±1 列の最大偏差。"""
    col = dn.mean(axis=1)
    c = NX // 2
    bg = np.median(np.concatenate([col[:, :c - 3], col[:, c + 4:]], axis=1), axis=1)
    return np.max(np.abs(col[:, c - 1:c + 2] - bg[:, None]), axis=1)


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    c0 = time.process_time()
    print("=" * 74)
    print("PoC: 「解像度の式」は見つかる大きさを教えない —— 照明ごとの POD(1823A)")
    print("=" * 74)
    print("物体側の画素 %.1f µm、レンズのぼけ σ = %.2f 画素、斜面 %.0f°±%.1f°"
          % (PX * 1000, PSF_PX, SLOPE_DEG, SLOPE_SD))

    # ---- 1. 描画の正しさ ------------------------------------------------- #
    print("\n[1] 描画 = 台帳の物理モデル")
    rng = np.random.default_rng(1)
    sizes_um = np.exp(rng.uniform(math.log(SIZE_UM[0]), math.log(SIZE_UM[1]), N_FLAW))
    widths = np.r_[sizes_um / 1000.0, np.zeros(N_CLEAN)]
    sites = build_sites(widths, seed=2)
    worst = 0.0
    for key, (_, lt) in LIGHTS.items():
        E, D, I0, m = ID._check_light(lt)
        idx = np.random.default_rng(3).choice(len(sites["Pf"]), 48, replace=False)
        P, N = sites["Pf"][idx], sites["Nf"][idx]
        idx2 = np.random.default_rng(4).choice(len(sites["Pc"]), 16, replace=False)
        P = np.r_[P, sites["Pc"][idx2]]
        N = np.r_[N, sites["NL"][idx2]]
        vec = radiance_many(P, N, lt)
        ref = np.array([ID._radiance(p, nn, (CAM - p) / np.linalg.norm(CAM - p), E, D, I0, m, SP)
                        for p, nn in zip(P, N)])
        worst = max(worst, float(np.max(np.abs(vec - ref) / np.abs(ref))))
    check(worst < 1e-12, "ベクトル化した放射輝度 = illumdesign._radiance(3 照明 x 64 点)",
          "最大相対差 %.1e" % worst)
    area = np.array([(sites["fl"][i, 0] + sites["fr"][i, 0]).sum() for i in range(N_FLAW)])
    err = float(np.max(np.abs(area - widths[:N_FLAW] / PX)))
    check(err < 1e-12, "斜面の面積の配分 = 幅 / 画素(厳密)", "最大差 %.1e" % err)

    # ---- 2. 撮像と測定 --------------------------------------------------- #
    print("\n[2] 撮像と â の測定(%d 部位 x %d 照明)" % (widths.size, len(LIGHTS)))
    t1 = time.time()
    meas, gains, imgs = {}, {}, {}
    for key, (_, lt) in LIGHTS.items():
        dn, g = render(sites, lt, seed=5)
        meas[key], gains[key] = measure(dn), g
        imgs[key] = dn
    # 応答の天井: 斜面が画素を埋め尽くす幅(1 mm)の傷の â。そこから先は幅を増やしても
    # 応答が伸びない(1823A の右打ち切り = 「最大の信号」)ので、天井の 8 割より上は
    # 「少なくともその値」として扱う。
    ceil = {}
    wide = build_sites(np.full(24, 1.0), seed=9)
    for key, (_, lt) in LIGHTS.items():
        dnw, _ = render(wide, lt, gain=gains[key], seed=10)
        ceil[key] = float(np.median(measure(dnw)))
    t_render = time.time() - t1
    print("  描画 + 測定 %.1f 秒" % t_render)
    for key, (name, _) in LIGHTS.items():
        nz = meas[key][N_FLAW:]
        print("  %-14s 雑音 â の 50/99 %% 点 %.2f / %.2f DN、傷の â の最大 %.1f DN、天井 %.1f DN"
              % (name, np.percentile(nz, 50), np.percentile(nz, 99), meas[key][:N_FLAW].max(),
                 ceil[key]))

    # ---- 3. POD ---------------------------------------------------------- #
    print("\n[3] â vs a(対数-対数、記録閾値 %.0f DN で左打ち切り、天井の %.0f %% で右打ち切り)"
          % (REC_DN, 100 * CEIL_FRAC))
    lim = VD.detectability_limit(np.geomspace(5.0, 1000.0, 200), focal_mm=FOCAL_MM,
                                 working_distance_mm=WD_MM, pixel_pitch_um=PITCH_UM,
                                 f_number=F_NUMBER, wavelength_um=WAVE_UM)
    print("  設計の式: 分解できる最小の大きさ %.0f µm(%s で決まる)"
          % (lim["lateral_limit_um"], lim["limited_by"]))
    fits, pods, refused = {}, {}, {}
    for key, (name, _) in LIGHTS.items():
        tab = {"a": sizes_um, "ahat": meas[key][:N_FLAW]}
        hi = CEIL_FRAC * ceil[key]
        try:
            f = fs.ledger.pod_ahat_fit(tab, log_size=True, log_response=True, censor_low=REC_DN,
                                       censor_high=hi if hi > 2 * REC_DN else None)
            p = fs.ledger.pod_from_ahat(f, A_DEC)
        except ValueError as exc:
            refused[key] = str(exc)
            print("  %-14s 曲線を拒否: %s" % (name, str(exc)[:110]))
            continue
        fits[key], pods[key] = f, p
        print("  %-14s β1 %.3f±%.3f σ %.3f 打ち切り 左 %d / 右 %d → a50 %.1f / a90 %.1f / "
              "a90/95 %.1f µm" % (name, f["beta1"], math.sqrt(f["cov"][1, 1]), f["sigma"],
                                  f["n_left"], f["n_right"], p["a50"], p["a90"], p["a90_95"]))

    # ゼロ点: 無欠陥の部位にでたらめな大きさを割り振る(応答は大きさと無関係)
    fake = np.exp(np.random.default_rng(11).uniform(math.log(SIZE_UM[0]), math.log(SIZE_UM[1]),
                                                     N_CLEAN))
    try:
        fz = fs.ledger.pod_ahat_fit({"a": fake, "ahat": meas["ring70"][N_FLAW:]},
                                    log_size=True, log_response=True)
        fs.ledger.pod_from_ahat(fz, A_DEC)
        null_msg = None
    except ValueError as exc:
        null_msg = str(exc)
    # 傾きが負なら「not positive」、正でも誤差の内なら「not distinguishable」—— どちらも
    # 「応答が大きさとともに増えるとは言えない」という同じ拒否。
    check(null_msg is not None and ("not distinguishable from 0" in null_msg
                                    or "not positive" in null_msg),
          "ゼロ点: 大きさと無関係な応答(無欠陥部位)では曲線を拒む",
          "(%s)" % (null_msg[:60] + "…" if null_msg else "曲線が出てしまった"))
    check({"ring70", "dome", "ring30"} <= set(pods), "3 照明とも回帰は立つ")
    f30 = fits["ring30"]
    check(f30["n_left"] > 0.75 * N_FLAW,
          "仰角 30°: 傷の 4 分の 3 以上が記録閾値の下", "%d / %d" % (f30["n_left"], N_FLAW))
    check(pods["ring30"]["a90_95_beyond_data"] and not pods["ring70"]["a90_95_beyond_data"]
          and not pods["dome"]["a90_95_beyond_data"],
          "仰角 30° の a90/95 だけ「試した範囲の外」の旗",
          "%.0f µm(試した最大 %.0f µm)" % (pods["ring30"]["a90_95"], sizes_um.max()))
    r70, rdm = pods["ring70"], pods["dome"]
    ratio = rdm["a90_95"] / r70["a90_95"]
    check(r70["a90_95"] < lim["lateral_limit_um"] / 5,
          "仰角 70° の a90/95 は解像度の限界の 1/5 未満",
          "%.1f µm vs %.0f µm(%.0f 分の 1)" % (r70["a90_95"], lim["lateral_limit_um"],
                                               lim["lateral_limit_um"] / r70["a90_95"]))
    check(ratio > 3.0, "同じカメラでも照明で a90/95 が 3 倍以上変わる",
          "ドーム %.1f µm / 仰角 70° %.1f µm = %.1f 倍" % (rdm["a90_95"], r70["a90_95"], ratio))

    # 打ち切りが要る理由
    for key in ("ring70", "dome"):
        f = fits[key]
        z = (f["ols_beta1"] - f["beta1"]) / math.sqrt(f["cov"][1, 1])
        print("  %s: 素朴な最小二乗の傾き %.3f vs 打ち切りつき %.3f(差 %.1f SE)"
              % (key, f["ols_beta1"], f["beta1"], z))
    zz = min((fits[k]["ols_beta1"] - fits[k]["beta1"]) / math.sqrt(fits[k]["cov"][1, 1])
             for k in ("ring70", "dome"))
    check(zz < -2.0, "打ち切りを無視した最小二乗は傾きを寝かせる", "最小 %.1f SE" % zz)

    # ---- 4. 物理で確かめる: a90 の傷を描き直して数える ------------------- #
    print("\n[4] 当てた a90 の大きさの傷を 200 本描き直し、â > %.0f DN の割合を数える" % A_DEC)
    for key in ("ring70", "dome"):
        a90 = pods[key]["a90"]
        s2 = build_sites(np.full(200, a90 / 1000.0), seed=50 + len(key))
        dn2, _ = render(s2, LIGHTS[key][1], gain=gains[key], seed=60 + len(key))
        frac = float(np.mean(measure(dn2) > A_DEC))
        band = 3.0 * math.sqrt(0.9 * 0.1 / 200)
        check(abs(frac - 0.9) <= band, "%s: a90 = %.1f µm での実測の検出率 ≈ 0.9" % (key, a90),
              "%.3f(帯 0.9 ± %.3f)" % (frac, band))

    # ---- 5. 2 値の解析と突き合わせる -------------------------------------- #
    print("\n[5] 同じ測定を見つけた/見落としたに落として 2 値 GLM(probit、対数の大きさ)")
    hms = {}
    for key in ("ring70", "dome", "ring30"):
        hit = (meas[key][:N_FLAW] > A_DEC).astype(int)
        try:
            h = fs.ledger.pod_hitmiss_fit({"a": sizes_um, "hit": hit}, link="probit",
                                          log_size=True)
        except ValueError as exc:
            print("  %-7s 2 値: 曲線を拒否(%s)" % (key, str(exc)[:80]))
            continue
        hms[key] = h
        if key == "ring30":
            print("  %-7s 2 値: a90/95 Wald %.0f µm(試した範囲の外: %s)"
                  % (key, h["a90_95"], h["a90_95_beyond_data"]))
            continue
        p = pods[key]
        d = abs(math.log(h["a90"]) - math.log(p["a90"]))
        se = math.hypot(h["se_x90"], p["se_x90"])
        print("  %-7s 2 値: a90 %.1f / a90/95 Wald %.1f・尤度比 %s µm(â vs a は %.1f / %.1f)"
              % (key, h["a90"], h["a90_95"],
                 "%.1f" % h["a90_95_lr"] if h["a90_95_lr"] else "上限なし", p["a90"], p["a90_95"]))
        check(d < 3 * se, "%s: 2 値の a90 と â vs a の a90 が 3 SE 以内" % key,
              "差 %.2f SE" % (d / se))

    # ---- 6. 誤検出と判定閾値の取引 ---------------------------------------- #
    print("\n[6] 誤検出(無欠陥 %d 部位)と判定閾値の取引表" % N_CLEAN)
    trades = {}
    for key in ("ring70", "dome"):
        nz = meas[key][N_FLAW:]
        q = fs.ledger.pod_false_call(nz, A_DEC, log_response=True)
        T = fs.ledger.pod_decision_tradeoff(fits[key], nz, a_dec_grid=np.linspace(2.0, 12.0, 11))
        trades[key] = T
        print("  %-7s âdec=%.0f DN: 誤検出 %d / %d、PFP50 %.4f、正規の裾 %.2e"
              % (key, A_DEC, q["n_false"], q["n"], q["pfp50"], q["pfp_normal"]))
        for i in (0, 2, 5, 10):
            print("          âdec %5.1f DN → a90/95 %6.1f µm、PFP(正規) %.1e"
                  % (T["a_dec"][i], T["a90_95"][i], T["pfp_normal"][i]))
        check(np.all(np.diff(T["a90"]) > 0) and np.all(np.diff(T["pfp_normal"]) < 0),
              "%s: 閾値を上げると a90 は増え、誤検出は減る" % key)

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    # ★2026-10-15: 壁時計は CI の並列のシャードで同じ機械の他のテストの負荷まで数える
    #   (poc_phase_measuring_deflectometry がこれで赤になった)。この門が抑えたいのはこの PoC 自身の計算量なので、プロセスの CPU 時間
    #   (time.process_time)で測り、壁時計は併記する。
    check(cpu < 45.0, "所要時間(CI の上限に余裕を残す)", "CPU %.1f 秒(壁時計 %.1f 秒)" % (cpu, elapsed))

    # ---- 図 ------------------------------------------------------------- #
    if figs.enabled():
        _figures(sizes_um, meas, imgs, fits, pods, hms, trades, lim)
    assert not figs.errors(), figs.errors()

    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


def _figures(sizes_um, meas, imgs, fits, pods, hms, trades, lim):
    order = np.argsort(sizes_um)
    # 代表の部位: 小・中・大の傷 + 無欠陥、3 照明
    picks = [int(order[k]) for k in (15, 60, 105)] + [N_FLAW]
    panels, caps = [], []
    for key, (name, _) in LIGHTS.items():
        for i in picks:
            panels.append(imgs[key][i] / FULL)
            caps.append("%s %s" % (name, "無欠陥" if i >= N_FLAW else "%.0f µm" % sizes_um[i]))
    figs.save_grid("sites", panels, caps, title="同じ傷・同じカメラ、照明だけ違う",
                   ncols=4, gray=True, vrange=(0.0, 0.6),
                   caption="1 部位 16x10 画素(1 画素 ≈ 100 µm)。仰角 70° は斜面が光を"
                           "カメラへ鏡面反射し、画素より小さい傷でも光る。仰角 30° は何も見えない。")
    ser, kinds, cols = [], [], []
    for key, col in (("ring70", "emphasis"), ("dome", "right"), ("ring30", "neutral")):
        y = np.maximum(meas[key][:N_FLAW], 0.3)
        ser.append((LIGHTS[key][0], np.log10(sizes_um), np.log10(y)))
        kinds.append("scatter")
        cols.append(col)
        if key in fits:
            f = fits[key]
            xs = np.linspace(math.log(SIZE_UM[0]), math.log(SIZE_UM[1]), 50)
            ser.append(("", xs / math.log(10), (f["beta0"] + f["beta1"] * xs) / math.log(10)))
            kinds.append("line")
            cols.append(col)
    for lvl, nm in ((REC_DN, "記録閾値"), (A_DEC, "判定閾値")):
        ser.append((nm, np.log10(SIZE_UM), np.log10([lvl, lvl])))
        kinds.append("line")
        cols.append("reference")
    figs.save_plot("ahat_vs_a", ser, xlabel="log10 傷の幅 [µm]", ylabel="log10 â [DN]",
                   title="â vs a(打ち切りつき最尤の直線)", kinds=kinds, colors=cols,
                   styles=[None] * (len(ser) - 2) + ["dashed"] * 2, size=(720, 440),
                   caption="記録閾値より下は左打ち切り、応答の天井の 8 割より上は右打ち切りとして"
                           "尤度に入る(照明ごとに天井が違う)。")
    ser, cols, sty = [], [], []
    for key, col in (("ring70", "emphasis"), ("dome", "right"), ("ring30", "neutral")):
        p = pods[key]
        ser += [(LIGHTS[key][0], np.log10(p["a"]), p["pod"]),
                ("", np.log10(p["a"]), p["pod_lower"])]
        cols += [col, col]
        sty += [None, "dashed"]
    ser.append(("解像度の限界(設計の式)", np.log10([lim["lateral_limit_um"]] * 2), [0.0, 1.0]))
    cols.append("reference")
    sty.append("dotted")
    figs.save_plot("pod_curves", ser, xlabel="log10 傷の幅 [µm]", ylabel="POD",
                   title="POD(a) と 95 % 下限(破線)", colors=cols, styles=sty, size=(720, 440),
                   caption="仰角 70° の a90/95 = %.1f µm、ドーム %.1f µm、設計の式の限界 %.0f µm。"
                           "仰角 30° は試した範囲(〜300 µm)でほとんど立ち上がらない。"
                           % (pods["ring70"]["a90_95"], pods["dome"]["a90_95"],
                              lim["lateral_limit_um"]))
    ser, cols = [], []
    for key, col in (("ring70", "emphasis"), ("dome", "right")):
        T = trades[key]
        ser.append((LIGHTS[key][0] + " a90/95", T["a_dec"], np.log10(T["a90_95"])))
        cols.append(col)
    figs.save_plot("tradeoff", ser, xlabel="判定閾値 âdec [DN]", ylabel="log10 a90/95 [µm]",
                   title="判定閾値と a90/95 の取引(誤検出は表に)", colors=cols, size=(640, 400),
                   caption="閾値を上げれば誤検出は減るが、90 % 見つかる大きさは伸びる(1823A 図 G-28)。")
    rows = []
    for key, (name, _) in LIGHTS.items():
        p, h = pods[key], hms.get(key)
        ext = "(外挿)" if p["a90_95_beyond_data"] else ""
        rows.append([name, "%.1f" % p["a50"], "%.1f" % p["a90"], "%.1f%s" % (p["a90_95"], ext),
                     "—" if h is None else "%.1f / %s" % (h["a90_95"], "%.1f" % h["a90_95_lr"]
                                                          if h["a90_95_lr"] else "上限なし")])
    rows.append(["設計の式(解像度)", "", "", "%.0f" % lim["lateral_limit_um"], ""])
    figs.save_table("numbers", ["照明", "a50 [µm]", "a90 [µm]", "a90/95 [µm]",
                                "2 値: Wald / 尤度比 [µm]"], rows,
                    title="照明ごとの検出確率(MIL-HDBK-1823A)",
                    caption="真値は描画に入れた傷の幅。a90 は同じ大きさの傷を描き直して実測の"
                            "検出率 0.9 を確かめてある。")


if __name__ == "__main__":
    main()
