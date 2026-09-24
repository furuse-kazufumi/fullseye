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
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: 検査対象外。``docs/`` は出典表記が許可される場所、``build/`` は生成物。
#: **第三者のコードは対象外**: この規律は「fullseye が自分のものに他社名を付けていないか」
#: を見るものであって、依存パッケージの命名を裁くものではない。2026-09-15、wheel の門が
#: 作った ``.wheelenv``(site-packages 入りの venv)を走査してしまい、numpy / pip / scipy の
#: ``writelines`` ``whitelist`` ``RateLimiter`` が 4 文字の禁止語に**部分一致**して 10 件の偽陽性で
#: 落ちた —— 門が**事故の起きない場所に立っていた**。
_SKIP_DIRS = {"build", "dist", ".git", "docs", "out", "__pycache__", ".pytest_cache",
              "node_modules", ".mypy_cache", ".ruff_cache", ".eggs", "site-packages"}

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
        ("acquire.py", "optscene.py"),
        "acquire.py = カメラ driver を選ぶ backend 識別子。optscene.py = sensor_catalog に"
        "載せた諸元の**出典**(公開されている EMVA1288 実測表)。どちらも実在するものを"
        "名指しているだけで、fullseye 側の何かに名前を付けてはいない。出典を消すと"
        "数値が検証不能になる(PROVENANCE.md の「出典表記」に当たる)",
    ),
    "allied vision": (
        ("acquire.py",),
        "``vimba`` backend が開く**実在の SDK の名前**(Vimba X / vmbpy)。basler と"
        "同じ扱いで、backend の表と opener の docstring に出るだけであり、fullseye 側の"
        "何かに名前を付けてはいない。誰の SDK かを消すと、利用者がどれを入れれば"
        "その backend が動くのか分からなくなる",
    ),
    "teledyne": (
        ("optscene.py",),
        "sensor_catalog が載せる**実在センサの製造元**。型番だけでは何のセンサか"
        "特定できず、利用者が一次情報に当たれなくなる。fullseye 側の命名ではない",
    ),
    "hamamatsu": (
        ("optscene.py",),
        "同上 —— sensor_catalog が載せる実在センサの製造元であり、諸元の出所を"
        "たどるための識別子。fullseye 側の何かに名前を付けてはいない",
    ),
}


def _is_virtualenv(path: str) -> bool:
    """``pyvenv.cfg`` があれば仮想環境。**名前でなく実体のマーカーで判定する** ——
    ``.venv`` ``.wheelenv`` ``.venv-gsplat`` のように名前は幾らでも増えるので、
    名前の一覧で弾くと必ず漏れる(実際 ``.wheelenv`` で漏れた)。"""
    return os.path.exists(os.path.join(path, "pyvenv.cfg"))


