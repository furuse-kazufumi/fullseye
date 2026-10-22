"""H16: processing failures must not be confused with empty domains."""
from __future__ import annotations

import subprocess
from pathlib import Path
import sys

import numpy as np
import pytest

import image_gen
from fslib import FImage, FsTypeError, FsValueError, Region, connection, threshold


@pytest.mark.parametrize("operator", [image_gen.change_domain, image_gen.reduce_domain],
                         ids=lambda fn: fn.__name__)
def test_domain_operator_accepts_legitimate_empty_region(operator):
    result = operator(np.ones((3, 4), dtype=np.float64),
                      np.zeros((3, 4), dtype=bool))
    assert result["image"].shape == (3, 4)
    assert result["image"].dtype == np.float64
    assert result["domain"].shape == (3, 4)
    assert result["domain"].dtype == np.bool_
    assert not result["domain"].any()


@pytest.mark.parametrize("operator", [image_gen.change_domain, image_gen.reduce_domain],
                         ids=lambda fn: fn.__name__)
def test_domain_operator_rejects_nan_with_named_reason(operator):
    image = np.ones((3, 4), dtype=np.float64)
    image[1, 2] = np.nan
    with pytest.raises(FsValueError, match=rf"{operator.__name__}.*NaN"):
        operator(image, np.zeros((3, 4), dtype=bool))


@pytest.mark.parametrize("operator", [image_gen.change_domain, image_gen.reduce_domain],
                         ids=lambda fn: fn.__name__)
def test_domain_operator_rejects_swapped_sorts(operator):
    with pytest.raises(FsTypeError, match=rf"{operator.__name__}.*region"):
        # 画像(0/1 以外の実数)を領域の位置に渡す。0/1 だけの実数配列は文書化された mask の形なので通る。
        operator(np.zeros((3, 4), dtype=np.float64), np.full((3, 4), 0.37))


@pytest.mark.parametrize("operator", [image_gen.change_domain, image_gen.reduce_domain],
                         ids=lambda fn: fn.__name__)
def test_domain_operator_rejects_shape_mismatch(operator):
    with pytest.raises(FsValueError, match=rf"{operator.__name__}.*shape"):
        operator(np.ones((3, 4)), np.zeros((4, 3), dtype=bool))


def test_typed_threshold_empty_is_a_normal_region():
    result = threshold(FImage(np.zeros((3, 4)), (0.0, 1.0)), 0.5, 1.0)
    assert isinstance(result, Region)
    assert result.shape == (3, 4)
    assert result.area() == 0


def test_typed_threshold_rejects_swapped_sort():
    with pytest.raises(FsTypeError, match="threshold.*FImage"):
        threshold(Region(np.zeros((3, 4), dtype=bool)), 0.5, 1.0)


def test_typed_connection_empty_is_a_normal_object_set():
    result = connection(Region(np.zeros((3, 4), dtype=bool)))
    assert len(result.ids) == 0


def test_typed_connection_rejects_swapped_sort():
    with pytest.raises(FsTypeError, match="connection.*Region"):
        connection(FImage(np.zeros((3, 4)), (0.0, 1.0)))


def test_fallback_audit_is_current():
    completed = subprocess.run(
        [sys.executable, "tools/audit_fallbacks.py", "--check"],
        cwd=str(Path(image_gen.__file__).resolve().parent), check=False,
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("operator", [image_gen.change_domain, image_gen.reduce_domain],
                         ids=lambda fn: fn.__name__)
def test_domain_operator_accepts_the_documented_0_1_mask_forms(operator):
    """docstring の例(int のリスト)と uint8 / float の 0/1 mask は bool と同じ結果。"""
    im = np.arange(6, dtype=np.float64).reshape(2, 3)
    ref = operator(im, np.array([[1, 0, 1], [0, 0, 1]], dtype=bool))
    for region in ([[1, 0, 1], [0, 0, 1]], np.array([[1, 0, 1], [0, 0, 1]], np.uint8),
                   np.array([[1, 0, 1], [0, 0, 1]], np.float64)):
        got = operator(im, region)
        assert got["domain"].dtype == np.bool_
        np.testing.assert_array_equal(got["domain"], ref["domain"])
        np.testing.assert_array_equal(got["image"], ref["image"])
