# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""入口 op(``backends_bridge``、category ``bridge``)の契約。

3 つのことを固定する:

1. **進化には見えない** —— ``ops._candidates`` はどの sort でも bridge を返さない
   (候補リストの長さが変わるとゲノム → op の写像が変わる。docs/WAVE0_STABLE_SLOTS.md)。
2. **名前では見える** —— ``RT`` / ``_BY_NAME`` / ``fullseye.apply`` から呼べる。
3. **出口の形は宣言どおり、決定的、有限** —— ``backends_typed._SHAPE_OK`` と同じ
   契約で、2 回呼んでビット一致、fail-soft では sort に合う空値へ落ちる。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ops  # noqa: E402
import backends_bridge as BB  # noqa: E402
import backends_typed as BT  # noqa: E402
import fullseye as fs  # noqa: E402


def _img(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = 0.2 + 0.5 * xx / (n - 1)
    img[(yy - 14) ** 2 + (xx - 14) ** 2 <= 36] = 0.95
    img[30:42, 26:44] = 0.05
    return np.clip(img, 0, 1)


@pytest.fixture(scope="module")
def bridges():
    out = [o for o in ops.REGISTRY if o.category == BB.CATEGORY]
    assert len(out) == len(BB.BRIDGES), "登録数が BRIDGES と違う(backend の import 失敗?)"
    return out


def test_bridges_are_registered_but_never_candidates(bridges):
    names = {o.name for o in bridges}
    assert names == {n for n, _s, _f in BB.BRIDGES}
    for o in bridges:
        assert o.in_sort == ops.IMAGE
        assert ops._BY_NAME[o.name] is o
        assert ops.RT[o.name] is o.fn
    sorts = {o.in_sort for o in ops.REGISTRY} | {ops.ANY}
    for s in sorts:
        assert not [o for o in ops._candidates(s) if o.category == BB.CATEGORY], s


def test_every_registered_in_sort_has_an_entry_from_image(bridges):
    """図と Studio サンプルの前提: 登録簿のどの in_sort も画像から作れること。"""
    made = {o.out_sort for o in bridges} | {"image", "any", "region", "contour", "color", "feature", "match"}
    # qimage は rgbimage 経由(tb_rgb_to_quaternion)でも作れるが、bridge 自身にも入口がある
    need = {o.in_sort for o in ops.REGISTRY}
    assert need <= made, "画像から作れない in_sort: %s" % sorted(need - made)


@pytest.mark.parametrize("name,out_sort", [(n, s) for n, s, _f in BB.BRIDGES])
def test_bridge_output_matches_its_declared_sort_and_is_deterministic(name, out_sort):
    img = _img()
    out1 = fs.apply(img, name, 0.5, 0.5, on_error="raise")
    out2 = fs.apply(img, name, 0.5, 0.5, on_error="raise")
    assert isinstance(out1, np.ndarray)
    assert BT._sort_ok(out1, out_sort), (name, out_sort, out1.shape, out1.dtype)
    assert np.array_equal(out1, out2), "%s: 2 回の呼び出しが一致しない" % name
    real = out1.real if out1.dtype.kind == "c" else out1
    assert np.isfinite(real).all() and (np.isfinite(out1.imag).all() if out1.dtype.kind == "c" else True)
    # ノブは効く(未使用と明記した img_to_matrix 以外は、a か b で出力が変わる)
    if name != "img_to_matrix":
        alt = fs.apply(img, name, 0.9, 0.1, on_error="raise")
        assert alt.shape != out1.shape or not np.array_equal(alt, out1), "%s: a, b が効いていない" % name


def test_specific_shapes_follow_the_docstrings():
    img = _img(48)
    assert fs.apply(img, "img_to_points", 0.5, 0.5, on_error="raise").shape == (24 * 24, 3)
    assert fs.apply(img, "img_to_points", 0.5, 0.0, on_error="raise").shape == (48 * 48, 3)
    assert fs.apply(img, "img_to_signal", 0.5, 0.0, on_error="raise").shape == (48,)
    assert fs.apply(img, "img_to_video", 0.5, 0.5, on_error="raise").shape == (BB.VIDEO_FRAMES, 48, 48)
    vol = fs.apply(img, "img_to_volume", 0.5, 0.5, on_error="raise")
    assert vol.shape == (36, 48, 48) and vol[0].sum() > 0
    lf = fs.apply(img, "img_to_lightfield", 0.5, 0.5, on_error="raise")
    assert lf.shape == BB.LF_ANGULAR + (48, 48)
    assert np.array_equal(lf[2, 2], img), "中央視点は入力そのもの"
    bc = fs.apply(img, "img_to_beatcube", 0.0, 0.5, on_error="raise")
    assert bc.shape == BB.BEAT_SHAPE and bc.dtype.kind == "c"
    cx = fs.apply(img, "img_to_cimage", 0.0, 0.5, on_error="raise")
    assert np.allclose(np.abs(cx), img) and np.allclose(cx.imag, 0.0), "a=0, b=0.5 は実場"
    cnt = fs.apply(img, "img_to_counts", 0.5, 0.0, on_error="raise")
    assert cnt.dtype == np.int64 and cnt.min() >= 0
    rgb = fs.apply(img, "img_to_rgb", 0.0, 0.0, on_error="raise")
    assert np.allclose(rgb[..., 0], img) and np.allclose(rgb[..., 1], img), "彩度 0 はグレー"
    red = fs.apply(img, "img_to_rgb", 0.0, 1.0, on_error="raise")
    dark = img < BB.SPECULAR_KNEE
    assert np.allclose(red[dark, 1], 0.0) and np.allclose(red[dark, 2], 0.0), "膝より暗い画素は純色"
    assert np.allclose(red[img >= 0.99], img[img >= 0.99, None]), "最明部は白(鏡面)"
    kp = fs.apply(img, "img_to_keypoints", 0.5, 0.9, on_error="raise")
    assert kp.ndim == 2 and kp.shape[1] == 2
    assert np.all(kp[:, 0] < 48) and np.all(kp[:, 1] < 48)


def test_bridge_rejects_bad_input_fail_closed_under_raise():
    with pytest.raises(ValueError):
        fs.apply(np.full((8, 8), np.nan), "img_to_points", 0.5, 0.5, on_error="raise")
    with pytest.raises(ValueError):
        fs.apply(np.zeros(8), "img_to_signal", 0.5, 0.5, on_error="raise")


def test_bridge_fail_soft_returns_a_sort_valid_empty_value():
    """既定(fail-soft)では、失敗が sort の嘘にならない(入力画像を返さない)。"""
    bad = np.full((8, 8), np.nan)
    for name, out_sort, _fn in BB.BRIDGES:
        out = ops.RT[name](bad, 0.5, 0.5)
        assert isinstance(out, np.ndarray)
        assert BT._sort_ok(out, out_sort), (name, out_sort, getattr(out, "shape", None))
        assert out.shape != bad.shape or out_sort in ("matrix",), name


def test_monogenic_entry_feeds_the_monogenic_family():
    img = _img(64)
    q = fs.apply(img, "img_to_monogenic", 0.5, 0.5, on_error="raise")
    assert q.shape == (64, 64, 4) and np.allclose(q[..., 3], 0.0)
    amp = fs.apply(q, "tb_monogenic_amplitude", 0.5, 0.5, on_error="raise")
    assert amp.shape == (64, 64) and np.isfinite(amp).all()


def test_typed_knob_range_keeps_wetness_inside_its_domain():
    """相対スケールで定義域を突き抜けていた `tb_wetness`(2026-09-07 実測)。"""
    rgb = fs.apply(_img(), "img_to_rgb", 0.3, 0.6, on_error="raise")
    for a in (0.0, 0.5, 1.0):
        out = fs.apply(rgb, "tb_wetness", a, 0.5, on_error="raise")
        assert out.shape == rgb.shape and np.isfinite(out).all()
    assert ("wetness", "wet") in BT.OP_KNOB_RANGE
