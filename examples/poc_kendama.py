# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ⑳: けん玉を先駆者の目で —— 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して皿で受ける。

けん玉をロボットにやらせた研究は 30 年続いている(1996 年の人の手本からの via-point、2009 年の DMP + 強化学習、2020 年の
「振り上げはオフライン・キャッチはオンライン」の 2 段割り)。この PoC は最後の構えを numpy の op(:mod:`kendama` /
:mod:`kendamaworld` / :mod:`ballistics` / :mod:`ballworld` / :mod:`balltrack`)で組み、**世界の側が持つ真値**で採点する。
閉ループが皿を動かす根拠は **画像だけ**: 描画 → 色度で玉を検出 → 2 台で三角測量 → ひもが弛んだら重力つきの放物線を当てて予測。
真値 (p, v) は世界を描くためだけに使う(計画には渡らない)。

形(出どころ): 玉 60 mm・横幅(大皿〜小皿)70 mm・全長(けんに玉を刺した状態)180 mm = 日本けん玉協会の公表値。けんの高さ
160 mm(公式ルール: 摩耗しても 150 mm 以上)・皿 大皿 42 / 中皿 38 / 小皿 35 mm・重さ 140〜150 g・糸は皿胴の穴から = ユーザー提供の
JKA 16-2 型の説明(一次資料は未確認)。穴の深さ 40 mm = 160 + 60 − 180(導いた値)。それ以外(皿の深さ、皿胴の太さ、けん先の形、
皿持ちの傾き 15° など)は kendama.kendama_params の docstring の「仮定」。形は MakerWorld の実寸モデルの写真と見比べた(図は使わない)。

技(ユーザーが調べた日本けん玉協会の級の技): 大皿(皿持ち: けん先は斜め下、大皿が上)・小皿(同じ持ち方で小皿)・中皿(けん持ち:
けん先をほぼ真下、中皿が上)・ろうそく(けん先をつまんで中皿)。**同じ計画と制御**(:func:`kendama.catch_plan_staged`)で、
姿勢(kp の技)だけを切り替える。制御の段階: lift(膝で真上に引き上げる = 開ループ、けんは糸穴の側へ 10 cm 逃がす)→ wait(弛むまで
動かさない)→ hold(玉の下端がけん玉のいちばん高い所を越えるまで寄せない)→ carry(皿を玉の真下へ水平に運ぶ)→ absorb(着地で
下げて相対速さを減らす)→ caught。

約束(ユーザーの条件): (1) 玉を動かすのは重力とひもの張力(≥ 0)だけ(空気抵抗も入れる)。けんは玉を押さない —— けん玉に玉が
触れたら(隙間 < −0.5 mm)その試行は失敗 "hit_ken"(:func:`kendamaworld.kendama_clearance` = 回転体の子午面の厳密な距離)。
(2) けんと皿胴は 1 つの剛体、姿勢は技ごとに固定、手元は並進。(3) 玉は弛んだ後に昇り(鉛直速度 > 0)、頂点を越えて下降中に受ける。
(4) けん先は穴にだけ: 皿の技でけん先に触れても hit_ken(とめけんは入れていない)。

門(真値の出どころ):
  1. **楕円積分の公表値と大振幅振り子の周期の定理**: K(0) = π/2、K(0.5) = 1.685750354812596 を AGM が 1e-12 で。周期
     T = 4√(L/g)·K(sin θ₀/2) をひも(10°・60°、dt = 1e-4)が 1e-3、棒(120°・170°)が 1e-9 で。
  2. **張力の閉形式と弛む角**: 真下から 150° 相当の速さで打ち出すと張力 m(v²/L + g cos θ) が 2 %、弛む角 cos θ_s = (2/3) cos θ₀ が 1°。
  3. **エネルギーと snap**: 張っている間は増えず散逸は dt に比例(比 5〜15)、飛翔中は保存(1e-12)、snap の落ち = ½ m v_r²(1 %)。
  4. **形の公表値を頂点から測る**: 皿胴の幅 70 mm、けん 160 mm(≥ 150)、大皿・中皿・小皿の縁の直径 42 / 38 / 35 mm、玉 60 mm、
     けん先を穴の底まで挿した全長 180 mm(すべて 1e-9)、けん先の穴に入る部分 < 穴の半径。推奨品の大皿 49 mm。
  5. **真値の世界で大皿**: 横 2 cm にずれて吊った玉を段階の制御で受ける(段階の順、けんに触れない、門 3 の飛び方)。逃がさず計画も
     ない振り上げは真下から昇る玉が皿胴に当たる(hit_ken)。
  6. **検出 → 三角測量 → 弛みの検出**(画像の閉ループの 1 試行): 玉の三角測量の誤差の中央値 < 3 mm、弛みの検出は真値の 4 コマ以内。
  7. **画像だけの閉ループが捕る**: 計画に渡った知覚は全部画像から(n_estimates = 計画の数)、20 試行の成功率が真値の知覚と 0.1 以内で ≥ 0.9。
  8. **3 技(+ ろうそく)を同じ計画で**: 大皿・小皿・中皿は画像で 20 試行 ≥ 0.9、ろうそくは真値 20 試行 ≥ 0.9 と画像の 1 試行。捕った
     全試行で門 3 の飛び方とけんに触れないことを確かめる。着地で下げると相対速さが下がる(4 技とも、20 試行の平均)。
  9. **予測誤差はコマ数とともに減る**: 弛んだ後のコマで当てた放物線から捕球の瞬間の玉の位置を読むと、20 試行の平均が 3 コマ → 最後で
     1/10 以下、途中で増える量は ≤ 0.5 mm(三角測量の誤差の中央値の程度)。
 10. **画素雑音のつまみ**: 0 / 0.5 / 1 / 2 / 8 / 16 px で 20 試行ずつ。0〜2 px は成功率 ≥ 0.9(平ら = 皿の縁の余裕、横ずれは増える)、
     16 px は 0 px より低い。
 11. **穴の向き**: 静止した玉を 40 通りの姿勢で撮り、2 台で見えた姿勢の穴の重心を三角測量して玉の中心からの向きを出すと、真の穴の軸と
     角度の誤差の中央値 < 5°・最大 < 10°(見えた姿勢 ≥ 8)。飛翔中の見え方は報告だけ(皿の技では計画に使わない)。
 12. **推奨品(大皿 49 mm)**: 同じ画像の閉ループで 20 試行、成功率は JKA 型以上(大きい皿が悪くならない)。
 13. **世界を 3D Gaussian Splatting にしてから認識**(ユーザー「fullseye の画像処理で玉や穴を認識、可能なら認識前に 3DGS にして」):
     :mod:`gsplatnp` が世界の面にガウシアンを貼り(間隔 4 mm)、EWA 投影 + 手前からの α 合成 + Mip-Splatting の補正で描いた画像を
     同じ知覚(色度の検出 → 三角測量 → 放物線)にかけ、閉ループが 1 + 2 試行すべて捕る(三角測量の誤差の中央値 < 3 mm)。
 14. **つまみが効く**: 間隔 2〜64 mm・位置の誤差 0〜20 mm・色の誤差 0〜0.3 で捕球の 12 コマを描き直す。密は検出率 ≥ 0.95、誤差を
     増やすと検出率は単調に下がり、20 mm / 0.3 で 0.5 未満(つまみが空回りしていない)。
 15. **3DGS の上の穴**: 解像度 × 2・間隔 2 mm で 2 台で見えた姿勢 ≥ 8・角度誤差の中央値 < 5°。間隔 4 mm では読めず、× 1 では
     メッシュより少ない(3DGS のぼけが 5 px の穴を塗りつぶす —— 穴を読むには玉に画素が、穴の中にガウシアンが要る)。
 16. **連続技**(ユーザー「受けたら、受けた状態から続けて別の皿で受けて」「10 回成功すれば良し」): 受けた皿から放ち(皿を上へ加速して g より強く
     止める → 玉が皿から離れる)、飛んでいる間に持ち替えて(手首 ≤ 30 rad/s、仮定)次の皿を着地点の真下へ運び、**速さを合わせて**受ける
     (位置と速度を目標にする手元の制御: 位置だけの制御は頂点 20 cm で 1 回も受けられない —— tests)。画像だけで もしかめ 10 回連続
     (+ full では 3 皿・真値も)。毎回 昇ってから下降中、けん玉に触れない、飛び始めも画像から。

正直に書くこと: 実写ではなく真値つきの合成映像(1 kHz の物理、100 fps・480 × 360 の 2 台)。玉 75 g・けん 70 g は仮定。ひもは伸びず
質量も無い。玉の回転は解かない(描画の約束: 張っている間は糸穴が結び目を向き、弛んだら最後の姿勢のまま)。皿の縁での跳ね・転がりは
扱わず、「縁に触れた瞬間に横ずれ ≤ 縁の半径・相対速さ ≤ 1 m/s(仮定の閾値)・下降中」を捕球とする。弛んだひもも真っ直ぐに描く。
1 回の技ではけんの姿勢は技ごとに固定(手首で迎えない)、手元の速さ ≤ 2 m/s・加速度 ≤ 20 m/s²(振り上げは開ループで 4.8 g)。連続技では飛んでいる間に持ち替えで回す(手首 ≤ 30 rad/s・手元 ≤ 2.5 m/s、仮定)。ろうそくが
中皿より難しい理由(つまんだ指の支え)は剛体・並進だけの手元では表せない —— 数字は中皿と同じ相対運動になる。
草稿から弱めた主張(測って退けた):
(a) ひもの周期を 120° でも 1e-3 で、は偽 —— ひもは 109.47° で弛む(棒で測る)。
(b) 弛むまでのエネルギー保存 1e-6 は偽 —— 射影法は 1 次精度で散逸的。「増えない・dt に比例」に変えた。
(c) 以前の版は「形が円柱の先に皿 1 枚」「閉ループが真値の (p, v) で動き画像の予測は採点だけ」だった(ユーザーの指摘)。作り直した。
(d) 手元を逃がさないと 20 試行すべてで玉が皿胴を突き抜けた(物理は衝突を解かない)→ けんとの隙間を毎 step 測って失敗に数える。
    +y へ逃がすとカメラ 2 から見てけんが玉を隠し、画像の予測の横ずれが増えた → 糸穴の側(−y)へ。
(e) 捕球を「縁から 1.5 r_b 上の窓に入った瞬間」にすると頂点が窓の中で「頂点で捕れて」しまう → 縁に触れた瞬間に。
(f) 着地で下げる動きを 60 ms 前から始めると皿が下がり切って止まり、玉がその分速く当たって 4 技とも弾かれた → 折り返しの時間 √(d/a)。
(g) 「弛み = 距離がひもより 5 mm 短いコマが 1 回」は 2 px の雑音で張っている間に誤検出した → 2 回続いたら。
(h) 穴を「玉の中の暗い画素」で探すと陰の側を穴と取り違えた → 色度も見る。飛翔中の穴は下(糸の反対)を向き、目の高さ 1.05 m の
    2 台からはほぼ真横になって 2 台同時にはほとんど見えない(門 11 は静止した玉で測る)。
