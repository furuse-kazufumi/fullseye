# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Entry bridges — 1 枚の画像から新設 sort を**作る**入口 op(category ``bridge``)。

**なぜ要るか(実測 2026-09-06)**: op ごとの「入力 → 出力」の図と Studio で走る
``sample:`` パイプラインは、**画像から型が届く op** にしか作れなかった。
2-D レジストリ 885 op のうち **161 op**(points 53 / signal 26 / video 16 /
volume 14 / qimage 11 / cimage 9 / counts 8 / lightfield 8 / rgbimage 6 /
beatcube 4 / matrix 4 / keypoints 2)は、その sort を画像から作る登録 op が
無かったので、ヘルプに図も実行例も付けられず「*図なし: 型が届かない*」と
書くしかなかった。

**なぜ typed bridge(``backends_typed``)に無かったか**: 進化の ``ops._candidates``
は ``in_sort`` で候補を絞り、ゲノムは **候補リストの長さ** で op を選ぶ
(``docs/WAVE0_STABLE_SLOTS.md``)。``in_sort=image`` の op を 1 本足すだけで
image の候補リストが伸び、既存の champion が黙って別の op に写ってしまう。
だから typed bridge は「消費側(新設 sort を入力に取る op)」だけを既定で
登録し、入口 op は ``IMGEVOLVE_WIDE_VOCAB=1`` の opt-in に隔離していた。

**本モジュールの解**: 入口 op を **category ``bridge``** で ``REGISTRY`` に載せ、
``ops._candidates`` が **この category を候補から除く**。これで

* 名前で引く経路(``fullseye.apply(img, "img_to_points")`` / Studio の
  プログラム / ``tools/gen_op_figures.py`` / 索引・ノート・ヘルプ)には見える
* 進化のゲノム → op の写像は **1 ビットも変わらない**(候補リスト不変。
  ``tests/test_wave0.py`` の pin と ``tests/test_backends_bridge.py`` が固定)

**設計の規律**:

* どの op も ``fn(v, a, b)``、``v`` は ``[0,1]`` の 2-D float 画像、``a, b ∈ [0,1]``。
  ノブが内部で何に写るかは各 docstring に **式で** 書く(使わないなら明記)。
* **決定的**(乱数は固定 seed)。同じ入力・同じノブなら 2 回の呼び出しがビット一致。
* 入口 op は「画像を、その sort の *意味のある* 値として読む」変換であって、
  形だけ合わせるキャストではない(``img_to_matrix`` だけは純粋なキャストで、
  そう明記してある)。合成データの作法は各 sort の既存の合成 op
  (``lf_synthesize`` / ``fmcw_beat_simulate`` / ``tcspc_simulate``)に合わせ、
  台帳に同等の前方モデルがあるものはそれを呼ぶ(``fmcw_beat_simulate``)。
* 出口の形は ``backends_typed._SHAPE_OK`` と同じ契約(points=(N,3)、
  keypoints=(N,2)、signal=1-D、cimage=complex 2-D、rgbimage=(H,W,3)、
  volume=3-D、lightfield=(V,U,H,W)、beatcube=(A,C,S) complex)。
* **fail-soft は backend 共通の ``backend_safe.guard``** に任せる(台帳に記録され、
  ``on_error="raise"`` で伝播する)。この層で握り潰さない。

**正直な限界**: ``points`` sort には列の規約が 2 つ混在している —— カメラ系の
``(x, y, z)``(``camera.depth_to_points``)と ``reprconv`` の ``(z, y, x)``。
本モジュールは **``(x, y, z)`` = (列, 行, 高さ)** を採り、docstring にそう書く。
規約の統一は別件(``docs/KNOWN_ISSUES.md``)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from backend_safe import guard

#: 図・サンプルの前提と同じく「1 枚の画像」から作る合成の既定寸法。
VIDEO_FRAMES = 8          # img_to_video のフレーム数
LF_ANGULAR = (5, 5)       # img_to_lightfield の角度サンプル (V, U)
BEAT_SHAPE = (4, 32, 64)  # img_to_beatcube の (antennas, chirps, samples)


