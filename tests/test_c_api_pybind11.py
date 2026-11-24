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
FS_E_BUSY = 14
FS_E_UNSUPPORTED = 6
FS_VALUE_IMAGE = 1
FS_VALUE_REGION = 2
FS_VALUE_OBJECTSET = 3
FS_VALUE_FEATURE = 4
FS_VALUE_COLOR = 6
FS_VALUE_VOLUME = 7
MIN_CALLABLE_C_API_OPS = 682


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


class Input(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result", C.c_void_p), ("result_index", C.c_size_t)]


class InputN(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result_id", C.c_uint64), ("result_index", C.c_size_t),
                ("array", ArrayView), ("feature", C.c_double)]


class PipelineInputN(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("name", C.c_char_p), ("name_bytes", C.c_size_t),
                ("value", InputN)]


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
    lib.fs_runtime_create.argtypes = [C.POINTER(InitOptions), C.POINTER(C.c_void_p)]
    lib.fs_runtime_create.restype = C.c_int
    lib.fs_runtime_destroy.argtypes = [C.c_void_p]
    lib.fs_call_id_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(InputN), C.c_size_t,
                              C.c_void_p, C.c_size_t, C.POINTER(C.c_uint64)]
    lib.fs_call_id_n.restype = C.c_int
    lib.fs_find_ops_json_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                        C.POINTER(C.c_void_p), C.POINTER(C.c_size_t)]
    lib.fs_find_ops_json_n.restype = C.c_int
    lib.fs_find_ops_json.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(C.c_void_p),
                                     C.POINTER(C.c_size_t)]
    lib.fs_find_ops_json.restype = C.c_int
    lib.fs_call.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Input), C.c_size_t,
                            C.c_void_p, C.POINTER(C.c_void_p)]
    lib.fs_call.restype = C.c_int
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
    lib.fs_pipeline_load_json_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p)]
    lib.fs_pipeline_load_json_n.restype = C.c_int
    lib.fs_pipeline_load_path_n.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p)]
    lib.fs_pipeline_load_path_n.restype = C.c_int
    lib.fs_pipeline_destroy.argtypes = [C.c_void_p]
    lib.fs_pipeline_destroy.restype = None
    lib.fs_pipeline_input_count.argtypes = [C.c_void_p]
    lib.fs_pipeline_input_count.restype = C.c_size_t
    lib.fs_pipeline_output_count.argtypes = [C.c_void_p]
    lib.fs_pipeline_output_count.restype = C.c_size_t
    lib.fs_pipeline_input_info.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p),
                                            C.POINTER(C.c_size_t), C.POINTER(C.c_int)]
    lib.fs_pipeline_input_info.restype = C.c_int
    lib.fs_pipeline_output_info.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p),
                                             C.POINTER(C.c_size_t), C.POINTER(C.c_int)]
    lib.fs_pipeline_output_info.restype = C.c_int
    lib.fs_pipeline_run_n.argtypes = [C.c_void_p, C.POINTER(PipelineInputN), C.c_size_t,
                                      C.POINTER(C.c_uint64)]
    lib.fs_pipeline_run_n.restype = C.c_int
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
    options = InitOptions(C.sizeof(InitOptions), root, None, 3, 0, 2, len(root), 0)
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
    return InputN(C.sizeof(InputN), FS_VALUE_IMAGE, view, 0, 0, ArrayView(), 0.0)


def _borrow(kind: int, result, index=0) -> InputN:
    return InputN(C.sizeof(InputN), kind, ImageView(), result, index, ArrayView(), 0.0)


def _call(abi, op: str, inputs: list[Input], params="{}"):
    lib, runtime = abi
    result = C.c_uint64()
    array = (InputN * len(inputs))(*inputs) if inputs else None
    op_bytes, params_bytes = op.encode(), params.encode()
    status = lib.fs_call_id_n(runtime, op_bytes, len(op_bytes), array, len(inputs),
                           params_bytes, len(params_bytes), C.byref(result))
    return status, result


def _error(lib, runtime) -> str:
    size = lib.fs_last_error(runtime, None, 0)
    buf = C.create_string_buffer(size)
    lib.fs_last_error(runtime, buf, size)
    return buf.value.decode("utf-8")


