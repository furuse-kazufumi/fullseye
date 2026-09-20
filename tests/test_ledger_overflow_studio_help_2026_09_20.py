# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""0.2.2 第 2 陣(2026-09-20): 台帳の取りこぼしを数える(N158)/ studio の --help が Qt を起こさない(N154)/
facade の名前空間に import の道具が漏れない(N175 / N176)。"""
from __future__ import annotations

import os
import subprocess
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import backend_safe  # noqa: E402
import fullseye as fs  # noqa: E402


def test_fallback_ring_counts_what_it_evicts():
    fs.clear_fallbacks()
    assert fs.fallback_overflow() == 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(backend_safe._EVENT_MAX + 7):
            backend_safe.record("ring_probe_%d" % (i % 3), RuntimeError("x"), "image", source="test")
    assert len(fs.fallbacks()) == backend_safe._EVENT_MAX
    assert fs.fallback_overflow() == 7
    assert sum(fs.fallback_counts().values()) == len(fs.fallbacks()) + fs.fallback_overflow()
    fs.clear_fallbacks()
    assert fs.fallback_overflow() == 0 and fs.fallbacks() == []


def _studio(args, env_extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")}
    env.update(env_extra)
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, os.path.join(ROOT, "studio.py")] + args, capture_output=True,
                          text=True, encoding="utf-8", env=env, cwd=ROOT, timeout=120)


def test_studio_help_and_version_answer_without_qt():
    r = _studio(["--help"], {})
    assert r.returncode == 0 and r.stdout.startswith("usage: fullseye-studio"), (r.returncode, r.stdout[:80], r.stderr[-200:])
    r = _studio(["--version"], {})
    assert r.returncode == 0 and r.stdout.strip() == "fullseye-studio %s" % fs.__version__
    r = _studio(["--bogus"], {})
    assert r.returncode == 2 and "unknown argument" in r.stderr


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="the display check is Linux-only")
def test_studio_without_a_display_stops_with_a_sentence_not_an_abort():
    r = _studio([], {})
    assert r.returncode == 2 and "no display" in r.stderr and "QT_QPA_PLATFORM" in r.stderr


def test_facade_namespace_has_no_import_tools():
    for name in ("os", "sys", "warnings", "annotations"):
        assert not hasattr(fs, name), "fullseye.%s が漏れている" % name
    assert fs.read_image and fs.apply and fs.__version__          # 消しても facade は動く
    assert np.asarray(fs.apply(np.zeros((8, 8)), "identity")).shape == (8, 8)
