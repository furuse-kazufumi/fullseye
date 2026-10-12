#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Factory-inspection (FA) sample images for Fullseye Studio, made by physics, with ground truth.

The bundled Studio samples were general-purpose (coins / camera / cell). An FA engineer
looking at the Studio wants to see *their* problems: a scratch on hairline stainless,
a dent and a foreign fibre on a moulded part, an engraved lot code, the holes of a
machined plate, porosity in a weld radiograph. This generator makes those scenes
**without any photograph** (licence: own work) and **with the defect positions known
exactly**, because every image is computed from a geometry written down here:

* ``metal_hairline_scratch`` / ``resin_dent_fibre`` / ``engraved_lot_code`` -- a height
  field (mm) lit by an :mod:`illumdesign` light (ring / bar emitters, inverse-square
  and cosine law) and seen through a Lambert + GGX microfacet BRDF -- the *same*
  reflectance model ``illumdesign.defect_contrast`` uses (:func:`render_height_field`
  is its per-pixel vectorisation, and ``tests/test_fa_samples.py`` pins the two
  together). Rough patches (a torn scratch floor, a laser-melted engraving) scatter
  their Fresnel fraction diffusely, which is what makes dark-field lighting work.
  Then a camera: lens PSF, exposure, photon (Poisson) and read noise, 8-bit PNG.
* ``machined_plate_holes`` -- the back-lit plate of ``examples/poc_dimensional_inspection``
  (signed-distance part -> sub-pixel area coverage -> Gaussian PSF -> pixel integration).
* ``weld_xray_porosity`` -- the radiograph of ``examples/poc_weld_radiograph_porosity``
  (Beer-Lambert through plate + weld cap - spherical pores, scatter, Poisson counts).

For every image the generator writes ``<name>.png`` (the picture), ``<name>.truth.png``
(the pixel-exact defect mask, white = defect) and a manifest entry with ``source``,
``licence``, ``description`` / ``description_ja`` (what is in the picture), ``truth``
(the defect geometry in numbers) and ``recipe`` (the Studio sample pipeline in
``recipes.py`` that finds it; ``tests/test_fa_samples.py`` measures that it does).

    py -3.11 tools/gen_fa_samples.py            # write PNGs + merge the manifest
    py -3.11 tools/gen_fa_samples.py --list     # what would be written; write nothing

Honest limits: the BRDF has no inter-reflection and no cast shadow (every defect here is
shallow -- micrometres to tens of micrometres); the hairline is a band-limited random
height field, not a model of an abrasive belt; the radiograph and the back-lit plate are
the PoCs' own models and their limits are documented there.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import illumdesign as ID                          # noqa: E402
import imgio                                      # noqa: E402
from gen_sample_images import merge_manifest      # noqa: E402  (shared owner-aware merge)

OUT = os.path.join(_ROOT, "studio_assets", "sample_images")
OWNER = "gen_fa_samples"
LICENCE = "own work (Apache-2.0; computed by Fullseye, no photograph)"


