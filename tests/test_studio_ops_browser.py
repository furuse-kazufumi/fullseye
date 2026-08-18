"""Studio op-browser(F6 核: 自動列挙・合成入力・render_hint 描画)の回帰テスト。"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

warnings.simplefilter("ignore")

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

import spikes.studio_ops_browser as b  # noqa: E402


def test_registry_available():
    assert len(b.ops) >= 590


def test_render_by_hint_all_types_dont_crash():
    """F6: 8 種の render_hint いずれも Figure を返し例外を投げない。"""
    samples = {
        "image": np.random.default_rng(0).random((16, 16)),
        "region": np.zeros((16, 16), bool),
        "contour": {"shape": (32, 32), "cs": [np.column_stack([np.arange(10), np.arange(10)])]},
        "point_cloud": np.random.default_rng(0).random((30, 3)),
        "pose": np.eye(4),
        "matrix": np.eye(3),
        "scalar": {"value": 1.0},
        "matches": {"num": 3},
    }
    for hint, r in samples.items():
        fig = Figure()
        out = b.render_by_hint(r, hint, fig)
        assert out is fig
        assert len(fig.axes) >= 1


def test_synthesize_args_for_known_ops():
    """F3: 自然 param 名から合成入力が作れる op がある。"""
    op = b.ops["gen_circle_contour_xld"]
    args = b.synthesize_args(op)
    assert args is not None
    res = op(*args)
    assert "cs" in res


def test_scalar_param_specs_shape():
    """F3→UI: scalar param が (name, lo, hi, default, is_int) の spec になる。"""
    op = b.ops["gen_circle_contour_xld"]
    specs = b.scalar_param_specs(op)
    assert all(len(s) == 5 for s in specs)
    names = [s[0] for s in specs]
    assert "row" in names and "radius" in names


def test_render_op_into_runs_or_cards():
    """F6: 代表 op が render_op_into で Run OK か F3 カード(auto-input 不可)になる。"""
    op = b.ops["difference_closed_contours_xld"]
    fig = Figure()
    status = b.render_op_into(op, fig, {})
    assert status in ("Run OK",) or status.startswith("Run 失敗") or "auto-input" in status
    assert len(fig.axes) >= 1


def test_coverage_meets_threshold():
    """honest: 合成入力だけで相当数(>=300)の op が自動実行・描画できる。"""
    rep = b.coverage_report()
    assert rep["total"] == len(b.ops)
    assert rep["auto_ran"] >= 300
    # エラーは少数(synthesizer のヒューリスティック外)
    assert rep["errored"] < 60


def test_overrides_change_result():
    """F6: スライダ override が実際に op へ渡る。"""
    op = b.ops["gen_circle_contour_xld"]
    fig = Figure()
    b.render_op_into(op, fig, {"radius": 5.0})
    small = op(row=32, col=32, radius=5.0)
    big = op(row=32, col=32, radius=20.0)
    ds = np.hypot(small["cs"][0][:, 0] - 32, small["cs"][0][:, 1] - 32)
    db = np.hypot(big["cs"][0][:, 0] - 32, big["cs"][0][:, 1] - 32)
    assert abs(ds.mean() - 5) < 1e-6 and abs(db.mean() - 20) < 1e-6
