<!-- i18n-source-sha: 8fe28ab585e4 -->
# Fullseye를 AI 어시스턴트의 RAG로 사용하는 방법(Claude Code용)

[日本語](./AI_RAG_GUIDE.md) · [English](./AI_RAG_GUIDE.en.md) · [简体中文](./AI_RAG_GUIDE.zh.md) · [繁體中文](./AI_RAG_GUIDE.tw.md) · **한국어** · [Deutsch](./AI_RAG_GUIDE.de.md)

Fullseye의 권장 운용 방식은 "**AI 코딩 어시스턴트의 지식 베이스(RAG)로 사용**"하는 것입니다. 모든 op가 기계가 읽을 수 있는 Markdown 노트(`docs/ops`, 단일 진실 원천)를 가지고 있으므로, 추가적인 벡터 DB나 임베딩 서비스는 **필요하지 않습니다**. grep이 가능한 환경이라면 그 자체가 곧 RAG가 됩니다.

3단계의 도입 방법을 제공합니다. **Tier 0/1은 외부 의존성이 전혀 없습니다**(Fullseye 저장소만으로 완결됩니다).

> **PyPI를 통한 사용**: `pip install fullseye`를 실행한 환경에서는 콘솔 스크립트 **`fullseye-rag`**를 사용할 수 있습니다. checkout(clone / `pip install -e .`)인 경우 `docs/ops`의 전체 코퍼스를 스킬에 고정하고, wheel만 설치한 경우에는 동봉된 `OP_CATALOG.md`(AI를 위한 전체 op 카탈로그)를 스킬에 고정합니다(완전한 개별 op 노트가 필요해지면 저장소를 clone하여 다시 실행하면 됩니다). 업데이트는 `py -3.11 tools/update_fullseye.py`로 수행합니다(dirty 트리 거부 · `--ff-only` · 스킬은 백업 후 업데이트 · Studio 설정은 건드리지 않음 — 환경을 망가뜨리지 않도록 설계됨).

---

## Tier 0: 저장소를 여는 것만으로(단계 없음)

Fullseye 저장소의 checkout을 Claude Code에서 열면 `docs/ops/INDEX.md`와 개별 op 노트를 그대로 검색·참조할 수 있습니다. 코퍼스는 저장소 콘텐츠이므로(wheel에는 포함되지 않음), pip 설치만 한 경우에는 저장소도 함께 clone하십시오.

```
docs/ops/2d/<category>/<op>.md   # 호출 형식·타입 계약·HALCON 별칭·참고 문헌·관련 op
docs/ops/3d/<category>/<op>.md
docs/ops/INDEX.md                # 폴더 계층을 순회하여 자동 생성한 전체 목차
docs/ops/2d/guides/<family>.md   # 13개 계열의 사용 가이드(수식·그림·정전 인용)
docs/OP_INDEX.json               # 레지스트리의 기계 판독 가능한 인덱스
```

## Tier 1: 스킬로 상주시키기(권장 · 동봉 설치 스크립트)

자신의 프로젝트에서 작업하면서 Fullseye를 참조하고 싶다면, 동봉된 설치 스크립트를 한 번 실행합니다.

```bash
py -3.11 tools/setup_claude_rag.py              # 설치(재실행 = 업데이트)
py -3.11 tools/setup_claude_rag.py --uninstall  # 제거
```

동봉된 스킬 `skills/fullseye-ops`가 `~/.claude/skills/fullseye-ops`로 복사되고, SKILL.md의 `FULLSEYE_REPO =` 줄이 **이 checkout의 절대 경로로 자동 고정**됩니다(AI가 어느 프로젝트에서 작업하든 코퍼스 위치를 알 수 있게 됩니다). 코퍼스(`docs/ops`)를 찾을 수 없는 checkout에서는 설치를 거부합니다(fail-closed).

