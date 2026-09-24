# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsllmcore —— LLM に至る系譜の芯(注意・位置符号・正規化)の統一レジストリ。

実体は ``llmcore.py``(10 op / 4 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsllmcore
    opsllmcore.list_ops("attend")
    y = opsllmcore.call("attention_tiled", q, k, v, tile=32)

入れる基準は fullseye の PoC シリーズと同じ —— **厳密な等式・保存量・整数不変量が
立つものだけ**。蒸留・Sampler・Perplexity は真値が無いので入れていない。
RAG / Tool Calling / Guardrails は**アルゴリズムではなく系の設計**なので、
この箱ではなく llmesh / llive の側。

型語彙は 2 つ足した。基準はこの repo 共通の 1 つ ——
「混ぜたときに例外ではなく、**もっともらしく間違った数値**が出るか」:

* ``tokens`` =(T, d)の実数列。**軸の順が意味を持つ**(T = 列の長さ、d = 幅)。
  既存の ``matrix`` に載せると、転置した (d, T) がそのまま通って
  「長さ d の列を幅 T で」計算してしまい、例外ではなく別の数が返る。
  ``signal``(1-D)や ``points``(3 列固定)とも別物。
* ``attnmap`` =(T, S)の注意行列。生のスコアと softmax 後の重みの両方が座る。
  ``image2d`` に載せると「画像として」平滑化やしきい値がかかってしまい、
  行和 1 という性質が黙って壊れる。``attention_apply`` は行和を入口で検査する
  ので、この席に画像を入れたら**例外で止まる**(それが型を分ける理由)。

どちらも ``backends_typed.TYPE_TO_SORT`` に**入れない** —— 2-D レジストリへの
自動の橋(``tb_<op>``)が架かると、注意の入力として意味の無い 1 枚の画像が
渡されて「走ったが全面が同じ値」になる([[feedback_ran_is_not_meaningful_output]])。
"""
import llmcore

_MOD = {"llmcore": llmcore}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 前処理 —— 正規化と位置符号(どちらも保存量が立つ)
    "prepare": [
        ("rms_norm", "llmcore", ["tokens"], "tokens"),
        ("rope_rotate", "llmcore", ["tokens"], "tokens"),
    ],
    # 3 段に分けた注意 —— スコア → 重み → 混ぜる
    "score": [
        ("attention_scores", "llmcore", ["tokens", "tokens"], "attnmap"),
        ("attention_weights", "llmcore", ["attnmap"], "attnmap"),
        ("attention_apply", "llmcore", ["attnmap", "tokens"], "tokens"),
    ],
    # 一括の注意と、その別の括り方(答えは一致する)
    "attend": [
        ("attention_softmax", "llmcore", ["tokens", "tokens", "tokens"], "tokens"),
        ("attention_tiled", "llmcore", ["tokens", "tokens", "tokens"], "tokens"),
        ("attention_linear", "llmcore", ["tokens", "tokens", "tokens"], "tokens"),
        ("attention_grouped", "llmcore", ["tokens", "tokens", "tokens"], "tokens"),
    ],
    # 1 トークンずつ進める推論
    "decode": [
        ("kv_cache_decode", "llmcore", ["tokens", "tokens", "tokens"], "tokens"),
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


OPSLLMCORE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSLLMCORE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSLLMCORE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSLLMCORE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSLLMCORE[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSLLMCORE.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsllmcore: {len(OPSLLMCORE)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
