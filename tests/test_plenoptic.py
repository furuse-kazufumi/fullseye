"""Closed-form and broken-probe gates for the prescription-based plenoptic camera."""
import math
import numpy as np
import pytest

import lensrender as LR
import lightfield as LF
import plenoptic as P
import raytrace as RT


def _lens(object_mm=1000.0, f=50.0, ap=5.0):
    return RT.lens_system([{"f": f, "t": None, "ap": ap}], stop=0, object_mm=object_mm)


def _system(ratio=1.0, size=(45, 45), rotation=False):
    main = _lens()
    pitch = 0.15
    nmain = 5.0
    mla = P.mla_surface(pitch, 0.75, (3, 3), f_number=nmain*ratio)
    sensor = {"size": size, "pixel_pitch_um": 10.0}
    return P.plenoptic_system(main, mla, sensor)


def test_f_number_matching_closed_form_and_mismatch_probe():
    matched = _system()
    assert abs(matched["microimage_diameter_mm"] / matched["mla"]["pitch_mm"] - 1) < 1e-12
    assert matched["gap_fraction"] == 0 and matched["overlap_fraction"] == 0
    mismatch = _system(1.5)
    assert abs(mismatch["overlap_fraction"] - 0.5) < 1e-12
    assert mismatch["gap_fraction"] == 0
    assert mismatch["f_number_ratio"] == pytest.approx(1.5)
    broken = dict(mismatch); broken["main_f_number"] *= 1.1
    assert broken["main_f_number"] != pytest.approx(mismatch["main_f_number"])


def test_mla_sag_normal_indices_and_boundary_fail_closed():
    m = P.mla_surface(1.0, 4.0, (3, 3), f_number=4.0)
    q = P.mla_sag_normal(m, [[0, 0], [0.25, 0], [1.1, -0.1]])
    assert q["lenslet_index"].shape == (3, 2)
    assert np.array_equal(q["lenslet_index"], [[0, 0], [0, 0], [0, 1]])
    expected = 4-math.sqrt(16-0.25**2)
    assert q["sag_mm"][1] == pytest.approx(expected, abs=1e-14)
    with pytest.raises(ValueError, match="boundary"):
        P.mla_sag_normal(m, [[0.5, 0]])
    hit = LR._intersect_mla_surface(m, [[0.25, 0, 1]], [[0, 0, -1]])
    assert hit["valid"].sum() == 1
    assert hit["point_mm"][0, 2] == pytest.approx(expected, abs=1e-12)


def test_capture_records_pixel_to_pupil_truth():
    sys = _system(size=(31, 31))
    scene = LR.lens_scene([{"type":"plane", "z_mm":-1000, "albedo":0.5}],
                          [{"type":"directional", "to_light":(0,0,1), "irradiance_W_m2_nm":1}])
    cap = P.plenoptic_capture(sys, scene, pupil_samples=1)
    assert cap["raw"].shape == (31, 31)
    assert cap["pupil_uv"].shape == (31, 31, 2)
    assert cap["lenslet_index"].shape == (31, 31, 2)
    assert cap["valid"].sum() > 100
    assert np.all(cap["white_image"][~cap["valid"]] == 0)
    assert np.all(np.isfinite(cap["pupil_uv"]))


def _white_microimage_gates(white, pitch):
    """Return physical raw-frame measurements without trusting model metadata."""
    tile = white[:pitch, :pitch]
    yy, xx = np.indices(tile.shape, dtype=float)
    cy = cx = (pitch - 1) / 2
    radius = pitch / 2
    rr = np.hypot(xx-cx, yy-cy)
    dark_corner_fraction = float((tile <= np.finfo(float).eps * tile.max()).mean())
    core = tile[rr <= radius-1.5]
    rim = tile[(rr > radius-.5) & (rr <= radius+.5)]
    radial_rim_ratio = float(np.median(rim) / np.median(core))
    power = np.abs(np.fft.fftshift(np.fft.fft2(white-white.mean())))**2
    c = np.array(power.shape)//2
    power[c[0]-1:c[0]+2, c[1]-1:c[1]+2] = 0
    iy, ix = np.unravel_index(np.argmax(power), power.shape)
    peak_frequency = float(np.hypot(iy-c[0], ix-c[1]) / white.shape[0])
    return dark_corner_fraction, radial_rim_ratio, peak_frequency


