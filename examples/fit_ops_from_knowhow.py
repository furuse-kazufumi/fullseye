"""Runnable truth-bearing examples for geometric and principal-axis fitting."""
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import fourier_shift

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import filters_freq as ff
import measure
import measure3d


def main():
    rng = np.random.default_rng(30)
    t = np.deg2rad(np.linspace(-15, 15, 80))
    arc = np.column_stack([7 + 50 * np.sin(t), -3 + 50 * np.cos(t)])
    arc += rng.normal(0, .5, arc.shape)
    algebraic = measure.fit_circle(arc)
    geometric = measure.fit_circle_geometric(arc)
    assert abs(geometric["r"] - 50) < abs(algebraic["r"] - 50)

    image = rng.normal(size=(96, 112))
    shift = np.array([2.35, -1.7])
    moved = np.fft.ifftn(fourier_shift(np.fft.fftn(image), shift)).real
    registered = ff.phase_correlation_shift(image, moved)
    assert np.linalg.norm(np.array([registered["dy"], registered["dx"]]) + shift) < .05

    x = np.linspace(-20, 20, 101)
    curve = np.column_stack([x, 3 * (x / 20) ** 2])
    a = np.deg2rad(85)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    curved_edge = (curve @ rot.T)[:, ::-1]
    curve_fit = measure.fit_curve_principal_axis(curved_edge, 2)
    assert curve_fit["rms"] < .04

    xx, yy = np.meshgrid(np.linspace(-3, 3, 13), np.linspace(-1, 1, 9))
    surface = np.column_stack([.2 * xx.ravel() - .3 * yy.ravel(), yy.ravel(), xx.ravel()])
    surf_fit = measure3d.fit_surface_principal_axes(surface, 1)
    assert abs(surf_fit["normal"] @ measure3d.fit_plane3(surface)["normal"]) > 1 - 1e-12
    print("circle radius errors:", abs(algebraic["r"] - 50), abs(geometric["r"] - 50))
    print("subpixel shift:", registered["dy"], registered["dx"])
    print("curve/surface RMS:", curve_fit["rms"], surf_fit["rms"])


if __name__ == "__main__":
    main()