def _pipeline_input(name: str, value: InputN) -> PipelineInputN:
    encoded = name.encode("utf-8")
    return PipelineInputN(C.sizeof(PipelineInputN), encoded, len(encoded), value)


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
    return InputN(C.sizeof(InputN), kind, ImageView(), 0, 0, view, 0.0), values


def _typed_array_with_dtype(shape, kind: int, dtype: int, numpy_dtype) -> tuple[InputN, np.ndarray]:
    """Build an oversized typed view for refusal tests / 拒否試験用の余裕ある view を組む。"""
    layout = np.empty(shape, dtype=numpy_dtype, order="C")
    values = np.ones(int(np.prod(shape)) * 2, dtype=numpy_dtype)
    full_shape = (C.c_int64 * 4)(*shape, *([0] * (4 - len(shape))))
    full_strides = (C.c_int64 * 4)(*layout.strides, *([0] * (4 - len(shape))))
    view = ArrayView(C.sizeof(ArrayView), int(values.ctypes.data), values.nbytes, len(shape),
                     full_shape, full_strides, dtype)
    return InputN(C.sizeof(InputN), kind, ImageView(), 0, 0, view, 0.0), values


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
    return InputN(C.sizeof(InputN), FS_VALUE_FEATURE, ImageView(), 0, 0, ArrayView(), value)


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
    view = ArrayView(C.sizeof(ArrayView))
    assert lib.fs_result_array_n(result, 0, C.byref(view)) == FS_OK
    shape = tuple(view.shape[:view.ndim])
    return np.ctypeslib.as_array(C.cast(view.data, C.POINTER(C.c_double)),
                                 shape=(int(np.prod(shape)),)).reshape(shape).copy()


def _direct_registry(op, value):
    return fullseye.apply(value, op.name, 0.5, 0.5, coerce=False, device="cpu",
                          on_error="raise", allow_nonfinite=False)


def test_every_typed_c_sdk_operator_matches_direct_python_on_a_contract_probe(abi):
    """All generated callable rows traverse C and match the direct Python call exactly.

    全生成対象を既存 ``inputs_for`` 探針で C 経由・Python 直呼びの両方に通す。配列は
    byte-for-byte equality; scalar feature も同じ一回の呼出しで比較する。
    """
    from conftest import inputs_for, requires_full_registry
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
        candidate = next((value for name, value in candidates if name in {"normal", "unit"}), candidates[0][1])
        held = []
        borrowed = []
        if row["in_sort"] != "feature":
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
    legacy_result = C.c_void_p()
    old_input = Input(C.sizeof(Input), FS_VALUE_IMAGE, _image(pixels).image, None, 0)
    assert lib.fs_call(runtime, b"contract:threshold", C.byref(old_input), 1,
                       b'{"lo":0.5,"hi":1.0}', C.byref(legacy_result)) == FS_OK
    lib.fs_result_release.argtypes = [C.c_void_p]
    lib.fs_result_release.restype = None
    lib.fs_result_release(legacy_result)


