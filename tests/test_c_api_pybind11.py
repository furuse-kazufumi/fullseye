# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Differential and refusal gates for the pybind11 C ABI / pybind11 C ABI の差分・拒否門。"""
from __future__ import annotations

import ctypes as C
import gc
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

import fslib
import fullseye

ROOT = Path(__file__).resolve().parents[1]
FS_OK = 0
FS_E_INVALID_ARG = 1
FS_E_TYPE = 2
FS_E_SHAPE = 3
FS_E_RANGE = 4
FS_E_NO_PYTHON = 10
FS_E_UNKNOWN_OP = 11
FS_E_BAD_PARAMS = 12
FS_E_UNSUPPORTED = 6
FS_VALUE_IMAGE = 1
FS_VALUE_REGION = 2
FS_VALUE_OBJECTSET = 3
FS_VALUE_FEATURE = 4
FS_VALUE_COLOR = 6
FS_VALUE_VOLUME = 7
FS_VALUE_CONTOUR = 8
FS_VALUE_POINTS = 9
MIN_CALLABLE_C_API_OPS = 805


class InitOptions(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("runtime_root", C.c_char_p),
                ("python_home", C.c_char_p), ("flags", C.c_uint32),
                ("abi_major", C.c_uint32), ("abi_minor", C.c_uint32),
                ("runtime_root_bytes", C.c_size_t), ("python_home_bytes", C.c_size_t)]


class ImageView(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("data", C.c_void_p),
                ("data_bytes", C.c_size_t), ("width", C.c_int64),
                ("height", C.c_int64), ("row_stride_bytes", C.c_int64),
                ("dtype", C.c_int), ("range_lo", C.c_double), ("range_hi", C.c_double)]


class ArrayView(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("data", C.c_void_p), ("data_bytes", C.c_size_t),
                ("ndim", C.c_uint32), ("shape", C.c_int64 * 4),
                ("stride_bytes", C.c_int64 * 4), ("dtype", C.c_int)]


class ContourPart(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("points", ArrayView), ("closed", C.c_uint32)]


class ContourView(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("width", C.c_int64), ("height", C.c_int64),
                ("contours", C.POINTER(ContourPart)), ("contours_bytes", C.c_size_t),
                ("contour_count", C.c_size_t), ("contour_stride_bytes", C.c_size_t)]


class Input(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result", C.c_void_p), ("result_index", C.c_size_t)]


class InputN(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result_id", C.c_uint64), ("result_index", C.c_size_t),
                ("array", ArrayView), ("feature", C.c_double),
                ("contour", ContourView), ("points", ArrayView)]


class Run(C.Structure):
    _fields_ = [("row", C.c_int32), ("col_begin", C.c_int32), ("col_end", C.c_int32)]


def _library_path() -> Path:
    explicit = os.environ.get("FULLSEYE_C_API_LIBRARY")
    if explicit:
        return Path(explicit)
    names = ("libfullseye-0.dll", "fullseye-0.dll", "libfullseye.so", "libfullseye.dylib")
    for folder in (ROOT / "build-c-api", ROOT / "build", ROOT / "build-c-api" / "Release"):
        for name in names:
            path = folder / name
            if path.is_file():
                return path
    pytest.skip("build the optional native SDK before running this gate")


def _bind(lib):
    lib.fs_abi_version.argtypes = [C.POINTER(C.c_int32), C.POINTER(C.c_int32)]
    lib.fs_abi_version.restype = C.c_int
    lib.fs_runtime_create.argtypes = [C.POINTER(InitOptions), C.POINTER(C.c_void_p)]
    lib.fs_runtime_create.restype = C.c_int
    lib.fs_runtime_destroy.argtypes = [C.c_void_p]
    lib.fs_call_id_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(InputN), C.c_size_t,
                              C.c_void_p, C.c_size_t, C.POINTER(C.c_uint64)]
    lib.fs_call_id_n.restype = C.c_int
    lib.fs_find_ops_json_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                        C.POINTER(C.c_void_p), C.POINTER(C.c_size_t)]
    lib.fs_find_ops_json_n.restype = C.c_int
    lib.fs_free.argtypes = [C.c_void_p]
    lib.fs_free.restype = None
    lib.fs_result_release_n.argtypes = [C.c_uint64]
    lib.fs_result_release_n.restype = C.c_int
    lib.fs_result_kind_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_int)]
    lib.fs_result_kind_n.restype = C.c_int
    lib.fs_result_image_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(ImageView)]
    lib.fs_result_image_n.restype = C.c_int
    lib.fs_result_array_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(ArrayView)]
    lib.fs_result_array_n.restype = C.c_int
    lib.fs_result_contour_count_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_size_t)]
    lib.fs_result_contour_count_n.restype = C.c_int
    lib.fs_result_contour_shape_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_int64),
                                              C.POINTER(C.c_int64)]
    lib.fs_result_contour_shape_n.restype = C.c_int
    lib.fs_result_contour_n.argtypes = [C.c_uint64, C.c_size_t, C.c_size_t,
                                        C.POINTER(ContourPart), C.POINTER(C.c_int64),
                                        C.POINTER(C.c_int64)]
    lib.fs_result_contour_n.restype = C.c_int
    lib.fs_result_points_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(ArrayView)]
    lib.fs_result_points_n.restype = C.c_int
    lib.fs_result_region_runs_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.POINTER(Run)),
                                           C.POINTER(C.c_size_t)]
    lib.fs_result_region_runs_n.restype = C.c_int
    lib.fs_result_object_count_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_size_t)]
    lib.fs_result_object_count_n.restype = C.c_int
    lib.fs_result_object_runs_n.argtypes = [C.c_uint64, C.c_size_t, C.c_size_t,
                                           C.POINTER(C.POINTER(Run)), C.POINTER(C.c_size_t)]
    lib.fs_result_object_runs_n.restype = C.c_int
    lib.fs_result_tuple_size_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_size_t)]
    lib.fs_result_tuple_size_n.restype = C.c_int
    lib.fs_result_tuple_real_n.argtypes = [C.c_uint64, C.c_size_t, C.c_size_t, C.POINTER(C.c_double)]
    lib.fs_result_tuple_real_n.restype = C.c_int
    lib.fs_result_real_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_double)]
    lib.fs_result_real_n.restype = C.c_int
    lib.fs_last_error.argtypes = [C.c_void_p, C.c_char_p, C.c_size_t]
    lib.fs_last_error.restype = C.c_size_t
    lib.fs_test_result_id_seed_next_generation.argtypes = [C.c_uint32]
    lib.fs_test_result_id_seed_next_generation.restype = C.c_int
    lib.fs_test_result_id_pause_after_lease.argtypes = [C.c_int]
    lib.fs_test_result_id_pause_after_lease.restype = C.c_int
    lib.fs_test_result_id_wait_for_lease.argtypes = [C.c_uint32]
    lib.fs_test_result_id_wait_for_lease.restype = C.c_int
    lib.fs_test_result_id_resume_lease.argtypes = []
    lib.fs_test_result_id_resume_lease.restype = C.c_int


