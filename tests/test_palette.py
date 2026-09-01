# -*- coding: utf-8 -*-
"""配色の流儀が 1 か所に閉じていることを守る検査。

図ごとに作者が色を選ぶと、同じ意味に違う色が付く ―― 実際この repo でも
「赤枠 = 誤り / 緑枠 = 正しい」の展示と、同じ意味を青-黒-橙で描いた展示が
同居していた。ここは「役割で引く」形が壊れないことを固定する。
"""
from __future__ import annotations

import numpy as np
import pytest

import palette as P


def test_every_scheme_defines_every_role():
    for scheme in P.SCHEMES:
        pal = P.semantic_palette(scheme)
        assert set(pal) == set(P.ROLES), f"{scheme} is missing roles"
        for role, rgb in pal.items():
            assert len(rgb) == 3 and all(0.0 <= c <= 1.0 for c in rgb), f"{scheme}/{role}"


def test_unknown_scheme_and_role_fail_closed():
    """黙って既定へ落とすと、流儀が割れていることに誰も気づけない。"""
    with pytest.raises(ValueError, match="unknown scheme"):
        P.semantic_palette("neon")
    with pytest.raises(ValueError, match="unknown role"):
        P.role_color("mistake")


def test_default_scheme_does_not_pair_red_with_green():
    """既定が赤緑の対だと、色覚特性によっては情報量がゼロになる。"""
    P.assert_not_red_green_pair("okabe_ito")
    P.assert_not_red_green_pair("blue_orange")


def test_red_green_is_kept_only_for_compatibility():
    with pytest.raises(ValueError, match="compatibility"):
        P.assert_not_red_green_pair("red_green")


def test_right_and_wrong_differ_in_lightness_too():
    """色相だけで分けない ―― 白黒印刷でも、色覚特性があっても分かれるように。"""
    for scheme in ("okabe_ito", "blue_orange"):
        pal = P.semantic_palette(scheme)
        lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        assert abs(lum(pal["right"]) - lum(pal["wrong"])) > 0.05, scheme


def test_role_rgb8_is_a_pil_ready_triple():
    rgb = P.role_rgb8("wrong")
    assert len(rgb) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in rgb)
    assert rgb == tuple(int(round(c * 255)) for c in P.role_color("wrong"))


def test_every_role_has_a_marker_so_colour_is_never_the_only_cue():
    assert set(P.ROLE_MARKERS) == set(P.ROLES)
    assert all(m.strip() for m in P.ROLE_MARKERS.values())


def test_diverging_lut_is_dark_in_the_middle_and_symmetric_in_extent():
    lut = P.diverging_lut(101)
    assert lut.shape == (101, 3)
    assert lut.min() >= 0.0 and lut.max() <= 1.0
    mid = lut[50].sum()
    assert mid < lut[0].sum() and mid < lut[-1].sum(), "中央が両端より暗いこと"
    assert np.allclose(lut[0], P.semantic_palette("blue_orange")["wrong"], atol=1e-9)
    assert np.allclose(lut[-1], P.semantic_palette("blue_orange")["right"], atol=1e-9)


def test_diverging_lut_rejects_a_degenerate_size():
    with pytest.raises(ValueError, match="n must be"):
        P.diverging_lut(1)
