"""tools/setup_claude_rag.py(Claude Code RAG インストーラー)のテスト。

インストールで SKILL.md の ``FULLSEYE_REPO =`` 行が checkout の絶対パスに固定され、
--uninstall で消えること。fail-closed(テンプレ行の drift 検出)も検証する。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import setup_claude_rag as rag


def test_install_pins_repo_path_and_uninstall_removes(tmp_path):
    dest = rag.install(tmp_path)
    assert dest == tmp_path / "fullseye-ops"
    text = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert "FULLSEYE_REPO = %s" % rag.REPO.as_posix() in text
    assert "(not pinned" not in text                      # placeholder fully replaced
    # the pinned corpus actually exists (the promise the skill makes to the AI)
    assert (rag.REPO / "docs" / "ops" / "INDEX.md").is_file()
    assert rag.uninstall(tmp_path) is True
    assert not dest.exists()
    assert rag.uninstall(tmp_path) is False               # idempotent


def test_cli_roundtrip(tmp_path, capsys):
    assert rag.main(["--target", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "installed Claude Code RAG skill" in out
    assert rag.main(["--target", str(tmp_path), "--uninstall"]) == 0
    assert not (tmp_path / "fullseye-ops").exists()


def test_template_has_pinnable_line():
    """スキル原本に FULLSEYE_REPO 行が無いと installer は fail-closed で拒否する —
    その前提(テンプレ行の存在)を CI で固定する。"""
    text = (rag.SKILL_SRC / "SKILL.md").read_text(encoding="utf-8")
    assert rag._REPO_LINE.search(text) is not None


def test_install_refuses_without_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "REPO", tmp_path)            # a checkout with no docs/ops
    with pytest.raises(SystemExit):
        rag.install(tmp_path / "skills")


def test_skill_template_stays_in_sync_with_repo_skill():
    """wheel モード用テンプレート(fullseye/skill_template)は repo スキルの複製 —
    片方だけ編集する drift をここで封じる(公開 wheel が古いスキルを配らない)。"""
    repo_md = (rag.SKILL_SRC / "SKILL.md").read_text(encoding="utf-8")
    tmpl_md = (rag.REPO / "fullseye" / "skill_template" / "SKILL.md").read_text(encoding="utf-8")
    assert tmpl_md == repo_md


def test_wheel_mode_pins_package_catalog(tmp_path):
    """PyPI(wheel)モード: repo が無くてもインストールは成功し、FULLSEYE_REPO 行は
    パッケージ内 OP_CATALOG.md を指す(fail-closed はカタログ欠損時)。"""
    from fullseye import rag_setup as core
    dest = core.install(tmp_path, repo=None, _auto_repo=False)   # wheel-mode 強制
    text = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert "FULLSEYE_REPO = %s" % core.PKG.as_posix() in text
    assert "OP_CATALOG.md" in text
    assert (core.PKG / "OP_CATALOG.md").is_file()                # the pin is real


def test_reinstall_backs_up_user_edited_skill(tmp_path):
    """公開前レビュー回帰(high): `fullseye-rag` の再インストール(=更新)が
    ユーザーの SKILL.md 手編集を黙って消さない — 上書き前にバックアップが残る。"""
    import setup_claude_rag as rag
    rag.install(tmp_path)
    skill_md = tmp_path / rag.SKILL_NAME / "SKILL.md"
    skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nUSER EDIT\n",
                        encoding="utf-8")
    rag.install(tmp_path)                       # 再インストール(更新の標準導線)
    baks = sorted(tmp_path.glob(rag.SKILL_NAME + ".bak-*"))
    assert baks, "reinstall left no backup of the edited skill"
    assert "USER EDIT" in (baks[-1] / "SKILL.md").read_text(encoding="utf-8")
    assert "USER EDIT" not in skill_md.read_text(encoding="utf-8")
    # 同一秒内の連続インストールでもバックアップ名は衝突しない
    rag.install(tmp_path)
    assert len(sorted(tmp_path.glob(rag.SKILL_NAME + ".bak-*"))) >= 2
