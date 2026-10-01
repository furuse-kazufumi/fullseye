# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""判断の場面: ミラーと死角・確認の順序・信号の現示とジレンマゾーン・緊急自動車(光と音)・バスの発進。

## 何を作るか

自動運転 PoC 第 9 回「判断の場面」の部品を numpy だけで持つ。第 8 回までで「見える/見えない」「止まれる/止まれない」は
測れるようになった。ここでは **運転者が決める場面** —— どこを見て、いつ合図し、黄で止まるか抜けるか、サイレンが
どちらから来るか、誰に道を譲るか —— を、閉形式の真値と照らせる op にする:

1. ミラー(``mirror_virtual_camera`` / ``mirror_aim_normal`` / ``convex_mirror_fov`` / ``mirror_blind_zone``)。
   平面鏡は「鏡面で折り返した仮想カメラ」、凸面鏡は視野角の閉形式、左後方の死角は 2D の多角形。
2. 確認の順序の採点(``check_sequence_score``): ミラー確認 → 合図 → (約 3 秒 / 30 m)→ 進路変更 → 合図をやめる。
3. 信号(``signal_phase_plan`` / ``signal_state`` / ``predict_amber_onset`` / ``dilemma_zone``)。並行する歩行者信号の
   青点滅から車両の黄までの残り時間を読む。黄で「止まれず抜けられない」区間(ジレンマゾーン)。
4. 緊急自動車(``flash_frequency`` / ``aliased_frequency`` / ``siren_signal`` / ``doppler_shift`` / ``doppler_track`` /
   ``tdoa_bearing`` / ``yield_maneuver_check``)。赤色灯の点滅をカメラの画素の時系列で、サイレンを 2 本のマイクで。
5. バスの発進(``bus_departure_yield_check``)。

## 真値にする閉形式(門)

