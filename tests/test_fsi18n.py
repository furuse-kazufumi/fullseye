"""fsi18n(ライブラリ側メッセージの言語切替下地)のテスト。
Tests for fsi18n, the library-side message-language substrate."""
import json

import fsi18n


def _reset():
    fsi18n.set_language(None)
    fsi18n._tables.clear()
    fsi18n._loaded.clear()


def test_english_default_is_passthrough(monkeypatch):
    _reset()
    monkeypatch.delenv("FULLSEYE_LANG", raising=False)
    assert fsi18n.get_language() == "en"
    assert fsi18n.msg("points must be (N, 3) (got shape {shape})", shape=(2, 2)) \
        == "points must be (N, 3) (got shape (2, 2))"


def test_shipped_ja_table_translates_template_then_formats(monkeypatch):
    _reset()
    monkeypatch.setenv("FULLSEYE_LANG", "ja")
    out = fsi18n.msg("points must be (N, 3) (got shape {shape})", shape=(5,))
    assert out == "points は (N, 3) が必要です(受領 shape=(5,))"
    # 訳の無いテンプレートは英語のまま(graceful) / untranslated stays English
    assert fsi18n.msg("no such template {x}", x=1) == "no such template 1"


def test_user_table_dir_overrides_shipped(tmp_path, monkeypatch):
    """ユーザー自作テーブル(FULLSEYE_I18N_DIR)が同梱訳より優先される —
    「翻訳テーブルはユーザーで作れる」仕様の実体。"""
    _reset()
    (tmp_path / "ja.json").write_text(json.dumps(
        {"points must be (N, 3) (got shape {shape})": "ユーザー訳 {shape}"},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("FULLSEYE_LANG", "ja")
    monkeypatch.setenv("FULLSEYE_I18N_DIR", str(tmp_path))
    assert fsi18n.msg("points must be (N, 3) (got shape {shape})", shape=1) == "ユーザー訳 1"


def test_user_table_adds_new_language(tmp_path, monkeypatch):
    _reset()
    (tmp_path / "de.json").write_text(json.dumps(
        {"empty point cloud": "leere Punktwolke"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("FULLSEYE_I18N_DIR", str(tmp_path))
    fsi18n.set_language("de")
    try:
        assert fsi18n.msg("empty point cloud") == "leere Punktwolke"
    finally:
        fsi18n.set_language(None)


def test_register_and_broken_translation_never_raise(monkeypatch):
    _reset()
    monkeypatch.setenv("FULLSEYE_LANG", "ja")
    fsi18n.register("ja", {"good {x}": "訳 {x}", "broken {x}": "壊れた {y}"})
    assert fsi18n.msg("good {x}", x=7) == "訳 7"
    # 訳側のプレースホルダ不整合 → 英語へフォールバック(絶対に raise しない)
    assert fsi18n.msg("broken {x}", x=7) == "broken 7"


def test_register_before_first_msg_beats_shipped_table(monkeypatch):
    """register() が最初の msg()(=テーブル初回ロード)より前でも、同梱訳に
    上書きされない — 敵対的レビュー指摘の回帰(register は常に最優先)。"""
    _reset()
    monkeypatch.setenv("FULLSEYE_LANG", "ja")
    # 同梱 ja.json に実在するキーへ、ロード前に register で別訳を載せる
    fsi18n.register("ja", {"points must be (N, 3) (got shape {shape})": "先勝ち {shape}"})
    assert fsi18n.msg("points must be (N, 3) (got shape {shape})", shape=1) == "先勝ち 1"


def test_env_language_code_is_case_insensitive(monkeypatch):
    """FULLSEYE_LANG=JA でも ja.json に届く(set_language と同じ正規化)。"""
    _reset()
    monkeypatch.setenv("FULLSEYE_LANG", "JA")
    assert fsi18n.get_language() == "ja"
    assert fsi18n.msg("empty point cloud") == "空の点群です"


def test_set_language_beats_env(monkeypatch):
    _reset()
    monkeypatch.setenv("FULLSEYE_LANG", "ja")
    fsi18n.set_language("en")
    try:
        assert fsi18n.msg("empty point cloud") == "empty point cloud"
    finally:
        fsi18n.set_language(None)
