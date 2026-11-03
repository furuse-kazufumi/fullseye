"""Optics and active optical sensing recipes (Fullseye's differentiators).

Families: optics (lens design / merit / tolerancing, illumination, polarization and shape-from-polarization,
OCT, indirect ToF, telecentric, spectral radiometry, moire alignment, photoelasticity, diffraction MTF),
acoustics, piv, flyvision, specular, lightfield, photon, astrostack, interferometry, motionmag, rangedoppler.

Every sample is synthetic with a closed-form truth (thick-lens EFL, Wien's law, Malus's law, Fresnel DoLP,
round-trip time of flight, FMCW range / Doppler bins, Airy MTF50 and so on). Several simulators of these
families return ``(value, truth)`` from the OP_GRAPH executor (the ledger wrapper drops the truth, the raw
executor the runner calls does not), so where such an op is the natural first stage the sample calls the
simulator itself and the recipe starts from the value; those ops are listed in ``FAILED_ATTEMPTS``.
"""
from __future__ import annotations

import math

import numpy as np

C_LIGHT = 299_792_458.0


def _rng(variant, salt=0):
    return np.random.default_rng(5000 + 31 * int(variant) + int(salt))


# ---------------------------------------------------------------------------------------------
# optics samples
# ---------------------------------------------------------------------------------------------
def op_singlet(variant):
    """Biconvex singlet (R, -R, t = 5 mm, n = 1.5168); truth = thick-lens EFL (lensmaker)."""
    r = 51.68 if variant == 0 else 80.0
    t, n = 5.0, 1.5168
    surf = [{"R": r, "t": t, "n": n, "ap": 10.0}, {"R": -r, "t": None, "n": 1.0, "ap": 10.0}]
    r1, r2 = r, -r
    power = (n - 1.0) * (1.0 / r1 - 1.0 / r2 + (n - 1.0) * t / (n * r1 * r2))
    efl = 1.0 / power
    bfl = efl * (1.0 - (n - 1.0) * t / (n * r1))
    return {"value": None, "aux": {"surfaces": surf, "efl_target": 60.0 if variant == 0 else 40.0},
            "truth": {"efl": efl, "bfl": bfl, "efl_target": 60.0 if variant == 0 else 40.0}}


def op_airy(variant):
    """Diffraction-limited lens f/N at 0.55 um; truth = MTF50 = 0.4040 / (lambda N) lp/mm."""
    fno = 5.6 if variant == 0 else 8.0
    lam_mm = 0.55e-3
    return {"value": None, "aux": {"f_number": fno},
            "truth": {"mtf50": 0.4040 / (lam_mm * fno), "cutoff": 1.0 / (lam_mm * fno)}}


def op_itof_scene(variant):
    """Depth map with two planes (m); truth = mean depth (beyond the 1.87 m single-frequency ambiguity)."""
    a, b = (2.3, 3.1) if variant == 0 else (1.2, 4.4)
    z = np.full((8, 8), a)
    z[:, 4:] = b
    return {"value": z, "aux": {}, "truth": {"mean_depth": float(z.mean())}}


def op_oct_film(variant):
    """PMMA coating on a glass-like substrate (n = 1.5) 300 um below the reference; truth = thickness um."""
    d = 60.0 if variant == 0 else 95.0
    smp = {"ambient": "air", "surface_um": 300.0,
           "layers": [{"material": "PMMA", "thickness_um": d}], "substrate": 1.5}
    return {"value": None, "aux": {"sample": smp}, "truth": {"thickness_um": d}}


def op_polarizer(variant):
    """Linear polarizer at angle a in front of horizontally polarized light; truth = Malus cos^2(a)."""
    a = 30.0 if variant == 0 else 65.0
    return {"value": None, "aux": {"angle_deg": a, "stokes_in": np.array([1.0, 1.0, 0.0, 0.0])},
            "truth": {"intensity": math.cos(math.radians(a)) ** 2, "azimuth_deg": a}}


def op_sphere_normals(variant, n=32):
    """Normal map of a convex spherical cap of radius R px; truth = mean curvature -1/R (convex < 0)."""
    r = 40.0 if variant == 0 else 25.0
    yy, xx = np.mgrid[0:n, 0:n] - (n - 1) / 2.0
    nx, ny = xx / r, yy / r
    nz = np.sqrt(1.0 - nx ** 2 - ny ** 2)
    return {"value": np.stack([nx, ny, nz], -1), "aux": {}, "truth": {"curvature": -1.0 / r, "radius": r}}


def op_telecentric(variant):
    """Object-side telecentric lens of design magnification m; truth = m (real-ray value within 2 %)."""
    m = -0.5 if variant == 0 else -1.0
    return {"value": None, "aux": {"magnification": m}, "truth": {"magnification": m}}


def op_point_light(variant):
    """Point LED (Lambertian, I0 = 1) at height h above a 100 mm field; truth = E(0) = I0 / h^2."""
    h = 100.0 if variant == 0 else 150.0
    r2 = 2 * 40.0 ** 2                   # corner of the central 80 % box
    return {"value": None, "aux": {"height_mm": h},
            "truth": {"centre": 1.0 / h ** 2, "uniformity": (h * h / (h * h + r2)) ** 2.0}}


def op_blackbody(variant):
    """Blackbody at T; truth = Wien peak 2.8978e6 / T nm."""
    t = 3000.0 if variant == 0 else 5000.0
    return {"value": None, "aux": {"temperature_k": t}, "truth": {"peak_nm": 2.897771955e6 / t}}


def op_moire(variant):
    """Moire alignment mark (mask 2.00 um / wafer 2.04 um gratings); truth = wafer shift in nm."""
    import moirealign
    shift = 120.0 if variant == 0 else -340.0
    ref = moirealign.moire_overlay_image(shape=(64, 512), layout="single", shift_nm=0.0)
    return {"value": None, "aux": {"shift_nm": shift, "ref": ref}, "truth": {"shift_nm": shift}}


def op_retardance(variant):
    """Retardance map from the stress-optic law delta = 2 pi t C (s1 - s2) / lambda; truth = mean delta."""
    t, c, lam = 0.006, 7.0e-11, 550e-9               # 6 mm epoxy, 70 brewster, green light
    smax = 1.5e6 if variant == 0 else 0.9e6           # Pa, ramp 10 % .. 100 % of smax
    ds = np.tile(np.linspace(0.1, 1.0, 32), (24, 1)) * smax
    delta = 2 * np.pi * t * c * ds / lam               # stays below pi/2 (camera4 is unique there)
    axis = 30.0 if variant == 0 else 75.0
    return {"value": delta, "aux": {"axis_deg": axis},
            "truth": {"mean_delta": float(delta.mean()), "axis_deg": axis}}


# ---------------------------------------------------------------------------------------------
# family samples
# ---------------------------------------------------------------------------------------------
_RBIN = C_LIGHT / (2 * 20e12 * 64 / 10e6)   # fmcw_design defaults: c / (2 slope N / fs) = 1.1711 m
_VBIN = 0.0038934 / (2 * 32 * 5e-5)         # lambda / (2 Nc Tc) = 1.2167 m/s


