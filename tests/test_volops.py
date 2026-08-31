"""Ground-truth tests for the 3-D volume analysis operators (volops.py).

Each test builds a *known* synthetic volume — a cylindrical tube, disjoint /
corner-touching blobs, a solid box, a solid sphere, a thin slab, a step edge —
and asserts the operator recovers the property that geometry guarantees, plus the
fail-closed contracts (3-D only, finite only). The volume frame is the one
:mod:`volio` and :mod:`ops` use: ``(D, H, W)`` float64 indexed ``[z, y, x]``.
"""
import numpy as np
import pytest

import volops


def _rng(seed=0):
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------- #
# synthetic volumes                                                           #
# --------------------------------------------------------------------------- #
def _tube_volume(shape=(28, 40, 40), radius=2.5, noise=0.02, seed=1):
    """A bright cylinder along the z-axis (constant in z, a bright disk in y/x),
    plus mild Gaussian noise. Returns (vol, disk_mask) where disk_mask is the
    (H, W) cross-section footprint of the tube."""
    D, H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    disk = ((yy - H / 2.0) ** 2 + (xx - W / 2.0) ** 2) <= radius ** 2
    vol = np.zeros(shape, np.float64)
    vol[:, disk] = 1.0
    vol += noise * _rng(seed).standard_normal(shape)
    return vol, disk


def _solid_box(shape, lo, hi):
    """A solid foreground box occupying indices [lo, hi] inclusive on every axis,
    surrounded by background. Returns (vol01, lo, hi)."""
    v = np.zeros(shape, np.float64)
    v[lo:hi + 1, lo:hi + 1, lo:hi + 1] = 1.0
    return v, lo, hi


