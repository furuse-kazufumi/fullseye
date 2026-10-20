# -*- coding: utf-8 -*-
"""同じ粒子を SEM と TEM で測る PoC の固有契約。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "poc_sem_tem_same_particle.py"


def test_poc_runs_without_figures_and_reports_all_six_chapters():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1", CI="1",
               FULLSEYE_FIGURES="off")
    run = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), env=env,
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
    assert sum(("\n%d)" % n) in run.stdout for n in range(1, 7)) == 6
    assert "SEM/TEM headline" in run.stdout
    assert "PASS" in run.stdout


def test_poc_declares_the_reserved_accession_and_video_call():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "2026.273" in text
    assert "figs.save_video(" in text
    assert "figs.errors()" in text
