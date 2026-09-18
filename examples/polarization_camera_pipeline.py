# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""polarization_camera_pipeline — 偏光カメラの生フレームから Stokes / DoLP / Mueller まで。

    py -3.11 examples/polarization_camera_pipeline.py
    FULLSEYE_FIGURE_DIR=out/figs py -3.11 examples/polarization_camera_pipeline.py

【この例が示すこと】
偏光カメラ(Sony IMX250MZR 系)は 2x2 の画素ブロックに 0/45/90/135 度の偏光子を並べた
**モザイク**を 1 枚で出す。それを

1. ``polarization_demosaic`` で 4 枚(0/45/90/135)に戻し(双線形。1 次の場は厳密に戻る)、
2. ``polarization_dolp_map`` / ``polarization_stokes`` で画素ごとの DoLP と Stokes に、
3. ``mueller_from_intensities`` で「既知の生成器・検光子の列で撮った強度」から試料の
   Mueller 行列を最小二乗で取り戻し(設計が S3 を見られなければ**階数を言って断る**)、
4. ``mueller_checks`` で取り戻した行列が**物理的**か(Cloude の coherency 行列が半正定値)、
   純粋か、どれだけ脱偏光しているか(Gil–Bernabeu 指数)を確かめる。

5. ``polarization_demosaic_color`` でカラー偏光センサ(4x4 ブロック)を 4 角度 x RGB に戻す。

【真値】全部合成。Stokes 場を決めて Malus の式で 4 枚を作り、モザイクに畳む。Mueller は
既知の素子の積。だから「戻った値 − 真値」がそのまま誤差になる(assert で落とす)。

EXTEND: 実カメラの生フレームなら ``raw`` を読み込むだけ(``layout`` がセンサと違えば
引数で渡す)。Mueller の設計(PSG/PSA)は ``mueller_element`` の積で自由に組める。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402


