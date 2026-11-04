# -*- coding: utf-8 -*-
"""BGA の半田ボールを型から型へ渡して戻す PoC の固有契約(収蔵 2026.299)。

``tests/test_poc_scripts_run.py`` が全 PoC を走らせて PASS を見る。ここでは
門そのものが**壊れた入力で落ちる**ことを別に確かめる(一致の門は空を通すので)。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from examples import poc_bga_ball_type_roundtrip as P

import fullseye as fs
import opsreprconv

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "poc_bga_ball_type_roundtrip.py"
R = opsreprconv.call


def test_poc_runs_without_figures_and_reports_all_seven_chapters():
    env = dict(os.environ, PYTHONUTF8="1", FULLSEYE_FIGURES="off")
    env.pop("FULLSEYE_FIGURE_DIR", None)
    run = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), env=env,
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert run.returncode == 0, run.stdout[-3000:] + "\n" + run.stderr[-1500:]
    assert all(("\n[%d]" % n) in run.stdout for n in range(1, 8))
    assert "[NG]" not in run.stdout
    assert run.stdout.count("[OK]") == 37, run.stdout.count("[OK]")   # 検査が黙って減らないこと
    assert "\nPASS" in run.stdout


def test_poc_declares_its_accession_number():
    assert P.ACCESSION == "2026.299"
    assert "2026.299" in SCRIPT.read_text(encoding="utf-8")


def test_board_truth_has_one_missing_ball_and_real_heights():
    b = P.board()
    assert len(b["rowcol"]) == 71
    assert np.bincount(b["package"]).tolist() == [35, 36]
    hm = b["height"]
    assert np.all(np.isfinite(hm)) and float(np.ptp(hm)) > 3.0
    assert abs(float(hm.max()) - P.BALL_R) < 0.05


def _two_balls(gap):
    pts = np.array([[0.0, 20.0, 20.0], [0.0, 20.0, 20.0 + gap]])
    g = R("points_to_gaussians", pts, k=1, scale=1.0)
    g = dict(g, sigma=np.full(2, 1.5))
    vol = R("gaussians_to_voxel", g, shape=(24, 40, 60), origin=(-12.0, 0.0, 0.0), truncate=6.0)
    amp = g["w"] / ((2.0 * np.pi) ** 1.5 * g["sigma"] ** 3)
    verts, faces = fs.ledger.voxel_to_mesh(vol, iso=0.25 * float(amp.min()))
    return P.mesh_euler(faces, len(verts))


def test_the_euler_gate_counts_spheres_and_sees_a_merge():
    """離れた 2 球は χ = 4、くっついた 2 球(半田ブリッジ)は χ = 2 —— 門が個数を見ている。"""
    assert _two_balls(12.0) == 4
    assert _two_balls(2.0) == 2


def test_the_xyz_pointmap_fed_as_zyx_is_silently_wrong():
    """``pointmap_to_points`` は (x, y, z)。(z, y, x) の受け手にそのまま渡しても例外は出ない。"""
    hm = P.board()["height"]
    pts = R("pointmap_to_points", fs.ledger.depth_to_organized_points(hm))
    naive = R("keypoints_to_image2d", R("points_zyx_to_keypoints_uv", pts), shape=hm.shape)
    right = R("keypoints_to_image2d", R("points_zyx_to_keypoints_uv", pts[:, ::-1]), shape=hm.shape)
    assert np.array_equal(right, np.ones(hm.shape))
    assert float(naive.sum()) == hm.size and not np.array_equal(naive, right)
    assert int(np.count_nonzero(naive.sum(axis=0))) <= 4


def test_the_shift_gate_rejects_a_wrong_shift():
    """相関のピークは本当のずれにだけ立つ(別のずれを入れると位置が変わる)。"""
    pts = np.array([[0.0, 20.0, 20.0], [1.0, 30.0, 45.0], [2.0, 12.0, 33.0]])
    g = R("points_to_gaussians", pts, k=2, scale=0.3)
    a = R("gaussians_to_voxel", g, shape=(24, 48, 64), origin=(-12.0, 0.0, 0.0), truncate=6.0)
    for shift in ((1, 2, 3), (0, -4, 6)):
        b = R("gaussians_to_voxel", dict(g, mu=pts + np.array(shift, float)), shape=(24, 48, 64),
              origin=(-12.0, 0.0, 0.0), truncate=6.0)
        pos = R("score_to_position", R("correlation_score", a, b))
        assert pos == tuple(float(v) for v in np.mod(shift, (24, 48, 64)))


@pytest.mark.parametrize("name", ["keypoints_from_image2d", "points_to_gaussians",
                                  "knn_graph_to_conn_graph", "curvature_to_shape_index"])
def test_the_ops_the_poc_leans_on_are_in_the_reprconv_ledger(name):
    assert name in opsreprconv.OPSREPRCONV
    assert opsreprconv.get(name) is not None
