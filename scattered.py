"""散布データ補間 / 距離変換(HALCON "Tools" chapter genuine, numpy/scipy).

不規則点群のスカラー場を格子/任意点へ補間、XLD 輪郭への距離変換。
歩行知覚では疎な深度点から密な地形高さ場を作るのに使う。
"""
from __future__ import annotations

import numpy as np


def _materialize(points, values, method):
    if method == "linear":
        from scipy.interpolate import LinearNDInterpolator
        return LinearNDInterpolator(points, values)
    if method == "cubic":
        from scipy.interpolate import CloughTocher2DInterpolator
        return CloughTocher2DInterpolator(points, values)
    if method == "nearest":
        from scipy.spatial import cKDTree
        return cKDTree(points)
    raise ValueError(f"unknown interpolation method: {method!r}")


def create_scattered_data_interpolator(points, values, method="linear"):
    """不規則点 (N,2) と値 (N,) から補間器を作る(create_scattered_data_interpolator)。"""
    pts = np.asarray(points, float).reshape(-1, 2)
    val = np.asarray(values, float).ravel()
    return {"points": pts, "values": val, "method": method,
            "interpolator": _materialize(pts, val, method)}


def interpolate_scattered_data(interp, query_points):
    """補間器を任意のクエリ点で評価(interpolate_scattered_data)。"""
    q = np.asarray(query_points, float).reshape(-1, 2)
    obj = interp.get("interpolator")
    if obj is None:
        obj = _materialize(interp["points"], interp["values"], interp["method"])
        interp["interpolator"] = obj
    if interp["method"] == "nearest":
        _, index = obj.query(q, k=1)
        return np.asarray(interp["values"])[index]
    out = np.asarray(obj(q))
    if np.isnan(out).any():
        missing = np.isnan(out)
        from scipy.spatial import cKDTree
        _, index = cKDTree(interp["points"]).query(q[missing], k=1)
        out[missing] = np.asarray(interp["values"])[index]
    return out


def interpolate_scattered_data_points_to_image(points, values, shape, method="linear"):
    """不規則点の値を密な格子画像へ補間(interpolate_scattered_data_points_to_image)。"""
    H, W = shape
    pts = np.asarray(points, float).reshape(-1, 2)
    val = np.asarray(values, float).ravel()
    rr, cc = np.mgrid[0:H, 0:W]
    grid = np.column_stack([rr.ravel(), cc.ravel()])
    interp = create_scattered_data_interpolator(pts, val, method)
    return interpolate_scattered_data(interp, grid).reshape(H, W)


def interpolate_scattered_data_image(image, region, method="linear"):
    """画像中の欠損 region を残り画素の散布補間で埋める(interpolate_scattered_data_image)。"""
    im = np.asarray(image, float); m = np.asarray(region, bool)
    known = ~m
    rr, cc = np.where(known)
    pts = np.column_stack([rr, cc]); val = im[known]
    return interpolate_scattered_data_points_to_image(pts, val, im.shape, method)


def create_distance_transform_xld(contour, shape):
    """XLD 輪郭(dict {cs:[Nx2]})から各画素の最短距離場を生成(create_distance_transform_xld)。"""
    from scipy.spatial import cKDTree
    H, W = shape
    pts = np.vstack([np.asarray(a, float) for a in contour.get("cs", [])])
    tree = cKDTree(pts)
    rr, cc = np.mgrid[0:H, 0:W]
    grid = np.column_stack([rr.ravel(), cc.ravel()])
    d, _ = tree.query(grid, k=1)
    return d.reshape(H, W)


def apply_distance_transform_xld(dist_field, contour, shape=None):
    """距離場を使い XLD 輪郭に沿う点の対応/距離を評価(apply_distance_transform_xld)。"""
    df = np.asarray(dist_field, float)
    out = []
    for arr in contour.get("cs", []):
        for row, col in np.asarray(arr, float):
            r = int(np.clip(round(row), 0, df.shape[0] - 1))
            c = int(np.clip(round(col), 0, df.shape[1] - 1))
            out.append(df[r, c])
    return np.asarray(out)
