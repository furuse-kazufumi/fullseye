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
        return [f"git リポジトリではありません: {REPO}(zip 配布なら再ダウンロードで更新)"]
    r = _git("status", "--porcelain")
    if r.stdout.strip():
        problems.append(
            "作業ツリーに未コミットの変更があります — 更新はあなたの変更に触れません。\n"
            "  commit / stash してから再実行してください:\n"
            + "\n".join("    " + ln for ln in r.stdout.strip().splitlines()[:10]))
    return problems


def has_remote() -> bool:
    r = _git("remote")
    return bool(r.stdout.strip())


def pull_ff_only(check: bool) -> str:
    if not has_remote():
        return "remote 未設定 — pull はスキップ(ローカル checkout)"
    if check:
        _git("fetch", "--quiet")
        r = _git("rev-list", "--count", "HEAD..@{u}")
        n = r.stdout.strip() or "?"
        return f"更新可能なコミット: {n} 件(--check のため未適用)"
    r = _git("pull", "--ff-only")
    if r.returncode != 0:
        raise SystemExit(
            "git pull --ff-only が拒否されました(ローカル独自コミットと分岐?)。\n"
            "履歴は書き換えません — 手動で rebase/merge を判断してください。\n" + r.stderr)
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "already up to date"


def update_rag_skill(check: bool) -> str:
    """インストール済みの RAG スキルだけ更新(未インストールなら何もしない)。
    上書き前にタイムスタンプ付きバックアップを残すので手編集も失われない。"""
    target = rag.default_target()
    dest = target / rag.SKILL_NAME
    if not dest.is_dir():
        return "RAG スキル未インストール — スキップ(入れるなら tools/setup_claude_rag.py)"
    if check:
        return f"RAG スキルを更新予定: {dest}(バックアップの上、再インストール)"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target / f"{rag.SKILL_NAME}.bak-{stamp}"
    shutil.copytree(dest, backup)
    rag.install(target)
    return f"RAG スキル更新済み(旧版のバックアップ: {backup})"


def pip_refresh(check: bool) -> str:
    if check:
        return f"pip install -e {REPO} を実行予定"
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(REPO)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("pip install -e . が失敗しました:\n" + r.stderr[-2000:])
    return "pip install -e . 完了"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="変更せず、何が起きるかだけ表示")
    ap.add_argument("--pip", action="store_true", help="pip install -e . も再実行する")
    args = ap.parse_args(argv)

    problems = preflight()
    if problems:
        print("更新を中止しました(環境保護):")
        for p in problems:
            print("  - " + p)
        return 2

    print("[1/3] " + pull_ff_only(args.check))
    print("[2/3] " + update_rag_skill(args.check))
    if args.pip:
        print("[3/3] " + pip_refresh(args.check))
    else:
        print("[3/3] pip はスキップ(依存が変わった版では --pip を付けて再実行)")
    if not args.check:
        print("推奨: py -3.11 -m pytest -q で更新後の健全性を確認できます")
    return 0


if __name__ == "__main__":
    sys.exit(main())