def synthetic_scene(h=96, w=128):
    """画素ごとの (S0, DoLP, AoLP) —— 左右で偏光度、上下で方位が変わる。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    s0 = 0.6 + 0.3 * np.sin(2 * np.pi * xx / w) * np.cos(2 * np.pi * yy / h)
    dolp = 0.1 + 0.8 * xx / (w - 1)
    aolp = np.radians(180.0 * yy / (h - 1))
    return s0, dolp, aolp


def to_mosaic(s0, dolp, aolp, layout=fs.POLARIZATION_MOSAIC_LAYOUT):
    """Malus: I(a) = S0/2 (1 + DoLP cos 2(a - AoLP))。4 枚を 2x2 配列に畳む。"""
    frames = {a: 0.5 * s0 * (1.0 + dolp * np.cos(2.0 * (np.radians(a) - aolp)))
              for a in fs.POLARIZATION_SWEEP_ANGLES}
    raw = np.zeros_like(s0)
    for r in range(2):
        for c in range(2):
            raw[r::2, c::2] = frames[layout[r][c]][r::2, c::2]
    return raw, frames


def main() -> int:
    s0, dolp, aolp = synthetic_scene()
    raw, truth = to_mosaic(s0, dolp, aolp)

    # 1. モザイク → 4 枚。滑らかな場なので双線形の誤差は小さい(縁は鏡映)。
    sweep = fs.polarization_demosaic(raw)
    err = max(float(np.abs(sweep[k][2:-2, 2:-2] - truth[a][2:-2, 2:-2]).max())
              for k, a in enumerate(fs.POLARIZATION_SWEEP_ANGLES))
    print("1. demosaic: 4 枚 %s、真値との最大差 %.2e(縁 2 画素を除く)" % (sweep.shape, err))
    assert err < 5e-3, err

    # 2. 画素ごとの DoLP。真値は自分で決めた dolp。
    d = fs.polarization_dolp_map(sweep, max_violation_frac=0.05)
    derr = float(np.abs(d[2:-2, 2:-2] - dolp[2:-2, 2:-2]).max())
    print("2. DoLP 地図: 真値との最大差 %.2e" % derr)
    assert derr < 2e-2, derr
    st = fs.stokes_analyze(fs.polarization_stokes(sweep, max_violation_frac=0.05))
    print("   場全体の Stokes: dolp=%.3f azimuth=%.1f deg" % (st["dolp"], st["azimuth_deg"]))

    # 3. 既知の生成器・検光子の列から Mueller を取り戻す。設計 = 偏光板 6 角 × QWP あり/なし。
    angs = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0]
    gens, anas = [], []
    for a in angs:
        p = fs.mueller_element("polarizer", a)
        gens += [p, fs.mueller_element("quarter_wave", a + 20.0) @ p]
        anas += [p, p @ fs.mueller_element("quarter_wave", a + 20.0)]
    psg = np.array([g for g in gens for _ in anas])
    psa = np.array([a for _ in gens for a in anas])
    m_true = fs.mueller_element("polarizer", 10.0) @ fs.mueller_element("retarder", 30.0, 70.0)
    inten = np.einsum("nj,jk,nk->n", psa[:, 0, :], m_true, psg[:, :, 0])
    rng = np.random.default_rng(0)
    m = fs.mueller_from_intensities(inten + rng.normal(0.0, 1e-4, inten.shape), psg, psa)
    print("3. Mueller の回復: %d 測定、最大誤差 %.2e(雑音 1e-4)" % (len(inten), np.abs(m - m_true).max()))
    assert np.abs(m - m_true).max() < 5e-3
    # 偏光板だけの設計は S3 が見えない → 階数 9 で断る(黙って擬似逆行列を返さない)。
    lin = [fs.mueller_element("polarizer", a) for a in angs]
    psg_l = np.array([g for g in lin for _ in lin]); psa_l = np.array([a for _ in lin for a in lin])
    inten_l = np.einsum("nj,jk,nk->n", psa_l[:, 0, :], m_true, psg_l[:, :, 0])
    try:
        fs.mueller_from_intensities(inten_l, psg_l, psa_l)
    except ValueError as exc:
        print("   偏光板だけの設計は断られる:", str(exc).split(" — ")[0])

    # 4. 物理性。回復した行列・素子・わざと壊した行列。
    # ★雑音つきで回復した行列は coherency の最小固有値が僅かに負に出る(雑音 1e-4 →
    #   -1e-4 程度)。tol は雑音の水準で置く。tol を勘で小さくすると「非物理」に化ける。
    for label, mm in (("回復した M(雑音)", m), ("理想の脱偏光子", fs.mueller_element("depolarizer")),
                      ("M11 > M00(非物理)", np.diag([1.0, 1.5, 1.0, 1.0]))):
        c = fs.mueller_checks(mm, tol=1e-3)
        print("4. %-16s physical=%s pure=%s P_delta=%.3f passive=%s  固有値=%s" % (
            label, c["physical"], c["pure"], c["depolarization_index"], c["passive"],
            ["%.3f" % v for v in c["coherency_eigenvalues"]]))
    assert fs.mueller_checks(m, tol=1e-3)["physical"]
    assert not fs.mueller_checks(np.diag([1.0, 1.5, 1.0, 1.0]))["physical"]

    # 5. カラー偏光センサ(4x4 ブロック): 同じ場を RGB で畳み、4 角度 x RGB に戻す。
    pos = fs.gfx2d._bayer_offsets("RGGB")
    rgb_fields = {a: np.stack([truth[a] * 1.0, truth[a] * 0.8, truth[a] * 0.6], axis=-1)
                  for a in fs.POLARIZATION_SWEEP_ANGLES}
    craw = np.zeros_like(raw)
    for r in range(2):
        for c in range(2):
            ang = fs.POLARIZATION_MOSAIC_LAYOUT[r][c]
            for ch, k in (("R", 0), ("G1", 1), ("G2", 1), ("B", 2)):
                br, bc = pos[ch]
                craw[r + 2 * br::4, c + 2 * bc::4] = rgb_fields[ang][r + 2 * br::4, c + 2 * bc::4, k]
    csweep = fs.polarization_demosaic_color(craw)
    cerr = max(float(np.abs(csweep[k][4:-4, 4:-4] - rgb_fields[a][4:-4, 4:-4]).max())
               for k, a in enumerate(fs.POLARIZATION_SWEEP_ANGLES))
    print("5. カラー偏光(4x4): %s、真値との最大差 %.2e(縁 4 画素を除く)" % (csweep.shape, cerr))
    assert cerr < 1e-2, cerr

    figs.save_grid("polarization_camera_pipeline",
                   [raw, sweep[0], sweep[2], d, dolp, np.degrees(aolp)],
                   ["生モザイク", "I_0(demosaic)", "I_90(demosaic)", "DoLP(推定)", "DoLP(真値)", "AoLP 真値 [deg]"],
                   ncols=3, gray=[True, True, True, False, False, False],
                   caption="偏光カメラのモザイク → 4 枚 → DoLP。真値は Malus で合成")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