# --------------------------------------------------------------------------- #
# physics: a height field under an illumdesign light, then a camera             #
# --------------------------------------------------------------------------- #
def render_height_field(height, px_mm, light, surface, *, albedo=None, rough=None,
                        camera_z_mm=300.0):
    """Radiance toward a camera on the optical axis from every pixel of a height field.

    *height* ``(H, W)`` in mm on a grid of pitch *px_mm* (row 0 at +y, the field centred
    on the optical axis); *light* is a dict from :func:`illumdesign.light_source` of a
    point-emitter family (``ring``, ``bar``, ``dome``, ``point``); *surface* an
    ``illumdesign`` preset or ``{albedo, roughness, f0}``. *albedo* (optional ``(H, W)``)
    overrides the body albedo per pixel (pigment, a foreign fibre); *rough* (optional
    bool ``(H, W)``) marks micro-rough patches that scatter the Fresnel fraction
    diffusely (``illumdesign._radiance(..., rough=True)``).

    Per pixel this is exactly ``illumdesign._radiance`` -- the sum over emitters of
    ``(rho/pi + f_GGX) * I0 cos^m(theta_e) / d^2 * (n.l)`` -- with the normal taken from
    the height gradient and the view direction toward ``(0, 0, camera_z_mm)``, vectorised
    over pixels instead of looped. Area sources (``coaxial``) are refused: their
    mirror-hit term is not vectorised here.
    """
    if light.get("area") is not None:
        raise ValueError("render_height_field: area sources (coaxial) are not supported")
    E, D, I0, m = ID._check_light(light)
    sp = ID._surface_params(surface)
    h = np.asarray(height, np.float64)
    if h.ndim != 2 or h.shape[0] < 3 or h.shape[1] < 3 or not np.isfinite(h).all():
        raise ValueError("height must be a finite 2-D array of at least 3x3")
    if not (np.isfinite(px_mm) and px_mm > 0):
        raise ValueError("px_mm must be a positive number")
    H, W = h.shape
    x = (np.arange(W) - (W - 1) / 2.0) * px_mm
    y = ((H - 1) / 2.0 - np.arange(H)) * px_mm
    X, Y = np.meshgrid(x, y)
    dh_drow, dh_dcol = np.gradient(h, px_mm)
    N = np.stack([-dh_dcol, dh_drow, np.ones_like(h)], -1)        # dh/dy = -dh/drow
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    P = np.stack([X, Y, h], -1)
    V = np.array([0.0, 0.0, float(camera_z_mm)]) - P
    V /= np.linalg.norm(V, axis=-1, keepdims=True)
    rho = np.full((H, W), sp["albedo"]) if albedo is None else np.asarray(albedo, np.float64)
    rmask = np.zeros((H, W), bool) if rough is None else np.asarray(rough, bool)
    if rho.shape != (H, W) or rmask.shape != (H, W):
        raise ValueError("albedo / rough must have the height field's shape")
    ndv = np.sum(N * V, -1)
    out = np.zeros((H, W))
    for e in range(len(E)):
        Lv = E[e] - P
        d2 = np.sum(Lv * Lv, -1)
        L = Lv / np.sqrt(d2)[..., None]
        cos_e = np.clip(np.sum(-L * D[e], -1), 0.0, None)
        irr = I0 * cos_e ** m / d2
        ndl = np.sum(L * N, -1)
        Hh = L + V
        Hh /= np.maximum(np.linalg.norm(Hh, axis=-1, keepdims=True), 1e-300)
        fs = ID._ggx(ndl, ndv, np.sum(Hh * N, -1), np.sum(Hh * V, -1), sp["roughness"], sp["f0"])
        lit = irr * np.clip(ndl, 0.0, None)
        F = sp["f0"] + (1.0 - sp["f0"]) * (1.0 - np.clip(ndl, 0.0, 1.0)) ** 5
        out += np.where(rmask, ((F + (1.0 - F) * rho) / np.pi) * lit, (rho / np.pi + fs) * lit)
    return out


def camera_capture(radiance, rng, *, background_level=0.32, psf_px=0.7, full_well=5000.0,
                   read_noise=0.004, dark=0.02):
    """Radiance -> image in [0, 1]: lens PSF, exposure, photon + read noise, clip.

    The exposure puts the **median** (the defect-free surface) at *background_level*, as
    an operator would set it; whatever is brighter than ``1 / background_level`` times
    the surface saturates, as it would on a real sensor.
    """
    img = ndimage.gaussian_filter(np.asarray(radiance, np.float64), psf_px)
    med = float(np.median(img))
    if not med > 0:
        raise ValueError("camera_capture: the scene is black (median radiance <= 0)")
    img = img / med * background_level
    e = rng.poisson(np.clip(img, 0.0, None) * full_well) / full_well
    return np.clip(e + dark + rng.normal(0.0, read_noise, img.shape), 0.0, 1.0)


def ring_light(elevation_deg, radius_mm=40.0, n=72):
    """An illumdesign ring light whose emitters see the field centre at *elevation_deg*."""
    return ID.light_source("ring", radius_mm=radius_mm,
                           height_mm=radius_mm * math.tan(math.radians(elevation_deg)), n=n)


def _curve_distance(shape, curve):
    """Distance (px) from every pixel to a densely sampled polyline, and the nearest sample."""
    from scipy.spatial import cKDTree
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    d, idx = cKDTree(curve).query(np.stack([yy.ravel(), xx.ravel()], 1))
    return d.reshape(H, W), idx.reshape(H, W)


