"""Polarization and fringe recipes that run unchanged through MCP ``fullseye_pipeline``.

The MCP agent e2e (PR #224) asks for the degree of linear polarization from four analyzer frames and for
the wrapped phase / height from 4-step phase-shifted fringes. Every stage below is an OP_GRAPH
``verified_executable`` op, the input is one handle (``polsweep`` / ``seq<image>`` from
``fullseye_load_stack``), and the parameters are plain values — so ``runner == "mcp"`` in the index.
Truths are closed form: Malus's law ``I(θ) = I0/2·(1 + p·cos 2(θ − φ))`` gives DoLP = p exactly, and
``I_i = A + B·cos(φ − 2πi/4)`` gives the phase φ exactly.
"""
from __future__ import annotations

import numpy as np

from fullseye.recipebook.common import rng

ANGLES = (0.0, 45.0, 90.0, 135.0)


def ms_pol_sweep(variant: int, n: int = 48):
    """Four analyzer frames of a part whose right half is glossy: DoLP p_left / p_right, AoLP φ."""
    p_left, p_right = 0.10 + 0.05 * variant, 0.45 + 0.15 * variant
    phi = np.deg2rad(20.0 + 15.0 * variant)
    split = n // 2 + 6 * variant                                # glossy right part, 24 / 18 columns
    p = np.full((n, n), p_left)
    p[:, split:] = p_right
    i0 = 0.8
    frames = np.stack([i0 / 2 * (1 + p * np.cos(2 * (np.deg2rad(a) - phi))) for a in ANGLES])
    frames = frames + 1e-4 * rng(variant, 31).standard_normal(frames.shape)
    return {"value": frames, "aux": {},
            "truth": {"dolp_mean": float(p.mean()), "dolp_left": p_left, "dolp_right": p_right,
                      "glossy_fraction": float((n - split) / n)}}


def ms_fringe_4step(variant: int, n: int = 48):
    """4-step phase-shifted fringes of a phase ramp φ(x) inside (−π, π); truth = mean phase."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    phi = -2.0 + (2.5 + 0.5 * variant) * xx / (n - 1)          # stays inside (−π, π): no wrap
    frames = np.stack([0.5 + 0.4 * np.cos(phi - 2 * np.pi * i / 4) for i in range(4)])
    return {"value": frames, "aux": {}, "truth": {"phase_mean": float(phi.mean()), "phase_max": float(phi.max())}}


def ms_fringe_height(variant: int, n: int = 48):
    """4-step fringes of a tilted plane whose phase spans several 2π (decode must unwrap); k = height/phase."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    phi = 0.3 + (9.0 + 3.0 * variant) * xx / (n - 1)           # 0.3 .. 9.3 / 12.3 rad: wraps 1-2 times
    frames = np.stack([0.5 + 0.4 * np.cos(phi - 2 * np.pi * i / 4) for i in range(4)])
    k = 0.25
    return {"value": frames, "aux": {}, "truth": {"k": k, "height_ptp": float(k * (phi.max() - phi.min())),
                                                  "height_step": float(k * (phi[0, 1] - phi[0, 0]))}}


