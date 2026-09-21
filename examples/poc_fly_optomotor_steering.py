# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで

外乱で向きが流れていく機体に、**複眼と閉じた式の回路しか**積んでいない。ジャイロも磁気コンパスも GPS も無い。
それでも「自分がどれだけ回ったか」を写真だけから読み、逆向きに舵を切れば進路の流れは半分以下になる —— これが
ハエの **optomotor 反応**で、この PoC はそれを fullseye の op だけで組み、**真値のジャイロと並べて**測る。

経路(すべて学習なしの閉形式。勾配で決めた数は 1 つも無い):

    複眼で標本化 → ラミナ(順応 + 帯域通過)→ ON / OFF に分ける → T4/T5 の 6 方向 → 局所フロー
    → 整合フィルタへの線形当てはめ → ヨー角速度 → 6 ニューロンの回路 → 舵

**測ったこと(この PoC の主張。数字はすべてこのスクリプトが出す)**:

1. **段ごとに厳密な恒等式がある。** 景色を 1 万倍明るくしてもラミナの出力は変わらない(Weber、差 7e-16)。
   T4 の三腕モデル(Haag ら 2016、τ=250 ms・k=5/5/10)は論文の 2 柱刺激で **24.9636 / 0.8195** をそのまま返し、
   「増強と抑制は相補的」という主張は **比の積の恒等式**(4.161 × 7.321 = 30.461 = 三腕)として機械精度で成り立つ。
   整合フィルタへの当てはめは 1.7 rad/s を 9 桁一致で戻す。
2. **縞のドラムなら回転計として十分**。古典の optomotor 刺激(方位 25° の正弦縞)では、動き続ける回転に対して
   推定と真値の相関 **0.976**。自然な 1/f の景色では **0.897** に落ちる。
3. **同じ回路が景色ごとに別の較正を要る。** 必要な利得は縞で 2.64、自然な景色で 6.76 と 7.88 ——
   **種類が変われば 3.0 倍、同じ統計の別の景色どうしでも 1.16 倍**ちがう。相関器は速度計ではなく
   「対比つきの運動計」だ、という性質がそのまま出る。
4. **複眼が広いことは飾りではない。** 視野 80° の 1 つの眼で同じ +0.5 rad/s を 12 枚の別々の景色で測ると、
   散らばり(標準偏差/平均)1.05 で、**12 枚中 4 枚は回転の符号すら間違える**。`fly_eye_merge` で 250° に
   束ねると散らばり 0.44、符号の誤りは 0 枚になる。狭い眼は、目の前にたまたま在る大きな模様に振り回される。
5. **閉ループでは効くが、真値には届かない。** 較正は景色 A、飛ぶのは景色 B(**見たことのない景色**)。
   舵を切らなければ進路は 51 度流れ、視葉の反射は 33 度に、真値のジャイロは 23 度にする。
   反射は**絶対の方位を知らない**ので流れをゼロにはできない —— そこから先は中枢複合体(コンパス)の仕事で、
   この PoC の外にある。
6. **操舵はコネクトームの側でも書ける。** 6 ニューロン・8 シナプスを手で配線し(左右の HS →指令→運動、
   対側を抑える押し引き)、`graph_conductance_states` でそのまま回すと、比例帰還と同じ 33 度を出す。
   学習は 1 回もしていない。膜電位は反転電位の凸結合なので、どんな入力でも発散しない。

図: `pathway`(眼が見たもの → 対比 → ON/OFF → フロー)/ `tuning`(縞と 1/f の速度特性)/
`wide_eye`(1 つの眼 vs 束ねた眼)/ `closed_loop`(進路の履歴)/ `circuit`(操舵回路の膜電位と入出力)/
`follow`(閉ループの GIF)/ `numbers`(数表)。

データは同梱しない(景色は `fly_sky_1f` が種から作る)。走らせ方: `py -3.11 examples/poc_fly_optomotor_steering.py`。
参考: B. Hassenstein & W. Reichardt, *Z. Naturforsch.* 11b:513 (1956); H. B. Barlow & R. W. Levick,
*J. Physiol.* 178:477 (1965); H. G. Krapp & R. Hengstenberg, *Nature* 384:463 (1996);
M. O. Franz & H. G. Krapp, *Biol. Cybern.* 83:185 (2000); J. Haag, A. Arenz, E. Serbe, F. Gabbiani &
A. Borst, *eLife* 5:e17421 (2016); M. S. Groschner et al., *Nature* 603:119 (2022).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger

