<!-- i18n-source-sha: a77086926760 -->
# Fullseye Studio 완전 가이드

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · [简体中文](./STUDIO_GUIDE.zh.md) · [繁體中文](./STUDIO_GUIDE.tw.md) · **한국어** · [Deutsch](./STUDIO_GUIDE.de.md)

**Fullseye Studio**는 HDevelop풍의 시각적 파이프라인 워크벤치입니다. 연산자를 검색해 배치하고, 2개의 다이얼을 슬라이더로 돌리고, 중간 결과를 확대/축소·패닝하며 한 단계씩 실행하고, 완성된 파이프라인을 `--ops` 문자열 / Python / JSON으로 내보낼 수 있습니다. 실체는 `fullseye` API의 얇은 GUI 프런트엔드이며, 파이프라인 로직(`PipelineModel`)·Inspector(`inspect_result`)·샘플 모음(`recipes`)은 모두 Qt에 의존하지 않고 개별적으로 단위 테스트되어 있습니다.

이 가이드는 `studio.py`(`build_window`)를 실제 코드와 대조해 기능을 나열한 것입니다. UX/디자인 의도는 [STUDIO_UX.md](STUDIO_UX.md)에, v14 지각 패널의 배경은 [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md)에 있습니다.

---

## 실행 방법

GUI extras(PySide6)가 필요합니다(`pip install -e ".[gui]"`).

```powershell
py -3.11 studio.py          # 저장소 루트에서 직접
fullseye-studio             # pip install -e .가 되어 있다면 콘솔 스크립트로
```

실행하면 1320×860 크기의 메인 창이 열립니다(제목: Fullseye Studio). `assets/fullseye.ico`가 있으면 창/작업 표시줄 아이콘으로 붙습니다. 초기 상태에서는 합성 데모 이미지(`demo_image`, 에지·블롭·그라디언트를 포함한 256×256)가 로드되어 있습니다.

---

## 화면 구성 (3개 패널)

상단에는 **메뉴 바**(File / Edit / View / Run / Help)와 **브랜드 툴바**, 하단에는 **상태 표시줄**(마우스를 올렸을 때의 좌표+픽셀 값, `flash()`의 일시적 메시지)이 있습니다. 중앙은 좌우로 나뉜 3개 패널입니다.

| 패널 | 구획(QGroupBox) | 역할 |
|---|---|---|
| 왼쪽 | **SAMPLE PIPELINES** / **OPERATORS** | 샘플 로드와 연산자 브라우저 |
| 가운데 | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | 파이프라인 구성·다이얼 조정·내보내기 |
| 오른쪽 | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | 결과 표시·컬러맵/지각·히스토그램/Inspector |

초기 분할 폭은 340 / 360 / 640 px이며, 오른쪽 패널이 신축합니다.

---

## 왼쪽 패널: Operators 브라우저

### 샘플 파이프라인(SAMPLE PIPELINES)
드롭다운에서 **20개**의 기성 레시피(`recipes.py`) 중 하나를 선택하면, 파이프라인이 그 레시피로 교체됩니다. 예: "Edge — Sobel + Otsu", "Denoise — bilateral + unsharp", "Segment — blob / coin", "Count — blobs", "Texture — Gabor" 등. 우선 실행해 보며 내용을 파악하는 출발점으로 편리합니다.

### 연산자 브라우저(OPERATORS)
- **카테고리 필터**: "all categories" + 31개 카테고리(smoothing / edges / morphology / segmentation / features / texture / region / contour / color / frequency / restoration / 3d …).
- **검색란**: 연산자 이름·HALCON 별칭·카테고리를 부분 일치로 필터링(지우기 버튼 포함).
- **목록**: 각 행에 `name [in_sort → out_sort]`를 표시. **더블클릭으로 삽입**. 마우스를 올리면 툴팁으로 "이름 / HALCON 별칭 / 카테고리 / sort 변환 / 다이얼 a,b 설명"이 나타납니다.

삽입 위치는 "선택된 단계의 바로 다음"입니다. 단계를 선택하지 않았다면 맨 끝에 추가됩니다.

