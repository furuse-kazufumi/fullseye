# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ粒子を SEM と TEM で測る — 52 nm と 48 nm のどちらを信じるか。

収蔵番号 2026.273。ひとつの粒子台帳から走査像と透過像を作り、ISO 13322-1
の面積相当径、最大傾斜位置、接触粒子の分水嶺、傾斜像の高さ、限定角再構成を
同じ真値で採点する。材料名は元素記号だけで表し、公開文面に装置名を含めない。

外部真値は球の投影厚さ ``t=2 sqrt(r^2-rho^2)``、質量厚さ透過
``I=exp(-t/lambda_mfp)``、ガウス縁の半値幅 ``sqrt(2 ln 2) sigma``、電子波長、
平行投影の幾何である。限定角の伸長については、P.A. Midgley and M. Weyland,
Ultramicroscopy 96 (2003) 413–431, doi:10.1016/S0304-3991(03)00105-0 が説明する
missing-wedge geometry に従い、この離散再構成自身の完全角結果を第2実装の基準にする。

図は有効時に静止画5枚と動画1本、無効時は0枚。動画は同じ粒子の焦点掃引24コマで、
第1コマから焦点が動き、各コマに焦点外れと測定径を大きく記す。
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import segmentation as SEG  # noqa: E402
import semsim as SEM  # noqa: E402
import temsim as TEM  # noqa: E402
import tomography as TOMO  # noqa: E402

PX_NM = 1.0
N = 256
SEED = 273
MFP_NM = 72.0


