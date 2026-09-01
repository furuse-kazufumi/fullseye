# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opstomography — fullseye 断層撮影(平行ビーム CT)op の統一レジストリ。

動機は fullseye 自身の空白の実測(2026-09-02)。CT ボリュームを**扱う** op は
多数あるのに(`vol_window_level` / `vol_label` / `vol_region_props` /
`marching_cubes` / `vol_boundary_points` / `voxelize` …)、**投影から作る**側が
1 つも無かった。`radon` / `sinogram` / `iradon` / `fbp` / `art` / `sirt` に該当
する関数はゼロ(`backproject` は別物 = 深度マップで画素を 3-D に持ち上げる
カメラ用の関数で、こちらは積分変換)。本レジストリはその欠けていた側の台帳
(tomography.py、17 op / 6 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): Radon 1917(変換と反転)/ Kak & Slaney 1988
(FBP・フィルタ・視点数の標本化則・偽像機構)/ Shepp & Logan 1974(ファントム)
/ Andersen & Kak 1984(SART)/ Kalender et al. 1987(LI-MAR)/ Donath et al.
2006(回転中心の重心恒等式)/ Winkelmann et al. 2007(黄金角)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 再構成した**後**は既存の 3-D 族がそのまま使える。`fbp_volume` が素の
    voxel を返すのはそのためで、`examples/tomography_reconstruct.py` は
    投影 → 再構成 → 窓 → 分離 → ボクセル → メッシュ → 体積 mm³ まで既存 op
    だけで閉じる。本モジュールは 3-D 側を 1 つも再実装していない。
  * 1-D フィルタ・FFT は dsp / filters_freq。ここの ramp フィルタは汎用
    フィルタではないので公開もしない。
  * **進化レジストリの `tm_` クラスタ(backends_tomo)とは別物**。あちらは
    `fn(v, a, b)` の画像→画像 op(遺伝的パイプライン探索用、出力を入力の
    HxW に嵌め戻す、契約として fail-**soft**、scikit-image があれば使う)。
    こちらは型つき・fail-**closed**・numpy+scipy のみで、facade が公開する
    ライブラリ。コードの共有はゼロ。名前が似ているだけ。

使い方:
    import opstomography
    opstomography.list_ops("reconstruct")
    opstomography.get("filtered_backprojection")(sino, angles)
