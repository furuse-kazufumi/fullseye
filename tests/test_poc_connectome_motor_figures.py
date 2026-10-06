# -*- coding: utf-8 -*-
"""motor bottleneck PoC の**図の経路**の門(2026-10-06)。

``tests/test_poc_scripts_run.py`` は全 PoC を ``FULLSEYE_FIGURES=off`` で回すので、
``if figs.enabled():`` の中は CI が 1 度も走らせない。この PoC はそこで落ちていた:
G1 / evis のデータが無い環境では Physical AI の系列が合成歩容 1 本だけになり、
折れ線(``kind='line'``)が点 1 個で描けず、PoC 自身の ``assert not figs.errors()`` で exit 1。
手元には G1 の qpos があったので緑のまま気づかなかった。

ここでは縮小予算(合成の配線・合成歩容、7 秒ほど)で**図つき**に回し、
exit 0・図 6 枚・``05_physical_ai.png`` が実際に書かれたことを確かめる。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "examples" / "poc_connectome_motor_bottleneck.py"


def test_motor_bottleneck_figure_path_runs_without_g1_data(tmp_path):
    figdir = tmp_path / "figs"
    cwd = tmp_path / "cwd"                     # 探針の相対パスが repo 直下に落ちないように
    cwd.mkdir()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               PYTHONPATH=str(ROOT), FULLSEYE_POC_BUDGET="reduced",
               FULLSEYE_FIGURE_DIR=str(figdir))
    for k in ("FULLSEYE_FIGURES", "FULLSEYE_G1_QPOS_DIR", "FULLSEYE_EVIS_CORPUS"):
        env.pop(k, None)                       # データの無い環境を再現する
    p = subprocess.run([sys.executable, str(POC)], cwd=str(cwd), env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert p.returncode == 0, (p.stdout[-2000:], p.stderr[-2000:])
    assert "PASS" in p.stdout
    man = json.loads((figdir / "figures.json").read_text(encoding="utf-8"))
    files = [e["file"] for e in man]
    assert len(files) == 6, files
    assert "05_physical_ai.png" in files and (figdir / "05_physical_ai.png").is_file()
    cap = [e["caption"] for e in man if e["file"] == "05_physical_ai.png"][0]
    assert "synthetic gait" in cap, cap        # 使っていない G1 / evis を図注で名乗らない
