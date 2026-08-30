"""ライブラリ側メッセージの言語切替の下地(fsi18n)。stdlib のみ・既定はゼロコスト。
Language-switching substrate for library-side messages (exceptions / CLI).
Stdlib-only; the English default is a zero-cost pass-through.

Studio の UI 対訳(studio_assets/i18n.json)とは**別レイヤ**: こちらは Python コードが
出すメッセージ(例外・CLI)用。設計方針(ユーザー仕様 2026-08-30):

- **英語がベース言語**(例外は英語に統一済み。traceback/ログ/検索の通貨)。
- **切替の下地**: ``FULLSEYE_LANG`` 環境変数か :func:`set_language`。既定 ``en`` は
  テーブルを読まず素通し(オーバーヘッドなし)。
- **翻訳テーブルはユーザーが作れる**: ``<lang>.json``(英語テンプレート → 訳)を
  ``FULLSEYE_I18N_DIR`` の指すディレクトリに置くだけ。同梱テーブル
  (``fullseye/i18n/<lang>.json``)より**ユーザーテーブルが優先**。
  :func:`register` でプログラムからも登録できる。

使い方(新規コード・主要バリデータから漸進採用)::

    from fsi18n import msg
    raise ValueError(msg("vertices must be (N, 3) (got shape {shape})", shape=V.shape))

**テンプレートを翻訳してから format する**のが要点 — 値が埋まった後の文字列は
テーブル照合できない。訳が無い/言語が en のときは英語テンプレートのまま。
翻訳テーブルの見つからないキー・壊れた JSON は黙って英語へフォールバック
(メッセージ機構自体が例外を投げてはいけない)。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_BUILTIN_DIR = Path(__file__).resolve().parent / "fullseye" / "i18n"
_lang: str | None = None                 # None = follow the environment
_tables: dict[str, dict[str, str]] = {}  # lang -> {english template: translation}
_loaded: set[str] = set()


def get_language() -> str:
    """現在の言語コード(set_language > FULLSEYE_LANG > 'en')。
    Current language code (set_language > FULLSEYE_LANG env > 'en')."""
    if _lang is not None:
        return _lang
    # set_language と同じ正規化(FULLSEYE_LANG=JA でも ja.json に届くように)
    # Normalise like set_language so FULLSEYE_LANG=JA still finds ja.json.
    return os.environ.get("FULLSEYE_LANG", "en").strip().lower() or "en"


def set_language(lang: str | None) -> None:
    """言語を明示設定(None で環境変数追従に戻す)。
    Set the language explicitly (None = follow the environment again)."""
    global _lang
    _lang = None if lang is None else str(lang).strip().lower()
    _loaded.discard(_lang)               # allow a table added after a previous miss


def register(lang: str, mapping: dict) -> None:
    """プログラムから対訳を登録(ユーザーテーブルと同格・既存キーを上書き)。
    Register translations programmatically (same rank as user tables; overrides)."""
    _tables.setdefault(lang, {}).update({str(k): str(v) for k, v in mapping.items()})


def _load(lang: str) -> None:
    if lang in _loaded:
        return
    table = _tables.setdefault(lang, {})
    # register() 済みの対訳は最優先で残す(最初の msg() より前に register された
    # キーがファイル読込で上書きされないように退避 → 最後に戻す)。
    # Keep register()ed entries top priority even when they predate the first load.
    registered = dict(table)
    # 同梱 → ユーザー(FULLSEYE_I18N_DIR)の順で読み、後勝ち=ユーザー優先
    dirs = [_BUILTIN_DIR]
    user_dir = os.environ.get("FULLSEYE_I18N_DIR", "").strip()
    if user_dir:
        dirs.append(Path(user_dir))
    for d in dirs:
        try:
            with open(d / (lang + ".json"), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                table.update({str(k): str(v) for k, v in data.items()})
        except Exception:
            pass                         # 壊れた/無いテーブルは黙って素通し(fail-open な翻訳)
    if registered:
        table.update(registered)
    # 完了後にマーク(並行 first-call は再ロードになりうるが冪等なので無害)。
    # Mark done last: a concurrent first call may reload, which is idempotent.
    _loaded.add(lang)


def msg(template: str, **kw) -> str:
    """英語テンプレートを現在言語へ翻訳してから format する。
    Translate the ENGLISH template first, then format it.

    訳が無ければ英語のまま。訳側のプレースホルダ欠落・format 失敗時も英語へ
    フォールバックし、**この関数自体は決して例外を出さない**。
    Missing translations and broken placeholders fall back to English; this
    function itself never raises."""
    lang = get_language()
    text = template
    if lang != "en":
        _load(lang)
        text = _tables.get(lang, {}).get(template, template)
    if not kw:
        return text
    try:
        return text.format(**kw)
    except Exception:
        try:
            return template.format(**kw)
        except Exception:
            return template
