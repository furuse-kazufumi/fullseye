"""Adversarial regressions for exact oriented-rectangle intersection."""

import math

import numpy as np
import pytest

import geometry2d
from fslib import FsValueError


def area(*args):
    return geometry2d.area_intersection_rectangle2(*args)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((0, 0, 0, 1, 1, 0, 0, .7, 1e-15, 1e-15), 4e-30),       # B1
        ((0, 0, .7, 1e-15, 1e-15, 0, 0, 0, 1, 1), 4e-30),       # B2
        ((0, 0, 0, 1e-6, 1e-6, 0, 0, .7, 1e-9, 5e-10), 2e-18), # B3
        ((1, 1, 0, 1e10, 1e10, 1, 1, .3, 1e-10, 1e-10), 4e-20),# B4
        ((0, 0, 0, 1e300, 1e299, 0, 0, .3, 1e-10, 1e-10), 4e-20),# B5
        ((0, 0, 0, 1e-25, 1e-25, 0, 0, .3, 1e-40, 1e-40), 4e-80),# B6
        ((1e300, 1e300, 0, 1, 1, 1e300, 1e300, 0, 1, 1), 4.0), # B9/B11
        ((1e15, 1e15, .3, 1e-3, 1e-3,
          1e15, 1e15, .3, 1e-3, 1e-3), 4e-6),                  # B11
        ((1e10, 1e10, 0, 1, .5, 1e10, 1e10, 0, 1, .5), 2.0), # B10
        ((0, 0, 0, 1e-100, 1e-100, 0, 0, 0, 1e100, 1e100), 4e-200),# R2
    ],
)
def test_verified_containment_and_far_centre_cases(args, expected):
    assert area(*args) == pytest.approx(expected, rel=2e-15, abs=0.0)


def test_g3_huge_separated_rectangles_are_empty():
    centre = 1e300
    assert area(0, centre, 0, 1e155, 1e155,
                0, centre + np.spacing(centre), 0, 1e155, 1e155) == 0.0


@pytest.mark.parametrize("scale", (1e-6, 1.0, 1e30))
def test_b7_b8_representable_shallow_gap_is_empty(scale):
    assert area(0, 0, 0, scale, scale,
                0, 2 * scale + 2e-9 * scale, 0, scale, scale) == 0.0


def test_b12_crossing_needles_preserve_positive_area():
    got = area(0, 0, 0, 1e-12, 1e6, 0, 0, .5, 1e-30, 1)
    if got == 0.0:
        pytest.xfail("documented normalized-thickness precision limit")
    assert got == pytest.approx(8.343318571733952e-24, rel=1e-8, abs=0.0)


@pytest.mark.parametrize("bad", (math.nan, math.inf, -math.inf))
@pytest.mark.parametrize("position", range(10))
def test_b16_nonfinite_input_fails_closed(bad, position):
    args = [0.0, 0.0, .3, 1.0, 1.0, .2, .1, .5, 1.0, 1.0]
    args[position] = bad
    with pytest.raises(FsValueError, match="area_intersection_rectangle2: non-finite input"):
        area(*args)


@pytest.mark.parametrize("ratio", (1e-1, 1e-3, 1e-10, 1e-30, 1e-100, 1e-150))
def test_nested_ratio_limit_is_symmetric(ratio):
    big = (0, 0, .2, 1.0, .8)
    small = (0, 0, .7, ratio, .5 * ratio)
    expected = 2 * ratio * ratio
    assert area(*(big + small)) == pytest.approx(expected, rel=2e-15, abs=0.0)
    assert area(*(small + big)) == pytest.approx(expected, rel=2e-15, abs=0.0)


@pytest.mark.parametrize("scale", (1e-30, 1e-6, 1.0, 1e6, 1e30))
def test_contact_gap_and_overlap_sweep(scale):
    for gap in (0.0, 1e-9 * scale, 1e-6 * scale):
        assert area(0, 0, 0, scale, scale,
                    0, 2 * scale + gap, 0, scale, scale) == 0.0
    for depth in (1e-12 * scale, 1e-9 * scale, 1e-6 * scale):
        centre = 2 * scale - depth
        got = area(0, 0, 0, scale, scale,
                   0, centre, 0, scale, scale)
        represented_depth = 2 * scale - centre
        assert got == pytest.approx(2 * scale * represented_depth, rel=1e-6)


def test_axis_aligned_and_identical_closed_forms():
    assert area(0, 0, 0, 2, 3, 1, 1, 0, 2, 3) == 15.0
    for phi in (0.0, math.pi / 2, .3, .3 + 1e-9):
        args = (4, -7, phi, 2, .5, 4, -7, phi, 2, .5)
        assert area(*args) == 4.0


