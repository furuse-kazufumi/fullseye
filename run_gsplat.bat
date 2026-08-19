@echo off
REM Fullseye 3DGS native ランナー: vcvars + 永続 CUDA 12.8(.gsplat-cuda)で gsplat を回す。
REM 使い方: run_gsplat.bat <script.py> [args...]
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set "ROOT=%~dp0"
set "CUDA_PATH=%ROOT%.gsplat-cuda\Library"
set "CUDA_HOME=%CUDA_PATH%"
set "TORCH_EXTENSIONS_DIR=%ROOT%.gsplat-build"
set "PATH=%CUDA_PATH%\bin;%CUDA_PATH%\nvvm\bin;%ROOT%.venv-gsplat\Scripts;%PATH%"
"%ROOT%.venv-gsplat\Scripts\python.exe" %*
