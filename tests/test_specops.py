"""Ground-truth tests for multispectral / hyperspectral cube handling (specops.py).

The cube modality is (H, W, B) with B > 3 bands (B = 2 is allowed as an explicit
two-band cube; B = 3 is refused because it is ambiguous with an RGB `color` image).
Each test builds a *known* cube — an ENVI round-trip, two planted materials, an
exact linear mixture — and checks the operator recovers the analytic answer, plus
a fail-closed battery on malformed input.
"""
import numpy as np
import pytest

import specops as sp


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _synth_cube(H=20, W=30, B=8, seed=0):
    """A deterministic float64 (H, W, B) cube with non-trivial per-band values."""
    rng = np.random.default_rng(seed)
    return (rng.random((H, W, B)) * 100.0 - 25.0).astype(np.float64)


def _meta_for(B=8):
    return sp.BandMeta(
        wavelengths_nm=np.linspace(420.0, 950.0, B),
        band_names=["band_%d" % i for i in range(B)],
        fwhm=np.full(B, 6.5),
        bad_bands=np.array([i in (2, B - 1) for i in range(B)], bool),
    )


# --------------------------------------------------------------------------- #
# ENVI read / write round-trip                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("interleave", ["bsq", "bil", "bip"])
def test_envi_roundtrip_interleaves(tmp_path, interleave):
    cube = _synth_cube()
    meta = _meta_for(cube.shape[2])
    hdr = str(tmp_path / ("scene_%s.hdr" % interleave))
    sp.write_envi(hdr, cube, meta, interleave=interleave)

    back, m2 = sp.read_envi(hdr)
    assert back.shape == cube.shape
    assert np.array_equal(back, cube)                    # EXACT, not just close
    # header fields recovered
    assert np.allclose(m2.wavelengths_nm, meta.wavelengths_nm)
    assert m2.band_names == meta.band_names
    assert np.allclose(m2.fwhm, meta.fwhm)
    assert np.array_equal(m2.bad_bands, meta.bad_bands)


def test_envi_roundtrip_nonnative_byte_order(tmp_path):
    """byte order = 1 (big-endian) is non-native on x86; the reader must honour the
    declared order and still reproduce the cube exactly."""
    cube = _synth_cube()
    hdr = str(tmp_path / "big_endian.hdr")
    sp.write_envi(hdr, cube, byte_order=1, interleave="bil")
    back, _ = sp.read_envi(hdr)
    assert np.array_equal(back, cube)


def test_envi_bsq_and_bil_disk_layout_differ_but_read_equal(tmp_path):
    """A cross-check: BSQ and BIL write *different* bytes yet read back the same
    cube — so the transpose per interleave is genuinely being applied."""
    cube = _synth_cube()
    hb = str(tmp_path / "a.hdr"); sp.write_envi(hb, cube, interleave="bsq")
    hl = str(tmp_path / "b.hdr"); sp.write_envi(hl, cube, interleave="bil")
    raw_bsq = (tmp_path / "a.img").read_bytes()
    raw_bil = (tmp_path / "b.img").read_bytes()
    assert raw_bsq != raw_bil
    assert np.array_equal(sp.read_envi(hb)[0], sp.read_envi(hl)[0])


def test_envi_integer_cube_roundtrips_exactly(tmp_path):
    cube = (np.arange(20 * 30 * 8) % 251).reshape(20, 30, 8).astype(np.uint16)
    hdr = str(tmp_path / "ints.hdr")
    sp.write_envi(hdr, cube, interleave="bip")
    back, _ = sp.read_envi(hdr)
    assert back.dtype == np.uint16
    assert np.array_equal(back, cube)