def _py_files():
    """検査対象の .py を repo 相対パスで列挙する(fullseye 自身の面だけ)。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS
                       and not _is_virtualenv(os.path.join(dirpath, d))]
        for fn in filenames:
            if fn.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                yield rel.replace(os.sep, "/")


def _allowed(word: str, relpath: str) -> bool:
    if word in _GLOBAL_INTEROP:
        return True
    entry = _INTEROP_ALLOWLIST.get(word)
    if entry is None:
        return False
    prefixes, _reason = entry
    return any(p in relpath for p in prefixes)


#: 識別子・散文を語に割る。``snake_case`` / ``camelCase`` / 数字の境界で切る。
_TOKEN_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _contains_vendor(text: str, vendor: str) -> bool:
    """``text`` にベンダ名が**語として**現れるか。

    素の部分文字列照合は使えない。禁止語のうち 4 文字の短いものは ``whitelist``
    ``writelines`` ``RateLimiter`` のような**普通の英単語の内側**にそのまま入って
    いて、片端から引っかかる。逆に語境界だけで見ると、大文字で連結した社名表記を
    取り逃がす。そこで**連続するトークンの連結**が禁止語(英数字だけに正規化した
    もの)と一致するかで見る:

      * 社名 + 名詞の camelCase -> [社名, 名詞] -> 社名に一致(捕まえる)
      * 社名を大文字連結した表記 -> [mv, tec] のように割れても連結すれば一致(捕まえる)
      * ハイフン社名 -> [語, 語] -> 連結が一致(捕まえる)
      * ``whitelist`` -> [whitelist] -> どの連結も禁止語にならない(通す)
      * ``RateLimiter`` -> [rate, limiter] -> 同上(通す)

    具体的な綴りは下の自己検査に実データとして置く(ここに実名を書くと、この
    docstring 自身が規律違反になる —— 実際 2026-09-15 にそれで落ちた)。
    """
    target = re.sub(r"[^a-z0-9]", "", vendor.lower())
    if not target:
        return False
    toks = _tokens(text)
    for i in range(len(toks)):
        joined = ""
        for j in range(i, len(toks)):
            joined += toks[j]
            if joined == target:
                return True
            if len(joined) > len(target):
                break
    return False


def _hits(text: str, relpath: str):
    return [w for w in _BANNED
            if _contains_vendor(text, w) and not _allowed(w, relpath)]


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
        assert prefixes, f"{word} の免除にパス制限が無い(パス限定側で全面免除は認めない)"
        assert len(reason) >= 20, f"{word} の免除理由が短すぎる: {reason!r}"
    for word, reason in _GLOBAL_INTEROP.items():
        assert word in _BANNED, f"{word} は禁止語に無いので免除の意味がない"
        assert len(reason) >= 20, f"{word} の全面免除の理由が短すぎる: {reason!r}"
    assert not (set(_GLOBAL_INTEROP) & set(_INTEROP_ALLOWLIST)), \
        "同じ語が全面免除とパス限定免除の両方にあると、どちらが効くか読めない"


def test_global_exemptions_stay_few():
    """全面免除は例外中の例外。増えたら規律が形骸化しているサインなので気づけるように。"""
    assert len(_GLOBAL_INTEROP) <= 3, (
        "全面免除が増えている。新しい語はパス限定側 (_INTEROP_ALLOWLIST) に入れるか、"
        "そもそも名前を使わない設計に直すこと")


def test_the_check_actually_catches_a_violation():
    """検査が空振りしていないこと(禁止語リストが機能しているかの自己検査)。"""
    assert _hits("this module exists because Prophesee ships it", "newmod.py")
    assert not _hits("this module exists because Prophesee ships it", "docs/x.md")[:0]
    # 免除は経路つき: 同じ語でも許可パス外なら失格になる
    assert _allowed("basler", "acquire.py")
    assert not _allowed("basler", "lightfield.py")


def test_the_check_catches_vendor_names_however_they_are_spelled():
    """語の切れ目が見えない綴り方でも捕まえること。

    ``camelCase`` の連結や ``snake_case``、区切り記号つきで書かれても、
    ベンダ名はベンダ名である(綴りはコード側の実データで与える)。
    """
    for name in ("TeliCamera", "toshiba_teli", "MVTecStyleCatalog",
                 "MicroEpsilonProbe", "prophesee_sensor"):
        assert _contains_vendor(name, _vendor_of(name)), name


def _vendor_of(name: str) -> str:
    """上のテスト用: その綴りが当たるはずの禁止語を返す。"""
    for w in _BANNED:
        if _contains_vendor(name, w):
            return w
    return "(なし)"


def test_the_check_does_not_fire_on_ordinary_english_words():
    """**偽陽性で落ちない**こと。

    2026-09-15、4 文字の禁止語が ``writelines`` ``whitelist`` ``RateLimiter``
    ``InfiniteLimits`` の内側に部分一致し、第三者パッケージで 10 件の偽陽性を
    出して門が赤くなった。**門が誤って鳴る**のは
    門が鳴らないのと同じくらい悪い —— 人は鳴りっぱなしの門を無視するようになる。
    """
    for word in ("writelines", "whitelist", "RateLimiter", "_InfiniteLimitsTransform",
                 "IntelItaniumCCompiler", "DEFAULT_METHOD_WHITELIST", "satellite",
                 "delete_line", "rate_limit"):
        assert not _hits(word, "somemod.py"), f"偽陽性: {word}"


def test_third_party_virtualenvs_are_not_scanned():
    """検査対象は **fullseye 自身の面**だけであること。

    ``.wheelenv`` は wheel の門が建てる venv で、中身は numpy / pip / scipy。
    ここを走査すると他社パッケージの命名を裁くことになり、偽陽性しか生まない。
    判定は名前でなく ``pyvenv.cfg`` の有無(名前の一覧は必ず漏れる)。
    """
    scanned = list(_py_files())
    assert scanned, "走査結果が空(門が何も見ていない)"
    intruders = [p for p in scanned if "site-packages" in p or "/.wheelenv/" in p
                 or p.startswith(".wheelenv/")]
    assert not intruders, "第三者パッケージを走査している: " + ", ".join(intruders[:10])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
