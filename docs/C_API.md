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