(i) 画素雑音 0〜2 px では成功率は動かない(皿の縁の余裕 21 mm に対し横ずれ 2〜4 mm)。落ちるのは 8 px 以上。
(j) 3DGS で穴が 40 姿勢中 0 回しか読めなかった。原因は形: 穴を「表面から 0.3 mm 浮かせた暗い円盤」にしていたので、ガウシアンを
    中心の深さで並べる 3DGS では斜めから手前の玉のガウシアンが円盤を覆った → 玉を穴の軸まわりの回転体にして、深さ 40 mm の
    くぼみ(暗い壁と底)にした。さらに縁の円盤が穴の口にはみ出し、画素より細い円盤が不透明のまま太った(糸が 3 画素に)→ 角に接する
    面は 1/4 の大きさで置き、Mip-Splatting の不透明度の補正を入れた。それでも 480 × 360 では玉 17 px・穴 5 px で読めない(門 15)。
(l) 連続技で雑音が無いと 100 回でも同じ 1 周期の繰り返し(放つ動きが閉形式で決まり玉は真上に上がる)—— 回数は頑健さの証拠にならない。
    画素雑音 2 px を足すと もしかめ 3 回・3 皿 6 回で崩れる(着地の直前に当て直すたびに目標が揺れ、手元が加速度の上限に張り付く)。
    深追いはしない(ユーザー「単なる PoC、実演でしかない」)。
(k) 3DGS の間隔を 64 mm まで粗くしても玉の検出は落ちない: 曲率の上限で玉の上には 146 個以上が残る。崩すのは位置と色の誤差。

Run: py -3.11 examples/poc_kendama.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。FULLSEYE_POC_BUDGET=reduced で試行を減らす
     —— CI では reduced が既定、展示の数字は full)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ballistics as B  # noqa: E402
import balltrack as BT  # noqa: E402
import driveworld as DW  # noqa: E402
import kendama as KD  # noqa: E402
import kendamaworld as KW  # noqa: E402
import gsplatnp as GSN  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
FPS = 100
X0 = 0.02                                   # 玉を吊る横ずれ [m]
DODGE = (0.0, -0.10, 0.0)                   # 振り上げの後半に手元を逃がす向き(糸穴の側)
CUP_Z = 1.30                                # 持ち上げ終わりの受ける皿の高さ [m](カメラが見る範囲の上寄り)
#: ★CI(2 コア、PoC を並列に走らせる)では full の設定が 600 秒の枠を超えて -1(timeout)になった(2026-09-30、run 36657843727、
#:   手元 160 s)。FULLSEYE_POC_BUDGET=reduced(CI では既定)で、大皿の 20 試行(予測誤差の曲線と主要な門)はそのままに、小皿・中皿・
#:   画素雑音・推奨品の試行を 10 に、画素雑音の段を 0 / 2 / 8 / 16 px に、3DGS の試行・コマ・間隔の段を減らす。門の閾値は変えない
#:   (測った段だけで判定)。展示の数字は full の実測で、reduced は「同じ経路が走る」ことの証拠に留める(先頭に BUDGET: を印字)。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_TRIALS = 20
N_SMALL = 10 if REDUCED else N_TRIALS         # 大皿以外の画像の試行数(10 なら 1 回の失敗で 0.9 = 門の閾値ちょうど)
N_GS = 1 if REDUCED else 2                  # 3DGS の閉ループの試行数(1 試行 ≈ 3 s)
PIX = (0.0, 2.0, 8.0, 16.0) if REDUCED else (0.0, 0.5, 1.0, 2.0, 8.0, 16.0)
TRICKS = ("ozara", "kozara", "chuzara", "rousoku")
ZERO = (0.0, 0.0, 0.0)
UP = (0.0, 0.0, 1.0)
ZH = np.array([0.0, 0.0, 1.0])
WORLD_N = 24                                # 知覚の世界の回転体の分割数(32 → 24 で描画が 16 % 速い、結果は同じ: 6 試行で測った)
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def _period_from_crossings(t, x):
    """符号が変わる区間を線形補間して零交差時刻を取り、その間隔の平均 × 2 を周期に(交差の数も返す)。"""
    idx = np.where(np.diff(np.sign(x)) != 0)[0]
    tc = np.array([t[i] - x[i] * (t[i + 1] - t[i]) / (x[i + 1] - x[i]) for i in idx])
    return (2.0 * float(np.mean(np.diff(tc))) if tc.size >= 2 else float("nan")), int(tc.size)


def _angle_from_bottom(P):
    """支点(原点)の真下から測った角 (N,)。"""
    P = np.asarray(P, np.float64).reshape(-1, 3)
    return np.arctan2(np.hypot(P[:, 0], P[:, 1]), -P[:, 2])


def _origin(kp, lift):
    """持ち上げ終わりに受ける皿が CUP_Z に来る手元の出発点。"""
    return np.array([0.0, 0.0, CUP_Z - lift - float(kp["cup_offset"][2])])


def _contact(kp):
    return lambda hand, p: KW.kendama_clearance(kp, hand, p)["gap"][0]


def _stages(r):
    return [s for i, s in enumerate(r["stage"]) if i == 0 or s != r["stage"][i - 1]]


def _flight_ok(r):
    """門 3(ユーザーの条件): 弛んだ瞬間の鉛直速度 > 0、頂点が弛んだ高さより上、捕球は頂点より低く下降中。"""
    if r["slack_t"] is None or not r["caught"]:
        return False
    i_s = int(round(r["slack_t"] / (r["t"][1] - r["t"][0])))
    i_a = int(np.argmax(r["p"][:, 2]))
    return bool(r["v"][i_s, 2] > 0 and i_a > i_s and r["p"][i_a, 2] > r["p"][i_s, 2] and r["p"][-1, 2] < r["p"][i_a, 2]
                and r["v"][-1, 2] < 0)


def _rel_speed(r):
    return float(np.linalg.norm(r["v"][-1] - r["cup_v"][-1]))


def _rates(kp, lift, origin, *, perceive=None, n=None, absorb=True):
    """20 試行(seed 0 = 真値と画像で同じ初期状態)。perceive = None なら真値、("cam", pixel_noise, world, rig) なら画像。"""
    fac = None
    if perceive is not None:
        _, pn, w, rig = perceive

        def fac(i):
            return KW.camera_perceiver(w, rig, fps=FPS, pixel_noise=pn, rng=np.random.default_rng(1000 + i))
    return KD.catch_success_rate(kp, n=N_TRIALS if n is None else n, seed=0, origin=origin, lift=lift, dodge=DODGE, contact=_contact(kp), keep_runs=True,
                                 perceiver_factory=fac, absorb=absorb)


def _zoom(world, cam, centre_uv, half=40, scale=3, gs=None, ret_origin=False):
    """同じカメラの像の (2·half)² の窓を scale 倍の解像度で描き直す(最近傍の拡大でなく本当に細かく描く: 焦点距離を scale 倍、
    主点を窓に合わせる)。窓は像の内側に押し込む。"""
    W, H = int(cam["width"]), int(cam["height"])
    x0 = min(max(float(centre_uv[0]) - half, 0.0), W - 2 * half)
    y0 = min(max(float(centre_uv[1]) - half, 0.0), H - 2 * half)
    K = np.asarray(cam["K"], np.float64).copy()
    K3 = K.copy()
    K3[0, 0] *= scale
    K3[1, 1] *= scale
    K3[0, 2] = scale * (K[0, 2] - x0)
    K3[1, 2] = scale * (K[1, 2] - y0)
    n = 2 * half * scale
    if gs is not None:                                  # 3DGS で描き直す(世界のいまの頂点へ付け直してから)
        GSN.gs_update(gs, world)
        img = GSN.gs_render(gs, cam["pose"], K3, n, n)["color"]
    else:
        img = DW.world_camera(world, cam["pose"], K3, n, n)["color"]
    return (img, x0, y0) if ret_origin else img


def _inset(img, big, label, side="left", margin=8, top=36):
    """拡大した絵 big を img の左上(side="left")か右上に貼り、枠と見出しをつける。"""
    out = np.asarray(img, np.float64).copy()
    W = out.shape[1]
    s = big.shape[0]
    x0 = margin if side == "left" else W - s - margin
    out[top - 2:top + s + 2, x0 - 2:x0 + s + 2] = 1.0
    out[top:top + s, x0:x0 + s] = big
    return np.asarray(AN.text_box(out, label, (x0, top + s + 4), anchor="lt", font_size=11))


def _zoom_centre(ball_uv, cup_uv):
    """拡大の中心: 玉と皿が 70 px 以内なら中点、離れていれば皿(けん玉)のまわり。"""
    b, c = np.asarray(ball_uv, float), np.asarray(cup_uv, float)
    return 0.5 * (b + c) if np.all(np.isfinite(b)) and np.linalg.norm(b - c) < 70.0 else c + np.array([0.0, -12.0])


def _layout_labels(img, targets, size):
    """引き出し線つきの注記を、左右の縁に縦に並べて重ならないように置く(対象の x が中央より左なら左の列)。"""
    left = sorted([(uv[1], k, uv) for k, uv in targets.items() if uv[0] < size / 2], key=lambda z: z[0])
    right = sorted([(uv[1], k, uv) for k, uv in targets.items() if uv[0] >= size / 2], key=lambda z: z[0])
    out = img
    for col, xa, anchor in ((left, 58, "rm"), (right, size - 58, "lm")):
        ys = []
        for y, _, _ in col:
            y = min(max(y, 16.0), size - 16.0)
            if ys and y < ys[-1] + 26.0:
                y = ys[-1] + 26.0
            ys.append(y)
        over = ys[-1] - (size - 16.0) if ys else 0.0
        if over > 0:
            ys = [y - over for y in ys]
        for (_, lab, uv), y in zip(col, ys):
            out = np.asarray(AN.leader_line(out, (xa, y), (float(uv[0]), float(uv[1])), text=lab, color="emphasis", width=1,
                                            font_size=12, anchor=anchor, elbow=False))
    return out


def _closeup_scene(kp, size=380):
    """近接カメラ(図のためだけ、けん玉から 0.36 m)の世界と姿勢: ``(world, pose, K, size)``。3DGS の図も同じカメラで描く。"""
    return _closeup(kp, size, scene_only=True)