# ---------------------------------------------------------------------------- #
#  眼と世界                                                                       #
# ---------------------------------------------------------------------------- #
RADIUS, DPHI, DRHO = 8, 5.0, 8.23      # 217 個眼 / 個眼間角 5° / 受容角 8.23°(Δρ/Δφ = 1.6)
FOV, IMG = 90.0, 96                    # 眼ごとのピンホール像
AZ0 = (-85.0, 0.0, 85.0)               # 3 つの眼で方位 250° を覆う(重なりは作らない)
PANO_W, PANO_H = 720, 360
DT = 0.02                              # 50 Hz
WIN = 60                               # 経路に渡す窓 = 1.2 s
TAU_ADAPT, TAU_LP, TAU_ARM = 0.3, 0.02, 0.15
EVERY = 2                              # 舵を打ち直す間隔[コマ](25 Hz)
K_FB = 2.0                             # 比例帰還の利得
CAL_SEED, TEST_SEED = 12, 20           # 較正の景色 / 飛ぶ景色(別物)
N_STEPS = 300


def make_eye(az0):
    """格子と、その眼のピンホール画素の視線方向(fly_hex_resample と同じ規約)。"""
    lat = L.fly_hex_lattice(radius=RADIUS, dphi_deg=DPHI, az0_deg=az0, el0_deg=0.0)
    uv = lat["uv"]
    c = int(np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0])
    axis = lat["dirs"][c]
    f = (IMG / 2.0) / np.tan(np.deg2rad(FOV) / 2.0)
    yy, xx = np.mgrid[0:IMG, 0:IMG].astype(float)
    xc = (xx + 0.5 - IMG / 2.0) / f
    yc = -(yy + 0.5 - IMG / 2.0) / f
    el0 = float(np.arcsin(np.clip(axis[2], -1.0, 1.0)))
    a0 = float(np.arctan2(axis[1], axis[0]))
    left = np.array([-np.sin(a0), np.cos(a0), 0.0])
    up = np.array([-np.cos(a0) * np.sin(el0), -np.sin(a0) * np.sin(el0), np.cos(el0)])
    d = (axis[None, None, :] + left[None, None, :] * xc[..., None]
         + up[None, None, :] * yc[..., None])
    return lat, d / np.linalg.norm(d, axis=-1, keepdims=True)


EYES = [make_eye(a) for a in AZ0]
WIDE = L.fly_eye_merge(*[e[0] for e in EYES])      # 3 つの眼 = 1 つの広い眼
N1 = EYES[0][0]["dirs"].shape[0]


def sample_pano(pano, az, el):
    """等距円筒パノラマ(行 = 仰角 +90→−90、列 = 方位 0→360)を双一次で引く。"""
    H, W = pano.shape
    col = (np.degrees(az) % 360.0) / 360.0 * W - 0.5
    row = (90.0 - np.degrees(el)) / 180.0 * H - 0.5
    c0 = np.floor(col).astype(int)
    r0 = np.floor(row).astype(int)
    fc, fr = col - c0, row - r0
    c1 = (c0 + 1) % W
    c0 = c0 % W
    r0c = np.clip(r0, 0, H - 1)
    r1 = np.clip(r0 + 1, 0, H - 1)
    return (pano[r0c, c0] * (1 - fr) * (1 - fc) + pano[r0c, c1] * (1 - fr) * fc
            + pano[r1, c0] * fr * (1 - fc) + pano[r1, c1] * fr * fc)


def look(pano, yaw):
    """ヨー角 *yaw* のときの、3 つの眼それぞれの個眼輝度 (n,)。"""
    out = []
    for lat, de in EYES:
        c, s = np.cos(yaw), np.sin(yaw)
        dx = c * de[..., 0] - s * de[..., 1]
        dy = s * de[..., 0] + c * de[..., 1]
        dz = de[..., 2]
        img = sample_pano(pano, np.arctan2(dy, dx), np.arcsin(np.clip(dz, -1.0, 1.0)))
        out.append(L.fly_hex_resample(img, lat, drho_deg=DRHO, fov_deg=FOV))
    return out


def stages(seg, lat):
    """1 つの眼の窓 (WIN, n) → (対比, ON, OFF, 方向別応答, 局所フロー)。"""
    contrast = L.fly_lamina_filter(seg, DT, tau_adapt_s=TAU_ADAPT, tau_lp_s=TAU_LP)
    onoff = L.fly_onoff_split(contrast, DT)
    on, off = onoff[:, :N1], onoff[:, N1:]
    field = (L.fly_t4t5_field(on, lat, DT, tau_s=TAU_ARM)
             + L.fly_t4t5_field(off, lat, DT, tau_s=TAU_ARM))
    return contrast, on, off, field, L.fly_flow_from_directions(field, lat)


