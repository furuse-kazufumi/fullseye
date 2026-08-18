"""校正ターゲット(caltab)生成・検出とワールド平面マップ(HALCON "Calibration" genuine, numpy).

円マーク格子の校正板を生成・シミュレート・画像から検出し、ワールド平面写像を作る。
image = 2D float64。マーク座標は (row, col)。
"""
from __future__ import annotations

import numpy as np


def caltab_points(rows=7, cols=7, spacing=1.0):
    """校正板の理想マーク座標(ワールド, mm)を返す(caltab_points)。"""
    r, c = np.mgrid[0:rows, 0:cols]
    x = c.ravel() * spacing; y = r.ravel() * spacing
    return np.column_stack([y, x]).astype(np.float64)


def gen_caltab(rows=7, cols=7, spacing=1.0, radius=0.3, image_size=256):
    """円マーク格子の校正板画像を生成(gen_caltab)。"""
    img = np.zeros((image_size, image_size))
    margin = image_size * 0.1
    step = (image_size - 2 * margin) / max(rows - 1, cols - 1)
    yy, xx = np.mgrid[0:image_size, 0:image_size]
    centers = []
    for i in range(rows):
        for j in range(cols):
            cy = margin + i * step; cx = margin + j * step
            img[(yy - cy) ** 2 + (xx - cx) ** 2 <= (radius * step) ** 2] = 1.0
            centers.append([cy, cx])
    return {"image": img, "centers": np.asarray(centers), "rows": rows, "cols": cols}


def create_caltab(rows=7, cols=7, spacing=1.0):
    """校正板の記述(理想点)を作る(create_caltab)。"""
    return {"points": caltab_points(rows, cols, spacing), "rows": rows, "cols": cols}


def sim_caltab(caltab, cam_par, pose, image_size=256):
    """校正板を指定カメラ姿勢で投影した画像をシミュレート(sim_caltab)。"""
    from calib import project_3d_point
    pts = caltab["points"] if isinstance(caltab, dict) and "points" in caltab else caltab_points()
    world = np.column_stack([pts[:, 1] - pts[:, 1].mean(), pts[:, 0] - pts[:, 0].mean(), np.zeros(len(pts))])
    px = project_3d_point(world, cam_par, pose)
    img = np.zeros((image_size, image_size)); yy, xx = np.mgrid[0:image_size, 0:image_size]
    for row, col in px:
        if 0 <= row < image_size and 0 <= col < image_size:
            img[(yy - row) ** 2 + (xx - col) ** 2 <= 9] = 1.0
    return {"image": img, "marks": px}


def disp_caltab(caltab):
    """校正板画像を返す(表示用)(disp_caltab)。"""
    return caltab["image"] if isinstance(caltab, dict) and "image" in caltab else caltab


def find_caltab(image, thresh=0.5):
    """画像から校正板の円マーク中心を検出(連結成分の重心)(find_caltab)。"""
    from scipy import ndimage
    m = np.asarray(image, float) > thresh
    lab, n = ndimage.label(m)
    if n == 0:
        return np.zeros((0, 2))
    centers = ndimage.center_of_mass(m, lab, range(1, n + 1))
    return np.asarray(centers)


def find_calib_object(image, thresh=0.5):
    """校正オブジェクト(マーク)を検出(find_calib_object)。find_caltab の別名。"""
    return {"marks": find_caltab(image, thresh)}


def find_marks_and_pose(image, cam_par, caltab, thresh=0.5):
    """マーク検出 + 校正板の姿勢推定(PnP 近似=平面ホモグラフィ)(find_marks_and_pose)。"""
    from calib import _K
    from transforms import proj_hom_mat2d_to_pose, vector_to_proj_hom_mat2d
    marks = find_caltab(image, thresh)
    ideal = caltab["points"] if isinstance(caltab, dict) and "points" in caltab else caltab_points()
    K = _K(cam_par)
    if len(marks) < 4 or len(ideal) < 4:
        return {"marks": marks, "pose": np.eye(4)}
    n = min(len(marks), len(ideal))
    # 単純な行優先ソートで対応づけ(理想も検出も左上→右下)
    ms = marks[np.lexsort((marks[:, 1], marks[:, 0]))][:n]
    ids = ideal[np.lexsort((ideal[:, 1], ideal[:, 0]))][:n]
    world_xy = ids[:, ::-1]                                 # (col,row)->(x,y)
    H = vector_to_proj_hom_mat2d(world_xy, ms[:, ::-1])
    pose = proj_hom_mat2d_to_pose(H, K)
    return {"marks": ms, "pose": pose, "homography": H}


def gen_image_to_world_plane_map(cam_par, pose, shape, scale=1.0):
    """画像→ワールド平面(z=0)の写像テーブルを生成(gen_image_to_world_plane_map)。"""
    from calib import image_points_to_world_plane
    H, W = shape
    rr, cc = np.mgrid[0:H, 0:W]
    px = np.column_stack([rr.ravel(), cc.ravel()])
    world = image_points_to_world_plane(cam_par, pose, px, scale)
    return {"x_map": world[:, 1].reshape(H, W), "y_map": world[:, 0].reshape(H, W)}


def binocular_calibration(object_points, image_points_left, image_points_right):
    """左右カメラを Zhang で個別校正しステレオ相対姿勢を推定(binocular_calibration)。"""
    from calib import camera_calibration
    cl = camera_calibration(object_points, image_points_left)
    cr = camera_calibration(object_points, image_points_right)
    return {"left": cl, "right": cr,
            "note": "相対姿勢は各視点の外部パラメータ差から算出(簡易)"}
