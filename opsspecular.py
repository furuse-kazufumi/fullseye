# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsspecular — 鏡面反射の分離と頑健フォトメトリックステレオの統一レジストリ。

`photometric.py` の docstring が自分で書いている: 線形最小二乗が厳密なのは
「Lambertian + 既知光源 + 影なし」の場合だけで、**影とスペキュラは線形性を破る**
ので頑健版が別途要る、と。本族はその「別途」であり、加えて **形状復元にかける前に
ハイライトを取り除く** 2 つの経路(色・偏光)を第一級の op にしたもの。
13 op / 4 カテゴリ(numpy のみ、実体は `specularity.py`)。

すべて閉形式なので、真値を持った合成データで機械精度まで検証できる — それが
本 repo で op を足してよい条件そのもの。

既存資産との棲み分け(**再実装せず import して合成**):
  * Lambertian 順方向レンダと法線積分 = photometric(``render_lambertian`` /
    ``synthesize_ps_images`` / ``integrate_gradients`` = Frankot-Chellappa /
    ``angular_error_deg``)。``dichromatic_render`` は body 項に
    ``render_lambertian`` を **呼び**、``photometric_stereo_robust`` は
    ``method="lstsq"`` で ``photometric_stereo`` を **呼ぶ** —
    「素の版がここで壊れる」を主張でなく **実測** にするため。
  * 偏光代数 = optics(``jones_*`` / ``mueller_*`` / ``stokes_analyze``)。
    ``polarization_stokes`` が返すのは ``stokes_analyze`` がそのまま食う
    Stokes ベクトルで、偏光度・方位・楕円率は向こうが答える。
  * 光線と面の相互作用・厳密 Fresnel = match3d(``reflect`` / ``refract`` /
    ``fresnel_reflectance`` / ``normal_from_reflection`` = デフレクトメトリ)。
    ``brdf_microfacet`` は Schlick 近似を **名指しで** 使う(それが microfacet
    文献の指定)。厳密な Fresnel 曲線が要るならそちら。
  * 色空間変換・ホワイトバランス・デモザイク = color backends。本族は
    **線形 RGB を受け取る前提** で、それを各 docstring に明記している。

使い方:
    import opsspecular
    opsspecular.list_ops("dichromatic")
    opsspecular.call("specular_diffuse_split", img)   # 宣言型(diffuse)だけ返る
    opsspecular.get("specular_diffuse_split")(img)    # 素の (diffuse, specular)
