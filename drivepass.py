# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""追越し・進路変更・環状交差点・坂の頂上・カーブミラー: 追越しに要る時間と距離、戻る位置(ルームミラー)、追越し禁止の
場所と場合、追い越される側の義務、後続車に要る減速度、環状交差点の優先と出口の合図、凸形縦断曲線の視距、凸面鏡の見誤り。

## 何を作るか

自動運転 PoC 第 12 回「追越しと見えない所」の部品を numpy だけで持つ。第 11 回(踏切と交差点の優先)に続き、
ここでは **前へ出てよいか・どこに戻るか・見えていない物をどう見積もるか** を条文と閉形式の判定にする。部品は
**学習を使わない** 閉形式・幾何・条文の判定・古典的な数値計算で、どれも独立な経路の検算(門)が立つものだけを置いた:

1. 追越し(``overtake_requirement`` / ``overtake_return_gap`` / ``no_overtaking_zones`` / ``overtake_permitted`` /
   ``overtaken_conduct_check``)—— 道交法 27〜30 条、教則 5-6-3 の手順(場面 S077〜S086・S145)。
2. 進路変更(``lane_change_follower_decel`` / ``lane_change_permitted``)—— 26 条の 2、53 条(S067・S072・S073)。
3. 環状交差点(``roundabout_entry_check`` / ``roundabout_signal_point`` / ``roundabout_signal_check``)——
   35 条の 2、37 条の 2、53 条 2 項(S069・S102)。
4. 坂(``crest_sight_distance`` / ``crest_safe_speed`` / ``hill_meeting_yield``)—— 42 条 2 号、30 条 1 号、
   道路構造令 2 条 24 号の視距(S065・S081・S128)。
5. カーブミラー(``convex_mirror_image`` / ``convex_mirror_misjudge`` / ``mirror_image_side`` /
   ``mirror_road_coverage``)—— 凸面鏡の結像と見誤り、像の左右、道の上で映る範囲(S064・S130)。

## 真値にする閉形式(門)

* 追越しの時間(``overtake_requirement``): 前車に対して進む距離 D = 後ろの余裕 + 前車の長さ + 自車の長さ + 前の余裕。
  自車は初速 v₀ から加速度 a で上限 v_max まで、前車は v_L で一定。相対速度 w = v₀ − v_L。加速の間に D に届けば
  t = 2D / (w + √(w² + 2aD))(a = 0 なら D/w。打ち消し合いを避けた形)、届かなければ t = t_a + (D − r_a)/(v_max − v_L)
  (t_a = (v_max − v₀)/a、r_a = w t_a + a t_a²/2)。戻りの時間 T_lc を足した占有時間 T = t + T_lc の間に自車が進む距離
  s(T) と、対向車が来ない境目 D* = s(T) + v_on (T + PET)。a = 0 で ``drivetraffic.passing_gap_required`` と一致(第 2 実装)。
* ルームミラーで前車の全体が見える距離(``overtake_return_gap``): 平面鏡は眼 E を鏡の直線で折り返した仮想の眼 E' から
  見るのと同じ。点 P が映る ⇔ 線分 E'P が鏡の線分と交わる。P を道に平行な直線(横位置 y)の上で後ろへ動かすと、交点の
  鏡の上の位置は一次分数関数で単調に動くので、鏡の端に届く位置は 1 次方程式の根。前車の前の 2 隅が両方とも映る位置
  (横位置ごとの境目は y の 1 次式なので、前の辺の両端で決まる)= 戻ってよい車間。
* 追越しの禁止の区間(``no_overtaking_zones``): 30 条 3 号の「手前の側端から前に 30 m」= [手前の端 − 30, 向こうの端]。
* 後続車に要る減速度(``lane_change_follower_decel``): 車間 g(後続車の前端と自車の後端)、後続車 v_f、自車 v_e
  (加速度 a_e ≥ 0)、反応 τ、残す車間 s₀。w₀ = v_f − v_e。反応の間に詰まる量 w₀τ − a_eτ²/2(w が 0 に届けば w₀²/(2a_e))、
  反応の後の相対速度 w₁ = w₀ − a_eτ、残り g₁ = g − s₀ − (詰まる量)。要る減速度 b = max(0, w₁²/(2g₁) − a_e)。
  b が「急な」減速度(**仮定** 2.0 m/s²)を超えると 26 条の 2 第 2 項の「急に変更させることとなるおそれ」。
* 環状交差点(右回り): 環道の車が角 θ_c から入口の角 θ_e まで進む弧 = R·((θ_c − θ_e) mod 2π)、着く時刻 = 弧 / v。
  入る車が衝突の点を抜けるまでに環道の車に要る減速度は ``drivecrossing.obstruction_decel``(2 条 22 号)。
* 出口の合図(教則 5-5-1(2)): 出口の 1 つ手前の出口の側方を通過したとき(入った直後の出口なら入ったとき)。
  右回りに進んだ角で、目的の出口より手前にある出口の角の最大値。
* 凸形縦断曲線の視距(放物線、半径 R = L/A、A = 勾配の差): 視距 S ≤ L なら S = √(2R)(√h₁ + √h₂)、S > L なら
  S = L/2 + (√h₁ + √h₂)²/A。h₁ = 1.2 m・h₂ = 0.1 m(道路構造令 2 条 24 号)で、構造令の表の 凸形 6,500 m → 視距 160 m、
  11,000 m → 210 m、100 m → 20 m が再現する(公表値の門)。水平に投影した長さ(勾配が小さい道で中心線の長さと同じ)。
* 視距の中で止まれる速さ(``crest_safe_speed``): v ρ + v²/(2A) = S を解いた v = 2S/(ρ + √(ρ² + 2S/A))、
  A = b + g sin θ + c_rr g cos θ(``drivelong.stopping_distance_grade`` の k = 0 の逆関数)。
* 凸面鏡(近軸、半径 R、焦点 R/2): 1/a + 1/b = 2/R の虚像(鏡の向こう)b = aR/(2a + R)、倍率 m = R/(2a + R)。
  眼が鏡から e のとき、像の見かけの大きさ θ = h m/(e + b) = h/(e + k a)、**k = 1 + 2e/R**。
  平面鏡のつもりで大きさから距離を読むと â = k a(**k 倍遠く**見える)。速さの読み方で結果が分かれる:
  - 大きさの読みと矛盾なく(â の変化から)読むと v̂ = k v(速く見える)、到達までの時間は (e + k a)/(k v) ≈ a/v。
  - 本当の距離に錨を置いて(平面鏡なら a にある物の大きさの変化として)読むと v̂ = k v (e + a)²/(e + k a)²、
    a > e/√k で v̂ < v(**遅く見える**)。
  - 横切る動き(像の角の速さ)を本当の距離に錨を置いて読むと v̂ = v (e + a)/(e + k a) < v(遅く見える)。
  「遠く・遅く見える」は錨の置き方による —— 門は 2 次元の光線追跡(反射点を二分法)で 3 つとも確かめる。
* 鏡の像の左右(``mirror_image_side``): 平面鏡の折り返し S(X) = X − 2((X − M)·n)n は向きを反転する(行列式 −1)ので、
  像を眼から見た角の速さは、物を **仮想の眼 E'** から見た角の速さの符号を反転したものに等しい。
* 道の上で鏡に映る範囲(``mirror_road_coverage``): 凸面鏡(円弧)の両端の法線で反射した 2 本の光線と道の直線の交点の間
  (凸面では反射光線の向きが鏡の上の位置に単調なので、間の光線が交点の間を埋める)。手前の端より交差点寄りは映らない。

## 条文の判定(一次: 道路交通法、e-Gov 法令 API の Wayback 保存版 2025-06-01 施行)

* 2 条 1 項 21 号: 追越し = 追い付いた車両等の側方を進路を変えて通過し、その前方に出ること。
* 26 条の 2 第 2 項: 変更後の進路を後方から来る車両等の速度又は方向を急に変更させることとなるおそれがあるときは
  進路を変更しない。第 3 項: 進路の変更の禁止を表示する道路標示を越えて変更しない(40 条の譲り・道路の障害の場合を除く)。
* 27 条 1 項: 最高速度が高い車両に追いつかれたら、追越しが終わるまで速度を増さない(同じか低い車両に追いつかれ、
  その速度より遅く進み続けるときも同じ)。乗合自動車・トロリーバスを除く。2 項: 車両通行帯の無い道路で十分な余地が
  無ければ、できる限り左側端に寄って進路を譲る。
