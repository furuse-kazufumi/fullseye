"""facade の dtype 契約・CPU fast twin 配線・O(N) region 判定の回帰テスト。

``docs/design/PERF_MEMORY_VIDEO_SURVEY.md`` の recommendation (a′) と §5.3 の
item 1 / 3 / 4 に対応する:

* item 1 — 整数 image 入力は「黙って別物」ではなく **変換 + 記録** か **拒否**
* (a′)  — ``fast=True`` / ``FULLSEYE_FAST=1`` の twin 経路は core と同じ答え
* item 3 — ``_coerce_input`` の ``np.unique`` を O(N) 判定に置換(判定は不変)
* item 4 — ``_try_accel`` の ACCEL 逆引きをモジュールレベルにキャッシュ
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

import api
import backend_safe as bs
import ops

try:
    import fast
    _HAS_FAST = bool(fast.FAST)
except Exception:                                    # pragma: no cover
    fast = None
    _HAS_FAST = False


def _img(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    rng = np.random.default_rng(4242)
    return np.clip(0.35 * (xx / (n - 1)) + 0.45 * disk + 0.03 * rng.standard_normal((n, n)), 0, 1)


@pytest.fixture(autouse=True)
def _clean_ledger(monkeypatch):
    monkeypatch.delenv("FULLSEYE_FAST", raising=False)
    monkeypatch.delenv("FULLSEYE_ON_ERROR", raising=False)
    bs.clear_fallbacks()
    api.reset_fast()
    yield
    bs.clear_fallbacks()
    api.reset_fast()


# --------------------------------------------------------------------------- #
# §5.3 item 1 — integer image input is fail-closed, not silently wrong        #
# --------------------------------------------------------------------------- #
def test_uint8_image_raises_under_on_error_raise():
    u8 = np.round(_img() * 255).astype(np.uint8)
    with pytest.raises(ValueError) as e:
        api.apply(u8, "gaussian", 0.5, 0.5, on_error="raise")
    msg = str(e.value)
    assert "uint8" in msg and "float64" in msg and "[0,1]" in msg


def test_uint8_image_is_converted_and_recorded_by_default():
    u8 = np.round(_img() * 255).astype(np.uint8)
    got = api.apply(u8, "gaussian", 0.5, 0.5)
    ref = api.apply(u8.astype(np.float64) / 255.0, "gaussian", 0.5, 0.5)
    assert got.dtype == np.float64                    # used to come back uint8 (survey §1.3)
    assert np.array_equal(got, ref)
    evs = [e for e in bs.fallbacks() if e["source"] == "input"]
    assert evs and "dtype_converted" in evs[-1]["error"] and "uint8" in evs[-1]["error"]


def test_uint16_and_bool_images_use_their_own_full_scale():
    x = _img()
    u16 = np.round(x * 65535).astype(np.uint16)
    assert np.allclose(api.apply(u16, "gaussian"),
                       api.apply(u16.astype(np.float64) / 65535.0, "gaussian"))
    mask = x > 0.5
    assert np.array_equal(api.apply(mask, "gaussian"),
                          api.apply(mask.astype(np.float64), "gaussian"))


def test_threshold_no_longer_returns_all_ones_for_uint8():
    """survey §1.3: ``threshold`` on uint8 was ``v > 0.5`` over 0..255 = every pixel."""
    u8 = np.round(_img() * 255).astype(np.uint8)
    out = api.apply(u8, "threshold", 0.5, 0.5)
    assert out.dtype == np.float64
    assert 0.0 < float(out.mean()) < 1.0
    assert np.array_equal(out, api.apply(u8.astype(np.float64) / 255.0, "threshold", 0.5, 0.5))


def test_int_region_mask_is_untouched_by_the_dtype_contract():
    """region ops legitimately take an int {0,1} mask — no rescaling, no ledger noise."""
    mask = np.zeros((24, 24), np.uint8)
    mask[4:14, 6:18] = 1
    out = api.apply(mask, "reg_erode", 0.5, 0.5)
    assert out.dtype == np.float64
    assert np.array_equal(out, api.apply(mask.astype(np.float64), "reg_erode", 0.5, 0.5))
    assert not [e for e in bs.fallbacks() if "dtype_converted" in e["error"]]


def test_run_pipeline_applies_the_same_dtype_contract():
    u8 = np.round(_img() * 255).astype(np.uint8)
    with pytest.raises(ValueError):
        api.run_pipeline(u8, ["gaussian", "sobel_mag"], on_error="raise")
    got = api.run_pipeline(u8, ["gaussian", "sobel_mag"])
    ref = api.run_pipeline(u8.astype(np.float64) / 255.0, ["gaussian", "sobel_mag"])
    assert np.array_equal(got, ref)


# --------------------------------------------------------------------------- #
# (a′) the fast twin path must not change a single float64 result             #
# --------------------------------------------------------------------------- #
_HASH_OPS = ["gaussian", "mean_box", "median", "gerode", "gopen",
             "sobel_mag", "laplace", "dog", "unsharp", "std_filter"]


def _digest(x):
    a = np.ascontiguousarray(np.asarray(x, np.float64))
    return hashlib.sha256(a.tobytes()).hexdigest()


def test_float64_results_are_bit_identical_with_and_without_the_flag():
    """10 op の出力を **ハッシュで**突き合わせる。既存の float64 呼び出しは 1 ビットも変えない。

    ここで比較しているのは「fast を切った呼び出し」= 従来経路そのものと、
    「fast を入れた呼び出し」。twin が載っている op でも **同じ bytes** でなければ
    ならない(twin が bit 一致でない median は許容差の中に居るので、この test は
    twin の faithful さではなく **既定 OFF が既定経路を変えないこと**を守る)。
    """
    x = _img()
    off = {n: _digest(api.apply(x.copy(), n, 0.5, 0.4)) for n in _HASH_OPS}
    # 1) 明示 fast=False、2) 環境変数なし(既定)——どちらも従来経路
    for kw in ({"fast": False}, {}):
        again = {n: _digest(api.apply(x.copy(), n, 0.5, 0.4, **kw)) for n in _HASH_OPS}
        assert again == off
    # 3) 直接 registry を叩いた値とも一致(facade が何も足していないこと)
    direct = {n: _digest(np.asarray(ops.RT[n](x.copy(), 0.5, 0.4), np.float64)) for n in _HASH_OPS}
    assert direct == off


@pytest.mark.skipif(not _HAS_FAST, reason="OpenCV not installed")
def test_fast_flag_uses_the_twin_and_stays_within_the_parity_gate():
    x = _img()
    for n in _HASH_OPS:
        base = api.apply(x.copy(), n, 0.5, 0.4)
        quick = api.apply(x.copy(), n, 0.5, 0.4, fast=True)
        assert quick.dtype == base.dtype and quick.shape == base.shape
        assert float(np.max(np.abs(base - quick))) <= fast.PARITY_TOL, n


@pytest.mark.skipif(not _HAS_FAST, reason="OpenCV not installed")
def test_env_var_enables_the_twin_path(monkeypatch):
    x = _img()
    calls = []
    real = api._try_fast

    def spy(op, v, a, b):
        calls.append(op.name)
        return real(op, v, a, b)

    monkeypatch.setattr(api, "_try_fast", spy)
    monkeypatch.setenv("FULLSEYE_FAST", "1")
    api.apply(x, "gaussian")
    assert calls == ["gaussian"]
    calls.clear()
    monkeypatch.setenv("FULLSEYE_FAST", "0")
    api.apply(x, "gaussian")
    assert calls == []


@pytest.mark.skipif(not _HAS_FAST, reason="OpenCV not installed")
def test_a_failing_twin_is_recorded_and_falls_back_to_core(monkeypatch):
    x = _img()
    boom = {"gaussian": fast.FastTwin(
        lambda v, a, b: (_ for _ in ()).throw(RuntimeError("twin exploded")), "f64", "test")}
    monkeypatch.setattr(fast, "FAST", boom)
    got = api.apply(x, "gaussian", 0.5, 0.4, fast=True)
    assert np.array_equal(got, ops.RT["gaussian"](x.copy(), 0.5, 0.4))
    evs = [e for e in bs.fallbacks() if e["source"] == "fast"]
    assert evs and "twin exploded" in evs[-1]["error"]
    assert api.fast_open_ops() == ["gaussian"]        # breaker opened
    with pytest.raises(RuntimeError):                 # on_error="raise" re-raises
        api.apply(x, "gaussian", 0.5, 0.4, fast=True, on_error="raise")
    assert api.reset_fast() == ["gaussian"]


@pytest.mark.skipif(not _HAS_FAST, reason="OpenCV not installed")
def test_run_pipeline_fast_matches_the_core_chain():
    x = _img()
    stages = ["gaussian", "gopen", "sobel_mag"]
    base = api.run_pipeline(x.copy(), stages, 0.5, 0.4)
    quick = api.run_pipeline(x.copy(), stages, 0.5, 0.4, fast=True)
    assert float(np.max(np.abs(base - quick))) <= fast.PARITY_TOL


# --------------------------------------------------------------------------- #
# §5.3 item 3 — the O(N) region test gives np.unique's verdict, exactly       #
# --------------------------------------------------------------------------- #
def _unique_verdict(a):
    """The literal pre-2026-09-03 test, kept here as the oracle."""
    vals = np.unique(a)
    return bool(vals.size > 2 or (vals.size and (vals.min() < 0.0 or vals.max() > 1.0)))


@pytest.mark.parametrize("arr", [
    np.zeros((6, 6)),
    np.ones((6, 6)),
    np.array([[0.0, 1.0], [1.0, 0.0]]),
    np.array([[0.3, 0.7], [0.7, 0.3]]),
    np.array([[0.3, 0.7], [0.9, 0.3]]),
    np.array([[-0.5, 1.0], [1.0, 0.0]]),
    np.array([[0.0, 2.0], [2.0, 0.0]]),
    np.zeros((0, 0)),
    np.array([[1, 0], [0, 1]], np.uint8),
    np.array([[5, 0], [0, 5]], np.int64),
    np.array([[np.nan, 0.5], [0.5, np.nan]]),
    np.array([[np.nan, 0.1], [0.2, 0.3]]),
    np.array([[np.inf, 0.1], [0.2, 0.3]]),
    np.array([[-np.inf, 0.0], [0.0, 1.0]]),
    np.full((4, 4), 0.42),
])
def test_needs_binarise_matches_np_unique(arr):
    assert api._needs_binarise(arr) == _unique_verdict(arr)


def test_needs_binarise_matches_np_unique_on_random_arrays():
    rng = np.random.default_rng(11)
    for _ in range(200):
        n = int(rng.integers(1, 6))
        kind = int(rng.integers(0, 4))
        if kind == 0:
            a = rng.random((n, n))
        elif kind == 1:
            a = rng.integers(0, 2, (n, n)).astype(np.float64)
        elif kind == 2:
            a = rng.integers(-2, 4, (n, n))
        else:
            a = rng.choice([0.0, 1.0, 0.5], (n, n))
        assert api._needs_binarise(a) == _unique_verdict(a), a


def test_coerce_input_behaviour_is_unchanged_for_region_ops():
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    cases = [np.array([[0.0, 1.0], [1.0, 0.0]]),
             np.array([[0.3, 0.7], [0.7, 0.3]]),
             np.array([[0.3, 0.7], [0.9, 0.3]]),
             np.array([[1, 0], [0, 1]], np.uint8),
             np.array([[5, 0], [0, 5]], np.int64),
             np.array([[True, False], [False, True]])]
    for c in cases:
        out = np.asarray(api._coerce_input(c, op))
        if c.dtype.kind == "b":
            assert out.dtype == np.float64 and np.array_equal(out, c.astype(np.float64))
        elif _unique_verdict(c):
            assert np.array_equal(out, (c.astype(np.float64) > 0.5).astype(np.float64))
        elif c.dtype.kind in "iu":
            assert out.dtype == np.float64 and np.array_equal(out, c.astype(np.float64))
        else:
            assert out is c


# --------------------------------------------------------------------------- #
# §5.3 item 4 — the ACCEL reverse index is built once                         #
# --------------------------------------------------------------------------- #
def test_accel_reverse_is_cached_and_correct():
    accel = pytest.importorskip("accel")
    expected = {c: k for k, (_f, c, _h) in accel.ACCEL.items()}
    first = api._accel_reverse(accel)
    assert first == expected
    assert api._accel_reverse(accel) is first          # same object: not rebuilt per call


def test_accel_reverse_notices_a_swapped_table():
    """テストや実験が ACCEL を差し替えたときに古い辞書を返さない。"""
    class _Fake:
        ACCEL = {"zz_key": (None, "zz_core", "zz")}
    assert api._accel_reverse(_Fake()) == {"zz_core": "zz_key"}
    accel = pytest.importorskip("accel")
    assert api._accel_reverse(accel) == {c: k for k, (_f, c, _h) in accel.ACCEL.items()}