def pathway(buffers, full=False):
    """3 つの眼の窓 → ヨー角速度(較正前の生の量)。"""
    flows, extra = [], []
    for (lat, _de), buf in zip(EYES, buffers):
        out = stages(np.asarray(buf), lat)
        flows.append(out[4])
        if full:
            extra.append(out)
    est = L.fly_egomotion_from_flow(np.vstack(flows), WIDE, axes=[[0.0, 0.0, 1.0]])
    return (est, extra) if full else est


def scene_1f(seed):
    return L.fly_sky_1f(PANO_W, PANO_H, band_lo_deg=-60.0, band_hi_deg=70.0,
                        amp=0.35, seed=seed)


def scene_drum(lam_deg=25.0):
    """古典の optomotor 刺激: 方位に正弦の縞を張った回転ドラム。"""
    az = np.linspace(0.0, 2.0 * np.pi, PANO_W, endpoint=False)[None, :]
    return 0.6 + 0.25 * np.sin(2.0 * np.pi / np.deg2rad(lam_deg) * az) * np.ones((PANO_H, 1))


def constant_turn(pano, rate):
    """一定の角速度で回りながら WIN コマ見て、経路に通す。"""
    bufs = [[] for _ in EYES]
    for i in range(WIN):
        for b, s in zip(bufs, look(pano, rate * i * DT)):
            b.append(s)
    return bufs


# ---------------------------------------------------------------------------- #
#  操舵回路 6 ニューロン・8 シナプス(手で配線する。学習しない)                                  #
# ---------------------------------------------------------------------------- #
CIRCUIT_NAMES = ("HS left", "HS right", "cmd left", "cmd right", "motor left", "motor right")
#: (pre, post, 重み)。正 = 興奮性、負 = 抑制性。左右対称で、対側を抑える(押し引き)。
CIRCUIT_SYNAPSES = ((0, 2, 0.6), (0, 3, -0.6), (1, 3, 0.6), (1, 2, -0.6),
                    (2, 4, 0.6), (3, 5, 0.6), (4, 5, -0.4), (5, 4, -0.4))
CIRCUIT_DRIVE = 0.3
CIRCUIT_SLOPE = 0.128                 # w = 0 近傍の傾き(下で測る)


def circuit_graph():
    syn = np.array([[a, b, abs(w)] for a, b, w in CIRCUIT_SYNAPSES], dtype=np.float64)
    sign = np.array([1.0 if w > 0 else -1.0 for _, _, w in CIRCUIT_SYNAPSES])
    W = L.graph_from_synapses(syn, n=len(CIRCUIT_NAMES))
    for (a, b, _w), s in zip(CIRCUIT_SYNAPSES, sign):
        W[a, b] = abs(_w) * s
    return W


def circuit_steer(W, series, n_hold=1, v0=None):
    """ヨー角速度の列 → 膜電位の列 (T, 6) と舵の列 (T,)。

    ``v0`` を渡すと前回の続きから回す —— 閉ループでは回路は切れ目なく動いている。"""
    series = np.asarray(series, dtype=np.float64)
    drive = np.zeros((series.size * n_hold, len(CIRCUIT_NAMES)))
    rep = np.repeat(series, n_hold)
    drive[:, 0] = np.maximum(rep, 0.0) * CIRCUIT_DRIVE
    drive[:, 1] = np.maximum(-rep, 0.0) * CIRCUIT_DRIVE
    V = L.graph_conductance_states(W, drive, dt_s=DT, tau_s=0.08, gain=1.0, v0=v0)
    return V, V[:, 4] - V[:, 5]


# ---------------------------------------------------------------------------- #
#  飛ぶ                                                                          #
# ---------------------------------------------------------------------------- #
def disturbance(n_t, seed, bias=0.3):
    """帯域制限した乱数 + 一定の偏り(片翼が弱い / 横風)。"""
    rng = np.random.default_rng(seed)
    w = np.zeros(n_t)
    v = 0.0
    for i in range(n_t):
        v += (-v / 2.0 + rng.normal(0.0, 2.0)) * DT
        w[i] = v + bias
    return w