def _image2d(v) -> np.ndarray:
    """入口の検証(fail-closed)。2-D・有限・数値でなければ ``ValueError``。"""
    a = np.asarray(v)
    if a.ndim == 3 and a.shape[-1] in (3, 4):
        # カラーが来たら輝度に落とす(黙って 3 本目の軸を空間軸と読まない)。
        a = a[..., :3].mean(axis=-1)
    if a.ndim != 2:
        raise ValueError("bridge: 入力は 2-D 画像が要る(受け取った形 %s)" % (a.shape,))
    if a.dtype.kind not in "fiub":
        raise ValueError("bridge: 数値配列が要る(dtype=%s)" % a.dtype)
    a = a.astype(np.float64, copy=False)
    if not np.isfinite(a).all():
        raise ValueError("bridge: 入力に NaN/Inf がある")
    return a


def _rel(knob: float) -> float:
    """typed bridge と同じ相対スケール: knob ∈ [0,1] → 既定の 1/4 〜 2 倍。"""
    return 0.25 + 1.75 * float(np.clip(knob, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# points / keypoints                                                           #
# --------------------------------------------------------------------------- #
def img_to_points(v, a, b):
    """画像を高さ場として読み、(x, y, z) の点群 (N,3) にする。

    各画素 ``(row, col)`` を 1 点 ``(x, y, z) = (col, row, value * H * s)`` に写す
    (``H`` は画像の高さ、単位はすべて画素)。列の規約は ``camera.depth_to_points``
    と同じ **(x, y, z)** —— ``reprconv`` の ``(z, y, x)`` とは逆なので、その族へ
    渡すときは ``tb_points_zyx_to_keypoints_uv`` 等の入口で読み替えること。

    - ``a`` → 高さの倍率 ``s = 0.25 + 1.75 * a``(a=0.5 で 1.125。値域 [0,1] の画像なら
      z の範囲は x, y と同じ桁になり、点群 op が「平面」でなく「地形」を見る)。
    - ``b`` → 間引きの歩幅 ``stride = 1 + int(b * 3)``(b=0.5 で 2。128×128 なら
      4,096 点。b=0 で全画素、b=1 で 1/16)。
    - 返り値: ``(N, 3)`` float64、``N = ceil(H/stride) * ceil(W/stride)``。空にはならない。
    - 順序は行優先(row-major)で決定的。同じ入力なら同じ配列。

    使いどころ: 点群 op(``tb_alpha_shape_boundary`` / ``tb_estimate_point_normals`` /
    ``tb_points_to_voxel`` …)を **1 枚の画像から** 試す入口。DEM(標高図)を
    ``value = 標高 / 最大標高`` に正規化して渡せば、そのまま地形の点群になる。
    """
    img = _image2d(v)
    h, w = img.shape
    stride = 1 + int(np.clip(b, 0.0, 1.0) * 3)
    sub = img[::stride, ::stride]
    yy, xx = np.mgrid[0:h:stride, 0:w:stride].astype(np.float64)
    z = sub * h * _rel(a)
    return np.stack([xx.ravel(), yy.ravel(), z.ravel()], axis=1)


def img_to_keypoints(v, a, b):
    """画像の局所極大を像面上の点 (u, v) = (col, row) の (N,2) にする。

    ``scipy.ndimage.maximum_filter`` で窓内最大と一致し、かつ値がしきい値以上の
    画素を極大とする(同値の平坦部は全画素が極大になる —— 前段に ``gaussian``
    を置くと減る)。

    - ``a`` → 窓の一辺 ``k = 3 + 2 * int(a * 4)``(a=0.5 で 7。大きいほど疎)。
    - ``b`` → しきい値 ``thr = b``(値 ≥ thr の極大だけ残す。b=0 で全極大)。
    - 返り値: ``(N, 2)`` float64 の ``(u, v) = (col, row)``。値の降順、同値は
      行優先で並ぶ(決定的)。**極大が 1 つも無ければ (0, 2)** —— 空でも形の
      契約は満たすが、下流の op によっては空を拒否する。
    - 画像の縁は ``mode="nearest"`` で処理するので縁の画素も極大になりうる。

    使いどころ: ``tb_keypoints_to_image2d``(点を画像に戻す)、
    ``tb_keypoints_uv_to_points``(z=0 の点群にする)への入口。
    """
    img = _image2d(v)
    k = 3 + 2 * int(np.clip(a, 0.0, 1.0) * 4)
    thr = float(np.clip(b, 0.0, 1.0))
    mx = ndimage.maximum_filter(img, size=k, mode="nearest")
    rows, cols = np.nonzero((img >= mx) & (img >= thr))
    if rows.size == 0:
        return np.zeros((0, 2), np.float64)
    vals = img[rows, cols]
    order = np.lexsort((cols, rows, -vals))     # 値の降順 → 行 → 列
    return np.stack([cols[order], rows[order]], axis=1).astype(np.float64)


# --------------------------------------------------------------------------- #
# signal / counts / matrix                                                     #
# --------------------------------------------------------------------------- #
def _profile(img: np.ndarray, a: float, b: float) -> np.ndarray:
    h, w = img.shape
    if b < 0.5:
        r = int(round(np.clip(a, 0.0, 1.0) * (h - 1)))
        return img[r, :].copy()
    c = int(round(np.clip(a, 0.0, 1.0) * (w - 1)))
    return img[:, c].copy()


def img_to_signal(v, a, b):
    """画像の 1 行(または 1 列)の濃度プロファイルを 1-D の signal にする。

    - ``a`` → 位置。``b < 0.5`` なら行 ``r = round(a * (H-1))`` を横に読む(長さ W)、
      ``b ≥ 0.5`` なら列 ``c = round(a * (W-1))`` を縦に読む(長さ H)。a=0.5 は中央。
    - 返り値: 1-D float64、値はそのまま(正規化しない。画像が [0,1] なら [0,1])。
    - 補間はしない(画素の値をそのまま並べる)。斜めの線が要るなら ``line_profile``
      (台帳)を使う。

    使いどころ: 1-D 関数の族(``tb_smooth_funct_1d_gauss`` / ``tb_derivate_funct_1d`` /
    ``tb_bandpass`` …)を画像の断面で試す入口。周期構造(市松・縞)を横切る行を
    選ぶとスペクトル系 op の効果が見える。
    """
    return _profile(_image2d(v), float(a), float(b))


def img_to_counts(v, a, b):
    """画像の 1 行(または 1 列)を光子の期待値として読み、Poisson 標本の 1-D カウント列にする。

    ``expected = profile * n_max`` を期待値とする Poisson 乱数(固定 seed 20260907)。
    光子計数の族(``tb_counts_to_countrate`` / ``tb_spad_deadtime_apply`` /
    ``tb_tcspc_background_subtract`` …)が受ける **非負整数の 1-D 列** の合成器で、
    ``tcspc_simulate`` と同じく「期待値が既知」なのが検算の根拠になる。

    - ``a`` → 行/列の位置(``img_to_signal`` と同じ規則。``b`` が向きも決める)。
    - ``b`` → ``b < 0.5`` で行、``b ≥ 0.5`` で列。加えて **1 画素あたりの最大光子数**
      ``n_max = 10 ** (1 + 2 * b)``(b=0 で 10、b=0.5 で 100、b=1 で 1,000)。
      少ないほど散布雑音が目立つ。
    - 返り値: 1-D ``int64``、非負。長さは行なら W、列なら H。
    - 決定的(seed 固定)。同じ入力・同じノブなら同じ列。

    注意: 期待値 0 の画素はカウント 0 になる(Poisson(0) は常に 0)。
    """
    img = _image2d(v)
    prof = _profile(img, float(a), float(b))
    n_max = 10.0 ** (1.0 + 2.0 * float(np.clip(b, 0.0, 1.0)))
    rng = np.random.default_rng(20260907)
    return rng.poisson(np.clip(prof, 0.0, None) * n_max).astype(np.int64)


def img_to_matrix(v, a, b):
    """画像 (H,W) をそのまま H×W の数値行列(sort ``matrix``)として扱う —— 純粋なキャスト。

    値も形も変えない(``float64`` へのコピーのみ)。線形代数の族
    (``tb_mat_cond`` / ``tb_mat_pinv`` / ``tb_stat_covariance`` …)に画像を渡す
    ための型の読み替えで、**a, b は未使用**。

    注意: 画像は一般に正則でも対称でもない。条件数は大きく(``tb_mat_cond``)、
    共分散(``tb_stat_covariance``)は「行 = 標本、列 = 変数」として読まれる ——
    つまり **各列(x 位置)を変数、各行を観測** とみなした統計になる。
    転置して渡したいなら前段に ``transpose``(台帳)を置く。
    """
    return _image2d(v).copy()


# --------------------------------------------------------------------------- #
# video / volume / lightfield                                                  #
# --------------------------------------------------------------------------- #
def img_to_video(v, a, b):
    """画像を一定速度で平行移動させた T フレームの動画 (T,H,W) にする。

    フレーム ``t`` は入力を ``(dy, dx) = t * step * (sin θ, cos θ)`` だけ動かしたもの
    (``scipy.ndimage.shift``、線形補間、縁は最近傍で延長)。**変位が閉形式で
    分かる**ので、動画の族(``tb_frame_difference_causal`` / ``tb_motion_energy_image`` /
    ``tb_background_subtraction_window`` …)の検算に使える。

    - ``a`` → 1 フレームあたりの歩幅 ``step = 4 * a`` 画素(a=0.5 で 2 px/frame)。
    - ``b`` → 移動方向 ``θ = 2π * b``(b=0 で +x、b=0.25 で +y(下)、b=0.5 で −x)。
    - フレーム数 ``T = VIDEO_FRAMES``(8)。フレーム 0 は入力そのもの。
    - 返り値: ``(T, H, W)`` float64、値域は入力と同じ([0,1] なら [0,1] のまま。
      線形補間は値域を広げない)。

    注意: 動くのは**画面全体**(カメラのパン)であって、物体だけではない。
    背景差分の族は「動かない背景」を仮定するので、全体パンでは前景が全画素に出る。
    """
    img = _image2d(v)
    step = 4.0 * float(np.clip(a, 0.0, 1.0))
    theta = 2.0 * np.pi * float(np.clip(b, 0.0, 1.0))
    dy, dx = step * np.sin(theta), step * np.cos(theta)
    frames = [img]
    for t in range(1, VIDEO_FRAMES):
        frames.append(ndimage.shift(img, (t * dy, t * dx), order=1, mode="nearest"))
    return np.stack(frames, axis=0)


def img_to_volume(v, a, b):
    """画像を高さ場として押し出し、(D,H,W) の体積(z 先頭)にする。

    ボクセル ``(z, y, x)`` は、その高さが画素の高さ以下なら画素値、超えていれば 0:
    ``vol[z, y, x] = img[y, x] if z <= img[y, x] * s * (D - 1) else 0``。
    つまり **高さ場の「中身が詰まった」固体**(地形・段差・押し出し部品)で、
    体積の族(``vol_dilate`` / ``vol_erosion_ball`` / ``macro_vol_denoise`` …)を
    1 枚の画像から試せる。軸順は 3-D 台帳の規約どおり **(depth, row, col)**。

    - ``a`` → 高さの倍率 ``s = 0.25 + 1.75 * a``(a=0.5 で 1.125。1 を超えた分は
      最上段 ``D-1`` で頭打ち)。
    - ``b`` → 段数 ``D = 8 + 2 * int(b * 28)``(b=0.5 で 36、b=0 で 8、b=1 で 64)。
    - 返り値: ``(D, H, W)`` float64、値域は入力と同じ。**z=0 の底面は
      値 > 0 の画素がすべて詰まる**(高さ 0 でも底面には乗る)。
    """
    img = _image2d(v)
    d = 8 + 2 * int(np.clip(b, 0.0, 1.0) * 28)
    top = np.clip(img * _rel(a) * (d - 1), 0.0, d - 1)
    z = np.arange(d, dtype=np.float64)[:, None, None]
    return np.where(z <= top[None, :, :], img[None, :, :], 0.0)


def img_to_lightfield(v, a, b):
    """画像を前景/背景の 2 層に分け、視差つきの 4-D ライトフィールド (V,U,H,W) にする。

    ``lf_synthesize`` と同じ前方モデルの 2 層版: 視点 ``(v, u)`` は層ごとに
    ``(slope * (v - v_c), slope * (u - u_c))`` だけ画像をずらして見る(線形補間、
    縁は最近傍)。背景層は傾き 0(無限遠)、前景層(しきい値以上の画素)は傾き
    ``slope`` で、前景が背景を**遮蔽**する(視点ごとにマスクもずらす)。
    変位が角度インデックスに線形なので、EPI の傾き・リフォーカスの最良スロープ・
    両端視点の視差 ``slope * (U - 1)`` がすべて閉形式で分かる。

    - ``a`` → 前景の傾き ``slope = 1.5 * a`` 画素/視点(a=0.5 で 0.75。5×5 なら
      両端で 3 px)。
    - ``b`` → 前景のしきい値 ``thr = b``(``img >= thr`` が前景。b=0.5 で明るい部分)。
    - 角度サンプルは ``LF_ANGULAR = (5, 5)``。返り値 ``(5, 5, H, W)`` float64。
    - 中央視点 ``(2, 2)`` は入力そのもの(ずれ 0)。

    使いどころ: ``tb_lf_epi`` / ``tb_lf_refocus`` / ``tb_lf_depth_from_focus`` の入口。
    深度推定の答えは「前景 = slope、背景 = 0」の 2 値。
    """
    img = _image2d(v)
    nv, nu = LF_ANGULAR
    slope = 1.5 * float(np.clip(a, 0.0, 1.0))
    fg = (img >= float(np.clip(b, 0.0, 1.0))).astype(np.float64)
    vc, uc = (nv - 1) / 2.0, (nu - 1) / 2.0
    out = np.empty((nv, nu) + img.shape, np.float64)
    for iv in range(nv):
        for iu in range(nu):
            sh = (slope * (iv - vc), slope * (iu - uc))
            if sh == (0.0, 0.0):
                out[iv, iu] = img
                continue
            layer = ndimage.shift(img, sh, order=1, mode="nearest")
            mask = ndimage.shift(fg, sh, order=1, mode="nearest") >= 0.5
            out[iv, iu] = np.where(mask, layer, img)
    return out


# --------------------------------------------------------------------------- #
# rgbimage / cimage / beatcube                                                 #
# --------------------------------------------------------------------------- #
def _hue_rgb(h: float) -> np.ndarray:
    """HSV(h, 1, 1) の RGB(h ∈ [0,1))。"""
    h6 = (h % 1.0) * 6.0
    i, f = int(h6), h6 - int(h6)
    table = [(1, f, 0), (1 - f, 1, 0), (0, 1, f), (0, 1 - f, 1), (f, 0, 1), (1, 0, 1 - f)]
    return np.asarray(table[i % 6], np.float64)


def img_to_rgb(v, a, b):
    """グレー画像に色相・彩度を与え、(H,W,3) の RGB 画像(sort ``rgbimage``)にする。

    ``rgb = gray * ((1 - sat) + sat * chroma)``、``chroma = HSV(hue, 1, 1)``。
    彩度 0 なら 3 チャンネル同値のグレー、1 なら単色の着色。**輝度(値)は
    どのチャンネルも入力以下**なので値域は [0,1] に留まる。

    - ``a`` → 色相 ``hue = a``(0 で赤、1/3 で緑、2/3 で青、1 で赤に戻る)。
    - ``b`` → 彩度 ``sat = b``(b=0.5 で半分だけ着色。反射モデルの族
      ``tb_specular_diffuse_split`` は「拡散 = 着色、鏡面 = 白」で分けるので、
      **明るい飽和部が鏡面として抜ける**)。
    - 返り値: ``(H, W, 3)`` float64。

    使いどころ: ``tb_rgb_to_quaternion``(→ qimage、四元数の色 op の入口)、
    ``tb_specular_free_transform`` / ``tb_wetness`` / ``tb_sensor_capture``。
    自然画像の色を再現するものではない(単一色相の合成)。
    """
    img = _image2d(v)
    sat = float(np.clip(b, 0.0, 1.0))
    chroma = _hue_rgb(float(np.clip(a, 0.0, 1.0)))
    return img[..., None] * ((1.0 - sat) + sat * chroma[None, None, :])


def img_to_cimage(v, a, b):
    """画像を振幅とし、位相を画素値と傾きから与えた複素場 (H,W) complex128 にする。

    ``field = img * exp(i * (2π * a * img + 2π * (b - 0.5) * 8 * x / W))``。
    振幅 = 画素値(透過率・開口として読む)、位相は **値に比例する成分**(位相物体
    としての厚み)と **x 方向の線形な傾き**(平面波の入射角)の和。角スペクトル法
    ``tb_angular_spectrum_propagate`` や ``tb_cx_*`` の族が受ける複素画像の合成器。

    - ``a`` → 位相の深さ ``2π * a * img``(a=0 で実場、a=0.5 で最大 π)。
    - ``b`` → 傾き。``(b - 0.5) * 8`` 周期ぶんの線形位相を x 方向に掛ける
      (b=0.5 で傾き 0。8 は「128 px で 8 縞」の目安)。
    - 返り値: ``(H, W)`` complex128。``|field| = img``、``arg`` は上式。
    - 値 0 の画素は位相が定義できない(``0 * exp(iφ) = 0``)。
    """
    img = _image2d(v)
    h, w = img.shape
    xx = np.arange(w, dtype=np.float64)[None, :] / max(w, 1)
    phase = 2.0 * np.pi * float(np.clip(a, 0.0, 1.0)) * img \
        + 2.0 * np.pi * (float(np.clip(b, 0.0, 1.0)) - 0.5) * 8.0 * xx
    return img * np.exp(1j * phase)


def img_to_beatcube(v, a, b):
    """画像の明点を FMCW レーダーの標的(距離 = 列、速度 = 行)として読み、複素ビート立方体 (A,C,S) にする。

    平滑化(σ=2)した画像の局所極大を値の降順に ``K`` 個拾い、各点を標的にする:
    ``range_m = 2 + 30 * col / W``、``velocity_ms = 15 * (2 * row / H - 1)``、
    振幅 = 画素値。前方モデルは台帳の ``fmcw_beat_simulate``(``rangedoppler``)
    そのもので、``n_samples = 64、n_chirps = 32、n_antennas = 4``(素子間隔は
    既定の半波長、標的はすべて正面 = 到来角 0°)、その他は
    同関数の既定(標本化 10 MHz、掃引 20 THz/s、チャープ周期 50 µs、波長 3.89 mm)。
    この既定では **距離は 0〜37.5 m、速度は ±19.5 m/s が曖昧さの無い範囲** で、
    上の写像はその内側に収まる。

    - ``a`` → 複素白色雑音の σ ``= 0.5 * a``(a=0 で無雑音)。
    - ``b`` → 標的数 ``K = 1 + int(b * 6)``(b=0.5 で 4。極大が足りなければその数)。
    - 返り値: ``(4, 32, 64)`` complex128。``tb_range_doppler_map`` で 2-D FFT すると
      標的ごとの峰が「列 → 距離ビン、行 → ドップラービン」に立ち、
      ``tb_beamform_delay_sum`` は 4 素子で到来角 0° の峰を返す。
    - 乱数 seed は 0 固定(決定的)。速度の符号は ``fmcw_beat_simulate`` の規約
      (**正 = 遠ざかる**)。
    """
    import rangedoppler as RD                            # 遅延 import(循環回避)

    img = _image2d(v)
    h, w = img.shape
    k = 1 + int(np.clip(b, 0.0, 1.0) * 6)
    sm = ndimage.gaussian_filter(img, 2.0)
    mx = ndimage.maximum_filter(sm, size=9, mode="nearest")
    rows, cols = np.nonzero(sm >= mx)
    vals = sm[rows, cols]
    order = np.lexsort((cols, rows, -vals))[:k]
    rows, cols, vals = rows[order], cols[order], vals[order]
    ranges = 2.0 + 30.0 * cols / max(w, 1)
    vels = 15.0 * (2.0 * rows / max(h, 1) - 1.0)
    amps = np.clip(vals, 1e-3, None)
    return RD.fmcw_beat_simulate(
        ranges_m=tuple(ranges), velocities_ms=tuple(vels), amplitudes=tuple(amps),
        n_samples=BEAT_SHAPE[2], n_chirps=BEAT_SHAPE[1], n_antennas=BEAT_SHAPE[0],
        noise_sigma=0.5 * float(np.clip(a, 0.0, 1.0)), seed=0)


def img_to_monogenic(v, a, b):
    """画像の単一スケールのモノジェニック信号(四元数場 (H,W,4)、sort ``qimage``)を作る。

    台帳の ``monogenic_signal``(Felsberg & Sommer 2001)そのもの: 対数放射状の
    raised-cosine 帯域通過を掛け、その Riesz 対と組にして四元数
    ``(帯域通過像, R1, R2, 0)`` に詰める。``tb_monogenic_amplitude`` /
    ``tb_monogenic_phase`` / ``tb_monogenic_orientation`` は **この形の qimage
    だけ** を受け付ける(色の四元数 ``tb_rgb_to_quaternion`` を渡すと
    「モノジェニック信号ではない」と拒否する)ので、その族の入口はこちら。

    - ``a`` → 中心波長 ``wavelength_px = 8 * (0.25 + 1.75 * a)`` 画素
      (a=0.5 で 9 px。小さいほど細かい構造に応答)。
    - ``b`` → 帯域幅 ``bandwidth_octaves = 1.0 * (0.25 + 1.75 * b)`` オクターブ
      (b=0.5 で 1.125)。
    - 返り値: ``(H, W, 4)`` float64。値域は入力に依存し [0,1] に収まらない
      (Riesz 対は符号つき)。
    """
    import quatimage as Q                                # 遅延 import(循環回避)

    img = _image2d(v)
    return np.asarray(Q.monogenic_signal(img, wavelength_px=8.0 * _rel(a),
                                         bandwidth_octaves=1.0 * _rel(b)), np.float64)


# --------------------------------------------------------------------------- #
# registration                                                                 #
# --------------------------------------------------------------------------- #
#: (名前, out_sort, 実装)。``in_sort`` はすべて image。
BRIDGES = (
    ("img_to_points", "points", img_to_points),
    ("img_to_keypoints", "keypoints", img_to_keypoints),
    ("img_to_signal", "signal", img_to_signal),
    ("img_to_counts", "counts", img_to_counts),
    ("img_to_matrix", "matrix", img_to_matrix),
    ("img_to_video", "video", img_to_video),
    ("img_to_volume", "volume", img_to_volume),
    ("img_to_lightfield", "lightfield", img_to_lightfield),
    ("img_to_rgb", "rgbimage", img_to_rgb),
    ("img_to_cimage", "cimage", img_to_cimage),
    ("img_to_beatcube", "beatcube", img_to_beatcube),
    ("img_to_monogenic", "qimage", img_to_monogenic),
)

CATEGORY = "bridge"


#: 失敗時(既定の fail-soft)に返す「中身は無いが sort として妥当な値」。
#: ``backends_typed._EMPTY_OF`` と同じ考え方で、そこに無い sort だけここで足す。
#: ``backend_safe.fallback`` は新設 sort を知らないので、任せると **入力画像が
#: そのまま返って sort の嘘になる**(実測 2026-09-07: points 宣言で (H,W) が返る)。
_EMPTY_OF = {
    "points": lambda: np.zeros((1, 3), np.float64),
    "keypoints": lambda: np.zeros((0, 2), np.float64),
    "signal": lambda: np.zeros(2, np.float64),
    "counts": lambda: np.zeros(2, np.int64),
    "matrix": lambda: np.zeros((2, 2), np.float64),
    "video": lambda: np.zeros((2, 2, 2), np.float64),
    "volume": lambda: np.zeros((2, 2, 2), np.float64),
    "lightfield": lambda: np.zeros((1, 1, 2, 2), np.float64),
    "rgbimage": lambda: np.zeros((2, 2, 3), np.float64),
    "cimage": lambda: np.zeros((2, 2), np.complex128),
    "beatcube": lambda: np.zeros((1, 2, 2), np.complex128),
    "qimage": lambda: np.zeros((2, 2, 4), np.float64),
}

#: 複素数を返す sort。``backend_safe.sanitize`` は複素出力の **実部だけ** を
#: 返す(実 sort 向けの規約)ので、この 2 sort は ``finish`` で素通しにする。
#: 有限性は各実装が入口検証(有限な入力・有界な演算)で保証する。
_COMPLEX_SORTS = frozenset({"cimage", "beatcube"})


def _keep(out, v):
    return out


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _bin):
    """``ops.py`` の登録規約。category は ``bridge``、in_sort は image。"""
    out = []
    for name, out_sort, fn in BRIDGES:
        empty = _EMPTY_OF[out_sort]
        g = guard(fn, out_sort, name=name,
                  on_fail=lambda v, _e=empty: _e(),
                  finish=_keep if out_sort in _COMPLEX_SORTS else None)
        out.append(Op(name, CATEGORY, "", IMAGE, out_sort, g))
    return out
