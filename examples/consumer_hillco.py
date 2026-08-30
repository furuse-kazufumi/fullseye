"""Consumer example: hillco / evis (MS-Human-700 walking, body-language) using Fullseye.

Honest use: hillco evolves a musculoskeletal humanoid gait; the physics sim owns
the ground truth. Fullseye is used here ONLY as an *independent* perception-side
double-check on top of the sim -- it never drives the controller. Three checks a
hillco run performs:

  1. Gait-stability double-check -- from the 4 foot-contact points and the COM
     trajectory, recompute the support polygon and the static stability margin
     independently of the sim's own reward, and confirm the margin sign flips
     exactly when the COM leaves the support polygon (i.e. the walker tips over).
  2. Terrain foot-placement for the "hill climbing" track -- from a heightmap,
     find the slope, the step edges, and safe foothold candidates so the planner
     avoids planting a foot on the lip of a step.
  3. COM-from-silhouette -- a cheap posture read of the CoM from a binary
     silhouette mask (e.g. a camera view of the walker), for cross-checking.

Self-contained: all data is synthetic, no external files.
Run:  cd <your-project>/imgevolve && py -3.11 examples/consumer_hillco.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def gait_stability_doublecheck():
    """4-foot square stance + a COM that walks off the edge; margin must flip sign."""
    contacts = np.array([[0.2, 0.2], [-0.2, 0.2], [-0.2, -0.2], [0.2, -0.2]], float)
    poly = fs.locomotion.support_polygon(contacts)
    # COM trajectory: from centre outward past the +x edge (x = 0.2).
    xs = np.linspace(0.0, 0.6, 13)
    margins = np.array([fs.locomotion.com_support_margin(np.array([x, 0.0]), contacts) for x in xs])
    # foot heights over a trot-like cycle -> gait phase / duty factor.
    t = np.linspace(0, 2 * np.pi, 12)
    foot_heights = np.stack([np.maximum(0, np.sin(t)),          # FL
                             np.maximum(0, np.sin(t + np.pi)),  # FR
                             np.maximum(0, np.sin(t + np.pi)),  # HL
                             np.maximum(0, np.sin(t))], axis=1) # HR
    gp = fs.locomotion.gait_phase(foot_heights, stance_frac=0.25)
    assert margins[0] > 0, "COM at centre must be inside the support polygon"
    assert margins[-1] < 0, "COM past the edge must be outside (negative margin)"
    assert np.any(margins[:-1] * margins[1:] < 0), "margin sign must flip when COM leaves polygon"
    assert 0.0 <= float(np.mean(gp["duty_factor"])) <= 1.0
    return poly, xs, margins, gp


def terrain_foot_placement():
    """Heightmap with a raised step; pick footholds that avoid the step edge."""
    cell = 0.05
    grid = np.zeros((40, 40), float)
    grid[:, 24:] = 0.30  # upper terrace of the hill: a 0.30 m step-up
    slope = fs.terrain.slope_map(grid, cell=cell, degrees=True)
    edge_mask, rise = fs.terrain.step_edges(grid, cell=cell, min_rise=0.05)
    cands = fs.terrain.foothold_candidates(grid, cell=cell, min_score=0.5, max_n=30)
    edge_cols = set(np.unique(np.where(edge_mask)[1]).tolist())
    on_edge = [c["cell"] for c in cands if c["cell"][1] in edge_cols]
    assert float(np.max(slope)) > 30.0, "step boundary must register a steep slope"
    assert int(edge_mask.sum()) > 0, "step_edges must flag the rise"
    assert len(cands) > 0, "must propose at least one foothold"
    assert not on_edge, "chosen footholds must avoid the step-edge columns"
    return slope, edge_mask, edge_cols, cands


def com_from_silhouette():
    """Posture read: centroid of a synthetic walker silhouette."""
    mask = np.zeros((60, 40), bool)
    mask[10:50, 12:28] = True  # torso block centred at (row 29.5, col 19.5)
    com = fs.locomotion.com_from_silhouette(mask)
    assert abs(com[0] - 29.5) < 1.0 and abs(com[1] - 19.5) < 1.0
    return com


if __name__ == "__main__":
    poly, xs, margins, gp = gait_stability_doublecheck()
    slope, edge_mask, edge_cols, cands = terrain_foot_placement()
    com = com_from_silhouette()

    print("=== hillco / evis consumer double-check via Fullseye ===")
    print("[1] gait stability")
    print(f"    support polygon: area={poly['area']:.3f} m^2, {len(poly['vertices'])} vertices")
    print(f"    stability margin along COM walk-out (m): {np.round(margins, 3).tolist()}")
    flip = int(np.argmax(margins[:-1] * margins[1:] < 0))
    print(f"    margin flips sign between COM x={xs[flip]:.3f} and x={xs[flip + 1]:.3f} m (tip-over)")
    print(f"    mean duty factor={float(np.mean(gp['duty_factor'])):.2f}, double_support={gp['double_support']:.2f}")
    print("[2] terrain foot placement (hill-climb track)")
    print(f"    max slope={float(np.max(slope)):.1f} deg, step-edge cells={int(edge_mask.sum())} at cols {sorted(edge_cols)}")
    best = cands[0]
    print(f"    {len(cands)} safe footholds; best cell={best['cell']} score={best['score']:.2f}")
    print("[3] COM from silhouette")
    print(f"    silhouette CoM (row,col)=({com[0]:.1f}, {com[1]:.1f})")
    print("all smoke checks passed")