RECIPES = [
    {"name": "Sense — degree of linear polarization map from four analyzer angles (0/45/90/135)",
     "family": "specular", "task": "measure", "task_class": "sensing", "halcon": None,
     "input_sort": "polsweep", "sample": "ms_pol_sweep",
     "stages": [{"op": "polarization_dolp_map", "kw": {"angles_deg": [0.0, 45.0, 90.0, 135.0]}}],
     "expect": [{"get": ["@mean"], "approx": "dolp_mean", "atol": 2e-3},
                {"get": [0, 0], "approx": "dolp_left", "atol": 2e-3},
                {"get": [0, -1], "approx": "dolp_right", "atol": 2e-3}],
     "note": "per-pixel degree of linear polarization (0..1) from a polarization camera or a rotated analyzer "
             "at 0, 45, 90, 135 degrees; glossy / specular and transparent surfaces polarize reflected light, "
             "matte ones barely do. Report the map or its mean. One stage: the op is the whole task"},
    {"name": "Inspect — glossy (specular) area from polarization: DoLP map, threshold, area fraction",
     "family": "specular", "task": "inspect", "task_class": "inspection", "halcon": "Regions",
     "input_sort": "polsweep", "sample": "ms_pol_sweep",
     "stages": [{"op": "polarization_dolp_map", "kw": {"angles_deg": [0.0, 45.0, 90.0, 135.0]}},
                {"op": "threshold", "a": 0.3, "b": 0.5},
                {"op": "area_frac", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "approx": "glossy_fraction", "atol": 0.03}],
     "note": "find shiny / specular regions (glare, wet film, lacquer) from four analyzer frames: degree of "
             "linear polarization, keep pixels above DoLP 0.3, fraction of the image they cover"},
    {"name": "Measure — wrapped phase from 4-step phase-shifted fringes",
     "family": "3d", "task": "measure", "task_class": "3d", "halcon": "3D Reconstruction",
     "input_sort": "seq<image>", "sample": "ms_fringe_4step",
     "stages": [{"op": "wrapped_phase", "kw": {"method": "general"}}],
     "expect": [{"get": ["@mean"], "approx": "phase_mean", "atol": 1e-6},
                {"get": ["@max"], "approx": "phase_max", "atol": 1e-6}],
     "note": "N equally phase-shifted fringe images (here 4 steps of π/2, structured light / interferometry) -> "
             "phase wrapped into (−π, π] per pixel by the N-step least-squares formula; the first step of "
             "fringe-projection 3-D measurement. One stage: unwrap with the height recipe"},
    {"name": "3D — height map from 4-step phase-shift fringes (decode, unwrap, scale)",
     "family": "3d", "task": "measure", "task_class": "3d", "halcon": "3D Reconstruction",
     "input_sort": "seq<image>", "sample": "ms_fringe_height",
     "stages": [{"op": "decode_fringe", "kw": {"k": 0.25}}],
     "expect": [{"get": ["@ptp"], "approx": "height_ptp", "rtol": 1e-6}],
     "note": "fringe projection 3-D: 4 phase-shifted fringe images -> wrapped phase -> unwrapped phase -> height "
             "= k · phase (k = phase-to-height calibration factor, here 0.25 per rad). The plane's phase spans "
             "several 2π, so the unwrap step matters. Without ref_phase the height is relative: single-frequency "
             "unwrapping fixes it only up to a constant 2π·k offset (measured: the mean comes out 2π·k lower), so "
             "pass a reference-plane phase (ref_phase) for absolute height"},
]

SAMPLES = {"ms_pol_sweep": ms_pol_sweep, "ms_fringe_4step": ms_fringe_4step, "ms_fringe_height": ms_fringe_height}
MISSING_OPS: list = []
FAILED_ATTEMPTS: list = []
NOTES_JA = {
    "Sense — degree of linear polarization map from four analyzer angles (0/45/90/135)":
        "偏光計測 — 偏光板 0・45・90・135 度の 4 枚から画素ごとの線偏光度マップを求め、平均を報告する(光沢面・透明面)",
    "Inspect — glossy (specular) area from polarization: DoLP map, threshold, area fraction":
        "外観検査 — 偏光 4 枚から線偏光度を出し、しきい値で光沢・鏡面反射の領域を抜いて面積の割合を求める",
    "Measure — wrapped phase from 4-step phase-shifted fringes":
        "位相計測 — 4 ステップ位相シフト縞画像から、二πに巻かれた位相マップ(ラップ位相)を画素ごとに求める",
    "3D — height map from 4-step phase-shift fringes (decode, unwrap, scale)":
        "三次元計測 — 位相シフト縞 4 枚を復号し、位相を展開(アンラップ)して係数をかけ、連続した高さマップを得る",
}