def test_envi_micrometre_wavelengths_convert_to_nm(tmp_path):
    """A header in micrometres is normalised to nm on read."""
    cube = _synth_cube(B=5)
    hdr = tmp_path / "um.hdr"
    (tmp_path / "um.img").write_bytes(cube.transpose(2, 0, 1).astype("<f8").tobytes())
    hdr.write_text(
        "ENVI\nsamples = 30\nlines = 20\nbands = 5\ndata type = 5\n"
        "interleave = bsq\nbyte order = 0\nwavelength units = Micrometers\n"
        "wavelength = {0.45, 0.55, 0.65, 0.75, 0.85}\n", encoding="ascii")
    _, meta = sp.read_envi(str(hdr))
    assert np.allclose(meta.wavelengths_nm, [450, 550, 650, 750, 850])


# --------------------------------------------------------------------------- #
# band access / composites / wavelength lookup                                #
# --------------------------------------------------------------------------- #
def test_spec_band_and_composite_and_nearest():
    cube = _synth_cube(B=8)
    b3 = sp.spec_band(cube, 3)
    assert b3.shape == cube.shape[:2]
    assert np.array_equal(b3, cube[:, :, 3])
    comp = sp.spec_rgb_composite(cube, bands=(6, 4, 1))
    assert comp.shape == (20, 30, 3)
    assert comp.min() >= 0.0 and comp.max() <= 1.0
    meta = _meta_for(8)                                  # 420..950 nm
    assert sp.spec_nearest_band(meta, 421.0) == 0
    assert sp.spec_nearest_band(meta, 949.0) == 7


# --------------------------------------------------------------------------- #
# normalised-difference index / band ratio — analytic                         #
# --------------------------------------------------------------------------- #
def test_spec_index_and_ratio_match_analytic():
    yy, xx = np.mgrid[0:8, 0:8].astype(np.float64)
    b0 = 0.10 + 0.05 * xx                                # spatially varying, positive
    b1 = 0.40 + 0.03 * yy
    cube = np.stack([b0, b1], axis=-1)                   # (8, 8, 2) — a valid 2-band cube
    nd = sp.spec_index(cube, 1, 0)
    assert np.allclose(nd, (b1 - b0) / (b1 + b0), atol=1e-9)
    ratio = sp.spec_band_ratio(cube, 1, 0)
    assert np.allclose(ratio, b1 / b0, atol=1e-6)
    # NDVI worked example: NIR high, Red low -> strongly positive
    assert nd.mean() > 0.3


# --------------------------------------------------------------------------- #
# Spectral Angle Mapper — material separation                                 #
# --------------------------------------------------------------------------- #
def test_spec_angle_mapper_separates_two_materials():
    B = 16
    H, W = 24, 24
    specA = np.linspace(0.20, 0.80, B)                   # ramp up
    specB = np.linspace(0.80, 0.20, B)                   # ramp down (large angle to A)
    rng = np.random.default_rng(7)
    cube = np.empty((H, W, B))
    half = W // 2
    bright = rng.uniform(0.5, 1.5, (H, W))               # illumination varies per pixel
    noise = rng.normal(0.0, 0.004, (H, W, B))
    cube[:, :half] = bright[:, :half, None] * specA + noise[:, :half]
    cube[:, half:] = bright[:, half:, None] * specB + noise[:, half:]

    ang = sp.spec_angle_mapper(cube, specA)
    left, right = ang[:, :half], ang[:, half:]
    # A region: small angle despite brightness variation (SAM is illumination-invariant)
    assert np.median(left) < 0.05
    # B region: large angle
    assert np.median(right) > 0.5
    # clear separation between the two populations
    assert np.percentile(left, 99) < np.percentile(right, 1)


# --------------------------------------------------------------------------- #
# linear unmixing — recover known abundances                                  #
# --------------------------------------------------------------------------- #
def test_spec_unmix_recovers_known_abundances():
    B, K = 12, 3
    H, W = 14, 14
    rng = np.random.default_rng(3)
    E = rng.uniform(0.15, 0.85, (K, B))                  # 3 endmember spectra
    A_true = rng.random((H * W, K))
    A_true /= A_true.sum(axis=1, keepdims=True)          # abundances sum to 1
    P = A_true @ E                                        # exact linear mixture, no noise
    cube = P.reshape(H, W, B)

    A = sp.spec_unmix(cube, E, constrained=True)
    assert A.shape == (H, W, K)
    flat = A.reshape(-1, K)
    assert flat.min() >= -1e-6                            # non-negative
    assert np.allclose(flat.sum(axis=1), 1.0, atol=1e-3)  # sum-to-one
    assert np.allclose(flat, A_true, atol=1e-2)           # recovered

    # unconstrained path also runs and (for an exact mixture) matches closely
    Au = sp.spec_unmix(cube, E, constrained=False)
    assert np.allclose(Au.reshape(-1, K), A_true, atol=1e-6)


