# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fssystem —— **システムパラメータ**(``set_system`` / ``get_system`` の相互運用面)。

産業用の画像処理ライブラリには、ライブラリ全体のふるまいを一箇所で切り替える
パラメータ群があるのが普通で、``set_system`` / ``get_system`` / ``query_system``
という**実在の名前**を相互運用のためにそのまま借りている(``docs/PROVENANCE.md``
の命名規約: 相互運用のための識別子は可、自分たちの物に他社製品名を付けるのは不可)。

## 2 つの制約 —— ここが素朴な実装と違うところ

### (1) 可変グローバルにしない

実体は :mod:`contextvars`。``drawstyle`` が同じ判断をしていて、理由もそのまま:

* 展示画像は**再生成で SHA-256 一致**が要件。共有された可変既定があると
  「どの図を先に描いたか」が結果に混ざる。
* 生成器は**並行に走る**。共有既定はレースで入れ替わり、**例外にならず
  「もっともらしく間違った図」**として出てくる。

``contextvars`` ならスレッド/タスクごとに独立し、例外経路でも復帰する。

### (2) **緩められない** —— 厳しくするか、意図を記録するかだけ

これがこのモジュールの中心的な設計判断。素朴なシステムパラメータは
「検査を切って速くする」ために使われるが、この repo では**それが最も危ない**。
``data_range`` の既定を隠れたパラメータで供給できるようにすると、
``[0,1]`` の絵を 255 の設定で測った **PSNR が 48.13 dB ずれる**のに、
呼び出し側のコードは 1 文字も変わらない ―― 追跡不能な事故になる。

よって、登録できるパラメータは次のどちらかに限る:

* **厳しくする方向のみ** —— 既定が最も緩い側で、変更すると検査が増える。
  (:data:`SYSTEM_PARAMS` の ``tightens_only=True``)
* **意図の記録のみ** —— 数値には一切影響せず、報告に何が書かれるかだけが変わる。

``tightens_only`` の宣言はテストが機械で検査する(``tests/test_fssystem.py``)。
**「速くするために検査を切る」パラメータはこの表に載せられない。**

使い方::

    import fullseye as fs

    fs.get_system("metric_contract")             # -> 'strict'(既定)

    with fs.system(metric_contract="tolerant"):  # 範囲を限って切り替える
        ...                                       # (予約のみ: 今はまだ何も読まない)

    old = fs.set_system("extra_checks", "on")    # その文脈で切り替え、前の値が返る
    fs.reset_system()                            # 全部を既定へ

### (3) 読み手が居ないパラメータは「予約」と表に書く