@pytest.fixture(scope="module")
def abi():
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    root = os.fsencode(ROOT)
    options = InitOptions(C.sizeof(InitOptions), root, None, 3, 0, 3, len(root), 0)
    runtime = C.c_void_p()
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_OK
    yield lib, runtime
    lib.fs_runtime_destroy(runtime)


def _image(array: np.ndarray, *, data_bytes=None, width=None, height=None, stride=None,
           dtype=4, lo=0.0, hi=1.0) -> InputN:
    view = ImageView(C.sizeof(ImageView), int(array.ctypes.data),
                     array.nbytes if data_bytes is None else data_bytes,
                     array.shape[1] if width is None else width,
                     array.shape[0] if height is None else height,
                     array.strides[0] if stride is None else stride, dtype, lo, hi)
    return InputN(C.sizeof(InputN), FS_VALUE_IMAGE, view, 0, 0, ArrayView(), 0.0,
                  ContourView(), ArrayView())


def _borrow(kind: int, result, index=0) -> InputN:
    return InputN(C.sizeof(InputN), kind, ImageView(), result, index, ArrayView(), 0.0,
                  ContourView(), ArrayView())


def _call(abi, op: str, inputs: list[Input], params="{}"):
    lib, runtime = abi
    result = C.c_uint64()
    array = (InputN * len(inputs))(*inputs) if inputs else None
    op_bytes, params_bytes = op.encode(), params.encode()
    status = lib.fs_call_id_n(runtime, op_bytes, len(op_bytes), array, len(inputs),
                           params_bytes, len(params_bytes), C.byref(result))
    return status, result


def _runs(lib, result, index=0):
    pointer = C.POINTER(Run)()
    count = C.c_size_t()
    assert lib.fs_result_region_runs_n(result, index, C.byref(pointer), C.byref(count)) == FS_OK
    return [(pointer[i].row, pointer[i].col_begin, pointer[i].col_end) for i in range(count.value)]


def _object_runs(lib, result, object_index):
    pointer = C.POINTER(Run)()
    count = C.c_size_t()
    assert lib.fs_result_object_runs_n(result, 0, object_index, C.byref(pointer), C.byref(count)) == FS_OK
    return [(pointer[i].row, pointer[i].col_begin, pointer[i].col_end) for i in range(count.value)]


def _tuple(lib, result, index):
    count = C.c_size_t()
    assert lib.fs_result_tuple_size_n(result, index, C.byref(count)) == FS_OK
    values = []
    for element in range(count.value):
        value = C.c_double()
        assert lib.fs_result_tuple_real_n(result, index, element, C.byref(value)) == FS_OK
        values.append(value.value)
    return values


def _typed_array(array: np.ndarray, kind: int) -> tuple[InputN, np.ndarray]:
    """Build the ABI's direct color/volume view / 色・volume の直接 ABI view を組む。"""
    values = np.ascontiguousarray(array, dtype=np.float64)
    shape = (C.c_int64 * 4)(*list(values.shape), *([0] * (4 - values.ndim)))
    strides = (C.c_int64 * 4)(*list(values.strides), *([0] * (4 - values.ndim)))
    view = ArrayView(C.sizeof(ArrayView), int(values.ctypes.data), values.nbytes, values.ndim,
                     shape, strides, 4)
    return InputN(C.sizeof(InputN), kind, ImageView(), 0, 0, view, 0.0,
                  ContourView(), ArrayView()), values


def _typed_array_with_dtype(shape, kind: int, dtype: int, numpy_dtype) -> tuple[InputN, np.ndarray]:
    """Build an oversized typed view for refusal tests / 拒否試験用の余裕ある view を組む。"""
    layout = np.empty(shape, dtype=numpy_dtype, order="C")
    values = np.ones(int(np.prod(shape)) * 2, dtype=numpy_dtype)
    full_shape = (C.c_int64 * 4)(*shape, *([0] * (4 - len(shape))))
    full_strides = (C.c_int64 * 4)(*layout.strides, *([0] * (4 - len(shape))))
    view = ArrayView(C.sizeof(ArrayView), int(values.ctypes.data), values.nbytes, len(shape),
                     full_shape, full_strides, dtype)
    return InputN(C.sizeof(InputN), kind, ImageView(), 0, 0, view, 0.0,
                  ContourView(), ArrayView()), values