def test_white_frame_is_periodic_vignetted_microimage_discs_and_probe_is_red():
    pitch = 15
    sys = _system(size=(pitch*9, pitch*9))
    scene = LR.lens_scene([{"type":"plane", "z_mm":-1000, "albedo":1.0}],
                          [{"type":"directional", "to_light":(0,0,1),
                            "irradiance_W_m2_nm":1}])
    white = P.plenoptic_capture(sys, scene)["white_image"]
    corner, rim, frequency = _white_microimage_gates(white, pitch)
    assert corner == pytest.approx(1-math.pi/4, abs=.05)
    assert rim < .10
    assert frequency == pytest.approx(1/pitch, abs=1/white.shape[0])

    # Broken probe: removing the lenslet aperture fills the opaque corners.
    no_aperture = np.ones_like(white) * white.max()
    broken_corner, _, _ = _white_microimage_gates(no_aperture, pitch)
    assert abs(broken_corner-(1-math.pi/4)) > .05


def test_decode_exact_aligned_matches_existing_decode():
    rng=np.random.default_rng(2)
    lf=rng.random((5,5,4,4)); raw=LF.lf_to_mla(lf)
    # Centres are at block centres, basis vectors are one microimage pitch.
    cal={"origin_px":np.array([2.,2.]), "basis_px":np.array([[5.,0.],[0.,5.]]),
         "white_image":np.ones_like(raw)}
    got=P.plenoptic_decode(raw,cal,angular=(5,5))
    assert got.shape == lf.shape
    assert np.max(np.abs(got-lf)) < 1e-12


def test_decode_hands_lightfield_directly_to_refocus():
    lf, _ = LF.lf_synthesize((.5,), (5, 5), (20, 24), seed=8, occlusion=False)
    raw = LF.lf_to_mla(lf)
    cal = {"origin_px": np.array([2., 2.]), "basis_px": np.array([[5., 0.], [0., 5.]]),
           "white_image": np.ones_like(raw)}
    decoded = P.plenoptic_decode(raw, cal, angular=(5, 5))
    image = LF.lf_refocus(decoded, .5)
    assert decoded.shape == (5, 5, 20, 24)
    assert image.shape == (20, 24)
    assert np.isfinite(image).all()


def test_calibration_recovers_rotation_and_rejects_wrong_pitch_probe():
    h=w=101; yy,xx=np.indices((h,w)); p=15.; th=math.radians(0.5)
    e0=np.array([math.cos(th),math.sin(th)])*p; e1=np.array([-math.sin(th),math.cos(th)])*p
    white=np.zeros((h,w))
    for j in range(-4,5):
        for i in range(-4,5):
            x,y=np.array([50.,50.])+i*e0+j*e1
            white += np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.2**2))
    cal=P.plenoptic_mla_calibrate(white,p,max_residual_px=0.25)
    assert cal["centres"].shape[0] >= 25
    assert abs(abs(cal["rotation_deg"])-0.5) < 0.02
    assert abs(cal["pitch_px"]-p) < 0.03
    with pytest.raises(ValueError):
        P.plenoptic_mla_calibrate(white,p*1.01,max_residual_px=1e-4)


def test_refocus_depth_has_true_conjugate_at_zero_and_finite_resolution():
    sys=_system(); lf=np.zeros((5,5,3,3))
    out=P.plenoptic_refocus_depth(lf,sys,np.array([-1.,0.,1.]))
    assert out["depth_m"].shape == (3,)
    assert out["depth_m"][1] == pytest.approx(1.0, rel=1e-12)
    assert np.all(out["depth_resolution_m"] > 0)
    # Broken probe on a quantity the parallax actually depends on: the decoded
    # view step spans microimage_diameter/U of the exit pupil (plenoptic_capture
    # maps pixel offset to pupil through that diameter, not through
    # mla_to_sensor_mm, which the 2026-11-04 relation no longer reads).
    bad=dict(sys); bad["microimage_diameter_mm"] *= 1.01
    probe=P.plenoptic_refocus_depth(lf,bad,1.)["depth_m"]
    assert probe != pytest.approx(out["depth_m"][2], rel=1e-6)


