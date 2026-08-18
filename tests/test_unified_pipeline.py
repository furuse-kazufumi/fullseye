"""F5 合成(Pipeline / Image チェーン)の回帰テスト — 単一 registry 上で op を段組み。"""
from __future__ import annotations

import warnings

import numpy as np

warnings.simplefilter("ignore")
import unified as u  # noqa: E402


def _img():
    return np.random.default_rng(0).random((48, 60)).astype(float)


def test_image_chain_composes_and_records_history():
    """F5: Image(arr).op().op() が文のように繋がり履歴を残す。"""
    out = u.Image(_img()).median().sobel_amp().invert()
    assert out.history == ["median", "sobel_amp", "invert"]
    assert np.asarray(out.value).shape == (48, 60)
    assert np.isfinite(out.value).all()


def test_image_is_immutable():
    """F5: 各段は新しい Image を返し、元は変わらない(不変)。"""
    a = u.Image(_img())
    b = a.median()
    assert a.history == [] and b.history == ["median"]
    assert a is not b


def test_pipeline_equals_image_chain():
    """F5: 汎用 Pipeline と Image チェーンは同じ registry op で結果一致。"""
    img = _img()
    p = u.pipeline("median", "sobel_amp", "invert")
    chain = u.Image(img).median().sobel_amp().invert()
    assert np.allclose(np.asarray(p.run(img)), np.asarray(chain.value))


def test_pipeline_trace_returns_intermediates():
    """F5: trace=True で入力+各段の中間出力を返す。"""
    img = _img()
    p = u.pipeline("median", "invert")
    out, mids = p.run(img, trace=True)
    assert len(mids) == 3                      # 入力 + 2 段
    assert np.allclose(np.asarray(mids[-1]), np.asarray(out))


def test_pipeline_bound_kwargs_threaded():
    """F5: 段に束縛した kwargs が適用される(知覚の段組み)。"""
    xs = np.arange(1, 5, 0.8)
    gx, gy = np.meshgrid(np.linspace(0, 5, 200), np.linspace(-0.3, 0.3, 15))
    z = np.zeros_like(gx)
    for x in xs:
        z[np.abs(gx - x) < 0.06] = 0.08
    cloud = np.column_stack([gx.ravel(), gy.ravel(), z.ravel()])
    grid, _ = u.ops["elevation_map"](cloud, cell=0.03, agg="max")
    p = u.pipeline(("slope_map", {"cell": 0.03}), ("roughness_map", {"window": 3}))
    out = p.run(grid)
    assert np.asarray(out).shape == np.asarray(grid).shape


def test_pipeline_describe_is_f3_metadata():
    """F5+F3: describe が段ごとの機械可読メタ(op メタ + 束縛 kwargs)を返す。"""
    p = u.pipeline("median", ("invert", {}))
    d = p.describe()
    assert d["n_stages"] == 2
    assert "→" in d["chain"]
    assert d["stages"][0]["name"] == "median"
    assert "render_hint" in d["stages"][0]


def test_pipeline_accepts_raw_callable():
    """F5: 生 callable も inline op として段に入れられる。"""
    p = u.Pipeline([lambda a: a * 2.0, "invert"])
    img = _img()
    assert len(p) == 2
    assert np.isfinite(p.run(img)).all()


def test_unknown_op_gives_helpful_error():
    """honest UX: 未知 op は候補付きの明示エラー。"""
    import pytest
    with pytest.raises(KeyError):
        u.pipeline("definitely_not_an_op").run(_img())
    with pytest.raises(AttributeError):
        u.Image(_img()).definitely_not_an_op()


def test_exposed_via_fullseye():
    """F5: fs.Image / fs.Pipeline / fs.pipeline がトップレベルに露出。"""
    import fullseye as fs
    assert hasattr(fs, "Image") and hasattr(fs, "Pipeline") and hasattr(fs, "pipeline")
    out = fs.Image(_img()).median().invert()
    assert out.history == ["median", "invert"]
