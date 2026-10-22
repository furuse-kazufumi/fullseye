"""非有限な入力は入口で拒否する(2026-10-23 の契約変更)。生の実装は触らず、包み紙 ``fullseye.apply`` で止める。

監査(``tools/audit_nan_inputs.py`` → ``docs/NAN_INPUT_AUDIT.md``)で 431 op が中央 1 画素の NaN / +inf を
黙って有限の答えに変えていた。ここでは (1) 入口の挙動を生で、(2) 台帳の包み紙経路で silent_finite が 0 である
ことを固定する。
"""
from __future__ import annotations

import inspect
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import api  # noqa: E402
import fullseye as F  # noqa: E402
import ops  # noqa: E402
from fslib import FsValueError  # noqa: E402
import audit_nan_inputs as audit  # noqa: E402

RNG = np.random.default_rng(20261023)


def _img():
    return RNG.random((16, 16))


@pytest.mark.parametrize("fill", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("policy", ["fallback", "warn", "raise"])
def test_a_single_nonfinite_pixel_is_refused_whatever_the_policy(fill, policy):
    x = _img()
    x[7, 3] = fill
    with pytest.raises(FsValueError, match=r"^gaussian: input contains NaN or infinity"):
        F.apply(x, "gaussian", on_error=policy)


def test_a_clean_input_is_untouched_and_the_escape_hatch_reaches_the_op():
    x = _img()
    assert np.array_equal(F.apply(x, "gaussian"), F.apply(x, "gaussian", allow_nonfinite=True))
    y = x.copy()
    y[0, 0] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = F.apply(y, "gaussian", allow_nonfinite=True)
    assert out.shape == x.shape and np.isfinite(out).all()      # 出口の埋め(従来どおり)はそのまま


def test_integer_and_bool_inputs_are_not_scanned():
    u8 = (RNG.random((16, 16)) * 255).astype(np.uint8)
    assert F.apply(u8, "gaussian").shape == (16, 16)
    assert F.apply(u8 > 127, "reg_erode").shape == (16, 16)
    assert api._nonfinite_leaf(np.zeros((4, 4), np.int64)) is None
    assert api._nonfinite_leaf(np.zeros(0)) is None            # 空は別の門(空入力の拒否)の仕事


def test_every_input_of_an_nary_list_is_scanned():
    x, y = _img(), _img()
    y[5, 5] = np.inf
    with pytest.raises(FsValueError, match=r"^add_image: input contains NaN or infinity \(input 1: "):
        F.apply([x, y], "add_image")
    assert F.apply([x, x], "add_image").shape == (16, 16)


def test_points_volume_and_dict_leaves_are_scanned():
    pts_op = next(o.name for o in ops.REGISTRY if o.in_sort == "points")
    pts = audit.baseline_for_sort("points").copy()
    pts[9, 2] = np.nan
    with pytest.raises(FsValueError, match="^%s: " % pts_op):
        F.apply(pts, pts_op, coerce=False)
    vol_op = next(o.name for o in ops.REGISTRY if o.in_sort == "volume")
    vol = audit.baseline_for_sort("volume").copy()
    vol.flat[3] = -np.inf
    with pytest.raises(FsValueError, match="^%s: " % vol_op):
        F.apply(vol, vol_op, coerce=False)
    hit = api._nonfinite_leaf({"shape": "polygon", "cs": np.array([[0.0, np.nan]])})
    assert hit is not None and hit.startswith("key 'cs'"), hit
    assert api._nonfinite_leaf({"a": [1.0, 2.0], "b": np.zeros(3, np.int64), "c": "text"}) is None
    assert api._nonfinite_leaf([[0.5, 0.5], [0.5, float("inf")]]) is not None   # 入れ子リストの画像
    cx = np.array([[1 + 1j, np.nan + 0j]])
    assert api._nonfinite_leaf(cx) is not None


def test_an_unknown_op_name_keeps_its_own_error_even_with_a_nan_input():
    x = _img()
    x[1, 1] = np.nan
    with pytest.raises(Exception) as ei:
        F.apply(x, "no_such_op_2026_10_23")
    assert "input contains NaN" not in str(ei.value), str(ei.value)


def test_the_pipeline_entry_is_refused_and_has_no_escape_hatch():
    x = _img()
    x[2, 2] = np.nan
    with pytest.raises(FsValueError, match=r"^gaussian: input contains NaN or infinity"):
        F.run_pipeline(x, ["gaussian", "otsu"])
    assert "allow_nonfinite" not in inspect.signature(F.run_pipeline).parameters
    assert "allow_nonfinite" in inspect.signature(F.apply).parameters


def test_one_op_per_array_sort_is_refused_live():
    """台帳だけでなく、sort ごとに 1 op を生で通す(台帳の鮮度に依らない最小の網)。"""
    seen = {}
    for op in ops.REGISTRY:
        if op.in_sort in audit.ARRAY_SORTS and op.in_sort not in seen:
            seen[op.in_sort] = op.name
    assert len(seen) >= 12, seen
    for sort, name in seen.items():
        v = audit.baseline_for_sort(sort).copy()
        v.flat[v.size // 2] = np.nan
        with pytest.raises(FsValueError, match="^%s: input contains NaN or infinity" % name):
            F.apply(v, name, coerce=False)


def test_the_ledger_shows_zero_passthrough_on_the_wrapped_route():
    data = json.loads(audit.JSON_PATH.read_text(encoding="utf-8"))
    w = data["summary"]["wrapper"]
    assert w["refusal"] == audit.WRAPPER_REFUSAL == "raised_FsValueError"
    assert w["applicable"] >= 850                                   # 範囲の下限(門が黙って縮まない)
    for kind in ("nan", "inf"):
        assert w["counts"][kind] == {audit.WRAPPER_REFUSAL: w["applicable"]}, w["counts"][kind]
    assert w["passthrough"] == []
    # 生の実装の表はそのまま(監査は変えていない): 入口で止めるという設計の根拠が残っていること
    assert data["summary"]["counts"]["nan"]["silent_finite"] >= 200
    assert all(r["wrapper_behaviour"].get("nan") == audit.WRAPPER_REFUSAL
               for r in data["records"] if r["in_sort"] in audit.ARRAY_SORTS)
