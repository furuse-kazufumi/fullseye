# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsastrostack — fullseye 天体写真スタッキング op の統一レジストリ。

動機(2026-09-02)は fullseye 自身の空白の実測。op カタログ全文に対して
``lucky`` / ``drizzle`` / ``sigma_clip`` / ``cosmic_ray`` / ``astrometr`` を
grep すると **op としては 1 件もヒットしなかった**(散文中の "lucky" が
9 件当たるだけで、そのすべてが「たまたま当たった seed」という別の意味)。
一方で ``photoncount``(光子計数)、``optics``(PSF / MTF)、
``volrestore.vol_richardson_lucy``、``features``(キーポイント検出とマッチング)、
``mosaic``(2-D 点対応 RANSAC)、``fit_transform``(Umeyama)は既にある。
つまり「同じ空を何十枚も撮って重ねる」という、**部品は全部あるのに一度も
組み上げられていなかった**領域がまるごと空白だった。
本レジストリはその台帳(astrostack.py、14 op / 6 カテゴリ)。

この族を選んだ理由は絵の派手さではなく **検算できること**:
drizzle は総フラックスを厳密に保存し(実測 相対誤差 0.0)、κ-σ 合成の破綻点は
中央値と同じ 50 %(実測 45 % で誤差 +0.007、50 % で +250.0)、合成星野の
既知フラックスに対する開口測光は開口を広げれば厳密に一致する(実測 -0.0000 %)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない):Fruchter & Hook, PASP 114, 144 (2002)
(drizzle)/ van Dokkum, PASP 113, 1420 (2001)(ラプラシアンによる宇宙線検出)/
Moffat, A&A 3, 455 (1969)(大気の星像プロファイル)/ Law, Mackay & Baldwin,
A&A 446, 739 (2006)(lucky imaging と選別基準)/ Merline & Howell,
Exp. Astron. 6, 163 (1995)(CCD の S/N 方程式)/ Croux & Rousseeuw,
Computational Statistics (1992)(MAD の小標本補正)/ Pech-Pacheco et al.,
ICPR 2000(ラプラシアンの分散による合焦指標)。

既存資産との棲み分け(**再実装せず import して合成**):
  * ショットノイズ = ``photoncount.photon_sample``。``synth_starfield`` は
    ``photons_per_unit=1.0`` で呼ぶだけで、Poisson 標本化のコードを持たない。
  * 読み出しノイズ = カウント領域の加法ガウス。``backends_aug.aug_read_noise``
    は [0,1] に clip するのでカウント領域では使えず(電子数 1500 の星が 1.0 に
    潰れる)、``photoncount.anscombe_transform`` の一般化形が受け取る
    ``gain`` / ``read_sigma`` と**同じ意味**の量だけをここが持つ。
  * 宇宙線の位置と形 = ``defectgen.defect_pits`` の一様点過程。
  * 回折 PSF = ``optics.airy_pattern``。地上の星像を支配するのは大気なので
    ``synth_starfield`` の既定は Moffat / Gaussian だが、回折限界の兄弟は
    あちらにあり複製しない。PSF → MTF も ``optics.psf_to_mtf`` へ直接渡せる。
  * 2-D 点対応 RANSAC = ``mosaic.proj_match_points_ransac``、変換の当てはめ =
    ``fit_transform.vector_to_similarity`` / ``vector_to_rigid`` /
    ``vector_to_hom_mat2d``。``frame_align`` はこの 2 つを呼ぶだけで、
    RANSAC ループも Umeyama も書いていない。
  * 記述子マッチング = ``features.match_keypoints``。**星野では使わない**
    (実測: 40 星のフレーム対で対応 4 件、うち真値から 1 px 以内は 0 件)。
    星は互いに見分けが付かないので、記述子ではなく配置の幾何(オフセット投票)
    を使う。これは「使えるのに使っていない」ではなく「使うと間違う」。
  * Poisson 逆畳み込み = ``volrestore.vol_richardson_lucy``。合成後の
    デコンボリューションはあちらの仕事で、ここでは一切ぼかしを戻さない。

