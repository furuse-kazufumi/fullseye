# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``reprconv`` / ``opsreprconv`` —— 変換 op の往復・型・軸・単位を機械検証する。

このファイルの構成は、変換 op が嘘をつく 4 つの面にそのまま対応している:

1. **往復** —— 可逆なはずのものは ε 以下、不可逆なものは「どう失うか」を測る。
   ``opsreprconv.ROUNDTRIPS`` の宣言表をそのまま回すので、**表と実装が
   食い違ったら落ちる**(片方だけ直せない)。
2. **宣言型と実戻り値** —— 台帳の ``out`` と実際の返りが一致するか。
   **型ではなく形で判定**する(GPU backend を持つ op は torch.Tensor を返すのが
   この repo の約束で、``isinstance(np.ndarray)`` と書くと述語の側が間違う)。
3. **軸と単位** —— (z,y,x) の順序、spacing、度/ラジアン、原点が変換をまたいで
   保存されるか。**ここが一番嘘をつく**。
4. **fail-closed** —— 非有限・空・次元不一致・巨大 shape を黙って通さないか。

加えて **敵対的検証**(``TestAdversarial``)を置く。狙いは「例外が出る」ではなく
「**黙って間違った数字を返す**」種類で、これは実際に 2 件見つかった(下記)。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import opsreprconv                                          # noqa: E402
import reprconv as rc                                       # noqa: E402


@pytest.fixture()
def rng():
    return np.random.default_rng(20260902)


def _unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


# --------------------------------------------------------------------------- #
# 1. 往復 —— 可逆なものは数値で、不可逆なものは失う量で                          #
# --------------------------------------------------------------------------- #
class TestRoundTripExact:
    """可逆と宣言したものが本当に可逆か。**誤差は数字で出す**。"""

    def test_normals_angles_bit_close(self, rng):
        v = _unit(rng.standard_normal((2048, 3)))
        err = float(np.max(np.abs(rc.angles_to_normals(rc.normals_to_angles(v)) - v)))
        assert err < 1e-12, f"normals round trip max|Δ| = {err}"

    def test_normals_angles_drops_only_magnitude(self, rng):
        """非単位ベクトルは**長さだけ**落ちる(向きは厳密に戻る)。"""
        v = rng.standard_normal((512, 3)) * rng.uniform(0.1, 9.0, (512, 1))
        back = rc.angles_to_normals(rc.normals_to_angles(v))
        assert np.allclose(np.linalg.norm(back, axis=1), 1.0, atol=1e-12)
        cos = np.sum(back * _unit(v), axis=1)
        assert float(np.max(np.abs(cos - 1.0))) < 1e-12

    def test_shape_index_exact_including_umbilics(self, rng):
        """臍点 (k1 == k2) と平面 (0, 0) を**必ず混ぜる**。

        除算で書いた形状指数はそこでだけ NaN を出す。混ぜないテストは
        「頑健だから通った」のか「その経路を一度も踏まなかった」のかを
        区別できない。
        """
        k = np.concatenate([rng.standard_normal((400, 2)),
                            np.repeat(rng.standard_normal((40, 1)), 2, axis=1),
                            np.zeros((5, 2))])
        k = np.stack([k.max(1), k.min(1)], 1)
        sc = rc.curvature_to_shape_index(k)
        assert np.all(np.isfinite(sc)), "shape index produced non-finite at umbilic/flat"
        assert np.all(np.abs(sc[:, 0]) <= 1.0 + 1e-12)
        assert np.all(sc[:, 1] >= 0.0)
        err = float(np.max(np.abs(rc.shape_index_to_curvature(sc) - k)))
        assert err < 1e-12, f"curvature round trip max|Δ| = {err}"

    def test_shape_index_known_values(self):
        """閉形式の真値: 球 (1,1) は S=+1、杯 (-1,-1) は S=-1、鞍 (1,-1) は S=0。"""
        k = np.array([[1.0, 1.0], [-1.0, -1.0], [1.0, -1.0], [1.0, 0.0]])
        s = rc.curvature_to_shape_index(k)[:, 0]
        assert np.allclose(s[:3], [1.0, -1.0, 0.0], atol=1e-12)
        assert np.isclose(s[3], 0.5, atol=1e-12)          # 稜: atan2(1,1) = pi/4
        c = rc.curvature_to_shape_index(k)[:, 1]
        assert np.allclose(c, [1.0, 1.0, 1.0, math.sqrt(0.5)], atol=1e-12)

    @pytest.mark.parametrize("shape", [(131,), (12, 9), (2, 5)])
    def test_descriptor_matrix_bit_identical(self, rng, shape):
        d = rng.standard_normal(shape)
        back = rc.matrix_to_descriptor(rc.descriptor_to_matrix(d))
        assert back.shape == d.shape, f"round trip changed shape {d.shape} -> {back.shape}"
        assert np.array_equal(back, d)

    def test_keypoints_points_bit_identical(self, rng):
        kp = rng.random((512, 2)) * 100.0
        z = rng.random(512) * 5.0
        back = rc.points_zyx_to_keypoints_uv(rc.keypoints_uv_to_points(kp, z))
        assert np.array_equal(back, kp)

    def test_indices_labels_bit_identical(self, rng):
        idx = np.unique(rng.integers(0, 500, size=120))
        assert np.array_equal(rc.labels_to_indices(rc.indices_to_labels(idx)), idx)

    def test_position_points_bit_identical(self):
        pos = (3.5, 7.25, 11.125)
        assert rc.points_to_position(rc.position_to_points(pos)) == pos

    def test_gaussian_centers_bit_identical(self, rng):
        p = rng.standard_normal((300, 3)) * 3.0
        assert np.array_equal(rc.gaussians_to_points(rc.points_to_gaussians(p)), p)

    def test_angle_matrix_roundtrip(self, rng):
        angs = rng.uniform(-179.9, 179.9, size=256)
        back = np.array([rc.matrix_to_angle(rc.angle_to_matrix(a)) for a in angs])
        err = float(np.max(np.abs(back - angs)))
        assert err < 1e-10, f"angle round trip max|Δ| = {err} deg"

    def test_rot_scale_matrix_roundtrip(self, rng):
        rs = np.stack([rng.uniform(-179.9, 179.9, 256), rng.uniform(0.05, 20.0, 256)], 1)
        back = np.array([rc.matrix_to_rot_scale(rc.rot_scale_to_matrix(r)) for r in rs])
        assert float(np.max(np.abs(back[:, 0] - rs[:, 0]))) < 1e-10
        assert float(np.max(np.abs(back[:, 1] / rs[:, 1] - 1.0))) < 1e-12

    def test_shift_vector_bit_identical(self, rng):
        for s in rng.integers(-16, 17, size=(64, 3)):
            assert rc.vector_to_shift(rc.shift_to_vector(tuple(int(x) for x in s))) \
                == tuple(int(x) for x in s)

    def test_cscalar_polar_roundtrip(self, rng):
        zs = rng.standard_normal(256) + 1j * rng.standard_normal(256)
        err = max(abs(rc.polar_to_cscalar(rc.cscalar_to_polar(z)) - z) for z in zs)
        assert err < 1e-12, f"cscalar round trip max|Δ| = {err}"

    def test_countrate_counts_relative(self, rng):
        """レートは 1e3-1e7 Hz と桁が広いので**相対**で言う(絶対だと大きく見える)。"""
        cr = 10.0 ** rng.uniform(3.0, 7.0, size=512)
        back = rc.counts_to_countrate(rc.countrate_to_counts(cr, 1e-3), 1e-3)
        rel = float(np.max(np.abs(back / cr - 1.0)))
        assert rel < 1e-15, f"countrate round trip max relative = {rel}"


