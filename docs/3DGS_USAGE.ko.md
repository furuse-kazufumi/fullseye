# Fullseye 3DGS — 사용법(명령어 한 줄)

[日本語](./3DGS_USAGE.md) · [English](./3DGS_USAGE.en.md) · [简体中文](./3DGS_USAGE.zh.md) · [繁體中文](./3DGS_USAGE.tw.md) · **한국어** · [Deutsch](./3DGS_USAGE.de.md)

MuJoCo의 시뮬레이션 장면을 **3D Gaussian Splatting**으로 만들어, 전방위로 돌려볼 수 있는 GIF와 새로운 시점 이미지를 생성합니다. 카메라 자세는 시뮬레이션의 실제 값(ground truth)을 사용하므로 **COLMAP이 필요 없습니다**.

## 가장 간단한 사용법

imgevolve 폴더에서:

```bat
3dgs go2 --open
```

이것만으로 go2(사족 로봇)를 3DGS화하고, 완성된 전방위 GIF를 자동으로 엽니다.

- 장면 변경: `3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- 자신의 MJCF: `3dgs <로컬 작업 경로>\path\to\scene.xml`
- 목록 보기: `3dgs --list`

## 품질 프리셋

```bat
3dgs go2 --quality fast       :: 128px / 8천 개 가우시안(몇 초, 미리보기용)
3dgs go2 --quality balanced   :: 256px / 2만 개 가우시안(기본값)
3dgs go2 --quality high       :: 384px / 4.5만 개 가우시안(가장 깨끗함)
```

## 더 선명하게(densify)

```bat
3dgs go2 --quality high --densify --open
```

`--densify`를 붙이면 학습 중에 **가우시안 수를 자동으로 늘려 디테일을 높입니다**(native gsplat에서만 동작). go2의 경우 약 8천 개에서 약 5만 개까지 늘어나며, 몸체와 다리가 더 매끄러워집니다. 수 초에서 십수 초면 완료됩니다.

## backend는 자동

- **native gsplat**(타일 CUDA)을 사용할 수 있으면 자동으로 그것을 사용합니다(빠르고 정밀하며, 초당 수백 it)
- 없으면 자동으로 **순수 PyTorch**로 폴백합니다(느리지만 동작합니다)
- `--backend torch` / `--backend gsplat`로 명시적으로 지정할 수도 있습니다

환경(CUDA/컴파일러)은 launcher가 자동으로 설정하므로 vcvars 등을 신경 쓸 필요가 없습니다.

## Studio에서

`spikes/studio_app.py`를 실행 → "시뮬레이션 모델을 3D로 보기 / 3DGS화" 패널에서 장면 이름(칩을 클릭하거나 직접 입력)과 품질을 선택하고 "3DGS 학습 🎇" → 완료되면 전방위 GIF가 열립니다.

## 출력

`out/3dgs_<scene>/`(또는 `--out`으로 지정한 위치)에 다음이 생성됩니다:
- `turntable.gif` … 전방위 미리보기
- `novelview.png` … 왼쪽 = 실제 값 / 오른쪽 = 새로운 시점 렌더링
- `gaussians.npz` … 학습된 가우시안(npz)
- `gaussians.ply` … 표준 3DGS .ply(native 사용 시). **SuperSplat 등의 웹 뷰어에 드래그 앤 드롭**하면 열 수 있습니다
- `report.json` … PSNR 등의 지표

## 필요 환경

- GPU 학습용 venv `.venv-gsplat`(torch cu128)
- native를 사용하려면 `.gsplat-cuda`(CUDA 12.8) + VS BuildTools의 C++ 도구가 필요합니다. 자세한 내용과 재현 절차는 `docs/GSPLAT_NATIVE_WINDOWS.md`를 참고하십시오

> 솔직한 참고: `--densify`의 효과는 장면에 따라 다릅니다. go2처럼 덩어리진 형태는 깔끔해지지만, cassie처럼 가느다란 이족 로봇은 학습 시점에 과적합되어 hold-out이 다소 흐려질 수 있습니다. 먼저 켜지 않고 시도해 보고, 부족하다면 추가하는 것을 권장합니다.

## 동작 재생하기(--motion)

```bat
3dgs go2 --motion --open
```

정지 상태가 아니라, **움직이는 로봇의 3DGS**를 만듭니다. 동작 원리:
1. 표준 자세로 3DGS를 학습
2. 각 가우시안이 MuJoCo의 어느 body(링크)에서 유래했는지 **segmentation**으로 확정하여 리깅
3. 관절을 움직이고(기본값 = 사인파), 각 프레임의 body 자세(시뮬레이션의 실제 값)로 강체 스키닝 → 다시 렌더링 → `motion.gif` 생성

로봇은 강체 링크의 집합이므로, 완전한 4D-GS를 사용하지 않고도 자연스럽게 움직일 수 있습니다. `--frames N`으로 프레임 수를 변경할 수 있습니다.

> 솔직한 참고: 기본 동작은 데모용 사인파입니다(실제 보행 정책이 아닙니다). 시뮬레이션의 자세가 실제 값이므로 무너지지는 않지만, 발끝 주변에 약간의 노이즈가 나타날 수 있습니다(초기화 지점의 body 소속 경계 부분).

### 걸음걸이(gait) 자동 생성

```bat
3dgs go2 --motion --gait trot --open
```

`--gait trot`로 **사족보행의 트롯 걸음걸이**(대각선 다리가 같은 위상으로 번갈아 딛는 방식)를 자동 생성하여 재생합니다. 관절 이름(FL/FR/RL/RR 또는 LF/RF/LH/RH + thigh/calf)으로 다리를 자동 감지하므로 go2와 anymal에서 동작합니다. 감지할 수 없는 모델은 사인파로 폴백합니다. 실제 보행 정책의 출력을 사용하려면 `--motion-file traj.npy`(qpos 궤적 (F,nq))를 사용하십시오.