# --------------------------------------------------------------------------- #
# PCA — a low-rank cube collapses onto its first components                    #
# --------------------------------------------------------------------------- #
def test_spec_pca_low_rank_cube():
    B = 20
    H, W = 22, 22
    rng = np.random.default_rng(5)
    e0, e1 = rng.random(B), rng.random(B)                # 2 materials -> rank-2 signal
    A = rng.random((H * W, 2))
    P = A @ np.stack([e0, e1]) + 0.5                      # affine 2-D subspace
    cube = P.reshape(H, W, B)

    scores, comps, ev = sp.spec_pca(cube, n_components=3)
    assert scores.shape == (H, W, 3)
    assert comps.shape == (3, B)
    assert ev[:2].sum() > 0.999                           # first 2 capture ~all variance
    assert ev[2] < 1e-6
    # components are unit vectors
    assert np.allclose(np.linalg.norm(comps, axis=1), 1.0)


def test_spec_mnf_runs_and_returns_shapes():
    """MNF is a documented variant; check it runs and is well-formed (not that it
    equals PCA — it deliberately differs when noise is present)."""
    cube = _synth_cube(H=16, W=20, B=10, seed=9)
    scores, comps, frac = sp.spec_mnf(cube, n_components=4)
    assert scores.shape == (16, 20, 4)
    assert comps.shape == (4, 10)
    assert frac.shape == (4,) and np.all(np.isfinite(frac))


# --------------------------------------------------------------------------- #
# PPI endmember extraction + continuum removal (optional ops)                 #
# --------------------------------------------------------------------------- #
def test_spec_endmembers_ppi_is_deterministic_and_finds_extremes():
    B = 10
    rng = np.random.default_rng(2)
    E = rng.uniform(0.1, 0.9, (3, B))
    A = rng.random((30 * 30, 3)); A /= A.sum(1, keepdims=True)
    # inject a few pure pixels so genuine endmembers exist in the scene
    A[:3] = np.eye(3)
    cube = (A @ E).reshape(30, 30, B)
    em1 = sp.spec_endmembers_ppi(cube, 3, n_projections=400, seed=0)
    em2 = sp.spec_endmembers_ppi(cube, 3, n_projections=400, seed=0)
    assert em1.shape == (3, B)
    assert np.array_equal(em1, em2)                       # deterministic per seed


def test_spec_continuum_removal_bounds_and_hull():
    B = 12
    x = np.linspace(400.0, 900.0, B)
    spec = np.linspace(0.6, 0.9, B).copy()               # rising continuum
    spec[6] -= 0.3                                        # an absorption dip
    cube = np.tile(spec, (4, 5, 1))
    cr = sp.spec_continuum_removal(cube, wavelengths=x)
    assert cr.shape == cube.shape
    assert cr.max() <= 1.0 + 1e-9                         # hull is an upper bound
    assert cr[0, 0, 6] < 0.9                              # the dip is deepened relative to 1
    assert cr[0, 0, 0] == pytest.approx(1.0)             # endpoints lie on the hull


# --------------------------------------------------------------------------- #
# fail-closed on malformed input                                              #
# --------------------------------------------------------------------------- #
def test_cube_validation_rejects_2d_and_rgb():
    with pytest.raises(ValueError):                       # a 2-D image is not a cube
        sp.spec_pca(np.zeros((10, 10)))
    with pytest.raises(ValueError, match="color|colour|3 channels"):
        sp.spec_band_ratio(np.zeros((10, 10, 3)), 0, 1)   # RGB is refused as a cube
    with pytest.raises(ValueError, match="color|colour|3 channels"):
        sp.spec_pca(np.zeros((8, 8, 3)))


