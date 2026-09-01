# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsgfx2d — fullseye リアルタイム 2-D グラフィックス op の統一レジストリ。

動機(2026-09-02)は著者の要望「ゲームのグラフィック位の物が描ける様な op が
あると良い」と、それを裏づける空白の実測。fullseye は **3-D レンダリング**は
既に持つ(`render3d` / `render_beauty` / `render_ao` / `render_shade` /
`render_shadow` / `render_ssaa` / `render_tonemap`)が、**画面のもう半分** ——
スプライト合成・ブレンドモード・タイルマップ・パーティクル・2-D ライティング・
ポスト処理 —— には語彙が 1 つも無かった(`alpha_composite` / `tilemap` /
`particle` / `bloom` / `vignette` / `dither` / `palette_quantize` /
`nine_slice` はいずれも repo 全体で 0 ヒット。唯一 `blend` だけが
`imagemorph.blend`(2 枚のクロスフェード)として存在したので、本族は
``blend_mode`` と名を分けた)。

**検査ライブラリがこれを欲しがる理由**は装飾ではない。`defectgen` が写真でなく
確率幾何から傷を描くのと同じ理由 —— **スプライトは真値が既知の物体**であり、
シルエットも位置も被覆率も「それを描いた数」そのものだから、スプライトで組んだ
シーンには**画素完全な正解マスクが最初から付いてくる**(後から誰かが引いた
アノテーションではない)。検出・分割・遮蔽の合成データ生成器がここで手に入る。

**この族の本当の危険は α の表現**(gfx2d.py の docstring が正典):
ストレート α と乗算済み α は同じ 4 つの数で意味が 2 つあり、取り違えても
**例外は出ず、縁に 1 画素のハローが出た絵が返る**。だから公開境界は
**ストレート α を正典**とし、算術だけを内部で乗算済みに落とす。

既存資産との棲み分け(**再実装せず、あるいは明示的に非重複**):
  * 3-D レンダリング = render3d / render_beauty / render_ao / render_shade /
    render_shadow / render_ssaa / render_tonemap。あちらは 3-D シーンから
    画像を作る。gfx2d は**既にある 2-D 画像を重ねる/加工する**だけで、
    3-D の幾何もカメラも持たない。呼びもしない。
  * 図形の線描画 = imagedraw / drawstyle。輪郭・線種・注記は向こうの担当で、
    gfx2d は 1 本も線を引かない(``sprite_synthesize`` は陰関数の被覆率で、
    線描画ではない)。
  * 2 枚の重み付き混合 = ``imagemorph.blend``。**同名を避けて
    ``blend_mode`` にした**のはこの衝突のため(署名の違う blend が 2 つある
    のは、この repo の命名テストが防いでいる型の事故そのもの)。
  * ぼかし・フィルタ = filters_* / backends_*。``bloom`` は
    ``scipy.ndimage.gaussian_filter`` を直接使う —— 既存 2-D 平滑 op は
    単チャネル・値域前提の入口を持つので、(H,W,3) を 3 回まわす配管を足すより
    直呼びのほうが層が薄い。ぼかし自体の再実装はしていない。
  * 配色 = palette。**役割名を色として受ける**入口を全 op に用意し、
    Okabe–Ito を既定にした(色を直接選ばせない)。再実装せず import。
  * 法線 = normalmap 語彙(pointmap/normalmap を産む既存 3-D 族)。
    ``normal_map_shade`` は**その語彙をそのまま食う**ので、3-D 側で作った
    法線マップが 2-D ライティングにそのまま流れる。
  * 色量子化 = ここが初出。``imgio.apply_cmap`` は LUT で**擬似カラーを着ける**
    向きで、``palette_quantize`` は**色を減らす**逆向き。重複しない。

型語彙の判断(**混ぜると例外でなくもっともらしく間違うか**が唯一の基準):

  新語彙 4 つ:
    * ``rgb`` —— (H,W,3) float [0,1] の**色**。既存 ``pointmap`` /
      ``normalmap`` は同じ (H,W,3) の述語を通るが、渡すと
      ``normal_map_shade`` は例外も NaN も出さずに**意味の無い陰影**を返す
      (XYZ を RGB と読み替える)。opsphoton が histcube を voxel から分けた
      のと同じ物差しで同じ答え。
    * ``rgba`` —— (H,W,4) **ストレート** α。
    * ``rgba_premul`` —— (H,W,4) **乗算済み** α。``rgba`` と分けたのが本族の
      中心判断。形も dtype も値域も同じで、取り違えは静かにハローになる。
      ただし述語には歯止めがある: 乗算済みは構成上 ``colour <= alpha`` を
      満たすので、ストレートを渡すと**色が被覆を超える画素があるところだけ**
      fail-closed になる。暗いスプライトはすり抜ける —— 網であって証明ではない
      ことを ``_require_rgba_premul`` の docstring に明記した。
      死んだ語彙ではない: 入口 ``premultiply``、自己ループ
      ``alpha_composite_premul``、出口 ``unpremultiply`` が揃っている。
    * ``sprites`` —— 同形 rgba の list。``table``(list|dict)に相乗りさせると
      dict が通ってしまい、``tilemap_render`` は 4 チャネル形状を要求するので
      そこで生 TypeError になる。入口 ``sprite_sheet_slice``、消費
      ``tilemap_render`` の両方がある。
    * ``lut`` —— (n,n,n,3) の 3-D カラー LUT。既存 ``voxel``(ndim==3)は
      通らない(ndim==4)し、``lightfield``(ndim==4)は通ってしまうが、
      角度 2 軸 × 空間 2 軸を色 LUT として引くと**黙って別の色**が出る。
      入口 ``color_lut``、消費 ``color_grade``。

  既存語彙をそのまま使ったもの(新語を作らなかった判断):
    * ``image2d`` —— ``shadow_cast_2d`` の可視率マップ (H,W)。閾値・
      morphology・blob が意味を保ったまま掛かる(「どこが影か」を二値化して
      領域にする、が実際の使い道)。
    * ``normalmap`` —— ``normal_map_decode`` の返り。既存 3-D 族と同じ
      (H,W,3) の単位ベクトルで、分ける理由が無い(むしろ繋ぐのが目的)。
    * ``table`` —— パーティクル状態 dict。TYPE_CHECKS の table は list|dict。

