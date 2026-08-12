"""I/O enrichment: coercion, colormaps, overlays, and export helpers."""
import numpy as np
import pytest

import imgio


def test_to_float01_dtype_scaling():
    assert imgio.to_float01(np.array([[0, 255]], np.uint8)).tolist() == [[0.0, 1.0]]
    assert imgio.to_float01(np.array([[True, False]])).tolist() == [[1.0, 0.0]]
    f = np.array([[0.25, 0.5]])
    assert np.allclose(imgio.to_float01(f), f)               # float passthrough


def test_to_uint8_roundtrip():
    a = np.array([[0.0, 0.5, 1.0]])
    assert imgio.to_uint8(a).tolist() == [[0, 127, 255]]


def test_apply_cmap_shape_range_and_invalid_black():
    x = np.linspace(0, 1, 12).reshape(3, 4)
    for name in imgio.COLORMAPS:
        rgb = imgio.apply_cmap(x, name=name)
        assert rgb.shape == (3, 4, 3)
        assert rgb.min() >= 0.0 and rgb.max() <= 1.0
    d = np.array([[1.0, np.inf], [2.0, 3.0]])
    rgb = imgio.colorize_depth(d)
    assert np.all(rgb[0, 1] == 0.0)                          # inf -> black


def test_colorize_labels_background_black_and_distinct():
    lab = np.array([[0, 1], [2, 2]])
    rgb = imgio.colorize_labels(lab)
    assert np.all(rgb[0, 0] == 0.0)                          # bg
    assert not np.allclose(rgb[0, 1], rgb[1, 0])             # label 1 != label 2


def test_overlay_mask_changes_only_masked():
    img = np.full((4, 4), 0.5)
    mask = np.zeros((4, 4), bool); mask[1, 1] = True
    out = imgio.overlay_mask(img, mask, color=(1, 0, 0), alpha=1.0)
    assert out.shape == (4, 4, 3)
    assert np.allclose(out[1, 1], [1, 0, 0])
    assert np.allclose(out[0, 0], [0.5, 0.5, 0.5])           # untouched


def test_normalize():
    a = np.array([10.0, 20.0, 30.0])
    assert np.allclose(imgio.normalize(a), [0.0, 0.5, 1.0])


def test_save_ply_writes_valid_header(tmp_path):
    pts = np.array([[0.0, 0, 0], [1, 2, 3]])
    p = tmp_path / "cloud.ply"
    imgio.save_ply(str(p), pts)
    txt = p.read_text()
    assert txt.startswith("ply")
    assert "element vertex 2" in txt
    assert txt.strip().endswith("1 2 3")


def test_save_load_roundtrip(tmp_path):
    cv2 = imgio._cv2()
    if cv2 is None:
        pytest.importorskip("PIL")
    img = (np.mgrid[0:16, 0:16][0] / 15.0)
    p = tmp_path / "g.png"
    imgio.save(str(p), img)
    back = imgio.load(str(p))
    assert back.shape == img.shape
    assert np.abs(back - img).max() < 0.02                   # 8-bit quantisation only