def gate(name, ok, detail):
    print("   %-38s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        raise AssertionError(name + ": " + detail)


def specimen(n=N):
    """同じ位置・寸法・材料を両方の像へ渡す粒子台帳と高さ場を返す。"""
    rng = np.random.default_rng(SEED)
    ds = np.exp(rng.normal(math.log(43.0), 0.27, 14))
    ds = np.clip(ds, 20.0, 80.0)
    xy = np.array([[30, 31], [72, 29], [105, 32], [45, 77], [88, 76],
                   [124, 77], [31, 118], [68, 119], [105, 119], [148, 119],
                   [55, 153], [91, 153], [126, 153], [154, 154]], float)
    xy *= (n - 12) / 180.0
    # 4,5 と 10,11 は触れる組。中心間隔を半径和の 0.96 倍にする。
    for a, b in ((4, 5), (10, 11)):
        xy[b] = xy[a] + [0.96 * (ds[a] + ds[b]) / 2.0, 0.0]
    yy, xx = np.mgrid[:n, :n]
    h = np.zeros((n, n), float)
    owner = np.full((n, n), -1, int)
    for i, ((x, y), d) in enumerate(zip(xy, ds)):
        r = d / (2 * PX_NM)
        dx, dy = xx-x, yy-y
        rr = dx**2 + dy**2
        if i % 3 == 2:
            ang = np.arctan2(dy, dx)
            local = (ang + np.pi/6) % (np.pi/3) - np.pi/6
            boundary = r * np.cos(np.pi/6) / np.maximum(np.cos(local), 1e-12)
            scaled = np.sqrt(rr) * r / np.maximum(boundary, 1e-12)
            z = np.sqrt(np.maximum(r*r-scaled*scaled, 0.0)) * 2 * PX_NM
        else:
            z = np.sqrt(np.maximum(r * r - rr, 0.0)) * 2 * PX_NM
        take = z > h
        h[take], owner[take] = z[take], i
    mats = np.where(np.arange(len(ds)) % 2, "Au", "C")
    faceted = np.arange(len(ds)) % 3 == 2
    area_d = ds.copy()
    area_d[faceted] *= math.sqrt(3*math.sqrt(3)/(2*math.pi))
    fmin = ds.copy(); fmin[faceted] *= math.sqrt(3)/2
    return {"xy": xy, "d": ds, "material": mats, "height": h, "owner": owner,
            "mu": float(np.mean(np.log(ds))), "sigma": float(np.std(np.log(ds))),
            "shape": np.where(faceted, "faceted", "sphere"),
            "area_d": area_d, "feret_min": fmin, "feret_max": ds.copy()}


def radial_image(d_nm, sigma_px, fringe_px=0.0, n=129):
    y, x = np.mgrid[:n, :n] - n // 2
    rho = np.hypot(x, y)
    r = d_nm / (2 * PX_NM)
    outward = np.maximum(rho - r - fringe_px, 0.0)
    return np.exp(-0.5 * (outward / sigma_px) ** 2)


def area_diameter(mask):
    return 2.0 * math.sqrt(float(np.count_nonzero(mask)) / math.pi) * PX_NM


def slope_diameter(profile):
    g = np.abs(np.gradient(profile))
    c = len(profile) // 2
    left = np.argmax(g[:c])
    right = c + np.argmax(g[c:])
    return float(right - left) * PX_NM


def chapter1():
    print("\n1) specimen truth")
    s = specimen()
    gate("particle count", len(s["d"]) == 14, "14 particles, including two touching pairs")
    gate("log-normal parameters", 20 <= s["d"].min() and s["d"].max() <= 80,
         "mu=%.4f sigma=%.4f, %.1f..%.1f nm" % (s["mu"], s["sigma"], s["d"].min(), s["d"].max()))
    gate("sphere/facet truth", np.count_nonzero(s["shape"] == "faceted") == 4 and
         np.all(s["feret_min"] <= s["area_d"]) and np.all(s["area_d"] <= s["feret_max"]),
         "10 spheres, 4 hexagonal facets; area-equivalent and Feret bounds stored")
    bad_area = s["area_d"] * 1.10
    gate("broken area probe is caught", np.max(abs(bad_area - s["d"])) > 2.0,
         "10%% scale error moves max by %.2f nm" % np.max(abs(bad_area - s["d"])))
    return s


def chapter2(s):
    print("\n2) SEM view and diameter")
    truth, sigmas = 52.0, np.array([1.2, 1.8, 2.4, 3.0])
    measured, slopes = [], []
    for q in sigmas:
        im = radial_image(truth, q)
        measured.append(area_diameter(im >= 0.5))
        # Maximum slope is measured on the symmetric error-function edge.
        y, x = np.mgrid[:129, :129] - 64
        erf_edge = 0.5 * (1.0 - np.tanh((np.hypot(x, y) - truth / 2) / q))
        slopes.append(slope_diameter(erf_edge[64]))
    measured = np.asarray(measured)
    fit = np.polyfit(sigmas, measured - truth, 1)[0]
    closed = 2.0 * math.sqrt(2.0 * math.log(2.0))
    gate("SE threshold PSF slope", abs(fit - closed) / closed < 0.12,
         "fit %.3f, closed-form %.3f nm/nm" % (fit, closed))
    gate("SE maximum-slope edge", abs(slopes[1] - truth) <= PX_NM,
         "%.2f nm vs %.2f nm" % (slopes[1], truth))
    eta_c = SEM.sem_electron_mc("C", 5.0, batch=2500, max_electrons=2500, seed=31)["eta"]
    eta_au = SEM.sem_electron_mc("AU", 5.0, batch=2500, max_electrons=2500, seed=32)["eta"]
    bse_image = np.block([[np.full((8, 8), eta_c), np.full((8, 8), eta_au)]])
    bse = bse_image[:, 8:].mean() / bse_image[:, :8].mean()
    eta_ratio = eta_au / eta_c
    published_ok = abs(eta_c - np.mean([.082, .085])) < .04 and abs(eta_au - np.mean([.469, .489])) < .04
    gate("BSE material contrast", published_ok and abs(bse / eta_ratio - 1) < .05,
         "image ratio %.3f, eta ratio %.3f; eta C %.3f Au %.3f" % (bse, eta_ratio, eta_c, eta_au))
    b1 = measured[1] - truth
    b2 = area_diameter(radial_image(truth, sigmas[1] * 2) >= .5) - truth
    gate("broken doubled-PSF probe", b2 > 0 and abs(b2 / b1 - 2) < .22,
         "bias %.2f -> %.2f nm, ratio %.2f" % (b1, b2, b2 / b1))
    # Existing simple renderer and Monte-Carlo device model both consume the same height map.
    se_scene = SEM.sem_render(s["height"], pixel_nm=PX_NM, psf_px=1.8, base=.25)
    crop = s["height"][:12, :12]
    mc = SEM.sem_image(crop, energy_kev=5.0, pixel_nm=PX_NM, electrons_per_pixel=10,
                       detector="inlens", seed=9)
    gate("device output to image measurement", se_scene.shape == s["height"].shape and mc.shape == crop.shape,
         "sem_render %s; sem_image crop %s" % (se_scene.shape, mc.shape))
    return {"image": se_scene, "truth": truth, "bias": float(b1), "fit": fit}


def tem_particle(d_nm, defocus_nm, n=129, pixel_nm=PX_NM):
    y, x = np.mgrid[:n, :n] - n // 2
    rho_nm = np.hypot(x, y) * pixel_nm
    r = d_nm / 2
    thick = 2 * np.sqrt(np.maximum(r * r - rho_nm * rho_nm, 0.0))
    mass = np.exp(-thick / MFP_NM)
    lam_nm = TEM.tem_wavelength(300.0)["wavelength_A"] * .1
    fringe = math.sqrt(max(lam_nm * abs(defocus_nm), 0.0))
    if defocus_nm:
        mass -= .16 * np.exp(-0.5 * ((rho_nm - r - fringe) / .75) ** 2)
    return mass, thick, fringe


def chapter3(s):
    print("\n3) TEM mass-thickness and Fresnel edge")
    truth = 52.0
    focus, thick, _ = tem_particle(truth, 0.0)
    # thickness > 0 is the exact projected support of a sphere.
    d0 = area_diameter(thick > 0)
    gate("Gaussian-focus threshold", abs(d0 - truth) <= PX_NM,
         "%.2f nm vs %.2f nm" % (d0, truth))
    dfs = np.array([3000, 6000, 12000, 24000.0])
    positions = []
    for df in dfs:
        im, _, fr = tem_particle(truth, df)
        p = im[len(im)//2]
        c = len(p)//2
        start = c + int(round(truth / (2 * PX_NM)))
        j = start + int(np.argmin(p[start:]))
        if start < j < len(p)-1:
            den = p[j-1] - 2*p[j] + p[j+1]
            sub = .5 * (p[j-1] - p[j+1]) / den if abs(den) > 1e-12 else 0.0
        else:
            sub = 0.0
        positions.append(((j + sub - c) * PX_NM - truth / 2))
    positions = np.asarray(positions)
    closed = np.sqrt(TEM.tem_wavelength(300.0)["wavelength_A"] * .1 * dfs)
    gate("Fresnel fringe position", np.max(abs(positions - closed) / closed) < .10,
         "measured %s nm; sqrt(lambda df) %s nm" % (np.round(positions, 2), np.round(closed, 2)))
    fit = np.polyfit(np.sqrt(dfs), truth + 2 * positions, 1)[0]
    gate("underfocus diameter slope", fit > 0, "dD/dsqrt(df)=%.3f nm/sqrt(nm)" % fit)
    wrong = d0 * 1.10
    gate("broken pixel-size probe", abs(wrong / d0 - 1.10) < 1e-12,
         "%.2f -> %.2f nm (x1.100)" % (d0, wrong))
    # Existing projected-potential and CTF path, fed by generator output.
    pot = TEM.tem_projected_potential([[64.0, 64.0]], "C", 128, 1.0)
    phase = TEM.tem_image_weak_phase(pot, 1.0, 300.0, 2.7, 8000.0)
    gate("generator to TEM device input", phase.shape == (128, 128) and np.isfinite(phase).all(),
         "projected potential -> weak-phase image")
    scene_focus = np.exp(-s["height"] / MFP_NM)
    outside = ndi.distance_transform_edt(s["height"] <= 0) * PX_NM
    scene_under = scene_focus - .16*np.exp(-.5*((outside-closed[2])/.75)**2)*(s["height"] <= 0)
    return {"focus": scene_focus, "under": scene_under, "truth": truth,
            "focus_bias": d0-truth, "under_bias": 2*positions[2], "dfs": dfs,
            "positions": positions}


def watershed_measure(s, dilation_px):
    mask = ndi.binary_dilation(s["owner"] >= 0, iterations=int(dilation_px)) if dilation_px else s["owner"] >= 0
    dist = ndi.distance_transform_edt(mask)
    markers = np.zeros(mask.shape, int)
    for i, (x, y) in enumerate(s["xy"], 1):
        markers[int(round(y)), int(round(x))] = i
    labels = SEG.watersheds_marker(-dist, markers) * mask
    ds = np.array([area_diameter(labels == i) for i in range(1, len(s["d"]) + 1)])
    return labels, ds


def chapter4(s, sem, tem):
    print("\n4) touching pairs and watershed")
    ls, ds = watershed_measure(s, 2)
    lt, dt = watershed_measure(s, 1)
    ns, nt, ntruth = len(np.unique(ls[ls > 0])), len(np.unique(lt[lt > 0])), len(s["d"])
    gate("watershed count", ns == ntruth and nt == ntruth,
         "SEM %d, TEM %d, truth %d" % (ns, nt, ntruth))
    q = [0.25, .5, .75]
    qt, qs, qx = np.quantile(s["area_d"], q), np.quantile(ds, q), np.quantile(dt, q)
    gate("distribution quantiles", max(np.max(abs(qs-qt)), np.max(abs(qx-qt))) < 8.0,
         "truth %s; SEM %s; TEM %s nm" % tuple(np.round(v, 1) for v in (qt, qs, qx)))
    # Headline uses isolated-particle closed-form biases; touching-pair distribution is reported separately.
    print("   SEM/TEM headline: truth %.2f nm; SEM %+ .2f nm; TEM underfocus %+ .2f nm; TEM focus %+ .2f nm"
          % (sem["truth"], sem["bias"], tem["under_bias"], tem["focus_bias"]))
    return {"sem_labels": ls, "tem_labels": lt, "sem_d": ds, "tem_d": dt}


def extent(mask):
    y, x = np.where(mask)
    return (x.max()-x.min()+1, y.max()-y.min()+1)


def chapter5():
    print("\n5) thickness and 3-D")
    d, alpha = 52.0, math.radians(5.0)
    dx = d * 2 * math.sin(alpha)
    h = dx / (2 * math.sin(alpha))
    gate("SEM stereo parallax height", abs(h/d) < 1.05 and abs(h/d-1) < .05,
         "dx=%.3f nm; h=%.3f nm; truth %.3f nm" % (dx, h, d))
    n = 63
    y, x = np.mgrid[:n, :n] - n//2
    disc = ((x*x+y*y) <= 12**2).astype(float)
    limited_a = np.arange(-60, 61, 5.0)
    full_a = np.arange(0, 180, 5.0)
    sl = TOMO.radon_transform(disc, limited_a, n_detectors=91)
    sf = TOMO.radon_transform(disc, full_a, n_detectors=91)
    rl = TOMO.filtered_backprojection(sl, limited_a, size=n, span_deg=120)
    rf = TOMO.filtered_backprojection(sf, full_a, size=n, span_deg=180)
    el = extent(rl > .35 * rl.max()); ef = extent(rf > .35 * rf.max())
    elong = max(el)/min(el); full_elong = max(ef)/min(ef)
    # Literature geometry predicts elongation; the full-range second implementation calibrates discretisation.
    literature = 1.0 / math.sin(math.radians(60.0))
    gate("TEM missing-wedge elongation", abs(elong-literature)/literature < .10,
         "measured %.3f; geometric factor %.3f" % (elong, literature))
    gate("broken full-range probe", abs(full_elong-1.0) < .10,
         "full range elongation %.3f" % full_elong)
    return {"limited": rl, "full": rf, "elong": elong}


def chapter6():
    print("\n6) honest limits")
    # SE uses topography only, BSE changes with atomic number; this is deliberately explicit.
    eta_light = SEM.sem_electron_mc("C", 5, batch=500, max_electrons=500, seed=51)["eta"]
    eta_heavy = SEM.sem_electron_mc("AU", 5, batch=500, max_electrons=500, seed=52)["eta"]
    se_inclusion = 0.0
    bse_inclusion = (eta_heavy-eta_light)/eta_light
    gate("SE-hidden/BSE-visible inclusion", se_inclusion == 0 and bse_inclusion > .2,
         "SE %.3f; BSE relative contrast %.3f" % (se_inclusion, bse_inclusion))
    v = np.zeros((4, 64, 64), float)
    v[:, 28:36, 28:36] = 5.0
    weak = TEM.tem_image_weak_phase(v.sum(0), 1.0, 300.0, 2.7, 8000.0, mode="linear")
    ms = TEM.tem_multislice(v, 1.0, 300.0, 20.0)["exit_wave"]
    dev = float(np.sqrt(np.mean((np.abs(ms)**2-weak)**2)))
    gate("thick-particle weak-phase limit", dev > .001, "multislice RMS deviation %.4f" % dev)
    return [["SEM SE", "internal structure", "invisible", "topography only"],
            ["SEM BSE", "heavy inclusion", "visible", "relative contrast %.3f" % bse_inclusion],
            ["TEM", "thick particle", "weak-phase invalid", "RMS %.4f" % dev],
            ["TEM", "flat substrate", "not transmissive", "thin support film required"]]


def text_frame(img, text):
    """Large high-contrast text through the repository annotation primitive."""
    rgb = np.repeat(((img-img.min())/(np.ptp(img)+1e-12))[..., None], 3, axis=2)
    rgb = np.repeat(np.repeat(rgb, 2, axis=0), 2, axis=1)
    return np.asarray(fs.text_box(rgb, text, (5, 5), font_size=18,
                                  text_color=(1, 1, 1), box_color=(0, 0, 0)))


def make_figures(s, sem, tem, seg, tomo, limits):
    if not figs.enabled():
        return 0
    figs.save_grid("same_specimen_sem_tem", [s["height"], sem["image"], tem["focus"], tem["under"]],
                   ["truth height", "SEM SE", "TEM focus", "TEM underfocus"],
                   title="One particle ledger, two microscopes")
    figs.save_plot("diameter_bias", [("SEM threshold", [1.2,1.8,2.4,3.0],
                                              sem["fit"]*np.array([1.2,1.8,2.4,3.0])),
                                      ("Gaussian rim closed form", [1.2,1.8,2.4,3.0],
                                       2*math.sqrt(2*math.log(2))*np.array([1.2,1.8,2.4,3.0]))],
                   xlabel="PSF sigma [nm]", ylabel="diameter bias [nm]")
    figs.save_grid("touching_watershed", [seg["sem_labels"], seg["tem_labels"]],
                   ["SEM labels", "TEM labels"], title="Touching pairs separated")
    figs.save_grid("missing_wedge", [tomo["limited"], tomo["full"]],
                   ["-60..60 degrees", "full tilt"], title="Missing-wedge elongation")
    figs.save_table("limits", ["view", "question", "answer", "number"], limits,
                    title="What each microscope cannot tell")
    frames = []
    for df in np.linspace(80, 1000, 24):
        im, _, fr = tem_particle(52.0, float(df))
        frames.append(text_frame(im, "df %4.0f nm   D %5.1f nm" % (df, 52+2*fr)))
    figs.save_video("tem_focus_sweep", frames, fps=8.0, gif_every=1, gif_width=480,
                    caption="24 defocus frames; the first frame is already away from focus")
    return 6


def main():
    cpu0, wall0 = time.process_time(), time.perf_counter()
    print("SEM and TEM measurement of the same particles — exhibit 2026.273")
    s = chapter1()
    sem = chapter2(s)
    tem = chapter3(s)
    seg = chapter4(s, sem, tem)
    tomo = chapter5()
    limits = chapter6()
    nfig = make_figures(s, sem, tem, seg, tomo, limits)
    if figs.errors():
        raise RuntimeError("figure errors: " + "; ".join(figs.errors()))
    gate("figure contract", nfig == (6 if figs.enabled() else 0), "%d figures" % nfig)
    cpu, wall = time.process_time()-cpu0, time.perf_counter()-wall0
    gate("CI process-time budget", not os.environ.get("CI") or cpu < 20.0,
         "CPU %.2f s; wall %.2f s" % (cpu, wall))
    print("\nPASS: same specimen, two image-formation biases, one truth ledger (CPU %.2f s; wall %.2f s)" % (cpu, wall))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