使い方:
    import opsastrostack
    opsastrostack.list_ops("stack")
    opsastrostack.call("sigma_clip_stack", frames, mode="sigma_clip")
"""
import astrostack

_MOD = {"astrostack": astrostack}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#
# --------------------------------------------------------------------------
# 新語彙は 1 つも足していない。その判断の記録。
# --------------------------------------------------------------------------
# 基準は opsphoton / opsoptics と同じ一つだけ ——
# 「**既存語彙で宣言すると型レベルの嘘になるか**」、言い換えると
# 「混ぜたときに例外ではなく、もっともらしく間違った数値が出るか」。
# photon 族は counts / countrate / histcube の 3 つを足したが、こちらは
# 同じ物差しを当てて **全部「分けない」に倒れた**。以下は当てた結果:
#
#   * images —— フレーム列。当初 ``frames`` という新語を検討したが、却下した。
#     ``images`` は「2-D 配列の list / tuple」であり、astrostack が食う
#     ものと**寸分違わない**。そして混ぜたときに嘘にならない:
#       - 任意の画像列を ``sigma_clip_stack`` に渡した結果は、天体でなくとも
#         「その列のロバスト平均」であって、定義どおりの正しい答えである。
#       - ``drizzle_resample`` の面積保存は入力が何であっても成り立つ
#         (面積比で撒くという操作に天体の仮定が無い)。
#       - ``lucky_select`` の点は「ピーク / 総フラックス × 真円度」で、
#         点像を含まない画像では星が 0 個になり **score = 0.0** が返る。
#         これは「もっともらしく間違った点」ではなく「選ぶ理由が無い」という
#         正しい答え。
#       - 形が揃っていなければ ``_require_frames`` が op 名つきで
#         ValueError にする(実測: "frames[1] has shape (8, 8) but frames[0]
#         has (16, 16) — align them first")。
#     ★ 代わりに **生の (N,H,W) ndarray を明示的に拒否**した。3-D 配列は
#     video (T,H,W) / voxel (D,H,W) / histcube (H,W,T) / zscan のどれもが
#     同じ構造検査を通り、取り違えても例外にならず「もっともらしく間違った
#     合成結果」が返る —— photon 族が histcube を voxel から分けたのと
#     **まったく同じ危険**である。ただしここでは型を増やすのではなく
#     「list であること」を要求することで同じ防御を得た。list(volume) と
#     書いた時点で、呼ぶ側が「先頭軸はフレーム軸だ」と宣言したことになる。
#
#   * image2d —— 合成結果、drizzle の出力、単一フレーム。どれも 2-D の
#     float64 で、既存の 2-D op(フィルタ・閾値・morphology・psf_to_mtf)が
#     意味を保ったまま使える。**非負でもない**(κ-σ 合成の残差やスプライン
#     補間の負の縁が出る)ので counts を名乗るのは逆に嘘になる。
#
#   * keypoints —— ``star_detect`` の返りは (N, 2) の (row, col)。
#     TYPE_CHECKS の keypoints は「(N,3) または任意の 2-D 配列」なので
#     そのまま該当し、``psf_fit`` / ``aperture_photometry`` が食う。
#     ★ ここは pairs ではない: pairs の正典は reprconv 側の 6 op が決めた
#     「(x, y) の対」で、こちらは画像座標の (row, col) であり
#     fit_transform / mosaic と同じ規約。混ぜると行と列が入れ替わる
#     (features.match_keypoints が (x,y) を返すのに fit_transform が
#     (row,col) を要求する、というこの repo 既知の罠と同じ形)。
#     keypoints を名乗れば、少なくとも「画像上の点」という約束は共有される。
#
#   * indices —— ``lucky_select`` が返す採用フレームの添字(1-D int)。
#     既存語彙そのもの。``[frames[i] for i in idx]`` で images に戻る。
#
#   * measurement —— ``noise_sigma`` は実スカラ 1 つ。
#
#   * matrix —— ``frame_align`` の (3,3) 同次変換。transforms / fit_transform /
#     mosaic が扱っているのと同じ物で、専用語を作る理由が無い。
#
#   * table —— dict / list of dict(品質、PSF 当てはめ、測光)。
#     TYPE_CHECKS の table は list|dict なのでどちらも該当。
#
# 分けなかったことの代償(honest): ``images`` プールに天体でない画像列が
# 入ると、``frame_align`` は星が見つからず ValueError で止まる。これは
# fail-closed なので「発見ゼロ」ではなく「到達したが正しく拒否した」だが、
# 連鎖ファザーから見ると align 系 2 op が CONTRACT にしかならない可能性がある。
# photon 族が counts を分けた理由(7/17 が一度も実行されない)と同じ症状が
# 出うるので、**もし実測でそうなったら**、そのときは「点像を含む画像列」を
# 別プールにする判断が正当化される —— 先回りして型を増やすことはしない
# (型は「混ぜると嘘になる」証拠が出てから増やす、が本 repo の順序)。
_CATALOG = {
    "synth": [
        ("synth_starfield", "astrostack", [], "image2d"),
        ("synth_frame_series", "astrostack", [], "images"),
    ],
    "quality": [
        ("frame_quality", "astrostack", ["image2d"], "table"),
        ("lucky_select", "astrostack", ["images"], "indices"),
        ("noise_sigma", "astrostack", ["image2d"], "measurement"),
    ],
    "stack": [
        ("sigma_clip_stack", "astrostack", ["images"], "image2d"),
        ("drizzle_resample", "astrostack", ["images"], "image2d"),
    ],
    "cosmic": [
        ("cosmic_ray_reject", "astrostack", ["image2d"], "image2d"),
        ("cosmic_ray_reject_stack", "astrostack", ["images"], "images"),
    ],
    "photometry": [
        ("star_detect", "astrostack", ["image2d"], "keypoints"),
        ("psf_fit", "astrostack", ["image2d", "keypoints"], "table"),
        ("aperture_photometry", "astrostack", ["image2d", "keypoints"], "table"),
    ],
    "align": [
        ("frame_align", "astrostack", ["image2d", "image2d"], "matrix"),
        ("align_frames", "astrostack", ["images"], "images"),
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


OPSASTROSTACK = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSASTROSTACK.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opscadmap と同じ一級機構)。
#:
#: **この族は 7 op が 2 要素タプルを返す。** opsphoton は
#: 「タプル返しの op を将来足すならここに登録すること」と書いて空にしていたが、
#: astrostack はまさにそれで、``defectgen`` の全 op が ``(image, mask)`` を
#: 返すのと同じ設計を採った —— 採否マスク・重みマップ・真値は
#: **返り値の一部であって、旗で有無が切り替わるものではない**(``return_mask``
#: のような旗で返り型が変わる op は、台帳がどちらの姿を宣言しても嘘になる)。
#:
#: adapter は先頭要素を取り出すだけで、**2 つ目を捨てているのではなく、
#: 台帳が宣言しているのは 1 つ目の型だ**と言っている。生の返りが欲しければ
#: :func:`get` を使う(こちらが本体で、:func:`call` が台帳向けの姿)。
_first = (lambda r: r[0])
RESULT_ADAPTERS = {
    "synth_starfield": _first,          # (frame, truth)          -> image2d
    "synth_frame_series": _first,       # (frames, truth)         -> images
    "sigma_clip_stack": _first,         # (stack, accepted)       -> image2d
    "drizzle_resample": _first,         # (sci, wht)              -> image2d
    "cosmic_ray_reject": _first,        # (cleaned, mask)         -> image2d
    "cosmic_ray_reject_stack": _first,  # (cleaned, masks)        -> images
    "frame_align": _first,              # (matrix, info)          -> matrix
    "align_frames": _first,             # (aligned, matrices)     -> images
    # lucky_select は (indices, scores) を返すが、宣言は indices。
    "lucky_select": _first,
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSASTROSTACK[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSASTROSTACK[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSASTROSTACK[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSASTROSTACK.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsastrostack: %d ops / %d categories"
          % (len(OPSASTROSTACK), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-11s %s" % (cat, ", ".join(list_ops(cat))))