def _bezier(p0, p1, p2, n):
    t = np.linspace(0.0, 1.0, n)
    p0, p1, p2 = (np.asarray(p, np.float64) for p in (p0, p1, p2))
    return t, (((1 - t) ** 2)[:, None] * p0 + (2 * (1 - t) * t)[:, None] * p1
               + (t ** 2)[:, None] * p2)


def _hairline(shape, px_mm, rng, slope_deg=3.0):
    """Hairline (brushed) finish: a height field correlated along x, ~1 px across."""
    H, W = shape
    hair = ndimage.gaussian_filter(rng.standard_normal((H, W)), (0.7, 60.0))
    env = ndimage.gaussian_filter(rng.standard_normal((H, W)), (4.0, 25.0))
    hair = hair * np.clip(1.0 + 0.3 * env / env.std(), 0.2, 2.0)
    hair *= math.tan(math.radians(slope_deg)) / np.gradient(hair, px_mm)[0].std()
    wav = ndimage.gaussian_filter(rng.standard_normal((H, W)), 40.0)
    return hair + wav * (0.004 / wav.std())


# --------------------------------------------------------------------------- #
# scenes                                                                         #
# --------------------------------------------------------------------------- #
def scene_metal_hairline_scratch(seed=20261012, defects=True):
    """A scratch across hairline stainless, under a low-angle (dark-field) ring light."""
    H = W = 320
    px = 0.05                                      # mm / px -> a 16 mm field
    rng = np.random.default_rng(seed)
    h = _hairline((H, W), px, rng)
    p = [[60.0, 50.0], [120.0, 200.0], [255.0, 265.0]]
    t, curve = _bezier(*p, 1200)
    wob = ndimage.gaussian_filter1d(rng.standard_normal(t.size), 40.0)
    wob /= np.abs(wob).max()
    taper = np.clip(np.minimum(t, 1.0 - t) / 0.12, 0.0, 1.0) ** 0.7
    half_w = (1.5 + 0.4 * wob) * (0.35 + 0.65 * taper)          # px
    depth = (0.006 + 0.002 * wob) * taper                        # mm
    torn = ndimage.gaussian_filter1d(rng.standard_normal(t.size), 6.0) > -0.2
    d, idx = _curve_distance((H, W), curve)
    hw, dep = half_w[idx], depth[idx]
    inside = d < hw
    truth = inside & (dep > 0.0015)                              # deeper than 1.5 um
    rough = inside & (d < 0.6 * hw) & torn[idx] & (dep > 0.002)
    if defects:
        h = h + np.where(inside, -dep * (1.0 - (d / hw) ** 2), 0.0)
    else:                                                        # the defect-free twin
        truth, rough = np.zeros_like(truth), np.zeros_like(rough)
    elev = 30.0
    rad = render_height_field(h, px, ring_light(elev), "brushed_metal", rough=rough)
    img = camera_capture(rad, np.random.default_rng(seed + 1))
    vis = depth > 0.0015
    return {
        "img": img, "mask": truth,
        "source": "illumdesign ring light + GGX height-field render",
        "description": ("Hairline (brushed) stainless steel, 16 x 16 mm at 50 um/px, lit by a "
                        "72-LED ring light at %.0f deg elevation (dark field). A curved scratch "
                        "(V-groove 4-8 um deep, torn rough floor in places) crosses the hairline. "
                        "The bright streaks along x are glints of the hairline itself, not defects."
                        % elev),
        "description_ja": ("ヘアライン仕上げのステンレス(16 × 16 mm、50 µm/px)を仰角 %.0f° のリング照明"
                           "(LED 72 個、暗視野)で撮った画像。弧を描く傷(深さ 4〜8 µm の V 溝、底が所々"
                           "荒れている)がヘアラインを横切る。横方向の明るい筋はヘアライン自身の反射で、"
                           "欠陥ではない。" % elev),
        "truth": {"kind": "scratch", "count": 1, "pixels": int(truth.sum()),
                  "bezier_row_col": p,
                  "half_width_px": [round(float(half_w[vis].min()), 2), round(float(half_w.max()), 2)],
                  "depth_um": [round(float(depth[vis].min() * 1e3), 2), round(float(depth.max() * 1e3), 2)],
                  "mask_rule": "groove footprint where the groove is deeper than 1.5 um"},
        "light": "illumdesign ring, radius 40 mm, elevation %.0f deg, 72 emitters" % elev,
        "recipe": "FA — scratch on hairline metal",
    }


