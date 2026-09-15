"""外部 AI の生 transcript から最終回答だけを切り出し、run dir(qNN.md + meta.json)にする。

    py -3.11 tools/rag_eval/ingest.py --ai codex   --transcript <codex exec の stdout> --out runs/2026-09-15_codex
    py -3.11 tools/rag_eval/ingest.py --ai copilot --transcript <copilot -p の stdout> --out runs/2026-09-15_copilot
        [--ids q01,q02,q03] [--prompt <投げたプロンプト>]

``run.py`` が 1 問ずつ投げた出力にも、手で 3 問まとめて投げた transcript にも同じ切り出しを
使う(問 N の見出しで分ける)。切り出しの規則:

* **codex**: ``codex exec`` の stdout は「思考の要約 → ``exec`` ブロック → ... → ``codex``
  見出し → 最終回答 → ``tokens used`` → 回答の再掲」。再掲(折り返し無し)があればそれを、
  無ければ最後の ``codex`` 見出し以降を最終回答とする。``exec`` の本数、``rejected: blocked
  by policy`` の本数、``tokens used`` の数、ヘッダの ``model:`` を meta に数える。
* **copilot**: ``copilot -p ... -s`` の stdout は「作業の語り(1 行ずつ)→ ``---`` → 回答」。
  最初の ``##`` 見出しより前の非空行(題名と ``---`` を除く)を ``narration_steps`` として
  数える(-s では tool 呼び出しそのものは出ないので、語りの行数が近似)。

問の見出し ``### 問1`` / ``### **問1：`` を q01.md、q02.md ... に割り当て、問でない後続の
節(感想・評価)は ``feedback.md`` にまとめる。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

_Q_HEAD = re.compile(r"^#{2,4}\s*\**\s*問\s*(\d+)", re.M)
_ANY_HEAD = re.compile(r"^#{2,4}\s", re.M)


def codex_final_answer(text: str) -> tuple[str, dict]:
    """codex exec の stdout → (最終回答, 計測 meta)。"""
    meta: dict = {}
    m = re.search(r"^model:\s*(.+)$", text, re.M)
    if m:
        meta["model"] = m.group(1).strip()
    meta["exec_blocks"] = len(re.findall(r"^exec$", text, re.M))
    meta["rejected_commands"] = len(re.findall(r"rejected: blocked by policy", text))
    tok = re.search(r"^tokens used\s*\n\s*([\d,]+)", text, re.M)
    if tok:
        meta["tokens_used"] = int(tok.group(1).replace(",", ""))
        answer = text[tok.end():]
    else:
        parts = re.split(r"^codex\s*$", text, flags=re.M)
        answer = parts[-1] if len(parts) > 1 else text
    return answer.strip() + "\n", meta


def copilot_final_answer(text: str) -> tuple[str, dict]:
    """copilot -s の stdout → (回答, 計測 meta)。語りは meta に数えて本文から外す。"""
    meta: dict = {}
    first = _ANY_HEAD.search(text)
    pre = text[: first.start()] if first else ""
    body = text[first.start():] if first else text
    steps = [ln for ln in pre.splitlines()
             if ln.strip() and not ln.startswith("# ") and ln.strip() != "---"]
    meta["narration_steps"] = len(steps)
    return body.strip() + "\n", meta


def split_questions(answer: str, ids: list[str] | None = None) -> tuple[dict[str, str], str]:
    """問 N 見出しで分割 → ({qNN: 本文}, 残り=感想)。``ids`` で番号→id を差し替えられる。"""
    heads = list(_Q_HEAD.finditer(answer))
    if not heads:
        raise SystemExit("問 N の見出しが見つからない(### 問1 / ### **問1： の形が要る)")
    out: dict[str, str] = {}
    feedback_parts: list[str] = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(answer)
        chunk = answer[h.start():end]
        # 問の節の中で、問でない ## 見出し(感想など)が始まればそこで切る
        nxt = [m for m in _ANY_HEAD.finditer(chunk) if m.start() > 0 and not _Q_HEAD.match(chunk, m.start())]
        if nxt:
            feedback_parts.append(chunk[nxt[0].start():])
            chunk = chunk[: nxt[0].start()]
        n = int(h.group(1))
        qid = ids[n - 1] if ids and n - 1 < len(ids) else f"q{n:02d}"
        out[qid] = chunk.strip() + "\n"
    if heads[0].start() > 0:
        feedback_parts.insert(0, answer[: heads[0].start()])
    feedback = "\n".join(p.strip() for p in feedback_parts if p.strip())
    return out, feedback


_LOCAL_ABS = re.compile(r"(?:[A-Za-z]:[\\/]|/home/|/Users/)[\w.\-\\/ ]*?(?=(docs|examples|examples_3d|tools|skills|tests|fullseye)[\\/])")


def scrub_local_paths(text: str) -> str:
    """回答に混じったローカル絶対パスをリポジトリ相対に落とす(公開物にローカルパスを残さない)。"""
    return _LOCAL_ABS.sub("", text)


def ingest(ai: str, transcript: Path, out: Path, ids: list[str] | None = None,
           prompt: Path | None = None, date: str | None = None,
           extra: dict | None = None, kind: str = "questions") -> dict:
    raw = transcript.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    if ai == "codex":
        answer, meta = codex_final_answer(raw)
    elif ai == "copilot":
        answer, meta = copilot_final_answer(raw)
    else:
        raise SystemExit(f"unknown ai: {ai}")
    answer = scrub_local_paths(answer)
    out.mkdir(parents=True, exist_ok=True)
    if kind == "interview":
        # 聞き取り(使い道と自分の課題)は採点しない —— 人が読む用に 1 ファイルへ
        head = (f"<!-- {ai} の聞き取り(採点対象外)。transcript から最終回答だけを切り出し、"
                f"ローカル絶対パスは相対に置換。検証済み注記は docs/RAG_EVAL.md -->\n\n")
        (out / "interview.md").write_text(head + answer, encoding="utf-8")
        meta = {"interview": {**meta, "transcript_bytes": len(raw.encode("utf-8")),
                              **(extra or {})}}
        mp = out / "meta.json"
        old = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        old.update(meta)
        mp.write_text(json.dumps(old, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return old
    per_q, feedback = split_questions(answer, ids)
    for qid, body in per_q.items():
        (out / f"{qid}.md").write_text(body, encoding="utf-8")
    if feedback.strip():
        (out / "feedback.md").write_text(feedback.strip() + "\n", encoding="utf-8")
    if prompt is not None:
        (out / "prompt.txt").write_text(prompt.read_text(encoding="utf-8"), encoding="utf-8")
    meta.update({
        "ai": ai,
        "date": date or _dt.date.today().isoformat(),
        "source": "transcript imported by tools/rag_eval/ingest.py",
        "transcript_bytes": len(raw.encode("utf-8")),
        "questions": sorted(per_q),
        "mode": "batch (all questions in one prompt)",
    })
    if extra:
        meta.update(extra)
    mp = out / "meta.json"
    if mp.is_file():
        old = json.loads(mp.read_text(encoding="utf-8"))
        old.update(meta)
        meta = old
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ai", required=True, choices=["codex", "copilot"])
    ap.add_argument("--transcript", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--ids", help="問 1,2,3 に割り当てる質問 id(既定 q01,q02,...)")
    ap.add_argument("--prompt", type=Path, help="投げたプロンプト(run dir に prompt.txt として複製)")
    ap.add_argument("--date", help="meta.json の date(既定 = 今日)")
    ap.add_argument("--extra", action="append", default=[],
                    help="meta.json に足す key=value(人が transcript から読み取った値。数字は int に)")
    ap.add_argument("--kind", choices=["questions", "interview"], default="questions",
                    help="questions = 問 N で分けて qNN.md / interview = 聞き取りを interview.md に(採点しない)")
    a = ap.parse_args(argv)
    ids = a.ids.split(",") if a.ids else None
    extra: dict = {}
    for kv in a.extra:
        k, _, v = kv.partition("=")
        extra[k] = int(v) if v.lstrip("-").isdigit() else v
    meta = ingest(a.ai, a.transcript, a.out, ids, a.prompt, a.date, extra, a.kind)
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