def _typed_array_view(values: np.ndarray, owner: np.ndarray, kind: int) -> InputN:
    """Keep dtype and first-axis padding in a direct ABI view / dtype と第 1 軸の余白を保つ。"""
    codes = {np.dtype(np.uint8): 1, np.dtype(np.uint16): 2,
             np.dtype(np.float32): 3, np.dtype(np.float64): 4}
    shape = (C.c_int64 * 4)(*values.shape, *([0] * (4 - values.ndim)))
    strides = (C.c_int64 * 4)(*values.strides, *([0] * (4 - values.ndim)))
    view = ArrayView(C.sizeof(ArrayView), int(values.ctypes.data), owner.nbytes, values.ndim,
                     shape, strides, codes[values.dtype])
    return InputN(C.sizeof(InputN), kind, ImageView(), 0, 0, view, 0.0)


def _feature(value: float) -> InputN:
    return InputN(C.sizeof(InputN), FS_VALUE_FEATURE, ImageView(), 0, 0, ArrayView(), value,
                  ContourView(), ArrayView())


def _points(array: np.ndarray, *, dtype=4) -> tuple[InputN, np.ndarray]:
    """Build a direct (N,2)/(N,3) coordinate input / 座標入力を組む。"""
    values = np.ascontiguousarray(array, dtype=np.float64)
    shape = (C.c_int64 * 4)(values.shape[0], values.shape[1], 0, 0)
    strides = (C.c_int64 * 4)(values.strides[0], values.strides[1], 0, 0)
    view = ArrayView(C.sizeof(ArrayView), int(values.ctypes.data), values.nbytes, 2,
                     shape, strides, dtype)
    return InputN(C.sizeof(InputN), FS_VALUE_POINTS, ImageView(), 0, 0, ArrayView(), 0.0,
                  ContourView(), view), values


def _contour(value: dict) -> tuple[InputN, tuple]:
    """Build a direct contour-set input / 複数点列の contour 入力を組む。"""
    arrays = [np.ascontiguousarray(points, dtype=np.float64) for points in value["cs"]]
    parts = (ContourPart * len(arrays))()
    for index, points in enumerate(arrays):
        shape = (C.c_int64 * 4)(points.shape[0], 2, 0, 0)
        strides = (C.c_int64 * 4)(points.strides[0], points.strides[1], 0, 0)
        view = ArrayView(C.sizeof(ArrayView), int(points.ctypes.data), points.nbytes, 2,
                         shape, strides, 4)
        closed = int(points.shape[0] > 1 and np.array_equal(points[0], points[-1]))
        parts[index] = ContourPart(C.sizeof(ContourPart), view, closed)
    height, width = value["shape"]
    view = ContourView(C.sizeof(ContourView), width, height, parts, C.sizeof(parts),
                       len(parts), C.sizeof(ContourPart))
    input_value = InputN(C.sizeof(InputN), FS_VALUE_CONTOUR, ImageView(), 0, 0,
                         ArrayView(), 0.0, view, ArrayView())
    return input_value, (arrays, parts)


def _c_output(lib, result, sort: str):
    if sort == "region":
        return _runs(lib, result)
    if sort == "feature":
        value = C.c_double()
        assert lib.fs_result_real_n(result, 0, C.byref(value)) == FS_OK
        return value.value
    if sort == "image":
        view = ImageView(C.sizeof(ImageView))
        assert lib.fs_result_image_n(result, 0, C.byref(view)) == FS_OK
        return np.ctypeslib.as_array(C.cast(view.data, C.POINTER(C.c_double)),
                                     shape=(view.height * view.width,)).reshape(view.height, view.width).copy()
    if sort == "contour":
        count = C.c_size_t()
        assert lib.fs_result_contour_count_n(result, 0, C.byref(count)) == FS_OK
        width, height = C.c_int64(), C.c_int64()
        assert lib.fs_result_contour_shape_n(result, 0, C.byref(width), C.byref(height)) == FS_OK
        contours = []
        closed = []
        for contour_index in range(count.value):
            part = ContourPart(C.sizeof(ContourPart), ArrayView(C.sizeof(ArrayView)), 0)
            width, height = C.c_int64(), C.c_int64()
            assert lib.fs_result_contour_n(result, 0, contour_index, C.byref(part),
                                           C.byref(width), C.byref(height)) == FS_OK
            shape = (part.points.shape[0], part.points.shape[1])
            points = np.ctypeslib.as_array(C.cast(part.points.data, C.POINTER(C.c_double)),
                                           shape=(int(np.prod(shape)),)).reshape(shape).copy()
            contours.append(points)
            closed.append(bool(part.closed))
        return {"shape": (height.value, width.value), "cs": contours, "closed": closed}
    if sort == "points":
        view = ArrayView(C.sizeof(ArrayView))
        assert lib.fs_result_points_n(result, 0, C.byref(view)) == FS_OK
        shape = tuple(view.shape[:view.ndim])
        if shape[0] == 0:
            return np.empty(shape, dtype=np.float64)
        return np.ctypeslib.as_array(C.cast(view.data, C.POINTER(C.c_double)),
                                     shape=(int(np.prod(shape)),)).reshape(shape).copy()
    view = ArrayView(C.sizeof(ArrayView))
    assert lib.fs_result_array_n(result, 0, C.byref(view)) == FS_OK
    shape = tuple(view.shape[:view.ndim])
    return np.ctypeslib.as_array(C.cast(view.data, C.POINTER(C.c_double)),
                                 shape=(int(np.prod(shape)),)).reshape(shape).copy()


def _direct_registry(op, value):
    return fullseye.apply(value, op.name, 0.5, 0.5, coerce=False, device="cpu",
                          on_error="raise", allow_nonfinite=False)


