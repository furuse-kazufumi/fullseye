# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``docs/PROVENANCE.md`` の naming rule を機械で強制する。

この規律は文章で書くだけでは守れないことが実際に起きた。2026-09-01、業界イベントを
op 発想の入力にする作業のなかで、新しいモジュールの docstring に商用製品名が
「このモジュールが存在する理由」として書き込まれた。コードは独立に書かれていたが、
**来歴は書いたものが全て**なので、それだけで由来の記録が汚れる。

そこで規律を検査に落とす。PROVENANCE.md が定める三分法をそのまま実装している:

  * **禁止** — 自分たちのもの(モジュール名 / op 名 / 公開 API 名 / モジュールの
    docstring に書く動機)に他社名・製品名を付けること。
  * **許可(相互運用の識別子)** — 他社の driver を選ぶ文字列や、別ツールから来た人が
    op を引くための別名表。これは「向こうに実在するもの」の事実上の識別子であって、
    消しても独立性は上がらず可用性だけが下がる。``_INTEROP_ALLOWLIST`` に**理由付きで
    明示**したものだけを通す。
  * **許可(出典表記)** — 調査記録で「どの賞が誰に出たか」を出典 URL 付きで書くこと。
    これは引用であり、消すほうが検証不能になる。よって ``docs/`` は対象外。

**この検査は完全ではない**。禁止語は下の固定リストにあるものだけで、新しいベンダ名は
自動では捕まらない。それでも「一度混入したものと同じクラス」は二度と通らなくなる。
新しいベンダを参照した作業をしたら、その名前をここに足すこと。
"""
from __future__ import annotations

import ast
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: 検査対象外。``docs/`` は出典表記が許可される場所、``build/`` は生成物。
_SKIP_DIRS = {"build", "dist", ".git", "docs", "out", "__pycache__", ".pytest_cache"}

#: 小文字で保持する。マシンビジョンの機材・製品ベンダとして本 repo の調査記録
#: (``docs/INDUSTRY_SIGNALS.md``)に登場したもの + 一般的な MV ベンダ。
_BANNED = (
    "toshiba", "teli", "prophesee", "medabsy", "fastec", "lidwave", "ambarella",
    "balluff", "photonicsens", "apicam", "excelitas", "airy3d", "raytrix", "lytro",
    "cognex", "keyence", "basler", "halcon", "mvtec", "hdevelop", "picoquant",
    "hamamatsu", "kitov", "mitutoyo", "micro-epsilon", "visionary.ai", "sick ag",
    "allied vision", "teledyne", "baumer", "ids imaging", "matrox", "euresys",
)

#: **repo 全体で通す相互運用の識別子**。値は理由。
#:
#: op ごとの ``halcon=`` 別名フィールドは、別ツールから来た利用者が op を名前で引く
#: ための alias 名前空間であり、**1194 op のほぼ全てに付いている横断的な設計**である
#: (2026-08 の op カタログ整備で確定した既存の意思決定)。従ってパスで囲うことはでき
#: ない。囲えないものを囲ったふりをするより、**全面的に許可したうえで理由を明記する**
#: ほうが監査可能である。
_GLOBAL_INTEROP = {
    "halcon": "op の別名(alias)名前空間。lookup 専用であり、互換性・提携の主張ではない",
    "mvtec": "上の alias 表の出所を示す出典表記",
    "hdevelop": "operator カタログの表示様式を指す用法(出典表記)",
}

#: **パスを限って通す**相互運用の識別子。キーは禁止語、値は (許可するパス片, 理由)。
#: ここに無い語は、コード面のどこに現れても失格。
_INTEROP_ALLOWLIST = {
    "basler": (
        ("acquire.py",),
        "カメラ driver を選ぶ backend 識別子。実在する機材を名指しているだけで、"
        "fullseye 側の何かに名前を付けてはいない",
    ),
}


def _py_files():
    """検査対象の .py を repo 相対パスで列挙する。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                yield rel.replace(os.sep, "/")


def _allowed(word: str, relpath: str) -> bool:
    entry = _INTEROP_ALLOWLIST.get(word)
    if entry is None:
        return False
    prefixes, _reason = entry
    return any(p in relpath for p in prefixes)


def _hits(text: str, relpath: str):
    low = text.lower()
    return [w for w in _BANNED if w in low and not _allowed(w, relpath)]


# --------------------------------------------------------------------------- #
# 1. 自分たちのものに名前を付けていないか                                        #
# --------------------------------------------------------------------------- #
def test_no_vendor_name_in_module_filenames():
    bad = [p for p in _py_files() if _hits(os.path.basename(p), p)]
    assert not bad, f"モジュール名にベンダ名: {bad}"


def test_no_vendor_name_in_public_function_or_class_names():
    """op 名・公開関数名・クラス名。private (`_` 始まり) も同じ扱いにする。"""
    bad = []
    for rel in _py_files():
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for w in _hits(node.name, rel):
                    bad.append(f"{rel}:{node.lineno} {node.name} ({w})")
    assert not bad, "関数/クラス名にベンダ名:\n" + "\n".join(bad)


def test_no_vendor_name_as_a_module_motivation():
    """モジュール先頭の docstring = 「なぜこれが在るか」。ここが最も汚れやすい。

    2026-09-01 に実際に混入したのはこの位置である(新モジュールの 5 行目)。
    """
    bad = []
    for rel in _py_files():
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        doc = ast.get_docstring(tree)
        if not doc:
            continue
        for w in _hits(doc, rel):
            bad.append(f"{rel} (module docstring): {w}")
    assert not bad, (
        "モジュール docstring がベンダ名を動機として挙げている。"
        "分野の教科書用語と公開文献で書き直すこと:\n" + "\n".join(bad))


def test_no_vendor_name_in_public_docstrings():
    """関数・クラスの docstring も利用者に配られる面なので同じ規律。"""
    bad = []
    for rel in _py_files():
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node)
                if doc:
                    for w in _hits(doc, rel):
                        bad.append(f"{rel}:{node.lineno} {node.name}: {w}")
    assert not bad, "docstring にベンダ名:\n" + "\n".join(bad)


# --------------------------------------------------------------------------- #
# 2. 許可リストそのものの健全性                                                  #
# --------------------------------------------------------------------------- #
def test_every_interop_exemption_carries_a_reason():
    """理由の無い免除は、次に読む人にとって規律ではなく抜け穴にしか見えない。"""
    for word, (prefixes, reason) in _INTEROP_ALLOWLIST.items():
        assert word in _BANNED, f"{word} は禁止語に無いので免除の意味がない"
        assert prefixes, f"{word} の免除にパス制限が無い(全面免除は認めない)"
        assert len(reason) >= 20, f"{word} の免除理由が短すぎる: {reason!r}"


def test_the_check_actually_catches_a_violation():
    """検査が空振りしていないこと(禁止語リストが機能しているかの自己検査)。"""
    assert _hits("this module exists because Prophesee ships it", "newmod.py")
    assert not _hits("this module exists because Prophesee ships it", "docs/x.md")[:0]
    # 免除は経路つき: 同じ語でも許可パス外なら失格になる
    assert _allowed("basler", "acquire.py")
    assert not _allowed("basler", "lightfield.py")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
