# -*- coding: utf-8 -*-
"""tools/rag_eval(他の AI に同じ質問集を投げて機械採点する仕組み)の門。

守るもの:

1. 質問集は 30 問・15 分野 × 2 問で、正解側の op 名は**全部実在**する
   (``fs.find_op`` → 台帳 → ノートの順で引く。2-D レジストリだけ見て「無い」と
   言わない —— 台帳の op を見落とした前科がある)。期待根拠のパスも実在する。
2. 鍵語(MCP の tool 名・診断の語)は、その問の期待根拠ファイルに実際に書いてある。
3. 採点器は 2026-09-15 の 2 本(Codex / Copilot)を**同じ数字**で再現する。
4. 門は壊して確かめる: 実在しない op を作った偽回答は減点され、存在しないパスを
   挙げた偽回答も減点され、引数名(文書語彙)は減点されない。
5. 実行器の dry-run は書き込まずコマンド列だけ出す。取り込みは問 N で正しく割る。
6. 公開物(runs/*.md)にローカル絶対パスが残っていない。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "rag_eval"
sys.path.insert(0, str(TOOLS))

import common  # noqa: E402
import ingest  # noqa: E402
import run as runner  # noqa: E402
import score  # noqa: E402

RUNS = TOOLS / "runs"
QUESTIONS = common.load_questions()


# --------------------------------------------------------------------------- #
# 1. 質問集                                                                    #
# --------------------------------------------------------------------------- #
def test_thirty_questions_two_per_domain():
    assert len(QUESTIONS) == 30
    ids = [q["id"] for q in QUESTIONS]
    assert ids == [f"q{i:02d}" for i in range(1, 31)]
    domains: dict[str, int] = {}
    for q in QUESTIONS:
        domains[q["domain"]] = domains.get(q["domain"], 0) + 1
    assert len(domains) == 15, sorted(domains)
    assert all(n == 2 for n in domains.values()), domains
    for q in QUESTIONS:
        assert q["question"].strip() and q["human_check"], q["id"]
        assert q["required_ops"] or q["required_terms"], q["id"]


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_every_answer_key_op_exists(q):
    """正解側の op 名は全部実在する(門)。作った名前で採点しない。"""
    names = [n for g in q["required_ops"] for n in g] + list(q.get("optional_ops", []))
    missing = [n for n in names if not common.op_exists(n)]
    assert not missing, f"{q['id']}: 実在しない op を正解に書いている {missing}"
    for g in q["required_ops"]:
        assert g, f"{q['id']}: 空の群"


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_expected_evidence_exists(q):
    assert q["expected_evidence"], q["id"]
    missing = [p for p in q["expected_evidence"] if not common.path_exists(p)]
    assert not missing, f"{q['id']}: 期待根拠が無い {missing}"


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q.get("required_terms")], ids=lambda q: q["id"])
def test_required_terms_are_written_in_the_evidence(q):
    """鍵語は期待根拠ファイルのどれかに実際に書いてある(空想の語で採点しない)。"""
    corpus = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in q["expected_evidence"])
    for group in q["required_terms"]:
        assert any(t in corpus for t in group), f"{q['id']}: 群 {group} のどれも根拠に無い"


def test_op_existence_looks_past_the_2d_registry():
    """``fs.find_op`` は 2-D レジストリしか見ない。台帳の op も実在と数えること。"""
    import fullseye as fs

    assert fs.find_op("polarization_separate") is None       # 2-D レジストリには無い
    assert common.op_exists("polarization_separate")          # 台帳にはある
    assert common.op_exists("lines_gauss")                    # 2-D
    assert common.op_exists("add_image")                      # n 項 op(ノート層)
    assert common.resolve_op("fit_circle_contour_xld") == "hx_fit_circle_contour"  # HALCON 別名
    assert not common.op_exists("polarization_remove_specular")
    assert len(common.op_universe()) >= 1900


# --------------------------------------------------------------------------- #
# 2. 採点の再現(2026-09-15 の 2 本)                                             #
# --------------------------------------------------------------------------- #
def _score_run(name: str) -> list[dict]:
    by_id = {q["id"]: q for q in QUESTIONS}
    out = []
    for md in sorted((RUNS / name).glob("q[0-9][0-9].md")):
        out.append(score.score_answer(md.read_text(encoding="utf-8"), by_id[md.stem]))
    return out


def test_codex_2026_09_15_scores_reproduce():
    r = _score_run("2026-09-15_codex")
    assert [x["score"] for x in r] == [75.0, 100.0, 100.0]
    q01 = r[0]
    assert q01["groups_satisfied"] == 1 and q01["groups_total"] == 2   # measure_pairs を見落とした
    assert "lines_gauss" in q01["cited_ops"] and "measure_pairs" not in q01["cited_ops"]
    assert all(not x["unknown_identifiers"] for x in r)                # op は作っていない
    assert all(x["path_exist_rate"] == 1.0 for x in r)


def test_copilot_2026_09_15_scores_reproduce():
    r = _score_run("2026-09-15_copilot")
    assert [x["score"] for x in r] == [93.3, 100.0, 93.3]
    q01 = r[0]
    assert q01["groups_satisfied"] == 2 and "measure_pairs" in q01["cited_ops"]
    # 減点の理由は根拠パス: examples/ を docs/examples/ と書いた(実在しない)
    assert q01["paths_missing"] == ["docs/examples/poc_real_defect_floor.py"]
    assert all(not x["unknown_identifiers"] for x in r)


def test_committed_score_json_matches_recomputation():
    """コミット済みの score.json は再計算と一致する(古い表を配らない)。"""
    for name in ("2026-09-15_codex", "2026-09-15_copilot"):
        saved = json.loads((RUNS / name / "score.json").read_text(encoding="utf-8"))
        fresh = _score_run(name)
        assert [q["score"] for q in saved["questions"]] == [q["score"] for q in fresh], name
        assert saved["mean_score"] == round(sum(q["score"] for q in fresh) / len(fresh), 1)


def test_today_runs_have_meta_and_interview():
    codex = json.loads((RUNS / "2026-09-15_codex" / "meta.json").read_text(encoding="utf-8"))
    assert codex["tokens_used"] == 90819 and codex["files_opened_self_reported"] == 20
    assert codex["exec_blocks"] == 27 and codex["interview"]["rejected_commands"] == 18
    copilot = json.loads((RUNS / "2026-09-15_copilot" / "meta.json").read_text(encoding="utf-8"))
    assert copilot["narration_steps"] == 21
    for name in ("2026-09-15_codex", "2026-09-15_copilot"):
        assert (RUNS / name / "interview.md").stat().st_size > 1000


# --------------------------------------------------------------------------- #
# 3. 門を壊して確かめる                                                          #
# --------------------------------------------------------------------------- #
Q02 = next(q for q in QUESTIONS if q["id"] == "q02")
GENUINE = ("`polarization_separate` を使う(`max_violation_frac` は既定 0)。"
           "根拠: docs/ops/specular/polarization/polarization_separate.md")


def test_phantom_op_is_penalized_but_documented_kwargs_are_not():
    good = score.score_answer(GENUINE, Q02)
    assert good["score"] == 100.0
    assert good["documented_non_ops"] == ["max_violation_frac"]   # 引数名は減点しない
    fake = GENUINE + " さらに `polarization_remove_specular` と `dolp_threshold_mask` で仕上げる。"
    bad = score.score_answer(fake, Q02)
    assert bad["unknown_identifiers"] == ["polarization_remove_specular", "dolp_threshold_mask"]
    assert bad["score"] == pytest.approx(100.0 - 20.0 * (2 / 3), abs=0.05)
    worst = score.score_answer(fake + " `a_b_c` も。", Q02)
    assert worst["score"] == 80.0                                  # 3 本で「作らない」配点ゼロ


def test_missing_required_op_and_missing_path_are_penalized():
    no_op = score.score_answer("`polarization_dolp_map` だけ。根拠: docs/MCP.md", Q02)
    assert no_op["groups_satisfied"] == 0 and no_op["score"] == 40.0   # 0 + 20 + 0 + 20
    bad_path = score.score_answer(GENUINE + " と docs/ops/specular/polarization/no_such_note.md", Q02)
    assert bad_path["path_exist_rate"] == 0.5 and bad_path["score"] == 90.0


def test_identifier_extraction_handles_call_forms():
    txt = ('`fs.ledger.polarization_separate(images, angles_deg=(0,45,90,135))` と '
           '`fullseye.apply(img, "lines_gauss", a=0.5, b=0.5)`、`opsmeasure1d.get("measure_pairs")`、'
           '`params["radius"]`、`n=40`')
    ids = common.extract_identifiers(txt)
    assert {"polarization_separate", "lines_gauss", "measure_pairs"} <= set(ids)
    assert "radius" not in ids and "40" not in ids


# --------------------------------------------------------------------------- #
# 4. 実行器・取り込み                                                            #
# --------------------------------------------------------------------------- #
def test_runner_dry_run_prints_commands_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "run"
    rc = runner.main(["--ai", "codex", "--ids", "q01,q02", "--dry-run", "--out", str(out)])
    assert rc == 0 and not out.exists()
    text = capsys.readouterr().out
    assert "[q01]" in text and "[q02]" in text and "read-only" in text and "stdin=DEVNULL" in text
    rc = runner.main(["--ai", "copilot", "--batch", "10", "--dry-run", "--out", str(out)])
    assert rc == 0 and "--allow-tool read" in capsys.readouterr().out and not out.exists()


def test_runner_rejects_unknown_ids():
    with pytest.raises(SystemExit):
        runner.main(["--ai", "codex", "--ids", "q99", "--dry-run"])


def test_prompt_numbers_questions_in_batch_order():
    batch = [q for q in QUESTIONS if q["id"] in ("q05", "q06")]
    p = runner.build_prompt(batch)
    assert "問 1: " + batch[0]["question"] in p and "問 2: " + batch[1]["question"] in p
    assert "推測で op 名を作らない" in p and "UTF-8" in p


def test_ingest_splits_codex_transcript(tmp_path):
    transcript = (
        "OpenAI Codex v0\nmodel: test-model\n--------\nuser\n問い\n\ncodex\n読みます\nexec\n"
        "powershell Get-Content x\n succeeded in 1ms:\n...\nexec\n`bad` rejected: blocked by policy\n"
        "codex\n### 問1\n`lines_gauss` を使う。\n### 問2\n`polarization_separate`。\n\n### 感想\nよい\n"
        "tokens used\n1,234\n### 問1\n`lines_gauss` を使う。\n### 問2\n`polarization_separate`。\n\n### 感想\nよい\n"
    ).replace("\n", "\r\n")
    src = tmp_path / "t.md"
    src.write_bytes(transcript.encode("utf-8"))
    out = tmp_path / "run"
    meta = ingest.ingest("codex", src, out, ids=["q05", "q06"], date="2026-01-01")
    assert meta["model"] == "test-model" and meta["tokens_used"] == 1234
    assert meta["exec_blocks"] == 2 and meta["rejected_commands"] == 1
    assert (out / "q05.md").read_text(encoding="utf-8").startswith("### 問1")
    assert "polarization_separate" in (out / "q06.md").read_text(encoding="utf-8")
    assert "感想" in (out / "feedback.md").read_text(encoding="utf-8")
    assert sorted(meta["questions"]) == ["q05", "q06"]


def test_ingest_scrubs_local_absolute_paths():
    s = ingest.scrub_local_paths("見た: [x](C:/dev/projects/imgevolve/docs/OP_CATALOG.md) と /home/u/repo/docs/MCP.md")
    assert "C:/" not in s and "/home/" not in s
    assert "docs/OP_CATALOG.md" in s and "docs/MCP.md" in s


def test_published_runs_carry_no_local_paths():
    bad = []
    for p in RUNS.rglob("*"):
        if p.suffix in (".md", ".json", ".txt") and p.is_file():
            if re.search(r"[A-Za-z]:[\\/]Users|[A-Za-z]:[\\/]dev[\\/]|/home/|/Users/", p.read_text(encoding="utf-8")):
                bad.append(p.relative_to(ROOT).as_posix())
    assert not bad, bad