def test_runtime_reports_abi_0_3(abi):
    """The new tail is advertised without changing the major / major を変えず 0.3 を返す。"""
    lib, _runtime = abi
    major, minor = C.c_int32(), C.c_int32()
    assert lib.fs_abi_version(C.byref(major), C.byref(minor)) == FS_OK
    assert (major.value, minor.value) == (0, 3)


def test_every_typed_c_sdk_operator_matches_direct_python_on_a_contract_probe(abi):
    """All generated callable rows traverse C and match the direct Python call exactly.

    全生成対象を既存 ``inputs_for`` 探針で C 経由・Python 直呼びの両方に通す。配列は
    byte-for-byte equality; scalar feature も同じ一回の呼出しで比較する。
    """
    from conftest import copy_input, inputs_for, requires_full_registry
    requires_full_registry()
    import ops
    from fullseye import c_api_bridge

    lib, _runtime = abi
    registry = {op.name: op for op in ops.REGISTRY}
    catalog = c_api_bridge.catalog()
    rows = [row for row in catalog["ops"] if row["callable"]]
    generated = json.loads(
        (ROOT / "fullseye" / "data" / "C_API_OPS.json").read_text(encoding="utf-8"))
    expected_count = generated["n_callable"]
    assert expected_count >= MIN_CALLABLE_C_API_OPS
    assert expected_count == sum(row["callable"] for row in generated["ops"])
    assert catalog["n_callable"] == len(rows) == expected_count
    exercised = []
    for row in rows:
        if row["tier"] == "contract":
            candidates = [("normal", np.linspace(0.0, 1.0, 64, dtype=np.float64).reshape(8, 8))]
        else:
            candidates = list(inputs_for(row["in_sort"], row["name"]))
        candidate = next((value for name, value in candidates if name == "override"),
                         next((value for name, value in candidates if name in {"normal", "unit"}),
                              candidates[0][1]))
        held = []
        borrowed = []
        if row["in_sort"] == "contour":
            c_input = copy_input(candidate)
            direct_input = copy_input(candidate)
            assert len(c_input["cs"]) == len(direct_input["cs"])
            assert all(np.shares_memory(left, right) is False
                       for left, right in zip(c_input["cs"], direct_input["cs"]))
        elif row["in_sort"] != "feature":
            c_input = np.array(candidate, dtype=np.float64, order="C", copy=True)
            direct_input = np.array(candidate, dtype=np.float64, order="C", copy=True)
            assert np.shares_memory(c_input, direct_input) is False, row["id"]
        if row["in_sort"] == "image":
            held.append(c_input)
            input_value = _image(c_input)
        elif row["in_sort"] == "region":
            held.append(c_input)
            status, seed = _call(abi, "contract:threshold", [_image(c_input)],
                                 '{"lo":0.5,"hi":1.0}')
            assert status == FS_OK, row["id"]
            borrowed.append(seed)
            input_value = _borrow(FS_VALUE_REGION, seed)
        elif row["in_sort"] == "color":
            input_value, keep = _typed_array(c_input, FS_VALUE_COLOR)
            held.append(keep)
        elif row["in_sort"] == "volume":
            input_value, keep = _typed_array(c_input, FS_VALUE_VOLUME)
            held.append(keep)
        elif row["in_sort"] == "contour":
            input_value, keep = _contour(c_input)
            held.append(keep)
        elif row["in_sort"] == "points":
            input_value, keep = _points(c_input)
            held.append(keep)
        else:
            input_value = _feature(float(candidate))
            direct_input = float(candidate)
        params = ({"contract:threshold": '{"lo":0.5,"hi":1.0}',
                   "contract:gauss": '{"sigma":0.5}'}.get(row["id"], "{}"))
        status, result = _call(abi, row["id"], [input_value], params)
        error = C.create_string_buffer(1024)
        lib.fs_last_error(_runtime, error, len(error))
        assert status == FS_OK, "%s: %s" % (row["id"], error.value.decode("utf-8"))
        try:
            if row["tier"] == "contract":
                fn = getattr(fslib, row["name"])
                direct = fn(fslib.FImage(direct_input), **(
                    {"lo": 0.5, "hi": 1.0} if row["name"] == "threshold"
                    else {"sigma": 0.5} if row["name"] == "gauss" else {}))
            else:
                direct = _direct_registry(registry[row["name"]], direct_input)
            got = _c_output(lib, result, row["out_sort"])
            if row["out_sort"] == "region":
                expected = _direct_runs(direct if isinstance(direct, fslib.Region)
                                        else fslib.Region(np.asarray(direct) > 0.5))
                assert got == expected, row["id"]
            elif row["out_sort"] == "feature":
                assert got == float(direct), row["id"]
            elif row["out_sort"] == "contour":
                assert got["shape"] == tuple(direct["shape"]), row["id"]
                assert len(got["cs"]) == len(direct["cs"]), row["id"]
                for actual_points, expected_points in zip(got["cs"], direct["cs"]):
                    np.testing.assert_array_equal(actual_points, expected_points, err_msg=row["id"])
                expected_closed = [bool(len(points) > 1 and np.array_equal(points[0], points[-1]))
                                   for points in direct["cs"]]
                assert got["closed"] == expected_closed, row["id"]
            else:
                expected = direct.pixels if isinstance(direct, fslib.FImage) else np.asarray(direct)
                np.testing.assert_array_equal(got, expected, err_msg=row["id"])
            exercised.append(row["id"])
        finally:
            assert lib.fs_result_release_n(result) == FS_OK
            for seed in borrowed:
                assert lib.fs_result_release_n(seed) == FS_OK
    assert exercised == [row["id"] for row in rows]