def scene_resin_dent_fibre(seed=20261013, defects=True):
    """A dent and a dark foreign fibre on a light-grey moulded resin part, raking bar light."""
    H, W = 288, 384
    px = 0.04                                      # mm / px -> 15.4 x 11.5 mm
    rng = np.random.default_rng(seed)
    tex = ndimage.gaussian_filter(rng.standard_normal((H, W)), 2.5)          # mould texture
    tex *= math.tan(math.radians(0.9)) / np.gradient(tex, px)[0].std()
    sink = ndimage.gaussian_filter(rng.standard_normal((H, W)), 60.0)         # long-wave waviness
    h = tex + sink * (0.01 / sink.std())
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dent_rc, dent_sigma_px, dent_depth = (150.0, 112.0), 14.0, 0.080          # px, px, mm
    r2 = (yy - dent_rc[0]) ** 2 + (xx - dent_rc[1]) ** 2
    dent = -dent_depth * np.exp(-r2 / (2.0 * dent_sigma_px ** 2))
    p = [[90.0, 250.0], [140.0, 300.0], [205.0, 282.0]]
    t, curve = _bezier(*p, 600)
    kink = ndimage.gaussian_filter1d(rng.standard_normal((t.size, 2)), 25.0, axis=0)
    curve = curve + kink * (2.5 / np.abs(kink).max())                     # a fibre is never a clean arc
    d, idx = _curve_distance((H, W), curve)
    fib_w = 1.0 + 0.5 * np.abs(ndimage.gaussian_filter1d(rng.standard_normal(t.size), 15.0))
    fib_w = fib_w / fib_w.max() * 1.6                                       # px half width 0.6-1.6
    fib_hw = fib_w[idx]
    fibre = d < fib_hw
    albedo = np.full((H, W), 0.45)
    if defects:
        h = h + dent + np.where(fibre, 0.012 * np.sqrt(np.clip(1 - (d / fib_hw) ** 2, 0, 1)), 0.0)
        albedo = np.where(fibre, 0.04, albedo)
    dent_mask = r2 <= (2.0 * dent_sigma_px) ** 2                             # depth > 13.5 % of max
    truth = dent_mask | fibre
    elev = 25.0
    light = ID.light_source("bar", radius_mm=40.0, height_mm=40.0 * math.tan(math.radians(elev)),
                            n=48, length_mm=120.0)
    surf = {"albedo": 0.45, "roughness": 0.45, "f0": 0.045}
    rad = render_height_field(h, px, light, surf, albedo=albedo)
    img = camera_capture(rad, np.random.default_rng(seed + 1), background_level=0.45)
    return {
        "img": img, "mask": truth if defects else np.zeros((H, W), bool),
        "source": "illumdesign bar light + GGX height-field render",
        "description": ("Light-grey injection-moulded resin, 15.4 x 11.5 mm at 40 um/px, lit by a "
                        "48-LED bar light raking from the top edge at %.0f deg elevation. Two defects: "
                        "a dent (Gaussian, 80 um deep, sigma 0.56 mm) left of centre, and a dark "
                        "foreign fibre (1-3 px wide, about 5 mm long) on the right. The slow shading "
                        "top-to-bottom is the bar light's fall-off, not a defect." % elev),
        "description_ja": ("薄灰色の射出成形樹脂(15.4 × 11.5 mm、40 µm/px)を、上辺から仰角 %.0f° で"
                           "斜めに当てたバー照明(LED 48 個)で撮った画像。欠陥は 2 つ: 中央左の打痕"
                           "(ガウス形、深さ 80 µm、σ 0.56 mm)と、右側の黒い異物の繊維(幅 1〜3 px・長さ"
                           "約 5 mm)。上から下へのゆるい明暗はバー照明の減衰で、欠陥ではない。" % elev),
        "truth": {"kind": "dent+foreign_fibre", "count": 2,
                  "dent": {"center_row_col": list(dent_rc), "sigma_px": dent_sigma_px,
                           "depth_um": round(dent_depth * 1e3, 3), "mask_radius_px": 2.0 * dent_sigma_px},
                  "fibre": {"bezier_row_col": p, "half_width_px": [round(float(fib_w.min()), 2), round(float(fib_w.max()), 2)], "albedo": 0.04,
                            "surround_albedo": 0.45, "pixels": int(fibre.sum())},
                  "pixels": int(truth.sum()),
                  "mask_rule": "dent: within 2 sigma of its centre; fibre: its painted footprint"},
        "light": "illumdesign bar, 120 mm long at y = 40 mm, elevation %.0f deg, 48 emitters" % elev,
        "recipe": "FA — dent and foreign fibre on resin",
    }


