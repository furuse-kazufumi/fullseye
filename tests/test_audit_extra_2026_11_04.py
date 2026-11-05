"""Regression gates for the external audit, round 2 (E1-E4, I1-I3, G1-G3, 2026-11-04).

Each test states the invariant the report showed broken, checked against an oracle that does
not share code with the path under test (stdlib zipfile, a closed-form point distance, the
plain ``run`` path, Python ints instead of NumPy inference ...). The sibling sweeps found
while fixing each item have their own tests next to it.
"""
from __future__ import annotations

import io
import math
import zipfile

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# E1  pipeline_evolve / evolve_params: max_len holds after mutation            #
# --------------------------------------------------------------------------- #
def test_e1_evolve_respects_max_len_zero_and_one():
    import pipeline_evolve as pe
    task = pe.make_denoise_task(n=80, n_outliers=10)
    r0 = pe.evolve(task, pop=8, gens=3, max_len=0, seed=1)
    assert r0["best"] == ()
    r1 = pe.evolve(task, pop=10, gens=6, max_len=1, seed=0)
    assert len(r1["best"]) <= 1


@pytest.mark.parametrize("max_len", [0, 1, 2, 4])
def test_e1_mutate_never_grows_past_max_len(max_len):
    import pipeline_evolve as pe
    task = pe.make_denoise_task(n=40, n_outliers=4)
    rng = np.random.default_rng(3)
    loops = pe._self_loop_ops(task.goal_type)
    for _ in range(300):
        chain = tuple(loops[int(rng.integers(len(loops)))] for _ in range(max_len))
        assert len(pe.mutate(chain, rng, task, max_len=max_len)) <= max_len


@pytest.mark.parametrize("max_len", [0, 1, 3])
def test_e1_sibling_evolve_params_mutate_respects_max_len(max_len):
    import evolve_params as ep
    rng = np.random.default_rng(5)
    for _ in range(300):
        chain = tuple(ep.random_gene(rng) for _ in range(max_len))
        assert len(ep.mutate(chain, rng, max_len=max_len)) <= max_len


def test_e1_sibling_evolve_params_result_respects_max_len():
    import evolve_params as ep
    import pipeline_evolve as pe
    task = pe.make_denoise_task(n=60, n_outliers=6)
    r = ep.evolve_params(task, pop=8, gens=3, max_len=1, seed=0)
    assert len(r["best"]) <= 1


# --------------------------------------------------------------------------- #
# E2  engine stage cache: the input key sees every byte                       #
# --------------------------------------------------------------------------- #
def test_e2_cache_key_sees_a_single_centre_pixel():
    from engine import FullseyeEngine, StageCache, _input_hash
    a = np.zeros((1024, 1024))
    b = a.copy()
    b[512, 512] = 1.0
    assert _input_hash(a) != _input_hash(b)
    eng = FullseyeEngine(["identity"])
    cache = StageCache()
    eng.run_cached(a, cache)
    got = eng.run_cached(b, cache)
    assert got[512, 512] == 1.0


@pytest.mark.parametrize("where", [0, 1, (1 << 20) - 1, 1 << 20, 3 << 19, (2 << 20) - 1, -1])
def test_e2_every_byte_position_changes_the_key(where):
    from engine import _input_hash
    a = np.zeros(3 << 17, dtype=np.float64)        # 3 MiB: the old key read only the first and last MiB
    assert a.view(np.uint8).size == 3 << 20
    b = a.copy()
    b.view(np.uint8)[where] ^= 1
    assert _input_hash(a) != _input_hash(b)


def test_e2_key_separates_shape_and_dtype_with_equal_bytes():
    from engine import _input_hash
    a = np.zeros((4, 8))
    assert _input_hash(a) != _input_hash(a.reshape(8, 4))
    assert _input_hash(a) != _input_hash(a.view(np.int64))


# --------------------------------------------------------------------------- #
# E3  generated Python carries the knobs at full precision                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method,fn_suffix", [("to_python", ""), ("to_python_staged", "_staged")])
def test_e3_exported_python_runs_the_same_knobs(method, fn_suffix):
    from engine import FullseyeEngine
    eng = FullseyeEngine([("scale_clip", 0.123456, 0.654321), ("gamma", 0.1 + 0.2, 0.5)], name="probe")
    ns = {}
    exec(getattr(eng, method)(), ns)
    x = np.full((2, 2), 0.25)
    assert np.array_equal(ns["probe" + fn_suffix](x), eng.run(x))