def fly(pano, dist, mode, gain, k=K_FB, keep=False):
    """*mode* = open(舵を切らない)/ gyro(真値の角速度)/ visual(視葉)/ circuit(視葉 + 回路)。"""
    yaw, u = 0.0, 0.0
    yaws, rates, ests, truth, volts, views = [], [], [], [], [], []
    bufs = [[] for _ in EYES]
    W = circuit_graph()
    v_state = np.zeros(len(CIRCUIT_NAMES))
    for i in range(len(dist)):
        seen = look(pano, yaw)
        for b, s in zip(bufs, seen):
            b.append(s)
            if len(b) > WIN:
                b.pop(0)
        wm = float(np.mean(rates[-WIN:])) if rates else 0.0     # 同じ窓で均した真値
        truth.append(wm)
        e = np.nan
        if len(bufs[0]) == WIN and i % EVERY == 0:
            if mode == "open_est":
                e = pathway(bufs)["yaw_rad_s"] * gain
            elif mode == "gyro":
                e = wm
                u = -k * e
            elif mode in ("visual", "circuit"):
                e = pathway(bufs)["yaw_rad_s"] * gain
                if mode == "visual":
                    u = -k * e
                else:
                    V, st = circuit_steer(W, [e], n_hold=EVERY, v0=v_state)
                    v_state = V[-1]
                    u = -k * float(st[-1]) / CIRCUIT_SLOPE
        ests.append(e)
        volts.append(v_state.copy())
        if keep:
            views.append(np.concatenate(seen))
        rate = dist[i] + (0.0 if mode in ("open", "open_est") else u)
        yaw += rate * DT
        yaws.append(yaw)
        rates.append(rate)
    return {"yaw": np.array(yaws), "rate": np.array(rates), "est": np.array(ests),
            "truth": np.array(truth), "volt": np.array(volts),
            "views": np.array(views) if keep else None}


# ---------------------------------------------------------------------------- #
#  図の小道具                                                                     #
# ---------------------------------------------------------------------------- #
def hex_raster(lat, values, step_deg=0.35, pad=1.0):
    """個眼の値を方位・仰角の平面に六角のまま描く(最近傍、視野の外は NaN→0)。"""
    az = np.degrees(np.asarray(lat["az_rad"]))
    el = np.degrees(np.asarray(lat["el_rad"]))
    xs = np.arange(az.min() - pad, az.max() + pad, step_deg)
    ys = np.arange(el.max() + pad, el.min() - pad, -step_deg)
    X, Y = np.meshgrid(xs, ys)
    d2 = (X[..., None] - az) ** 2 + (Y[..., None] - el) ** 2
    k = np.argmin(d2, axis=2)
    out = np.asarray(values, float)[k]
    out[np.take_along_axis(d2, k[..., None], axis=2)[..., 0] > (1.2 * DPHI) ** 2] = 0.0
    return out


