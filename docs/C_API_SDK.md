# C/C++ SDK runtime requirement

This SDK is for development use. It does not include CPython or the `fullseye`
Python package. Install Fullseye into a Python environment and pass that
environment's package root as `fs_init_options_t.runtime_root`, or set
`FULLSEYE_PYTHON_ROOT` before `fs_runtime_create`. If neither is supplied, the
API returns `FS_E_NO_PYTHON` with an actionable error message.

`FS_INIT_ISOLATED` is the default and rejects an already initialized CPython.
`FS_INIT_ALLOW_HOST_PYTHON_UNSAFE` is an explicit opt-in for hosts that accept
their interpreter's module cache and import configuration.

The installer catalog's `sdk` component installs headers, libraries, and its
CMake package only; its declared `runtime/python` and `runtime/site-packages`
locations are reserved for a later self-contained runtime distribution.