# --------------------------------------------------------------------------- #
# E4  run_cached refuses what run refuses                                      #
# --------------------------------------------------------------------------- #
def test_e4_run_cached_refuses_a_sort_mismatch_like_run():
    from engine import FullseyeEngine
    eng = FullseyeEngine.from_ops("otsu,invert")
    x = np.linspace(0, 1, 64).reshape(8, 8)
    with pytest.raises(ValueError) as plain:
        eng.run(x)
    with pytest.raises(ValueError) as cached:
        eng.run_cached(x)
    assert str(cached.value) == str(plain.value)


def test_e4_run_cached_refuses_a_nan_knob_like_run():
    from engine import FullseyeEngine
    eng = FullseyeEngine([("threshold", float("nan"), 0.5)])
    x = np.linspace(0, 1, 64).reshape(8, 8)
    with pytest.raises(ValueError):
        eng.run(x)
    with pytest.raises(ValueError):
        eng.run_cached(x)


@pytest.mark.parametrize("ops", ["gaussian,sobel_amp,otsu", "gaussian,invert", "otsu"])
def test_e4_run_cached_equals_run_including_uint8_entry(ops):
    from engine import FullseyeEngine, StageCache
    eng = FullseyeEngine.from_ops(ops)
    rng = np.random.default_rng(0)
    for img in (rng.random((24, 24)), (rng.random((24, 24)) * 255).astype(np.uint8)):
        cache = StageCache()
        first = eng.run_cached(img, cache)
        again = eng.run_cached(img, cache)            # served from the cache
        ref = eng.run(img)
        assert np.array_equal(np.asarray(first), np.asarray(ref))
        assert np.array_equal(np.asarray(again), np.asarray(ref))


# --------------------------------------------------------------------------- #
# I1  readable typed JSON keeps every integer                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dtype,values", [
    (np.uint64, [0, 2**63 + 1]),
    (np.uint64, [2**64 - 1, 2**53 + 1, 1]),
    (np.int64, [-(2**63), 2**63 - 1, -(2**53) - 1]),
    (np.int64, [[1, 2**62 + 3], [-5, 7]]),
])
def test_i1_readable_integer_lists_round_trip_exactly(dtype, values):
    from fullseye import jsonio as J
    original = np.array(values, dtype=dtype)
    back, _ = J.from_json(J.to_json(original, "signal" if original.ndim == 1 else "matrix",
                                    readable=True))
    assert back.dtype == original.dtype
    assert back.tolist() == original.tolist()            # Python ints: no float comparison


@pytest.mark.parametrize("data", [[0, 1.5], [0, 2.0**60], [0, float("nan")], [0, "1"], [0, [1]]])
def test_i1_integer_lists_refuse_values_that_are_not_exact_ints(data):
    from fullseye import jsonio as J
    env = {"fullseye_sort": "signal", "version": 1,
           "payload": {"encoding": "list", "dtype": "int64", "shape": [2], "data": data}}
    with pytest.raises(ValueError):
        J.from_jsonable(env)


@pytest.mark.parametrize("dtype,data", [("uint8", [0, 256]), ("uint64", [-1, 0]),
                                        ("int64", [0, 2**63]), ("uint64", [0, 2**64])])
def test_i1_integer_lists_refuse_out_of_range(dtype, data):
    from fullseye import jsonio as J
    env = {"fullseye_sort": "signal", "version": 1,
           "payload": {"encoding": "list", "dtype": dtype, "shape": [2], "data": data}}
    with pytest.raises(ValueError):
        J.from_jsonable(env)


def test_i1_integer_lists_still_accept_small_integral_floats():
    from fullseye import jsonio as J
    env = {"fullseye_sort": "signal", "version": 1,
           "payload": {"encoding": "list", "dtype": "int64", "shape": [2], "data": [3.0, -4.0]}}
    out, _ = J.from_jsonable(env)
    assert out.dtype == np.int64 and out.tolist() == [3, -4]


