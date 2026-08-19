@echo off
REM Fullseye 3DGS one-liner: 3dgs <scene> [--quality fast^|balanced^|high] [--open]
REM examples: 3dgs go2 --quality high --open  /  3dgs path	o\scene.xml  /  3dgs --list
"%~dp0.venv-gsplat\Scripts\python.exe" "%~dp0fullseye_3dgs.py" %*
