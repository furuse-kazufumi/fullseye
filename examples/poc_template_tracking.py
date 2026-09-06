# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_template_tracking —— 追跡は「見失う」より先に「静かにずれる」。

    py -3.11 examples/poc_template_tracking.py

【この PoC が答える問題】
テンプレート追跡は動画のいちばん素朴な道具で、実装も 3 行で書ける ——
最初のフレームから小さな窓を切り出し、次のフレームで相関が最大の場所を探す。
問題は **止まり方** のほうにある。この道具は次の 3 通りで壊れるのに、
どれも「壊れました」とは言わない。

  (1) **見失う** —— 遮蔽・大きな移動で、まったく別の場所にロックする。
  (2) **静かにずれる** —— テンプレートを更新すると、1 フレームあたり
      1 画素未満の丸め誤差が積み上がって最後には対象から外れる。
      このとき相関ピークは **むしろ最高値** を出す(自分の直前の切り出しに
      合わせているのだから当たり前)。
  (3) **自信満々で間違える** —— 繰り返し模様の上では、正解と同じ高さの
      ピークが等間隔に何本も立つ。ピーク値だけを信頼度に使うと、
      **嘘の側で信頼度が高く出る**。

ここでは真値を自分で握る。大きな世界画像の上を既知の相似変換(並進 + 回転 +
拡大縮小)でカメラを動かし、**追う対象が各フレームのどこに何度で何倍で写るかを
私が決める**。遮蔽・照明変化・動きぼけも既知の量で足す。だから「何画素ずれたか」
「いつ壊れたか」を推測ではなく引き算で出せる。

ゼロ点は **1 枚目のテンプレートを毎フレーム全域探索で当てる(更新なし)**。
更新もしない・予測もしない、いちばん素朴な系である。以降の工夫は
すべてこれを上回るかどうかで測る。

    EXTEND: 実写に替えるなら ``make_sequence`` を捨てて自分のフレーム列を
    ``frames`` に、追う対象の位置を ``truth`` に入れるだけでよい。ただし
    **真値が消える** ので「真の位置からのずれ」は測れなくなる。残るのは
    (a) 手で打った数フレームぶんの正解との照合、(b) 往復追跡の不一致
    (t → t+k → t で戻れるか。真値なしで測れる数少ない絶対量)、
    (c) 相関ピークと突出度。第 10 章のとおり (c) は **条件によって嘘をつく**
    ので、(c) だけを合否に使ってはいけない。

【章立て】
 0. 舞台 —— 真値の作り方と検算
 1. 4 つの対象の素性 —— 追う前に、そのテンプレートが一意かどうかを測る
 2. ゼロ点 —— 更新なし全域探索を、対象 4 種 × 軌跡 2 種で
 3. 系の比較(更新なし / 毎フレーム更新 / 一定間隔更新 / 予測つき局所探索)
 4. ★ 崖 (a) フレーム間の移動量 —— 局所探索の窓を超えた瞬間に何が起きるか
 5. ★ 崖 (b) 遮蔽率 0 → 80 %、そして「見つけた」と誤って報告する率
 6. ★ 崖 (c) スケールと回転 —— 並進しか探さない追跡はどこまで耐えるか
 7. ★ 崖 (d) 照明変化 —— NCC は本当に明るさ変化に強いのか
 8. ★ 崖 (e) 更新間隔とドリフト —— log-log の傾きを実測する
 9. ★ 崖 (f) 繰り返し模様 —— 誤ロックは窓の広さで決まる
10. ★★ 見失ったことに気づけるか —— ピーク値 vs 突出度(どちらも万能ではない)
11. 時間推移 —— 1 つの数字にまとめない
12. 速度と、測らなかったこと

【★ この PoC が出した道具の穴(op 本体は直していない)】
(a) **``ncc_locate`` は相関マップを返さない**。返るのは ``[相関値, 行, 列]`` の
    3 要素だけ。**突出度(2 番目のピークとの差)が公開 API では計算できない**。
    第 10 章の主題そのものが公開 API の外にある。マップを作る ``_ncc_map`` は
    private で、``fs`` ファサードにも ``fs.op`` にも出てこない。
(b) **2 次元だけ副画素がない**。``accel_match.ncc_locate_3d`` には
    ``subvoxel=True``(相関ピーク近傍の重心)があり ``ncc_locate_3d_pyramid``
    まであるのに、2 次元の ``ncc_locate`` / ``ncc_locate_batch`` はどちらも
    整数座標しか返さない。同じ repo で 3 次元のほうが進んでいる。
    第 2 章でこの量子化が誤差の床を作っているのを実測する。
(c) **テンプレートが引数でなくグローバル状態**。``fs.set_match_template(T)`` を
    呼んでから ``fs.op.ncc_locate(image)`` を呼ぶ。追跡は「フレームごとに
    テンプレートを差し替える」処理なので、**毎回グローバルを書き換える**
    ことになる。並べて走らせると取り違えても例外は出ない。
(d) **探索範囲を指定できない**。全域探索しかない。局所探索は呼ぶ側が画像を
    自分で切って、返ってきた座標にオフセットを足し戻すしかない
    (この PoC の ``locate_local``)。切り出しが小さすぎると
    full-overlap 位置が消えて **黙って ``[0,0,0]``** が返る。
(e) **返り値の座標系が ``(行, 列)``**。この PoC の幾何は ``(x, y)`` なので
    毎回入れ替えている。取り違えても例外は出ない(第 0 章で検算した)。
(f) **``shape_locate`` の角度刻みは 30 度固定**で、刻みを渡す引数が無い。
    さらに回転テンプレートを ``reshape=False`` で作るので **四隅がゼロで
    埋まり**、その分だけ相関値が構造的に下がる。第 6 章で実測する。
(g) **追跡の状態を持つ入口が無い**。``track_points``(疎な点の Lucas-Kanade)は
    あるが、テンプレート追跡の系(更新方針・予測・見失い判定)は無い。
    第 3 章の 4 系はすべてこの PoC の自前である。
(h) **信頼度の語彙が無い**。``ncc_locate`` の第 1 要素は相関値そのもので、
    「これは信用できるか」を表す量ではない。第 10 章のとおり相関値は
    条件によって嘘の側で高く出る。
