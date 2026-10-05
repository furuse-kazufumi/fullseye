"""名前の無い非公開関数 136 本の棚卸し(2026-10-02)で見つけた欠陥の回帰門。

1. photometric.normals_to_gradients: nz = 0 で np.sign(0) = 0 → p = −1e12(抑えが効かない)。
2. filters_flow.gen_gauss_bandpass: σ を逆に渡すとマスクが全面負のまま黙って通る。
3. imgio.ensure_color: RGBA を 4 チャネルのまま返す / (H, W, 1) を複製しない。
4. filters_flow.gen_gauss_bandpass の門: 純正弦波の利得 = マスクの値(線形・ずらし不変の定理)。
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import filters_flow as FF  # noqa: E402
import imgio  # noqa: E402
import photometric as PH  # noqa: E402


def test_a_sideways_normal_is_clamped_not_blown_up():
    p, q = PH.normals_to_gradients(np.array([1.0, 0.0, 0.0]))
    assert np.isfinite(p) and abs(p) <= 1e6 + 1
    p2, _ = PH.normals_to_gradients(np.array([1.0, 0.0, -0.0]))
    assert abs(p2) <= 1e6 + 1


def test_normals_to_gradients_inverts_the_surface_normal():
    """n ∝ (−p, −q, 1) の往復(普通の向きでは抑えに触れない)。"""
    rng = np.random.default_rng(0)
    p0, q0 = rng.normal(size=(2, 50))
    n = np.stack([-p0, -q0, np.ones(50)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    p, q = PH.normals_to_gradients(n)
    assert np.allclose(p, p0) and np.allclose(q, q0)


def test_bandpass_rejects_reversed_sigmas():
    with pytest.raises(ValueError):
        FF.gen_gauss_bandpass((64, 64), 0.2, 0.02)
    with pytest.raises(ValueError):
        FF.gen_gauss_bandpass((64, 64), 0.0, 0.2)


def test_bandpass_gain_on_a_pure_sinusoid_equals_the_mask_value():
    """FFT で掛けると、周期境界の純正弦波は周波数のマスク値 × 元の波になる(厳密)。"""
    H = W = 64
    m = FF.gen_gauss_bandpass((H, W), 0.02, 0.2)
    assert m[0, 0] == pytest.approx(0.0, abs=1e-12)          # DC は通さない
    y, x = np.mgrid[:H, :W]
    for k in (2, 8, 20):
        img = np.cos(2 * np.pi * k * x / W)
        out = np.real(np.fft.ifft2(np.fft.fft2(img) * m))
        assert np.allclose(out, m[0, k] * img, atol=1e-12)


@pytest.mark.parametrize("shape", [(5, 6), (5, 6, 1), (5, 6, 3), (5, 6, 4)])
def test_ensure_color_always_returns_three_channels(shape):
    a = np.random.default_rng(1).random(shape)
    out = imgio.ensure_color(a)
    assert out.shape == (5, 6, 3)
    if len(shape) == 3 and shape[2] >= 3:
        assert np.array_equal(out, a[:, :, :3])


def test_the_lazy_registry_still_loads_every_layer():
    """unified._ensure が全層を積む(build_registry を 0.4.0 で消した後も、層の手順は _load_layers の 1 か所)。"""
    import unified as u
    assert len(u._ensure().list()) > 1000


# ---- 0.3.0 で非推奨にした公開名 5 つは 0.4.0 で削除した —— 名前がもう無く、移行先は在ること ---- #
_REMOVED_IN_040 = (
    ("ops", "op_slot", "SLOTS"),
    ("transforms", "hom_mat3d_transpose_", "hom_mat3d_transpose"),
    ("unified", "build_registry", "_ensure"),
    ("contours_xld2", "gen_contour_nurbs_xld", None),
    ("contours_xld2", "gen_nurbs_interp", None),
)


@pytest.mark.parametrize("mod, name, successor", _REMOVED_IN_040)
def test_the_names_deprecated_in_030_are_gone_in_040(mod, name, successor):
    import importlib
    m = importlib.import_module(mod)
    assert not hasattr(m, name), "%s.%s は 0.4.0 で削除したはず" % (mod, name)
    if successor is not None:
        assert hasattr(m, successor)


def test_the_nurbs_successor_exists_and_the_halcon_facade_no_longer_points_at_the_removed_names():
    """旧 NURBS 2 本の移行先(mathgeometry.nurbs_curve)が在り、HALCON 名の facade 表が消した関数を指さない。"""
    import json
    import mathgeometry as G
    assert callable(G.nurbs_curve)
    root = Path(__file__).resolve().parents[1]
    facade = json.loads((root / "fullseye" / "data" / "halcon_facade_map.json").read_text(encoding="utf-8"))
    assert len(facade) > 500                      # 表が空なら下の not any は無条件に通る
    assert not any(str(v).startswith("contours_xld2.gen_") and "nurbs" in str(v) for v in facade.values())
    stubs = json.loads((root / "fullseye" / "data" / "halcon_stubs.json").read_text(encoding="utf-8"))
    assert stubs["operators"]["gen_contour_nurbs_xld"]["covered"] is False
    assert stubs["operators"]["gen_nurbs_interp"]["covered"] is False
    assert stubs["n_covered"] == sum(1 for v in stubs["operators"].values() if v.get("covered"))
