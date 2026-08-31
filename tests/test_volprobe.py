"""Ground-truth tests for the 3-D virtual probe operators (volprobe.py).

Each test builds a *known* synthetic volume — a linear intensity gradient, a
step edge at a known half-integer position, slabs of known thickness — and
asserts the probe recovers the value geometry guarantees: analytic profile
values, physical (anisotropic-spacing) lengths by hand calculation, sub-voxel
edge positions, and wall thicknesses in millimetres. Plus the fail-closed
contracts (inside-the-volume endpoints only, finite only, n >= 2).
Frame convention: ``(D, H, W)`` float64 indexed ``[z, y, x]``; points are
``(z, y, x)``; spacing is ``(sz, sy, sx)``.
"""
import numpy as np
import pytest

import volprobe


# --------------------------------------------------------------------------- #
# synthetic volumes                                                           #
# --------------------------------------------------------------------------- #
def _gradient_volume(shape=(16, 8, 8)):
    """vol[z, y, x] = z — an exact linear ramp along the z axis."""
    D, H, W = shape
    return np.broadcast_to(np.arange(D, dtype=np.float64)[:, None, None],
                           shape).copy()


def _step_volume(shape=(20, 8, 8), k=10, level=1.0):
    """0 for z < k, ``level`` for z >= k: a step whose true (continuous) edge
    is at z = k - 0.5 (midpoint between the last 0-sample and first 1-sample)."""
    v = np.zeros(shape, np.float64)
    v[k:] = level
    return v


def _slab_volume(shape, spans, level=1.0):
    """Bright slabs (z-ranges ``[lo, hi)``) in a dark volume."""
    v = np.zeros(shape, np.float64)
    for lo, hi in spans:
        v[lo:hi] = level
    return v


def _z_probe(shape):
    """A probe along the z axis through the (y, x) centre, edge to edge."""
    D, H, W = shape
    return (0.0, H / 2.0, W / 2.0), (float(D - 1), H / 2.0, W / 2.0)


# --------------------------------------------------------------------------- #
# vol_profile_line                                                            #
# --------------------------------------------------------------------------- #
def test_profile_axis_ramp_matches_analytic_line():
    """The axis-aligned profile of vol[z]=z must be the analytic line z(t)."""
    vol = _gradient_volume((16, 8, 8))
    p0, p1 = _z_probe(vol.shape)
    t, vals = volprobe.vol_profile_line(vol, p0, p1)
    assert len(t) == len(vals) == 16          # default: 1 sample per voxel-step
    np.testing.assert_allclose(vals, np.arange(16, dtype=np.float64), atol=1e-12)
    np.testing.assert_allclose(t, np.arange(16, dtype=np.float64), atol=1e-12)


def test_profile_oblique_physical_length_anisotropic():
    """Hand calculation: p0=(0,0,0) -> p1=(4,3,0) under spacing (2,1,1) spans
    sqrt((4*2)^2 + (3*1)^2) = sqrt(73) mm; t_mm must end exactly there."""
    vol = np.zeros((8, 8, 8), np.float64)
    t, _ = volprobe.vol_profile_line(vol, (0, 0, 0), (4, 3, 0),
                                     spacing=(2.0, 1.0, 1.0))
    assert t[0] == 0.0
    assert np.all(np.diff(t) > 0.0)
    assert t[-1] == pytest.approx(np.sqrt(73.0), abs=1e-9)


def test_profile_spacing_accepts_volumemeta_duck():
    """Anything exposing ``spacing_mm`` (volio.VolumeMeta) works as spacing."""
    class _Meta:
        spacing_mm = (2.0, 1.0, 1.0)
    vol = np.zeros((8, 8, 8), np.float64)
    t, _ = volprobe.vol_profile_line(vol, (0, 0, 0), (4, 3, 0), spacing=_Meta())
    assert t[-1] == pytest.approx(np.sqrt(73.0), abs=1e-9)


def test_profile_explicit_n_and_rejections():
    vol = np.zeros((8, 8, 8), np.float64)
    t, vals = volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), n=29)
    assert len(t) == len(vals) == 29
    with pytest.raises(ValueError):           # n < 2
        volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), n=1)
    with pytest.raises(ValueError):           # p0 == p1: no direction
        volprobe.vol_profile_line(vol, (3, 3, 3), (3, 3, 3))
    with pytest.raises(ValueError):           # endpoint outside the volume
        volprobe.vol_profile_line(vol, (0, 0, 0), (8, 0, 0))
    with pytest.raises(ValueError):           # negative coordinate
        volprobe.vol_profile_line(vol, (-0.5, 0, 0), (7, 0, 0))
    with pytest.raises(ValueError):           # malformed spacing
        volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), spacing=(1.0, 0.0, 1.0))
    with pytest.raises(ValueError):           # invalid interpolation order
        volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), order=9)
    with pytest.raises(ValueError):           # not 3-D
        volprobe.vol_profile_line(np.zeros((8, 8)), (0, 0, 0), (7, 0, 0))