def op_fmcw_target(variant):
    """One FMCW radar target on the range / Doppler bin grid; truth = range m, radial velocity m/s."""
    kr, kv = (10, 2) if variant == 0 else (25, -5)
    return {"value": None, "aux": {"ranges": [kr * _RBIN], "velocities": [kv * _VBIN]},
            "truth": {"range_m": kr * _RBIN, "velocity_ms": kv * _VBIN}}


def op_fmcw_array(variant):
    """FMCW target seen by an 8-element half-wavelength array; truth = direction of arrival (deg)."""
    a = 20.0 if variant == 0 else -35.0
    return {"value": None, "aux": {"angles": [a]}, "truth": {"angle_deg": a}}


def op_tcspc(variant):
    """Single-pixel dTOF target at distance d (m); truth = d."""
    d = 3.0 if variant == 0 else 1.7
    return {"value": None, "aux": {"distance_m": d}, "truth": {"distance_m": d}}


def op_dtof_scene(variant):
    """Flash-lidar depth map with a step (m, < 3.84 m unambiguous at 256 x 100 ps); truth = mean depth."""
    a, b = (1.5, 3.0) if variant == 0 else (0.8, 2.2)
    z = np.full((8, 8), a)
    z[:, 5:] = b
    return {"value": z, "aux": {}, "truth": {"mean_depth": float(z.mean())}}


def op_flat_irradiance(variant):
    """Flat image of level L (relative irradiance); at 100 photons per unit the truth mean = 100 L."""
    lev = 0.3 if variant == 0 else 0.7
    yy, xx = np.mgrid[0:48, 0:48]
    img = np.full((48, 48), lev) + 0.0 * xx
    return {"value": img, "aux": {}, "truth": {"mean_counts": 100.0 * lev}}


def op_csi_point(variant):
    """White-light (coherence scanning) interferometer at one pixel; truth = surface height um."""
    z = 4.3 if variant == 0 else 7.85
    return {"value": None, "aux": {"surface_um": z}, "truth": {"surface_um": z}}


def op_csi_tilt(variant, n=24):
    """Tilted flat z = 2 + s x um on 1 um pixels; truth = tilt atan(s) in degrees."""
    s = 0.15 if variant == 0 else 0.3
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return {"value": 2.0 + s * xx, "aux": {}, "truth": {"tilt_deg": math.degrees(math.atan(s))}}


def op_confocal_point(variant):
    """Chromatic confocal probe on a surface at z um; truth = z."""
    z = 7.0 if variant == 0 else -12.5
    return {"value": None, "aux": {"surface_um": z}, "truth": {"surface_um": z}}


def op_starfield(variant):
    """Synthetic star field (64x64, Gaussian PSF); truth = number of stars and PSF FWHM (px)."""
    import astrostack
    n = 8 if variant == 0 else 14
    fwhm = 3.2 if variant == 0 else 4.5
    img, tr = astrostack.synth_starfield(shape=(64, 64), n_stars=n, fwhm_px=fwhm, flux_min=3000.0,
                                         flux_max=9000.0, seed=2 + variant, margin_px=8.0)
    return {"value": img, "aux": {}, "truth": {"n_stars": n, "n_lo": n - 1, "n_hi": n, "fwhm_px": fwhm}}


def op_sky_frames(variant):
    """N flat-sky frames (sky 100 e-, read noise 5 e- Gaussian); truth = stacked noise 5 / sqrt(N)."""
    nf = 4 if variant == 0 else 16
    g = _rng(variant, 11)
    frames = [100.0 + 5.0 * g.standard_normal((64, 64)) for _ in range(nf)]
    return {"value": frames, "aux": {}, "truth": {"sigma_stack": 5.0 / math.sqrt(nf)}}


def op_mla_raw(variant):
    """Plenoptic (micro-lens array) raw sensor image of a fronto-parallel textured plane at disparity s."""
    import lightfield
    s = 1.0 if variant == 0 else -1.5
    lf, _ = lightfield.lf_synthesize(slopes=[s], shape=[48, 48], seed=3)
    return {"value": lightfield.lf_to_mla(lf), "aux": {}, "truth": {"slope": s}}


def op_rotating_flow(variant, n=24):
    """Solid-body rotation (2, h, w) = (dy, dx) px/frame with two spiked vectors; truth = vorticity -2 w."""
    w = 0.05 if variant == 0 else -0.08
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = (n - 1) / 2.0
    fl = np.stack([w * (xx - c), -w * (yy - c)])
    fl[:, 5, 7] += 3.0
    fl[:, 15, 18] -= 2.5
    return {"value": fl, "aux": {}, "truth": {"vorticity": -2.0 * w}}


def op_uniform_flow(variant, n=16):
    """Uniform PIV displacement (dy, dx) px between frames; 10 um pixels, 1 ms; truth = speed m/s."""
    dy, dx = (1.5, -2.0) if variant == 0 else (0.5, 3.5)
    fl = np.stack([np.full((n, n), dy), np.full((n, n), dx)])
    fl = fl + 1e-3 * _rng(variant, 12).standard_normal(fl.shape)
    return {"value": fl, "aux": {}, "truth": {"speed": math.hypot(dy, dx) * 1e-5 / 1e-3}}


def op_bearing(variant):
    """Rolling bearing with an outer-race defect: impacts at f_d modulating a 2 kHz resonance."""
    f = 107.0 if variant == 0 else 162.0
    return {"value": None, "aux": {"defect_hz": f}, "truth": {"defect_hz": f}}


def op_mic_pair(variant):
    """White noise reaching two microphones 0.2 m apart from angle a (c = 343 m/s); truth = TDOA s."""
    fs, n, d, c = 48000.0, 4096, 0.2, 343.0
    a = 30.0 if variant == 0 else -50.0
    tau = d * math.sin(math.radians(a)) / c
    g = _rng(variant, 13)
    x = g.standard_normal(n)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    y = np.fft.irfft(np.fft.rfft(x) * np.exp(-2j * np.pi * f * tau), n)
    return {"value": x, "aux": {"mic2": y, "rate": fs}, "truth": {"tdoa_s": tau, "angle_deg": a}}


def op_tone(variant):
    """1 kHz tone of amplitude A (84 whole cycles at 48 kHz); truth = Leq 20 log10(A / sqrt 2) dB."""
    a = 1.0 if variant == 0 else 0.25
    fs, n = 48000.0, 4032
    t = np.arange(n) / fs
    return {"value": a * np.sin(2 * np.pi * 1000.0 * t), "aux": {"rate": fs},
            "truth": {"leq_db": 20 * math.log10(a / math.sqrt(2.0))}}