def _oracle(args):
    """Independent long-double Sutherland--Hodgman reference."""
    def vertices(r, c, phi, la, lb):
        cp, sp = np.longdouble(math.cos(phi)), np.longdouble(math.sin(phi))
        centre = np.array([c, r], dtype=np.longdouble)
        u, v = np.array([cp, sp]), np.array([-sp, cp])
        return [centre + sx * la * u + sy * lb * v
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    # Translate before constructing vertices, matching the mathematical
    # coordinates represented by the two input centres without cancellation.
    dr = np.longdouble(args[5]) - np.longdouble(args[0])
    dc = np.longdouble(args[6]) - np.longdouble(args[1])
    subject = vertices(-dr / 2, -dc / 2, *args[2:5])
    clip = vertices(dr / 2, dc / 2, *args[7:])
    for a, b in zip(clip, clip[1:] + clip[:1]):
        edge = b - a
        side = lambda p: edge[0] * (p[1] - a[1]) - edge[1] * (p[0] - a[0])
        old, subject = subject, []
        if not old:
            break
        previous, previous_side = old[-1], side(old[-1])
        for current in old:
            current_side = side(current)
            if current_side >= 0:
                if previous_side < 0:
                    subject.append(previous + (current - previous) *
                                   previous_side / (previous_side - current_side))
                subject.append(current)
            elif previous_side >= 0:
                subject.append(previous + (current - previous) *
                               previous_side / (previous_side - current_side))
            previous, previous_side = current, current_side
    if len(subject) < 3:
        return 0.0
    points = np.asarray(subject)
    points -= points[0]
    return float(abs(np.dot(points[:, 0], np.roll(points[:, 1], -1)) -
                     np.dot(points[:, 1], np.roll(points[:, 0], -1))) / 2)


def test_500_random_cases_against_independent_oracle():
    rng = np.random.default_rng(20261022)
    worst = (0.0, None)
    for _ in range(500):
        scale = 10.0 ** rng.uniform(-30, 30)
        centre = rng.uniform(-1e9, 1e9) * scale
        args = (centre + rng.uniform(-2, 2) * scale,
                centre + rng.uniform(-2, 2) * scale, rng.uniform(-math.pi, math.pi),
                scale * rng.uniform(.1, 2), scale * rng.uniform(.1, 2),
                centre + rng.uniform(-2, 2) * scale,
                centre + rng.uniform(-2, 2) * scale, rng.uniform(-math.pi, math.pi),
                scale * rng.uniform(.1, 2), scale * rng.uniform(.1, 2))
        expected = _oracle(args)
        got = area(*args)
        reference = max(expected, 4 * min(args[3] * args[4], args[8] * args[9]))
        error = abs(got - expected) / reference
        worst = max(worst, (error, args), key=lambda item: item[0])
    assert worst[0] <= 1e-9, f"worst relative error {worst[0]:.3g}: {worst[1]}"


def test_500_ordinary_inputs_preserve_legacy_results():
    """The pre-rewrite clipper is the reference on well-conditioned inputs."""
    def legacy(args):
        if min(args[3], args[4], args[8], args[9]) <= 0:
            return 0.0

        def vertices(r, c, phi, la, lb):
            cp, sp = np.cos(phi), np.sin(phi)
            u, v = np.array([cp, sp]), np.array([-sp, cp])
            centre = np.array([c, r])
            return [centre + sx * la * u + sy * lb * v
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

        subject, clip = vertices(*args[:5]), vertices(*args[5:])
        eps = np.finfo(float).eps * 64
        for a, b in zip(clip, clip[1:] + clip[:1]):
            edge = b - a
            side = lambda p: edge[0] * (p[1] - a[1]) - edge[1] * (p[0] - a[0])
            old, subject = subject, []
            if not old:
                break
            previous, previous_side = old[-1], side(old[-1])
            for current in old:
                current_side = side(current)
                if current_side >= -eps:
                    if previous_side < -eps:
                        subject.append(previous + (current - previous) *
                                       previous_side / (previous_side - current_side))
                    subject.append(current)
                elif previous_side >= -eps:
                    subject.append(previous + (current - previous) *
                                   previous_side / (previous_side - current_side))
                previous, previous_side = current, current_side
        if len(subject) < 3:
            return 0.0
        points = np.asarray(subject)
        points -= points[0]
        return float(abs(np.dot(points[:, 0], np.roll(points[:, 1], -1)) -
                         np.dot(points[:, 1], np.roll(points[:, 0], -1))) / 2)

    rng = np.random.default_rng(21)
    exact = 0
    for _ in range(500):
        args = tuple(rng.uniform(-5, 5, 10) *
                     np.array([1, 1, 1, .5, .5, 1, 1, 1, .5, .5]) +
                     np.array([0, 0, 0, 1, 1, 0, 0, 0, 1, 1]) * .8)
        got, expected = area(*args), legacy(args)
        exact += got == expected
        assert got == expected or got == pytest.approx(expected, rel=1e-12, abs=1e-15)
    assert exact >= 470
