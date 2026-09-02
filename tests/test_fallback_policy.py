"""The facade's error policy and the fallback ledger (backend_safe + api).

2026-09-02 audit: 6 of the 7 confirmed bugs were of the "no exception, wrong
answer" kind, because fail-soft was stacked in three layers (facade / GPU branch /
per-backend ``_safe``) and only ONE of 24 wrapper families recorded anything.
These tests pin the resolution:

* every fail-soft wrapper reports to the same ledger (``backend_safe.guard``);
* ``on_error="fallback"`` keeps the old behaviour but is visible (ledger + one
  warning per op); ``"warn"`` warns every time; ``"raise"`` is fail-closed;
* a wrong-sort input, a failed GPU path and a failed op are three distinguishable
  ledger sources;
* the n-ary tier is callable from the facade with a list of inputs (it used to be
  listed by ``list_ops`` but raise ``KeyError`` from ``apply``);
* the matching ops accept a template through the facade;
* HALCON aliases shared by several ops resolve by an explicit table, never by
  registration order.
"""
import warnings

import numpy as np
import pytest

import api
import backend_safe as bs
import backends
import ops


def _img(n=32):
    y, x = np.mgrid[0:n, 0:n]
    return np.clip(0.5 + 0.3 * np.sin(x / 5.0) * np.cos(y / 7.0), 0, 1)


def _boom(v, a, b):
    raise RuntimeError("library API drift")


@pytest.fixture(autouse=True)
def _clean_ledger():
    bs.clear_fallbacks(reset_warnings=True)
    yield
    bs.clear_fallbacks(reset_warnings=True)


# --------------------------------------------------------------------------- #
# guard: one mediator
# --------------------------------------------------------------------------- #
def test_guard_records_and_degrades_by_default():
    w = bs.guard(_boom, "image", name="boom_op")
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        out = w(_img(), 0.5, 0.5)
    assert np.array_equal(out, _img())                      # old behaviour: clipped input
    assert bs.fallback_counts() == {"boom_op": 1}
    ev = bs.last_fallback()
    assert ev["name"] == "boom_op" and ev["source"] == "op" and "API drift" in ev["error"]
    assert [r for r in rec if issubclass(r.category, bs.FullseyeFallbackWarning)]


def test_guard_warns_once_per_name_but_counts_every_time():
    w = bs.guard(_boom, "image", name="boom_once")
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        for _ in range(5):
            w(_img(), 0.5, 0.5)
    n_warn = len([r for r in rec if issubclass(r.category, bs.FullseyeFallbackWarning)])
    assert n_warn == 1
    assert bs.fallback_counts()["boom_once"] == 5


def test_guard_reraises_in_strict_mode():
    w = bs.guard(_boom, "image", name="boom_strict")
    with bs.strict_mode():
        with pytest.raises(RuntimeError, match="API drift"):
            w(_img(), 0.5, 0.5)
    assert bs.fallback_counts() == {}                        # nothing was swallowed


def test_guard_custom_on_fail_and_finish_are_honoured():
    w = bs.guard(_boom, "image", name="custom", on_fail=lambda v: np.full_like(v, 0.25))
    assert np.all(w(_img(), 0.5, 0.5) == 0.25)
    w2 = bs.guard(lambda v, a, b: v * 3.0, "image", name="fin", finish=lambda o, v: np.clip(o, 0, 1))
    assert w2(_img(), 0.5, 0.5).max() <= 1.0


def test_every_backend_wrapper_family_reports_to_the_ledger():
    """Force every registry op through a raising body and check the ledger sees it.

    The wrappers are created at build time around the real op body; here we go
    through the SAME wrapper factories by calling each backend's ``_safe`` (or the
    guard) on ``_boom`` — the point is that no backend file keeps a private,
    non-recording ``except Exception``.
    """
    import importlib
    import pkgutil
    seen = 0
    for name in sorted(m.name for m in pkgutil.iter_modules(["."]) if m.name.startswith("backends_")):
        mod = importlib.import_module(name)
        safe = getattr(mod, "_safe", None)
        if safe is None:
            continue
        bs.clear_fallbacks()
        try:
            w = safe(_boom, "image")
        except TypeError:                                    # decomp/filters2/physics: _safe(fn)
            w = safe(_boom)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w(_img(), 0.5, 0.5)
        assert bs.fallback_counts(), "%s._safe swallowed an exception without recording it" % name
        seen += 1
    assert seen >= 15


def test_backends_compat_aliases_still_work():
    backends.clear_errors()
    assert backends.last_error() is None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        backends._safe(_boom, "region")(_img(), 0.5, 0.5)
    err = backends.last_error()
    assert err["fn"] == err["name"] and err["out_sort"] == "region"
    assert len(backends.swallowed_errors()) == 1


def test_registry_ops_carry_the_guard_marker():
    """Every backend-registered op that went through a wrapper is identifiable."""
    marked = sum(1 for fn in ops.RT.values() if getattr(fn, "__fullseye_guarded__", False))
    assert marked > 300, marked


# --------------------------------------------------------------------------- #
# facade policy
# --------------------------------------------------------------------------- #
def test_apply_default_policy_is_unchanged_but_visible(monkeypatch):
    monkeypatch.setitem(ops.RT, "gaussian", bs.guard(_boom, "image"))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        out = api.apply(_img(), "gaussian")
    assert out.shape == (32, 32)
    assert bs.fallback_counts() == {"gaussian": 1}           # attributed to the OP name
    assert any(issubclass(r.category, bs.FullseyeFallbackWarning) for r in rec)


def test_apply_on_error_raise_is_fail_closed(monkeypatch):
    monkeypatch.setitem(ops.RT, "gaussian", bs.guard(_boom, "image"))
    with pytest.raises(RuntimeError, match="API drift"):
        api.apply(_img(), "gaussian", on_error="raise")
    assert bs.fallback_counts() == {}


