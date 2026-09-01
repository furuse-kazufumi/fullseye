# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for gfx2d — real-time 2-D graphics.

This subject has an unusually cheap ground truth and the tests spend it. Almost
every claim here is a closed form rather than a tolerance chosen to pass:

* "over" in premultiplied colour is affine, so it is **exactly associative**;
* a blend mode has a published formula, so a hand-evaluated table of thirteen
  numbers checks the implementation against the specification and not against
  itself;
* trilinear interpolation of a coordinate function is that coordinate, so an
  identity LUT proves the interpolation before any grade is tested;
* the ordered-dither mean error has the closed bound ``0.5 / (n^2 (L-1))``,
  which is checked at 101 grey levels times 3 matrix sizes;
* nearest-neighbour palette assignment is optimal by construction, checked by
  brute force against every other palette entry.

The adversarial block then attacks the family the way this repository's
discipline asks: not for exceptions, but for **quietly wrong pictures** — the
straight/premultiplied alpha swap (whose cost is measured, not asserted away),
sRGB versus linear light, (row, col) versus (x, y), and clipping that destroys
information without saying so.
"""
import hashlib

import numpy as np
import pytest

import gfx2d as g
import opsgfx2d
import palette


# --------------------------------------------------------------------------- #
# Fixtures: deterministic, no files, no randomness outside an explicit seed.   #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260902)


def _rgb(n=32):
    return _rng().random((n, n, 3))


def _opaque(n, value=0.0):
    img = np.zeros((n, n, 4))
    img[..., :3] = value
    img[..., 3] = 1.0
    return img


def _disc(n=64, color=(1.0, 1.0, 1.0), black_outside=True):
    """A white anti-aliased disc whose transparent region is black (real assets are)."""
    s = g.sprite_synthesize("disc", n, color)
    if black_outside:
        s[..., :3] *= (s[..., 3:4] > 0)
    return s


# =========================================================================== #
# 1. The alpha convention — the centre of this family                         #
# =========================================================================== #
def test_premultiply_round_trip_is_exact_where_alpha_is_positive():
    s = g.sprite_synthesize("star", 33, "emphasis")
    back = g.unpremultiply(g.premultiply(s))
    live = s[..., 3] > 0
    assert np.abs(back[..., 3] - s[..., 3]).max() == 0.0
    assert np.abs(back[..., :3][live] - s[..., :3][live]).max() < 1e-15
    # and the documented loss: colour under alpha == 0 is gone
    assert np.all(back[..., :3][~live] == 0.0)


def test_over_is_exactly_associative_in_both_representations():
    a = g.sprite_synthesize("disc", 24, "right")
    b = g.sprite_synthesize("box", 24, "wrong")
    c = g.sprite_synthesize("star", 24, "neutral")
    left = g.alpha_composite(g.alpha_composite(a, b), c)
    right = g.alpha_composite(a, g.alpha_composite(b, c))
    assert np.abs(left - right).max() < 1e-15

    pa, pb, pc = g.premultiply(a), g.premultiply(b), g.premultiply(c)
    lp = g.alpha_composite_premul(g.alpha_composite_premul(pa, pb), pc)
    rp = g.alpha_composite_premul(pa, g.alpha_composite_premul(pb, pc))
    assert np.abs(lp - rp).max() < 1e-15


def test_over_degenerates_correctly():
    src = g.sprite_synthesize("disc", 16, "right")
    empty = np.zeros((16, 16, 4))
    # over nothing == the source, with the documented transparent-colour loss
    out = g.alpha_composite(src, empty)
    live = src[..., 3] > 0
    assert np.abs(out[..., 3] - src[..., 3]).max() == 0.0
    assert np.abs(out[..., :3][live] - src[..., :3][live]).max() < 1e-15
    # a fully transparent source leaves the backdrop alone, exactly
    dst = _opaque(16, 0.4)
    assert np.abs(g.alpha_composite(np.zeros((16, 16, 4)), dst) - dst).max() == 0.0
    # a fully opaque source replaces the backdrop, exactly
    opq = _opaque(16, 0.7)
    assert np.abs(g.alpha_composite(opq, dst) - opq).max() == 0.0


def test_alpha_convention_confusion_is_measured():
    """The headline number: what the straight/premultiplied swap actually costs.

    Both wrong answers have a closed form, and both are checked against it:

    * straight fed to a premultiplied consumer: error ``(1 - a) C_s`` — grows as
      coverage shrinks, so the halo is brightest where the object is faintest;
    * premultiplied fed to a straight consumer: error ``a (1 - a) C_s`` — bounded
      by exactly 0.25 at ``a = 0.5``.
    """
    spr = g.sprite_synthesize("disc", 64, (1.0, 1.0, 1.0))  # colour 1 everywhere
    dst = _opaque(64, 0.0)
    correct = g.alpha_composite(spr, dst)[..., :3]
    a = spr[..., 3:4]
    edge = (spr[..., 3] > 0) & (spr[..., 3] < 1)
    assert edge.sum() == 188, "the test disc changed; the quoted numbers refer to this one"

    wrong_pm = np.clip(spr[..., :3] + dst[..., :3] * (1 - a), 0, 1)
    err = np.abs(wrong_pm - correct)[edge]
    closed = (1.0 - spr[..., 3])[edge][:, None]
    assert np.abs(err - closed).max() < 1e-15, "not the closed form (1-a)*C_s"
    assert err.max() == pytest.approx(0.9375, abs=1e-12)
    assert err.mean() == pytest.approx(0.4428, abs=5e-4)

    pm = g.premultiply(spr)
    wrong_st = np.clip(pm[..., :3] * a + dst[..., :3] * (1 - a), 0, 1)
    err2 = np.abs(wrong_st - correct)[edge]
    closed2 = (spr[..., 3] * (1.0 - spr[..., 3]))[edge][:, None]
    assert np.abs(err2 - closed2).max() < 1e-15, "not the closed form a(1-a)*C_s"
    assert err2.max() == pytest.approx(0.25, abs=1e-12), "a(1-a) peaks at exactly 1/4"
    assert err2.mean() == pytest.approx(0.1590, abs=5e-4)
    # Neither wrong picture raises, and neither leaves [0, 1]. That is the point.
    assert np.all(np.isfinite(wrong_pm)) and np.all(np.isfinite(wrong_st))


def test_premultiplied_type_check_catches_only_what_it_can():
    """The runtime guard is a net, not a proof — and the docstring says so."""
    bright = g.sprite_synthesize("disc", 24, (1.0, 1.0, 1.0))
    with pytest.raises(ValueError, match="not premultiplied"):
        g.unpremultiply(bright)                     # colour > alpha at the edge: caught
    # A sprite darker than its own coverage satisfies colour <= alpha everywhere and
    # slips straight through the guard: any colour below the smallest non-zero
    # coverage on the edge (0.125 for this disc) is invisible to the check.
    dark = g.sprite_synthesize("disc", 24, (0.05, 0.05, 0.05))
    dark[..., :3] *= (dark[..., 3:4] > 0)
    assert dark[..., 3][dark[..., 3] > 0].min() == pytest.approx(0.125)
    slipped = g.unpremultiply(dark)                  # accepted, and wrong
    edge = (dark[..., 3] > 0) & (dark[..., 3] < 0.3)
    assert np.abs(slipped[..., :3][edge] - dark[..., :3][edge]).max() > 0.1, \
        "the guard let a wrong picture through, which is the point being documented"


# =========================================================================== #
# 2. Blend modes against the published formulae                               #
# =========================================================================== #
#: Hand-evaluated from *Compositing and Blending Level 1* at cb = 0.2, cs = 0.6.
#: These are literals so the test compares the code to the specification and not
#: to a second copy of itself.
_EXPECTED_BLEND = {
    "normal": 0.6,
    "multiply": 0.12,
    "screen": 0.68,
    "darken": 0.2,
    "lighten": 0.6,
    "difference": 0.4,
    "exclusion": 0.56,
    "add": 0.8,
    "hard_light": 0.36,
    "overlay": 0.24,
    "soft_light": 0.2496,
    "color_dodge": 0.5,
    "color_burn": 0.0,
}


@pytest.mark.parametrize("mode", sorted(_EXPECTED_BLEND))
def test_blend_mode_matches_the_specification(mode):
    cb = np.full((4, 4, 3), 0.2)
    cs = np.full((4, 4, 3), 0.6)
    out = g.blend_mode(cb, cs, mode)
    assert out.min() == pytest.approx(out.max(), abs=1e-15)
    assert float(out[0, 0, 0]) == pytest.approx(_EXPECTED_BLEND[mode], abs=1e-12)


def test_blend_mode_covers_every_declared_mode():
    assert set(_EXPECTED_BLEND) == set(g.BLEND_MODES)


def test_blend_mode_degeneracies_are_exact():
    base = _rgb(16)
    top = _rng().random((16, 16, 3))
    assert np.abs(g.blend_mode(base, top, "normal", 0.0) - base).max() == 0.0
    assert np.abs(g.blend_mode(base, top, "normal", 1.0) - top).max() == 0.0
    assert np.abs(g.blend_mode(base, np.ones_like(base), "multiply") - base).max() == 0.0
    assert np.abs(g.blend_mode(base, np.zeros_like(base), "screen") - base).max() == 0.0
    assert np.abs(g.blend_mode(base, np.zeros_like(base), "difference") - base).max() == 0.0
    # soft-light with a 0.5 source is the exact identity (both branches meet there)
    assert np.abs(g.blend_mode(base, np.full_like(base, 0.5), "soft_light") - base).max() < 1e-15


def test_layer_stack_reduces_to_alpha_composite():
    a = g.sprite_synthesize("disc", 20, "right")
    b = g.sprite_synthesize("box", 20, "wrong")
    stacked = g.layer_stack([{"image": a}, {"image": b}])
    assert np.abs(stacked - g.alpha_composite(b, g.alpha_composite(a, np.zeros_like(a)))).max() < 1e-15
    # a single layer over empty space keeps its own colour whatever the mode
    for mode in g.BLEND_MODES:
        one = g.layer_stack([{"image": a, "mode": mode}])
        live = a[..., 3] > 0
        assert np.abs(one[..., :3][live] - a[..., :3][live]).max() < 1e-12, mode


# =========================================================================== #
# 3. Sprites                                                                   #
# =========================================================================== #
def test_sprite_coverage_lands_on_the_supersampling_lattice():
    s = g.sprite_synthesize("disc", 40, "right")
    lattice = np.round(s[..., 3] * 16.0) / 16.0
    assert np.abs(s[..., 3] - lattice).max() < 1e-15
    # and the disc's area is the closed form to within one supersample per edge pixel
    area = s[..., 3].sum()
    assert area == pytest.approx(np.pi * 20.0 ** 2, rel=0.01)


def test_sprite_blit_places_pixels_where_the_anchor_says():
    dst = _opaque(32, 0.5)
    spr = _opaque(8, 1.0)                              # fully opaque white block
    out = g.sprite_blit(dst, spr, 4, 6, anchor="top_left")
    assert np.abs(out[6:14, 4:12, :3] - 1.0).max() == 0.0
    assert np.abs(out[0:6, :, :3] - 0.5).max() == 0.0  # nothing else moved
    centred = g.sprite_blit(dst, spr, 16, 16, anchor="center")
    assert np.abs(centred[12:20, 12:20, :3] - 1.0).max() == 0.0


def test_sprite_blit_clips_silently_and_says_so():
    dst = _opaque(16, 0.0)
    spr = _opaque(8, 1.0)
    half = g.sprite_blit(dst, spr, -4, -4)             # a quarter on screen
    assert np.abs(half[0:4, 0:4, :3] - 1.0).max() == 0.0
    assert half[5, 5, 0] == 0.0
    off = g.sprite_blit(dst, spr, 100, 100)            # entirely away
    assert np.abs(off - dst).max() == 0.0


def test_sprite_blit_flip_and_opacity():
    dst = np.zeros((8, 8, 4))
    spr = np.zeros((8, 8, 4))
    spr[0, :, 3] = 1.0                                  # a bar along the top row
    assert g.sprite_blit(dst, spr, 0, 0, flip_y=True)[7, 0, 3] == 1.0
    faded = g.sprite_blit(dst, spr, 0, 0, opacity=0.25)
    assert faded[0, 0, 3] == pytest.approx(0.25, abs=1e-15)


def test_sprite_transform_is_exact_where_it_claims_to_be():
    s = g.sprite_synthesize("star", 17, "right")
    s[0:3, 0:5, 3] = 1.0                                # break the symmetry
    assert np.abs(g.sprite_transform(s, 0.0, 1.0) - s).max() == 0.0
    rot = g.sprite_transform(s, 90.0, 1.0, "nearest", (17, 17))
    ref = np.rot90(s, -1)                               # +90 deg == clockwise on screen
    assert np.abs(rot[..., 3] - ref[..., 3]).max() == 0.0, "alpha must be an exact permutation"
    live = (rot[..., 3] > 0) & (ref[..., 3] > 0)
    assert np.abs(rot[..., :3][live] - ref[..., :3][live]).max() < 2e-16
    # four quarter turns return the original alpha exactly
    four = s
    for _ in range(4):
        four = g.sprite_transform(four, 90.0, 1.0, "nearest", (17, 17))
    assert np.abs(four[..., 3] - s[..., 3]).max() == 0.0


def test_sprite_transform_premultiplied_resampling_beats_straight_and_by_how_much():
    """Resampling straight colour bleeds transparent black into the edge."""
    from scipy import ndimage
    s = _disc(64)
    h, w = s.shape[:2]
    bg = _opaque(64, 0.5)
    worst = []
    for ang in (13.0, 37.0, 45.0):
        th = np.radians(ang)
        co, si = np.cos(th), np.sin(th)
        rr, cc = np.mgrid[0:h, 0:w].astype(float)
        cy = cx = (h - 1) / 2.0
        xs = co * (cc - cx) + si * (rr - cy) + cx
        ys = -si * (cc - cx) + co * (rr - cy) + cy
        naive = np.empty_like(s)
        for k in range(4):
            naive[..., k] = ndimage.map_coordinates(s[..., k], [ys, xs], order=1,
                                                    mode="constant")
        naive = np.clip(naive, 0.0, 1.0)
        good = g.sprite_transform(s, ang, 1.0, "bilinear", (h, w))
        d = np.abs(g.alpha_composite(naive, bg)[..., :3]
                   - g.alpha_composite(good, bg)[..., :3])
        worst.append(d.max())
        assert np.mean(naive[..., :3][naive[..., 3] > 0.02]) < \
            np.mean(good[..., :3][good[..., 3] > 0.02]), "straight resampling darkens the edge"
    assert max(worst) == pytest.approx(0.203, abs=0.01)


def test_sprite_transform_round_trip_error_is_reported_not_hidden():
    s = _disc(64)
    there = g.sprite_transform(s, 37.0, 1.0, "bilinear", (64, 64))
    back = g.sprite_transform(there, -37.0, 1.0, "bilinear", (64, 64))
    d = np.abs(back[..., 3] - s[..., 3])
    assert d.mean() == pytest.approx(0.0150, abs=2e-3)
    assert d.max() == pytest.approx(0.8125, abs=0.05)


def test_sheet_slice_and_tilemap_are_inverses():
    tiles = [g.sprite_synthesize(k, 8, c) for k, c in
             (("disc", "right"), ("box", "wrong"), ("star", "neutral"))]
    idx = np.array([[0, 1, 2], [2, 0, 1]])
    sheet = g.tilemap_render(tiles, idx)
    assert sheet.shape == (16, 24, 4)
    cut = g.sprite_sheet_slice(sheet, 8, 8)
    assert len(cut) == 6
    for k, cell in enumerate(cut):
        assert np.abs(cell - tiles[int(idx.flat[k])]).max() == 0.0


def test_sheet_slice_honours_margin_and_spacing():
    tile = g.sprite_synthesize("box", 6, "right")
    sheet = np.zeros((2 + 6 + 3 + 6 + 2, 2 + 6 + 3 + 6 + 2, 4))
    sheet[2:8, 2:8] = tile
    sheet[11:17, 11:17] = tile
    cells = g.sprite_sheet_slice(sheet, 6, 6, margin=2, spacing=3)
    assert len(cells) == 4
    assert np.abs(cells[0] - tile).max() == 0.0
    assert np.abs(cells[3] - tile).max() == 0.0
    assert cells[1].max() == 0.0


def test_tilemap_empty_cells_are_transparent():
    tile = g.sprite_synthesize("box", 4, "right")
    out = g.tilemap_render([tile], np.array([[0, -1]]))
    assert out[:, 4:].max() == 0.0
    assert np.abs(out[:, :4] - tile).max() == 0.0


def test_nine_slice_preserves_corners_and_is_the_identity_at_equal_size():
    s = g.sprite_synthesize("box", 16, "reference")
    s[0:4, 0:4, 3] = 1.0                                # a distinctive corner
    same = g.nine_slice(s, 4, 4, 4, 4, 16, 16)
    assert np.abs(same - s).max() == 0.0
    big = g.nine_slice(s, 4, 4, 4, 4, 40, 30)
    assert big.shape == (40, 30, 4)
    assert np.abs(big[0:4, 0:4] - s[0:4, 0:4]).max() == 0.0          # top-left
    assert np.abs(big[-4:, -4:] - s[-4:, -4:]).max() == 0.0          # bottom-right
    assert np.abs(big[0:4, -4:] - s[0:4, -4:]).max() == 0.0          # top-right
    assert np.abs(big[-4:, 0:4] - s[-4:, 0:4]).max() == 0.0          # bottom-left


def test_parallax_wraps_exactly():
    tile = g.sprite_synthesize("disc", 8, "right")
    layer = g.tilemap_render([tile], np.array([[0, 0], [0, 0]]))
    out = g.parallax_layers([layer], float(layer.shape[1]), [1.0])
    assert np.abs(out[..., 3] - layer[..., 3]).max() == 0.0
    live = layer[..., 3] > 0
    assert np.abs(out[..., :3][live] - layer[..., :3][live]).max() < 1e-15
    # factor 0 == a layer that does not move
    fixed = g.parallax_layers([layer], 123.0, [0.0])
    assert np.abs(fixed[..., 3] - layer[..., 3]).max() == 0.0


# =========================================================================== #
# 4. Particles — closed-form kinematics                                       #
# =========================================================================== #
def test_particle_step_matches_the_closed_form():
    st = g.particle_emit(64, 11, origin=(10.0, 20.0), speed=(5.0, 25.0))
    p0, v0 = st["pos"].copy(), st["vel"].copy()
    cur, dt, n = st, 0.02, 50
    for _ in range(n):
        cur = g.particle_step(cur, dt, gravity=(0.0, 0.0), drag=0.0)
    assert np.abs(cur["pos"] - (p0 + v0 * dt * n)).max() < 1e-11
    assert np.abs(cur["vel"] - v0).max() == 0.0
    assert cur["age"] == pytest.approx(np.full(64, dt * n), abs=1e-12)

    # drag alone is a geometric sequence, exactly
    cur, drag = st, 3.0
    for _ in range(n):
        cur = g.particle_step(cur, dt, gravity=(0.0, 0.0), drag=drag)
    assert np.abs(cur["vel"] - v0 * (1.0 - drag * dt) ** n).max() < 1e-12

    # gravity alone: v_k = k*g*dt exactly (semi-implicit Euler)
    cur = g.particle_step(st, dt, gravity=(0.0, 100.0), drag=0.0)
    assert np.abs(cur["vel"][:, 1] - (v0[:, 1] + 100.0 * dt)).max() < 1e-12


def test_particle_step_does_not_mutate_its_input():
    st = g.particle_emit(16, 3)
    before = {k: v.copy() for k, v in st.items()}
    g.particle_step(st, 0.1)
    for k, v in before.items():
        assert np.array_equal(st[k], v), f"particle_step mutated {k}"


def test_particle_emit_and_render_are_deterministic():
    a = g.particle_emit(500, 42, origin=(32.0, 32.0), size=(1.0, 4.0))
    b = g.particle_emit(500, 42, origin=(32.0, 32.0), size=(1.0, 4.0))
    for k in a:
        assert hashlib.sha256(a[k].tobytes()).hexdigest() == \
            hashlib.sha256(b[k].tobytes()).hexdigest(), k
    c = g.particle_emit(500, 43, origin=(32.0, 32.0), size=(1.0, 4.0))
    assert not np.array_equal(a["vel"], c["vel"]), "a different seed must differ"
    img1 = g.particle_render(a, 64, 64)
    img2 = g.particle_render(b, 64, 64)
    assert hashlib.sha256(img1.tobytes()).hexdigest() == \
        hashlib.sha256(img2.tobytes()).hexdigest()


def test_particle_render_drops_dead_particles():
    st = g.particle_emit(32, 5, origin=(16.0, 16.0), speed=(0.0, 0.0), life=(1.0, 1.0),
                         size=(3.0, 3.0))
    assert g.particle_render(st, 32, 32)[..., 3].max() > 0.0
    st["age"] = np.full(32, 2.0)
    assert g.particle_render(st, 32, 32).max() == 0.0


# =========================================================================== #
# 5. Lighting                                                                  #
# =========================================================================== #
def test_radial_light_centre_and_compact_support_are_exact():
    lit = g.radial_light(41, 41, 20, 20, 10.0, intensity=0.8, falloff="smooth",
                         color=(1.0, 1.0, 1.0))
    assert lit[20, 20, 0] == pytest.approx(0.8, abs=1e-15)
    assert lit[20, 0, 0] == 0.0 and lit[0, 20, 0] == 0.0
    lin = g.radial_light(41, 41, 20, 20, 10.0, falloff="linear", color=(1.0, 1.0, 1.0))
    assert lin[20, 30, 0] == pytest.approx(0.0, abs=1e-15)
    # the inverse-square falloff is honestly not compact
    inv = g.radial_light(41, 41, 20, 20, 10.0, falloff="inverse_square",
                         color=(1.0, 1.0, 1.0))
    assert inv[20, 30, 0] == pytest.approx(0.1, abs=1e-12)
    assert inv.min() > 0.0


def test_light_mask_identity_and_role_colour():
    base = _rgb(16)
    assert np.abs(g.light_mask(base, np.zeros_like(base), ambient=1.0) - base).max() == 0.0
    lit = g.radial_light(16, 16, 8, 8, 6.0, color="emphasis")
    assert np.allclose(lit[8, 8], palette.role_color("emphasis"))


def test_normal_map_shading_is_the_lambert_closed_form():
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    flat = g.normal_map_shade(n, (0.0, 0.0, 1.0), ambient=0.0, diffuse=(1.0, 1.0, 1.0))
    assert np.abs(flat - 1.0).max() < 1e-15
    # a normal tilted by theta gives cos(theta), exactly
    for deg in (30.0, 60.0, 89.0):
        th = np.radians(deg)
        tilt = np.zeros((4, 4, 3))
        tilt[..., 0] = np.sin(th)
        tilt[..., 2] = np.cos(th)
        out = g.normal_map_shade(tilt, (0.0, 0.0, 1.0), ambient=0.0, diffuse=(1.0, 1.0, 1.0))
        assert np.abs(out - np.cos(th)).max() < 1e-12
    # a light behind the surface contributes nothing (clamped, not negative)
    away = g.normal_map_shade(n, (0.0, 0.0, -1.0), ambient=0.0, diffuse=(1.0, 1.0, 1.0))
    assert away.max() == 0.0


def test_normal_map_decode_round_trips():
    n = np.zeros((6, 6, 3))
    n[..., 0], n[..., 2] = 0.6, 0.8
    enc = (n + 1.0) / 2.0
    assert np.abs(g.normal_map_decode(enc) - n).max() < 1e-15


def test_shadow_cast_is_exact_for_a_binary_occluder():
    occ = np.zeros((21, 21))
    vis = g.shadow_cast_2d(occ, 10, 0)
    assert vis.min() == 1.0 and vis.max() == 1.0, "no occluder means nothing is shadowed"
    occ[10, 10] = 1.0                                   # one blocking pixel
    vis = g.shadow_cast_2d(occ, 10, 0, steps=64)        # light directly above
    assert vis[15, 10] == 0.0, "the pixel behind the blocker must be dark"
    assert vis[5, 10] == 1.0, "the pixel between light and blocker must be lit"
    assert vis[10, 10] == 1.0, "the occluder's own light-facing surface stays lit"
    assert set(np.unique(vis)) <= {0.0, 1.0}, "a binary occluder gives a binary map"


# =========================================================================== #
# 6. Post-processing                                                          #
# =========================================================================== #
def test_bloom_identities_and_blackness():
    img = _rgb(48)
    assert np.abs(g.bloom(img, threshold=1.0) - img).max() == 0.0
    assert np.abs(g.bloom(img, intensity=0.0) - img).max() == 0.0
    assert g.bloom(np.zeros((16, 16, 3))).max() == 0.0
    assert g.bloom(img).max() >= img.max() - 1e-15, "bloom never darkens"


def test_bloom_energy_and_clipping():
    from scipy import ndimage
    blob = np.zeros((129, 129, 3))
    yy, xx = np.mgrid[0:129, 0:129]
    blob[(yy - 64) ** 2 + (xx - 64) ** 2 < 100] = 1.0
    bright = np.clip(blob - 0.8, 0.0, None) / 0.2
    blurred = ndimage.gaussian_filter(bright, (4.0, 4.0, 0.0), mode="nearest")
    assert abs(blurred.sum() - bright.sum()) / bright.sum() < 1e-14, "the blur keeps its mass"

    scene = np.clip(np.random.default_rng(5).random((128, 128, 3)) * 0.6 + 0.3, 0, 1)
    scene[40:60, 40:60] = 1.0
    raw = scene + 0.6 * ndimage.gaussian_filter(
        np.clip(scene - 0.8, 0.0, None) / 0.2, (4.0, 4.0, 0.0), mode="nearest")
    out = g.bloom(scene)
    assert np.abs(out - np.clip(raw, 0, 1)).max() < 1e-14
    clipped = 100.0 * float((raw > 1.0).mean())
    lost = 100.0 * float((raw.sum() - out.sum()) / raw.sum())
    assert clipped == pytest.approx(2.7, abs=0.3), "docstring quotes 2.7 % of pixels"
    assert lost == pytest.approx(1.7, abs=0.3), "docstring quotes 1.7 % of energy"


def test_vignette_and_chromatic_aberration_identities():
    img = _rgb(33)
    assert np.abs(g.vignette(img, strength=0.0) - img).max() == 0.0
    v = g.vignette(img, strength=0.7)
    assert np.abs(v[16, 16] - img[16, 16]).max() < 1e-15, "the centre is untouched"
    assert v[0, 0].max() < img[0, 0].max(), "the corner is darkened"
    assert np.abs(g.chromatic_aberration(img, 0.0) - img).max() == 0.0
    ca = g.chromatic_aberration(img, 0.02)
    assert np.abs(ca[..., 1] - img[..., 1]).max() == 0.0, "green is the reference channel"
    assert np.abs(ca[..., 0] - img[..., 0]).max() > 0.0


def test_film_grain_determinism_and_measured_clip_bias():
    img = np.full((256, 256, 3), 0.5)
    a = g.film_grain(img, 0.03, seed=7)
    b = g.film_grain(img, 0.03, seed=7)
    assert hashlib.sha256(a.tobytes()).hexdigest() == hashlib.sha256(b.tobytes()).hexdigest()
    assert not np.array_equal(a, g.film_grain(img, 0.03, seed=8))
    assert np.abs(g.film_grain(img, 0.0, seed=7) - img).max() == 0.0
    assert abs(a.mean() - 0.5) == pytest.approx(2.4e-4, abs=2e-4)
    bw = np.zeros((256, 256, 3))
    bw[:, 128:] = 1.0
    assert abs(g.film_grain(bw, 0.03, seed=7).mean() - bw.mean()) < 1e-3
    mono = g.film_grain(img, 0.05, seed=1, monochrome=True)
    assert np.abs(mono[..., 0] - mono[..., 2]).max() == 0.0
    assert np.abs(g.film_grain(img, 0.05, seed=1, monochrome=False)[..., 0]
                  - g.film_grain(img, 0.05, seed=1, monochrome=False)[..., 2]).max() > 0.0


def test_identity_lut_is_the_identity_which_proves_the_interpolation():
    img = _rgb(64)
    for size in (2, 5, 17, 33):
        out = g.color_grade(img, g.color_lut(size))
        assert np.abs(out - img).max() < 1e-14, f"identity LUT of side {size} is not identity"
    graded = g.color_grade(img, g.color_lut(17, gain=(1.0, 1.0, 1.0), gamma=(2.0, 2.0, 2.0)))
    assert np.abs(graded - img ** 2).max() < 5e-3, "a gamma LUT approximates x^2"
    grey = g.color_grade(img, g.color_lut(17, saturation=0.0))
    assert np.abs(grey[..., 0] - grey[..., 2]).max() < 1e-12, "saturation 0 is grey"


def test_ordered_dither_mean_error_obeys_its_closed_bound():
    worst = -1.0
    for value in np.linspace(0.0, 1.0, 101):
        for ms in (2, 4, 8):
            for levels in (2, 4):
                out = g.dither(np.full((64, 64), value), levels, "ordered", ms)
                bound = 0.5 / (ms * ms * (levels - 1))
                err = abs(float(out.mean()) - value)
                worst = max(worst, err - bound)
    assert worst <= 0.0, f"ordered dither exceeded its closed bound by {worst:.3e}"


def test_dither_lands_on_the_quantisation_lattice_and_preserves_the_ramp_mean():
    ramp = np.tile(np.linspace(0.0, 1.0, 128), (128, 1))
    for method in ("ordered", "floyd_steinberg"):
        for levels in (2, 4, 16):
            out = g.dither(ramp, levels, method)
            lattice = np.round(out * (levels - 1)) / (levels - 1)
            assert np.abs(out - lattice).max() < 1e-15, (method, levels)
            assert abs(out.mean() - ramp.mean()) < 2e-3, (method, levels)
    # the honest comparison quoted in the docstring: neither method dominates
    assert abs(g.dither(ramp, 2, "ordered").mean() - ramp.mean()) < 1e-15
    assert abs(g.dither(ramp, 16, "floyd_steinberg").mean() - ramp.mean()) < 1e-4


def test_dither_handles_rgba_and_keeps_alpha_on_the_lattice():
    spr = g.sprite_synthesize("disc", 32, "right")
    out = g.dither(spr, 2, "ordered")
    assert out.shape == spr.shape
    assert set(np.unique(out[..., 3])) <= {0.0, 1.0}


def test_palette_quantize_is_optimal_and_idempotent():
    img = _rgb(24)
    table = np.asarray([palette.role_color(r) for r in palette.ROLES]
                       + [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)])
    out = g.palette_quantize(img)
    # every pixel is at least as close as every other palette entry (brute force)
    chosen = np.linalg.norm(out - img, axis=2)
    for k in range(table.shape[0]):
        other = np.linalg.norm(table[k] - img, axis=2)
        assert np.all(chosen <= other + 1e-12), f"entry {k} was closer than the chosen one"
    # an image already made of palette colours comes back bit for bit
    exact = table[np.random.default_rng(2).integers(0, table.shape[0], (12, 12))]
    assert np.abs(g.palette_quantize(exact) - exact).max() == 0.0
    assert np.abs(g.palette_quantize(out) - out).max() == 0.0, "quantising twice changes nothing"


def test_viewport_is_an_exact_crop_at_unit_scale():
    img = _rgb(32)
    assert np.abs(g.viewport(img, 3, 5, 10, 8) - img[5:13, 3:13]).max() == 0.0
    rgba = g.sprite_synthesize("disc", 32, "right")
    assert g.viewport(rgba, 0, 0, 16, 16).shape == (16, 16, 4), "channel count is preserved"
    assert g.viewport(img, 0, 0, 16, 16, scale=2.0).shape == (32, 32, 3)


# =========================================================================== #
# 7. Colour space                                                             #
# =========================================================================== #
def test_srgb_round_trip_and_the_cost_of_skipping_it():
    img = _rgb(32)
    assert np.abs(g.linear_to_srgb(g.srgb_to_linear(img)) - img).max() < 1e-14
    assert g.srgb_to_linear(np.zeros((2, 2, 3))).max() == 0.0
    assert np.abs(g.srgb_to_linear(np.ones((2, 2, 3))) - 1.0).max() < 1e-15
    # alpha is left alone
    rgba = g.sprite_synthesize("disc", 16, "right")
    assert np.abs(g.srgb_to_linear(rgba)[..., 3] - rgba[..., 3]).max() == 0.0
    # the measured overshoot quoted in the module docstring
    lin = float(g.srgb_to_linear(np.full((1, 1, 3), 0.5))[0, 0, 0]) * 2.0
    correct = float(g.linear_to_srgb(np.full((1, 1, 3), min(lin, 1.0)))[0, 0, 0])
    assert correct == pytest.approx(0.6858, abs=1e-3)
    assert (1.0 - correct) / correct * 100.0 == pytest.approx(45.8, abs=0.5)


# =========================================================================== #
# 8. Adversarial: the family must fail closed, never plausibly                #
# =========================================================================== #
def test_non_finite_and_wrong_dtypes_are_rejected():
    bad = np.zeros((8, 8, 3))
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or infinity"):
        g.bloom(bad)
    bad[0, 0, 0] = np.inf
    with pytest.raises(ValueError, match="NaN or infinity"):
        g.vignette(bad)
    with pytest.raises(ValueError, match="complex"):
        g.bloom(np.zeros((8, 8, 3), dtype=complex))
    with pytest.raises(ValueError, match="masked"):
        g.bloom(np.ma.masked_array(np.zeros((8, 8, 3))))
    with pytest.raises(ValueError, match="not an image"):
        g.bloom(True)


def test_values_outside_the_unit_range_are_rejected_not_clipped():
    hot = np.full((8, 8, 3), 1.5)
    with pytest.raises(ValueError, match=r"must lie in \[0, 1\]"):
        g.vignette(hot)
    cold = np.full((8, 8, 4), -0.2)
    with pytest.raises(ValueError, match=r"must lie in \[0, 1\]"):
        g.premultiply(cold)
    # ...but a float64 pipeline landing on 1 + 1e-16 is not an error
    almost = np.full((4, 4, 3), 1.0) + 1e-16
    g.vignette(almost)


def test_images_never_broadcast():
    a = np.zeros((8, 8, 4))
    b = np.zeros((8, 1, 4))
    with pytest.raises(ValueError, match="never broadcasts"):
        g.alpha_composite(a, b)
    with pytest.raises(ValueError, match="never broadcasts"):
        g.blend_mode(np.zeros((8, 8, 3)), np.zeros((4, 4, 3)))
    with pytest.raises(ValueError, match="never broadcasts"):
        g.layer_stack([{"image": a}, {"image": np.zeros((4, 4, 4))}])


def test_wrong_channel_counts_are_named():
    with pytest.raises(ValueError, match=r"\(H, W, 4\) rgba"):
        g.premultiply(np.zeros((8, 8, 3)))
    with pytest.raises(ValueError, match=r"\(H, W, 3\) rgb"):
        g.bloom(np.zeros((8, 8, 4)))
    with pytest.raises(ValueError, match="rgb image"):
        g.vignette(np.zeros((8, 8)))


def test_unknown_string_arguments_list_what_is_known():
    with pytest.raises(ValueError, match="unknown value 'vivid_light'"):
        g.blend_mode(np.zeros((4, 4, 3)), np.zeros((4, 4, 3)), "vivid_light")
    with pytest.raises(ValueError, match="unknown value"):
        g.sprite_transform(g.sprite_synthesize("disc", 8), 10.0, 1.0, "lanczos")
    with pytest.raises(ValueError, match="unknown value"):
        g.sprite_blit(np.zeros((8, 8, 4)), np.zeros((4, 4, 4)), anchor="middle")
    with pytest.raises(ValueError, match="unknown value"):
        g.radial_light(8, 8, 4, 4, 3.0, falloff="exponential")
    with pytest.raises(ValueError, match="unknown role"):
        g.sprite_synthesize("disc", 8, "danger")
    with pytest.raises(ValueError, match="unknown scheme"):
        g.sprite_synthesize("disc", 8, "right", scheme="pastel")


def test_scalars_that_are_not_numbers_are_rejected():
    img = np.zeros((8, 8, 3))
    with pytest.raises(ValueError, match="not a number"):
        g.vignette(img, strength="0.5")
    with pytest.raises(ValueError, match="not a number"):
        g.vignette(img, strength=True)
    with pytest.raises(ValueError, match="must be <= 1"):
        g.vignette(img, strength=1.5)
    with pytest.raises(ValueError, match="must be an int"):
        g.sprite_blit(np.zeros((8, 8, 4)), np.zeros((4, 4, 4)), x=2.5)
    with pytest.raises(ValueError, match="non-negative int"):
        g.film_grain(img, 0.01, seed=1.5)
    with pytest.raises(ValueError, match="must be >= 0"):
        g.film_grain(img, 0.01, seed=-1)


def test_degenerate_geometry_is_rejected():
    spr = g.sprite_synthesize("disc", 8)
    with pytest.raises(ValueError, match="must be > 0"):
        g.sprite_transform(spr, 0.0, scale=0.0)
    with pytest.raises(ValueError, match="must be > 0"):
        g.radial_light(8, 8, 4, 4, radius=0.0)
    with pytest.raises(ValueError, match="must be >= 1"):
        g.radial_light(0, 8, 4, 4, 2.0)
    with pytest.raises(ValueError, match="must be < sprite width"):
        g.nine_slice(spr, 4, 4, 2, 2, 20, 20)
    with pytest.raises(ValueError, match="smaller than the borders"):
        g.nine_slice(g.sprite_synthesize("box", 16), 4, 4, 4, 4, 20, 5)


def test_viewport_refuses_to_leave_the_image_while_blit_clips():
    img = _rgb(16)
    with pytest.raises(ValueError, match="does not clip"):
        g.viewport(img, 10, 10, 10, 10)
    with pytest.raises(ValueError, match="does not clip"):
        g.viewport(img, -1, 0, 4, 4)
    # the deliberate asymmetry: the same situation is fine for a sprite
    g.sprite_blit(np.zeros((16, 16, 4)), np.zeros((8, 8, 4)), 12, 12)


def test_tilemap_and_sheet_fail_closed_on_bad_grids():
    tile = g.sprite_synthesize("box", 4, "right")
    with pytest.raises(ValueError, match="integer array"):
        g.tilemap_render([tile], np.array([[0.0, 1.0]]))
    with pytest.raises(ValueError, match="outside the tile set"):
        g.tilemap_render([tile], np.array([[0, 3]]))
    with pytest.raises(ValueError, match="mixed sizes"):
        g.tilemap_render([tile, g.sprite_synthesize("box", 6)], np.array([[0, 1]]))
    with pytest.raises(ValueError, match="empty tile set"):
        g.tilemap_render([], np.array([[0]]))
    with pytest.raises(ValueError, match="whole number"):
        g.sprite_sheet_slice(np.zeros((10, 10, 4)), 4, 4)


def test_particles_fail_closed_on_unstable_or_impossible_state():
    st = g.particle_emit(8, 1)
    with pytest.raises(ValueError, match="must be > 0"):
        g.particle_step(st, 0.0)
    with pytest.raises(ValueError, match="reverses the velocity"):
        g.particle_step(st, 0.1, drag=10.0)
    with pytest.raises(ValueError, match="missing key"):
        g.particle_step({"pos": st["pos"]}, 0.1)
    bad = dict(st)
    bad["life"] = np.zeros(8)
    with pytest.raises(ValueError, match="lifetime must be > 0"):
        g.particle_step(bad, 0.1)
    with pytest.raises(ValueError, match=r"expected \(N, 2\)"):
        g.particle_render(dict(st, pos=st["pos"][:, :1]), 8, 8)
    with pytest.raises(ValueError, match="high .* < low"):
        g.particle_emit(4, 1, speed=(10.0, 1.0))


def test_lighting_fails_closed_on_undecoded_and_negative_input():
    encoded = np.tile([0.5, 0.5, 1.0], (8, 8, 1))
    with pytest.raises(ValueError, match="not unit length"):
        g.normal_map_shade(encoded)
    with pytest.raises(ValueError, match="zero-length normal"):
        g.normal_map_decode(np.full((4, 4, 3), 0.5))
    n = np.zeros((4, 4, 3))
    n[..., 2] = 1.0
    with pytest.raises(ValueError, match="zero-length direction"):
        g.normal_map_shade(n, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="negative radiance"):
        g.light_mask(np.zeros((4, 4, 3)), np.full((4, 4, 3), -0.1))


def test_layer_stack_rejects_a_malformed_stack():
    img = np.zeros((4, 4, 4))
    with pytest.raises(ValueError, match="empty stack"):
        g.layer_stack([])
    with pytest.raises(ValueError, match="expected a dict"):
        g.layer_stack([img])
    with pytest.raises(ValueError, match="unknown key"):
        g.layer_stack([{"image": img, "offset": (1, 1)}])
    with pytest.raises(ValueError, match="missing 'image'"):
        g.layer_stack([{"mode": "normal"}])
    with pytest.raises(ValueError, match="exceeds MAX_LAYERS"):
        g.layer_stack([{"image": img}] * (g.MAX_LAYERS + 1))


def test_dither_and_lut_reject_impossible_parameters():
    img = np.zeros((8, 8))
    with pytest.raises(ValueError, match="power of two"):
        g.dither(img, 2, "ordered", matrix_size=3)
    with pytest.raises(ValueError, match="must be >= 2"):
        g.dither(img, 1)
    with pytest.raises(ValueError, match="unknown value"):
        g.dither(img, 2, "riemersma")
    with pytest.raises(ValueError, match="cubic"):
        g.color_grade(np.zeros((4, 4, 3)), np.zeros((4, 5, 4, 3)))
    with pytest.raises(ValueError, match="empty palette"):
        g.palette_quantize(np.zeros((4, 4, 3)), np.zeros((0, 3)))
    with pytest.raises(ValueError, match=r"expected \(K, 3\)"):
        g.palette_quantize(np.zeros((4, 4, 3)), np.zeros((4, 4)))


def test_allocation_caps_are_enforced_before_the_allocation():
    with pytest.raises(ValueError, match="exceeds MAX_DIM"):
        g.radial_light(g.MAX_DIM + 1, 8, 4, 4, 2.0)
    with pytest.raises(ValueError, match="exceeds MAX_PIXELS"):
        g.radial_light(8192, 8192, 4, 4, 2.0)
    with pytest.raises(ValueError, match="MAX_RAY_ELEMENTS"):
        g.shadow_cast_2d(np.zeros((1024, 1024)), 0, 0, steps=64)
    with pytest.raises(ValueError, match="MAX_SPLAT_ELEMENTS"):
        st = g.particle_emit(20000, 1, size=(200.0, 200.0))
        g.particle_render(st, 64, 64)
    with pytest.raises(ValueError, match=r"outside \[2, 64\]"):
        g.color_grade(np.zeros((4, 4, 3)), np.zeros((1, 1, 1, 3)))
    with pytest.raises(ValueError, match="MAX_QUANT_ELEMENTS"):
        g.palette_quantize(np.zeros((4000, 4000, 3)), np.zeros((512, 3)))


def test_a_0_255_integer_image_is_named_not_silently_reinterpreted():
    """uint8 is the other everyday representation swap, and it must not slide by."""
    u8 = (np.random.default_rng(1).random((8, 8, 3)) * 255).astype(np.uint8)
    with pytest.raises(ValueError, match="imgio.to_float01"):
        g.vignette(u8)
    # a 0/1 integer mask is legitimate and still works (shadow_cast_2d takes one)
    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[4, 4] = 1
    assert g.shadow_cast_2d(mask, 0, 0).min() == 0.0


# =========================================================================== #
# 9. Determinism and the ledger                                               #
# =========================================================================== #
def _scene():
    """The whole family in one picture, from a fixed seed."""
    sky = np.zeros((64, 96, 4))
    sky[..., 3] = 1.0
    sky[..., :3] = np.linspace(0.1, 0.5, 64)[:, None, None]
    tiles = [g.sprite_synthesize(k, 16, c) for k, c in
             (("box", "reference"), ("disc", "right"), ("star", "emphasis"))]
    ground = g.tilemap_render(tiles, np.array([[0, 1, 2, 0, 1, 2]]))
    scene = g.sprite_blit(sky, ground, 0, 48)
    scene = g.sprite_blit(scene, g.sprite_transform(tiles[2], 24.0, 1.5), 40, 24,
                          anchor="center")
    sparks = g.particle_emit(300, 2026, origin=(40.0, 24.0), speed=(5.0, 30.0),
                             size=(0.8, 2.0), color="emphasis")
    sparks = g.particle_step(sparks, 0.05)
    scene = g.alpha_composite(g.particle_render(sparks, 64, 96), scene)
    lit = g.light_mask(scene[..., :3], g.radial_light(64, 96, 40, 24, 40.0,
                                                     color=(1.0, 1.0, 1.0)),
                       ambient=0.35)
    return g.vignette(g.bloom(lit, 0.7, 3.0, 0.5), 0.4)


def test_the_whole_pipeline_is_byte_for_byte_deterministic():
    a, b = _scene(), _scene()
    assert hashlib.sha256(a.tobytes()).hexdigest() == hashlib.sha256(b.tobytes()).hexdigest()
    assert a.shape == (64, 96, 3)
    assert np.all(np.isfinite(a)) and a.min() >= 0.0 and a.max() <= 1.0


def test_ledger_declares_every_public_op_and_nothing_else():
    public = {n for n in g.__all__ if n.islower()}
    assert set(opsgfx2d.OPSGFX2D) == public
    assert opsgfx2d.missing() == []
    assert len(opsgfx2d.OPSGFX2D) == 32


def test_ledger_sorts_have_a_producer_and_a_consumer():
    """A sort nobody produces is dead; a sort nobody eats is a leak."""
    produced, consumed = set(), set()
    for meta in opsgfx2d.OPSGFX2D.values():
        produced.add(meta["out"])
        consumed.update(meta["in"])
    for sort in ("rgb", "rgba", "rgba_premul", "sprites", "lut", "normalmap", "image2d",
                 "table"):
        assert sort in produced, f"{sort} has no producer in this ledger"
        assert sort in consumed, f"{sort} has no consumer in this ledger"


def test_ledger_call_matches_get():
    a = opsgfx2d.get("sprite_synthesize")("disc", 8, "right")
    b = opsgfx2d.call("sprite_synthesize", "disc", 8, "right")
    assert np.array_equal(a, b)
    assert opsgfx2d.info("bloom")["category"] == "post"
    assert "bloom" in opsgfx2d.list_ops("post")
    assert len(opsgfx2d.categories()) == 8
