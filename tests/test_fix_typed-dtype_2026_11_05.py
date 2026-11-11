"""1.0 前の修正 2026-11-05(typed-dtype): 画素値の型つき sort にも入口の dtype 契約を掛ける。

``api._DTYPE_CONTRACT_SORTS`` は ``image`` / ``color`` / ``volume`` だけで、同じ [0,1] の画素値を運ぶ
型つき sort(``video`` の (T,H,W[,3])、``rgbimage`` の (H,W,3)、``lightfield`` の (V,U,H,W))には
契約が無かった。実測(修正前): uint8 の動画は ``on_error="raise"`` でも通り、
``tb_temporal_bandpass`` は float の答えと最大 194、``tb_temporal_band_power`` は 7246 違う値
(×255 / ×255²)を例外も台帳記録も無く返した。

門(真値 = 同じ値を float64 / 255 で渡したときの答え。独立な読み方として op の実装を直接呼んだ答え):

* 画素値の sort の全 consumer op で、整数入力は strict(``on_error="raise"``)で ValueError、
  fallback では /255 され台帳に ``dtype_converted`` が残り、答えは float /255 の答えと一致する。
* float64 入力の答えは不変(``_contract_dtype`` は同じ物を返し、apply の答えは op の実装と一致)。
* 入口は全部同じ規則: ``api.apply`` / ``api.run_pipeline`` / ``FullseyeEngine.run`` ·
  ``run_stepwise`` · ``run_cached`` / MCP の段(``server._run_op`` = ``fullseye.apply``)/
  ファサード ``fullseye.apply``。
* 画素値の約束が無い sort(counts・cimage・qimage・signal …)は契約の外のまま(整数が意味を持つ)。
"""
from __future__ import annotations

import numpy as np
import pytest

import api
import backend_safe as bs
import fullseye

#: 画素値の約束がある型つき sort(この便で契約に入れたもの)。
PIXEL_TYPED_SORTS = ("video", "rgbimage", "lightfield")
#: 画素値の約束が無い sort(契約の外のまま)。
NON_PIXEL_SORTS = ("counts", "cimage", "beatcube", "qimage", "signal", "matrix",
                   "points", "keypoints", "region")


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("FULLSEYE_ON_ERROR", raising=False)
    monkeypatch.delenv("FULLSEYE_FAST", raising=False)
    bs.clear_fallbacks()
    yield
    bs.clear_fallbacks()


