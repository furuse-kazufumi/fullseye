from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import realdata
from examples import poc_real_sem_metal_layer as poc


def _svg(track=True, circles=()):
    body = []
    if track:
        body.append('<path d="M2,2 L18,2 L18,7 L2,7 Z" fill="lime"/>')
    for x, y, r in circles:
        body.append('<circle cx="%s" cy="%s" r="%s" fill="red"/>' % (x, y, r))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="20" viewBox="0 0 24 20">'
            + "".join(body) + '</svg>')


def test_svg_op_and_independent_reader_agree(tmp_path):
    path = tmp_path / "label0000.svg"
    path.write_text(_svg(circles=[(8, 10, 3)]), encoding="utf-8")
    tracks, vias = poc.read_label(path, (20, 24))
    assert tracks == [[(2.0, 2.0), (18.0, 2.0), (18.0, 7.0), (2.0, 7.0)]]
    assert vias == [(8.0, 10.0, 3.0)]
    mask = poc._polygon_mask((20, 24), tracks)
    assert mask[4, 10] and not mask[10, 10]


def test_svg_reader_refuses_doctype(tmp_path):
    path = tmp_path / "label0000.svg"
    path.write_text('<!DOCTYPE svg [<!ENTITY x "boom">]><svg xmlns="http://www.w3.org/2000/svg" '
                    'viewBox="0 0 24 20"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="DOCTYPE|ENTITY"):
        poc.read_label(path, (20, 24))


def test_via_duplicates_and_border_are_counted():
    keep, duplicates, border = poc.deduplicate_vias(
        [(10, 10, 5), (11, 10, 3), (30, 30, 4), (1, 20, 3)], (40, 40))
    assert duplicates == 1
    assert border == 1
    assert keep == [(10.0, 10.0, 5.0), (30.0, 30.0, 4.0)]


def test_noisy_300_nm_band_width_is_within_one_pixel_and_methods_agree():
    got = poc.synthetic_width_gate()
    assert abs(got["pred_px"] - got["truth_px"]) <= 1.0
    assert abs(got["pred_px"] - got["skeleton_px"]) <= 1.0 + 1e-9


def test_partial_border_track_label_gap_is_counted_and_only_gap_is_excluded():
    fixed = np.zeros((40, 100), bool)
    fixed[15:25, :] = True
    label = np.zeros_like(fixed)
    label[15:25, :70] = True
    missing, whole, partial = poc._label_missing_border_tracks(fixed, label)
    assert whole == 0
    assert partial == 1
    assert not missing[20, 50]
    assert missing[20, 95]


def test_realdata_pair_discovery_is_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "dataset"
    (root / "sems").mkdir(parents=True)
    (root / "labels").mkdir()
    Image.fromarray(np.zeros((20, 24), np.uint8)).save(root / "sems" / "sem0000.png")
    (root / "labels" / "label0000.svg").write_text(_svg(), encoding="utf-8")
    monkeypatch.setenv("FULLSEYE_SEM_METAL_DATA", str(root))
    pairs = realdata.sem_metal_layer_pairs()
    assert [(a.name, b.name) for a, b in pairs] == [("sem0000.png", "label0000.svg")]
    (root / "labels" / "label0001.svg").write_text(_svg(), encoding="utf-8")
    with pytest.raises(realdata.RealDataError, match="対応する SEM が無い"):
        realdata.sem_metal_layer_pairs()


def test_realdata_pair_discovery_accepts_distributed_m2_layout(tmp_path, monkeypatch):
    root = tmp_path / "dataset"
    (root / "sems" / "m2").mkdir(parents=True)
    (root / "labels" / "m2").mkdir(parents=True)
    Image.fromarray(np.zeros((20, 24), np.uint8)).save(root / "sems" / "m2" / "sem0000.png")
    (root / "labels" / "m2" / "label0000.svg").write_text(_svg(), encoding="utf-8")
    monkeypatch.setenv("FULLSEYE_SEM_METAL_DATA", str(root))
    pairs = realdata.sem_metal_layer_pairs()
    assert [(a.name, b.name) for a, b in pairs] == [("sem0000.png", "label0000.svg")]


def test_ci_does_not_download_and_prints_recorded(tmp_path):
    env = dict(os.environ)
    env["CI"] = "1"
    env.pop("FULLSEYE_SEM_METAL_DATA", None)
    env["FULLSEYE_FIGURES"] = "off"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    run = subprocess.run([sys.executable, "examples/poc_real_sem_metal_layer.py"],
                         cwd=Path(__file__).resolve().parents[1], env=env,
                         text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert "6.4 GB を取得しない" in run.stdout
    assert "RECORDED" in run.stdout
