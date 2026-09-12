<!-- i18n-source-sha: bd321cfbdaaa -->
# 범용 알고리즘을 구현 가능하게 만들기 — algo-c 대응 로드맵

[日本語](./GENERAL_ALGORITHMS.md) · [English](./GENERAL_ALGORITHMS.en.md) · [简体中文](./GENERAL_ALGORITHMS.zh.md) · [繁體中文](./GENERAL_ALGORITHMS.tw.md) · **한국어** · [Deutsch](./GENERAL_ALGORITHMS.de.md)

> 사용자 요청(2026-08-16): <https://github.com/okumuralab/algo-c>(오쿠무라 하루히코(奥村晴彦)
> 『[개정신판] C언어에 의한 표준 알고리즘 사전』전체 소스)에 있는 것과 같은 **범용 알고리즘**도
> Fullseye에서 구현할 수 있게 하고 싶다.
>
> **솔직한 현재 인식**: Fullseye는 현재 **이미지 알고리즘 설계 AI**(op 레지스트리 = image/region/
> feature/contour/volume의 sort, 진화 + holdout gate + Python→C codegen). 범용 알고리즘
> (정렬/탐색/그래프/수론/암호/압축)은 이미지 sort에 올라가지 않으므로 **언어·타입·codegen 확장**이 필요하다.
> 이는 여러 세션에 걸친 작업이다. 본 doc은 그 **확정 계획**(다음 세션이 full context로 실행할 정본)이다.

## algo-c의 카테고리(서적 목차·구현 대상 맵)
※ 엄밀한 망라는 repo의 `/src`를 정본으로 한다.

| 분야 | 대표 알고리즘 | Fullseye에서의 수용처 |
|---|---|---|
| 수치계산 | 방정식(이분법/Newton), 수치적분(Simpson/Romberg), 연립일차(Gauss/LU), 보간(spline), FFT | 기존 `dsp`(FFT) + 신규 `numeric` op 계열 |
| 난수·통계 | Mersenne Twister, 분포, 통계량 | 신규 `rng`/`stat` op(결정적 seed) |
| 정렬 | quick/heap/merge/shell/radix | 신규 `array` sort + `seq` 타입 |
| 탐색 | 이분탐색, 해시, BST/AVL/B-tree | 신규 `array`/`map` op |
| 문자열 | KMP/BM/Rabin-Karp, 편집거리, 정규표현식 | 신규 `text` 타입 + op |
| 그래프 | DFS/BFS, Dijkstra, Warshall-Floyd, MST, 최대유량 | 신규 `graph` 타입 + op |
| 기하 | 볼록껍질, 선분교차, 보로노이 | 기존 `pcseg`/기하 + 신규 `geom2d` |
| 수론·암호 | 소수, GCD, RSA, MD5/SHA, AES | 신규 `numtheory`/`crypto`(교육용·honest 공개) |
| 데이터 압축 | Huffman, LZ/LZW, 산술부호화 | 신규 `compress` op |
| DP/탐색 | 8-queens, 배낭문제, DP | fscript의 제어흐름 + `array` |

## 구현 아키텍처(확정 방침)
Fullseye의 기존 자산을 범용으로 확장한다. **이미지 AI의 초점은 흐리지 않는다**(범용 op는 별도 tier / opt-in).

1. **타입 시스템 확장**: 현재 6+1 sort(image/region/feature/contour/match/any/volume)에
   **`seq`(1-D 배열)/`text`(문자열)/`graph`/`scalar`**를 추가(`ops.py`의 sort·`fslib` 타입).
2. **fscript의 범용 언어화**: 이미 if/for/while·대입·튜플이 있다. **배열/문자열 리터럴,
   인덱싱, procedure(함수)**를 단계적으로 추가(현재는 언어 스코프를 좁히는 결정이었으므로,
   범용 tier는 별도 프로파일로 해금). 정본 = `docs/FSCRIPT_DECISION.md`의 A/B 분기를 재검토.
