<!-- i18n-source-sha: 8d925234d62d -->
# FullseyeEngine — 설계한 파이프라인을 실행하는 런타임

[日本語](./ENGINE.md) · [English](./ENGINE.en.md) · [简体中文](./ENGINE.zh.md) · [繁體中文](./ENGINE.tw.md) · **한국어** · [Deutsch](./ENGINE.de.md)

`FullseyeEngine`(`engine.py`)은 Fullseye Studio에서 **구성한** 이미지 오퍼레이터 파이프라인을 자신의 코드나 CLI에서 **실행하기** 위한 런타임입니다. MVTec의 **HDevEngine**에 해당하며, 시각적 도구로 절차를 설계하고 다시 작성할 필요 없이 그대로 애플리케이션에서 호출한다는 2단계 구조의 후반부를 담당합니다.

- **설계(author)**: Fullseye Studio → `Save pipeline`으로 JSON을 내보냅니다([STUDIO_GUIDE.md](STUDIO_GUIDE.md)).
- **실행(execute)**: `FullseyeEngine.load("pipeline.json").run(frame)` — **numpy 배열 입력, numpy 배열 출력**. 파일 I/O도 GUI도 필요 없습니다.

파이프라인은 `(op, a, b)`로 이루어진 단계 목록입니다. 엔진은 Studio의 JSON, `--ops` 문자열, Python 리스트 중 어느 것에서든 로드할 수 있으며, 입출력 sort를 확인하고, 각 단계의 노브를 조정하며, numpy 프레임에 대해(전체·중간까지·단계별로) 실행할 수 있습니다. 구조 검증(알 수 없는 오퍼레이터, sort 불일치)도 수행하며, 이는 Studio 진단 패널과 동일한 검사입니다.

---

## 가장 간단한 사용법

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 각 단계의 중간 결과(리스트)
```

`FullseyeEngine`과 `diagnose_stages`는 `fullseye`(및 `engine`)에서 공개되어 있습니다.

---

## 네 가지 로드 방법

| 구축 방법 | 시그니처 | 용도 |
|---|---|---|
| JSON 파일 | `FullseyeEngine.load(path)` | Studio의 `Save pipeline` 출력을 읽음 |
| ops 문자열 | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | `"gaussian,sobel_amp,otsu"`와 같은 콤마 구분(공통 노브) |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | `{"stages": [...]}`를 가진 딕셔너리로부터 |
| 단계 리스트 | `FullseyeEngine(stages=None, name="pipeline")` | `[("gaussian",0.4,0.5), "otsu"]`를 직접(이름만 있는 단계는 a=b=0.5) |

`from_dict`는 `"stages"` 키가 없으면 `ValueError`를 발생시킵니다. `load`는 JSON을 읽어 `from_dict`에 전달하고, 파일명(확장자 제외)을 `name`으로 사용합니다.

---

## 메서드 목록

| 메서드 | 반환값 | 설명 |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | Studio의 JSON에서 로드 |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | 콤마 구분 ops 문자열에서(공통 노브) |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | `{"stages": [...]}`에서 로드 |
| `describe()` | `list[dict]` | 각 단계의 `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | 각 단계의 오퍼레이터 이름 |
| `input_sort()` | `str \| None` | 파이프라인이 기대하는 입력 sort(첫 번째 알려진 op의 in_sort) |
| `output_sort()` | `str \| None` | 파이프라인이 반환하는 출력 sort(마지막 알려진 op의 out_sort) |
| `validate()` | `list[dict]` | 구조적 문제 `{index, op, severity, message}`. `[]`이면 정상 |
| `is_runnable()` | `bool` | 모든 단계가 알려진 오퍼레이터로 해석되면(error가 없으면) `True` |
| `get_knobs(i)` | `tuple` | 단계 `i`의 노브 `(a, b)` |
| `set_knobs(i, a=None, b=None)` | `self` | 단계 `i`의 노브를 변경(체이닝 가능) |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | 파이프라인 실행. `upto`로 0..upto 단계만 실행 |
| `run_stepwise(image, coerce=True)` | `list` | 각 단계 적용 후의 중간 결과(길이 = 단계 수) |
| `run_file(in_path, out_path=None, upto=None)` | 원시 결과 | 이미지를 읽고 실행한 뒤, 래스터 결과면 선택적으로 저장 |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | 콤마 구분 ops 문자열 |
| `to_python()` | `str` | 단일 Python 함수 소스(Studio의 Export와 동일) |
| `save(path)` | `None` | `to_dict()`를 JSON으로 저장 |
| `len(eng)` | `int` | 단계 수 |

`diagnose_stages(stages)`는 엔진을 생성하지 않고도 단계 리스트를 검증하는 함수로, `validate()`의 실체입니다. `severity`는 알 수 없는 오퍼레이터의 경우 `"error"`, 인접 단계의 sort 불일치는 `"warning"`입니다.

### sort(타입)에 대해