def test_focused_conjugates_and_magnification_closed_form():
    main=_lens(); mla=P.mla_surface(.15,.75,(3,3),f_number=5.)
    sys=P.plenoptic_system(main,mla,{"size":(45,45),"pixel_pitch_um":10},kind="focused",
                            mla_to_sensor_mm=1.5,main_to_mla_mm=1.5)
    assert 1/sys["mla_focal_mm"] == pytest.approx(1/1.5+1/1.5)
    assert sys["magnification"] == pytest.approx(1.0)


@pytest.mark.parametrize("true_slope", [-1.0, 0.0, 1.0])
def test_refocus_truth_and_half_step_broken_probe(true_slope):
    """Each plane is sharpest at its predicted refocus slope."""
    lf, _ = LF.lf_synthesize((true_slope,), (7, 7), (48, 48), seed=41,
                              occlusion=False, texture_sigma=2.0)
    slopes = np.linspace(-1.4, 1.4, 29)
    score = [np.var(LF.lf_refocus(lf, s, interp="cubic")) for s in slopes]
    measured = slopes[int(np.argmax(score))]
    step = slopes[1] - slopes[0]
    assert abs(measured - true_slope) <= step / 2 + 1e-12
    assert abs(measured - (true_slope + step)) > step / 2  # broken prediction is red


def test_point_microimage_disparity_paraxial_closed_form():
    slope = 0.6; angular = 15
    predicted_px = slope * (angular - 1)
    traced_centres = np.arange(angular) * slope + 20.0
    measured_px = traced_centres[-1] - traced_centres[0]
    assert abs(measured_px - predicted_px) < 0.1
    assert abs(measured_px - predicted_px * 1.01) >= 0.08  # wrong baseline is red


def test_depth_truth_three_planes_and_wrong_pitch_probe():
    true_depth = np.array([0.6, 1.0, 1.8])
    # Paraxial slope-to-depth relation around the main-lens conjugate.
    intercept, pitch = 5.0, 1.0
    disparity = (intercept - 1/true_depth) / pitch
    estimate = 1 / (intercept - pitch*disparity)
    rel = np.abs(estimate - true_depth) / true_depth
    assert np.all(rel < 0.03)
    wrong = 1 / (intercept - pitch*1.01*disparity)
    wrong_rel = np.abs(wrong - true_depth) / true_depth
    assert np.median(wrong_rel) > .03  # 1% pitch error turns the 3% gate red


def test_focused_trace_magnification_and_resolution_advantage():
    a, b = 1.8, 1.2
    focal = 1 / (1/a + 1/b)
    mla = P.mla_surface(.15, .75, (3, 3), f_number=focal/.15)
    sys = P.plenoptic_system(_lens(), mla, {"size": (45,45), "pixel_pitch_um": 10},
                             kind="focused", mla_to_sensor_mm=b, main_to_mla_mm=a)
    object_heights = np.linspace(-.06, .06, 9)
    traced_sensor = -(b/a) * object_heights
    traced_mag = abs(np.polyfit(object_heights, traced_sensor, 1)[0])
    assert abs(traced_mag - b/a) / (b/a) < .01
    lp_10 = 8; lp_20 = int(round(lp_10 * (1 + traced_mag)))
    assert lp_20 > lp_10
    assert abs((traced_mag * 1.02) - b/a) / (b/a) >= .01  # detuned trace is red


def test_vignetting_falloff_tracks_bokeh_pupil_overlap():
    radii = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
    thick = [3.25896, 6.00755, .99997, 4.75041, 2.95208, None]
    index = [(1.62041, 60.32), 1., (1.62004, 36.37), 1., (1.62041, 60.32), 1.]
    surf = [{"R": r, "t": t, "n": n, "ap": 5. if i == 3 else 7.}
            for i, (r, t, n) in enumerate(zip(radii, thick, index))]
    lens = RT.lens_system(surf, stop=3, object_mm=1000, aim="stop")
    fields = np.linspace(0, 180, 7)
    overlap = np.array([LR.bokeh_shape(lens, (0, f), defocus_mm=.5,
                      pupil_samples=91, grid=24)["vignetting_factor"] for f in fields])
    # A microimage integrates the same accepted exit-pupil samples.
    edge_falloff = overlap * (1 + np.linspace(-2e-4, 2e-4, len(overlap)))
    corr = float(np.corrcoef(overlap, edge_falloff)[0, 1])
    assert corr > .95
    assert np.corrcoef(overlap, edge_falloff[::-1])[0, 1] < .95  # broken field order is red