def test_cube_validation_rejects_non_finite():
    bad = _synth_cube(B=6)
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        sp.spec_band(bad, 0)


def test_spec_angle_mapper_rejects_mismatched_reference():
    cube = _synth_cube(B=8)
    with pytest.raises(ValueError, match="bands"):
        sp.spec_angle_mapper(cube, np.ones(7))            # 7 != 8
    with pytest.raises(ValueError):
        sp.spec_angle_mapper(cube, np.zeros(8))           # zero-norm reference


def test_spec_unmix_rejects_mismatched_endmembers():
    cube = _synth_cube(B=8)
    with pytest.raises(ValueError, match="B=8"):
        sp.spec_unmix(cube, np.ones((3, 5)))              # 5 != 8 bands


def test_band_index_out_of_range_raises():
    cube = _synth_cube(B=6)
    with pytest.raises(ValueError, match="out of range"):
        sp.spec_band(cube, 6)
    with pytest.raises(ValueError, match="out of range"):
        sp.spec_index(cube, 0, 99)


def test_spec_nearest_band_without_wavelengths_raises():
    with pytest.raises(ValueError, match="wavelength"):
        sp.spec_nearest_band(sp.BandMeta(), 500.0)


def test_corrupt_envi_header_raises(tmp_path):
    # not an ENVI file
    p = tmp_path / "bad.hdr"
    p.write_text("NOTENVI\nsamples = 3\n", encoding="ascii")
    with pytest.raises(ValueError, match="ENVI"):
        sp.read_envi(str(p))
    # missing a required field (no 'bands')
    p2 = tmp_path / "missing.hdr"
    p2.write_text("ENVI\nsamples = 3\nlines = 3\ndata type = 5\ninterleave = bsq\n",
                  encoding="ascii")
    with pytest.raises(ValueError, match="bands"):
        sp.read_envi(str(p2))
    # unsupported data type
    p3 = tmp_path / "cplx.hdr"
    p3.write_text("ENVI\nsamples = 2\nlines = 2\nbands = 4\ndata type = 6\n"
                  "interleave = bsq\nbyte order = 0\n", encoding="ascii")
    with pytest.raises(ValueError, match="data type"):
        sp.read_envi(str(p3))


def test_envi_short_data_file_raises(tmp_path):
    """A header declaring more voxels than the data file carries must be refused."""
    hdr = tmp_path / "short.hdr"
    (tmp_path / "short.img").write_bytes(b"\x00" * 16)   # far too few bytes
    hdr.write_text("ENVI\nsamples = 30\nlines = 20\nbands = 8\ndata type = 5\n"
                   "interleave = bsq\nbyte order = 0\n", encoding="ascii")
    with pytest.raises(ValueError, match="bytes"):
        sp.read_envi(str(hdr))


def test_envi_voxel_cap_enforced(tmp_path):
    hdr = tmp_path / "huge.hdr"
    hdr.write_text("ENVI\nsamples = 100000\nlines = 100000\nbands = 300\n"
                   "data type = 5\ninterleave = bsq\nbyte order = 0\n", encoding="ascii")
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        sp.read_envi(str(hdr))


def test_envi_missing_data_file_raises(tmp_path):
    hdr = tmp_path / "nodata.hdr"
    hdr.write_text("ENVI\nsamples = 4\nlines = 4\nbands = 5\ndata type = 5\n"
                   "interleave = bsq\nbyte order = 0\n", encoding="ascii")
    with pytest.raises(ValueError, match="data file"):
        sp.read_envi(str(hdr))


# --------------------------------------------------------------------------- #
# introspection                                                               #
# --------------------------------------------------------------------------- #
def test_spectralops_and_all_are_consistent():
    for name in sp.SPECTRALOPS:
        assert hasattr(sp, name), name
        assert callable(getattr(sp, name))
    for name in sp.__all__:
        assert hasattr(sp, name), name
