"""Claude Code 向け RAG セットアップ(``fullseye-rag`` console script)。

同梱スキル(fullseye-ops)をユーザーの Claude Code スキルディレクトリへコピーし、
SKILL.md の ``FULLSEYE_REPO =`` 行をコーパスの実在パスに固定する。2 モード:

- **checkout モード**(git clone / ``pip install -e .``): リポジトリの
  ``docs/ops``(per-op ノート 1000 枚)がフルコーパス。
- **wheel モード**(PyPI からの ``pip install fullseye``): インストール済み
  パッケージ内の ``OP_CATALOG.md``(AI 向け全 op カタログ)+ ``studio_assets``
  の help がコーパス。フルの per-op ノートはリポジトリ clone で得られる旨を
  スキルに明記する。

fail-closed: どちらのモードでもコーパス実体が見つからなければインストールを拒否。
ユーザーの既存環境(QSettings / 他のスキル)には触れない。

使い方::

    fullseye-rag                # インストール(再実行=更新)
    fullseye-rag --uninstall    # 削除
    fullseye-rag --target DIR   # テスト/別環境用
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent           # installed (or checkout) fullseye package
SKILL_NAME = "fullseye-ops"
_REPO_LINE = re.compile(r"^FULLSEYE_REPO = .*$", re.MULTILINE)


def find_repo() -> Path | None:
    """checkout(または editable install)ならリポジトリ root、wheel なら None。"""
    cand = PKG.parent
    if ((cand / "docs" / "ops" / "INDEX.md").is_file()
            and (cand / "skills" / SKILL_NAME / "SKILL.md").is_file()):
        return cand
    return None


def default_target() -> Path:
    return Path.home() / ".claude" / "skills"


def _skill_source(repo: Path | None) -> Path:
    if repo is not None:
        src = repo / "skills" / SKILL_NAME
        if not (src / "SKILL.md").is_file():
            raise SystemExit(f"skill source not found: {src / 'SKILL.md'} (broken checkout?)")
        return src
    tmpl = PKG / "skill_template"
    if not (tmpl / "SKILL.md").is_file():
        raise SystemExit(f"skill template not shipped: {tmpl / 'SKILL.md'} (broken install)")
    return tmpl


def _pin_line(repo: Path | None) -> str:
    if repo is not None:
        if not (repo / "docs" / "ops" / "INDEX.md").is_file():
            raise SystemExit(
                f"op corpus not found: {repo / 'docs' / 'ops' / 'INDEX.md'} — "
                "run from a full repo checkout (the corpus is repo content)")
        return "FULLSEYE_REPO = %s" % repo.as_posix()
    if not (PKG / "OP_CATALOG.md").is_file():
        raise SystemExit(
            f"catalog not found: {PKG / 'OP_CATALOG.md'} (broken install) — "
            "reinstall fullseye, or clone the repo for the full corpus")
    return ("FULLSEYE_REPO = %s  (pip install: catalog = OP_CATALOG.md here; "
            "full per-op notes = clone the GitHub repo)" % PKG.as_posix())


def _backup_existing(dest: Path) -> Path | None:
    """既存スキルをタイムスタンプ付きで退避し、退避先を返す(無ければ None)。

    再インストール(=更新)がユーザーの手編集を黙って消さないための関門。
    同一秒内の連続実行でも衝突しないよう、既存ならカウンタを足す。
    Back up an existing skill dir before overwrite so a reinstall never
    silently destroys the user's hand edits; collision-safe within a second."""
    if not dest.is_dir():
        return None
    import datetime
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = dest.with_name(f"{dest.name}.bak-{stamp}")
    n = 1
    while backup.exists():
        backup = dest.with_name(f"{dest.name}.bak-{stamp}-{n}")
        n += 1
    shutil.copytree(dest, backup)
    return backup


def install(target_dir: Path, repo: Path | None = None, _auto_repo: bool = True,
            backup: bool = True) -> Path:
    """スキルをコピーし FULLSEYE_REPO 行を固定して dest を返す(fail-closed)。

    既定で、既存インストールがあれば上書き前にバックアップを残す
    (``backup=False`` は呼び出し側が独自にバックアップ済みの場合のみ)。"""
    if repo is None and _auto_repo:
        repo = find_repo()
    src_dir = _skill_source(repo)
    pinned = _pin_line(repo)
    dest = target_dir / SKILL_NAME
    if backup:
        saved = _backup_existing(dest)
        if saved is not None:
            print("existing skill backed up to: %s" % saved)
    dest.mkdir(parents=True, exist_ok=True)
    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        if src.is_dir():
            (dest / rel).mkdir(parents=True, exist_ok=True)
            continue
        if src.name == "SKILL.md":
            text = src.read_text(encoding="utf-8")
            text, n = _REPO_LINE.subn(pinned, text, count=1)
            if n != 1:
                raise SystemExit("SKILL.md has no 'FULLSEYE_REPO =' line to pin (template drift)")
            (dest / rel).write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copy2(src, dest / rel)
    return dest


def uninstall(target_dir: Path) -> bool:
    dest = target_dir / SKILL_NAME
    if dest.is_dir():
        shutil.rmtree(dest)
        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uninstall", action="store_true", help="スキルを削除する")
    ap.add_argument("--target", type=Path, default=None,
                    help="スキルディレクトリ(既定: ~/.claude/skills)")
    args = ap.parse_args(argv)
    target = args.target if args.target is not None else default_target()
    if args.uninstall:
        removed = uninstall(target)
        print("removed: %s" % (target / SKILL_NAME) if removed
              else "not installed: %s" % (target / SKILL_NAME))
        return 0
    repo = find_repo()
    dest = install(target, repo=repo, _auto_repo=False)
    print("installed Claude Code RAG skill: %s" % dest)
    if repo is not None:
        print("corpus pinned to: %s (full per-op notes)" % (repo / "docs" / "ops"))
    else:
        print("corpus pinned to: %s (pip install — OP_CATALOG.md; "
              "clone the repo for the full per-op notes)" % PKG)
    print("next: open Claude Code anywhere and ask an image-processing question — "
          "the 'fullseye-ops' skill routes it through the corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
