# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsgenerative —— 「絵を作る側」の op 台帳(錯視 / 無限描画 / 循環動画)。

動機(2026-09-23)は著者の 3 つの要望 ——「錯視画像とかぱっと作れるような op」
「大昔から無限にグラフィックを描画し続けるような物を作る op」「時間軸で循環する
ような画像」。3 つとも作品づくりの話に見えるが、この repo に入る理由は同じ 1 つ:

    **どれも「見た目では確かめられない主張」を持ち、その主張には厳密な真値がある。**

  * 錯視は「見た目が嘘をつく」ことの純粋な実例。カフェウォールの目地は厳密に
    平行、ミュラー・リヤーの軸は厳密に等長、チェッカーシャドウの 2 マスは厳密に
    同値 —— **目が否定する不変量**を、生成器自身が数として返す
    (``illusion_ground_truth``)。
  * 無限描画は「いつ止めても途中」なので、絵の採点ができない。だから絵とは
    独立な恒等式を持つものだけを入れた —— 規則 90 の行はリュカの定理で
    ``C(n,k) mod 2``、アポロニウスはデカルトの円定理、カール場は発散が恒等的に 0、
    餌も死も無い反応拡散は総量保存、ラングトンの蟻は周期 104 の高速道路
    (``perpetual_identities``)。
  * 循環動画の「継ぎ目が無い」は**編集で消すもの**ではなく、時間依存の量を
    すべて θ の関数にすれば**構成から従う**。``perpetual_loop_seam`` は
    「最後のまたぎが、ほかのまたぎと見分けが付かない」を数で出す
    (比が 0 ではなく **1 に近い**のが正解 —— 0 は「動きが止まっている」)。

**この台帳がライブラリとして効く形**: ここで作った絵は「真値つきの入力」になる。
錯視図は測る側の採点表(目には傾いて見える目地を、測る op は 0 と答えるか)、
無限描画は尽きない試験入力、循環動画は時間方向の op を周期境界で試せる素材。
``defectgen`` が写真でなく確率幾何から傷を描くのと同じ理由で、**正解が最初から
付いてくる**。

型語彙(**新語はゼロ**):
  * ``rgb`` —— (H,W,3)、[0,1] の float。生成器の既定の返り。既存の 2,147 op が
    そのまま掛かることに意味があるので、「錯視画像」という特別な型は作らない。
  * ``rgbvideo`` —— (T,H,W,3)。``perpetual_loop`` の返り。``video``(T,H,W)と
    分かれているのは既存の区別で、ここで新しく作ったものではない。
  * ``table`` —— 状態 dict と、真値/恒等式/継ぎ目の表。既存の table。

使い方::

    import opsgenerative
    opsgenerative.list_ops("illusion")
    img = opsgenerative.get("illusion_cafe_wall")()
    gt = opsgenerative.call("illusion_ground_truth", "cafe_wall")
"""
import illusion
import perpetual

_MOD = {"illusion": illusion, "perpetual": perpetual}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "illusion": [
        ("illusion_cafe_wall", "illusion", [], "rgb"),
        ("illusion_muller_lyer", "illusion", [], "rgb"),
        ("illusion_ponzo", "illusion", [], "rgb"),
        ("illusion_zollner", "illusion", [], "rgb"),
        ("illusion_poggendorff", "illusion", [], "rgb"),
        ("illusion_fraser_spiral", "illusion", [], "rgb"),
        ("illusion_ebbinghaus", "illusion", [], "rgb"),
        ("illusion_kanizsa", "illusion", [], "rgb"),
        ("illusion_checker_shadow", "illusion", [], "rgb"),
        ("illusion_simultaneous_contrast", "illusion", [], "rgb"),
        ("illusion_hermann_grid", "illusion", [], "rgb"),
        ("illusion_scintillating_grid", "illusion", [], "rgb"),
        ("illusion_ground_truth", "illusion", [], "table"),
    ],
    "perpetual": [
        ("perpetual_ten_print", "perpetual", [], "rgb"),
        ("perpetual_truchet", "perpetual", [], "rgb"),
        ("perpetual_elementary_ca", "perpetual", [], "rgb"),
        ("perpetual_langtons_ant", "perpetual", [], "rgb"),
        ("perpetual_chaos_game", "perpetual", [], "rgb"),
        ("perpetual_apollonian", "perpetual", [], "rgb"),
        ("perpetual_harmonograph", "perpetual", [], "rgb"),
        ("perpetual_ifs_attractor", "perpetual", [], "rgb"),
        ("perpetual_flow_field", "perpetual", [], "rgb"),
        ("perpetual_reaction_diffusion", "perpetual", [], "rgb"),
        ("perpetual_plasma", "perpetual", [], "rgb"),
        ("perpetual_identities", "perpetual", [], "table"),
    ],
    "stream": [
        ("perpetual_state", "perpetual", [], "table"),
        ("perpetual_step", "perpetual", ["table"], "table"),
        ("perpetual_render", "perpetual", ["table"], "rgb"),
    ],
    "loop": [
        ("perpetual_loop", "perpetual", [], "rgbvideo"),
        ("perpetual_loop_seam", "perpetual", ["rgbvideo"], "table"),
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


OPSGENERATIVE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSGENERATIVE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。生成器は ndarray を、
#: 表と状態は dict を素で返すので、adapter を挟まないほうが連鎖ファザーの
#: 検証が最も厳しくなる(素の返りをそのまま宣言と突き合わせる)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSGENERATIVE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSGENERATIVE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSGENERATIVE[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSGENERATIVE.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsgenerative: {len(OPSGENERATIVE)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