"""
import tomography

_MOD = {"tomography": tomography}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / voxel / measurement / signal / table
#   新語彙: sinogram / sinostack
#
# --------------------------------------------------------------------------
# 既存語彙をそのまま使った判断(新語を作らなかったもの)
# --------------------------------------------------------------------------
#   * image2d — ellipse_phantom の出力と、3 つの再構成 op の出力。**再構成
#     結果はただの画像**であって断層専用の何かではない。閾値・morphology・
#     blob・計測がそのまま意味を持つ(現場の手順そのもの)ので、ここで新語を
#     作るのは語彙を分断するだけ。ellipse_phantom は image2d プールへ「既知の
#     真値を持つ画像」を注ぐ入口にもなる。
#   * voxel — fbp_volume の出力。同上を 3-D でやる。既存の vol_* / marching_cubes
#     が全部そのまま噛む。**これが「CT からボクセル化」の接続点**。
#   * measurement — sinogram_center_of_rotation は検出器画素単位の実スカラ 1 つ。
#   * signal — projection_angles の出力(度の 1-D 実配列)。角度列は
#     「単調な実数列」以上の約束を持たないので、既存の広い sort へ**戻す**のが
#     正しい。専用語を作ると産むだけ食わない袋小路になる(consumer 側は
#     angles_deg を**引数**で受けるので型プールを必要としない)。
#   * table — sinogram_design の返りは dict(csi_design / fmcw_design /
#     lf_plenoptic_design と同じ「買う前に決まる限界」役)。
#
# --------------------------------------------------------------------------
# 新語彙 2 つと、その理由(どちらも実測に基づく。基準は既存台帳と同じ
# 「**混ぜたときに例外が出るなら同じ型でよい。もっともらしく間違った数字が
#   返るなら分ける**」)
# --------------------------------------------------------------------------
#
#   * sinogram — (角度, 検出器) の 2-D。既存 `image2d` と**構造は完全に同じ**
#     (2-D float)なので、相乗りさせるとどうなるかを実際に両方向で測った。
#
#     (a) sinogram -> image2d 側は **9 op すべてが黙って通る**(実測)。
#         `otsu` / `gauss_filter` / `sobel_amp` / `mean_image` / `threshold` /
#         `dyn_threshold` / `fft_image` / `distance_transform` / `skeleton` の
#         どれも例外も NaN も出さず、有限でもっともらしい「二値化結果」
#         「エッジ」「距離場」「骨格」を返す。サイノグラムの骨格に意味は無い。
#     (b) image2d -> sinogram 側も **6 op 中 5 op が黙って通る**(実測)。
#         ただの写真を filtered_backprojection に渡すと (89,89) の有限な
#         「断層像」が返り、backproject_sinogram / ring_artifact_remove /
#         beam_hardening_apply / metal_trace_interpolate も同様。
#         唯一 sinogram_center_of_rotation だけが拒否したが、それは型を
#         見抜いたからではなく**たまたま暗い行があって質量が 0 だった**から
#         で、実行時チェックには頼れないことの証拠のほうである。
#     (c) さらに悪いのが**転置**。正方サイノグラム(183x183)とその転置を
#         FBP に食わせると、どちらも有限でもっともらしい像を返し、両者は
#         nRMS 0.175 だけ違う。例外は出ない。転置したサイノグラムは
#         「別のスキャンの正当なサイノグラム」なので、**構造検査で見抜くことは
#         原理的にできない**。だから型で守るしかない。
#     sinogram は 12 op(産む 3 + 食う 9)で、入口 = `radon_transform`
#     (image2d -> sinogram) と `ellipse_sinogram` ([] -> sinogram、閉形式の
#     真値をプールに注ぐ)、出口 = 3 つの再構成 op (-> image2d) と
#     `sinogram_center_of_rotation` (-> measurement)。偽像の 5 op は
#     sinogram -> sinogram で、プールの中を回して敵対入力を作る。袋小路なし。
#
#   * sinostack — (スライス, 角度, 検出器) の 3-D。既存 voxel / video / zscan /
#     labels / sdf / histcube と**述語を相互に満たす**(実測: 3 つの述語すべてに
#     stack も volume も True)。そして両方向とも黙って通る:
#       - stack -> 3-D 側: `vol_window_level` は (6,32,47) の有限な結果を返し、
#         `vol_boundary_points` は 2076 点の「境界点群」を返す(実測)。
#         角度軸を z 軸として読んだ、意味の無い有限値である。
#       - 逆向き: 本物のボリュームを `fbp_volume` に渡すと (6,21,21) の有限な
#         「再構成ボリューム」が返る(実測)。z を角度として読んでいる。
#     入口 = `radon_volume` (voxel -> sinostack)、出口 = `fbp_volume`
#     (-> voxel)。voxel プールが既に在るので入口から到達でき、出口が voxel へ
#     戻るので既存の 3-D 語彙へ合流する(zscan / histcube と同じ形)。
_CATALOG = {
    "layout": [
        ("projection_angles", "tomography", [], "signal"),
        ("sinogram_design", "tomography", [], "table"),
    ],
    "forward": [
        ("ellipse_phantom", "tomography", [], "image2d"),
        ("ellipse_sinogram", "tomography", [], "sinogram"),
        ("radon_transform", "tomography", ["image2d"], "sinogram"),
    ],
    "reconstruct": [
        ("backproject_sinogram", "tomography", ["sinogram"], "image2d"),
        ("filtered_backprojection", "tomography", ["sinogram"], "image2d"),
        ("sart_reconstruct", "tomography", ["sinogram"], "image2d"),
    ],
    "artifact": [
        ("beam_hardening_apply", "tomography", ["sinogram"], "sinogram"),
        ("beam_hardening_correct", "tomography", ["sinogram"], "sinogram"),
        ("ring_artifact_apply", "tomography", ["sinogram"], "sinogram"),
        ("ring_artifact_remove", "tomography", ["sinogram"], "sinogram"),
        ("metal_trace_interpolate", "tomography", ["sinogram"], "sinogram"),
    ],
    "geometry": [
        ("sinogram_center_of_rotation", "tomography", ["sinogram"], "measurement"),
        ("sinogram_center_shift", "tomography", ["sinogram"], "sinogram"),
    ],
    "volume": [
        ("radon_volume", "tomography", ["voxel"], "sinostack"),
        ("fbp_volume", "tomography", ["sinostack"], "voxel"),
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


OPSTOMOGRAPHY = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSTOMOGRAPHY.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton / opsinterferometry と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。tomography の 17 op はすべて宣言型そのもの
#: (ndarray / float / dict)を素で返す設計にしてある。とくに
#: ``sinogram_center_of_rotation`` は「(オフセット, 残差, 信頼度) タプル」では
#: なく **float だけ**を返す — adapter を要らなくするためではなく、1 op = 1 量
#: のほうが連鎖の型検査が厳しくなるからである。空にしておくと :func:`call` は
#: :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りを
#: そのまま**宣言と突き合わせる = 検証が最も厳しい。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSTOMOGRAPHY[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSTOMOGRAPHY[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSTOMOGRAPHY[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSTOMOGRAPHY.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opstomography: {len(OPSTOMOGRAPHY)} ops / "
          f"{len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