각 오퍼레이터는 입력/출력의 **sort**를 선언합니다: `image`(gray H×W float64 [0,1]) / `region`(이진 {0,1}) / `color`(H×W×3 RGB) / `feature`(스칼라 float) / `contour`(XLD dict) / `volume`(3D 스택) / `any`(무엇과도 연결 가능). `validate()`는 인접 단계의 out→in이 어긋나면 경고를 출력합니다(`any`는 항상 정합).

---

## Python에서의 사용 예

### 검증 후 실행

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # error(알 수 없는 op)가 있으면 중단
    raise SystemExit(problems)
result = eng.run(frame)                         # region(이진)을 반환
```

### 중간까지 / 단계별로

```python
mid = eng.run(frame, upto=1)                    # 0..1 단계까지(gaussian → sobel_amp)
for i, s in enumerate(eng.run_stepwise(frame)):  # 각 단계의 중간 결과
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### 노브를 조정하여 재실행

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # 체이닝 가능
out = eng.run(frame)
```

### 파일 입출력(코드 안에서 완결)

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # 읽기 → 실행 → 래스터면 저장
```

### 저장 / 내보내기

```python
eng.save("edge.json")                           # JSON으로 저장(Studio에서 다시 열 수 있음)
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # 단일 Python 함수로 출력
```

`to_python()` 출력 예시:

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

저장한 파이프라인(JSON 또는 ops 문자열)을 CLI에서 실행할 수 있습니다. 내부적으로 `FullseyeEngine`을 사용합니다.

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| 인수 / 옵션 | 의미 |
|---|---|
| `pipeline` | 파이프라인 `.json`(Studio의 Save pipeline) 또는 콤마 구분 ops 문자열 |
| `inp` | 입력 이미지(생략 시 `--describe` / `--to-python`만 실행 가능) |
| `--out PATH` | 결과 저장 경로(래스터 결과만 저장) |
| `--upto N` | 0..N 단계까지 실행 |
| `--stepwise` | 각 단계의 결과를 보고하며, `--out` 지정 시 `PATH_00`, `PATH_01`, … 로 저장 |
| `--describe` | 파이프라인의 I/O와 각 단계·검증 결과를 표시(입력이 없으면 표시만 하고 종료) |
| `--to-python` | 파이프라인을 Python 함수로 출력 |
| `--a` / `--b` | ops 문자열로 생성할 때의 공통 노브(기본값 0.5) |

예:

```powershell
# 구조만 확인(이미지 불필요)
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # 실행하여 저장
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # 각 단계를 저장
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops 문자열 → Python
```

알 수 없는 오퍼레이터(error)를 포함한 파이프라인은 `--describe`로는 표시할 수 있지만, 실행 시에는 중단되어 문제를 보고합니다.

---

## 다른 프로젝트에서의 호출(onocollo / evis / hillco 등)

`fullseye`는 numpy 배열로 입출력이 완결되므로, 로보틱스/비전 파이프라인에 직접 연결할 수 있습니다. **설계는 Studio, 실행은 각 프로젝트**라는 역할 분담이 가능합니다.

```python
import fullseye

# 시작 시 한 번만 로드(가벼움. ops 해석 결과와 노브만 보유)
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: 직접 준비한 float64 gray [0,1]
    seg = PIPELINE.run(frame)                   # numpy 입력, numpy 출력(디스크 불필요)
    return seg
```

포인트:

- **파일 I/O 불필요**: 센서/시뮬레이터에서 얻은 numpy 프레임을 직접 전달하고 numpy를 받을 수 있습니다. 임베디드나 GPU 시뮬레이션 환경에서도 I/O 백엔드 없이 동작합니다.
- **경량**: `load` / `from_ops`는 오퍼레이터 이름과 노브만 보유합니다. 무거운 연산은 `run` 호출 시에만 발생합니다.
- **버전 독립**: 파이프라인 JSON은 데이터이므로, 파이프라인을 교체해도 호출 측 코드는 변하지 않습니다. 연구 반복(파이프라인을 Studio에서 조정 → JSON 업데이트)이 사용 측에 영향을 주지 않습니다.
- **단일 오퍼레이터로 충분하다면** `fullseye.apply(frame, "otsu")`, 여러 단계라면 `fullseye.run_pipeline(frame, [...])`를 직접 호출해도 됩니다(엔진을 거치지 않는 가벼운 경로).

지각 스택(stereo / terrain / flow / detect / registration / pose)도 마찬가지로 numpy로 동작합니다(`fullseye.disparity_map` 등). 사용 예는 `examples/`([../examples/README.md](../examples/README.md))와 [PERCEPTION.md](PERCEPTION.md) / [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md)를 참고하십시오.

---

## 관련 문서

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) — 파이프라인을 구성하고 JSON을 내보내기
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5분 만에 시작하기
- [INSTALL.md](INSTALL.md) — 환경 구축(임베디드·최소 구성 포함)
