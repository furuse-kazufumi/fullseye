"""GPU 第 3 便の回帰: 採用 op ごとの parity と、採否表の門。

parity は torch があれば CPU で必ず回し、GPU 側は CUDA の無い CI では skip する(``device`` の param)。
門は台帳・実測ログ・生成物を別経路で突き合わせる: 採用は全部 ACCEL 系の台帳に在り、実測が閾値を通り、
不採用は台帳に無く、48 + 48 件が 1 件も欠けずに理由つきで表に載る。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

torch = pytest.importorskip("torch")
accel = pytest.importorskip("accel")
accel_typed = pytest.importorskip("accel_typed")

from scipy import ndimage  # noqa: E402

DEVICES = ["cpu", pytest.param("cuda", marks=pytest.mark.gpu)]


def _device(dev):
    if dev == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    return dev


def _images():
    rng = np.random.default_rng(7)
    base = np.clip(rng.random((64, 64)) * 0.6 + 0.2 * (np.mgrid[0:64, 0:64][1] / 64), 0, 1)
    smooth = np.clip(ndimage.gaussian_filter(rng.random((64, 80)), 2) * 4 - 1.5, 0, 1)
    return [base, smooth, np.round(base * 255) / 255]


COLOR = {"rgb1_to_gray", "rgb3_to_gray", "principal_comp", "linear_trans_color"}


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("name", sorted(accel.FILL3_ADOPTED))
def test_adopted_2d_op_matches_registry(name, device):
    import ops
    device = _device(device)
    fn = next(f for f, core, _h in accel.ACCEL.values() if core == name)
    if name in COLOR:
        b0 = _images()[0]
        imgs = [np.stack([b0, np.roll(b0, 5, 0) * 0.5, np.roll(b0, 9, 1)], -1)]
    else:
        imgs = _images()
    for a, b in accel.PARITY_AB:
        m = max(3, accel._k(a) // 2 + 1)
        for im in imgs:
            ref = np.clip(ops.RT[name](im.copy(), a, b), 0, 1)
            got = accel._from_batch(fn(accel._to_batch([im], device), a, b, device).clamp(0, 1))[0]
            assert got.shape == ref.shape
            assert np.ptp(ref) > 0, "vacuous reference"
            assert np.abs(ref - got)[m:-m, m:-m].max() < accel.PARITY_TOL


@pytest.mark.parametrize("device", DEVICES)
def test_spline_warp_matches_ndimage_including_the_reflected_corners(device):
    """第 2 便が「画素一致不可」とした order=3 の幾何ワープを、四隅の鏡映まで含めて全画素で比べる。"""
    device = _device(device)
    rng = np.random.default_rng(1)
    im = rng.random((48, 60))
    M = np.array([[0.9, -0.3], [0.4, 1.05]])
    off = np.array([3.5, -2.25])
    ref = ndimage.affine_transform(im, M, offset=off, mode="reflect")
    got = accel._from_batch(accel._affine_spline(accel._to_batch([im], device), M, off, device))[0]
    assert np.abs(ref - got).max() < 1e-4


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("name", sorted(accel.NARY_ACCEL))
def test_adopted_nary_op_matches_registry(name, device):
    import imgops_nary as N
    device = _device(device)
    core = {o.name: o for o in N.build_nary()}[name]
    x = _images()[0]
    yy, xx = np.mgrid[-4:5, -4:5]
    second = np.exp(-(xx * xx + yy * yy) / 8.0) * (1 + 0.1 * xx) if name == "convol_image" else np.roll(x, 3, 0)
    ref = np.clip(core.fn([x, second], 0.5, 0.4), 0, 1)
    got = accel.run_nary(name, [x, second], 0.5, 0.4, device)
    assert np.ptp(ref) > 0
    assert np.abs(ref - got).max() < accel.PARITY_TOL


def _typed_case(name):
    import plane_sweep as ps
    import tomography as tm
    rng = np.random.default_rng(3)
    im = np.clip(ndimage.gaussian_filter(rng.random((64, 64)), 2) * 5 - 2, 0, 1)
    ang = np.linspace(0, 180, 40, endpoint=False)
    sino = tm.radon_transform(im, ang)
    vol = np.stack([im, np.roll(im, 4, 0)])
    A = ndimage.gaussian_filter(rng.random((128, 128)), 1.2)
    B = ndimage.shift(A, (2.3, -1.4), order=3, mode="wrap")
    P = rng.random((5000, 3)) * 2 - 1
    K = np.array([[200., 0, 32], [0, 200, 32], [0, 0, 1]])
    lights = np.array([[0, 0, 1.], [.5, 0, 1], [0, .5, 1], [-.5, 0, 1]])
    table = {
        "radon_transform": lambda f: f(im, ang), "radon_volume": lambda f: f(vol, ang),
        "backproject_sinogram": lambda f: f(sino, ang), "filtered_backprojection": lambda f: f(sino, ang),
        "fbp_volume": lambda f: f(tm.radon_volume(vol, ang), ang),
        "sart_reconstruct": lambda f: f(sino, ang, size=64, n_iter=2),
        "piv_cross_correlate": lambda f: f(A, B, window=32)[0], "piv_multipass": lambda f: f(A, B)[0],
        "piv_ensemble_correlate": lambda f: f([A, B, np.roll(B, 1, 0)], window=32)[0],
        "plane_sweep_depth": lambda f: f(im, im, K, np.eye(3), np.array([.01, 0, 0]), np.linspace(1, 4, 6), window=1),
        "joint_bilateral": lambda f: f(im, np.roll(im, 1, 0), 2.0, 0.1),
        "temporal_bilateral": lambda f: f(np.stack([im, im * 0.9, np.roll(im, 1, 0), im])),
        "voxel_grid_downsample": lambda f: f(P, 0.2),
        "occupancy_grid": lambda f: f(P, ((-1, 1), (-1, 1), (-1, 1)), 16),
        "photometric_stereo": lambda f: f(np.stack([np.clip(im * (0.5 + 0.1 * i) + 0.1, 0, 1) for i in range(4)]), lights)[0],
        "points_to_voxel": lambda f: f(P, 16),
        "scene_flow_lk": lambda f: f(ndimage.gaussian_filter(rng.random((24,) * 3), 1.5),
                                     ndimage.gaussian_filter(rng.random((24,) * 3), 1.5)),
    }
    del ps
    return table[name]


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("name", sorted(accel_typed.TYPED_ADOPTED))
def test_adopted_typed_op_matches_core(name, device):
    device = _device(device)
    module, fname, _k, _d = accel_typed.CANDIDATES[name]
    core = getattr(__import__(module), fname)
    case = _typed_case(name)
    # 乱数入力の op があるので、core と GPU に同じ乱数列を渡すため case を作り直す
    a = np.asarray(case(core), float)
    case = _typed_case(name)
    b = np.asarray(case(lambda *x, **k: accel_typed.call(name, *x, device=device, **k)), float)
    ok = np.isfinite(a) & np.isfinite(b)
    assert (np.isfinite(a) == np.isfinite(b)).mean() > 0.999
    assert np.ptp(a[ok]) > 0
    assert np.abs(a[ok] - b[ok]).max() / np.abs(a[ok]).max() < accel.PARITY_TOL


def test_unregistered_typed_op_is_refused_not_silently_cpu():
    with pytest.raises(KeyError):
        accel_typed.call("no_such_op", device="cpu")


def test_seam_is_empty_by_default_and_restored():
    import accel_seam
    assert accel_seam.kernel("tomography.project") is None
    with accel_seam.use({"tomography.project": len}):
        assert accel_seam.kernel("tomography.project") is len
    assert accel_seam.kernel("tomography.project") is None


def test_every_halcon_and_required_op_has_a_verdict_and_the_ledger_agrees():
    import gen_gpu_fill3_report as g
    data = g.build()
    assert g.consistency(data) == []
    # HALCON は 48 件が全部載る(独立に行列 JSON から数え直す)
    par = json.loads((ROOT / "docs" / "perf" / "halcon_opencl_parity.json").read_text(encoding="utf-8"))
    assert par["n1_fullseye"] == 71
    assert len({r["halcon"] for r in data["halcon"]}) == 48
    for r in data["halcon"] + data["required"]:
        assert r["verdict"] in ("採用", "不採用", "測定不能") and r["reason"]
        if r["verdict"] == "採用":
            assert r["ratio"] >= g.THRESHOLD
            assert max(r["parity_cpu"], r["parity_gpu"]) < accel.PARITY_TOL
    # 不採用の幾何・計算核の op は台帳に載らない
    ledger = set(data["adopted_2d"]) | set(data["adopted_nary"]) | set(data["adopted_typed"])
    for r in data["halcon"] + data["required"]:
        if r["verdict"] != "採用":
            assert r["op"].split("@")[0] not in ledger or r["op"].endswith("31x31")


def test_report_is_generated_not_edited():
    import gen_gpu_fill3_report as g
    assert g.main(["--check"]) == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