---

## 가운데 패널: 파이프라인 구성과 단계 실행

### PIPELINE(단계 목록)
각 행은 `N. op (a=…, b=…) -> 결과 요약` 형식이며, 그 단계까지 실행한 결과 상태(image/region/feature 등)가 오른쪽에 표시됩니다.

- **순서 변경**: 행을 드래그(InternalMove)해 바꾸거나, **↑ Up / ↓ Down** 버튼·**Ctrl+↑ / Ctrl+↓**를 사용.
- **삭제**: **Remove** 버튼·**Del**.
- **단계 실행용 3개 버튼**:
  - **⏮ Reset(Home)** — 파이프라인을 적용하기 전의 원본 이미지를 표시(단계 실행의 시작점).
  - **Step ▶(Ctrl+→)** — 한 단계 진행.
  - **Run all ▶▶(Ctrl+Enter)** — 최종 결과까지 한 번에 표시(주 강조색 버튼).

단계를 선택하면 그 단계까지의 중간 결과가 오른쪽 IMAGE 패널에 그려지고, 아래의 ANALYSIS(히스토그램 / Inspector)도 함께 갱신됩니다. 이는 "단계별 디버거"에 해당합니다.

### SELECTED STAGE · KNOBS(다이얼 조정)
선택한 단계의 상세 정보(`op_detail`: 이름·`in → out` sort·카테고리·HALCON 별칭)를 표시하고, **2개의 슬라이더 a / b(0.00~1.00)**로 조정합니다. 값을 움직이면 즉시 결과가 재계산됩니다. 단계를 선택하지 않았을 때는 슬라이더가 비활성화됩니다(의미 없는 다이얼을 죽은 상태로 두지 않는 설계).

다이얼의 의미는 연산자마다 다릅니다(반경 / 임계값 / σ / 방향 등). 무엇을 조정하는지는 단계 상세 레이블과 툴팁으로 확인할 수 있습니다.

### EXPORT & I/O
- **Export(ops string + Python)…(Ctrl+E)** — 현재 파이프라인을 `--ops "…"` 문자열과 단독 실행 가능한 Python 함수, 두 가지 형태로 대화상자에 출력(복사용).
- **Save pipeline…(Ctrl+Shift+S)** — 파이프라인을 JSON으로 저장(`{"fullseye_pipeline": 1, "stages": [...]}`). 이 JSON이 `FullseyeEngine.load` / `imgevolve.py run`의 입력이 됩니다.
- **Open pipeline…(Ctrl+Shift+O)** — 저장한 JSON을 불러오기.

---

## 오른쪽 패널: 표시·지각·분석

### IMAGE(결과 뷰)
- **Load image…(Ctrl+O)** — 이미지 파일을 기준 프레임으로 불러오기(png/jpg/bmp/tif).
- **Synthetic demo(Ctrl+D)** — 합성 데모 이미지를 불러오기.
- **Save result…(Ctrl+S)** — 표시 중인 결과를 PNG로 저장.
- **줌**: 마우스 휠로 커서 위치를 기준으로 확대/축소, 드래그로 패닝. **Zoom +(Ctrl+=) / Zoom −(Ctrl+-) / Fit(Ctrl+0) / 1:1(Ctrl+1)**.
- 스칼라 feature 결과·contour 결과·이미지 미로드 상태일 때는 뷰 중앙에 메시지를 표시합니다(빈 화면으로 두지 않음).
- 마우스를 올리면 상태 표시줄에 `x, y, value`(컬러라면 RGB)를 표시합니다.

