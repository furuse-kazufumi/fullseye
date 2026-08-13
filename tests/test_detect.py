"""Ground-truth tests for object segmentation / description / identification."""
import numpy as np

import detect


def _disk(img, cy, cx, r, val=1.0):
    y, x = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    img[(y - cy) ** 2 + (x - cx) ** 2 <= r * r] = val
    return img


def _square(img, cy, cx, s, val=1.0):
    img[cy - s:cy + s, cx - s:cx + s] = val
    return img


def _scene():
    g = np.zeros((100, 100))
    _disk(g, 20, 20, 6)          # small, area ~113
    _disk(g, 70, 30, 12)         # large, area ~452
    _square(g, 40, 75, 8)        # square 16x16 = 256
    return g


def test_segment_objects_finds_all_and_orders_by_area():
    objs = detect.segment_objects(_scene(), threshold="otsu")
    assert len(objs) == 3
    areas = [o["area"] for o in objs]
    assert areas == sorted(areas, reverse=True)               # sorted largest-first
    assert objs[0]["area"] > objs[-1]["area"]
    # the biggest object is the r=12 disk, centred near (70, 30)
    cy, cx = objs[0]["centroid"]
    assert abs(cy - 70) < 2 and abs(cx - 30) < 2


def test_min_area_filters_small_specks():
    g = _scene()
    g[5, 90] = 1.0                                            # a 1-px speck
    objs = detect.segment_objects(g, threshold="otsu", min_area=5)
    assert len(objs) == 3                                     # speck dropped


def test_hu_descriptor_is_rotation_stable_for_same_shape():
    a = np.zeros((80, 80)); _square(a, 40, 40, 12)
    b = np.zeros((80, 80))
    from scipy import ndimage
    b = (ndimage.rotate(a, 35, reshape=False, order=0) > 0.5).astype(float)
    da = detect.object_descriptor(detect.segment_objects(a, threshold="none")[0])
    db = detect.object_descriptor(detect.segment_objects(b, threshold="none")[0])
    # Hu moments are rotation invariant -> descriptors close despite the 35° turn
    assert np.linalg.norm(da[:4] - db[:4]) < 0.5


def test_nearest_prototype_identifies_shape():
    disk = np.zeros((80, 80)); _disk(disk, 40, 40, 15)
    square = np.zeros((80, 80)); _square(square, 40, 40, 13)
    protos = {
        "disk": detect.object_descriptor(detect.segment_objects(disk, threshold="none")[0]),
        "square": detect.object_descriptor(detect.segment_objects(square, threshold="none")[0]),
    }
    query = np.zeros((80, 80)); _disk(query, 30, 50, 10)      # a different disk
    qd = detect.object_descriptor(detect.segment_objects(query, threshold="none")[0])
    label, dist = detect.nearest_prototype(qd, protos)
    assert label == "disk"


def test_otsu_mask_not_degenerate_on_skewed_image():
    # a mostly-bright field with a few dark spots trips a wrong between-class
    # variance formula into an all-empty mask (the fixed bug). Foreground must be a
    # sensible fraction, not 0 or 1.
    img = np.full((100, 100), 0.7)
    img[10:30, 10:30] = 0.15
    img[60:80, 60:85] = 0.15
    frac = detect._otsu_mask(img).mean()
    assert 0.02 < frac < 0.98


def test_segment_real_coins_image():
    # regression for the Otsu empty-mask bug: real coins must segment into a
    # plausible count of round objects, not zero.
    data = __import__("importlib").import_module("skimage.data")
    from scipy import ndimage
    img = detect.np.asarray(data.coins(), np.float64) / 255.0
    sm = ndimage.gaussian_filter(img, 1.0)
    objs = detect.segment_objects(sm, threshold="otsu", min_area=120)
    assert 15 <= len(objs) <= 30, f"expected ~24 coins, got {len(objs)}"
    round_like = [o for o in objs if o.get("eccentricity", 1) < 0.8]
    assert len(round_like) >= len(objs) * 0.7      # most coins are disk-shaped


def test_feature_table_and_circularity():
    disk = np.zeros((80, 80)); yy, xx = np.mgrid[0:80, 0:80]
    disk[(yy - 40) ** 2 + (xx - 40) ** 2 <= 15 ** 2] = 1
    o = detect.segment_objects(disk, threshold="none")[0]
    assert 0.7 < o["circularity"] <= 1.0          # a disk is nearly circular
    txt = detect.feature_table([o])
    assert "circ" in txt and "area" in txt


def test_draw_objects_returns_rgb():
    objs = detect.segment_objects(_scene(), threshold="otsu")
    vis = detect.draw_objects(_scene(), objs)
    assert vis.ndim == 3 and vis.shape[2] == 3
    assert vis.min() >= 0 and vis.max() <= 1
