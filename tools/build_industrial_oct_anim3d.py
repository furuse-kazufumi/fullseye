#!/usr/bin/env python3
"""Industrial OCT field-sweep viewer for ViEW 2026 (ja/en)."""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import octscan as octs  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
ANIM3D_I18N_LANGS = ("ja", "en")
LANGS = ANIM3D_I18N_LANGS
OUT_HTML = ROOT / "docs" / "view2026" / "viewers" / "industrial_oct_anim3d.html"
REAL_PATH = ROOT / "data" / "oct_real" / "paint_sdoct_cc_by.npz"
FRAMES = 16
PANEL = 256
N_CLEAR_GROUP = 1.56
N_BASE_GROUP = 1.64
PHASE_BIAS = np.array([0.009, 0.019])
AXIAL_EXAGGERATION = 8.0
LATERAL_UM_PER_WORLD = 1000.0 / 4.5
KEYS = ("V-D", "VI-D", "III-B", "IV-C")
PAPER = {
    "V-D": ("濃色 A", "dark A", (44.6, 11.8), (45.5, 12.2)),
    "VI-D": ("濃色 B", "dark B", (85.5, 15.4), (87.9, 18.0)),
    "III-B": ("黒 A", "black A", (99.8, 20.9), (103.3, 20.6)),
    "IV-C": ("黒 B", "black B", (72.3, 15.3), (74.4, 14.7)),
}
for _font_path in (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
                   Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
    if _font_path.is_file():
        PANEL_FONT = ImageFont.truetype(str(_font_path), 11)
        break
else:  # pragma: no cover - supported build hosts provide one of the fonts above
    PANEL_FONT = ImageFont.load_default()


def _e(value):
    return "< 1e-12" if abs(float(value)) < 1e-12 else "%.4g" % float(value)


def _snap_to_column_mean_peak(image, z, target, max_rows=6):
    """Snap an op-detected interface to the nearest local maximum in the flattened B-scan."""
    mean = np.nanmean(np.asarray(image, float), axis=1)
    maxima = np.flatnonzero((mean[1:-1] >= mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
    row = int(np.argmin(np.abs(np.asarray(z) - target)))
    nearby = maxima[np.abs(maxima - row) <= max_rows]
    if not len(nearby):
        return float(target)
    peak = int(nearby[np.argmin(np.abs(nearby - row))])
    return float(np.asarray(z)[peak])


def _real_sample(data, key, n_lines=64):
    """Raw public spectra through the same octscan op chain as the PoC."""
    spectra = data["spectra_" + key].astype(float)
    take = np.linspace(0, len(spectra) - 1, n_lines).round().astype(int)
    spectra = spectra[take]
    table = octs.oct_from_spectra(
        spectra, data["wavelength_nm"], center_nm=840.0, bandwidth_nm=47.0,
        x_um=np.linspace(0.0, 1000.0, len(spectra)))
    bscan = octs.oct_bscan(table, dc="smooth", window="hann", zero_pad=2)
    dz = float(bscan["dz_um"])
    image = bscan["image_db"]
    surface = octs.oct_bscan_boundaries(
        image[:int(600 / dz)], 1, um_per_px=dz, top_px=int(15 / dz), max_jump_px=3)["rows"][0]
    flat = octs.oct_bscan_flatten(bscan, surface, above_um=20.0, below_um=300.0)
    first = octs.oct_layer_thickness(flat, n_interfaces=1, z_range_um=(50.0, 320.0))
    z2 = float(first["z_opt_um"][0])
    second = octs.oct_layer_thickness(
        flat, n_interfaces=1, z_range_um=(z2 + 8.0, z2 + 60.0), min_prominence_db=1.0)
    z3 = float(second["z_opt_um"][0])
    image_flat = np.asarray(flat["flat_image_db"], float)
    z_flat = np.asarray(flat["z_um"], float) - 20.0
    cumulative = np.array([
        _snap_to_column_mean_peak(image_flat, z_flat, z2 - 20.0),
        _snap_to_column_mean_peak(image_flat, z_flat, z3 - 20.0),
    ])
    optical = np.diff(np.r_[0.0, cumulative])
    return {
        "key": key, "image": image_flat,
        "z": z_flat,
        "profile": np.asarray(flat["db"], float),
        "optical": optical,
        "group_thickness": optical / np.array([N_CLEAR_GROUP, N_BASE_GROUP]),
    }


def _synthetic_samples():
    """PMMA/PC/PS fallback; its displayed B-scans still come from octscan ops."""
    samples = []
    xfine = np.linspace(0.0, 1000.0, 160)
    for k, scale in enumerate((0.88, 0.96, 1.04, 1.12)):
        top = 30.0 + 1.2 * np.sin(2 * np.pi * xfine / 1000.0 + k)
        a = top + 25.0 * scale
        b = a + 40.0 * scale
        c = b + 15.0 * scale
        sample2d = {
            "materials": ["air", "PMMA", "POLYCARBONATE", "POLYSTYRENE", {"n": 1.51, "n_group": 1.53}],
            "interfaces_um": [top, a, b, c], "surface_um": 250.0,
            "scatter": [{"layer": 2, "density_per_mm2": 120.0, "amplitude": 5e-4}],
        }
        raw = octs.oct_bscan_simulate(
            sample2d, width_um=1000.0, n_columns=64, n_pixels=1024,
            center_nm=840.0, bandwidth_nm=50.0, noise=False, seed=30 + k)
        bscan = octs.oct_bscan(raw, dc="reference", window="hann", zero_pad=2)
        dz = float(bscan["dz_um"])
        surface = octs.oct_bscan_boundaries(
            bscan["image_db"][:int(700 / dz)], 1, um_per_px=dz,
            top_px=int(150 / dz), bottom_px=int(360 / dz), max_jump_px=8)["rows"][0]
        flat = octs.oct_bscan_flatten(bscan, surface, above_um=20.0, below_um=300.0)
        # Exercise the same thickness op on the synthetic A-scan; known interfaces
        # remain the fallback truth if a closely spaced peak is rejected.
        try:
            layers = octs.oct_layer_thickness(flat, n_group=["PMMA", "POLYCARBONATE", "POLYSTYRENE"],
                                               n_interfaces=4, z_range_um=(10.0, 250.0))
            group_t = np.asarray(layers["thickness_um"][:2], float)
            optical = np.asarray(layers["optical_thickness_um"][:2], float)
        except ValueError:
            group_t = np.array([25.0, 40.0]) * scale
            optical = group_t * np.array([N_CLEAR_GROUP, N_BASE_GROUP])
        image_flat = np.asarray(flat["flat_image_db"], float)
        z_flat = np.asarray(flat["z_um"], float) - 20.0
        cumulative = np.array([_snap_to_column_mean_peak(image_flat, z_flat, target)
                               for target in np.cumsum(optical)])
        optical = np.diff(np.r_[0.0, cumulative])
        group_t = optical / np.array([N_CLEAR_GROUP, N_BASE_GROUP])
        samples.append({
            "key": "PMMA/PC/PS-%d" % (k + 1), "image": image_flat,
            "z": z_flat, "profile": np.asarray(flat["db"], float),
            "optical": optical, "group_thickness": group_t,
        })
    return samples


def load_samples():
    if REAL_PATH.is_file():
        with np.load(REAL_PATH) as data:
            return [_real_sample(data, key) for key in KEYS], "real"
    return _synthetic_samples(), "synthetic"


def _grid_faces(rows, cols, offset=0):
    ids = np.arange(rows * cols).reshape(rows, cols) + offset
    faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            q = ids[r:r + 2, c:c + 2]
            faces.extend(((q[0, 0], q[0, 1], q[1, 1]), (q[0, 0], q[1, 1], q[1, 0])))
    return faces


def _indices(mode, axis_values):
    axis_values = np.asarray(axis_values, float)
    if mode == "index":
        phase = np.array([N_CLEAR_GROUP, N_BASE_GROUP]) / (1.0 + PHASE_BIAS)
        return phase[None] * (1.0 - axis_values[:, None]) + np.array(
            [N_CLEAR_GROUP, N_BASE_GROUP])[None] * axis_values[:, None]
    # A compact group-index dispersion model anchored at the paper's 840 nm values.
    scale = 1.0 + 0.004 * (840.0 - axis_values) / 40.0
    return np.array([N_CLEAR_GROUP, N_BASE_GROUP])[None] * scale[:, None]


def _physical_to_optical(depth, optical, index):
    d = np.asarray(depth, float)
    t0 = optical[0] / index[0]
    return np.where(d <= t0, d * index[0], optical[0] + (d - t0) * index[1])


def _optical_to_physical(depth, optical, index):
    """Invert the piecewise optical-depth mapping used by every OCT panel."""
    d = np.asarray(depth, float)
    return np.where(d <= optical[0], d / index[0],
                    optical[0] / index[0] + (d - optical[0]) / index[1])


def _display_z(depth_um):
    """Axially exaggerated display coordinate; the numeric factor is shown on screen."""
    return -np.asarray(depth_um, float) / LATERAL_UM_PER_WORLD * AXIAL_EXAGGERATION


def _interface_peak_offsets(sample):
    """Row distance from each displayed interface to the local column-mean maximum."""
    mean = np.nanmean(sample["image"], axis=1)
    maxima = np.flatnonzero((mean[1:-1] >= mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
    offsets = []
    for optical_depth in np.cumsum(sample["optical"]):
        row = int(np.argmin(np.abs(sample["z"] - optical_depth)))
        nearby = maxima[np.abs(maxima - row) <= 12]
        if not len(nearby):
            offsets.append(len(mean))
        else:
            offsets.append(int(nearby[np.argmin(np.abs(nearby - row))] - row))
    return np.asarray(offsets, int)


def _field(samples, mode, axis_values):
    indices = _indices(mode, axis_values)
    rows, cols = 64, 48
    physical = np.linspace(0.0, 155.0, rows)
    xplot = np.linspace(-2.25, 2.25, cols)
    pos, faces, values = [], [], []
    per_frame = [[] for _ in axis_values]
    for si, sample in enumerate(samples):
        y = -1.35 + 0.90 * si
        xx, zz = np.meshgrid(xplot, physical)
        start = len(pos)
        pos.extend(np.c_[xx.ravel(), np.full(xx.size, y), _display_z(zz).ravel()])
        faces.extend(_grid_faces(rows, cols, start))
        src_x = np.linspace(0.0, 1.0, sample["image"].shape[1])
        dst_x = np.linspace(0.0, 1.0, cols)
        for fi, idx in enumerate(indices):
            zopt = _physical_to_optical(physical, sample["optical"], idx)
            resampled = np.empty((rows, cols))
            for c, u in enumerate(dst_x):
                j = int(round(u * (len(src_x) - 1)))
                resampled[:, c] = np.interp(zopt, sample["z"], sample["image"][:, j],
                                             left=sample["image"][0, j], right=sample["image"][-1, j])
            per_frame[fi].append(resampled.ravel())
        values.append(sample["image"])
    val = np.stack([np.concatenate(v) for v in per_frame])
    return np.asarray(pos, float), np.asarray(faces, int), val, indices


def _interface_body(samples, indices, layer, rgb):
    frames, points = len(indices), 0
    positions = []
    for idx in indices:
        frame = []
        for si, sample in enumerate(samples):
            thickness = sample["optical"] / idx
            depth = float(np.sum(thickness[:layer + 1]))
            y = -1.35 + 0.90 * si
            for x in np.linspace(-2.25, 2.25, 72):
                z = float(_display_z(depth))
                frame.extend(((x, y - 0.018, z), (x, y + 0.018, z)))
        positions.append(frame)
        points = len(frame)
    faces = []
    for si in range(len(samples)):
        base = si * 144
        for j in range(71):
            a = base + 2 * j
            faces.extend(((a, a + 2, a + 3), (a, a + 3, a + 1)))
    return {"name": "interface_%d" % layer, "pos": np.asarray(positions), "faces": np.asarray(faces),
            "rgb": rgb, "label": T("界面 %d" % (layer + 1), "interface %d" % (layer + 1))}


def _surface_body(samples, frames):
    positions = []
    for _ in range(frames):
        frame = []
        for si in range(len(samples)):
            y = -1.35 + 0.90 * si
            for x in np.linspace(-2.25, 2.25, 72):
                frame.extend(((x, y - 0.014, 0.0), (x, y + 0.014, 0.0)))
        positions.append(frame)
    faces = []
    for si in range(len(samples)):
        base = si * 144
        for j in range(71):
            a = base + 2 * j
            faces.extend(((a, a + 2, a + 3), (a, a + 3, a + 1)))
    return {"name": "surface_interface", "pos": np.asarray(positions), "faces": np.asarray(faces),
            "rgb": [245, 245, 245], "label": T("表面", "surface")}


def _thickness_band_body(samples, indices, layer, rgb):
    """A narrow ruler beside every slice makes a one-percent thickness shift visible."""
    positions = []
    for idx in indices:
        frame = []
        for si, sample in enumerate(samples):
            thickness = sample["optical"] / idx
            top = float(np.sum(thickness[:layer])) if layer else 0.0
            bottom = float(np.sum(thickness[:layer + 1]))
            y = -1.35 + 0.90 * si
            z0, z1 = float(_display_z(top)), float(_display_z(bottom))
            frame.extend(((2.31, y - 0.055, z0), (2.48, y - 0.055, z0),
                          (2.48, y - 0.055, z1), (2.31, y - 0.055, z1)))
        positions.append(frame)
    faces = []
    for si in range(len(samples)):
        a = 4 * si
        faces.extend(((a, a + 1, a + 2), (a, a + 2, a + 3)))
    return {"name": "thickness_band_%d" % layer, "pos": np.asarray(positions),
            "faces": np.asarray(faces), "rgb": rgb,
            "label": T("層厚バー %d" % (layer + 1), "layer-thickness ruler %d" % (layer + 1))}


def _rgb_map(a, lo, hi):
    q = np.clip((np.asarray(a, float) - lo) / max(hi - lo, 1e-12), 0, 1)
    return np.uint8(np.stack([255 * q, 255 * np.sqrt(q), 255 * (1 - q)], -1))


def _resize(a):
    return np.asarray(Image.fromarray(np.asarray(a, np.uint8), "RGB").resize((PANEL, PANEL), Image.Resampling.BILINEAR))


def _bscan_panel(sample, index):
    depth = np.linspace(0.0, 155.0, PANEL)
    zopt = _physical_to_optical(depth, sample["optical"], index)
    cols = np.linspace(0, sample["image"].shape[1] - 1, PANEL).round().astype(int)
    a = np.stack([np.interp(zopt, sample["z"], sample["image"][:, c]) for c in cols], 1)
    lo, hi = np.percentile(a, (5, 99.5))
    rgb = _rgb_map(a, lo, hi)
    for li, colour in enumerate(((255, 70, 70), (70, 255, 130))):
        dep = np.sum(sample["optical"][:li + 1] / index[:li + 1])
        r = int(np.clip(dep / 155.0 * (PANEL - 1), 0, PANEL - 1))
        rgb[max(0, r - 1):min(PANEL, r + 2)] = colour
    return rgb


def _table_panel(current, paper, micro, source):
    im = Image.new("RGB", (PANEL, PANEL), (12, 16, 21)); d = ImageDraw.Draw(im)
    d.text((8, 8), "µm", fill=(240, 244, 248), font=PANEL_FONT)
    headers = ("", "PoC", "OCT", "µscope")
    for j, h in enumerate(headers): d.text((8 + j * 59, 58), h, fill=(130, 205, 255), font=PANEL_FONT)
    for i, name in enumerate(("L1", "L2")):
        y = 91 + i * 52; d.text((8, y), name, fill=(240, 244, 248), font=PANEL_FONT)
        for j, value in enumerate((current[i], paper[i], micro[i])):
            d.text((67 + j * 59, y), "%.2f" % value, fill=(255, 190, 90) if j == 0 else (210, 220, 228), font=PANEL_FONT)
    return np.asarray(im)


def _profile_panel(sample, index):
    depth = _optical_to_physical(sample["z"], sample["optical"], index)
    db = sample["profile"]
    im = Image.new("RGB", (PANEL, PANEL), (12, 16, 21)); d = ImageDraw.Draw(im)
    left, right, top, bottom = 35, 246, 25, 224
    lo, hi = np.percentile(db, (2, 99.5))
    x = left + np.clip(depth / 155.0, 0, 1) * (right - left)
    y = bottom - np.clip((db - lo) / max(hi - lo, 1e-12), 0, 1) * (bottom - top)
    d.line(list(zip(x, y)), fill=(90, 205, 255), width=2)
    for li, colour in enumerate(((255, 70, 70), (70, 255, 130))):
        dep = np.sum(sample["optical"][:li + 1] / index[:li + 1])
        xx = left + dep / 155.0 * (right - left); d.line((xx, top, xx, bottom), fill=colour, width=2)
    d.text((213, 232), "µm", fill=(180, 190, 200), font=PANEL_FONT)
    return np.asarray(im)


def _limit_panel(center_nm, index):
    design = octs.oct_design(center_nm=float(center_nm), bandwidth_nm=47.0, n_pixels=2048, grid="k", n_group=float(index[0]))
    psf = float(design["axial_resolution_air_um"] * design["window_broadening"])
    limit = 1.4 * psf / index[0]
    values = np.linspace(0, max(14.0, 1.8 * limit), 200)
    im = Image.new("RGB", (PANEL, PANEL), (12, 16, 21)); d = ImageDraw.Draw(im)
    d.text((8, 8), "PSF × 1.4", fill=(240, 244, 248), font=PANEL_FONT)
    x0, x1, y = 24, 238, 138; d.line((x0, y, x1, y), fill=(180, 190, 200), width=2)
    cut = x0 + limit / values[-1] * (x1 - x0)
    d.rectangle((x0, y - 25, cut, y + 25), fill=(90, 52, 46)); d.rectangle((cut, y - 25, x1, y + 25), fill=(35, 92, 72))
    d.line((cut, y - 38, cut, y + 38), fill=(255, 210, 95), width=3)
    d.text((8, 188), "%.2f µm × 1.4 / n = %.2f µm" % (psf, limit), fill=(225, 230, 235), font=PANEL_FONT)
    d.text((35, 112), "< 1.4 PSF", fill=(255, 180, 160), font=PANEL_FONT)
    d.text((175, 112), "≥ 1.4 PSF", fill=(150, 240, 190), font=PANEL_FONT)
    return np.asarray(im), limit


def _motion(frames, bodies):
    xyz = np.zeros((frames, bodies, 3)); quat = np.zeros((frames, bodies, 4)); quat[..., 0] = 1.0
    return xyz, quat


def _make_tab(samples, source, mode, axis_values):
    pos, faces, val, indices = _field(samples, mode, axis_values)
    intensity_lo, intensity_hi = float(np.percentile(val, 2)), float(np.percentile(val, 99.5))
    volume = {"name": "flattened_oct_volume", "pos": pos, "faces": faces, "val": val,
              "label": T("表面で平らにした強度体積", "surface-flattened intensity volume")}
    bodies = [volume, _surface_body(samples, len(indices)),
              _interface_body(samples, indices, 0, [255, 75, 75]),
              _interface_body(samples, indices, 1, [75, 255, 135]),
              _thickness_band_body(samples, indices, 0, [255, 112, 67]),
              _thickness_band_body(samples, indices, 1, [102, 187, 106])]
    xyz, quat = _motion(len(axis_values), len(bodies))
    sample = samples[2]
    if source == "real":
        paper, micro = np.asarray(PAPER["III-B"][2]), np.asarray(PAPER["III-B"][3])
        source_text = "public car paint (CC BY 4.0)"
    else:
        paper = micro = np.array([25.0, 40.0])
        source_text = "synthetic PMMA/PC/PS"
    bscan, table, profile, limit, thickness = [], [], [], [], []
    limits = []
    for value, idx in zip(axis_values, indices):
        current = sample["optical"] / idx
        thickness.append(current)
        bscan.append(_bscan_panel(sample, idx))
        table.append(_table_panel(current, paper, micro, source_text))
        profile.append(_profile_panel(sample, idx))
        lp, lim = _limit_panel(value if mode == "wavelength" else 840.0, idx)
        limit.append(lp); limits.append(lim)
    thickness = np.asarray(thickness)
    endpoint_colour = float(np.ptp(val[-1] - val[0]))
    closed = sample["optical"][None] / indices
    closed_error = float(np.max(np.abs(thickness - closed)))
    peak_offsets = np.stack([_interface_peak_offsets(s) for s in samples])
    checks = [
        {"what": T("掃引の両端で3-Dの色が変わる", "3-D colour changes between sweep endpoints"),
         "criterion": "ptp > 0", "result": "%.6g dB" % endpoint_colour, "ok": endpoint_colour > 0},
        {"what": T("層厚と閉形式 optical/n の一致", "layer thickness agrees with closed form optical/n"),
         "criterion": "< 1e-12 µm", "result": _e(closed_error) + " µm", "ok": closed_error < 1e-12},
        {"what": T("界面線と平坦化Bスキャンのピーク", "interface lines coincide with flattened B-scan peaks"),
         "criterion": T("全界面で±2行以内", "within ±2 rows at every interface"),
         "result": T("最大%d行" % np.max(np.abs(peak_offsets)), "maximum %d rows" % np.max(np.abs(peak_offsets))),
         "ok": np.max(np.abs(peak_offsets)) <= 2},
    ]
    if mode == "index":
        bias = 100 * (thickness[0] / thickness[-1] - 1)
        checks.append({"what": T("位相屈折率で厚く出る量", "excess thickness with phase index"),
                       "criterion": T("透明 0.9%、着色 1.9%", "clear 0.9%, colour 1.9%"),
                       "result": "%.1f%% / %.1f%%" % tuple(bias), "ok": np.allclose(bias, [0.9, 1.9])})
        label = T("① 位相屈折率 → 群屈折率", "① Phase index → group index")
        text = T("同じ界面の光学厚をどの屈折率で割るかを切り替える。群屈折率で論文値に一致する。",
                 "Switch the index used to divide the same optical interface spacing; the group index matches the paper values.")
        axis = {"values": axis_values, "segments": [{"k": 0, "label": T("群屈折率への切替", "blend to group index"), "unit": "", "decimals": 2}]}
    else:
        label = T("② 中心波長を動かす", "② Sweep centre wavelength")
        text = T("材料分散で群屈折率が変わるため、同じ光学厚から読む物理厚と3-Dの色が同期して動く。",
                 "Material dispersion changes group index, so physical thickness from the same optical spacing and 3-D colour move together.")
        axis = {"values": axis_values, "segments": [{"k": 0, "label": T("中心波長", "centre wavelength"), "unit": "nm", "decimals": 0}]}
    panes = [
        {"label": T("(a) 断面(Bスキャン)と界面", "(a) B-scan and interfaces"), "frames": np.asarray(bscan), "png": True},
        {"label": T("(b) 層厚: 本PoC / 論文OCT / 顕微鏡", "(b) Thickness: this PoC / paper OCT / microscopy"),
         "frames": np.asarray(table), "png": True, "data": np.stack([thickness, np.broadcast_to(paper, thickness.shape),
                                                                           np.broadcast_to(micro, thickness.shape)], 1),
         "data_unit": "µm"},
        {"label": T("(c) 深さ方向Aスキャン", "(c) Depth A-scan"), "frames": np.asarray(profile), "png": True},
        {"label": T("(d) 薄い層の拒否: 点像幅の1.4倍", "(d) Thin-layer rejection: 1.4× PSF"),
         "frames": np.asarray(limit), "png": True},
    ]
    series = []
    for i, (ja, en, color) in enumerate((("透明層", "clear layer", "#ff7043"),
                                         ("着色層", "colour layer", "#66bb6a"))):
        values = thickness[:, i]
        lo = min(float(values.min()), float(paper[i])); hi = max(float(values.max()), float(paper[i]))
        pad = max((hi - lo) * 0.08, abs(hi) * 0.002)
        series.append({"label": T(ja, en), "values": values, "unit": "µm", "color": color,
                       "lo": lo - pad, "hi": hi + pad, "references": [float(paper[i])], "decimals": 2})
    tab = pv.viewer_anim3d_tab(
        mode, label, "passed", text, np.arange(len(axis_values)) / 8.0, bodies, xyz, quat,
        series=series, panes=panes, cbar={"lo": intensity_lo, "hi": intensity_hi, "unit": "dB", "cmap": "seq",
                                          "label": T("OCT強度", "OCT intensity")},
        numbers=[pv.viewer_number(T("深さ方向の表示倍率", "axial display exaggeration"),
                                  "×%.0f" % AXIAL_EXAGGERATION)],
        axis=axis, checks=checks, view={"az": -0.8, "el": 0.30, "dist": 1.12})
    return tab, {"endpoint_colour_ptp": endpoint_colour, "thickness_endpoints": thickness[[0, -1]],
                 "thin_limit_endpoints": np.asarray(limits)[[0, -1]], "indices": indices[[0, -1]],
                 "interface_peak_offsets": peak_offsets, "axial_exaggeration": AXIAL_EXAGGERATION}


def build_spec():
    samples, source = load_samples()
    index_tab, index_acc = _make_tab(samples, source, "index", np.linspace(0.0, 1.0, FRAMES))
    wave_tab, wave_acc = _make_tab(samples, source, "wavelength", np.linspace(800.0, 900.0, FRAMES))
    source_ja = "実測の自動車塗装(Liverpool Research Data Catalogue 126、CC BY 4.0、改変あり)" if source == "real" else "合成の多層フィルム(PMMA/PC/PS)"
    source_en = "measured automotive paint (Liverpool Research Data Catalogue 126, CC BY 4.0, modified)" if source == "real" else "synthetic PMMA/PC/PS multilayer film"
    spec = pv.viewer_spec(
        "industrial_oct", T("自動車塗装の層をOCTで測る", "Measure automotive paint layers with OCT"),
        T("Bスキャンを表面で平らにした強度体積。赤・緑の線が層の界面。", "Surface-flattened B-scan intensity volume; red and green lines mark interfaces."),
        T("屈折率または中心波長を動かし、3-Dと(a)〜(d)の同期を見る。", "Move index or centre wavelength and watch 3-D and panels (a)-(d) stay synchronized."),
        [index_tab, wave_tab],
        credit=T(source_ja + "。計算: oct_from_spectra, oct_bscan, oct_bscan_boundaries, oct_bscan_flatten, oct_layer_thickness, oct_design。",
                 source_en + ". Computation: oct_from_spectra, oct_bscan, oct_bscan_boundaries, oct_bscan_flatten, oct_layer_thickness, oct_design."))
    spec["generated"] = "2026-11-01"
    spec["_acceptance"] = {"source": source, "frames": FRAMES, "index": index_acc, "wavelength": wave_acc,
                            "ops": ["oct_from_spectra", "oct_bscan", "oct_bscan_boundaries", "oct_bscan_flatten",
                                    "oct_layer_thickness", "oct_design"]}
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=OUT_HTML); ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    spec = build_spec()
    a = spec["_acceptance"]
    for tab in ("index", "wavelength"):
        v = a[tab]
        print("CHECK %s colour_ptp=%.6g thickness=%s -> %s" % (tab, v["endpoint_colour_ptp"],
              np.array2string(v["thickness_endpoints"][0], precision=3), np.array2string(v["thickness_endpoints"][1], precision=3)))
    if args.check:
        pv._build_html(spec, list(LANGS), detect_lang=True)
    else:
        pv.write_viewer(spec, str(args.out), list(LANGS), detect_lang=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
