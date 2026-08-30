"""Fullseye の安全アップデータ(環境をつぶさない更新)。

「更新」で壊れやすいものを列挙し、それぞれ**壊さない側**に倒す:

1. **ユーザーの未コミット変更** — 作業ツリーが dirty なら pull を**拒否**する
   (自動 stash はしない。ユーザーの作業に触れないのが最優先)。
2. **git 履歴** — ``git pull --ff-only`` のみ。fast-forward できない(=ローカルに
   独自コミットがある)場合も**拒否**して状況を報告する。履歴の書き換えはしない。
3. **Claude Code RAG スキル** — インストール済みなら更新するが、上書き前に
   **タイムスタンプ付きバックアップ**を残す(ユーザーが SKILL.md を手で編集して
   いても失われない)。未インストールなら何もしない(勝手に環境へ書き込まない)。
4. **Studio の環境設定(QSettings)** — 一切触れない。
5. **pip 環境** — 既定では触れない。``--pip`` を明示したときだけ
   ``pip install -e .`` を再実行する(依存が増えた版への追従用)。

使い方::

    py -3.11 tools/update_fullseye.py            # preflight → ff-only pull → skill 更新
    py -3.11 tools/update_fullseye.py --check    # 何が起きるかの確認だけ(変更なし)
    py -3.11 tools/update_fullseye.py --pip      # + 依存の再インストール
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup_claude_rag as rag


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True)


def preflight() -> list[str]:
    """更新して安全かの検査。問題のリスト(空=安全)を返す。"""
    problems = []
    r = _git("rev-parse", "--is-inside-work-tree")
    if r.returncode != 0:
        return [f"not a git repository: {REPO} (zip distribution: re-download to update)"]
    r = _git("status", "--porcelain")
    if r.stdout.strip():
        problems.append(
            "uncommitted changes in the working tree — the updater never touches your work.\n"
            "  commit / stash them, then re-run:\n"
            + "\n".join("    " + ln for ln in r.stdout.strip().splitlines()[:10]))
    return problems


def has_remote() -> bool:
    r = _git("remote")
    return bool(r.stdout.strip())


def pull_ff_only(check: bool) -> str:
    if not has_remote():
        return "no remote configured — pull skipped (local checkout)"
    if check:
        _git("fetch", "--quiet")
        r = _git("rev-list", "--count", "HEAD..@{u}")
        n = r.stdout.strip() or "?"
        return f"commits available: {n} (not applied because of --check)"
    r = _git("pull", "--ff-only")
    if r.returncode != 0:
        raise SystemExit(
            "git pull --ff-only was refused (diverged from local commits?).\n"
            "History is never rewritten — decide rebase/merge manually.\n" + r.stderr)
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "already up to date"


def update_rag_skill(check: bool) -> str:
    """インストール済みの RAG スキルだけ更新(未インストールなら何もしない)。
    上書き前にタイムスタンプ付きバックアップを残すので手編集も失われない。"""
    target = rag.default_target()
    dest = target / rag.SKILL_NAME
    if not dest.is_dir():
        return "RAG skill not installed — skipped (to install: tools/setup_claude_rag.py)"
    if check:
        return f"RAG skill would be updated: {dest} (backup, then reinstall)"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target / f"{rag.SKILL_NAME}.bak-{stamp}"
    n = 1
    while backup.exists():                   # 同一秒内の再実行でも衝突させない
        backup = target / f"{rag.SKILL_NAME}.bak-{stamp}-{n}"
        n += 1
    shutil.copytree(dest, backup)
    rag.install(target, backup=False)        # 退避済み — install 側の二重バックアップを抑止
    return f"RAG skill updated (previous version backed up: {backup})"


def pip_refresh(check: bool) -> str:
    if check:
        return f"would run: pip install -e {REPO}"
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(REPO)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("pip install -e . failed:\n" + r.stderr[-2000:])
    return "pip install -e . done"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="dry run: show what would happen, change nothing")
    ap.add_argument("--pip", action="store_true", help="also re-run pip install -e .")
    args = ap.parse_args(argv)

    problems = preflight()
    if problems:
        print("update aborted (environment protection):")
        for p in problems:
            print("  - " + p)
        return 2

    print("[1/3] " + pull_ff_only(args.check))
    print("[2/3] " + update_rag_skill(args.check))
    if args.pip:
        print("[3/3] " + pip_refresh(args.check))
    else:
        print("[3/3] pip skipped (re-run with --pip when dependencies changed)")
    if not args.check:
        print("recommended: py -3.11 -m pytest -q to verify the updated tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