def main():
    t_start = time.time()
    checks, rows = [], []
    np.set_printoptions(precision=4, suppress=True)
    print("ハエの視葉だけで進路を立て直す —— 眼 %d 個 x %d 個眼(方位 %.0f 度をカバー)"
          % (len(EYES), N1, (AZ0[-1] - AZ0[0]) + 2 * RADIUS * DPHI))

    # ---------------------------------------------------------------- 1. 恒等式
    print()
    print("1. 段ごとの恒等式(合成刺激、閉じた式)")
    lat0 = EYES[1][0]
    t = np.arange(400) * 0.005
    flick = (1.0 + 0.2 * np.sin(2 * np.pi * 2.0 * t))[:, None] * np.ones((1, N1))
    weber = float(np.abs(L.fly_lamina_filter(flick, 0.005)
                         - L.fly_lamina_filter(1e4 * flick, 0.005)).max())
    print("   Weber: 景色を 1 万倍明るくしたときのラミナ出力の差 = %.2e" % weber)
    checks.append(("ラミナは明るさに依らない(Weber)", weber < 1e-12))

    lut = {(int(u), int(v)): i for i, (u, v) in enumerate(np.asarray(lat0["uv"]))}
    c0 = lut[(0, 0)]
    ratios = {}
    for model in ("three_arm", "enhance", "suppress"):
        vals = {}
        for order in ("pd", "nd"):
            first = lut[(0, -1)] if order == "pd" else lut[(0, 1)]
            x = np.zeros((251, N1))
            x[1:, first] = 1.0
            x[-1, c0] = 1.0
            vals[order] = L.fly_t4t5_field(x, lat0, 0.001, model=model,
                                           reduce="last")[0, c0] + 1.0
        ratios[model] = vals["pd"] / vals["nd"]
        if model == "three_arm":
            pd_nd = vals
    print("   T4 三腕(Haag 2016 の逐語の定数): 好む向き %.4f / 逆向き %.4f(論文 24.96 / 0.820)"
          % (pd_nd["pd"], pd_nd["nd"]))
    print("   増強だけ %.3f x 抑制だけ %.3f = %.3f、三腕 %.3f(積の恒等式)"
          % (ratios["enhance"], ratios["suppress"],
             ratios["enhance"] * ratios["suppress"], ratios["three_arm"]))
    checks.append(("三腕は論文の 2 柱刺激の値を返す",
                   abs(pd_nd["pd"] - 24.9636) < 1e-3 and abs(pd_nd["nd"] - 0.8195) < 1e-3))
    checks.append(("方向選択性は増強と抑制の積(相補的)",
                   abs(ratios["three_arm"] - ratios["enhance"] * ratios["suppress"])
                   < 1e-6 * ratios["three_arm"]))

    tmpl = L.fly_matched_filter(WIDE, axis=(0.0, 0.0, 1.0))
    back = L.fly_egomotion_from_flow(tmpl * 1.7, WIDE, axes=[[0.0, 0.0, 1.0]])
    one = EYES[1][0]
    cond_one = L.fly_egomotion_from_flow(L.fly_matched_filter(one, axis=(0, 0, 1)),
                                         one)["condition"]
    cond_wide = L.fly_egomotion_from_flow(tmpl, WIDE)["condition"]
    print("   整合フィルタ → 当てはめ: 1.7 rad/s を %.9f rad/s で戻す(説明率 %.6f)"
          % (back["yaw_rad_s"], back["explained"]))
    print("   3 軸を分ける条件数: 1 つの眼 %.2f → 束ねた眼 %.2f(狭い眼は回転軸を分けられない)"
          % (cond_one, cond_wide))
    checks.append(("整合フィルタの回転を厳密に戻す", abs(back["yaw_rad_s"] - 1.7) < 1e-9))
    checks.append(("束ねた眼のほうが条件数が良い", cond_wide < cond_one))

    # ---------------------------------------------------------------- 2. 速度特性
    print()
    print("2. 速度特性(一定の回転を見せて、推定が真値に比例するか)")
    rates_cal = np.array([-0.6, -0.3, -0.15, 0.15, 0.3, 0.6])
    tuning = {}
    for name, pano in (("縞 25 度", scene_drum()), ("1/f 景色 A", scene_1f(CAL_SEED)),
                       ("1/f 景色 B", scene_1f(TEST_SEED))):
        raw = np.array([pathway(constant_turn(pano, r))["yaw_rad_s"] for r in rates_cal])
        g = float(np.dot(raw, rates_cal) / np.dot(raw, raw))
        r = float(np.corrcoef(raw, rates_cal)[0, 1])
        tuning[name] = (raw, g, r)
        print("   %-10s 相関 %.4f   必要な較正利得 %6.2f   単調 %s"
              % (name, r, g, "yes" if np.all(np.diff(raw) > 0) else "no"))
        rows.append([name, "%.4f" % r, "%.2f" % g,
                     "yes" if np.all(np.diff(raw) > 0) else "no", "-", "-"])
    gain_a, gain_b = tuning["1/f 景色 A"][1], tuning["1/f 景色 B"][1]
    gain_drum = tuning["縞 25 度"][1]
    print("   必要な利得: 縞 %.2f に対し自然な景色は %.2f / %.2f —— 種類が変わると %.1f 倍、"
          "同じ統計の別の景色どうしでも %.2f 倍ちがう(相関器は対比つきの運動計で、速度計ではない)"
          % (gain_drum, gain_a, gain_b, max(gain_a, gain_b) / gain_drum,
             max(gain_a / gain_b, gain_b / gain_a)))
    checks.append(("縞では単調かつ相関 0.95 以上",
                   tuning["縞 25 度"][2] > 0.95 and np.all(np.diff(tuning["縞 25 度"][0]) > 0)))
    checks.append(("景色の種類が変わると較正利得が 2 倍以上ずれる",
                   max(gain_a, gain_b) / gain_drum > 2.0))

    # ---------------------------------------------------------------- 3. 眼の広さ
    print()
    print("3. 眼の広さ(同じ +0.5 rad/s を 12 枚の別々の景色で測る)")
    one_lat = EYES[1][0]
    got_one, got_wide = [], []
    for sd in range(12):
        pano = scene_1f(sd)
        bufs = constant_turn(pano, 0.5)
        flows = [stages(np.asarray(b), lat)[4] for b, (lat, _d) in zip(bufs, EYES)]
        got_one.append(L.fly_egomotion_from_flow(flows[1], one_lat,
                                                 axes=[[0, 0, 1]])["yaw_rad_s"])
        got_wide.append(L.fly_egomotion_from_flow(np.vstack(flows), WIDE,
                                                  axes=[[0, 0, 1]])["yaw_rad_s"])
    got_one, got_wide = np.array(got_one), np.array(got_wide)
    cv_one = float(got_one.std() / abs(got_one.mean()))
    cv_wide = float(got_wide.std() / abs(got_wide.mean()))
    bad_one = int((got_one <= 0).sum())
    bad_wide = int((got_wide <= 0).sum())
    print("   1 つの眼 (視野 %.0f 度): 散らばり/平均 %.2f、符号を誤った景色 %d / 12"
          % (2 * RADIUS * DPHI, cv_one, bad_one))
    print("   束ねた眼 (視野 %.0f 度): 散らばり/平均 %.2f、符号を誤った景色 %d / 12"
          % ((AZ0[-1] - AZ0[0]) + 2 * RADIUS * DPHI, cv_wide, bad_wide))
    rows.append(["1 つの眼(80 度)", "-", "-", "-", "%.2f" % cv_one, "%d / 12" % bad_one])
    rows.append(["束ねた眼(250 度)", "-", "-", "-", "%.2f" % cv_wide, "%d / 12" % bad_wide])
    checks.append(("束ねた眼のほうが散らばりが小さい", cv_wide < cv_one))
    checks.append(("束ねた眼は符号を誤らない", bad_wide == 0))
    checks.append(("束ねた眼の散らばりは 1 つの眼の 7 割以下", cv_wide < 0.7 * cv_one))

    # ------------------------------------------------- 3b. 時間変化する回転
    print()
    print("3b. 動きが変わり続けるとき(同じ外乱を縞と自然な景色で開ループで見る)")
    dist = disturbance(N_STEPS, seed=5)
    varying = {}
    for name, pano in (("縞 25 度", scene_drum()), ("1/f 景色 B", scene_1f(TEST_SEED))):
        r = fly(pano, dist, "open_est", tuning[name][1])
        ok = np.isfinite(r["est"])
        varying[name] = float(np.corrcoef(r["est"][ok], r["truth"][ok])[0, 1])
        print("   %-10s 推定と真値(同じ窓で均したもの)の相関 %.3f" % (name, varying[name]))
        rows.append([name + "(動く刺激)", "%.3f" % varying[name], "-", "-", "-", "-"])
    checks.append(("縞では相関 0.9 以上", varying["縞 25 度"] > 0.9))
    checks.append(("自然な景色では縞より落ちる", varying["1/f 景色 B"] < varying["縞 25 度"]))

    # ---------------------------------------------------------------- 4. 閉ループ
    print()
    print("4. 閉ループ(較正は景色 A、飛ぶのは見たことのない景色 B)")
    gain = gain_a
    runs = {}
    for mode in ("open", "gyro", "visual", "circuit"):
        runs[mode] = fly(scene_1f(TEST_SEED), dist, mode, gain, keep=(mode == "circuit"))
    names = {"open": "舵を切らない", "gyro": "真値のジャイロ", "visual": "視葉(比例)",
             "circuit": "視葉 + 6 ニューロンの回路"}
    drift0 = abs(np.degrees(runs["open"]["yaw"][-1]))
    for mode in ("open", "gyro", "visual", "circuit"):
        r = runs[mode]
        ok = np.isfinite(r["est"])
        corr = (float(np.corrcoef(r["est"][ok], r["truth"][ok])[0, 1])
                if ok.sum() > 5 else float("nan"))
        drift = abs(float(np.degrees(r["yaw"][-1])))
        rms = float(np.sqrt((r["rate"] ** 2).mean()))
        print("   %-22s 進路の流れ %6.1f 度(%3.0f %%)  角速度 rms %.3f rad/s  推定と真値の相関 %s"
              % (names[mode], drift, 100.0 * drift / drift0, rms,
                 "--" if not np.isfinite(corr) else "%.3f" % corr))
        rows.append([names[mode], "-", "-", "-", "%.1f 度" % drift, "%.3f" % rms])
    d_open = abs(float(np.degrees(runs["open"]["yaw"][-1])))
    d_vis = abs(float(np.degrees(runs["visual"]["yaw"][-1])))
    d_gyro = abs(float(np.degrees(runs["gyro"]["yaw"][-1])))
    d_cir = abs(float(np.degrees(runs["circuit"]["yaw"][-1])))
    checks.append(("視覚の反射は進路の流れを減らす", d_vis < 0.85 * d_open))
    checks.append(("真値のジャイロには届かない(正直に併記)", d_gyro < d_vis))
    checks.append(("6 ニューロンの回路でも同じ仕事ができる", d_cir < 0.85 * d_open))
    ok = np.isfinite(runs["visual"]["est"])
    corr_loop = float(np.corrcoef(runs["visual"]["est"][ok], runs["visual"]["truth"][ok])[0, 1])
    checks.append(("閉ループでも推定は真値と相関する", corr_loop > 0.5))

    # ---------------------------------------------------------------- 5. 回路
    print()
    print("5. 操舵回路(6 ニューロン・8 シナプス、手で配線、学習なし)")
    W = circuit_graph()
    probe = np.array([-1.0, -0.6, -0.3, -0.1, 0.0, 0.1, 0.3, 0.6, 1.0])
    curve = np.array([circuit_steer(W, [p], n_hold=200)[1][-1] for p in probe])
    volts = runs["circuit"]["volt"]
    print("   入出力: %s" % np.round(curve, 4))
    print("   奇対称の誤差 %.2e、単調 %s、飽和(|舵| の上限) %.4f"
          % (float(np.abs(curve + curve[::-1]).max()), np.all(np.diff(curve) > 0),
             float(np.abs(curve).max())))
    print("   膜電位は反転電位の間に留まる: %.4f .. %.4f(構造で保証、発散しない)"
          % (float(volts.min()), float(volts.max())))
    checks.append(("回路は奇対称で単調", float(np.abs(curve + curve[::-1]).max()) < 1e-9
                   and bool(np.all(np.diff(curve) > 0))))
    checks.append(("膜電位は反転電位の間に留まる",
                   float(volts.min()) >= -1.0 - 1e-12 and float(volts.max()) <= 1.0 + 1e-12))

    # ---------------------------------------------------------------- 図
    if figs.enabled():
        pano = scene_1f(TEST_SEED)
        bufs = constant_turn(pano, 0.5)
        _est, extra = pathway(bufs, full=True)
        contrast, on, off, field, flow = extra[1]
        lat = EYES[1][0]
        panels = [hex_raster(lat, bufs[1][-1]), hex_raster(lat, contrast[-1]),
                  hex_raster(lat, on[-1]), hex_raster(lat, off[-1]),
                  hex_raster(lat, flow[:, 0]), hex_raster(lat, field[0] - field[3])]
        figs.save_grid("pathway", panels,
                       captions=["個眼が見た明るさ", "ラミナの対比(明るさは捨てた)",
                                 "ON チャネル(Mi1 / Tm3)", "OFF チャネル(Tm1 / Tm2)",
                                 "局所フローの方位成分", "方向 0 − 方向 3(opponent)"],
                       ncols=3, signed=[False, True, False, False, True, True],
                       title="前向きの眼が +0.5 rad/s で回っているときの各段",
                       caption="left to right, top to bottom: what the ommatidia see, the lamina's "
                               "contrast (brightness thrown away), the ON and OFF channels, and the "
                               "direction-selective field read as a local flow. The eye is turning at "
                               "0.5 rad/s in a 1/f panorama; nothing here was trained.")
        figs.save_plot("tuning",
                       [(k, rates_cal, v[0] * v[1]) for k, v in tuning.items()]
                       + [("真値", rates_cal, rates_cal)],
                       xlabel="真のヨー角速度 [rad/s]", ylabel="推定(各景色で較正)[rad/s]",
                       title="速度特性: 縞のドラムと自然な景色",
                       caption="each scene is fitted with its own single gain; the striped drum is "
                               "nearly linear, and a natural 1/f scene needs a gain %.1fx larger "
                               "— a correlation detector reports contrast-weighted motion, not velocity"
                               % (max(gain_a, gain_b) / gain_drum))
        figs.save_plot("wide_eye",
                       [("1 つの眼(80 度)", np.arange(float(len(got_one))), got_one),
                        ("束ねた眼(250 度)", np.arange(float(len(got_wide))), got_wide)],
                       xlabel="景色(1/f、種だけ違う)", ylabel="推定した回転(生の量)",
                       title="同じ +0.5 rad/s を 12 枚の景色で測る",
                       caption="a narrow eye is at the mercy of whichever few large features are in "
                               "front of it: over eight scenes of identical statistics it scatters and "
                               "gets the sign wrong %d time(s) out of 12; the merged 250-degree eye gets it wrong "
                               "%d time(s), and its scatter is %.0f%% smaller" % (bad_one, bad_wide, 100 * (1 - cv_wide / cv_one)))
        tt = np.arange(N_STEPS) * DT
        figs.save_plot("closed_loop",
                       [(names[m], tt, np.degrees(runs[m]["yaw"])) for m in
                        ("open", "gyro", "visual", "circuit")],
                       xlabel="時間 [s]", ylabel="進路 [度]",
                       title="外乱のなかで進路を保つ(較正は別の景色)",
                       caption="the disturbance has a steady bias, so the open loop drifts away; the "
                               "optomotor reflex cuts the drift but cannot null it — a reflex has no "
                               "absolute heading, which is where the central complex would come in")
        figs.save_plot("circuit",
                       [(CIRCUIT_NAMES[i], tt, volts[:, i]) for i in range(len(CIRCUIT_NAMES))],
                       xlabel="時間 [s]", ylabel="膜電位(反転電位の間)",
                       title="8 シナプスの操舵回路(学習なし)",
                       caption="the wiring is written by hand as a synapse table and run as a "
                               "conductance circuit; the state is a convex combination of the reversal "
                               "potentials, so it cannot diverge whatever the input does")
        keep = runs["circuit"]["views"]
        if keep is not None and len(keep):
            idx = np.linspace(WIN, N_STEPS - 1, 48).astype(int)
            est_hold = runs["circuit"]["est"].copy()
            last = 0.0
            for j in range(est_hold.size):                      # 舵は EVERY コマ保持される
                if np.isfinite(est_hold[j]):
                    last = float(est_hold[j])
                est_hold[j] = last
            rasters = []
            for i in idx:
                # 左・前・右の 3 つの眼を、世界の方位の順(左が +方位)に並べる
                per = [hex_raster(EYES[e][0], keep[i][e * N1:(e + 1) * N1], step_deg=0.6)
                       for e in (2, 1, 0)]
                h = min(p.shape[0] for p in per)
                rasters.append(np.hstack([p[:h] for p in per]))
            hmin = min(r.shape[0] for r in rasters)
            wmin = min(r.shape[1] for r in rasters)
            rasters = [r[:hmin, :wmin] for r in rasters]
            top = max(float(r.max()) for r in rasters)          # 尺度は全コマで 1 つ
            frames = []
            for r, i in zip(rasters, idx):
                bar = np.zeros((14, wmin))
                mid = wmin // 2
                bar[:, mid] = 0.35                              # 真ん中(回っていない)の目印
                w = int(np.clip(float(est_hold[i]) / 0.5, -1.0, 1.0) * (mid - 3))
                bar[4:11, min(mid, mid + w):max(mid, mid + w) + 1] = 1.0
                frames.append(np.vstack([r / max(top, 1e-9), bar]))
            figs.save_gif("follow", frames, fps=8.0,
                          caption="the three eyes (left, front, right = 250 degrees of azimuth) during "
                                  "the closed-loop run, and under them the yaw rate the circuit is "
                                  "steering against (full width = 0.5 rad/s, the tick is zero). "
                                  "%d frames, %.0f ms apart" % (len(frames), DT * 1000 * (N_STEPS - WIN) / 48))
        figs.save_table("numbers",
                        ["場面 / 走り", "相関", "較正利得", "単調", "散らばり or 流れ", "誤符号 or rms"],
                        rows, title="ハエの視葉だけで進路を立て直す: 測った数",
                        caption="rows 1-3 are the speed tuning per scene, rows 4-5 the width of the "
                                "eye, rows 6-9 the closed loop (drift in degrees and the rms yaw rate)")

    print()
    print("走行 %.1f 秒。学習した数: 0。較正した数: 1(景色 A で決めた利得 %.2f を景色 B で使った)"
          % (time.time() - t_start, gain))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print("  [%s] %s" % ("ok" if ok else "NG", n))
    if bad:
        print("FAIL: %d 件の検査が成り立たなかった" % len(bad))
        raise SystemExit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