def test_profile_order_and_n_are_never_silently_truncated():
    """Regression: ``order=1.9`` used to be truncated to 1 and ``n=5.7`` to 5
    by a bare int() — a silent parameter change, against the module's own
    fail-closed contract and the volxform convention (exact integers only)."""
    vol = np.zeros((8, 8, 8), np.float64)
    with pytest.raises(ValueError, match="exact integer"):
        volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), order=1.9)
    with pytest.raises(ValueError, match="exact integer"):
        volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), n=5.7)
    # exact float integers remain accepted (2.0 == 2)
    t, vals = volprobe.vol_profile_line(vol, (0, 0, 0), (7, 0, 0), n=5.0, order=1.0)
    assert len(t) == len(vals) == 5


# --------------------------------------------------------------------------- #
# vol_edge_probe                                                              #
# --------------------------------------------------------------------------- #
def test_edge_probe_subvoxel_step_position():
    """A binary step between z=9 and z=10 has its continuous edge at z=9.5;
    the sub-sample refinement must land within 0.2 voxel of it."""
    vol = _step_volume((20, 8, 8), k=10)
    p0, p1 = _z_probe(vol.shape)
    edges = volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1)
    assert len(edges) == 1
    (e,) = edges
    assert abs(e["position"][0] - 9.5) < 0.2
    assert abs(e["t_mm"] - 9.5) < 0.2         # no spacing -> voxel units
    assert e["polarity"] == 1                 # dark -> bright along the probe
    assert e["amplitude"] >= 0.1
    # y / x of the edge point stay on the probe line
    assert e["position"][1] == pytest.approx(4.0)
    assert e["position"][2] == pytest.approx(4.0)


def test_edge_probe_polarity_filter():
    vol = _step_volume((20, 8, 8), k=10)      # one rising edge only
    p0, p1 = _z_probe(vol.shape)
    assert len(volprobe.vol_edge_probe(vol, p0, p1, polarity="positive")) == 1
    assert volprobe.vol_edge_probe(vol, p0, p1, polarity="negative") == []
    inv = 1.0 - vol                           # inverted: one falling edge
    neg = volprobe.vol_edge_probe(inv, p0, p1, polarity="negative")
    assert len(neg) == 1 and neg[0]["polarity"] == -1
    with pytest.raises(ValueError):
        volprobe.vol_edge_probe(vol, p0, p1, polarity="both")


def test_edge_probe_absolute_threshold_drops_small_edge():
    """A 1.0 step and a 0.05 step: threshold=0.1 (absolute, intensity/voxel)
    keeps only the big edge; threshold=0.01 keeps both."""
    vol = np.zeros((30, 8, 8), np.float64)
    vol[8:] = 1.0
    vol[20:] += 0.05
    p0, p1 = _z_probe(vol.shape)
    big_only = volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1)
    assert len(big_only) == 1
    assert abs(big_only[0]["position"][0] - 7.5) < 0.2
    both = volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.01)
    assert len(both) == 2
    assert abs(both[1]["position"][0] - 19.5) < 0.3
    assert both[0]["amplitude"] > both[1]["amplitude"]


# --------------------------------------------------------------------------- #
# vol_wall_thickness                                                          #
# --------------------------------------------------------------------------- #
def test_wall_thickness_single_slab_mm():
    """An 8-voxel slab probed along z with sz=2.0 mm reads 16 mm +- 0.5."""
    vol = _slab_volume((40, 8, 8), [(16, 24)])
    p0, p1 = _z_probe(vol.shape)
    th = volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.05,
                                     spacing=(2.0, 1.0, 1.0))
    assert len(th) == 1
    assert th[0] == pytest.approx(16.0, abs=0.5)


def test_wall_thickness_double_wall():
    vol = _slab_volume((60, 8, 8), [(10, 18), (30, 38)])
    p0, p1 = _z_probe(vol.shape)
    th = volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.05)
    assert len(th) == 2
    for t in th:
        assert t == pytest.approx(8.0, abs=0.5)   # voxel units without spacing


def test_wall_thickness_ignores_unpaired_trailing_edge():
    """A probe ending inside material leaves a dangling rising edge, which is
    ignored: one complete wall -> exactly one thickness."""
    vol = _slab_volume((40, 8, 8), [(10, 18)])
    vol[30:] = 1.0                            # material to the end of the probe
    p0, p1 = _z_probe(vol.shape)
    edges = volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.05)
    assert len(edges) == 3                    # rise, fall, dangling rise
    th = volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.05)
    assert len(th) == 1
    assert th[0] == pytest.approx(8.0, abs=0.5)


# --------------------------------------------------------------------------- #
# fail-closed: NaN / Inf rejected by every op                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_all_ops_reject_nonfinite(bad):
    vol = _step_volume((20, 8, 8), k=10)
    vol[3, 3, 3] = bad
    p0, p1 = _z_probe(vol.shape)
    with pytest.raises(ValueError):
        volprobe.vol_profile_line(vol, p0, p1)
    with pytest.raises(ValueError):
        volprobe.vol_edge_probe(vol, p0, p1)
    with pytest.raises(ValueError):
        volprobe.vol_wall_thickness(vol, p0, p1)
