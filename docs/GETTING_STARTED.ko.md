# 시작하기 (5분 만에 실행하기)

[日本語](./GETTING_STARTED.md) · [English](./GETTING_STARTED.en.md) · [简体中文](./GETTING_STARTED.zh.md) · [繁體中文](./GETTING_STARTED.tw.md) · **한국어** · [Deutsch](./GETTING_STARTED.de.md)

## 어느 것이 내 업무에 맞는가(3개의 진입점)

Fullseye는 범위가 넓어서, 맨 처음 "무엇을 먼저 열어볼지"를 정하지 못하면 멈춰버립니다. 여기 나열한 것은
새로 작성한 데모가 아니라 **게이트(gate)가 매번 실행하고 있는 예제**입니다(실패하면 CI가 빨간색이 됩니다).

| 진입점 | 대상 | 5분: 우선 실행 | 30분: 내부까지 추적 | 반나절: 내 데이터로 |
|---|---|---|---|---|
| **설명 가능한 외관 검사** | 검사·품질 보증 | `py -3.11 examples/poc_solder_fillet_aoi.py` 납땜 필렛(fillet) AOI | `py -3.11 examples/poc_fabric_defect.py` 미검출과 오검출을 나누어 집계 | [CAPABILITIES.md](CAPABILITIES.md)의 "찾기" → Studio에서 내 이미지로 |
| **로봇을 위한 3-D** | 로봇·3-D 계측 | `py -3.11 examples/perception_pipeline.py` 스테레오→깊이→포인트 클라우드→주행 가능성 | `py -3.11 examples/grasp_pose.py` 포인트 클라우드를 모델에 정합해 6-DoF 자세와 파지 방향 산출 | [EXAMPLES_3D.md](EXAMPLES_3D.md) → 내 포인트 클라우드·메시 입력 |
| **물리 기반 비파괴 검사** | X선·광학·계측 | `py -3.11 examples/ct_reconstruction.py` 투영→재구성→치수(mm)와 결함 수 | `py -3.11 examples/poc_ct_void_morphology.py` 합격/불합격이라는 숫자 하나가 형상에 왜 무지한가 | [CAPABILITIES.md](CAPABILITIES.md)의 "형상화" → 내 볼륨 데이터로 |

어느 예제든 **참값(ground truth)**을 갖고 있습니다(폐형해 또는 합성 데이터). 항상 제로 포인트(아무것도 하지 않았을 때)의
결과를 함께 제시하므로, "효과가 있었다"고 말할 수 있는지 스스로 확인할 수 있습니다. 어디까지 검증되어 있는지의
장부는 [MATURITY.md](MATURITY.md)에 있습니다 —— 손으로 작성한 것이 아니라, 실제로 돌아가는 게이트와 실데이터 유무로부터
집계해 낸 것입니다.

---

이 문서는 Fullseye(작업명 imgevolve)를 최단 경로로 실행하기 위한 가이드입니다. **설치 → 첫 파이프라인 만들기 → 실행 → 결과 확인**의
순서로, 막히지 않는 동선을 따라 진행합니다. 더 상세한 환경 구축은 [INSTALL.md](INSTALL.md), Studio의 전체 기능은
[STUDIO_GUIDE.md](STUDIO_GUIDE.md), 코드에서의 실행은 [ENGINE.md](ENGINE.md)를 참조하세요.

Fullseye는 **numpy 배열을 입력·출력으로 하는 이미지 처리 연산자 라이브러리**이며, 그 위에 **HDevelop풍의 시각적
파이프라인 설계 환경(Fullseye Studio)**과 **실행 런타임(FullseyeEngine)**이 얹혀 있습니다. HALCON/HDevelop 식으로 말하면
"HDevelop에서 절차를 조립하고, HDevEngine에서 자신의 애플리케이션에서 호출한다"는 2단 구조를, 그대로 Python + numpy로
재현한 것입니다.

---

## 1. 설치 (1분)