def test_legacy_c_strings_accept_the_exact_limit_and_reject_limit_plus_one_with_remedy(abi):
    """ABI 0.1 scans exactly one byte past its 256 B / 1 MiB limits, never farther.

    旧 ABI の NUL 文字列は上限ちょうどを Python 側まで通し、+1 B は値・上限・修復方法を
    含む文で、Python に渡す前に拒否する。
    """
    lib, runtime = abi
    max_op, max_json = 256, 1024 * 1024
    pixels = np.ones((2, 2), dtype=np.float64)
    old_input = Input(C.sizeof(Input), FS_VALUE_IMAGE, _image(pixels).image, None, 0)

    query_at_limit = C.create_string_buffer(b"{}" + b" " * (max_json - 2))
    found = C.c_void_p()
    found_bytes = C.c_size_t()
    assert lib.fs_find_ops_json(runtime, query_at_limit, C.byref(found), C.byref(found_bytes)) == FS_OK
    try:
        assert found.value and found_bytes.value > 1
    finally:
        lib.fs_free(found)

    op_at_limit = C.create_string_buffer(b"contract:threshold" + b" " * (max_op - len(b"contract:threshold")))
    legacy_result = C.c_void_p()
    assert lib.fs_call(runtime, op_at_limit, None, 0, C.create_string_buffer(b"{}"),
                       C.byref(legacy_result)) == FS_E_UNKNOWN_OP

    params_at_limit = C.create_string_buffer(b'{"lo":0.5,"hi":1.0}' + b" " *
                                             (max_json - len(b'{"lo":0.5,"hi":1.0}')))
    assert lib.fs_call(runtime, C.create_string_buffer(b"contract:threshold"), C.byref(old_input), 1,
                       params_at_limit, C.byref(legacy_result)) == FS_OK
    lib.fs_result_release(legacy_result)

    op_plus_one = (C.c_char * (max_op + 1)).from_buffer_copy(b"x" * (max_op + 1))
    assert lib.fs_call(runtime, op_plus_one, None, 0, C.create_string_buffer(b"{}"),
                       C.byref(legacy_result)) == FS_E_INVALID_ARG
    message = _error(lib, runtime)
    assert all(fragment in message for fragment in ("op_id", "257", "256", "fs_call_id_n", "少なくとも", "上限"))

    params_plus_one = (C.c_char * (max_json + 1)).from_buffer_copy(b" " * (max_json + 1))
    assert lib.fs_call(runtime, C.create_string_buffer(b"contract:threshold"), None, 0,
                       params_plus_one, C.byref(legacy_result)) == FS_E_INVALID_ARG
    message = _error(lib, runtime)
    assert all(fragment in message for fragment in ("params_json", "1048577", "1048576", "fs_call_id_n", "少なくとも", "上限"))

    query_plus_one = (C.c_char * (max_json + 1)).from_buffer_copy(b" " * (max_json + 1))
    assert lib.fs_find_ops_json(runtime, query_plus_one, C.byref(found), C.byref(found_bytes)) == FS_E_INVALID_ARG
    assert not found.value and found_bytes.value == 0
    message = _error(lib, runtime)
    assert all(fragment in message for fragment in ("query_json", "1048577", "1048576", "fs_find_ops_json_n", "少なくとも", "上限"))


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


def test_saved_pipeline_path_reports_named_types_and_matches_python_after_json_replacement(abi, tmp_path):
    """One C DLL, two Studio JSON saves: C and Python agree / 再ビルドなしの差し替え差分門。"""
    lib, runtime = abi
    path = tmp_path / "inspect.json"
    document = {"fullseye_pipeline": 1, "name": "inspect", "stages": [["threshold", 0.5, 0.5]]}
    path.write_text(json.dumps(document), encoding="utf-8")
    pipeline = C.c_void_p()
    path_bytes = os.fsencode(path)
    assert lib.fs_pipeline_load_path_n(runtime, path_bytes, len(path_bytes), C.byref(pipeline)) == FS_OK
    try:
        assert lib.fs_pipeline_input_count(pipeline) == lib.fs_pipeline_output_count(pipeline) == 1
        name = C.c_void_p()
        name_bytes = C.c_size_t()
        kind = C.c_int()
        assert lib.fs_pipeline_input_info(pipeline, 0, C.byref(name), C.byref(name_bytes), C.byref(kind)) == FS_OK
        try:
            assert C.string_at(name, name_bytes.value - 1) == b"image"
            assert kind.value == FS_VALUE_IMAGE
        finally:
            lib.fs_free(name)
        assert lib.fs_pipeline_output_info(pipeline, 0, C.byref(name), C.byref(name_bytes), C.byref(kind)) == FS_OK
        try:
            assert C.string_at(name, name_bytes.value - 1) == b"result"
            assert kind.value == FS_VALUE_REGION
        finally:
            lib.fs_free(name)

        pixels = np.array([[0.0, 0.2, 0.0], [0.2, 1.0, 0.2], [0.0, 0.2, 0.0]], dtype=np.float64)
        result = C.c_uint64()
        named = _pipeline_input("image", _image(pixels.copy()))
        assert lib.fs_pipeline_run_n(pipeline, C.byref(named), 1, C.byref(result)) == FS_OK
        try:
            c_first = _runs(lib, result)
        finally:
            assert lib.fs_result_release_n(result) == FS_OK
        python_first = fullseye.load_pipeline(path).run(pixels.copy())
        assert c_first == _direct_runs(fslib.Region(np.asarray(python_first) > 0.5))
    finally:
        lib.fs_pipeline_destroy(pipeline)

    # Only the saved JSON changes.  The already-built native DLL is reused.
    document["stages"][0][1] = 0.1
    path.write_text(json.dumps(document), encoding="utf-8")
    replaced = C.c_void_p()
    assert lib.fs_pipeline_load_path_n(runtime, path_bytes, len(path_bytes), C.byref(replaced)) == FS_OK
    try:
        result = C.c_uint64()
        named = _pipeline_input("image", _image(pixels.copy()))
        assert lib.fs_pipeline_run_n(replaced, C.byref(named), 1, C.byref(result)) == FS_OK
        try:
            c_second = _runs(lib, result)
        finally:
            assert lib.fs_result_release_n(result) == FS_OK
        python_second = fullseye.load_pipeline(path).run(pixels.copy())
        assert c_second == _direct_runs(fslib.Region(np.asarray(python_second) > 0.5))
        assert c_second != c_first
    finally:
        lib.fs_pipeline_destroy(replaced)


