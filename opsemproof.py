# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsemproof —— EM 連結体校正の「古典 CV セカンドオピニオン」op の統一レジストリ。

実体は ``emproof.py``(7 op / 4 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsemproof
    opsemproof.list_ops("suspect")
    t = opsemproof.call("seg_boundary_membrane_gap", labels, membrane)

EM の自動分割が残す**融合**(2 細胞が 1 id)と**分断**(1 細胞が 2 id)を、深層学習なしで数える。
先行研究(MergeNet 2017 / Zung 2017 / Dmitriev 2018 / ConnectomeBench 2025)はすべて学習器で候補を出す
ので、原理の違う第 2 意見 = 「膜(暗い稜線)はラベルの境界にしか無いはず」という 1 つの物理的前提を
2 通りに数える(内部の膜の弦 = 融合、膜の無い境界 = 分断)。評価用の人工誤りとホールドアウトの評価器を
同じ族に置き、閾値を選ぶ断面と測る断面を分けることを台帳の形で強制する。

新しい型は作らない。**基準はこの repo 共通の 1 つ** ——「混ぜたときに例外ではなく、もっともらしく
間違った数値が出るか」:

* 断面のラベルは既存の ``labels2d``(2-D 整数、0 = 背景)。blob2d の述語どおりで、EM のラベル
  (背景なし・id は連番でない)もそのまま載る。``ignore_zero`` で 0 の扱いを op ごとに選べる。
* 膜応答と生 EM は ``image2d``。``seg_membrane_response`` が産み、``seg_*`` が受ける。
  レジストリの ``sk_frangi`` の出力も同じ席に入る。
* 疑いの表・差分・評価は ``table``(列名 → 配列、または名前 → スカラの dict)。
* ``holdout_threshold`` はスコア列 ``signal`` × 4(訓練の正/負、評価の正/負)を受ける。
  fuzz は任意の 1-D 信号を入れるので AUC は 0.5 付近になるだけで、例外にはならない(契約どおり)。
"""
import emproof

_MOD = {"emproof": emproof}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 膜応答 —— 生 EM から暗い線を取る(Hessian の固有値、閉形式)
    "response": [
        ("seg_membrane_response", "emproof", ["image2d"], "image2d"),
    ],
    # 疑い —— 融合(内部の膜の弦)と分断(膜の無い境界)
    "suspect": [
        ("seg_membrane_chord_score", "emproof", ["labels2d", "image2d"], "table"),
        ("seg_boundary_membrane_gap", "emproof", ["labels2d", "image2d"], "table"),
    ],
    # 仕込む —— 評価用の人工誤りと、その答え合わせ
    "inject": [
        ("seg_inject_merge", "emproof", ["labels2d"], "labels2d"),
        ("seg_inject_split", "emproof", ["labels2d"], "labels2d"),
        ("seg_label_changes", "emproof", ["labels2d", "labels2d"], "table"),
    ],
    # 測る —— 閾値は訓練側で選び、評価は別の側で
    "evaluate": [
        ("holdout_threshold", "emproof", ["signal", "signal", "signal", "signal"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSEMPROOF = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSEMPROOF.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSEMPROOF[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSEMPROOF[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSEMPROOF[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSEMPROOF.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsemproof: {len(OPSEMPROOF)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
