# Fullseye C SDK compatibility

The pybind11 C SDK is first published as ABI 0.2 and extended compatibly in
ABI 0.3. It is a development SDK: set
`fs_init_options_t.runtime_root` (with `runtime_root_bytes` for 0.2) or
`FULLSEYE_PYTHON_ROOT` to an environment containing the `fullseye` package.

| Surface | Version | Result lifetime |
| --- | --- | --- |
| `fullseye_abi.h` public L1 contract | published 0.1 | Each function's declared opaque handle |
| `fs_runtime_create`, `fs_find_ops_json`, `fs_call`, and pointer accessors | C SDK 0.2 | `fs_result_t *`, released by `fs_result_release` |
| `fs_find_ops_json_n`, `fs_call_id_n`, and ID accessors | C SDK 0.2 | `fs_result_id_t`, released by `fs_result_release_n` |
| `fs_input_n_t` contour/points tail and coordinate result accessors | C SDK 0.3 | Borrowed coordinate views, valid until `fs_result_release_n` |

Use `fs_call_id_n` for new code that needs explicit byte spans and a checked,
generation-tagged result ID. It rejects unknown and released IDs. A slot whose
32-bit generation reaches its maximum is retired instead of wrapping, so a
stale ID cannot become valid again. `runtime_root` and `python_home` spans
reject embedded NUL bytes.

The pointer API accepts valid NUL-terminated strings for compatibility. Its
result pointer and borrowed views are invalid after `fs_result_release`.
Direct input buffers are borrowed only while `fs_call` or `fs_call_id_n` is
running. The caller must keep them valid and unchanged until the call returns;
the library does not retain their pointers afterward.

## Building the native SDK

Install the native extra, then pass the CMake package directory reported by
the installed pybind11 module explicitly. CI uses this same route rather than
depending on a system-wide pybind11 CMake package:

```sh
python -m pip install -e ".[native]"
cmake -S . -B build-c-api -DFULLSEYE_BUILD_NATIVE=ON \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
cmake --build build-c-api
```

## Typed operator reachability

`fs_call_id_n` derives its callable operators from the contract and registry
type ledgers. An operator is callable when both its declared input and output
are one of `image`, `region`, `color`, `volume`, scalar `feature`, `contour`,
or `points`; a row
with another sort is rejected as `FS_E_UNSUPPORTED` with the declared-sort
reason. This is fail-closed: it does not substitute an image or tuple for an
unrepresentable value.

`fs_input_n_t` carries direct `image`, `color`, `volume`, and `feature` inputs.
Color uses a 3-D `(H, W, 3)` `fs_array_view_t`; volume uses a dense 3-D or 4-D
`fs_array_view_t`. Shape and stride slots after `ndim` must be zero, and every
axis after the first must be contiguous for all four supported dtypes. Feature
is a finite `double`. Use `fs_result_array_n`
for color or volume outputs and `fs_result_real_n` for feature outputs. The
machine-readable ledger and complete help are generated in
[`fullseye/data/C_API_OPS.json`](../fullseye/data/C_API_OPS.json) and
[`C_API_OPS.md`](C_API_OPS.md); regenerate both with
`py -3.11 tools/gen_c_api_ops.py`.

ABI 0.3 appends `contour` and `points` fields to `fs_input_n_t`; no existing
field or numeric enum value moved. `fs_points_view_t` is the same stable array
layout as `fs_array_view_t`, restricted on direct input to a dense `(N,2)` or
`(N,3)` matrix with `N > 0`; results may be an empty `(0,2)` or `(0,3)` matrix.
A direct contour input is an image `(height,width)` plus one or more
`fs_contour_part_t` values; an operator result may contain no parts. Every part
is a non-empty `(N,2)` coordinate matrix and carries an explicit `closed` flag.
`contours_bytes` and `contour_stride_bytes` bound the descriptor array. The flag is semantic: a
closed C contour has an implicit last-to-first segment. The bridge maps it to
the Python contour convention by repeating the first point when needed, and
removes a repeated endpoint from a part explicitly marked open.

Coordinate views apply the same fail-closed checks as color and volume:
supported dtype, positive dimensions and strides, zero unused shape/stride
slots, contiguous inner axis, sufficient byte extent, alignment, and no NaN or
infinity. Direct input memory is borrowed only during `fs_call_id_n`. Use
`fs_result_points_n`, or `fs_result_contour_shape_n`,
`fs_result_contour_count_n`, and `fs_result_contour_n` for borrowed outputs.
