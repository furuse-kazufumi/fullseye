# Fullseye 문서 색인

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **참고:** 지금 번역되어 있는 것은 이 색인 페이지뿐입니다. 여기서 링크되는 개별 문서는 당분간 일본어판만 있습니다.

**Fullseye**(작업명 imgevolve)는 HALCON/HDevelop 급의 실용 도구입니다. numpy 네이티브 이미지 처리 연산자 라이브러리에, HDevelop 스타일의 비주얼 파이프라인 설계 환경(Fullseye Studio)과 실행 런타임(FullseyeEngine)을 갖추고 있습니다. 연산자는 약 **521**개(레지스트리 기준), 실제 HALCON 연산자 **269/2313**개를 genuine(이름만이 아니라 진짜로 같은 동작을 하는) 구현으로 제공하며, 31개 카테고리를 아우릅니다.

> **여기서 시작하세요 → [GETTING_STARTED.md](GETTING_STARTED.md) (5분이면 돌려볼 수 있습니다)**

---

## 사용법 (사용자용 — 우선 이 네 가지)

| 문서 | 내용 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5분 만에 시작하기: 설치 → 첫 파이프라인 → Studio／CLI／코드에서 실행 → 결과 확인 |
| **[INSTALL.md](INSTALL.md)** | 환경 구축 완전 가이드: 전제 조건, `pip install -e .`와 extras 선택 기준, Windows／Linux 설치 프로그램, 최소 구성과 임베디드 통합, 문제 해결 |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 완전 가이드: 3개 패널, 연산자 브라우저, 단계 실행, 파라미터 노브, Inspector, 퍼셉션 패널, 명령 팔레트, 단축키, 내보내기 |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine(설계 → 실행): 모든 메서드, Python에서 쓰는 법, CLI `run`, 다른 프로젝트에서 호출하기 |

---

## 연산자 / API 레퍼런스

| 문서 | 내용 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 521개 연산자 전체 카탈로그(31개 카테고리, sort별 정리, HALCON／OpenCV／scikit-image／MATLAB의 대응 API 포함) |
| [EXAMPLES.md](EXAMPLES.md) | 연산자별 예제 코드(다른 라이브러리에서의 동등한 호출 포함) |
| [OP_INDEX.json](OP_INDEX.json) | 기계가 읽을 수 있는 연산자 색인(`imgevolve.py index`로 다시 생성) |
| [ADDING_OPS.md](ADDING_OPS.md) | 새 연산자를 추가하는 방법(진화·codegen·카탈로그·색인이 자동으로 따라옵니다) |
| [../examples/README.md](../examples/README.md) | 그대로 실행할 수 있는 엔드투엔드 예제 스크립트 모음 |

## 퍼셉션 스택 (로보틱스 / 비전)

| 문서 | 내용 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 퍼셉션 스택 한 장 레퍼런스(stereo／terrain／detect／registration／pose／flow／motion) |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 실제 촬영 클립에서의 측정 결과(비디오 I/O ＋ 정직하게 밝힌 실측값) |

## HALCON 패리티 / 커버리지 (정직한 공개, honest disclosure)

| 문서 | 내용 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | genuine(진짜) 구현 현황(269/2313) — "이름만 같은" 것이 아니라 실제로 같은 처리를 해내는지 |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 공식 레퍼런스(v2605)를 실제로 스크레이핑해서 측정한 커버리지 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 여러 라이브러리를 가로지르는 커버리지(HALCON 밖의 특색 있는 연산자 흡수) |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 독립적으로 만든 구현(scipy／cv2／skimage) 사이의 백엔드 간 일치로 패리티를 입증 |

## 품질 / 출처 이력 / 재현

| 문서 | 내용 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 상설 정확도 표: 진화로 얻은 champion 대 null 기준선(holdout) |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 체인 퍼저 — 연산자를 사슬로 엮어 흔들어 보는 세 번째 품질 보증 계층(확산 → 수렴 → 최소 재현) |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 진화형 알고리즘 개발 환경(확산 → 수축 → 승격. counterfactual utility 게이트와 두 연산자 우주를 잇는 다리) |
| [PROVENANCE.md](PROVENANCE.md) | 출처 이력: 공개된 알고리즘을 바탕으로 직접 만든 것임을 밝히는 기록 |
| [REFERENCES.md](REFERENCES.md) | 각 연산자의 문헌적 근거 |
| [REPRODUCE.md](REPRODUCE.md) | 수치를 재현하는 절차: seed로 구동되는 결정론적 방식 |
| [STATUS.md](STATUS.md) | 프로젝트의 현재 위치와 앞으로의 계획(plan_ref) |

## 릴리스 노트 / 설계

| 문서 | 내용 |
|---|---|
| [V13.md](V13.md) | v13 ＝ 실용화 ＋ 프로젝트 간 packaging ＋ 퍼셉션 스택 |
| [V14.md](V14.md) | v14 ＝ 퍼셉션 스택 완성(모션 ＋ 견고화) |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio의 UX／디자인 개선 의도와 배경 |

---

## 빠른 명령

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 설치(이미지 I/O + Studio)
py -3.11 studio.py                              # Fullseye Studio 실행(= fullseye-studio)
py -3.11 imgevolve.py ops --search edge         # 연산자 검색(= fullseye ops --search edge)
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # 정직한 커버리지 수치
```

Python에서:

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