* 28 条 1 項: 前車の右側を通行。2 項: 前車が 25 条 2 項・34 条 2・4 項で中央・右側端に寄っているときは左側。
  4 項: 反対方向・後方・前方の交通に十分に注意し、できる限り安全な速度と方法で進行。
* 29 条: 前車が他の自動車又はトロリーバスを追い越そうとしているときは追越しを始めない。
* 30 条: 標識等で禁止された部分と、1 号 曲がり角付近・上り坂の頂上付近・勾配の急な下り坂、2 号 トンネル(車両通行帯の
  設けられた道路を除く)、3 号 交差点(優先道路を通行している場合のその交差点を除く)・踏切・横断歩道・自転車横断帯と
  それらの手前の側端から前に 30 m 以内で、他の車両(特定小型原動機付自転車等を除く)を追い越すため進路を変更し、
  又は前車の側方を通過しない。
* 35 条の 2: 環状交差点で左折・右折・直進・転回するときは、あらかじめできる限り左側端に寄り、側端に沿って徐行。
* 37 条の 2 第 1 項: 環状交差点内を通行する車両等の進行妨害をしない(36 条 1・2 項・37 条にかかわらず)。2 項: 入るときは徐行。
* 42 条 2 号: 上り坂の頂上附近・勾配の急な下り坂では徐行。
* 53 条 1 項: 進路を変えるとき合図し、終わるまで続ける。2 項: 環状交差点では出るとき(と徐行・停止・後退)に合図。
  3 項: 時期と方法は政令(施行令 21 条 —— **e-Gov 保守中で本文未確認**。3 秒・出口の 1 つ手前は教則の値を使う)。
  4 項: 行為が終わったらやめる、行為をしないのに合図をしない。

## 出典(書誌)と確認の状態

``SOURCES`` に 1 つずつ。primary = 一次の本文を文字で確認、secondary = 二次資料だけ、**assumed(仮定)** = 法令・規格に
数値が無い、unverified = 一次がある筈だが今回読めなかった。

## 単位と座標

m, s, m/s, m/s², rad。道に沿った位置 x(進行方向に増える)。上から見た 2 次元は x = 前・y = 左(左側通行)。
環状交差点の角は数学の向き(反時計回りが正)で、右回り = 角が減る向き。

## 限界(self_reported)

* 「付近」「勾配の急な」「急に」「徐行」に数値の規定は無い(付近 30 m、急な下り 10 %、急な減速 2.0 m/s²、徐行 10 km/h は
  **仮定**)。
* ルームミラーは平面鏡・後ろの窓や車体による遮りを見ない(鏡に映る範囲だけ)。
* 凸面鏡の見誤りは近軸(鏡の中心付近で反射)。鏡を斜めに見る実際の置き方では非点収差で縦と横の倍率が違う(測っていない)。
* 縦断曲線の視距は水平投影。平面の曲線と重なる道(平面視距)は見ない。
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

import drivecrossing as _DC
import drivedecide as _DD
import drivelateral as _DL

__all__ = [
    "SOURCES", "G", "SIGHT_EYE_HEIGHT", "SIGHT_OBJECT_HEIGHT", "SIGHT_DISTANCE_TABLE", "CREST_RADIUS_TABLE",
    "NO_PASSING_ZONE", "VICINITY", "STEEP_GRADE", "SUDDEN_DECEL", "CRAWL_SPEED", "SIGNAL_LEAD_TIME", "EXEMPT_KINDS",
    "overtake_requirement", "overtake_return_gap", "no_overtaking_zones", "overtake_permitted",
    "overtaken_conduct_check",
    "lane_change_follower_decel", "lane_change_permitted",
    "roundabout_entry_check", "roundabout_signal_point", "roundabout_signal_check",
    "crest_sight_distance", "crest_safe_speed", "hill_meeting_yield",
    "convex_mirror_image", "convex_mirror_misjudge", "mirror_image_side", "mirror_road_coverage",
]

G = 9.80665                                          # 標準重力 [m/s²]、drivelong と同じ
#: 道路構造令 2 条 24 号: 視距は車線の中心線 1.2 m の高さから、中心線上の高さ 10 cm の物の頂点を見とおす距離
SIGHT_EYE_HEIGHT = 1.2
SIGHT_OBJECT_HEIGHT = 0.1
#: 道路構造令 19 条の表(視距 [m])。国交省「道路構造令について」の抜粋に載っている行だけ(途中の行は ・・・ で省略されている)
SIGHT_DISTANCE_TABLE: Dict[int, float] = {120: 210.0, 100: 160.0, 20: 20.0}
#: 道路構造令 22 条の表(凸形縦断曲線の半径 [m])。同じ抜粋に載っている行だけ
CREST_RADIUS_TABLE: Dict[int, float] = {120: 11000.0, 100: 6500.0, 20: 100.0}
#: 30 条 3 号: 交差点・踏切・横断歩道・自転車横断帯の手前の側端から前に 30 m
NO_PASSING_ZONE = 30.0
#: 30 条 1 号の「付近」の幅 [m]。**仮定**: 法に数値なし
VICINITY: Dict[str, float] = {"curve": 30.0, "crest": 30.0}
#: 30 条 1 号・42 条 2 号の「勾配の急な」下り坂(**仮定**: 10 % 以上。法に数値なし)
STEEP_GRADE = 0.10
#: 26 条の 2 第 2 項・2 条 22 号の「急に」(**仮定**: drivecrossing の進行妨害と同じ 2.0 m/s²)
SUDDEN_DECEL = 2.0
#: 徐行(2 条 1 項 20 号「直ちに停止することができるような速度」)を 10 km/h 以下とみなす(**仮定**、drivelateral と同じ)
CRAWL_SPEED = 10.0 / 3.6
#: 進路変更の合図の時期(教則 5-5-1 表「約 3 秒前」。施行令 21 条は未確認)
SIGNAL_LEAD_TIME = 3.0
#: 30 条で追越し禁止の対象から除かれる「特定小型原動機付自転車等」(drivecrossing と同じ)
EXEMPT_KINDS = _DC.EXEMPT_KINDS

SOURCES: Dict[str, Dict[str, str]] = {
    "road_traffic_act": {
        "status": "primary", "value": "道路交通法 2条1項20・21・22号・26条の2・27条・28条・29条・30条・35条の2・37条の2・"
                                      "42条・53条",
        "source": "道路交通法(昭和35年法律第105号)。e-Gov 法令 API v2 の Wayback Machine 保存版(2026-02-04 捕捉、"
                  "2025-06-01 施行版)を本文で確認(第 11 回の取得物 act_arts.json)。e-Gov 本体は 2026-10-01 保守中"},
    "enforcement_order_art21": {
        "status": "unverified", "value": "合図の時期(進路変更 3 秒前・右左折 30 m 手前・環状交差点の出口)",
        "source": "道路交通法施行令 21 条。e-Gov 法令検索は JavaScript の画面で、Wayback の保存版(2024-05-18・2026-08-04)は"
                  "本文を含まない = 未確認。値は教則の表(下の kyosoku)を使う"},
    "kyosoku": {
        "status": "primary", "value": "5-5-1(1)(2) 合図の表(約 3 秒前・出口の 1 つ手前の出口の側方)、5-6-3 追越しの手順"
                                      "(約 3 秒後に右へ・ルームミラーで見える距離まで進んで戻る)、5-7-4 環状交差点、"
                                      "6-2-1(3)(6) 坂の頂上・坂道の行き違い",
        "source": "交通の方法に関する教則(令和6年9月4日 告示第37号まで)npa.go.jp/bureau/traffic/20241113kyousoku.pdf の"
                  "本文(27・52・55・66 頁)を文字で確認。要約のみ・転載しない"},
    "sight_distance": {
        "status": "primary", "value": "視距 = 1.2 m の高さから 10 cm の物の頂点(構造令 2 条 24 号)、表: 120 km/h 210 m・"
                                      "100 km/h 160 m・20 km/h 20 m(19 条)、凸形縦断曲線半径 11,000・6,500・100 m(22 条)",
        "source": "国土交通省 道路局「道路構造令について(1)」86–87 頁(条文の引用。出典表記: 道路構造令の解説と運用 "
                  "令和3年3月 日本道路協会)。構造令の本文そのもの(e-Gov)は保守中で未照合"},
    "parabolic_crest": {
        "status": "literature", "value": "S ≤ L: L = A S²/(2(√h₁+√h₂)²)、S > L: L = 2S − 2(√h₁+√h₂)²/A(A は比)",
        "source": "AASHTO, A Policy on Geometric Design of Highways and Streets(Green Book)3.4.6 の式を比で書いた形。"
                  "式は放物線の幾何から出る(門は見通し線の総当たりで検算)"},
    "paraxial_mirror": {
        "status": "literature", "value": "1/a + 1/b = 2/R(球面鏡、近軸)、倍率 b/a",
        "source": "E. Hecht, Optics, 5th ed., Pearson 2017, 5.4。門は 2 次元の光線追跡"},
    "vicinity": {
        "status": "assumed", "value": "曲がり角・上り坂の頂上の「付近」= 前後 30 m",
        "source": "法に数値なし"},
    "steep_grade": {
        "status": "assumed", "value": "「勾配の急な」= 10 % 以上", "source": "法に数値なし"},
    "sudden_decel": {
        "status": "assumed", "value": "「急に」= 要る減速度 > 2.0 m/s²", "source": "法に数値なし(drivecrossing と同じ値)"},
    "crawl": {
        "status": "assumed", "value": "徐行 = 10 km/h 以下", "source": "法 2 条 1 項 20 号は文言のみ(drivelateral と同じ値)"},
    "increase_tol": {
        "status": "assumed", "value": "27 条 1 項の「速度を増す」= 0.2 m/s を超える増加", "source": "法に数値なし(測定の雑音分)"},
    "hill_refuge": {
        "status": "assumed", "value": "坂道の行き違いで上りの車が使う「近くの待避所」= 30 m 以内",
        "source": "教則 6-2-1(6) は「近くに」のみ。法に明文なし"},
}