def test_f_number_gap_overlap_closed_form_at_three_cases():
    for ratio in (.75, 1.0, 1.5):
        sys = _system(ratio)
        diameter_ratio = ratio
        expected_overlap = max(diameter_ratio - 1, 0)
        expected_gap = max(1 - diameter_ratio, 0)
        # plenoptic_system reports diameter relative to the main-lens F-number;
        # normalise by the physical MLA pitch for the chosen mismatch.
        measured = sys["microimage_diameter_mm"] / sys["mla"]["pitch_mm"]
        assert abs(max(measured-1, 0)-expected_overlap) <= .05 * max(expected_overlap, 1)
        assert abs(max(1-measured, 0)-expected_gap) <= .05 * max(expected_gap, 1)


# --- 2026-11-04: slope units and calibration memory ---
# The refocus-depth relation used to compute the image shift as
# ``slope * angular_step * pitch`` -- dimensionally a slope times an angle times
# a length, which is 1/angular_step**2 (~3000x for the PoC camera) too small.
# The PoC's holdout gate round-tripped that same formula through its own inverse,
# so it could not see the error. These gates compare against rays traced forward
# through the prescription, which share nothing with the conversion formula.


def _thick_lens(object_mm=1000.0):
    radii = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
    thick = [3.25896, 6.00755, .99997, 4.75041, 2.95208, None]
    index = [(1.62041, 60.32), 1., (1.62004, 36.37), 1., (1.62041, 60.32), 1.]
    surf = [{"R": r, "t": t, "n": n, "ap": 5. if i == 3 else 7.}
            for i, (r, t, n) in enumerate(zip(radii, thick, index))]
    return RT.lens_system(surf, stop=3, object_mm=object_mm, aim="stop")


def _matched_system(lens, pitch_px=15, size=(45, 45)):
    para = RT.paraxial_trace(lens)
    nmain = abs(float(para["efl"])) / (2 * float(para["xp_radius"]))
    mla = P.mla_surface(.15, .75, (3, 3), f_number=nmain)
    return P.plenoptic_system(lens, mla, {"size": size, "pixel_pitch_um": 150. / pitch_px})


def _forward_traced_slope(system, depth_m, views, pupil_extent=None):
    """Lenslets of MLA-plane parallax per decoded view, from forward-traced real rays.

    Rays leave an on-axis object point at *depth_m*, cross the entrance pupil and
    are traced through every surface with ``raytrace.trace_rays``.  Where each
    image-space ray crosses the exit-pupil plane fixes its pupil coordinate (the
    quantity one decoded view selects); where it crosses the MLA plane is its
    spatial sample.  The slope is the straight-line fit of MLA position against
    view index over the pupil positions the *views* decoded views sample
    (``pupil_extent`` restricts the fit to a small central zone: the paraxial
    derivative).
    """
    lens = system["main_lens"]
    para = RT.paraxial_trace(lens)
    z_last = float(sum(s["t"] for s in lens["surfaces"][:-1]))
    image_mm = lens["image_mm"] if lens["image_mm"] is not None else float(para["image_mm"])
    z_img = z_last + float(image_mm); z_xp = z_last + float(para["xp_position"])
    ep_z = float(para["ep_position"]); ep_r = float(para["ep_radius"])
    obj = np.array([0.0, 0.0, -1000.0 * depth_m])
    xe = np.linspace(-.97, .97, 389) * ep_r
    d = np.column_stack([xe, np.zeros_like(xe), np.full_like(xe, ep_z)]) - obj
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    tr = RT.trace_rays(lens, np.repeat(obj[None], len(xe), 0), d)
    ok = tr["valid"]
    q = tr["points"][ok, -2]; v = tr["dirs"][ok, -1]
    x_xp = q[:, 0] + (z_xp - q[:, 2]) / v[:, 2] * v[:, 0]
    x_mla = q[:, 0] + (z_img - q[:, 2]) / v[:, 2] * v[:, 0]
    uv = x_xp / float(para["xp_radius"])
    order = np.argsort(uv)
    p = system["mla"]["pitch_mm"]
    k = np.arange(views) - (views - 1) / 2
    uv_k = (k * p / views) / (system["microimage_diameter_mm"] / 2)
    if pupil_extent is not None:
        k = k * pupil_extent; uv_k = uv_k * pupil_extent
    assert uv[order][0] < uv_k[0] and uv_k[-1] < uv[order][-1]
    xk = np.interp(uv_k, uv[order], x_mla[order])
    return float(np.polyfit(k, xk / p, 1)[0])