def _closeup(kp, size=380, scene_only=False):
    """近接カメラ(図のためだけ、けん玉から 0.36 m)で技の姿勢のけん玉を描き、部品に引き出し線をつける。玉は糸穴から斜め前に置き、
    穴をカメラへ向ける(見せるための置き方)。"""
    hand = np.array([0.0, 0.0, 1.0])
    w = KW.kendama_world(kp, floor=False, hand=hand)
    O = hand - kp["R_ken"] @ kp["grip"]
    R = kp["R_ken"]
    tie = O + R @ np.array([0.0, -kp["cross_radius"], 0.0])
    p_ball = tie + np.array([0.06, -0.05, -0.08])
    s_b = kp["cross_from_tip"] - kp["ken_length"]
    key = np.array([O + R @ np.array([kp["cross_from_tip"], 0, 0]), O + R @ np.array([s_b, 0, 0]),
                    O + R @ np.array([0, 0, 0.035]), O + R @ np.array([0, 0, -0.035]), p_ball])
    centre = 0.5 * (key.min(axis=0) + key.max(axis=0))
    view = np.array([0.55, -0.75, 0.38])
    view /= np.linalg.norm(view)
    eye = centre + 0.36 * view
    Rb = KW._rot_from_to(KW.HOLE_AXIS_LOCAL, (eye - p_ball) / np.linalg.norm(eye - p_ball) + np.array([0.0, 0.0, -0.3]))
    st = KW.kendama_pose(w, hand, p_ball, R_ball=Rb)
    K_ = DW.camera_intrinsics(48, size, size)
    pose = DW.camera_pose(eye, centre)
    if scene_only:
        return w, pose, K_, size
    img = DW.world_camera(w, pose, K_, size, size)["color"]
    an = w["objects"][w["kendama"]["ken"]]["anchors"]
    pts = {"けん先": O + R @ an["spike_tip"], "皿胴": O + R @ np.array([0.0, -0.013, 0.012]),
           "大皿": O + R @ an["big_rim"], "小皿": O + R @ an["small_rim"], "中皿": O + R @ an["base_rim"],
           "玉の穴": p_ball + kp["ball_radius"] * st["hole_axis"], "糸": 0.5 * (st["tie"] + st["string_hole"])}
    uv = {k: BT.reproject(v[None], pose, K_)[0] for k, v in pts.items()}
    uv = {k: v for k, v in uv.items() if np.all(np.isfinite(v)) and 4 <= v[0] <= size - 5 and 4 <= v[1] <= size - 5}
    return _layout_labels(img, uv, size)


# ─────────────────────────────── 連続技(19 巡目)の組み立て ───────────────────────────────
COMBO_CUP_Z = 1.15                          # 振り上げ終わりの大皿の高さ [m](連続技の頂点 ~1.45 m までカメラに入るよう CUP_Z から下げた)
COMBO_RIG = dict(distance=2.0, height=1.05, target=(0.0, -0.05, 1.0))   # 2 台(方位 0°・90°)、2 m から: 0.4〜1.6 m が像に入る


def _contact_combo(kp):
    """連続技の接触: 手元 = 皿胴の中心、姿勢 R は時刻ごと(kendama_clearance の R_ken)。"""
    return lambda hand, p, R: KW.kendama_clearance(kp, hand, p, R_ken=R, grip=np.zeros(3))["gap"][0]


