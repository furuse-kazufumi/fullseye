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


def test_all_palettes_valid():
    x = np.linspace(0, 1, 20).reshape(4, 5)
    assert len(imgio.COLORMAPS) >= 12
    for name in imgio.COLORMAPS:
        rgb = imgio.apply_cmap(x, name=name)
        assert rgb.shape == (4, 5, 3), name
        assert rgb.min() >= 0.0 and rgb.max() <= 1.0, name


def test_shaded_relief_and_colorize_height():
    hm = np.tile(np.linspace(0, 1, 32), (32, 1))          # a slope
    sh = imgio.shaded_relief(hm)
    assert sh.shape == (32, 32) and 0 <= sh.min() and sh.max() <= 1
    assert sh.std() > 0                                   # a slope shades non-uniformly
    ch = imgio.colorize_height(hm, name="terrain")
    assert ch.shape == (32, 32, 3) and ch.min() >= 0 and ch.max() <= 1
    # inf in a depth map stays handled
    d = np.array([[1.0, np.inf], [2.0, 3.0]])
    assert imgio.shaded_relief(d).shape == (2, 2)


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


def test_load_16bit_png_keeps_bit_depth(tmp_path):
    """A 16-bit raster must not be crushed to 8 bits: load() divides by the true
    max level (65535), so levels inside one 8-bit bucket stay distinct."""
    cv2 = imgio._cv2()
    if cv2 is None:
        pytest.skip("16-bit decode needs opencv-python")
    a = np.array([[40000, 40001, 40100], [0, 32768, 65535]], np.uint16)
    p = tmp_path / "g16.png"
    assert cv2.imwrite(str(p), a)
    back = imgio.load(str(p))
    assert back.dtype == np.float64
    assert np.allclose(back, a.astype(np.float64) / 65535.0, atol=1e-9)
    assert abs(back[0, 0] - 40000 / 65535.0) < 1e-9          # not the 8-bit 156/255
    assert len(np.unique(back[0])) == 3                      # 3 levels in one 8-bit bucket
    # colour read keeps the depth too
    c = np.zeros((2, 2, 3), np.uint16); c[..., 2] = 40000    # cv2 writes BGR -> red
    pc = tmp_path / "c16.png"
    assert cv2.imwrite(str(pc), c)
    rgb = imgio.load(str(pc), color=True)
    assert rgb.shape == (2, 2, 3)
    assert np.allclose(rgb[..., 0], 40000 / 65535.0, atol=1e-9)


def test_load_8bit_png_unchanged(tmp_path):
    """The 8-bit contract the operator suite depends on must not move."""
    cv2 = imgio._cv2()
    if cv2 is None:
        pytest.skip("needs opencv-python")
    c = (np.random.default_rng(0).random((9, 7, 3)) * 255).astype(np.uint8)
    p = str(tmp_path / "c8.png")
    assert cv2.imwrite(p, c)
    ref_g = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float64) / 255.0
    ref_c = cv2.imread(p, cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float64) / 255.0
    assert np.array_equal(imgio.load(p), ref_g)
    assert np.array_equal(imgio.load(p, color=True), ref_c)


def test_save_raises_on_unwritable_path(tmp_path):
    """Regression: cv2.imwrite returns False (never raises) on an unwritable path,
    so save() used to report a phantom success — a caller's try/except could not
    see the failure. save() now checks the return value and raises OSError."""
    if imgio._cv2() is None:
        pytest.skip("needs opencv-python (the cv2.imwrite-returns-False path)")
    bad = str(tmp_path / "no_such_subdir" / "x.png")   # parent dir does not exist -> imwrite False
    with pytest.raises(OSError):
        imgio.save(bad, np.zeros((8, 8), np.float64))
    with pytest.raises(OSError):                        # unknown extension -> cv2.error, normalised
        imgio.save(str(tmp_path / "x.zzz"), np.zeros((8, 8), np.float64))
