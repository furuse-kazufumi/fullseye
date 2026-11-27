"""None の参照数が Studio の窓の 1 巡(作る・出す・言語の切り替え・消す)で減らない事(Python 3.11 のみ、2026-11-23)。

Linux CI(Python 3.11 / PySide6 6.12)で ``Fatal Python error: none_dealloc`` が毎回同じ所(窓の 16 巡目)で
起きた。None の参照数が少しずつ削られて 0 になった = どこかが None を余分に DECREF している。3.12 以降の None は
不死(immortal)なので数が変わらず、この門は 3.11 でだけ意味がある。どの段で減るかを 1 行ずつ出す。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


_ROOT = Path(__file__).resolve().parents[1]
#: 窓の巡の数(None の数が 0 に届く前に減り方が見える数。CI では 16 巡目で落ちた)。
_CYCLES = 6
#: 子プロセスの上限(窓 6 つ分。遅い CI でも余る値)。
_CHILD_TIMEOUT_SECONDS = 300
#: 1 巡あたり許す減り(ゆらぎの分。減り続けるなら 1 巡で数千になる)。
_ALLOWED_DROP_PER_CYCLE = 200

_CHILD = r"""
import gc
import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtWidgets
import studio

CYCLES = int(sys.argv[1])
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


def drain():
    for _ in range(3):
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()


def none_refs():
    gc.collect()
    return sys.getrefcount(None)


for cycle in range(CYCLES):
    row = {"cycle": cycle, "start": none_refs()}
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    row["built"] = none_refs()
    win.resize(1200, 800)
    win.show()
    pump(0.3)
    row["shown"] = none_refs()
    for lang in ("ja", "en"):
        win._apply_language(lang)
        pump(0.05)
    row["languages"] = none_refs()
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    win.deleteLater()
    drain()
    del win, _model
    drain()
    row["deleted"] = none_refs()
    print("NONE " + json.dumps(row), flush=True)
print("done", flush=True)
"""


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="None is immortal from Python 3.12: its count does not move")
def test_none_is_not_released_too_often_by_a_window_cycle(tmp_path):
    pytest.importorskip("PySide6")
    child_data = tmp_path / "child-data"
    child_data.mkdir()
    env = dict(
        os.environ,
        APPDATA=str(child_data),
        LOCALAPPDATA=str(child_data),
        FULLSEYE_STUDIO_SETTINGS=str(child_data / "studio.ini"),
        PYTHONPATH=str(_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        PYTHONUTF8="1",
        QT_QPA_PLATFORM="offscreen",
    )
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", _CHILD, str(_CYCLES)],
        cwd=_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=_CHILD_TIMEOUT_SECONDS,
    )
    rows = [json.loads(line[5:]) for line in result.stdout.splitlines() if line.startswith("NONE ")]
    report = "\n".join(
        "cycle %(cycle)d: start %(start)d  build %(b)+d  show %(s)+d  languages %(l)+d  delete %(d)+d  net %(n)+d"
        % dict(r, b=r["built"] - r["start"], s=r["shown"] - r["built"], l=r["languages"] - r["shown"],
               d=r["deleted"] - r["languages"], n=r["deleted"] - r["start"]) for r in rows)
    assert result.returncode == 0 and "done" in result.stdout, (
        result.returncode, report, result.stdout[-800:], result.stderr[-2000:])
    assert len(rows) == _CYCLES, report
    steady = rows[1:]                                    # the first cycle also fills one-time caches
    drops = [r["deleted"] - r["start"] for r in steady]
    assert min(drops) >= -_ALLOWED_DROP_PER_CYCLE, "None loses references every window cycle:\n" + report
