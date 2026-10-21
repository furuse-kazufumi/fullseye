"""Qt-free verification of Studio pipelines against their exported Python.

The exported program is deliberately ordinary Python that can be opened and
edited in Studio's Python editor.  Verification runs that text in an isolated
interpreter and exchanges arrays through NumPy files; the GUI process never
imports or executes the exported text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import subprocess
import sys
import tempfile
from typing import Mapping

import numpy as np


_NAN_POLICIES = {"same_positions", "ignore", "strict"}


@dataclass(frozen=True)
class RoundtripStage:
    index: int
    ok: bool
    shape_ok: bool
    dtype_ok: bool
    finite_ok: bool
    nan_ok: bool
    values_ok: bool
    max_abs_error: float | None = None
    max_rel_error: float | None = None
    message: str = ""


@dataclass(frozen=True)
class RoundtripReport:
    stages: tuple[RoundtripStage, ...] = field(default_factory=tuple)
    missing_gui: tuple[int, ...] = field(default_factory=tuple)
    missing_exported: tuple[int, ...] = field(default_factory=tuple)
    atol: float = 0.0
    rtol: float = 0.0
    nan_policy: str = "same_positions"

    @property
    def ok(self):
        return (not self.missing_gui and not self.missing_exported
                and all(stage.ok for stage in self.stages))

    @property
    def first_mismatch(self):
        bad = list(self.missing_gui) + list(self.missing_exported)
        bad += [stage.index for stage in self.stages if not stage.ok]
        return min(bad) if bad else None

    def describe(self, lang="en"):
        """Return a short Problems-pane summary in one of Studio's languages."""
        language = str(lang or "en").split("-", 1)[0].lower()
        labels = {
            "en": ("Export matches GUI at all %d stages.",
                   "Export differs from GUI first at stage %d: %s",
                   "shape, dtype, finite values, NaN positions and tolerance were checked."),
            "ja": ("エクスポート結果は全%d段でGUI結果と一致しました。",
                   "エクスポート結果は段%dで初めてGUI結果と異なります: %s",
                   "shape、dtype、有限値、NaN位置、許容誤差を確認しました。"),
            "zh": ("导出结果在全部%d个阶段都与GUI结果一致。",
                   "导出结果首次在阶段%d与GUI结果不同：%s",
                   "已检查形状、数据类型、有限值、NaN位置和容差。"),
            "tw": ("匯出結果在全部%d個階段都與GUI結果一致。",
                   "匯出結果首次在階段%d與GUI結果不同：%s",
                   "已檢查形狀、資料型別、有限值、NaN位置與容差。"),
            "ko": ("내보낸 결과가 전체 %d단계에서 GUI 결과와 일치합니다.",
                   "내보낸 결과가 %d단계에서 처음 다릅니다: %s",
                   "shape, dtype, 유한값, NaN 위치와 허용 오차를 확인했습니다."),
            "de": ("Der Export stimmt in allen %d Stufen mit der GUI überein.",
                   "Der Export weicht erstmals in Stufe %d von der GUI ab: %s",
                   "Form, Datentyp, endliche Werte, NaN-Positionen und Toleranz wurden geprüft."),
            "hi": ("निर्यात सभी %d चरणों में GUI परिणाम से मेल खाता है।",
                   "निर्यात पहली बार चरण %d में GUI परिणाम से अलग है: %s",
                   "shape, dtype, सीमित मान, NaN स्थान और tolerance जाँचे गए।"),
        }
        good, bad, checked = labels.get(language, labels["en"])
        if self.ok:
            return (good % len(self.stages)) + " " + checked
        idx = self.first_mismatch
        detail = "missing stage result"
        stage = next((s for s in self.stages if s.index == idx), None)
        if stage is not None and stage.message:
            detail = stage.message
        return (bad % ((idx + 1) if idx is not None else 0, detail)) + " " + checked


def export_script(model, input_ref=None):
    """Return editable Python whose ``run(input)`` returns every stage result.

    Each pipeline operation occupies one source line.  Bypassed stages are kept
    as explicit assignments so stage numbering stays identical to the GUI.
    """
    ref = json.dumps(dict(input_ref or {}), sort_keys=True, ensure_ascii=True)
    lines = ["import fullseye", "import numpy as np", "", f"INPUT_REFERENCE = {ref}", "",
             "def run(input):", "    value = np.asarray(input)", "    results = {}"]
    for index, stage in enumerate(model.stages):
        name, a, b = stage[:3]
        bypass = bool(getattr(stage, "bypass", False) or (len(stage) > 3 and stage[3]))
        if bypass:
            lines.append(f"    value = value  # stage {index + 1}: bypassed {name}")
        else:
            spec = (name, a, b)
            lines.append(f"    value = fullseye.run_pipeline(value, [{spec!r}])  # stage {index + 1}")
        lines.append(f"    results[{index}] = np.asarray(value)")
    lines += ["    return results", ""]
    return "\n".join(lines)


