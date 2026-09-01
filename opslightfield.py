# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opslightfield — fullseye ライトフィールド(plenoptic)op の統一レジストリ。

ユーザー方針(2026-09-01)「VISION Award にあるような事に繋がる機能がほしい」。
一次確認した実在ファイナリスト photonicSENS **apiCAM**(産業用 plenoptic:
マイクロレンズアレイで**単一センサ・単一ショット**から 2D 画像と画素ごとの
校正済み深度を同時取得)に対応する機能が fullseye には 1 つも無かった —
``light_field`` / ``plenoptic`` / ``refocus`` / ``sub_aperture`` / ``microlens``
/ ``epi`` は全 op 名でヒット 0(2026-09-01 実測)。本レジストリはその台帳
(lightfield.py、17 op / 5 カテゴリ)。

既存資産との棲み分け(**再実装せず import して合成**):
  * レンズ・絞り・被写界深度の算術 = optics(``thin_lens`` / ``depth_of_field``
    ほか 18 op)。``lf_plenoptic_design`` はそれを**呼ぶ** — plenoptic カメラの
    リフォーカス可能レンジは「許容錯乱円を画素ピッチではなく**マイクロレンズ
    ピッチ**にした被写界深度」そのもので、実際にそう計算している(実測
    ``refocus_gain`` = 8.004 @ 角度分解能 8 = 教科書どおり)。
  * 2 眼ステレオ = stereo(``disparity_map`` / ``disparity_census`` /
    ``disparity_sgm`` / ``depth_from_disparity`` / ``lr_consistency``)。
    ライトフィールドは「2 台のカメラ」ではなく**角度グリッド全体**を同時に
    使う(それが遮蔽ロバスト性と subpixel 視差の出所)。2 視点しか無いなら
    stereo の方が適任なのでそちらへ。
  * 実カメラの焦点合成 = focus_stack(物理的に N 回合焦し直す)。
    ``lf_focal_stack`` は同じものを**単一露光から計算で**作り、返りは素の
    2-D 画像 list(``images`` 型)なので focus_stack の融合機構がそのまま乗る。
  * 点群・再投影・3D フィット = match3d / pointcloud / ransac_fit。
    ``lf_disparity_to_depth`` は metric depth map で止める。
  * 汎用の鮮鋭度・Laplacian・分散フィルタ = ops / filters_freq。
    ``lf_depth_from_focus`` 内の焦点尺度は意図的に private ヘルパ。

使い方:
    import opslightfield
    opslightfield.list_ops("depth")
    lf, gt = opslightfield.get("lf_synthesize")((1.0,), (5, 5), (64, 64))
    img = opslightfield.call("lf_refocus", lf, 1.0)
