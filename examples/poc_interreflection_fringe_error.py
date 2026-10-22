# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 白い Lambert の溝でも縞投影は外れる —— 相互反射を直接光と分け、誤差を事前に予測し、マイクロ位相シフトで消す

    py -3.11 examples/poc_interreflection_fringe_error.py

縞投影(位相シフト)は「画素に届く光は、プロジェクタの 1 点から来た」と仮定して位相を高さに
変えます。凹んだ形 —— V 溝、加工ポケットの内角、はんだフィレット —— では、片方の面で反射した
光が向かいの面を照らし、画素には**別の場所の縞の位相を持った光**が混ざります(相互反射)。
光沢も金属も要りません。**真っ白な紙のような Lambert 面でも、凹んでいれば起きます**。

この PoC は、幅 1 mm の溝を 3 つ並べた白い部品(反射率 0.85)で、次を実測します。

1. **直接光と大域光(相互反射)を分ける**。溝に平行な 2 値の縞をずらして 8 枚撮り、画素ごとの
   最大と最小から分ける(Nayar ら 2006)。大域光の像は**凹みの中だけが光り**、V 溝の底では
   相互反射が直接光より明るい。真値(輸送行列で別に計算)と比べ、縞の周期を細かくすると
   分離の誤差が減ること、細かすぎると画素の足跡より細くなって崩れることも数字で見せます。
2. **縞の位相の誤差を、撮る前に予測する**。輸送行列から各画素の「直接のフェーザ + 大域の
   フェーザ」の偏角を閉形式で計算し(``predict_fringe_phase_error``)、実際に描いた縞を
   ``fringe.wrapped_phase`` で復号した誤差と画素ごとに重ねます(一致は 1e-12 rad)。視野に縞
   1 本の位相シフト(視野 4 mm)では、深さ 0.5 mm の 90° の溝で高さ誤差が RMS 約 280 µm。
   よく使う 2 段の位相接続(縞 1 本で次数を決め、16 px の縞で精度を出す)も救いになりません:
   縞 1 本の誤差(最大 80 px 超)が 16 px の縞の半周期 8 px を超えた画素(溝の 7 割)で次数が
   何段もずれ(1 段 = 137 µm)、誤差は縞 1 本とほぼ同じ大きさのまま残ります。
3. **マイクロ位相シフト(Gupta & Nayar 2012)に切り替えると誤差が消える**。周期の近い高周波の
   縞 3 組(16 / 16.2 / 15.8 px)だけを使い、うなり(合成周期 1296 px)で次数を決めます。
   どの縞も細かいので、相互反射の光は縞の位相をほぼ平均してしまい、位相を引っぱらない。
4. **ToF も同じ理屈で外れる**。部屋の隅(4 m の 90° の角、白い壁)を連続波 ToF(20 MHz)で
   測ると、壁どうしの相互反射が経路を長くして、隅が**丸く遠く**見える。反射ごとの遅れを
   入れた複素ラジオシティで予測します。

真値: 2-D(押し出し形状)の Lambert ラジオシティ。形態係数は Hottel の crossed-strings 則の
閉形式で、``tests/test_lighttransport.py`` が V 溝の閉形式 ``1 − sin(θ/2)`` と数値積分で
1e-14 まで確かめてあります。直接だけの真値は、反射回数 0 の輸送行列で描いた画像です。