def test_generated_catalog_and_fs_find_ops_json_have_the_same_callable_rows(abi):
    """Generated JSON, help source, and the C search entry share one typed ledger.

    生成 JSON と ``fs_find_ops_json`` の両方が同じ呼出可能 ID を返すことを確認する。
    """
    from conftest import requires_full_registry
    requires_full_registry()
    import json
    from fullseye import c_api_bridge

    lib, runtime = abi
    data = c_api_bridge.catalog()
    generated = json.loads((ROOT / "fullseye" / "data" / "C_API_OPS.json").read_text(encoding="utf-8"))
    assert generated == data
    query = b'{"limit":1000}'
    text = C.c_void_p()
    size = C.c_size_t()
    assert lib.fs_find_ops_json_n(runtime, query, len(query), C.byref(text), C.byref(size)) == FS_OK
    try:
        found = json.loads(C.string_at(text, size.value - 1).decode("utf-8"))
    finally:
        lib.fs_free(text)
    expected = [row for row in data["ops"] if row["callable"]]
    assert found["n_callable"] == data["n_callable"] == len(expected)
    assert found["ops"] == expected


def _direct_runs(region: fslib.Region):
    return [tuple(map(int, row)) for row in region.runs()]


def test_contract_threshold_matches_python_and_objectset_contract_is_explicitly_rejected(abi):
    lib, _runtime = abi
    pixels = np.zeros((7, 9), dtype=np.float64)
    pixels[0, 0:2] = 0.8                 # image edge / 画像端
    pixels[2:4, 2:4] = 0.9
    pixels[4, 5] = pixels[5, 6] = 0.7   # diagonal contact = one 8-connected object
    pixels[6, 8] = 1.0                  # opposite edge / 反対側の端
    direct_region = fslib.threshold(fslib.FImage(pixels), 0.6, 1.0)
    status, region = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.6,"hi":1.0}')
    assert status == FS_OK and _runs(lib, region) == _direct_runs(direct_region)
    status, objects = _call(abi, "contract:connection", [_borrow(FS_VALUE_REGION, region)])
    assert status == FS_E_UNSUPPORTED and not objects.value
    assert lib.fs_result_release_n(region) == FS_OK


def test_empty_region_and_registry_results_match_direct_python(abi):
    lib, _runtime = abi
    pixels = np.zeros((3, 4), dtype=np.float64)
    status, region = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.8,"hi":1.0}')
    assert status == FS_OK and _runs(lib, region) == []
    status, objects = _call(abi, "contract:connection", [_borrow(FS_VALUE_REGION, region)])
    assert status == FS_E_UNSUPPORTED and not objects.value

    pixels[0, 0] = pixels[1, 1] = 0.9
    direct = fullseye.apply(pixels, "threshold", 0.6, 0.5, coerce=False,
                            on_error="raise", allow_nonfinite=False)
    status, registry_region = _call(abi, "registry:threshold", [_image(pixels)], '{"a":0.6,"b":0.5}')
    assert status == FS_OK and _runs(lib, registry_region) == _direct_runs(fslib.Region(direct > 0.5))
    status, count = _call(abi, "registry:blob_count", [_borrow(FS_VALUE_REGION, registry_region)])
    value = C.c_double()
    assert status == FS_OK and lib.fs_result_real_n(count, 0, C.byref(value)) == FS_OK
    expected = fullseye.apply((direct > 0.5).astype(np.float64), "blob_count", 0.5, 0.5,
                              coerce=False, on_error="raise", allow_nonfinite=False)
    assert value.value == float(expected) == 1.0

    for result in (count, registry_region, region):
        assert lib.fs_result_release_n(result) == FS_OK


def test_result_owns_data_after_input_is_freed(abi):
    lib, _runtime = abi
    pixels = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    status, result = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK
    del pixels
    gc.collect()
    assert _runs(lib, result) == [(0, 1, 2), (1, 0, 1)]
    assert lib.fs_result_release_n(result) == FS_OK


@pytest.mark.parametrize("case,expected", [
    ("null_data", FS_E_INVALID_ARG),
    ("zero_size", FS_E_SHAPE),
    ("short_stride", FS_E_SHAPE),
    ("short_buffer", FS_E_SHAPE),
    ("overflow", FS_E_SHAPE),
    ("nan", FS_E_INVALID_ARG),
    ("inf", FS_E_INVALID_ARG),
    ("dtype", FS_E_TYPE),
])
def test_invalid_image_views_are_rejected(abi, case, expected):
    pixels = np.ones((2, 3), dtype=np.float64)
    input_value = _image(pixels)
    if case == "null_data":
        input_value.image.data = None
    elif case == "zero_size":
        input_value.image.width = 0
    elif case == "short_stride":
        input_value.image.row_stride_bytes = 2 * 8
    elif case == "short_buffer":
        input_value.image.data_bytes -= 1
    elif case == "overflow":
        input_value.image.width = 2**63 - 1
        input_value.image.row_stride_bytes = 2**63 - 1
        input_value.image.data_bytes = C.c_size_t(-1).value
    elif case == "nan":
        pixels[0, 0] = np.nan
    elif case == "inf":
        pixels[0, 0] = np.inf
    elif case == "dtype":
        input_value.image.dtype = 999
    status, result = _call(abi, "contract:threshold", [input_value], '{"lo":0.2,"hi":0.8}')
    assert status == expected and not result.value


@pytest.mark.parametrize("kind,shape,op", [
    (FS_VALUE_COLOR, (2, 2, 3), "registry:rgb1_to_gray"),
    (FS_VALUE_VOLUME, (2, 2, 2), "registry:vol_gaussian"),
])
@pytest.mark.parametrize("dtype,numpy_dtype", [
    (1, np.uint8),
    (2, np.uint16),
    (3, np.float32),
    (4, np.float64),
])
@pytest.mark.parametrize("case", ["short_buffer", "extra_shape", "extra_stride", "inner_stride",
                                  "overlapping_outer_stride"])
