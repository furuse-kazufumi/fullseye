"""External audit regressions for the 0.7.2 maintenance release.

The reproductions were independently re-derived from data supplied by the reviewer.
"""

from unittest.mock import patch

import numpy as np
import pytest
from scipy.linalg import expm, logm

import acquire
import coherent
import mathestimation
import mathnumerics
import motionmag
import occupancy
import reconstruction


class TestB01SmallAngleSE3:
    @staticmethod
    def _generator(xi):
        A = np.zeros((4, 4))
        A[:3, :3] = mathestimation._hat(xi[3:])
        A[:3, 3] = xi[:3]
        return A

    @pytest.mark.parametrize("theta", [0.0, 1e-12, 1e-8, 1.1e-8, 1e-6, 1e-4, 1e-3, 0.1, 3.0])
    def test_exp_log_sweep_and_independent_reference(self, theta):
        xi = np.array([0.3, -0.2, 0.7, theta, 0.0, 0.0])
        T = mathestimation.se3_exp(xi)
        np.testing.assert_allclose(mathestimation.se3_log(T), xi, atol=1e-12, rtol=1e-12)
        np.testing.assert_allclose(mathestimation.se3_exp(mathestimation.se3_log(T)), T,
                                   atol=1e-12, rtol=1e-12)
        if theta >= 1e-6:
            ref = expm(self._generator(xi))
            np.testing.assert_allclose(T, ref, atol=1e-10, rtol=1e-10)
            np.testing.assert_allclose(mathestimation.se3_log(ref),
                                       np.real_if_close(logm(ref))[:3, 3].tolist() + xi[3:].tolist(),
                                       atol=1e-10, rtol=1e-10)


class TestB02NyquistAutocorrelation:
    @pytest.mark.parametrize("n", [15, 16])
    @pytest.mark.parametrize("up", [1, 2, 4])
    def test_integer_lags_match_direct_periodic_computation(self, n, up):
        y, x = np.indices((n, n))
        image = 2 + 0.25 * ((-1.0) ** x + (-1.0) ** y) + 0.2 * (
            np.cos(2 * np.pi * x / n) + np.cos(2 * np.pi * y / n))
        d = image - image.mean()
        expected = np.array([
            0.5 * (np.mean(d * np.roll(d, k, 0)) + np.mean(d * np.roll(d, k, 1)))
            / np.mean(d * d) for k in range(n // 2)
        ])
        got = coherent.speckle_statistics(image, upsample=up)["acf"][::up][:expected.size]
        np.testing.assert_allclose(got, expected, atol=1e-10, rtol=1e-10)


class TestB03FiniteInflationRadius:
    @pytest.mark.parametrize("fn", [occupancy.inflate, occupancy.inflate_obstacles])
    @pytest.mark.parametrize("radius", [np.nan, np.inf, -np.inf])
    def test_nonfinite_radius_is_rejected(self, fn, radius):
        with pytest.raises(ValueError):
            fn(np.eye(4, dtype=bool), radius)

    @pytest.mark.parametrize("radius", [0.0, 0.25, 1.0, 5.0])
    def test_finite_inflation_preserves_every_obstacle(self, radius):
        source = np.zeros((4, 5, 6), dtype=bool)
        source[2, 2, 2] = True
        assert np.all(occupancy.inflate(source, radius)[source])


class TestB04TriangulationCorrespondences:
    def test_shapes_counts_and_empty_result(self):
        P1 = np.c_[np.eye(3), np.zeros(3)]
        P2 = np.c_[np.eye(3), [-1.0, 0.0, 0.0]]
        with pytest.raises(ValueError):
            reconstruction.triangulate_points(P1, P2, [[0, 0], [.2, .1]], [[-.2, 0]])
        for bad in (np.zeros(2), np.zeros((2, 3))):
            with pytest.raises(ValueError):
                reconstruction.triangulate_points(P1, P2, bad, np.zeros((2, 2)))
        assert reconstruction.triangulate_points(P1, P2, np.empty((0, 2)),
                                                  np.empty((0, 2))).shape == (0, 3)


class TestB05RawPackedBuffers:
    @pytest.mark.parametrize("bits", [10, 12])
    @pytest.mark.parametrize("count", [1, 2, 3, 7])
    def test_bytes_memoryview_and_array_are_identical(self, bits, count):
        values = (np.arange(count, dtype=np.uint16) * 347 + 1) & ((1 << bits) - 1)
        bitstream = ((values[:, None].astype(np.uint32) >> np.arange(bits)) & 1).astype(np.uint8)
        raw = np.packbits(bitstream.ravel(), bitorder="little").tobytes()
        expected = acquire.unpack_lsb(np.frombuffer(raw, np.uint8), bits, count)
        for buf in (raw, bytearray(raw), memoryview(raw)):
            np.testing.assert_array_equal(acquire.unpack_lsb(buf, bits, count), expected)
        with pytest.raises(ValueError):
            acquire.unpack_lsb(raw[:-1], bits, count)

    def test_grouped_accepts_raw_buffer_forms(self):
        raw = bytes([1, 0x21, 3])
        expected = acquire.unpack_grouped(np.frombuffer(raw, np.uint8), 10, 2)
        for buf in (raw, bytearray(raw), memoryview(raw)):
            np.testing.assert_array_equal(acquire.unpack_grouped(buf, 10, 2), expected)


class TestB06FiniteQuadratureBounds:
    @pytest.mark.parametrize("a,b", [(0, np.inf), (-np.inf, 1), (np.nan, 1)])
    def test_quadrature_rejects_nonfinite_bounds(self, a, b):
        with pytest.raises(ValueError):
            mathnumerics.gauss_quadrature(4, a=a, b=b)

    def test_cubature_rejects_nonfinite_bounds(self):
        with pytest.raises(ValueError):
            mathnumerics.gauss_cubature(3, 2, [0, 0], [1, np.inf])


class TestB07AllocationGuardOrdering:
    def test_oversized_view_is_rejected_before_conversion(self):
        view = np.lib.stride_tricks.as_strided(np.zeros(1), (300, 1024, 1024), (0, 0, 0))
        with patch.object(motionmag.np, "ascontiguousarray",
                          side_effect=AssertionError("conversion preceded size validation")):
            with pytest.raises(ValueError):
                motionmag.motion_magnify(view, 2.0, 3.0, 5.0, 32.0)

    def test_oversized_image_is_rejected_before_conversion(self):
        view = np.lib.stride_tricks.as_strided(np.zeros(1), (4097, 4097), (0, 0))
        with patch.object(motionmag.np, "ascontiguousarray",
                          side_effect=AssertionError("conversion preceded size validation")):
            with pytest.raises(ValueError):
                motionmag.complex_steerable_decompose(view)