"""
from __future__ import annotations

import time

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

import fullseye as fs
# ★ 穴 (a): 相関マップを返す公開 op が無いので private を借りる。
#    第 0 章で公開 op ``fs.op.ncc_locate`` と一致することを検算してから使う。
import ops

T_START = time.perf_counter()

# ── 舞台の寸法(真値は私が決める)──────────────────────────────────────── #
WORLD = 640                      # 世界画像の一辺
FR_H, FR_W = 120, 160            # 1 フレーム
TPL = 25                         # テンプレートの一辺(奇数)
HALF = TPL // 2
O_XY = np.array([(FR_W - 1) / 2.0, (FR_H - 1) / 2.0])    # フレーム中心 (x, y)

# 追う対象を置く世界座標 (x, y)。1 つの視野に 1 つしか入らないよう離す。
TARGETS = {
    "一意":   np.array([150.0, 150.0]),   # 大きさも明るさもばらばらの角の集まり
    "繰返":   np.array([470.0, 150.0]),   # 同じ字形が周期 22 px で並ぶ
    "直線縁": np.array([150.0, 470.0]),   # 1 本の直線の縁が主体(開口問題)
    "片側":   np.array([470.0, 470.0]),   # 左半分だけテクスチャ、右半分は平坦
}
LOST_PX = 5.0                    # 「見失った」の線。テンプレート半幅 12 px の 4 割
_gx, _gy = np.meshgrid(np.arange(FR_W, dtype=float), np.arange(FR_H, dtype=float))
_FXY = np.stack([_gx.ravel(), _gy.ravel()])              # (2, H*W) の (x, y)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def _rot(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])


# ===========================================================================
# 0. 舞台 —— 世界画像・カメラ・軌跡
# ===========================================================================
def make_world(rng):
    """世界画像を作る。**構造のあるものを必ず混ぜる**。

    乱数の斑点だけで作ると、どのテンプレートも一意になってしまい
    「誤対応」が一度も起きない —— 崖の材料が消える。ここでは 4 種類を置く。

    (1) 低周波の地 + 小さな四角の紙吹雪 —— 世界のどこにでもある背景。
        紙吹雪は大きさも明るさもばらばらなので、切り出した窓が一意になりやすい。
    (2) **繰り返し模様** —— 同じ字形を周期 22 px の格子で並べる。窓がこの中に
        入ると、正解と同じ高さのピークが等間隔に何本も立つ(第 9 章)。
    (3) **直線の縁が主体の場所** —— 紙吹雪を消して斜めの半平面だけを置く。
        縁に沿った方向は相関が平らになる(開口問題)。
    (4) **片側だけテクスチャ** —— 左半分に細かい市松、右半分は平坦。
        「窓の半分は情報が無い」という現実の対象(部品の縁、無地の面)を模す。
    """
    base = gaussian_filter(rng.normal(size=(WORLD, WORLD)), 9.0)
    img = 0.34 + 0.34 * (base - base.min()) / np.ptp(base)

    n = 5200                                            # (1) 紙吹雪
    ys = rng.integers(0, WORLD - 6, n)
    xs = rng.integers(0, WORLD - 6, n)
    sz = rng.integers(2, 6, n)
    vv = rng.uniform(0.05, 0.95, n)
    for y, x, s, v in zip(ys, xs, sz, vv):
        img[y:y + s, x:x + s] = v

    gx, gy = TARGETS["繰返"]                             # (2) 繰り返し模様
    glyph = np.zeros((11, 11))
    glyph[1:10, 5] = 1.0
    glyph[5, 1:10] = 1.0
    glyph[1:4, 1:4] = 1.0
    r0, c0 = int(gy) - 90, int(gx) - 90
    img[r0:r0 + 180, c0:c0 + 180] = 0.30                # まず消してから並べる
    for a in range(0, 180 - 11, 22):
        for b in range(0, 180 - 11, 22):
            tile = img[r0 + a:r0 + a + 11, c0 + b:c0 + b + 11]
            img[r0 + a:r0 + a + 11, c0 + b:c0 + b + 11] = np.where(glyph > 0, 0.88, tile)

    ex, ey = TARGETS["直線縁"]                           # (3) 直線の縁だけ
    r0, c0 = int(ey) - 70, int(ex) - 70
    yy, xx = np.mgrid[0:140, 0:140]
    half = (0.62 * (xx - 70) + 0.78 * (yy - 70)) > 0.0  # 傾いた半平面
    img[r0:r0 + 140, c0:c0 + 140] = np.where(half, 0.70, 0.26)
    img[r0:r0 + 140, c0:c0 + 140] += 0.02 * gaussian_filter(
        rng.normal(size=(140, 140)), 2.0)               # 縁以外は情報のない微弱な地

    sx, sy = TARGETS["片側"]                             # (4) 片側だけテクスチャ
    r0, c0 = int(sy) - 70, int(sx) - 70
    yy, xx = np.mgrid[0:140, 0:140]
    checker = 0.30 + 0.50 * (((xx // 3) + (yy // 3)) % 2)
    img[r0:r0 + 140, c0:c0 + 140] = np.where(xx < 70, checker, 0.52)
    img[r0:r0 + 140, c0:c0 + 140] += 0.01 * rng.normal(size=(140, 140))
    return np.clip(img, 0.0, 1.0)


def world_to_frame(pts_xy, c, theta, s):
    """世界座標 → そのカメラ姿勢でのフレーム座標(どちらも ``(x, y)``)。"""
    p = np.atleast_2d(np.asarray(pts_xy, float))
    return O_XY + (_rot(-theta) @ (p - c).T).T / s


def frame_to_world(pts_xy, c, theta, s):
    p = np.atleast_2d(np.asarray(pts_xy, float))
    return c + s * (_rot(theta) @ (p - O_XY).T).T


def render(world, c, theta, s):
    """世界画像からフレームを 1 枚切り出す(双一次)。"""
    w = c[:, None] + s * (_rot(theta) @ (_FXY - O_XY[:, None]))
    return map_coordinates(world, [w[1], w[0]], order=1,
                           mode="nearest").reshape(FR_H, FR_W)


def make_sequence(world, target, n=40, step=2.0, rot_deg=0.0, zoom=1.0, amp=20.0,
                  noise=0.004, seed=0, occl=0.0, occl_from=3, gain=1.0, offset=0.0,
                  blur_px=0.0, blur_k=5, twin=False, twin_blur=1.6):
    """既知の軌跡で動画を合成する。真値は ``truth``(各フレームの ``(x, y)``)。

    対象がフレーム内で描く軌跡を **先に決めてから** カメラ位置を逆算する。
    こうすると「1 フレームあたり何画素動くか」を厳密に ``step`` で指定できる
    (第 4 章の掃引がそのまま意味を持つ)。軌跡は半径 ``amp`` の円弧なので
    等速・滑らかで、定速予測が効く条件になっている。

    ``rot_deg`` / ``zoom`` は最終フレームまでの総量。``occl`` は
    **テンプレート面積に対する遮蔽率**(左から帯が入る)。``gain``/``offset`` は
    照明変化、``blur_px`` は 1 フレームぶんの動きぼけの長さ。``twin`` は
    **そっくりな別物体**(1 枚目のテンプレートを少しぼかした複製)を
    一定のずれた位置に一緒に動かす —— 同じ部品が 2 つ流れてくる状況。

    最後に **[0, 1] で切って 8 bit に量子化する**。カメラは 1 を超える値を
    出せないので、飽和は「明るさが上がった」ではなく **情報が消えた** 状態に
    なる。第 7 章の結論はこの切り捨てがあって初めて意味を持つ。
    """
    omega = 2.0 * np.arcsin(min(1.0, step / (2.0 * amp)))
    rng = np.random.default_rng(1000 + seed)
    twin_patch = None
    if twin:
        xy0 = O_XY.copy()
        twin_patch = gaussian_filter(
            crop_template(render(world, target, 0.0, 1.0), xy0), twin_blur)
    frames, truth, angles, scales = [], [], [], []
    for t in range(n):
        u = t / max(1, n - 1)
        th = np.deg2rad(rot_deg) * u
        sc = zoom ** u
        xy = O_XY + amp * np.array([np.cos(omega * t) - 1.0, np.sin(omega * t)])
        c = target - sc * (_rot(th) @ (xy - O_XY))
        if blur_px > 0.0:                       # 動きぼけ = 露光中の姿勢を平均
            acc = np.zeros((FR_H, FR_W))
            for k in range(blur_k):
                dt = (k / (blur_k - 1) - 0.5) * (blur_px / max(step, 1e-6))
                th2 = np.deg2rad(rot_deg) * ((t + dt) / max(1, n - 1))
                sc2 = zoom ** ((t + dt) / max(1, n - 1))
                xy2 = O_XY + amp * np.array([np.cos(omega * (t + dt)) - 1.0,
                                             np.sin(omega * (t + dt))])
                acc += render(world, target - sc2 * (_rot(th2) @ (xy2 - O_XY)), th2, sc2)
            img = acc / blur_k
        else:
            img = render(world, c, th, sc)
        if gain != 1.0 or offset != 0.0:
            img = gain * img + offset
        if occl > 0.0 and t >= occl_from:       # 左から入る遮蔽物(平坦な物体)
            x0, x1 = xy[0] - HALF, xy[0] - HALF + occl * TPL
            y0, y1 = xy[1] - 42.0, xy[1] + 42.0
            m = ((_gx >= max(0.0, x0 - 40.0)) & (_gx < x1)
                 & (_gy >= y0) & (_gy < y1))
            img = np.where(m, 0.47 + 0.01 * rng.normal(size=img.shape), img)
        if twin_patch is not None and t >= occl_from:    # そっくりな別物体
            img = np.asarray(img, float).copy()
            r = int(round(xy[1] - 26.0))
            c = int(round(xy[0] + 44.0))
            if HALF <= r < FR_H - HALF and HALF <= c < FR_W - HALF:
                img[r - HALF:r + HALF + 1, c - HALF:c + HALF + 1] = twin_patch
        img = np.clip(img + noise * rng.normal(size=img.shape), 0.0, 1.0)
        frames.append(np.round(img * 255.0) / 255.0)      # 8 bit 量子化
        truth.append(xy.copy())
        angles.append(np.rad2deg(th))
        scales.append(sc)
    return (frames, np.asarray(truth), np.asarray(angles), np.asarray(scales))


def crop_template(img, xy):
    """フレーム上の ``(x, y)`` を中心に ``TPL x TPL`` を切り出す(枠内へ丸める)。"""
    r = int(np.clip(round(xy[1]), HALF, FR_H - 1 - HALF))
    c = int(np.clip(round(xy[0]), HALF, FR_W - 1 - HALF))
    return img[r - HALF:r + HALF + 1, c - HALF:c + HALF + 1].copy()


# ===========================================================================
# 探索の道具
# ===========================================================================
def peak_and_prominence(corr):
    """相関マップから ``(ピーク値, (x, y), 突出度, 2 位までの距離)``。

    突出度 = ピーク値 − **ピーク近傍(± ``TPL``)を除いた残りの最大値**。
    近傍を除かないと同じ山の肩を 2 位として数えてしまい、どんな場合でも
    突出度がほぼ 0 になる。除く半径をテンプレート幅にしているのは、
    それ以内の 2 位は「同じ対応」だからである。

    ★ 穴 (a): この計算に必要な相関マップは公開 API から返ってこない。
    """
    idx = np.unravel_index(int(np.argmax(corr)), corr.shape)
    peak = float(corr[idx])
    m = corr.copy()
    r0, r1 = max(0, idx[0] - TPL), min(corr.shape[0], idx[0] + TPL + 1)
    c0, c1 = max(0, idx[1] - TPL), min(corr.shape[1], idx[1] + TPL + 1)
    m[r0:r1, c0:c1] = -2.0
    if float(m.max()) <= -2.0:                  # 近傍を除いたら何も残らなかった
        return peak, np.array([float(idx[1]), float(idx[0])]), peak, float("nan")
    j = np.unravel_index(int(np.argmax(m)), m.shape)
    return (peak, np.array([float(idx[1]), float(idx[0])]),
            peak - float(m[j]), float(np.hypot(j[0] - idx[0], j[1] - idx[1])))


def locate_full(img, tpl):
    """全域探索。ゼロ点が使う探索そのもの。"""
    return peak_and_prominence(ops._ncc_map(img, tpl))


def locate_local(img, tpl, pred_xy, rad):
    """予測位置の周り ``± rad`` だけを探す。

    ★ 穴 (d): 探索範囲を渡す引数が無いので呼ぶ側で切る。切り出しは
    ``rad + HALF + 1`` の余白を取らないと full-overlap 位置が消えて
    **黙って何も見つからない** ことになる(ここでは明示的に失敗を返す)。
    """
    h = int(rad) + HALF + 1
    p = np.where(np.isfinite(pred_xy), pred_xy, O_XY)     # 予測が壊れたら画面中心へ
    r = int(np.clip(round(float(p[1])), 0, FR_H - 1))
    c = int(np.clip(round(float(p[0])), 0, FR_W - 1))
    r0, r1 = max(0, r - h), min(FR_H, r + h + 1)
    c0, c1 = max(0, c - h), min(FR_W, c + h + 1)
    crop = img[r0:r1, c0:c1]
    if crop.shape[0] <= TPL or crop.shape[1] <= TPL:
        # ★ 穴 (d): 公開 op ならここで黙って [0,0,0] が返る。明示的に失敗を返す。
        return 0.0, np.array([float(c), float(r)]), 0.0, float("nan")
    pk, xy, prom, d2 = peak_and_prominence(ops._ncc_map(crop, tpl))
    return pk, xy + np.array([c0, r0]), prom, d2


def run_tracker(frames, tpl0, xy0, mode="static", update_k=None, rad=12):
    """4 つの系を 1 つの関数で。返りは各フレームの位置・ピーク・突出度。

    ``static``   更新なし全域探索(**ゼロ点**)
    ``update1``  毎フレーム更新・全域探索
    ``updatek``  ``update_k`` フレームごとに更新・全域探索
    ``local``    更新なし・定速予測つき局所探索(半径 ``rad``)
    """
    tpl = tpl0.copy()
    est = [np.asarray(xy0, float)]
    pk = [1.0]
    prom = [float("nan")]
    for t in range(1, len(frames)):
        if mode == "local":
            v = est[-1] - est[-2] if t >= 2 else np.zeros(2)
            p, xy, pr, _ = locate_local(frames[t], tpl, est[-1] + v, rad)
        else:
            p, xy, pr, _ = locate_full(frames[t], tpl)
        if not np.isfinite(xy).all():
            xy = est[-1].copy()
        est.append(xy)
        pk.append(p)
        prom.append(pr)
        if mode == "update1" or (mode == "updatek" and t % update_k == 0):
            if np.isfinite(xy).all():
                tpl = crop_template(frames[t], xy)
    return np.asarray(est), np.asarray(pk), np.asarray(prom)


def err_of(est, truth):
    return np.linalg.norm(est - truth, axis=1)


def auc_lost(score, lost):
    """「見失ったフレームほど大きい」と主張する量の識別力(0.5 = 無力, 1.0 = 完全)。"""
    a, b = np.asarray(score)[lost], np.asarray(score)[~lost]
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    gt = np.greater.outer(a, b).mean()
    eq = np.equal.outer(a, b).mean()
    return float(gt + 0.5 * eq)


def loglog_slope(t, e):
    """log-log の傾き(誤差がフレーム数の何乗で伸びるか)。"""
    m = (t > 0) & (e > 1e-9)
    if m.sum() < 3:
        return float("nan")
    return float(np.polyfit(np.log(t[m]), np.log(e[m]), 1)[0])


# ===========================================================================
def main():
    rng = np.random.default_rng(20260906)
    world = make_world(rng)

    # =======================================================================
    rule("0. 舞台 —— 真値の作り方と検算")
    # =======================================================================
    print(f"世界 {WORLD} x {WORLD} px / フレーム {FR_W} x {FR_H} px / "
          f"テンプレート {TPL} x {TPL} px")
    print(f"追う対象 4 種: {' / '.join(TARGETS)}(構造の違う 4 つ。乱数の斑点だけには頼らない)")

    _c = np.array([300.0, 260.0])
    _th, _s = np.deg2rad(11.0), 1.13
    _p = np.array([[40.0, 30.0], [120.0, 90.0], [5.0, 115.0]])
    _chk1 = np.abs(world_to_frame(frame_to_world(_p, _c, _th, _s), _c, _th, _s) - _p).max()
    print(f"検算 1  フレーム→世界→フレームの往復              最大 {_chk1:.3e} px")

    _tg = TARGETS["一意"]
    _f0 = render(world, _tg, 0.0, 1.0)
    _t0 = crop_template(_f0, O_XY)
    fs.set_match_template(_t0)                      # ★ 穴 (c): グローバル状態
    _pub = fs.op.ncc_locate(_f0)
    _mine = locate_full(_f0, _t0)
    _chk2 = abs(_pub[0] - _mine[0]) + abs(_pub[1] - _mine[1][1]) + abs(_pub[2] - _mine[1][0])
    print(f"検算 2  公開 op ncc_locate と自前の相関マップ        差 {_chk2:.3e}")
    print(f"        (公開 op の返り {np.round(_pub, 6).tolist()} = [相関値, 行, 列]。"
          f"★ 穴 (e) 行列順)")
    _chk3 = abs(_pub[0] - 1.0)
    print(f"検算 3  同じフレームを自分で探すと相関              {_pub[0]:.9f}(1 との差 {_chk3:.1e})")

    fs.set_match_template(None)
    _none = fs.op.ncc_locate(_f0)
    print(f"検算 4  テンプレート未設定だと {np.round(_none, 3).tolist()}(fail-closed。"
          f"ただし「見つからない」と「相関 0」が同じ値)")
    assert _chk1 < 1e-9 and _chk2 < 1e-9 and _chk3 < 1e-9, "舞台の真値が閉じていない"
    print("→ 真値は閉じている。以降のずれはすべて **推定の誤差** である。")

    # =======================================================================
    rule("1. 4 つの対象の素性 —— 追う前に、そのテンプレートが一意かどうか")
    # =======================================================================
    print("動かす前に、1 枚目の中でテンプレートを探させる。正解は必ず中心(相関 1.0)。")
    print("見るのは **2 番目のピーク** —— これが高いほど、少し崩れただけで乗り換える。")
    print()
    print(f"{'対象':<8}{'2 位の相関':>12}{'突出度':>10}{'2 位までの距離':>16}"
          f"{'縁方向の平坦さ':>16}")
    print("-" * 64)
    T0, F0 = {}, {}
    profile = {}
    for name, tg in TARGETS.items():
        f0 = render(world, tg, 0.0, 1.0)
        t0 = crop_template(f0, O_XY)
        T0[name], F0[name] = t0, f0
        corr = ops._ncc_map(f0, t0)
        pk, xy, prom, d2 = peak_and_prominence(corr)
        # 開口問題の指標: ピークから ±3 px の相関の落ち方が最も緩い方向
        r, c = int(round(xy[1])), int(round(xy[0]))
        drops = [1.0 - corr[r + dy * 3, c + dx * 3]
                 for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1))]
        profile[name] = dict(second=pk - prom, prom=prom, d2=d2, flat=min(drops))
        print(f"{name:<8}{pk - prom:>12.4f}{prom:>10.4f}{d2:>16.1f}{min(drops):>16.4f}")
    print("-" * 64)
    print("「縁方向の平坦さ」= ピークから 3 px ずらしたときの相関の落ちが最小の方向の値。")
    print("小さいほど、その方向へずれても相関が下がらない = 位置が決まらない。")
    print(f"→ 繰返 の 2 位は {profile['繰返']['second']:.3f} で、"
          f"しかも {profile['繰返']['d2']:.0f} px 離れている(= 別の字形)。")
    print(f"→ 直線縁 は縁方向の落ちが {profile['直線縁']['flat']:.4f} しかない = 開口問題。")
    print("→ **この表は動かす前に作れる**。追跡が失敗しそうな対象は事前に分かる。")

    # =======================================================================
    rule("2. ゼロ点 —— 更新なし全域探索(対象 4 種 × 軌跡 2 種)")
    # =======================================================================
    print("ゼロ点は「1 枚目のテンプレートを毎フレーム全域探索で当てる。更新しない」。")
    print("軌跡は 40 フレーム、1 フレーム 2.0 px。純並進と、回転 6 度 + 拡大 1.06 倍を足したもの。")
    print()
    print(f"{'対象':<8}{'軌跡':<20}{'平均':>8}{'最悪':>8}{'最終':>8}"
          f"{'壊れ':>7}{'最小ピーク':>12}")
    print("-" * 71)
    SEQ = {}
    zero = {}
    for name in TARGETS:
        for tag, kw in (("純並進", dict()), ("並進+回転6度+1.06倍", dict(rot_deg=6.0, zoom=1.06))):
            fr, tr, _, _ = make_sequence(world, TARGETS[name], n=40, step=2.0, **kw)
            t0 = crop_template(fr[0], tr[0])
            est, pk, pr = run_tracker(fr, t0, tr[0], "static")
            e = err_of(est, tr)
            SEQ[(name, tag)] = (fr, tr, t0)
            zero[(name, tag)] = dict(err=e, peak=pk, prom=pr, est=est)
            print(f"{name:<8}{tag:<20}{e.mean():>8.2f}{e.max():>8.2f}{e[-1]:>8.2f}"
                  f"{int((e > LOST_PX).sum()):>5} /40{pk.min():>12.3f}")
    print("-" * 71)
    print("単位は画素。「壊れ」= 誤差が 5 px を超えたフレーム数。")
    e_pure = zero[("一意", "純並進")]["err"]
    print(f"\n→ 一意 な対象の純並進で 平均 {e_pure.mean():.2f} px。"
          f"**これがこの道具の床** であって 0 ではない。")
    print(f"   ★ 穴 (b): ncc_locate は整数座標しか返さない。真値は副画素なので "
          f"±0.5 px は原理的に消せない。")
    print(f"   実測の内訳: 誤差の 90 % 点 {np.percentile(e_pure, 90):.2f} px、"
          f"最大 {e_pure.max():.2f} px。")
    e_rot = zero[("一意", "並進+回転6度+1.06倍")]["err"]
    print(f"→ **予想は外れた**: 回転 6 度 + 1.06 倍を足しても 平均 "
          f"{e_pure.mean():.2f} → {e_rot.mean():.2f} px で悪化しない。")
    print("   この程度の変形は量子化の床に埋もれる。更新しない系が変形に弱いのは")
    print("   本当だが、**弱くなる境目はもっと先** にある(第 6 章で崖を探す)。")
    print(f"→ 直線縁 は純並進でも 平均 "
          f"{zero[('直線縁', '純並進')]['err'].mean():.2f} px。"
          f"縁に沿った方向が決まらないから(第 1 章の予告どおり)。")

    # =======================================================================
    rule("3. 系の比較 —— 更新するか、予測するか")
    # =======================================================================
    print("対象は 一意。同じ 4 系を **変形の弱い軌跡と強い軌跡の 2 条件** で走らせる。")
    print("1 条件だけで表を作ると「どれが良いか」を言い切ってしまうので、")
    print("**順位が入れ替わることそのもの** を見せる。")
    SYS = [("0 更新なし全域探索(ゼロ点)", dict(mode="static")),
           ("1 毎フレーム更新", dict(mode="update1")),
           ("2 5 フレームごと更新", dict(mode="updatek", update_k=5)),
           ("3 予測つき局所探索(±12)", dict(mode="local", rad=12))]
    COND3 = (("弱い変形(回転 6 度 + 1.06 倍)", dict(rot_deg=6.0, zoom=1.06)),
             ("強い変形(回転 30 度 + 1.35 倍)", dict(rot_deg=30.0, zoom=1.35)))
    ch3 = {}
    for cond, ckw in COND3:
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=40, step=2.0, **ckw)
        t0 = crop_template(fr[0], tr[0])
        print(f"\n[{cond}]")
        print(f"{'系':<28}{'平均':>8}{'最悪':>8}{'最終':>8}{'壊れ':>7}"
              f"{'平均ピーク':>12}{'秒':>8}")
        print("-" * 79)
        for label, kw in SYS:
            t_a = time.perf_counter()
            est, pk, pr = run_tracker(fr, t0, tr[0], **kw)
            dt = time.perf_counter() - t_a
            e = err_of(est, tr)
            ch3[(cond, label)] = dict(err=e, peak=pk, prom=pr, sec=dt)
            print(f"{label:<28}{e.mean():>8.2f}{e.max():>8.2f}{e[-1]:>8.2f}"
                  f"{int((e > LOST_PX).sum()):>5} /40{np.nanmean(pk):>12.3f}{dt:>8.3f}")
        print("-" * 79)
    C_W, C_S = COND3[0][0], COND3[1][0]
    sys_z = ch3[(C_W, "0 更新なし全域探索(ゼロ点)")]
    u1 = ch3[(C_W, "1 毎フレーム更新")]
    u5 = ch3[(C_W, "2 5 フレームごと更新")]
    lo = ch3[(C_W, "3 予測つき局所探索(±12)")]
    sz_s = ch3[(C_S, "0 更新なし全域探索(ゼロ点)")]
    u1_s = ch3[(C_S, "1 毎フレーム更新")]
    print(f"\n→ **順位が入れ替わる**。弱い変形ではゼロ点 {sys_z['err'].mean():.2f} px が")
    print(f"   毎フレーム更新 {u1['err'].mean():.2f} px に勝つ。強い変形では逆で、")
    print(f"   ゼロ点 {sz_s['err'].mean():.2f} px に対し毎フレーム更新 {u1_s['err'].mean():.2f} px。")
    print("   更新は「変形についていく」ことと「丸め誤差を溜めること」を同時にする。")
    print("   どちらが勝つかは **対象がどれだけ変形するか** で決まり、定数では決められない。")
    print(f"→ 弱い変形でも毎フレーム更新の平均ピークは {np.nanmean(u1['peak']):.3f} で、")
    print(f"   ゼロ点の {np.nanmean(sys_z['peak']):.3f} より高い。誤差は逆に大きいのに、である。")
    print("   **自分の直前の切り出しに合わせているのだから、高くて当たり前** ——")
    print("   相関値は「対象に合っているか」ではなく「直前の自分に合っているか」を測っている。")
    print(f"→ 局所探索は全域探索の {sys_z['sec'] / max(lo['sec'], 1e-9):.0f} 倍速い"
          f"({lo['sec'] * 1e3 / 39:.1f} ms/frame 対 {sys_z['sec'] * 1e3 / 39:.1f} ms/frame)。")
    print(f"   弱い変形での精度は {lo['err'].mean():.2f} px でゼロ点 {sys_z['err'].mean():.2f} px と同等 ——")
    print("   **ここでは速さだけを買っている**。精度を買える場面は第 9 章に出る。")
    print(f"→ 5 フレームごと更新は弱い変形で {u5['err'].mean():.2f} px、強い変形で "
          f"{ch3[(C_S, '2 5 フレームごと更新')]['err'].mean():.2f} px。"
          f"最適な間隔は条件で動く(第 8 章)。")

    # =======================================================================
    rule("4. ★ 崖 (a) フレーム間の移動量 —— 局所探索の窓を超えた瞬間")
    # =======================================================================
    print("対象 一意、20 フレーム、純並進。1 フレームの移動量を 1 → 24 px で振る。")
    print("局所探索の窓を 3 通り。予測は定速(前 2 フレームの差)。")
    print()
    rads = (6, 12, 24)
    print(f"{'移動 px':>8}" + "".join(f"{'±' + str(r) + ' 平均':>13}" for r in rads)
          + f"{'全域探索':>12}")
    print("-" * 63)
    ch4 = {}
    for step in (1.0, 2.0, 4.0, 8.0, 12.0, 18.0, 24.0):
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=20, step=step, amp=30.0)
        t0 = crop_template(fr[0], tr[0])
        row = []
        for r in rads:
            est, pk, pr = run_tracker(fr, t0, tr[0], "local", rad=r)
            row.append(err_of(est, tr).mean())
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        ez = err_of(est, tr).mean()
        ch4[step] = (row, ez)
        print(f"{step:>8.0f}" + "".join(f"{v:>13.2f}" for v in row) + f"{ez:>12.2f}")
    print("-" * 63)
    print("→ 定速予測が効いているうちは窓が小さくても壊れない。壊れるのは")
    print("   **予測の残差が窓を超えたとき** で、移動量そのものではない。")
    br = {r: next((s for s in sorted(ch4) if ch4[s][0][i] > LOST_PX), None)
          for i, r in enumerate(rads)}
    for i, r in enumerate(rads):
        print(f"   窓 ±{r:>2}: 崖は {br[r]} px/frame"
              f"{'(この範囲では壊れなかった)' if br[r] is None else ''}")
    print("→ 全域探索は移動量にまったく影響されない(窓が無いのだから当然)。")
    print("   速さと引き換えに **崖を 1 つ買っている** のが局所探索である。")

    print("\n[同じ章のおまけ] 動きぼけ —— 露光中に対象が動くと、テンプレートは変形する。")
    print(f"{'ぼけ px':>8}{'平均誤差':>10}{'最悪':>8}{'平均ピーク':>12}")
    print("-" * 38)
    ch4b = {}
    for bl in (0.0, 2.0, 4.0, 8.0, 14.0):
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=14, step=4.0, amp=30.0,
                                     blur_px=bl)
        t0 = crop_template(F0["一意"], O_XY)         # ★ ぼけていない 1 枚目を使う
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        ch4b[bl] = (e, pk)
        print(f"{bl:>8.0f}{e.mean():>10.2f}{e.max():>8.2f}{np.nanmean(pk):>12.3f}")
    print("-" * 38)
    print(f"→ ぼけ 14 px でピークは {np.nanmean(ch4b[14.0][1]):.3f} まで下がるが、"
          f"誤差は {ch4b[14.0][0].mean():.2f} px。")
    print("   **ピークの低下は誤差の増加より早い** —— ここではピーク値が正直に働く。")

    # =======================================================================
    rule("5. ★ 崖 (b) 遮蔽 —— どこで見失うか、そして誤って「見つけた」と言う率")
    # =======================================================================
    print("対象 一意、30 フレーム、純並進 2 px。3 フレーム目から左に平坦な遮蔽物が入る。")
    print("遮蔽率はテンプレート面積に対する割合。しきい値は **遮蔽 0 % の系で校正** する")
    print("(実運用でできるのはそれだけ。壊れたデータで校正はできない)。")
    fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=30, step=2.0)
    t0 = crop_template(fr[0], tr[0])
    est, pk0, pr0 = run_tracker(fr, t0, tr[0], "static")
    THR_PK = float(np.nanmin(pk0[1:]))
    THR_PR = float(np.nanmin(pr0[1:]))
    print(f"\n校正: 遮蔽なしの最小ピーク {THR_PK:.3f} / 最小突出度 {THR_PR:.3f} をしきい値に。")
    print()
    print(f"{'遮蔽 %':>7}{'平均誤差':>10}{'最悪':>8}{'壊れ':>8}{'平均ピーク':>12}"
          f"{'平均突出度':>12}{'誤って見つけた':>16}")
    print("-" * 73)
    ch5 = {}
    for f_occ in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=30, step=2.0, occl=f_occ)
        t0 = crop_template(fr[0], tr[0])
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        m = np.arange(len(e)) >= 3                      # 遮蔽が入っているフレームだけ
        lost = e > LOST_PX
        false_found = int((lost & m & (pk >= THR_PK)).sum())
        n_lost = int((lost & m).sum())
        ch5[f_occ] = dict(err=e, peak=pk, prom=pr, lost=lost, mask=m)
        print(f"{f_occ * 100:>7.0f}{e.mean():>10.2f}{e.max():>8.2f}"
              f"{n_lost:>6} /27{np.nanmean(pk[m]):>12.3f}{np.nanmean(pr[m]):>12.3f}"
              f"{false_found:>10} /{n_lost:<3}")
    print("-" * 73)
    print("「誤って見つけた」= 実際は 5 px 以上ずれているのにピークがしきい値以上だった数")
    print("  / ずれていたフレーム数。分母が 0 の行は「一度もずれなかった」。")
    occ_l = sorted(f for f in ch5 if (ch5[f]["err"] > LOST_PX).any())
    cliff = occ_l[0] if occ_l else None
    prev = max([f for f in ch5 if cliff is not None and f < cliff], default=None)
    print(f"\n→ 崖は遮蔽 {0 if prev is None else prev * 100:.0f} % と "
          f"{'(壊れなかった)' if cliff is None else format(cliff * 100, '.0f') + ' %'} の間。")
    print("   それ未満は **遮蔽されていない側だけで当たる** —— 半分隠れても位置は出る。")
    print(f"→ ピーク値は遮蔽率とともに単調に下がる"
          f"({np.nanmean(ch5[0.0]['peak'][3:]):.3f} → {np.nanmean(ch5[0.8]['peak'][3:]):.3f})。")
    print("   **平坦な遮蔽物に限れば ピーク値は正直** である(第 10 章で数値化する)。")

    print("\n[同じ章の本番] そっくりな別物体が一緒に流れてくる場合。")
    print("同じ部品が 2 つ並んで流れる産業の場面。1 枚目のテンプレートを少しぼかした")
    print("複製を、真の対象から 51 px 離れた位置に一緒に動かす。遮蔽率は真の対象にだけ掛ける。")
    print()
    print(f"{'遮蔽 %':>7}{'平均誤差':>10}{'最悪':>8}{'壊れ':>8}{'平均ピーク':>12}"
          f"{'平均突出度':>12}{'誤報(ピーク)':>15}{'誤報(突出度)':>15}")
    print("-" * 91)
    ch5t = {}
    for f_occ in (0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8):
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=30, step=2.0,
                                     occl=f_occ, twin=True)
        t0 = crop_template(fr[0], tr[0])
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        m = np.arange(len(e)) >= 3
        lost = e > LOST_PX
        n_lost = int((lost & m).sum())
        ff = int((lost & m & (pk >= THR_PK)).sum())
        ffp = int((lost & m & (np.nan_to_num(pr) >= THR_PR)).sum())
        ch5t[f_occ] = dict(err=e, peak=pk, prom=pr, lost=lost, mask=m,
                           ff=ff, ffp=ffp, nl=n_lost)
        print(f"{f_occ * 100:>7.0f}{e.mean():>10.2f}{e.max():>8.2f}"
              f"{n_lost:>6} /27{np.nanmean(pk[m]):>12.3f}{np.nanmean(pr[m]):>12.3f}"
              f"{ff:>10} /{n_lost:<4}{ffp:>10} /{n_lost:<4}")
    print("-" * 91)
    print(f"「誤報」= ずれている(5 px 超)のにその量が校正しきい値以上だったフレーム数。")
    tw_l = sorted(f for f in ch5t if ch5t[f]["nl"] > 0)
    tw_cliff = tw_l[0] if tw_l else None
    ff_tot = sum(ch5t[f]["ff"] for f in ch5t)
    ffp_tot = sum(ch5t[f]["ffp"] for f in ch5t)
    nl_tot = sum(ch5t[f]["nl"] for f in ch5t)
    _maj = next((f for f in sorted(ch5t) if ch5t[f]["nl"] >= 14), None)
    print(f"\n→ 崖は遮蔽 {'(壊れなかった)' if tw_cliff is None else format(tw_cliff * 100, '.0f') + ' %'}"
          f"(半数を超えるのは {'—' if _maj is None else format(_maj * 100, '.0f') + ' %'})。")
    print(f"   平坦な遮蔽物の崖({'—' if cliff is None else format(cliff * 100, '.0f') + ' %'})"
          f"より **はるかに手前に来る** ——")
    print("   **同型の物体が視野にいるだけで既に危ない**。真の対象がほんの少し崩れた瞬間に、")
    print("   崩れていない複製のほうが相関が高くなって乗り換える。")
    if nl_tot:
        print(f"→ **ここでピーク値は嘘をつく**。ずれていた {nl_tot} フレームのうち "
              f"{ff_tot} フレーム({100.0 * ff_tot / nl_tot:.0f} %)で")
        print(f"   ピークが校正しきい値 {THR_PK:.3f} 以上 = 「見つけた」と報告する。")
        _tf = max(ch5t)
        print(f"   遮蔽 {_tf * 100:.0f} % の平均ピークは {np.nanmean(ch5t[_tf]['peak'][3:]):.3f} で、")
        print(f"   平坦な遮蔽物の同じ条件 {np.nanmean(ch5[_tf]['peak'][3:]):.3f} より **高い**。")
        _lo = min(ch5t, key=lambda f: np.nanmean(ch5t[f]["prom"][3:]))
        print(f"→ 突出度はここでは効く: 誤報 {ffp_tot} / {nl_tot} フレーム "
              f"(しきい値 {THR_PR:.3f})。")
        print(f"   ただし **効きしろは細っていく**。遮蔽 {_lo * 100:.0f} % で "
              f"{np.nanmean(ch5t[_lo]['prom'][3:]):.3f} だった突出度は、")
        print(f"   遮蔽 {_tf * 100:.0f} % では {np.nanmean(ch5t[_tf]['prom'][3:]):.3f} まで "
              f"**戻ってくる**(しきい値 {THR_PR:.3f} まであと "
              f"{THR_PR - np.nanmean(ch5t[_tf]['prom'][3:]):.3f})。")
        print("   真の対象が消えてしまえば、間違ったロックには競合が無いので曖昧さも無い。")
        print("   **突出度が測っているのは曖昧さであって、正しさではない** ——")
        print("   同じ性質が第 9 章では逆方向に出る(窓を狭めると自信だけが増す)。")

    # =======================================================================
    rule("6. ★ 崖 (c) スケールと回転 —— 並進しか探さない追跡はどこまで耐えるか")
    # =======================================================================
    print("24 フレーム、純並進 2 px に、総拡大率 / 総回転角だけを足して掃引する。")
    print(f"\n{'総拡大率':>10}{'平均誤差':>10}{'最悪':>8}{'最終ピーク':>12}"
          f"{'壊れ':>8}")
    print("-" * 48)
    ch6s = {}
    for zf in (1.0, 1.05, 1.10, 1.20, 1.35, 1.50, 1.80):
        fr, tr, _, sc = make_sequence(world, TARGETS["一意"], n=24, step=2.0, zoom=zf)
        t0 = crop_template(fr[0], tr[0])
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        ch6s[zf] = (e, pk)
        print(f"{zf:>10.2f}{e.mean():>10.2f}{e.max():>8.2f}{pk[-1]:>12.3f}"
              f"{int((e > LOST_PX).sum()):>6} /24")
    print("-" * 48)
    print(f"\n{'総回転度':>10}{'平均誤差':>10}{'最悪':>8}{'最終ピーク':>12}{'壊れ':>8}")
    print("-" * 48)
    ch6r = {}
    for rd in (0.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0):
        fr, tr, an, _ = make_sequence(world, TARGETS["一意"], n=24, step=2.0, rot_deg=rd)
        t0 = crop_template(fr[0], tr[0])
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        ch6r[rd] = (e, pk, fr, tr, an, t0)
        print(f"{rd:>10.0f}{e.mean():>10.2f}{e.max():>8.2f}{pk[-1]:>12.3f}"
              f"{int((e > LOST_PX).sum()):>6} /24")
    print("-" * 48)
    z_cliff = next((q for q in sorted(ch6s) if (ch6s[q][0] > LOST_PX).any()), None)
    r_cliff = next((r for r in sorted(ch6r) if (ch6r[r][0] > LOST_PX).any()), None)
    print(f"→ 拡大の崖は {z_cliff} 倍(それ未満では壊れない)。"
          f"回転の崖は {r_cliff} 度。")
    print("   どちらも **ピークが先に落ちてから誤差が跳ねる** ので、順序としては気づける。")

    print("\n[回転を探す op を当ててみる] shape_locate は 30 度刻みでテンプレートを回して探す。")
    print(f"{'真の角度':>10}{'ncc 位置誤差':>14}{'ncc ピーク':>12}"
          f"{'shape 位置誤差':>16}{'shape 角':>10}{'shape ピーク':>14}")
    print("-" * 76)
    ch6h = []
    for rd in (0.0, 10.0, 20.0, 30.0, 45.0, 60.0):
        fr, tr, an, _ = make_sequence(world, TARGETS["一意"], n=6, step=2.0, rot_deg=rd)
        t0 = crop_template(fr[0], tr[0])
        img, true_xy, true_ang = fr[-1], tr[-1], an[-1]
        pk_n, xy_n, _, _ = locate_full(img, t0)
        fs.set_match_template(t0)                    # ★ 穴 (c)
        s = fs.op.shape_locate(img)
        e_n = float(np.linalg.norm(xy_n - true_xy))
        e_s = float(np.hypot(s[2] - true_xy[0], s[1] - true_xy[1]))
        ch6h.append((true_ang, e_n, pk_n, e_s, s[3], s[0]))
        print(f"{true_ang:>10.1f}{e_n:>14.2f}{pk_n:>12.3f}{e_s:>16.2f}"
              f"{s[3]:>10.0f}{s[0]:>14.3f}")
    print("-" * 76)
    print("★ 穴 (f): 角度は 30 度刻み固定(引数が無い)。真の角度 10 度・20 度はどちらも")
    print("   0 度か 30 度に丸められる。さらに回転テンプレートを reshape=False で作るので")
    print("   **四隅がゼロで埋まり**、0 度以外は相関値が構造的に下がる。実測では")
    print(f"   0 度の shape ピーク {ch6h[0][5]:.3f} に対し 30 度で {ch6h[3][5]:.3f}。")
    print("   0 度でも ncc と一致しないのは、この四隅のゼロが効いているため。")

    # =======================================================================
    rule("7. ★ 崖 (d) 照明変化 —— NCC は本当に明るさ変化に強いのか")
    # =======================================================================
    print("24 フレーム、純並進 2 px。輝度を gain·I + offset に置き換える(真値は不変)。")
    print("NCC は定義上、平均を引いて分散で割るので **一次の輝度変化には不変** のはず。")
    print(f"\n{'gain':>7}{'offset':>9}{'平均誤差':>10}{'最悪':>8}{'平均ピーク':>12}"
          f"{'飽和画素 %':>12}{'階調数':>10}")
    print("-" * 68)
    ch7 = {}
    LIN = ((1.0, 0.0), (1.6, 0.0), (0.4, 0.0), (1.0, 0.30), (1.0, -0.20))
    for g, off in LIN + ((2.2, -0.30), (0.15, 0.0), (0.06, 0.0), (2.6, 0.25)):
        fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=24, step=2.0,
                                     gain=g, offset=off)
        t0 = crop_template(fr[0], tr[0])
        est, pk, pr = run_tracker(fr, t0, tr[0], "static")
        e = err_of(est, tr)
        sat = 100.0 * np.mean([np.mean((f <= 0.0) | (f >= 1.0)) for f in fr])
        lev = float(np.mean([len(np.unique(f)) for f in fr]))
        ch7[(g, off)] = (e, pk, sat, lev)
        print(f"{g:>7.2f}{off:>9.2f}{e.mean():>10.2f}{e.max():>8.2f}"
              f"{np.nanmean(pk):>12.4f}{sat:>12.2f}{lev:>10.0f}")
    print("-" * 68)
    base = ch7[(1.0, 0.0)]
    lin_max = max(ch7[k][0].mean() for k in LIN)
    worst = max(ch7, key=lambda k: ch7[k][0].mean())
    print(f"→ **強い**: 飽和しない範囲(表の上 {len(LIN)} 行、飽和 "
          f"{max(ch7[k][2] for k in LIN):.2f} % 以下)では")
    print(f"   平均誤差 {min(ch7[k][0].mean() for k in LIN):.2f}〜{lin_max:.2f} px。"
          f"素の {base[0].mean():.2f} px と実質同じで、")
    print("   ピークもほとんど動かない。**一次の輝度変化に対する不変性は本物**である。")
    print(f"→ **弱い**: 崩れたのは飽和だけ。gain={worst[0]} offset={worst[1]} は")
    print(f"   飽和 {ch7[worst][2]:.2f} % で 平均誤差 {ch7[worst][0].mean():.2f} px、"
          f"ピーク {np.nanmean(ch7[worst][1]):.3f}。")
    print("   飽和は輝度の一次変換ではなく **情報を捨てる操作** なので、NCC の不変性は")
    print("   そもそも掛からない。「照明に強い」の射程はここで終わる。")
    _lc = ch7[(0.06, 0.0)]
    print(f"→ **予想が外れたほう**: 低コントラスト gain=0.06 は階調が {_lc[3]:.0f} 段しか")
    print(f"   残らずピークが {np.nanmean(_lc[1]):.3f} まで落ちるのに、平均誤差は "
          f"{_lc[0].mean():.2f} px で **壊れない**。")
    print("   量子化が奪うのは「相関の高さ」であって「ピークの位置」ではなかった。")
    print("   ★ これは第 10 章に直結する: **ピークが低い = 失敗、ではない**。")
    print(f"   ここでピークは {np.nanmean(_lc[1]):.3f} と警報レベルなのに位置は正しく、")
    print("   逆にそっくりな別物体(第 5 章)ではピーク 0.9 台で位置が 51 px 間違っている。")

    # =======================================================================
    rule("8. ★ 崖 (e) 更新間隔とドリフト —— log-log の傾きを実測する")
    # =======================================================================
    print("対象 一意、64 フレーム、純並進 1.5 px。雑音の種を 3 つ振って平均する")
    print("(1 本の軌跡だけだと、たまたまの丸め方向で傾きが変わる)。")
    print()
    print(f"{'更新間隔':<14}{'平均誤差':>10}{'最終誤差':>10}{'最悪':>8}"
          f"{'log-log 傾き':>14}{'平均ピーク':>12}")
    print("-" * 68)
    ch8 = {}
    NF = 64
    tt = np.arange(NF, dtype=float)
    for k, label in ((1, "毎フレーム"), (2, "2 フレーム"), (4, "4 フレーム"),
                     (8, "8 フレーム"), (16, "16 フレーム"), (None, "更新なし")):
        acc, pks = [], []
        for sd in range(3):
            fr, tr, _, _ = make_sequence(world, TARGETS["一意"], n=NF, step=1.5,
                                         amp=26.0, seed=sd)
            t0 = crop_template(fr[0], tr[0])
            if k is None:
                est, pk, pr = run_tracker(fr, t0, tr[0], "static")
            elif k == 1:
                est, pk, pr = run_tracker(fr, t0, tr[0], "update1")
            else:
                est, pk, pr = run_tracker(fr, t0, tr[0], "updatek", update_k=k)
            acc.append(err_of(est, tr))
            pks.append(pk)
        e = np.mean(acc, axis=0)
        slope = loglog_slope(tt, e)
        ch8[label] = dict(err=e, slope=slope, peak=np.mean(pks, axis=0),
                          raw_err=acc, raw_peak=pks)
        print(f"{label:<14}{e.mean():>10.2f}{e[-1]:>10.2f}{e.max():>8.2f}"
              f"{slope:>14.3f}{np.nanmean(np.mean(pks, axis=0)):>12.3f}")
    print("-" * 68)
    s1 = ch8["毎フレーム"]["slope"]
    print(f"\n→ 毎フレーム更新のドリフトは log-log の傾き **{s1:.3f}**。")
    print(f"   独立な丸め誤差のランダムウォークなら 0.5、毎段同じ向きに偏るなら 1.0。")
    print(f"   実測 {s1:.3f} は {'偏りが支配的' if s1 > 0.75 else 'ランダムウォーク寄り' if s1 < 0.65 else '両者の中間'}"
          f" —— 整数丸めが動きの向きに対して系統的に働くため。")
    print(f"→ 更新なしはドリフトしない(傾き {ch8['更新なし']['slope']:.3f}、"
          f"平均 {ch8['更新なし']['err'].mean():.2f} px)。")
    best = min((lab for lab in ch8), key=lambda lab: ch8[lab]["err"].mean())
    print(f"→ この条件(純並進・変形なし)での最良は **{best}**"
          f"({ch8[best]['err'].mean():.2f} px)。")
    print(f"   しかし第 3 章の強い変形では 毎フレーム更新 {u1_s['err'].mean():.2f} px が")
    print(f"   更新なし {sz_s['err'].mean():.2f} px を大きく上回った。"
          f"**最適な更新間隔は条件で動く** —— 定数で決め打ちできない。")
    print("   決めているのは「対象がどれだけ変形するか」対「1 回の更新で入る丸め誤差」の比。")

    # =======================================================================
    rule("9. ★ 崖 (f) 繰り返し模様 —— 誤ロックは窓の広さで決まる")
    # =======================================================================
    print("対象 繰返(同じ字形が周期 22 px)。24 フレーム、純並進 2 px。")
    print("探索範囲だけを変える。全域探索から、半径を狭めた局所探索まで。")
    print()
    print(f"{'探索':<18}{'平均誤差':>10}{'最悪':>8}{'壊れ':>8}"
          f"{'平均ピーク':>12}{'平均突出度':>12}")
    print("-" * 68)
    fr, tr, _, _ = make_sequence(world, TARGETS["繰返"], n=24, step=2.0)
    t0 = crop_template(fr[0], tr[0])
    ch9 = {}
    for label, kw in (("全域探索", dict(mode="static")),
                      ("局所 ±30", dict(mode="local", rad=30)),
                      ("局所 ±20", dict(mode="local", rad=20)),
                      ("局所 ±12", dict(mode="local", rad=12)),
                      ("局所 ±6", dict(mode="local", rad=6))):
        est, pk, pr = run_tracker(fr, t0, tr[0], **kw)
        e = err_of(est, tr)
        ch9[label] = dict(err=e, peak=pk, prom=pr)
        print(f"{label:<18}{e.mean():>10.2f}{e.max():>8.2f}"
              f"{int((e > LOST_PX).sum()):>6} /24{np.nanmean(pk):>12.3f}"
              f"{np.nanmean(pr):>12.3f}")
    print("-" * 68)
    g_full, g_narrow = ch9["全域探索"], ch9["局所 ±6"]
    print(f"\n→ 全域探索は平均 {g_full['err'].mean():.2f} px / 最悪 "
          f"{g_full['err'].max():.2f} px。**ピークは {np.nanmean(g_full['peak']):.3f} と高いまま**。")
    print(f"→ 窓を周期(22 px)より狭くすると平均 {g_narrow['err'].mean():.2f} px。")
    print("   第 3 章では局所探索は速いだけだったが、ここでは **精度そのものを買っている**。")
    print("   窓の役目は速さではなく「隣の周期を候補から外すこと」。")
    print(f"→ 突出度は全域 {np.nanmean(g_full['prom']):.3f} に対し狭い窓 "
          f"{np.nanmean(g_narrow['prom']):.3f}。")
    print("   狭い窓では 2 位の候補がそもそも視野に入らないので、**突出度は自動的に高くなる**。")
    _bad = ch9["局所 ±20"]
    print(f"   ★ その罠が数字に出ている: 局所 ±20 は突出度 {np.nanmean(_bad['prom']):.3f} と")
    print(f"   全域の {np.nanmean(g_full['prom']):.3f} よりはるかに高いのに、"
          f"{int((_bad['err'] > LOST_PX).sum())} / {len(_bad['err'])} フレームで")
    print("   ずれている。**窓を狭めるほど自信が増し、正しさは増えない**。")
    print("   突出度を信頼度に使うなら、窓の大きさを固定して校正しないと意味を持たない。")

    # =======================================================================
    rule("10. ★★ 見失ったことに気づけるか —— ピーク値 vs 突出度")
    # =======================================================================
    print("これまでに集めたフレームを条件ごとに束ね、「誤差 5 px 超」を当てられるかを測る。")
    print("識別力は AUC(0.5 = 無力、1.0 = 完全)。値が **0.5 を下回ったら、")
    print("その量は嘘の側で高く出ている** —— 使うと逆効果になる。")
    print()
    bundles = {}
    p_occ = np.concatenate([ch5[f]["peak"][3:] for f in ch5])
    r_occ = np.concatenate([ch5[f]["prom"][3:] for f in ch5])
    l_occ = np.concatenate([(ch5[f]["err"][3:] > LOST_PX) for f in ch5])
    bundles["遮蔽 0-80 %"] = (p_occ, r_occ, l_occ)

    p_amb = np.concatenate([zero[k]["peak"][1:] for k in zero])
    r_amb = np.concatenate([zero[k]["prom"][1:] for k in zero])
    l_amb = np.concatenate([(zero[k]["err"][1:] > LOST_PX) for k in zero])
    bundles["紛らわしい対象(全域)"] = (p_amb, r_amb, l_amb)

    p_rep, r_rep, l_rep = [], [], []
    for lab in ch9:
        p_rep.append(ch9[lab]["peak"][1:])
        r_rep.append(ch9[lab]["prom"][1:])
        l_rep.append(ch9[lab]["err"][1:] > LOST_PX)
    bundles["繰返・窓を混ぜる"] = (np.concatenate(p_rep), np.concatenate(r_rep),
                            np.concatenate(l_rep))

    p_sc = np.concatenate([ch6s[q][1][1:] for q in ch6s] + [ch6r[r][1][1:] for r in ch6r])
    l_sc = np.concatenate([(ch6s[q][0][1:] > LOST_PX) for q in ch6s]
                          + [(ch6r[r][0][1:] > LOST_PX) for r in ch6r])
    bundles["拡大・回転"] = (p_sc, None, l_sc)

    p_tw = np.concatenate([ch5t[f]["peak"][3:] for f in ch5t])
    r_tw = np.concatenate([ch5t[f]["prom"][3:] for f in ch5t])
    l_tw = np.concatenate([(ch5t[f]["err"][3:] > LOST_PX) for f in ch5t])
    bundles["そっくりな別物体"] = (p_tw, r_tw, l_tw)

    e_dr = np.concatenate([e[1:] for e in ch8["毎フレーム"]["raw_err"]])
    p_dr = np.concatenate([p[1:] for p in ch8["毎フレーム"]["raw_peak"]])
    bundles["更新によるドリフト"] = (p_dr, None, e_dr > LOST_PX)

    print(f"{'条件':<20}{'フレーム':>9}{'うち失敗':>9}{'ピーク値 AUC':>15}"
          f"{'突出度 AUC':>13}")
    print("-" * 66)
    auc_tbl = {}
    for name, (pkv, prv, lost) in bundles.items():
        a_pk = auc_lost(-np.asarray(pkv, float), np.asarray(lost))
        a_pr = auc_lost(-np.asarray(prv, float), np.asarray(lost)) if prv is not None \
            else float("nan")
        auc_tbl[name] = (a_pk, a_pr)
        print(f"{name:<20}{len(lost):>9}{int(lost.sum()):>9}{a_pk:>15.3f}"
              f"{'—' if prv is None else format(a_pr, '.3f'):>13}")
    print("-" * 66)
    print("(拡大・回転 と ドリフト の突出度は出さない —— どちらも自分自身の肩が 2 位になり、")
    print(" 「別の候補との差」という意味を失うため。無意味な数字を並べない。)")
    a_occ, a_amb = auc_tbl["遮蔽 0-80 %"], auc_tbl["紛らわしい対象(全域)"]
    a_rep = auc_tbl["繰返・窓を混ぜる"]
    a_tw, a_dr = auc_tbl["そっくりな別物体"], auc_tbl["更新によるドリフト"]
    drift_lost = bundles["更新によるドリフト"][2]
    print(f"\n【結論 1】**得意な崖が逆である。片方だけを信頼度にはできない。**")
    print(f"  平坦な遮蔽:       ピーク値 {a_occ[0]:.3f} / 突出度 {a_occ[1]:.3f}"
          f"   → ピーク値の勝ち")
    print(f"  紛らわしい対象:   ピーク値 {a_amb[0]:.3f} / 突出度 {a_amb[1]:.3f}"
          f"   → 突出度の勝ち")
    print("  遮蔽では相関が素直に落ちるのでピーク値が効く。繰り返し模様・直線の縁・")
    print("  片側だけのテクスチャでは **正解と同じ高さのピークが別の場所に立つ** ので")
    print(f"  ピーク値はほとんど何も言えない({a_amb[0]:.3f})。2 位との差だけが見分ける。")
    print(f"\n【結論 2】**AUC(順位)としきい値(運用点)は別物**。そっくりな別物体では")
    print(f"  ピーク値の AUC は {a_tw[0]:.3f} —— 順位づけとしては完璧に近い。ところが")
    print(f"  遮蔽なしで校正したしきい値 {THR_PK:.3f} を当てると、ずれていた "
          f"{nl_tot} フレームの")
    print(f"  {ff_tot} フレーム全部が「見つけた」を通る。**順位は正しいのに運用点が使えない**。")
    print("  AUC だけを見て「この信頼度は使える」と言うと、現場では 1 件も止められない。")
    print(f"\n【結論 3】**突出度は曖昧さを測る量で、正しさを測る量ではない。**")
    print(f"  そっくりな別物体の突出度 AUC は {a_tw[1]:.3f} —— 0.5 を大きく下回る = 逆相関。")
    print("  真の対象が遮蔽で消えたあとは、間違ったロックに競合が無いので突出度が戻る。")
    _w20, _wf = ch9["局所 ±20"], ch9["全域探索"]
    print(f"  探索窓でも同じことが起きる。繰り返し模様で 局所 ±20 の突出度は "
          f"{np.nanmean(_w20['prom']):.3f} で")
    print(f"  全域探索の {np.nanmean(_wf['prom']):.3f} よりはるかに高いのに、"
          f"{int((_w20['err'] > LOST_PX).sum())} / {len(_w20['err'])} フレームずれている。")
    print(f"  ただし束全体の AUC は {a_rep[1]:.3f} で、平均としては効いている ——")
    print("  **効くのに、効かない場合の当て方が分からない** のがこの量のたちの悪さである。")
    print("  窓を変えたら校正しなおすしかない(窓を狭めれば 2 位は視野から消えるので)。")
    print(f"\n【結論 4】**ドリフトはどちらでも検出できない。** 毎フレーム更新の")
    print(f"  ピーク値 AUC {a_dr[0]:.3f}"
          f"({'0.5 を下回った = 逆相関' if a_dr[0] < 0.5 else '無力'})。"
          f"ずれているフレームの平均ピーク")
    print(f"  {np.nanmean(p_dr[drift_lost]):.4f} に対し、合っているフレームは "
          f"{np.nanmean(p_dr[~drift_lost]):.4f} —— **ずれている側が高い**。")
    print("  更新した追跡は「直前の自分」に合わせているので、対象から離れるほど")
    print("  自分自身とはよく合う。ここで必要なのは相関の別の測り方ではなく、")
    print("  **別の観測**(1 枚目のテンプレートとの照合を並走させる / 往復追跡)である。")
    print(f"\n【結論 5】1 本のしきい値では覆えない。平坦な遮蔽で校正した "
          f"ピーク {THR_PK:.3f} を")
    _p9, _e9 = ch9["全域探索"]["peak"][1:], ch9["全域探索"]["err"][1:]
    print(f"  繰り返し模様に当てると {int((_p9 >= THR_PK).sum())} / {len(_p9)} フレームが"
          f"「見つけた」になり、")
    print(f"  そのうち {int(((_p9 >= THR_PK) & (_e9 > LOST_PX)).sum())} フレームは実際にはずれている。")
    print(f"  同じしきい値を そっくりな別物体 に当てると {ff_tot} / {nl_tot}、")
    print(f"  突出度のしきい値 {THR_PR:.3f} でも {ffp_tot} / {nl_tot} が通る。")
    print("  信頼度は **崖の種類ごとに** 校正しなければならず、しかも遭う崖は事前に選べない。")

    # =======================================================================
    rule("11. 時間推移 —— 1 つの数字にまとめない")
    # =======================================================================
    print(f"第 3 章の 4 系を、平均でなく時間で並べる({C_S})。")
    print()
    hdr = f"{'frame':>6}" + "".join(f"{lab.split()[0]:>10}" for lab, _ in SYS)
    print(hdr + f"{'ゼロ点ピーク':>14}{'毎更新ピーク':>14}")
    print("-" * (len(hdr) + 28))
    for t in (0, 5, 10, 15, 20, 25, 30, 35, 39):
        line = f"{t:>6}"
        for lab, _ in SYS:
            line += f"{ch3[(C_S, lab)]['err'][t]:>10.2f}"
        line += f"{ch3[(C_S, SYS[0][0])]['peak'][t]:>14.4f}"
        line += f"{ch3[(C_S, SYS[1][0])]['peak'][t]:>14.4f}"
        print(line)
    print("-" * (len(hdr) + 28))
    print("列は誤差[px]。0/1/2/3 は第 3 章の系番号。")
    z_e = ch3[(C_S, SYS[0][0])]["err"]
    t_cross = next((t for t in range(len(z_e)) if z_e[t] > LOST_PX), None)
    if t_cross is None:
        print("\n→ ゼロ点はこの条件では 5 px を超えなかった。")
    else:
        print(f"\n→ ゼロ点が 5 px を超えるのはフレーム {t_cross}。そのときピークは "
              f"{ch3[(C_S, SYS[0][0])]['peak'][t_cross]:.4f}。")
    print("   平均だけを見ていると **いつ壊れたか** が消える。壊れる前に")
    print("   ピークが落ちているかどうかも、時間で並べて初めて分かる。")
    dr = ch8["毎フレーム"]
    print(f"→ 毎フレーム更新のドリフト(第 8 章、純並進 64 フレーム)は"
          f"「壊れた瞬間」が無い:")
    print(f"   誤差 {np.round(dr['err'][::8], 2).tolist()}(8 フレームおき)")
    print(f"   ピーク {np.round(dr['peak'][::8], 3).tolist()}")
    print("   誤差だけが単調に伸び、ピークは最後まで動かない。**時間推移でも見えない崖**。")
    print(f"→ 遮蔽 70 % + そっくりな別物体: 誤差 "
          f"{np.round(ch5t[0.7]['err'][::6], 1).tolist()}(6 フレームおき)")
    print(f"   ピーク {np.round(ch5t[0.7]['peak'][::6], 3).tolist()} / "
          f"突出度 {np.round(ch5t[0.7]['prom'][::6], 3).tolist()}")
    print("   誤差が跳ねた瞬間にピークは高いまま、**突出度だけが落ちる**。")

    # =======================================================================
    rule("12. 速度と、測らなかったこと")
    # =======================================================================
    n_full = 200
    _img = SEQ[("一意", "純並進")][0][0]
    _t = SEQ[("一意", "純並進")][2]
    t_a = time.perf_counter()
    for _ in range(n_full):
        ops._ncc_map(_img, _t)
    t_full = (time.perf_counter() - t_a) / n_full
    t_a = time.perf_counter()
    for _ in range(n_full):
        locate_local(_img, _t, O_XY, 12)
    t_loc = (time.perf_counter() - t_a) / n_full
    print(f"全域探索 (160x120, テンプレート 25x25)   {t_full * 1e3:6.2f} ms/frame "
          f"= {1.0 / t_full:6.0f} fps")
    print(f"局所探索 (±12 px)                        {t_loc * 1e3:6.2f} ms/frame "
          f"= {1.0 / t_loc:6.0f} fps({t_full / t_loc:.0f} 倍速い)")
    print("\n測っていないこと(この PoC の主張が及ばない範囲):")
    print("  * 実写。ここは合成なので雑音は加法ガウス、遮蔽は平坦な帯、動きぼけは一様。")
    print("    実写の圧縮ノイズ・自動露出・ローリングシャッターは入っていない。")
    print("  * カラー。すべて 1 チャンネル。色を使えば繰り返し模様の一部は解ける。")
    print("  * 複数対象・再検出。見失った後にどう復帰するかは扱っていない。")
    print("  * 対象そのものの変形(非剛体)。ここでの変形は相似変換だけ。")
    print("  * 副画素での当てはめ。★ 穴 (b) のとおり道具側に入口が無いので、")
    print("    「あれば床がどれだけ下がるか」は測っていない(提案は末尾)。")

    # =======================================================================
    rule("道具の穴(op 本体は直していない)")
    # =======================================================================
    print("(a) ncc_locate が相関マップを返さない → 突出度が公開 API で計算できない。")
    print("    第 10 章の主題(繰り返し模様の誤ロック検出)は公開 API の外にある。")
    print("(b) 2 次元だけ副画素が無い。accel_match.ncc_locate_3d は subvoxel=True を持ち、")
    print("    ncc_locate_3d_pyramid まであるのに、2 次元は整数座標のみ。")
    print(f"    実測の床: 純並進・変形なしで平均 {e_pure.mean():.2f} px。")
    print("(c) テンプレートがグローバル状態(set_match_template)。追跡は毎フレーム")
    print("    差し替える処理なので、この設計と最も相性が悪い。")
    print("(d) 探索範囲を渡せない。局所探索は呼ぶ側が画像を切るしかなく、")
    print("    切り出しが小さいと full-overlap 位置が消えて黙って [0,0,0] が返る。")
    print("(e) 返りは (行, 列)。幾何側の (x, y) と取り違えても例外は出ない。")
    print("(f) shape_locate の角度刻みは 30 度固定(引数なし)+ 回転テンプレートの")
    print(f"    四隅がゼロ埋め。実測で 0 度 {ch6h[0][5]:.3f} → 30 度 {ch6h[3][5]:.3f}。")
    print("(g) 追跡の系(更新方針・予測・見失い判定)が無い。第 3 章の 4 系は自前。")
    print("(h) 信頼度の語彙が無い。返る相関値は第 10 章のとおり条件で嘘をつく。")

    # =======================================================================
    # 結論を assert で固定する
    # =======================================================================
    # (1) 舞台は閉じている(上で assert 済み)
    # (2) ゼロ点には床がある —— 整数座標の量子化(★ 穴 b)
    assert 0.05 < e_pure.mean() < 2.0, f"純並進の床が想定外 ({e_pure.mean():.3f} px)"
    # (3) 弱い変形はゼロ点を悪化させない(予想が外れた側を固定する)
    assert e_rot.mean() < 2.0, "回転 6 度 + 1.06 倍でゼロ点が崩れた(想定外)"
    # (3b) 強い変形ならゼロ点は崩れ、更新が上回る —— 順位が入れ替わる
    assert sz_s["err"].mean() > 3.0 * u1_s["err"].mean(), "強い変形で順位が入れ替わらない"
    assert sys_z["err"].mean() < u1["err"].mean(), "弱い変形でゼロ点が負けた"
    # (4) 毎フレーム更新はドリフトし、log-log で伸びる
    assert ch8["毎フレーム"]["err"][-1] > 3.0 * ch8["更新なし"]["err"][-1], \
        "毎フレーム更新がドリフトしていない"
    assert 0.3 < ch8["毎フレーム"]["slope"] < 1.6, \
        f"ドリフトの傾きが範囲外 ({ch8['毎フレーム']['slope']:.3f})"
    assert abs(ch8["更新なし"]["slope"]) < 0.3, "更新なしがドリフトしている"
    # (5) 局所探索には移動量の崖があり、全域探索には無い
    assert ch4[24.0][0][0] > LOST_PX, "窓 ±6 が 24 px/frame で壊れない"
    assert ch4[24.0][1] < LOST_PX, "全域探索が移動量で壊れた"
    # (6) 遮蔽には崖があり、それ以下では耐える。そっくりな別物体は崖が手前に来る
    assert (ch5[0.3]["err"] <= LOST_PX).all(), "遮蔽 30 % で既に壊れている"
    assert (ch5[0.8]["err"] > LOST_PX).any(), "遮蔽 80 % でも壊れない"
    assert tw_cliff is not None and tw_cliff <= (cliff if cliff is not None else 1.0), \
        "そっくりな別物体の崖が平坦な遮蔽物より手前に来ていない"
    assert ff_tot > 0, "そっくりな別物体でピーク値が嘘をつかなかった"
    # (7) NCC は一次の照明変化に強い —— ただし信号が残っている間だけ
    assert abs(ch7[(1.6, 0.0)][0].mean() - base[0].mean()) < 0.10, "gain で誤差が動いた"
    assert abs(ch7[(1.0, 0.30)][0].mean() - base[0].mean()) < 0.10, "offset で誤差が動いた"
    assert ch7[(2.6, 0.25)][2] > 50.0, "gain 2.6 で飽和していない(舞台の想定違い)"
    # (8) 繰り返し模様: 全域探索は壊れ、窓を周期より狭めると直る
    assert (ch9["全域探索"]["err"] > LOST_PX).any(), "繰り返し模様で誤ロックしない"
    assert ch9["局所 ±6"]["err"].mean() < ch9["全域探索"]["err"].mean(), \
        "窓を狭めても直らない"
    # (9) ★ 主題: 信頼度は条件で得意・不得意が逆転する
    assert a_occ[0] > 0.75, f"平坦な遮蔽でピーク値が効かない (AUC {a_occ[0]:.3f})"
    assert a_occ[0] > a_occ[1], "平坦な遮蔽でピーク値が突出度に勝てない"
    assert a_amb[1] > a_amb[0], "紛らわしい対象で突出度がピーク値に勝てない"
    # ★ 得意な崖が逆である = どちらか一方を信頼度に選ぶことはできない
    assert (a_occ[0] - a_occ[1]) * (a_amb[0] - a_amb[1]) < 0, "得意な崖が逆転していない"
    # (9b) AUC が良くても運用点は使えない(そっくりな別物体)
    assert a_tw[0] > 0.9 and ff_tot == nl_tot, \
        f"AUC {a_tw[0]:.3f} と誤報 {ff_tot}/{nl_tot} の食い違いが再現しない"
    # (9c) 突出度は曖昧さの量であって正しさの量ではない(逆相関になる)
    assert a_tw[1] < 0.4, f"そっくりな別物体で突出度が逆相関にならない ({a_tw[1]:.3f})"
    assert a_rep[1] < 0.6, f"窓を混ぜたとき突出度が無力にならない ({a_rep[1]:.3f})"
    # (9d) ドリフトはどちらでも検出できない(AUC が 0.5 付近か、それ未満)
    assert a_dr[0] < 0.6, f"ドリフトをピーク値が検出できてしまった (AUC {a_dr[0]:.3f})"
    assert np.nanmean(p_dr[drift_lost]) > np.nanmean(p_dr[~drift_lost]), \
        "ドリフトしたフレームのほうがピークが低い(想定と逆)"
    # (10) shape_locate の角度は 30 度刻みに丸められる
    assert set(a[4] for a in ch6h) <= set(float(x) for x in range(0, 360, 30)), \
        "shape_locate が 30 度刻み以外を返した"

    el = time.perf_counter() - T_START
    print(f"\n  (所要 {el:.1f} 秒)")
    assert el < 90.0, f"90 秒を超えた ({el:.1f} 秒)"
    print("\nPASS")


if __name__ == "__main__":
    main()
