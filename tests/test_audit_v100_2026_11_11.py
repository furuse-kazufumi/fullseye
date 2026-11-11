"""Regression tests for the v1.0.0 external audit (2026-11-11): each finding checked against the code."""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import fullseye as fs  # noqa: E402
import imgevolve  # noqa: E402
import tomography  # noqa: E402


def _fake_index(monkeypatch):
    fake = {"fake_cv_op": {"name": "fake_cv_op", "tier": "registry", "module": "backends_color",
                           "requires": ["definitely_missing_mod_xyz"]}}
    monkeypatch.setattr(api, "_SHIPPED_INDEX_CACHE", fake)


def test_cli_has_says_exists_but_backend_missing_not_unknown(monkeypatch, capsys):
    _fake_index(monkeypatch)
    rc = imgevolve.cmd_has(argparse.Namespace(op="fake_cv_op"))
    out = capsys.readouterr().out
    assert rc == 1                                   # not available here: still a non-zero exit
    assert "unknown op" not in out
    assert "exists" in out.lower() and "definitely_missing_mod_xyz" in out and "pip install" in out


def test_cli_has_still_says_unknown_for_a_name_nobody_knows(monkeypatch, capsys):
    monkeypatch.setattr(api, "_SHIPPED_INDEX_CACHE", {})
    rc = imgevolve.cmd_has(argparse.Namespace(op="no_such_op_zzz_9"))
    assert rc == 1 and "unknown op" in capsys.readouterr().out


def test_facade_attribute_for_a_missing_backend_op_explains_the_extra(monkeypatch):
    _fake_index(monkeypatch)
    with pytest.raises(AttributeError) as ei:
        fs.fake_cv_op                                  # noqa: B018
    assert "definitely_missing_mod_xyz" in str(ei.value) and "pip install" in str(ei.value)
    assert not hasattr(fs, "fake_cv_op")               # the contract: still an AttributeError


def test_facade_attribute_for_a_registered_op_points_at_apply():
    name = "otsu"
    if hasattr(fs, name):
        pytest.skip("otsu became a facade attribute")
    with pytest.raises(AttributeError) as ei:
        getattr(fs, name)
    assert "fullseye.apply" in str(ei.value) and "fullseye.op.otsu" in str(ei.value)


def test_facade_attribute_for_an_unknown_name_keeps_the_plain_message():
    with pytest.raises(AttributeError) as ei:
        fs.no_such_name_zzz_9                           # noqa: B018
    assert str(ei.value) == "module 'fullseye' has no attribute 'no_such_name_zzz_9'"


def test_fbp_default_size_is_the_inscribed_square_not_the_source_size():
    """Documented, deliberate, and recorded (KNOWN_ISSUES §53): the sinogram does not carry the source size."""
    x = np.zeros((32, 32))
    x[10:20, 12:22] = 1.0
    sino = tomography.radon_transform(x)
    assert sino.shape[1] == 47
    assert tomography.filtered_backprojection(sino).shape == (33, 33)
    assert tomography.filtered_backprojection(sino, size=32).shape == (32, 32)
    assert "KNOWN_ISSUES" in tomography.filtered_backprojection.__doc__


def test_halcon_coverage_note_explains_the_chapter_sum():
    import halcon_coverage as hc
    a = {"per_chapter": {"A": (3, 5), "B": (1, 4)}, "real": {"x": 1, "y": 1, "z": 1},
         "chapter_ops": {"A": {"x", "y"}, "B": {"x", "z"}}, "covered": {"x"}, "n_real": 3, "version": "2605"}
    note = hc._chapter_note(a)
    assert "1 operators under more than one chapter" in note and "4 covered / 9 total" in note
    assert "(1 / 3)" in note and "2605" in note


# ---- (6) user-facing text of the installed CLI does not name the old working title -------------
def test_cli_help_and_error_do_not_name_imgevolve(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [os.path.join(ROOT, "fullseye", "__main__.py"), "--help"])
    with pytest.raises(SystemExit):
        imgevolve.main()
    helptext = capsys.readouterr().out
    head = helptext.split("(installed:")[0]               # the checkout spelling lives only in the epilog
    assert "imgevolve" not in head and "fullseye — single CLI entry point" in helptext
    assert "python -m fullseye has" in head
    monkeypatch.setattr(sys, "argv", [os.path.join(ROOT, "fullseye", "__main__.py"), "apply", "x", "y", "z"])
    monkeypatch.setattr(imgevolve, "_find_op", lambda ops, key: None)
    with pytest.raises(SystemExit) as ei:
        imgevolve.main()
    assert "imgevolve" not in str(ei.value) and "python -m fullseye has" in str(ei.value)


def test_installed_console_script_error_uses_fullseye(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["C:\\Scripts\\fullseye.exe", "apply", "x", "y", "z"])
    monkeypatch.setattr(imgevolve, "_find_op", lambda ops, key: None)
    with pytest.raises(SystemExit) as ei:
        imgevolve.main()
    assert "imgevolve" not in str(ei.value) and "fullseye has" in str(ei.value)


# ---- (7) a plain uint8 -> float conversion is not reported as a degradation --------------------
def test_uint8_input_warns_neutrally_once_and_still_counts():
    import warnings
    import backend_safe as bs
    fs.clear_fallbacks()
    x = (np.random.default_rng(0).random((16, 16)) * 255).astype(np.uint8)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        for _ in range(3):
            fs.apply(x, "gauss_filter", 0.5)
    msgs = [str(m.message) for m in w if issubclass(m.category, fs.FullseyeFallbackWarning)]
    if not bs._WARN_ONCE:
        pytest.skip("FULLSEYE_QUIET_FALLBACK set")
    assert len(msgs) <= 1                                  # first time only, never per call
    assert all("degraded" not in m and "converted" in m for m in msgs), msgs
    assert fs.fallback_counts().get("gauss_filter") == 3   # the ledger keeps counting every conversion


def test_a_real_degradation_keeps_the_degraded_text():
    import warnings
    import backend_safe as bs
    if not bs._WARN_ONCE:
        pytest.skip("FULLSEYE_QUIET_FALLBACK set")
    bs._WARNED.discard("zz_audit_op")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        bs.record("zz_audit_op", RuntimeError("boom"), "image", source="op")
    assert any("degraded to a fallback" in str(m.message) for m in w)
    assert not bs._is_dtype_conversion("RuntimeError: boom")