def _combo_run(sequence=("ozara", "chuzara"), n_catch=10, perception="image", apex_above_cup=0.20):
    """吊った玉を振り上げて大皿で受け(18 巡目の制御)、そのまま連続技(:func:`kendama.kendama_combo_simulate`)へ渡す。
    知覚は真値か画像だけ(振り上げ = 糸の弛み、連続技 = 皿からの飛び始め を画像から)。返り値 {"swing", "combo", "count_total", "per"}。"""
    kp = KD.kendama_params(trick="ozara")
    lift = KD.swing_up_lift(kp)
    H0 = np.array([0.0, 0.0, COMBO_CUP_Z - lift - float(kp["cup_offset"][2])])
    handle = KD.swing_up_plan(kp, lift=lift, origin=H0, dodge=DODGE)
    L = kp["pendulum_length"]
    p0 = H0 + kp["tie_offset"] + np.array([X0, 0.0, -math.sqrt(L * L - X0 * X0)])
    per_s = per_c = None
    if perception == "image":
        world = KW.kendama_world(kp, hand=H0, n=WORLD_N)
        rig = KW.kendama_rig(kp, **COMBO_RIG)
        per_s = KW.camera_perceiver(world, rig, fps=FPS)
        per_c = KW.camera_perceiver(world, rig, fps=FPS, flight_from="cup")
    sw = KD.kendama_simulate(kp, handle, p0=p0, v0=np.zeros(3), t_end=1.5, catch_plan=KD.catch_plan_staged(kp), plan_from=handle.T_lift,
                             perceive=per_s, contact=lambda h, p: KW.kendama_clearance(kp, h, p)["gap"][0])
    out = {"swing": sw, "combo": None, "count_total": 0, "per": per_c}
    if sw["caught"]:
        cb = KD.kendama_combo_simulate(kp, sequence, n_catch=n_catch, hand0=sw["hand"][-1], hand_v0=sw["cup_v"][-1],
                                       apex_above_cup=apex_above_cup, perceive=per_c, contact=_contact_combo(kp))
        out["combo"] = cb
        out["count_total"] = 1 + cb["count"]
    return out


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    kp = KD.kendama_params()
    kv = KD.kendama_params(rho=0.0, tie_offset=ZERO, cup_offset=ZERO, cup_axis=UP)     # 点のけん: 定理の門
    L = kp["pendulum_length"]
    m = kp["mass"]
    g = B.G
    origin0 = np.zeros(3)

    # ─────────────────────────────── 1. 定理 ─────────────────────────────
    print("== 1. 楕円積分の公表値・大振幅振り子の周期・張力の閉形式と弛む角・エネルギーと snap(ひもの有効長 %.2f m = 糸 %.2f + 玉の半径)" % (
        L, kp["string"]))
    k_err = max(abs(KD.elliptic_k_agm(0.0) - math.pi / 2), abs(KD.elliptic_k_agm(0.5) - 1.685750354812596))
    per_str, per_rod = [], []
    for deg in (10.0, 60.0):
        th = math.radians(deg)
        Tx = KD.pendulum_period_exact(L, th, g)
        s = B.tether_simulate([L * math.sin(th), 0.0, -L * math.cos(th)], [0.0, 0.0, 0.0], origin0, L, 3.0 * Tx, 1e-4, g=g, mass=m)
        Tm, nc = _period_from_crossings(s["t"], s["p"][:, 0])
        per_str.append((deg, Tm, Tx, (Tm - Tx) / Tx, nc))
    for deg in (120.0, 170.0):
        th = math.radians(deg)
        Tx = KD.pendulum_period_exact(L, th, g)
        r = KD.pendulum_rod_simulate(L, th, 3.0 * Tx, 1e-3, g)
        Tm, nc = _period_from_crossings(r["t"], r["theta"])
        per_rod.append((deg, Tm, Tx, (Tm - Tx) / Tx, nc))
    for kind, rows in (("ひも", per_str), ("棒", per_rod)):
        for deg, Tm, Tx, e, nc in rows:
            print("  %s θ₀ = %3.0f°: 周期 測定 %.6f s、定理 %.6f s(相対差 %+.1e、零交差 %d 回)" % (kind, deg, Tm, Tx, e, nc))
    gate("楕円積分の公表値(1e-12)と大振幅振り子の周期の定理(ひも 1e-3、棒 1e-9)",
         k_err < 1e-12 and all(r[4] >= 4 for r in per_str + per_rod) and max(abs(r[3]) for r in per_str) < 1e-3
         and max(abs(r[3]) for r in per_rod) < 1e-9,
         "K %.1e / ひも %.1e / 棒 %.1e" % (k_err, max(abs(r[3]) for r in per_str), max(abs(r[3]) for r in per_rod)))

    th0 = math.radians(150.0)
    v0 = KD.pendulum_launch_speed(th0, L, g)
    sim = B.tether_simulate([0.0, 0.0, -L], [v0, 0.0, 0.0], origin0, L, 0.5, 2e-4, g=g, mass=m)
    taut = sim["taut"]
    idx = np.where(taut[1:-1] & ~taut[2:])[0]
    i_s = int(idx[0]) + 1 if idx.size else None
    th_t = _angle_from_bottom(sim["p"])
    speed = np.linalg.norm(sim["v"], axis=1)
    T_closed = np.array([KD.tether_tension_fixed(speed[i], th_t[i], L, m, g) for i in range(len(speed))])
    strong = np.zeros(len(speed), bool)
    if i_s is not None:
        strong[1:i_s] = T_closed[1:i_s] > 0.1 * T_closed[1:i_s].max()
    ten_rel = np.abs(sim["tension"][strong] - T_closed[strong]) / T_closed[strong] if strong.sum() else np.array([np.inf])
    th_s = KD.tether_slack_angle(th0, L, g)
    th_s_meas = float(th_t[i_s]) if i_s is not None else float("nan")
    print("  150° 相当の速さ %.3f m/s で真下から: 張力の相対差 最大 %.2e(%d 点)。弛む角 測定 %.2f°、閉形式 %.2f°" % (
        v0, ten_rel.max(), int(strong.sum()), math.degrees(th_s_meas), math.degrees(th_s)))
    gate("張力の閉形式(2 %)と弛む角(1°)", strong.sum() > 500 and ten_rel.max() < 0.02 and th_s is not None
         and abs(math.degrees(th_s_meas - th_s)) < 1.0, "角の差 %+.2f°" % math.degrees(th_s_meas - th_s))

    swing = 0.5 * m * KD.pendulum_launch_speed(math.radians(60.0), L, g) ** 2
    loss, never_up = [], True
    for dt in (1e-3, 1e-4):
        r = KD.kendama_simulate(kv, origin0, p0=[0.0, 0.0, -L], v0=[KD.pendulum_launch_speed(math.radians(60.0), L, g), 0.0, 0.0],
                                t_end=3.0, dt=dt)
        never_up &= bool(np.all(np.diff(r["energy"]) <= 1e-12)) and r["slack_t"] is None
        loss.append(float(np.ptp(r["energy"])) / swing)
    s = KD.kendama_simulate(kv, origin0, p0=[0.0, 0.0, -L], v0=[0.4, 0.0, 3.0], t_end=1.5, stop_on_miss=False)
    i_sn = int(np.argmin(np.abs(s["t"] - s["snap_times"][0]))) if s["snap_times"].size else None
    free_ptp = float(np.ptp(s["energy"][1:i_sn - 1])) if i_sn else float("inf")
    drop = float(s["energy"][i_sn - 1] - s["energy"][i_sn]) if i_sn else float("nan")
    snap_rel = abs(drop - s["snap_loss"]) / s["snap_loss"] if i_sn else float("inf")
    print("  60° の振り子 3 s: 損失 %.2f %%(dt 1e-3)/ %.3f %%(dt 1e-4)、比 %.1f。飛翔中のエネルギーの幅 %.1e J、snap の落ち %.4f J、"
          "½ m v_r² = %.4f J" % (100 * loss[0], 100 * loss[1], loss[0] / loss[1], free_ptp, drop, s["snap_loss"]))
    gate("エネルギー: 張っている間は増えず散逸は dt に比例(比 5〜15)、飛翔中は保存(1e-12)、snap の落ち = ½ m v_r²(1 %)",
         never_up and 5.0 < loss[0] / loss[1] < 15.0 and free_ptp < 1e-12 and snap_rel < 0.01)

    # ─────────────────────────────── 2. 形 ─────────────────────────────
    print("== 2. けん玉の形: 公表寸法を頂点から測る(JKA 16-2 型、推奨品)")
    dims = {}
    for name, kpx in (("jka", kp), ("large", KD.kendama_params("recommended_large_cup"))):
        mm = KW.ken_mesh(kpx)
        cross = mm["V"][np.unique(mm["F"][slice(*mm["parts"]["cross"])])]
        ken = mm["V"][np.unique(mm["F"][slice(*mm["parts"]["ken"])])]

        def diam(labels, axes):
            F = mm["F"][np.isin(mm["label"], labels)]
            V = mm["V"][np.unique(F)]
            return 2.0 * float(np.hypot(V[:, axes[0]], V[:, axes[1]]).max())

        w = KW.kendama_world(kpx, floor=False, hand=(0.0, 0.0, 1.0))
        u = kpx["R_ken"] @ np.array([1.0, 0.0, 0.0])
        O = np.array([0.0, 0.0, 1.0]) - kpx["R_ken"] @ kpx["grip"]
        tip = O + kpx["cross_from_tip"] * u
        KW.kendama_pose(w, (0.0, 0.0, 1.0), tip - (kpx["hole_depth"] - kpx["ball_radius"]) * u,
                        R_ball=KW._rot_from_to(KW.HOLE_AXIS_LOCAL, -u))
        ob = w["objects"][w["kendama"]["ball"]]
        f0, f1 = ob["faces"]
        Vb = w["V"][np.unique(w["F"][f0:f1][w["face_label"][f0:f1] == 23])]
        Vk = w["V"][slice(*w["objects"][w["kendama"]["ken"]]["verts"])]
        total = max((Vk @ u).max(), (Vb @ u).max()) - min((Vk @ u).min(), (Vb @ u).min())
        ball_d = float(np.linalg.norm(Vb[:, None, :] - Vb[None, :, :], axis=2).max())
        inside = ken[:, 0] > kpx["cross_from_tip"] - kpx["hole_depth"] - 1e-12
        fits = float(np.hypot(ken[inside, 1], ken[inside, 2]).max()) < kpx["hole_radius"]
        dims[name] = {"width": float(np.ptp(cross[:, 2])), "ken": float(np.ptp(ken[:, 0])), "big": diam([28], (0, 1)),
                      "small": diam([30], (0, 1)), "base": diam([31], (1, 2)), "ball": ball_d, "total": total, "fits": fits}
        d = dims[name]
        print("  %s: 横幅 %.3f mm、けん %.3f mm、大皿 %.3f mm、中皿 %.3f mm、小皿 %.3f mm、玉 %.3f mm、組み立ての全長 %.3f mm、"
              "けん先は穴(直径 %.0f mm、深さ %.0f mm)に入る: %s" % (
                  name, 1e3 * d["width"], 1e3 * d["ken"], 1e3 * d["big"], 1e3 * d["base"], 1e3 * d["small"], 1e3 * d["ball"],
                  1e3 * d["total"], 2e3 * kpx["hole_radius"], 1e3 * kpx["hole_depth"], d["fits"]))
    j, lg = dims["jka"], dims["large"]
    gate("形: 横幅 70・けん 160(≥ 150)・大皿 42・中皿 38・小皿 35・玉 60・全長 180 mm(1e-9)、けん先が穴に入る、推奨品の大皿 49 mm",
         abs(j["width"] - 0.070) < 1e-9 and abs(j["ken"] - 0.160) < 1e-9 and j["ken"] >= 0.150 and abs(j["big"] - 0.042) < 1e-9
         and abs(j["base"] - 0.038) < 1e-9 and abs(j["small"] - 0.035) < 1e-9 and abs(j["ball"] - 0.060) < 1e-9
         and abs(j["total"] - 0.180) < 1e-9 and j["fits"] and lg["fits"] and abs(lg["big"] - 0.049) < 1e-9
         and abs(lg["total"] - 0.180) < 1e-9)

    # ─────────────────────────────── 3. 真値の世界で大皿 ─────────────────────────
    print("== 3. 真値の世界で大皿(皿持ち: けん先 15° 下): lift → wait → hold → carry → absorb → caught")
    lift = KD.swing_up_lift(kp)
    H0 = _origin(kp, lift)
    handle = KD.swing_up_plan(kp, lift=lift, origin=H0, dodge=DODGE)
    ap = KD.swing_up_apex(kp, lift=lift)
    p_ball0 = H0 + kp["tie_offset"] + np.array([X0, 0.0, -math.sqrt(L * L - X0 * X0)])
    truth = KD.kendama_simulate(kp, handle, p0=p_ball0, v0=np.zeros(3), t_end=1.5, catch_plan=KD.catch_plan_staged(kp),
                                plan_from=handle.T_lift, contact=_contact(kp))
    naive = KD.kendama_simulate(kp, KD.swing_up_plan(kp, lift=lift, origin=H0), p0=p_ball0, v0=np.zeros(3), t_end=1.5,
                                contact=_contact(kp))
    print("  手元を %.1f cm / %.2f s で持ち上げ(%.1f g、閉形式で t = %.3f s に弛み、頂点は受ける皿の %.1f mm 上)、後半で −y へ 10 cm 逃がす" % (
        100 * lift, handle.T_lift, handle.accel / g, ap["slack_t"], 1e3 * ap["apex_above_cup"]))
    print("  閉ループ(真値): %s(t = %s s、横ずれ %.2f mm、相対速さ %.2f m/s、けんとの隙間の最小 %.1f mm)、段階 %s" % (
        truth["end_reason"], "%.3f" % truth["catch_t"] if truth["catch_t"] else "—", 1e3 * (truth["lateral"] or np.nan),
        _rel_speed(truth), 1e3 * truth["min_gap"], " → ".join(_stages(truth))))
    print("  逃がさず計画もない振り上げ: %s(t = %.3f s、隙間の最小 %.1f mm = 真下から昇る玉が皿胴に当たる)" % (
        naive["end_reason"], naive["t"][-1], 1e3 * naive["min_gap"]))
    gate("真値の世界で大皿: 段階の順に捕る・けんに触れない・弛んだ後に昇って頂点を越え下降中に受ける。逃がさない振り上げは hit_ken",
         truth["caught"] and _stages(truth) == ["lift", "wait", "hold", "carry", "absorb", "caught"] and truth["min_gap"] > 0
         and _flight_ok(truth) and naive["end_reason"] == "hit_ken")

    # ─────────────────────────────── 4. 画像だけの閉ループ(1 試行) ───────────────
    print("== 4. 画像だけの閉ループ: 描画 → 色度で玉 → DLT → 弛み → 重力つきの放物線 → 皿(%d fps、480 × 360 × 2 台)" % FPS)
    world = KW.kendama_world(kp, hand=H0, n=WORLD_N)
    rig = KW.kendama_rig(kp)
    per = KW.camera_perceiver(world, rig, fps=FPS, keep_frames=figs.enabled())
    t_r = time.time()
    img_run = KD.kendama_simulate(kp, handle, p0=p_ball0, v0=np.zeros(3), t_end=1.5, catch_plan=KD.catch_plan_staged(kp),
                                  plan_from=handle.T_lift, perceive=per, contact=_contact(kp))
    t_img = time.time() - t_r
    T_f = np.array([f["t"] for f in per.frames])
    P_hat = np.array([f["p_hat"] for f in per.frames])
    P_tru = np.column_stack([np.interp(T_f, img_run["t"], img_run["p"][:, k]) for k in range(3)])
    okb = np.isfinite(P_hat).all(axis=1)
    eb = np.linalg.norm(P_hat[okb] - P_tru[okb], axis=1)
    t_det = per.frames[per.slack_frame]["t"] if per.slack_frame is not None else float("nan")
    print("  %d コマ、玉は %d コマで 2 台とも検出、三角測量の誤差 中央値 %.2f mm・最大 %.2f mm。弛み: 真値 %.3f s、画像 %.3f s(%+.0f ms)" % (
        len(per.frames), okb.sum(), 1e3 * np.median(eb), 1e3 * eb.max(), img_run["slack_t"], t_det, 1e3 * (t_det - img_run["slack_t"])))
    print("  結果: %s(t = %.3f s、横ずれ %.2f mm、相対速さ %.2f m/s)、計画に渡った推定 %d 回(全部画像から)、段階 %s。描画 %d 窓・%.2f s(試行全体 %.2f s)" % (
        img_run["end_reason"], img_run["catch_t"] or np.nan, 1e3 * (img_run["lateral"] or np.nan), _rel_speed(img_run), img_run["n_estimates"],
        " → ".join(_stages(img_run)), per.n_render, per.render_s, t_img))
    gate("検出 → 三角測量(中央値 < 3 mm、9 割のコマで検出)→ 弛みの検出(真値の 4 コマ以内)", okb.mean() > 0.9 and np.median(eb) < 3e-3
         and 0.0 < t_det - img_run["slack_t"] <= 4.0 / FPS)

    print("== 5. 成功率: 真値の知覚 vs 画像だけの予測(%d 試行ずつ、同じ初期状態)" % N_TRIALS)
    t_s = time.time()
    res = {}
    for trick in TRICKS:
        kt = KD.kendama_params(trick=trick)
        lt = KD.swing_up_lift(kt)
        ot = _origin(kt, lt)
        wt = world if trick == "ozara" else KW.kendama_world(kt, hand=ot, n=WORLD_N)
        rt = rig
        tr = _rates(kt, lt, ot)
        na = _rates(kt, lt, ot, absorb=False)
        im = (_rates(kt, lt, ot, perceive=("cam", 0.0, wt, rt), n=None if trick == "ozara" else N_SMALL)
              if trick != "rousoku" else None)
        if trick == "rousoku":
            pr = KW.camera_perceiver(wt, rt, fps=FPS)
            hr = KD.swing_up_plan(kt, lift=lt, origin=ot, dodge=DODGE)
            pb = ot + kt["tie_offset"] + np.array([X0, 0.0, -math.sqrt(L * L - X0 * X0)])
            one = KD.kendama_simulate(kt, hr, p0=pb, v0=np.zeros(3), t_end=1.5, catch_plan=KD.catch_plan_staged(kt), plan_from=hr.T_lift,
                                      perceive=pr, contact=_contact(kt))
        runs_c = [r for r in tr["runs"] + (im["runs"] if im else []) if r["caught"]]
        res[trick] = {"truth": tr, "noabs": na, "image": im, "lift": lt,
                      "flight_ok": all(_flight_ok(r) and r["min_gap"] > 0 for r in runs_c), "n_caught": len(runs_c),
                      "rel_abs": float(np.mean([_rel_speed(r) for r in tr["runs"] if r["caught"]])),
                      "rel_no": float(np.mean([_rel_speed(r) for r in na["runs"] if r["caught"]])),
                      "one": one if trick == "rousoku" else None}
        q = res[trick]
        print("  %-8s(%s、持ち上げ %.1f cm): 真値 %.2f(%s)、画像 %s、着地で下げる/下げない %.2f / %.2f(相対速さの平均 %.2f / %.2f m/s)%s" % (
            trick, KD.KENDAMA_TRICKS[trick]["name"], 100 * lt, tr["rate"],
            ", ".join("%s %d" % (k, tr["end_reasons"].count(k)) for k in sorted(set(tr["end_reasons"]))),
            "%.2f(%s、横ずれ %.2f mm)" % (im["rate"], ", ".join("%s %d" % (k, im["end_reasons"].count(k))
                                                            for k in sorted(set(im["end_reasons"]))), 1e3 * im["mean_lateral"]) if im else "—",
            tr["rate"], na["rate"], q["rel_abs"], q["rel_no"],
            "、画像の 1 試行: %s" % one["end_reason"] if trick == "rousoku" else ""))
    print("  (%.1f s)" % (time.time() - t_s))
    oz = res["ozara"]
    gate("画像だけの閉ループが捕る(1 試行: 推定は全部画像から)、20 試行で ≥ 0.9 かつ真値と 0.1 以内",
         img_run["caught"] and img_run["n_estimates"] == len(img_run["plan_log"]) > 100 and oz["image"]["rate"] >= 0.9
         and abs(oz["image"]["rate"] - oz["truth"]["rate"]) <= 0.1, "真値 %.2f、画像 %.2f" % (oz["truth"]["rate"], oz["image"]["rate"]))
    gate("同じ計画で 3 技(+ ろうそく): 画像 20 試行 ≥ 0.9(大皿・小皿・中皿)、ろうそくは真値 ≥ 0.9 と画像の 1 試行、捕った全試行で飛び方とけんに"
         "触れないこと、着地で下げると相対速さが下がる",
         all(res[t]["image"]["rate"] >= 0.9 for t in ("ozara", "kozara", "chuzara")) and res["rousoku"]["truth"]["rate"] >= 0.9
         and res["rousoku"]["one"]["caught"] and all(res[t]["flight_ok"] for t in TRICKS)
         and all(res[t]["rel_abs"] < res[t]["rel_no"] for t in TRICKS),
         "; ".join("%s %.2f→%.2f m/s" % (t, res[t]["rel_no"], res[t]["rel_abs"]) for t in TRICKS))

    # ─────────────────────────────── 6. 予測誤差 vs コマ数 ─────────────────────
    print("== 6. 落下点の予測誤差: 弛んだ後の n コマに当てた放物線から、捕球の瞬間の玉の位置を読む(20 試行の平均)")

    def curve(rr):
        cs = []
        for r, pp in zip(rr["runs"], rr["perceivers"]):
            if not r["caught"] or pp.slack_frame is None:
                continue
            tc, pt = r["t"][-1], r["p"][-1]
            e = []
            for (tf, nu, pr_, vr_, trf) in pp.fits:
                if tf > tc:
                    break
                tau = tc - trf
                e.append(float(np.linalg.norm(pr_ + vr_ * tau - 0.5 * g * tau * tau * ZH - pt)))
            cs.append(e)
        mn = min(len(c) for c in cs)
        return np.mean([c[:mn] for c in cs], axis=0)

    cv0 = curve(oz["image"])
    rise0 = float(np.max(np.diff(cv0)))
    ns = np.arange(3, 3 + cv0.size)
    print("  0 px: n = %s → %s mm(最大の増え %.2f mm)" % (
        "/".join(str(n) for n in ns[[0, 2, 7, 17, 27, -1]]), " / ".join("%.2f" % (1e3 * cv0[i]) for i in (0, 2, 7, 17, 27, -1)), 1e3 * rise0))

    # ─────────────────────────────── 7. 画素雑音のつまみ ───────────────────────
    print("== 7. 画素雑音(検出の画素に足すガウス、σ)→ 成功率(大皿、0 px と 2 px は %d 試行、他は %d 試行ずつ)" % (N_TRIALS, N_SMALL))
    t_s = time.time()
    sweep = [(0.0, oz["image"])]
    for pn in PIX[1:]:
        # 2 px は予測誤差の曲線(門)にも使う: 10 試行の平均だと途中の増えが 2.55 mm に揺れた(測った)ので reduced でも 20 試行
        sweep.append((pn, _rates(kp, lift, H0, perceive=("cam", pn, world, rig), n=N_TRIALS if pn == 2.0 else N_SMALL)))
    for pn, rr in sweep:
        se = math.sqrt(max(rr["rate"] * (1 - rr["rate"]), 1e-12) / rr["n"])
        print("  %4.1f px → 成功率 %.2f(± %.2f、%s)、捕った試行の横ずれの平均 %.2f mm" % (
            pn, rr["rate"], se, ", ".join("%s %d" % (k, rr["end_reasons"].count(k)) for k in sorted(set(rr["end_reasons"]))),
            1e3 * rr["mean_lateral"]))
    cv2 = curve(dict(sweep)[2.0])
    print("  2 px の予測誤差: n = 3 → 最後 %.1f → %.2f mm(最大の増え %.2f mm)。(%.1f s)" % (
        1e3 * cv2[0], 1e3 * cv2[-1], 1e3 * float(np.max(np.diff(cv2))), time.time() - t_s))
    gate("予測誤差はコマ数とともに減る: 最後 ≤ 3 コマの 1/10、途中の増え ≤ 0.5 mm(0 px と 2 px)",
         cv0[-1] <= cv0[0] / 10 and rise0 <= 5e-4 and cv2[-1] <= cv2[0] / 10 and float(np.max(np.diff(cv2))) <= 5e-4,
         "0 px %.2f → %.2f mm、2 px %.1f → %.2f mm" % (1e3 * cv0[0], 1e3 * cv0[-1], 1e3 * cv2[0], 1e3 * cv2[-1]))
    rates = {pn: rr["rate"] for pn, rr in sweep}
    lats = {pn: rr["mean_lateral"] for pn, rr in sweep}
    gate("画素雑音: 0〜2 px は ≥ 0.9(平ら = 皿の縁の余裕、横ずれは 0 < 2 < 8 px と増える)、16 px は 0 px より低い",
         all(rates[p] >= 0.9 for p in PIX if p <= 2.0) and lats[0.0] < lats[2.0] < lats[8.0] and rates[16.0] < rates[0.0],
         " / ".join("%g px %.2f" % (p, rates[p]) for p in PIX))

    # ─────────────────────────────── 8. 穴の向き ─────────────────────────
    print("== 8. 穴の向き: kendama.hole_detect(玉の窓の中の暗い茶の円盤)→ 2 台の重心を三角測量 → 玉の中心からの向き")
    wh = KW.kendama_world(kp, hand=(0.0, 0.6, 1.3))
    Ps = np.array([c["pose"] for c in rig])
    Ks = np.array([c["K"] for c in rig])
    rng = np.random.default_rng(0)
    pc = np.array([0.0, 0.0, 1.1])
    herr, n_seen = [], 0
    for _ in range(40):
        dvec = rng.normal(size=3)
        dvec[:2] = np.abs(dvec[:2])
        dvec /= np.linalg.norm(dvec)
        KW.kendama_pose(wh, (0.0, 0.6, 1.3), pc, R_ball=KW._rot_from_to(KW.HOLE_AXIS_LOCAL, dvec))
        ub, uh = [], []
        for c in rig:
            im_ = DW.world_camera(wh, c["pose"], c["K"], c["width"], c["height"])["color"]
            b = [x for x in BT.ball_detect(im_, mode="chroma", color=KW.BALL_COLOR, color_tol=0.12, radius_range=(2.5, 80)) if x["fill"] >= 0.6]
            h = KD.hole_detect(im_, (b[0]["col"], b[0]["row"]), b[0]["radius"]) if b else {"found": False}
            ub.append((b[0]["col"], b[0]["row"]) if b else (np.nan, np.nan))
            uh.append((h["col"], h["row"]) if h["found"] else (np.nan, np.nan))
        ub, uh = np.array(ub), np.array(uh)
        if np.isfinite(uh).all() and np.isfinite(ub).all():
            n_seen += 1
            e = BT.triangulate_dlt(uh, Ps, Ks)["p"] - BT.triangulate_dlt(ub, Ps, Ks)["p"]
            herr.append(math.degrees(math.acos(float(np.clip(e @ dvec / np.linalg.norm(e), -1, 1)))))
    fl_seen = sum(np.all(np.isfinite(f["hole_dir"])) for f in per.frames)
    fl_one = sum(sum(np.all(np.isfinite(hh)) for hh in f["hole_uv"]) >= 1 for f in per.frames)
    print("  静止 40 姿勢: 2 台で見えた %d、角度誤差 中央値 %.1f°・最大 %.1f°。飛翔(画像の 1 試行 %d コマ): 1 台以上で見えた %d、2 台で %d"
          "(穴は糸の反対 = 下を向いて飛ぶ)" % (n_seen, np.median(herr) if herr else np.nan, max(herr) if herr else np.nan,
                                        len(per.frames), fl_one, fl_seen))
    gate("穴の向き(静止): 2 台で見えた姿勢 ≥ 8、角度誤差 中央値 < 5°・最大 < 10°", n_seen >= 8 and np.median(herr) < 5.0 and max(herr) < 10.0)

    print("== 9. 推奨品(大皿 49 mm、穴 24 mm)を同じ画像の閉ループで")
    kl = KD.kendama_params("recommended_large_cup")
    ll = KD.swing_up_lift(kl)
    ol = _origin(kl, ll)
    big = _rates(kl, ll, ol, perceive=("cam", 0.0, KW.kendama_world(kl, hand=ol, n=WORLD_N), rig), n=N_SMALL)
    print("  推奨品: 成功率 %.2f(横ずれ %.2f mm)、JKA 型 %.2f(横ずれ %.2f mm)" % (big["rate"], 1e3 * big["mean_lateral"], oz["image"]["rate"],
                                                                         1e3 * oz["image"]["mean_lateral"]))
    gate("推奨品(大皿 49 mm)の成功率は JKA 型以上(大きい皿が悪くならない)", big["rate"] >= oz["image"]["rate"],
         "%.2f vs %.2f" % (big["rate"], oz["image"]["rate"]))

    # ─────────────────────────────── 10. 3DGS にしてから認識 ─────────────────────────
    print("== 10. 世界を 3D Gaussian Splatting にしてから認識(gsplatnp: 面に貼ったガウシアン + EWA 描画 + Mip の補正)")
    t_g = time.time()
    GSP = 0.004                                             # 閉ループの 3DGS の間隔 [m]
    gsw = KW.kendama_world(kp, hand=H0, n=WORLD_N)
    gs = GSN.gs_from_world(gsw, spacing=GSP, max_per_object=8000)
    i_ball_obj = [o["name"] for o in gsw["objects"]].index("ball")
    rf = GSN.gs_render_fn(gs)
    per_g = KW.camera_perceiver(gsw, rig, fps=FPS, render_fn=rf, keep_frames=figs.enabled())
    g_run = KD.kendama_simulate(kp, handle, p0=p_ball0, v0=np.zeros(3), t_end=1.5, catch_plan=KD.catch_plan_staged(kp),
                                plan_from=handle.T_lift, perceive=per_g, contact=_contact(kp))
    rf_rate = GSN.gs_render_fn(gs)
    g_rate = KD.catch_success_rate(kp, n=N_GS, seed=0, origin=H0, lift=lift, dodge=DODGE, contact=_contact(kp), keep_runs=True,
                                   perceiver_factory=lambda i: KW.camera_perceiver(gsw, rig, fps=FPS, render_fn=rf_rate))
    Tg = np.array([f["t"] for f in per_g.frames])
    Pg = np.array([f["p_hat"] for f in per_g.frames])
    Pg_t = np.column_stack([np.interp(Tg, g_run["t"], g_run["p"][:, k]) for k in range(3)])
    okg = np.isfinite(Pg).all(axis=1)
    eg = np.linalg.norm(Pg[okg] - Pg_t[okg], axis=1)
    print("  3DGS(間隔 %.0f mm、ガウシアン %d 個、玉に %d 個): 1 試行 %s(横ずれ %.2f mm、推定 %d 回は全部 3DGS の画像から)、三角測量の誤差 中央値 %.2f mm、"
          "%d 試行の成功率 %.2f(%s)" % (1e3 * GSP, len(gs["face"]), int((gs["obj"] == i_ball_obj).sum()), g_run["end_reason"],
                                     1e3 * (g_run["lateral"] or np.nan), g_run["n_estimates"], 1e3 * np.median(eg), N_GS, g_rate["rate"],
                                     ", ".join("%s %d" % (k, g_rate["end_reasons"].count(k)) for k in sorted(set(g_rate["end_reasons"])))))
    gate("3DGS の世界で画像だけの閉ループが捕る(1 試行 + %d 試行すべて)、三角測量の誤差 中央値 < 3 mm、捕った試行は飛び方とけんに触れないこと" % N_GS,
         g_run["caught"] and g_run["n_estimates"] > 100 and g_rate["rate"] == 1.0 and np.median(eg) < 3e-3
         and all(_flight_ok(r) and r["min_gap"] > 0 for r in g_rate["runs"] + [g_run] if r["caught"]))

    # つまみ: 密度・位置の誤差・色の誤差 → 検出率と三角測量の誤差(捕球の試行の弛み → 捕球の 12 コマを、玉のまわりの窓だけ描き直す)
    Ps_ = np.array([c["pose"] for c in rig])
    Ks_ = np.array([c["K"] for c in rig])
    ks = np.linspace(int(np.searchsorted(g_run["t"], g_run["slack_t"])), int(np.searchsorted(g_run["t"], g_run["catch_t"])) - 1, 8 if REDUCED else 12).astype(int)

    def _sweep(sp, pn, cn):
        gg = GSN.gs_from_world(gsw, spacing=sp, pos_noise=pn, color_noise=cn, max_per_object=8000, seed=0)
        errs, nd = [], 0
        for i in ks:
            p = g_run["p"][i]
            KW.kendama_pose(gsw, g_run["hand"][i], p)
            GSN.gs_update(gg, gsw)
            uvs = []
            for c in rig:
                uv0 = BT.reproject(p[None], c["pose"], c["K"])[0]
                x0 = int(round(min(max(uv0[0] - 64, 0), c["width"] - 128)))
                y0 = int(round(min(max(uv0[1] - 64, 0), c["height"] - 128)))
                K2 = np.array(c["K"], np.float64)
                K2[0, 2] -= x0
                K2[1, 2] -= y0
                im_ = GSN.gs_render(gg, c["pose"], K2, 128, 128)["color"]
                d = [x for x in BT.ball_detect(im_, mode="chroma", color=KW.BALL_COLOR, color_tol=0.12, radius_range=(2.5, 80)) if x["fill"] >= 0.6]
                uvs.append((d[0]["col"] + x0, d[0]["row"] + y0) if d else (np.nan, np.nan))
            uvs = np.array(uvs)
            if np.isfinite(uvs).all():
                nd += 1
                errs.append(float(np.linalg.norm(BT.triangulate_dlt(uvs, Ps_, Ks_)["p"] - p)))
        return {"rate": nd / len(ks), "med": float(np.median(errs)) if errs else float("nan"), "n_ball": int((gg["obj"] == i_ball_obj).sum())}

    SPS = (0.002, 0.004, 0.008, 0.064) if REDUCED else (0.002, 0.004, 0.008, 0.016, 0.032, 0.064)
    PNS = (0.0, 0.005, 0.010, 0.020)
    CNS = (0.0, 0.1, 0.2, 0.3)
    sw_sp = {s: _sweep(s, 0.0, 0.0) for s in SPS}
    sw_pn = {p: (_sweep(GSP, p, 0.0) if p > 0 else sw_sp[GSP]) for p in PNS}
    sw_cn = {c: (_sweep(GSP, 0.0, c) if c > 0 else sw_sp[GSP]) for c in CNS}
    print("  間隔 [mm] → 検出率 / 誤差の中央値 [mm] / 玉のガウシアン: " + "; ".join(
        "%g → %.2f / %.2f / %d" % (1e3 * s, sw_sp[s]["rate"], 1e3 * sw_sp[s]["med"], sw_sp[s]["n_ball"]) for s in SPS))
    print("  位置の誤差 [mm] → " + "; ".join("%g → %.2f / %.2f" % (1e3 * p, sw_pn[p]["rate"], 1e3 * sw_pn[p]["med"]) for p in PNS))
    print("  色の誤差 → " + "; ".join("%g → %.2f / %.2f" % (c, sw_cn[c]["rate"], 1e3 * sw_cn[c]["med"]) for c in CNS))
    print("  (玉の上の個数が間隔ほど減らないのは曲率の上限: 円盤が球面からはみ出さない大きさ σ ≤ 0.5 R に抑えて、そのぶん密に置く)")
    rp = [sw_pn[p]["rate"] for p in PNS]
    rc = [sw_cn[c]["rate"] for c in CNS]
    gate("つまみが効く: 密(2〜8 mm)は検出率 ≥ 0.95・誤差 < 2 mm、位置の誤差・色の誤差を増やすと検出率は下がり(単調)、20 mm / 0.3 で 0.5 未満",
         all(sw_sp[s]["rate"] >= 0.95 and sw_sp[s]["med"] < 2e-3 for s in (0.002, 0.004, 0.008))
         and all(a >= b for a, b in zip(rp, rp[1:])) and all(a >= b for a, b in zip(rc, rc[1:])) and rp[-1] < 0.5 and rc[-1] < 0.5,
         "位置 %s、色 %s" % (" / ".join("%.2f" % r for r in rp), " / ".join("%.2f" % r for r in rc)))

    # 穴: 3DGS の上でも読めるか(静止した玉 40 姿勢、窓だけ描く)。解像度(同じ画角で画素数 × 1 / 2 / 3)と間隔を振る
    def _holes(scale, sp):
        rg = KW.kendama_rig(kp, width=480 * scale, height_px=360 * scale)
        P2 = np.array([c["pose"] for c in rg])
        K2s = np.array([c["K"] for c in rg])
        gg = None if sp is None else GSN.gs_from_world(wh, spacing=sp, max_per_object=8000)
        rng_ = np.random.default_rng(0)
        er, n = [], 0
        for _ in range(40):
            dv = rng_.normal(size=3)
            dv[:2] = np.abs(dv[:2])
            dv /= np.linalg.norm(dv)
            KW.kendama_pose(wh, (0.0, 0.6, 1.3), pc, R_ball=KW._rot_from_to(KW.HOLE_AXIS_LOCAL, dv))
            if gg is not None:
                GSN.gs_update(gg, wh)
            ub, uh = [], []
            for c in rg:
                uv = BT.reproject(pc[None], c["pose"], c["K"])[0]
                w_ = 40 * scale
                x0, y0 = int(uv[0] - w_ // 2), int(uv[1] - w_ // 2)
                K2 = np.array(c["K"], np.float64)
                K2[0, 2] -= x0
                K2[1, 2] -= y0
                im_ = (DW.world_camera(wh, c["pose"], K2, w_, w_)["color"] if gg is None else GSN.gs_render(gg, c["pose"], K2, w_, w_)["color"])
                b = [x for x in BT.ball_detect(im_, mode="chroma", color=KW.BALL_COLOR, color_tol=0.12, radius_range=(2.5, 200)) if x["fill"] >= 0.6]
                h = KD.hole_detect(im_, (b[0]["col"], b[0]["row"]), b[0]["radius"]) if b else {"found": False}
                ub.append((b[0]["col"] + x0, b[0]["row"] + y0) if b else (np.nan, np.nan))
                uh.append((h["col"] + x0, h["row"] + y0) if h["found"] else (np.nan, np.nan))
            ub, uh = np.array(ub), np.array(uh)
            if np.isfinite(uh).all() and np.isfinite(ub).all():
                n += 1
                e = BT.triangulate_dlt(uh, P2, K2s)["p"] - BT.triangulate_dlt(ub, P2, K2s)["p"]
                er.append(math.degrees(math.acos(float(np.clip(e @ dv / np.linalg.norm(e), -1, 1)))))
        return {"n": n, "med": float(np.median(er)) if er else float("nan"), "max": float(max(er)) if er else float("nan")}

    HOLE_CFG = [(1, None), (1, 0.002), (2, None), (2, 0.002), (2, 0.004)]
    hol = {cfg: _holes(*cfg) for cfg in HOLE_CFG}
    print("  穴(2 台で見えた姿勢 / 40、角度誤差 中央値・最大): " + "; ".join(
        "×%d %s → %d(%.1f° / %.1f°)" % (s, "メッシュ" if sp is None else "3DGS %g mm" % (1e3 * sp), hol[(s, sp)]["n"], hol[(s, sp)]["med"],
                                     hol[(s, sp)]["max"]) for s, sp in HOLE_CFG))
    print("  → 3DGS のぼけ(低域 0.3 px² + 円盤の大きさ)は、玉 17 px・穴 5 px の像では穴を塗りつぶす。穴を読むには玉に画素が要り(× 2 以上)、"
          "穴の中に入るガウシアンが要る(間隔 ≤ 2 mm。4 mm では × 2 でも読めない)。(%.1f s)" % (time.time() - t_g))
    gate("3DGS の上の穴: × 2 の解像度・間隔 2 mm で 2 台で見えた姿勢 ≥ 8・誤差 中央値 < 5°、間隔 4 mm より多く見える、× 1 ではメッシュより少ない",
         hol[(2, 0.002)]["n"] >= 8 and hol[(2, 0.002)]["med"] < 5.0 and hol[(2, 0.002)]["n"] > hol[(2, 0.004)]["n"]
         and hol[(1, 0.002)]["n"] < hol[(1, None)]["n"],
         "×2 2 mm %d(%.1f°)、×2 4 mm %d、×1 2 mm %d vs メッシュ %d" % (hol[(2, 0.002)]["n"], hol[(2, 0.002)]["med"], hol[(2, 0.004)]["n"],
                                                             hol[(1, 0.002)]["n"], hol[(1, None)]["n"]))

    # ─────────────────────────────── 12. 連続技(受けた状態から続けて別の皿で) ─────────────────────────
    print("== 12. 連続技: 受けた皿から放ち、飛んでいる間に持ち替えて次の皿で受ける(もしかめ = 大皿 ↔ 中皿、3 皿 = 大皿 → 小皿 → 中皿)")
    t_c = time.time()
    combo_runs = [("もしかめ・画像", KD.COMBO_SEQUENCES["mosikame"], "image")]
    if not REDUCED:
        combo_runs += [("3 皿・画像", KD.COMBO_SEQUENCES["three_cups"], "image"), ("もしかめ・真値", KD.COMBO_SEQUENCES["mosikame"], "truth")]
    combo = {}
    for label, seq, pc in combo_runs:
        rr = _combo_run(seq, n_catch=10, perception=pc)
        cb = rr["combo"]
        combo[label] = rr
        if cb is None:
            print("  %s: 振り上げで失敗(%s)" % (label, rr["swing"]["end_reason"]))
            continue
        rs = [c["rel_speed"] for c in cb["catches"]]
        print("  %s: 振り上げの 1 回 + 連続 %d 回(終わり %s)= 協会のもしかめの級で %s 相当、着地の相対速さ %.2f〜%.2f m/s、けん玉との隙間の最小 %.1f mm(皿に乗っている間の接触 = 0、めり込みは無い)、"
              "手首の角速度の最大 %.1f rad/s%s" % (label, cb["count"], cb["end_reason"], KD._mosikame_grade(rr["count_total"]), min(rs), max(rs),
                                                1e3 * cb["min_gap"], cb["max_omega"],
                                                "、飛び始めを画像から決めた回数 %d" % len(rr["per"].flights) if pc == "image" else ""))
    print("  (%.1f s)" % (time.time() - t_c))
    ok_c = True
    for label, seq, pc in combo_runs:
        cb = combo[label]["combo"]
        ok_c &= (cb is not None and cb["count"] >= 10 and all(c["rose_then_fell"] for c in cb["catches"])
                 and max(c["rel_speed"] for c in cb["catches"]) <= 1.0 and cb["min_gap"] > -5e-4
                 and (pc != "image" or len(combo[label]["per"].flights) >= 10))
    gate("連続技 10 回連続(ユーザーの合格線「10 回成功すれば良し」= 協会のもしかめ 5 級相当): 毎回 昇ってから下降中に受け、けん玉に触れず、"
         "画像では飛び始めも画像から", ok_c, " / ".join("%s %d" % (k, v["combo"]["count"] if v["combo"] else 0) for k, v in combo.items()))

    # ─────────────────────────────── 11. 図 ─────────────────────────
    if figs.enabled():
        print("== 11. 図")
        CV = 1
        cam = rig[CV]
        k_top = int(np.argmax(P_tru[:, 2]))
        frames = [imgs[CV] for imgs in per.images]
        cup_uv = BT.reproject(np.array([img_run["cup"][min(int(round(t / 1e-3)), len(img_run["cup"]) - 1)] for t in T_f]), cam["pose"], cam["K"])
        img = frames[k_top].copy()
        img = np.asarray(AN.crosshair(img, tuple(BT.reproject(P_tru[k_top][None], cam["pose"], cam["K"])[0]), color="baseline",
                                      width=1, gap=14, extent=22))
        ball_uv = BT.reproject(P_tru, cam["pose"], cam["K"])
        i_top = min(int(round(T_f[k_top] / 1e-3)), len(img_run["hand"]) - 1)
        KW.kendama_pose(world, img_run["hand"][i_top], P_tru[k_top], R_ball=per.R_ball[k_top])
        img = _inset(img, _zoom(world, cam, _zoom_centre(ball_uv[k_top], cup_uv[k_top])), "けん玉のまわり(3 倍の解像度で描き直し)")
        img = np.asarray(AN.text_box(img, "カメラ 2  t = %.2f s(玉の頂点)  十字 = 玉の真値の投影" % T_f[k_top], (8, 8), anchor="lt", font_size=12))
        figs.save("rig_view", img, "カメラ 2(480 × 360、45°、方位 90°、1.5 m)のコマ、玉が頂点にいる t = %.2f s。JKA 16-2 型の寸法(玉 60 mm、"
                                   "けん 160 mm、横幅 70 mm、大皿 42 mm)で作った世界で、左の枠はけん玉のまわりを同じカメラで 3 倍の解像度に描き直した窓(皿持ち: "
                                   "けん先が 15° 下、大皿が上。玉は糸穴の側へ 10 cm 逃がしたけんの上へ昇っている)。2 台の検出から三角測量した"
                                   "玉の誤差の中央値 %.2f mm。" % (T_f[k_top], 1e3 * np.median(eb)))
        panels, caps = [], []
        for trick in TRICKS:
            panels.append(_closeup(KD.kendama_params(trick=trick)))
            caps.append("%s(%s)" % (KD.KENDAMA_TRICKS[trick]["name"], {"cross": "皿持ち", "ken": "けん持ち", "spike": "けん先をつまむ"}[
                KD.KENDAMA_TRICKS[trick]["grip"]]))
        figs.save_grid("kendama_closeup", panels, captions=caps, ncols=2,
                       caption="近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → "
                               "中皿)、皿胴の両端がラッパのように開いた大皿(赤)・小皿(紫)、中皿(青)、直径 %d mm・深さ 40 mm の穴(くぼみ)のある玉、"
                               "皿胴の糸穴から出る糸。寸法は JKA 16-2 型(けん 160 mm、横幅 70 mm、皿 42 / 38 / 35 mm)。玉の位置と向きは"
                               "見せるために置いたもの。" % round(2e3 * kp["hole_radius"]))
        mt = (sim["t"] <= 0.45) & (sim["t"] > 0.0)
        mc = mt & taut
        figs.save_plot("tension_closed_form", [("積分器の張力(射影で消した速度から)", sim["t"][mt], sim["tension"][mt]),
                                               ("閉形式 m(v²/L + g cos θ)(張っている間)", sim["t"][mc], T_closed[mc])],
                       kinds=["line", "line"], xlabel="t [s]", ylabel="張力 [N]",
                       caption="真下から 150° 相当の速さ(%.2f m/s)で打ち出した玉のひも(有効長 %.2f m)の張力。積分器の推定は閉形式と最大 %.2f %% で一致し、"
                               "cos θ_s = (2/3) cos θ₀ の角(閉形式 %.2f°、測定 %.2f°)で 0 になって弛む。" % (
                                   v0, L, 100 * ten_rel.max(), math.degrees(th_s), math.degrees(th_s_meas)))
        ok_f = okb
        figs.save_plot("catch_yz", [("玉(真値)", img_run["p"][:, 1], img_run["p"][:, 2]),
                                    ("大皿の縁の中心(画像の閉ループ)", img_run["cup"][:, 1], img_run["cup"][:, 2]),
                                    ("玉(2 台の三角測量)", P_hat[ok_f, 1], P_hat[ok_f, 2])],
                       kinds=["line", "line", "scatter"], xlabel="y [m]", ylabel="z [m]", xlim=(-0.11, 0.16),
                       caption="y–z 面(手元を逃がす向き)。横 2 cm にずれて吊った玉を %.1f cm 持ち上げ、後半で手元を −y へ 10 cm 逃がす。玉は t = %.3f s に"
                               "弛んで昇り、皿は玉の下端がけん玉を越えるまで待ってから(hold)水平に戻り(carry)、着地の直前に下がって(absorb)"
                               "t = %.3f s に横ずれ %.2f mm・相対速さ %.2f m/s で受ける。皿を動かした根拠は画像だけ(点 = 三角測量した玉)。" % (
                                   100 * lift, img_run["slack_t"], img_run["catch_t"], 1e3 * img_run["lateral"], _rel_speed(img_run)))
        gaps = KW.kendama_clearance(kp, img_run["hand"], img_run["p"])["gap"]
        in_pass = np.array([st in ("wait", "hold") for st in img_run["stage"]])
        gap_pass = float(gaps[:in_pass.size][in_pass].min())
        jp = {"lift": "振り上げ(膝で真上に)", "wait": "ひもが弛んだ → 待つ", "hold": "玉がけんを越えるまで待つ(hold)",
              "carry": "皿を玉の真下へ水平に運ぶ(carry)", "absorb": "着地で下げる(absorb)", "caught": "受けた", "plan": "計画"}
        gif = []
        gif_side = "left" if float(np.mean(cup_uv[:, 0])) > 240 else "right"          # 動画の間は同じ側(跳ねると見づらい)
        for k in range(len(frames)):
            fr = frames[k].copy()
            i_st = min(int(round(T_f[k] / 1e-3)), len(img_run["stage"]) - 1)
            st = img_run["stage"][i_st]
            if k == len(frames) - 1:
                st = "caught"
            logs = [pl for pl in img_run["plan_log"] if pl[0] <= T_f[k] + 1e-9]
            if logs and st in ("carry", "absorb"):
                tg = np.asarray(logs[-1][1]["landing"])
                uvt = BT.reproject(tg[None], cam["pose"], cam["K"])[0]
                if np.all(np.isfinite(uvt)) and 0 <= uvt[0] < 480 and 0 <= uvt[1] < 360:
                    fr = np.asarray(AN.crosshair(fr, (float(uvt[0]), float(uvt[1])), color="emphasis", width=2, gap=5, extent=16))
            i_k = min(int(round(T_f[k] / 1e-3)), len(img_run["hand"]) - 1)
            KW.kendama_pose(world, img_run["hand"][i_k], P_tru[k], R_ball=per.R_ball[k])
            fr = _inset(fr, _zoom(world, cam, _zoom_centre(ball_uv[k], cup_uv[k])), "けん玉のまわり(3 倍の解像度)", side=gif_side)
            fr = np.asarray(AN.text_box(fr, "t = %.2f s  %s" % (T_f[k], jp.get(st, st)), (8, 8), anchor="lt", font_size=12))
            if logs and st in ("carry", "absorb"):
                fr = np.asarray(AN.text_box(fr, "十字 = 画像の予測から読んだ着地点", (8, 352), anchor="lb", font_size=11))
            gif.append(fr)
        gif += [gif[-1]] * 10
        figs.save_gif("catch_gif", gif, fps=10,
                      caption="カメラ 2、%d fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = %.3f s にひもが弛む(画像での検出 %.3f s)→ 玉がけんを"
                              "越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = %.3f s に大皿で受ける。十字は画像の予測(弛んだ後のコマに当てた"
                              "重力つきの放物線)から読んだ着地点、枠の中は同じカメラでけん玉のまわりを 3 倍の解像度に描き直した窓。t ≈ 0.3 s に玉がけんに重なって見えるのはカメラから見た"
                              "重なりで、けんは糸穴の側へ 10 cm 逃げて玉の奥にある(その間の隙間の最小 %.0f mm)。正直に: 捕球は「縁に触れた瞬間に"
                              "横ずれ ≤ 21 mm・相対速さ ≤ 1 m/s・下降中」の判定で、縁での跳ねと転がりは描いていない。" % (
                                  FPS, img_run["slack_t"], t_det, img_run["catch_t"], 1e3 * gap_pass))
        figs.save_plot("prediction_error_vs_frames", [("画素雑音 0 px(20 試行の平均)", ns, np.log10(1e3 * cv0)),
                                                      ("画素雑音 2 px", np.arange(3, 3 + cv2.size), np.log10(1e3 * cv2))],
                       kinds=["line", "line"], xlabel="弛んだ後に使ったコマ数", ylabel="log10(捕球の瞬間の玉の位置の誤差 [mm])",
                       caption="弛んだ後の n コマ(100 fps)に重力つきの放物線(未知 6)を当て、捕球の瞬間の玉の位置を読んだ誤差(大皿、20 試行の平均)。"
                               "0 px: %.2f → %.2f mm、2 px: %.0f → %.2f mm。途中の増えは最大 %.2f mm(0 px)。3 コマでの大きな誤差は、短い区間の"
                               "速度の推定に三角測量の誤差が乗るため。" % (1e3 * cv0[0], 1e3 * cv0[-1], 1e3 * cv2[0], 1e3 * cv2[-1], 1e3 * rise0))
        figs.save_plot("success_vs_pixel_noise", [("成功率(20 試行)", np.array(PIX), np.array([rates[p] for p in PIX])),
                                                  ("横ずれの平均 / 21 mm", np.array(PIX), np.array([lats[p] / 0.021 for p in PIX]))],
                       kinds=["line", "line"], xlabel="検出の画素雑音 σ [px]", ylabel="成功率・横ずれの割合", ylim=(0.0, 1.05),
                       caption="画像だけの閉ループの成功率(大皿、各 20 試行): %s。0〜2 px で平らなのは皿の縁の余裕(半径 21 mm)が吸う分で、捕った試行の"
                               "横ずれの平均は %.1f → %.1f → %.1f mm(0 / 2 / 8 px)と増えている。落ちた試行は玉がけん玉(皿の縁)に当たった。" % (
                                   "、".join("%g px → %.2f" % (p, rates[p]) for p in PIX), 1e3 * lats[0.0], 1e3 * lats[2.0], 1e3 * lats[8.0]))
        # ── 3DGS の図: 同じ近接カメラでメッシュ(真の形)と 3DGS(密・粗・誤差つき)、つまみの検出率、3DGS の閉ループの動画
        cw, cpose, cK, csz = _closeup_scene(kp, 300)
        g_cfgs = [("メッシュ(真の形)", None), ("3DGS 間隔 2 mm", dict(spacing=0.002)), ("3DGS 間隔 16 mm", dict(spacing=0.016)),
                  ("3DGS 4 mm + 位置の誤差 5 mm・色 0.1", dict(spacing=0.004, pos_noise=0.005, color_noise=0.1))]
        g_panels, g_caps = [], []
        for lab, cfg in g_cfgs:
            if cfg is None:
                g_panels.append(DW.world_camera(cw, cpose, cK, csz, csz)["color"])
            else:
                gg = GSN.gs_from_world(cw, max_per_object=20000, **cfg)
                g_panels.append(GSN.gs_render(gg, cpose, cK, csz, csz)["color"])
            g_caps.append(lab)
        figs.save_grid("gs_views", g_panels, captions=g_caps, ncols=2,
                       caption="同じ近接カメラで、メッシュ(真の形)と、世界の面にガウシアンを貼った 3D Gaussian Splatting(gsplatnp: EWA 投影 + 手前からの "
                               "α 合成 + Mip-Splatting の不透明度の補正)。密(2 mm)は形も穴もほぼ同じ、粗い(16 mm)は滲む(玉のガウシアンは曲率の上限"
                               " σ ≤ 0.5 R = 15 mm まで大きくなる。糸は同じ上限で細かいまま)。皿の縁や穴の口の「角」に接する面は 1/4 の大きさで置く"
                               "(3DGS が縁で細かくするのと同じ)。誤差つき(位置 5 mm・色 0.1)は毛羽立って色がにじむ。正直に: ガウシアンは写真から"
                               "学習したものでなく真の形から作り、再構成の不完全さは密度と誤差のつまみで模す。")
        figs.save_plot("gs_noise_knobs", [("位置の誤差 [mm] → 玉の検出率", 1e3 * np.array(PNS), np.array(rp)),
                                          ("色の誤差 × 100 → 玉の検出率", 100 * np.array(CNS), np.array(rc)),
                                          ("間隔 [mm] → 玉の検出率", 1e3 * np.array(SPS), np.array([sw_sp[s]["rate"] for s in SPS]))],
                       kinds=["line", "line", "line"], xlabel="つまみの値(位置 mm・色 ×100・間隔 mm)", ylabel="2 台で玉を検出したコマの割合", ylim=(0.0, 1.05),
                       caption="3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)に"
                               "かけた。間隔 2〜64 mm では検出率 1.00(三角測量の誤差の中央値 %.2f〜%.2f mm)—— 玉の上の個数は曲率の上限で %d〜%d 個に保たれる。"
                               "崩すのは位置の誤差(20 mm で %.2f)と色の誤差(0.3 で %.2f。検出器の色の許容 0.12 を越える)。" % (
                                   1e3 * min(sw_sp[s]["med"] for s in SPS), 1e3 * max(sw_sp[s]["med"] for s in SPS),
                                   min(sw_sp[s]["n_ball"] for s in SPS), max(sw_sp[s]["n_ball"] for s in SPS), rp[-1], rc[-1]))
        CVg = 1
        camg = rig[CVg]
        Pg_true = np.column_stack([np.interp(Tg, g_run["t"], g_run["p"][:, k]) for k in range(3)])
        gif_g = []
        for k in range(len(per_g.frames)):
            i_k = min(int(round(Tg[k] / 1e-3)), len(g_run["hand"]) - 1)
            KW.kendama_pose(gsw, g_run["hand"][i_k], Pg_true[k], R_ball=per_g.R_ball[k])
            left = DW.world_camera(gsw, camg["pose"], camg["K"], int(camg["width"]), int(camg["height"]))["color"]
            right = np.asarray(per_g.images[k][CVg], np.float64).copy()
            b_uv = BT.reproject(Pg_true[k][None], camg["pose"], camg["K"])[0]
            c_uv = BT.reproject(g_run["cup"][min(i_k, len(g_run["cup"]) - 1)][None], camg["pose"], camg["K"])[0]
            zc = _zoom_centre(b_uv, c_uv)
            zl = _zoom(gsw, camg, zc)
            zr, zx0, zy0 = _zoom(gsw, camg, zc, gs=gs, ret_origin=True)
            uvd = per_g.frames[k]["uv"][CVg]
            logs = [pl for pl in g_run["plan_log"] if pl[0] <= Tg[k] + 1e-9]
            st = g_run["stage"][min(i_k, len(g_run["stage"]) - 1)] if k < len(per_g.frames) - 1 else "caught"
            uvt = None
            if logs and st in ("carry", "absorb"):
                uvt = BT.reproject(np.asarray(logs[-1][1]["landing"])[None], camg["pose"], camg["K"])[0]
                if not np.all(np.isfinite(uvt)):
                    uvt = None
            for tgt, sc, ox, oy, rad in ((right, 1, 0.0, 0.0, 12.0), (zr, 3, zx0, zy0, 30.0)):
                if np.all(np.isfinite(uvd)):
                    yy, xx = np.mgrid[0:tgt.shape[0], 0:tgt.shape[1]]
                    rr = np.hypot(xx - sc * (uvd[0] - ox), yy - sc * (uvd[1] - oy))
                    tgt[:] = np.asarray(AN.overlay_mask(tgt, (rr >= rad - 1.2 * sc / 3 - 0.8) & (rr <= rad + 1.2 * sc / 3 + 0.8), color="reference", alpha=1.0))
                if uvt is not None:
                    q = (sc * (float(uvt[0]) - ox), sc * (float(uvt[1]) - oy))
                    if 0 <= q[0] < tgt.shape[1] and 0 <= q[1] < tgt.shape[0]:
                        tgt[:] = np.asarray(AN.crosshair(tgt, q, color="wrong", width=2, gap=5, extent=16))
            left = _inset(left, zl, "メッシュの窓(3 倍の解像度)", side="right")
            right = _inset(right, zr, "3DGS の窓(輪 = 検出、十字 = 予測)", side="right")
            left = np.asarray(AN.text_box(left, "メッシュ(真の形)  t = %.2f s" % Tg[k], (8, 8), anchor="lt", font_size=12))
            right = np.asarray(AN.text_box(right, "3DGS 間隔 %.0f mm = 知覚が見る画像  %s" % (1e3 * GSP, jp.get(st, st)), (8, 8), anchor="lt", font_size=12))
            gif_g.append(np.hstack([left, np.ones((left.shape[0], 4, 3)), right]))
        gif_g += [gif_g[-1]] * 10
        figs.save_gif("gs_catch_gif", gif_g, fps=10,
                      caption="右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、%d fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。"
                              "右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左はメッシュ、右は同じ 3DGS)。青の輪 = 色度で検出した玉、"
                              "十字 = 弛んだ後のコマに当てた重力つきの放物線から読んだ着地点。t = %.3f s に大皿で受ける"
                              "(横ずれ %.2f mm、推定 %d 回は全部 3DGS の画像から)。" % (FPS, g_run["catch_t"], 1e3 * g_run["lateral"], g_run["n_estimates"]))
        cm = combo.get("もしかめ・画像")
        if cm is not None and cm["combo"] is not None:
            cb = cm["combo"]
            tc = np.array([c["t"] for c in cb["catches"]])
            zc = np.array([c["z_catch"] for c in cb["catches"]])
            figs.save_plot("combo_height", [("玉の高さ z(t)(画像だけの閉ループ)", cb["t"], cb["p"][:, 2]),
                                            ("受けた瞬間(大皿と中皿を交互に)", tc, zc)],
                           kinds=["line", "scatter"], xlabel="t [s](連続技の開始から)", ylabel="玉の中心の高さ [m]",
                           caption="もしかめ(大皿 ↔ 中皿)10 回連続。受けた皿から放つと玉は重力だけの放物線で約 %.0f cm 昇り、下りてくるところを、飛んでいる"
                                   "間に持ち替えた次の皿で受ける(着地の相対速さ %.2f〜%.2f m/s: 皿を玉と同じ向きに動かして速さを合わせる = 膝のクッション)。"
                                   "手元を動かす根拠は 2 台のカメラの画像だけ(飛び始めも画像から)。" % (
                                       100 * float(np.median([c["apex"] - c["z_catch"] for c in cb["catches"]])),
                                       min(c["rel_speed"] for c in cb["catches"]), max(c["rel_speed"] for c in cb["catches"])))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
