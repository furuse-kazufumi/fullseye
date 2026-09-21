# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsvideocube —— 動画を空間 × 時間の立方体として見る op(Video Summagator の再実装)の統一レジストリ。

実体は ``videocube.py``(6 op / 4 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsvideocube
    opsvideocube.list_ops("render")
    rgb = opsvideocube.call("vol_render_transfer", opsvideocube.call("video_spacetime_cube", clip))

Nguyen・Niu・Liu(ACM CHI 2012)の Video Summagator は、動画を (x, y, t) の立方体にして「動かない背景を薄く・
動く物体を濃く」描き、切って回して場面へ飛ぶ道具。既存の ``videostream``(時間フィルタ・背景差分)と
``render_volume_projection``(X 線 / MIP)の間に、「動きだけを不透明度にした α 合成」と「断面(スリットスキャン)」が
無かった。

新しい型は作らない。**基準はこの repo 共通の 1 つ** ——「混ぜたときに例外ではなく、もっともらしく間違った
数値が出るか」:

* 動画は既存の ``video``(T, H, W)。立方体は既存の ``voxel``(3-D 配列)—— 時間軸が先頭にあるだけで、
  3-D の op(``vol_mip`` / ``render_volume_projection``)にそのまま渡して**意味のある**投影が出る側なので分けない。
* 描いた絵は ``rgb``、回した動画は ``rgbvideo``(conngraph の ``points_activity_video`` と同じ出口)、断面は ``image2d``、
  代表フレームの添字は ``indices``。
"""
import videocube

_MOD = {"videocube": videocube}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 立方体 —— 動画を (t, y, x) の場にする、断面を切る
    "cube": [
        ("video_spacetime_cube", "videocube", ["video"], "voxel"),
        ("video_cube_cut", "videocube", ["video"], "image2d"),
    ],
    # 描く —— 前から後ろへの α 合成、回す
    "render": [
        ("vol_render_transfer", "videocube", ["voxel"], "rgb"),
        ("video_cube_orbit", "videocube", ["video"], "rgbvideo"),
    ],
    # 要約 —— 何かが起きたフレーム
    "summary": [
        ("video_summary_keyframes", "videocube", ["video"], "indices"),
    ],
    # 書き出す —— 色動画をアニメーション GIF に(使い回しの出口。灰の video も受ける)
    "export": [
        ("video_write_gif", "videocube", ["rgbvideo"], "text"),
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


OPSVIDEOCUBE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSVIDEOCUBE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSVIDEOCUBE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSVIDEOCUBE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSVIDEOCUBE[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSVIDEOCUBE.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsvideocube: {len(OPSVIDEOCUBE)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
