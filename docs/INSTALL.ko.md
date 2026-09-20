<!-- i18n-source-sha: b5eeee92dc95 -->
# 설치 / 환경 구축 완전 가이드

[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · [简体中文](./INSTALL.zh.md) · [繁體中文](./INSTALL.tw.md) · **한국어** · [Deutsch](./INSTALL.de.md)

개발 머신부터 임베디드 Linux까지, 목적에 맞게 Fullseye(작업명 imgevolve)를 구축하기 위한 가이드입니다. 5분 만에 바로 실행해 보고 싶다면 [GETTING_STARTED.md](GETTING_STARTED.md)가 지름길입니다.

Fullseye의 설계 방침은 **"numpy + scipy만으로 동작하는 코어" + "무거운 의존성은 모두 선택 사항(optional)"**입니다. 추가 백엔드가 없어도 해당 백엔드 전용 오퍼레이터만 비활성화될 뿐, 코어는 항상 동작합니다(우아한 성능 저하, graceful degradation).

---

## (a) 전제 조건

| 항목 | 요구 사항 |
|---|---|
| Python | **3.11**(`pyproject.toml`의 `requires-python = ">=3.10"`. 개발·검증은 3.11 사용) |
| 실행 명령 | Windows: `py -3.11` / Linux: `python3.11` |
| 코어 의존성 | `numpy>=1.23`, `scipy>=1.9`(`pip install -e .`로 자동 설치) |
| OS | Windows 10/11, Linux(임베디드 포함). Python이 동작하면 macOS도 가능 |

---

## (b) pip install(extras의 의미와 사용법)

저장소 최상위 디렉터리에서 editable install을 수행합니다.

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # 코어만(numpy + scipy. 모든 op가 보이고, optional backend가 필요한 op는 호출 시 부족한 extra를 알려 줌)
```

추가 백엔드는 **extras**로 선택합니다(`pyproject.toml`의 `[project.optional-dependencies]`가 실체입니다).

| extras | 추가되는 의존성 | 활성화되는 내용 |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | 이미지 파일 I/O(`apply`/`pipeline` CLI가 필수로 요구), `cv_*` 계열 오퍼레이터 |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*` 계열(다수의 자동 생성 오퍼레이터의 기반) |
| `pil` | `Pillow>=9` | 이미지 I/O의 대체 수단, `xpil_*` 계열(emboss/posterize/solarize 등) |
| `wavelets` | `PyWavelets>=1.4` | 웨이블릿 계열(VisuShrink/서브밴드/패킷 등) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU 배치 백엔드(`accel.py`/`bench.py`), `xkor_*`(kornia) 계열 |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*`(curvature flow 등), mahotas 유래(Zernike/pftas 등) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio**(`studio.py` / `fullseye-studio`) |
| `all` | 위 항목 중 GUI를 제외한 전부(opencv, skimage, pil, wavelets, gpu, extra) | 모든 오퍼레이터·백엔드 |

사용 기준:

```powershell
# 실무에서 자주 쓰는 최소 구성 + 이미지 I/O(GUI 불필요, 코드/CLI 중심)
py -3.11 -m pip install -e ".[opencv]"

# GUI(Studio)도 사용
py -3.11 -m pip install -e ".[opencv,gui]"

# 풀 세트(GUI 포함. all에는 GUI가 없으므로 gui를 함께 명시)
py -3.11 -m pip install -e ".[all,gui]"

# GPU 배치 경로도 시도(CUDA 지원 torch 필요)
py -3.11 -m pip install -e ".[gpu]"
```

> `all`에는 **`gui`가 포함되지 않습니다**(GUI는 용도가 다르므로 별도로 분리). Studio를 사용하려면 반드시 `gui`를 명시적으로 추가하십시오.

설치가 성공하면 다음 **두 개의 콘솔 스크립트**를 사용할 수 있습니다(`[project.scripts]`).

| 명령 | 실체 | 대응하는 직접 실행 방법 |
|---|---|---|
| `fullseye` | `imgevolve:main`(CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main`(GUI) | `py -3.11 studio.py` |

설치 없이 시도하고 싶다면, 저장소 최상위 디렉터리를 `PYTHONPATH`에 추가하면 `import fullseye`는 동작합니다(콘솔 스크립트는 사용할 수 없습니다).

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows 설치 프로그램

`install\install.ps1`을 실행하면 환경 구축과 바탕화면 연동이 한 번에 이루어집니다(PowerShell).

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

이 설치 프로그램을 실행하면 대략 다음과 같은 작업이 이루어집니다.

- Python 3.11 존재 여부 확인
- `pip install -e .`(필요한 extras 포함)를 통한 Fullseye 설치
- **Fullseye Studio 바로 가기(`Fullseye Studio.lnk`) 생성** — 콘솔 창을 띄우지 않고 실행할 수 있도록 `pyw.exe`를 통해 등록되며, `assets\fullseye.ico` 아이콘이 적용됩니다

이후 시작 메뉴 / 바탕화면 바로 가기에서 Studio를 실행할 수 있습니다.

> 실행 정책 때문에 막힐 경우 `-ExecutionPolicy Bypass`를 추가하십시오(위 명령에 이미 포함되어 있습니다).

---

## (d) Linux 설치 스크립트 + `.desktop` 런처

`install/install.sh`를 실행하면 Linux 환경에서 동등한 구축이 이루어집니다.

```bash
cd /path/to/imgevolve
bash install/install.sh
```

이 스크립트를 실행하면 대략 다음과 같은 작업이 이루어집니다.

- `python3.11` 존재 여부 확인
- `pip install -e .`(필요한 extras 포함)
- **`.desktop` 런처 생성** — 애플리케이션 메뉴에서 Fullseye Studio를 실행할 수 있도록 `assets/fullseye.ico`를 아이콘으로 하는 데스크톱 항목이 등록됩니다

이후 데스크톱 환경의 애플리케이션 목록에서 Studio를 실행할 수 있습니다.

---

## (e) 최소 구성 / 임베디드(embedded Linux)

Fullseye의 코어는 **numpy + scipy만으로** 동작하도록 만들어져 있습니다. GUI·GPU·무거운 백엔드가 필요 없는 임베디드 용도에서는 코어만 설치하면 충분합니다.

```bash
python3.11 -m pip install -e .        # numpy + scipy만. GUI/torch/opencv 불필요
```

임베디드 사용 시 핵심 사항:

- **numpy 배열만으로 입출력이 완결**됩니다. 파일 I/O를 전혀 거치지 않고, 센서/카메라에서 얻은 numpy 프레임을 직접 전달할 수 있습니다.

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # 직접 취득한 float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # 디스크에 쓸 필요 없음
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **파일 I/O가 필요할 때**(`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples)는 **OpenCV 또는 Pillow 둘 중 하나**만 있으면 동작합니다(`imgio`가 자동으로 대체 처리). 임베디드에서 경량을 우선한다면 Pillow(`[pil]`)가 더 작습니다.
- **설계는 개발 머신, 실행은 임베디드 머신**이라는 역할 분담이 가능합니다. 개발 머신의 Studio에서 파이프라인을 구성해 JSON을 내보내고, 임베디드 머신에서는 `FullseyeEngine.load("pipeline.json").run(frame)`으로 실행하기만 하면 됩니다(GUI 불필요). 자세한 내용은 [ENGINE.md](ENGINE.md)를 참고하십시오.
- **지각 스택**(stereo / terrain / flow / detect / registration / pose)도 numpy + scipy만으로 동작합니다(`fullseye.disparity_map` 등). 로봇/비전 용도에서 추가 의존성 없이 사용할 수 있습니다.

> GPU(`torch`)는 어디까지나 **배치 가속을 위한 선택 사항(opt-in)**입니다. 임베디드의 단일 이미지 처리에는 불필요하며, 설치하지 않아도 모든 오퍼레이터가 CPU에서 동작합니다.

---

## (f) 자주 발생하는 문제

| 증상 | 원인 | 대처 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 미설치 / 경로 미설정 | `pip install -e .` 실행, 또는 저장소 최상위 디렉터리를 `PYTHONPATH`에 추가 |
| `fullseye` / `fullseye-studio` 명령을 찾을 수 없음 | 콘솔 스크립트 미등록 | `pip install -e .`를 실행. 설치하지 않으려면 `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| Studio 실행 시 PySide6의 ImportError | GUI extras 미도입 | `pip install -e ".[gui]"` |
| `apply` / `pipeline`에서 `cannot read <path>` | 이미지 I/O 백엔드 없음 | `pip install -e ".[opencv]"`(또는 `[pil]`) |
| `read_image` / `write_image`(API)에서 cv2의 ImportError | 이들은 **OpenCV 전용** | `pip install -e ".[opencv]"`. Pillow만으로 해결하고 싶다면 `fullseye.load` / `fullseye.save`를 사용 |
| `list_ops`에 기대한 오퍼레이터가 없음 / `has`가 unknown | 해당 백엔드 미도입 | 대응하는 extras(`skimage`/`wavelets`/`extra` 등)를 추가 |
| GPU 배치(`accel`/`bench`)가 CPU에서 느림 | `torch`가 CPU 버전 | GPU에서는 `--device cuda`. CPU에서는 단순한 pointwise 연산이 변환 비용 때문에 불리함(설계상 그러함) |
| Studio의 3D surface가 열리지 않음 | `QtDataVisualization` 부재 | best-effort 기능. PySide6의 버전/구성에 따라 다르며, 없으면 조용히 건너뜀 |

### 이미지 I/O 의존 관계(중요)

파일 읽기/쓰기에 필요한 백엔드는 경로에 따라 다릅니다.

| 경로 | 필요한 백엔드 |
|---|---|
| `fullseye.load` / `fullseye.save`(= `imgio`), `imgevolve.py run`, examples | **OpenCV 또는 Pillow**(둘 중 하나면 충분 / 자동 대체) |
| `imgevolve.py apply` / `pipeline` | **OpenCV 필수** |
| `fullseye.read_image` / `fullseye.write_image`(API) | **OpenCV 필수** |

numpy 배열을 직접 전달하는 `apply` / `run_pipeline` / `FullseyeEngine.run`은 **이미지 I/O 백엔드가 전혀 필요하지 않습니다**(코어의 numpy + scipy만으로 동작).

---

## 동작 확인

```powershell
py -3.11 imgevolve.py coverage        # 정직한 커버리지 수치(979/2313개 HALCON op를 실제로 구현)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()`은 `0.1.0`, `op_names()`는 860개의 레지스트리 오퍼레이터를 반환합니다(2026-09-03 기준).
