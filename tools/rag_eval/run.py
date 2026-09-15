"""質問集を外部 AI(Codex CLI / Copilot CLI)に投げ、生の出力を run dir に保存する実行器。

    py -3.11 tools/rag_eval/run.py --ai codex   --dry-run              # コマンド列を印字するだけ
    py -3.11 tools/rag_eval/run.py --ai copilot --ids q01,q02 --dry-run
    py -3.11 tools/rag_eval/run.py --ai codex --batch 3 --timeout 900   # 実行(3 問ずつ束ねる)

出力: ``tools/rag_eval/runs/<date>_<ai>/``
    qNN.md        最終回答(問ごと。``ingest.py`` と同じ切り出し)
    qNN.raw.txt   stdout そのまま(transcript)/ qNN.err.txt  stderr
    prompt_qNN.txt 投げたプロンプト
    meta.json     コマンド・所要秒・returncode・timeout・tokens(codex)・失敗の記録

**読み取り専用**で走らせる(Codex ``-s read-only`` / Copilot ``--allow-tool read`` +
``--no-ask-user``)。cwd はリポジトリ root。stdin は閉じる(Codex は stdin を待つ)。
外部 AI の finding は一次情報で検証してから採用する(``score.py`` が機械的に測れる分だけ測る)。

各 AI の**登録・ログインの手順は書かない**(それぞれの CLI の手順に従う)。CLI が無ければ
``--dry-run`` 以外は exit 127。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import ingest  # noqa: E402

TEMPLATE = HERE / "prompt_template.txt"


def build_prompt(batch: list[dict]) -> str:
    """質問の束 → プロンプト。見出し番号は 1 から振り(束の中の順)、id との対応は meta に残す。"""
    lines = [f"問 {i}: {q['question']}" for i, q in enumerate(batch, 1)]
    return TEMPLATE.read_text(encoding="utf-8").replace("{questions}", "\n".join(lines))


def build_command(ai: str, prompt: str, repo: Path, model: str | None) -> list[str]:
    """list 形式の argv(shell に文字列を渡さない —— プロンプトに引用符があっても安全)。"""
    if ai == "codex":
        exe = shutil.which("codex") or "codex"
        cmd = [exe, "exec", "-s", "read-only", "-C", str(repo)]
        if model:
            cmd += ["-m", model]
        cmd.append(prompt)
        return cmd
    if ai == "copilot":
        exe = shutil.which("copilot") or "copilot"
        cmd = [exe, "--add-dir", str(repo), "--allow-tool", "read", "-s", "--no-ask-user"]
        if model:
            cmd += ["--model", model]
        cmd += ["-p", prompt]
        return cmd
    raise SystemExit(f"unknown ai: {ai}")


def run_one(cmd: list[str], repo: Path, timeout: float) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    t0 = time.time()
    rec: dict = {"command": cmd, "timeout_s": timeout}
    try:
        p = subprocess.run(cmd, cwd=str(repo), stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=timeout, env=env)
        rec.update(returncode=p.returncode, stdout=p.stdout.decode("utf-8", "replace"),
                   stderr=p.stderr.decode("utf-8", "replace"),
                   status="ok" if p.returncode == 0 else "error")
    except subprocess.TimeoutExpired as e:
        rec.update(returncode=None, status="timeout",
                   stdout=(e.stdout or b"").decode("utf-8", "replace"),
                   stderr=(e.stderr or b"").decode("utf-8", "replace"))
    except FileNotFoundError as e:
        rec.update(returncode=127, status="cli-not-found", stdout="", stderr=str(e))
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ai", required=True, choices=["codex", "copilot"])
    ap.add_argument("--questions", type=Path, default=common.QUESTIONS_PATH)
    ap.add_argument("--ids", help="投げる質問 id(カンマ区切り。既定 = 全 30 問)")
    ap.add_argument("--batch", type=int, default=1, help="1 回の呼び出しに束ねる問数(既定 1)")
    ap.add_argument("--timeout", type=float, default=900.0, help="1 回の呼び出しの上限秒(既定 900)")
    ap.add_argument("--model", help="CLI に渡すモデル名(codex -m / copilot --model)。省略 = CLI 既定")
    ap.add_argument("--repo", type=Path, default=common.REPO, help="cwd にするリポジトリ(既定 = この checkout)")
    ap.add_argument("--out", type=Path, help="run dir(既定 tools/rag_eval/runs/<date>_<ai>)")
    ap.add_argument("--dry-run", action="store_true", help="コマンド列を印字するだけで実行しない")
    a = ap.parse_args(argv)

    questions = common.load_questions(a.questions)
    if a.ids:
        want = a.ids.split(",")
        questions = [q for q in questions if q["id"] in want]
        missing = set(want) - {q["id"] for q in questions}
        if missing:
            raise SystemExit(f"質問集に無い id: {sorted(missing)}")
    if not questions:
        raise SystemExit("投げる質問が無い")
    date = _dt.date.today().isoformat()
    out = a.out or (HERE / "runs" / f"{date}_{a.ai}")
    batches = [questions[i:i + a.batch] for i in range(0, len(questions), a.batch)]

    if a.dry_run:
        for batch in batches:
            cmd = build_command(a.ai, build_prompt(batch), a.repo, a.model)
            ids = ",".join(q["id"] for q in batch)
            shown = [c if len(c) < 80 else c[:60] + f"...<{len(c)} chars>" for c in cmd]
            print(f"[{ids}] cwd={a.repo}  timeout={a.timeout:.0f}s  stdin=DEVNULL")
            print("  " + " ".join(shlex.quote(c) for c in shown))
        print(f"(dry-run) {len(batches)} 回の呼び出し → {out}(書き込み無し)")
        return 0

    if shutil.which(a.ai) is None:
        print(f"ERROR: '{a.ai}' CLI が PATH に無い(--dry-run ならコマンド列だけ出せる)", file=sys.stderr)
        return 127
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    meta.update(ai=a.ai, date=date, model=a.model, mode=f"batch={a.batch}", repo=a.repo.name,
                source="tools/rag_eval/run.py", questions=meta.get("questions", []),
                calls=meta.get("calls", []))
    for batch in batches:
        ids = [q["id"] for q in batch]
        prompt = build_prompt(batch)
        tag = ids[0] if len(ids) == 1 else f"{ids[0]}-{ids[-1]}"
        (out / f"prompt_{tag}.txt").write_text(prompt, encoding="utf-8")
        cmd = build_command(a.ai, prompt, a.repo, a.model)
        rec = run_one(cmd, a.repo, a.timeout)
        (out / f"{tag}.raw.txt").write_text(rec.pop("stdout"), encoding="utf-8")
        (out / f"{tag}.err.txt").write_text(rec.pop("stderr"), encoding="utf-8")
        rec["command"] = [c if c is not prompt else f"<prompt {len(prompt)} chars>" for c in cmd]
        rec["ids"] = ids
        extracted: list[str] = []
        if rec["status"] == "ok":
            raw = (out / f"{tag}.raw.txt").read_text(encoding="utf-8")
            try:
                answer, m2 = (ingest.codex_final_answer(raw) if a.ai == "codex"
                              else ingest.copilot_final_answer(raw))
                rec.update(m2)
                per_q, feedback = ingest.split_questions(answer, ids)
                for qid, body in per_q.items():
                    (out / f"{qid}.md").write_text(body, encoding="utf-8")
                    extracted.append(qid)
                if feedback.strip():
                    (out / f"{tag}.extra.md").write_text(feedback + "\n", encoding="utf-8")
            except SystemExit as e:  # 見出しが無い → raw は残し、失敗として記録
                rec["status"] = "unparsed"
                rec["error"] = str(e)
        rec["extracted"] = extracted
        meta["calls"].append(rec)
        meta["questions"] = sorted(set(meta["questions"]) | set(extracted))
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"[{tag}] {rec['status']} {rec['seconds']}s → {extracted or '(no answer)'}")
    print(f"done → {out}  (次: py -3.11 tools/rag_eval/score.py {out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
