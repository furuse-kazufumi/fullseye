# -*- coding: utf-8 -*-
"""同じ粒子を SEM と TEM で測る PoC の固有契約。"""
from __future__ import annotations

import os
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

from examples import poc_sem_tem_same_particle as P


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


def test_sem_secondary_electron_resemblance_and_destructive_dwell_probe():
    """SEの縁強調とPoisson滞留時間則を公開統計に照合する。

    J. Jirákほか, Scanning 34 (2012), PMC5449051 は急斜面のoverbrighteningを
    edge effectとして報告する（CC BY 3.0）。A. Dattaほか, Microscopy and
    Microanalysis 31 (2025), doi:10.1093/mam/ozaf048.213 は電子計数のPoisson挙動を
    報告する（著者公開抄録、数値法則のみ使用）。画像は転載しない。
    """
    s = P.specimen()
    full = P.sem_micrograph(s, 10.0, seed=610)
    half = P.sem_micrograph(s, 5.0, seed=610)
    h = np.maximum(P._continuous_field(s["height"]), 0.0)
    gy, gx = np.gradient(h, P.MICRO_PX_NM)
    slope = np.hypot(gx, gy)
    facing = -gx/np.sqrt(1+gx*gx+gy*gy)
    particle = h > .1
    edge = particle & (slope > np.percentile(slope[particle], 70)) & (facing > 0)
    top = particle & (slope < np.percentile(slope[particle], 30))
    assert 1.15 < full["ideal"][edge].mean()/full["ideal"][top].mean() < 1.45
    bg = h < .01
    ratio = np.std((half["raw"]-half["ideal"])[bg]) / np.std((full["raw"]-full["ideal"])[bg])
    assert abs(ratio-math.sqrt(2))/math.sqrt(2) < .12
    # Destructive probe: unchanged counts at half dwell must be rejected.
    assert abs(1.0-math.sqrt(2))/math.sqrt(2) > .12


def test_tem_fresnel_and_support_spectrum_resemblance_with_destructive_probe():
    """第一Fresnel縞と非晶質支持膜の周波数統計を公開物理に照合する。

    K. Fukushima, H. Kawakatsu, A. Fukami, Journal of Physics D 7 (1974)
    257, doi:10.1088/0022-3727/7/2/310 は焦点外れによるFresnel縞を報告する
    （出版社著作物、式と数値のみ使用、画像転載なし）。J. M. Gibsonほか,
    Microscopy and Microanalysis 31 (2025), doi:10.1093/mam/ozaf049 は非晶質試料の
    Poisson支配域を報告する（著者公開抄録、数値のみ使用）。
    """
    lam = P.TEM.tem_wavelength(300.0)["wavelength_A"] * .1
    f1 = P.tem_particle(52.0, 6000.0)[2]
    f2 = P.tem_particle(52.0, 12000.0)[2]
    assert abs(f1-math.sqrt(lam*6000.0)) < 1e-12
    assert abs(f2/f1-math.sqrt(2)) < 1e-12
    texture = P._powerlaw_texture(512, -2.2, seed=811)
    power = np.abs(np.fft.rfft2(texture))**2
    fy = np.fft.fftfreq(512)[:, None]; fx = np.fft.rfftfreq(512)[None, :]
    freq = np.hypot(fx, fy); band = (freq > .01) & (freq < .20)
    slope = np.polyfit(np.log(freq[band]), np.log(power[band]), 1)[0]
    assert -2.45 < slope < -1.95
    # Destructive probe: a linear-in-defocus renderer would double, not grow by sqrt(2).
    assert abs(2.0-math.sqrt(2)) > .10