def test_i1_sibling_csv_integer_column_beyond_2_53_is_not_rounded():
    import fileio
    meta = {"source": "probe", "generated_at": "2026-11-04T00:00:00+09:00", "coordinate_meaning": "none"}
    big = [1730000000123456789, 2**53 + 1, 0]
    text = fileio.table_write_csv({"t_ns": np.array(big, dtype=np.int64), "x": [0.5, 1.5, 2.5]},
                                  units={"t_ns": "ns", "x": "mm"}, meta=meta)
    back = fileio.table_read_csv(text)["columns"]
    assert back["t_ns"].tolist() == big
    assert back["x"].dtype == np.float64 and back["x"].tolist() == [0.5, 1.5, 2.5]


def test_i1_sibling_csv_small_integer_column_stays_float64():
    import fileio
    meta = {"source": "probe", "generated_at": "2026-11-04T00:00:00+09:00", "coordinate_meaning": "none"}
    text = fileio.table_write_csv({"n": np.array([1, 2, 3])}, units={"n": "1"}, meta=meta)
    back = fileio.table_read_csv(text)["columns"]["n"]
    assert back.dtype == np.float64 and back.tolist() == [1.0, 2.0, 3.0]


# --------------------------------------------------------------------------- #
# I2  NRRD: the header ends at the first blank line, CRLF or LF                #
# --------------------------------------------------------------------------- #
def _nrrd_lf_and_crlf():
    import fileio
    original = np.full((2, 1), 10, dtype=np.uint8)      # the raw body is b"\n\n"
    payload = fileio.nrrd_write(original, meta={"space_directions": np.eye(2), "space_unit": "mm",
                                                "space_origin": [0, 0]}, encoding="raw")
    header, body = payload.split(b"\n\n", 1)
    crlf = header.replace(b"\n", b"\r\n") + b"\r\n\r\n" + body
    return original, payload, crlf


def test_i2_crlf_nrrd_with_newline_bytes_in_the_body_reads():
    import fileio
    original, payload, crlf = _nrrd_lf_and_crlf()
    for blob in (payload, crlf):
        arr, meta = fileio.nrrd_read(blob)
        assert arr.dtype == original.dtype and np.array_equal(arr, original)
        assert meta["space_unit"] == "mm"


def test_i2_crlf_body_with_crlfcrlf_bytes_inside_reads():
    import fileio
    original = np.array([[13], [10], [13], [10]], dtype=np.uint8)   # body = b"\r\n\r\n"
    payload = fileio.nrrd_write(original, meta={"space_directions": np.eye(2), "space_unit": "mm",
                                                "space_origin": [0, 0]}, encoding="raw")
    header, body = payload.split(b"\n\n", 1)
    crlf = header.replace(b"\n", b"\r\n") + b"\r\n\r\n" + body
    for blob in (payload, crlf):
        arr, _ = fileio.nrrd_read(blob)
        assert np.array_equal(arr, original)


def test_i2_header_without_blank_line_is_still_refused():
    import fileio
    _, payload, _ = _nrrd_lf_and_crlf()
    header = payload.split(b"\n\n", 1)[0]
    with pytest.raises(ValueError, match="blank-line"):
        fileio.nrrd_read(header + b"\n")


# --------------------------------------------------------------------------- #
# I3  ZIP archive_create honours the level                                     #
# --------------------------------------------------------------------------- #
def _member_size(blob, name):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        assert archive.read(name) == b"abcde" * 100
        return archive.getinfo(name).compress_size


@pytest.mark.parametrize("level", [0, 1, 6, 9])
def test_i3_zip_level_matches_the_stdlib_control(level):
    import fileio
    data = b"abcde" * 100
    ref = io.BytesIO()
    with zipfile.ZipFile(ref, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level) as archive:
        archive.writestr("a.txt", data)
    expected = _member_size(ref.getvalue(), "a.txt")
    got = _member_size(fileio.archive_create({"a.txt": data}, "zip", level=level), "a.txt")
    assert got == expected


def test_i3_zip_levels_give_different_archives():
    import fileio
    data = b"abcde" * 100
    blobs = {lv: fileio.archive_create({"a.txt": data}, "zip", level=lv) for lv in (0, 1, 9)}
    assert len(set(blobs.values())) == 3
    assert _member_size(blobs[0], "a.txt") > len(data)            # level 0 = stored deflate blocks