def test_c_pipeline_after_runtime_destroy_stays_busy_with_a_bilingual_cause_and_fix(abi):
    """The C ABI retains FS_E_BUSY, but explains the destroyed-runtime ordering.

    C の所有権規約では pipeline を残したまま runtime を先に破棄すると run は busy のまま。
    ただし原因と pipeline/runtime の正しい破棄順を日英で返す。
    """
    lib, _shared_runtime = abi
    root = os.fsencode(ROOT)
    options = InitOptions(C.sizeof(InitOptions), root, None, 3, 0, 2, len(root), 0)
    runtime = C.c_void_p()
    assert lib.fs_runtime_create(C.byref(options), C.byref(runtime)) == FS_OK
    pipeline = C.c_void_p()
    payload = json.dumps({"fullseye_pipeline": 1, "name": "inspect",
                          "stages": [["threshold", 0.5, 0.5]]}).encode("utf-8")
    assert lib.fs_pipeline_load_json_n(runtime, payload, len(payload), C.byref(pipeline)) == FS_OK
    try:
        lib.fs_runtime_destroy(runtime)
        pixels = np.ones((2, 2), dtype=np.float64)
        result = C.c_uint64()
        named = _pipeline_input("image", _image(pixels))
        assert lib.fs_pipeline_run_n(pipeline, C.byref(named), 1, C.byref(result)) == FS_E_BUSY
        message = _error(lib, runtime)
        assert all(fragment in message for fragment in (
            "destroyed before this pipeline", "Destroy the pipeline first",
            "Runtime が pipeline より先に破棄", "pipeline を先に破棄"))
    finally:
        lib.fs_pipeline_destroy(pipeline)


@pytest.mark.parametrize("document, required", [
    ({"stages": [["not_an_operator", 0.5, 0.5]]}, ("stage 1", "unknown operator", "Choose an operator")),
    ({"stages": [["threshold", 0.5, 0.5], ["gaussian", 0.5, 0.5]]},
     ("stage 1", "outputs 'region'", "converting operator")),
    ({"stages": [["gaussian", 0.5, 0.5]], "typo": True}, ("unsupported key", "'typo'", "remove")),
])
def test_saved_pipeline_rejections_name_the_problem_reason_and_fix(abi, document, required):
    """Unknown op, bad type chain and extra key never reach execution / 親切な fail-closed 門。"""
    lib, runtime = abi
    payload = json.dumps(document).encode("utf-8")
    pipeline = C.c_void_p()
    assert lib.fs_pipeline_load_json_n(runtime, payload, len(payload), C.byref(pipeline)) == FS_E_BAD_PARAMS
    assert not pipeline.value
    message = _error(lib, runtime)
    for fragment in required:
        assert fragment in message


def test_saved_pipeline_path_and_file_bytes_are_bounded_before_open_or_parse(abi):
    """Hostile spans cannot force path scans or JSON allocation / path・file 上限の門。"""
    lib, runtime = abi
    pipeline = C.c_void_p()
    too_long_path = (C.c_char * 98302)(*([ord("x")] * 98302))
    assert lib.fs_pipeline_load_path_n(runtime, too_long_path, C.sizeof(too_long_path), C.byref(pipeline)) == FS_E_INVALID_ARG
    assert "98301-byte limit" in _error(lib, runtime)
    payload = b" " * (1024 * 1024 + 1)
    assert lib.fs_pipeline_load_json_n(runtime, payload, len(payload), C.byref(pipeline)) == FS_E_INVALID_ARG
    assert "1 MiB limit" in _error(lib, runtime)