★正直に書いておくこと(範囲と合成であること):
  * **Lambert(完全拡散)と、溝の軸方向に無限に長い形**だけです。実物のはんだや金属の溝では
    鏡面の相互反射が支配的で、誤差はもっと大きく形も違います —— その真値には Mitsuba 3 の
    ``gi_render``(optional)が要り、この PoC は使っていません。
  * カメラとプロジェクタは正射影、縞は溝に平行。雑音・ボケ・プロジェクタの黒レベルは入れて
    いません(黒レベルは ``separate_direct_global`` の ``black_level`` で扱えます)。
  * マイクロ位相シフトは論文の F + 2 枚の同時解法ではなく、周波数ごとに 4 枚(計 12 枚)で
    復号し、2 周波のうなりで次数を決めています。雑音があると、うなりの位相は 81 倍に
    増幅されるので、実機では周波数の組を論文のように選び直す必要があります。
  * ToF の部屋の隅は 2-D のモデル(壁は上下に無限、光源はカメラ位置の線光源)の数字です。
    3-D の点光源では大域光の割合が変わります(符号と「隅が丸く遠く見える」形は同じ)。

走らせ方: ``py -3.11 examples/poc_interreflection_fringe_error.py``
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
import fringe  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)

CHECKS = []

ALBEDO = 0.85             # 白い樹脂・白い塗装くらい
BETA = 20.0               # 三角測量の角(プロジェクタの傾き)[°]
COLS = 160                # 溝 1 本あたりのカメラの列(幅 1 mm → 6.25 µm / 画素)
FLAT = 40                 # 溝のあいだの平らな部分の列(0.25 mm)
OVERSAMPLE = 2            # プロジェクタの画素はカメラの画素の半分(平らな面の上で)
ROWS = 96                 # 図の縦(溝の軸方向。2-D なので全行が同じ)
MICRO = (16.0, 16.2, 15.8)


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def _wrap(a):
    return np.angle(np.exp(1j * a))


def build_part():
    """平ら | 90° の V 溝(内角) | 平ら | 60° の V 溝 | 平ら | R つきのポケット | 平ら。

    溝はそれぞれ独立した凹み(平らな上面は空しか見ず、溝の中は開口の外を見ない)なので、
    区間ごとに輸送行列を作って横に並べれば部品全体の画像になる。"""
    dx = 1.0 / COLS
    flat = fs.ledger.groove_profile("polyline", vertices=np.stack([np.arange(FLAT + 1) * dx,
                                                                    np.zeros(FLAT + 1)], axis=1))
    segs = [("平ら", flat),
            ("90° の V 溝(内角)", fs.ledger.groove_profile("vgroove", COLS, angle_deg=90.0)),
            ("平ら", flat),
            ("60° の V 溝", fs.ledger.groove_profile("vgroove", COLS, angle_deg=60.0)),
            ("平ら", flat),
            ("R つきのポケット(床 40 %、壁 65°)",
             fs.ledger.groove_profile("trough", COLS, angle_deg=65.0, floor_frac=0.4)),
            ("平ら", flat)]
    out, col = [], 0
    for name, pr in segs:
        n = len(pr["lengths"])
        out.append({"name": name, "profile": pr, "col0": col, "n": n,
                    "tr": fs.ledger.transport_matrix_radiosity(pr, ALBEDO),
                    "direct": fs.ledger.transport_matrix_radiosity(pr, ALBEDO, n_bounces=0),
                    "px0": OVERSAMPLE * col, "npx": OVERSAMPLE * n})
        col += n
    return out, col


def render(segs, patterns, which="tr"):
    """部品全体の投影パターン(プロジェクタ全幅)→ 区間ごとに切り出して輸送行列で描き、横に並べる。

    溝の縁はどれも z = 0 なので、プロジェクタ座標 u = x cos β は区間の境目で連続 ——
    各区間の切り出しはちょうど OVERSAMPLE × 列数の画素になる。"""
    pats = np.asarray(patterns, float)
    cols = []
    for s in segs:
        crop = pats[:, :, s["px0"]:s["px0"] + s["npx"]]
        cols.append(np.stack(fs.ledger.render_transport(s[which], list(crop), BETA))[:, 0, :])
    return np.concatenate(cols, axis=1)                     # (K, 全列)


