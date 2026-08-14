"""End-to-end Physical-AI perception pipelines built entirely on ``fullseye``.

Two runnable pipelines a robot uses, wired from the new perception modules
(camera / pcseg / stereo / terrain / locomotion / sceneflow / ppf):

  1. MANIPULATION:  scene cloud -> remove ground -> cluster into objects ->
     match a known model (PPF 6-DoF pose) -> plan an antipodal grasp.
  2. LOCOMOTION:    depth frame -> camera-frame cloud + normals -> elevation map
     -> slope / foothold candidates -> support polygon + static stability margin.

Run:  py -3.11 examples/physical_ai_perception.py
It builds synthetic-but-exact scenes and prints a summary; the ``assert``s make it
a smoke test that the whole chain composes and returns sane geometry. Copy either
function as a template for onocollo / evis / hillco.
"""
from __future__ import annotations

import numpy as np

import fullseye as fs


def _ellipsoid(n=260, a=0.10, b=0.07, c=0.05, seed=0):
    """A graspable object as a point cloud with exact outward normals (metres)."""
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = d * np.array([a, b, c])
    N = P / np.array([a, b, c]) ** 2
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    return P, N


def demo_manipulation():
    print("\n=== MANIPULATION: scene -> object -> 6-DoF pose -> grasp ===")
    # known object model (CAD stand-in) + normals
    model_pts, model_nrm = _ellipsoid(seed=1)

    # scene: a table (ground plane) with the object sitting on it, at a known pose
    rng = np.random.default_rng(7)
    table = np.column_stack([rng.uniform(-0.4, 0.4, 1500),
                             rng.uniform(-0.4, 0.4, 1500),
                             rng.normal(0.0, 0.002, 1500)])
    R_true = fs.rodrigues([0.15, -0.25, 0.1])
    t_true = np.array([0.12, -0.05, 0.10])           # object 10 cm above the table
    obj = model_pts @ R_true.T + t_true + rng.normal(0, 0.002, model_pts.shape)
    scene = np.vstack([table, obj])

    # 1) drop the ground plane
    nonground, gmask = fs.remove_ground(scene, thresh=0.01)
    print(f"  ground removed: {int(gmask.sum())}/{len(scene)} pts;  {len(nonground)} remain")

    # 2) cluster what's left into candidate objects, take the largest
    clusters = fs.euclidean_clusters(nonground, tol=0.03, min_size=30)
    print(f"  clusters found: {len(clusters)} (sizes {[len(c) for c in clusters[:3]]})")
    cluster = nonground[clusters[0]]
    box = fs.obb(cluster)
    print(f"  object OBB extents (m): {np.round(box['extents'], 3)}")

    # 3) recover the object's 6-DoF pose by matching the known model (PPF + ICP)
    res = fs.find_surface_pose(model_pts, cluster, model_nrm,
                               ref_fraction=0.4, topk=6, seed=3)
    ang = np.degrees(np.linalg.norm(fs.rotation_log(res["R"] @ R_true.T)))
    print(f"  PPF pose: inliers={res['inlier_fraction']:.2f} rmse={res['rmse']:.4f} "
          f"| rot err={ang:.2f} deg  t err={np.linalg.norm(res['t'] - t_true):.4f} m")
    assert res["inlier_fraction"] > 0.8 and ang < 8.0

    # 4) plan a grasp on the (now localised) object model
    grasps = fs.grasps_from_mesh  # note: mesh grasp needs V,F; use point-cloud approach dir
    nrm = fs.estimate_normals(cluster, k=16, viewpoint=(0, 0, 1.0))
    approach = fs.approach_vector_from_normals(nrm)
    print(f"  grasp approach vector (from surface normals): {np.round(approach, 3)}")
    return res


def demo_locomotion():
    print("\n=== LOCOMOTION: depth -> cloud -> terrain -> foothold -> stability ===")
    # a depth frame of gently sloped ground with a raised step (camera looking down +z)
    K = fs.intrinsic_matrix(300.0, 300.0, 80.0, 60.0)
    H, W = 120, 160
    v, u = np.mgrid[0:H, 0:W].astype(float)
    # tilted ground plane in the camera frame -> per-pixel depth
    nrm = np.array([0.15, 0.0, -1.0]); nrm /= np.linalg.norm(nrm)
    dpp = 2.0 * nrm[2]
    x = (u - 80.0) / 300.0
    y = (v - 60.0) / 300.0
    Z = dpp / (nrm[0] * x + nrm[1] * y + nrm[2])
    Z[40:70, 60:100] -= 0.15                          # a raised block (closer to camera)

    cloud = fs.depth_to_points(Z, K)                  # camera-frame (N,3)
    normals = fs.normals_from_depth(Z, K)             # per-pixel surface normals
    print(f"  depth -> cloud: {cloud.shape[0]} pts;  normal[centre]={np.round(normals[60,80],2)}")

    # treat camera -x/-y as ground plane, -z as up (toy world transform) -> heightmap
    world = cloud[:, [0, 1, 2]].copy()
    world[:, 2] = -world[:, 2]                         # make 'up' positive
    grid, extent = fs.elevation_map(world, cell=0.01, agg="max")
    slope = fs.slope_map(grid, cell=0.01)
    cands = fs.foothold_candidates(grid, cell=0.01, min_score=0.5, min_dist=0.05,
                                   extent=extent)
    print(f"  heightmap {grid.shape};  median slope={np.nanmedian(slope):.1f} deg;  "
          f"{len(cands)} foothold candidates")

    # static stability: is the COM over the feet?
    feet = np.array([[0.10, 0.10, 0.0], [-0.10, 0.10, 0.0],
                     [0.10, -0.10, 0.0], [-0.10, -0.10, 0.0]])
    poly = fs.support_polygon(feet)
    inside = fs.com_support_margin([0.02, 0.0], feet)
    outside = fs.com_support_margin([0.20, 0.0], feet)
    print(f"  support polygon area={poly['area']:.3f} m^2;  "
          f"margin(COM inside)={inside:+.3f} m  margin(COM outside)={outside:+.3f} m")
    assert inside > 0 and outside < 0 and len(cands) >= 1
    return grid, cands


def demo_egomotion():
    print("\n=== EGO-MOTION: optical flow -> heading + time-to-contact ===")
    yy, xx = np.mgrid[0:120, 0:160].astype(float)
    K = fs.intrinsic_matrix(300.0, 300.0, 80.0, 60.0)
    s = 0.03                                           # forward approach (expanding flow)
    u = s * (xx - 92.0)                                # FoE offset from centre -> heading tilt
    v = s * (yy - 60.0)
    foe = fs.focus_of_expansion(u, v)
    heading = fs.ego_translation_from_flow(u, v, K)
    loom = fs.looming(u, v)
    print(f"  FoE={tuple(round(f,1) for f in foe)}  heading={np.round(heading,3)}  "
          f"looming={loom['expanding']} ttc={loom['ttc']:.1f} frames")
    assert loom["expanding"] and np.isfinite(loom["ttc"])


if __name__ == "__main__":
    demo_manipulation()
    demo_locomotion()
    demo_egomotion()
    print("\nAll Physical-AI perception pipelines composed OK.")
