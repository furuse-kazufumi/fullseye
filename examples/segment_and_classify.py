"""Segment objects in a scene, describe each, and identify them against a small
set of prototypes — the perception a robot needs to pick or sort items.

A template: build `prototypes` once from labelled reference shapes, then classify
whatever `segment_objects` finds in a new frame. Runs on synthetic data.

    py -3.11 examples/segment_and_classify.py [--save out_dir]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def _disk(img, cy, cx, r, val=1.0):
    y, x = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    img[(y - cy) ** 2 + (x - cx) ** 2 <= r * r] = val
    return img


def _square(img, cy, cx, s, val=1.0):
    img[cy - s:cy + s, cx - s:cx + s] = val
    return img


def build_prototypes():
    """Descriptors for a 'disk' and a 'square' reference shape."""
    disk = _disk(np.zeros((80, 80)), 40, 40, 15)
    square = _square(np.zeros((80, 80)), 40, 40, 13)
    return {
        "disk": fs.object_descriptor(fs.segment_objects(disk, threshold="none")[0]),
        "square": fs.object_descriptor(fs.segment_objects(square, threshold="none")[0]),
    }


def run(save_dir=None):
    # a scene with two disks and one square of varied sizes/positions
    scene = np.zeros((120, 160))
    _disk(scene, 30, 40, 10)
    _disk(scene, 80, 110, 16)
    _square(scene, 60, 70, 12)

    prototypes = build_prototypes()
    objs = fs.segment_objects(scene, threshold="otsu", min_area=20)

    labelled = []
    for o in objs:
        name, dist = fs.nearest_prototype(fs.object_descriptor(o), prototypes)
        labelled.append((name, o["area"], o["centroid"], dist))
        print(f"[detect] {name:6s}  area={o['area']:.0f}  centroid=({o['centroid'][0]:.0f},"
              f"{o['centroid'][1]:.0f})  dist={dist:.3f}")

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save(os.path.join(save_dir, "objects.png"), fs.draw_objects(scene, objs))
        print(f"[detect] wrote objects.png -> {save_dir}")
    return labelled


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", default=None)
    a = ap.parse_args()
    run(save_dir=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
