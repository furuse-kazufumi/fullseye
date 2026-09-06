# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光で鏡面反射を剥がす —— フレネルの式で真値を作り、分離結果を突き合わせる。

EXTEND: 実際の偏光カメラ(Sony IMX250MZR = 画素上に 0/45/90/135 度の
ワイヤグリッドを敷いた division-of-focal-plane センサ)の生データに差し替えるなら、
本 PoC の ``render_sweep`` だけを実データ読み込みに置き換える。留意点は 4 つ。
(1) **デモザイクの前に生 Bayer 相当の 2x2 偏光モザイクを分離する** —— 4 枚は
互いに半画素ずれた別々の視点なので、補間せずに 1/2 解像度で扱うのが最も正直。
補間すると縁で偏光度が跳ね、それが「鏡面」として分離結果に漏れる。
(2) **リニアな輻度に戻す** —— 本族の op は全部リニア RGB / リニア輻度が前提で、
sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけ。
(3) **飽和を最優先で潰す** —— 8-(c) 節のとおり、白飛びは例外も出さず拡散を
過大評価する側へ倒し、しかも画素率に対して超線形に悪化する。露光を切り詰めるか
HDR 合成する方が、偏光子の角度較正に手をかけるより効く。角度較正は同じ節の
実測では **一番効かない**(素子ばらつき 1 度で誤差 1.1e-4)。ただし全画素共通の
オフセットは分離を一切壊さない代わりに **方位(AoLP)を丸ごと δ ずらす**ので、
形状復元に方位を使うなら絶対角の較正が要る。壊れる先が違う。
(4) **暗電流・黒レベルを引く** —— オフセットが残ると ``I_min`` が持ち上がり、
拡散成分が一律に過大評価される(これは雑音と違って平均しても消えない)。

この PoC が示すこと:

1. **真値は自分で作る** —— 拡散(無偏光)と鏡面(部分偏光)を s/p 成分に分けて
   自分で合成し、フレネルの式から偏光度を出す。分離結果はその真値と突き合わせる。
2. **ゼロ点を置く** —— 「分離しない」「フレームの最小値を拡散とみなす」を並べ、
   偏光を使う手が何倍勝つのかを数字で出す。**20 度では 1.2 倍しか勝たない。**
3. **ブリュースター角が最良、は本当か** —— 20/40/56.31/70 度で測ると、拡散成分の
   誤差は閉形式 ``R_p * E`` に厳密一致し、ブリュースター角で 0 になる。
4. **壊れる条件を数字で** —— 雑音・偏光子角度の較正誤差・白飛びの 3 つ。

★ この PoC が出した道具の穴は末尾の「所見」節に 5 件まとめた。要点は
``polarization_separate`` の返す "diffuse" が **``R_p * E`` だけ系統的に大きい**
こと、そしてその補正に必要な入射角の口が op に無いこと。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import match3d                                                   # noqa: E402
import specularity                                               # noqa: E402

ETA = 1.5                       # 誘電体(ガラス / 樹脂)の屈折率
THETA_B = math.degrees(math.atan(ETA))          # ブリュースター角 = 56.3099 度
ANGLES = (0.0, 45.0, 90.0, 135.0)               # DoFP センサの 4 方位
H, W = 96, 128
E0 = 3.0                        # 鏡面ローブに入る光源の照度(拡散の数倍が普通)
AZIMUTH = 22.5                  # 入射面の方位。4 方位の格子から最も遠い最悪値
THETAS = (20.0, 40.0, THETA_B, 70.0)