def test_invalid_color_and_volume_views_are_rejected_for_every_dtype(
        abi, kind, shape, op, dtype, numpy_dtype, case):
    """Reject malformed typed views for every dtype / 全 dtype で不正 view を拒否する。"""
    lib, _runtime = abi
    input_value, keep = _typed_array_with_dtype(shape, kind, dtype, numpy_dtype)
    element = keep.dtype.itemsize
    if case == "short_buffer":
        input_value.array.data_bytes = int(np.prod(shape)) * element - 1
    elif case == "extra_shape":
        input_value.array.shape[len(shape)] = 1
    elif case == "extra_stride":
        input_value.array.stride_bytes[len(shape)] = element
    elif case == "inner_stride":
        input_value.array.stride_bytes[1] += element
    else:
        input_value.array.stride_bytes[0] -= element
    status, result = _call(abi, op, [input_value])
    if result.value:
        assert lib.fs_result_release_n(result) == FS_OK
    assert status == FS_E_SHAPE


@pytest.mark.parametrize("kind,shape,op", [
    (FS_VALUE_COLOR, (2, 2, 3), "registry:rgb1_to_gray"),
    (FS_VALUE_VOLUME, (2, 2, 2), "registry:vol_gaussian"),
])
def test_color_and_volume_views_allow_first_axis_padding(abi, kind, shape, op):
    """A first-axis gap is valid; only overlapping rows are refused / 行間の余白だけを許す。"""
    lib, _runtime = abi
    input_value, keep = _typed_array_with_dtype(shape, kind, 4, np.float64)
    input_value.array.stride_bytes[0] += keep.dtype.itemsize
    status, result = _call(abi, op, [input_value])
    try:
        assert status == FS_OK and result.value
    finally:
        if result.value:
            assert lib.fs_result_release_n(result) == FS_OK


@pytest.mark.parametrize("nonfinite", [np.nan, np.inf])
def test_region_output_rejects_nonfinite_values_with_the_operator_id(nonfinite):
    """A non-finite region must not be silently thresholded / NaN/inf を領域化しない。"""
    from fullseye import c_api_bridge

    with pytest.raises(c_api_bridge._Refuse) as raised:
        c_api_bridge._output(np.array([[0.0, nonfinite]]),
                             {"id": "contract:threshold", "out_sort": "region"})
    assert raised.value.status == FS_E_UNSUPPORTED
    assert "contract:threshold" in str(raised.value)


@pytest.mark.parametrize("kind,shape,op,out_sort", [
    (FS_VALUE_COLOR, (2, 3, 3), "registry:rgb1_to_gray", "image"),
    (FS_VALUE_VOLUME, (2, 3, 4), "registry:vol_gaussian", "volume"),
    (FS_VALUE_VOLUME, (2, 2, 3, 4), "registry:vol_gaussian", "volume"),
])
@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.float32, np.float64])
def test_typed_c_sdk_parity_covers_dtype_row_padding_and_volume_rank(abi, kind, shape, op, out_sort,
                                                                       dtype):
    """C/Python equality spans all ABI dtypes, padded rows, and 3-D/4-D volumes.

    C/Python の一致を全 ABI dtype、行余白、3-D/4-D volume に広げる。
    """
    lib, _runtime = abi
    backing_shape = (shape[0], shape[1] + 1, *shape[2:])
    owner = np.arange(np.prod(backing_shape), dtype=dtype).reshape(backing_shape)
    values = owner[:, :shape[1], ...]
    input_value = _typed_array_view(values, owner, kind)
    status, result = _call(abi, op, [input_value])
    assert status == FS_OK and result.value
    try:
        direct = fullseye.apply(np.asarray(values, dtype=np.float64), op.split(":", 1)[1], 0.5, 0.5,
                                coerce=False, device="cpu", on_error="raise", allow_nonfinite=False)
        np.testing.assert_array_equal(_c_output(lib, result, out_sort), np.asarray(direct))
    finally:
        assert lib.fs_result_release_n(result) == FS_OK


@pytest.mark.parametrize("kind,shape,op", [
    (FS_VALUE_COLOR, (2, 2, 3), "registry:rgb1_to_gray"),
    (FS_VALUE_VOLUME, (2, 2, 2), "registry:vol_gaussian"),
])
def test_color_and_volume_views_reject_unknown_dtype(abi, kind, shape, op):
    """Reject an unknown typed-array dtype / 未知の配列 dtype を拒否する。"""
    input_value, _keep = _typed_array_with_dtype(shape, kind, 999, np.uint8)
    status, result = _call(abi, op, [input_value])
    assert status == FS_E_TYPE and not result.value


@pytest.mark.parametrize("dimensions", [2, 3])
def test_points_accept_two_or_three_coordinates_and_match_python(abi, dimensions):
    """Both declared coordinate widths cross the ABI without aliasing / 2/3 次元を照合する。"""
    lib, _runtime = abi
    c_points = np.arange(15, dtype=np.float64).reshape(5, 3)[:, :dimensions].copy()
    direct_points = c_points.copy()
    assert np.shares_memory(c_points, direct_points) is False
    input_value, keep = _points(c_points)
    status, result = _call(abi, "registry:tb_arc_length", [input_value])
    assert keep is not None and status == FS_OK
    try:
        got = _c_output(lib, result, "feature")
        expected = _direct_registry(next(op for op in __import__("ops").REGISTRY
                                         if op.name == "tb_arc_length"), direct_points)
        assert got == float(expected)
    finally:
        assert lib.fs_result_release_n(result) == FS_OK


