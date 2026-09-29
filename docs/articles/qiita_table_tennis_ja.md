---
title: '卓球の球は跳ねるので、物理を知らない追跡は着地点を 20 cm 外す ―― 跳ねと摩擦を映像から測る PoC シリーズ'
tags:
  - Python
  - NumPy
  - 物理
  - 画像処理
  - robotics
public_private: true
public_id: b6498dc822bf9eed100f
---

> **言語 / Language**: **日本語** · [English](https://qiita.com/furuse-kazufumi/items/a82bf9f341cc4f04ca75)

# 卓球の球は跳ねるので、物理を知らない追跡は着地点を 20 cm 外す ―― 跳ねと摩擦を映像から測る PoC シリーズ

<!--
  追記手順(ja / en の両方に同じ順で入れる。片方だけ足さない):
    1. 「シリーズの現在地」表に 1 行足す。
    2. 節を 1 つ足す —— 図 → 手順 → 門と成績 → 実装で踏む穴 → 向かないこと → 動かす。
    3. 図は raw.githubusercontent の絶対 URL。更新したら ?v=N を増やす。
    4. 末尾の「次回」を本節に昇格させ、新しい「次回」を置く。
  ★読者の役に立つことだけ書く。開発の経緯・こちらが踏んだ順番・直した履歴は書かない。
-->

![2 本のラケットの送り合い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)

*↑ 自由に動く 2 本のラケット(赤・青)が、相手のコートで 1 度跳ねた球を運動方程式で狙って返す。最初の 3 秒を 1/5 速で。**続いた**ことは見れば分かる。この記事の主役は、ラリーの**本数**が知覚・予測・制御の成績表になっていることです。*

## この記事について

卓球の球は 2.7 g で、時速 100 km 近くで飛び、台で跳ね、毎分 3,000 回転で回ります。空気の抵抗で減速し、回転のせいで曲がり(マグヌス力)、台に当たると回転が跳ね返り方を変えます。放物線で追う追跡器は、跳ねる前までは合っていて、跳ねた後の着地点を **20 cm** 外します。

ロボット卓球の先行研究は、複数の高速カメラで球を三角測量し、抵抗とマグヌスを入れた運動方程式で跳ねを越えて予測し、模様から回転を測ります。この記事は、その一式を **numpy だけ**で作り、それぞれの段に**真値つきの門**を立てたものです。

> **(i) 定理が門になるか、(ii) 閉形式の構造を仮定しない第 2 実装が真値になるか、(iii) 公表値(規格・測定値)があるか。**
> どれも満たさないものは書かない。**使った式で答え合わせをするのは禁止。**

自動運転のシリーズ([こちら](https://qiita.com/furuse-kazufumi/items/1f128b8a36df373c11c7))と同じ基準です。違うのは題材が「跳ねる・滑る・回る」で、摩擦係数と反発係数が主役になること。けん玉(ひもと皿)も同じ道具で扱えるので、この系列で続けます。

## シリーズの現在地

| 回 | 何を測るか | 門(真値の出どころ) |
|---|---|---|
| 1 | [球は跳ねる —— 追跡・三角測量・跳ねを越える予測・スピン・ラリー](#第-1-回-球は跳ねる--追跡三角測量跳ねを越える予測スピンラリー) | 真空の閉形式 / 接触点まわりの角運動量保存 / 頂点の等比 e^{2k}h₀ / ITTF の跳ねの規格 / 真値を持った世界 / ラリーの本数 |

---

## 第 1 回: 球は跳ねる —— 追跡・三角測量・跳ねを越える予測・スピン・ラリー

### 手順

```
力学   : 抗力(Re 依存の球の経験式)+ マグヌス(スピン比)+ スピン減衰 + 速度依存の反発係数 + クーロン摩擦の跳ね(掴む / 滑る)を RK4 で
世界   : ITTF の台(2.74 × 1.525 m、高さ 0.76 m、ネット 15.25 cm)と 40 mm の球(黒い模様 14 個)を真値つきで描く。追跡カメラ 2 台 + 跳ね際の近接カメラ 1 台
映像   : 色度で球を検出(サブピクセル)→ 等速予測で追跡 → DLT で三角測量 → 等加速度 Kalman
予測   : z の局所最小で跳ねを検出 → 跳ねる前の 15 コマから運動方程式の 6 パラメータを Gauss–Newton で当て、跳ねを越えて着地点を読む
測る   : 前後 12 コマの当てはめから反発係数 e、近接カメラの模様の対応(Kabsch)から角速度
ラリー : 2 本のラケットが相手コートで 1 度跳ねた球を面で迎え、狙った点へ返す。打つ前に先読みして外すなら巻き戻す。本数が指標
```

**かみ砕き**: 球の動きを決める式は 3 つです。**抗力**(速いほど強く減速する)、**マグヌス力**(回転と進行方向の外積の向きに曲がる)、**跳ね**(台に当たると鉛直の速さが e 倍で返り、水平は摩擦で削られ回転が変わる)。追跡はカメラの像で球を見つけて 3 次元に戻す作業、予測は式を積分する作業、測定はその逆問題です。

[![追跡カメラ 1 のコマ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view.png)

*↑ 追跡カメラ 1 のコマ(t = 0.15 s)。球は像で半径 4 px しかない。十字は世界の側が持っている真値の投影。*

### 門と成績

| # | 門 | 真値 | 成績 |
|---|---|---|---|
| 1 | 真空の恒等式 | 閉形式 | RK4 と閉形式の差 1e-12、放物線の当てはめで g = 9.81 が 4e-15 で戻る |
| 2 | 跳ねの定理 | 接触点まわりの角運動量保存 | 乱数 500 通り(e ∈ [0.3, 1]、μ ∈ [0, 0.6])で相対誤差 最大 4.9e-16、エネルギーは増えない、転がりに移る 136 / 滑ったまま 364 |
| 3 | 頂点の等比と ITTF の跳ね | e^{2k}h₀ と規格 24〜26 cm | 30.5 cm から落として頂点 24.7 / 20.0 / 16.2 / 13.1 cm、閉形式との差 3e-7。総時間 4.736 s(閉形式 4.738 s) |
| 4 | 検出 | 世界の真値の投影 | 122 / 122 コマ、中心の誤差 中央値 **0.15 px**(像の半径 4.3 px) |
| 5 | 三角測量 | 世界の真値 | 真値の投影から 4e-15 m、検出から 中央値 **1.6 mm** |
| 6 | Kalman | 放物線の真値 | 新息 最大 8e-9 m(抗力とマグヌス入りの真値だと 2e-3 m = モデルの外)、速度の誤差 中央値 0.07 m/s |
| 7 | 跳ねの検出 | 世界の接触時刻 | 差 **0.6 ms**(1 コマ = 10 ms) |
| 8 | 跳ねを越える予測 | 世界の着地点 | 真のスピンを知っていれば **0.4 cm**、スピンを無視すると **20.2 cm**、放物線だと 6.6 cm |
| 9 | スピン | 世界の角速度 | 模様が対応づいたコマ組 19 / 19、\|ω\| 2394 rpm の相対誤差 **3.7 %** |
| 10 | 反発係数 | 世界の e = 0.90 | 運動方程式の当てはめで **0.911**。放物線の当てはめだと 0.940(抗力とマグヌスを g に吸う) |
| 11 | ラリーの本数 | 上限・攻めの有無・知覚の雑音 | 送り合い 12 本(上限)、攻め vs 送り 9 本(out)、知覚の雑音 0 / 50 / 100 mm → 8 / 8 / 2 本 |

[![x–z 面の軌跡](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz.png)

*↑ 検出から三角測量した点(誤差の中央値 1.6 mm)は真値に乗る。跳ねる前の 15 コマから当てた初期状態で先を読むと、2291 rpm のトップスピンを知っていれば着地点は 0.4 cm、スピンを無視すると 20.2 cm 外れる。*

**門 11 の読み方(この記事の主張)**。ラリーの本数は、検出・三角測量・予測・打ち方・ラケットの移動の**全部が同時に**合っているときだけ伸びます。どこか 1 段が壊れると本数に出る。だから 1 つの数で採点できます。片方を「勝つ打ち方」(遠い隅を速く)にすると 9 本で終わり、両方を「前回に近い、少しずらした位置へ返す」にすると上限まで続く。知覚に 5 cm の雑音を足しても本数は減らず、10 cm で 2 本に落ちる。減らない区間は板(15 × 16 cm)の余裕です —— 板の半分より小さい誤差は本数に出ない。これは指標の分解能でもあります。

**巻き戻し**。打つ前に真の物理で先読みして、ネット・自陣で跳ねる・届かない高さ、のどれかなら**時間を戻してやり直す**(回数を数える)。攻める側で 99 回巻き戻しても 9 本で終わるのは、計画器の式(閉形式の狙い + 反復)と世界の物理(Re 依存の抗力・スピン比の揚力)のずれが、速い球ほど効くからです。巻き戻しの回数は**計画器と物理のずれの量**として読めます。

### ★ 実装すると、ここで間違える

#### 1. Kalman の門を「本物の軌跡」で立てると、Kalman が壊れているように見える

等加速度 Kalman は放物線には厳密です(新息 1e-9 m)。抗力とマグヌスが入った軌跡を入れると新息が 2e-3 m 出ますが、それはモデルの外にいるだけで、フィルタの欠陥ではありません。門は放物線で立て、実物の軌跡には「予測は運動方程式で」と役割を分けます。

#### 2. 放物線で当てると、反発係数が 4 % ずれる

跳ねの前後を放物線で当てて v_z を出すと、抗力とマグヌスが重力に吸われて e = 0.940(真値 0.90)。運動方程式で当てると 0.911。着地点も放物線だと 6.6 cm、運動方程式だと 0.4 cm。**当てる式は予測する式と同じにする**。

#### 3. 模様が 1 つでは回転が決まらない

1 つの模様の向きが分かっても、その軸まわりの回転は見えません。2 つ以上の模様が同じコマ組で見えて初めて Kabsch(2 組の向きから回転を最小二乗で出す)が立ちます。6 方向だけの模様だと見えるのは 2〜3 個で、暗い縁と混ざって 1 個に落ちるコマが出る。14 個(6 軸 + 8 隅)にして、近接カメラはストロボ照明(陰影を弱く)にすると 19 / 19 のコマ組で対応がつきます。

#### 4. 動くラケットの跳ねは、相対速度で計算する

ラケットは面が動くので、球の速度をそのまま跳ねの式に入れると間違えます。面の速度を引いて跳ねさせ、また足す。狙いの逆算(閉形式)も同じで、n ∝ v_out − v_in、v_r·n = |Δv| / (1 + e) + v_in·n。

#### 5. 上限つきの移動は、最後の 1 歩で加速度を超える

bang-bang(全力で加速し、間に合うところで全力で減速)を離散時間で回すと、止まる直前の 1 歩で加速度の上限を超えます。止まる速さを max(0, √(2ad) − a·dt) にして、離散の 1 歩ぶんの余裕を取る。

#### 6. 跳ねは無限に続く(Zeno)

頂点は e^{2k}h₀ で、跳ねの間隔は等比で縮み、総時間 √(2h₀/g)(1 + e)/(1 − e) の中に**無限回**の接触が入ります。接触時の鉛直の速さが閾値を切ったら台に置く、と決めないと積分は止まりません。

#### 7. 法線が零だと、黙って NaN が全部に広がる

正規化の分母が零のとき、例外を出さずに NaN を返すと、ラリーの残り全部が NaN のまま「続いた」ことになります。fail-closed(ValueError)にして、門は NaN を通しません。

### 向かないこと

**本物の映像はまだ入れていません。** カメラ・台・球は真値を持った合成世界です。検出器(色度)は照明の陰影には強いですが、背景に同じ色度の物があるとそちらを拾います。実写は次回以降の題材です。

**抗力係数と揚力係数の既定値は文献値です。** 測定値ではありません。同定の op(fit_aero: 軌跡から C_d・C_L を Gauss–Newton で当てる、真値で 1e-15 で戻る)はありますが、本物の球で回してはいません。

**ラリーの計画器は、世界の物理を知っています。** 巻き戻しは「真の物理で先読み」なので、実機ではそのままは使えません。実機では予測器(運動方程式の当てはめ)を先読みに使うことになり、巻き戻しは「予測器の言うことと実際のずれ」に化けます。

**回転の測定は模様が要ります。** 無地の球では Kabsch は立ちません。継ぎ目やロゴを使う方法は別の op です。

### 動かす

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_ball_bounce.py            # 門 11 本と図 8 枚(GIF 2)、約 110 秒
```

```python
import numpy as np
import fullseye as fs

bp = fs.ledger.ball_params()                      # 40 mm・2.7 g、抗力 0.4、揚力はスピン比から
ip = fs.ledger.impact_params(0.90, 0.25)          # 反発係数 e、摩擦係数 μ
tp = fs.ledger.table_params()                     # ITTF: 2.74 × 1.525 m、高さ 0.76 m

# トップスピンの打球を台の上で飛ばす(台は z = 0.76、範囲は台の面)
r = fs.ledger.flight_simulate([-1.3, 0.0, 1.0], [5.2, -0.3, 0.6], [0.0, 240.0, 0.0], bp, ip,
                              t_end=0.8, table_z=tp["height"], table_xy=(-1.37, 1.37, -0.7625, 0.7625))
c = r["contacts"][0]
print(round(c["t"], 4), np.round(c["p"][:2], 3), c["regime"], np.round(c["omega_out"], 1))
# 0.2495 [-0.095 -0.07 ] grip [  7.8 228.8   0. ]     ← 接触時刻 [s]、点 [m]、掴んだか滑ったか、跳ねた後の角速度 [rad/s]

# 30.5 cm から落とす: 頂点の等比と ITTF の規格(最初の跳ね 24〜26 cm)
h = fs.ledger.apex_sequence(0.305, 0.90, 4)              # h₀ と、その後の頂点 4 つ
print(np.round(100 * h, 1))
# [30.5 24.7 20.  16.2 13.1]

# 2 本のラケットで 12 本まで打ち合う(送り合い)
rp = fs.ledger.racket_params()
from racket import strategy_feeder, strategy_attacker
res = fs.ledger.rally_simulate(bp, rp, tp, strategies=(strategy_feeder, strategy_feeder), retries=0, max_hits=12, seed=1, table_ip=ip)
print(res["hits"], res["end_reason"], res["rewinds"])
# 12 max_hits 0
```

`end_reason` が `out` / `net` / `double_bounce` / `unreachable` のどれで終わったかを見てください。攻める側にすると 9 本で `out` になります。本数が減ったら、それは球の運動が変わったか、知覚か、計画器か —— 巻き戻しの回数と合わせて読むと、どの段かが絞れます。

---

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ball_bounce)

#### この回の残りの図

![追跡カメラの GIF](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)

*↑ 追跡カメラ 1、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。*

[![頂点の等比](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes.png)

*↑ 30.5 cm から落とした球(e = 0.90)の頂点。閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。*

[![スピンのコマ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames.png)

*↑ 跳ね際の近接カメラ(1000 fps、20°)の 4 コマ。黒い模様(14 個のうち 4〜6 個が見える)の向きを前のコマと対応づけ、Kabsch で回転を当てる。*

[![像での軌跡](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d.png)

*↑ カメラ 1 の像での球の軌跡。真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。*

[![雑音と本数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise.png)

*↑ 知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本)。5 cm までは減らず、10 cm で 2 本。減らない区間は板の余裕。*

---

## 次回

けん玉。ひもは**片側だけの拘束**(張力は正、たるめば自由落下、張ったときの径方向の速さは失われる)で、皿の捕球は幾何の判定です。同じ跳ね・摩擦の道具で、玉が皿に乗るまでを真値つきで採点します。その先で、本物の映像(高速カメラ 1 台)から反発係数と摩擦係数を測ります。