# --------------------------------------------------------------------------- #
# 1. 真値の生成 —— 拡散・鏡面・フレネル                                          #
# --------------------------------------------------------------------------- #
def scene(h=H, w=W):
    """拡散輻度 (H,W) と鏡面ローブ (H,W) を作る。乱数は使わない。

    拡散側は同心円の縞・斜めの傾き・暗いパッチを重ねた **構造を持つ** 場にする。
    一様な板だと「どの画素でも同じ答え」になり、画素ごとに壊れる不具合が
    平均に隠れる(乱数でも同じ理由で隠れる)。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.hypot(yy - cy, xx - cx) / max(h, w)
    diffuse = 0.30 + 0.16 * np.cos(14.0 * r) + 0.10 * (xx / (w - 1))
    diffuse[10:26, 12:34] = 0.02                    # 暗いパッチ(雑音が最初に壊す所)
    diffuse[60:80, 90:120] = 0.55                   # 明るいパッチ
    diffuse = np.clip(diffuse, 0.02, 0.60)
    # 鏡面ローブ = 光源の像。中心を外し、拡散の縞とも暗パッチとも重ねる。
    gy, gx = 0.42 * (h - 1), 0.58 * (w - 1)
    lobe = np.exp(-(((yy - gy) / (0.16 * h)) ** 2 + ((xx - gx) / (0.16 * w)) ** 2))
    return diffuse, lobe


def fresnel_sp(theta_deg, eta=ETA):
    """入射角(度)→ (R_s, R_p)。空気 → 屈折率 eta の誘電体、強度反射率。

    r_s = (n1 cos_i - n2 cos_t)/(n1 cos_i + n2 cos_t)
    r_p = (n1 cos_t - n2 cos_i)/(n1 cos_t + n2 cos_i)
    ブリュースター角 tan(theta_B) = n2/n1 で r_p = 0 —— **p 偏光が消える**ので
    反射光は s 偏光だけになる = 偏光度 1。これが「偏光で鏡面が剥がせる」の全て。
    """
    ci = math.cos(math.radians(theta_deg))
    st = math.sin(math.radians(theta_deg)) / eta
    ct = math.sqrt(max(0.0, 1.0 - st * st))
    rs = (ci - eta * ct) / (ci + eta * ct)
    rp = (ct - eta * ci) / (ct + eta * ci)
    return rs * rs, rp * rp


def specular_components(lobe, theta_deg, irradiance=E0):
    """鏡面反射の s 成分・p 成分の輻度 (H,W) を返す。

    無偏光の光源(照度 E)は s と p に E/2 ずつ配分される。反射すると各々
    ``R_s * E/2`` と ``R_p * E/2`` になる。合計 = 鏡面の全輻度、差 = 偏光した分。
    """
    rs, rp = fresnel_sp(theta_deg)
    return 0.5 * rs * irradiance * lobe, 0.5 * rp * irradiance * lobe


def render_sweep(diffuse, spec_s, spec_p, angles=ANGLES, azimuth=AZIMUTH):
    """偏光子掃引 (N,H,W) を合成する。検光子角 t は s 軸から測る。

    ``I(t) = 0.5*D + I_s cos^2(t - az) + I_p sin^2(t - az)``
    拡散は完全無偏光なのでどの角度でも半分通る。鏡面は s/p が独立にマリュスの
    法則に従う。``specularity.polarization_render`` は鏡面を **完全偏光** として
    しか描けないので(下の 2 節で示すとおり等価な組み替えは可能)、部分偏光の
    前方モデルはここで自分で書く。
    """
    t = np.radians(np.asarray(angles, float) - azimuth)[:, None, None]
    return 0.5 * diffuse[None] + spec_s[None] * np.cos(t) ** 2 \
        + spec_p[None] * np.sin(t) ** 2


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def ratio(num, den):
    """num/den。分母 0 は inf(0/0 は 1)—— 比の表で 0 除算に落ちないように。

    ゼロ点が **厳密に** 真値を当てることが実際に起きる(6 節の方位 0/45 度)。
    そこを例外で落とすと、一番面白い行だけが表から消える。
    """
    if den == 0.0:
        return 1.0 if num == 0.0 else float("inf")
    return num / den


def separate(frames, angles=ANGLES, mvf=0.0):
    return specularity.polarization_separate(frames, angles, max_violation_frac=mvf)


# --------------------------------------------------------------------------- #
# ゼロ点(null)                                                                #
# --------------------------------------------------------------------------- #
def null_no_separation(frames):
    """何もしない —— 撮れた輻度をそのまま拡散だとみなす。

    等間隔 4 方位の平均は当てはめの a0 に厳密一致するので、全輻度 = 2*平均。
    """
    return 2.0 * frames.mean(axis=0)


def null_frame_min(frames):
    """素朴 —— 4 枚の画素ごと最小値を拡散とみなす(残りが鏡面)。"""
    return frames.min(axis=0)


def null_frame_min2(frames):
    """素朴 + 尺度だけ直した版 —— 2 x (4 枚の最小値)。

    op と同じ ``2 * I_min`` の式だが、``I_min`` を **正弦波当てはめでなく
    離散の最小値**で取る。方位が 4 方位の格子に乗っていれば op と一致し、
    外れていると必ず過大評価になる。ゼロ点として一番手強い。
    """
    return 2.0 * frames.min(axis=0)


def main():
    t_all = time.perf_counter()
    diffuse, lobe = scene()

    # ---------------------------------------------------------------- #
    print("=== 1. フレネル —— 入射角と鏡面の偏光度 ===")
    print(f"  屈折率 {ETA} / ブリュースター角 tan^-1({ETA}) = {THETA_B:.4f} 度")
    print(f"  {'入射角':>8}{'R_s':>10}{'R_p':>12}{'(R_s+R_p)/2':>14}"
          f"{'鏡面の偏光度':>14}{'match3d 差':>12}")
    for th in (0.0, 20.0, 40.0, THETA_B, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp) if (rs + rp) > 0 else 0.0
        ref = match3d.fresnel_reflectance(math.cos(math.radians(th)), 1.0, ETA)
        print(f"  {th:>8.2f}{rs:>10.5f}{rp:>12.3e}{0.5 * (rs + rp):>14.5f}"
              f"{dop:>14.6f}{abs(0.5 * (rs + rp) - ref):>12.2e}")
    print("  → ブリュースター角で R_p が **厳密に 0.0**(丸めですらない: 分子の")
    print("     cos_t - eta*cos_i が倍精度で完全に打ち消す)= 偏光度 1。")
    print("     垂直入射(0 度)は偏光度 0 —— 偏光板を回しても鏡面は動かない。")
    print("     85 度で偏光度が 0.195 まで落ちるのも重要: **浅すぎても深すぎても")
    print("     偏光は効かない**。使える窓はブリュースター角の周りに限られる。")
    print("     最右列は match3d.fresnel_reflectance との差。同じ式を見ている。")
    if figs.enabled():
        # 図: この PoC の物理はこの 3 本の曲線に尽きる。R_p がブリュースター角で
        #     0 を横切ることが「偏光で鏡面が剥がせる」の全て。
        th_ax = np.linspace(0.0, 89.0, 90)
        rs_c = np.array([fresnel_sp(t)[0] for t in th_ax])
        rp_c = np.array([fresnel_sp(t)[1] for t in th_ax])
        figs.save_plot("fresnel",
                       [("R_s", th_ax, rs_c), ("R_p", th_ax, rp_c),
                        ("鏡面の偏光度 (R_s-R_p)/(R_s+R_p)", th_ax,
                         (rs_c - rp_c) / np.maximum(rs_c + rp_c, 1e-30))],
                       xlabel="入射角 [度]", ylabel="強度反射率 / 偏光度",
                       title="フレネル(屈折率 %.1f、ブリュースター角 %.2f 度)"
                             % (ETA, THETA_B),
                       caption="R_p がブリュースター角で 0 を横切る。浅すぎても"
                               "深すぎても偏光度は落ちる —— 使える窓は限られる。")

    # ---------------------------------------------------------------- #
    print("\n=== 2. 前方モデル —— op の完全偏光モデルとの等価な組み替え ===")
    s_s, s_p = specular_components(lobe, THETA_B)
    frames = render_sweep(diffuse, s_s, s_p)
    # I(t) = 0.5*(D + 2*I_p) + (I_s - I_p) cos^2(t-az)  という恒等式。
    eff_d, eff_s = diffuse + 2.0 * s_p, s_s - s_p
    ref = specularity.polarization_render(eff_d, eff_s, ANGLES, azimuth_deg=AZIMUTH)
    print(f"  自作の部分偏光レンダ vs polarization_render(等価な split)"
          f"の最大差 {np.abs(frames - ref).max():.3e}")
    print("  → 部分偏光の鏡面は「無偏光 2*I_p + 完全偏光 (I_s - I_p)」に厳密に")
    print("     分解できる。**op が拡散として返すのは D ではなく D + 2*I_p** で、")
    print("     これが以下すべての誤差の正体(モデルの外挿ではなく恒等式)。")
    for th in (20.0, 70.0):
        a, b = specular_components(lobe, th)
        f2 = render_sweep(diffuse, a, b)
        r2 = specularity.polarization_render(diffuse + 2 * b, a - b, ANGLES,
                                             azimuth_deg=AZIMUTH)
        print(f"     入射角 {th:>5.1f} 度でも最大差 {np.abs(f2 - r2).max():.3e}")

    # ---------------------------------------------------------------- #
    print("\n=== 3. ブリュースター角での分離 —— ゼロ点と並べる ===")
    d_true = diffuse
    s_true = s_s + s_p
    d_op, s_op = separate(frames)
    rho = 1.0                                       # ブリュースター角の鏡面偏光度
    print(f"  真値: 拡散 平均 {d_true.mean():.4f} / 鏡面 最大 {s_true.max():.4f}"
          f"(ローブ中心)")
    print(f"  {'手法':<34}{'拡散 RMSE':>12}{'鏡面 RMSE':>12}{'op 比':>9}")
    base = rmse(d_op, d_true)
    rows = [
        ("ゼロ点 1: 分離しない(全輻度)", null_no_separation(frames), None),
        ("ゼロ点 2: 4 枚の最小値", null_frame_min(frames), None),
        ("ゼロ点 3: 2 x 4 枚の最小値", null_frame_min2(frames), None),
        ("polarization_separate", d_op, s_op),
    ]
    for name, d_est, s_est in rows:
        e = rmse(d_est, d_true)
        es = rmse(s_est, s_true) if s_est is not None else float("nan")
        rs_txt = f"{es:>12.3e}" if s_est is not None else f"{'—':>12}"
        print(f"  {name:<34}{e:>12.3e}{rs_txt}{ratio(e, base):>11.3g}")
    print("  → ブリュースター角では op の誤差が 1e-17 台 = 倍精度の床。R_p = 0 な")
    print("     ので「2*I_min = D」が恒等式として成り立ち、ゼロ点との比は 14〜15 桁。")
    print("     この「比が意味を失うほど勝つ」のはブリュースター角限定で、4 節で")
    print("     角度を振ると 1.2 倍まで落ちる。**一点で測って一般化してはいけない。**")

    # ---------------------------------------------------------------- #
    print("\n=== 4. 入射角を振る —— 誤差は R_p * E に一致するか ===")
    print(f"  {'入射角':>8}{'鏡面偏光度':>12}{'op 拡散RMSE':>14}{'閉形式 R_p*E':>14}"
          f"{'差':>10}{'ゼロ点1':>12}{'ゼロ点1/op':>12}")
    ang_rows = {}
    g_rms = float(np.sqrt(np.mean(lobe ** 2)))
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp)
        e = rmse(d_e, diffuse)
        pred = rp * E0 * g_rms                      # 2*I_p = R_p * E * lobe
        e0n = rmse(null_no_separation(f), diffuse)
        rt = ratio(e0n, e)
        ang_rows[th] = (dop, e, pred, e0n, rt)
        print(f"  {th:>8.2f}{dop:>12.6f}{e:>14.3e}{pred:>14.3e}"
              f"{abs(e - pred):>10.1e}{e0n:>12.3e}{rt:>12.3g}")
    th_ax = list(THETAS)
    figs.save_plot("angle_error",
                   [("op の拡散 RMSE", th_ax, [ang_rows[t][1] for t in th_ax]),
                    ("閉形式 R_p * E", th_ax, [ang_rows[t][2] for t in th_ax]),
                    ("ゼロ点 1(分離しない)", th_ax,
                     [ang_rows[t][3] for t in th_ax])],
                   xlabel="入射角 [度]", ylabel="拡散の RMSE",
                   title="誤差は R_p * E に一致する(ブリュースター角で 0)",
                   caption="実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪い"
                           "のに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。")
    print("  → 誤差は閉形式 R_p * E に厳密一致(差は 1e-17 台)。理論どおり")
    print("     ブリュースター角で最良。ただし **20 度ではゼロ点の 1.2 倍しか")
    print("     勝たない** —— 偏光板を付ける価値が無い角度がある。")
    print("  → **最適角は評価軸で変わる、というのがこの表の一番の中身。**")
    print("     絶対誤差で並べると 56.31 < 40 度(8.6e-3)< 20 度(2.0e-2)")
    print("     < 70 度(2.6e-2)で、**70 度は 20 度より悪い**(R_p が 1 節の表の")
    print("     とおり 20 度 0.033 → 70 度 0.042 と、深い側で急に立ち上がるため)。")
    print("     ところがゼロ点との比では 70 度(4.03)が最良で 20 度(1.20)が最悪。")
    print("     鏡面自体が 70 度で強いので「何もしない」損が大きいから。")
    print("     ハイライトを消したいなら比を、拡散の絶対値が要るなら絶対誤差を見る。")

    # ---------------------------------------------------------------- #
    print("\n=== 5. 入射角が既知なら偏りは閉形式で消せる ===")
    print(f"  {'入射角':>8}{'op RMSE':>12}{'補正後 RMSE':>14}{'雑音増幅 1/ρ':>14}")
    corr_rows = {}
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        r = (rs - rp) / (rs + rp)
        s_c = s_e / r                               # 真の鏡面 = 偏光分 / 偏光度
        d_c = (d_e + s_e) - s_c                     # 全輻度は保存されている
        corr_rows[th] = (rmse(d_e, diffuse), rmse(d_c, diffuse), 1.0 / r)
        print(f"  {th:>8.2f}{corr_rows[th][0]:>12.3e}{corr_rows[th][1]:>14.3e}"
              f"{1.0 / r:>14.2f}")
    print("  → I_s + I_p = (I_s - I_p)/ρ、ρ = (R_s-R_p)/(R_s+R_p) = 鏡面の偏光度。")
    print("     入射角さえ分かれば偏りは完全に消える(1e-17 台)。代償は 1/ρ 倍の")
    print("     雑音増幅で、20 度では 5.9 倍。**op にはこの ρ を渡す口が無い**(所見 a)。")

    # ---------------------------------------------------------------- #
    print("\n=== 6. 方位が 4 方位の格子に乗るかどうか ===")
    print("  ブリュースター角で測る(op が厳密になる条件。ここで出る差は")
    print("  すべて「方位が格子に乗るか」だけに由来する)。右 2 列は入射角 70 度。")
    print(f"  {'入射面方位':>10}{'op RMSE':>12}{'ゼロ点3':>12}{'比':>10}"
          f"{'op(70度)':>12}{'ゼロ点3(70度)':>16}{'比':>8}")
    az_rows = {}
    ab_b, bb_b = specular_components(lobe, THETA_B)
    ab_7, bb_7 = specular_components(lobe, 70.0)
    for az in (0.0, 10.0, 22.5, 45.0):
        fb = render_sweep(diffuse, ab_b, bb_b, azimuth=az)
        f7 = render_sweep(diffuse, ab_7, bb_7, azimuth=az)
        e, e3 = rmse(separate(fb)[0], diffuse), rmse(null_frame_min2(fb), diffuse)
        e7, e37 = rmse(separate(f7)[0], diffuse), rmse(null_frame_min2(f7), diffuse)
        az_rows[az] = (e, e3, e7, e37)
        print(f"  {az:>10.1f}{e:>12.3e}{e3:>12.3e}{ratio(e3, e):>10.3g}"
              f"{e7:>12.3e}{e37:>16.3e}{ratio(e37, e7):>8.2f}")
    print("  → 方位が 0 度 / 45 度(= 測った角度そのもの)では離散最小値が真の")
    print("     I_min に **厳密に**一致するので、素朴なゼロ点 3 の誤差が 0 になり、")
    print("     丸めの乗る当てはめ(4.7e-17)より **わずかに良い**(比 0 はそれ)。")
    print("     22.5 度で初めて差がつく。正弦波当てはめが効くのは格子から外れた")
    print("     ときだけで、「当てはめだから常に良い」ではない。")
    print("  → 右 2 列(70 度)では同じ比が 1.9 倍まで縮む。op 側に R_p 由来の偏り")
    print("     2.6e-2 が常時載っていて、方位のずれによる差をそれが覆い隠すため。")
    print("     **比を見るときは分母が何で律速されているかを先に見る。**")

    # ---------------------------------------------------------------- #
    print("\n=== 7. 偏光度と Stokes —— 別の op も同じ真値に合うか ===")
    a70, b70 = specular_components(lobe, 70.0)
    f70 = render_sweep(diffuse, a70, b70)
    dolp = specularity.polarization_dolp_map(f70, ANGLES)
    dolp_true = (a70 - b70) / (diffuse + a70 + b70)
    print(f"  polarization_dolp_map と閉形式 (I_s-I_p)/(D+I_s+I_p) の最大差 "
          f"{np.abs(dolp - dolp_true).max():.3e}")
    print(f"  画素ごとの偏光度: 最大 {dolp.max():.4f}(ローブ中心)/ "
          f"ローブ外 {dolp[0, 0]:.3e}")
    st = specularity.polarization_stokes(f70, ANGLES)
    s0_true = float((diffuse + a70 + b70).mean())
    print(f"  polarization_stokes S0 {st[0]:.6f} / 閉形式の全輻度平均 "
          f"{s0_true:.6f}(差 {abs(st[0] - s0_true):.2e})")
    print(f"  S3 = {st[3]:.1f} —— 直線検光子だけでは円偏光は見えない(仕様どおり)。")
    print(f"  → 場面全体の偏光度は {math.hypot(st[1], st[2]) / st[0]:.4f} で、")
    print(f"     画素最大 {dolp.max():.4f} の 1/6 しかない。**空間平均は鏡面を")
    print("     薄める** —— ここを取り違えると「偏光が使えない場面」と誤判定する。")

    # ---------------------------------------------------------------- #
    print("\n=== 8. 壊れる条件 —— すべてブリュースター角で測る ===")
    print("  雑音も較正誤差も飽和も無ければ op はここで厳密(3 節)。だから以下の")
    print("  表に出る誤差は 100% 壊れ由来で、モデルの偏りと混ざらない。")
    bias70 = ang_rows[70.0][1]              # 入射角 70 度で常時載る偏り = 物差し
    print(f"  物差し: 入射角 70 度で常時載る R_p 由来の偏り = {bias70:.3e}。")
    print("  壊れがこれを超えたら「角度を選び直す」より先に直すべき問題になる。")

    print("\n=== 8-(a) 雑音 ===")
    print(f"  {'雑音σ':>10}{'既定(fail-closed)':>20}{'違反画素率':>12}"
          f"{'RMSE(強制通過)':>16}{'70度の偏り比':>14}")
    fb = render_sweep(diffuse, s_s, s_p)            # ブリュースター角の掃引
    noise_rows = {}
    rng = np.random.default_rng(20260906)
    cvec = np.cos(np.radians(2 * np.asarray(ANGLES)))[:, None, None]
    svec = np.sin(np.radians(2 * np.asarray(ANGLES)))[:, None, None]
    for sigma in (0.0, 1e-4, 1e-3, 2e-3, 3e-3, 4e-3, 5e-3, 1e-2, 3e-2, 1e-1):
        fn = np.maximum(fb + sigma * rng.standard_normal(fb.shape), 0.0)
        try:
            separate(fn)
            verdict = "通る"
        except ValueError:
            verdict = "拒否"
        d_f, _ = separate(fn, mvf=1.0)              # 強制的に通した場合
        # 違反画素率 = 当てはめた最小輻度が負になった画素(4 方位なら閉形式)
        a0 = fn.mean(axis=0)
        amp = np.hypot(2 * (fn * cvec).mean(axis=0), 2 * (fn * svec).mean(axis=0))
        frac = float((a0 - amp < 0).mean())
        e = rmse(d_f, diffuse)
        noise_rows[sigma] = (verdict, frac, e)
        if sigma == 1e-2:
            noisy_ref = fn
        print(f"  {sigma:>10.0e}{verdict:>18}{frac:>12.5f}{e:>16.3e}"
              f"{e / bias70:>14.3f}")
    print("  → **既定の fail-closed が拒否に転じる境界は σ = 3e-3 と 4e-3 の間**")
    print("     (暗パッチの拡散 0.02 = 最小輻度 0.01 に雑音が届く点。12288 画素の")
    print("     うち 0.03% = 4 画素が負の最小輻度を吐いた時点で全体が止まる)。")
    print("     強制通過させた誤差は σ にほぼ厳密に比例する(σ 10 倍 → 誤差 10 倍)。")
    print("     70 度の偏り 2.56e-2 に並ぶのは **σ ≈ 1.3e-2**。つまり σ がそれ未満")
    print("     なら、雑音を減らすより **入射角を選び直す方が効く**。")
    print("     拒否は「使えない」ではなく「その画素の偏光信号が雑音に埋もれた」")
    print("     という正しい報告(1 画素でも全体を止めるのは設計どおり)。")

    # 4 枚目は何を買っているのか。3 枚(0/45/90)でも未知数はちょうど決まる。
    e4 = noise_rows[1e-2][2]
    e3 = rmse(specularity.polarization_separate(
        noisy_ref[:3], ANGLES[:3], max_violation_frac=1.0)[0], diffuse)
    noise_3v4 = (e3, e4)
    print(f"  σ=1e-2 で 3 枚(0/45/90){e3:.3e} vs 4 枚 {e4:.3e} "
          f"= 4 枚が {e3 / e4:.2f} 倍良い")
    print("  → **4 枚目は雑音があるときだけ効く。** 未知数は 3 つなので雑音が")
    print("     無ければ 3 枚で厳密に決まり(この PoC の他の節は 3 枚でも同じ数字)、")
    print("     4 枚目が買っているのは平均化だけ。DoFP センサが 4 方位を敷くのは")
    print("     解を決めるためではない。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(b) 偏光子角度の較正誤差 ===")
    print(f"  {'誤差δ[度]':>10}{'全体オフセット':>16}{'方位の誤差[度]':>16}"
          f"{'1 枚だけずれ':>16}{'70度の偏り比':>14}")
    cal_rows = {}
    for delta in (0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
        f_all = render_sweep(diffuse, s_s, s_p,
                             angles=tuple(x + delta for x in ANGLES))
        e_all = rmse(separate(f_all)[0], diffuse)   # 公称角で解く
        sk = specularity.polarization_stokes(f_all, ANGLES)
        az_est = 0.5 * math.degrees(math.atan2(sk[2], sk[1]))
        az_err = abs((az_est - AZIMUTH + 90.0) % 180.0 - 90.0)
        f_one = render_sweep(diffuse, s_s, s_p,
                             angles=(0.0, 45.0 + delta, 90.0, 135.0))
        e_one = rmse(separate(f_one, mvf=1.0)[0], diffuse)
        cal_rows[delta] = (e_all, az_err, e_one)
        print(f"  {delta:>10.1f}{e_all:>16.3e}{az_err:>16.3f}{e_one:>16.3e}"
              f"{e_one / bias70:>14.3f}")
    print("  → **全画素共通のオフセットは分離を一切壊さない**(20 度ずらしても")
    print("     1e-17 台のまま)。基底が丸ごと回るだけで、当てはめの平均も振幅も")
    print("     変わらないから。代わりに **方位(AoLP)がちょうど δ だけ狂う**")
    print("     (3 列目が δ に厳密一致)。壊れる先が違う 2 つを、1 つの「較正精度」")
    print("     という数字で語ってはいけない —— 絶対角は形状復元だけを壊す。")
    print("  → 1 枚だけのずれ(= 相対角の誤差)は分離そのものを壊すが、**係数が")
    print("     小さい**: δ <= 5 度では 1 度あたり 1.14e-4 で厳密に比例し、その先は")
    print("     頭打ちになる(20 度で 1.5e-3)。20 度ずらしても 70 度の偏りの")
    print("     0.06 倍にしかならず、これは想定と逆だった。**この 3 つの壊れの")
    print("     中で較正誤差が一番効かない。** IMX250MZR 級の素子ばらつき 1 度は、")
    print("     偏光分離の観点では無視してよい(方位を使う形状復元では効く)。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(c) 鏡面の白飛び ===")
    print("  露光は固定のまま **光源だけを強くする**(拡散の最大は 0.275 で")
    print("  飽和しないので、飛ぶのはハイライトだけ)。真の拡散は不変。")
    print(f"  {'光源倍率':>10}{'鏡面ピーク':>12}{'飽和画素率':>12}{'例外':>8}"
          f"{'拡散RMSE':>14}{'70度の偏り比':>14}{'拡散に対する%':>16}")
    sat_rows = {}
    for k in (1.0, 3.0, 4.0, 5.0, 6.0, 8.0):
        fk = np.minimum(render_sweep(diffuse, k * s_s, k * s_p), 1.0)
        raw = render_sweep(diffuse, k * s_s, k * s_p)
        frac = float((raw > 1.0).mean())
        try:
            separate(fk)
            exc = "無し"
        except ValueError:
            exc = "拒否"
        d_k, _ = separate(fk, mvf=1.0)
        e = rmse(d_k, diffuse)
        sat_rows[k] = (frac, exc, e)
        print(f"  {k:>10.1f}{float((k * s_s).max()):>12.3f}{frac:>12.5f}{exc:>8}"
              f"{e:>14.3e}{e / bias70:>14.3f}{100 * e / diffuse.mean():>16.2f}")
    print("  → 白飛びは **一度も例外を出さない**。I_max が頭打ちになると振幅が")
    print("     縮み、I_min が持ち上がり、拡散が過大評価される側へ静かに倒れる。")
    print("     しかも壊れ方が急峻: 飽和 0.6% で 70 度の偏りの 0.15 倍、1.3% で")
    print("     0.49 倍、**2.4% で 1.35 倍**(拡散平均の 9.7% を誤る)。雑音(σ に")
    print("     比例)や較正誤差(δ に比例)と違い、**飽和は画素率に対して超線形**")
    print("     (画素率 1.8 倍で誤差 2.8 倍)。飛んだ画素では偏光情報が完全に")
    print("     失われるので、当てはめは残った 3 点に平気で正弦波を通す。")
    print("     fail-closed 検査は「最小輻度が負」= **下端しか見ておらず、上端の")
    print("     飽和は素通りする**(所見 c)。3 つの壊れのうちこれだけが黙っている。")

    # ---------------------------------------------------------------- #
    print("\n=== 9. 速度(この機械での実測)===")
    big_d, big_l = scene(1024, 1024)
    ba, bb = specular_components(big_l, 70.0)
    big = render_sweep(big_d, ba, bb)
    for label, fn in (("polarization_separate", lambda: separate(big)),
                      ("polarization_dolp_map",
                       lambda: specularity.polarization_dolp_map(big, ANGLES)),
                      ("polarization_stokes",
                       lambda: specularity.polarization_stokes(big, ANGLES)),
                      ("ゼロ点 3(最小値)", lambda: null_frame_min2(big))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<26}{1e3 * (time.perf_counter() - t0):>9.1f} ms  "
              f"(4 x 1024 x 1024)")
    print("  → 3 つの op はどれも同じ正弦波当てはめ 1 回で、コストは区別できない。")
    print("     素朴な最小値の 13 倍だが、1 Mpixel で 83 ms は毎フレーム回せる。")
    print("     **偏光板を付けない理由に計算コストは使えない。**")

    # ---------------------------------------------------------------- #
    print("\n所見(想定と違ったこと):")
    print("   (1) 「ブリュースター角付近が最良」は正しかったが、**理由が予想と")
    print("       違った**。最初は「鏡面が強く偏光するから分離しやすい」と書こうと")
    print("       したが、誤差の閉形式は R_p * E であって R_s には依らない。")
    print("       効いているのは「s が強い」ではなく「**p が消える**」の方。")
    print("   (2) 「ブリュースター角から離れるほど悪い」を対称だと思い込んでいた。")
    print("       R_p は浅い側では緩やか(0 度 0.040 → 20 度 0.033 → 40 度 0.014)")
    print("       なのに深い側では急峻(70 度 0.042)で、**70 度の絶対誤差は")
    print("       20 度より悪い**。それでもゼロ点比では 70 度が最良(4.0 対 1.2)。")
    print("       同じ実験の同じ列から、評価軸を変えると最適角が 40 度と 70 度に")
    print("       割れる。**「最良の入射角」は単独では意味を持たない。**")
    print("   (3) 素朴な 2 x 最小値が方位 0/45 度では op に引き分けた(6 節)。")
    print("       それどころか誤差が厳密に 0 で、丸めの乗る当てはめより少し良い。")
    print("       ゼロ点を 3 種類置かなければ「当てはめが常に勝つ」と書いていた。")
    print("   (4) 3 つの壊れの強さの順が予想と逆だった。**較正誤差が一番効かず**")
    print("       (20 度ずれても 70 度の偏りの 0.06 倍)、飽和が一番危ない。")
    print("       危険さは大きさではなく **黙るかどうか** で決まる: 雑音は拒否で")
    print("       止まり、較正誤差は小さく、飽和だけが例外なしで大きく外す。")

    print("\n所見(fullseye の穴 —— この PoC が出した道具の穴):")
    print("   (a) `polarization_separate` の返す \"diffuse\" は真の拡散より")
    print("       **常に R_p * E だけ大きい**(2 節の恒等式、4 節の実測)。docstring は")
    print("       「垂直入射で false」とだけ書くが、**偏りが閉形式で書ける**ことも、")
    print("       ρ = (R_s-R_p)/(R_s+R_p) を渡せば完全に消せることも書いていない。")
    print("       `specular_dop=` のような引数が 1 つあれば 5 節の補正が op 内で済む。")
    print("   (b) **AoLP(偏光の方位角)を返す op が無い。** `_polar_fit` は a1,a2 を")
    print("       計算しているので 0.5*atan2(a2,a1) を返すだけだが、外へ出る口は")
    print("       `polarization_stokes` の **場面全体 1 本**しかない。方位は入射面の")
    print("       向き = 面法線の方位そのもので、形状復元の主役なのに画素ごとに")
    print("       取れない(`polar_cam.py` は自前で計算していて op を使っていない)。")
    print("   (c) fail-closed 検査は下端(最小輻度が負)だけを見ており、**上端の")
    print("       飽和は素通りする**(8-c)。飽和は例外なしで拡散を過大評価する側へ")
    print("       倒れるので、雑音より質が悪い。`I >= 1.0` の画素率を返すか、")
    print("       `max_saturated_frac` があると同じ規律で守れる。")
    print("   (d) **画素ごとの Stokes 地図が無い。** `polarization_stokes` は空間平均")
    print("       (4,) だけで、7 節のとおり場面平均の偏光度 "
          f"{math.hypot(st[1], st[2]) / st[0]:.3f} は画素最大 {dolp.max():.3f} の")
    print("       1/6 以下。平均値で「偏光は使えない」と判断すると取り逃す。")
    print("   (e) 部分偏光の鏡面を **前方合成する op が無い**。")
    print("       `polarization_render` は鏡面完全偏光だけで、フレネルから")
    print("       (R_s, R_p) を作って掃引にする経路は本 PoC が手で書いた。")
    print("       `match3d.fresnel_reflectance` は s/p 平均しか返さないので、")
    print("       s と p を別々に返す口(または `polarization_render_fresnel`)が")
    print("       あれば、この PoC 全体が op の合成で書ける。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1. フレネル: ブリュースター角で R_p = 0、match3d と同じ式
    rs_b, rp_b = fresnel_sp(THETA_B)
    assert rp_b < 1e-30, f"ブリュースター角で R_p が 0 でない: {rp_b}"
    for th in (0.0, 20.0, 40.0, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        assert abs(0.5 * (rs + rp)
                   - match3d.fresnel_reflectance(math.cos(math.radians(th)),
                                                 1.0, ETA)) < 1e-12
    assert abs(fresnel_sp(0.0)[0] - fresnel_sp(0.0)[1]) < 1e-15, \
        "垂直入射で s と p が違う"

    # 2. 前方モデル: 部分偏光レンダ == op の完全偏光レンダ(等価な split)
    assert np.abs(frames - ref).max() < 1e-15, "前方モデルの組み替えが一致しない"

    # 3. ブリュースター角では分離が厳密(倍精度の床)
    assert rmse(d_op, d_true) < 1e-14, \
        f"ブリュースター角で拡散が厳密に出ない: {rmse(d_op, d_true):.3e}"
    assert rmse(s_op, s_true) < 1e-14, "ブリュースター角で鏡面が厳密に出ない"
    # 全輻度は分離で保存される(何も失わず何も作らない)
    assert np.abs((d_op + s_op) - (d_true + s_true)).max() < 1e-14
    # 雑音が無ければ 3 枚でも同じ答え(8-a の主張の裏取り)
    d3 = specularity.polarization_separate(frames[:3], ANGLES[:3])[0]
    assert np.abs(d3 - d_op).max() < 1e-14, "雑音なしで 3 枚と 4 枚の答えが違う"

    # 4. 誤差は閉形式 R_p * E に一致し、ゼロ点に勝つ
    for th, (dop, e, pred, e0n, rt) in ang_rows.items():
        assert abs(e - pred) < 1e-12 + 1e-6 * pred, \
            f"入射角 {th}: 誤差 {e:.3e} が閉形式 {pred:.3e} と違う"
        assert rt > 1.0, f"入射角 {th}: ゼロ点 1 に勝てていない (比 {rt:.2f})"
    assert ang_rows[THETA_B][1] < ang_rows[40.0][1] < ang_rows[20.0][1], \
        "ブリュースター角 → 40 度 → 20 度の順に悪くならない"
    assert ang_rows[THETA_B][1] < ang_rows[70.0][1], "ブリュースター角が最良でない"
    assert ang_rows[20.0][4] < 1.5, "20 度でゼロ点との差が小さいという所見が崩れた"
    # 評価軸で最適角が割れる(所見 2)。絶対誤差では 70 度が 20 度より悪く、
    # ゼロ点比では逆転する。この 2 行が同時に成り立つことが所見の中身そのもの。
    assert ang_rows[70.0][1] > ang_rows[20.0][1], \
        "絶対誤差で 70 度が 20 度より悪い、という所見が崩れた"
    assert ang_rows[70.0][4] > ang_rows[20.0][4], \
        "ゼロ点比で 70 度が 20 度より良い、という所見が崩れた"

    # 5. 入射角が既知なら偏りは消える
    for th, (e_raw, e_corr, amp) in corr_rows.items():
        assert e_corr <= e_raw + 1e-15, f"入射角 {th}: 補正で悪化した"
        assert e_corr < 1e-14, f"入射角 {th}: 補正後も偏りが残る ({e_corr:.3e})"

    # 6. 方位が格子に乗ると素朴なゼロ点が並ぶ / 外れると当てはめが効く
    for az in (0.0, 45.0):
        assert az_rows[az][1] < 1e-14, \
            f"方位 {az} 度で素朴法が引き分ける、という所見が崩れた"
        assert abs(az_rows[az][3] - az_rows[az][2]) < 1e-14, \
            f"方位 {az} 度は 70 度でも引き分けるはず"
    assert az_rows[22.5][1] > 1e3 * az_rows[22.5][0] + 1e-6, \
        "方位 22.5 度で当てはめが効く、という所見が崩れた"
    # op 自体は方位に依らない(当てはめが 3 未知数を厳密に解いているから)
    assert max(az_rows[a][2] for a in az_rows) - min(az_rows[a][2] for a in az_rows) < 1e-14

    # 7. 偏光度と Stokes が閉形式に一致
    assert np.abs(dolp - dolp_true).max() < 1e-12, "偏光度が閉形式と違う"
    assert abs(st[0] - s0_true) < 1e-12, "Stokes S0 が全輻度平均と違う"
    assert st[3] == 0.0, "直線検光子だけで S3 が出ている"

    # 8-(a) 雑音: 既定は fail-closed、σ が上がれば誤差も上がる(単調)
    assert noise_rows[0.0][0] == "通る", "雑音なしで拒否された"
    assert noise_rows[1e-1][0] == "拒否", "σ=0.1 でも拒否されない(fail-closed 破れ)"
    sig = (1e-4, 1e-3, 2e-3, 3e-3, 5e-3, 1e-2, 3e-2, 1e-1)
    errs = [noise_rows[s][2] for s in sig]
    assert all(b > a for a, b in zip(errs, errs[1:])), "雑音で誤差が単調に増えない"
    # 拒否の境界が実在する = どこかで「通る」→「拒否」に変わる
    verdicts = [noise_rows[s][0] for s in sig]
    assert "通る" in verdicts and "拒否" in verdicts, "雑音で境界が見えない"
    assert verdicts.index("拒否") > verdicts.index("通る"), "拒否が先に来ている"
    # 4 枚目は雑音のときだけ効く(3 枚でも未知数はちょうど決まる)
    assert noise_3v4[0] > 1.05 * noise_3v4[1], \
        f"雑音下で 4 枚目が効いていない: 3 枚 {noise_3v4[0]:.3e} / 4 枚 {noise_3v4[1]:.3e}"

    # 8-(b) 全体オフセットは無害(方位だけ δ 狂う)/ 1 枚ずれは有害だが小さい
    for delta, (e_all, az_err, e_one) in cal_rows.items():
        assert e_all < 1e-14, \
            f"全体オフセット {delta} 度で分離が壊れた: {e_all:.3e}"
        assert abs(az_err - delta) < 1e-6, \
            f"全体オフセット {delta} 度で方位誤差が δ に一致しない: {az_err:.4f}"
    assert cal_rows[1.0][2] > 1e6 * cal_rows[0.0][2], \
        "1 枚だけの角度誤差が全体オフセットと区別できない(想定外)"
    assert 1e-5 < cal_rows[1.0][2] < 1e-3, \
        f"1 枚 1 度ずれの誤差が想定の桁でない: {cal_rows[1.0][2]:.3e}"
    ones = [cal_rows[d][2] for d in (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0)]
    assert all(b > a for a, b in zip(ones, ones[1:])), \
        "1 枚ずれの誤差が δ で単調に増えない"
    assert cal_rows[20.0][2] < bias70, \
        "20 度ずれても 70 度の偏りに届かない、という所見が崩れた"

    # 8-(c) 飽和は例外なしで静かに悪化する(拡散側は最後まで飽和させない)
    assert (0.5 * diffuse).max() < 1.0, "拡散だけで飽和している(実験設計が壊れた)"
    assert sat_rows[1.0][0] == 0.0, "光源 1 倍で既に飽和している"
    assert sat_rows[8.0][0] > 0.02, "光源 8 倍でも飽和しない(シーンが暗すぎる)"
    assert all(v[1] == "無し" for v in sat_rows.values()), \
        "飽和で例外が出た(所見 c の前提が変わった)"
    assert sat_rows[8.0][2] > 1e3 * sat_rows[1.0][2], "飽和で悪化していない"
    assert sat_rows[8.0][2] > bias70, "飽和が 70 度の偏りにすら届かない"

    # 9. ゼロ点の妥当性(そもそもゼロ点が真値そのものになっていないこと)
    assert rmse(null_no_separation(frames), d_true) > 1e-3
    assert rmse(null_frame_min(frames), d_true) > 1e-2

    print(f"\n総所要 {time.perf_counter() - t_all:.1f} 秒")
    print("PASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
