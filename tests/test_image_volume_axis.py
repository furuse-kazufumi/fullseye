"""2-D op に立体 (8,8,8) を渡す穴の opt-in 門 / opt-in guard for volumes fed to 2-D image ops.

既定の数値は変えない(docs/KNOWN_ISSUES.md §34: `_NDIM_OK["image"] = (2, 3)` は意図的)が、
最終軸が 1/3/4 でない 3-D 配列には op ごとに 1 回の Fullseye 警告を出す。
``extra_checks='on'`` のときは既定方針でも image/region op が入口で断る。
"""
import warnings
import json
from pathlib import Path

import numpy as np
import pytest

import api
import fullseye as fs
import ops

VOL = np.random.default_rng(0).random((8, 8, 8))
RGB = np.random.default_rng(1).random((8, 8, 3))


def test_default_is_unchanged_volume_still_passes():
    fs.clear_fallbacks(reset_warnings=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = fs.apply(VOL, "gauss_filter")
    assert out.shape == (8, 8, 8)
    notices = [w for w in caught if issubclass(w.category, fs.FullseyeFallbackWarning)]
    assert len(notices) == 1
    assert "volume needs a volume op" in str(notices[0].message)


def test_opt_in_refuses_a_volume_for_image_and_region_ops():
    with _on():
        with pytest.raises(ValueError, match="3-D array of shape"):
            fs.apply(VOL, "gauss_filter")
        with pytest.raises(ValueError, match="3-D array of shape"):
            fs.apply(VOL > 0.5, "skeleton")


def test_volume_axis_warning_guard_covers_all_declared_2d_ops():
    """§34: volume inputs warn; generated per-slice maps are the one safe exception / 立体は警告する。"""
    all_2d = [op for op in ops.REGISTRY if op.in_sort in ("image", "region")]
    names = {op.name for op in all_2d}
    assert api._STACK_POINTWISE_2D_OPS <= names
    graph = json.loads((Path(__file__).resolve().parents[1] / "fullseye" / "data" /
                        "OP_GRAPH.json").read_text(encoding="utf-8"))
    map_bases = {edge["op"].removeprefix("map::") for edge in graph["edges"]
                 if edge["op"].startswith("map::")}
    assert api._STACK_POINTWISE_2D_OPS == map_bases
    targets = [op for op in all_2d if op.name not in api._STACK_POINTWISE_2D_OPS]
    assert targets, "the volume-axis guard lost every non-map 2-D op"
    assert all(api._check_image_volume_axis(VOL, op) is not None for op in targets)

    # The input guard is the production path before a backend runs. Call it directly
    # so every declared op is checked without conflating this coverage gate with an
    # unrelated backend's own documented failure on an 8-cube.
    fs.clear_fallbacks(reset_warnings=True)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for op in targets:
                api._guard_input(VOL, op, "fallback")
        notices = [w for w in caught if issubclass(w.category, fs.FullseyeFallbackWarning)]
        assert len(notices) == len(targets)
        counts = fs.fallback_counts()
        assert all(counts.get(op.name) == 1 for op in targets)
    finally:
        fs.clear_fallbacks(reset_warnings=True)


def test_lifted_map_base_runs_as_the_documented_per_slice_stack():
    """A map base accepts seq<image> and equals the 2-D slice calls / map の各枚を正しく通す。"""
    stack = np.random.default_rng(2).random((3, 8, 8))
    expected = np.stack([fs.apply(slice_, "companding_mu_law", on_error="raise")
                         for slice_ in stack])
    fs.clear_fallbacks(reset_warnings=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        actual = fs.apply(stack, "companding_mu_law", on_error="raise")
    assert np.allclose(actual, expected, atol=1e-12)
    assert not [w for w in caught if issubclass(w.category, fs.FullseyeFallbackWarning)]
    assert "companding_mu_law" not in fs.fallback_counts()


def test_opt_in_keeps_colour_and_gray_images_working():
    with _on():
        assert fs.apply(RGB, "invert", on_error="raise").shape == (8, 8, 3)
        assert fs.apply(RGB[..., :1], "invert", on_error="raise").shape == (8, 8, 1)
        assert fs.apply(RGB[..., 0], "gauss_filter", on_error="raise").shape == (8, 8)


class _on:
    def __enter__(self):
        self._old = fs.set_system("extra_checks", "on")

    def __exit__(self, *a):
        fs.set_system("extra_checks", self._old)
