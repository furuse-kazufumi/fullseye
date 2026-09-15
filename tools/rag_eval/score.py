"""回答 Markdown を機械採点する —— LLM は使わない。

    py -3.11 tools/rag_eval/score.py tools/rag_eval/runs/2026-09-15_codex [他の run dir ...]
        [--questions tools/rag_eval/questions.json] [--compare 表.md]

run dir の ``qNN.md`` を質問集と突き合わせ、``score.json`` と ``score.md`` を同 dir に
書く。複数 dir を渡すと ``--compare`` で AI 横並びの表(問ごと)も出す。

## 採点の定義(0〜100、全部機械的に測れるものだけ)

| 項目 | 配点 | 何を測るか |
|---|---|---|
| op 網羅 | 50 | 質問の「必須 op 群」(各群は代替の集合)のうち、回答が**実在する** op 名で満たした群の割合。``required_terms``(MCP の tool 名や診断の鍵語)も同じ群として数える |
| 根拠の実在 | 20 | 回答が挙げたリポジトリ相対パスのうち実在する割合(挙げていなければ 0) |
| 期待根拠 | 10 | 質問側が想定するノート/ガイドのどれかを挙げていれば加点 |
| 実在しない op を作らない | 20 | op でも文書語彙でもない snake_case をバッククォートで書いた数 ``u`` に対し ``20·max(0, 1−u/3)`` |

「迷った点」「金属で信頼できないと言えたか」のような**感想・限界の指摘は採点しない**。
``human_check`` に検証済みの事実を置いてあるので、人が読んで判断する
(memory ``feedback_external_ai_verify``: 外部 AI の finding は一次情報で一件ずつ検証)。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

W_COVERAGE, W_PATHS, W_EXPECTED, W_PHANTOM = 50.0, 20.0, 10.0, 20.0
PHANTOM_FREE_ALLOWANCE = 3  # 3 本作ったら「作らない」配点はゼロ


def score_answer(text: str, q: dict) -> dict:
    """1 問ぶんの採点。返り値はそのまま JSON に落とせる dict。"""
    vocab = common.vocabulary()
    idents = common.extract_identifiers(text)

    cited: list[str] = []          # 実在 op(正規名)
    aliases: dict[str, str] = {}   # 別名で書かれたもの → 正規名
    documented: list[str] = []     # op ではないが文書語彙(引数名・鍵など)
    unknown: list[str] = []        # op でも語彙でもない snake_case = 作った疑い
    for tok in idents:
        canon = common.resolve_op(tok)
        if canon is not None:
            if canon not in cited:
                cited.append(canon)
            if canon != tok:
                aliases[tok] = canon
        elif tok in vocab:
            documented.append(tok)
        elif "_" in tok:
            unknown.append(tok)
        # 下線無しの未知語(`images`, `table` など普通の単語)は数えない

    cited_set = set(cited)
    groups = [list(g) for g in q.get("required_ops", [])]
    op_hits = [sorted(cited_set & set(g)) for g in groups]
    term_groups = [list(g) for g in q.get("required_terms", [])]
    term_hits = [[t for t in g if t in text] for g in term_groups]
    n_groups = len(groups) + len(term_groups)
    n_sat = sum(1 for h in op_hits if h) + sum(1 for h in term_hits if h)
    coverage = (n_sat / n_groups) if n_groups else 1.0

    paths = common.extract_paths(text)
    existing = [p for p in paths if common.path_exists(p)]
    path_rate = (len(existing) / len(paths)) if paths else 0.0
    expected = [p for p in q.get("expected_evidence", [])]
    expected_hit = sorted(set(expected) & set(paths))

    phantom_term = max(0.0, 1.0 - len(unknown) / PHANTOM_FREE_ALLOWANCE)
    score = (W_COVERAGE * coverage + W_PATHS * path_rate
             + W_EXPECTED * (1.0 if expected_hit else 0.0) + W_PHANTOM * phantom_term)
    optional_hits = sorted(cited_set & set(q.get("optional_ops", [])))
    return {
        "id": q["id"],
        "domain": q["domain"],
        "score": round(score, 1),
        "coverage": round(coverage, 3),
        "groups_satisfied": n_sat,
        "groups_total": n_groups,
        "required_hits": op_hits,
        "term_hits": term_hits,
        "optional_hits": optional_hits,
        "cited_ops": cited,
        "aliases_resolved": aliases,
        "documented_non_ops": documented,
        "unknown_identifiers": unknown,
        "paths_cited": paths,
        "paths_missing": [p for p in paths if p not in existing],
        "path_exist_rate": round(path_rate, 3),
        "expected_evidence_hit": expected_hit,
    }


def score_run(run_dir: Path, questions: list[dict]) -> dict:
    """run dir の全 ``qNN.md`` を採点し、``score.json`` / ``score.md`` を書いて返す。"""
    by_id = {q["id"]: q for q in questions}
    results = []
    for md in sorted(run_dir.glob("q[0-9][0-9].md")):
        qid = md.stem
        if qid not in by_id:
            raise SystemExit(f"{md}: 質問集に {qid} が無い")
        results.append(score_answer(md.read_text(encoding="utf-8"), by_id[qid]))
    if not results:
        raise SystemExit(f"{run_dir}: qNN.md が無い")
    meta = {}
    mp = run_dir / "meta.json"
    if mp.is_file():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    summary = {
        "run": run_dir.name,
        "ai": meta.get("ai", run_dir.name.split("_", 1)[-1]),
        "n_questions": len(results),
        "mean_score": round(sum(r["score"] for r in results) / len(results), 1),
        "unknown_identifiers_total": sum(len(r["unknown_identifiers"]) for r in results),
        "questions": results,
    }
    (run_dir / "score.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (run_dir / "score.md").write_text(render_run_table(summary), encoding="utf-8")
    return summary


def render_run_table(summary: dict) -> str:
    lines = [f"# {summary['run']} — 採点表(機械採点、平均 {summary['mean_score']})", "",
             "| 問 | 分野 | 点 | 必須群 | 根拠実在 | 期待根拠 | 実在 op | 作った疑い |",
             "|---|---|---:|---:|---:|:-:|---|---|"]
    for r in summary["questions"]:
        lines.append(
            f"| {r['id']} | {r['domain']} | {r['score']} | {r['groups_satisfied']}/{r['groups_total']} "
            f"| {r['path_exist_rate']} | {'✓' if r['expected_evidence_hit'] else '-'} "
            f"| {', '.join(r['cited_ops']) or '-'} | {', '.join(r['unknown_identifiers']) or '-'} |")
    lines.append("")
    lines.append("点 = 50·必須群の充足率 + 20·根拠パスの実在率 + 10·期待根拠 + 20·(1 − 作った疑い/3)。"
                 "感想・限界の指摘は採点外(人が読む)。")
    return "\n".join(lines) + "\n"


def render_compare(summaries: list[dict]) -> str:
    ids = sorted({r["id"] for s in summaries for r in s["questions"]})
    names = [s["ai"] for s in summaries]
    lines = ["| 問 | 分野 | " + " | ".join(names) + " |",
             "|---|---|" + "|".join("---:" for _ in names) + "|"]
    dom = {r["id"]: r["domain"] for s in summaries for r in s["questions"]}
    for qid in ids:
        cells = []
        for s in summaries:
            r = next((x for x in s["questions"] if x["id"] == qid), None)
            cells.append(f"{r['score']}" if r else "-")
        lines.append(f"| {qid} | {dom[qid]} | " + " | ".join(cells) + " |")
    lines.append("| **平均** | | " + " | ".join(f"**{s['mean_score']}**" for s in summaries) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dirs", nargs="+", type=Path)
    ap.add_argument("--questions", type=Path, default=common.QUESTIONS_PATH)
    ap.add_argument("--compare", type=Path, help="AI 横並びの表をこのファイルにも書く")
    a = ap.parse_args(argv)
    questions = common.load_questions(a.questions)
    summaries = [score_run(d, questions) for d in a.run_dirs]
    for s in summaries:
        print(render_run_table(s))
    if len(summaries) > 1 or a.compare:
        table = render_compare(summaries)
        print(table)
        if a.compare:
            a.compare.write_text(table, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