### DISPLAY & PERCEPTION (v14)
- **Display(컬러맵)** — 2D 결과를 표시용으로 채색: `gray` / `shaded relief` / `height (color)` / 각종 컬러맵(jet, viridis, turbo, magma, plasma, inferno …).
- **3D surface(Ctrl+3)** — 현재 결과를 회전 가능한 3D 표면으로 표시(`QtDataVisualization`이 있을 때만／best-effort). 높이/깊이 맵 확인에 사용.
- **지각 패널(2 프레임)** — **Load frame B…**로 두 번째 프레임을 불러오고, 모드를 선택한 뒤 **Run**:
  - `optical flow` — 두 프레임 사이의 밀집 광류를 색상으로 시각화.
  - `motion overlay` — 움직이는 영역을 원본 이미지에 겹쳐 표시.
  - `stereo depth` — 스테레오 시차로부터 깊이를 추정해 채색.
  - `stereo terrain` — 스테레오→포인트 클라우드→지형 높이맵을 채색.

  프레임 B가 없거나 크기가 일치하지 않으면 상태 표시줄에 오류를 표시하고 안전하게 중단합니다.

### ANALYSIS
- **Histogram** — 현재 2D 결과의 밝기 히스토그램.
- **Inspector(variable / image / region)** — sort에 따라 결과를 검사. image/color는 shape·min/max/mean·비유한값 개수, region은 연결 요소 수·면적·최대 영역, feature는 값, contour는 윤곽선 수를 표시. 이진 영역일 때는 각 영역의 특징 표(`detect.feature_table`)도 함께 표시됩니다.

---

## Command palette(Ctrl+P)

`Ctrl+P`를 누르면 **이름으로 어떤 동작이나 어떤 연산자든 실행**할 수 있는 퍼지 검색 대화상자가 열립니다. 접두 일치 > 단어 접두 일치 > 부분 일치 순으로 순위가 매겨집니다(`palette_filter`, Qt에 의존하지 않고 단위 테스트됨). 동작(예: `▸ Open image`)이 먼저 나오고, 이어서 모든 연산자(예: `op: gaussian`)가 나열되며, Enter로 실행합니다. 키보드만으로 연산자 삽입까지 완결할 수 있습니다.

---

## 키보드 단축키

앱 내에서는 **Help ▸ Keyboard shortcuts(F1)**로 전체 목록이 표로 표시됩니다(자체 문서화). 주요 항목(`studio.py`의 `act_*` 정의 기준):