def main():
    t0 = time.time()
    c0 = time.process_time()
    segs, ncol = build_part()
    wp = OVERSAMPLE * ncol
    x_mm = np.arange(ncol) / COLS
    grooves = [s for s in segs if s["name"] != "平ら"]
    gmask = np.zeros(ncol, bool)
    for s in grooves:
        gmask[s["col0"]:s["col0"] + s["n"]] = True
    print("部品: 白い Lambert(反射率 %.2f)、幅 1 mm の溝 3 本、カメラ %d 列、プロジェクタ %d 画素、β = %.0f°"
          % (ALBEDO, ncol, wp, BETA))

    # ---- 0. 形態係数(輸送行列の材料)は閉形式に合う ----------------------------- #
    v90 = segs[1]
    F = fs.ledger.form_factors_2d(v90["profile"])
    L = v90["profile"]["lengths"]
    h = COLS // 2
    f12 = float((L[:h, None] * F[:h, h:]).sum() / L[:h].sum())
    check(abs(f12 - (1.0 - math.sin(math.radians(45.0)))) < 1e-12,
          "90° の内角: 左の面から出た光の 29.3 % が右の面に当たる(形態係数 = 1 − sin 45°)", "%.15f" % f12)

    # ---- 1. 直接と大域を分ける ------------------------------------------------ #
    print("\n[1] 直接光と大域光(相互反射)を分ける —— 溝に平行な 2 値の縞を 8 回ずらす")
    white = np.ones((1, 1, wp))
    full = render(segs, white)[0]
    direct = render(segs, white, "direct")[0]
    glob = full - direct
    period = 8
    pats = fs.ledger.high_frequency_patterns((1, wp), period, fill=0.5)
    shots = render(segs, pats)
    sep = fs.ledger.separate_direct_global([r[None, :] for r in shots], fill=0.5)
    sd, sg = sep["direct"][0], sep["global"][0]
    e_d = float(np.sqrt(np.mean((sd - direct)[gmask] ** 2)) / direct[gmask].mean())
    e_g = float(np.sqrt(np.mean((sg - glob)[gmask] ** 2)) / glob[gmask].mean())
    for s in grooves:
        sl = slice(s["col0"], s["col0"] + s["n"])
        print("  %-28s 大域 / 直接: 平均 %.2f、最大 %.2f(底の近く)"
              % (s["name"], (glob[sl] / direct[sl]).mean(), (glob[sl] / direct[sl]).max()))
    check(e_d < 0.03 and e_g < 0.08, "分離した直接・大域が輸送行列の真値と合う(周期 %d px、溝の中の RMS / 平均)" % period,
          "直接 %.2f %%、大域 %.2f %%" % (100 * e_d, 100 * e_g))
    flat_g = float(np.abs(sg[~gmask]).max() / direct[~gmask].mean())
    check(flat_g < 1e-9, "平らな上面に大域光は無い(分離した大域 / 直接)", "%.1e" % flat_g)
    sl90 = slice(v90["col0"], v90["col0"] + v90["n"])
    ratio_max = float((glob[sl90] / direct[sl90]).max())
    check(ratio_max > 1.0, "白い 90° の内角の底では、相互反射が直接光より明るい", "大域 / 直接 最大 %.2f" % ratio_max)
    periods = [128, 64, 32, 16, 8, 4]
    sep_curve = []
    for p in periods:
        r = render(segs, fs.ledger.high_frequency_patterns((1, wp), p))
        q = fs.ledger.separate_direct_global([v[None, :] for v in r])
        sep_curve.append((float(np.sqrt(np.mean((q["direct"][0] - direct)[gmask] ** 2)) / direct[gmask].mean()),
                          float(np.sqrt(np.mean((q["global"][0] - glob)[gmask] ** 2)) / glob[gmask].mean())))
    print("  周期 [px] と分離の誤差(直接 / 大域、溝の中):",
          ", ".join("%d: %.1f/%.1f %%" % (p, 100 * a, 100 * b) for p, (a, b) in zip(periods, sep_curve)))
    ed = [a for a, _ in sep_curve]
    check(all(b < a for a, b in zip(ed[:5], ed[1:5])) and ed[5] > 5 * ed[4],
          "縞を細かくすると分離が良くなり、画素の足跡より細いと崩れる(大域が縞より滑らか、が前提)",
          "128 px: %.1f %% → 8 px: %.1f %%、4 px: %.0f %%" % (100 * ed[0], 100 * ed[4], 100 * ed[5]))

    # ---- 2. 縞の位相の誤差を予測する ------------------------------------------ #
    print("\n[2] 縞の位相の誤差を、撮る前に予測する(視野に縞 1 本の 4 ステップ位相シフト)")
    um_per_rad = lambda p: p * (math.cos(math.radians(BETA)) / (OVERSAMPLE * COLS)) / (2 * np.pi) \
        / math.sin(math.radians(BETA)) * 1000.0           # 位相 1 rad → 高さ [µm]
    low = fs.ledger.high_frequency_patterns((1, wp), float(wp), kind="sinusoid")
    ph = fringe.wrapped_phase(render(segs, low)[:, None, :])[0]
    ph_d = fringe.wrapped_phase(render(segs, low, "direct")[:, None, :])[0]
    meas = _wrap(ph - ph_d)
    pred = np.zeros(ncol)
    bound = np.zeros(ncol)
    for s in segs:
        r = fs.ledger.predict_fringe_phase_error(s["tr"], float(wp), BETA, projector_width=s["npx"])
        pred[s["col0"]:s["col0"] + s["n"]] = r["bias"]
        # 2 つのフェーザの和の閉形式: 位相の誤差は、大域 / 直接の振幅比 r で asin(r) を超えない
        two = fs.ledger.fringe_multipath_phase_error(r["direct_amplitude"], r["direct_phase"],
                                                     r["global_amplitude"], r["global_phase"])
        bound[s["col0"]:s["col0"] + s["n"]] = two["worst_case"]
    gap = float(np.abs(_wrap(pred - meas)).max())
    check(gap < 1e-9, "予測(フェーザ和の閉形式)= 描いた縞を wrapped_phase で復号した誤差(全画素)", "最大の差 %.1e rad" % gap)
    check((np.abs(meas) <= bound + 1e-12).all(), "誤差は振幅比で決まる上限 asin(大域 / 直接) を超えない(全画素)",
          "上限に対する最大の比 %.2f" % float(np.max(np.abs(meas)[bound > 0] / bound[bound > 0])))
    h_conv = -meas * um_per_rad(float(wp))
    for s in grooves:
        sl = slice(s["col0"], s["col0"] + s["n"])
        print("  %-28s 高さ誤差 RMS %6.1f µm、最大 %6.1f µm"
              % (s["name"], np.sqrt(np.mean(h_conv[sl] ** 2)), np.abs(h_conv[sl]).max()))
    rms90 = float(np.sqrt(np.mean(h_conv[sl90] ** 2)))
    check(rms90 > 100.0, "白い Lambert の 90° の内角(深さ 0.5 mm、視野 4 mm に縞 1 本)でも高さが数百 µm 外れる",
          "RMS %.1f µm" % rms90)
    # 従来の 2 段の時間的位相接続(縞 1 本で次数を決め、16 px の縞で精度を出す)
    hi = fs.ledger.high_frequency_patterns((1, wp), 16.0, kind="sinusoid")
    ph16 = fringe.wrapped_phase(render(segs, hi)[:, None, :])[0]
    ph16_d = fringe.wrapped_phase(render(segs, hi, "direct")[:, None, :])[0]
    u_low = np.mod(ph, 2 * np.pi) / (2 * np.pi) * wp
    u16 = np.mod(ph16, 2 * np.pi) / (2 * np.pi) * 16.0
    u_two = u16 + np.round((u_low - u16) / 16.0) * 16.0
    u_low_d = np.mod(ph_d, 2 * np.pi) / (2 * np.pi) * wp
    u16_d = np.mod(ph16_d, 2 * np.pi) / (2 * np.pi) * 16.0
    u_two_d = u16_d + np.round((u_low_d - u16_d) / 16.0) * 16.0
    jumps = int((np.abs(u_two - u_two_d) > 8.0).sum())
    pitch_mm = math.cos(math.radians(BETA)) / (OVERSAMPLE * COLS)
    h_two = -(u_two - u_two_d) * pitch_mm / math.sin(math.radians(BETA)) * 1000.0
    steps = np.round(np.abs(u_two - u_two_d) / 16.0)[gmask]
    check(jumps > 0, "従来の 2 段の位相接続(縞 1 本 → 16 px)でも、縞 1 本の誤差が半周期 8 px を超えた画素で次数がずれる",
          "%d / %d 画素、ずれは最大 %d 段(1 段 = %.0f µm)"
          % (jumps, int(gmask.sum()), int(steps.max()), 16 * pitch_mm / math.sin(math.radians(BETA)) * 1000))

    # ---- 3. マイクロ位相シフト ------------------------------------------------- #
    print("\n[3] マイクロ位相シフト(周期 %s px、各 4 枚)に切り替える" % "/".join("%g" % p for p in MICRO))
    mp = fs.ledger.high_frequency_patterns((1, wp), list(MICRO), kind="sinusoid")
    imgs = render(segs, mp)
    m = fs.ledger.micro_phase_decode([r[None, :] for r in imgs], MICRO)
    md = fs.ledger.micro_phase_decode([r[None, :] for r in render(segs, mp, "direct")], MICRO)
    du = m["coordinate"][0] - md["coordinate"][0]
    h_micro = -du * (2 * np.pi / wp) * um_per_rad(float(wp))
    rows = []
    for s in grooves:
        sl = slice(s["col0"], s["col0"] + s["n"])
        a, b = np.sqrt(np.mean(h_conv[sl] ** 2)), np.sqrt(np.mean(h_micro[sl] ** 2))
        c2 = np.sqrt(np.mean(h_two[sl] ** 2))
        rows.append((s["name"], a, np.abs(h_conv[sl]).max(), c2, b, np.abs(h_micro[sl]).max()))
        print("  %-28s 縞 1 本 RMS %6.1f µm / 2 段 %6.1f µm → マイクロ %5.2f µm" % (s["name"], a, c2, b))
    tot_c = float(np.sqrt(np.mean(h_conv[gmask] ** 2)))
    tot_m = float(np.sqrt(np.mean(h_micro[gmask] ** 2)))
    check(m["synthetic_period"] >= wp, "うなりの合成周期が視野を覆う(次数が一意)", "%.0f px ≥ %d px" % (m["synthetic_period"], wp))
    tot_2 = float(np.sqrt(np.mean(h_two[gmask] ** 2)))
    check(tot_m < tot_c / 30.0 and tot_m < tot_2 / 10.0,
          "マイクロ位相シフトで高さ誤差が 1 桁以上落ちる(溝 3 本の RMS)",
          "縞 1 本 %.1f µm / 2 段 %.1f µm → %.2f µm" % (tot_c, tot_2, tot_m))
    worst_micro = float(np.abs(h_micro[gmask]).max())
    print("  残る最大 %.1f µm は V 溝の頂点の数画素: 頂点のすぐ隣のパッチからの光は縞の位相が近く、"
          "どれだけ細かい縞でも平均されない(正直な限界)" % worst_micro)
    # 周期と誤差(予測の閉形式で掃引)
    sweep = [float(wp), 640.0, 256.0, 128.0, 64.0, 32.0, 16.0, 8.0]
    curves = {s["name"]: [] for s in grooves}
    for p in sweep:
        for s in grooves:
            r = fs.ledger.predict_fringe_phase_error(s["tr"], p, BETA, projector_width=s["npx"])
            curves[s["name"]].append(float(np.sqrt(np.mean(r["height_error"] ** 2))) * 1000.0)
    c90 = curves[v90["name"]]
    check(all(b < a for a, b in zip(c90, c90[1:])), "周期を細かくするほど誤差が減る(90° の内角、予測)",
          " / ".join("%g px: %.2f µm" % (p, c) for p, c in zip(sweep, c90)))

    # ---- 4. ToF の部屋の隅 ------------------------------------------------------ #
    print("\n[4] ToF でも同じ: 部屋の隅(幅 4 m の 90° の角、白い壁 0.8)を 20 MHz の連続波 ToF で")
    room = fs.ledger.groove_profile("vgroove", 200, width=4.0, angle_deg=90.0)
    rt = fs.ledger.transport_matrix_radiosity(room, 0.8)
    cam = np.array([0.0, 0.6])
    tof = fs.ledger.tof_transport_depth(rt, cam, 20e6)
    c = room["centers"]
    dirs = (c - cam) / np.linalg.norm(c - cam, axis=1)[:, None]
    seen = cam + dirs * (tof["true_depth"] + tof["bias"])[:, None]
    mid = len(c) // 2
    print("  距離のバイアス: 隅 %+.0f mm、壁の中ほど %+.0f mm、最大 %+.0f mm(大域 / 直接 最大 %.2f)"
          % (1000 * tof["bias"][mid], 1000 * tof["bias"][mid // 2], 1000 * tof["bias"].max(), tof["ratio"].max()))
    check((tof["bias"] > 0).mean() > 0.9, "相互反射の経路は長いので、ToF は壁を遠くに見る(9 割以上の画素で正)",
          "正の画素 %.0f %%" % (100 * (tof["bias"] > 0).mean()))
    two = fs.ledger.tof_multipath_phase(np.array([[1.0], [0.3]]) * np.ones((2, 361)),
                                        np.stack([np.full(361, 4.0), 4.0 + np.linspace(0, 1, 361) * 299792458.0 / 20e6]),
                                        20e6)
    check(abs(np.abs(two["bias"]).max() - math.asin(0.3) * 299792458.0 / (4 * np.pi * 20e6)) < 1e-3,
          "2 経路の最悪のバイアス = asin(r)·c/(4πf)(r = 0.3)", "%.3f m" % np.abs(two["bias"]).max())

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    # ★2026-10-15: 壁時計は CI の並列のシャードで同じ機械の他のテストの負荷まで数える
    #   (poc_phase_measuring_deflectometry がこれで赤になった)。この門が抑えたいのはこの PoC 自身の計算量なので、プロセスの CPU 時間
    #   (time.process_time)で測り、壁時計は併記する。
    #   ★この PoC だけは CPU 時間が壁時計を大きく上回る(手元 24 スレッドで CPU 10〜13 秒・壁時計 0.6〜0.7 秒、
    #   OMP/OPENBLAS/MKL_NUM_THREADS=1 では CPU・壁時計とも 0.1 秒未満)。計算そのものは小さく、差は BLAS の
    #   スレッドの空回り(待ちの spin)で、コア数に比例して増える。60 秒の上限は手元の 4.7 倍で、CI の走者(4 コア)
    #   では空回りがさらに小さいので据え置く。上限に近づいたら、計算が増えたのか空回りかをスレッド 1 で切り分ける。
    check(cpu < 60.0, "所要時間(CI の上限に余裕を残す)", "CPU %.1f 秒(壁時計 %.1f 秒)" % (cpu, elapsed))

    if figs.enabled():
        _figures(segs, ncol, x_mm, gmask, pats, shots, full, direct, glob, sd, sg, periods, sep_curve,
                 meas, pred, h_conv, h_two, h_micro, sweep, curves, rows, room, cam, seen, tof)
    assert not figs.errors(), figs.errors()

    bad = [ck for ck in CHECKS if not ck[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


def _img(row):
    return np.repeat(np.asarray(row, float)[None, :], ROWS, axis=0)


def _figures(segs, ncol, x_mm, gmask, pats, shots, full, direct, glob, sd, sg, periods, sep_curve,
             meas, pred, h_conv, h_two, h_micro, sweep, curves, rows, room, cam, seen, tof):
    # 断面(部品の形)
    xs, zs = [], []
    for s in segs:
        v = s["profile"]["vertices"]
        x0 = s["col0"] / COLS - v[0, 0]
        xs.append(v[:, 0] + x0)
        zs.append(v[:, 1])
    xs, zs = np.concatenate(xs), np.concatenate(zs)
    figs.save_plot("part", [("断面", xs, zs)], xlabel="x [mm]", ylabel="z [mm]",
                   title="白い部品の断面: 90° の内角・60° の V 溝・R つきのポケット",
                   colors=["neutral"], size=(760, 260), aspect="equal",
                   caption="反射率 0.85 の Lambert 面。光沢も金属も無い。カメラは真上、プロジェクタは 20° 傾けて縞を溝に平行に投影。")
    top = max(full.max(), 1e-12)
    figs.save_grid("direct_global",
                   [_img(full), _img(sd), _img(sg), _img(glob / np.maximum(direct, 1e-12))],
                   ["全点灯で撮った像", "分離した直接光(L_max − L_min)", "分離した大域光(2 L_min)= 相互反射",
                    "大域 / 直接(真値)"],
                   title="白い溝の中だけが、自分の光で光っている", ncols=2,
                   gray=[True, True, True, False], vrange=[(0, top), (0, top), (0, top), (0.0, 1.5)],
                   caption="縞を 8 回ずらした 8 枚の画素ごとの最大と最小から分けた(Nayar ら 2006)。平らな上面に大域光は無く、"
                           "V 溝の底では相互反射が直接光より明るい。60° の溝の片面に出る細い縦縞は、縞の周期と画素の足跡の"
                           "ずれが残す分離の誤差(真値との差は溝の中で直接 2.2 %、大域 6.3 %)。")
    frames = [_img(s / top) for s in shots]
    figs.save_gif("stripes", frames, fps=4.0,
                  caption="縞をずらしながら撮った 8 枚。縞が当たっていない画素も、溝の中では向かいの面からの光で暗くならない。")
    figs.save_plot("separation_vs_period",
                   [("直接光の誤差", np.asarray(periods, float), 100 * np.array([a for a, _ in sep_curve])),
                    ("大域光の誤差", np.asarray(periods, float), 100 * np.array([b for _, b in sep_curve]))],
                   xlabel="縞の周期 [プロジェクタ画素]", ylabel="RMS 誤差 / 平均 [%]",
                   title="縞は細かいほどよい —— 画素の足跡より細くなるまでは",
                   colors=["emphasis", "neutral"], size=(620, 360),
                   caption="分離は「大域光が縞の周期より滑らか」という仮定で成り立つ。周期 4 px は点灯幅 2 px が画素の足跡"
                           "(最大 2.7 px)より狭く、どのずらしでも画素が全部は照らされない。")
    groove_x = x_mm[gmask]
    figs.save_plot("phase_error",
                   [("予測(フェーザ和の閉形式)", x_mm, pred),
                    ("実測(縞を描いて wrapped_phase で復号)", groove_x[::3], meas[gmask][::3])],
                   xlabel="x [mm]", ylabel="位相の誤差 [rad]", title="縞 1 本の位相シフト: 予測と実測が重なる",
                   kinds=["line", "scatter"], colors=["reference", "emphasis"], styles=["dashed", None],
                   size=(760, 340), caption="差は全画素で 1e-12 rad 未満。誤差は撮る前に輸送行列から出せる。")
    figs.save_plot("height_error",
                   [("縞 1 本", x_mm, h_conv), ("2 段の位相接続(縞 1 本 → 16 px)", x_mm, h_two),
                    ("マイクロ位相シフト", x_mm, h_micro)],
                   xlabel="x [mm]", ylabel="高さの誤差 [µm]", title="相互反射の高さ誤差: 縞 1 本 vs マイクロ位相シフト",
                   colors=["wrong", "neutral", "right"], size=(760, 340),
                   caption="白い Lambert の溝でも数百 µm。2 段の位相接続は、縞 1 本の誤差が 16 px の縞の半周期を超えたところで次数を何段も取り違え、ほとんど救えない。周期 16 px 前後の縞 3 組だけにすると、相互反射は縞の位相を"
                           "平均してしまい、誤差は頂点の数画素を除いてほぼ消える。")
    figs.save_grid("error_maps", [_img(h_conv), _img(h_two), _img(h_micro)],
                   ["縞 1 本の高さ誤差 [µm](±300)", "2 段の位相接続 [µm](±300)", "マイクロ位相シフト [µm](±300)"],
                   title="同じ部品、同じ反射率、縞の選び方だけ違う", ncols=1, signed=True,
                   vrange=[(-300.0, 300.0)] * 3,
                   caption="橙と青が高さの誤差の符号。2 段の位相接続は次数を取り違えて階段状に残り、マイクロ位相シフトはほぼ一様に 0。")
    names = list(curves)
    figs.save_plot("error_vs_period",
                   [(n, np.log2(np.asarray(sweep)), np.log10(np.maximum(np.asarray(curves[n]), 1e-6))) for n in names],
                   xlabel="log2(縞の周期 [px])", ylabel="log10(高さ誤差 RMS [µm])",
                   title="縞の周期と相互反射の誤差(予測)", colors=["emphasis", "wrong", "neutral"],
                   size=(620, 380), caption="周期を半分にするたびに誤差は 2〜3 分の 1。60° の溝は 90° より向かいの面がよく見え、誤差が大きい。")
    figs.save_table("numbers", ["溝", "縞 1 本 RMS [µm]", "縞 1 本 最大 [µm]", "2 段 RMS [µm]", "マイクロ RMS [µm]",
                                "マイクロ 最大 [µm]"],
                    [[r[0], "%.1f" % r[1], "%.1f" % r[2], "%.1f" % r[3], "%.2f" % r[4], "%.1f" % r[5]] for r in rows],
                    title="高さの誤差(白い Lambert、反射率 0.85、幅 1 mm)",
                    caption="真値は反射回数 0 の輸送行列で描いた直接光だけの像を同じ方法で復号した座標。")
    v = room["vertices"]
    figs.save_plot("tof_corner",
                   [("壁(真値)", v[:, 0], v[:, 1]), ("ToF が見た壁", seen[:, 0], seen[:, 1]),
                    ("カメラ", np.array([cam[0]]), np.array([cam[1]]))],
                   xlabel="x [m]", ylabel="z [m]", title="部屋の隅は、ToF には丸く遠く見える",
                   kinds=["line", "scatter", "scatter"], colors=["reference", "wrong", "emphasis"],
                   styles=["dashed", None, None], size=(620, 420), aspect="equal",
                   caption="白い壁(0.8)の 90° の隅を 20 MHz の連続波 ToF で。壁どうしの相互反射は経路が長く、"
                           "隅の近くほど距離を長く読む(2-D のモデル)。")
    figs.save_plot("tof_bias", [("距離のバイアス", room["centers"][:, 0], 1000 * tof["bias"])],
                   xlabel="壁の位置 x [m]", ylabel="バイアス [mm]", title="ToF の距離のバイアス(反射ごとの遅れを入れた複素ラジオシティ)",
                   colors=["wrong"], size=(620, 340), caption="正 = 遠く見える。")


if __name__ == "__main__":
    main()