def op_fly_drum(variant):
    """Fly eye (127 ommatidia) inside a rotating drum of 30 deg stripes; truth = yaw sign (-pattern)."""
    import flyvision
    w = 0.4 if variant == 0 else -0.4
    lat = flyvision.fly_hex_lattice(radius=6, dphi_deg=5.0)
    dt = 0.01
    az = np.asarray(lat["az_rad"])
    t = np.arange(150) * dt
    movie = 1.0 + 0.3 * np.sin(2 * np.pi / np.deg2rad(30.0) * (az[None, :] - w * t[:, None]))
    lo, hi = (-1.0, -1e-5) if w > 0 else (1e-5, 1.0)
    return {"value": movie, "aux": {"lat": lat, "dt": dt}, "truth": {"yaw_lo": lo, "yaw_hi": hi}}


def op_fly_pair(variant):
    """Two adjacent ommatidia seeing a drifting grating with phase lag psi; truth = HR correlator mean."""
    dt, tau, f, di = 0.001, 0.05, 3.0, 0.5
    psi = math.pi / 3 if variant == 0 else -math.pi / 2
    t = np.arange(4096) * dt
    a = 1.0 + di * np.sin(2 * np.pi * f * t)
    b = 1.0 + di * np.sin(2 * np.pi * f * t - psi)
    wt = 2 * np.pi * f * tau
    rbar = di ** 2 / 2.0 * math.sin(psi) * wt / (1 + wt ** 2)
    return {"value": a, "aux": {"b": b}, "truth": {"rbar": rbar}}


def op_looming(variant):
    """Sphere (r = 0.1 m) approaching at v from 10 m; subtense 2 asin(r/d); truth = tau at sample 100."""
    v = 5.0 if variant == 0 else 2.0
    dt = 0.01
    t = np.arange(150) * dt
    d = 10.0 - v * t
    theta = 2 * np.arcsin(0.1 / d)
    return {"value": theta, "aux": {"dt": dt}, "truth": {"tau100": float(d[100] / v)}}


def op_glossy_dome(variant, n=32):
    """Glossy dome normal map; the dichromatic render uses specular weight ks; truth = ks."""
    yy, xx = (np.mgrid[0:n, 0:n] / (n - 1)) * 2 - 1
    nz = np.sqrt(np.clip(1 - 0.5 * (xx ** 2 + yy ** 2), 0.05, 1))
    nm = np.stack([0.5 * xx, 0.5 * yy, nz], -1)
    nm /= np.linalg.norm(nm, axis=-1, keepdims=True)
    if variant == 1:
        nm = nm[::-1].copy()
    ks = 0.25 if variant == 0 else 0.6
    return {"value": nm, "aux": {"ks": ks}, "truth": {"ks": ks}}


def _fresnel_dolp(theta, n):
    st, ct = np.sin(theta), np.cos(theta)
    root = np.sqrt(n * n - st * st)
    rs = ((ct - root) / (ct + root)) ** 2
    rp = ((n * n * ct - root) / (n * n * ct + root)) ** 2
    return (rs - rp) / (rs + rp)


def op_tilted_dielectric(variant, n=24):
    """Cylinder-like dielectric (n = 1.5) with zenith 20..50 deg (or 35..75) across x; truth = median DoLP."""
    lo, hi = (20.0, 50.0) if variant == 0 else (35.0, 75.0)
    th = np.radians(np.tile(np.linspace(lo, hi, n), (n, 1)))
    nm = np.stack([np.sin(th), np.zeros_like(th), np.cos(th)], -1)
    return {"value": nm, "aux": {}, "truth": {"dolp_median": float(np.median(_fresnel_dolp(th, 1.5)))}}


def op_vibration(variant):
    """Textured patch translating sinusoidally (amplitude a px, f Hz at 32 fps); truth = a."""
    a, f = (0.5, 4.0) if variant == 0 else (0.3, 8.0)
    return {"value": None, "aux": {"amp": a, "freq": f}, "truth": {"amp": a, "freq": f}}


def op_vibration_video(variant):
    """Video of a patch vibrating at 4 Hz with amplitude a px (32 frames, 32 fps)."""
    import motionmag
    a = 0.2 if variant == 0 else 0.1
    v = motionmag.synthesize_translation(shape=(32, 32), frames=32, amplitude_px=a, frequency_hz=4.0, fps=32.0)
    return {"value": v, "aux": {}, "truth": {"amp": a}}


SAMPLES = {
    "op_singlet": op_singlet, "op_airy": op_airy, "op_itof_scene": op_itof_scene, "op_oct_film": op_oct_film,
    "op_polarizer": op_polarizer, "op_sphere_normals": op_sphere_normals, "op_telecentric": op_telecentric,
    "op_point_light": op_point_light, "op_blackbody": op_blackbody, "op_moire": op_moire,
    "op_retardance": op_retardance, "op_fmcw_target": op_fmcw_target, "op_fmcw_array": op_fmcw_array,
    "op_tcspc": op_tcspc, "op_dtof_scene": op_dtof_scene, "op_flat_irradiance": op_flat_irradiance,
    "op_csi_point": op_csi_point, "op_csi_tilt": op_csi_tilt, "op_confocal_point": op_confocal_point,
    "op_starfield": op_starfield, "op_sky_frames": op_sky_frames, "op_mla_raw": op_mla_raw,
    "op_rotating_flow": op_rotating_flow, "op_uniform_flow": op_uniform_flow, "op_bearing": op_bearing,
    "op_mic_pair": op_mic_pair, "op_tone": op_tone, "op_fly_drum": op_fly_drum, "op_fly_pair": op_fly_pair,
    "op_looming": op_looming, "op_glossy_dome": op_glossy_dome, "op_tilted_dielectric": op_tilted_dielectric,
    "op_vibration": op_vibration, "op_vibration_video": op_vibration_video,
}

_SLOPES = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]

