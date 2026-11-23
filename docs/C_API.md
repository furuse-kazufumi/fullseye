# Fullseye C SDK compatibility

The pybind11 C SDK is first published as ABI 0.2. It is a development SDK: set
`fs_init_options_t.runtime_root` (with `runtime_root_bytes` for 0.2) or
`FULLSEYE_PYTHON_ROOT` to an environment containing the `fullseye` package.

| Surface | Version | Result lifetime |
| --- | --- | --- |
| `fullseye_abi.h` public L1 contract | published 0.1 | Each function's declared opaque handle |
| `fs_runtime_create`, `fs_find_ops_json`, `fs_call`, and pointer accessors | C SDK 0.2 | `fs_result_t *`, released by `fs_result_release` |
| `fs_find_ops_json_n`, `fs_call_id_n`, and ID accessors | C SDK 0.2 | `fs_result_id_t`, released by `fs_result_release_n` |

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

## Typed operator reachability

`fs_call_id_n` derives its callable operators from the contract and registry
type ledgers. An operator is callable when both its declared input and output
are one of `image`, `region`, `color`, `volume`, or scalar `feature`; a row
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