# --------------------------------------------------------------------------- #
# G1  points3d RMSE is per point under every neutral option                    #
# --------------------------------------------------------------------------- #
_PKW = dict(nan_policy="raise", unit="mm", reduction="mean", empty="raise", domain="points3d")


def test_g1_points3d_rmse_neutral_options_agree():
    from fullseye.evaluation.metrics import rmse
    a = np.array([[1.0, 2.0, 2.0]])
    b = np.zeros_like(a)
    oracle = 3.0
    got = {
        "default": rmse(a, b, **_PKW),
        "all_true_mask": rmse(a, b, mask=np.ones_like(a, dtype=bool), **_PKW),
        "unit_weights": rmse(a, b, weights=np.ones_like(a), **_PKW),
        "omit": rmse(a, b, **dict(_PKW, nan_policy="omit")),
        "propagate": rmse(a, b, **dict(_PKW, nan_policy="propagate")),
    }
    assert all(math.isclose(v, oracle, rel_tol=0, abs_tol=1e-12) for v in got.values()), got


def test_g1_points3d_rmse_mask_weights_omit_select_whole_points():
    from fullseye.evaluation.metrics import rmse
    a = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 1.0], [np.nan, 1.0, 1.0]])
    b = np.zeros_like(a)
    d2 = np.array([25.0, 1.0])
    rows = np.array([[True] * 3, [True] * 3, [False] * 3])
    assert rmse(a, b, mask=rows, **_PKW) == pytest.approx(np.sqrt(d2.mean()), abs=1e-12)
    assert rmse(a, b, **dict(_PKW, nan_policy="omit")) == pytest.approx(np.sqrt(d2.mean()), abs=1e-12)
    w = np.array([[1.0] * 3, [3.0] * 3, [1.0] * 3])
    assert rmse(a, b, mask=rows, weights=w, **_PKW) == pytest.approx(
        np.sqrt((25.0 * 1 + 1.0 * 3) / 4.0), abs=1e-12)
    assert rmse(a, b, mask=rows, **dict(_PKW, reduction="sum")) == pytest.approx(np.sqrt(26.0), abs=1e-12)


def test_g1_points3d_rmse_refuses_a_mask_or_weights_that_split_a_point():
    from fullseye.evaluation.metrics import rmse
    a = np.ones((2, 3))
    b = np.zeros_like(a)
    with pytest.raises(ValueError, match="whole points"):
        rmse(a, b, mask=np.array([[True, False, True], [True, True, True]]), **_PKW)
    with pytest.raises(ValueError, match="same weight"):
        rmse(a, b, weights=np.array([[1.0, 2.0, 1.0], [1.0, 1.0, 1.0]]), **_PKW)


def test_g1_points3d_rmse_matches_rmse_correspondence_oracle():
    import metrics3d
    from fullseye.evaluation.metrics import rmse
    rng = np.random.default_rng(1)
    a = rng.normal(size=(50, 3))
    b = rng.normal(size=(50, 3))
    ref = metrics3d.rmse_correspondence(a, b)
    assert rmse(a, b, mask=np.ones_like(a, bool), **_PKW) == pytest.approx(ref, abs=1e-12)
    assert rmse(a, b, weights=np.full_like(a, 2.5), **_PKW) == pytest.approx(ref, abs=1e-12)


# --------------------------------------------------------------------------- #
# G2  weighted IoU / Dice after omitting a NaN weight                          #
# --------------------------------------------------------------------------- #
_OKW = dict(nan_policy="omit", unit="1", reduction="mean", empty="raise", domain="array")


@pytest.mark.parametrize("name", ["iou", "dice"])
def test_g2_overlap_omit_nan_weight(name):
    from fullseye.evaluation import metrics as M
    metric = getattr(M, name)
    oracle = metric([True], [True], weights=[1.0], **_OKW)
    assert oracle == 1.0
    assert metric([True, True], [True, False], weights=[1.0, np.nan], **_OKW) == oracle


@pytest.mark.parametrize("name", ["iou", "dice"])
def test_g2_overlap_all_weights_omitted_is_empty(name):
    from fullseye.evaluation import metrics as M
    metric = getattr(M, name)
    with pytest.raises(ValueError, match="empty"):
        metric([True, False], [True, True], weights=[np.nan, np.inf], **_OKW)
    assert math.isnan(metric([True, False], [True, True], weights=[np.nan, np.inf], **dict(_OKW, empty="nan")))