class TestRoundTripLossy:
    """不可逆なものは「戻らない」で終わらせず、**どの量がどれだけ落ちるか**を測る。"""

    def test_keypoint_raster_quantization_matches_theory(self, rng):
        """よく離した点なら、往復誤差は一様量子化の理論値と一致する。

        軸あたり RMS = 1/sqrt(12) = 0.2887 px、2-D 距離 RMS = sqrt(2/12) = 0.4082 px。
        **軸あたりと距離を混ぜない** —— 混ぜると正しい実装が誤って見える。
        """
        grid = np.stack(np.meshgrid(np.arange(3.0, 122.0, 4.0),
                                    np.arange(3.0, 122.0, 4.0), indexing="ij"), -1)
        kp = grid.reshape(-1, 2) + rng.uniform(-0.5, 0.5, size=(grid[..., 0].size, 2))
        back = rc.keypoints_from_image2d(rc.keypoints_to_image2d(kp, shape=(128, 128)))
        assert back.shape == kp.shape, "well-separated points must not merge"
        from scipy.spatial import cKDTree
        _, j = cKDTree(back).query(kp, k=1)
        axis_rms = float(np.sqrt(np.mean((back[j] - kp) ** 2)))
        assert abs(axis_rms - 1.0 / math.sqrt(12.0)) < 0.02, \
            f"per-axis quantization RMS {axis_rms} != theory {1 / math.sqrt(12):.4f}"

    def test_keypoint_raster_merges_are_reported_not_hidden(self):
        """同じ画素に落ちた 2 点は融合する。**点数が減ることを固定する**。"""
        kp = np.array([[10.1, 10.1], [10.2, 10.0], [40.0, 40.0]])
        back = rc.keypoints_from_image2d(rc.keypoints_to_image2d(kp, shape=(64, 64)))
        assert back.shape[0] == 2, "two adjacent points must merge into one component"

    def test_points_to_position_loses_spread(self, rng):
        cloud = rng.standard_normal((500, 3)) * 2.0
        pos = rc.points_to_position(cloud)
        spread = float(np.sqrt(np.mean(np.sum((cloud - np.asarray(pos)) ** 2, axis=1))))
        assert spread > 1.0, "the discarded spread must be measurable, not zero"
        assert np.allclose(pos, cloud.mean(0))

    def test_labels_to_indices_loses_trailing_background(self):
        lab = np.zeros(100, np.int64)
        lab[[3, 17, 40]] = 1
        back = rc.indices_to_labels(rc.labels_to_indices(lab))
        assert back.size == 41, f"length must truncate to max_index+1; got {back.size}"
        assert np.array_equal(back, lab[:41])

    def test_gaussians_to_voxel_mass_matches_box_truncation(self):
        """★実際に間違えた数字の回帰テスト。

        最初 docstring に「3 sigma の**球**の質量 97.07%」と書いたが、実装の
        打ち切りは**軸並行の箱**なので正しい極限は ``erf(3/sqrt(2))**3`` =
        99.194%。刻みを細かくすると 99.94% -> 99.30% と**箱の値へ**単調に
        近づき、球の 97.07% には近づかない —— これが反証。
        例外も NaN も出ない、「黙って間違った数字」の典型。
        """
        box = math.erf(3.0 / math.sqrt(2.0)) ** 3
        ball = math.erf(3.0 / math.sqrt(2.0)) - math.sqrt(2.0 / math.pi) * 3.0 * math.exp(-4.5)
        g = {"mu": np.array([[8.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
        mass = [float(rc.gaussians_to_voxel(g, shape=(int(round(16 / s)),) * 3,
                                            spacing=(s, s, s)).sum())
                for s in (1.0, 0.5, 0.25, 0.125)]
        assert all(a > b for a, b in zip(mass, mass[1:])), \
            f"midpoint-rule mass must decrease monotonically; got {mass}"
        assert abs(mass[-1] - box) < 0.002, f"finest grid {mass[-1]} must approach box {box}"
        assert abs(mass[-1] - ball) > 0.02, \
            f"finest grid {mass[-1]} must NOT approach the ball value {ball}"

    def test_gaussians_to_voxel_boundary_clipping_is_larger(self):
        """縁に置いたガウシアンは打ち切りより遥かに大きく欠ける(数字で固定)。"""
        c = {"mu": np.array([[8.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
        e = {"mu": np.array([[1.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
        m_c = float(rc.gaussians_to_voxel(c, shape=(16, 16, 16)).sum())
        m_e = float(rc.gaussians_to_voxel(e, shape=(16, 16, 16)).sum())
        assert m_c > 0.99 and 0.80 < m_e < 0.90, f"centered {m_c}, edge {m_e}"

    def test_egi_binning_loss_is_bounded_by_bin_width(self, rng):
        n = _unit(np.array([0.3, 0.4, 0.8]))
        cloud = _unit(n + 0.02 * rng.standard_normal((8000, 3)))
        egi = rc.normals_to_egi(cloud, n_az=36, n_el=18)
        ei, ai = np.unravel_index(int(np.argmax(egi)), egi.shape)
        peak = rc.angles_to_normals(np.array([[
            (ai + 0.5) / 36.0 * 360.0 - 180.0,
            math.degrees(math.asin((ei + 0.5) / 18.0 * 2.0 - 1.0))]]))[0]
        err = math.degrees(math.acos(float(np.clip(peak @ n, -1, 1))))
        assert err < 10.0, f"peak bin off by {err} deg (bin width is 10 deg)"
        assert egi.sum() == cloud.shape[0], "EGI must conserve the count"


class TestRoundTripTableMatchesImplementation:
    """``opsreprconv.ROUNDTRIPS`` の宣言表と実装の一致そのものを検査する。"""

    def test_every_named_op_exists(self):
        for r in opsreprconv.ROUNDTRIPS:
            assert r["forward"] in opsreprconv.OPSREPRCONV, r["forward"]
            if r["backward"] is not None:
                assert r["backward"] in opsreprconv.OPSREPRCONV, r["backward"]

    def test_exact_pairs_declare_a_backward_and_a_tol(self):
        for r in opsreprconv.ROUNDTRIPS:
            if r["kind"] == "exact":
                assert r["backward"] is not None, f"{r['forward']}: exact needs a backward"
                assert "tol" in r, f"{r['forward']}: exact needs a numeric tol"
            else:
                assert r.get("lost"), f"{r['forward']}: lossy/oneway must say what is lost"

    def test_backward_out_type_matches_forward_in_type(self):
        """A -> B の逆は B -> A でなければならない(台帳レベルの整合)。"""
        for r in opsreprconv.ROUNDTRIPS:
            if r["backward"] is None:
                continue
            f = opsreprconv.info(r["forward"])
            b = opsreprconv.info(r["backward"])
            assert b["in"][0] == f["out"], f"{r['forward']} -> {r['backward']}: " \
                                           f"{f['out']} != {b['in'][0]}"
            assert b["out"] == f["in"][0], f"{r['forward']} -> {r['backward']}: " \
                                           f"{b['out']} != {f['in'][0]}"

    def test_selftest_reports_every_declared_exact_pair(self):
        rows = rc.roundtrip_report(seed=0)
        assert sum(1 for r in rows if r["kind"] == "exact") >= 12
        for r in rows:
            if r["kind"] == "exact":
                assert r["max_abs"] < 1e-9, f"{r['pair']}: max|Δ| = {r['max_abs']}"


# --------------------------------------------------------------------------- #
# 2. 宣言型と実戻り値 —— 上の 4 件の実バグは全部これ                             #
# --------------------------------------------------------------------------- #
#: **型ではなく形で判定する**述語。``chain_fuzz.TYPE_CHECKS`` と同じ流儀で、
#: GPU backend が torch.Tensor を返しても述語の側が間違わないようにする。
def _has_shape(v, want):
    s = tuple(getattr(v, "shape", ()))
    if len(s) != len(want):
        return False
    return all(w is None or w == a for w, a in zip(want, s))


DECLARED_CHECKS = {
    "points": lambda v: _has_shape(v, (None, 3)),
    "normals": lambda v: _has_shape(v, (None, 3)),
    "keypoints": lambda v: _has_shape(v, (None, 2)),
    "pairs": lambda v: _has_shape(v, (None, 2)),
    "curvature": lambda v: _has_shape(v, (None, 2)),
    "descriptor": lambda v: len(getattr(v, "shape", ())) in (1, 2),
    "matrix": lambda v: len(getattr(v, "shape", ())) == 2,
    "image2d": lambda v: len(getattr(v, "shape", ())) == 2,
    "rgbimage": lambda v: _has_shape(v, (None, None, 3)),
    "voxel": lambda v: len(getattr(v, "shape", ())) == 3,
    "score": lambda v: len(getattr(v, "shape", ())) == 3,
    "signal": lambda v: len(getattr(v, "shape", ())) == 1,
    "counts": lambda v: len(getattr(v, "shape", ())) == 1 and np.all(np.asarray(v) >= 0),
    "countrate": lambda v: len(getattr(v, "shape", ())) == 1 and np.all(np.asarray(v) >= 0),
    "labels": lambda v: len(getattr(v, "shape", ())) >= 1,
    "indices": lambda v: len(getattr(v, "shape", ())) == 1,
    "vector": lambda v: _has_shape(v, (3,)),
    "position": lambda v: isinstance(v, tuple) and len(v) == 3
    and all(isinstance(x, float) for x in v),
    "shift": lambda v: isinstance(v, tuple) and len(v) == 3
    and all(isinstance(x, int) for x in v),
    "rot_scale": lambda v: isinstance(v, tuple) and len(v) == 2
    and all(isinstance(x, float) for x in v),
    "angle": lambda v: isinstance(v, float),
    "cscalar": lambda v: isinstance(v, complex),
    "table": lambda v: isinstance(v, (dict, list)),
    "gaussians": lambda v: isinstance(v, dict) and {"mu", "sigma", "w"} <= set(v),
    "flow": lambda v: len(getattr(v, "shape", ())) in (2, 4),
    "deformation": lambda v: isinstance(v, dict) and "ctrl" in v,
}


def _sample_inputs(rng):
    """各型の代表入力(``chain_fuzz`` の種と同じ流儀で小さく・決定的に)。"""
    n = _unit(rng.standard_normal((160, 3)))
    pts = rng.random((160, 3)) * 10.0
    vox = np.exp(-(((np.mgrid[0:16, 0:16, 0:16] - 8.0) ** 2).sum(0)) / 12.0)
    return {
        "normals": n,
        "pairs": np.stack([np.arange(64.0), rng.standard_normal(64)], 1),
        "curvature": np.stack([np.abs(rng.standard_normal(64)) + 0.1,
                               -np.abs(rng.standard_normal(64)) - 0.1], 1),
        "descriptor": rng.standard_normal(131),
        "matrix": rng.standard_normal((6, 6)),
        "keypoints": rng.random((64, 2)) * 30.0,
        "points": pts,
        "position": (3.5, 7.25, 11.125),
        "indices": np.unique(rng.integers(0, 160, size=32)),
        "labels": (rng.random((24, 24)) > 0.7).astype(np.int32),
        "image2d": (rng.random((32, 32)) > 0.9).astype(float),
        "flow": np.stack([rng.standard_normal((12, 12, 12)) for _ in range(3)]),
        "gaussians": rc.points_to_gaussians(pts),
        "score": vox,
        "voxel": vox,
        "angle": 37.5,
        "rot_scale": (37.5, 2.0),
        "shift": (1, -2, 3),
        "vector": np.array([1.4, -2.6, 3.5]),
        "cscalar": complex(0.7, -1.3),
        "countrate": np.sort(10.0 ** rng.uniform(3.0, 7.0, size=32)),
        "counts": np.abs(rng.standard_normal(32)) * 100.0,
        "deformation": {"ctrl": pts.copy(), "w": rng.standard_normal((160, 3)) * 0.01,
                        "a": rng.standard_normal((4, 3)), "lam": 0.0},
    }


def _special_inputs(pool, scattered):
    """同じ型名でも op ごとに要求する**形**が違うものを明示する。

    ``matrix`` は ``matrix_to_angle`` が (3,3)、``matrix_to_rot_scale`` が (2,2)、
    ``matrix_to_descriptor`` は任意 —— 同じ型プールの 1 つの値では全部を賄えない。
    これを黙って型プールの都合に合わせると、**一部の op が「実行できなかった」
    まま合格する**(この repo で実バグを見逃した経路そのもの)。
    """
    return {
        "flow_speed": (scattered,),
        "flow_apply": (pool["points"], scattered),
        "correlation_score": (pool["voxel"], np.roll(pool["voxel"], 2, axis=1)),
        "select_points": (pool["points"], pool["indices"]),
        "polar_to_cscalar": (np.array([[2.0, 30.0]]),),
        "shape_index_to_curvature": (np.stack(
            [np.linspace(-1.0, 1.0, 32), np.linspace(0.1, 2.0, 32)], 1),),
        "angles_to_normals": (np.stack(
            [np.linspace(-179.0, 179.0, 32), np.linspace(-89.0, 89.0, 32)], 1),),
        "matrix_to_angle": (rc.angle_to_matrix(37.5),),
        "matrix_to_rot_scale": (rc.rot_scale_to_matrix((37.5, 2.0)),),
    }


class TestDeclaredTypeMatchesActualReturn:
    """台帳の ``out`` 宣言と実際の返りが一致するか。**全 op を実際に実行する**。

    「実行されていないので誰も気づけなかった」を防ぐため、実行できなかった op が
    1 つでもあれば失敗させる —— 実行できないことは合格の理由にならない。
    """

    def test_every_op_runs_and_returns_its_declared_type(self, rng):
        pool = _sample_inputs(rng)
        # 散在フローは (N,3)。密フロー用の op と入力を分ける(同じ型名で別物)
        scattered = rng.standard_normal((160, 3)) * 0.1
        special = _special_inputs(pool, scattered)
        ran, problems = 0, []
        for name, meta in sorted(opsreprconv.OPSREPRCONV.items()):
            args = special.get(name) or tuple(pool[t] for t in meta["in"])
            try:
                out = opsreprconv.call(name, *args)
            except Exception as exc:                     # noqa: BLE001
                problems.append(f"{name}: NOT EXECUTED ({type(exc).__name__}: {exc})")
                continue
            ran += 1
            check = DECLARED_CHECKS[meta["out"]]
            if not check(out):
                problems.append(f"{name}: declares out={meta['out']} but returned "
                                f"{type(out).__name__} shape {getattr(out, 'shape', None)}")
        assert not problems, "\n".join(problems)
        assert ran == len(opsreprconv.OPSREPRCONV), f"only {ran} ops executed"

    def test_no_op_leaks_non_finite_from_finite_input(self, rng):
        """有限入力から NaN/Inf が無言で出ないか(NONFINITE_BY_CONTRACT は空)。"""
        pool = _sample_inputs(rng)
        scattered = rng.standard_normal((160, 3)) * 0.1
        special = _special_inputs(pool, scattered)
        for name, meta in sorted(opsreprconv.OPSREPRCONV.items()):
            out = opsreprconv.call(name, *(special.get(name)
                                           or tuple(pool[t] for t in meta["in"])))
            vals = out if isinstance(out, (dict,)) else {"": out}
            for key, v in (vals.items() if isinstance(vals, dict) else []):
                a = np.asarray(list(v) if isinstance(v, tuple) else v)
                if a.dtype.kind in "fc":
                    assert np.all(np.isfinite(a)), f"{name}{'[' + key + ']' if key else ''}"

    def test_adapters_and_contract_sets_are_empty_by_design(self):
        assert opsreprconv.RESULT_ADAPTERS == {}
        assert opsreprconv.NONFINITE_BY_CONTRACT == frozenset()

    def test_catalog_is_complete_and_names_match_module(self):
        assert opsreprconv.missing() == []
        assert set(opsreprconv.OPSREPRCONV) <= set(rc.__all__)


# --------------------------------------------------------------------------- #
# 3. 軸・単位・spacing —— 一番嘘をつくところ                                     #
# --------------------------------------------------------------------------- #
class TestAxesUnitsSpacing:

    def test_position_is_zyx_and_survives_points(self):
        """``position`` は (z, y, x)。``vol_rle_centroid`` の実測と突き合わせる。"""
        import volregion
        v = np.zeros((20, 30, 40))
        v[2:4, 10:12, 30:32] = 1.0
        pos = volregion.vol_rle_centroid(volregion.vol_rle_encode(v > 0.5))
        assert pos == (2.5, 10.5, 30.5)
        assert rc.points_to_position(rc.position_to_points(pos)) == pos

    def test_keypoints_uv_are_col_row_not_row_col(self):
        """``project_points`` の (u, v) = (列, 行) を実測で確かめ、変換が守るか見る。"""
        import match3d
        K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]])
        # カメラ座標 (X, Y, Z): X を +1 動かすと u(列)が動き、v(行)は動かない
        uv, _ = match3d.project_points(np.array([[0.0, 0.0, 5.0], [1.0, 0.0, 5.0]]), K)
        assert uv[1, 0] > uv[0, 0] and uv[1, 1] == uv[0, 1], \
            "project_points must return (u, v) = (col, row)"
        pts = rc.keypoints_uv_to_points(uv, z=0.0)
        assert np.allclose(pts[:, 2], uv[:, 0]), "u must land on axis 2 (x/col)"
        assert np.allclose(pts[:, 1], uv[:, 1]), "v must land on axis 1 (y/row)"

    def test_swapping_uv_is_a_silent_error_not_an_exception(self):
        """**誤り例**: (u,v) を (v,u) と読んでも例外は出ず、位置だけがずれる。"""
        kp = np.array([[10.0, 40.0]])
        right = rc.keypoints_uv_to_points(kp, z=0.0)
        wrong = rc.keypoints_uv_to_points(kp[:, ::-1], z=0.0)
        assert np.all(np.isfinite(wrong)), "the wrong reading raises nothing — that is the point"
        assert float(np.linalg.norm(right - wrong)) == pytest.approx(30.0 * math.sqrt(2.0))

    def test_keypoints_raster_puts_v_on_rows(self):
        img = rc.keypoints_to_image2d(np.array([[3.0, 9.0]]), shape=(16, 16))
        assert img[9, 3] == 1.0 and img.sum() == 1.0, "row must be v, column must be u"

    def test_score_position_is_zyx_unravel_order(self):
        s = np.zeros((7, 11, 13))
        s[2, 5, 9] = 1.0
        assert rc.score_to_position(s) == (2.0, 5.0, 9.0)

    def test_correlation_recovers_a_known_integer_shift_exactly(self):
        """閉形式の真値: 巡回シフトした体積の相関ピークは厳密にそのシフトに立つ。"""
        n = 24
        zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
        base = np.exp(-(((zz - 11.0) ** 2 + (yy - 13.0) ** 2 + (xx - 7.0) ** 2) / 8.0))
        for sh in [(3, -5, 2), (0, 0, 0), (-1, 7, -7)]:
            got = rc.score_to_position(
                rc.correlation_score(base, np.roll(base, sh, axis=(0, 1, 2))))
            assert got == tuple(float(s % n) for s in sh), f"shift {sh} -> {got}"

    def test_gaussians_to_voxel_honours_origin_and_spacing(self):
        """世界座標 -> 添字は ``(mu - origin) / spacing``。**取り違えは黙って通る**。"""
        g = {"mu": np.array([[10.0, 12.0, 14.0]]), "sigma": np.array([0.4]),
             "w": np.array([1.0])}
        v = rc.gaussians_to_voxel(g, shape=(16, 16, 16), origin=(2.0, 2.0, 2.0),
                                  spacing=(2.0, 2.0, 2.0), truncate=4.0)
        assert np.unravel_index(int(np.argmax(v)), v.shape) == (4, 5, 6)
        # spacing を無視すると別の場所に立つ。例外は出ない = 誤り例
        w = rc.gaussians_to_voxel(g, shape=(16, 16, 16))
        assert np.all(np.isfinite(w))
        assert np.unravel_index(int(np.argmax(w)), w.shape) == (10, 12, 14)

    def test_angle_is_degrees_and_rotates_axis2_to_axis1(self):
        r = rc.angle_to_matrix(90.0)
        assert np.allclose(r @ np.array([0.0, 0.0, 1.0]), [0.0, -1.0, 0.0], atol=1e-12)
        assert np.allclose(r @ np.array([0.0, 1.0, 0.0]), [0.0, 0.0, 1.0], atol=1e-12)
        # ラジアンを渡しても例外は出ない = 誤り例
        assert abs(rc.matrix_to_angle(rc.angle_to_matrix(math.pi / 2.0)) - 90.0) > 88.0

    def test_normals_angles_are_degrees_with_known_axes(self):
        a = rc.normals_to_angles(np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                                           [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]]))
        assert np.allclose(a[:, 0], [0.0, 90.0, 0.0, 180.0], atol=1e-12)
        assert np.allclose(a[:, 1], [0.0, 0.0, 90.0, 0.0], atol=1e-12)

    def test_countrate_unit_is_hz_times_seconds(self):
        cr = np.array([1.0e6])
        assert rc.countrate_to_counts(cr, gate_s=1.0e-3)[0] == pytest.approx(1000.0)
        assert rc.counts_to_countrate(np.array([1000.0]), gate_s=1.0e-3)[0] \
            == pytest.approx(1.0e6)

    def test_wrong_gate_scales_counts_without_raising(self):
        """**誤り例**: gate を 1 ms でなく 1 s と読むと 1000 倍ずれるが例外は出ない。"""
        cr = np.array([1.0e6])
        assert rc.countrate_to_counts(cr, 1.0)[0] / rc.countrate_to_counts(cr, 1e-3)[0] \
            == pytest.approx(1000.0)

    def test_rot_scale_angle_is_degrees(self):
        m = rc.rot_scale_to_matrix((90.0, 3.0))
        assert np.allclose(m @ np.array([1.0, 0.0]), [0.0, 3.0], atol=1e-12)
        ang, sc = rc.matrix_to_rot_scale(m)
        assert ang == pytest.approx(90.0) and sc == pytest.approx(3.0)


# --------------------------------------------------------------------------- #
# 4. fail-closed —— 黙って通さない                                              #
# --------------------------------------------------------------------------- #
class TestFailClosed:

    @pytest.mark.parametrize("fn,bad", [
        (rc.normals_to_angles, np.array([[1.0, np.nan, 0.0]])),
        (rc.normals_to_angles, np.array([[np.inf, 0.0, 0.0]])),
        (rc.angles_to_normals, np.array([[0.0, np.nan]])),
        (rc.pairs_to_signal, np.array([[np.nan, 1.0]])),
        (rc.descriptor_to_matrix, np.array([np.nan, 1.0])),
        (rc.countrate_to_counts, np.array([np.inf])),
        (rc.score_to_position, np.full((3, 3, 3), np.nan)),
    ])
    def test_non_finite_rejected(self, fn, bad):
        with pytest.raises(ValueError, match="non-finite"):
            fn(bad)

    @pytest.mark.parametrize("fn", [
        rc.normals_to_angles, rc.pairs_to_signal, rc.descriptor_to_matrix,
        rc.labels_to_indices, rc.countrate_to_counts, rc.score_to_position,
    ])
    def test_empty_rejected(self, fn):
        with pytest.raises(ValueError, match="empty"):
            fn(np.zeros((0,)))

    @pytest.mark.parametrize("fn,bad,msg", [
        (rc.normals_to_angles, np.zeros((4, 2)), r"\(N, 3\)"),
        (rc.angles_to_normals, np.zeros((4, 3)), r"\(N, 2\)"),
        (rc.position_to_points, np.zeros(4), "length-3"),
        (rc.shift_to_vector, np.zeros(2), "length-3"),
        (rc.rot_scale_to_matrix, np.zeros(3), "length-2"),
        (rc.matrix_to_angle, np.zeros((2, 2)), r"\(3, 3\)"),
        (rc.matrix_to_rot_scale, np.zeros((3, 3)), r"\(2, 2\)"),
        (rc.score_to_image2d, np.zeros((4, 4)), "3-D"),
        (rc.descriptor_to_matrix, np.zeros((2, 2, 2)), "1-D or 2-D"),
    ])
    def test_shape_mismatch_rejected(self, fn, bad, msg):
        with pytest.raises(ValueError, match=msg):
            fn(bad)

    def test_zero_length_normal_rejected(self):
        with pytest.raises(ValueError, match="zero-length"):
            rc.normals_to_angles(np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]))

    def test_elevation_out_of_range_rejected(self):
        """**折り返して「もっともらしく」通してはいけない**。"""
        with pytest.raises(ValueError, match=r"\[-90, 90\]"):
            rc.angles_to_normals(np.array([[0.0, 100.0]]))

    def test_shape_index_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"\[-1, 1\]"):
            rc.shape_index_to_curvature(np.array([[1.5, 1.0]]))
        with pytest.raises(ValueError, match=">= 0"):
            rc.shape_index_to_curvature(np.array([[0.5, -1.0]]))

    def test_small_input_cannot_request_a_huge_allocation(self):
        """小さい入力から**内部割当だけ巨大**になる形を止める。"""
        kp = np.array([[1.0, 1.0]])
        with pytest.raises(ValueError, match="MAX_ELEMENTS"):
            rc.keypoints_to_image2d(kp, shape=(40000, 40000))
        with pytest.raises(ValueError, match="MAX_ELEMENTS"):
            rc.pairs_to_image2d(np.zeros((2, 2)), shape=(2 ** 16, 2 ** 16))
        g = rc.points_to_gaussians(np.random.default_rng(0).random((4, 3)))
        with pytest.raises(ValueError, match="MAX_ELEMENTS"):
            rc.gaussians_to_voxel(g, shape=(1024, 1024, 1024))
        with pytest.raises(ValueError, match="MAX_ELEMENTS"):
            rc.indices_to_labels(np.array([10 ** 12]))

    def test_out_of_raster_keypoints_are_not_silently_dropped(self):
        with pytest.raises(ValueError, match="outside"):
            rc.keypoints_to_image2d(np.array([[3.0, 3.0], [99.0, 3.0]]), shape=(16, 16))

    def test_dense_and_scattered_flow_do_not_cross(self):
        """同じ ``flow`` 型名の下の別物を、受け側で必ず選ばせる。"""
        dense = np.zeros((3, 4, 5, 6))
        scattered = np.zeros((7, 3))
        with pytest.raises(ValueError, match="DENSE"):
            rc.flow_magnitude(scattered)
        with pytest.raises(ValueError, match="DENSE"):
            rc.flow_to_rgbimage(scattered)
        with pytest.raises(ValueError, match="SCATTERED"):
            rc.flow_speed(dense)
        with pytest.raises(ValueError, match="SCATTERED"):
            rc.flow_apply(np.zeros((4, 3)), dense)

    def test_mismatched_pair_tuple_rejected(self):
        """``stat_histogram`` の (10,) と (11,) は「対」ではない。"""
        with pytest.raises(ValueError, match="equal length"):
            rc.pairs_to_signal((np.zeros(10), np.zeros(11)))

    def test_zernike_dict_descriptor_rejected_with_a_reason(self):
        with pytest.raises(ValueError, match="fit_zernike"):
            rc.descriptor_to_matrix({(0, 0): 0.5, (1, 1): 0.2})

    def test_gaussians_key_and_shape_checks(self):
        with pytest.raises(ValueError, match="missing"):
            rc.gaussians_to_points({"mu": np.zeros((3, 3))})
        with pytest.raises(ValueError, match="to match mu"):
            rc.gaussians_to_points({"mu": np.zeros((3, 3)), "sigma": np.ones(2),
                                    "w": np.ones(3)})
        with pytest.raises(ValueError, match="sigma must be > 0"):
            rc.gaussians_to_points({"mu": np.zeros((3, 3)), "sigma": np.zeros(3),
                                    "w": np.ones(3)})

    def test_constant_volume_has_no_correlation_peak(self):
        with pytest.raises(ValueError, match="constant volume"):
            rc.correlation_score(np.ones((8, 8, 8)), np.ones((8, 8, 8)))

    def test_negative_rate_and_bad_gate_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            rc.countrate_to_counts(np.array([-1.0]))
        with pytest.raises(ValueError, match="> 0 s"):
            rc.countrate_to_counts(np.array([1.0]), gate_s=0.0)

    def test_out_of_range_indices_rejected(self):
        with pytest.raises(ValueError, match="out of range"):
            rc.select_points(np.zeros((4, 3)), np.array([0, 9]))
        with pytest.raises(ValueError, match="non-negative"):
            rc.indices_to_labels(np.array([-1, 2]))

    def test_all_background_labels_rejected(self):
        with pytest.raises(ValueError, match="background"):
            rc.labels_to_indices(np.zeros((4, 4)))

    def test_empty_image_extraction_rejected(self):
        with pytest.raises(ValueError, match="no pixel exceeds"):
            rc.keypoints_from_image2d(np.zeros((8, 8)))

    def test_bad_slice_index_and_scale_rejected(self):
        f = np.zeros((3, 4, 5, 6))
        f[0, 0, 0, 0] = 1.0
        with pytest.raises(ValueError, match="within"):
            rc.flow_to_rgbimage(f, index=9)
        with pytest.raises(ValueError, match="> 0"):
            rc.flow_to_rgbimage(f, scale=0.0)


# --------------------------------------------------------------------------- #
# 5. 敵対的検証 —— 「例外が出る」でなく「黙って間違う」を狙う                     #
# --------------------------------------------------------------------------- #
class TestAdversarial:
    """自分の実装が **もっともらしく間違う** 経路を先に潰す。"""

    def test_shape_index_does_not_divide_by_zero_at_umbilics(self):
        """教科書式 ``atan((k1+k2)/(k1-k2))`` なら NaN が出る入力を通す。"""
        k = np.array([[2.0, 2.0], [0.0, 0.0], [-3.0, -3.0]])
        s = rc.curvature_to_shape_index(k)
        assert np.all(np.isfinite(s))
        assert np.allclose(s[:, 0], [1.0, 0.0, -1.0], atol=1e-12)
        assert np.allclose(rc.shape_index_to_curvature(s), k, atol=1e-12)

    def test_curvature_scalar_input_is_refused_not_guessed(self):
        """(N,) の単独曲率を「もう一方は 0」と決めつけると黙って間違う。"""
        with pytest.raises(ValueError, match=r"\(N, 2\)"):
            rc.curvature_to_shape_index(np.array([0.1, 0.2, 0.3]))
        # ただし統計だけなら (N,) でも意味があるので、そちらは通す
        t = rc.curvature_to_table(np.array([0.1, 0.2, 0.3]))
        assert t["kind"] == "scalar"

    def test_float_to_index_cast_cannot_corrupt_silently(self):
        """★実バグの回帰テスト(敵対的な型スイープで見つけた)。

        ``np.asarray(nan, dtype=int64)`` は例外を出さず INT_MIN を返し、
        キャスト**後**は ``dtype.kind == 'i'`` なので非有限検査を素通りする。
        3.7 のような非整数も黙って 3 に切り詰まり、**添字が 1 ずれた結果が
        例外もなく返る**。いまはキャストの前に生の値を見る。
        """
        for bad in (np.array([1.0, np.nan]), np.array([1.0, np.inf])):
            with pytest.raises(ValueError, match="non-finite"):
                rc.indices_to_labels(bad)
        with pytest.raises(ValueError, match="whole numbers"):
            rc.indices_to_labels(np.array([1.0, 3.7]))
        with pytest.raises(ValueError, match="whole numbers"):
            rc.select_points(np.zeros((8, 3)), np.array([0.0, 2.5]))
        # 整数値の float はそのまま通す(3.0 は 3 として正しい)
        assert np.array_equal(rc.indices_to_labels(np.array([1.0, 3.0])),
                              np.array([0, 1, 0, 1]))

    def test_matrix_to_descriptor_asymmetry_is_deliberate(self):
        """(1,n) だけ 1-D へ戻す非対称が無いと往復が静かに形を変える。"""
        assert rc.matrix_to_descriptor(np.zeros((1, 5))).shape == (5,)
        assert rc.matrix_to_descriptor(np.zeros((2, 5))).shape == (2, 5)

    def test_one_row_descriptor_ambiguity_is_documented_not_hidden(self):
        """★塞げない穴を**塞がずに固定**する。

        元から (1, n) の 2-D だった記述子は往復で (n,) になる。(1,n) の行列は
        「1-D 記述子を包んだもの」と「行 1 本の記述子束」を区別できないので、
        これは実装の粗さではなく**表現の情報量そのもの**。値は全て保存される
        (損失は「行が 1 本だった」というメタ情報のみ)ことを固定しておく。
        """
        d = np.arange(7.0).reshape(1, 7)
        back = rc.matrix_to_descriptor(rc.descriptor_to_matrix(d))
        assert back.shape == (7,), "the ambiguity is real; this test records it"
        assert np.array_equal(back, d.reshape(-1)), "but no value may be lost"

    def test_pairs_to_signal_silently_drops_x_and_table_says_so(self):
        """非等間隔の x を持つ対は ``signal`` へ落とすと位置情報が消える。

        落とすこと自体は型の定義どおりなので例外にしない。代わりに
        ``pairs_to_table`` が ``x_uniform=False`` を必ず出し、**判別できる**
        ようにしてある(判別できない損失こそが嘘になる)。
        """
        p = np.stack([np.array([0.0, 1.0, 5.0, 5.5]), np.arange(4.0)], 1)
        assert rc.pairs_to_table(p)["x_uniform"] is False
        assert "x_step" not in rc.pairs_to_table(p)
        q = np.stack([np.arange(0.0, 8.0, 2.0), np.arange(4.0)], 1)
        assert rc.pairs_to_table(q)["x_uniform"] is True
        assert rc.pairs_to_table(q)["x_step"] == pytest.approx(2.0)
        assert np.array_equal(rc.pairs_to_signal(p), rc.pairs_to_signal(q))  # 見分けが付かない

    def test_egi_uses_equal_solid_angle_not_equal_degrees(self):
        """仰角を度で等分すると「極に面が集中している」という嘘の山が立つ。

        一様な球面分布を入れたとき、等立体角なら全 bin がほぼ同数になる。
        度で等分した実装なら極の bin が数分の 1 になる —— それを反証にする。
        """
        rng = np.random.default_rng(7)
        v = _unit(rng.standard_normal((200000, 3)))
        egi = rc.normals_to_egi(v, n_az=36, n_el=18)
        per_bin = egi.sum() / egi.size
        rows = egi.sum(axis=1)                       # 仰角ごとの合計
        assert float(rows.max() / rows.min()) < 1.15, \
            f"elevation bins are not equal-solid-angle: {rows.min()} .. {rows.max()}"
        assert abs(float(egi.mean()) - per_bin) < 1e-9

    def test_correlation_is_circular_and_says_so(self):
        """巡回相関なので端は巻き込む。**打ち切り相関だと思うと誤読する**。"""
        n = 16
        a = np.zeros((n, n, n))
        a[1, 1, 1] = 1.0
        b = np.zeros((n, n, n))
        b[n - 1, 1, 1] = 1.0                          # -2 のシフト = 巡回で n-2
        assert rc.score_to_position(rc.correlation_score(a, b)) == (float(n - 2), 0.0, 0.0)

    def test_duplicate_points_fail_closed_instead_of_a_sentinel_sigma(self):
        """★実バグの回帰テスト(**黙って NaN を返していた**)。

        最初の実装は重複点の sigma を ``np.finfo(float).tiny`` = 2.2e-308 で
        埋めていた。``sigma > 0`` は満たすので検査も通るが、
        ``gaussians_to_voxel`` の ``sigma ** 3`` が**アンダーフローで 0** になり、
        0 除算で体積の一部が NaN になる —— 例外もエラーメッセージも出ない。
        「0 を避ける番兵」が「下流で NaN を作る値」だったという、
        変換 op が黙って間違う典型。いまは fail-closed。
        """
        with pytest.raises(ValueError, match="spacing is 0"):
            rc.points_to_gaussians(np.zeros((8, 3)))
        # 部分的な重複は通る(全近傍が一致した点だけが問題)
        p = np.concatenate([np.zeros((2, 3)), np.array([[1.0, 0.0, 0.0]])])
        g = rc.points_to_gaussians(p, k=2)
        assert np.all(g["sigma"] > 0.0)
        assert np.all(np.isfinite(rc.gaussians_to_voxel(g, shape=(8, 8, 8))))

    def test_unrepresentable_sigma_is_refused_not_turned_into_nan(self):
        g = {"mu": np.zeros((1, 3)), "sigma": np.array([1e-200]), "w": np.array([1.0])}
        with pytest.raises(ValueError, match="too small"):
            rc.gaussians_to_voxel(g, shape=(8, 8, 8))

    def test_flow_rgb_hue_covers_the_wheel_and_zero_is_black(self):
        """色相環が本当に一周するか(半分しか使っていない実装は「それらしく」見える)。"""
        n = 32
        yy, xx = np.mgrid[0:n, 0:n].astype(float) - (n - 1) / 2.0
        f = np.zeros((3, 1, n, n))
        f[1, 0], f[2, 0] = yy, xx
        rgbimg = rc.flow_to_rgbimage(f, index=0)
        assert rgbimg.shape == (n, n, 3)
        assert np.all((rgbimg >= 0.0) & (rgbimg <= 1.0))
        # 中央 (速さ 0) は黒
        assert float(rgbimg[n // 2, n // 2].max()) < 0.05
        # 4 象限すべてで支配的なチャンネルが違う = 色相が一周している
        corners = [rgbimg[2, 2], rgbimg[2, -3], rgbimg[-3, 2], rgbimg[-3, -3]]
        assert len({int(np.argmax(c)) for c in corners}) >= 3

    def test_conversion_edges_actually_open_the_dead_ends(self):
        """袋小路だった型に、本当に出口ができたか(台帳レベルで機械確認)。"""
        opened = {a for a, _ in opsreprconv.conversion_edges()}
        for t in ("pairs", "indices", "curvature", "descriptor", "keypoints",
                  "normals", "position", "flow", "gaussians", "score",
                  "cscalar", "countrate", "angle", "shift", "rot_scale", "deformation"):
            assert t in opened, f"{t} still has no single-input conversion out"

    def test_no_new_type_vocabulary_was_invented(self):
        """既存語彙だけで書けているか(新語を足すなら理由が要る、という規律)。"""
        import chain_fuzz
        known = set()
        for _, _, ins, out, _ in chain_fuzz.catalog():
            known.update(ins)
            known.add(out)
        for name, meta in opsreprconv.OPSREPRCONV.items():
            for t in list(meta["in"]) + [meta["out"]]:
                assert t in known, f"{name} introduces a new type '{t}' without justification"