#: The two lines laser-engraved on the plate of ``engraved_lot_code``.
LOT_CODE = ("LOT 2610-A7", "FS-0042")


def scene_engraved_lot_code(seed=20261014, elev=20.0, roughness=0.5, background_level=0.30):
    """A laser-engraved lot code on bead-blasted aluminium, under a low-angle (dark-field) ring."""
    import cv2
    H, W = 224, 384
    px = 0.04                                      # mm / px -> 15.4 x 9.0 mm
    rng = np.random.default_rng(seed)
    blast = ndimage.gaussian_filter(rng.standard_normal((H, W)), 1.2)        # bead-blast pits
    blast *= math.tan(math.radians(6.0)) / np.gradient(blast, px)[0].std()
    wav = ndimage.gaussian_filter(rng.standard_normal((H, W)), 50.0)
    h = blast + wav * (0.006 / wav.std())
    ink = np.zeros((H, W), np.uint8)
    for k, line in enumerate(LOT_CODE):
        cv2.putText(ink, line, (34, 88 + 80 * k), cv2.FONT_HERSHEY_SIMPLEX, 1.55, 255, 4, cv2.LINE_8)
    mark = ink > 0
    depth = 0.020                                                            # mm
    wall = ndimage.gaussian_filter(mark.astype(np.float64), 0.8)             # sloped walls
    h = h - depth * wall
    melt = ndimage.gaussian_filter(rng.standard_normal((H, W)), 1.0) > -0.6  # re-solidified melt
    rough = ndimage.binary_erosion(mark) & melt
    surf = {"albedo": 0.12, "roughness": roughness, "f0": 0.90}                   # aluminium
    rad = render_height_field(h, px, ring_light(elev), surf, rough=rough)
    img = camera_capture(rad, np.random.default_rng(seed + 1), background_level=background_level)
    n_chars = int(ndimage.label(mark, structure=np.ones((3, 3)))[1])
    return {
        "img": img, "mask": mark,
        "source": "illumdesign ring light + GGX height-field render",
        "description": ("Bead-blasted aluminium plate, 15.4 x 9.0 mm at 40 um/px, with the lot code "
                        "'%s' / '%s' laser-engraved 20 um deep (re-solidified, rough floor). A 72-LED "
                        "ring light at %.0f deg elevation (dark field) makes the rough engraving bright "
                        "on the darker blasted surface." % (LOT_CODE[0], LOT_CODE[1], elev)),
        "description_ja": ("ショットブラストしたアルミ板(15.4 × 9.0 mm、40 µm/px)に、ロット番号 '%s' / '%s' を"
                           "深さ 20 µm でレーザー刻印したもの(底は再凝固で荒れている)。仰角 %.0f° のリング照明"
                           "(LED 72 個、暗視野)で、荒れた刻印がブラスト面より明るく写る。"
                           % (LOT_CODE[0], LOT_CODE[1], elev)),
        "truth": {"kind": "engraved_text", "text": list(LOT_CODE), "glyph_components": n_chars,
                  "pixels": int(mark.sum()), "depth_um": depth * 1e3,
                  "font": "OpenCV Hershey Simplex, scale 1.55, thickness 4",
                  "baselines_row": [88, 168], "left_col": 34,
                  "mask_rule": "the engraved footprint (the rasterised glyph strokes)"},
        "light": "illumdesign ring, radius 40 mm, elevation %.0f deg, 72 emitters" % elev,
        "recipe": "FA — engraved lot code (binarize for OCR)",
    }