RECIPES = [
    # ------------------------------------------------------------------ optics: lens design
    {"name": "Optics — focal length of a biconvex singlet lens (paraxial EFL / BFL)", "family": "optics",
     "task": "design", "task_class": "optics", "halcon": None, "input_sort": None, "sample": "op_singlet",
     "stages": [{"op": "lens_system", "kw": {"surfaces": "$aux.surfaces"}},
                {"op": "paraxial_trace"}],
     "expect": [{"get": ["efl"], "approx": "efl", "rtol": 1e-6},
                {"get": ["bfl"], "approx": "bfl", "rtol": 1e-6}],
     "note": "lens design: build a sequential prescription (radii mm, thickness mm, glass index) and trace the "
             "paraxial marginal / chief rays; effective focal length and back focal length in mm match the "
             "thick-lens lensmaker equation 1/f = (n-1)(1/R1 - 1/R2 + (n-1)t/(n R1 R2))"},
    {"name": "Optics — optimize a singlet to a target focal length (merit function, damped least squares)",
     "family": "optics", "task": "design", "task_class": "optics", "halcon": None, "input_sort": None,
     "sample": "op_singlet",
     "stages": [{"op": "lens_system", "kw": {"surfaces": "$aux.surfaces"}},
                {"op": "merit_default", "kw": {"rings": 2, "efl_target": "$aux.efl_target", "efl_weight": 100.0}},
                {"op": "optimize_lens_operands", "args": ["$s1"],
                 "kw": {"operands": "$s2", "variables": ["c0", "c1"], "iterations": 30}}],
     "expect": [{"get": ["table_after", "table", 1, "value"], "approx": "efl_target", "atol": 0.3}],
     "note": "lens optimization: default merit function (RMS spot transverse aberration + EFFL operand with a "
             "target focal length in mm, weight 100) minimized by Levenberg-Marquardt over both curvatures; the "
             "optimized EFFL row lands on the target (60 mm or 40 mm) within 0.3 mm"},
    {"name": "Optics — tolerance sensitivity of a singlet (which radius drives the RMS spot)",
     "family": "optics", "task": "tolerance", "task_class": "optics", "halcon": None, "input_sort": None,
     "sample": "op_singlet",
     "stages": [{"op": "lens_system", "kw": {"surfaces": "$aux.surfaces"}},
                {"op": "tolerance_table", "kw": {"defaults": {"radius_pct": 0.01}}},
                {"op": "tolerance_criteria", "kw": {"rms_spot": {}, "rings": 2}},
                {"op": "tolerance_sensitivity", "args": ["$s1", "$s2", "$s3"]}],
     "expect": [{"get": ["drivers", "@len"], "between": [1, 50]},
                {"get": ["nominal", "rms_spot"], "between": [1e-4, 5.0]}],
     "note": "lens tolerancing: a tolerance table (radius +-1 %), a criterion (RMS spot radius, mm) and the "
             "sensitivity analysis that ranks the tolerance drivers by their contribution to the RSS degradation; "
             "no closed form, the gate only checks the drivers exist and the nominal spot is physical"},
    {"name": "Optics — diffraction-limited MTF50 of an f-number (Airy PSF to MTF)", "family": "optics",
     "task": "measure", "task_class": "optics", "halcon": None, "input_sort": None, "sample": "op_airy",
     "stages": [{"op": "airy_pattern", "kw": {"size": 128, "wavelength_um": 0.55, "f_number": "$aux.f_number",
                                              "pixel_pitch_um": 0.5}},
                {"op": "psf_to_mtf", "kw": {"pixel_pitch_um": 0.5}},
                {"op": "mtf50"}],
     "expect": [{"get": [], "approx": "mtf50", "rtol": 0.03}],
     "note": "image quality: Airy point spread function of a perfect lens (lambda 0.55 um, f/5.6 or f/8, sampled "
             "at 0.5 um), its MTF and the spatial frequency where contrast drops to 50 % in lp/mm; matches the "
             "closed form 0.404 / (lambda N) of the incoherent diffraction MTF within 3 % (sampling)"},
    # ------------------------------------------------------------------ optics: active sensing
    {"name": "Sense — indirect ToF depth with dual-frequency phase unwrapping", "family": "optics",
     "task": "sense", "task_class": "sensing", "halcon": "3D Reconstruction", "input_sort": "depth",
     "sample": "op_itof_scene",
     "stages": [{"op": "itof_capture", "kw": {"frequencies_hz": [80e6, 100e6]}},
                {"op": "itof_phase_amplitude"},
                {"op": "itof_unwrap_multifreq"}],
     "expect": [{"get": ["depth", "@mean"], "approx": "mean_depth", "atol": 0.03}],
     "note": "time-of-flight camera (CW-iToF): simulate 4-phase correlation samples at 80 and 100 MHz with shot "
             "noise, recover phase / amplitude, then unwrap with the two frequencies (ML) to metric depth in m; "
             "the scene lies beyond the 1.87 m single-frequency ambiguity range and is recovered to 3 cm"},
    {"name": "Measure — coating thickness by spectral-domain OCT", "family": "optics", "task": "measure",
     "task_class": "measurement", "halcon": None, "input_sort": None, "sample": "op_oct_film",
     "stages": [{"op": "oct_interferogram", "kw": {"sample": "$aux.sample", "grid": "k", "seed": 1}},
                {"op": "oct_ascan", "kw": {"zero_pad": 4}},
                {"op": "oct_layer_thickness", "kw": {"n_group": "PMMA", "n_interfaces": 2,
                                                     "z_range_um": [200.0, 500.0]}}],
     "expect": [{"get": ["thickness_um", 0], "approx": "thickness_um", "atol": 0.6}],
     "note": "optical coherence tomography for industrial film / paint layers: simulate the 840 nm SD-OCT "
             "interference spectrum of a PMMA layer, FFT to an A-scan, pick the two interface peaks and divide "
             "the optical thickness by the PMMA group index; physical thickness in um within 0.6 um"},
    {"name": "Optics — Malus's law through a linear polarizer (Mueller calculus)", "family": "optics",
     "task": "simulate", "task_class": "optics", "halcon": None, "input_sort": None, "sample": "op_polarizer",
     "stages": [{"op": "mueller_element", "kw": {"kind": "polarizer", "angle_deg": "$aux.angle_deg"}},
                {"op": "mueller_apply", "args": ["$prev", "$aux.stokes_in"]},
                {"op": "stokes_analyze"}],
     "expect": [{"get": ["intensity"], "approx": "intensity", "atol": 1e-9},
                {"get": ["azimuth_deg"], "approx": "azimuth_deg", "atol": 1e-6}],
     "note": "polarization optics: Mueller matrix of an ideal linear polarizer at angle a applied to horizontally "
             "polarized light (Stokes 1,1,0,0); transmitted intensity cos^2 a and output azimuth a — the "
             "check of a polarizer / analyzer setup for glare suppression"},
    {"name": "3D — shape from polarization of a glossy dome (curvature from polarization images)",
     "family": "optics", "task": "3d", "task_class": "3d", "halcon": "3D Reconstruction",
     "input_sort": "normalmap", "sample": "op_sphere_normals",
     "stages": [{"op": "sfp_render", "kw": {"refractive_index": 1.5}},
                {"op": "sfp_normals", "kw": {"refractive_index": 1.5, "model": "specular"}},
                {"op": "sfp_disambiguate", "kw": {"prior": "convex"}},
                {"op": "slope_to_curvature", "kw": {"spacing": 1.0}}],
     "expect": [{"get": ["@median"], "approx": "curvature", "rtol": 0.03}],
     "note": "polarization camera (0/45/90/135 deg) images of a specular dielectric dome (n = 1.5) are inverted "
             "per pixel to zenith / azimuth candidates, the convex prior resolves the ambiguity, and the normal "
             "map gives the mean curvature in 1/px: -1/R of the sphere (convex negative) within 3 %"},
    {"name": "Optics — object-side telecentric lens: magnification and telecentricity error", "family": "optics",
     "task": "design", "task_class": "optics", "halcon": "Calibration", "input_sort": None,
     "sample": "op_telecentric",
     "stages": [{"op": "telecentric_lens", "kw": {"kind": "object", "magnification": "$aux.magnification"}},
                {"op": "telecentricity_error", "kw": {"field_mm": 5.0, "step_height_mm": 1.0}}],
     "expect": [{"get": ["magnification_low"], "approx": "magnification", "rtol": 0.02},
                {"get": ["relative_size_error", "@abs"], "between": [0.0, 1e-3]}],
     "note": "gauging optics: a telecentric lens keeps the same magnification when the part moves in depth; real "
             "ray trace of the design gives the magnification (within 2 % of design) and the relative size error "
             "over a 1 mm height step (< 0.1 %) — why telecentric lenses are used for dimensional measurement"},
    {"name": "Optics — irradiance and uniformity of a point LED over the field (illumination design)",
     "family": "optics", "task": "design", "task_class": "optics", "halcon": None, "input_sort": None,
     "sample": "op_point_light",
     "stages": [{"op": "light_source", "kw": {"kind": "point", "height_mm": "$aux.height_mm"}},
                {"op": "irradiance_map", "kw": {"size_mm": [100.0, 100.0], "shape": [49, 49]}},
                {"op": "illumination_uniformity"}],
     "expect": [{"get": ["centre"], "approx": "centre", "rtol": 1e-6},
                {"get": ["uniformity"], "approx": "uniformity", "atol": 0.03}],
     "note": "machine-vision lighting design: a Lambertian point LED at 100 or 150 mm above the part, irradiance "
             "map over a 100 mm field and its uniformity (min/max over the central 80 %); centre irradiance is "
             "I0/h^2 exactly and uniformity follows the cos^4 law (h^2/(h^2+r^2))^2 at the box corner"},
    {"name": "Optics — peak wavelength of a blackbody source (Wien's law, spectral radiometry)",
     "family": "optics", "task": "measure", "task_class": "optics", "halcon": None, "input_sort": None,
     "sample": "op_blackbody",
     "stages": [{"op": "blackbody_spectrum", "kw": {"temperature_k": "$aux.temperature_k", "wl_min_nm": 300.0,
                                                    "wl_max_nm": 3000.0, "n_points": 541}},
                {"op": "spectral_stats"}],
     "expect": [{"get": ["peak_nm"], "approx": "peak_nm", "atol": 5.0}],
     "note": "spectral radiometry of a halogen / blackbody light source: Planck spectrum on a 5 nm grid and its "
             "statistics; the peak wavelength in nm follows Wien's displacement law 2.898e6 nm K / T"},
    {"name": "Measure — overlay alignment from a moire mark (nm-scale shift)", "family": "optics",
     "task": "measure", "task_class": "measurement", "halcon": "2D Metrology", "input_sort": None,
     "sample": "op_moire",
     "stages": [{"op": "moire_overlay_image", "kw": {"shape": [64, 512], "layout": "single",
                                                     "shift_nm": "$aux.shift_nm"}},
                {"op": "moire_mark_read", "args": ["$prev", "$aux.ref"], "kw": {"layout": "single"}}],
     "expect": [{"get": ["shift_x_nm"], "approx": "shift_nm", "atol": 2.0}],
     "note": "lithography overlay / alignment: two gratings of 2.00 and 2.04 um pitch form a moire fringe that "
             "magnifies the wafer shift 50x; the camera image (0.5 um pixels) is demodulated against the zero-shift "
             "reference and converted to the grating shift in nm"},
    {"name": "Measure — photoelastic retardance and principal-stress direction (polarization camera)",
     "family": "optics", "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "image",
     "sample": "op_retardance",
     "stages": [{"op": "photoelastic_polarization_images", "kw": {"axis_deg": "$aux.axis_deg"}},
                {"op": "photoelastic_phase_estimate"}],
     "expect": [{"get": ["delta_rad", "@mean"], "approx": "mean_delta", "rtol": 1e-6},
                {"get": ["axis_deg", "@median"], "approx": "axis_deg", "atol": 1e-6}],
     "note": "stress inspection in glass / epoxy: retardance delta = 2 pi t C (s1-s2)/lambda (rad) under "
             "circularly polarized light is imaged by a 4-direction polarization camera and inverted in closed "
             "form to retardance and fast-axis angle in degrees"},
    # ------------------------------------------------------------------ rangedoppler
    {"name": "Sense — FMCW radar range and velocity of a target (range-Doppler map)", "family": "rangedoppler",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": None, "sample": "op_fmcw_target",
     "stages": [{"op": "fmcw_beat_simulate", "kw": {"ranges_m": "$aux.ranges", "velocities_ms": "$aux.velocities",
                                                    "noise_sigma": 0.05, "seed": 1}},
                {"op": "fmcw_window_apply", "kw": {"window": "hann", "axis": "range"}},
                {"op": "range_doppler_map"},
                {"op": "range_doppler_peaks", "kw": {"range_bin_m": _RBIN, "velocity_bin_ms": _VBIN}}],
     "expect": [{"get": ["peaks", 0, "range_m"], "approx": "range_m", "atol": 0.05},
                {"get": ["peaks", 0, "velocity_ms"], "approx": "velocity_ms", "atol": 0.05}],
     "note": "automotive / industrial 77 GHz FMCW radar: beat signal of one moving target (64 samples x 32 chirps), "
             "Hann range window, 2-D FFT range-Doppler map, strongest peak converted with the 1.171 m range bin "
             "and 1.217 m/s velocity bin to range m and radial velocity m/s"},
    {"name": "Sense — radar direction of arrival with a uniform linear array (beamforming)",
     "family": "rangedoppler", "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": None,
     "sample": "op_fmcw_array",
     "stages": [{"op": "fmcw_beat_simulate", "kw": {"ranges_m": [12.0], "velocities_ms": [0.0],
                                                    "angles_deg": "$aux.angles", "n_antennas": 8,
                                                    "noise_sigma": 0.05, "seed": 2}},
                {"op": "beamform_doa"}],
     "expect": [{"get": ["angles_deg", 0], "approx": "angle_deg", "atol": 1.0}],
     "note": "angle of a radar target from an 8-element half-wavelength array: delay-and-sum beam scan over "
             "-90..90 deg at the strongest range-Doppler cell; direction of arrival in degrees on a 1 deg grid"},
    # ------------------------------------------------------------------ photon
    {"name": "Sense — direct ToF distance from a TCSPC histogram (SPAD lidar pixel)", "family": "photon",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": None, "sample": "op_tcspc",
     "stages": [{"op": "tcspc_simulate", "kw": {"distance_m": "$aux.distance_m", "signal_photons": 200.0,
                                                "ambient_photons": 50.0, "seed": 4}},
                {"op": "tcspc_background_subtract"},
                {"op": "dtof_depth"}],
     "expect": [{"get": [], "approx": "distance_m", "atol": 0.02}],
     "note": "single-photon lidar: time-correlated single photon counting histogram (256 bins x 100 ps) with "
             "ambient background and a 200 ps IRF, median background removed, the return peak converted by "
             "c t / 2 to distance in m (one bin = 1.5 cm)"},
    {"name": "3D — flash lidar depth map from a SPAD histogram cube", "family": "photon", "task": "3d",
     "task_class": "3d", "halcon": "3D Reconstruction", "input_sort": "depth", "sample": "op_dtof_scene",
     "stages": [{"op": "dtof_cube_simulate", "kw": {"signal_photons": 40.0, "ambient_photons": 5.0}},
                {"op": "dtof_cube_depth"}],
     "expect": [{"get": ["@mean"], "approx": "mean_depth", "atol": 0.03}],
     "note": "flash dTOF (SPAD array) imaging: per-pixel arrival-time histograms of a stepped scene, peak bin to "
             "depth in m; the depth map reproduces the scene (mean depth within 3 cm)"},
    {"name": "Preprocess — variance-stabilize a photon-limited image (Anscombe transform)", "family": "photon",
     "task": "preprocess", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "op_flat_irradiance",
     "stages": [{"op": "photon_sample", "kw": {"photons_per_unit": 100.0, "seed": 7}},
                {"op": "anscombe_transform"}],
     "expect": [{"get": ["@std"], "approx": 1.0, "atol": 0.08},
                {"get": ["$s1", "@mean"], "approx": "mean_counts", "rtol": 0.03}],
     "note": "low-light / photon-counting cameras: Poisson-sample a flat irradiance at 100 photons per unit, then "
             "the Anscombe transform turns signal-dependent shot noise into unit-variance Gaussian noise so "
             "standard denoisers apply; std of the result ~ 1 whatever the brightness"},
    # ------------------------------------------------------------------ interferometry
    {"name": "Measure — surface height at a pixel by white-light interferometry (CSI peak)",
     "family": "interferometry", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": None, "sample": "op_csi_point",
     "stages": [{"op": "csi_signal_simulate", "kw": {"surface_um": "$aux.surface_um", "noise": 0.005, "seed": 1}},
                {"op": "csi_peak_position"}],
     "expect": [{"get": [], "approx": "surface_um", "atol": 0.02}],
     "note": "coherence scanning interferometry: the correlogram of a 0.6 um broadband source scanned in 0.05 um "
             "steps peaks where the optical path difference is zero; envelope + phase gives the height in um"},
    {"name": "Measure — tilt of a flat measured by a coherence-scanning interferometer", "family": "interferometry",
     "task": "measure", "task_class": "measurement", "halcon": "3D Reconstruction", "input_sort": "depth",
     "sample": "op_csi_tilt",
     "stages": [{"op": "csi_stack_simulate"},
                {"op": "csi_height_map"},
                {"op": "dem_slope", "kw": {"cell_size": 1.0}}],
     "expect": [{"get": ["@median"], "approx": "tilt_deg", "atol": 0.1}],
     "note": "areal surface metrology: simulate the CSI image stack of a tilted flat (heights um on 1 um pixels), "
             "reconstruct the height map, and take the local slope angle in degrees; the median slope equals "
             "atan(tilt) — checks the interferometer's height scale"},
    {"name": "Measure — distance by chromatic confocal sensor (spectral peak to height)",
     "family": "interferometry", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": None, "sample": "op_confocal_point",
     "stages": [{"op": "chromatic_confocal_simulate", "kw": {"surface_um": "$aux.surface_um", "noise": 2.0,
                                                             "seed": 3}},
                {"op": "chromatic_confocal_height"}],
     "expect": [{"get": [], "approx": "surface_um", "atol": 0.05}],
     "note": "chromatic confocal point sensor: axial chromatic dispersion (0.2 um/nm) focuses one wavelength on the "
             "surface; the spectrometer peak (Gaussian fit) maps back to height in um"},
    # ------------------------------------------------------------------ astrostack
    {"name": "Sense — detect and photometer stars in a frame (aperture photometry)", "family": "astrostack",
     "task": "detect", "task_class": "sensing", "halcon": None, "input_sort": "image", "sample": "op_starfield",
     "stages": [{"op": "star_detect", "kw": {"threshold_sigma": 5.0}},
                {"op": "aperture_photometry", "args": ["$in", "$prev"]}],
     "expect": [{"get": ["@len"], "between": ["n_lo", "n_hi"]}],
     "note": "point-source detection and photometry (stars, also laser spots / fluorescent beads): MAD-noise "
             "threshold at 5 sigma, centroids, then aperture flux with local sky annulus; count of sources found"},
    {"name": "Measure — seeing / PSF FWHM of point sources (Gaussian PSF fit)", "family": "astrostack",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "image", "sample": "op_starfield",
     "stages": [{"op": "star_detect", "kw": {"threshold_sigma": 5.0}},
                {"op": "psf_fit", "args": ["$in", "$prev"]}],
     "expect": [{"get": ["@len"], "between": ["n_lo", "n_hi"]}],
     "note": "image quality of a telescope or optical bench: fit a 2-D Gaussian to every detected point source; "
             "the FWHM in px is the seeing / focus figure (synthetic PSF 3.2 or 4.5 px)"},
    {"name": "Preprocess — stack N frames with sigma clipping (noise drops as 1/sqrt N)", "family": "astrostack",
     "task": "preprocess", "task_class": "preprocess", "halcon": "Filters", "input_sort": "seq<image>",
     "sample": "op_sky_frames",
     "stages": [{"op": "sigma_clip_stack", "kw": {"kappa": 3.0}}],
     "expect": [{"get": [0, "@std"], "approx": "sigma_stack", "rtol": 0.12}],
     "note": "frame stacking for low-light imaging: kappa-sigma clipped mean of 4 or 16 flat-sky frames (read noise "
             "5 e-); the stacked noise falls as 5/sqrt(N). Single stage: the executor returns (stack, accepted) "
             "so no op can follow it (see FAILED_ATTEMPTS); get [0] reads the stack"},
    # ------------------------------------------------------------------ lightfield
    {"name": "3D — depth of a plane from a plenoptic camera raw image (refocus stack, depth from focus)",
     "family": "lightfield", "task": "3d", "task_class": "3d", "halcon": "3D Reconstruction",
     "input_sort": "image", "sample": "op_mla_raw",
     "stages": [{"op": "lf_from_mla", "kw": {"angular": [5, 5]}},
                {"op": "lf_focal_stack", "kw": {"slopes": _SLOPES}},
                {"op": "depth_from_focus", "kw": {"focus_positions": _SLOPES}}],
     "expect": [{"get": ["@median"], "approx": "slope", "atol": 0.25}],
     "note": "light-field (micro-lens array) camera: decode the raw sensor into 5x5 sub-aperture views, "
             "synthetically refocus at disparities -2..2 px/view, and pick per pixel the sharpest refocus "
             "(Sum-Modified-Laplacian); the median disparity equals the plane's true disparity"},
    # ------------------------------------------------------------------ piv
    {"name": "Measure — vorticity of a PIV vector field after outlier replacement", "family": "piv",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "flow2d",
     "sample": "op_rotating_flow",
     "stages": [{"op": "piv_outlier_mask", "kw": {"threshold": 2.0}},
                {"op": "piv_replace_outliers", "args": ["$in", "$prev"]},
                {"op": "piv_vorticity", "kw": {"spacing": 1.0}}],
     "expect": [{"get": ["@median"], "approx": "vorticity", "atol": 1e-6},
                {"get": ["$s1", "@count"], "between": [2, 6]}],
     "note": "particle image velocimetry post-processing: normalized median test flags spurious vectors, they are "
             "replaced by the neighbourhood median, and vorticity (1/frame) of a solid-body rotation equals -2 w "
             "in image coordinates (components (dy, dx))"},
    {"name": "Measure — flow speed in m/s from PIV displacement (pixel size, frame interval)", "family": "piv",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "flow2d",
     "sample": "op_uniform_flow",
     "stages": [{"op": "piv_to_velocity", "kw": {"pixel_size_m": 1e-5, "dt_s": 1e-3}},
                {"op": "piv_flow_magnitude"}],
     "expect": [{"get": ["@median"], "approx": "speed", "rtol": 0.01}],
     "note": "calibrate PIV displacement (px/frame) to velocity with a 10 um object pixel and 1 ms pulse "
             "separation, then the speed map in m/s"},
    # ------------------------------------------------------------------ acoustics
    {"name": "Inspect — bearing outer-race defect frequency by envelope spectrum", "family": "acoustics",
     "task": "inspect", "task_class": "inspection", "halcon": None, "input_sort": None, "sample": "op_bearing",
     "stages": [{"op": "synthesize_bearing_signal", "kw": {"rate": 8000.0, "duration": 0.5, "carrier_hz": 2000.0,
                                                           "defect_hz": "$aux.defect_hz", "noise_sigma": 0.05,
                                                           "seed": 1}},
                {"op": "envelope_spectrum", "kw": {"rate": 8000.0, "low": 1500.0, "high": 2500.0}}],
     "expect": [{"get": ["peak_freq"], "approx": "defect_hz", "atol": 2.0}],
     "note": "vibration / acoustic condition monitoring: band-pass around the 2 kHz structural resonance, Hilbert "
             "envelope, spectrum of the envelope; the peak in Hz is the defect repetition rate (BPFO) within the "
             "2 Hz resolution"},
    {"name": "Sense — time difference of arrival between two microphones (GCC-PHAT)", "family": "acoustics",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": "signal", "sample": "op_mic_pair",
     "stages": [{"op": "gcc_delay", "args": ["$prev", "$aux.mic2"],
                 "kw": {"rate": "$aux.rate", "weight": "phat", "band": [0.0, 24000.0]}}],
     "expect": [{"get": [], "approx": "tdoa_s", "atol": 3e-6}],
     "note": "acoustic source localization: generalized cross-correlation with PHAT weighting between a "
             "microphone pair (0.2 m, 48 kHz) gives the sub-sample delay in s; bearing = asin(c tau / d). "
             "Single stage: no op converts a delay to a bearing (MISSING_OPS)"},
    {"name": "Measure — A-weighted equivalent sound level of a tone", "family": "acoustics", "task": "measure",
     "task_class": "measurement", "halcon": None, "input_sort": "signal", "sample": "op_tone",
     "stages": [{"op": "apply_weighting", "kw": {"rate": "$aux.rate", "kind": "A"}},
                {"op": "equivalent_level", "kw": {"rate": "$aux.rate", "weighting": "Z"}}],
     "expect": [{"get": [], "approx": "leq_db", "atol": 0.3}],
     "note": "noise measurement (sound level meter): IEC 61672 A-weighting filter then the equivalent continuous "
             "level Leq in dB re 1; at 1 kHz the A weight is 0 dB so Leq = 20 log10(A / sqrt 2)"},
    # ------------------------------------------------------------------ flyvision
    {"name": "Sense — self-rotation of a compound eye from optic flow (fly motion vision)", "family": "flyvision",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": "matrix", "sample": "op_fly_drum",
     "stages": [{"op": "fly_lamina_filter", "kw": {"dt_s": "$aux.dt", "tau_adapt_s": 0.1, "tau_lp_s": 0.02}},
                {"op": "fly_t4t5_field", "args": ["$prev", "$aux.lat"],
                 "kw": {"dt_s": "$aux.dt", "tau_s": 0.05, "model": "hr"}},
                {"op": "fly_flow_from_directions", "args": ["$prev", "$aux.lat"]},
                {"op": "fly_egomotion_from_flow", "args": ["$prev", "$aux.lat"], "kw": {"axes": [[0.0, 0.0, 1.0]]}}],
     "expect": [{"get": ["yaw_rad_s"], "between": ["yaw_lo", "yaw_hi"]}],
     "note": "bio-inspired motion sensing: 127-ommatidia hexagonal eye inside a drum of 30 deg stripes, lamina "
             "contrast adaptation, Hassenstein-Reichardt correlators in 6 directions, local flow vectors and a "
             "least-squares rotation fit; the sign of yaw (rad/s) is opposite to the drum's rotation "
             "(correlator magnitude depends on contrast, so only the direction is gated)"},
    {"name": "Sense — motion direction from two photoreceptors (Reichardt correlator)", "family": "flyvision",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": "signal", "sample": "op_fly_pair",
     "stages": [{"op": "fly_emd_response", "args": ["$prev", "$aux.b"], "kw": {"tau_s": 0.05, "dt_s": 0.001}}],
     "expect": [{"get": ["@mean"], "approx": "rbar", "rtol": 0.08}],
     "note": "elementary motion detector: low-pass-delayed cross-correlation of two neighbouring receptors; the "
             "mean response sign is the motion direction and its size dI^2/2 sin(psi) w tau / (1 + (w tau)^2). "
             "Single stage: the detector itself is the task"},
    {"name": "Sense — time to collision from the looming angle (tau)", "family": "flyvision", "task": "sense",
     "task_class": "sensing", "halcon": None, "input_sort": "signal", "sample": "op_looming",
     "stages": [{"op": "fly_tau_from_expansion", "kw": {"dt_s": "$aux.dt", "shape": "sphere"}}],
     "expect": [{"get": [100], "approx": "tau100", "rtol": 0.01}],
     "note": "collision warning from a monocular camera: the subtended angle of an approaching sphere and its "
             "rate give tau = 2 tan(theta/2) / theta' = distance / closing speed in s, with no range sensor. "
             "Single stage: tau is the end product"},
    # ------------------------------------------------------------------ specular
    {"name": "Inspect — specular highlight strength of a glossy part (dichromatic model)", "family": "specular",
     "task": "inspect", "task_class": "inspection", "halcon": "Color", "input_sort": "normalmap",
     "sample": "op_glossy_dome",
     "stages": [{"op": "dichromatic_render", "kw": {"specular": "$aux.ks"}},
                {"op": "specular_coefficient_map"}],
     "expect": [{"get": ["@max"], "approx": "ks", "rtol": 0.03}],
     "note": "gloss inspection: render a dome with the dichromatic reflection model (body color + illuminant-colored "
             "Blinn-Phong highlight of weight ks), then recover per pixel the specular coefficient from the RGB "
             "values; its peak equals ks — separates glare from paint color"},
    {"name": "Sense — degree of linear polarization of specular reflection (Fresnel)", "family": "specular",
     "task": "sense", "task_class": "sensing", "halcon": None, "input_sort": "normalmap",
     "sample": "op_tilted_dielectric",
     "stages": [{"op": "sfp_render", "kw": {"refractive_index": 1.5, "specular_radiance": 1.0,
                                            "diffuse_radiance": 0.0}},
                {"op": "polarization_dolp_map"}],
     "expect": [{"get": ["@median"], "approx": "dolp_median", "atol": 0.01}],
     "note": "polarization imaging of glossy dielectrics: specular reflection off n = 1.5 at zenith 20..75 deg seen "
             "through 0/45/90/135 deg analyzers; the DoLP map follows Fresnel (Rs - Rp)/(Rs + Rp) — basis of "
             "glare removal and shape-from-polarization"},
    # ------------------------------------------------------------------ motionmag
    {"name": "Measure — sub-pixel vibration amplitude from video (phase-based)", "family": "motionmag",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": None, "sample": "op_vibration",
     "stages": [{"op": "synthesize_translation", "kw": {"shape": [32, 32], "frames": 32, "fps": 32.0,
                                                        "amplitude_px": "$aux.amp", "frequency_hz": "$aux.freq"}},
                {"op": "displacement_series", "kw": {"f_lo": 3.0, "f_hi": 9.0, "fps": 32.0}}],
     "expect": [{"get": ["@max"], "approx": "amp", "atol": 0.03}],
     "note": "non-contact vibration measurement with a camera: complex steerable pyramid phase of a translating "
             "texture, band-passed 3..9 Hz, gives the displacement time series in px; its peak is the vibration "
             "amplitude (0.5 px at 4 Hz or 0.3 px at 8 Hz)"},
    {"name": "Inspect — magnify a small vibration in video (motion magnification)", "family": "motionmag",
     "task": "inspect", "task_class": "inspection", "halcon": None, "input_sort": "seq<image>",
     "sample": "op_vibration_video",
     "stages": [{"op": "motion_magnify", "kw": {"alpha": 10.0, "f_lo": 3.0, "f_hi": 5.0, "fps": 32.0}}],
     "expect": [{"get": ["phase_shift_max_rad"], "between": [0.0, 10.0]}],
     "note": "visual vibration inspection (machines, structures): phase-based Eulerian motion magnification by "
             "alpha = 10 in the 3..5 Hz band; returns the magnified video and SNR / linearity figures. "
             "Single stage: the magnified video is the end product"},
    {"name": "Measure — vibration SNR in a frequency band of a video", "family": "motionmag", "task": "measure",
     "task_class": "measurement", "halcon": None, "input_sort": "seq<image>", "sample": "op_vibration_video",
     "stages": [{"op": "temporal_bandpass", "kw": {"f_lo": 3.0, "f_hi": 5.0, "fps": 32.0}},
                {"op": "band_snr", "kw": {"f_lo": 3.0, "f_hi": 5.0, "fps": 32.0}}],
     "expect": [{"get": ["motion_power"], "between": [0.0, 1.0]}],
     "note": "how detectable is a vibration: temporal band-pass 3..5 Hz of every pixel, then band power vs noise "
             "per bin (dB); motion power scales with amplitude^2"},
]