전제 조건: **Python 3.11**(Windows는 `py -3.11`, Linux는 `python3.11`).

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # numpy + scipy 코어만(약 885개 연산자)
```

코어는 **numpy와 scipy만으로** 동작합니다. OpenCV / scikit-image / Pillow 등 추가 백엔드는 선택 사항이며, 설치되어
있지 않아도 해당 백엔드 고유의 연산자만 비활성화될 뿐입니다(우아한 저하, graceful degradation). 실무에서는 최소한
이미지 파일 읽기/쓰기에 OpenCV나 Pillow가 필요하므로, 다음 중 하나를 추가로 설치해 두면 편리합니다.

```powershell
py -3.11 -m pip install -e ".[opencv]"    # 이미지 I/O + OpenCV 유래 연산자
py -3.11 -m pip install -e ".[all]"       # 전체 백엔드(opencv, skimage, pil, wavelets, gpu, extra)
py -3.11 -m pip install -e ".[gui]"       # Fullseye Studio(PySide6)를 사용한다면
```

extras 목록과 의미는 [INSTALL.md](INSTALL.md)에 정리되어 있습니다. GUI를 사용하려면 `[gui]`(또는 `[all]` + `[gui]`)가
필요합니다.

> 설치하지 않고 시험해 볼 수도 있습니다. 저장소 최상위 디렉터리(`<path-to-fullseye>`)를 작업 디렉터리로 하고, 환경 변수
> `PYTHONPATH`에 그 경로를 등록하면 `import fullseye`는 동작합니다. 다만 `fullseye` / `fullseye-studio`라는 명령(콘솔
> 스크립트)은 `pip install -e .`를 실행해야 비로소 사용할 수 있습니다.

---

## 2. 먼저 연산자 1개를 실행해 본다 (Python)

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image(그래디언트 강도)
seg   = fullseye.apply(frame, "otsu")          # image → region(0/1 이진)
n     = fullseye.apply(seg,   "count_obj")     # region → feature(객체 수 = Python float)
print(n)                                       # 예: 316.0
```

> **인자 순서는 `apply(image, name, a, b)`** — 첫 번째 인자가 배열, 두 번째 인자가 연산자 이름입니다. 반대로
> 넘기면 0.1.9부터는 `TypeError: ... arguments look swapped`로 멈춥니다(0.1.8까지는 numpy의
> "truth value of an array is ambiguous"라는 관계없는 오류가 발생했습니다).
> `a`/`b`는 0..1 사이의 유한값이어야 합니다. 문자열·`None`·NaN은 즉시 `TypeError`/`ValueError`가 되고, 범위를
> 벗어난 값은 잘려서 장부에 기록됩니다.

- `apply(image, name, a=0.5, b=0.5)`는 **연산자 1개**를 적용합니다. `name`은 **연산자 이름**(예: `gaussian`)이어도
  **HALCON 별칭**(예: `gauss_filter`)이어도 모두 해석됩니다.
- `a`, `b`는 각 연산자가 가진 **2개의 다이얼(0.0~1.0)**입니다. 의미는 연산자마다 다릅니다(반경·임계값·σ 등).
- 출력 타입(sort)은 연산자에 따라 결정됩니다: `image`(그레이스케일) / `region`(이진) / `feature`(스칼라 float) /
  `color`(RGB) / `contour`(XLD) / `volume`(3D).