@pytest.mark.parametrize("name", ["rmse", "mae"])
def test_g2_sibling_numeric_omit_nan_weight_matches_dropping_the_element(name):
    from fullseye.evaluation import metrics as M
    metric = getattr(M, name)
    kw = dict(_OKW, unit="mm")
    ref = metric([1.0, 2.0], [0.0, 0.0], weights=[1.0, 3.0], **kw)
    assert metric([1.0, 2.0, 9.0], [0.0, 0.0, 0.0], weights=[1.0, 3.0, np.nan], **kw) == ref


# --------------------------------------------------------------------------- #
# G3  ZYX Euler round trip at exact gimbal lock                                #
# --------------------------------------------------------------------------- #
def _rand_rot(rng):
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def test_g3_exact_gimbal_lock_round_trip():
    import transforms as T
    H = np.array([[0., 1., 0., 0.], [0., 0., -1., 0.], [-1., 0., 0., 0.], [0., 0., 0., 1.]])
    np.testing.assert_allclose(T.pose_to_hom_mat3d(T.hom_mat3d_to_pose(H)), H, rtol=0, atol=1e-12)


def _exact_gimbal(s, rx, rz):
    """Rz(rz) . Ry(s * 90 deg) . Rx(rx) with the Ry block exactly 0 / +-1 (cos(ry) == 0 in floats)."""
    cx, sx, cz, sz = math.cos(rx), math.sin(rx), math.cos(rz), math.sin(rz)
    Rx = np.array([[1.0, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[0.0, 0, s], [0, 1, 0], [-s, 0, 0]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1.0]])
    H = np.eye(4)
    H[:3, :3] = Rz @ Ry @ Rx
    H[:3, 3] = [1.0, 2.0, 3.0]
    assert H[0, 0] == 0.0 and H[1, 0] == 0.0 and abs(H[2, 0]) == 1.0
    return H


@pytest.mark.parametrize("s", [1.0, -1.0])
@pytest.mark.parametrize("rx,rz", [(0.0, 0.0), (0.7, 0.0), (0.0, -1.1), (0.4, 2.5), (-3.0, 3.0)])
def test_g3_both_gimbal_signs_round_trip(s, rx, rz):
    import transforms as T
    H = _exact_gimbal(s, rx, rz)
    back = T.pose_to_hom_mat3d(T.hom_mat3d_to_pose(H))
    np.testing.assert_allclose(back, H, rtol=0, atol=1e-12)


def test_g3_generic_rotations_still_round_trip():
    import transforms as T
    rng = np.random.default_rng(2)
    for _ in range(200):
        H = np.eye(4)
        H[:3, :3] = _rand_rot(rng)
        np.testing.assert_allclose(T.pose_to_hom_mat3d(T.hom_mat3d_to_pose(H)), H, rtol=0, atol=1e-12)


@pytest.mark.parametrize("s", [1.0, -1.0])
@pytest.mark.parametrize("rx,rz", [(0.0, 0.0), (0.5, 0.0), (0.0, 0.8), (0.3, -1.2)])
def test_g3_sibling_raytrace3d_euler_zyx_round_trips_at_gimbal_lock(s, rx, rz):
    import raytrace3d as R3
    import transforms as T
    H = _exact_gimbal(s, rx, rz)
    a, b, g = (math.radians(v) for v in R3._euler_zyx(H[:3, :3]))
    back = T.pose_to_hom_mat3d([a, b, g, 1.0, 2.0, 3.0])
    np.testing.assert_allclose(back, H, rtol=0, atol=1e-12)


def test_g3_sibling_raytrace3d_euler_zyx_generic_unchanged():
    import raytrace3d as R3
    import transforms as T
    rng = np.random.default_rng(4)
    for _ in range(100):
        R = _rand_rot(rng)
        a, b, g = (math.radians(v) for v in R3._euler_zyx(R))
        np.testing.assert_allclose(T.pose_to_hom_mat3d([a, b, g, 0, 0, 0])[:3, :3], R, rtol=0, atol=1e-12)
