# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye の偏光 op を、外部の 3 実装(pypolar / py-pol / polanalyser)と突き合わせる差分検査。

同じ仕様を別の人が書いた実装は、単一実装のテストが原理的に見つけられない物を出す
(memory: feedback_second_implementation_finds_what_tests_cannot)。ここでは
  * mueller_element(polarizer / retarder / quarter_wave / half_wave / rotator)
  * jones_element(同上)→ Mueller に写して比較
  * stokes_analyze(dop / azimuth / ellipticity)
  * polarization_stokes / polarization_dolp_map(掃引 → Stokes)
  * mueller_from_intensities ↔ polanalyser.calcMueller
  * polarization_demosaic ↔ polanalyser.demosaicing(双線形)
を角度・リターダンスの掃引で比べ、最大差を表にする。差が出たら**規約の違い**(回転の向き・
位相の符号・角度の単位)か**不具合**かを人が切り分ける —— この script は判定しない。
"""
import os
import sys
import numpy as np

sys.path.insert(0, r"C:\dev\projects\imgevolve")
import optics as O          # noqa: E402
import specularity as S     # noqa: E402
import pypolar.mueller as pm  # noqa: E402
import pypolar.jones as pj    # noqa: E402
import polanalyser as pa      # noqa: E402
from py_pol.mueller import Mueller  # noqa: E402
from py_pol.stokes import Stokes    # noqa: E402

rows = []
def rep(name, other, diff, note=""):
    rows.append((name, other, float(diff), note))

angs = np.arange(0.0, 180.0, 7.5)
rets = [30.0, 60.0, 90.0, 120.0, 180.0]

# ---- mueller_element ------------------------------------------------------
for kind, mk in (("polarizer", None), ("quarter_wave", 90.0), ("half_wave", 180.0)):
    d1 = d2 = d3 = 0.0
    for a in angs:
        fs = O.mueller_element(kind, a)
        t = np.radians(a)
        if kind == "polarizer":
            x1 = pm.op_linear_polarizer(t); x2 = pa.polarizer(t)
            x3 = Mueller().diattenuator_perfect(azimuth=t).M
        elif kind == "quarter_wave":
            x1 = pm.op_quarter_wave_plate(t); x2 = pa.qwp(t)
            x3 = Mueller().quarter_waveplate(azimuth=t).M
        else:
            x1 = pm.op_half_wave_plate(t); x2 = pa.hwp(t)
            x3 = Mueller().half_waveplate(azimuth=t).M
        d1 = max(d1, np.abs(fs - x1).max()); d2 = max(d2, np.abs(fs - x2).max())
        d3 = max(d3, np.abs(fs - np.asarray(x3).reshape(4, 4)).max())
    rep("mueller_element(%s)" % kind, "pypolar", d1); rep("mueller_element(%s)" % kind, "polanalyser", d2)
    rep("mueller_element(%s)" % kind, "py-pol", d3)

d1 = d2 = d3 = 0.0
for a in angs:
    for r in rets:
        fs = O.mueller_element("retarder", a, r)
        t, dl = np.radians(a), np.radians(r)
        d1 = max(d1, np.abs(fs - pm.op_retarder(t, dl)).max())
        d2 = max(d2, np.abs(fs - pa.retarder(dl, t)).max())
        d3 = max(d3, np.abs(fs - np.asarray(Mueller().retarder_linear(ret=dl, azimuth=t).M).reshape(4, 4)).max())
rep("mueller_element(retarder)", "pypolar", d1); rep("mueller_element(retarder)", "polanalyser", d2)
rep("mueller_element(retarder)", "py-pol", d3)

d1 = d2 = 0.0
for a in angs:
    fs = O.mueller_element("rotator", a); t = np.radians(a)
    d1 = max(d1, np.abs(fs - pm.op_rotation(t)).max()); d2 = max(d2, np.abs(fs - pa.rotator(t)).max())
rep("mueller_element(rotator)", "pypolar op_rotation", d1); rep("mueller_element(rotator)", "polanalyser rotator", d2)
d2b = max(np.abs(O.mueller_element("rotator", a) - pa.rotator(-np.radians(a))).max() for a in angs)
rep("mueller_element(rotator)", "polanalyser rotator(-theta)", d2b, "符号を反転した場合")

# ---- jones_element → Mueller ----------------------------------------------
for kind in ("polarizer", "quarter_wave", "half_wave", "retarder"):
    d1 = 0.0
    for a in angs:
        for r in ([60.0] if kind == "retarder" else [90.0]):
            j = O.jones_element(kind, a, r); t = np.radians(a)
            if kind == "polarizer":
                x = pj.op_linear_polarizer(t)
            elif kind == "quarter_wave":
                x = pj.op_quarter_wave_plate(t)
            elif kind == "half_wave":
                x = pj.op_half_wave_plate(t)
            else:
                x = pj.op_retarder(t, np.radians(r))
            # Jones は全体位相が自由なので Mueller に写して比べる
            d1 = max(d1, np.abs(pj.jones_op_to_mueller_op(j) - pj.jones_op_to_mueller_op(x)).max())
            d1b = np.abs(pj.jones_op_to_mueller_op(j) - O.mueller_element(kind, a, r)).max()
            d1 = max(d1, d1b)
    rep("jones_element(%s) → Mueller" % kind, "pypolar (+ 自前 mueller_element)", d1)

# ---- stokes_analyze --------------------------------------------------------
d_dop = d_az = d_el = 0.0
rng = np.random.default_rng(1)
for _ in range(200):
    v = rng.normal(size=3); p = rng.uniform(0.0, 1.0)
    s = np.array([1.0, *(p * v / np.linalg.norm(v))])
    a = O.stokes_analyze(s)
    d_dop = max(d_dop, abs(a["dop"] - pm.degree_of_polarization(s)))
    d_az = max(d_az, abs(np.radians(a["azimuth_deg"]) - pm.ellipse_orientation(s)) % np.pi)
    d_el = max(d_el, abs(np.radians(a["ellipticity_deg"]) - pm.ellipticity_angle(s)))
    st = Stokes().from_matrix(s)
    d_dop = max(d_dop, abs(a["dop"] - float(np.ravel(st.parameters.degree_polarization())[0])))
rep("stokes_analyze dop", "pypolar / py-pol", d_dop)
rep("stokes_analyze azimuth", "pypolar ellipse_orientation", min(d_az, abs(np.pi - d_az)))
rep("stokes_analyze ellipticity", "pypolar ellipticity_angle", d_el)

# ---- polarization_stokes / dolp ↔ polanalyser.calcStokes ------------------
h, w = 24, 32
yy, xx = np.mgrid[0:h, 0:w].astype(float)
s0 = 0.6 + 0.2 * np.sin(xx / 5.0); dolp = 0.1 + 0.8 * xx / (w - 1); aolp = np.radians(180.0 * yy / (h - 1))
frames = [0.5 * s0 * (1.0 + dolp * np.cos(2.0 * (np.radians(a) - aolp))) for a in (0.0, 45.0, 90.0, 135.0)]
st_pa = pa.calcStokes(np.stack(frames), np.radians([0.0, 45.0, 90.0, 135.0]))
dolp_pa = pa.cvtStokesToDoLP(st_pa)
dolp_fs = S.polarization_dolp_map(np.stack(frames))
rep("polarization_dolp_map", "polanalyser calcStokes→DoLP", np.abs(dolp_fs - dolp_pa).max())
aolp_pa = pa.cvtStokesToAoLP(st_pa)
sv = S.polarization_stokes(np.stack(frames))
rep("polarization_stokes (場全体 S1/S0)", "polanalyser mean S1/S0", abs(sv[1] / sv[0] - float((st_pa[..., 1] / st_pa[..., 0]).mean())), "場の平均どうし(定義が違えば差が出る)")

# ---- mueller_from_intensities ↔ calcMueller --------------------------------
gens, anas = [], []
for a in np.arange(0.0, 180.0, 30.0):
    p = O.mueller_element("polarizer", a)
    gens += [p, O.mueller_element("quarter_wave", a + 20.0) @ p]; anas += [p, p @ O.mueller_element("quarter_wave", a + 20.0)]
psg = np.array([g for g in gens for _ in anas]); psa = np.array([a for _ in gens for a in anas])
m_true = O.mueller_element("polarizer", 10.0) @ O.mueller_element("retarder", 30.0, 70.0)
inten = np.einsum("nj,jk,nk->n", psa[:, 0, :], m_true, psg[:, :, 0])
m_fs = O.mueller_from_intensities(inten, psg, psa); m_pa = pa.calcMueller(inten, psg, psa)
rep("mueller_from_intensities", "polanalyser calcMueller", np.abs(m_fs - m_pa).max())
rep("mueller_from_intensities", "真値", np.abs(m_fs - m_true).max())

# ---- polarization_demosaic ↔ polanalyser.demosaicing ------------------------
raw = rng.random((64, 80))
fs4 = O.polarization_demosaic(raw)
pa4 = pa.demosaicing((raw * 65535).astype(np.uint16), pa.COLOR_PolarMono)   # 0/45/90/135 の順
pa4 = [x.astype(float) / 65535.0 for x in pa4]
d_in = max(np.abs(fs4[k][2:-2, 2:-2] - pa4[k][2:-2, 2:-2]).max() for k in range(4))
d_all = max(np.abs(fs4[k] - pa4[k]).max() for k in range(4))
rep("polarization_demosaic (内側)", "polanalyser bilinear", d_in, "16 bit 量子化 1.5e-5 を含む")
rep("polarization_demosaic (縁込み)", "polanalyser bilinear", d_all, "縁の扱いが違えばここに出る")

print("%-42s %-34s %10s  %s" % ("fullseye op", "相手", "最大差", "注"))
for n, o, d, note in rows:
    print("%-42s %-34s %10.2e  %s" % (n, o, d, note))
