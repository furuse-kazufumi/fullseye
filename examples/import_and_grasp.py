"""Import an object -> make it simulation-ready -> find where to grasp it -> render it.

The evis / onocollo / hillco use case end to end, entirely through the `fullseye`
facade and entirely numpy-native: a mesh (imported from OBJ/STL/PLY/OFF, or built
here) becomes a watertight sim body with an *exact* inertia tensor (for MuJoCo), a
ranked set of antipodal parallel-jaw grasps, and a rendered depth / silhouette view
(what the robot's camera would see).

    py -3.11 examples/import_and_grasp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
import fullseye as fs  # noqa: E402


def make_box(sx, sy, sz):
    """A box mesh (8 verts, 12 tris). In practice this is ``fs.read_mesh('part.stl')``."""
    V = np.array([[0, 0, 0], [sx, 0, 0], [sx, sy, 0], [0, sy, 0],
                  [0, 0, sz], [sx, 0, sz], [sx, sy, sz], [0, sy, sz]], float)
    F = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1],
                  [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]], int)
    return V, F


def main():
    # 1. Import the object (here: a graspable 4x10x10 cm block). Real use: fs.read_mesh(path).
    V, F = make_box(0.04, 0.10, 0.10)
    print("object: %d verts, %d faces" % (len(V), len(F)))

    # 2. Make it simulation-ready: watertight check + EXACT inertia tensor (Mirtich 1996).
    assert fs.is_watertight(V, F), "mesh must be closed for a well-defined inertia"
    I = fs.inertia_tensor(V, F, density=700.0)       # ~ dense plastic (kg/m^3)
    print("sim body: mass=%.4f kg  com=%s  diag(I)=%s"
          % (I["mass"], np.round(I["com"], 3), np.round(np.diag(I["inertia"]), 8)))

    # 3. Find WHERE to grasp it: antipodal parallel-jaw, force-closure ranked.
    grasps = fs.grasps_from_mesh(V, F, n_surface=3000, mu=0.5, width_max=0.06, seed=0)
    assert grasps, "no force-closure grasp found"
    g = grasps[0]
    print("best grasp: width=%.4f m  quality=%.4f  approach=%s  axis=%s"
          % (g.width, g.quality, np.round(g.approach, 2), np.round(g.axis, 2)))

    # 4. Render the object as the robot's camera would see it (depth + silhouette).
    view = fs.render_mesh(V, F, width=192, height=192)
    fin = np.isfinite(view["depth"])
    cov = int((view["silhouette"] > 0.5).sum())
    print("render: silhouette %d px, depth in [%.3f, %.3f] m"
          % (cov, float(view["depth"][fin].min()), float(view["depth"][fin].max())))

    # smoke: the pipeline produced a sane, graspable, renderable sim body
    assert 0.03 < g.width < 0.05 and g.quality > 0 and cov > 0 and I["mass"] > 0
    print("OK: imported -> sim-ready -> grasp -> render")


if __name__ == "__main__":
    main()
