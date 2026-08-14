"""Consumer example: **onocollo** (CPU world-models / gaitlab locomotion, physics-render videos).

Two *honest* Fullseye uses onocollo actually needs (see docs/CONSUMER_APPLICATIONS.md):

  1. STATIC-STABILITY CHECK from a MuJoCo-style state -- feed foot contact points and
     the COM ground-projection into locomotion.support_polygon / com_support_margin
     (+ contact_points to pick the feet touching the floor, gait_phase to read the
     stance/swing pattern). Positive margin = statically stable; negative = tipping.

  2. PHYSICS-VIDEO MOTION VERIFICATION -- from two rendered frames of an approaching
     scene, flow.optical_flow_lk gives the flow field, then sceneflow.looming /
     time_to_contact / focus_of_expansion quantify the approach so a rendered clip's
     "the camera is closing on the object" claim is checked against the pixels.

Self-contained: synthetic-but-exact data, no external files.
Run:  cd C:/dev/projects/imgevolve && py -3.11 examples/consumer_onocollo.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def stability_from_state(com_xy):
    """MuJoCo-style state -> static-stability margin for a quadruped standing square."""
    # Body cloud: 4 feet on the floor (z~0) + a torso point above it.
    cloud = np.array([[0.20, 0.15, 0.001], [0.20, -0.15, 0.0],
                      [-0.20, 0.15, 0.0], [-0.20, -0.15, 0.002],
                      [0.0, 0.0, 0.30]])
    ground = np.array([0.0, 0.0, 1.0, 0.0])                 # z = 0 plane [a,b,c,d]
    contacts, mask = fs.locomotion.contact_points(cloud, ground, tol=0.02)
    poly = fs.locomotion.support_polygon(contacts)
    margin = fs.locomotion.com_support_margin(np.asarray(com_xy, float), contacts)
    return int(mask.sum()), poly["area"], margin


def gait_readout():
    """Synthetic (T, F) foot heights for a trot -> stance/swing + duty factor."""
    t = np.linspace(0, 2 * np.pi, 24)
    diag_a = np.clip(0.06 * np.sin(t), 0, None)              # feet 0,3 lift together
    diag_b = np.clip(0.06 * np.sin(t + np.pi), 0, None)      # feet 1,2 antiphase
    foot_heights = np.stack([diag_a, diag_b, diag_b, diag_a], axis=1)  # (24, 4)
    return fs.locomotion.gait_phase(foot_heights, stance_frac=0.25)


def approaching_clip(h=96, w=120, scale=1.18, seed=3):
    """Two physics-render frames where the scene magnifies about center = camera approach."""
    rng = np.random.default_rng(seed)
    prev = np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.4), 0, 1)
    yy, xx = np.mgrid[0:h, 0:w]
    for cy, cx in [(30, 40), (60, 90), (45, 60), (70, 30)]:   # texture for LK gradients
        prev = np.clip(prev + 0.7 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 7.0 ** 2)), 0, 1)
    c = ((h - 1) / 2, (w - 1) / 2)
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    nxt = ndimage.map_coordinates(prev, [c[0] + (ys - c[0]) / scale, c[1] + (xs - c[1]) / scale],
                                  order=1, mode="nearest")
    return prev, nxt, c


def verify_approach(prev, nxt):
    u, v = fs.flow.optical_flow_lk(prev, nxt, window=15, levels=3, iters=5)
    loom = fs.sceneflow.looming(u, v)
    foe = fs.sceneflow.focus_of_expansion(u, v)
    tau = fs.sceneflow.time_to_contact(u, v)
    return loom, foe, tau


def main():
    print("=== onocollo x Fullseye ===")

    print("\n[1] Static-stability check from MuJoCo-style state (locomotion)")
    n_stable, area, m_stable = stability_from_state(com_xy=(0.0, 0.0))
    _, _, m_tip = stability_from_state(com_xy=(0.35, 0.0))     # COM shoved past the feet
    print(f"  feet touching floor = {n_stable}   support area = {area:.4f} m^2")
    print(f"  COM centred  -> margin = {m_stable:+.4f} m  ({'stable' if m_stable > 0 else 'TIPPING'})")
    print(f"  COM shoved   -> margin = {m_tip:+.4f} m  ({'stable' if m_tip > 0 else 'TIPPING'})")
    gait = gait_readout()
    print(f"  gait: duty_factor = {np.round(gait['duty_factor'], 2)}  double_support = {gait['double_support']:.2f}")

    print("\n[2] Physics-video motion verification (flow -> sceneflow)")
    prev, nxt, center = approaching_clip()
    loom, foe, tau = verify_approach(prev, nxt)
    finite = np.isfinite(tau)
    print(f"  mean_divergence = {loom['mean_divergence']:+.3f}   expanding = {loom['expanding']}")
    print(f"  global time-to-contact = {loom['ttc']:.1f} frames")
    print(f"  focus of expansion = ({foe[0]:.1f}, {foe[1]:.1f})  vs image center ({center[1]:.1f}, {center[0]:.1f})")
    print(f"  per-pixel TTC finite (approaching) on {100 * finite.mean():.0f}% of frame, median {np.median(tau[finite]):.1f} frames")

    # ---- smoke checks: prove each capability actually works ----
    assert m_stable > 0.0, "centred COM must be statically stable"
    assert m_tip < 0.0, "COM outside the feet must read as tipping"
    assert n_stable == 4 and 0.10 < area < 0.14, "expected 4 floor contacts and a ~0.12 m^2 base"
    assert np.all((gait["duty_factor"] > 0) & (gait["duty_factor"] < 1)), "duty factors in (0,1)"
    assert loom["expanding"] and loom["mean_divergence"] > 0, "approaching scene must read as looming"
    assert np.isfinite(loom["ttc"]) and loom["ttc"] > 0, "approach must give a finite positive TTC"
    assert abs(foe[0] - center[1]) < 6 and abs(foe[1] - center[0]) < 6, "FoE must sit near the zoom center"
    print("\nAll smoke checks passed.")


if __name__ == "__main__":
    main()
