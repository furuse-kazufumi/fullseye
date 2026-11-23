# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Differential and refusal gates for the pybind11 C ABI / pybind11 C ABI の差分・拒否門。"""
from __future__ import annotations

import ctypes as C
import gc
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
FS_VALUE_IMAGE = 1
FS_VALUE_REGION = 2
FS_VALUE_OBJECTSET = 3


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


class Input(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result", C.c_void_p), ("result_index", C.c_size_t)]


class InputN(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("kind", C.c_int), ("image", ImageView),
                ("result_id", C.c_uint64), ("result_index", C.c_size_t)]


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
    lib.fs_result_release_n.argtypes = [C.c_uint64]
    lib.fs_result_release_n.restype = C.c_int
    lib.fs_result_kind_n.argtypes = [C.c_uint64, C.c_size_t, C.POINTER(C.c_int)]
    lib.fs_result_kind_n.restype = C.c_int
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
    return InputN(C.sizeof(InputN), FS_VALUE_IMAGE, view, 0, 0)


def _borrow(kind: int, result, index=0) -> InputN:
    return InputN(C.sizeof(InputN), kind, ImageView(), result, index)


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


def _direct_runs(region: fslib.Region):
    return [tuple(map(int, row)) for row in region.runs()]


def test_contract_pipeline_matches_python_at_edges_and_preserves_order(abi):
    lib, _runtime = abi
    pixels = np.zeros((7, 9), dtype=np.float64)
    pixels[0, 0:2] = 0.8                 # image edge / 画像端
    pixels[2:4, 2:4] = 0.9
    pixels[4, 5] = pixels[5, 6] = 0.7   # diagonal contact = one 8-connected object
    pixels[6, 8] = 1.0                  # opposite edge / 反対側の端
    direct_region = fslib.threshold(fslib.FImage(pixels), 0.6, 1.0)
    direct_objects = fslib.connection(direct_region)
    direct_measures = fslib.measure_all(direct_objects)

    status, region = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.6,"hi":1.0}')
    assert status == FS_OK and _runs(lib, region) == _direct_runs(direct_region)
    status, objects = _call(abi, "contract:connection", [_borrow(FS_VALUE_REGION, region)])
    assert status == FS_OK
    count = C.c_size_t()
    assert lib.fs_result_object_count_n(objects, 0, C.byref(count)) == FS_OK
    assert count.value == len(direct_objects)
    assert [_object_runs(lib, objects, i) for i in range(count.value)] == [
        _direct_runs(direct_objects.region(i)) for i in range(len(direct_objects))]
    status, measures = _call(abi, "contract:measure_all", [_borrow(FS_VALUE_OBJECTSET, objects)])
    assert status == FS_OK
    for index, expected in enumerate(direct_measures):
        np.testing.assert_array_equal(_tuple(lib, measures, index), np.asarray(expected))

    for result in (measures, objects, region):
        assert lib.fs_result_release_n(result) == FS_OK


def test_empty_region_and_registry_results_match_direct_python(abi):
    lib, _runtime = abi
    pixels = np.zeros((3, 4), dtype=np.float64)
    status, region = _call(abi, "contract:threshold", [_image(pixels)], '{"lo":0.8,"hi":1.0}')
    assert status == FS_OK and _runs(lib, region) == []
    status, objects = _call(abi, "contract:connection", [_borrow(FS_VALUE_REGION, region)])
    assert status == FS_OK
    status, measures = _call(abi, "contract:measure_all", [_borrow(FS_VALUE_OBJECTSET, objects)])
    assert status == FS_OK and [_tuple(lib, measures, i) for i in range(3)] == [[], [], []]

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

    for result in (count, registry_region, measures, objects, region):
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