MISSING_OPS = [
    {"family": "acoustics", "need": "TDOA (s) + microphone spacing -> source bearing angle (deg)",
     "why": "gcc_delay returns a delay; no op turns delay into a direction of arrival for a mic pair / array"},
    {"family": "astrostack", "need": "stacked-image SNR / noise gain report vs single frame",
     "why": "noise_sigma works on one image; every stacking op returns a tuple, so the gain cannot be chained"},
    {"family": "piv", "need": "image pair -> flow2d estimator whose executor returns only the flow",
     "why": "piv_cross_correlate / piv_multipass / piv_deform_pass / piv_ensemble_correlate all return (flow, info)"},
]

FAILED_ATTEMPTS = [
    {"family": "astrostack", "recipe": "starfield -> star_detect", "op": "synth_starfield",
     "error": "star_detect: ValueError setting an array element with a sequence (got a 2-tuple)",
     "cause": "declaration_lie"},
    {"family": "astrostack", "recipe": "frames -> sigma_clip_stack -> noise_sigma", "op": "sigma_clip_stack",
     "error": "noise_sigma: ValueError inhomogeneous shape — executor returns (stack, accepted), declared image",
     "cause": "declaration_lie"},
    {"family": "astrostack", "recipe": "frames -> align_frames -> sigma_clip_stack", "op": "align_frames",
     "error": "returns (aligned, matrices), declared seq<image>; same for cosmic_ray_reject(_stack), "
              "drizzle_resample, synth_frame_series, frame_align", "cause": "declaration_lie"},
    {"family": "piv", "recipe": "piv_synth_pair -> piv_cross_correlate -> piv_vorticity", "op": "piv_cross_correlate",
     "error": "returns (flow, info) (2-tuple), declared flow2d — fails TYPE_CHECKS['flow2d']; piv_synth_pair returns "
              "(a, b, truth) declared image", "cause": "declaration_lie"},
    {"family": "lightfield", "recipe": "lf_synthesize -> lf_depth_from_focus", "op": "lf_synthesize",
     "error": "lf_depth_from_focus: ValueError inhomogeneous shape — lf_synthesize returns (lf, truth), declared "
              "lightfield", "cause": "declaration_lie"},
    {"family": "lightfield", "recipe": "lightfield -> lf_epi_slope -> lf_disparity_to_depth", "op": "lf_epi_slope",
     "error": "lf_epi_slope and lf_depth_from_focus return (map, confidence) declared image; lf_disparity_to_depth "
              "then silently returns a (2, H, W) 'depth'", "cause": "declaration_lie"},
    {"family": "specular", "recipe": "seq<image> -> photometric_stereo_robust -> slope_to_curvature",
     "op": "photometric_stereo_robust",
     "error": "returns a 3-tuple (normals, ...) declared normalmap", "cause": "declaration_lie"},
    {"family": "specular", "recipe": "rgbimage -> specular_diffuse_split -> ...", "op": "specular_diffuse_split",
     "error": "returns (diffuse, specular) 2-tuple declared rgbimage", "cause": "declaration_lie"},
    {"family": "optics", "recipe": "thick_lens -> paraxial_trace", "op": "thick_lens",
     "error": "paraxial_trace: expected the dict returned by lens_system(); thick_lens returns its own EFL table",
     "cause": "type_gap"},
    {"family": "flyvision", "recipe": "matrix -> fly_lamina_filter -> fly_t4t5_field(three_arm)",
     "op": "fly_t4t5_field",
     "error": "ValueError movie has a negative entry; the default model needs one ON/OFF half (onoff[:, :n]) which "
              "a chain cannot slice — used model='hr' instead", "cause": "type_gap"},
]