@pytest.mark.parametrize("case,expected", [
    ("short_buffer", FS_E_SHAPE),
    ("extra_shape", FS_E_SHAPE),
    ("extra_stride", FS_E_SHAPE),
    ("inner_stride", FS_E_SHAPE),
    ("unknown_dtype", FS_E_TYPE),
    ("nan", FS_E_INVALID_ARG),
    ("zero_points", FS_E_SHAPE),
])
def test_invalid_points_views_are_rejected(abi, case, expected):
    values = np.arange(12, dtype=np.float64).reshape(4, 3)
    input_value, keep = _points(values)
    if case == "short_buffer":
        input_value.points.data_bytes -= 1
    elif case == "extra_shape":
        input_value.points.shape[2] = 1
    elif case == "extra_stride":
        input_value.points.stride_bytes[2] = 8
    elif case == "inner_stride":
        input_value.points.stride_bytes[1] = 16
    elif case == "unknown_dtype":
        input_value.points.dtype = 999
    elif case == "nan":
        keep[0, 0] = np.nan
    else:
        input_value.points.shape[0] = 0
    status, result = _call(abi, "registry:tb_arc_length", [input_value])
    assert status == expected and not result.value


@pytest.mark.parametrize("case,expected", [
    ("short_descriptor_buffer", FS_E_SHAPE),
    ("short_point_buffer", FS_E_SHAPE),
    ("extra_shape", FS_E_SHAPE),
    ("extra_stride", FS_E_SHAPE),
    ("inner_stride", FS_E_SHAPE),
    ("unknown_dtype", FS_E_TYPE),
    ("nan", FS_E_INVALID_ARG),
    ("zero_points", FS_E_SHAPE),
])
def test_invalid_contour_views_are_rejected(abi, case, expected):
    points = np.array([[1.0, 1.0], [1.0, 5.0], [5.0, 1.0], [1.0, 1.0]])
    input_value, keep = _contour({"shape": (8, 8), "cs": [points]})
    arrays, _parts = keep
    part = input_value.contour.contours[0]
    if case == "short_descriptor_buffer":
        input_value.contour.contours_bytes = 0
    elif case == "short_point_buffer":
        part.points.data_bytes -= 1
    elif case == "extra_shape":
        part.points.shape[2] = 1
    elif case == "extra_stride":
        part.points.stride_bytes[2] = 8
    elif case == "inner_stride":
        part.points.stride_bytes[1] = 16
    elif case == "unknown_dtype":
        part.points.dtype = 999
    elif case == "nan":
        arrays[0][0, 0] = np.nan
    else:
        part.points.shape[0] = 0
    status, result = _call(abi, "registry:count_contours", [input_value])
    assert status == expected and not result.value


def test_null_input_array_unknown_ops_and_extra_json_are_rejected(abi):
    lib, runtime = abi
    result = C.c_uint64()
    op, params = b"contract:threshold", b"{}"
    assert lib.fs_call_id_n(runtime, op, len(op), None, 1, params, len(params),
                         C.byref(result)) == FS_E_INVALID_ARG
    pixels = np.ones((2, 2), dtype=np.float64)
    assert _call(abi, "threshold", [_image(pixels)], '{"lo":0.2,"hi":0.8}')[0] == FS_E_UNKNOWN_OP
    assert _call(abi, "registry:no_such_op", [_image(pixels)])[0] == FS_E_UNKNOWN_OP
    assert _call(abi, "registry:threshold", [_image(pixels)], '{"a":0.2,"extra":1}')[0] == FS_E_BAD_PARAMS


def test_last_error_is_isolated_per_os_thread(abi):
    lib, runtime = abi

    def worker(index):
        op = "registry:thread_missing_%d" % index
        status, result = _call(abi, op, [])
        buf = C.create_string_buffer(1024)
        lib.fs_last_error(runtime, buf, len(buf))
        return status, result.value, buf.value.decode("utf-8")

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(worker, range(32)))
    assert len(rows) == 32
    for index, (status, result, message) in enumerate(rows):
        assert status == FS_E_UNKNOWN_OP and result == 0
        assert "registry:thread_missing_%d" % index in message


def test_runtime_rejects_an_incompatible_abi_major():
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    root = os.fsencode(ROOT)
    options = InitOptions(C.sizeof(InitOptions), root, None, 3, 999, 0, 0, 0)
    runtime = C.c_void_p()
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == 6
    assert runtime.value is None


def test_isolated_mode_rejects_existing_cpython_and_unsafe_host_opt_in_is_explicit():
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    root = os.fsencode(ROOT)
    runtime = C.c_void_p()
    isolated = InitOptions(C.sizeof(InitOptions), root, None, 1, 0, 2, len(root), 0)
    assert lib.fs_runtime_create(C.byref(isolated), C.byref(runtime)) == FS_E_INVALID_ARG
    unsafe = InitOptions(C.sizeof(InitOptions), root, None, 3, 0, 2, len(root), 0)
    assert lib.fs_runtime_create(C.byref(unsafe), C.byref(runtime)) == FS_OK
    lib.fs_runtime_destroy(runtime)


def test_abi_0_2_runtime_paths_are_explicit_spans_without_a_trailing_nul():
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    root = os.fsencode(ROOT)
    root_span = (C.c_char * len(root)).from_buffer_copy(root)
    runtime = C.c_void_p()
    options = InitOptions(C.sizeof(InitOptions), C.cast(root_span, C.c_char_p), None,
                          3, 0, 2, len(root), 0)
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_OK
    lib.fs_runtime_destroy(runtime)
    options.runtime_root_bytes = 0
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_E_INVALID_ARG


