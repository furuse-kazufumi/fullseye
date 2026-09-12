# Building native gsplat on Windows (RTX 5090 / torch cu128) — a proven procedure

[日本語](./GSPLAT_NATIVE_WINDOWS.md) · **English**

On 2026-08-19, native gsplat was built successfully on an RTX 5090 (1532 rasterizations/s). This note records the key points and the fixes for the sticking points.

## Environment
- GPU: RTX 5090 (Blackwell sm_120) / driver 610.74
- venv: `<local working path>\dev\projects\imgevolve\.venv-gsplat` (torch 2.11.0+cu128, gsplat 1.5.3)
- The shared py -3.11 was left unchanged

## Required toolchain
1. **MSVC C++ (cl.exe)**: "Desktop development with C++ (VCTools)" from VS BuildTools 2022. Installation requires administrator elevation (UAC).
   `...\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe`
2. **nvcc 12.8 (matching the version of torch cu128)**: System CUDA 13.3 is header-incompatible with torch 2.11. **Obtain it via conda, which requires no admin:**
   ```
   micromamba create -p <prefix>\cuda128 -c conda-forge "cuda-nvcc=12.8.*" "cuda-cudart-dev=12.8.*" "cuda-cccl=12.8.*" "cuda-nvrtc-dev=12.8.*"
   # CUDA_HOME = <prefix>\cuda128\Library, nvcc = Library\bin\nvcc.exe
   # torch looks at lib/x64, so: cp Library/lib/*.lib Library/lib/x64/
   ```

## Build-time environment (bat)
```
call "...\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set CUDA_PATH=<prefix>\cuda128\Library
set CUDA_HOME=%CUDA_PATH%
set PATH=%CUDA_PATH%\bin;%CUDA_PATH%\nvvm\bin;%PATH%
.venv-gsplat\Scripts\python.exe -c "import gsplat, torch; gsplat.rasterization(...)"  # JIT build on first run (~44s)
```

## Applied patches (★ they vanish on reinstall. They must be reapplied)
1. **`small` macro clash in the torch header** (torch 2.11 Windows bug):
   In `.venv-gsplat\Lib\site-packages\torch\include\c10\cuda\CUDACachingAllocator.h`,
   insert `#ifdef small` / `#undef small` / `#endif` immediately before `struct StreamSegmentSize`.
   (Because Windows rpcndr.h's `#define small char` turns `bool small` into `bool char`.)
2. **Remove gsplat's `-Wno-attributes` under MSVC**:
   `.venv-gsplat\Lib\site-packages\gsplat\cuda\_backend.py`
   `extra_cflags = [opt_level] if os.name=="nt" else [opt_level, "-Wno-attributes"]`
   (cl.exe rejects GCC-style flags with D8021.)

## Result
`gsplat.rasterization` works, 50 iterations in 0.033s = **1532/s**. It can be swapped in as a backend that is orders of magnitude faster than pure torch (non-tiled, `gsplat_torch.py`).