``metric_contract`` / ``unmeasurable_policy`` は受理・記録されるが、**2026-09 時点で
読むコードが無い**(``applied_by=None``)。設定しても数値も経路も変わらない。
効いていない設定を「効く」と読ませないため、各項目の ``applied_by`` に実際に
``get_system`` を呼ぶファイルを列挙し、テストが grep で突き合わせる。
"""
from __future__ import annotations

import contextlib
import contextvars

__all__ = [
    "SYSTEM_PARAMS", "set_system", "get_system", "query_system",
    "system", "reset_system", "system_snapshot",
]


#: 登録済みシステムパラメータ。
#:
#: ``tightens_only`` が ``True`` のものは、既定から動かすと**検査が増える**だけ。
#: ``False`` のものは**数値に一切影響しない**(報告の記述が変わるだけ)。
#: 「検査を切って速くする」種類のパラメータはここに載せられない —— 載せると
#: ``tests/test_fssystem.py`` の宣言検査が落ちる。
#:
#: ``applied_by`` は**その値を実際に読むモジュール**(``get_system("<name>")`` を
#: 呼ぶファイル名のタプル)。``None`` は **予約のみ**: 値は受理・記録されるが
#: **まだ何も読まない**(設定しても挙動は 1 bit も変わらない)。「設定できるのに
#: 効いていない」を仕様書の文章でなく表で言い、``tests/test_fssystem.py`` が
#: grep で裏を取る(読み手を名乗るのに読んでいない/数値に影響するのに読み手が
#: 無い、はどちらも落ちる)。
SYSTEM_PARAMS = {
    "metric_contract": {
        "values": ("strict", "tolerant"),
        "default": "strict",
        "tightens_only": False,
        "affects_numbers": False,
        "applied_by": None,
        "doc": (
            "測定 op を人が呼んでいるのか(strict)、自動で回しているのか(tolerant)。"
            "**op 自身はこの値を読まない** —— 読むと隠れた状態で返り値の型が変わり、"
            "この repo がいちばん嫌う『例外でなく、もっともらしく間違う』になる。"
            "★予約のみ(applied_by=None): 現状 metriccontract の寛容な入口"
            "(attempt/rank_attempts)はこの値を読まず、明示的に呼び分ける。"
            "設定は system_snapshot() で報告に写るだけで、数値も経路も変えない。"
        ),
    },
    "extra_checks": {
        "values": ("off", "on"),
        "default": "off",
        "tightens_only": True,
        "affects_numbers": False,
        "applied_by": ("colortransport.py", "imgmetrics.py"),
        "doc": (
            "既定でも fail-closed だが、**理屈の上では正しくないが実害が出るとは"
            "限らない**場面(同値を引き裂くヒストグラム整合、対称でない圧縮距離)を"
            "拒否に格上げする。既定を on にしていないのは、既存の呼び手が"
            "意図してその挙動を使っている場合があるため。"
        ),
    },
    "unmeasurable_policy": {
        "values": ("worst", "skip"),
        "default": "worst",
        "tightens_only": False,
        "affects_numbers": False,
        "applied_by": None,
        "doc": (
            "寛容な契約で『測れなかった』候補をどう扱うか。worst = 最悪値に倒して"
            "順位の最下位に置く / skip = 順位から外す。**strict の経路には無関係**。"
            "★予約のみ(applied_by=None): rank_attempts は常に worst(最下位)で、"
            "skip を設定しても順位は変わらない。"
        ),
    },
}

_VARS = {
    name: contextvars.ContextVar(f"fssystem.{name}", default=spec["default"])
    for name, spec in SYSTEM_PARAMS.items()
}


def _check(param, value):
    if param not in SYSTEM_PARAMS:
        raise ValueError(
            f"unknown system parameter {param!r}; known: {sorted(SYSTEM_PARAMS)} "
            "(silently accepting an unknown name would let a typo look like it took effect)"
        )
    allowed = SYSTEM_PARAMS[param]["values"]
    if value not in allowed:
        raise ValueError(f"system parameter {param!r} takes one of {allowed}, got {value!r}")
    return value


def get_system(param):
    """システムパラメータの現在値。"""
    if param not in _VARS:
        raise ValueError(f"unknown system parameter {param!r}; known: {sorted(SYSTEM_PARAMS)}")
    return _VARS[param].get()


def set_system(param, value):
    """システムパラメータを**現在の文脈で**切り替え、**前の値を返す**。

    プロセス全体の可変グローバルではない(:mod:`contextvars` なのでスレッド/
    タスクごとに独立)。前の値を返すのは、呼び手が明示的に戻せるようにするため
    —— 範囲を限るなら :func:`system` の方が安全。
    """
    _check(param, value)
    old = _VARS[param].get()
    _VARS[param].set(value)
    return old


@contextlib.contextmanager
def system(**params):
    """範囲を限ってシステムパラメータを切り替える文脈。

    ``with system(metric_contract="tolerant"): ...``。
    例外で抜けても必ず元へ戻る(トークンで復帰する)。
    """
    for k, v in params.items():
        _check(k, v)
    tokens = {k: _VARS[k].set(v) for k, v in params.items()}
    try:
        yield
    finally:
        for k, tok in tokens.items():
            _VARS[k].reset(tok)


def reset_system():
    """すべてのシステムパラメータを既定へ戻す。"""
    for name, spec in SYSTEM_PARAMS.items():
        _VARS[name].set(spec["default"])


def query_system(param=None):
    """パラメータの一覧、または 1 つの仕様(取りうる値・既定・説明)。"""
    if param is None:
        return sorted(SYSTEM_PARAMS)
    if param not in SYSTEM_PARAMS:
        raise ValueError(f"unknown system parameter {param!r}; known: {sorted(SYSTEM_PARAMS)}")
    return dict(SYSTEM_PARAMS[param])


def system_snapshot():
    """現在値をまとめて返す。**報告に何の設定で測ったかを書くため**。

    数値だけを図注に写して条件が消える事故を防ぐのが、この repo の一貫した
    方針なので、システムパラメータも同じように持ち回れる形にしておく。
    """
    return {name: var.get() for name, var in sorted(_VARS.items())}


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    print(f"fssystem: {len(SYSTEM_PARAMS)} params")
    for name, spec in sorted(SYSTEM_PARAMS.items()):
        kind = "厳しくする方向のみ" if spec["tightens_only"] else "数値に影響しない"
        print(f"  {name:22s} {spec['values']}  既定={spec['default']!r}  ({kind})")