# ───────────────────────────── 入力の検査 ─────────────────────────────
def _finite(v, name: str, op: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (op, name, v))
    return x


def _positive(v, name: str, op: str) -> float:
    x = _finite(v, name, op)
    if x <= 0:
        raise ValueError("%s: %s must be > 0 (got %r)" % (op, name, v))
    return x


def _nonneg(v, name: str, op: str) -> float:
    x = _finite(v, name, op)
    if x < 0:
        raise ValueError("%s: %s must be >= 0 (got %r)" % (op, name, v))
    return x


def _array(v, name: str, op: str) -> np.ndarray:
    try:
        a = np.asarray(v, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric" % (op, name)) from None
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _vec2(v, name: str, op: str) -> np.ndarray:
    a = _array(v, name, op)
    if a.shape != (2,):
        raise ValueError("%s: %s must be a 2-vector" % (op, name))
    return a


def _unit2(v, name: str, op: str) -> np.ndarray:
    a = _vec2(v, name, op)
    n = float(np.linalg.norm(a))
    if not n > 1e-12:
        raise ValueError("%s: %s must be non-zero" % (op, name))
    return a / n


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _merge(iv: Iterable[Tuple[float, float]]) -> np.ndarray:
    merged: List[List[float]] = []
    for a, b in sorted(iv):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return np.array(merged, np.float64).reshape(-1, 2)


# ───────────────────────────── 1. 追越し ─────────────────────────────
def _rel_time(D: float, w: float, a: float, vmax: float, vL: float, v0: float) -> float:
    """相対距離 D を進む時間(自車 v0 → a で vmax まで、前車 vL 一定)。w = v0 − vL。"""
    if a == 0.0:
        return D / w
    ta = (vmax - v0) / a
    ra = w * ta + 0.5 * a * ta * ta
    if D <= ra:
        return 2.0 * D / (w + math.sqrt(w * w + 2.0 * a * D))
    return ta + (D - ra) / (vmax - vL)


def _ego_dist(t: float, v0: float, a: float, vmax: float) -> float:
    if a == 0.0:
        return v0 * t
    ta = (vmax - v0) / a
    if t <= ta:
        return v0 * t + 0.5 * a * t * t
    return v0 * ta + 0.5 * a * ta * ta + vmax * (t - ta)


def overtake_requirement(v_ego: float, v_lead: float, *, lead_length: float, ego_length: float, gap_back: float,
                         gap_front: float, accel: float = 0.0, v_max: Optional[float] = None,
                         lane_change_time: float = 0.0, v_oncoming: float = 0.0, pet_min: float = 0.0) -> Dict[str, float]:
    """前車を追い越すのに要る時間・道のりと、対向車が来ない境目の距離(閉形式)。場面 S079・S086・S145(28 条 4 項)。

    自車の前端が前車の後端の ``gap_back`` 手前で対向車線(又は右の車線)に出てから、自車の後端が前車の前端の ``gap_front``
    先に出るまで(相対の距離 D = gap_back + lead_length + ego_length + gap_front)。自車は初速 ``v_ego`` から ``accel`` で
    ``v_max`` まで加速(教則 5-6-3(4)「最高速度の制限内で加速しながら」)、前車は ``v_lead`` で一定。そのあと
    ``lane_change_time`` かけて元の車線に戻り切る。``gap_front`` に ``overtake_return_gap`` の値を入れると「ルームミラーで
    見える距離」まで進んでから戻る手順(教則 5-6-3(6))になる。

    返り値: ``relative_distance`` = D、``t_pass``、``t_occupy`` = t_pass + lane_change_time、``ego_distance``(占有の間に
    自車が進む道のり)、``v_pass``(追い越し終えたときの速さ)、``d_required`` = ego_distance + v_oncoming (t_occupy +
    pet_min)(判断の時点で対向車がこれより遠ければ、戻り切ってから pet_min 秒以上あとに対向車がその地点に着く)。
    前に出られない(相対速度が正にならない)は ValueError。"""
    op = "overtake_requirement"
    v0 = _nonneg(v_ego, "v_ego", op)
    vL = _nonneg(v_lead, "v_lead", op)
    Ll = _positive(lead_length, "lead_length", op)
    Le = _positive(ego_length, "ego_length", op)
    gb = _nonneg(gap_back, "gap_back", op)
    gf = _nonneg(gap_front, "gap_front", op)
    a = _nonneg(accel, "accel", op)
    tlc = _nonneg(lane_change_time, "lane_change_time", op)
    von = _nonneg(v_oncoming, "v_oncoming", op)
    pm = _nonneg(pet_min, "pet_min", op)
    if v_max is None:
        vmax = math.inf
    else:
        vmax = _positive(v_max, "v_max", op)
        if v0 > vmax:
            raise ValueError("%s: v_ego must not exceed v_max" % op)
    if a == 0.0:
        if not v0 > vL:
            raise ValueError("%s: without acceleration v_ego must exceed v_lead" % op)
        vmax = v0
    elif not vmax > vL:
        raise ValueError("%s: v_max must exceed v_lead (otherwise the lead is never passed)" % op)
    D = gb + Ll + Le + gf
    w = v0 - vL
    t = _rel_time(D, w, a, vmax if math.isfinite(vmax) else 1e300, vL, v0)
    T = t + tlc
    vm = vmax if math.isfinite(vmax) else 1e300
    s = _ego_dist(T, v0, a, vm)
    vp = min(v0 + a * t, vmax)
    return {"relative_distance": D, "t_pass": t, "t_occupy": T, "ego_distance": s, "v_pass": vp,
            "d_required": s + von * (T + pm)}


def _virtual_eye(E, M, n):
    return E - 2.0 * float(np.dot(E - M, n)) * n


def _mirror_s(P, Ev, M, n, t):
    """仮想の眼 Ev から点 P(配列可)を結ぶ直線が鏡の直線と交わる位置(鏡の中心からの符号つき距離)。"""
    q = P - Ev
    c = float(np.dot(M - Ev, n))
    lam = c / (q @ n)
    X = Ev + lam[..., None] * q
    return (X - M) @ t


def overtake_return_gap(*, lane_offset: float, lead_width: float, eye_xy=(0.0, -0.35), mirror_center_xy=(0.55, 0.0),
                        mirror_normal_xy=None, mirror_width: float = 0.25, eye_to_rear: float = 2.8) -> Dict[str, object]:
    """追い越した前車の **全体がルームミラーに映る** ときの車間(自車の後端と前車の前端の間)。場面 S086・S145。

    教則 5-6-3(6)「追い越した車がルームミラーで見えるくらいの距離までそのまま進み」・7-2-3「追い越した車全体が
    ルームミラーに映ってから」を幾何にする。座標は自車(x = 前、y = 左、原点 = 眼の真横の車の中心線)。前車は左の車線
    (横の中心 = ``lane_offset``、幅 ``lead_width``)で自車の後ろ。ルームミラーは平面鏡(中心 ``mirror_center_xy``、
    幅 ``mirror_width``、法線は眼の側)。法線を省くと、眼から鏡の中心への光線を真後ろ(−x)へ返す向き
    (``drivedecide.mirror_aim_normal``)。

    映る ⇔ 仮想の眼 E'(眼を鏡の直線で折り返した点)と点を結ぶ線分が鏡の線分を通る。道に平行な直線の上では境目は 1 次
    方程式の根で、前の辺の両端(2 隅)で決まる。返り値: ``gap`` = 眼の後ろ ``eye_to_rear`` の自車の後端から、前の 2 隅が
    映る前車の前端までの距離、``corner_limit_x``(各隅が映る x の上限)、``straight_back_s``(真後ろの方向が鏡のどこを通るか。
    鏡の外なら真後ろが映らない = ValueError)。"""
    op = "overtake_return_gap"
    lo = _finite(lane_offset, "lane_offset", op)
    lw = _positive(lead_width, "lead_width", op)
    E = _vec2(eye_xy, "eye_xy", op)
    M = _vec2(mirror_center_xy, "mirror_center_xy", op)
    w = _positive(mirror_width, "mirror_width", op) / 2.0
    er = _positive(eye_to_rear, "eye_to_rear", op)
    if mirror_normal_xy is None:
        n = _DD.mirror_aim_normal(E, M, np.array([-1.0, 0.0]))
    else:
        n = _unit2(mirror_normal_xy, "mirror_normal_xy", op)
    if float(np.dot(E - M, n)) <= 0:
        raise ValueError("%s: the mirror normal must face the eye" % op)
    t = np.array([-n[1], n[0]])
    Ev = _virtual_eye(E, M, n)
    c = float(np.dot(M - Ev, n))
    sE = float(np.dot(Ev - M, t))
    # 真後ろ(x → −∞)の方向 (−1, 0) が通る鏡の位置
    d = np.array([-1.0, 0.0])
    if float(d @ n) <= 0:
        raise ValueError("%s: the mirror does not face backwards" % op)
    s_inf = sE + c * float(d @ t) / float(d @ n)
    if abs(s_inf) > w:
        raise ValueError("%s: straight back is not in the mirror (s = %.3f, half width %.3f)" % (op, s_inf, w))
    limits = []
    for y in (lo - lw / 2.0, lo + lw / 2.0):
        roots = []
        for edge in (-w, w):
            kap = (edge - sE) / c
            gx, gy = t[0] - kap * n[0], t[1] - kap * n[1]
            if abs(gx) < 1e-15:
                continue
            x = Ev[0] - gy * (y - Ev[1]) / gx
            P = np.array([x, y])
            if float(np.dot(P - M, n)) > 1e-12:            # 鏡の眼の側にある根だけ
                roots.append(x)
        # 後ろ(−∞)から前へ動かして最初に鏡の端に届く根
        xm = M[0] + (M[1] - y) * n[1] / n[0] if abs(n[0]) > 1e-15 else math.inf   # 鏡の直線と横位置 y の交点
        limits.append(min(roots) if roots else xm)
    xf = min(limits)
    return {"gap": (-er) - xf, "corner_limit_x": np.array(limits), "straight_back_s": s_inf, "virtual_eye": Ev,
            "mirror_normal": n}


def no_overtaking_zones(features: Iterable[dict], *, priority_road: bool = False, vicinity: Optional[dict] = None,
                        steep_grade: float = STEEP_GRADE, zone: float = NO_PASSING_ZONE) -> Dict[str, object]:
    """道に沿った施設から、30 条の追越し(のための進路変更・側方通過)の禁止区間を作る。場面 S081・S009・S130。

    features[i] = {"kind", "start", "end"}(点の施設は "at")。kind:
    ``sign``(標識等で禁止された区間をそのまま)、``curve``(曲がり角、1 号「付近」= 前後 ``vicinity``、**仮定** 30 m)、
    ``crest``(上り坂の頂上、同)、``downhill``(下り坂、"grade" が ``steep_grade``(**仮定** 10 %)以上か grade 無しなら
    1 号の「勾配の急な」)、``tunnel``(2 号。"has_lanes" が真なら除外)、``intersection``(3 号。``priority_road`` を
    通行しているなら除外)、``railway_crossing`` / ``crosswalk`` / ``bicycle_crossing``(3 号)。3 号は [start − 30, end]。
    返り値: ``zones`` = [(a, b, kind, 号)]、``merged`` = 重なりを併せた (k, 2)。"""
    op = "no_overtaking_zones"
    V = dict(VICINITY)
    if vicinity:
        V.update(vicinity)
    sg = _nonneg(steep_grade, "steep_grade", op)
    zn = _nonneg(zone, "zone", op)
    art = {"sign": "30条(標識等)", "curve": "30条1号", "crest": "30条1号", "downhill": "30条1号", "tunnel": "30条2号",
           "intersection": "30条3号", "railway_crossing": "30条3号", "crosswalk": "30条3号", "bicycle_crossing": "30条3号"}
    zones = []
    for f in features:
        if not isinstance(f, dict) or "kind" not in f:
            raise ValueError("%s: each feature must be a dict with 'kind'" % op)
        k = f["kind"]
        if k not in art:
            raise ValueError("%s: unknown kind %r (known: %s)" % (op, k, sorted(art)))
        if "at" in f:
            s = e = _finite(f["at"], "at", op)
        else:
            s = _finite(f.get("start"), "start", op)
            e = _finite(f.get("end"), "end", op)
        if e < s:
            raise ValueError("%s: end must be >= start" % op)
        if k == "tunnel" and bool(f.get("has_lanes", False)):
            continue
        if k == "intersection" and priority_road:
            continue
        if k == "downhill" and "grade" in f and abs(_finite(f["grade"], "grade", op)) < sg:
            continue
        if k in ("curve", "crest"):
            d = _nonneg(V[k], "vicinity", op)
            a, b = s - d, e + d
        elif k in ("intersection", "railway_crossing", "crosswalk", "bicycle_crossing"):
            a, b = s - zn, e
        else:
            a, b = s, e
        zones.append((a, b, k, art[k]))
    return {"zones": zones, "merged": _merge((z[0], z[1]) for z in zones)}


def overtake_permitted(*, maneuver_start: float, maneuver_end: float, zones_result: Optional[dict] = None,
                       lead_kind: str = "car", lead_overtaking: bool = False, lead_keeping_right: bool = False,
                       side: str = "right", dist_oncoming: float = math.inf, requirement: Optional[dict] = None,
                       being_overtaken: bool = False) -> Dict[str, object]:
    """追越しを始めてよいか(条文と教則の判定)。場面 S077・S078・S079・S080・S081・S083。

    ``maneuver_start`` .. ``maneuver_end`` = 進路を変え始めてから前車の側方を通り終えるまでの自車の前端の位置。
    理由(code, 根拠):
    * ``no_passing_zone``(30 条): その区間が ``no_overtaking_zones`` の禁止区間と重なる(前車が ``EXEMPT_KINDS`` なら除く)。
    * ``double_overtaking``(29 条): 前車が他の自動車を追い越そうとしている。
    * ``wrong_side``(28 条 1・2 項): 前車が右折のため中央(右側端)に寄っている(``lead_keeping_right``)なら左、それ以外は右。
    * ``oncoming_too_close``(28 条 4 項 + 閉形式): ``dist_oncoming`` < ``requirement["d_required"]``
      (``overtake_requirement`` の返り値)。
    * ``being_overtaken``(教則 5-6-1(2)エ。**法の明文なし**、場面 S080): 後ろの車が自車を追い越そうとしている。
    返り値: ``ok``、``reasons`` = [(code, 根拠)]、``required_side``。"""
    op = "overtake_permitted"
    a = _finite(maneuver_start, "maneuver_start", op)
    b = _finite(maneuver_end, "maneuver_end", op)
    if b < a:
        raise ValueError("%s: maneuver_end must be >= maneuver_start" % op)
    if side not in ("right", "left"):
        raise ValueError("%s: side must be 'right' or 'left'" % op)
    reasons: List[Tuple[str, str]] = []
    if zones_result is not None:
        if not isinstance(zones_result, dict) or "zones" not in zones_result:
            raise ValueError("%s: zones_result must come from no_overtaking_zones" % op)
        if str(lead_kind) not in EXEMPT_KINDS:
            hit = [z for z in zones_result["zones"] if min(b, z[1]) - max(a, z[0]) > 0]
            if hit:
                reasons.append(("no_passing_zone", " / ".join(sorted({z[3] for z in hit}))))
    if lead_overtaking:
        reasons.append(("double_overtaking", "29条"))
    need = "left" if lead_keeping_right else "right"
    if side != need:
        reasons.append(("wrong_side", "28条2項" if lead_keeping_right else "28条1項"))
    if requirement is not None:
        if not isinstance(requirement, dict) or "d_required" not in requirement:
            raise ValueError("%s: requirement must come from overtake_requirement" % op)
        D = float(dist_oncoming)
        if math.isnan(D) or D == -math.inf:
            raise ValueError("%s: dist_oncoming must be a number or +inf" % op)
        if D < requirement["d_required"]:
            reasons.append(("oncoming_too_close", "28条4項(閉形式の境目)"))
    if being_overtaken:
        reasons.append(("being_overtaken", "教則5-6-1(2)エ(法の明文なし)"))
    return {"ok": not reasons, "reasons": reasons, "required_side": need}


def overtaken_conduct_check(trajectory, *, t_caught: float, t_passed: float, kind: str = "car",
                            overtaker_higher_limit: bool = True, continuing_slower: bool = False,
                            lanes: bool = False, room: Optional[float] = None, room_needed: Optional[float] = None,
                            tol: float = 0.2) -> Dict[str, object]:
    """追い越される側の義務(27 条)。場面 S085。

    ``trajectory`` = {"t", "v"}(追い越される車の速さ)。27 条 1 項の対象 = 乗合自動車・トロリーバス(``kind`` が
    "route_bus" / "trolleybus")以外で、追いついた車の最高速度が高い(``overtaker_higher_limit``)か、同じか低くても
    その速さより遅く進み続ける(``continuing_slower``)とき。その間 [t_caught, t_passed] に **速度を増した量** =
    max_t (v(t) − min_{s ≤ t} v(s)) が ``tol``(**仮定** 0.2 m/s)を超えると ``speed_increased``。
    27 条 2 項: 車両通行帯の無い道路(``lanes`` が偽)で中央との間の余地 ``room`` < ``room_needed`` なら ``must_yield_left``。
    返り値: ``applies``、``increase``、``violations``、``must_yield_left``。"""
    op = "overtaken_conduct_check"
    if not isinstance(trajectory, dict) or "t" not in trajectory or "v" not in trajectory:
        raise ValueError("%s: trajectory must be a dict with 't' and 'v'" % op)
    t = _array(trajectory["t"], "t", op)
    v = _array(trajectory["v"], "v", op)
    if t.ndim != 1 or t.shape != v.shape or t.size < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("%s: t, v must be 1-D of the same length >= 2 with t strictly increasing" % op)
    t0 = _finite(t_caught, "t_caught", op)
    t1 = _finite(t_passed, "t_passed", op)
    if t1 < t0:
        raise ValueError("%s: t_passed must be >= t_caught" % op)
    tl = _nonneg(tol, "tol", op)
    applies = kind not in ("route_bus", "trolleybus") and (bool(overtaker_higher_limit) or bool(continuing_slower))
    sel = (t >= t0) & (t <= t1)
    vv = np.concatenate([[np.interp(t0, t, v)], v[sel], [np.interp(t1, t, v)]])
    inc = float(np.max(vv - np.minimum.accumulate(vv)))
    viol = []
    if applies and inc > tl:
        viol.append("speed_increased")
    must = False
    if applies and not lanes and room is not None:
        need = _positive(room_needed, "room_needed", op) if room_needed is not None else None
        if need is None:
            raise ValueError("%s: room_needed is required with room" % op)
        must = _finite(room, "room", op) < need
    return {"applies": applies, "increase": inc, "violations": viol, "ok": not viol, "must_yield_left": must}


# ───────────────────────────── 2. 進路変更 ─────────────────────────────
def lane_change_follower_decel(gap, v_follow, v_ego, *, reaction: float, accel_ego: float = 0.0, min_gap: float = 0.0,
                               sudden: float = SUDDEN_DECEL) -> Dict[str, object]:
    """進路を変えた先の後続車が、自車に min_gap より近づかないために要る一定の減速度(閉形式、配列可)。場面 S072。

    車間 ``gap`` = 後続車の前端と自車の後端の距離(変えた瞬間)、後続車 ``v_follow``、自車 ``v_ego``(``accel_ego`` ≥ 0 で
    加速し続ける)。後続車は ``reaction`` の間は速さを保ち、その後一定の減速。w₀ = v_follow − v_ego。
    反応の間に詰まる量 = w₀τ − a_eτ²/2(相対速度が反応の中で 0 に届けば w₀²/(2a_e))。反応の後の相対速度
    w₁ = w₀ − a_eτ、残り g₁ = gap − min_gap − (詰まる量)。要る減速度 b = max(0, w₁²/(2g₁) − a_e)。
    反応の間にもう min_gap を割るなら ∞。``obstructs`` = b > ``sudden``(**仮定** 2.0 m/s²、26 条の 2 第 2 項「急に」)。"""
    op = "lane_change_follower_decel"
    g = _array(gap, "gap", op)
    vf = _array(v_follow, "v_follow", op)
    ve = _array(v_ego, "v_ego", op)
    tau = _nonneg(reaction, "reaction", op)
    ae = _nonneg(accel_ego, "accel_ego", op)
    s0 = _nonneg(min_gap, "min_gap", op)
    sd = _positive(sudden, "sudden", op)
    if np.any(vf < 0) or np.any(ve < 0):
        raise ValueError("%s: speeds must be >= 0" % op)
    g, vf, ve = np.broadcast_arrays(g, vf, ve)
    ge = g - s0
    w0 = vf - ve
    if ae > 0:
        t_zero = np.where(w0 > 0, w0 / ae, 0.0)
        early = t_zero <= tau                                    # 反応の中で相対速度が 0 に届く
        close = np.where(early, w0 * w0 / (2.0 * ae), w0 * tau - 0.5 * ae * tau * tau)
    else:
        early = np.zeros(w0.shape, bool)
        close = w0 * tau
    w1 = np.where(early, 0.0, w0 - ae * tau)
    g1 = ge - close
    with np.errstate(divide="ignore", invalid="ignore"):
        b = np.where(g1 > 0, w1 * w1 / (2.0 * np.where(g1 > 0, g1, 1.0)) - ae, np.inf)
    b = np.maximum(b, 0.0)
    b = np.where((w0 <= 0) & (ge >= 0), 0.0, b)                  # 近づかない
    b = np.where(early & (g1 >= 0), 0.0, b)                      # 反応の中で離れ始める
    b = np.where(ge < 0, np.inf, b)                              # 変えた瞬間にもう近すぎる
    out = float(b) if b.ndim == 0 else b
    obs = b > sd
    return {"decel": out, "obstructs": bool(obs) if obs.ndim == 0 else obs}


def lane_change_permitted(*, follower: Optional[dict] = None, boundary: str = "none", exception: Optional[str] = None,
                          signal_events: Optional[Sequence[dict]] = None, sudden: float = SUDDEN_DECEL) -> Dict[str, object]:
    """進路変更をしてよいか(条文の判定)。場面 S067・S072・S073。

    * ``follower_sudden_decel``(26 条の 2 第 2 項): ``follower`` = {"gap", "v_follow", "v_ego", "reaction"[, "accel_ego",
      "min_gap"]} に ``lane_change_follower_decel`` で要る減速度が ``sudden`` を超える。
    * ``no_lane_change_marking``(26 条の 2 第 3 項): ``boundary`` = "yellow"(進路変更の禁止を表示する道路標示)を越える。
      ``exception`` = "article40"(緊急自動車に譲る)/ "obstruction"(道路の損壊・工事その他の障害)なら除外(同項 1・2 号)。
    * ``signal_*``(53 条 1 項・教則 5-5-1「約 3 秒前」): ``signal_events`` を ``drivedecide.check_sequence_score``
      (maneuver="lane_change")で採点した違反をそのまま足す(施行令 21 条は未確認)。
    26 条の 2 第 1 項「みだりに」は数値にできないので判定しない。返り値: ``ok``、``reasons``、``decel``、``sequence``。"""
    op = "lane_change_permitted"
    if boundary not in ("none", "white", "yellow"):
        raise ValueError("%s: boundary must be 'none', 'white' or 'yellow'" % op)
    if exception not in (None, "article40", "obstruction"):
        raise ValueError("%s: exception must be None, 'article40' or 'obstruction'" % op)
    reasons: List[Tuple[str, str]] = []
    dec = None
    if follower is not None:
        if not isinstance(follower, dict):
            raise ValueError("%s: follower must be a dict" % op)
        for k in ("gap", "v_follow", "v_ego", "reaction"):
            if k not in follower:
                raise ValueError("%s: follower needs %r" % (op, k))
        r = lane_change_follower_decel(follower["gap"], follower["v_follow"], follower["v_ego"],
                                       reaction=follower["reaction"], accel_ego=follower.get("accel_ego", 0.0),
                                       min_gap=follower.get("min_gap", 0.0), sudden=sudden)
        dec = r["decel"]
        if r["obstructs"]:
            reasons.append(("follower_sudden_decel", "26条の2第2項"))
    if boundary == "yellow" and exception is None:
        reasons.append(("no_lane_change_marking", "26条の2第3項"))
    seq = None
    if signal_events is not None:
        seq = _DD.check_sequence_score(signal_events, maneuver="lane_change", lead_time=SIGNAL_LEAD_TIME)
        for v in seq["violations"]:
            reasons.append(("signal_" + str(v["rule"]), "53条1項・教則5-5-1"))
    return {"ok": not reasons, "reasons": reasons, "decel": dec, "sequence": seq}


# ───────────────────────────── 3. 環状交差点 ─────────────────────────────
def _cw(a_from, a_to):
    """右回り(角が減る向き)に a_from から a_to まで進む角 ∈ [0, 2π)。"""
    return np.mod(np.asarray(a_from, np.float64) - np.asarray(a_to, np.float64), 2.0 * math.pi)


def roundabout_entry_check(entry_theta: float, ring_radius: float, circulating: Sequence[dict], *, t_clear: float,
                           entry_speed: float, crawl: float = CRAWL_SPEED, sudden: float = SUDDEN_DECEL,
                           side_friction: Optional[float] = None) -> Dict[str, object]:
    """環状交差点に入ってよいか(37 条の 2 第 1・2 項、35 条の 2)。場面 S102。

    環道(中心 = 原点、半径 ``ring_radius``)を右回りに走る車 circulating[i] = {"theta", "speed"} が、入口の角 ``entry_theta``
    (衝突の点)まで進む弧 = R·((θ − θ_e) mod 2π)、着く時刻 = 弧 / speed。入る車が衝突の点を抜けるのに ``t_clear`` 秒かかる
    とき、環道の車が t_clear まで点に入らないために要る減速度(``drivecrossing.obstruction_decel``)が ``sudden``
    (**仮定**)を超えれば進行妨害 → ``must_yield``(37 条の 2 第 1 項)。``entry_speed`` > ``crawl``(**仮定** 10 km/h)は
    ``not_crawling``(同 2 項・35 条の 2 の徐行)。``side_friction`` を渡すと環道の曲線の上限速度
    (``drivelateral.curve_speed_limit``)も返す。返り値: ``ok``、``reasons``、``cars`` = [{"arc", "t_arrive", "decel",
    "obstructs"}]、``ring_speed_limit``。"""
    op = "roundabout_entry_check"
    te = _finite(entry_theta, "entry_theta", op)
    R = _positive(ring_radius, "ring_radius", op)
    tc = _nonneg(t_clear, "t_clear", op)
    es = _nonneg(entry_speed, "entry_speed", op)
    cr = _positive(crawl, "crawl", op)
    cars = []
    for i, c in enumerate(circulating):
        if not isinstance(c, dict) or "theta" not in c or "speed" not in c:
            raise ValueError("%s: circulating[%d] must be a dict with 'theta' and 'speed'" % (op, i))
        th = _finite(c["theta"], "theta", op)
        sp = _nonneg(c["speed"], "speed", op)
        arc = R * float(_cw(th, te))
        ta = arc / sp if sp > 0 else math.inf
        ob = _DC.obstruction_decel(arc, sp, tc, sudden=sudden)
        cars.append({"arc": arc, "t_arrive": ta, "decel": ob["decel"], "obstructs": bool(ob["obstructs"])})
    reasons: List[Tuple[str, str]] = []
    if True in [c["obstructs"] for c in cars]:
        reasons.append(("must_yield", "37条の2第1項"))
    if es > cr + 1e-12:
        reasons.append(("not_crawling", "37条の2第2項・35条の2"))
    lim = None
    if side_friction is not None:
        lim = _DL.curve_speed_limit(R, side_friction=side_friction)
    return {"ok": not reasons, "reasons": reasons, "cars": cars, "ring_speed_limit": lim}


def roundabout_signal_point(arm_angles: Sequence[float], entry: int, exit: int) -> Dict[str, object]:
    """環状交差点を出るときの左の合図を始める位置(右回りに進んだ角)。場面 S069。

    教則 5-5-1(2)・5-7-2(4): 出ようとする地点の直前の出口の側方を通過したとき、入った直後の出口を出るなら入ったとき
    (53 条 2 項。時期の政令 = 施行令 21 条は未確認)。``arm_angles`` = 各枝の角、``entry`` / ``exit`` = 番号。
    右回りに入口から測った各枝の角 d_i = (θ_entry − θ_i) mod 2π(出口 = 入口なら 2π、転回)。合図の角 = 目的の出口の角より
    小さい d_i の最大値(無ければ 0 = 入ったとき)。返り値: ``signal_angle``、``exit_angle``、``exits_before``(通り過ぎる出口の数)、
    ``signal_theta``(環道の上の角)。"""
    op = "roundabout_signal_point"
    th = _array(arm_angles, "arm_angles", op)
    if th.ndim != 1 or th.size < 2:
        raise ValueError("%s: arm_angles must be 1-D with >= 2 arms" % op)
    n = th.size
    for nm, k in (("entry", entry), ("exit", exit)):
        if not isinstance(k, (int, np.integer)) or not 0 <= int(k) < n:
            raise ValueError("%s: %s must be an arm index in [0, %d)" % (op, nm, n))
    d = _cw(th[entry], th)
    d[entry] = 2.0 * math.pi
    if np.any(d[np.arange(n) != entry] <= 1e-12):
        raise ValueError("%s: two arms share the same angle" % op)
    dt = float(d[exit])
    before = d[(d < dt - 1e-12) & (np.arange(n) != entry)]
    sa = float(before.max()) if before.size else 0.0
    return {"signal_angle": sa, "exit_angle": dt, "exits_before": int(before.size),
            "signal_theta": float(np.mod(th[entry] - sa, 2.0 * math.pi))}


def roundabout_signal_check(progress, left_on, *, arm_angles: Sequence[float], entry: int, exit: int, right_on=None,
                            tol: float = 0.05) -> Dict[str, object]:
    """環状交差点の中の合図を採点する(53 条 2・4 項、教則 5-5-1(2))。場面 S069。

    ``progress`` = 入口から右回りに進んだ角 [rad]、単調非減少、サンプルごと、``left_on`` / ``right_on`` = 合図の状態(bool)。
    * ``left_late``: 合図の角 + ``tol`` から出口の角までの間に左の合図が消えているサンプルがある。
    * ``left_early``: 合図の角 − ``tol`` より手前で左の合図が点いている(手前の出口で出るように見える。53 条 4 項の
      「行為をしないのに合図」の **解釈**)。入った直後の出口(合図の角 = 0)では問わない。
    * ``right_signal``: 環道の中で右の合図(53 条 2 項は出るときだけを求める。4 項の **解釈**)。"""
    op = "roundabout_signal_check"
    p = _array(progress, "progress", op)
    lo = np.asarray(left_on, bool)
    if p.ndim != 1 or p.size < 2 or lo.shape != p.shape:
        raise ValueError("%s: progress and left_on must be 1-D of the same length >= 2" % op)
    if np.any(np.diff(p) < 0):
        raise ValueError("%s: progress must be non-decreasing" % op)
    tl = _nonneg(tol, "tol", op)
    sp = roundabout_signal_point(arm_angles, entry, exit)
    sa, ea = sp["signal_angle"], sp["exit_angle"]
    viol = []
    need = (p >= sa + tl) & (p <= ea)
    if np.any(need & ~lo):
        viol.append("left_late")
    if sa > 0 and np.any((p < sa - tl) & lo):
        viol.append("left_early")
    if right_on is not None:
        ro = np.asarray(right_on, bool)
        if ro.shape != p.shape:
            raise ValueError("%s: right_on must match progress" % op)
        if np.any(ro & (p <= ea)):
            viol.append("right_signal")
    return {"ok": not viol, "violations": viol, "signal_angle": sa, "exit_angle": ea}


# ───────────────────────────── 4. 坂 ─────────────────────────────
def crest_sight_distance(*, radius: Optional[float] = None, grade_in: Optional[float] = None,
                         grade_out: Optional[float] = None, length: Optional[float] = None,
                         eye_height: float = SIGHT_EYE_HEIGHT, object_height: float = SIGHT_OBJECT_HEIGHT) -> Dict[str, object]:
    """凸形縦断曲線(放物線)を越える最小の視距(閉形式)。場面 S065・S081(上り坂の頂上付近)。

    ``radius`` だけなら長さ無限の曲線(視距が曲線の中に収まる): S = √(2R)(√h₁ + √h₂)。``grade_in`` / ``grade_out``
    (比、上りが正)と ``length`` = 曲線の水平の長さ L なら A = grade_in − grade_out(> 0)、R = L/A で、
    S ≤ L なら上の式、S > L なら S = L/2 + (√h₁ + √h₂)²/A。h₁ = ``eye_height``、h₂ = ``object_height``
    (既定 1.2 m・0.1 m = 道路構造令 2 条 24 号。対向車を見るなら h₂ = 車の高さ)。
    返り値: ``sight``、``radius``、``within_curve``(S ≤ L)。"""
    op = "crest_sight_distance"
    h1 = _positive(eye_height, "eye_height", op)
    h2 = _nonneg(object_height, "object_height", op)
    K = (math.sqrt(h1) + math.sqrt(h2)) ** 2
    if radius is not None:
        if grade_in is not None or grade_out is not None or length is not None:
            raise ValueError("%s: give radius, or grade_in/grade_out/length — not both" % op)
        R = _positive(radius, "radius", op)
        return {"sight": math.sqrt(2.0 * R * K), "radius": R, "within_curve": True}
    if grade_in is None or grade_out is None or length is None:
        raise ValueError("%s: need radius, or grade_in, grade_out and length" % op)
    g1 = _finite(grade_in, "grade_in", op)
    g2 = _finite(grade_out, "grade_out", op)
    L = _positive(length, "length", op)
    A = g1 - g2
    if not A > 0:
        raise ValueError("%s: grade_in must exceed grade_out (a crest)" % op)
    R = L / A
    S = math.sqrt(2.0 * R * K)
    if S <= L:
        return {"sight": S, "radius": R, "within_curve": True}
    return {"sight": L / 2.0 + K / A, "radius": R, "within_curve": False}


def crest_safe_speed(sight, *, reaction: float, brake: float, theta: float = 0.0, c_rr: float = 0.0,
                     g: float = G, crawl: float = CRAWL_SPEED) -> Dict[str, object]:
    """見えている距離の中で止まれる上限の速さ(停止距離の逆関数、閉形式、配列可)。場面 S065。

    v ρ + v²/(2A) = S、A = brake + g sin θ + c_rr g cos θ(θ > 0 = 上り。``drivelong.stopping_distance_grade`` の空気抵抗なしの式)
    を解いた v = 2S/(ρ + √(ρ² + 2S/A))。A ≤ 0 は ValueError。返り値: ``speed`` [m/s]、``speed_kmh``、
    ``crawl_required``(42 条 2 号は頂上付近では速さによらず徐行 = True)、``crawl_sufficient``(徐行 ``crawl``(**仮定**)で
    視距の中に止まれるか)。"""
    op = "crest_safe_speed"
    S = _array(sight, "sight", op)
    if np.any(S < 0):
        raise ValueError("%s: sight must be >= 0" % op)
    rho = _nonneg(reaction, "reaction", op)
    b = _nonneg(brake, "brake", op)
    th = _finite(theta, "theta", op)
    if abs(th) >= math.pi / 4:
        raise ValueError("%s: |theta| must be < 45 degrees" % op)
    crr = _nonneg(c_rr, "c_rr", op)
    g = _positive(g, "g", op)
    cr = _positive(crawl, "crawl", op)
    A = b + g * math.sin(th) + crr * g * math.cos(th)
    if not A > 0:
        raise ValueError("%s: braking does not overcome the slope (A <= 0)" % op)
    v = 2.0 * S / (rho + np.sqrt(rho * rho + 2.0 * S / A))
    ok = v >= cr
    return {"speed": float(v) if v.ndim == 0 else v, "speed_kmh": float(v * 3.6) if v.ndim == 0 else v * 3.6,
            "crawl_required": True, "crawl_sufficient": bool(ok) if ok.ndim == 0 else ok}


def hill_meeting_yield(ego_direction: str, *, ego_refuge_distance: Optional[float] = None,
                       other_refuge_distance: Optional[float] = None, near: float = 30.0) -> Dict[str, object]:
    """坂道の狭い所での行き違い: どちらが譲るか(教則 6-2-1(6)。**法の明文なし**)。場面 S128。

    原則は下りの車が上りの車に譲る(上り坂の発進が難しいため)。ただし上りの車の近く(``near``、**仮定** 30 m 以内)に
    待避所があれば上りの車がそこに入って待つ。``ego_direction`` = "up" / "down"、``*_refuge_distance`` = その車から前方の
    待避所までの距離(無ければ None)。返り値: ``yielder`` ∈ {"ego", "other"}、``where`` ∈ {"refuge", "stop"}、``basis``。"""
    op = "hill_meeting_yield"
    if ego_direction not in ("up", "down"):
        raise ValueError("%s: ego_direction must be 'up' or 'down'" % op)
    nr = _nonneg(near, "near", op)
    er = None if ego_refuge_distance is None else _nonneg(ego_refuge_distance, "ego_refuge_distance", op)
    orr = None if other_refuge_distance is None else _nonneg(other_refuge_distance, "other_refuge_distance", op)
    up_ref = er if ego_direction == "up" else orr
    if up_ref is not None and up_ref <= nr:
        y = "ego" if ego_direction == "up" else "other"
        return {"yielder": y, "where": "refuge", "basis": "教則6-2-1(6)(上りの車でも近くの待避所で待つ)"}
    y = "ego" if ego_direction == "down" else "other"
    dn_ref = er if ego_direction == "down" else orr
    return {"yielder": y, "where": "refuge" if dn_ref is not None and dn_ref <= nr else "stop",
            "basis": "教則6-2-1(6)(下りの車が上りの車に譲る)"}


# ───────────────────────────── 5. カーブミラー ─────────────────────────────
def convex_mirror_image(object_distance, radius: float, *, eye_distance: float, object_size: float = 1.0) -> Dict[str, object]:
    """凸面鏡の虚像(近軸、配列可)。場面 S064・S130。

    1/a + 1/b = 2/R(b は鏡の向こうの虚像)→ b = aR/(2a + R)、倍率 m = R/(2a + R)。眼が鏡から e(``eye_distance``)のとき
    像の見かけの大きさ θ = 2 atan(m h /(2(e + b)))、近軸では m h/(e + b) = h/(e + k a)、k = 1 + 2e/R。
    ``flat_equivalent_distance`` = 同じ大きさに見える平面鏡の距離 k a(遠くに見える量)。"""
    op = "convex_mirror_image"
    a = _array(object_distance, "object_distance", op)
    if np.any(a <= 0):
        raise ValueError("%s: object_distance must be > 0" % op)
    R = _positive(radius, "radius", op)
    e = _positive(eye_distance, "eye_distance", op)
    h = _positive(object_size, "object_size", op)
    b = a * R / (2.0 * a + R)
    m = R / (2.0 * a + R)
    k = 1.0 + 2.0 * e / R
    th = 2.0 * np.arctan(m * h / (2.0 * (e + b)))

    def o(x):
        return float(x) if np.ndim(x) == 0 else x
    return {"image_distance": o(b), "magnification": o(m), "angular_size": o(th), "k": k,
            "flat_equivalent_distance": o(k * a)}


def convex_mirror_misjudge(object_distance, speed, radius: float, *, eye_distance: float) -> Dict[str, object]:
    """凸面鏡に映った車の距離と速さを平面鏡のつもりで読んだときの見誤り(近軸の閉形式、配列可)。場面 S064・S130。

    k = 1 + 2e/R。距離(大きさから): â = k a。速さは読み方で 3 つ:
    ``speed_size_consistent`` = k v(大きさの変化を、大きさから読んだ距離と矛盾なく読む → 速く見える)、
    ``speed_size_anchored`` = k v (e + a)²/(e + k a)²(本当の距離 a にある物の大きさの変化として読む → a > e/√k で遅い)、
    ``speed_lateral_anchored`` = v (e + a)/(e + k a)(横切る動きの角の速さを本当の距離で読む → 遅い)。
    ``tau_apparent`` = (e + k a)/(k v)(大きさとその変化率の比 = 見かけの到達時間)、``tau_true`` = a / v。
    遠く見える(k > 1)は読み方によらないが、**遅く見えるのは本当の距離に錨を置いたときだけ** —— 返り値の 3 つで分かる。"""
    op = "convex_mirror_misjudge"
    a = _array(object_distance, "object_distance", op)
    v = _array(speed, "speed", op)
    if np.any(a <= 0) or np.any(v <= 0):
        raise ValueError("%s: object_distance and speed must be > 0" % op)
    R = _positive(radius, "radius", op)
    e = _positive(eye_distance, "eye_distance", op)
    a, v = np.broadcast_arrays(a, v)
    k = 1.0 + 2.0 * e / R

    def o(x):
        return float(x) if np.ndim(x) == 0 else x
    return {"k": k, "distance_apparent": o(k * a), "speed_size_consistent": o(k * v),
            "speed_size_anchored": o(k * v * (e + a) ** 2 / (e + k * a) ** 2),
            "speed_lateral_anchored": o(v * (e + a) / (e + k * a)),
            "tau_apparent": o((e + k * a) / (k * v)), "tau_true": o(a / v),
            "slower_if_anchored_beyond": e / math.sqrt(k)}


def mirror_image_side(eye_xy, mirror_center_xy, mirror_normal_xy, points, *, heading, velocities=None) -> Dict[str, object]:
    """カーブミラーに映る点が、鏡の中心より左右どちらに見えるか・どちらへ動いて見えるか(平面鏡の閉形式)。場面 S064・S130。

    左右の向きは凸面鏡でも同じ(門で光線追跡と照合。凸面は角を縮めるだけ)。

    上から見た 2 次元(x, y)。像 P' = P − 2((P − M)·n)n(``drivedecide.mirror_reflection_matrix`` の 2 次元版)。
    ``image_offset`` = 眼から鏡の中心を見る向きに対する像の向きの角(+ = 左)。``real_side`` = ``heading``(運転者の前)に
    対して物が左(+1)か右(−1)か。``velocities`` を渡すと ``image_motion`` = 像の角の速さ、``direct_motion`` = 眼から物を
    直接見たときの角の速さ(遮りは見ない)、``virtual_eye_motion`` = 仮想の眼 E' から見た角の速さ(= −image_motion が恒等式)、
    ``reversed`` = 像と直接の動きの向きが逆か。"""
    op = "mirror_image_side"
    E = _vec2(eye_xy, "eye_xy", op)
    M = _vec2(mirror_center_xy, "mirror_center_xy", op)
    n = _unit2(mirror_normal_xy, "mirror_normal_xy", op)
    hd = _unit2(heading, "heading", op)
    P = _array(points, "points", op).reshape(-1, 2)
    if float(np.dot(E - M, n)) <= 0:
        raise ValueError("%s: the mirror normal must face the eye" % op)
    if np.any((P - M) @ n <= 0):
        raise ValueError("%s: every point must be in front of the mirror (on the eye's side)" % op)
    Pi = P - 2.0 * ((P - M) @ n)[:, None] * n[None, :]
    c = M - E
    q = Pi - E
    off = np.arctan2(_cross(c[None, :], q), q @ c)
    side = np.sign(_cross(hd[None, :], P - E))
    out = {"image_offset": off, "image_side": np.sign(off), "real_side": side, "image_points": Pi}
    if velocities is not None:
        V = _array(velocities, "velocities", op).reshape(-1, 2)
        if V.shape != P.shape:
            raise ValueError("%s: velocities must match points" % op)
        Vi = V - 2.0 * (V @ n)[:, None] * n[None, :]
        im = _cross(q, Vi) / np.sum(q * q, axis=1)
        dq = P - E
        dm = _cross(dq, V) / np.sum(dq * dq, axis=1)
        Ev = _virtual_eye(E, M, n)
        vq = P - Ev
        vm = _cross(vq, V) / np.sum(vq * vq, axis=1)
        out.update({"image_motion": im, "direct_motion": dm, "virtual_eye_motion": vm,
                    "reversed": np.sign(im) != np.sign(dm)})
    return out


def mirror_road_coverage(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width: float, *, mirror_radius=math.inf,
                         road_point, road_direction) -> Dict[str, object]:
    """カーブミラー(凸面の円弧 or 平面)に映る道の範囲(上から見た 2 次元、閉形式)。場面 S064・S130。

    道 = 直線 Q(λ) = road_point + λ·road_direction(単位にする。λ = 0 を交差点の衝突の点に置くと読みやすい)。鏡の両端
    (円弧なら端の法線 N = cos φ n ± sin φ t、φ = asin(w/2R))で眼からの光線を反射させ、道との交点 λ₁, λ₂ を求める。
    凸面では反射光線の向きが鏡の上の位置に単調なので、映る範囲 = [min λ, max λ]。光線が道に届かなければ(平行・背を向ける)
    その側は ±∞(光線の向きと道の向きの内積の符号)。``blind_near`` = λ = 0 から映る範囲の手前の端までの長さ(0 より奥から
    しか映らないとき、交差点の直前が映らない死角)。``drivedecide.convex_mirror_fov`` と同じ端の光線(眼が軸上なら
    2 本の向きの差 = 全視野角)。"""
    op = "mirror_road_coverage"
    E = _vec2(eye_xy, "eye_xy", op)
    M = _vec2(mirror_center_xy, "mirror_center_xy", op)
    n = _unit2(mirror_normal_xy, "mirror_normal_xy", op)
    w = _positive(mirror_width, "mirror_width", op) / 2.0
    R = math.inf if (isinstance(mirror_radius, float) and math.isinf(mirror_radius) and mirror_radius > 0) \
        else _positive(mirror_radius, "mirror_radius", op)
    if not math.isinf(R) and not w < R:
        raise ValueError("%s: mirror_width/2 must be smaller than mirror_radius" % op)
    Q0 = _vec2(road_point, "road_point", op)
    u = _unit2(road_direction, "road_direction", op)
    if float(np.dot(E - M, n)) <= 0:
        raise ValueError("%s: the mirror normal must face the eye" % op)
    t = np.array([-n[1], n[0]])
    if math.isinf(R):
        pts = [M - w * t, M + w * t]
        nrm = [n, n]
    else:
        phi = math.asin(w / R)
        O = M - R * n
        nrm = [math.cos(phi) * n - math.sin(phi) * t, math.cos(phi) * n + math.sin(phi) * t]
        pts = [O + R * N for N in nrm]
    lams, rays = [], []
    for P, N in zip(pts, nrm):
        d = (P - E) / float(np.linalg.norm(P - E))
        r = d - 2.0 * float(np.dot(d, N)) * N
        rays.append(r)
        A = np.array([[r[0], -u[0]], [r[1], -u[1]]])
        det = float(np.linalg.det(A))
        if abs(det) < 1e-14:
            lams.append(math.copysign(math.inf, float(np.dot(r, u))))
            continue
        s, lam = np.linalg.solve(A, Q0 - P)
        lams.append(float(lam) if s > 0 else math.copysign(math.inf, float(np.dot(r, u))))
    lo, hi = min(lams), max(lams)
    return {"interval": (lo, hi), "edge_lambdas": lams, "edge_rays": np.array(rays), "edge_points": np.array(pts),
            "blind_near": max(0.0, lo) if lo > 0 else 0.0}
