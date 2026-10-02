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


def test_build_registry_and_the_lazy_registry_load_the_same_layers():
    """unified.build_registry と _ensure は同じ層を同じ順に積む(手順を 1 か所にした回帰)。"""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import unified as u
        a, b = u.build_registry(), u._ensure()
    assert sorted(a.list()) == sorted(b.list())
    assert len(a.list()) > 1000


def test_the_transpose_alias_matches_the_original():
    import transforms as T
    H = np.arange(16.0).reshape(4, 4)
    assert np.array_equal(T.hom_mat3d_transpose_(H), T.hom_mat3d_transpose(H))



# ---- 呼び出し元 0 本の公開名 3 つは非推奨(0.3.0 で非推奨・0.4.0 で削除)—— 警告を出し、答えは変えない ---- #
def test_the_three_dead_public_names_warn_and_still_answer():
    import pytest
    import ops
    import transforms as T
    import unified as u
    name = next(iter(ops.SLOTS))
    with pytest.warns(DeprecationWarning, match="0.4.0"):
        assert ops.op_slot(name) == ops.SLOTS[name]
    H = np.arange(16.0).reshape(4, 4)
    with pytest.warns(DeprecationWarning, match="0.4.0"):
        assert np.array_equal(T.hom_mat3d_transpose_(H), H.T)
    with pytest.warns(DeprecationWarning, match="0.4.0"):
        assert len(u.build_registry().list()) > 1000


def test_the_warning_points_at_the_caller_not_the_library():
    import warnings
    import transforms as T
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        T.hom_mat3d_transpose_(np.eye(4))
    assert w and w[0].filename == __file__        # stacklevel=2
