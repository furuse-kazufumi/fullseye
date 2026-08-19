# gsplat native を Windows(RTX 5090 / torch cu128)でビルドする — 実証済み手順

2026-08-19 に RTX 5090 上でネイティブ gsplat のビルド成功(1532 rasterizations/s)。要点と“詰まり”の解を残す。

## 環境
- GPU: RTX 5090 (Blackwell sm_120) / driver 610.74
- venv: `C:\dev\projects\imgevolve\.venv-gsplat`(torch 2.11.0+cu128, gsplat 1.5.3)
- 共有 py -3.11 は非変更

## 必要ツールチェーン
1. **MSVC C++ (cl.exe)**: VS BuildTools 2022 の「C++ によるデスクトップ開発(VCTools)」。導入は管理者昇格(UAC)必須。
   `...\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe`
2. **nvcc 12.8(torch cu128 と版一致)**: システム CUDA 13.3 は torch 2.11 ヘッダ非互換。**admin 不要の conda で取得**:
   ```
   micromamba create -p <prefix>\cuda128 -c conda-forge "cuda-nvcc=12.8.*" "cuda-cudart-dev=12.8.*" "cuda-cccl=12.8.*" "cuda-nvrtc-dev=12.8.*"
   # CUDA_HOME = <prefix>\cuda128\Library, nvcc = Library\bin\nvcc.exe
   # torch は lib/x64 を見るので: cp Library/lib/*.lib Library/lib/x64/
   ```

## ビルド時の環境(bat)
```
call "...\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set CUDA_PATH=<prefix>\cuda128\Library
set CUDA_HOME=%CUDA_PATH%
set PATH=%CUDA_PATH%\bin;%CUDA_PATH%\nvvm\bin;%PATH%
.venv-gsplat\Scripts\python.exe -c "import gsplat, torch; gsplat.rasterization(...)"  # 初回に JIT ビルド(~44s)
```

## 適用したパッチ(★再インストールで消える。要再適用)
1. **torch header の `small` マクロ衝突**(torch 2.11 Windows バグ):
   `.venv-gsplat\Lib\site-packages\torch\include\c10\cuda\CUDACachingAllocator.h`
   の `struct StreamSegmentSize` 直前に `#ifdef small` / `#undef small` / `#endif` を挿入。
   （Windows rpcndr.h の `#define small char` が `bool small` を `bool char` に化けさせるため）
2. **gsplat の `-Wno-attributes` を MSVC で除去**:
   `.venv-gsplat\Lib\site-packages\gsplat\cuda\_backend.py`
   `extra_cflags = [opt_level] if os.name=="nt" else [opt_level, "-Wno-attributes"]`
   （cl.exe が GCC 系フラグを D8021 で拒否）

## 結果
`gsplat.rasterization` 動作、50 回 0.033s = **1532/s**。純 torch(非 tiled, `gsplat_torch.py`)の桁違い高速版として backend 差し替え可能。
