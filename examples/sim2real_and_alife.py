"""Physical-AI / evolution op families — sim2real augmentation, artificial life, tactile.

Three registry op clusters added for near-future Physical-AI and evolutionary
robotics, all classical numpy/scipy (no learned model, no HALCON equivalent -> each
carries ``halcon=""``):

  aug_*    sensor / sim-to-real corruption models — degrade a clean render the way a
           real camera would (photon shot noise, read noise, fixed-pattern noise,
           motion/rolling-shutter, vignetting, JPEG blocks, lens distortion, cutout).
           Use them to train an evolved / RL policy that must survive the real sensor.
  alife_*  artificial-life / cellular-automata generators — treat the image as the
           initial condition of a dynamical system (Conway-family CA, cyclic CA,
           Gray-Scott / Gierer-Meinhardt reaction-diffusion, Greenberg-Hastings
           excitable medium, diffusion-limited aggregation). Open-ended pattern
           substrate for evolution / procedural texture.
  tac_*    tactile / contact-from-shading — recover contact geometry from a single
           GelSight-style tactile image (contact mask, height-from-shading, surface
           normal, pressure, shear proxy). Next-decade dexterous manipulation.

Plus the self-expanding registry: ``macro_denoise`` is a "DNA" op — a champion
pipeline the evolutionary core discovered (three tuned bilateral passes), frozen
into one reusable operator (see backends_macro.py / data/macro_champions.json).

Run:  py -3.11 examples/sim2real_and_alife.py
It is a smoke test: it applies a representative op from each family and prints a
one-line, honest summary (shape + a cheap statistic), never asserting a pretty
number. Exit code 0 means every op ran and returned a finite, shaped result.
"""
from __future__ import annotations

import os
import sys

import numpy as np

# imgevolve is a flat project: allow "import fullseye" when run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye  # noqa: E402


def _scene(n: int = 96) -> np.ndarray:
    """A small synthetic 'clean render': a few bright shapes on a mid background."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.full((n, n), 0.30)
    img[(yy - 0.35 * n) ** 2 + (xx - 0.4 * n) ** 2 < (0.16 * n) ** 2] = 0.9   # disk
    img[int(0.55 * n):int(0.8 * n), int(0.2 * n):int(0.7 * n)] = 0.65          # bar
    return np.clip(img, 0.0, 1.0)


def _line(name: str, out) -> None:
    arr = np.asarray(out, np.float64)
    finite = bool(np.isfinite(arr).all())
    kind = "region" if set(np.unique(arr)).issubset({0.0, 1.0}) else "image"
    print(f"  {name:24s} -> {str(arr.shape):12s} {kind:6s} "
          f"mean={arr.mean():.3f} finite={finite}")


def main() -> int:
    scene = _scene()
    tactile = np.clip(scene + 0.15 * np.sin(np.linspace(0, 12, scene.size)).reshape(scene.shape), 0, 1)

    print("== sim2real sensor corruption (aug_) — one clean render, three sensors ==")
    for name, a, b in [("aug_shot_noise", 0.2, 0.0), ("aug_fixed_pattern", 0.6, 0.3),
                       ("aug_vignette", 0.7, 0.4), ("aug_rolling_shutter", 0.5, 0.7),
                       ("aug_jpeg_blocks", 0.8, 0.0), ("aug_barrel", 0.5, 0.2)]:
        _line(name, fullseye.apply(scene, name, a, b))

    print("== artificial life / cellular automata (alife_) — image as initial state ==")
    for name, a, b in [("alife_life_step", 0.0, 0.5), ("alife_cyclic_ca", 0.4, 0.6),
                       ("alife_reaction_bz", 0.0, 0.5), ("alife_dla", 0.6, 0.4),
                       ("alife_turing", 0.5, 0.8)]:
        _line(name, fullseye.apply(scene, name, a, b))

    print("== tactile / contact-from-shading (tac_) — one GelSight-style frame ==")
    for name, a, b in [("tac_contact_mask", 0.5, 0.3), ("tac_height_from_shading", 0.5, 0.4),
                       ("tac_surface_normal", 0.5, 0.3), ("tac_pressure_proxy", 0.5, 0.4),
                       ("tac_shear_field", 0.5, 0.5)]:
        _line(name, fullseye.apply(tactile, name, a, b))

    print("== self-expanding registry: the DNA op the evolutionary core discovered ==")
    _line("macro_denoise", fullseye.apply(
        np.clip(scene + 0.2 * np.sin(np.linspace(0, 40, scene.size)).reshape(scene.shape), 0, 1),
        "macro_denoise"))
    print("\nAll families ran. Discover every op with fullseye.list_ops(search='aug_'|'alife_'|'tac_').")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