def _u8_video(t=10, h=16, w=16, colour=False, seed=0):
    rng = np.random.default_rng(seed)
    tt = np.arange(t, dtype=np.float64)[:, None, None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    base = 0.5 + 0.3 * np.sin(2 * np.pi * (tt / 4.0 + xx[None] / w)) + 0.05 * yy[None] / h
    v = np.clip(base + 0.05 * rng.standard_normal((t, h, w)), 0, 1)
    if colour:
        v = np.stack([v, v ** 2, 1.0 - v], axis=-1)
    return np.round(v * 255).astype(np.uint8)


def _u8_rgb(h=20, w=20, seed=1):
    rng = np.random.default_rng(seed)
    g = np.clip(0.2 + 0.6 * rng.random((h, w)), 0, 1)
    rgb = np.asarray(fullseye.apply(g, "img_to_rgb", 0.3, 0.6), np.float64)
    return np.round(rgb * 255).astype(np.uint8)


def _u8_lightfield(h=20, w=20, seed=2):
    rng = np.random.default_rng(seed)
    g = np.clip(0.1 + 0.8 * rng.random((h, w)), 0, 1)
    lf = np.asarray(fullseye.apply(g, "img_to_lightfield", 0.5, 0.5), np.float64)
    return np.round(lf * 255).astype(np.uint8)


_MAKERS = {"video": _u8_video, "rgbimage": _u8_rgb, "lightfield": _u8_lightfield}


def _consumers(sort):
    return sorted(op.name for op in api.REGISTRY if op.in_sort == sort)


def _cases():
    out = []
    for s in PIXEL_TYPED_SORTS:
        for n in _consumers(s):
            out.append((s, n))
    return out


_CASES = _cases()


def test_inventory_is_not_empty():
    """件数の下限(空集合への表明を避ける)。video 16 本 · rgbimage 7 本 · lightfield 8 本(2026-11-05)。"""
    counts = {s: len(_consumers(s)) for s in PIXEL_TYPED_SORTS}
    assert counts["video"] >= 16 and counts["rgbimage"] >= 7 and counts["lightfield"] >= 8, counts
    assert len(_CASES) >= 31


def test_contract_set_is_exactly_the_pixel_sorts():
    for s in ("image", "color", "volume") + PIXEL_TYPED_SORTS:
        assert s in api._DTYPE_CONTRACT_SORTS, s
    for s in NON_PIXEL_SORTS:
        assert s not in api._DTYPE_CONTRACT_SORTS, s


def _same(a, b):
    a, b = np.asarray(a), np.asarray(b)
    assert a.shape == b.shape, (a.shape, b.shape)
    if a.dtype.kind in "fc":
        np.testing.assert_array_equal(np.nan_to_num(a), np.nan_to_num(b))
    else:
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("sort,name", _CASES)
def test_integer_input_refused_under_raise(sort, name):
    u8 = _MAKERS[sort]()
    with pytest.raises(ValueError) as e:
        api.apply(u8, name, 0.5, 0.5, on_error="raise")
    msg = str(e.value)
    assert "uint8" in msg and "float64" in msg and sort in msg, msg


@pytest.mark.parametrize("sort,name", _CASES)
def test_integer_input_converted_recorded_and_equal_to_float(sort, name):
    u8 = _MAKERS[sort]()
    ref = api.apply(u8.astype(np.float64) / 255.0, name, 0.5, 0.5, on_error="fallback")
    bs.clear_fallbacks()
    got = api.apply(u8, name, 0.5, 0.5, on_error="fallback")
    ev = [e for e in bs.fallbacks() if e["name"] == name and e["source"] == "input" and "dtype_converted" in e["error"]]
    assert len(ev) == 1, bs.fallbacks()
    assert "uint8 -> float64 (/255)" in ev[0]["error"]
    _same(got, ref)


@pytest.mark.parametrize("sort,name", _CASES)
def test_float64_input_untouched(sort, name):
    """float64 の入力は契約で 1 ビットも変わらない(同じ物が返る)。apply の答えは op の実装と一致する。"""
    f = _MAKERS[sort]().astype(np.float64) / 255.0
    op = api.find_op(name)
    assert api._contract_dtype(f, op, "raise") is f
    with bs.strict_mode(False):
        direct = op.fn(f.copy(), 0.5, 0.5)
    _same(api.apply(f, name, 0.5, 0.5, on_error="fallback"), direct)


def test_bandpass_answer_was_x255_before_and_is_float_now():
    """不具合の中身: bandpass は線形なので uint8 のまま走らせると答えが厳密に 255 倍になる。
    修正後の fallback 経路の答えは float /255 の答えと一致し、255 倍の答えとは一致しない。"""
    u8 = _u8_video()
    f = u8.astype(np.float64) / 255.0
    op = api.find_op("tb_temporal_bandpass")
    with bs.strict_mode(False):
        raw = np.asarray(op.fn(u8.astype(np.float64), 0.5, 0.5))     # what the unguarded path computed
    good = np.asarray(api.apply(f, "tb_temporal_bandpass", 0.5, 0.5))
    assert float(np.max(np.abs(good))) > 1e-3                         # a non-trivial answer
    np.testing.assert_allclose(raw, 255.0 * good, rtol=1e-9, atol=1e-9)
    got = np.asarray(api.apply(u8, "tb_temporal_bandpass", 0.5, 0.5, on_error="fallback"))
    np.testing.assert_array_equal(got, good)
    assert float(np.max(np.abs(got - raw))) > 1.0


def test_colour_video_is_under_the_contract():
    u8 = _u8_video(colour=True)
    assert u8.shape[-1] == 3 and u8.ndim == 4
    names = _consumers("video")
    assert len(names) >= 16
    for n in names:
        with pytest.raises(ValueError):
            api.apply(u8, n, 0.5, 0.5, on_error="raise")
        ref = api.apply(u8.astype(np.float64) / 255.0, n, 0.5, 0.5, on_error="fallback")
        _same(api.apply(u8, n, 0.5, 0.5, on_error="fallback"), ref)


def test_uint16_and_bool_follow_the_image_rule():
    u8 = _u8_video()
    u16 = (u8.astype(np.uint16) * 257)
    ref = api.apply(u16.astype(np.float64) / 65535.0, "tb_moving_average_window", 0.5, 0.5)
    _same(api.apply(u16, "tb_moving_average_window", 0.5, 0.5, on_error="fallback"), ref)
    m = u8 > 128
    with pytest.raises(ValueError):
        api.apply(m, "tb_moving_average_window", 0.5, 0.5, on_error="raise")
    ref = api.apply(m.astype(np.float64), "tb_moving_average_window", 0.5, 0.5)
    _same(api.apply(m, "tb_moving_average_window", 0.5, 0.5, on_error="fallback"), ref)


# --------------------------------------------------------------------------- #
# every entry applies the same rule                                            #
# --------------------------------------------------------------------------- #
_ENTRY_OPS = ("tb_temporal_bandpass", "tb_temporal_band_power")


@pytest.mark.parametrize("name", _ENTRY_OPS)
def test_all_entries_agree(name, monkeypatch):
    import engine
    from fullseye.mcp import server

    u8 = _u8_video()
    f = u8.astype(np.float64) / 255.0
    good = np.asarray(api.apply(f, name, 0.5, 0.5))
    op = api.find_op(name)

    # strict: every entry refuses
    with pytest.raises(ValueError):
        fullseye.apply(u8, name, 0.5, 0.5, on_error="raise")
    with pytest.raises(ValueError):
        api.run_pipeline(u8, [(name, 0.5, 0.5)], on_error="raise")
    out, _deg, err = server._run_op(u8, op, 0.5, 0.5, False)
    assert out is None and err is not None and err["type"] == "ValueError", err
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")
    eng = engine.FullseyeEngine([(name, 0.5, 0.5)])
    with pytest.raises(ValueError):
        eng.run(u8)
    with pytest.raises(ValueError):
        eng.run_stepwise(u8)
    with pytest.raises(ValueError):
        eng.run_cached(u8)
    monkeypatch.delenv("FULLSEYE_ON_ERROR")

    # fallback: every entry converts, records, and returns the float answer
    results = {
        "fullseye.apply": lambda: fullseye.apply(u8, name, 0.5, 0.5, on_error="fallback"),
        "run_pipeline": lambda: api.run_pipeline(u8, [(name, 0.5, 0.5)], on_error="fallback"),
        "mcp_stage": lambda: server._run_op(u8, op, 0.5, 0.5, True)[0],
        "engine.run": lambda: engine.FullseyeEngine([(name, 0.5, 0.5)]).run(u8),
        "engine.run_stepwise": lambda: engine.FullseyeEngine([(name, 0.5, 0.5)]).run_stepwise(u8)[-1],
        "engine.run_cached": lambda: engine.FullseyeEngine([(name, 0.5, 0.5)]).run_cached(u8),
    }
    assert len(results) == 6
    for entry, call in results.items():
        bs.clear_fallbacks()
        got = call()
        ev = [e for e in bs.fallbacks() if "dtype_converted" in e["error"]]
        assert len(ev) >= 1, (entry, bs.fallbacks())
        np.testing.assert_array_equal(np.asarray(got), good, err_msg=entry)


# --------------------------------------------------------------------------- #
# sorts without a pixel-value promise stay outside                              #
# --------------------------------------------------------------------------- #
def test_counts_integer_is_the_meaning_and_stays_untouched():
    rng = np.random.default_rng(5)
    c = rng.poisson(40.0, size=64).astype(np.int64)
    names = _consumers("counts")
    assert len(names) >= 8
    op = api.find_op("tb_counts_to_countrate")
    assert api._contract_dtype(c, op, "raise") is c
    for n in names:
        bs.clear_fallbacks()
        try:
            api.apply(c, n, 0.5, 0.5, on_error="fallback")
        except Exception:  # noqa: BLE001 - only the dtype contract is under test here
            pass
        assert not [e for e in bs.fallbacks() if "dtype_converted" in e["error"]], n


@pytest.mark.parametrize("sort", NON_PIXEL_SORTS)
def test_non_pixel_sorts_are_passed_through(sort):
    names = _consumers(sort)
    assert len(names) >= 1, sort
    op = api.find_op(names[0])
    x = np.arange(12, dtype=np.int64).reshape(4, 3)
    assert api._contract_dtype(x, op, "raise") is x