def test_abi_0_2_runtime_paths_reject_embedded_nul_bytes():
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    root = (C.c_char * len(b"root\0suffix")).from_buffer_copy(b"root\0suffix")
    runtime = C.c_void_p()
    options = InitOptions(C.sizeof(InitOptions), C.cast(root, C.c_char_p), None,
                          3, 0, 2, C.sizeof(root), 0)
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_E_INVALID_ARG
    home = (C.c_char * len(b"home\0suffix")).from_buffer_copy(b"home\0suffix")
    options.runtime_root = os.fsencode(ROOT)
    options.runtime_root_bytes = len(options.runtime_root)
    options.python_home = C.cast(home, C.c_char_p)
    options.python_home_bytes = C.sizeof(home)
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_E_INVALID_ARG


def test_bounded_strings_do_not_require_nul_and_legacy_entrypoint_remains_abi_0_1_compatible(abi):
    lib, runtime = abi
    op = (C.c_char * len(b"contract:threshold")).from_buffer_copy(b"contract:threshold")
    params = (C.c_char * len(b'{"lo":0.5,"hi":1.0}')).from_buffer_copy(b'{"lo":0.5,"hi":1.0}')
    pixels = np.ones((2, 2), dtype=np.float64)
    result = C.c_uint64()
    assert lib.fs_call_id_n(runtime, op, C.sizeof(op), C.byref(_image(pixels)), 1,
                         params, C.sizeof(params), C.byref(result)) == FS_OK
    assert lib.fs_result_release_n(result) == FS_OK
    legacy = lib.fs_call
    legacy.argtypes = [C.c_void_p, C.c_char_p, C.POINTER(Input), C.c_size_t,
                       C.c_char_p, C.POINTER(C.c_void_p)]
    legacy.restype = C.c_int
    legacy_result = C.c_void_p()
    old_input = Input(C.sizeof(Input), FS_VALUE_IMAGE, _image(pixels).image, None, 0)
    assert legacy(runtime, b"contract:threshold", C.byref(old_input), 1,
                  b'{"lo":0.5,"hi":1.0}', C.byref(legacy_result)) == FS_OK
    lib.fs_result_release.argtypes = [C.c_void_p]
    lib.fs_result_release.restype = None
    lib.fs_result_release(legacy_result)


def test_released_and_unknown_result_handles_are_rejected_and_double_release_errors(abi):
    lib, _runtime = abi
    pixels = np.ones((2, 2), dtype=np.float64)
    status, result = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK and result.value
    assert lib.fs_result_release_n(result) == FS_OK
    kind = C.c_int()
    assert lib.fs_result_kind_n(result, 0, C.byref(kind)) == FS_E_INVALID_ARG
    assert lib.fs_result_release_n(result) == FS_E_INVALID_ARG
    unknown = C.c_uint64(0x1234)
    assert lib.fs_result_kind_n(unknown, 0, C.byref(kind)) == FS_E_INVALID_ARG
    input_value = _borrow(FS_VALUE_REGION, result)
    assert _call(abi, "contract:connection", [input_value])[0] == FS_E_INVALID_ARG
    status, replacement = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK and replacement.value != result.value
    assert lib.fs_result_release_n(replacement) == FS_OK


def test_maximum_generation_slot_is_retired_without_revalidating_a_stale_id(abi):
    lib, _runtime = abi
    pixels = np.ones((2, 2), dtype=np.float64)
    status, first = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK
    assert lib.fs_result_release_n(first) == FS_OK
    assert lib.fs_test_result_id_seed_next_generation(2**32 - 1) == FS_OK
    status, maximum = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK
    assert maximum.value >> 32 == 2**32 - 1
    assert lib.fs_result_release_n(maximum) == FS_OK
    kind = C.c_int()
    assert lib.fs_result_kind_n(maximum, 0, C.byref(kind)) == FS_E_INVALID_ARG
    status, replacement = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK
    assert (replacement.value & 0xFFFFFFFF) != (maximum.value & 0xFFFFFFFF)
    assert lib.fs_result_kind_n(maximum, 0, C.byref(kind)) == FS_E_INVALID_ARG
    assert lib.fs_result_release_n(replacement) == FS_OK


def test_runtime_without_a_named_python_environment_fails_closed(monkeypatch):
    lib = C.CDLL(str(_library_path()))
    _bind(lib)
    monkeypatch.delenv("FULLSEYE_PYTHON_ROOT", raising=False)
    runtime = C.c_void_p()
    options = InitOptions(C.sizeof(InitOptions), None, None, 3, 0, 2, 0, 0)
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_E_NO_PYTHON
    assert runtime.value is None


def test_release_and_accessor_concurrency_keeps_the_handle_lifetime_safe(abi):
    lib, _runtime = abi
    pixels = np.ones((8, 8), dtype=np.float64)
    status, result = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.5,"hi":1.0}')
    assert status == FS_OK
    assert lib.fs_test_result_id_pause_after_lease(1) == FS_OK

    def read_result():
        pointer = C.POINTER(Run)()
        count = C.c_size_t()
        return lib.fs_result_region_runs_n(result, 0, C.byref(pointer), C.byref(count)), count.value

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(read_result)
        assert lib.fs_test_result_id_wait_for_lease(5000) == FS_OK
        assert lib.fs_result_release_n(result) == FS_OK
        assert lib.fs_test_result_id_resume_lease() == FS_OK
        status, count = future.result()
    assert status == FS_OK and count == 8
    assert lib.fs_result_region_runs_n(result, 0, C.byref(C.POINTER(Run)()), C.byref(C.c_size_t())) == FS_E_INVALID_ARG
    assert lib.fs_test_result_id_pause_after_lease(0) == FS_OK