| 동작 | 단축키 | 동작 | 단축키 |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+Backspace` |
| Open pipeline | `Ctrl+Shift+O` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Save pipeline | `Ctrl+Shift+S` | Fit / Actual size (1:1) | `Ctrl+0` / `Ctrl+1` |
| Export | `Ctrl+E` | 3D surface | `Ctrl+3` |
| Quit | `Ctrl+Q` | Reset to start | `Home` |
| Command palette | `Ctrl+P` | Step forward | `Ctrl+→` |
| Keyboard shortcuts | `F1` | Run all | `Ctrl+Enter` |

각 동작은 메뉴·툴바·버튼 중 어느 것에서 호출하든 동일한 핸들러가 실행됩니다(하나의 동작, 여러 개의 입구).

---

## HDevelop `dev_*` 렌더링 제어 지시문

HDevelop과 마찬가지로, **프로그램에서 렌더링 동작을 제어**할 수 있습니다. Program 창의
스크립트에 `dev_*` 행을 쓰면, 이미지 단계가 아니라 **표시 지시문**으로 해석되어
Apply 시 적용됩니다(`docs/HDEVELOP_DEV_OPS.md`에 전체 43개 `dev_*`가 망라되어 있습니다).

| 지시문 | 효과 | 대응 UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | 그래픽 창의 자동 갱신 전환 | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | 변수 창의 자동 갱신 전환 | 위와 동일, Variable window |
| `dev_update_pc ('off'|'on')` | 실행 커서 갱신 전환 | 위와 동일, Program counter |
| `dev_update_time ('off'|'on')` | 행별 처리 시간 표시 전환 | 위와 동일, Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | 위 항목 전체를 일괄 off / on | 툴바 **Auto-update** 토글 |
| `dev_set_part (Row1, Col1, Row2, Col2)` | 표시 범위(확대/이동) 설정·음수=전체 | 마우스 휠/Fit과 병용 |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | 컬러맵(LUT) 전환 | View ▸ Display mode |
| `dev_clear_window ()` | 현재 창을 지움 | — |
| `set_system ('thread_num', N)` | OpenCV 작업 스레드 수 설정(0=기본/전체) | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | 소프트 연산자 타임아웃(느린 단계를 Run status에서 경고) | 위와 동일 |
| `dev_set_draw ('fill'|'margin')` | region 오버레이의 채우기(fill)/윤곽(margin) 전환 | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | region 오버레이 색상 | 위와 동일 |
| `dev_set_line_width (N)` | margin 윤곽선 두께(px) | 위와 동일 |
| `dev_disp_text ('label', Row, Col)` | 결과 위에 텍스트 주석 추가(다음 렌더링/`dev_clear_window`에서 사라짐) | — |
| `dev_open_window (Row, Col, W, H)` | 그래픽 창을 **열어서 배치하고 현재 창으로 지정**(다시 Apply해도 같은 창을 재배치=증식하지 않음) | Ctrl+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | 핸들로 현재 창 전환 | 창 클릭 |
| `dev_set_window_extents (Row, Col, W, H)` | 현재 창의 위치·크기(-1=현재 상태 유지) | 창 드래그 |
| `dev_close_window ()` | 현재 창을 닫음(상주하는 메인 창은 보호됨) | 창의 × |
| `set_system ('max_graphics_windows', N)` | 창 개수 상한(기본 256·모든 경로 fail-closed) | Tools ▸ System settings ▸ Windows |

**용도**: 맨 앞에 `dev_update_off ()`를 두면 **렌더링 비용 없이** 무거운 처리나 대량 편집을 할 수 있고,
`dev_update_on ()`으로 현재 상태까지 한 번에 갱신할 수 있습니다(HDevelop의 성능 기법과 동일). 갱신이
꺼져 있는 동안에는 상태 표시줄 오른쪽에 `updates off: …`가 표시되므로, 정지된 상태가 "고장난 것처럼"
보이는 일은 없습니다. 툴바의 **Auto-update** 토글로도 동일하게 전환할 수 있습니다.

**주의**(정직한 고지): `dev_*`는 파이프라인 단계와 달리 `if`/`for`를 따르지 않고 **무조건 적용**됩니다
(분기 안에 두어도 실행됩니다). 최상위 레벨에 작성하세요. 지원되지 않는 `dev_*`는 오류가 됩니다.

**직접 실행해 보기**: **File ▸ dev_* visualization demo**를 실행하면, coins 이미지 + 위의 `dev_*`를
실제로 사용하는 HDevelop 프로그램(분할→영역을 청록색 윤곽선 + 레이블로 표시)이 로드되어 적용됩니다.
연습용 샘플 이미지는 **File ▸ Sample images**(8장, 출처는 `studio_assets/sample_images/manifest.json`
참조. 합성 이미지 = 자체 제작물／`coins`·`camera` 등 = skimage.data의 BSD/퍼블릭 도메인 소재.
`tools/gen_sample_images.py`로 재생성 가능)에 있습니다.

---

## 다국어 지원(en / ja / zh, 표 기반)

UI 언어는 **Tools ▸ Language / 言語 / 语言**에서 전환할 수 있습니다(선택이 기억됩니다). 번역문은
**`studio_assets/i18n.json`**에 일원화된 표로 관리되며, 코드 변경 없이 언어를 추가할 수 있습니다:

- `languages` — 언어 목록(추가하면 메뉴에 자동으로 표시. 영어가 항상 기준)
- `tooltips` — 툴팁 번역문(영어 원문이 키)
- `strings` — **메뉴·버튼·대화상자 레이블 번역문**(영어 원문이 키. 2026-08-30
  추가. 일본어 40개 이상 항목 동봉, 미번역 문자열은 영어 그대로=우아한 저하)
- `guide` — 퀵 가이드 본문(Shift+F2)

연산자 도움말은 `op_help/<name>.<lang>.html`이 있으면 언어별로 표시됩니다. 정직한 고지:
실행 중 변화하는 상태 문구(`running…` / `PASS` 등)와 연산자 노트 본문은 현재
번역 대상이 아닙니다(연산자 노트의 영어화는 docstring 이중 언어화와 세트인 향후 과제입니다).

## Python 편집기와 IDE 기능(2026-08-30)

Studio는 "파이프라인에서만 코드를 호출할 수 있는" 단계를 넘어, **Python 개발 환경**으로도 사용할 수 있습니다.

- **Python Editor**(File ▸ Python Editor… / 갤러리의 "Open in editor"): 구문 강조 표시+
  줄 번호+자동 들여쓰기를 갖춘 **다중 탭** 편집기(HDevelop의 메인+서브 스크립트와 마찬가지로,
  여러 스크립트를 동시에 편집). **F5 / Run**으로 현재 탭을 서브프로세스에서 실행(저장소가
  PYTHONPATH에 등록되므로 `import fullseye`가 그대로 동작. 저장하지 않은 버퍼는 임시 사본으로
  실행되어 Save를 강제하지 않음). **Samples ▾**에서 모든 예제를 새 탭으로 열 수 있음(경로 없이
  열리므로 출하 시 샘플을 실수로 덮어쓸 수 없음). 실행에 사용할 인터프리터는 System settings ▸
  Editor에서 변경 가능.
- **MDI 코드 창**(갤러리의 "Open in window"): 예제 코드를 독립된 창으로
  **몇 개든 나란히** 배치해 일부를 선택해 복사할 수 있음(Window ▸ Tile/Cascade도 동작).
- **실행 제어**: 거터를 클릭해 중단점(=일시 정지) 설정, **Continue** 버튼으로 실행 중인 줄에서
  다음 중단점/끝까지 재개, 단계를 우클릭한 **Run from here**로 임의의 줄부터 다시 시작
  (**Run to here**와 대응).
- **변수 감시**: Variables 창에 임의의 표현식(`v.mean()` / `np.percentile(v, 99)` /
  `(v > 0.5).sum()` 등. `v`=선택된 변수, `np`=numpy, `img`=입력)을 등록하면, 선택 변경이나
  파이프라인 변경 때마다 **자동으로 재평가**됩니다. 평가에 실패한 표현식은 그 줄에 ⚠가 표시됩니다
  (패널은 죽지 않음). 변수를 **우클릭 ▸ Inspect in popup…**하면 타입별 검사+백분위수+값 미리보기가
  즉시 표시됩니다. 알려진 제약(정직한 고지): 감시 표현식은 GUI 스레드에서 동기적으로 평가되므로,
  **매우 무거운 표현식**(거대 배열 전체 스캔 등)은 그동안 UI가 멈춥니다. 무거운 집계는 표현식을
  가볍게 하거나 Python Editor 쪽에서 실행하세요.
- **System settings**(Tools ▸ System settings… / Ctrl+,): 카테고리 트리+페이지 구성.
  Execution(스레드 수 / 타임아웃)·Windows(창 개수 상한)·Display(기본 LUT / region 렌더링)·
  Editor(글꼴 크기 / 실행 인터프리터).

## Export와 Save/Open의 관계

Studio에서 구성한 파이프라인은 3가지 형태로 가지고 나갈 수 있습니다.

| 형식 | 내보내는 방법 | 사용처 |
|---|---|---|
| `--ops` 문자열 | Export(Ctrl+E) | CLI의 `imgevolve.py pipeline --ops "…"` / `run "…"`에 붙여넣기 |
| Python 함수 | Export(Ctrl+E) | 자신의 코드에 `fullseye.run_pipeline(...)`로 내장 |
| JSON | Save pipeline(Ctrl+Shift+S) | `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json`으로 실행 |

**설계는 Studio에서, 실행은 코드/CLI에서**라는 HDevelop→HDevEngine에 해당하는 흐름은 JSON을 매개로 이루어집니다. JSON을 받아 실행하는 쪽은 [ENGINE.md](ENGINE.md)를 참조하세요.

---

## 관련 문서

- [STUDIO_UX.md](STUDIO_UX.md) — 디자인 시스템·UX 개선의 의도와 배경(디자인 관점)
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — 지각 패널의 내용(flow / stereo / terrain)
- [ENGINE.md](ENGINE.md) — 내보낸 파이프라인 실행하기
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5분 만에 시작하기
