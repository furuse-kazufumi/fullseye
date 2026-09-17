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
#: 点群の箱の一辺。typed bridge が点群 op に束縛した値(``tools/chain_fuzz`` の
#: 種 ``rng.random((160, 3)) * 10``、``bounds=((0,10),)*3``、``radius=2.0`` …)は
#: **一辺 10 の箱**を前提にしている。画素座標(0〜127)のまま渡すと、半径系の op は
#: 近傍が空、占有格子は箱の外で全 0 になる(2026-09-07 実測: ``tb_radius_outlier_removal``
#: が空、``tb_occupancy_grid`` が全 0)。入口はその尺度に合わせる。
POINTS_BOX = 10.0


def img_to_points(v, a, b):
    """画像を高さ場として読み、(x, y, z) の点群 (N,3) にする。

    各画素 ``(row, col)`` を 1 点 ``(x, y, z) = (col * 10/W, row * 10/H, value * 10 * s)``
    に写す —— 画像の幅・高さを **一辺 10 の箱** に正規化した座標(``POINTS_BOX``)。
    点群 op の橋渡し(``tb_*``)が束縛している半径・境界箱・格子解像度はこの尺度
    (連鎖ファザーの種 ``[0,10)^3``)を前提にしているので、画素座標のまま渡すと
    半径系 op の近傍が空になり占有格子が全 0 になる(実測)。画素に戻すなら
    ``x * W / 10``、``y * H / 10``。列の規約は ``camera.depth_to_points`` と同じ
    **(x, y, z)** —— ``reprconv`` の ``(z, y, x)`` とは逆なので、その族へ渡すときは
    ``tb_points_zyx_to_keypoints_uv`` 等の入口で読み替えること。

    - ``a`` → 高さの倍率 ``s = 0.25 + 1.75 * a``(a=0.5 で 1.125。値域 [0,1] の画像なら
      z の範囲は x, y と同じ桁 [0, 11.25] になり、点群 op が「平面」でなく「地形」を見る)。
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
    x = xx * (POINTS_BOX / max(w, 1))
    y = yy * (POINTS_BOX / max(h, 1))
    z = sub * POINTS_BOX * _rel(a)
    return np.stack([x.ravel(), y.ravel(), z.ravel()], axis=1)


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


def img_to_projection_profile(v, a, b):
    """画像を 1 方向へ潰した**射影プロファイル**を 1-D の signal にする ―― 版面解析の基本量。

    ``img_to_signal`` が「1 本の行/列をそのまま読む」のに対し、こちらは**全行(全列)を
    束ねて 1 本にまとめる**。文字列の切れ目・罫線・帯の境目は、1 本の走査線では雑音に
    埋もれるが、潰すと谷として立ち上がる。

    - ``b`` → 向き。``b < 0.5`` で**縦に潰して長さ W**(列ごとの代表値。横に並んだ字の
      切れ目が谷になる)、``b >= 0.5`` で**横に潰して長さ H**(行ごと。行間が谷になる)。
      ``img_to_signal`` と同じく ``b`` が向きを決めるが、``a`` の意味は違う。
    - ``a`` → **上側トリム率**。潰す軸の値を大きい順に並べ、上位
      ``m = max(1, round((1-a) * N))`` 個だけを平均する。``a=0`` は**ただの平均射影**
      (古典的な projection profile そのもの)、``a=1`` は**最大値射影**(MIP)、
      その間は「外れ値だけを残して均す」連続的な折衷になる。
    - 返り値: 1-D float64。**正規化しない**(値域は入力のまま。[0,1] の画像なら [0,1])。
      長さは向きで決まる(W または H)。空フレームは一定値の列になる。

    **なぜノブがトリム率なのか**: 平均射影は雑音に強いが、細い線 1 本が背景に薄められて
    消える。最大値射影は細い線を残すが、輝点 1 個で列全体が持ち上がる。どちらを選んでも
    失うものがあるので、**どれだけ捨てるかをノブにして取引を明示した**。``a`` を上げると
    細い構造が残り、下げると雑音が均される ―― 単調で、両端が古典的な 2 つの射影に一致する。

    **暗い字には前段で反転を**。この op は**大きい方**を残すので、白地に黒字のまま渡すと
    トリムが**背景**を拾う。``invert``(台帳)を挟めば、``a`` が「濃い字のところ」を残す。

    **先行と対応**: 平均射影は文書解析の古典そのもの(Postl 1986 / Baird 1987 が傾き
    推定に使った量)で、HALCON では ``gray_projections``(水平・垂直の濃淡射影)に
    あたる —— 対応表で **`covered: false`** だった op を、これが埋める。上位トリムで
    最大値射影へ連続に寄せる族は、蛍光顕微鏡の時間フレーム融合で使われる
    **分位点射影**(上側 75 % 点を取る)と同じ発想だが、こちらは**上位 m 個の平均**
    なので **両端が厳密に平均射影と最大値射影に一致し、その間が単調**になる。

    使いどころ: 行の切り出し(横に潰して谷を探す)、字の切り出し(縦に潰す)、罫線検出、
    帯の境目、``deskew`` が内部で使っている判定量の可視化。下流は 1-D 関数の族
    (``tb_smooth_funct_1d_gauss`` / ``tb_local_min_funct_1d`` / ``tb_derivate_funct_1d``)。
    """
    img = _image2d(v)
    axis = 0 if float(b) < 0.5 else 1
    n = img.shape[axis]
    m = max(1, int(round((1.0 - float(np.clip(a, 0.0, 1.0))) * n)))
    top = np.sort(img, axis=axis)
    top = top[n - m:, :] if axis == 0 else top[:, n - m:]
    return np.asarray(top.mean(axis=axis), np.float64)


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


#: 二色性反射モデルの「鏡面」の膝。この明るさを超えた分は白(無彩色)へ戻す。
SPECULAR_KNEE = 0.75


def img_to_rgb(v, a, b):
    """グレー画像に色相・彩度を与え、(H,W,3) の RGB 画像(sort ``rgbimage``)にする。

    二色性反射モデル(拡散 = 着色、鏡面 = 白)の形で作る:
    ``mix = (1 - sat) + sat * chroma``、``chroma = HSV(hue, 1, 1)``、
    ``spec = clip((gray - 0.75) / 0.25, 0, 1) ** 2``、
    ``rgb = gray * (mix * (1 - spec) + spec)``。
    つまり暗〜中間の画素は色相で着色され、**明るさ 0.75 を超える画素ほど白(無彩色)に
    戻る**。彩度 0 なら 3 チャンネル同値のグレー(``spec`` に依らず入力そのもの)。
    どのチャンネルも入力以下なので値域は [0,1] に留まる。

    - ``a`` → 色相 ``hue = a``(0 で赤、1/3 で緑、2/3 で青、1 で赤に戻る)。
    - ``b`` → 彩度 ``sat = b``(b=0.5 で半分だけ着色)。
    - 返り値: ``(H, W, 3)`` float64。
    - 鏡面の膝 ``SPECULAR_KNEE = 0.75`` は固定(ノブにしていない)。

    なぜ鏡面を入れるか(2026-09-07 実測): 単純な着色 ``gray * mix`` だと明るい部分も
    同じ色相の飽和色になり、``tb_specular_coefficient_map`` / ``tb_specular_diffuse_split`` /
    ``tb_specular_free_transform`` が見る「無彩色のハイライト」が 1 画素も無く、
    鏡面係数が全 0 の真っ黒な図になった。合成の入力側が族の前提(二色性)を満たす。

    使いどころ: ``tb_rgb_to_quaternion``(→ qimage、四元数の色 op の入口)、
    ``tb_specular_free_transform`` / ``tb_wetness`` / ``tb_sensor_capture``。
    自然画像の色を再現するものではない(単一色相の合成)。
    """
    img = _image2d(v)
    sat = float(np.clip(b, 0.0, 1.0))
    chroma = _hue_rgb(float(np.clip(a, 0.0, 1.0)))
    mix = (1.0 - sat) + sat * chroma[None, None, :]
    spec = np.clip((img - SPECULAR_KNEE) / (1.0 - SPECULAR_KNEE), 0.0, 1.0) ** 2
    return img[..., None] * (mix * (1.0 - spec)[..., None] + spec[..., None])


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
# 戻りの橋 (新設 sort -> image)                                                 #
# --------------------------------------------------------------------------- #
#: 戻りの橋が描くキャンバスの一辺(画素)と描画域 (x, y, w, h)。
#: 図の生成器の既定(``tools/gen_op_figures.SIZE`` = 128)に合わせてある。
CANVAS = 128
_RECT = (12, 8, CANVAS - 24, CANVAS - 20)


def _blank_page():
    return np.full((CANVAS, CANVAS), 1.0, np.float64)


def _plot_1d(y, a, b, kinds=("scatter", "line", "bar")):
    """1-D 列を 1 枚の白地の図にする。``a`` = 縦軸の余白、``b`` = 描き方。"""
    import annotate as A                                 # 遅延 import(循環回避)

    y = np.asarray(y, np.float64).ravel()
    if y.size == 0:
        return _blank_page()
    lo, hi = float(np.min(y)), float(np.max(y))
    span = hi - lo
    pad = 0.30 * float(np.clip(a, 0.0, 1.0)) * (span if span > 1e-12 else 1.0)
    lo, hi = lo - pad, hi + pad
    if hi - lo < 1e-9:
        # ★定数列で軸が潰れると ``axes_transform`` は ValueError を投げる(傾きが
        #   無限大になるため、向こうの仕様)。潰れた軸だけここで開く —— 定数列は
        #   「描けない」のではなく「真ん中に水平線 1 本」が正しい絵。
        lo, hi = lo - 0.5, hi + 0.5
    x = np.arange(y.size, dtype=np.float64)
    ax = A.axes_transform(_RECT, (0.0, max(1.0, float(y.size - 1))), (lo, hi))
    t = float(np.clip(b, 0.0, 1.0))
    kind = kinds[0] if t < 1.0 / 3.0 else (kinds[1] if t < 2.0 / 3.0 else kinds[2])
    img = np.asarray(A.plot_series(_blank_page(), ax, x, y, kind=kind), np.float64)
    img = np.asarray(A.axes_frame(img, ax), np.float64)
    return np.clip(img, 0.0, 1.0)


def signal_to_img(v, a, b):
    """1-D の signal を**折れ線の図**にして画像へ戻す —— 「作った列を見る」入口。

    行きの橋(``img_to_signal`` / ``img_to_projection_profile``)で画像から列を
    作れるようになったが、**その列を見る登録 op が無かった**。signal を画像に
    落とせる op は ``spectrogram`` の 2 本だけで、どちらも描くのは**スペクトル**
    であって列そのものではない。図の生成器は 1-D を折れ線で描いているが、
    それは**道具の中の実装**で、``fullseye.apply`` からも Studio からも呼べない。
    この op がその穴を埋める。

    - ``a`` → 縦軸の**余白** ``pad = 0.30 * a * (データの幅)``(a=0 でぴったり、
      a=1 で上下に 30 % の余白)。ぴったりだと端の点が枠に重なる。
    - ``b`` → 描き方。``b < 1/3`` で**点**、``< 2/3`` で**折れ線**、それ以上で**棒**。
      ★並びは「**既定のノブ 0.5 がその型に素直な描き方になる**」ように決めてある
      —— 列は折れ線が素直なので真ん中が折れ線。
    - 横軸は添字 ``0..N-1``、縦軸はデータの範囲(+ 余白)。**軸は閉形式**
      (``annotate.axes_transform``)なので、値が画素のどこに来るかは計算できる。
    - 返り値: ``(128, 128)`` float64、白地に濃い線([0,1])。★**定数列は潰れた軸を
      ±0.5 開いて中央に水平線 1 本**を描く(``axes_transform`` は幅 0 の軸を
      ValueError で拒否するので、ここで開く)。空の列は白紙。

    使いどころ: 射影プロファイルの谷を目で確かめる、1-D 関数族
    (``tb_smooth_funct_1d_gauss`` / ``tb_derivate_funct_1d``)の効果を見る、
    図・記事にそのまま貼る。
    """
    return _plot_1d(v, a, b)


def counts_to_img(v, a, b):
    """非負整数の 1-D カウント列を**棒グラフ**にして画像へ戻す。

    ``counts`` を画像に落とせる op は **1 本も無かった**(作る op は 13 本ある)。
    既定を棒にしてあるのは、カウントが**整数の度数**だからで、折れ線で結ぶと
    「間の値」が在るように見えてしまう。

    - ``a`` → 縦軸の余白(``signal_to_img`` と同じ式)。
    - ``b`` → 描き方。``b < 1/3`` で**折れ線**、``< 2/3`` で**棒**(既定)、それ以上で
      **点**。``signal_to_img`` と**並びが違う**のは、既定のノブ 0.5 でその型に
      素直な描き方になるようにしているから —— カウントは棒が素直。
    - 返り値: ``(128, 128)`` float64。
    """
    return _plot_1d(v, a, b, kinds=("line", "bar", "scatter"))


def matrix_to_img(v, a, b):
    """行列を**見るための濃淡**にして画像へ戻す —— キャストではない。

    行き(``img_to_matrix``)は値も形も変えない**純粋なキャスト**だと明記して
    あるが、戻りを同じくキャストにすると嘘になる: 行列の値は [0,1] に収まらず、
    最小値が黒・最大値が白に伸びるだけだと **0 がどこかが分からない**。
    共分散・相関・擬似逆行列の符号は、そこが読めないと意味を持たない。

    - ``a`` → **対数圧縮**の強さ。``k = 10**(3a) - 1`` として
      ``y = sign(x) * log1p(k|x|) / log1p(k)``(a=0 は線形、a=1 で 1000 倍の圧縮)。
      条件数のように桁が開く行列で、小さい成分が全部黒に潰れるのを防ぐ。
    - ``b`` → 基準。``b < 0.5`` は**データの min–max を [0,1] に伸ばす**、
      ``b >= 0.5`` は **0 を 0.5 に置いて ``|x|`` の最大で対称に**(符号つきの
      行列向け。0.5 が中立、明るい = 正、暗い = 負)。
    - 返り値: 入力と**同じ形**の float64、値域 [0,1]。全要素が等しい行列は一様な
      0.5(min–max 側でも 0 除算にならないよう中立へ倒す)。
    """
    x = np.asarray(_image2d(v), np.float64)
    k = 10.0 ** (3.0 * float(np.clip(a, 0.0, 1.0))) - 1.0
    if k > 0:
        x = np.sign(x) * np.log1p(k * np.abs(x)) / np.log1p(k)
    if float(b) < 0.5:
        lo, hi = float(np.min(x)), float(np.max(x))
        if hi - lo < 1e-12:
            return np.full(x.shape, 0.5, np.float64)
        return (x - lo) / (hi - lo)
    m = float(np.max(np.abs(x)))
    if m < 1e-12:
        return np.full(x.shape, 0.5, np.float64)
    return np.clip(0.5 + 0.5 * x / m, 0.0, 1.0)


def contour_to_img(v, a, b):
    """XLD 輪郭を**その輪郭自身の座標系に描き戻す** —— 43 本の op が作るのに、
    画像に落とせる op は 1 本も無かった。

    図の生成器は輪郭を折れ線で描いているが、それは**道具の中の実装**で登録 op
    からは呼べない(``fullseye.apply`` にも Studio にも出てこない)。

    - ``a`` → 線の太さ ``1 + int(2a)``(1〜3 画素)。
    - ``b`` → 濃さの付け方。``b < 0.5`` は**全部同じ濃さ**、``b >= 0.5`` は
      **点数の多い輪郭ほど濃く**(順位で 0.15〜0.85 に割り振る)。どれが主要な
      輪郭かが一目で分かる。
    - 返り値: 輪郭が持つ ``shape``(元画像の大きさ)の float64、白地に暗い線。
      ★輪郭が 1 本も無ければ**白紙**を返す(黒い板にしない)。
    """
    import imagedraw as D                                # 遅延 import(循環回避)

    cs = list(v.get("cs") or []) if isinstance(v, dict) else []
    shape = tuple(v.get("shape") or (CANVAS, CANVAS)) if isinstance(v, dict) else (CANVAS, CANVAS)
    img = np.ones((int(shape[0]), int(shape[1])), np.float64)
    if not cs:
        return img
    width = 1 + int(float(np.clip(a, 0.0, 1.0)) * 2.0)
    order = np.argsort([-len(np.asarray(c)) for c in cs])
    rank = {int(j): i for i, j in enumerate(order)}
    n = max(1, len(cs) - 1)
    for j, c in enumerate(cs):
        arr = np.asarray(c, np.float64)
        if arr.ndim != 2 or arr.shape[0] < 2:
            continue
        if float(b) < 0.5:
            tone = 0.15
        else:
            tone = 0.15 + 0.70 * (rank[j] / n)
        img = np.asarray(D.draw_polyline(img, arr[:, ::-1], color=float(tone),
                                         width=width, closed=False), np.float64)
    return np.clip(img, 0.0, 1.0)


def feature_to_img(v, a, b):
    """スカラの feature を**目盛りつきの帯**にして画像へ戻す —— 2-D 台帳で
    **125 本の op が作るのに、画像に落とせる op が 1 本も無かった** sort。

    ★**数字そのものは描かない。** 文字を焼くと絵が**環境に入っている書体**で
    変わり、同じ入力で同じ画素という契約が壊れる。描くのは値の**位置**で、
    目盛り(0・1/4・1/2・3/4・1)が読みの手掛かりになる。数値が要るなら
    ``annotate_table`` / ``annotate_leader``(paper 族)に渡すこと。

    - ``a`` → スケールの上限 ``hi = 10 ** (4a - 2)``(a=0 で 0.01、a=0.5 で **1.0**、
      a=1 で 100)。特徴量は桁がまちまちなので、見たい桁をここで選ぶ。
    - ``b`` → 目盛りの張り方。``b < 0.5`` は **片側** ``[0, hi]``(左端が 0)、
      ``b >= 0.5`` は **両側** ``[-hi, +hi]``(**中央が 0**。相関・歪度など符号の
      ある量向け)。
    - 上限を超える値は**端で止める**(帯が振り切れた状態 = 「スケールが小さい」の
      合図)。★NaN / Inf は**白紙**を返す(振り切れと区別する)。
    - 返り値: ``(128, 128)`` float64、白地([0,1])。
    """
    try:
        x = float(np.asarray(v, np.float64).ravel()[0])
    except Exception:                                    # noqa: BLE001 - 形は guard が見る
        return _blank_page()
    img = _blank_page()
    if not np.isfinite(x):
        return img
    hi = 10.0 ** (4.0 * float(np.clip(a, 0.0, 1.0)) - 2.0)
    y0, y1 = CANVAS // 2 - 14, CANVAS // 2 + 14          # 帯の上下
    x0, x1 = 12, CANVAS - 12                             # 帯の左右
    img[y0:y1, x0] = 0.0
    img[y0:y1, x1 - 1] = 0.0
    img[y0, x0:x1] = 0.0
    img[y1 - 1, x0:x1] = 0.0
    span = x1 - 1 - x0
    for q in (0.0, 0.25, 0.5, 0.75, 1.0):                # 目盛り
        c = x0 + int(round(q * span))
        img[y1:y1 + 6, min(c, x1 - 1)] = 0.0
    if float(b) < 0.5:
        frac = float(np.clip(x / hi, 0.0, 1.0))
        w = int(round(frac * span))
        if w > 0:
            img[y0 + 2:y1 - 2, x0 + 1:x0 + 1 + w] = 0.25
    else:
        mid = x0 + span // 2
        img[y0 - 4:y0, mid] = 0.0                        # 0 の位置を上に出す
        frac = float(np.clip(x / hi, -1.0, 1.0))
        w = int(round(abs(frac) * (span // 2)))
        if w > 0:
            if frac >= 0:
                img[y0 + 2:y1 - 2, mid:mid + w] = 0.25
            else:
                img[y0 + 2:y1 - 2, mid - w:mid] = 0.25
    return np.clip(img, 0.0, 1.0)


#: (名前, in_sort, 実装)。``out_sort`` はすべて image。**戻りの橋**。
RETURN_BRIDGES = (
    ("signal_to_img", "signal", signal_to_img),
    ("counts_to_img", "counts", counts_to_img),
    ("matrix_to_img", "matrix", matrix_to_img),
    ("contour_to_img", "contour", contour_to_img),
    ("feature_to_img", "feature", feature_to_img),
)


# --------------------------------------------------------------------------- #
# registration                                                                 #
# --------------------------------------------------------------------------- #
#: (名前, out_sort, 実装)。``in_sort`` はすべて image。
BRIDGES = (
    ("img_to_points", "points", img_to_points),
    ("img_to_keypoints", "keypoints", img_to_keypoints),
    ("img_to_signal", "signal", img_to_signal),
    ("img_to_projection_profile", "signal", img_to_projection_profile),
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
    # 戻りの橋(-> image)の fail-soft。中身の無い白紙ではなく **0 の板**にする
    # のは、他の sort の空値(すべて零)と読み方を揃えるため。
    "image": lambda: np.zeros((CANVAS, CANVAS), np.float64),
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
    # 戻りの橋(新設 sort -> image)。category は同じ ``bridge`` なので
    # ``ops._candidates`` から除かれ、**進化のゲノム -> op の写像は変わらない**。
    # ここを普通の category にすると signal/contour/matrix/counts/feature の
    # 候補リストが伸び、それらを消費する既存 champion が黙って別の op に移る。
    empty_img = _EMPTY_OF["image"]
    for name, in_sort, fn in RETURN_BRIDGES:
        g = guard(fn, "image", name=name, on_fail=lambda v, _e=empty_img: _e())
        out.append(Op(name, CATEGORY, "", in_sort, IMAGE, g))
    return out