"""
import specularity

_MOD = {"specularity": specularity}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / images / normalmap / vector / labels / stokes
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * image2d  — スカラ地図(鏡面係数 m_s、残差、拡散/鏡面の輻度、偏光度)。
#     まさに 2-D の実数場で、threshold / morph / measure にそのまま流せる。
#     ここで専用語を作ると 2-D 生態系との接続を切るだけで得が無い。
#   * images   — 偏光板を回して撮った (N,H,W) と、光源を切り替えて撮った
#     (N,H,W)。どちらも「同じ画角の N 枚」という既存の意味そのもので、
#     N の意味(角度か光源か)は **引数**(angles_deg / lights)が持つ。
#   * normalmap — フォトメトリックステレオの返す法線場 (H,W,3) は photometric
#     と同じ規約(+z がカメラ向き)。既存語をそのまま使うので、法線を食う
#     既存 op(勾配化・積分・可視化)へ無改造で流れる。
#   * vector   — 光源色は (3,) の実ベクトル。unit 化して返すので `vector` の
#     TYPE_CHECKS(shape == (3,))にそのまま合う。
#   * labels   — 材質の (H,W) 整数地図。既存のセグメンテーション出力がそのまま
#     材質分割として使える(=この op の入口が既存生態系の中にある)。
#   * stokes   — `polarization_stokes` の返り。**既存の狭い語彙へ橋を架ける側**:
#     これまで stokes を産むのは optics の `stokes_from_jones` /
#     `mueller_apply` だけで、いずれも代数の内側だった。実測(偏光板を回して
#     撮った画像)から stokes を産む入口はここが初めてになる。
#
# 新語彙 1 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsmath の cpoints / cscalar、opsoptics の jones / stokes、
# opsphoton の histcube):
#   * rgbimage — 線形 RGB 画像 (H,W,3)。構造は pointmap / normalmap と
#     **完全に同じ** (ndim==3, shape[2]==3) だが、意味が違う。二色性反射モデルは
#     3 成分を「色」として扱い、光源色方向への射影で分離する — そこへ計量 XYZ の
#     pointmap や単位法線の normalmap を渡しても **例外は出ない**。出るのは
#     「もっともらしく間違った分離結果」で、これは histcube を voxel から分けた
#     判断(時間軸が最後、渡すと黙って間違った深度)と同じクラスの問題。
#     image2d(2-D)は形からして不可。
#
# **狭い sort にならないための配線**(型を分けると安全になる代わりに、誰も産まない
# 型は永久に到達不能な死んだ語彙になる — 実測済みの教訓)。rgbimage は
# 入口 1・内部 2・出口 2 を持たせてある:
#   入口: dichromatic_render (normalmap -> rgbimage)。既存の normalmap プールから
#         橋が架かるので、新語彙は最初から到達可能。
#   内部: specular_free_transform (rgbimage -> rgbimage)、
#         specular_diffuse_split (rgbimage -> rgbimage)。
#   出口: specular_coefficient_map (rgbimage -> image2d = 最大のプールへ戻る)、
#         illuminant_from_dichromatic_planes (rgbimage + labels -> vector)。
_CATALOG = {
    "dichromatic": [
        ("specular_diffuse_split", "specularity", ["rgbimage"], "rgbimage"),
        ("specular_coefficient_map", "specularity", ["rgbimage"], "image2d"),
        ("specular_free_transform", "specularity", ["rgbimage"], "rgbimage"),
        ("illuminant_from_dichromatic_planes", "specularity",
         ["rgbimage", "labels"], "vector"),
    ],
    "reflectance": [
        ("brdf_blinn_phong", "specularity", ["normalmap"], "image2d"),
        ("brdf_microfacet", "specularity", ["normalmap"], "image2d"),
        ("dichromatic_render", "specularity", ["normalmap"], "rgbimage"),
    ],
    "photometric": [
        ("photometric_stereo_robust", "specularity", ["images"], "normalmap"),
        ("photometric_residual", "specularity", ["images"], "image2d"),
    ],
    "polarization": [
        ("polarization_render", "specularity", ["image2d", "image2d"], "images"),
        ("polarization_separate", "specularity", ["images"], "image2d"),
        ("polarization_dolp_map", "specularity", ["images"], "image2d"),
        ("polarization_stokes", "specularity", ["images"], "stokes"),
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


OPSSPECULAR = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSPECULAR.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opslightfield と同じ一級機構)。opsoptics では空だったが、ここには 3 つある —
#: いずれも **素の返りをタプルにした方が正直** な op で、adapter を埋めるために
#: 返り型を変えたのではなく、**返りを削るために adapter を置いている**:
#:
#:   * ``specular_diffuse_split``     → ``(diffuse, specular)``。捨てた方が
#:     常に ``image - もう一方`` で復元できるが、**鏡面成分こそがこの op の
#:     存在理由**(光沢面の欠陥検出はそれを見る)なので素の返りからは外さない。
#:   * ``photometric_stereo_robust``  → ``(normals, albedo, inliers)``。
#:     ``inliers`` は「どの光源をその画素で信じたか」で、**3 枚しか残らなかった
#:     画素**を見分ける唯一の手段。これを返さないと「最小構成の 3 枚で出した
#:     法線」と「8 枚の合意で出した法線」が区別できず、同じ確信度の顔をする。
#:   * ``polarization_separate``      → ``(diffuse, specular)``。同上。
#:
#: :func:`call` は宣言どおり第 1 要素だけを返し、:func:`get` は素の関数を返す。
#: 連鎖ファザーの TYPEMISS 検査は :func:`call` の結果を宣言と突き合わせる。
RESULT_ADAPTERS = {
    "specular_diffuse_split": lambda r: r[0],
    "photometric_stereo_robust": lambda r: r[0],
    "polarization_separate": lambda r: r[0],
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSSPECULAR[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSSPECULAR[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSPECULAR[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSSPECULAR.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsspecular: {len(OPSSPECULAR)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