def _load_poc(stem):
    """Import ``examples/<stem>.py`` by path (examples/ is not a package)."""
    path = os.path.join(_ROOT, "examples", stem + ".py")
    if not os.path.exists(path):
        raise FileNotFoundError("%s is needed to build this sample (run from a source checkout)" % path)
    spec = importlib.util.spec_from_file_location("_fa_poc_" + stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scene_machined_plate_holes(seed=None):
    """The back-lit machined plate of poc_dimensional_inspection: 8 through-holes, exact geometry."""
    P = _load_poc("poc_dimensional_inspection")
    seed = P.SEED if seed is None else seed
    # the PoC draws the part bright on dark; a back light shows it the other way round
    # (metal blocks the light), so the picture is inverted to the physical polarity.
    img = 1.0 - np.clip(P.render_part(psf_sigma=1.2, noise_sigma=0.012, illum_grad=0.10, seed=seed),
                        0.0, 1.0)
    rr, cc = np.mgrid[0:P.H, 0:P.W].astype(np.float64)
    holes = np.zeros((P.H, P.W), bool)
    holes |= P._sdf_box(rr, cc, P.SLOT_R0, P.SLOT_R1, P.SLOT_C0, P.SLOT_C1) < 0.0
    holes |= np.hypot(rr - P.HOLE_R, cc - P.HOLE_C) < P.HOLE_RAD
    bolts = [(float(r), float(c)) for r, c, _ in P.bolt_hole_centers()]
    for r, c in bolts:
        holes |= np.hypot(rr - r, cc - c) < P.BOLT_RAD
    return {
        "img": img, "mask": holes,
        "source": "examples/poc_dimensional_inspection.py render_part: SDF part, area coverage, PSF",
        "description": ("A machined plate seen in silhouette on a back light (dark = metal, bright = "
                        "light passing; 12.5 um/px). Eight through-features: a 68.50 px round hole, a "
                        "50.50 px wide slot and six 10.5 px bolt holes on a 104 px pitch circle; also a "
                        "chamfer, a fillet, a step and a 12 deg end face for edge measurement. PSF sigma "
                        "1.2 px, noise 0.012, a 10 % left-right illumination slope."),
        "description_ja": ("バックライトで撮った機械加工プレートの影絵(暗 = 金属、明 = 光が抜ける所。"
                           "12.5 µm/px)。貫通形状は 8 つ: 直径 68.50 px の丸穴、幅 50.50 px の長穴、"
                           "ピッチ円 104 px 上の直径 10.5 px のボルト穴 6 個。面取り・丸み・段差・12° の"
                           "端面もあり、エッジ計測にも使える。PSF σ 1.2 px、雑音 0.012、左右 10 % の照明傾斜。"),
        "truth": {"kind": "through_holes", "count": 8, "pixels": int(holes.sum()),
                  "round_hole": {"center_row_col": [P.HOLE_R, P.HOLE_C], "diameter_px": 2 * P.HOLE_RAD},
                  "slot": {"rows": [P.SLOT_R0, P.SLOT_R1], "cols": [P.SLOT_C0, P.SLOT_C1],
                           "width_px": P.SLOT_W},
                  "bolt_holes": {"centers_row_col": [[round(r, 3), round(c, 3)] for r, c in bolts],
                                 "diameter_px": 2 * P.BOLT_RAD, "pcd_px": 2 * P.BOLT_PCD},
                  "um_per_px": P.PIX_UM,
                  "mask_rule": "pixel centres inside the analytic hole / slot boundaries"},
        "light": "back light (silhouette)",
        "recipe": "FA — count holes in a back-lit plate",
    }


def scene_weld_xray_porosity(seed=None, defects=True):
    """The weld radiograph of poc_weld_radiograph_porosity: spherical pores of known size and place."""
    P = _load_poc("poc_weld_radiograph_porosity")
    rng = np.random.default_rng(P.SEED if seed is None else seed)
    pores = P.place_pores(rng, 7, 0.6, 2.0)
    sc = P.render(pores if defects else [], rng)
    if not defects:                                              # the pore-free twin
        pores = []
    # display window (window / level, as a radiograph viewer does): the detector values span
    # only ~0.1 of the range, so the linear map [lo, hi] -> [0, 1] is applied for viewing.
    raw = np.asarray(sc["img"], np.float64)
    lo, hi = np.percentile(raw, [0.1, 99.9])
    img = np.clip((raw - lo) / (hi - lo), 0.0, 1.0)
    rr, cc = np.mgrid[0:P.H, 0:P.W].astype(np.float64)
    mask = np.zeros((P.H, P.W), bool)
    for r0, c0, d in pores:
        mask |= np.hypot(rr - r0, cc - c0) < d / (2.0 * P.PX)
    return {
        "img": img, "mask": mask,
        "source": "examples/poc_weld_radiograph_porosity.py render: Beer-Lambert, scatter, Poisson",
        "description": ("X-ray radiograph of a butt weld in 10 mm steel (0.1 mm/px; bright = thinner). "
                        "The darker horizontal band is the weld cap (2 mm reinforcement). %d spherical "
                        "gas pores, 0.6-2.0 mm diameter, sit in the weld; scatter (SPR 0.5), detector "
                        "blur and photon noise are modelled. Shown with a linear display window "
                        "(the 0.1-99.9 percentile range mapped to black-white)." % len(pores)),
        "description_ja": ("板厚 10 mm 鋼の突合せ溶接の X 線透過像(0.1 mm/px、明るい = 薄い)。横に走る暗い帯は"
                           "余盛(高さ 2 mm)。溶接部に直径 0.6〜2.0 mm の球形の気孔が %d 個ある。散乱"
                           "(散乱/一次線比 0.5)・検出器のぼけ・光子雑音を模している。表示用に線形のウィンドウ処理"
                           "(0.1〜99.9 パーセンタイルを黒〜白に)をかけてある。" % len(pores)),
        "truth": {"kind": "porosity", "count": len(pores), "pixels": int(mask.sum()),
                  "pores_row_col_dmm": [[round(r, 2), round(c, 2), round(d, 3)] for r, c, d in pores],
                  "mm_per_px": P.PX,
                  "display_window": [round(float(lo), 5), round(float(hi), 5)],
                  "mask_rule": "pixel centres inside each pore's projected circle"},
        "light": "X-ray (about 250 kV effective), film/detector",
        "recipe": "FA — weld porosity (X-ray)",
    }


SCENES = {
    "metal_hairline_scratch": scene_metal_hairline_scratch,
    "resin_dent_fibre": scene_resin_dent_fibre,
    "engraved_lot_code": scene_engraved_lot_code,
    "machined_plate_holes": scene_machined_plate_holes,
    "weld_xray_porosity": scene_weld_xray_porosity,
}


def build(name):
    """Compute scene *name* (no file is written). Returns the scene dict."""
    if name not in SCENES:
        raise KeyError("unknown FA scene %r (have: %s)" % (name, ", ".join(SCENES)))
    sc = SCENES[name]()
    img, mask = np.asarray(sc["img"], np.float64), np.asarray(sc["mask"], bool)
    if img.shape != mask.shape or not mask.any() or float(np.ptp(img)) < 0.05:
        raise RuntimeError("%s: degenerate scene (shape %s, mask %d px, ptp %.3f)"
                           % (name, img.shape, int(mask.sum()), float(np.ptp(img))))
    sc["img"], sc["mask"] = img, mask
    return sc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="FA sample images (physics, with ground truth)")
    ap.add_argument("--list", action="store_true", help="print what would be written; write nothing")
    args = ap.parse_args(argv)
    if args.list:
        for n, fn in SCENES.items():
            print("%-26s %s" % (n, (fn.__doc__ or "").strip().splitlines()[0]))
        return 0
    os.makedirs(OUT, exist_ok=True)
    entries = []
    for name in SCENES:
        sc = build(name)
        img, mask = sc["img"], sc["mask"]
        imgio.save(os.path.join(OUT, name + ".png"), img)
        imgio.save(os.path.join(OUT, name + ".truth.png"), mask.astype(np.float64))
        if not np.array_equal(imgio.load(os.path.join(OUT, name + ".truth.png")) > 0.5, mask):
            raise RuntimeError("%s: the truth mask did not survive the PNG round trip" % name)
        entries.append({"name": name, "file": name + ".png", "truth_mask": name + ".truth.png",
                        "source": "computed by Fullseye (tools/gen_fa_samples.py; %s)" % sc["source"],
                        "licence": LICENCE, "description": sc["description"],
                        "description_ja": sc["description_ja"], "truth": sc["truth"],
                        "light": sc.get("light", ""), "recipe": sc["recipe"]})
        print("  %-26s %dx%d  truth %d px" % (name, img.shape[1], img.shape[0], int(mask.sum())))
    manifest = merge_manifest(os.path.join(OUT, "manifest.json"), entries, OWNER)
    print("[fa_samples] wrote %d images (manifest now %d entries) -> %s"
          % (len(entries), len(manifest["images"]), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