이후로는 이미지 처리·기하 비전 주제에서 Claude Code가 자동으로 이 스킬을 실행하여, `docs/ops`를 검색(retrieve) → 타입(sort)이 이어지는 op를 선택해 구현 → 동봉된 worked example로 검증, 이라는 흐름으로 동작합니다. 스킬 본문 자체가 "AI를 위한 사용 지침서"입니다. 수동으로 설치하고 싶다면 `skills/fullseye-ops`를 `~/.claude/skills/`로 복사하는 것만으로도 동작합니다(경로 고정이 없는 만큼 AI가 매번 저장소 위치를 탐색합니다).

## Tier 2(선택): 클러스터링된 코퍼스 — 외부 도구를 이용한 발전형

**2,195개**의 노트를 주제 클러스터로 계층화하고, 각 클러스터에 LLM 요약을 붙인 "내비게이션이 있는 코퍼스"도 만들 수 있습니다. 내부적으로는 [RAPTOR](https://github.com/gadievron/raptor) 포크의 `corpus2skill`(TF-IDF + k-means + LLM 요약)을 사용하고 있지만, **이는 어디까지나 선택적인 최적화이며 필수가 아닙니다**. 요구 사항은 "`docs/ops`를 입력으로 클러스터별 SKILL.md 계층을 출력"하는 것뿐이므로, 동등한 도구라면 무엇으로든 대체할 수 있습니다.

재수집(노트 업데이트 후)의 예 — 내부 운용을 그대로 정직하게 기록한 것입니다.

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # ANTHROPIC_API_KEY 필요
```

주의: 클러스터링된 코퍼스는 **수집 시점의 스냅샷**입니다. `docs/ops`를 업데이트한 후 재수집하지 않으면 낡아집니다(Tier 0/1은 항상 원본 노트를 읽으므로 낡아지지 않습니다).

---

## Tier 3(동봉): 문헌층 — 제조 기술 지식을 「어떤 op를 쓸지」로 내리기

op 노트는 「이 op가 무엇을 하는가」에는 답하지만 「이 공정·이 부품에서 무엇을 측정해야 하는가」에는 답하지 않습니다.
[`docs/literature/`](literature/INDEX.md)가 그 틈을 메웁니다: 외부 문헌 코퍼스(기계 설계·메카트로닉스 부품·제조 공정, 약 7,000건의
OpenAlex 메타데이터)를 클러스터별로 요약하고, **각 클러스터에서 쓸 op**(사람이 쓴 주제 → op 대응표, op 이름은 생성 시 출하 노트와
대조해 실재를 보증)와 대표 논문의 제목·연도·DOI를 출처로 붙였습니다. 읽는 순서는 「공정·부품의 화제 → 문헌 클러스터 → 쓸 op →
op 노트(타입 계약·실행 가능한 예)→ 구현」. 초록은 옮기지 않고, 단어 일치로 op를 고르지도 않습니다(일반어로 무관한 op가 나열되는
것을 실측하고 버렸습니다). 코퍼스 본체는 저장소에 없으므로 이 층만 `tools/gen_literature_notes.py --rad-root <RAD>`로 다시 만들며,
`tests/test_literature_notes.py`가 형태를 지킵니다.

---

## 이 방식이 동작하는 이유(설계상의 근거)

1. **md = 단일 진실 원천**: 노트는 레지스트리로부터 결정론적으로 자동 생성되며, CI의 drift 테스트가 "커밋된 노트 == 현재 코드로부터 생성한 노트"임을 강제합니다. **AI가 읽는 문서와 실제 코드는 항상 같은 버전**입니다(frontmatter의 `version` + fingerprint).
2. **타입(sort) 계약**: 각 노트는 `in:`/`out:`과 "타입이 이어지는 관련 op"를 가지고 있어, AI가 **타입을 검사하면서** 파이프라인을 구성할 수 있습니다.
3. **검증 가능**: 모든 op에는 ground truth가 포함된 worked example(`examples/` / `examples_3d/`)이 있어, AI가 스스로 자신의 제안을 실행해 확인할 수 있습니다.
4. **표시까지 일관되게 이어짐**: Studio(`py -3.11 studio.py`)를 열면, AI가 구성한 결과를 이미지 창·3D 표시로 사람이 같은 화면에서 검사할 수 있습니다(`dev_open_window` 등을 통해 스크립트에서 여러 창을 배치할 수도 있습니다).
