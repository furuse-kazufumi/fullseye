# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""空の入力を生の例外(ZeroDivisionError / IndexError)でなく、名指しの ValueError で拒否する(2026-10-11)。

台帳の空入力の探針(``tools/ledger_gaps.py``)が、第 1 引数を空にすると 0 除算や添字エラーで
落ちる台帳 op を 20 本挙げた。どれも「何が空なのか」を言わずに深い所で落ちていた。
入口で拒否し、docstring に「空の入力は ValueError」と書いたので、以後は台帳の門
(``tests/test_ledger_contracts.py``、約束した op は ValueError を要求)も同じ 20 本を見張る。

入力はその門と同じ探針(``ledger_contracts.bind``)で組み、第 1 引数だけを空にする。
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

lc = pytest.importorskip("ledger_contracts")
lg = pytest.importorskip("ledger_gaps")

#: 生の ZeroDivisionError だった 7 本と IndexError だった 13 本。
FIXED = (
    "vol_fft_lowpass", "vol_fft_highpass", "vol_fft_bandpass", "integrate_normals",
    "membrane_recover", "membrane_delta_from_normals", "plate_mesh_from_image",
    "class_2dim_sup", "expand_gray", "fbp_volume", "geodesic_mesh", "heap_spheres_select",
    "mean_edge_error", "mean_reprojection_error", "mesh_signed_volume", "mesh_to_points",
    "mesh_to_voxel", "vda5050_order", "vol_euler_number", "vol_stretch",
)

#: 通常入力で optional の torch を要る op(拒否は torch 無しでも確かめる)。
NEEDS_TORCH = {"mesh_to_voxel"}


@pytest.fixture(scope="module")
def bound():
    cf = lc._cf()
    ops = {o[0]: o for o in lc.ledger_ops()}
    extra = dict(lc._io_builders(), **lc.probe_builders())
    out = {}
    with cf._scratch_cwd():
        rng = np.random.default_rng(lc._SEED)
        pool = {t: [g(rng)] for t, g in sorted(cf.make_generators().items())}
        for name in FIXED:
            _n, _led, ins, _out, fn = ops[name]
            args, kwargs = lc.bind(name, fn, ins, pool, cf, extra)
            out[name] = (fn, args, kwargs)
    return out


@pytest.mark.parametrize("name", FIXED)
def test_empty_first_input_is_a_named_value_error(bound, name):
    fn, args, kwargs = bound[name]
    empty = lg.empty_like(args[0])
    assert empty is not None
    with pytest.raises(ValueError, match="empty"):
        lc._call(fn, [empty] + list(args[1:]), kwargs)
    # 空でない元の入力ではこれまでどおり動く(門が入口を塞いでいないこと)
    # ★mesh_to_voxel は points_to_voxel が optional の torch を要る。CI には torch が無いので
    #   拒否の確認(上)だけ走らせ、通常入力の実行は torch のある環境に限る。
    if name in NEEDS_TORCH and importlib.util.find_spec("torch") is None:
        return
    lc._call(fn, list(args), kwargs)
    # docstring の約束として読めること(台帳の門がこの op を見張る条件)
    import inspect
    names = list(inspect.signature(fn).parameters)
    assert lg.promises_empty_refusal(fn.__doc__ or "", names[0], names[1:]), name