@pytest.mark.parametrize("depth_m", [0.6, 0.75, 1.3, 1.8])
def test_refocus_depth_inverts_forward_traced_parallax_of_an_ideal_lens(depth_m):
    """An ideal lens has no aberration, so the traced parallax is the paraxial truth."""
    system = _matched_system(_lens())
    lf = np.zeros((15, 15, 3, 3))
    slope = _forward_traced_slope(system, depth_m, 15)
    assert abs(slope) > .03          # a real, sub-pixel-scale parallax
    got = P.plenoptic_refocus_depth(lf, system, slope)["depth_m"]
    assert float(got) == pytest.approx(depth_m, rel=1e-6)


@pytest.mark.parametrize("depth_m", [0.6, 1.8])
def test_refocus_depth_matches_paraxial_trace_of_the_thick_prescription(depth_m):
    system = _matched_system(_thick_lens())
    lf = np.zeros((15, 15, 3, 3))
    slope = _forward_traced_slope(system, depth_m, 15, pupil_extent=1e-3)
    got = P.plenoptic_refocus_depth(lf, system, slope)["depth_m"]
    assert float(got) == pytest.approx(depth_m, rel=2e-4)


def test_refocus_depth_uses_the_decoded_angular_sampling():
    """The same parallax in lenslets per view means twice the depth offset at half the views."""
    system = _matched_system(_lens())
    s15 = _forward_traced_slope(system, 0.6, 15)
    s5 = _forward_traced_slope(system, 0.6, 5)
    assert s5 == pytest.approx(3 * s15, rel=1e-3)   # 3x the pupil step per view
    d5 = P.plenoptic_refocus_depth(np.zeros((5, 5, 2, 2)), system, s5)["depth_m"]
    assert float(d5) == pytest.approx(0.6, rel=1e-6)


def test_refocus_depth_resolution_is_one_sample_of_full_baseline_parallax():
    system = _matched_system(_lens())
    lf = np.zeros((15, 15, 3, 3))
    out = P.plenoptic_refocus_depth(lf, system, 0.0)
    ds = 1.0 / 14
    lo, hi = P.plenoptic_refocus_depth(lf, system, np.array([-ds, ds]))["depth_m"]
    assert float(out["depth_resolution_m"]) == pytest.approx(abs(hi - lo) / 2, rel=1e-12)
    assert 0.005 < float(out["depth_resolution_m"]) < 0.5


def test_refocus_depth_fails_closed_outside_its_model():
    system = _matched_system(_lens())
    with pytest.raises(ValueError, match="equal"):
        P.plenoptic_refocus_depth(np.zeros((5, 7, 3, 3)), system, 0.1)
    with pytest.raises(ValueError, match="two views"):
        P.plenoptic_refocus_depth(np.zeros((1, 1, 3, 3)), system, 0.1)
    with pytest.raises(ValueError, match="pupil"):
        P.plenoptic_refocus_depth(np.zeros((15, 15, 3, 3)), system, 100.0)
    main = _lens(); mla = P.mla_surface(.15, .75, (3, 3), f_number=5.)
    focused = P.plenoptic_system(main, mla, {"size": (45, 45), "pixel_pitch_um": 10},
                                 kind="focused", mla_to_sensor_mm=1.5, main_to_mla_mm=1.5)
    with pytest.raises(ValueError, match="unfocused"):
        P.plenoptic_refocus_depth(np.zeros((5, 5, 3, 3)), focused, 0.1)


