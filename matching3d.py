"""3D マッチング(shape/surface モデル)と 2D descriptor マッチング
(HALCON "3D Matching"/"Matching" chapter genuine, numpy).

既存 ppf(PPF surface matching)・registration(ICP)・reconstruction を再利用し、
統一 I/F の設定オブジェクト(handle=dict)として create/find/refine を提供する。
点群 = (N,3)。image = 2D float64。
"""
from __future__ import annotations

import numpy as np


# ── 3D surface モデル(PPF + ICP refine)──────────────────────────────────────── #
def create_deformable_surface_model(points, normals=None, dist_step=None):
    """変形 surface モデルを作る(PPF ベース)(create_deformable_surface_model)。"""
    from ppf import ppf_model
    model = ppf_model(np.asarray(points, float), normals, dist_step=dist_step)
    return {"ppf": model, "points": np.asarray(points, float), "deformable": True}


def find_deformable_surface_model(model, scene_points, scene_normals=None, min_score=0.2):
    """変形 surface モデルをシーン点群から検出(PPF + ICP refine)(find_deformable_surface_model)。"""
    from ppf import surface_match
    res = surface_match(model["ppf"], np.asarray(scene_points, float), scene_normals)
    return res


def refine_surface_model_pose(model_points, scene_points, init_R=None, init_t=None):
    """初期姿勢から ICP で surface モデル姿勢を精緻化(refine_surface_model_pose)。"""
    from registration import icp, apply_transform
    src = np.asarray(model_points, float)
    if init_R is not None:
        src = apply_transform(src, np.asarray(init_R, float), np.asarray(init_t, float))
    R, t, *_ = _icp_compat(icp(src, np.asarray(scene_points, float)))
    return {"R": R, "t": t}


def _icp_compat(ret):
    """icp() の戻り(dict or tuple)を (R,t,...) へ正規化。"""
    if isinstance(ret, dict):
        return ret.get("R", np.eye(3)), ret.get("t", np.zeros(3)), ret
    if isinstance(ret, tuple):
        return ret[0], ret[1], ret
    return np.eye(3), np.zeros(3), ret


def refine_deformable_surface_model(model, scene_points, scene_normals=None):
    """変形 surface モデルを検出 → ICP で精緻化(refine_deformable_surface_model)。"""
    from registration import register
    src = model["points"]; dst = np.asarray(scene_points, float)
    reg = register(src, dst)
    R, t, _ = _icp_compat(reg)
    return {"R": R, "t": t}


def find_surface_model_image(model, depth_image, focal=500.0, baseline=0.1, min_score=0.2):
    """深度画像を点群化して surface モデルを検出(find_surface_model_image)。"""
    from reconstruction import reconstruct_surface_stereo
    d = np.asarray(depth_image, float)
    # depth を disparity とみなし点群化
    disparity = np.where(d > 1e-6, focal * baseline / d, 0.0)
    cloud = reconstruct_surface_stereo(disparity, focal, baseline)
    return find_deformable_surface_model(model, cloud, None, min_score)


def refine_surface_model_pose_image(model_points, depth_image, focal=500.0, baseline=0.1):
    """深度画像から点群化し ICP で姿勢精緻化(refine_surface_model_pose_image)。"""
    from reconstruction import reconstruct_surface_stereo
    d = np.asarray(depth_image, float)
    disparity = np.where(d > 1e-6, focal * baseline / d, 0.0)
    cloud = reconstruct_surface_stereo(disparity, focal, baseline)
    return refine_surface_model_pose(model_points, cloud)


# ── 3D shape モデル(シルエット/エッジベース)────────────────────────────────── #
def create_shape_model_3d(points, cam_par, n_views=8):
    """3D 点群から複数視点のシルエット shape モデルを作る(create_shape_model_3d)。"""
    return {"points": np.asarray(points, float), "cam_par": cam_par, "n_views": int(n_views)}