"""
import lightfield

_MOD = {"lightfield": lightfield}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / images(画像の並び)/ depth / table(dict or list)
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * image2d — サブアパーチャ画像・中心視点・EPI・リフォーカス像・開口マスク・
#     **スロープ地図**はすべて素の 2-D float 配列で、型として嘘が無い。特に
#     スロープ地図を depth と宣言しなかったのは意図的: 中身は px/view であって
#     距離ではないので、depth と名乗ると下流の距離 op に単位違いを渡せてしまう。
#     距離を名乗るのは lf_disparity_to_depth の返りだけ。
#   * images  — 焦点スタックと視点リストは「2-D 画像の並び」そのもの。list を
#     返すので既存の多画像 op(融合・統計・focus_stack 系)へ無変換で流れる。
#   * depth   — lf_disparity_to_depth の返りのみ。baseline と同じ長さ単位の
#     実距離マップで、これは既存語彙の意味と完全に一致する。
#   * table   — lf_stats / lf_plenoptic_design の返りは dict。TYPE_CHECKS の
#     table は list|dict なので該当。
#
# 新語彙 1 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsmath の cpoints / cscalar、opsoptics の jones / stokes):
#   * lightfield — 4-D の ``(V, U, H, W)`` 実配列。角度 2 軸 + 空間 2 軸で、
#     **角度がグリッドであること**が全 op の前提(u と v の両方向で視差を取る、
#     開口マスクが (V, U) の 2-D、EPI が角度 1 軸と空間 1 軸の断面)。
#     - ``images``(2-D の list)へ潰すと「どの視点か」が消える。lf_views が
#       まさにその潰す操作で、潰した後は refocus も EPI も定義できない。
#     - ``voxel`` は 3-D 配列。次元数から違うので宣言できない。
#     - ``pointmap`` / ``normalmap`` は (H, W, 3) 固定。
#     4-D を表す既存語彙が catalog に一つも無いため新設した。
_CATALOG = {
    "synthesis": [
        ("lf_synthesize", "lightfield", [], "lightfield"),
    ],
    "decode": [
        ("lf_from_mla", "lightfield", ["image2d"], "lightfield"),
        ("lf_to_mla", "lightfield", ["lightfield"], "image2d"),
        ("lf_stats", "lightfield", ["lightfield"], "table"),
    ],
    "views": [
        ("lf_subaperture", "lightfield", ["lightfield"], "image2d"),
        ("lf_center_view", "lightfield", ["lightfield"], "image2d"),
        ("lf_views", "lightfield", ["lightfield"], "images"),
        ("lf_epi", "lightfield", ["lightfield"], "image2d"),
    ],
    "refocus": [
        ("lf_refocus", "lightfield", ["lightfield"], "image2d"),
        ("lf_focal_stack", "lightfield", ["lightfield"], "images"),
        ("lf_aperture_mask", "lightfield", [], "image2d"),
        ("lf_synthetic_aperture", "lightfield", ["lightfield"], "image2d"),
    ],
    "depth": [
        ("lf_depth_from_focus", "lightfield", ["lightfield"], "image2d"),
        ("lf_epi_slope", "lightfield", ["lightfield"], "image2d"),
        ("lf_disparity_to_depth", "lightfield", ["image2d"], "depth"),
        ("lf_all_in_focus", "lightfield", ["lightfield", "image2d"], "image2d"),
        ("lf_plenoptic_design", "lightfield", [], "table"),
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


OPSLIGHTFIELD = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSLIGHTFIELD.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics と同じ
#: 一級機構)。opsoptics では空だったが、ここでは 3 つ登録がある — いずれも
#: 「**素の返りをタプルにした方が正直**」な op で、adapter を埋めるために返り型を
#: 変えたのではなく、**返りを削るために adapter を置いている**:
#:
#:   * ``lf_synthesize``      → ``(light_field, slope_map)``。合成場のグラウンド
#:     トゥルース(層の slope 地図)を捨てると、この op の存在理由である
#:     「閉形式の答えと突き合わせる」が成立しない。
#:   * ``lf_depth_from_focus`` → ``(slope_map, sharpness)``。sharpness が
#:     信頼度そのもの(無地の画素は鮮鋭度ピークを持たず slope は無意味)。
#:     これを返さないと「無地画素に尤もらしい数値を黙って返す」op になる。
#:   * ``lf_epi_slope``        → ``(slope_map, energy)``。同上で energy が
#:     構造テンソルの分母 = 視差が測れたかどうか。
#:
#: :func:`call` は宣言どおり第 1 要素(スロープ地図 / 光場)だけを返し、
#: :func:`get` は素の関数(タプル返し)を返す。連鎖ファザーの TYPEMISS 検査は
#: :func:`call` の結果を宣言と突き合わせる。
RESULT_ADAPTERS = {
    "lf_synthesize": lambda r: r[0],
    "lf_depth_from_focus": lambda r: r[0],
    "lf_epi_slope": lambda r: r[0],
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSLIGHTFIELD[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSLIGHTFIELD[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSLIGHTFIELD[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSLIGHTFIELD.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opslightfield: {len(OPSLIGHTFIELD)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
