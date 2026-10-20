"""Performance batch 22 equivalence gates against the pre-change implementations."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation
from scipy.signal import fftconvolve

import regions_setops as rs
import coherent
import pxrd
import recon3d
import reconstruction as reconstruction
import tacsim
import tacdome


def _old_powder_reflections(phase, wavelength, two_theta_max=90.0):
    """Items 186/187 reference: full mesh and full reflection-by-atom matrices."""
    import math
    ph = pxrd._check_phase(phase)
    a, b, c, al, be, ga = ph["cell"]
    G, volume = pxrd._cell_metric((a, b, c, al, be, ga))
    Gs = np.linalg.inv(G)
    qmax = (2 * math.sin(math.radians(two_theta_max / 2)) / wavelength) ** 2
    hmax = [int(math.floor(math.sqrt(qmax * G[i, i]))) + 1 for i in range(3)]
    ranges = [np.arange(-m, m + 1) for m in hmax]
    H = np.stack(np.meshgrid(*ranges, indexing="ij"), -1).reshape(-1, 3)
    H = H[np.any(H != 0, axis=1)]
    q = np.einsum("ni,ij,nj->n", H, Gs, H)
    keep = q <= qmax * (1 + 1e-12)
    H, q = H[keep], q[keep]
    d = 1 / np.sqrt(q); s = 0.5 / d
    X = np.array([atom["xyz"] for atom in ph["atoms"]])
    occ = np.array([atom["occ"] for atom in ph["atoms"]])
    Bs = np.array([atom["B"] for atom in ph["atoms"]])
    types = [atom["type"] for atom in ph["atoms"]]
    cache = {element: pxrd._f0(element, s) for element in set(types)}
    fj = np.stack([cache[element] for element in types], 1) * occ[None, :] * np.exp(-np.outer(s ** 2, Bs))
    F = np.sum(fj * np.exp(2j * np.pi * (H @ X.T)), axis=1)
    F2 = np.abs(F) ** 2
    kd, kf = np.round(d, 9), np.round(F2 / max(F2.max(), 1e-300), 9)
    order = np.lexsort((kf, -kd)); groups = {}
    for i in order:
        groups.setdefault((kd[i], kf[i]), []).append(i)
    rows = []
    fmax = F2.max()
    for indices in groups.values():
        hk = H[indices]
        rep = max((tuple(int(v) for v in row) for row in hk), key=lambda row: (sum(v >= 0 for v in row), row))
        f2_value = float(F2[indices[0]])
        if f2_value >= 1e-10 * fmax:
            rows.append((float(d[indices[0]]), rep, len(indices), f2_value))
    rows.sort(key=lambda row: -row[0])
    dd = np.array([row[0] for row in rows]); f2 = np.array([row[3] for row in rows]); mult = np.array([row[2] for row in rows])
    tt = pxrd._two_theta_deg(dd, wavelength)
    return {"hkl": np.array([row[1] for row in rows]), "d": dd, "two_theta": tt,
            "multiplicity": mult, "F2": f2, "intensity": mult * f2 * pxrd._lorentz(tt, "powder"),
            "volume": volume}


def test_186_187_powder_enumeration_and_atom_sum_order_match_original():
    phase = pxrd.cubic_prototype("diamond", 5.431, ["Si"], name="phase")
    expected = _old_powder_reflections(phase, 0.5, 140.0)
    actual = pxrd.powder_reflections(phase, 0.5, 140.0)
    for key in ("hkl", "d", "two_theta", "multiplicity", "F2", "intensity"):
        assert np.array_equal(actual[key], expected[key])  # F2 equality is the 0-ulp atom-order gate.


def _old_azimuthal_integrate(image, geometry, n_bins=None, two_theta_range=None, mask=None, solid_angle=True,
                              polarization=None, chi_range=None, supersample=2):
    """Item 188 reference: the pre-slice list-and-concatenate implementation."""
    im = pxrd._image(image)
    g = pxrd._geometry(geometry)
    nb = None if n_bins is None else int(pxrd._num(n_bins, "n_bins", positive=True))
    ss = int(pxrd._num(supersample, "supersample", positive=True))
    valid = np.ones(im.shape, dtype=bool) if mask is None else ~np.asarray(mask)
    pol = None if polarization is None else pxrd._num(polarization, "polarization")
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]].astype(np.float64)
    off = (np.arange(ss) + 0.5) / ss - 0.5
    vals, tths, wts, cors = [], [], [], []
    for dy in off:
        for dx in off:
            tth, chi, om = pxrd._tth_chi(rr + dy, cc + dx, g)
            corr = np.ones_like(tth)
            if solid_angle:
                corr *= om
            if pol is not None:
                corr *= pxrd._polarization(tth, chi, pol)
            sel = valid.copy()
            if chi_range is not None:
                c0, c1 = chi_range
                sel &= (chi >= c0) & (chi < c1) if c0 < c1 else (chi >= c0) | (chi < c1)
            vals.append((im / corr)[sel]); cors.append(corr[sel]); tths.append(tth[sel])
            wts.append(np.full(int(sel.sum()), 1.0 / ss ** 2))
    val, tt, wt, cr = map(np.concatenate, (vals, tths, wts, cors))
    lo, hi = (float(tt.min()), float(tt.max())) if two_theta_range is None else two_theta_range
    if nb is None:
        nb = max(8, int(np.ceil((hi - lo) / (0.5 * np.degrees(g["pixel"] / g["distance"])))))
    edges = np.linspace(lo, hi, nb + 1)
    idx = np.searchsorted(edges, tt, side="right") - 1
    ok = (idx >= 0) & (idx < nb)
    sw = np.bincount(idx[ok], weights=wt[ok], minlength=nb)
    sv = np.bincount(idx[ok], weights=(val * wt)[ok], minlength=nb)
    sva = np.bincount(idx[ok], weights=(np.abs(val) / cr * wt)[ok], minlength=nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean, sig = sv / sw, np.sqrt(sva) / sw
    mean[sw == 0] = np.nan; sig[sw == 0] = np.nan
    return {"two_theta": (edges[1:] + edges[:-1]) * 0.5, "intensity": mean, "count": sw, "sigma": sig}


def test_188_streaming_azimuthal_integral_matches_original():
    rng = np.random.default_rng(188)
    image = rng.poisson(20, (97, 113)).astype(float)
    geometry = {"cx": 55.2, "cy": 48.7, "distance": 100.0, "pixel": 0.2, "wavelength": 1.54}
    kw = dict(n_bins=80, two_theta_range=(0.0, 20.0), polarization=0.4,
              chi_range=(-140.0, 120.0), supersample=3)
    expected = _old_azimuthal_integrate(image, geometry, **kw)
    actual = pxrd.azimuthal_integrate(image, geometry, memory_budget=32 << 20, **kw)
    for key in ("two_theta", "intensity", "count", "sigma"):
        assert np.allclose(actual[key], expected[key], rtol=1e-12, atol=1e-12, equal_nan=True)


def _old_photometric_stereo(images, light_dirs):
    I = np.stack([np.asarray(im, float) for im in images], axis=0)
    K, H, W = I.shape
    G = np.linalg.lstsq(np.asarray(light_dirs, float), I.reshape(K, -1), rcond=None)[0]
    albedo = np.linalg.norm(G, axis=0)
    return {"normals": (G / (albedo + 1e-12)).T.reshape(H, W, 3), "albedo": albedo.reshape(H, W)}


def _old_uncalibrated_photometric_stereo(images):
    I = np.stack([np.asarray(im, float) for im in images], axis=0)
    K, H, W = I.shape
    _U, S, Vt = np.linalg.svd(I.reshape(K, -1), full_matrices=False)
    B = np.diag(S[:3]) @ Vt[:3]
    albedo = np.linalg.norm(B, axis=0)
    return {"normals": (B / (albedo + 1e-12)).T.reshape(H, W, 3), "albedo": albedo.reshape(H, W)}


def test_207_208_reconstruction_default_and_variants_keep_exact_default():
    rng = np.random.default_rng(207)
    images = rng.random((12, 71, 67))
    lights = rng.normal(size=(12, 3))
    expected = _old_photometric_stereo(images, lights)
    for actual in (reconstruction.photometric_stereo(images, lights),
                   reconstruction.photometric_stereo(images, lights, chunk=257)):
        assert np.allclose(actual["normals"], expected["normals"], rtol=1e-12, atol=1e-12)
        assert np.allclose(actual["albedo"], expected["albedo"], rtol=1e-12, atol=1e-12)
    exact = reconstruction.uncalibrated_photometric_stereo(images)
    old = _old_uncalibrated_photometric_stereo(images)
    assert np.array_equal(exact["normals"], old["normals"])
    assert np.array_equal(exact["albedo"], old["albedo"])
    fast = reconstruction.uncalibrated_photometric_stereo(images, method="fast")
    assert np.allclose(fast["albedo"], old["albedo"], rtol=1e-10, atol=1e-10)


def _old_circumradii(P, simplices):
    T = P[simplices]
    p0 = T[:, 0]
    A = 2.0 * (T[:, 1:] - p0[:, None, :])
    rhs = (T[:, 1:] ** 2).sum(2) - (p0 ** 2).sum(1)[:, None]
    det = np.linalg.det(A)
    denom = np.prod(np.linalg.norm(A, axis=2), axis=1)
    rel = np.divide(np.abs(det), denom, out=np.zeros_like(det), where=denom > 0)
    radii = np.full(len(T), np.inf)
    good = rel > 1e-9
    radii[good] = np.linalg.norm(np.linalg.solve(A[good], rhs[good][..., None])[..., 0] - p0[good], axis=1)
    return radii


def test_204_blocked_circumradii_matches_original():
    rng = np.random.default_rng(204)
    points = rng.normal(size=(5000, 3))
    simplices = rng.integers(0, len(points), size=(70000, 4))
    expected = _old_circumradii(points, simplices)
    actual = recon3d._circumradii(points, simplices)
    assert np.allclose(actual, expected, rtol=1e-12, atol=1e-12, equal_nan=True)


def _old_radial_slope_profile(normals, X, Y, centre_xy, pitch):
    import photometric
    p, q = photometric.normals_to_gradients(normals)
    dx, dy = X - centre_xy[0], Y - centre_xy[1]
    r = np.hypot(dx, dy)
    with np.errstate(invalid="ignore", divide="ignore"):
        sr = np.where(r > 1e-12, (p * dx + q * dy) / np.maximum(r, 1e-15), 0.0)
    cx, cy = centre_xy
    rmax = float(min(cx - X.min(), X.max() - cx, cy - Y.min(), Y.max() - cy))
    nb = int(rmax / pitch)
    idx = np.clip((r / (rmax / nb)).astype(int), 0, nb)
    prof, cnt = np.zeros(nb + 1), np.zeros(nb + 1)
    np.add.at(prof, idx.ravel(), sr.ravel()); np.add.at(cnt, idx.ravel(), 1.0)
    prof, cnt = prof[:nb], cnt[:nb]
    prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)
    return (np.arange(nb) + 0.5) * (rmax / nb), prof, cnt


def test_213_bincount_profile_preserves_original_summation_result():
    axis = np.linspace(-0.01, 0.01, 301)
    X, Y = np.meshgrid(axis, axis)
    normals = np.dstack((-0.2 * X, -0.2 * Y, np.ones_like(X)))
    old = _old_radial_slope_profile(normals, X, Y, (0.0, 0.0), axis[1] - axis[0])
    new = tacsim._radial_slope_profile(normals, X, Y, (0.0, 0.0), axis[1] - axis[0])
    for got, want in zip(new, old):
        assert np.array_equal(got, want)


def _old_bbox(region):
    r = np.asarray(region, dtype=bool)
    if not r.any():
        return None
    rows, cols = np.where(r)
    return rows.min(), cols.min(), rows.max(), cols.max()


def _old_neighbors(regions, max_distance=1):
    masks = [np.asarray(x, dtype=bool) for x in regions]
    dilated = [binary_dilation(m, iterations=int(max_distance)) for m in masks]
    return [
        (i, j)
        for i in range(len(masks))
        for j in range(i + 1, len(masks))
        if (dilated[i] & masks[j]).any()
    ]


def _old_select(regions, reference, relation="above"):
    out = []
    for region in regions:
        spatial = rs.spatial_relation(reference, region)
        if spatial and relation in spatial["relations"]:
            out.append(region)
    return out


def _old_subset(region1, region2):
    r1 = np.asarray(region1, dtype=bool)
    return bool((r1 & ~np.asarray(region2, dtype=bool)).sum() == 0)


def _old_runs(region):
    r = np.asarray(region, dtype=bool)
    runs = []
    for row in range(r.shape[0]):
        cols = np.where(r[row])[0]
        if cols.size == 0:
            continue
        breaks = np.where(np.diff(cols) > 1)[0]
        start = 0
        for end in list(breaks) + [len(cols) - 1]:
            runs.append((row, int(cols[start]), int(cols[end])))
            start = end + 1
    return runs


def _masks():
    rng = np.random.default_rng(221)
    masks = [
        np.zeros((31, 37), bool),
        np.ones((31, 37), bool),
        np.indices((31, 37)).sum(axis=0) % 2 == 0,
        rng.random((31, 37)) < 0.03,
        rng.random((31, 37)) < 0.83,
    ]
    border = np.zeros((31, 37), bool)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    masks.append(border)
    return masks


def test_221_bbox_matches_old_on_random_structured_and_empty_masks():
    masks = _masks()
    assert masks
    for mask in masks:
        assert rs._bbox(mask) == _old_bbox(mask)


def test_222_spatial_selection_is_identity_and_order_identical():
    masks = _masks()
    for relation in ("above", "below", "left", "right"):
        expected = _old_select(masks, masks[2], relation)
        actual = rs.select_region_spatial(masks, masks[2], relation)
        assert len(actual) == len(expected)
        assert all(got is want for got, want in zip(actual, expected))


def test_223_neighbors_match_old_for_special_and_positive_iterations():
    masks = _masks()
    for distance in (-1, 0, 1, 2, 5):
        assert rs.find_neighbors(masks, distance) == _old_neighbors(masks, distance)


def test_224_subset_matches_old_on_random_structured_and_empty_masks():
    masks = _masks()
    assert masks
    for left in masks:
        for right in masks:
            assert rs.test_subset_region(left, right) is _old_subset(left, right)


def test_225_runs_match_old_including_many_transitions():
    masks = _masks()
    assert masks
    for mask in masks:
        assert rs.get_region_runs(mask) == _old_runs(mask)


def _old_depth_from_focus(images, focus_positions=None):
    from scipy.ndimage import laplace, uniform_filter

    stack = np.stack([np.asarray(image, float) for image in images], axis=0)
    measures = np.stack(
        [uniform_filter(np.abs(laplace(stack[k])), 5) for k in range(stack.shape[0])],
        axis=0,
    )
    best = np.argmax(measures, axis=0)
    depth = best.astype(float) if focus_positions is None else np.asarray(focus_positions, float)[best]
    return {"depth": depth, "index": best, "sharpness": measures.max(axis=0)}


def test_206_depth_from_focus_matches_old_including_ties_and_nan():
    rng = np.random.default_rng(206)
    images = rng.normal(size=(7, 33, 29))
    images[2, 4, 5] = np.nan
    images[3] = images[1]  # exact ties must keep the first index
    expected = _old_depth_from_focus(images, np.linspace(0.1, 0.7, len(images)))
    actual = reconstruction.depth_from_focus(images, np.linspace(0.1, 0.7, len(images)))
    assert np.array_equal(actual["index"], expected["index"])
    assert np.array_equal(actual["depth"], expected["depth"])
    assert np.array_equal(actual["sharpness"], expected["sharpness"], equal_nan=True)


def _old_select_grayvalues(image_stack, index_image):
    stack = np.stack([np.asarray(image, float) for image in image_stack], axis=0)
    idx = np.clip(np.asarray(index_image, int), 0, stack.shape[0] - 1)
    rows, cols = np.mgrid[0:idx.shape[0], 0:idx.shape[1]]
    return stack[idx, rows, cols]


def test_210_grayvalue_gather_matches_old_for_array_and_list(monkeypatch):
    rng = np.random.default_rng(210)
    stack = rng.normal(size=(9, 21, 17))
    index = rng.integers(-2, 12, size=stack.shape[1:])
    expected = _old_select_grayvalues(stack, index)
    calls = 0
    original_stack = np.stack

    def counted_stack(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_stack(*args, **kwargs)

    monkeypatch.setattr(np, "stack", counted_stack)
    assert np.array_equal(reconstruction.select_grayvalues_from_channels(stack, index), expected)
    assert calls == 0
    assert np.array_equal(reconstruction.select_grayvalues_from_channels(list(stack), index), expected)
    assert calls == 1


def _old_inverse_root(a, length, linear, tol=1e-14):
    p = linear["p"]
    low, high = 0.0, 1.0 - 1e-9

    def radius(d):
        return float(tacdome.largedef_radius_ratio(d, p)) * linear["D"] * (d * length) ** (1.0 / p)

    iterations = 0
    while high - low > tol * max(high, 1e-300) and iterations < 200:
        middle = 0.5 * (low + high)
        if radius(middle) < a:
            low = middle
        else:
            high = middle
        iterations += 1
    return 0.5 * (low + high), iterations


def test_215_inverse_scalar_evaluator_preserves_root_and_skips_public_array_path(monkeypatch):
    linear = tacdome.powerlaw_linear_contact("sphere", 8e-3, 4e5)
    for d in (1e-6, 0.03, 0.3, 0.8):
        radius = tacdome.large_deformation_contact(d * 8e-3, 8e-3, linear)["a"]
        expected_d, expected_iterations = _old_inverse_root(radius, 8e-3, linear)
        calls = 0
        original = tacdome.largedef_radius_ratio

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(tacdome, "largedef_radius_ratio", counted)
        actual = tacdome.large_deformation_inverse(radius, 8e-3, linear)
        monkeypatch.setattr(tacdome, "largedef_radius_ratio", original)
        assert actual["d"] == expected_d
        assert actual["iterations"] == expected_iterations
        assert calls == 1  # 最終結果の構築だけ。二分法の反復からは呼ばない。


def _old_acf_cuts(img, up):
    d = img - img.mean()
    spectrum = np.abs(np.fft.fft2(d)) ** 2
    out = []
    for axis in (0, 1):
        s1 = spectrum.sum(axis=1 - axis)
        n, m = s1.size, s1.size * up
        pad = np.zeros(m, dtype=np.complex128)
        half = n // 2
        pad[:half] = s1[:half]
        pad[m - (n - half):] = s1[half:]
        if n % 2 == 0:
            pad[half] = pad[m - half] = 0.5 * s1[half]
        cut = np.fft.ifft(pad).real
        out.append(cut / cut[0])
    return out


def test_196_acf_axis_fft_matches_old_2d_spectrum():
    image = np.random.default_rng(196).normal(size=(31, 28))
    old = _old_acf_cuts(image, 4)
    new = coherent._acf_cuts(image, 4)
    assert np.allclose(new[0], old[0], rtol=2e-14, atol=2e-14)
    assert np.allclose(new[1], old[1], rtol=2e-14, atol=2e-14)


def _old_alpha_boundary(P, alpha):
    from scipy.spatial import Delaunay
    simp = Delaunay(P).simplices
    keep = recon3d._circumradii(P, simp) < 1.0 / alpha
    kept = simp[keep]
    faces = np.concatenate([kept[:, [0, 1, 2]], kept[:, [0, 1, 3]],
                            kept[:, [0, 2, 3]], kept[:, [1, 2, 3]]])
    uniq, counts = np.unique(np.sort(faces, axis=1), axis=0, return_counts=True)
    return uniq[counts == 1]


def test_203_delaunay_neighbors_match_old_face_counting():
    points = np.random.default_rng(203).normal(size=(80, 3))
    assert np.array_equal(recon3d._alpha_boundary_faces(points, 0.7), _old_alpha_boundary(points, 0.7))


def _old_triangulate(P1, P2, pts1, pts2):
    out = []
    for (x1, y1), (x2, y2) in zip(pts1, pts2):
        A = np.vstack([x1 * P1[2] - P1[0], y1 * P1[2] - P1[1],
                       x2 * P2[2] - P2[0], y2 * P2[2] - P2[1]])
        X = np.linalg.svd(A)[2][-1]
        out.append(X[:3] / X[3])
    return np.asarray(out)


def test_209_batched_triangulation_matches_old_loop():
    P1 = np.c_[np.eye(3), np.zeros(3)]
    P2 = np.c_[np.eye(3), np.array([-0.2, 0.0, 0.0])]
    p1 = np.random.default_rng(209).normal(size=(64, 2))
    p2 = p1 - np.array([0.1, 0.0])
    assert np.allclose(reconstruction.triangulate_points(P1, P2, p1, p2),
                       _old_triangulate(P1, P2, p1, p2), rtol=1e-12, atol=1e-12)


def _old_render(normals, lights, albedo, ambient):
    import photometric
    return np.stack([np.asarray(photometric.render_lambertian(normals, albedo, light, ambient), float)
                     for light in lights], axis=-1)


def test_211_vector_light_render_matches_old_three_calls():
    rng = np.random.default_rng(211)
    normals = rng.normal(size=(23, 19, 3))
    lights = tacsim.membrane_lights()
    assert np.array_equal(tacsim.membrane_render_rgb(normals, lights, 0.8, 0.03),
                          _old_render(normals, lights, 0.8, 0.03))


def test_216_217_fast_radius_ratio_agrees_with_exact_path():
    d = np.r_[0.0, np.geomspace(1e-12, 0.8, 200)]
    for p in (1.0, 2.0, 1.7):
        assert np.allclose(tacdome.largedef_radius_ratio(d, p, method="fast"),
                           tacdome.largedef_radius_ratio(d, p), rtol=2e-13, atol=2e-13)