3. **op 레지스트리 확장**: algo-c의 각 알고리즘을 **op**(name/in-out sort/params/**c_stmt**)로
   등록. 기존 Python→C codegen(`engine.to_python`/`to_c`) + **difftest**(honest gate: Python이
   oracle, C를 차분 검증)을 그대로 재사용 → **「C로 구현 가능하다」를 실측으로 보증**.
4. **honest gate**: algo-c의 C를 참조 구현으로 `difftest`에 넣고, Fullseye codegen의 C와
   수치/비트 일치를 검증(기존 gate의 확장). **원 코드의 라이선스**(algo-c = 서적 부속,
   이용조건 확인 필요)를 존중하고, **그대로 베끼지 않고 사양으로부터 재구현**(공개 공개 정책).

## 단계 계획(다음 세션 이후)
- **P1**: `seq`/`scalar` 타입 + 정렬 3종(quick/heap/merge)을 op화 + C codegen + difftest.
  = 「Fullseye는 범용 알고리즘도 C 생성할 수 있다」최소 실증.
- **P2**: 수치계산(이분법/Newton/Simpson/Gauss) op 계열.
- **P3**: 문자열(KMP/BM/편집거리) + `text` 타입.
- **P4**: 그래프(Dijkstra/BFS/MST) + `graph` 타입.
- **P5**: 압축/수론/암호(교육용·honest 공개, 그대로 베끼기 금지).
- 각 P에서: 진화 gate는 비대상(범용 op는 결정적·holdout 진화하지 않음), **difftest로 C 일치를 honest 실측**,
  Studio의 op 브라우저에 신규 tier를 노출.

## honest한 한계와 규율
- **그대로 베끼지 않는다**: algo-c의 C를 참조하되 **사양으로부터 재구현**(`feedback_provenance_research_method`).
  라이선스 확인 전에는 코드를 반입하지 않는다.
- **이미지 AI의 초점을 흐리지 않는다**: 범용 op는 opt-in tier. 북극성(HALCON급 이미지 op 망라 + honest
  holdout)은 불변.

---

## P1 완료 기록(2026-08-16, Opus5[1m]/ultracode)
**최소 실증 「Fullseye는 범용 알고리즘도 C 생성할 수 있고, C 일치를 honest 실측할 수 있다」를 달성.**

- **신규 tier(이미지 REGISTRY와 완전 분리·opt-in)** = `algo.py`. `seq`(1-D 수열)/`scalar`(단일 실수) 타입을 신설.
  이미지 `ops.REGISTRY`에는 일절 손대지 않으므로 진화 탐색·Wave-0 champion pin은 영향 없음(테스트로 실증).
- **op(5)**: 정렬 3종 `quicksort`(Hoare/median-of-three/Lomuto/명시적 스택)·`heapsort`(Williams
  1964 binary max-heap)·`mergesort`(von Neumann 1945 top-down stable) = `seq→seq`. 추가로 `scalar`
  타입에 역할을 부여하는 reduction `seq_max`/`seq_min`(`seq→scalar`, 순서 비의존으로 exact). **모두 사양으로부터
  재구현**(algo-c 소스는 그대로 베끼지 않고, 각 op에 `provenance`를 명기).
- **단일 source of truth**: 각 op는 Python 본체와 C 본체를 **문자열로 보유**하며, in-process 참조는
  `algo.py_fn`이 동일 문자열을 compile, `algo_codegen`은 동일 문자열을 standalone `.py`/`.c`로 emit.
  → 테스트한 oracle과 출하물이 drift하지 않는다(테스트 `test_emitted_python_*`로 실증).
- **codegen** = `algo_codegen.py`(`emit_python`/`emit_c`. C는 함수 + 바이너리 I/O driver = 완전히
  compile 가능한 단독 프로그램).
- **honest gate** = `algo_difftest.py`(2개의 실측, deferred skip이 아님):
  (1) Python 참조 **== numpy oracle**(`np.sort`/`np.max`/`np.min`), (2) codegen **C == Python이
  bit 일치**(holdout=edge case 10 + random 40). 이들 op는 기존 double을 이동/선택할 뿐이므로
  올바른 구현은 bit 완전 일치(tol=0.0).
- **★실측(2026-08-16, `zig cc` = `python -m ziglang cc`, ziglang 0.16.0을 pip로 도입)**:
  전 5개 op에서 **python diff 0.00e+00 / C-vs-Python diff 0.00e+00 / passed=True**(실 compile→실 run→bit
  비교). = 「C 일치를 honest 실측」을 **deferred skip이 아닌 진짜 측정**으로 달성.
- **fail-closed**: toolchain 없음 → C 절반은 honest skip(Python 절반은 동작). compile/run 실패 →
  gate FAIL(neutral skip으로 하지 않음. 테스트 `test_difftest_compile_error_fails_closed`로 실증).
- **facade**: `fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()`
  (+ `api.py`). **skill** = `~/.claude/skills/image-processing/SKILL.md`에 「General algorithms
  (algo-c tier)」절을 추기(서브에이전트에서 사용 가능).
- **테스트**: `tests/test_algo.py`(42건=registry 정합·Python==sorted/oracle·안정성·단일 source
  of truth·C bit 일치[toolchain 있을 때]·compile-error fail-closed·이미지 registry 비오염·facade).
- **honest한 한계**: ① NaN을 포함하는 수열은 비교정렬의 규약이 Python/C/numpy에서 갈리므로 holdout에서
  제외(공개). ② 부동소수의 합 등 **누적으로 순서 의존이 되는 op는 P1에 포함하지 않음**(seq_max/min은 exact).
  ③ CLI 서브커맨드 통합(`imgevolve.py algo ...`)과 Studio op 브라우저 tier 표시는 다음 단계(P1.5).
  ④ fscript의 배열/procedure 언어화(설계 doc 아키텍처 항목 2)는 P1 범위 외(별도 트랙).

## P1 적대적 리뷰 후 강화(2026-08-16, [[feedback_no_solo_ai_judgment]])
본 세션의 자작 코드에 독립 적대적 리뷰(Workflow 4개 렌즈=알고리즘 정확성 / codegen·C 안전 /
gate 건전성 / 통합·초점 안전, 22 findings)를 실시. 전건을 내가 1차 코드 검증(v11 규율)하여
진짜 결함을 수정:
- **[HIGH] gate의 fail-open(NaN/부호 있는 제로)**: `_max_diff_*`가 `max(0.0, nan)=0.0`으로 NaN 차분을
  뭉개어 「bit 일치」라고 위증하고 있었다(실측 재현) → **(1)Python×oracle=값 비교이지만 비유한은 fail-closed
  (inf, tol로 통과시키지 않음), (2)C×Python=진짜 bit 비교(IEEE float64 원시 바이트=부호 있는 제로/NaN 페이로드
  도 검출)**로 분리. `c_verified` 필드로 「실 compile 검증완료 pass」와 「toolchain 없음 unverified
  pass」를 구별.
- **[HIGH] quicksort가 중복 다수 입력에서 O(n²)**(Lomuto `<=`로 모든 동등값이 한쪽으로 쏠림. 이진값=binary mask flatten
  이 현실적 입력·실측 quadratic) → **3-way(Dutch national flag) partition + median-of-three**로 Python/C
  모두 재작성(모든 동등값 O(n)). 성능 가드 테스트(20000 전부 동일 <2s) 추가.
- **[HIGH] emitted C `heapsort`가 BSD `<stdlib.h>`의 `heapsort()`와 충돌**(macOS/BSD에서 compile 불가.
  `zig cc -target x86_64-macos`로 실측) → C 심볼을 **`heapsort_asc`**로 개명(`mergesort_asc`와 통일).
  **전 op의 macOS cross-compile 테스트**를 추가(회귀 가드).
- **[LOW] C의 fail-open/UB 3건**: mergesort의 malloc 실패=미정렬 출력 → **in-place 삽입정렬
  fallback(fail-closed·stable 유지)** / heapsort의 `2*root+1` int overflow → **long long**화 /
  driver의 len이 32-bit로 size_t wrap → **`SIZE_MAX/sizeof(double)` 상한 체크 + `<stdint.h>`**.
- **[MED] test_mergesort_is_stable이 공허**(값 비교=어떤 정렬도 통과) → **부호 있는 제로의 순서 보존**으로
  안정성을 실관측(`<`=불안정으로의 퇴행을 검출)으로 재작성. **no-mutation 테스트**(`run(a)`가 호출자의
  list를 파괴하지 않음)도 추가.
- **[MED] holdout이 작고 중복이 희박** → 큰 all-equal(300)/ 이진(300)/ few-distinct(300) + 중복 많은
  랜덤을 추가(C gate가 중복·크기 regime을 실검사).
- **[MED/honesty] NaN 규약 미문서화** → module docstring과 각 op docstring에 「NaN-free 전제·비유한은
  gate에서 fail-closed」를 명기. seq_max/min의 「order-independent」→「NaN-free 입력에서 order-independent」.
- **인접한 기존 ship-bug**: `sample_images`(studio가 runtime import)가 `pyproject.toml` py-modules
  누락=non-editable wheel에서 사라짐 → 추가(wheel 실빌드로 확인).
- 테스트 **43→58건**(bit-check·fail-closed·macOS cross-compile·중복 성능·no-mutation·c_verified·
  안정성 관측을 추가). 전 op의 difftest 재실행 = python/C 모두 diff 0.0·bit 일치·passed=True.
- **미수정(사용자 판단·P1 범위 외 기존 문제)**: (a) `pyproject.toml`의 `[tool.setuptools.package-data]`
  `"*"` glob이 root-level flat인 `studio_assets/`·`data/`를 wheel에 실을 수 없음(studio i18n/op-help/
  sample 이미지가 installed wheel에서 누락=기존·MANIFEST.in 또는 package화의 설계 변경 필요) / (b) `fullseye.__all__`
  이 api의 pcseg 계열 18개 이름을 결여(star-import로 누락=기존). **algo tier는 무관(algo*는 py-modules로
  확실히 동봉·facade는 정합)**.

## 다음(P2 이후)
- **P1.5a(완료, 2026-08-16)**: `imgevolve.py algo <list|run|emit-c|emit-py|difftest>` 서브커맨드를 추가
  (통일 CLI 진입점. `algo run quicksort --seq 3,1,2` / `algo emit-c mergesort` / `algo difftest all`).
  CLI 회귀 테스트 2건 + skill의 CLI 예시를 갱신.
- **P1.5b(완료 2026-08-17)**: Studio의 op 브라우저에 general(algo) tier를 **read-only 표시**(아래 기록).
- **P2(완료 2026-08-16)**: 수치계산 op를 seq/scalar 타입 기반 위에. **simpson / bisection / newton**
  (다항식·샘플을 입력 seq에 내포하는 seq→scalar·기존 reduce 드라이버에 올림) + **gauss_solve**
  (연립일차 Gauss 소거·부분 피벗=아래 P2 완수 기록). honest gate = **C-vs-Python은 bit 일치**
  (동일 알고리즘 + `-ffp-contract=off`로 FMA 억제) / **Python-vs-oracle은 수치 허용오차**(`AlgoOp.tol`)로
  독립 oracle(simpson=scipy / 구근=잔차 |p(root)| / gauss=`np.linalg.solve`) 대조. fail-soft를 honest 문서화.
- **P3(완료 2026-08-17)**: 문자열 op(아래 P3 완수 기록). `text` 타입은 「코드포인트 열을 float64로 운반」
  규약(`text_to_seq`/`seq_to_text`)으로 기존 float64 harness에 실어, 새 wire 타입을 추가하지 않고 실현.
- **P4(완료 2026-08-17)**: 그래프 op(components/mst_weight/dijkstra, 아래 P4 완수 기록). `graph`는
  `[n, m, (u,v,w)*m]` 팩으로 기존 harness에 실었다(새 wire 타입 불필요).
- **P5(완료 2026-08-17)**: 수론·압축·교육용 해시(gcd_seq / sieve_primes / pow_mod / crc32 /
  rle_encode, 아래 P5 완수 기록). 정수를 float64로 운반(exact <2^53)하므로 새 wire 타입 불필요. 전 op가
  **exact**(C bit 일치이면서 Python==독립 oracle tol 0). **암호는 primitive만**(modular
  exponentiation / CRC) = 완전한 RSA/AES/SHA는 bignum/큰 상태로 float64 seq harness에 실리지 않으므로 범위 외
  라고 honest 공개.

## P3 완수 기록 — 문자열 op(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**문자열 알고리즘 3종을 algo tier에 추가.** 「문자열 = 코드포인트 열을 float64로 운반」(Unicode 스칼라는
< 2^53이므로 엄밀)로 **기존 float64 바이너리 harness에 무개조로 실린다**(새 wire 타입 불필요). 값은 등가비교만(정수 코드로
엄밀)·위치/거리는 엄밀 정수 → **C-vs-Python bit 일치이면서 Python-vs-oracle은 EXACT(tol 0)**.

- **op(3)**: `strfind`(Knuth-Morris-Pratt=실패함수 프리픽스 오토마톤. 입력 `[m, pattern(m), text]` → 전체 출현
  시작 위치의 오름차순 리스트·중복 출현 포함=**가변길이 KIND_MAP**, gauss에서 만든 가변길이 wire를 재사용) / `edit_distance`
  (Wagner-Fischer/Levenshtein 2행 DP=**KIND_REDUCE**·엄밀 정수) / `lcs_length`(최장 공통 부분수열 길이 2행 DP=
  KIND_REDUCE). 모두 사양으로부터 재구현(provenance 명기). fail-soft=공 패턴/절단/패턴>텍스트는 `[]`,
  na<0/절단은 `0.0`.
- **단일 source of truth + text 타입 헬퍼**: `text_to_seq(s)`/`seq_to_text(seq)`(코드포인트↔float64)를 추가.
- **honest gate 실측(3 op 모두 passed=True·c_verified=true)**: Python==**독립 oracle**(strfind=단순 all-occurrences
  스캔[KMP와 독립] / edit·lcs=**top-down memo 재귀**[bottom-up 2행 DP와 다른 코드 경로])로 **diff 0.0(exact)** /
  codegen **C==Python bit 일치**(ziglang cc). 
- **work-graph op 파도(후보 d의 실연)**: 신규 op마다 `algo_gate` 게이트 노드를 쌓는다=**1 op=1 노드**. 3 op를
  `raptor-worklog add --capability tool` → `run-once --available tool:command`로 **무인 done**(gate_ok.json 생성).
- **회귀**: `tests/test_algo.py`에 strfind/edit_distance/lcs_length의 테스트 군(기지해·random×독립 oracle·fail-soft·
  가변길이 출력·no-mutation·python exact·C bit 일치). 전 스위트 **4669 passed / 0 failed**(P2 후 4649에서 +20)·
  ruff clean·mypy 회귀 0. commit + push는 이 세션에서 실시(사용자 승인 2026-08-16 취침 시=push 게이트 개방).

### P3 문자열 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
독립 적대적 리뷰 Workflow(4개 렌즈·각 finding을 검증 에이전트가 실 코드/실 compile로 확인) = **3 findings 전부
CONFIRMED**(그중 2건은 동일 근본원인을 다른 렌즈가 보고). 1차 검증 후 전건 수정:
- **[MED] Python이 `int(a[0])`을 범위체크 전에 실행 → C와 불일치**: edit_distance/lcs_length의 Python은
  `na = int(a[0])`을 먼저 평가(truncation), C는 raw double을 먼저 가드. **`a[0]` ∈ (-1.0, 0.0)**(예 -0.5)에서
  Python은 na=0(유효한 빈 문자열)으로 계속 진행해 실제 거리를 반환하는 반면, C는 raw guard로 거부해 0.0 → **bit 일치 계약 위반**
  (ziglang cc로 실측: `[-0.5,65,66]` = Python 2.0 vs C 0.0). holdout은 비음수 정수 na만이므로 게이트가 미검출.
- **[LOW] NaN 헤더에서 Python이 크래시**(C는 fail-soft): `int(nan)`이 ValueError를 발생시켜, op docstring의
  fail-soft 약속에 반한다(C는 NaN-false 가드로 0.0/`[]`). ※NaN은 「NaN-free 전제」로 계약 외지만 동일한 가드 순서의 결함.
- **수정(하나로 둘 다)**: 3 op 전부의 Python을 **raw-value 가드를 `int()` 전으로** 이동(`not (x >= lo and x <= hi)`=
  NaN-false)=**C를 엄밀히 거울처럼 반영**. gauss는 원래 raw guard로 올바랐다(같은 형태로 통일).
- **경계의 피복**: oracle 검증 영역 밖(oracle은 truncation으로 다른 값을 냄=바로 이 버그) 이므로, 소수 음수/NaN/초과 헤더의
  **C-vs-Python parity를 전용 테스트로 직접 고정**(`test_string_c_python_parity_on_bad_headers`) + Python fail-soft
  no-crash 테스트. algorithm-correctness/c-safety의 핵심 지적은 0(KMP/DP/메모리 안전은 깨끗함).
- 리뷰 후: 3 op 모두 difftest = python exact / C bit 일치 / c_verified=true, 전 스위트 녹색(아래)·ruff/mypy 회귀 0.

## P2 완수 기록 — gauss_solve(2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**연립일차방정식 Gauss 소거(부분 피벗)를 추가하여 P2 수치계산을 완수.** 사용자 지시대로
`graph-loop-engineering` 스킬로 raptor work-graph에 노드화하고, tool driver에 무인 실행시켰다(2층 방침=
breadth는 work-graph의 difftest 게이트, 적대적 findings 채택 여부·push는 세션의 human checkpoint).

- **신규 kind `KIND_MAP`(`map_varlen`) = 가변길이 seq→seq**: 기존 op는 sort(입력길이=출력길이) / reduce(→1값)
  뿐으로, 연립해(입력 `[n, 확대계수행렬 n×(n+1) row-major]` → 해벡터 길이 n)는 입력길이≠출력길이. C 경계=
  `int f(const double* a, int n, double* out)`가 out에 out_len(≤ n)개를 써넣고 out_len을 반환(fail-soft=0).
- **`algo_codegen` 드라이버에 가변길이 출력 모드**: KIND_MAP 분기가 `{int32 out_len, out_len*float64}`를 쓴다
  (sort와 같은 wire이지만 out_len≠입력길이). out 버퍼는 입력길이로 확보(계약 out_len≤n이 상한을 보증) +
  `out_len ∈ [0,len]`에 **fail-closed clamp**(폭주하는 op가 읽는 쪽을 over-read시키지 않도록).
- **gauss_solve(`algo.py`)**: Python 참조(stdlib만·index-by-index로 C를 거울처럼 반영)와 C 참조를 단일 source.
  전진소거(부분 피벗=최대 |요소| 행을 선택) + 후진대입. 특이(피벗 0 잔존) / malformed는 **[] / 0**으로
  fail-soft(예외 없음). **Python/C의 FP 연산 순서를 엄밀 일치**(동일 나눗셈·subtract-then-multiply·소거된 요소를
  exact `0.0` 대입·abs는 inline 부호반전으로 `math.h`/`-lm` 비의존)이므로 bit 일치. int overflow는 `n≤46340` +
  `long long need`로 방지.
- **honest gate 2단계(실측)**: (1)Python **== `np.linalg.solve`**(독립 oracle·양호 조건 holdout 34 케이스=대각
  우세 + 행치환 + **피벗 필수 케이스**[exact-zero(0,0)·미소(0,0)·3×3 제로 대각]) → **max abs diff 3.55e-15**
  (tol 1e-9). (2)codegen **C == Python bit 일치**(`ziglang cc`·`-ffp-contract=off`) → **diff 0.0 / c_verified=true**.
  특이/malformed의 **C fail-soft는 Python과 완전 일치**를 별도 테스트로 직접 검증(oracle 비대응 영역이므로 holdout이 아닌
  C-vs-Python 직접 비교).
- **`tools/algo_gate.py`(재사용 가능한 gated-stage runner)**: work-graph의 `CommandWorker`는 produces 생성 또는
  exit0로 done 판정하므로, difftest가 FAIL시에도 JSON을 쓰는 현재 상태로는 **fail-open**(실패 게이트가 done)이 된다.
  이를 막는다 = **pass 시에만 마커 `gate_ok.json`을 쓰고, exit code=판정**으로. 노드의 produces를 마커로
  향하게 하면 실패 게이트가 **fail-closed**로 노드 실패가 된다. P3 이후의 op 파도(1 op=1 노드)에 그대로 사용 가능.
- **work-graph 노드화**: `raptor-worklog add --capability tool --project imgevolve --priority 0`(spec=
  `tools/algo_gate.py --op gauss_solve --out <OUT>`, produces=`<OUT>/gate_ok.json`) → `run-once --available
  tool:command`로 **무인 실행 → status=done**(exit0·c_verified=true·bit 일치 마커 생성).
- **회귀**: `tests/test_algo.py`에 gauss + algo_gate + C fail-soft + require_c 테스트 군을 추가(알고리즘 테스트
  **93 passed**), 전 스위트 **4649 passed / 0 failed**(리뷰 전 4637에서 +12). 내 전체 파일 **ruff clean**·
  mypy 회귀 0(기존 baseline=scipy/ziglang stub 결여와 difftest 시그니처의 기존 quirk뿐, 내 추가행 유래 0). 전건
  local commit·**미push=human-gate**.

### P2 gauss 적대적 리뷰 후 강화(2026-08-16, [[feedback_no_solo_ai_judgment]])
자작 gauss 코드에 독립 적대적 리뷰 Workflow(4개 렌즈=numeric 정확성 / C 안전 / gate 건전성 / 통합·피복,
각 finding을 검증 에이전트가 **실행 재현**). 5 findings 중 **4 CONFIRMED**를 1차 코드 검증 후 전건 수정:
- **[HIGH] algo_gate의 fail-open(미지 op)**: `find_algo`의 `SystemExit`이 `marker.unlink()`보다 **먼저**
  있어, 이전 pass의 `gate_ok.json`이 잔존 → CommandWorker가 produces 존재로 **done 오판정**(op 개명/typo의
  재실행에서 표면화). → **mkdir + stale-marker unlink를 registry 체크보다 앞**으로 이동(어느 조기 exit에서도 이전 pass를
  이어받지 않음). 회귀 테스트 추가.
- **[MED] gate가 부분 피벗을 반증할 수 없음**: holdout이 대각우세뿐(exact-zero 피벗 없음) → 피벗탐색을
  삭제한 mutant도 `np.linalg.solve`와 2.2e-14로 일치해 **PASS**(pytest는 포착하지만 work-graph가 실행하는
  algo_gate는 difftest holdout이므로 포착 못함). → **피벗 필수 케이스**(exact-zero(0,0)=`[[0,1],[1,0]]`·
  미소(0,0)=`[[1e-14,1],[1,1]]`·3×3 제로 대각)를 holdout에 추가=no-pivot mutant를 **구조 불일치→inf→FAIL**로
  falsify(자체 실측 확인완료). 오해를 부르는 코멘트도 정정.
- **[MED] C skip에서도 pass 마커**: toolchain 부재로 C 절반이 skip(honest하지만 **미검증**)이어도
  `res["passed"]`만으로 마커를 쓰고, graph는 마커 존재만 읽는다 → **미compile C를 certify**. →
  `require_c`(기본값 True)를 추가=미검증 pass는 `gate_ok.json`을 쓰지 않고(`gate_unverified.json`에 diagnostic)
  **fail-closed**. `--allow-unverified-c`로 명시 opt-out, `--no-c`는 Python-only인 의도적 약한 게이트.
- **[REFUTED] 「out_len==0의 wire가 미테스트」**: 내가 선제적으로 추가한 `test_gauss_c_fail_soft_matches_python`
  이 실제 C를 compile/run해 피복 완료 → 검증 에이전트가 mutation으로 건전성을 확인해 **기각**. 남는 macOS
  cross-compile guard의 경미한 nit(`_ALL`→`_ALL_OPS`로 numeric/gauss도 피복)만 채택.
레비뷰 후에도 gauss difftest = python 3.55e-15 / C bit 일치 / c_verified=true·work-graph 노드(hardened) = done.

## P1.5b 완수 기록 — Studio에 general tier를 read-only 표시(2026-08-17, Opus5[1m]/ultracode)
**op 브라우저에 general(algo) tier를 표시.** 이미지 초점을 흐리지 않는 설계 = general op는 seq/scalar의 별도
계산 모델이므로 **read-only**(이미지 파이프라인에 넣지 않음).
- `api.list_ops(include_algo=False)`에 opt-in 파라미터 + `api.algo_rows()`(backend="general"·category "algo:*"·
  tier "z_algo"로 말미 정렬·halcon None·provenance 부여). **기본값은 불변**(기존 caller는 이미지 op만=초점 유지).
- studio: `all_ops = list_ops(include_algo=True)`로 browser에 표시 / `_op_row`가 algo 폴백 /
  `op_signature_detail`·`op_tooltip`이 general 분기(「seq/scalar op·not an image op·run via CLI」+ provenance) /
  `on_op_selected`가 general 선택 시 Insert·Run once·Help·a/b 노브를 무효화 / `add_op`·`run_op_once`·
  palette가 general을 flash 거부. 다중 방어 = **`PipelineModel.add_stage`가 이미지 REGISTRY로 KeyError fail-closed**.
- **적대적 리뷰(2개 렌즈·실행 검증) = 3 CONFIRMED(2건은 동일 근본원인)를 전건 수정**:
  - **[HIGH/MED] Program(HDevelop 코드) 에디터의 「Apply → pipeline」이 미가드**: `op_names`를
    `list_ops(include_algo=True)`에서 도출하고 있었기 때문에 general 이름이 코드 파서/보완/Help 피커에 전파 →
    `apply_program`이 `model.stages=` 직접 쓰기로 **add_stage backstop을 우회** → general op가 파이프라인에 침입.
    → **`op_names`를 이미지 한정으로**(`backend != "general"`로 제외. browser 표시 `all_ops`는 general 유지) +
    `apply_program`에 general stage 거부 가드(다중 방어).
  - **[MED] Help 다이얼로그의 피커가 general을 허위 표시**(「Two knobs a,b tune this operator」) → 같은
    `op_names` 이미지 한정화로 Help 피커에서도 제외(root fix가 둘 다 해소).
- 회귀 테스트: `_op_row`/signature/tooltip의 general 분기, offscreen에서 browser가 general을 표시하면서 Insert 등이
  무효·`win._op_names`가 general 제외·코드 파서가 general 행을 거부. 전 스위트 녹색·ruff net-new 0(신규 테스트는
  clean, studio.py의 flash는 파일의 `%`-format idiom에 일관)·mypy 회귀 0. **후보 (d) op 파도**도 실연=전 12개 algo op를
  work-graph에 1 op=1 노드로 실어 `run-once`로 무인 done.

## P4 완수 기록 — 그래프 op(2026-08-17, Opus5[1m]/ultracode, bonus)
**그래프 알고리즘 3종을 algo tier에 추가**(후보 외지만 사용자 「전부 진행해」+7-8h 자율에 따른 보너스). 그래프를
입력 seq에 팩(`[n, m, (u,v,w)*m]`, 무방향; dijkstra는 src 전치 `[n, m, src, ...]`)해 기존 float64 harness에 싣는다.
- **op(3)**: `graph_components`(union-find·연결성분 수=KIND_REDUCE 엄밀 정수) / `graph_mst_weight`(Kruskal·최소
  전역삼림의 총 가중치=KIND_REDUCE) / `graph_dijkstra`(단일시작점 최단거리=**KIND_MAP**·-1.0=도달불가). 결정적 union 규칙 +
  (weight,index) 정렬 + 최소거리·최소 index의 settle 순서로 **C==Python bit 일치**.
- **★KIND_MAP driver를 2단계화(size-probe)**: dijkstra는 출력길이 n이 입력길이 3+3m을 **초과할 수 있다**(희소 그래프). 구 driver
  는 out을 입력길이로 확보하고 있었으므로 heap OOB가 되는 결함 → driver가 `f(a,n,NULL)`로 out_len 상한을 묻고, 그만큼 확보
  한 뒤 실제로 써넣는 2단계 프로토콜로 변경(gauss/strfind/dijkstra에 `if(!out) return <bound>`).
- **honest gate**: Python == 독립 oracle **scipy.sparse.csgraph**(connected_components/minimum_spanning_tree/dijkstra).
  정수 가중치 holdout에서 **components 엄밀(tol 0) / mst·dijkstra tol 1e-9(실측 0)**. C==Python bit 일치(ziglang cc).
  MST/Dijkstra holdout은 단순 그래프(csr의 중복 가산 회피), components는 다중변 허용(연결성만).
- **적대적 리뷰(3개 렌즈·실행 검증) = 2 CONFIRMED(둘 다 HIGH·dijkstra 메모리 안전)를 전건 수정**:
  (#2)out 버퍼가 입력길이 크기 → n>3+3m에서 OOB 기록 → **2단계화 driver**로 해소(발견 전에 선제 수정완료).
  (#1)src 가드가 raw `sd < nd`로 소수 nd에서 src==n이 통과해 out[n] OOB → **정수 n으로 속박**(`sd < n`). 1 REFUTED
  (도달불가 노드 미검증←known-answer/sparse 테스트로 피복). numeric/oracle 각 렌즈의 다른 지적 없음.
- **op 파도**: 3개 그래프 op도 work-graph 게이트화(전 algo op = 15가 1 op=1 노드로 무인 done). 전 스위트 녹색·ruff clean
  ·mypy 회귀 0. push는 세션(사용자 승인).

## P5 완수 기록 — 수론·압축·교육용 해시(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**범용 알고리즘 5종을 algo tier에 추가하여 algo-c 로드맵(P1→P5)을 완수.** 정수를 float64로 운반
(exact < 2^53)하므로 새 wire 타입 불필요. 비트/정수 연산은 C 측에서 `unsigned long long`/`unsigned int`로 cast해서 수행하고,
double로 되돌린다(결과는 < 2^53이므로 exact). **전 5개 op가 exact**(C==Python bit 일치이면서 Python==독립 oracle tol 0).
- **op(5)**:
  - `gcd_seq`(KIND_REDUCE): 비음수 정수열의 GCD(Euclid·열에 fold). oracle=`math.gcd`.
  - `sieve_primes`(**KIND_MAP**): 에라토스테네스의 체. 입력 `[n]`(길이 1) → n 이하의 소수 오름차순=**출력이 입력길이를
    크게 초과**하는 대표 예. size-probe 상한 `π(n) ≤ n/2 + 1`(2와 홀수의 개수, log 불필요=`math.h` 비의존). oracle=시험나눗셈(독립 경로).
  - `pow_mod`(KIND_REDUCE): 모듈러 거듭제곱 base^exp mod m(square-and-multiply=RSA/DH의 primitive·교육용). oracle=builtin `pow`.
  - `crc32`(KIND_REDUCE): CRC-32(IEEE 802.3·reflected·poly 0xEDB88320). **c_func는 `crc32_ieee`**(zlib/BSD의
    `crc32` 심볼 충돌을 방어적으로 회피, cf. heapsort_asc). oracle=`zlib.crc32`(zlib C 라이브러리=완전 독립).
  - `rle_encode`(**KIND_MAP**): 연속길이 압축 →`[value, count, ...]`(**출력 최대 2×입력**, 전부 다르면 2n). 가역·oracle=`itertools.groupby`.
- **★honest 영역의 공개(pow_mod)**: uint64의 중간곱이 넘치지 않도록 **mod ≤ 2^32−1**(곱 < mod² < 2^64), base/exp ≤ 2^53.
  결과 < mod < 2^53으로 float64 exact. 영역 외는 fail-soft 0.0(raw guard를 int() 전에·NaN 안전).
- **★암호는 primitive만(honest scope)**: 완전한 RSA/AES/SHA는 bignum·큰 상태로 float64 seq harness에 실리지 않으므로
  범위 외로 명기. 실을 수 있는 primitive(modular exponentiation / CRC checksum)를 **알고리즘 공개**로 제공(cipher가 아니다).
- **★정수성 가드(신규·honest 개선)**: gcd_seq/pow_mod/crc32는 **데이터 값**이므로 비정수는 malformed → fail-soft.
  `x == float(int(x))` / `x == (double)(long long)x`를 **범위체크 후에 short-circuit**(NaN/초과값에서는 cast에 도달하지 않아
  `int(nan)` 크래시·C의 `(long long)nan` UB를 회피). header 계열(sieve의 n)은 기존 gauss/dijkstra와 같은 절삭 규약.
- **★KIND_MAP 2단계 size-probe를 신규 2 op에서 활용**: sieve(출력≫입력)·rle(출력≤2×입력) 모두 `if(!out) return <상한>`으로
  driver가 상한을 묻고→확보→실제 기록. 전용 테스트로 **C 출력이 입력길이를 초과해도 heap OOB하지 않음**을 실 compile/run으로 고정.
- **honest gate 실측(5 op 모두 passed=True·c_verified=true·ziglang cc)**: Python==독립 oracle **diff 0.0(exact)** /
  codegen **C==Python bit 일치 diff 0.0**. crc32는 `zlib.crc32`와 전체 바이트값·"Hello"·전 256바이트에서 일치 확인.
- **work-graph op 파도**: 5개 P5 op를 `algo_gate` 게이트 노드화(`1 op=1 노드`·priority 0·tool capability) →
  `run-once --available tool:command`로 **5노드 무인 done**(각 `gate_ok.json`=c_verified/bit 일치 마커 생성).
  = **전 algo op 20개가 work-graph 게이트화**(15→20).
- **회귀**: `tests/test_algo.py`에 P5 테스트 군(기지해·독립 oracle 대조 over-random·fail-soft·정수성·
  2단계 probe의 출력초과·bad-input C-vs-Python parity·no-mutation·python exact·C bit 일치). 전 스위트
  **4700 → 4736 passed / 0 failed**(+36)·내 신규 파일 ruff clean·mypy 신규 에러 0(기존 baseline뿐).

### P5 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
자작 P5 코드에 독립 적대적 리뷰 Workflow(4개 렌즈=algorithm-correctness / C-safety-codegen / gate-honesty /
integration-focus, 각 finding을 검증 에이전트가 **실 compile/실행으로 재현**, 18 agents). **14 raw → 9 CONFIRMED / 5
REFUTED**. 전 CONFIRMED를 내가 1차 재현(직접 ziglang compile·실행)한 후 수정. **특기할 만한 것은 「gate가 자작
guard를 falsify할 수 있는가」에 대한 깊은 파고듦**:
- **[MED] pow_mod의 honest 영역(base/exp ≤ 2^53)이 holdout에서 미측정** → exp를 uint32로 절삭하는 C 변이가 gate를
  통과(base/exp 최대 1e6/1e5로 상위 ~33bit 미측정). **수정**=holdout에 2^53 경계 케이스([2,2^53,7]·[2^53,2^53,2^32-1]
  등) 추가 + random을 [0,2^53] 전영역으로 확대. **재현 확인**: 수정 후는 exp→uint32 변이가 `passed=False`.
- **[LOW] gcd(2^53 guard)/sieve(5,000,000 cap)도 같은 종류의 미측정 경계** → gcd 경계를 holdout에 추가(변이 falsify 확인),
  sieve at-cap은 Python 참조가 느리므로(~7.7s) **전용 C-only 테스트**로 n=5,000,000 수리(π=348513·독립 numpy sieve로 검산)
  ·n=5,000,001 기각을 측정.
- **[MED] -ffast-math / -ffinite-math-only가 NaN 가드를 소거** → shipped C artifact를 fast-math로 compile하면
  `x >= 0.0`의 NaN 기각이 생략되어 `(long long)NaN` UB가 실행(**자체 재현**: `gcd_seq([NaN,6])`이 `-ffinite-math-only`에서 2.0,
  gate 기본값 `-ffp-contract=off`에서는 0.0). **수정**=`algo_codegen.emit_c`에 `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ →
  #error`를 주입(artifact가 silent miscompile되지 않고 **빌드 거부**=fail-closed) + C 코멘트의 「UB 도달불가」를 IEEE 전제로
  honest하게 정정 + fast-math 빌드 거부 테스트 추가.
- **[MED] C의 짧은 입력 가드(pow_mod `n<3` / sieve `n_in<1`)가 falsify 불가능** → 전 holdout이 고정길이이므로 가드 삭제로
  OOB heap read를 허용해도 전 테스트가 녹색. **수정**=holdout / parity 테스트에 빈/짧은 배열을 추가해 경계 경로를 실행.
  **honest 공개**: black-box 값 비교는 safety-guard 삭제를 **결정적으로는** 포착할 수 없다(OOB 읽기값이 비결정적). 본래는
  ASan이 정공법이지만 **ziglang의 ASan은 본 Windows 환경에서 링크 불가**(`__asan_shadow_memory_dynamic_address` 미정의).
  Python 측 가드는 결정적으로 falsify 가능·C 측은 경계 실행 + 새니타이저로 포착 가능(환경 제약으로 자동화는 보류).
- **[MED] pow_mod의 `1 % mod` 특수 분기가 falsify 불가능**(exp==0이면서 mod==1인 동시 케이스가 어디에도 없음) → holdout에
  [7,0,1]·[0,0,1] 추가 + 기지해 assert(**재현 확인**: `1%mod→1` 변이가 `passed=False`).
- **[MED] P5 oracle이 영역 외 입력에서 크래시**(zlib.crc32 / pow() / int(nan)이 raise) → holdout에 영역 외 케이스를 넣으면
  difftest가 예외 발생=gate가 guard 규약을 **구조적으로 피복할 수 없다**(1개의 unit test만 포착). **수정**=각 P5 oracle을
  **도메인 인식화**(`_int_in`으로 op의 선언 영역을 거울처럼 반영→영역 외는 op의 fail-soft 값 0.0/[]를 반환=크래시 회피). 이로써
  gate 자체가 guard 이탈을 falsify 가능(**재현 확인**: crc integrality 삭제·gcd guard 축소의 각 변이가 `passed=False`).
- **[LOW] Studio의 Operator-help 카드가 general op에 「Two knobs a,b」라고 허위 표시**(P1.5b에서 picker는 막았지만
  browser 선택의 `op_help_html` fallthrough는 미가드·전 20개 algo op에 파급) → `op_help_html`에 general 분기 추가
  (provenance + packed-input 계약 + CLI 실행을 표시) + `_op_row`/`api.algo_rows`에 `desc`(op.doc) 추가 + 회귀 테스트.
- **[LOW] image-processing skill의 YAML frontmatter description(auto-trigger 면)이 P1만 광고**(body는 20 op 갱신완료) →
  description의 algo 절을 P2–P5 전 범위 + 트리거 단어(primes/modular exponentiation/CRC-32/RLE/shortest path)로 확장.
- **REFUTED 5건**(검증으로 기각): 모두 현행 코드는 올바르고, finding이 실동작을 오인(검증 에이전트가 실행으로 반증).
- 리뷰 후: 5개 P5 op 모두 difftest = python exact / C bit 일치 / c_verified=true, 전 스위트 **4742 passed / 0 failed**
  (리뷰 수정 테스트 +6)·내 신규 파일 ruff clean·mypy 신규 0. work-graph 5노드도 post-fix로 재게이트(done).

## P6 완수 기록 — 계산기하(2026-08-17, Opus5[1m]/ultracode, 12h 자율·`graph-loop-engineering`)
**기하 알고리즘 3종을 algo tier에 추가**(algo-c 로드맵 P1→P5 완수 후의 확장=P6. 당초 TOC의 「기하=볼록껍질/
선분교차」에 대응). **이미지 tier의 윤곽/영역처리로의 가교**이기도 하다. 2-D 점을 입력 seq에 팩하고, **정수좌표**
(각 [-100000, 100000])로 모든 방향판정/신발끈합을 **엄밀한 정수**로 만든다(부동소수 나눗셈을 일절 사용하지 않음)=C bit 일치이면서
Python==독립 oracle tol 0.
- **op(3)**:
  - `polygon_area2`(KIND_REDUCE): 신발끈 공식으로 다각형의 **2×부호 있는 면적**(부호=회전방향). oracle=numpy 벡터화 신발끈
    (`dot`+`roll`=다른 코드 경로). **honest 영역**: 좌표 ≤1e5·n ≤1e5에서 합은 최대 2e15 < 2^53(box 순회 스파이럴로 실측=exact).
  - `point_in_polygon`(KIND_REDUCE): 교차수(레이캐스팅)로 내외판정. 정수의 외적으로 교차를 결정(나눗셈 없음).
    oracle=**권취수 알고리즘**(교차수와는 다른 방법·양자는 단순 다각형의 엄밀한 내외에서 일치). 오목 다각형도 정확(notch=outside를 검증).
    **경계(변 위)의 점은 구현 의존**이라고 공개해 holdout에서 제외(교차 vs 권취수가 경계에서 갈릴 수 있으므로).
  - `convex_hull`(**KIND_MAP**): Andrew의 monotone chain으로 볼록껍질. 출력=**lex-min 정점부터 CCW 순서**의 정점열(공선점은 제외
    =strict hull·scipy와 일치). oracle=`scipy.spatial.ConvexHull`의 **정점집합** 비교(순서는 C-vs-Python bit 일치로 별도 담보).
    퇴화(3 미만의 distinct / 전부 공선)는 양자 [] 로 fail-soft. **2000 랜덤 점집합에서 scipy와 mismatch 0**을 사전 실측.
- **KIND_MAP**: convex_hull은 출력 ≤ 입력길이(정점 ≤ n)이지만 2단계 size-probe(상한 2n)를 답습.
- **honest gate 실측(3 op 모두 passed=True·c_verified=true·ziglang cc)**: Python==독립 oracle diff 0.0 / C==Python bit 일치 diff 0.0.
- **work-graph op 파도**: 3개 기하 op도 `algo_gate` 노드화(`1 op=1 노드`) → `run-once`로 무인 done(전 algo op 23이 gate화).
- **회귀**: `tests/test_algo.py`에 기하 테스트 군(기지해·scipy/numpy/matplotlib/권취수의 복수 독립 oracle 대조·볼록성/CCW/점 내포의
  구조검증·fail-soft·퇴화·no-mutation·python exact·C bit 일치). 전 스위트 **4742 → 4765 passed / 0 failed**(+23)·ruff clean·mypy 신규 0.

### P6 적대적 리뷰(2026-08-17, [[feedback_no_solo_ai_judgment]])
2건의 독립 적대적 리뷰 Workflow(각 finding을 검증 에이전트가 실 compile/실행/스트레스로 재현)를 병행 실시:
- **P6a(polygon_area2 / point_in_polygon, 4개 렌즈·102 tool uses) = findings 0**. geometry-correctness / C-safety /
  gate-honesty / integration-focus 모두 제로(정수 엄밀·경계 공개·2^53 영역을 사전 실측완료). 나도 최악 케이스(box 순회 스파이럴
  n=1e5)에서 2×면적=2.0e15 < 2^53을 실측해 op==numpy==C 일치를 확인완료.
- **P6b(convex_hull, 3개 렌즈·85 tool uses) = 1 raw → 0 CONFIRMED**(1 REFUTED). 유일한 지적 「dedup 삭제 변이가 difftest를
  통과」는 **비결함**이라고 검증으로 기각: dedup은 strict `<=0` monotone-chain pop + `hv<3` 후치 체크로 이미 보증되는 **방어적 잉여**
  (양쪽 backend 모두 삭제해도 등가=200,000 중복 다점 집합에서 divergence 0). 검증 에이전트가 독립적으로 확인=**2n size-probe는 타이트한
  비초과 상한**(포물선 입력에서 out_len=2n) / **ASan+UBSan이 1104개 hostile case에서 클린**(out[] 기록 OOB 없음·long long 외적
  overflow 없음) / C==Python bit 일치·Python==scipy 정점집합 전 일치 / CCW-from-lex-min 순서도 test로 담보 / qsort 불안정성은
  (x,y) 전순서 비교자 + 인접 dedup으로 무영향(=`sorted(set())`). → dedup이 방어적 잉여라는 취지의 설명 코멘트만 추기(동작 불변).
- **결론**: P6 기하 3 op에 shipped bug 없음. commit + push는 이 세션(`24bc8ad`).

## P7 완수 기록 — 선분교차(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**기하 툴킷을 1 op 확장**: `segments_intersect`(KIND_REDUCE) = 2개의 닫힌 선분 `[x1,y1,x2,y2,x3,y3,x4,y4]`가 교차하는지
(1.0/0.0). **이미지의 직선/윤곽 해석으로의 가교**. CLRS 33.1의 정수 orientation 법(proper crossing = 끝점이 상대 선을 엄밀히
가로지름 + 4가지 공선 on-segment 특수 케이스). 정수좌표 [-100000,100000]에서 외적은 엄밀(|cross| ≤ 8e10이 long long에 수용됨)=
C bit 일치. **oracle = `sympy.geometry`의 Segment 교차**(기호계산=orientation과는 전혀 다른 방법). 실측: 고정 8케이스 정답 +
**sympy와 2970개 랜덤 정수 선분쌍에서 mismatch 0**(공선 중복/T자/끝점공유/near-miss를 포함). 퇴화(점) 선분은 sympy가
Segment를 만들 수 없으므로 holdout에서 제외(op는 일반 orientation 로직으로 동작하지만 미gate=공개). difftest passed(python exact /
C bit 일치 / c_verified), work-graph 노드 무인 done(전 algo op 24가 gate화).

### P7 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
3개 렌즈 적대적 리뷰(검증 에이전트가 실 compile/실행으로 재현) = **1 raw → 1 CONFIRMED**(MED·gate-honesty). **op 자체는
올바르다**(sympy와 전 일치)만, **difftest holdout이 d1/d3/d4의 on-segment 특수 케이스(끝점이 상대 선분의 내부에 놓임=공유 끝점 없음)
를 단독 이유로 하는 1.0 판정으로서 한 번도 구동하지 않아**, 그 분기를 뺀 wrong op를 gate가 통과시킨다(50개 holdout의 판정이 하나도 바뀌지 않음).
자체 재현으로 확정(d3+d4 drop 변이가 passed=True·`[0,0,10,0,3,0,3,5]`→0.0 오류). **수정**=각 on_seg 분기(d1/d2/d3/d4)를 단독 이유로
하는 고정 holdout 케이스(끝점이 상대 내부·축 평행 4 + 대각 2)를 추가 → **각 분기를 빼면 difftest가 FAIL**(d1/d2/d3/d4 모두
passed=False)을 자체 확인. 기지해 테스트에도 끝점-내부 4케이스를 추가. 전 스위트 **4765 → 4772 passed / 0 failed**(+7)·ruff clean·
mypy 신규 0.

## P8 완수 기록 — 탐색/선택(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**탐색/선택 알고리즘 2종을 algo tier에 추가**(기하에서 다른 도메인으로 옮겨 tier를 균등화). 비교 기반으로 임의의
(NaN-free) double을 다룬다=결과는 index 또는 기존 요소이므로 exact(tol 0)·C bit 일치.
- **op(2)**: `binary_search`(KIND_REDUCE): 정렬된 열 `[target, v0..v_{n-1}]`의 target의 **최좌 index**(lower bound), 없으면
  -1.0. oracle=`bisect_left` + 존재확인(독립). / `kth_smallest`(KIND_REDUCE): `[k, v0..]`의 k번째로 작은 값(0-indexed order
  statistic)을 **quickselect**(median-of-three pivot·Lomuto)로. **k번째 값은 순서 비의존**이므로 pivot 순서가 달라도 C==Python bit
  일치. oracle=`sorted()[k]`(Timsort=다른 알고리즘). median-of-three로 정렬된 입력도 O(n)(n=40001이 <2s).
- **honest gate 실측**: 양 op 모두 passed=True·python exact / C bit 일치 / c_verified. **각 5000개 랜덤 케이스에서 oracle과
  mismatch 0**을 사전 실측. fail-soft=binary_search는 빈/없음→-1.0, kth_smallest는 k 영역외/비정수/빈→0.0.
- **work-graph**: 2 op도 `algo_gate` 노드 무인 done(전 algo op 26이 gate화). 회귀=`tests/test_algo.py`에 P8 군(기지해·
  bisect/sorted 대조·O(n²) 가드·fail-soft·no-mutation·python exact·C bit 일치). ruff clean·mypy 신규 0.

### P8 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
2개 렌즈 적대적 리뷰(실 compile/실행 검증) = **1 raw → 1 CONFIRMED**(LOW·correctness). **정확성 불변이지만 성능 결함**:
kth_smallest의 quickselect가 단일 pivot Lomuto이므로 **all-equal/저카디널리티 대입력에서 O(n²)**(median-of-three는 중복을
보호하지 않음·n=40000 all-equal에서 7.44s, sorted/reverse는 고속). 테스트는 holdout n≤30·타이밍 테스트가 sorted만으로 미포착.
자매인 quicksort는 이미 3-way(Dutch flag) partition을 사용. **수정**=kth_smallest를 **3-way(Dutch national flag) partition**으로
재작성(equal-band로 중복을 접어→all-equal을 O(n)으로·비교만+순서 비의존으로 **C==Python==sorted()[k] parity 유지**). 자체 재현으로
확인=**all-equal n=40000이 7.44s → 0.0019s**(O(n)화)·correctness 5000 cases mism 0·difftest bit 일치. 타이밍 테스트를
sorted/reverse/**all_equal/few_distinct**로 확대(회귀를 실제로 가드).

## P9 완수 기록 — 통계/집계(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**통계 op 2종을 algo tier에 추가**: `count_distinct`(distinct 값 수=정수 count) / `mode_value`(최빈값·작은 쪽이 tie 승리).
비교 기반(임의의 NaN-free double)·결과는 count 또는 기존 요소이므로 exact(tol 0). 양 op 모두 copy를 sort → run 주사(결과는
순서 비의존으로 C의 qsort와 Python의 sorted가 달라도 bit 일치). oracle=`len(set())` / `collections.Counter`(독립 메커니즘).
**★proactive 견고화**: mode_value의 제로 mode에서 ±0.0 혼재 시, C의 unstable qsort와 Python의 stable sort로 반환값의 부호가 어긋나
bit 불일치가 될 수 있음 → **`+ 0.0`으로 −0.0→+0.0 정준화**(다른 값은 불변)로 C==Python을 견고하게(rle_encode의 signed-zero 공개와 같은 계열).
실측: 각 5000개 랜덤 케이스에서 oracle mismatch 0·difftest passed(python exact / C bit 일치 / c_verified). 전 algo op 28이 gate화.
ruff clean·mypy 신규 0.

### P9 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
2개 렌즈 적대적 리뷰(실 compile/실행/변이 검증) = **1 raw → 1 CONFIRMED**(MED·gate-safety). **정확성 불변이지만 gate coverage gap**:
mode_value의 `+0.0` 정준화를 빼는 변이를 holdout이 falsify할 수 없다(유일한 signed-zero 케이스 `[0.0,-0.0,0.0]`이 양 backend에서
+0.0-last로 정렬 → 정준화 삭제해도 bit 일치). 코멘트가 담보한다고 주장하는 bit-check가 정준화를 한 번도 실제로 구동하지 않는다. **수정**=
`-0.0`이 run 말미에 오지 않는 `[0.0,-0.0]`·`[-0.0,0.0]`을 holdout에 추가(양 순서=qsort tie 순서에 무관하게 한쪽은 반드시 발산). 자체 재현으로
확인=**정준화 삭제 변이가 difftest FAIL**·현행(정준화완료) 코드는 추가 케이스에서 bit 일치 pass. 전 스위트 **4787 → 4796 passed / 0 failed**.

## P10 완수 기록 — 수론(제2부)(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**수론 op 2종을 추가**(P5의 정수 메커니즘 위에·category numtheory를 공유). 정수를 float64로 운반(exact <2^53)·honest 영역에서 전
모듈러 곱이 uint64/long long에 수용됨=C bit 일치이면서 Python==독립 oracle tol 0.
- **op(2)**: `is_prime`(KIND_REDUCE): **결정적 Miller-Rabin**(witness {2..37}). honest 영역 0≤n≤2^32−1(a·a mod n이 uint64에
  수용되고 witness set이 결정적=n<3.3e24까지 소수성 증명). oracle=`sympy.isprime`. ★Carmichael 수(561/1105/1729/2465…)를
  올바르게 합성수 판정. / `modular_inverse`(KIND_REDUCE): **확장 유클리드**로 a^−1 mod m(gcd≠1은 −1.0). 영역 a≤2^53·m≤2^53(Bezout
  계수는 불변량 |q·s|=|old_s−new_s|≤2m으로 long long에 수용됨)·m=1→0. C의 truncated mod를 [0,m−1]로 정규화(+m)해서 Python의
  floor mod와 일치. oracle=builtin `pow(a,−1,m)`.
- **honest gate 실측**: 양 op passed=True·python exact / C bit 일치 / c_verified. **is_prime을 sympy와 8000 random + 2000
  exhaustive(561 Carmichael 포함)에서 mism 0 / modular_inverse를 pow와 8000에서 mism 0**을 사전 실측. 전 algo op 30이 gate화.
  ruff clean·mypy 신규 0.

### P10 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
2개 렌즈 적대적 리뷰(실 compile/실행/변이 검증) = **1 raw → 1 CONFIRMED**(MED·c-safety-gate). **op 자체는 올바르고 overflow-safe**
(353개 적대적 케이스로 검증)이지만, **modular_inverse의 holdout이 선언 영역 2^53을 구동하지 않아**(in-domain m이 ~1e9에 그침), C의
`long long→int` 폭축소 변이(2^53 영역을 무너뜨림)가 gate를 bit 일치로 통과. 자매인 pow_mod(base=exp=2^53을 핀) / gcd_seq(2^53 가드 끝) /
is_prime(near-2^32)은 같은 종류의 변이를 포착하는데 modular_inverse만 미대응. **수정**=2^53 끝 케이스(`[2, 2^53−1]` coprime→inverse·
large coprime near 2^53·`[2^52, 2^53]` both even→−1)를 holdout에 추가(Bezout 연산이 |q·s|~2m~2^54를 구동). 자체 재현으로 확인=
**`long long→int` 변이가 difftest FAIL**·baseline은 bit 일치 pass. oracle(pow)은 이미 대응완료이므로 holdout만 추가. 전 스위트 녹색.

## P11 완수 기록 — 비트 조작(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**비트 조작 op 2종을 추가**: `xor_reduce`(전 요소의 bitwise XOR) / `popcount_total`(전 요소의 1비트 총수=Kernighan).
비음수 정수를 float64로 운반하고, 영역 [0, 2^53−1]에서 전 값을 53비트에 담는다(XOR 결과도 < 2^53=exact·popcount는 작은 정수)=
C bit 일치이면서 Python==독립 oracle(`functools.reduce(operator.xor)` / builtin `int.bit_count()`=Kernighan과는 다른 메커니즘) tol 0.
양 op 모두 passed=True·python exact / C bit 일치 / c_verified. 각 3000개 랜덤 케이스에서 oracle mism 0을 사전 실측. fail-soft=음수/비정수/≥2^53→0.0.
전 algo op 32가 gate화. ruff clean(FURB161로 `bin().count('1')`→`.bit_count()`화)·mypy 신규 0.

### P11 적대적 리뷰 결과(2026-08-17, [[feedback_no_solo_ai_judgment]])
2개 렌즈 적대적 리뷰 Workflow(correctness + gate-safety, `wf_7d130631-c0f`) = **findings 0(결함 없음)**. 리뷰어1은
`{findings:[]}`, 리뷰어2는 「게이트 mutation testing(구현을 부수어 게이트가 잡는가)」 도중 window 압축으로 중단
(결과 미산출). **규율에 따라, 죽은 background를 되살리지 않고, 내가 같은 mutation test를 1차 검증으로 완수**: xor_reduce/popcount_total
의 대표 7개 변이(빈 초기화 acc=1 / OR 오용 / 2^53 영역 경계 off-by-one / 음수 가드 제거 / Kernighan→shift[popcount≠bitlength] /
+2 오류 / 2^53 admit)를 holdout에 대해 실행 → **전 7개 변이를 독립 oracle이 포착**(oracle_err > 0). **결론=P11 게이트는
falsifying·확정 결함 없음**(`fed093a`는 정당·follow-up commit 불필요).

## P12 완수 기록 — 확장 유클리드 호제법(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**수론 op 1종을 추가**(P5의 정수 메커니즘 + P10의 Bezout 불변량 위에·category numtheory를 공유=P5+P10+P12).
`extended_gcd`(**KIND_MAP**): 입력 `[a, b]`(비음수 정수 ≤ 2^53) → 출력 `[g, x, y]`(**엄밀 3값**, `a·x + b·y = g = gcd(a,b)`),
영역 외는 `[]` fail-soft. 반복판 two-variable sweep으로 계수를 계산. **계수는 엄밀**(불변량 `|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤ 2^54`
가 C의 long long에 수용됨)이므로 C == Python bit 일치. domain은 **[0, 2^53] inclusive**(2^53은 exact·계수 |x|,|y| ≲ 2^52도
float64로 exact).
- **★oracle 독립성의 요점(P10의 교훈)**: Bezout (x,y)는 비유일이므로 「`a·x+b·y==g`」의 **항등식 검증으로는 부호/정준형의 어긋남을
  gate가 falsify할 수 없다**. → oracle은 **독립적인 재귀판 확장 유클리드 `_ext_gcd_rec`(다른 코드 경로)로 (g,x,y)를 계산해 요소 일치**.
  반복판과 재귀판은 동일한 canonical 계수를 반환한다(재귀를 전개하면 반복이 됨=수학적으로 일치, `[0,b]`/`[a,0]`/`[0,0]`/등가 전 끝점도 일치 확인).
- **honest gate 실측(passed=True·c_verified=true·ziglang cc·70 cases)**: python==독립 재귀 oracle **diff 0.0(exact)** /
  codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**200,000 랜덤(2^53 영역 끝 포함)에서 반복 op == 재귀 oracle mism 0이면서
  `a·x+b·y==g==math.gcd(a,b)` 항등식(bignum으로 독립 검산) 실패 0**. fail-soft=짧음/비정수/음수/NaN/>2^53 → `[]`.
- **★게이트 mutation test(자체 검증)**: swap x,y / negate x / drop old_s update / widen guard(>2^53 admit) / wrong-length
  의 5개 종단 변이를 **전부 포착**(요소 불일치 또는 구조 불일치 inf). 잘못된 몫 q+1은 op 자신이 무한루프(difftest harness의
  timeout이 failure 검출)=종단하는 잘못된 구현은 전부 falsify.
- **holdout(영역 끝과 전 분기를 단독 이유로 구동)**: 기지 `[35,15]→(5,1,-2)` 등 + coprime/비coprime + 등가 `[7,7]` + 한쪽 0
  (`[0,5]`/`[5,0]`/`[0,0]`) + a=1 + **2^53 영역 끝**(`[2, 2^53−1]` coprime·large coprime near 2^53·`[2^52, 2^53]` gcd 2^52·
  `[2^53, 6]` inclusive 상단) + 영역 외 fail-soft(짧음/`>2^53`=`[2^53+2,3]`/비정수/음수/NaN) + random 48.
- **work-graph op 파도**: extended_gcd를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`·priority 0·tool capability·
  produces=gate JSON) → `run-once --available tool:command`로 **무인 done**(passed:true·c_verified·bit 일치 마커 생성).
  = **전 algo op 33이 work-graph 게이트화**(32→33).
- **회귀**: `tests/test_algo.py`에 P12 군(기지값·Bezout 항등식 random×5000·독립 재귀 oracle 일치 random×5000·fail-soft·
  category grouping[numtheory=P5+P10+P12]·difftest python exact·C bit 일치). 전 스위트 **4827 passed / 0 failed**(test_algo.py
  단체 260)·내 전 변경 ruff clean·mypy 신규 0(origin/master=15와 동수=net-new 0).

### P12 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
3개 렌즈 적대적 리뷰 Workflow(correctness / c-safety+gate-honesty / integration, 각 finding을 검증 에이전트가 **실 compile/
실행의 mutation으로 재현**, 5 agents·125 tool uses) = **2 raw(동일 근본원인) → 1 CONFIRMED**(MED·gate-cannot-falsify). **op 자체는
올바르다**(200k + 전 끝에서 검증·재귀 oracle과 비발산·in-domain에서 long long overflow 없음)만, **difftest holdout의 영역 외 케이스가 전부
operand `a` 쪽**(`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`)이고, 유일한 bad-`b` 케이스 `[7,NaN]`은 NaN이 `bd>=0.0`에서 단락되어 b의 3개 가드절을
하나도 단독 구동하지 않는다 → **`b` 쪽 가드의 편측 퇴행(a/b는 복붙 대칭이므로 plausible)이 양쪽 게이트 절반을 통과**(P5/P7/P9/P10과 같은 gate-coverage
교훈). **자체 재현으로 확정**: `bd>=0` / `bd<=2^53` / `bd==int`를 _PY/_C 양쪽에서 삭제 → **모두 `passed=True`(MISSED)**, 대칭인 `a` 쪽 삭제는
전부 `passed=False`(CAUGHT·a의 영역 끝이 holdout에 있으므로). **수정**=`[valid_a, finite_bad_b]` 케이스(`[3, 2^53+2]`·`[7,-1]`·`[7,2.5]`)
를 holdout과 fail-soft 테스트에 추가 → 재실측으로 **b 쪽 3개 삭제가 전부 CAUGHT(passed=False, pydiff=inf)**·baseline은 70 cases에서 bit 일치
pass. ★**검증 에이전트의 honest한 정정을 채택**(finding의 과잉 주장은 각하): 「`bd<=2^53` 삭제는 b=2^62에서 C long long overflow UB」는
**부정확** — b=2^62에서 C(long long)와 Python(bignum)은 bit 일치(overflow 없음). 진짜 오류는 **출력의 정밀도 손실**(Bezout 계수가 > 2^53에서
float64로 엄밀 표현 불가능해 `a·x+b·y==g`가 깨짐)이며, `b<=2^53` 상한은 이 정밀도를 지킨다. 메커니즘은 오류지만 결함과 remedy는 성립=채택.

## P13 완수 기록 — 최근접점쌍(분할정복)(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**계산기하를 1 op 확장(P6/P7에 이은 geometry 제2탄)**: `closest_pair`(KIND_REDUCE) = 2-D 정수 점군의 **최소 제곱거리**를
**분할정복**(CLRS 33.4)으로 구한다. 입력 `[x0,y0,x1,y1,...]`(2n개·정수좌표 [-1e5,1e5]) → 출력=최소 제곱 유클리드 거리
(정수 엄밀). **제곱거리만(sqrt 없음)**이므로 long long/정수 float64에 닫혀, C==Python bit 일치. 최대 제곱거리 = (2e5)²×2 = 8e10
< 2^53=exact. fail-soft=점 <2(n<4) / 홀수길이 / 좌표가 비정수·[-1e5,1e5] 영역 외 → -1.0.
- **알고리즘**: x로 정렬(동률은 y) → 좌우 절반을 재귀 → d=min(dl,dr) → 중앙선에서 (x−midx)²<d의 점으로 strip 구축 →
  strip을 y로 정렬 → 각 점에서 전방 주사(`(yj−yi)²<d`인 동안만=7 이웃 상한). base(m≤3)는 전수조사. 중복점(dist 0)은
  같은 x가 인접 정렬되어, 분할선을 넘어도 strip이 포착. C는 `CpPt` 구조체 + `cp_rec` 재귀 + `cp_cmp_x/cp_cmp_y`(qsort)를
  op.c_code 내에 정의(codegen은 c_code를 verbatim 삽입하므로 static helper 가능). strip 버퍼는 1개를 재귀 사이에 공유
  (자식이 먼저 완료=post-order이므로 alias 없음). 재귀 깊이 ~log2(n)(n=1e5에서 17)=스택 안전.
- **honest gate 실측(passed=True·c_verified=true·ziglang cc·58 cases)**: python==**독립 전수조사 O(n²) 오라클**(정렬/strip
  없는 다른 코드 경로) **diff 0.0(exact)** / codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**30,000 랜덤(클러스터 R=3/8/30으로
  strip 깊이를 구동) + 16,000 적대적 레이아웃(밀집 그리드/종횡 직선[전 점이 strip 내]/미소 클러스터/경계 좌표)에서 전수조사와 mism 0**.
- **★게이트 mutation test(자체 검증)**: strip 스캔 생략 / sq가 y 무시 / 좌표 상한 삭제 / 좌표 하한 삭제 / 정수성 삭제 / 빈 strip의
  6개 변이를 **전부 포착**(passed=False). cross-strip 최소 케이스([-5,-5,-1,0,1,0,5,5]→4)가 strip 로직을, 양쪽 좌표 슬롯의 영역 외
  케이스가 가드를 단독 구동(P12의 편측 가드 교훈을 반영).
- **holdout**: 기지(단일쌍 25·3점·중복 dist0·세로 일렬·**cross-strip 최소**) + 극단 in-domain 좌표(8e10 상단) + 영역 외를 **양
  좌표 슬롯**에서 단독 이유화(홀수길이/1점/비정수 x·y/±1e5 초과 x·y/NaN x·y) + random 40(클러스터).
- **work-graph op 파도**: closest_pair를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`) → `run-once`로 무인 done.
  = **전 algo op 34가 work-graph 게이트화**(33→34).
- **회귀**: `tests/test_algo.py`에 P13 군(기지값·전수조사 일치 random×4000·fail-soft[양 좌표 슬롯]·category grouping
  [geometry=P6+P7+P13]·difftest python exact·C bit 일치). 전 스위트 **4834 passed / 0 failed**(+7)·ruff clean·mypy
  신규 0(origin/master=15와 동수). 적대적 리뷰 결과=아래(1 CONFIRMED를 자체 재현·수정).

### P13 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
3개 렌즈 적대적 리뷰 Workflow(correctness / c-safety+gate-honesty / integration, 각 finding을 검증 에이전트가 **실 compile/
실행의 mutation으로 재현**) = **3개 렌즈가 동일 근본원인으로 수렴 → 1 CONFIRMED**(severity=내 초기 평가 MED / **검증 에이전트는 HIGH**
=gate-honesty 실패[gate가 잘못된 op를 green-light]를 무겁게 봄. honest 공개로서 양론 병기·수정 내용은 동일). **op 자체는 올바르다**(30k+16k
적대적 케이스에서 전수조사와 mism 0)만, **difftest holdout이 strip의 y-scan을 immediate neighbor(j==i+1)보다 앞으로 구동하지 않아** →
strip 전방주사를 **j==i+1만으로 잘라내는 regression을 gate가 falsify할 수 없다**(7-이웃 정리는 「최대 7」이지 「1」이 아니므로,
y 순서로 비인접인 최근접 쌍이 실재할 수 있다). **자체 재현으로 확정**: 주사를 `range(i+1, min(i+2, sc))`로 잘라낸 mutation을 _PY/_C 양쪽에
적용 → `passed=True`(MISSED). falsify하는 최소 케이스를 정수 격자로 탐색해 발견(예 `[0,-6,-2,-2,4,-3,-5,3]`= 최근접 쌍이 y 순서로
2개 떨어짐 → full/전수조사 20이지만 j==i+1-only는 25). **수정**=strip 내에서 최근접 쌍이 y-sorted로 비인접이 되는 3케이스
(`[0,-6,-2,-2,4,-3,-5,3]`→20 / `[-4,5,-1,-3,0,-1,3,-3]`→5 / `[-1,-6,-1,0,-5,-4,1,-4,4,4]`→8)를 holdout과 기지값 테스트에 추가 →
재실측으로 **j==i+1-only mutation이 CAUGHT(passed=False, pydiff=12)**·baseline은 61 cases에서 bit 일치 pass·다른 5개 mutation도 회귀
없음. 기존 6개 mutation(strip 생략/sq y 무시/좌표 상하한/정수성/빈 strip)에 더해 strip 주사 깊이도 falsify 가능해짐(P12의 gate-coverage
교훈을 geometry의 strip 주사로 확장).

## P14 완수 기록 — Huffman 최적 프리픽스 부호 비용(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**데이터 압축을 1 op 확장(P5 rle_encode에 이은 compress 제2탄)**: `huffman_cost`(KIND_REDUCE) = 기호 빈도 `[f0,f1,...]`
(비음수 정수 ≤2^40)에 대한 **최적 프리픽스(Huffman) 부호의 최소 총비용**=전 내부노드의 결합가중치 합(=Σ freq×부호길이).
**★핵심=최적비용은 tie 불변**(기호별 부호길이는 tie 처리에 따라 달라지지만, 총비용은 빈도 다중집합으로 일의)이므로 C와 Python이 동등가중
요소를 다른 순서로 꺼내도 **총합은 동일=bit 일치가 깔끔하게 성립**. 정수를 long long으로 운반(영역 가드로 < 2^54로 속박=overflow 없음).
- **알고리즘=2 큐 법**(Huffman O(n log n)): 빈도를 오름차순 정렬해 q1[잎]에, q2[병합노드]는 비감소로 생성 → q1/q2의
  각 선두에서 2 최소값을 꺼내 병합합 s를 total에 더하고 q2 말미로(n−1회). C도 2개 배열 + 2개 선두 index로 동일 구현(qsort 비교자 hc_cmp).
- **영역과 fail-soft**: 각 빈도 0≤f≤2^40(정수)·else -1.0. **merge total이 2^53을 넘으면 -1.0**(float64로 엄밀 표현 불가)=**값이critical한
  exactness 분기(falsify 가능)**. 총빈도 total_freq를 guard 중 누적해 >2^53에서 조기 -1.0 = long long safety(각 s≤total_freq≤2^53·
  total≤2^54<2^63). n=0/1 → 0.0. ★**honest 공개**: 상류 total_freq guard는 「빈도합계 자체가 long long을 넘치게 하는 극단적 n(>~4M 기호)」
  에 대한 safety guard로, 현실적 n에서는 merge bail과 같은 -1.0을 반환=값 비교로 단독 falsify하기 어렵다(P5의 OOB 가드 공개와 같은 형태). exactness를
  지키는 merge-total bail은 holdout의 `[2^40]×1024`(합계 2^50<2^53으로 상류 통과·비용~2^53.3으로 merge bail)가 단독 구동=falsify 가능.
- **honest gate 실측(passed=True·c_verified=true·ziglang cc)**: python==**독립 heapq(min-heap)판 Huffman 비용**(2큐와 다른
  코드 경로) **diff 0.0(exact)** / codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**50k 랜덤(전 동일빈도/0빈도/2^40 영역 끝에서
  tie를 구동)에서 heapq와 mism 0**·**4k 미소 케이스에서 전 결합순서의 전수 최적(true optimum)과 mism 0**(=greedy가 최적을 달성)·**20k에서
  역 tie 순 heap과 mism 0**(=tie 불변을 실증).
- **★게이트 mutation test(자체 검증)**: 빈도상한 삭제 / 음수가드 삭제 / 정수성 삭제 / **merge-total bail 무효화**(`[2^40]×1024`가
  falsify) / 병합이 x2를 놓침 / n==1이 1.0을 반환 하는 6개 값 분기 변이를 **전부 포착**(passed=False).
- **work-graph op 파도**: huffman_cost를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`) → `run-once`로 무인 done.
  = **전 algo op 35가 work-graph 게이트화**(34→35).
- **회귀**: `tests/test_algo.py`에 P14 군(기지값·heapq 일치 random×5000·fail-soft/overflow·category grouping[compress=P5+P14]·
  difftest python exact·C bit 일치). 전 스위트 **4841 passed / 0 failed**(+7)·ruff clean·mypy 신규 0(origin/master=15와 동수).

### P14 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
3개 렌즈 적대적 리뷰 Workflow(correctness / c-safety+gate-honesty / integration, 각 finding을 검증 에이전트가 **실 mutation으로 재현**) =
**3 CONFIRMED**(모두 overflow bail 경계의 gate-coverage·op 자체는 올바르고 tie 불변도 50k+4k+20k로 확정완료). **correctness 계열의 지적 0**
(tie 불변 claim·2큐법의 최적성은 견고). CONFIRMED는 모두 「merge-total>2^53의 fail-soft 경계」의 망라:
- **[MED] 임계값이 ~6 decade 미고정**(merge-total의 threshold 2^53을 2^50 등으로 좁히는 변이가 gate를 통과) = **자체 재현으로 확정**(2^53→2^50
  변이가 passed=True). **수정**=`[2^40]×837`(cost 8997303650091008 ≈ 2^52.998·VALID·엄밀 반환) + `[2^40]×838`(cost > 2^53 → -1.0)을
  holdout에 추가해 임계값을 **2^53의 ±~1e13에 타이트 고정** → 재실측으로 threshold 축소 변이(2^53→2^50·→8e15)가 전부 **CAUGHT**. 기지값 테스트에도
  837/838을 추가.
- **[MED] cost == exactly 2^53이 holdout에 없어 `>`→`>=` off-by-one 미포착 → WITNESS로 수정**: 당초 「freq ≤ 2^40에서는 cost가 정확히
  2^53이 되지 않는다」라고 공개하려 했으나, **검증 에이전트가 construction을 발견**=`2^16개 × freq 2^33`(= 2^33 ≤ 2^40)은 각 깊이 16에서
  **cost = 2^16 · 2^33 · 16 = 정확히 2^53**. 2^53은 표현 가능하므로 VALID(2^53을 반환)이며, `>=` 변이는 이를 잘못 -1.0으로 떨어뜨린다. **직접
  1차 검증**(bignum으로 cost==2^53 확인·op가 2^53 반환·total_freq=2^49<2^53으로 상류 통과)한 후, 이 witness 케이스를 holdout과 기지값
  테스트에 **채택** → `>`→`>=` off-by-one이 falsify 가능해짐(이 1개의 값 경계를 단독으로 pin). **적대적 리뷰가 gap뿐 아니라 fix 그 자체를
  발견한 좋은 예**(내 당초의 「도달불가」 판단을 반증).
- **[LOW] 상류 `total_freq > 2^53` guard branch가 미구동/비falsify** = **honest 공개**: 이는 「빈도합계 자체가 long long을 넘치게 하는 극단적
  n(>~4M 기호)」에 대한 safety guard. 현실적 n에서는 merge bail이 같은 -1.0을 반환(삭제해도 long long overflow 없이 결과 불변)하므로 값 비교로 단독
  falsify할 수 없다(P5의 OOB 가드 공개와 같은 형태). 극단 n의 holdout은 비현실적으로 느리므로 추가하지 않는다.
- 검증 에이전트는 3건을 「gate가 특정 잘못된 구현을 falsify할 수 없다」는 실제 결함으로 CONFIRMED. **op의 정확성은 불변**(잘못된 op를 출하하지 않음),
  gate의 망라를 #2로 강화하고 #1/#3을 honest 공개.

## P15 완수 기록 — 최장 증가 부분수열의 길이(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**탐색/선택을 1 op 확장(P8 binary_search/kth_smallest에 이은 search 제2탄·DP/patience sorting의 신규 알고리즘 계열)**:
`lis_length`(KIND_REDUCE) = 임의의 NaN-free double 열의 **최장 강증가 부분수열(LIS)의 길이**를 **patience sorting**으로 구한다.
비교만(값에 산술을 가하지 않음)이므로 길이는 배열 고유로 일의=**C==Python bit 일치**. tails[k]에 길이 k+1의 증가 부분수열의 최소 말미를 두고,
각 요소에서 `tails[mid] < x`(bisect_left·**강증가**) 위치를 치환 또는 말미 확장(O(n log n)). 빈→0.0, NaN 혼재→-1.0 fail-soft(`x != x`로 검출).
- **honest gate 실측(passed=True·c_verified=true·ziglang cc)**: python==**독립 O(n²) DP 오라클**(`dp[i]=1+max(dp[j]|j<i,a[j]<a[i])`
  =patience sorting과 다른 코드 경로) **diff 0.0(exact)** / codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**40k 랜덤(정수+float·
  작은 범위로 tie를 대량 발생=강증가 비교를 구동)에서 DP와 mism 0**.
- **★게이트 mutation test(자체 검증)**: 강증가 `<`→`<=`(비감소=다른 답) / NaN 가드 삭제 / 이분탐색 방향 반전 의 3개 변이를 **전부 포착**
  (passed=False). 전부 동일 `[2,2,2,2]`→1과 중복 교대 케이스가 강증가 비교를 단독 구동, NaN holdout이 가드를 구동.
- **holdout**: 기지(`[3,1,2,4]`→3·`[5,4,3,2,1]`→1·전 증가→n·빈→0·단일→1) + **전 동일→1(강증가로 중복 비신장)** + 중복 교대 + 
  -0.0/+0.0 등가 + ±inf + float의 tie + NaN을 **선두/중앙/말미**에서 fail-soft + random(정수 tie 다수 + float).
- **C 안전**: tails 버퍼 malloc(n)·기록 tails[lo]는 lo≤len<n으로 OOB 없음·n=0은 malloc(1)+루프 미실행으로 0.0·malloc 실패는 -1.0·
  NaN 가드는 전 비교 전(NaN 안전).
- **work-graph op 파도**: lis_length를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`) → `run-once`로 무인 done.
  = **전 algo op 36이 work-graph 게이트화**(35→36).
- **회귀**: `tests/test_algo.py`에 P15 군(기지값·DP 일치 random×5000·NaN fail-soft[3위치]·category grouping[search=P8+P15]·
  difftest python exact·C bit 일치). 전 스위트 **4848 passed / 0 failed**(+7)·ruff clean·mypy 신규 0(origin/master=15와 동수).

### P15 적대적 리뷰 결과(2026-08-17, [[feedback_no_solo_ai_judgment]])
3개 렌즈 적대적 리뷰 Workflow(correctness / c-safety+gate-honesty / integration, mutation 검증) = **findings 0**(전 렌즈 지적 없음).
patience sorting의 강증가 비교·NaN 가드·tails 버퍼 안전·O(n²) DP oracle의 독립성·holdout의 강증가 단독 구동을 검증했고, falsify 가능한
결함은 검출되지 않음. 사전의 mutation 3/3 포착(강증가 `<`→`<=`/NaN 가드/이분탐색 방향)과 40k DP 일치로 gate는 견고.

## P16 완수 기록 — 전도수(마스터 정렬법)(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**통계를 1 op 확장(P9 count_distinct/mode_value에 이은 stat 제2탄)**: `count_inversions`(KIND_REDUCE) = 임의의 NaN-free double 열의
**전도수**(i<j이면서 a[i] > a[j]인 **강**쌍의 수)를 **계수 병합정렬**로 O(n log n)에 구한다. 비교만(값에 산술 없음)이므로 count는 배열 고유로 일의
=**C==Python bit 일치**. 병합 시 우측 열을 먼저 취할 때마다 남은 좌측 열 수를 가산(고전적). count는 비음수 정수이므로 **-1.0이 safe sentinel**: NaN→-1.0
fail-soft, 빈/단일→0.0. 등가는 전도가 아니다(tie로 좌측을 먼저 취함=`arr[i] <= arr[j]`).
- **honest gate 실측(passed=True·c_verified=true·ziglang cc)**: python==**독립 O(n²) 전수조사 count**(병합정렬과 다른 코드 경로)
  **diff 0.0(exact)** / codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**40k 랜덤(정수+float·작은 범위로 tie 대량=강비교를
  구동)에서 전수조사와 mism 0**.
- **★게이트 mutation test(자체 검증)**: tie 처리 `<=`→`<`(등가를 전도로 오계상) / inv 계수 off-by-one / NaN 가드 삭제 / 비계수(inv=0)
  의 4개 변이를 **전부 포착**(passed=False). 전 동일 `[2,2,2]`→0과 중복 케이스가 강비교를 단독 구동.
- **holdout**: 기지(sorted→0·reversed→n(n-1)/2·`[2,1,3]`→1·`[3,1,2]`→2·빈/단일→0) + **전 동일→0(강)** + 중복(sorted→0·
  `[2,1,2,1]`→3) + -0.0/+0.0 등가(양 순서) + ±inf + NaN을 **선두/중앙/말미**에서 fail-soft + random(정수 tie 다수 + float).
- **C 안전**: arr/tmp를 malloc(n)·재귀깊이 O(log n)·malloc 실패는 -1.0·NaN 가드는 전 비교 전. count는 long long(n(n-1)/2 < 2^63 for
  n < 4.3e9), 반환 double은 n(n-1)/2 < 2^53으로 엄밀(honest: 극단적 n에서는 비엄밀해질 수 있으나 holdout/실용 영역에서는 엄밀).
- **work-graph op 파도**: count_inversions를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`) → `run-once`로 무인 done.
  = **전 algo op 37이 work-graph 게이트화**(36→37).
- **회귀**: `tests/test_algo.py`에 P16 군(기지값·전수조사 일치 random×5000·NaN fail-soft[3위치]·category grouping[stat=P9+P16]·
  difftest python exact·C bit 일치). 전 스위트 **4855 passed / 0 failed**(+7)·ruff clean·mypy 신규 0(origin/master=15와 동수).
  **적대적 리뷰는 worktree 격리로 실행**(P14에서
  리뷰 에이전트가 대상 repo의 algo.py를 mutate한 교훈=commit 후 격리 worktree에서 리뷰→결과는 follow-up).

### P16 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
**★worktree 격리 리뷰의 첫 적용이 성공**: 3개 렌즈 × 격리 git worktree(각 에이전트가 cd76da0으로부터 자기 전용 copy를 만들어 mutation)
→ **본 repo의 algo.py는 시종 clean**(검증 에이전트도 「real repo는 read only·격리 worktree에서 mutation·뒷정리 완료」라고 명기). P14의
오염 문제를 구조적으로 해소. 결과=**2 CONFIRMED(둘 다 LOW)**·correctness 계열 0(op는 올바름):
- **[LOW gate-coverage] long long 폭이 미falsify**: holdout의 최대 전도수가 INT_MAX 미만(len ≤ 40 → 최대 ~700)이므로, C의 누산기를
  `long long`→`int`로 축소하는 변이가 gate를 통과(shipped는 올바르게 long long). **자체 재현으로 확정**(int 축소 변이가 passed=True·
  n=65537의 강내림차순에서 진짜값 2147516416 > INT_MAX를 int가 -2147450880으로 wrap). **수정**=(1) **독립 Fenwick(BIT)판 오라클
  `_fenwick_inversions`**(O(n log n)·병합정렬과 다른 알고리즘=O(n²) 전수조사가 너무 느린 대형 n을 검산 가능)를 추가, (2) **강내림차순
  witness(n=65537, 전도수 2147516416 > INT_MAX)**를 holdout+기지값 테스트에 추가 → 재실측으로 int 축소 변이가 **CAUGHT**(passed=False).
- **[LOW annotation] 코멘트 오류**: `[inf,1,-inf]`에 `-> 2`라고 주석을 달았지만 실제로는 3(전 3쌍이 전도). gate는 oracle과 비교(3으로
  일치)하므로 잘못된 구현은 통과시키지 않는다=**주석뿐인 부정확**. **수정**=코멘트를 `-> 3`으로 정정(op/oracle/Fenwick 모두 3으로 일치를 확인).
- **★운용 개선의 실증**: 이후의 리뷰는 worktree 격리를 기본으로. 전 스위트 녹색·ruff clean·mypy 신규 0.

## P17 완수 기록 — 최대 부분수열합(Kadane 법)(2026-08-17, Opus5[1m]/ultracode, 12h 자율)
**탐색/최적화를 1 op 확장(P8 binary_search/kth_smallest·P15 lis_length에 이은 search 제3탄)**: `max_subarray`(KIND_REDUCE) = 정수값 double 열의
**연속 부분수열의 최대합**을 **Kadane의 O(n) 리셋 주사**(`cur = max(0, cur+x); best = max(best, cur)`)로 구한다. **빈 부분수열을 허용**(합 0)하므로 답은 **항상 ≥ 0**
(전 음수→0.0)=**-1.0이 safe sentinel**. 정수 영역(각 `|x| ≤ 2^52`이면서 절댓값의 진행합 ≤ 2^52)에서 전 부분합을 엄밀 정수 < 2^53으로 유지 → 답은 엄밀·
**C==Python bit 일치**. 독립 오라클(전 O(n²) 부분수열의 전수조사 최대)은 **정수 덧셈의 결합법칙**이므로 Kadane과 엄밀히 일치. fail-soft -1.0 = NaN / inf / 비정수 /
`|x| > 2^52` / 진행합 오버플로우.
- **honest gate 실측(passed=True·c_verified=true·ziglang cc)**: python==**독립 O(n²) 전수조사**(Kadane과 다른 코드 경로) **diff 0.0(exact)** /
  codegen **C==Python bit 일치 diff 0.0**. 사전 실측=**5000 랜덤(정수·혼합부호·작은 범위로 tie/리셋을 대량 구동)에서 전수조사와 mism 0**.
- **★게이트 mutation test(자체 검증)**: (1) overflow 가드 `>`→`>=`(exact-2^52 witness로 오bail) → **CAUGHT**, (2) 리셋 `if cur<0: cur=0` 삭제
  (접미합화=오류) → **CAUGHT**, (3) 영역가드 삭제(inf에서 `int()` 크래시) → **CAUGHT**, (4) **진짜 비어있지 않은 Kadane**(빈 옵션 없음) → 전 음수 holdout
  `[-1,-2,-3]`(정답 0.0)에서 **CAUGHT**(err=5.0), (5) best 갱신 `>`→`>=`(등가) → 예상대로 not-caught.
- **★설계 근거의 재확인**: 진짜 비어있지 않은 Kadane은 전 음수 `[-1,-2,-3]`에서 최대요소 -1.0을 반환=**fail-soft sentinel -1.0과 충돌**. 「빈 허용이므로 답 ≥ 0 →
  -1.0이 안전」이라는 설계가, 바로 이 충돌 회피로서 기능함을 mutation test가 실증(빈 허용 = sentinel 건전성의 전제).
- **holdout**: 빈/단일 양수(5)/단일 음수(0)·**전 음수→0(빈 허용을 단독 pin)**·고전 Kadane `[-2,1,-3,4,-1,2,1,-5,4]`→6·중앙 드롭으로 리셋·
  0/-0.0 부호제로·**overflow 경계를 2^52로 pin**(`[2^52]`=진행합 2^52 → **valid**(`>` vs `>=`를 단독 pin) / `[2^52,1]`=2^52+1 → -1.0 /
  `[2^51,2^51]`=2^52 → valid / 단일 `[2^52+1]` > 2^52 → -1.0)·비정수/±inf(선두/중앙)/NaN(선두/중앙/말미)를 fail-soft·random 정수.
- **C 안전**: 영역체크 `x >= -LIM && x <= LIM`이 **(long long) 캐스트 전**에 NaN/inf/거대값을 걸러냄(NaN→int는 UB). 누산은 long long, 진행합 ≤ 2^52
  이므로 전 부분합 < 2^63(오버플로우 없음), 반환 double은 best < 2^53으로 엄밀.
- **work-graph op 파도**: max_subarray를 `algo_difftest --op` 게이트 노드화(`1 op=1 노드`) → `run-once --available tool:command`로 무인 done
  (gate JSON passed=True·c_verified=true). = **전 algo op 38이 work-graph 게이트화**(37→38).
- **회귀**: `tests/test_algo.py`에 P17 군(registered_kind·기지값·전수조사 일치 random×5000·fail-soft/overflow·difftest python exact·C bit 일치).
  **honest**: 첫 전체 실행에서 `test_search_ops_registered_kinds`가 1 failed(search 카테고리 집합의 갱신을 **2곳** 중 한쪽[`test_categories_grouping`]만
  고쳤음) → 감지해 즉시 수정, 재실행으로 **test_algo.py 295 passed / 0 failed**·ruff clean·mypy 신규 0(origin/master=15와 동수).
  **적대적 리뷰는 worktree 격리로 실행**(P16에서 확립).

### P17 적대적 리뷰 후 강화(2026-08-17, [[feedback_no_solo_ai_judgment]])
**worktree 격리 리뷰(4 에이전트·3개 렌즈 + 적대적 verify) = 1 CONFIRMED(LOW·gate-honesty) / refuted 0**. 검증 에이전트는
격리 worktree에서 전부 재현하고, 본 repo의 algo.py 무오염(`status --porcelain`은 auto의 SESSION_SUMMARY뿐)을 명기. correctness/integration 계열 0(op는 올바름):
- **[LOW gate-honesty] C의 「NaN을 캐스트 전에 거부」가 gate에서 falsify 불가능**: honest gate는 C를 `-O2 -std=c99 -ffp-contract=off`(UBSan 없음)로만
  compile한다. C의 영역가드를 **De Morgan 재작성** `if (!(x>=-LIM && x<=LIM))` → `if (x<-LIM || x>LIM)`(NaN에서 양쪽 비교가 false=NaN이 빠져나감)
  로 하면, 다음 행 `x != (double)(long long)x`의 **`(long long)NaN`이 UB**가 되어, -O2에서는 우연히 -1.0 상당으로 떨어져 Python과 bit 일치 → gate가 passed=True.
  하지만 같은 변이는 **UBSan/ReleaseSafe build에서 hard-trap**(`panic: nan is outside the range of representable values of type 'long long'`)한다.
  **출하된 op는 올바르다**(가드 `!(x>=-LIM && x<=LIM)`는 캐스트 전에 NaN을 거부함) = gate-coverage의 구멍(production 버그가 아님). Python 절반은
  이미 pin됨(영역가드 제거로 `int(nan)`이 ValueError → gate는 통과시키지 않고 error) = C 측만 비대칭으로 미pin.
- **1차 검증(자체 재현)**: standalone probe를 gate와 동일 플래그 `-O2 -std=c99 -ffp-contract=off`로: 출하 guard=NaN→-1.0 정상 / De Morgan+UBSan=
  `(long long)NaN`에서 trap(finding의 panic과 일치) / 출하 guard+UBSan=trap 없음(NaN을 캐스트 전에 거름=**UBSan-clean**). **honest한 차이**: 내
  standalone은 De Morgan+-O2가 exit3으로 떨어졌지만, **실 게이트**(`algo_difftest --op`)에서는 검증 에이전트 보고대로 passed 통과를 확인 = -O2의 UB 거동은
  부정(不定)이며 어느 쪽이든 「-O2만으로는 reject-before-cast를 확실하게는 pin할 수 없다」.
- **수정(전 op를 강화)**: `run_c_backend`에 **UBSan pass** 추가 — -O2 bit 비교 후에 동일 C를 `-fsanitize=undefined -fno-sanitize-recover=all`로
  재 compile+같은 holdout 재 run. NaN/inf/영역 외 값이 정수 캐스트에 도달하면 trap → **gate fail**(UBSan 비대응 toolchain은 `"unsupported"`=neutral로 오검출하지 않음).
  **사전 실측**: 전 38개 op가 UBSan-clean(trap 0) = 오fail 없이 안전하게 채택 가능. **수정 후 실측**: 출하 op=passed=True/ubsan=ok, **De Morgan 변이=
  passed=False/ubsan=trap**(bit는 -O2에서 True인데 UBSan에서 포착). 다른 op 회귀 없음. = **「reject-before-cast」를 C에서도 load-bearing으로**(Python의
  `int(nan)` raise와 대칭). 회귀 pytest `test_ubsan_pass_catches_nan_slip_through_cast` 추가. 전 스위트 **295→296 passed / 0 failed**·ruff clean·mypy 신규 0.
- **★이것은 max_subarray 고유가 아니라 gate 기반의 강화** = 이후의 전 algo op에서 「비유한 값이 캐스트에 도달하는 UB」를 gate가 falsify 가능해짐.

## 2026-09-03: 적대적 리뷰(algo + C codegen)의 수정 8건

- **[HIGH] C의 `unsharp`(`sharpen`)가 [0,1] 클립을 결여해, 후단의 op가 Python과 괴리**(unsharp→gaussian 최대차 6.6e-2,
  unsharp→threshold(1.0)에서 512 px 반전). `sharpen` 출구에서 클램프 + `codegen.py`가 clip 대상 sort의 각 stage 후에
  `clamp01()`을 출력(이중 보험). 수정 후 ≤ 3e-7.
- `difftest.py`가 gcc/cc/clang만 찾아서 **이 환경에서는 C 게이트가 조용히 skip**되고 있었다(= 위의 괴리가 보이지 않았다).
  `algo_difftest.find_c_compiler()`(ziglang fallback)를 공용. 결과 dict에 `compiler`를 기록.
- 그래프 op의 `n`이 int32 상한까지 무제한(`graph_components([2147483000,0])`으로 17 GB 확보) → **`n ≤ 5,000,000`**(sieve와 같은
  명시적 상한), `m ≤ 2147483000`, Python/C 모두.
- 끝점을 `(int)`로 캐스트한 후 범위검사(float→int overflow UB, UBSan 트랩) → raw double로 범위·정수성을 먼저 검사.
  UBSan 트랩 3 → 0, 39/39 비트 일치.
- **센티널 값의 변경(ABI)**: 「0.0이 정당한 답이기도 한」 op의 fail-soft 센티널 값을 **0.0 → −1.0**으로 변경 —
  `is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` / `lcs_length`(P13〜P18과 같은 규약).
  예: `is_prime([4294967311])`(정의역 외)는 0.0「합성수」가 아니라 −1.0. 미변경(충돌 가능성 있음, 검토 필요):
  `pow_mod` / `gcd_seq` / `popcount_total` / `polygon_area2`.
- `run_algo`가 2^53 초과 int를 `float()`로 반올림한 후 정의역 검사를 하고 있었음 → `wire_float()`로 |x|>2^53의 정수 입력은
  `ValueError`(fail-closed).
- `box`의 짝수 k가 k+1 tap / k로 나누고 있었음(gain 1.25) → scipy `uniform_filter`와 같은 origin으로 k tap.
- `difftest`의 NaN이 `max(0.0, nan)=0.0`으로 합격하고 있었음 → 비유한은 inf로서 불합격.
- 회귀: `tests/test_imgops_c.py`(신설 11)외 35건 추가, 5개 파일 355 passed(C 테스트는 모두 ziglang으로 실행).
