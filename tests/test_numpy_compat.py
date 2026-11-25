# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""NumPy 1.x / 2.x integration-spelling compatibility / 版差の回帰試験。"""
from __future__ import annotations

from types import SimpleNamespace

import numpy_compat as NC


def test_trapezoid_uses_numpy2_spelling_without_accessing_removed_trapz(monkeypatch):
    """NumPy 2.x 側: trapz を持たない環境でも新しい綴りだけを呼ぶ。"""
    calls = []

    def modern(y, *, x, dx, axis):
        calls.append((y, x, dx, axis))
        return "numpy2"

    monkeypatch.setattr(NC, "np", SimpleNamespace(trapezoid=modern))
    assert NC.trapezoid([1, 2], x=[0, 1], dx=0.25, axis=0) == "numpy2"
    assert calls == [([1, 2], [0, 1], 0.25, 0)]


def test_trapezoid_uses_numpy1_spelling_when_trapezoid_is_absent(monkeypatch):
    """NumPy 1.x 側: trapezoid を持たない環境では旧い綴りだけを呼ぶ。"""
    calls = []

    def legacy(y, *, x, dx, axis):
        calls.append((y, x, dx, axis))
        return "numpy1"

    monkeypatch.setattr(NC, "np", SimpleNamespace(trapz=legacy))
    assert NC.trapezoid([1, 2], x=[0, 1], dx=0.25, axis=0) == "numpy1"
    assert calls == [([1, 2], [0, 1], 0.25, 0)]