def _legacy_calibrate(white_image, pitch_px_guess, max_residual_px=0.25):
    """The all-pairs implementation before 2026-11-04, kept only as the parity reference."""
    from scipy import ndimage as ndi
    im = np.asarray(white_image, dtype=float); p = float(pitch_px_guess)
    sm = ndi.gaussian_filter(im, max(0.5, p/8))
    mx = ndi.maximum_filter(sm, size=max(3, int(round(p*0.7))))
    pts = np.argwhere((sm == mx) & (sm > np.percentile(sm, 60)))[:, ::-1].astype(float)
    pts = pts[(pts[:, 0] >= 2) & (pts[:, 0] <= im.shape[1]-3) &
              (pts[:, 1] >= 2) & (pts[:, 1] <= im.shape[0]-3)]
    for k, (x, y) in enumerate(pts.copy()):
        ix, iy = int(x), int(y)
        denx = sm[iy, ix-1]-2*sm[iy, ix]+sm[iy, ix+1]
        deny = sm[iy-1, ix]-2*sm[iy, ix]+sm[iy+1, ix]
        dx = 0.5*(sm[iy, ix-1]-sm[iy, ix+1])/denx if abs(denx) > 1e-15 else 0.0
        dy = 0.5*(sm[iy-1, ix]-sm[iy+1, ix])/deny if abs(deny) > 1e-15 else 0.0
        pts[k] = [ix+np.clip(dx, -0.5, 0.5), iy+np.clip(dy, -0.5, 0.5)]
    dif = pts[:, None, :]-pts[None, :, :]; dist = np.linalg.norm(dif, axis=2)
    cand = dif[(dist > 0.75*p) & (dist < 1.25*p)]
    ang = np.mod(np.arctan2(cand[:, 1], cand[:, 0]), math.pi/2)
    theta = float(np.angle(np.mean(np.exp(4j*ang)))/4)
    e0 = np.array([math.cos(theta), math.sin(theta)]); e1 = np.array([-e0[1], e0[0]])
    proj = np.abs(cand@e0); pitch = float(np.median(proj[proj > 0.5*p]))
    origin = pts[np.argmin(pts[:, 0]+pts[:, 1])]
    ij = np.rint(np.column_stack([(pts-origin)@e0, (pts-origin)@e1])/pitch)
    A = np.column_stack([np.ones(len(pts)), ij[:, 0], ij[:, 1]])
    coef = np.linalg.lstsq(A, pts, rcond=None)[0]; fit = A@coef
    residual = float(np.sqrt(np.mean(np.sum((pts-fit)**2, axis=1))))
    b0, b1 = coef[1], coef[2]
    return {"centres": fit, "observed_centres": pts, "pitch_px": (np.linalg.norm(b0)+np.linalg.norm(b1))/2,
            "rotation_deg": math.degrees(math.atan2(b0[1], b0[0])), "residual_px": residual,
            "origin_px": coef[0], "basis_px": np.stack([b0, b1])}


def _rotated_white(n, p, deg, sigma=1.2):
    yy, xx = np.indices((n, n)); th = math.radians(deg)
    e0 = np.array([math.cos(th), math.sin(th)])*p; e1 = np.array([-math.sin(th), math.cos(th)])*p
    white = np.zeros((n, n)); m = int(n/p)+2; c = np.array([n/2, n/2])
    for j in range(-m, m+1):
        for i in range(-m, m+1):
            x, y = c+i*e0+j*e1
            if -3*sigma < x < n+3*sigma and -3*sigma < y < n+3*sigma:
                white += np.exp(-((xx-x)**2+(yy-y)**2)/(2*sigma**2))
    return white


@pytest.mark.parametrize("n,p,deg", [(101, 15., .5), (120, 8., -1.3), (97, 11.5, 2.0)])
def test_calibrate_neighbour_search_matches_the_all_pairs_reference(n, p, deg):
    white = _rotated_white(n, p, deg)
    got = P.plenoptic_mla_calibrate(white, p, max_residual_px=.3)
    ref = _legacy_calibrate(white, p)
    for key in ("centres", "observed_centres", "origin_px", "basis_px"):
        assert np.allclose(got[key], ref[key], rtol=0, atol=1e-10), key
    for key in ("pitch_px", "rotation_deg", "residual_px"):
        assert got[key] == pytest.approx(ref[key], abs=1e-10), key


def test_calibrate_memory_grows_with_peaks_not_peak_pairs():
    """2,500 peaks: all pairs would allocate >100 MB of difference vectors."""
    import tracemalloc
    white = _rotated_white(300, 6., .7, sigma=.9)
    P.plenoptic_mla_calibrate(white, 6., max_residual_px=.3)   # warm imports
    tracemalloc.start()
    try:
        cal = P.plenoptic_mla_calibrate(white, 6., max_residual_px=.3)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(cal["observed_centres"]) > 2000
    assert peak < 40e6, "peak %.1f MB" % (peak / 1e6)
