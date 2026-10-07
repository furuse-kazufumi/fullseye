"""変位の符号の規約を固定する(2026-10-07 の全体見直し)。

``phase_correlation_fft`` と ``crt_displacement`` は同じ引数順で**逆向き**の符号を返す(どちらも文書どおり)。
公開 API なので符号は変えず、取り違えが黙って起きないよう両方の向きをここで固定し、docstring で互いを指す。
"""
import numpy as np
from scipy.ndimage import gaussian_filter

from filters_freq import phase_correlation_fft
import residue


def _pair(dr, dc):
    rng = np.random.default_rng(1)
    a = gaussian_filter(rng.random((128, 128)), 2)
    return a, np.roll(a, (dr, dc), axis=(0, 1))


def test_phase_correlation_returns_the_shift_that_brings_image1_onto_image2_negated():
    a, b = _pair(3, 5)
    r = phase_correlation_fft(a, b)
    assert (r["row_shift"], r["col_shift"]) == (-3.0, -5.0)


def test_crt_displacement_returns_the_motion_from_image0_to_image1():
    a, b = _pair(0, 5)
    r = residue.crt_displacement(a, b, axis="x")
    d = np.asarray(r["d"])[32:96, 32:96]
    assert d.size > 0
    assert abs(float(np.median(d)) - 5.0) < 0.5
    a, b = _pair(-4, 0)
    d = np.asarray(residue.crt_displacement(a, b, axis="y")["d"])[32:96, 32:96]
    assert abs(float(np.median(d)) + 4.0) < 0.5


def test_docstrings_point_at_each_other():
    assert "crt_displacement" in (phase_correlation_fft.__doc__ or "")
    assert "phase_correlation_fft" in (residue.crt_displacement.__doc__ or "")