def run_exported(script_text, input_array):
    """Run exported text under ``sys.executable -I`` and return stage arrays."""
    runner = r'''import os, sys, numpy as np
root, script_path, input_path, output_path = sys.argv[1:5]
sys.path.insert(0, root)
namespace = {"__name__": "__studio_export__", "__file__": script_path}
with open(script_path, "r", encoding="utf-8") as handle:
    code = compile(handle.read(), script_path, "exec")
exec(code, namespace)
run = namespace.get("run")
if not callable(run):
    raise RuntimeError("exported script does not define run(input)")
result = run(np.load(input_path, allow_pickle=False))
if not isinstance(result, dict):
    raise TypeError("run(input) must return a dict of stage arrays")
arrays = {}
for key, value in result.items():
    index = int(key)
    array = np.asarray(value)
    if array.dtype.hasobject:
        raise TypeError("stage %d returned an object array" % index)
    arrays["stage_%d" % index] = array
np.savez(output_path, **arrays)
'''
    root = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory(prefix="fullseye_roundtrip_") as temp:
        script_path = os.path.join(temp, "exported_pipeline.py")
        input_path = os.path.join(temp, "input.npy")
        output_path = os.path.join(temp, "results.npz")
        with open(script_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(str(script_text))
        np.save(input_path, np.asarray(input_array), allow_pickle=False)
        proc = subprocess.run([sys.executable, "-I", "-c", runner, root, script_path,
                               input_path, output_path], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
        if proc.returncode:
            detail = (proc.stderr or proc.stdout).strip()
            raise RuntimeError("exported pipeline failed in isolated Python: " + detail)
        if not os.path.isfile(output_path):
            raise RuntimeError("exported pipeline did not produce stage results")
        with np.load(output_path, allow_pickle=False) as archive:
            out = {int(name[6:]): np.array(archive[name], copy=True)
                   for name in archive.files if name.startswith("stage_")}
    return dict(sorted(out.items()))


def compare_results(gui_results, exported_results, *, atol=0.0, rtol=0.0,
                    nan_policy="same_positions"):
    """Compare aligned stage mappings without changing either set of values."""
    if nan_policy not in _NAN_POLICIES:
        raise ValueError("nan_policy must be 'same_positions', 'ignore', or 'strict'")
    if atol < 0 or rtol < 0:
        raise ValueError("atol and rtol must be non-negative")
    gui = {int(k): np.asarray(v) for k, v in gui_results.items()}
    exported = {int(k): np.asarray(v) for k, v in exported_results.items()}
    common = sorted(set(gui) & set(exported))
    stages = []
    for index in common:
        a, b = gui[index], exported[index]
        shape_ok = a.shape == b.shape
        dtype_ok = a.dtype == b.dtype
        finite_ok = nan_ok = values_ok = False
        max_abs = max_rel = None
        messages = []
        if not shape_ok:
            messages.append("shape %s != %s" % (a.shape, b.shape))
        if not dtype_ok:
            messages.append("dtype %s != %s" % (a.dtype, b.dtype))
        if shape_ok:
            try:
                a_nan, b_nan = np.isnan(a), np.isnan(b)
                a_inf, b_inf = np.isinf(a), np.isinf(b)
            except TypeError:
                a_nan = b_nan = np.zeros(a.shape, dtype=bool)
                a_inf = b_inf = np.zeros(a.shape, dtype=bool)
            nan_ok = (not np.any(a_nan | b_nan) if nan_policy == "strict"
                      else True if nan_policy == "ignore" else np.array_equal(a_nan, b_nan))
            finite_ok = np.array_equal(a_inf, b_inf)
            if finite_ok and np.any(a_inf):
                finite_ok = np.array_equal(a[a_inf], b[b_inf])
            mask = ~(a_nan | b_nan | a_inf | b_inf)
            try:
                values_ok = bool(np.allclose(a[mask], b[mask], atol=atol, rtol=rtol,
                                             equal_nan=False))
                if np.any(mask):
                    delta = np.abs(a[mask] - b[mask])
                    max_abs = float(np.max(delta))
                    denom = np.maximum(np.abs(b[mask]), np.finfo(float).tiny)
                    max_rel = float(np.max(delta / denom))
            except (TypeError, ValueError):
                values_ok = bool(np.array_equal(a[mask], b[mask]))
            if not nan_ok:
                messages.append("NaN positions differ" if nan_policy != "strict" else "NaN is not allowed")
            if not finite_ok:
                messages.append("infinite values differ")
            if not values_ok:
                messages.append("values exceed tolerance (max abs %s)" % max_abs)
        ok = shape_ok and dtype_ok and finite_ok and nan_ok and values_ok
        stages.append(RoundtripStage(index, ok, shape_ok, dtype_ok, finite_ok, nan_ok,
                                     values_ok, max_abs, max_rel, "; ".join(messages)))
    return RoundtripReport(tuple(stages), tuple(sorted(set(exported) - set(gui))),
                           tuple(sorted(set(gui) - set(exported))), float(atol), float(rtol),
                           nan_policy)
