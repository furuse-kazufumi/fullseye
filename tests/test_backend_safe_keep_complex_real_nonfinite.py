"""複素の sort を名乗る op が実数の非有限を返しても、外へは有限で出ること(0.7.0 の preflight で発見)。"""
import warnings

import numpy as np
import pytest

import fullseye as F

OPS = ["tb_angular_spectrum_propagate", "tb_cx_apply_transfer_function", "tb_fmcw_window_apply"]
INPUTS = {
    "nan": np.full((16, 16), np.nan),
    "inf": np.full((16, 16), np.inf),
    "ninf": np.full((16, 16), -np.inf),
    "halfnan": np.where(np.arange(256).reshape(16, 16) % 2 == 0, np.nan, 0.5),
}


@pytest.mark.parametrize("name", OPS)
@pytest.mark.parametrize("kind", sorted(INPUTS))
def test_complex_sort_op_returns_finite_for_nonfinite_input(name, kind):
    if name not in F.op_names():
        pytest.skip("%s は この環境で登録されていない" % name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = np.asarray(F.apply(INPUTS[kind], name, 0.5, 0.5))
    assert np.isfinite(out).all()


def test_keep_complex_fills_real_and_complex_nonfinite_but_keeps_the_phase():
    import backend_safe as bs
    real = np.array([[np.nan, 1.0]])
    assert np.array_equal(bs._keep_complex(real, real, "cimage", "probe"), [[0.0, 1.0]])
    cx = np.array([[np.inf + 0j, 1.0 + 2.0j]])
    got = bs._keep_complex(cx, cx, "cimage", "probe")
    assert got.dtype.kind == "c" and got[0, 1] == 1.0 + 2.0j and got[0, 0] == 0