- **실패하면 어떻게 되는가**(2026-09-03부터): 기본값 `on_error="fallback"`에서는, 연산자가 내부에서 실패해도 타입에
  맞는 무해한 값(이미지라면 입력의 복사본 등)이 반환되고, **같은 연산자에 대해 1회만** `FullseyeFallbackWarning`이
  발생합니다. 무엇이 몇 번 폴백했는지는 `fullseye.fallbacks()` / `fullseye.fallback_counts()`로 확인할 수 있습니다.
  `on_error="raise"`를 넘기면(또는 환경 변수 `FULLSEYE_ON_ERROR=raise`) **fail-closed**가 되어, 연산자의 진짜
  예외·dtype 계약 위반(정수/bool 이미지)·GPU 커널 실패가 그대로 발생합니다. **sort 불일치는 부분적으로만 검사됩니다**
  (예: RGB `(H,W,3)`을 2-D 연산자에 넘기면 볼륨으로 처리되어, `raise`에서도 예외가 되지 않습니다 —
  `docs/KNOWN_ISSUES.md` #32-4). CI나 검증에서는 `raise`를 권장합니다.
- **다중 입력 연산자**(`add_image` / `union2` 등, `list_ops()`에서 `tier == "nary"`)는 **입력을 리스트로** 전달합니다:
  `fullseye.apply([img1, img2], "add_image")`.
- **템플릿 매칭**(`ncc_locate` / `shape_locate`)은 `template=`으로 찾을 이미지를 전달합니다:
  `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)`(반환되는 row/col은 일치 위치의 **중심**입니다).
  템플릿이 없으면 no-match인 `[0, 0, 0]`이 반환됩니다.

어떤 연산자가 있는지는 다음으로 찾을 수 있습니다.

```python
fullseye.op_names()                 # 전체 레지스트리 연산자 이름(860개, 2026-09-03 기준)
fullseye.list_ops(search="edge")    # 이름 / HALCON 이름 / 카테고리로 부분 일치 검색
fullseye.list_ops(sort="region")    # 입력 sort로 필터링
fullseye.categories()               # 47개 카테고리
```

---

## 3. 파이프라인을 조립한다(여러 연산자를 연결)

여러 연산자를 순서대로 통과시키는 것이 "파이프라인"입니다. 배열을 각 단계로 전달해 최종 결과를 반환합니다.

```python
# 모든 단계에서 같은 a, b를 사용(CLI와 같은 형태)
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# 단계마다 다른 다이얼을 쓰고 싶을 때((name, a, b) 튜플로 지정)
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

이것은 "smooth(평활화) → 에지 강도 → Otsu 이진화"로, 이미지에서 이진 에지 맵을 만드는 전형적인 예입니다.
바로 쓸 수 있는 조합(레시피)이 **20개** 동봉되어 있습니다.

```python
import recipes
recipes.names()                                   # 레시피 이름 목록
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. 시각적으로 조립한다 (Fullseye Studio)

코드를 작성하지 않고, 연산자를 검색해 배치하고, 다이얼을 슬라이더로 돌리고, 한 단계씩 실행하며 중간 결과를 눈으로
보면서 조립할 수 있습니다. GUI extras(`pip install -e ".[gui]"` = PySide6)가 필요합니다.

```powershell
py -3.11 studio.py          # 또는 설치되어 있다면: fullseye-studio
```

3개의 패널로 구성됩니다.

- **왼쪽(Operators)**: 연산자를 카테고리 / 검색으로 좁히고, **더블클릭으로 삽입**(Edit ▸ Focus operator search =
  **Ctrl+F**로 검색란으로 이동). 샘플 파이프라인도 여기서 불러올 수 있습니다. **Insert(＋)는 HDevelop의 연산자
  창과 동일**하며, 파이프라인에 단계를 추가하는 동시에 Program 창의 커서 위치에 `op (a, b)` 한 줄을 씁니다(값은
  `repr`의 전체 정밀도. Program에 아직 적용되지 않은 수동 편집이 있으면 그 줄만 삽입되고, Apply로 반영됩니다).
- **가운데(Pipeline)**: 배치된 단계 목록. 드래그나 Ctrl+↑/↓로 순서를 바꾸고, 선택한 단계의 **다이얼 a / b**를
  조정합니다. 다이얼은 항상 0..1 값이지만, **연산자별 표시 사양(`param_specs.py`)이 있는 경우 실제 단위로 조작할
  수 있습니다** — `gaussian`이라면 σ를 px로(슬라이더 + 단위가 붙은 스핀), `median`이라면 커널 크기를 3/5/7/9의
  콤보로, `reg_erode`라면 반복 횟수를 정수 스핀으로, `aug_barrel`의 b는 "pincushion" 체크박스로. 오른쪽 끝의 0..1
  스핀은 항상 원시 값입니다(정확한 입력용). 사양은 ops.py의 변환식(예: `0.3 + 2.7·a`)으로부터 수기로 작성했고,
  테스트로 구현과 대조하고 있습니다(`tests/test_studio_params.py`). 사양이 없는 연산자는 기존과 같이 0..1 슬라이더
  2개입니다. 단계 목록도 표시 단위로 기록됩니다(`gaussian (blur σ=1.08 px, b=–)`). **Reset(Home) → Step(Ctrl+→) →
  Run all(Ctrl+Enter)**로 한 단계씩, 또는 한 번에 실행할 수 있습니다.
- **오른쪽(Image / Perception / Analysis)**: 결과 이미지를 확대/축소·패닝하여 표시, 히스토그램, Inspector
  (image / region / feature 값 검사), v14의 지각 패널(옵티컬 플로우 / 스테레오 깊이 등). **이미지 뷰에서 우클릭**하면
  Fit / 1:1 / Zoom / Save result / Save view as shown / Copy / Display mode / 3D surface(메뉴와 동일한 동작)를
  실행할 수 있습니다. 추가로 연 그래픽스 창에도 Fit·1:1·±·Save의 작은 도구 모음과 같은 우클릭 메뉴가 붙고, 3-D
  뷰어(Ctrl+4)는 우클릭으로 Reset view / 1인칭(원근) 전환 / Wireframe / Save screenshot을 할 수 있습니다.

조립한 파이프라인은 **Export(Ctrl+E)**로 `--ops` 문자열이나 Python 코드로 내보낼 수 있고, **Save pipeline
(Ctrl+Shift+S)**로 JSON으로 저장할 수 있습니다. 전체 기능과 단축키는 [STUDIO_GUIDE.md](STUDIO_GUIDE.md)를, 앱
내에서는 **F1**로 목록이 나옵니다.

---

## 5. 저장한 파이프라인을 실행한다 (CLI / 코드)

Studio에서 `Save pipeline`한 JSON(또는 `--ops` 문자열)을, 그대로 파일에 대해 실행할 수 있습니다. 이것이
HDevEngine에 해당하는 "설계한 것을 다시 작성하지 않고 실행한다"는 경로입니다.

```powershell
# 저장한 JSON의 I/O와 각 단계를 확인(이미지 없이 구조만 점검)
py -3.11 imgevolve.py run edge.json --describe

# 이미지에 적용해 결과를 저장
py -3.11 imgevolve.py run edge.json in.png --out result.png

# 한 단계씩 결과를 저장(result_00.png, result_01.png, ...)
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# 파이프라인을 단독 Python 함수로 내보내기
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

코드에서 실행할 때는 `FullseyeEngine`을 사용합니다(자세한 내용은 [ENGINE.md](ENGINE.md)).

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 각 단계의 중간 결과(리스트)
```

---

## 6. CLI로 하나씩 적용한다

이미지 파일을 직접 처리하고 싶을 때는 CLI가 간편합니다(이미지 I/O에 OpenCV나 Pillow가 필요합니다).

```powershell
py -3.11 imgevolve.py ops --search edge                    # 연산자 검색
py -3.11 imgevolve.py has gauss_filter                      # 해당 HALCON 이름이 구현되어 있는지 + 호출 방법
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline`은 각 단계에서 공통의 `--a` / `--b`를 사용합니다. 단계마다 다른 다이얼을 쓰고 싶다면,
위의 `run_pipeline`(Python)이나 Studio를 사용하세요.

---

## 막혔을 때

| 증상 | 대처 |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | `pip install -e .`를 실행하거나, 저장소 최상위 디렉터리를 `PYTHONPATH`에 등록 |
| `fullseye` / `fullseye-studio` 명령이 없음 | 콘솔 스크립트는 `pip install -e .`로 등록됩니다. 설치하지 않았다면 `py -3.11 imgevolve.py ...` / `py -3.11 studio.py`를 사용 |
| Studio가 실행되지 않음 | GUI extras 미설치. `pip install -e ".[gui]"`(PySide6) |
| `apply` / `pipeline`에서 `cannot read ...` | 이미지 I/O용으로 OpenCV(`[opencv]`)나 Pillow(`[pil]`)를 설치 |
| 추가 백엔드의 연산자가 "unknown"으로 표시됨 | 해당 백엔드가 미설치. `.[skimage]` `.[wavelets]` `.[extra]` 등을 추가 |

더 상세한 문제 해결은 [INSTALL.md](INSTALL.md)를 참조하세요.

## 다음으로 읽을 것

- **[INSTALL.md](INSTALL.md)** — 환경 구축 완전 가이드(extras 사용 구분, Windows/Linux 설치 도구, 최소 구성·임베딩)
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — Fullseye Studio 완전 가이드
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine(설계 → 실행) 가이드
- **[README.md](README.md)** — 문서 색인