* 平面鏡: 鏡面 n·X = d(|n| = 1)での折り返し S(X) = (I − 2nnᵀ)X + 2dn。カメラ(world→camera の 4×4 ``P``)が鏡越しに
  見る像は、実物の場面を ``P·S`` で写したものに等しい。``P·S`` の回転は行列式 −1(左右が反転した「鏡の中の世界」)。
  カメラの x 軸を反転した ``F·P·S``(F = diag(−1, 1, 1, 1))は普通の右手系のカメラ = **仮想カメラ**(眼 S(C))で、その画像は
  鏡に映る像の **左右反転**(u' = 2c_x − u)。門は「入射角 = 反射角」を数値で解いた光線追跡(Fermat の最短経路)。
* 鏡の向き: 眼 E から鏡の中心 M への光線を方向 ℓ へ反射させる法線は n = normalize(unit(E − M) + unit(ℓ))(反射の法則)。
* 凸面鏡(半径 R、開口の直径 a、眼は軸上で頂点から D): 縁の半高 h = a/2、縁の法線の傾き α = asin(h/R)、
  縁の奥行き(サグ)s = R − sqrt(R² − h²)、眼から縁を見る角 β = atan(h/(D + s))。縁で反射した光線の軸からの角は
  β + 2α なので **全視野角 = 2(β + 2α)**(厳密)。近軸(h ≪ R, h ≪ D)では ≈ a(1/D + 2/R) = a(1/D + 1/f)、f = R/2。
  平面鏡(R = ∞)は 2 atan(h/D)。近軸の誤差は h³ の桁(門で 2 次でなく 3 次で縮むことを固定)。
* 死角: 鏡(円弧)の両端で反射した 2 本の光線の間 ∩ 鏡の前 = 鏡で見える領域(凸面鏡の反射光線は互いに交わらず
  広がるので、両端の光線で挟まれた所は中間の光線で埋まる)。直接の視界は眼から見た方位 ≤ ``direct_limit``。
  死角 = 対象領域 ∖ (鏡で見える ∪ 直接見える) を凸多角形の和(互いに素)で返す。門は格子の点ごとの光線追跡。
* ジレンマゾーン(Gazis, Herman, Maradudin 1960): 停止線までの距離 x、速度 v、反応 δ、減速 a、黄 τ、交差点の幅 w、
  車長 L。止まれる ⇔ x ≥ x_c = vδ + v²/(2a)。黄のうちに抜けられる(一定速度で後端が向こう側を出る)⇔
  x ≤ x_0 = vτ − (w + L)。x_0 < x < x_c が「止まれず抜けられない」。x_c < x_0 なら両方できる「選べる区間」。
  x_c = x_0 になる速度は v²/(2a) + v(δ − τ) + (w + L) = 0 の根。黄の間に加速する版(GHM の a₁)も ``accel`` で。
* 歩行者の青点滅の長さ F = 横断長 / 歩行速度(``walk_speed``)。予測は区間の積: 青の最後の観測 t_g と青点滅の最初の
  観測 t_f の間に点滅の始まりがあるので、黄 ∈ [t_g + F + Δ, t_f + F + Δ](Δ = 歩行者の赤から車両の黄までの時間)。
  赤の観測があれば同様に [t_f' + Δ, t_r + Δ]。区間の中点を推定、半幅を誤差の上限として返す。
* エイリアシング: 周波数 f をフレームレート fps で標本化した見かけの周波数 = |f − fps·round(f/fps)| ∈ [0, fps/2]。
* ドップラー(音源が動き、聞き手は静止): f_obs = f_src · c / (c − v_r)、v_r = 音源の **近づく向きの** 視線速度。
  合成は発音時刻 τ を「到着 t = τ + |p(τ) − m|/c」の 2 次方程式で厳密に解いて作る(ドップラーの式は使わない →
  推定の門は独立な経路)。``doppler_track`` は解析信号の位相差で瞬時周波数を出し v_r = c(1 − f_src/f_obs) に直す。
* 到着時間差: 2 本のマイク(間隔 d)の遠方近似 sin θ = cΔt/d。Δt は相互相関の最大(周波数領域で補間)。
* 緊急車両の回避(道交法 40 条)と、バスの発進(31 条の 2)は軌跡から二値で採点する。バスの「急に変更しなければ
  ならない」は、合図の時点で反応 ρ の後に一定減速でバスの後端の手前に止まるための減速 a_req = v²/(2(D − vρ))
  (D = 後端までの距離 − 余裕)が ``sudden_decel`` を超えるかで判定。門は ``rsssafety.rss_stopping_distance`` と
  刻みを進めるブレーキのシミュレーション(二分法)。

## 出典(書誌)と仮定

**法令・教則(一次で本文を確認したもの)**:

* 道路交通法(昭和35年法律第105号)第 40 条(緊急自動車の優先)・第 31 条の 2(乗合自動車の発進の保護)・
  第 53 条(合図。1 項「これらの行為が終わるまで当該合図を継続」、4 項「行為を終わつたときは当該合図をやめなければ
  ならない」)・第 26 条の 2。本文は e-Gov 法令 API v2(施行日 2025-06-01 版)の Wayback 捕捉
  (2026-02-04)から読んだ(2026-10-01 は e-Gov が保守中)。
* 交通の方法に関する教則(昭和53年国家公安委員会告示第3号、最終改正 令和6年国家公安委員会告示第37号、警察庁掲載
  20241113kyousoku.pdf)第 5 章第 5 節 1「安全の確認と合図」(52/148 頁): 「あらかじめバックミラーなどで安全を
  確かめてから合図」、左折・右折・転回は「30 メートル手前の地点に達したとき」、同一方向の進路変更は「進路を変えようと
  する時の約 3 秒前」。**「約 3 秒」「30 m」は教則の値**。法 53 条 3 項が時期を政令に委ねる(施行令 21 条)が、
  政令本文は **この巡では未確認**。歩行者用信号の青の点滅は「黄信号と同じ意味」(教則 第 2 章)。

**その他の数値**(``SOURCES`` に出典 / 仮定を 1 つずつ書く。一次で確認できなかったものは **仮定**):
``CHECK_DEDUCTIONS``(技能試験の減点)・``WALK_SPEED_SIGNAL``・``SIREN_*``・黄 3 s / 全赤 2 s の例・
``sudden_decel``・``near_margin``・``left_tol`` 等。

* GHM: D. Gazis, R. Herman, A. Maradudin, "The problem of the amber signal light in traffic flow",
  Operations Research 8(1), 112–132 (1960), doi:10.1287/opre.8.1.112。式 (4) x_c = v0 δ2 + v0²/(2a2)、
  式 (7) x0 = v0 τ − (w + L)(調査の部下 AI が本文 PDF で確認。δ2 = 止まる側の反応遅れ。加速する版の反応 δ1 は
  ここでは δ2 と同じ値と置いた = 仮定)。

## 単位と座標

m, s, m/s, m/s², Hz, rad。3D のカメラ姿勢は ``render3d.look_at`` と同じ world→camera の 4×4(−Z 前方、+X 右、+Y 上)。
2D の車の座標は x = 前、y = 左(日本の右ハンドル車では運転席が y < 0、左のドアミラーが y > 0)。
音は 2D の平面上(x, y)、マイクの配列は ``tdoa_bearing`` では「左マイクが +y、右マイクが −y」、方位 θ は前方からの角で
左が正(遠方近似、前後の区別はつかない)。

## 限界(self_reported)

* 鏡は理想の鏡面(厚み・歪み・汚れ・鏡のハウジングによる直接視界の遮りを持たない)。凸面鏡は球面。死角は 2D
  (目の高さ・窓枠の高さ・ピラーを持たない。直接の視界は方位の上限 1 つで、首を回す目視は含めない)。
* ジレンマゾーンは一定減速・一定速度(GHM の基本形)。路面の勾配・車両の加速の上限・運転者のばらつきは持たない。
* ``predict_amber_onset`` は「歩行者の赤から車両の黄まで Δ」の現示の構造を知っている前提(交差点ごとに違う。
  感応式・押しボタン式は扱わない)。点滅の「消えている」コマを青と見誤る画像側の問題は持たない(状態は分類済で受け取る)。
* ``flash_frequency`` は瞬間の標本化(露光時間による平均化 = sinc の減衰を持たない)。
* ``doppler_track`` は 2 音の公称周波数を知っている前提。近づく視線速度が 35.8 m/s を超えると低い音を高い音と取り違える
  (960/770 Hz のとき。docstring に式)。反射・風・雑音は持たない。
* ``tdoa_bearing`` は遠方近似で前後の区別なし。純音に近いと相関の山が 1/f ごとに並ぶので、d > c/(2 f_max) なら曖昧と返す。
* 40 条・31 条の 2 の採点は「寄る」「附近」「急に」の数値を法が定めていないので、閾値はすべて仮定の引数。
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

__all__ = [
    "SOURCES", "CHECK_DEDUCTIONS", "PASS_SCORE", "WALK_SPEED_SIGNAL", "SIREN_HIGH_HZ", "SIREN_LOW_HZ", "SIREN_PERIOD_S",
    "SPEED_OF_SOUND",
    "mirror_reflection_matrix", "mirror_virtual_camera", "mirror_aim_normal", "convex_mirror_fov",
    "mirror_blind_zone",
    "check_sequence_score",
    "signal_phase_plan", "signal_state", "predict_amber_onset", "dilemma_zone",
    "flash_frequency", "aliased_frequency", "siren_signal", "doppler_shift", "doppler_track", "tdoa_bearing",
    "yield_maneuver_check", "bus_departure_yield_check",
]

SPEED_OF_SOUND = 343.0          # 20 ℃ の空気中の音速 [m/s](物理定数の近似。気温で変わる)
WALK_SPEED_SIGNAL = 1.0         # 歩行者の青点滅の長さを決める歩行速度 [m/s](出典は SOURCES)
SIREN_HIGH_HZ = 960.0           # 救急車のサイレンの高い音 [Hz](出典は SOURCES)
SIREN_LOW_HZ = 770.0            # 低い音 [Hz]
SIREN_PERIOD_S = 1.3            # 高低 1 組の周期 [s](出典は SOURCES)

# 数値ごとの出典と確認の状態("primary" = 一次で本文を確認、"assumed" = 仮定)
SOURCES: Dict[str, Dict[str, str]] = {
    "signal_lead_lane_change_3s": {
        "status": "primary", "value": "約 3 秒前",
        "source": "交通の方法に関する教則 第5章第5節1 合図の表(警察庁 20241113kyousoku.pdf 52/148 頁)。"
                  "法 53 条 3 項 → 施行令 21 条は未確認"},
    "signal_distance_turn_30m": {
        "status": "primary", "value": "30 m 手前",
        "source": "同上(左折・右折・転回)"},
    "mirror_before_signal": {
        "status": "primary", "value": "順序",
        "source": "教則 第5章第5節1(1)「あらかじめバックミラーなどで安全を確かめてから合図」"},
    "signal_continue_until_done": {
        "status": "primary", "value": "継続・終了後にやめる",
        "source": "道路交通法 53 条 1 項・4 項(e-Gov 法令 API v2 の Wayback 捕捉 2026-02-04)"},
    "emergency_yield": {
        "status": "primary", "value": "交差点又はその附近: 交差点を避け左に寄って一時停止 / それ以外: 左に寄って進路を譲る",
        "source": "道路交通法 40 条 1 項・2 項(同上)"},
    "bus_departure": {
        "status": "primary", "value": "急に速度・方向を変えなければならない場合を除き、合図をしたバスの進路変更を妨げない",
        "source": "道路交通法 31 条の 2(同上)"},
    "ped_flash_means_amber": {
        "status": "primary", "value": "歩行者用信号の青の点滅は黄信号と同じ意味",
        "source": "教則 第2章(信号の意味)"},
    "dilemma_zone_formula": {
        "status": "literature", "value": "x_c = vδ + v²/(2a)、x_0 = vτ − (w + L)",
        "source": "Gazis, Herman, Maradudin, Operations Research 8(1) 112–132 (1960)"},
    "check_deductions": {
        "status": "primary", "value": "安全不確認 10 点 / 合図不履行等 5 点(合図をしない・時機が遅い又は著しく早い・"
                                       "継続しない・もどさない を含む)、合格 = 第一種 70 点以上",
        "source": "警察庁 丁運発第44号(令和5年3月30日)「運転免許技能試験に係る採点基準の運用の標準について」"
                  "npa.go.jp/laws/notification/koutuu/menkyo/menkyo20230330_44.pdf(PDF 6–7 頁を本文で確認)。"
                  "合格基準は丙運発第2号(令和8年2月4日)別添6 = 調査の部下 AI の抽出(本文は未照合)"},
    "walk_speed_signal": {
        "status": "primary", "value": "1.0 m/s",
        "source": "警視庁「横断歩道の青信号の時間を延長してほしい」(shingo_faq/crosswalk_extention.html)"
                  "「一般的には歩行速度を秒速1メートルとして道路を渡りきれるよう調整しています」。"
                  "警察庁の通達・指針の本文は未確認"},
    "flash_rule": {
        "status": "assumed", "value": "青点滅 F = 横断長 / 歩行速度(flash_fraction = 1)",
        "source": "仮定。学会論文(井料ほか、土木学会)には F = L/(2V)(横断の途中の人が渡りきる)の形があり、"
                  "flash_fraction = 0.5 で選べる。どちらが運用の基準かは一次未確認"},
    "amber_3s_all_red_2s": {
        "status": "semi-primary", "value": "黄 3 s(実務の設定値は 3 または 4 s)・全赤 2 s は例",
        "source": "交通工学研究会 ハンドブック(jste.or.jp/toptoe/hb/cp/p177.pdf)「黄時間の実務的な設定値としては"
                  "3秒または4秒」・全赤は最大 4 s(部下 AI の抽出、本文未照合)。全赤 2 s は仮定"},
    "ped_red_to_amber": {"status": "assumed", "value": "例 2 s", "source": "仮定(交差点ごとに違う)"},
    "siren_tones": {
        "status": "secondary", "value": "960 Hz / 770 Hz、各 0.65 s、1 組 1.3 s",
        "source": "消防防第337号(昭和45年6月10日)「救急自動車に備えるサイレンの音色の変更について」を引用する"
                  "東京消防庁の報告(tfd.metro.tokyo.lg.jp/content/safetyreport/000007152.pdf)。通知の原本は未確認。"
                  "音量は細目告示 75 条 二号「前方20mの位置において90dB以上120dB以下」(mlit.go.jp/jidosha/content/S075.pdf)"},
    "beacon_flash_rate": {
        "status": "primary", "value": "法令上の点滅回数の規定なし",
        "source": "細目告示 75 条 一号は「前方300mの距離から点灯を確認できる赤色」のみ(部下 AI の抽出、本文未照合)。"
                  "テストの点滅周波数は例(仮定)"},
    "lead_tolerance": {"status": "assumed", "value": "「約」3 秒の許容 ±0.5 s・30 m の許容 −3 m", "source": "仮定"},
    "near_margin_30m": {"status": "assumed", "value": "交差点の「附近」= 交差点の端から 30 m 以内", "source": "仮定(法に数値なし)"},
    "left_tol_1m": {"status": "assumed", "value": "「左に寄る」= 左端から 1.0 m 以内", "source": "仮定(法に数値なし)"},
    "sudden_decel_3": {"status": "assumed", "value": "「急に」= 3.0 m/s² を超える減速", "source": "仮定(法に数値なし)"},
}

# 技能試験の減点(採点の重み)。キー → (点数, SOURCES のキー)
CHECK_DEDUCTIONS: Dict[str, int] = {
    "safety_check_missing": 10,     # 安全不確認 10 点(丁運発第44号)
    "signal_missing": 5,            # 合図不履行等 5 点(合図をしない)
    "signal_timing": 5,             # 同(合図をした時機が遅い又は著しく早い)
    "signal_not_continued": 5,      # 同(継続しない。法 53 条 1 項)
    "signal_not_cancelled": 5,      # 同(もどさない。法 53 条 4 項)
}
PASS_SCORE = 70                     # 第一種免許の技能試験の合格(100 点から減点、70 点以上)

_SAFETY_KINDS = ("mirror", "head_check")
_EVENT_KINDS = ("mirror", "head_check", "signal_on", "signal_off", "start", "end")
_MANEUVERS = ("lane_change", "left_turn", "right_turn", "u_turn")


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _finite(v, name: str, op: str) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    if not math.isfinite(v):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    return v


def _positive(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if not v > 0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return v


def _nonneg(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if not v >= 0:
        raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    return v


def _array(v, name: str, op: str) -> np.ndarray:
    try:
        a = np.asarray(v, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric, got %r" % (op, name, v))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _vec(v, n: int, name: str, op: str) -> np.ndarray:
    a = _array(v, name, op)
    if a.shape != (n,):
        raise ValueError("%s: %s must be a %d-vector, got shape %r" % (op, name, n, a.shape))
    return a


def _unit(v, name: str, op: str) -> np.ndarray:
    nv = float(np.linalg.norm(v))
    if not nv > 1e-12:
        raise ValueError("%s: %s must be a non-zero vector" % (op, name))
    return v / nv


# ---- 1. ミラー --------------------------------------------------------------------------------------
def mirror_reflection_matrix(mirror_plane) -> np.ndarray:
    """平面 ``mirror_plane`` = (n_x, n_y, n_z, d)(点 X が鏡面上 ⇔ n·X = d、n は正規化する)での折り返しの 4×4 同次行列。

        S = [[I − 2nnᵀ, 2dn], [0, 1]]

    S·S = I(対合)、回転部の行列式 = −1(向きを反転)。"""
    op = "mirror_reflection_matrix"
    p = _vec(mirror_plane, 4, "mirror_plane", op)
    nn = float(np.linalg.norm(p[:3]))
    if not nn > 1e-12:
        raise ValueError("%s: mirror_plane normal must be non-zero" % op)
    n, d = p[:3] / nn, p[3] / nn
    S = np.eye(4)
    S[:3, :3] -= 2.0 * np.outer(n, n)
    S[:3, 3] = 2.0 * d * n
    return S


def mirror_virtual_camera(cam_pose, mirror_plane) -> Dict[str, object]:
    """平面鏡に映る像を撮る **仮想カメラ**。

    ``cam_pose`` は world→camera の 4×4(``render3d.look_at`` の規約: X_cam = P X、−Z 前方)。``mirror_plane`` は
    (n_x, n_y, n_z, d)(n·X = d)。

    返り値(dict):

    * ``reflection``: 折り返し S(``mirror_reflection_matrix``)。
    * ``pose_mirrored`` = P·S: 実物の場面をこれで写すと、実カメラが **鏡越しに見る像そのもの**(画素の位置まで同じ)。
      回転部の行列式は −1(左右が反転した座標系。描画器によっては面の表裏の判定が逆になる)。
    * ``pose`` = F·P·S、F = diag(−1, 1, 1, 1): 普通の右手系のカメラ(行列式 +1)= 鏡の向こうにいる仮想カメラ。
      これで撮った画像は鏡に映る像の **左右反転**(画素では u' = 2c_x − u)。バックミラーを「後ろ向きのカメラ」と
      して扱うときはこちら(運転者が見る像に戻すには左右を反転する)。
    * ``eye``: 仮想カメラの位置 S(C)(C = 実カメラの位置)。``eye_real``: C。
    * ``flip``: ``"x"``(``pose`` の画像は x を反転すると鏡像になる)。

    閉形式: S(X) = X − 2(n·X − d)n。鏡に映る点 Q の像の位置は S(Q)(鏡の向こう側、鏡面から同じ距離)。
    門(テスト): 入射角 = 反射角を満たす鏡面上の点 M を数値で解き(Fermat の最短経路)、C + (|CM| + |MQ|)·unit(M − C)
    が S(Q) と一致すること。"""
    op = "mirror_virtual_camera"
    P = _array(cam_pose, "cam_pose", op)
    if P.shape != (4, 4):
        raise ValueError("%s: cam_pose must be a 4x4 world->camera matrix, got shape %r" % (op, P.shape))
    if abs(float(np.linalg.det(P[:3, :3]))) < 1e-9:
        raise ValueError("%s: cam_pose rotation is degenerate" % op)
    S = mirror_reflection_matrix(mirror_plane)
    Pm = P @ S
    F = np.diag([-1.0, 1.0, 1.0, 1.0])
    Pv = F @ Pm
    C = -np.linalg.solve(P[:3, :3], P[:3, 3])          # 実カメラの中心(P[:3,:3] C + P[:3,3] = 0)
    eye = S[:3, :3] @ C + S[:3, 3]
    return {"reflection": S, "pose_mirrored": Pm, "pose": Pv, "eye": eye, "eye_real": C, "flip": "x"}


def mirror_aim_normal(eye, mirror_center, look_dir) -> np.ndarray:
    """眼 ``eye`` から鏡の中心 ``mirror_center`` へ来た光線を方向 ``look_dir`` へ反射させる鏡の法線(2D でも 3D でも)。

        n = normalize(unit(E − M) + unit(ℓ))

    (反射の法則: 入射の逆向きと反射の向きの二等分)。法線は眼の側を向く。``look_dir`` が眼の方向と正反対(鏡を真横から
    見る)だと定まらないので ValueError。"""
    op = "mirror_aim_normal"
    E = _array(eye, "eye", op)
    M = _array(mirror_center, "mirror_center", op)
    L = _array(look_dir, "look_dir", op)
    if E.ndim != 1 or E.shape != M.shape or E.shape != L.shape or E.shape[0] not in (2, 3):
        raise ValueError("%s: eye, mirror_center, look_dir must be same-length 2- or 3-vectors" % op)
    a = _unit(E - M, "eye - mirror_center", op)
    b = _unit(L, "look_dir", op)
    s = a + b
    if float(np.linalg.norm(s)) < 1e-9:
        raise ValueError("%s: look_dir points straight back at the eye's opposite side (grazing mirror)" % op)
    return s / float(np.linalg.norm(s))


def convex_mirror_fov(radius, aperture, eye_distance) -> Dict[str, float]:
    """凸面鏡(球面、半径 ``radius``、開口の直径 ``aperture``)を軸上 ``eye_distance``(頂点から)の眼で見たときの視野角。

    厳密(軸を含む断面): h = a/2、α = asin(h/R)、s = R − sqrt(R² − h²)、β = atan(h/(D + s))、
    **全視野角 = 2(β + 2α)**。``radius = inf`` は平面鏡 2 atan(h/D)。
    近軸: ≈ a (1/D + 2/R)(誤差は h³ の桁。h/R ≲ 0.2 かつ h/D ≲ 0.2 で相対誤差が数 % 以内が目安)。

    返り値: ``fov_rad`` / ``fov_deg``(厳密)、``fov_paraxial_rad``、``flat_fov_rad``(同じ開口の平面鏡)、
    ``widening``(= fov / flat_fov、凸面で何倍広く見えるか)、``edge_tilt_rad`` = α、``eye_angle_rad`` = β。
    h ≥ R(半球より大きい開口)は ValueError。"""
    op = "convex_mirror_fov"
    R = _finite(radius, "radius", op) if not (isinstance(radius, float) and math.isinf(radius) and radius > 0) \
        else math.inf
    if not R > 0:
        raise ValueError("%s: radius must be positive (convex) or inf (flat), got %r" % (op, radius))
    a = _positive(aperture, "aperture", op)
    D = _positive(eye_distance, "eye_distance", op)
    h = a / 2.0
    beta_flat = math.atan(h / D)
    if math.isinf(R):
        alpha, s, beta = 0.0, 0.0, beta_flat
        par = 2.0 * h / D
    else:
        if not h < R:
            raise ValueError("%s: aperture/2 = %r must be smaller than radius = %r" % (op, h, R))
        alpha = math.asin(h / R)
        s = R - math.sqrt(R * R - h * h)
        beta = math.atan(h / (D + s))
        par = a * (1.0 / D + 2.0 / R)
    fov = 2.0 * (beta + 2.0 * alpha)
    flat = 2.0 * beta_flat
    return {"fov_rad": fov, "fov_deg": math.degrees(fov), "fov_paraxial_rad": par, "flat_fov_rad": flat,
            "widening": fov / flat, "edge_tilt_rad": alpha, "eye_angle_rad": beta, "sag": s}


def _mirror_arc(center, normal, half_width, radius, n: int):
    """2D の鏡(円弧 or 線分)の点と法線を n 点。法線は眼の側を向く。"""
    t = np.array([-normal[1], normal[0]])
    if math.isinf(radius):
        u = np.linspace(-half_width, half_width, n)
        P = center[None, :] + u[:, None] * t[None, :]
        N = np.repeat(normal[None, :], n, axis=0)
    else:
        phim = math.asin(half_width / radius)
        phi = np.linspace(-phim, phim, n)
        N = np.cos(phi)[:, None] * normal[None, :] + np.sin(phi)[:, None] * t[None, :]
        O = center - radius * normal
        P = O[None, :] + radius * N
    return P, N


def _reflect(d, n):
    return d - 2.0 * np.sum(d * n, axis=-1, keepdims=True) * n


def _clip(poly: np.ndarray, a: np.ndarray, b: float) -> np.ndarray:
    """凸多角形を半平面 a·p ≤ b で切る(Sutherland–Hodgman の 1 辺)。"""
    if len(poly) == 0:
        return poly
    out = []
    f = poly @ a - b
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        if f[i] <= 0:
            out.append(poly[i])
        if f[i] * f[j] < 0:
            t = f[i] / (f[i] - f[j])
            out.append(poly[i] + t * (poly[j] - poly[i]))
    return np.array(out).reshape(-1, 2)


def _area(poly: np.ndarray) -> float:
    if len(poly) < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def mirror_blind_zone(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width, *, mirror_radius=math.inf,
                      direct_limit_deg: float = 100.0, roi=(-15.0, -2.0, 0.9, 4.4)) -> Dict[str, object]:
    """自車の左後方で、左のドアミラーにも直接の視界にも入らない領域(2D、上から見た図)。

    座標は車の x = 前・y = 左。``eye_xy`` = 運転者の眼、``mirror_center_xy`` = 鏡の中心、``mirror_normal_xy`` = 鏡の
    法線(眼の側を向く。``mirror_aim_normal`` で作れる)、``mirror_width`` = 鏡の幅(上から見た弦の長さ)、
    ``mirror_radius`` = 凸面の曲率半径(inf = 平面鏡)。``direct_limit_deg`` = 首を回さずに直接見える方位の上限
    (前方から左回り。100° は **仮定**)。``roi`` = (x_min, x_max, y_min, y_max) の対象領域(左の隣の車線。鏡の本体と
    車体を含まないように置くこと = 鏡の光線が車体を通るかは見ていない)。

    鏡で見える領域 = 鏡の両端で反射した 2 本の光線に挟まれ、かつ鏡の弦より眼の側。直接見える = 眼から見た方位 ≤ 上限。
    死角 = roi ∖ (鏡 ∪ 直接) を **互いに素な凸多角形の列** で返す(凸 ∖ 凸 = 半平面を 1 つずつ外した和)。

    返り値: ``pieces``(凸多角形 (k, 2) の list)、``area``、``mirror_edges``(両端の点 (2, 2))、
    ``mirror_rays``(両端の反射光線の単位ベクトル (2, 2))、``mirror_area`` / ``direct_area``(roi の中で見える面積)。"""
    op = "mirror_blind_zone"
    E = _vec(eye_xy, 2, "eye_xy", op)
    M = _vec(mirror_center_xy, 2, "mirror_center_xy", op)
    n0 = _unit(_vec(mirror_normal_xy, 2, "mirror_normal_xy", op), "mirror_normal_xy", op)
    w = _positive(mirror_width, "mirror_width", op) / 2.0
    R = math.inf if (isinstance(mirror_radius, float) and math.isinf(mirror_radius) and mirror_radius > 0) \
        else _positive(mirror_radius, "mirror_radius", op)
    if not math.isinf(R) and not w < R:
        raise ValueError("%s: mirror_width/2 must be smaller than mirror_radius" % op)
    lim = _finite(direct_limit_deg, "direct_limit_deg", op)
    if not 0.0 < lim < 180.0:
        raise ValueError("%s: direct_limit_deg must be in (0, 180), got %r" % (op, lim))
    r = _vec(roi, 4, "roi", op)
    x0, x1, y0, y1 = (float(v) for v in r)
    if not (x1 > x0 and y1 > y0):
        raise ValueError("%s: roi must be (x_min, x_max, y_min, y_max) with x_max > x_min, y_max > y_min" % op)
    if not y0 > E[1]:
        raise ValueError("%s: roi must lie left of the eye (y_min > eye y) for the direct-view half-plane" % op)
    if float(np.dot(E - M, n0)) <= 0:
        raise ValueError("%s: the mirror normal must face the eye" % op)

    P, N = _mirror_arc(M, n0, w, R, 2)                     # 両端
    d = P - E[None, :]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    rays = _reflect(d, N)
    box = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)

    # 直接見えない = cross(u_lim, T − E) > 0(方位 > 上限)→ a·T ≤ b の形に
    u = np.array([math.cos(math.radians(lim)), math.sin(math.radians(lim))])
    nd = np.array([u[1], -u[0]])                           # cross(u, T−E) = −nd·(T−E) ... 符号を合わせる
    # cross(u, v) = u_x v_y − u_y v_x = (−u_y, u_x)·v。> 0 を (u_y, −u_x)·v < 0 と書く
    not_direct = _clip(box, nd, float(nd @ E))
    direct = _clip(box, -nd, float(-nd @ E))

    # 鏡で見える = 半平面 3 つ(両端の光線で挟む + 弦の眼の側)
    chord_mid = P.mean(axis=0)
    T_in = chord_mid + (rays[0] + rays[1])               # 中の点(眼の側へ 1 m)
    hp = []
    for k in range(2):
        g = np.array([-rays[k, 1], rays[k, 0]])          # cross(r, T − P) = g·(T − P)
        s = 1.0 if float(g @ (T_in - P[k])) >= 0 else -1.0
        hp.append((-s * g, float(-s * g @ P[k])))         # s·g·(T−P) ≥ 0 ⇔ (−s g)·T ≤ (−s g)·P
    tch = P[1] - P[0]
    gc = np.array([-tch[1], tch[0]])
    s = 1.0 if float(gc @ (T_in - P[0])) >= 0 else -1.0
    hp.append((-s * gc, float(-s * gc @ P[0])))

    pieces: List[np.ndarray] = []
    acc = not_direct
    for a, b in hp:                                      # not_direct ∖ C = ∪_i (H_1..H_{i−1} ∩ ¬H_i)
        out = _clip(acc, -a, -b)
        if _area(out) > 1e-12:
            pieces.append(out)
        acc = _clip(acc, a, b)
    mirror_vis = _clip(_clip(_clip(box, *hp[0]), *hp[1]), *hp[2])
    return {"pieces": pieces, "area": float(sum(_area(p) for p in pieces)), "mirror_edges": P, "mirror_rays": rays,
            "mirror_area": _area(mirror_vis), "direct_area": _area(direct), "roi_area": _area(box)}


# ---- 2. 確認の順序 -----------------------------------------------------------------------------------
def check_sequence_score(events, *, maneuver: str = "lane_change", lead_time: float = 3.0, lead_tol: float = 0.5,
                         max_lead: Optional[float] = None, signal_distance: float = 30.0, distance_tol: float = 3.0,
                         cancel_tol: float = 2.0) -> Dict[str, object]:
    """進路変更・右左折の前の「安全確認 → 合図 → (約 3 秒 / 30 m)→ 行為 → 合図をやめる」を採点する。

    ``events``: ``{"t": 時刻, "kind": 種類, "s": 道のりの位置(任意)}`` の列。種類は
    ``mirror`` / ``head_check``(安全確認)、``signal_on`` / ``signal_off``(合図)、``start``(進路を変え始めた /
    右左折の地点に達した)、``end``(行為が終わった)。``start`` は必須(1 回)。

    規則(根拠は ``SOURCES``):

    1. 合図がある(``signal_missing``)。
    2. 合図より前(かつ start より前)に安全確認がある(``safety_check_missing``。教則「あらかじめバックミラーなどで
       安全を確かめてから合図」)。
    3. 合図の時期(``signal_timing``): 進路変更は start − 合図 ≥ ``lead_time − lead_tol``(教則「約 3 秒前」。許容は仮定)、
       ``max_lead`` を与えれば早すぎも減点。右左折・転回は start の位置 − 合図の位置 ≥ ``signal_distance − distance_tol``
       (教則「30 メートル手前」。``s`` が必要)。
    4. ``end`` より前に合図をやめていない(``signal_not_continued``、法 53 条 1 項)。
    5. ``end`` の後 ``cancel_tol`` 秒以内に合図をやめた(``signal_not_cancelled``、法 53 条 4 項。許容は仮定)。
       ``end`` が無ければ 4・5 は見ない。

    返り値: ``violations``(各 ``{"rule", "detail", "deduction"}``)、``deduction``、``score`` = 100 − deduction、
    ``ok``、``lead``(秒、進路変更)/ ``distance``(m、右左折)。"""
    op = "check_sequence_score"
    if maneuver not in _MANEUVERS:
        raise ValueError("%s: maneuver must be one of %r, got %r" % (op, _MANEUVERS, maneuver))
    lead_time = _positive(lead_time, "lead_time", op)
    lead_tol = _nonneg(lead_tol, "lead_tol", op)
    if max_lead is not None:
        max_lead = _positive(max_lead, "max_lead", op)
    signal_distance = _positive(signal_distance, "signal_distance", op)
    distance_tol = _nonneg(distance_tol, "distance_tol", op)
    cancel_tol = _nonneg(cancel_tol, "cancel_tol", op)
    ev = []
    for i, e in enumerate(events):
        if not isinstance(e, dict) or "t" not in e or "kind" not in e:
            raise ValueError("%s: events[%d] must be a dict with 't' and 'kind'" % (op, i))
        k = e["kind"]
        if k not in _EVENT_KINDS:
            raise ValueError("%s: events[%d].kind must be one of %r, got %r" % (op, i, _EVENT_KINDS, k))
        s = None if e.get("s") is None else _finite(e["s"], "events[%d].s" % i, op)
        ev.append((_finite(e["t"], "events[%d].t" % i, op), k, s))
    starts = [e for e in ev if e[1] == "start"]
    if len(starts) != 1:
        raise ValueError("%s: exactly one 'start' event is required, got %d" % (op, len(starts)))
    t_start, _, s_start = starts[0]
    ends = [e for e in ev if e[1] == "end"]
    t_end = min(e[0] for e in ends) if ends else None
    if t_end is not None and t_end < t_start:
        raise ValueError("%s: 'end' must not precede 'start'" % op)
    ons = sorted(e for e in ev if e[1] == "signal_on" and e[0] <= t_start)
    viol = []

    def add(rule, detail):
        viol.append({"rule": rule, "detail": detail, "deduction": CHECK_DEDUCTIONS[rule]})

    lead = dist = None
    if not ons:
        add("signal_missing", "start より前に合図が無い")
        t_sig = None
    else:
        t_sig, _, s_sig = ons[-1]                         # start 直前の(続いている)合図
        offs = [e[0] for e in ev if e[1] == "signal_off" and t_sig <= e[0] < t_start]
        if offs:                                         # 合図を出してから start までに消した = 続いていない
            t_sig = None
            add("signal_missing", "合図が start までに消えている(t = %.2f)" % min(offs))
    safety = [e[0] for e in ev if e[1] in _SAFETY_KINDS and e[0] <= t_start]
    if t_sig is None:
        if not safety:
            add("safety_check_missing", "start より前に安全確認が無い")
    else:
        if not any(t <= t_sig for t in safety):
            add("safety_check_missing", "合図より前に安全確認が無い(合図の後だけ・または無し)")
        if maneuver == "lane_change":
            lead = t_start - t_sig
            if lead < lead_time - lead_tol:
                add("signal_timing", "合図から進路変更まで %.2f s(約 %.1f s が要る)" % (lead, lead_time))
            elif max_lead is not None and lead > max_lead:
                add("signal_timing", "合図が早すぎる(%.2f s > %.2f s)" % (lead, max_lead))
        else:
            if s_start is None or s_sig is None:
                raise ValueError("%s: turns need 's' on the 'start' and 'signal_on' events" % op)
            dist = s_start - s_sig
            if dist < signal_distance - distance_tol:
                add("signal_timing", "合図の位置が %.1f m 手前(%.0f m 手前が要る)" % (dist, signal_distance))
        if t_end is not None:
            offs = sorted(e[0] for e in ev if e[1] == "signal_off" and e[0] >= t_start)
            if offs and offs[0] < t_end:
                add("signal_not_continued", "行為の途中(t = %.2f)で合図をやめた" % offs[0])
            elif not offs or offs[0] > t_end + cancel_tol:
                add("signal_not_cancelled", "行為の後も合図を出したまま")
    ded = int(sum(v["deduction"] for v in viol))
    return {"violations": viol, "deduction": ded, "score": 100 - ded, "ok": not viol,
            "passes_exam": 100 - ded >= PASS_SCORE, "lead": lead,
            "distance": dist, "maneuver": maneuver}


# ---- 3. 信号 ---------------------------------------------------------------------------------------
def signal_phase_plan(*, crossing_length: float, ped_green: float, walk_speed: float = WALK_SPEED_SIGNAL,
                      ped_red_to_amber: float = 2.0, amber: float = 3.0, all_red: float = 2.0,
                      cross_green: float = 20.0, cross_amber: Optional[float] = None,
                      cross_all_red: Optional[float] = None, flash_fraction: float = 1.0) -> Dict[str, object]:
    """2 現示の信号の時間割(主道路 A と、それに **並行する歩行者信号**、交差道路 B)。時刻 0 = A の青の始まり。

        歩行者 A: 青 [0, g) → 青点滅 [g, g + F) → 赤 [g + F, 周期)、F = flash_fraction · crossing_length / walk_speed
        車両 A:   青 [0, t_y) → 黄 [t_y, t_y + Y) → 赤、t_y = g + F + Δ(Δ = ``ped_red_to_amber``)
        全赤 [t_y + Y, t_y + Y + AR) → 車両 B: 青 G_B → 黄 → 全赤 → 周期の終わり

    返り値: ``intervals``(``{"veh_A", "ped_A", "veh_B"}`` → [(始, 終, 状態)])、``cycle``、``ped_flash_start`` = g、
    ``ped_flash_duration`` = F、``ped_red_onset``、``amber_onset`` = t_y、``red_onset``、``ped_red_to_amber`` = Δ。
    状態は ``"green" / "flash" / "amber" / "red"``。
    ``flash_fraction`` = 1 は「点滅の始めに渡り始めた人が渡りきる」、0.5 は学会論文の L/(2V)(SOURCES "flash_rule")。数値の既定(黄 3 s・全赤 2 s・Δ 2 s・歩行速度)は ``SOURCES`` を見る。"""
    op = "signal_phase_plan"
    L = _positive(crossing_length, "crossing_length", op)
    g = _positive(ped_green, "ped_green", op)
    vw = _positive(walk_speed, "walk_speed", op)
    dl = _nonneg(ped_red_to_amber, "ped_red_to_amber", op)
    Y = _positive(amber, "amber", op)
    AR = _nonneg(all_red, "all_red", op)
    GB = _positive(cross_green, "cross_green", op)
    YB = Y if cross_amber is None else _positive(cross_amber, "cross_amber", op)
    ARB = AR if cross_all_red is None else _nonneg(cross_all_red, "cross_all_red", op)
    ff = _positive(flash_fraction, "flash_fraction", op)
    if ff > 1.0:
        raise ValueError("%s: flash_fraction must be in (0, 1], got %r" % (op, ff))
    F = ff * L / vw
    t_pr = g + F
    t_y = t_pr + dl
    t_r = t_y + Y
    tb0 = t_r + AR
    tb1 = tb0 + GB
    tb2 = tb1 + YB
    cyc = tb2 + ARB
    iv = {
        "veh_A": [(0.0, t_y, "green"), (t_y, t_r, "amber"), (t_r, cyc, "red")],
        "ped_A": [(0.0, g, "green"), (g, t_pr, "flash"), (t_pr, cyc, "red")],
        "veh_B": [(0.0, tb0, "red"), (tb0, tb1, "green"), (tb1, tb2, "amber"), (tb2, cyc, "red")],
    }
    return {"intervals": iv, "cycle": cyc, "ped_flash_start": g, "ped_flash_duration": F, "ped_red_onset": t_pr,
            "amber_onset": t_y, "red_onset": t_r, "ped_red_to_amber": dl, "all_red": AR, "amber": Y}


def signal_state(plan: dict, signal: str, t) -> np.ndarray:
    """``signal_phase_plan`` の時間割で時刻 ``t``(周期で折り返す)の状態(文字列の配列)。区間は [始, 終)。"""
    op = "signal_state"
    if not isinstance(plan, dict) or "intervals" not in plan:
        raise ValueError("%s: plan must come from signal_phase_plan" % op)
    if signal not in plan["intervals"]:
        raise ValueError("%s: signal must be one of %r, got %r" % (op, tuple(plan["intervals"]), signal))
    tt = np.mod(_array(t, "t", op), plan["cycle"])
    out = np.empty(tt.shape, dtype=object)
    for a, b, s in plan["intervals"][signal]:
        out[(tt >= a) & (tt < b)] = s
    return out


def predict_amber_onset(observations, *, flash_duration: Optional[float] = None,
                        crossing_length: Optional[float] = None, walk_speed: float = WALK_SPEED_SIGNAL,
                        ped_red_to_amber: float = 2.0, t_now: Optional[float] = None) -> Dict[str, object]:
    """並行する歩行者信号の観測(時刻順の ``(t, state)``、state ∈ green / flash / red)から車両の黄の始まりを推定する。

    F = ``flash_duration``(無ければ ``crossing_length / walk_speed``)、Δ = ``ped_red_to_amber``。
    観測の切り替わり(green→flash、flash→red)ごとに黄の時刻が入る区間を作り、その **積** をとる:

        green→flash(最後の green t_g、最初の flash t_f): 黄 ∈ [t_g + F + Δ, t_f + F + Δ]
        flash→red  (最後の flash t_f'、最初の red t_r):   黄 ∈ [t_f' + Δ, t_r + Δ]

    返り値: ``amber_onset``(区間の中点)、``lo`` / ``hi``、``half_width``(誤差の上限)、``remaining``
    = amber_onset − t_now(既定 = 最後の観測時刻)、``basis``(使った切り替わり)。切り替わりが 1 つも無ければ
    ValueError(青が続いているだけでは「いつ点滅するか」は分からない)。区間が空(観測と F・Δ が矛盾)も ValueError。"""
    op = "predict_amber_onset"
    dl = _nonneg(ped_red_to_amber, "ped_red_to_amber", op)
    if flash_duration is not None:
        F = _positive(flash_duration, "flash_duration", op)
    elif crossing_length is not None:
        F = _positive(crossing_length, "crossing_length", op) / _positive(walk_speed, "walk_speed", op)
    else:
        F = None
    obs = []
    for i, o in enumerate(observations):
        try:
            t, s = o
        except (TypeError, ValueError):
            raise ValueError("%s: observations[%d] must be (t, state)" % (op, i))
        if s not in ("green", "flash", "red"):
            raise ValueError("%s: observations[%d] state must be green/flash/red, got %r" % (op, i, s))
        obs.append((_finite(t, "observations[%d].t" % i, op), s))
    if len(obs) < 2:
        raise ValueError("%s: need at least two observations" % op)
    ts = [o[0] for o in obs]
    if any(b <= a for a, b in zip(ts, ts[1:])):
        raise ValueError("%s: observation times must be strictly increasing" % op)
    lo, hi, basis = -math.inf, math.inf, []
    for (ta, sa), (tb, sb) in zip(obs, obs[1:]):
        if sa == sb:
            continue
        if (sa, sb) == ("green", "flash"):
            if F is None:
                continue
            lo, hi = max(lo, ta + F + dl), min(hi, tb + F + dl)
            basis.append("green->flash")
        elif (sa, sb) == ("flash", "red"):
            lo, hi = max(lo, ta + dl), min(hi, tb + dl)
            basis.append("flash->red")
        else:
            raise ValueError("%s: unexpected transition %s -> %s within one phase" % (op, sa, sb))
    if not basis:
        raise ValueError("%s: no usable green->flash or flash->red transition observed%s"
                         % (op, "" if F is not None else " (green->flash needs flash_duration or crossing_length)"))
    if lo > hi + 1e-12:
        raise ValueError("%s: observations are inconsistent with flash_duration/ped_red_to_amber (empty interval)" % op)
    est = 0.5 * (lo + hi)
    now = ts[-1] if t_now is None else _finite(t_now, "t_now", op)
    return {"amber_onset": est, "lo": lo, "hi": hi, "half_width": 0.5 * (hi - lo), "remaining": est - now,
            "basis": basis, "flash_duration": F}


def dilemma_zone(v, *, reaction: float, decel: float, amber: float, intersection_width: float, car_length: float,
                 accel: float = 0.0) -> Dict[str, object]:
    """黄信号のジレンマゾーン(Gazis, Herman, Maradudin 1960)。

    速度 ``v`` で停止線の手前 x にいるとき黄が点いた:

        止まれる     ⇔ x ≥ x_c = v δ + v²/(2a)                         (δ = reaction、a = decel)
        抜けられる   ⇔ x ≤ x_0 = v τ + ½ a₁ (τ − δ)² − (w + L)          (τ = amber、a₁ = accel ≥ 0、w = 交差点の幅、L = 車長)

    (a₁ = 0 が基本形。加速は反応の後から黄の終わりまで、と置いた形。τ ≤ δ なら加速項は 0。)
    max(x_0, 0) < x < x_c が **ジレンマゾーン**(止まれず抜けられない。x < 0 は停止線を越えているので除く)、
    x_c ≤ x ≤ x_0 が **選べる区間**(両方できる)。

    日本の法令の読み: 教則 付表1(黄)は「停止位置に近く安全に止まれない場合はそのまま進行可」= **停止線を越えれば
    よい**(交差点を黄のうちに抜ける義務ではない)。その読みでは ``intersection_width = car_length = 0`` として呼ぶ
    (x_0 = vτ)。GHM の「交差点を抜ける」は全赤の時間が無い前提の厳しい読み。

    返り値: ``x_stop_min`` = x_c、``x_clear_max`` = x_0、``dilemma``((lo, hi) か None)、``option``(同)、
    ``length``(ジレンマゾーンの長さ、無ければ 0)、``v_critical``(a₁ = 0 のとき x_c = x_0 になる速度の組。
    実根が無ければ空 = どの速度でもジレンマが無い)。``v`` は 1 つの数(配列は ``np.vectorize`` などで)。"""
    op = "dilemma_zone"
    v = _nonneg(v, "v", op)
    d = _nonneg(reaction, "reaction", op)
    a = _positive(decel, "decel", op)
    tau = _positive(amber, "amber", op)
    w = _nonneg(intersection_width, "intersection_width", op)
    L = _nonneg(car_length, "car_length", op)
    a1 = _nonneg(accel, "accel", op)
    xc = v * d + v * v / (2.0 * a)
    ta = max(0.0, tau - d)
    x0 = v * tau + 0.5 * a1 * ta * ta - (w + L)
    lo = max(x0, 0.0)                                   # x < 0 = もう停止線を越えている(区間から除く)
    dil = (lo, xc) if xc > lo else None
    opt = (xc, x0) if x0 >= xc else None
    # v²/(2a) + v(δ − τ) + (w + L) = 0
    A, B, Cq = 1.0 / (2.0 * a), d - tau, w + L
    disc = B * B - 4.0 * A * Cq
    vc = ()
    if disc >= 0:
        r = math.sqrt(disc)
        vc = tuple(sorted(x for x in ((-B - r) / (2 * A), (-B + r) / (2 * A)) if x >= 0))
    return {"x_stop_min": xc, "x_clear_max": x0, "dilemma": dil, "option": opt,
            "length": (xc - lo) if dil else 0.0, "v_critical": vc}


# ---- 4. 緊急自動車: 光 --------------------------------------------------------------------------------
def aliased_frequency(f, fps):
    """周波数 ``f`` [Hz] の明滅をフレームレート ``fps`` で標本化したときの **見かけの** 周波数(閉形式)。

        f_a = | f − fps · round(f / fps) |  ∈ [0, fps/2]

    f < fps/2 ならそのまま、fps の整数倍に近いほど遅く見える(車輪が止まって見える現象と同じ)。配列も可。"""
    op = "aliased_frequency"
    fa = _array(f, "f", op)
    fs = _positive(fps, "fps", op)
    if np.any(fa < 0):
        raise ValueError("%s: f must be non-negative" % op)
    out = np.abs(fa - fs * np.round(fa / fs))
    return float(out) if out.ndim == 0 else out


def flash_frequency(intensity_series, fps, *, f_min: float = 0.0, pad: int = 8) -> Dict[str, float]:
    """画素(または領域の平均)の明るさの時系列から点滅の周波数を推定する(FFT のいちばん高い山)。

    平均を引き、Hann 窓をかけ、``pad`` 倍に 0 を詰めて rFFT。``f_min`` 以上でいちばん高い山を対数振幅の放物線で
    補間する。返る周波数は **見かけの** 周波数(fps/2 を超える点滅は ``aliased_frequency`` の値に折り返って見える)。

    返り値: ``frequency``、``bin_width`` = fps / n(窓の分解能の目安)、``nyquist`` = fps/2、``peak_ratio``(山の高さ /
    山以外の中央値。点滅していない画素は小さい)。一定の系列(振れ幅 0)は ValueError。"""
    op = "flash_frequency"
    x = _array(intensity_series, "intensity_series", op)
    if x.ndim != 1 or x.size < 8:
        raise ValueError("%s: intensity_series must be 1-D with at least 8 samples" % op)
    fs = _positive(fps, "fps", op)
    f_min = _nonneg(f_min, "f_min", op)
    pad = int(pad)
    if pad < 1:
        raise ValueError("%s: pad must be >= 1" % op)
    x = x - x.mean()
    if float(np.ptp(x)) <= 1e-12 * max(1.0, float(np.max(np.abs(x)))):
        raise ValueError("%s: intensity_series is constant (no flashing)" % op)
    n = x.size
    nfft = 1 << int(math.ceil(math.log2(n * pad)))
    X = np.abs(np.fft.rfft(x * np.hanning(n), nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    ok = f >= max(f_min, fs / n)                         # 0 Hz の窓の裾を除く
    if not np.any(ok):
        raise ValueError("%s: f_min is above the Nyquist frequency" % op)
    idx = np.flatnonzero(ok)
    k = int(idx[np.argmax(X[idx])])
    fk = f[k]
    if 0 < k < len(X) - 1 and X[k - 1] > 0 and X[k + 1] > 0:
        a, b, c = np.log(X[k - 1]), np.log(X[k]), np.log(X[k + 1])
        den = a - 2 * b + c
        if den < 0:
            fk = f[k] + 0.5 * (a - c) / den * (f[1] - f[0])
    rest = np.median(X[idx]) if idx.size else 0.0
    return {"frequency": float(fk), "bin_width": fs / n, "nyquist": fs / 2.0,
            "peak_ratio": float(X[k] / rest) if rest > 0 else math.inf}


# ---- 4. 緊急自動車: 音 --------------------------------------------------------------------------------
def doppler_shift(f, v_source_radial, c: float = SPEED_OF_SOUND):
    """音源が動き聞き手が止まっているときの聞こえる周波数(閉形式)。

        f_obs = f · c / (c − v_r)

    ``v_source_radial`` = 音源の **聞き手へ近づく向きの** 視線速度(近づけば正 → 高く聞こえる)。|v_r| < c。配列も可。"""
    op = "doppler_shift"
    fa = _array(f, "f", op)
    vr = _array(v_source_radial, "v_source_radial", op)
    cc = _positive(c, "c", op)
    if np.any(np.abs(vr) >= cc):
        raise ValueError("%s: |v_source_radial| must be below the speed of sound" % op)
    out = fa * cc / (cc - vr)
    return float(out) if np.ndim(out) == 0 else out


def _siren_phase(tau, f_high, f_low, half):
    """二音を半周期ずつ交互に(高い音から)。位相は連続(∫ f dτ の閉形式)。"""
    per = 2.0 * half
    k = np.floor(tau / per)
    u = tau - k * per
    base = k * (f_high + f_low) * half
    return 2.0 * np.pi * np.where(u < half, base + f_high * u, base + f_high * half + f_low * (u - half))


def siren_signal(duration: float, fs: float, *, f_high: float = SIREN_HIGH_HZ, f_low: float = SIREN_LOW_HZ,
                 period: float = SIREN_PERIOD_S, source_start=(-60.0, 10.0), source_velocity=(15.0, 0.0),
                 mics=((0.0, 0.0),), c: float = SPEED_OF_SOUND, spreading: bool = True,
                 mic_velocity=(0.0, 0.0), mic_track=None) -> Dict[str, object]:
    """動く救急車のサイレン(二音の交互)を、止まっているマイクで聞いた音を合成する。

    音源 p(τ) = ``source_start`` + ``source_velocity``·τ(2D、等速直線)、発する音は sin φ(τ)、φ は高い音 f_high と
    低い音 f_low を ``period``/2 ずつ交互に鳴らす連続位相。マイク m が時刻 t に聞く音は、発音時刻 τ が

        c (t − τ) = |p(τ) − m|   ⇔   (c² − |u|²) s² + 2 (q·u) s − |q|² = 0,  s = t − τ ≥ 0,  q = p(t) − m

    を満たすときの sin φ(τ)(振幅は ``spreading`` なら r_ref / r、r_ref = 最初の距離)。**ドップラーの式は使っていない**
    (到着時刻の幾何だけ)ので、``doppler_track`` の門の独立な経路になる。

    ``mic_velocity`` = マイク(を載せた自車)の等速度(空気 = 地面に対して。風なし)。マイクは m(t) = m₀ + u_L t と動く。
    上の式は q = p(t) − m(t) と置けば同じ形のまま成り立つ(c(t − τ) = |p(τ) − m(t)|、p(τ) = p(t) − u s)。
    2 次方程式に入るのは **受信時のマイクの位置だけ**(音源は等速)なので、マイクは任意の道を動いてよい:
    ``mic_track`` = (位置 (k, n, 2), 速度 (k, n, 2))を標本ごとに与えると ``mics`` / ``mic_velocity`` の代わりに使う
    (減速して左に寄る自車に載せたマイク。速度は dτ/dt の閉形式にだけ使う)。

    返り値: ``t``(n,)、``signals``(マイク数, n)、``tau``(同)、``f_emit``(同、発した周波数)、``v_radial``(同、
    **近づく向きの距離の変化率** −d|p(τ) − m(t)|/dt を「音源の視線速度に換算した値」c(1 − 1/D)、D = dτ/dt。マイクが
    止まっていれば発音時の −ṙ と同じ)、``range_rate``(同、受信時の幾何の距離 |p(τ) − m(t)| の時間微分。負 = 近づく)、
    ``f_true``(同、= f_emit · dτ/dt。閉形式 dτ/dt = (c + r̂·u_L)/(c + r̂·u_S)、r̂ = (p(τ) − m(t))/r の単位ベクトル)。"""
    op = "siren_signal"
    T = _positive(duration, "duration", op)
    fs = _positive(fs, "fs", op)
    fh = _positive(f_high, "f_high", op)
    fl = _positive(f_low, "f_low", op)
    per = _positive(period, "period", op)
    cc = _positive(c, "c", op)
    if max(fh, fl) >= fs / 2:
        raise ValueError("%s: tones must be below fs/2" % op)
    p0 = _vec(source_start, 2, "source_start", op)
    u = _vec(source_velocity, 2, "source_velocity", op)
    uu = float(u @ u)
    if not uu < cc * cc:
        raise ValueError("%s: source speed must be below the speed of sound" % op)
    n = int(round(T * fs))
    if n < 2:
        raise ValueError("%s: duration * fs must give at least 2 samples" % op)
    t = np.arange(n) / fs
    if mic_track is None:
        m = _array(mics, "mics", op)
        if m.ndim != 2 or m.shape[1] != 2:
            raise ValueError("%s: mics must be shape (k, 2)" % op)
        uL = _vec(mic_velocity, 2, "mic_velocity", op)
        if not float(uL @ uL) < cc * cc:
            raise ValueError("%s: mic speed must be below the speed of sound" % op)
        tracks = [(mi[None, :] + t[:, None] * uL[None, :], np.broadcast_to(uL, (n, 2))) for mi in m]
    else:
        try:
            mp, mv = mic_track
        except (TypeError, ValueError):
            raise ValueError("%s: mic_track must be (positions, velocities)" % op)
        mp = _array(mp, "mic_track positions", op)
        mv = _array(mv, "mic_track velocities", op)
        if mp.ndim != 3 or mp.shape[1:] != (n, 2) or mv.shape != mp.shape:
            raise ValueError("%s: mic_track arrays must be shape (k, %d, 2) (n = round(duration * fs))" % (op, n))
        if np.any(np.sum(mv * mv, axis=-1) >= cc * cc):
            raise ValueError("%s: mic speed must be below the speed of sound" % op)
        tracks = list(zip(mp, mv))
    half = per / 2.0
    sig, taus, fe, vr, ft, rr = [], [], [], [], [], []
    for mt, uLt in tracks:
        q = p0[None, :] + t[:, None] * u[None, :] - mt
        qu = q @ u
        qq = np.sum(q * q, axis=1)
        A = cc * cc - uu
        s = (-qu + np.sqrt(qu * qu + A * qq)) / A
        tau = t - s
        rvec = p0[None, :] + tau[:, None] * u[None, :] - mt
        r = np.linalg.norm(rvec, axis=1)
        if np.any(r <= 0):
            raise ValueError("%s: the source passes through a microphone" % op)
        rh = rvec / r[:, None]
        dtau = (cc + np.sum(rh * uLt, axis=1)) / (cc + rh @ u)      # dτ/dt(閉形式、聞き手が動く一般のドップラー)
        amp = (r[0] / r) if spreading else np.ones_like(r)
        sig.append(amp * np.sin(_siren_phase(tau, fh, fl, half)))
        uh = np.mod(tau, per) < half
        f_e = np.where(uh, fh, fl)
        taus.append(tau)
        fe.append(f_e)
        vr.append(cc * (1.0 - 1.0 / dtau))
        rr.append(rh @ u * dtau - np.sum(rh * uLt, axis=1))          # d|p(τ) − m(t)|/dt
        ft.append(f_e * dtau)
    return {"t": t, "signals": np.array(sig), "tau": np.array(taus), "f_emit": np.array(fe),
            "v_radial": np.array(vr), "range_rate": np.array(rr), "f_true": np.array(ft), "fs": fs}


def _analytic(x: np.ndarray) -> np.ndarray:
    n = x.size
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    return np.fft.ifft(X * h)


def doppler_track(signal, fs, *, f_high: float = SIREN_HIGH_HZ, f_low: float = SIREN_LOW_HZ,
                  c: float = SPEED_OF_SOUND, smooth: float = 0.005, guard: float = 0.01, edge: float = 0.05,
                  v_tol: float = 1.0, verdict_window: float = 0.5) -> Dict[str, object]:
    """サイレンの音から瞬時周波数を推定し、近づいている / 遠ざかっているを判定する。

    1. 解析信号(FFT の Hilbert 変換)の位相差 → 瞬時周波数 f(t) = arg(z[n+1] z̄[n]) fs / 2π。
    2. 幅 ``smooth`` 秒の移動中央値。
    3. 各時刻で公称の 2 音(``f_high`` / ``f_low``)のうち比が近い方を「発した音」とみなし、ドップラー係数
       D = f / f_nom、視線速度 v_r = c (1 − 1/D)(``doppler_shift`` を v_r について解いたもの)。
    4. 音が切り替わる所(中央値の跳び > 20 Hz)の前後 ``guard`` 秒と、両端 ``edge`` 秒は無効(``valid`` = False)。
    5. 判定: 最後の ``verdict_window`` 秒の有効な v_r の中央値が +v_tol より大 → ``"approaching"``、−v_tol より小 →
       ``"receding"``、間 → ``"abeam"``。``state`` は各時刻の同じ判定(無効な所は ``"unknown"``)。

    公称音の取り違えの限界: 振り分けの境目は幾何平均 √(f_h f_l)。低い音が近づいて境目を越えるのは
    v_r = c (1 − √(f_l/f_h))、高い音が遠ざかって越えるのは v_r = −c (√(f_h/f_l) − 1)。960/770 Hz では
    +35.8 m/s(129 km/h)と −40.0 m/s。これより速い視線速度は取り違える(テストで固定)。
    """
    op = "doppler_track"
    x = _array(signal, "signal", op)
    if x.ndim != 1 or x.size < 64:
        raise ValueError("%s: signal must be 1-D with at least 64 samples" % op)
    fs = _positive(fs, "fs", op)
    fh = _positive(f_high, "f_high", op)
    fl = _positive(f_low, "f_low", op)
    if not fh > fl:
        raise ValueError("%s: f_high must exceed f_low" % op)
    cc = _positive(c, "c", op)
    sm = _positive(smooth, "smooth", op)
    gd = _nonneg(guard, "guard", op)
    ed = _nonneg(edge, "edge", op)
    vt = _nonneg(v_tol, "v_tol", op)
    vw = _positive(verdict_window, "verdict_window", op)
    z = _analytic(x - x.mean())
    f = np.angle(z[1:] * np.conj(z[:-1])) * fs / (2 * np.pi)
    w = max(1, int(round(sm * fs)) | 1)
    if w > 1 and f.size > w:
        pad = w // 2
        fp = np.pad(f, pad, mode="edge")
        f = np.median(np.lib.stride_tricks.sliding_window_view(fp, w), axis=1)
    tt = (np.arange(f.size) + 0.5) / fs
    gm = math.sqrt(fh * fl)
    fnom = np.where(f >= gm, fh, fl)
    D = f / fnom
    vr = cc * (1.0 - 1.0 / D)
    valid = (tt >= ed) & (tt <= tt[-1] - ed) & (f > 0)
    jumps = np.flatnonzero(np.abs(np.diff(f)) > 20.0)
    g = int(round(gd * fs))
    for j in jumps:
        valid[max(0, j - g):j + g + 2] = False
    state = np.full(f.size, "unknown", dtype=object)
    state[valid & (vr > vt)] = "approaching"
    state[valid & (vr < -vt)] = "receding"
    state[valid & (np.abs(vr) <= vt)] = "abeam"
    last = valid & (tt >= tt[-1] - ed - vw)
    if not np.any(last):
        verdict, vmed = "unknown", math.nan
    else:
        vmed = float(np.median(vr[last]))
        verdict = "approaching" if vmed > vt else ("receding" if vmed < -vt else "abeam")
    return {"t": tt, "f_inst": f, "f_nominal": fnom, "doppler_factor": D, "v_radial": vr, "valid": valid,
            "state": state, "verdict": verdict, "v_radial_last": vmed}


def tdoa_bearing(sig_left, sig_right, fs, mic_spacing, *, c: float = SPEED_OF_SOUND, upsample: int = 16) -> Dict[str, object]:
    """2 本のマイク(左 = +y、右 = −y、間隔 ``mic_spacing``)の到着時間差から音源の方位(遠方近似)。

        Δt = t_右 − t_左(左に先に着けば正)、 sin θ = c Δt / d、θ = 前方からの角(左が正)

    Δt は相互相関 Σ right[n] left[n − k] の最大(周波数領域で 0 を詰めて ``upsample`` 倍に補間し、さらに放物線)。
    探す範囲は物理的にありうる |Δt| ≤ d/c に限る。前後(θ と π − θ)は区別できない。

    返り値: ``delay``(秒)、``bearing_rad`` / ``bearing_deg``、``sin_theta``(クリップ前)、``ambiguous``
    (主な周波数 f_peak で d > c/(2 f_peak) なら True = 相関の山が 1/f ごとに並び範囲内に 2 つ入りうる)、``f_peak``。"""
    op = "tdoa_bearing"
    a = _array(sig_left, "sig_left", op)
    b = _array(sig_right, "sig_right", op)
    if a.ndim != 1 or a.shape != b.shape or a.size < 16:
        raise ValueError("%s: sig_left and sig_right must be 1-D of the same length (>= 16)" % op)
    fs = _positive(fs, "fs", op)
    d = _positive(mic_spacing, "mic_spacing", op)
    cc = _positive(c, "c", op)
    up = int(upsample)
    if up < 1:
        raise ValueError("%s: upsample must be >= 1" % op)
    a = a - a.mean()
    b = b - b.mean()
    n = a.size
    nfft = 1 << int(math.ceil(math.log2(2 * n)))
    A = np.fft.rfft(a, nfft)
    B = np.fft.rfft(b, nfft)
    G = B * np.conj(A)
    cc_up = np.fft.irfft(G, nfft * up)
    kmax = int(math.ceil(d / cc * fs * up)) + 1
    lags = np.arange(-kmax, kmax + 1)
    vals = cc_up[lags % (nfft * up)]
    i = int(np.argmax(vals))
    k = float(lags[i])
    if 0 < i < len(vals) - 1:
        y0, y1, y2 = vals[i - 1], vals[i], vals[i + 1]
        den = y0 - 2 * y1 + y2
        if den < 0:
            k += 0.5 * (y0 - y2) / den
    delay = k / (fs * up)
    st = cc * delay / d
    th = math.asin(max(-1.0, min(1.0, st)))
    P = np.abs(A) ** 2 + np.abs(B) ** 2
    fpk = float(np.fft.rfftfreq(nfft, 1.0 / fs)[int(np.argmax(P[1:])) + 1])
    return {"delay": delay, "sin_theta": st, "bearing_rad": th, "bearing_deg": math.degrees(th),
            "ambiguous": bool(d > cc / (2.0 * fpk)), "f_peak": fpk}


# ---- 4. 緊急自動車: 譲り方の採点(道交法 40 条) ----------------------------------------------------------
def _traj(traj, keys, op):
    if not isinstance(traj, dict):
        raise ValueError("%s: trajectory must be a dict of arrays %r" % (op, keys))
    out = {}
    n = None
    for k in keys:
        if k not in traj:
            raise ValueError("%s: trajectory needs key %r" % (op, k))
        a = _array(traj[k], "trajectory[%r]" % k, op)
        if a.ndim != 1:
            raise ValueError("%s: trajectory[%r] must be 1-D" % (op, k))
        if n is None:
            n = a.size
        elif a.size != n:
            raise ValueError("%s: trajectory arrays must have the same length" % op)
        out[k] = a
    if n < 2 or np.any(np.diff(out["t"]) <= 0):
        raise ValueError("%s: trajectory['t'] must be strictly increasing with >= 2 samples" % op)
    return out


def yield_maneuver_check(trajectory, *, t_approach: float, t_passed: float, intersections=(),
                         near_margin: float = 30.0, left_tol: float = 1.0, stop_speed: float = 0.1,
                         car_length: float = 4.5) -> Dict[str, object]:
    """緊急自動車が近づいたときの自車の動きを道路交通法 40 条で採点する。

    40 条 1 項: 交差点又はその附近 → 交差点を避け、道路の左側に寄って **一時停止**。
    40 条 2 項: それ以外 → 道路の左側に寄って進路を譲る(停止までは求めない)。
    (一方通行で左に寄ると妨げる場合の右寄せは扱わない。)

    ``trajectory``: ``{"t", "x", "y", "v"}``。x = 道に沿った前端の位置、y = 車の左側面と道路の左端の距離(≥ 0)、
    v = 速さ。``intersections`` = [(x_in, x_out), ...](交差点の範囲)。車は [x − car_length, x] を占める。
    ``t_approach`` = 近づきに気づくべき時刻、``t_passed`` = 緊急自動車が通り過ぎた時刻。

    判定(閾値はすべて **仮定**、法は数値を定めていない):
    * 「附近」= t_approach の自車の前端が [x_in − near_margin, x_out + near_margin] に入る交差点がある。
    * 「左に寄る」= 期間中に y ≤ ``left_tol``。「一時停止」= 期間中に v ≤ ``stop_speed`` の刻みがある。
    * 「交差点を避け」= 期間中に止まっている刻み(v ≤ stop_speed)で車体が交差点の範囲に重ならない。

    返り値: ``case``(``"40-1"`` / ``"40-2"``)、``violations``(各 ``{"rule", "detail", "article"}``)、``ok``、
    ``min_y``、``stopped``、``stopped_in_intersection``。"""
    op = "yield_maneuver_check"
    tr = _traj(trajectory, ("t", "x", "y", "v"), op)
    t0 = _finite(t_approach, "t_approach", op)
    t1 = _finite(t_passed, "t_passed", op)
    if not t1 > t0:
        raise ValueError("%s: t_passed must be after t_approach" % op)
    nm = _nonneg(near_margin, "near_margin", op)
    lt = _nonneg(left_tol, "left_tol", op)
    vs = _nonneg(stop_speed, "stop_speed", op)
    cl = _nonneg(car_length, "car_length", op)
    boxes = []
    for i, iv in enumerate(intersections):
        a = _vec(iv, 2, "intersections[%d]" % i, op)
        if not a[1] > a[0]:
            raise ValueError("%s: intersections[%d] must be (x_in, x_out) with x_out > x_in" % (op, i))
        boxes.append((float(a[0]), float(a[1])))
    t, x, y, v = tr["t"], tr["x"], tr["y"], tr["v"]
    if np.any(v < 0) or np.any(y < 0):
        raise ValueError("%s: v and y must be non-negative" % op)
    if not (t[0] <= t0 <= t[-1]):
        raise ValueError("%s: t_approach must lie within the trajectory" % op)
    x_at = float(np.interp(t0, t, x))
    near = any(a - nm <= x_at <= b + nm for a, b in boxes)
    W = (t >= t0) & (t <= t1)
    if not np.any(W):
        raise ValueError("%s: no trajectory samples between t_approach and t_passed" % op)
    stop = W & (v <= vs)
    inbox = np.zeros_like(W)
    for a, b in boxes:
        inbox |= (x > a) & (x - cl < b)
    stopped_in = bool(np.any(stop & inbox))
    left = W & (y <= lt)
    min_y = float(np.min(y[W]))
    viol = []
    case = "40-1" if near else "40-2"
    art = "道路交通法 40 条 %s 項" % ("1" if near else "2")
    if stopped_in:
        viol.append({"rule": "stopped_in_intersection", "detail": "交差点の中で止まった(交差点を避けていない)",
                     "article": "道路交通法 40 条 1 項"})
    if not np.any(left):
        viol.append({"rule": "not_left", "detail": "左に寄っていない(最小 y = %.2f m > %.2f m)" % (min_y, lt),
                     "article": art})
    if near and not np.any(stop & ~inbox & (y <= lt)):
        viol.append({"rule": "no_stop", "detail": "交差点の外で左に寄って一時停止していない", "article": art})
    return {"case": case, "violations": viol, "ok": not viol, "min_y": min_y, "stopped": bool(np.any(stop)),
            "stopped_in_intersection": stopped_in, "x_at_approach": x_at}


# ---- 5. バスの発進(道交法 31 条の 2) ------------------------------------------------------------------
def bus_departure_yield_check(trajectory, *, t_signal: float, bus_rear_x: float, merge_time: float = 4.0,
                              reaction: float = 1.0, sudden_decel: float = 3.0, standoff: float = 2.0) -> Dict[str, object]:
    """停留所から発進の合図をしたバスの進路変更を、後ろの自車が妨げたかを採点する(道路交通法 31 条の 2)。

    ``trajectory``: ``{"t", "x", "v"}``(自車の前端の位置、バスが入ってくる車線)。バスの後端は ``bus_rear_x``
    (合図から ``merge_time`` 秒は止まっている / ゆっくり出る間とみなす)。

    * 譲る義務: 合図の時刻 t_s の自車の (x_s, v_s) から、反応 ρ の後に一定減速でバスの後端の ``standoff`` 手前に
      止まる減速 a_req = v²/(2(D − vρ))、D = bus_rear_x − standoff − x_s(D ≤ vρ なら ∞)。
      a_req ≤ ``sudden_decel`` なら **急に速度を変えずに譲れる** → 譲る義務あり(``must_yield``)。
    * 妨げた: [t_s, t_s + merge_time] のどこかで自車の前端がバスの後端を越えた(横に並んだ / 追い抜いた)。
    * 違反 = 譲る義務あり かつ 妨げた。

    「急に」の閾値 3.0 m/s²・反応 1.0 s・余裕 2 m・合流の時間 4 s は **仮定**(法に数値なし)。
    返り値: ``a_required``、``must_yield``、``obstructed``、``violation``、``article``、``detail``。"""
    op = "bus_departure_yield_check"
    tr = _traj(trajectory, ("t", "x", "v"), op)
    ts = _finite(t_signal, "t_signal", op)
    xb = _finite(bus_rear_x, "bus_rear_x", op)
    mt = _positive(merge_time, "merge_time", op)
    rho = _nonneg(reaction, "reaction", op)
    ad = _positive(sudden_decel, "sudden_decel", op)
    so = _nonneg(standoff, "standoff", op)
    t, x, v = tr["t"], tr["x"], tr["v"]
    if np.any(v < 0):
        raise ValueError("%s: v must be non-negative" % op)
    if not (t[0] <= ts <= t[-1]):
        raise ValueError("%s: t_signal must lie within the trajectory" % op)
    xs = float(np.interp(ts, t, x))
    vs = float(np.interp(ts, t, v))
    D = xb - so - xs
    if xs >= xb:
        a_req, already = math.inf, True                  # 合図の時にもう並んでいる = 妨げようがない(後方ではない)
    else:
        already = False
        free = D - vs * rho
        a_req = 0.0 if vs == 0 and D >= 0 else (vs * vs / (2.0 * free) if free > 0 else math.inf)
    must = (not already) and a_req <= ad
    W = (t >= ts) & (t <= ts + mt)
    obstructed = (not already) and bool(np.any(x[W] > xb))
    viol = must and obstructed
    if already:
        det = "合図の時点で自車はバスの後端より前(後方の車両ではない)"
    elif not must:
        det = "譲るには %.2f m/s² の減速が要る(> %.1f = 急に)→ 義務なし" % (a_req, ad)
    else:
        det = "%.2f m/s² で譲れた(≤ %.1f)のに%s" % (a_req, ad, "前へ出た" if obstructed else "→ 譲った")
    return {"a_required": a_req, "must_yield": must, "obstructed": obstructed, "violation": viol,
            "article": "道路交通法 31 条の 2", "detail": det, "x_at_signal": xs, "v_at_signal": vs}