使い方:
    import opsgfx2d
    opsgfx2d.list_ops("composite")
    s = opsgfx2d.get("sprite_synthesize")("disc", 32, "emphasis")
    out = opsgfx2d.get("sprite_blit")(dst, s, 10, 20, anchor="center")
"""
import gfx2d

_MOD = {"gfx2d": gfx2d}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "colorspace": [
        ("srgb_to_linear", "gfx2d", ["rgb"], "rgb"),
        ("linear_to_srgb", "gfx2d", ["rgb"], "rgb"),
    ],
    "composite": [
        ("premultiply", "gfx2d", ["rgba"], "rgba_premul"),
        ("unpremultiply", "gfx2d", ["rgba_premul"], "rgba"),
        ("alpha_composite", "gfx2d", ["rgba", "rgba"], "rgba"),
        ("alpha_composite_premul", "gfx2d", ["rgba_premul", "rgba_premul"], "rgba_premul"),
        ("blend_mode", "gfx2d", ["rgb", "rgb"], "rgb"),
        ("layer_stack", "gfx2d", ["table"], "rgba"),
    ],
    "sprite": [
        ("sprite_synthesize", "gfx2d", [], "rgba"),
        ("sprite_blit", "gfx2d", ["rgba", "rgba"], "rgba"),
        ("sprite_transform", "gfx2d", ["rgba"], "rgba"),
        ("sprite_sheet_slice", "gfx2d", ["rgba"], "sprites"),
        ("nine_slice", "gfx2d", ["rgba"], "rgba"),
    ],
    "tile": [
        ("tilemap_render", "gfx2d", ["sprites"], "rgba"),
        ("parallax_layers", "gfx2d", ["sprites"], "rgba"),
    ],
    "particle": [
        ("particle_emit", "gfx2d", [], "table"),
        ("particle_step", "gfx2d", ["table"], "table"),
        ("particle_render", "gfx2d", ["table"], "rgba"),
    ],
    "light": [
        ("radial_light", "gfx2d", [], "rgb"),
        ("light_mask", "gfx2d", ["rgb", "rgb"], "rgb"),
        ("normal_map_decode", "gfx2d", ["rgb"], "normalmap"),
        ("normal_map_shade", "gfx2d", ["normalmap"], "rgb"),
        ("shadow_cast_2d", "gfx2d", ["image2d"], "image2d"),
    ],
    "post": [
        ("bloom", "gfx2d", ["rgb"], "rgb"),
        ("vignette", "gfx2d", ["rgb"], "rgb"),
        ("chromatic_aberration", "gfx2d", ["rgb"], "rgb"),
        ("film_grain", "gfx2d", ["rgb"], "rgb"),
        ("color_lut", "gfx2d", [], "lut"),
        ("color_grade", "gfx2d", ["rgb", "lut"], "rgb"),
        ("dither", "gfx2d", ["image2d"], "image2d"),
        ("palette_quantize", "gfx2d", ["rgb"], "rgb"),
    ],
    "camera": [
        ("viewport", "gfx2d", ["rgb"], "rgb"),
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


OPSGFX2D = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSGFX2D.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton / opsmotionmag と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。32 op すべてが宣言型そのもの(ndarray / dict /
#: list)を素で返す設計にしてある。空にしておくと :func:`call` は :func:`get`
#: と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りをそのまま**宣言と
#: 突き合わせる = 検証が最も厳しい。
#:
#: 埋めたくなる誘惑を 1 つ明記しておく: ``viewport`` は rgb でも rgba でも
#: 受けて**入力と同じチャネル数**を返す。宣言は片方(rgb)しか書けないので、
#: rgba を渡したときの返りは宣言と食い違う。ここに adapter を書いて rgb へ
#: 落とすと**α を黙って捨てる**ことになるので書かない。rgba を切りたい呼び側は
#: 4 チャネルのまま受け取り、必要なら自分で落とす。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSGFX2D[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSGFX2D[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSGFX2D[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSGFX2D.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsgfx2d: {len(OPSGFX2D)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