def test_apply_on_error_warn_warns_every_call(monkeypatch):
    monkeypatch.setitem(ops.RT, "gaussian", bs.guard(_boom, "image"))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        for _ in range(3):
            api.apply(_img(), "gaussian", on_error="warn")
    assert len([r for r in rec if issubclass(r.category, bs.FullseyeFallbackWarning)]) >= 3


def test_apply_on_error_env_default(monkeypatch):
    monkeypatch.setitem(ops.RT, "gaussian", bs.guard(_boom, "image"))
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")
    with pytest.raises(RuntimeError):
        api.apply(_img(), "gaussian")
    with pytest.raises(ValueError):
        api.apply(_img(), "gaussian", on_error="explode")


def test_wrong_sort_input_is_recorded_by_default_and_raised_when_strict():
    v = np.linspace(0, 1, 40)                                # 1-D handed to an image op
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        api.apply(v, "sobel_amp")
    evs = [e for e in bs.fallbacks() if e["source"] == "input"]
    assert evs and evs[0]["name"] == "sobel_amp"
    with pytest.raises(ValueError, match="expects a image"):
        api.apply(v, "sobel_amp", on_error="raise")


def test_run_pipeline_attributes_fallbacks_per_stage(monkeypatch):
    monkeypatch.setitem(ops.RT, "invert", bs.guard(_boom, "image"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = api.run_pipeline(_img(), ["gaussian", "invert", "otsu"])
    assert set(np.unique(out)).issubset({0.0, 1.0})
    assert bs.fallback_counts() == {"invert": 1}
    with pytest.raises(RuntimeError):
        api.run_pipeline(_img(), ["gaussian", "invert"], on_error="raise")


def test_gpu_failure_is_recorded_not_swallowed(monkeypatch):
    """A broken accelerated kernel used to fall to CPU under ``except Exception: pass``."""
    import types
    fake = types.SimpleNamespace(
        ACCEL={"gaussian_gpu": (None, "gaussian", None)},
        run_batch=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("CUDA kernel exploded")),
    )
    monkeypatch.setitem(__import__("sys").modules, "accel", fake)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = api.apply(_img(), "gaussian", device="cuda")   # CPU result, but RECORDED
    assert out.shape == (32, 32)
    evs = [e for e in bs.fallbacks() if e["source"] == "gpu"]
    assert evs and "CUDA kernel exploded" in evs[0]["error"]
    with pytest.raises(RuntimeError, match="CUDA kernel exploded"):
        api.apply(_img(), "gaussian", device="cuda", on_error="raise")


def test_gpu_absent_is_silent_by_design(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "accel", None)   # import raises ImportError
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        api.apply(_img(), "gaussian", device="cuda", on_error="raise")
    assert not [r for r in rec if issubclass(r.category, bs.FullseyeFallbackWarning)]
    assert bs.fallback_counts() == {}


# --------------------------------------------------------------------------- #
# n-ary tier, templates, aliases
# --------------------------------------------------------------------------- #
def test_nary_ops_are_callable_with_a_list_and_explain_single_input_misuse():
    nary = api._nary_by_name()
    if "add_image" not in nary:
        pytest.skip("n-ary tier unavailable")
    a, b = _img(), 1.0 - _img()
    out = api.apply([a, b], "add_image", 0.5, 0.5)
    assert out.shape == a.shape and np.all(np.isfinite(out))
    with pytest.raises(TypeError, match="n-ary"):
        api.apply(a, "add_image")
    with pytest.raises(TypeError, match="takes 2 inputs"):
        api.apply([a], "add_image")
    with pytest.raises(TypeError, match="single-input"):
        api.apply([a, b], "gaussian")


def test_every_listed_nary_op_is_callable_from_the_facade():
    rows = [r for r in api.list_ops() if r["tier"] == "nary"]
    if not rows:
        pytest.skip("n-ary tier unavailable")
    a = _img()
    reg = (a > 0.5).astype(np.float64)
    for r in rows:
        ins = [a if s == "image" else reg for s in r["in_sorts"]]
        out = api.apply(ins, r["name"], 0.5, 0.5, on_error="raise")
        assert out is not None, r["name"]


def test_match_ops_take_a_template_through_the_facade():
    img = np.zeros((48, 48))
    img[20:28, 30:38] = _img(8)                 # textured patch (a constant one has zero NCC variance)
    tmpl = img[20:28, 30:38].copy()
    assert np.array_equal(api.apply(img, "ncc_locate"), [0.0, 0.0, 0.0])   # no template: no-match
    corr, r, c = api.apply(img, "ncc_locate", template=tmpl)
    assert corr > 0.99 and abs(r - 24) <= 1 and abs(c - 34) <= 1     # (row, col) of the match CENTRE
    assert ops._MATCH_CTX.get("template") is None                            # restored
    out = api.apply(img, "shape_locate", template=tmpl)
    assert out.shape == (4,) and out[0] > 0.9


def test_ambiguous_halcon_aliases_all_have_a_table_row():
    amb = api.ambiguous_aliases()
    missing = {k: v for k, v in amb.items() if k not in api._ALIAS_CANONICAL}
    assert not missing, "add a row to api._ALIAS_CANONICAL for: %r" % missing
    for alias, pick in api._ALIAS_CANONICAL.items():
        assert api.find_op(alias).name == pick
        assert pick in amb.get(alias, [pick])


def test_failed_backend_imports_are_visible():
    assert isinstance(api.FAILED_BACKENDS, list)
    assert api.FAILED_BACKENDS == [], api.FAILED_BACKENDS   # everything builds in this checkout