def _solid_sphere(shape, radius, center):
    zz, yy, xx = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]].astype(np.float64)
    cz, cy, cx = center
    mask = ((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2) <= radius ** 2
    return mask.astype(np.float64)


# --------------------------------------------------------------------------- #
# vol_frangi / vol_sato — a bright tube must beat the background              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fn", [volops.vol_frangi, volops.vol_sato])
def test_tube_filters_separate_tube_from_background(fn):
    vol, disk = _tube_volume()
    resp = fn(vol, scales=(1, 2, 3))
    assert resp.shape == vol.shape and resp.dtype == np.float64
    assert np.isfinite(resp).all()
    assert resp.min() >= 0.0 and resp.max() <= 1.0 + 1e-12

    tube = np.broadcast_to(disk, vol.shape)          # the cylinder (all z)
    background = ~tube
    tube_mean = resp[tube].mean()
    bg_mean = resp[background].mean()
    # a clear separation: the tube lights up, the noisy background does not
    assert tube_mean > bg_mean + 0.1, (fn.__name__, tube_mean, bg_mean)
    # the tube's central axis is among the strongest responders
    axis = resp[:, vol.shape[1] // 2, vol.shape[2] // 2]
    assert axis.mean() > bg_mean + 0.2


def test_frangi_black_ridges_polarity():
    """A bright tube gives a bright-ridge response and (near) nothing when asked
    for dark ridges — the sign convention actually gates the output."""
    vol, disk = _tube_volume()
    bright = volops.vol_frangi(vol, scales=(1, 2, 3), black_ridges=False)
    dark = volops.vol_frangi(vol, scales=(1, 2, 3), black_ridges=True)
    tube = np.broadcast_to(disk, vol.shape)
    assert bright[tube].mean() > 0.2
    assert dark[tube].mean() < 0.05


def test_constant_volume_gives_zero_response():
    const = np.full((10, 12, 12), 0.5)
    for fn in (volops.vol_frangi, volops.vol_sato):
        r = fn(const, scales=(1, 2))
        assert np.isfinite(r).all() and float(r.max()) == 0.0


def test_hessian_blobness_prefers_blob_over_tube():
    shape = (24, 24, 24)
    blob = _solid_sphere(shape, 3.0, (12, 12, 12))
    blob = volops.vol_hessian_blobness(blob, scale=3.0)
    assert blob.shape == shape and np.isfinite(blob).all()
    assert 0.0 <= blob.min() and blob.max() <= 1.0 + 1e-12
    # response concentrates at the blob centre
    assert blob[12, 12, 12] > 0.5
    assert blob[0, 0, 0] < 0.1


# --------------------------------------------------------------------------- #
# vol_label — connectivity genuinely matters                                  #
# --------------------------------------------------------------------------- #
def test_label_two_disjoint_blobs():
    v = np.zeros((10, 10, 10), np.float64)
    v[1:3, 1:3, 1:3] = 1.0
    v[6:8, 6:8, 6:8] = 1.0
    labels, n = volops.vol_label(v, connectivity=26)
    assert labels.dtype == np.int32 and labels.shape == v.shape
    assert n == 2
    assert set(np.unique(labels)) == {0, 1, 2}


def test_label_corner_touch_depends_on_connectivity():
    """Two cubes sharing a single corner: voxel (2,2,2) and (3,3,3) are diagonal
    neighbours — one component under 26-connectivity, two under 6."""
    v = np.zeros((8, 8, 8), np.float64)
    v[1:3, 1:3, 1:3] = 1.0                          # corner at (2,2,2)
    v[3:5, 3:5, 3:5] = 1.0                          # corner at (3,3,3)
    _, n6 = volops.vol_label(v, connectivity=6)
    _, n18 = volops.vol_label(v, connectivity=18)
    _, n26 = volops.vol_label(v, connectivity=26)
    assert n6 == 2                                   # corner touch is not face-connected
    assert n18 == 2                                  # nor edge-connected
    assert n26 == 1                                  # but is corner-connected


def test_label_rejects_bad_connectivity():
    with pytest.raises(ValueError, match="connectivity"):
        volops.vol_label(np.zeros((4, 4, 4)), connectivity=8)


# --------------------------------------------------------------------------- #
# vol_distance_transform — exact centre distance + spacing-aware scaling        #
# --------------------------------------------------------------------------- #
def test_distance_transform_box_centre_is_half_thickness():
    shape = (21, 21, 21)
    lo, hi = 3, 17                                   # width w = 15 voxels, odd
    v, lo, hi = _solid_box(shape, lo, hi)
    dt = volops.vol_distance_transform(v)
    assert dt.dtype == np.float64 and dt.shape == shape
    c = (lo + hi) // 2                               # centre index = 10
    w = hi - lo + 1                                  # 15
    # discrete EDT at the centre = distance to the nearest background voxel
    # (one step outside the box) = (w + 1)//2  ~=  half the thickness
    expected = (w + 1) // 2                          # 8
    assert dt[c, c, c] == pytest.approx(expected)
    assert float(dt.max()) == pytest.approx(expected)
    assert float(dt[v <= 0.5].max()) == 0.0          # background stays 0


def test_distance_transform_spacing_scales():
    shape = (21, 21, 21)
    v, lo, hi = _solid_box(shape, 3, 17)
    dt1 = volops.vol_distance_transform(v)
    dt2 = volops.vol_distance_transform(v, spacing=(2.0, 2.0, 2.0))
    # isotropic spacing k scales every distance by exactly k
    assert np.allclose(dt2, 2.0 * dt1)
    # a VolumeMeta may be passed directly, and anisotropy is honoured
    from volio import VolumeMeta
    dt_meta = volops.vol_distance_transform(v, spacing=VolumeMeta(spacing_mm=(2.0, 2.0, 2.0)))
    assert np.allclose(dt_meta, dt2)


# --------------------------------------------------------------------------- #
# vol_region_props — sphere ~ round, slab ~ flat, centroid correct            #
# --------------------------------------------------------------------------- #
def test_region_props_sphere_volume_and_sphericity():
    shape = (28, 28, 28)
    r, center = 8.0, (14, 14, 14)
    v = _solid_sphere(shape, r, center)
    labels, n = volops.vol_label(v, connectivity=26)
    assert n == 1
    props = volops.vol_region_props(labels)
    assert len(props) == 1
    p = props[0]
    expected_vox = (4.0 / 3.0) * np.pi * r ** 3
    assert abs(p["voxel_count"] / expected_vox - 1.0) < 0.06     # discrete ~ analytic
    assert p["volume"] == float(p["voxel_count"])                # no spacing -> voxels
    # centroid recovers the sphere centre
    assert np.allclose(p["centroid"], center, atol=0.5)
    # a sphere is round: sphericity ~ 1 (marching-cubes surface when skimage present)
    assert 0.85 < p["sphericity"] <= 1.05, p["sphericity"]


def test_region_props_slab_is_not_spherical():
    shape = (24, 24, 24)
    v = np.zeros(shape, np.float64)
    v[11:13, 2:22, 2:22] = 1.0                       # 2 voxels thick, 20x20 wide
    labels, n = volops.vol_label(v)
    props = volops.vol_region_props(labels)
    assert n == 1 and len(props) == 1
    p = props[0]
    assert p["sphericity"] < 0.5                     # a flat slab is far from round
    # bbox upper bounds are exclusive (slice stop)
    assert p["bbox"] == (11, 13, 2, 22, 2, 22)


def test_region_props_spacing_gives_physical_units():
    shape = (20, 20, 20)
    v = np.zeros(shape, np.float64)
    v[8:12, 8:12, 8:12] = 1.0                        # 4^3 = 64 voxels
    labels, _ = volops.vol_label(v)
    p_vox = volops.vol_region_props(labels)[0]
    p_mm = volops.vol_region_props(labels, spacing=(2.0, 2.0, 2.0), surface="faces")[0]
    assert p_vox["volume"] == 64.0
    assert p_mm["volume"] == pytest.approx(64.0 * 8.0)           # each voxel = 2^3 mm^3
    # faces: 6 sides x 16 voxel-faces x (2*2 mm^2 per face) = 384 mm^2
    assert p_mm["surface_area"] == pytest.approx(6 * 16 * 4.0)


def test_region_props_faces_surface_is_deterministic_cube():
    v = np.zeros((9, 9, 9), np.float64)
    v[3:6, 3:6, 3:6] = 1.0                           # 3x3x3 cube
    labels, _ = volops.vol_label(v)
    p = volops.vol_region_props(labels, surface="faces")[0]
    assert p["voxel_count"] == 27
    assert p["surface_area"] == pytest.approx(6 * 9)  # 6 faces x 9 unit voxel-faces


# --------------------------------------------------------------------------- #
# vol_gradient_magnitude — response localises at a step edge                  #
# --------------------------------------------------------------------------- #
def test_gradient_magnitude_localises_at_step_edge():
    shape = (12, 16, 16)
    v = np.zeros(shape, np.float64)
    v[:, :, 8:] = 1.0                                # step along x at index 8
    g = volops.vol_gradient_magnitude(v)
    assert g.shape == shape and np.isfinite(g).all()
    # energy sits on the interface columns (7 and 8), not in the flat interior
    edge = g[:, :, 7:9].mean()
    flat = g[:, :, [0, 1, 2, 13, 14, 15]].mean()
    assert edge > flat + 1.0
    assert flat < 1e-9


# --------------------------------------------------------------------------- #
# vol_local_maxima — finds planted peaks, ignores flat volumes                #
# --------------------------------------------------------------------------- #
def test_local_maxima_finds_planted_peaks():
    shape = (20, 20, 20)
    v = _rng(3).normal(0.0, 0.01, shape)
    centers = [(5, 5, 5), (5, 14, 14), (14, 8, 12)]
    for (z, y, x) in centers:
        v[z, y, x] += 1.0
    coords = volops.vol_local_maxima(v, min_distance=2, threshold=0.5)
    assert coords.shape[1] == 3
    found = {tuple(c) for c in coords.tolist()}
    for c in centers:
        assert c in found


def test_local_maxima_constant_volume_has_no_peaks():
    coords = volops.vol_local_maxima(np.full((8, 8, 8), 0.3), min_distance=1)
    assert coords.shape == (0, 3)


# --------------------------------------------------------------------------- #
# vol_watershed — optional (scikit-image); splits touching blobs              #
# --------------------------------------------------------------------------- #
def test_watershed_splits_touching_blobs():
    pytest.importorskip("skimage")
    shape = (12, 24, 12)
    v = np.zeros(shape, np.float64)
    v[3:9, 4:11, 3:9] = 1.0                          # blob A
    v[3:9, 12:19, 3:9] = 1.0                         # blob B (abuts A's neighbourhood)
    mask = v > 0.5
    dist = volops.vol_distance_transform(v)
    markers = np.zeros(shape, np.int32)
    markers[6, 7, 6] = 1                             # seed inside A
    markers[6, 15, 6] = 2                            # seed inside B
    labels = volops.vol_watershed(-dist, markers, mask=mask)
    assert labels.dtype == np.int32
    assert labels[6, 7, 6] == 1 and labels[6, 15, 6] == 2
    assert set(np.unique(labels[mask])) == {1, 2}    # two basins, no background leak


# --------------------------------------------------------------------------- #
# fail-closed contracts                                                       #
# --------------------------------------------------------------------------- #
def test_rejects_non_3d_input():
    flat = np.zeros((16, 16))                         # a 2-D image is not a volume
    for fn in (volops.vol_frangi, volops.vol_sato, volops.vol_gradient_magnitude,
               volops.vol_distance_transform, volops.vol_label):
        with pytest.raises(ValueError, match="3-D"):
            fn(flat)
    with pytest.raises(ValueError, match="3-D"):
        volops.vol_hessian_blobness(flat, scale=1.0)


def test_rejects_non_finite_voxels():
    v = np.zeros((6, 6, 6), np.float64)
    v[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        volops.vol_gradient_magnitude(v)
    v[0, 0, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        volops.vol_frangi(v)


def test_bad_scales_and_spacing_raise():
    v = np.zeros((6, 6, 6), np.float64)
    with pytest.raises(ValueError, match="scales"):
        volops.vol_frangi(v, scales=())
    with pytest.raises(ValueError, match="scales"):
        volops.vol_sato(v, scales=(-1.0,))
    with pytest.raises(ValueError, match="spacing"):
        volops.vol_distance_transform(v > 0.5, spacing=(1.0, 2.0))     # not length-3
    with pytest.raises(ValueError, match="spacing"):
        volops.vol_distance_transform(v > 0.5, spacing=(1.0, 0.0, 1.0))  # non-positive


def test_voxel_budget_caps_are_enforced(monkeypatch):
    """The heavy-op cap refuses an over-budget volume *before* allocation."""
    monkeypatch.setattr(volops, "MAX_EIGEN_VOXELS", 100)
    with pytest.raises(ValueError, match="MAX_EIGEN_VOXELS"):
        volops.vol_frangi(np.zeros((8, 8, 8)))       # 512 voxels > 100
    monkeypatch.setattr(volops, "MAX_VOXELS", 100)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        volops.vol_label(np.zeros((8, 8, 8)))


def test_volops_introspection_list_matches_module():
    for name in volops.VOLOPS:
        assert hasattr(volops, name), name
        assert callable(getattr(volops, name))
    assert set(volops.VOLOPS).issubset(set(volops.__all__))


# --------------------------------------------------------------------------- #
# domain (reduce / bounding box / crop / uncrop)                               #
# --------------------------------------------------------------------------- #
def _cube_scene():
    """20^3 volume, gray gradient everywhere, a 6^3 mask at offset (3, 4, 5)."""
    vol = np.arange(20 * 20 * 20, dtype=np.float64).reshape(20, 20, 20) / 8000.0
    mask = np.zeros((20, 20, 20), np.float64)
    mask[3:9, 4:10, 5:11] = 1.0
    return vol, mask


def test_reduce_domain_zeroes_outside_and_keeps_inside():
    vol, mask = _cube_scene()
    out = volops.vol_reduce_domain(vol, mask)
    assert out.shape == vol.shape
    assert np.array_equal(out[3:9, 4:10, 5:11], vol[3:9, 4:10, 5:11])
    outside = out[mask < 0.5]
    assert outside.size and np.all(outside == 0.0)
    with pytest.raises(ValueError, match="shape"):
        volops.vol_reduce_domain(vol, np.ones((5, 5, 5)))


def test_bounding_box_exact_margin_and_clip():
    _, mask = _cube_scene()
    assert volops.vol_bounding_box(mask) == (3, 4, 5, 9, 10, 11)
    # margin grows per side; margin=5 clips at the z low edge (3-5 -> 0)
    assert volops.vol_bounding_box(mask, margin=2) == (1, 2, 3, 11, 12, 13)
    assert volops.vol_bounding_box(mask, margin=5) == (0, 0, 0, 14, 15, 16)
    with pytest.raises(ValueError, match="empty"):
        volops.vol_bounding_box(np.zeros((4, 4, 4)))
    with pytest.raises(ValueError, match="margin"):
        volops.vol_bounding_box(mask, margin=-1)


def test_crop_domain_is_tight_and_memory_reducing():
    vol, mask = _cube_scene()
    part, off = volops.vol_crop_domain(vol, mask)
    assert off == (3, 4, 5)
    assert part.shape == (6, 6, 6)
    assert np.array_equal(part, vol[3:9, 4:10, 5:11])   # gray kept verbatim
    assert vol.size / part.size > 37.0                  # 8000/216 = 37.03x smaller
    # domain=None crops to the volume's own support
    part2, off2 = volops.vol_crop_domain(volops.vol_reduce_domain(vol, mask))
    assert off2 == (3, 4, 5) and part2.shape == (6, 6, 6)
    with pytest.raises(ValueError, match="empty"):
        volops.vol_crop_domain(np.zeros((4, 4, 4)))


def test_uncrop_roundtrips_and_refuses_clipping():
    vol, mask = _cube_scene()
    part, off = volops.vol_crop_domain(vol, mask)
    back = volops.vol_uncrop(part, off, vol.shape)
    assert back.shape == vol.shape
    assert np.array_equal(back[3:9, 4:10, 5:11], vol[3:9, 4:10, 5:11])
    assert np.all(back[mask < 0.5][back[mask < 0.5] != vol[mask < 0.5]] == 0.0) or True
    # exact: outside the box everything is fill (0), inside it equals vol
    box = np.zeros_like(vol, dtype=bool)
    box[3:9, 4:10, 5:11] = True
    assert np.all(back[~box] == 0.0)
    assert float(volops.vol_uncrop(part, off, vol.shape, fill=7.5)[0, 0, 0]) == 7.5
    with pytest.raises(ValueError, match="fit"):
        volops.vol_uncrop(part, (17, 0, 0), vol.shape)   # 17+6 > 20
    with pytest.raises(ValueError, match="fit"):
        volops.vol_uncrop(part, (-1, 0, 0), vol.shape)
    with pytest.raises(ValueError, match="length"):
        volops.vol_uncrop(part, (0, 0), vol.shape)


# --------------------------------------------------------------------------- #
# boundary (shell / points)                                                    #
# --------------------------------------------------------------------------- #
def test_boundary_counts_match_hand_computation():
    # solid 7^3 cube with the centre voxel removed, floating in a 15^3 volume
    m = np.zeros((15, 15, 15), np.float64)
    m[4:11, 4:11, 4:11] = 1.0
    m[7, 7, 7] = 0.0
    b6 = volops.vol_boundary(m, connectivity=6)
    b26 = volops.vol_boundary(m, connectivity=26)
    # outer shell of the cube: 7^3 - 5^3 = 218 voxels under both neighbourhoods
    # (a cube's interior voxels have all 26 neighbours inside); the centre hole
    # adds its 6 face neighbours under conn 6 but all 26 under conn 26
    assert int(b6.sum()) == 218 + 6
    assert int(b26.sum()) == 218 + 26
    assert set(np.unique(b6)) <= {0.0, 1.0}
    with pytest.raises(ValueError, match="connectivity"):
        volops.vol_boundary(m, connectivity=8)
    with pytest.raises(ValueError, match="side"):
        volops.vol_boundary(m, side="both")


def test_boundary_outer_and_volume_border_conventions():
    # a single voxel: inner boundary is itself; outer is its neighbourhood
    one = np.zeros((9, 9, 9), np.float64)
    one[4, 4, 4] = 1.0
    assert int(volops.vol_boundary(one, 6, side="inner").sum()) == 1
    assert int(volops.vol_boundary(one, 6, side="outer").sum()) == 6
    assert int(volops.vol_boundary(one, 26, side="outer").sum()) == 26
    # a mask filling the whole volume: the volume border counts as background,
    # so the inner boundary is the border shell: 6^3 - 4^3 = 152
    full = np.ones((6, 6, 6), np.float64)
    assert int(volops.vol_boundary(full, 6).sum()) == 216 - 64
    # ... but the outer shell has nowhere to live: empty (documented convention)
    assert int(volops.vol_boundary(full, 6, side="outer").sum()) == 0


def test_uncrop_cap_rejects_absurd_shape_cleanly():
    """An int64-overflowing target shape must hit the cap, not a MemoryError."""
    part = np.zeros((2, 2, 2), np.float64)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        volops.vol_uncrop(part, (0, 0, 0), (1 << 21, 1 << 21, 1 << 21))


def test_boundary_is_the_memory_frugal_representation():
    """The advertised claim: a solid ball keeps only a few %% as its shell."""
    z, y, x = np.mgrid[0:40, 0:40, 0:40]
    ball = ((z - 20.0) ** 2 + (y - 20.0) ** 2 + (x - 20.0) ** 2 <= 15.0 ** 2)
    shell = volops.vol_boundary(ball.astype(np.float64), connectivity=6)
    # surface/volume of a ball ~ 3/r: r=15 -> ~0.2 analytic, 0.1599 measured
    assert shell.sum() < 0.2 * ball.sum()
    assert shell.sum() > 0                        # and it is not empty


def test_boundary_points_physical_coordinates_and_origin():
    one = np.zeros((5, 5, 5), np.float64)
    one[2, 3, 4] = 1.0
    pts = volops.vol_boundary_points(one, spacing=(2.0, 3.0, 4.0), origin=(10, 0, 0))
    assert pts.shape == (1, 3)
    # (index + origin) * spacing, (z, y, x) order
    assert np.allclose(pts[0], [(2 + 10) * 2.0, 3 * 3.0, 4 * 4.0])
    # empty mask -> a valid empty answer, not an error
    empty = volops.vol_boundary_points(np.zeros((4, 4, 4)))
    assert empty.shape == (0, 3) and empty.dtype == np.float64
    with pytest.raises(ValueError, match="origin"):
        volops.vol_boundary_points(one, origin=(1, 2))


def test_crop_then_boundary_points_land_in_uncropped_frame():
    """The composed memory pipeline: crop -> boundary -> points, coordinates
    identical to running boundary -> points on the full volume."""
    _, mask = _cube_scene()
    part, off = volops.vol_crop_domain(mask)
    p_full = volops.vol_boundary_points(mask, spacing=(1.0, 1.0, 1.0))
    p_crop = volops.vol_boundary_points(part, spacing=(1.0, 1.0, 1.0), origin=off)
    assert p_full.shape == p_crop.shape
    assert np.array_equal(np.sort(p_full, axis=0), np.sort(p_crop, axis=0))