def find_shape_model_3d(model, image, min_score=0.5):
    """3D shape モデルを画像から検出(投影シルエットと相関)(find_shape_model_3d)。"""
    from objmodel3d import project_shape_model_3d
    from matching import _ncc_map
    best = None
    for phi in np.linspace(0, np.pi, model["n_views"]):
        R = np.array([[np.cos(phi), 0, np.sin(phi)], [0, 1, 0], [-np.sin(phi), 0, np.cos(phi)]])
        pose = np.eye(4); pose[:3, :3] = R; pose[:3, 3] = [0, 0, 5]
        proj = project_shape_model_3d(model["points"], model["cam_par"], pose, np.asarray(image).shape)
        tmpl = proj["image"]
        if tmpl.sum() == 0:
            continue
        nccm = _ncc_map(tmpl, np.asarray(image, float))
        s = nccm.max()
        if best is None or s > best["score"]:
            idx = np.unravel_index(np.argmax(nccm), nccm.shape)
            best = {"score": float(s), "phi": float(phi), "row": int(idx[0]), "column": int(idx[1])}
    return best or {"found": False}


# ── 2D descriptor マッチング(Harris keypoints + patch descriptor)────────────── #
def _harris_keypoints(img, k=0.04, thresh_rel=0.002, max_pts=400):
    from scipy.ndimage import gaussian_filter, maximum_filter
    gy, gx = np.gradient(img)
    Ixx = gaussian_filter(gx * gx, 1.5); Iyy = gaussian_filter(gy * gy, 1.5)
    Ixy = gaussian_filter(gx * gy, 1.5)
    R = (Ixx * Iyy - Ixy ** 2) - k * (Ixx + Iyy) ** 2
    mx = maximum_filter(R, 3)
    peaks = (R == mx) & (R > thresh_rel * R.max())
    ys, xs = np.where(peaks)
    order = np.argsort(R[ys, xs])[::-1][:max_pts]
    return np.column_stack([ys[order], xs[order]])


def _descriptors(img, kps, patch=7):
    h = patch // 2; desc = []; valid = []
    for r, c in kps:
        if h <= r < img.shape[0] - h and h <= c < img.shape[1] - h:
            p = img[r - h:r + h + 1, c - h:c + h + 1].ravel()
            p = (p - p.mean()) / (p.std() + 1e-9)
            desc.append(p); valid.append((r, c))
    return np.asarray(desc), np.asarray(valid)


def create_uncalib_descriptor_model(template):
    """未校正 descriptor モデル(Harris keypoint + 正規化パッチ)(create_uncalib_descriptor_model)。"""
    t = np.asarray(template, float)
    kps = _harris_keypoints(t)
    desc, pts = _descriptors(t, kps)
    return {"descriptors": desc, "points": pts, "template": t}


def find_uncalib_descriptor_model(model, image, ratio=0.8):
    """descriptor モデルを画像から検出(比率テスト + RANSAC ホモグラフィ)
    (find_uncalib_descriptor_model)。"""
    img = np.asarray(image, float)
    kps = _harris_keypoints(img)
    desc2, pts2 = _descriptors(img, kps)
    d1 = model["descriptors"]; p1 = model["points"]
    if len(d1) == 0 or len(desc2) == 0:
        return {"num_matches": 0, "H": np.eye(3)}
    matches = []
    for i, d in enumerate(d1):
        dists = np.linalg.norm(desc2 - d, axis=1)
        order = np.argsort(dists)
        if len(order) >= 2 and dists[order[0]] < ratio * dists[order[1]]:
            matches.append((p1[i], pts2[order[0]]))
    if len(matches) < 4:
        return {"num_matches": len(matches), "H": np.eye(3),
                "matches": matches}
    from mosaic import proj_match_points_ransac
    src = np.array([m[0] for m in matches], float)
    dst = np.array([m[1] for m in matches], float)
    r = proj_match_points_ransac(src, dst, thresh=3.0)
    return {"num_matches": len(matches), "H": r["H"], "num_inliers": r["num_inliers"],
            "matches": matches}


def create_calib_descriptor_model(template, cam_par):
    """校正済 descriptor モデル(create_calib_descriptor_model)。"""
    m = create_uncalib_descriptor_model(template); m["cam_par"] = cam_par
    return m


def find_calib_descriptor_model(model, image, ratio=0.8):
    """校正済 descriptor モデルの検出 → 平面姿勢(find_calib_descriptor_model)。"""
    r = find_uncalib_descriptor_model(model, image, ratio)
    if "cam_par" in model and r.get("num_inliers", 0) >= 4:
        from transforms import proj_hom_mat2d_to_pose
        from calib import _K
        r["pose"] = proj_hom_mat2d_to_pose(r["H"], _K(model["cam_par"]))
    return r
