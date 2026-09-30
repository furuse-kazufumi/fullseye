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
| 2 | [けん玉 —— 糸は引くだけ、玉は放物線、皿は画像の予測で運ぶ](#第-2-回-けん玉--糸は引くだけ玉は放物線皿は画像の予測で運ぶ) | 楕円積分と周期の定理 / 張力と弛む角の閉形式 / 日本けん玉協会の寸法 / 真値を持った世界 / 3DGS の投影と合成の式 |
| 3 | [回転で曲がる球を撮って、回転を 2 通りで読む —— 曲がり方から / 模様から](#第-3-回-回転で曲がる球を撮って回転を-2-通りで読む--曲がり方から--模様から) | ω × v の定理(進行方向の回転は力を生まない)/ 真値を持った世界 / 独立な 2 つの読み(軌跡と模様)の一致 |

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

## 第 2 回: けん玉 —— 糸は引くだけ、玉は放物線、皿は画像の予測で運ぶ

![3DGS の世界で大皿に受ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)

*↑ 右 = 閉ループの知覚が実際に見た画像(世界を 3D Gaussian Splatting にして描いたもの)、左 = 同じ瞬間の真の形。右上の窓はけん玉のまわりを 3 倍の解像度で描き直したもの。青の輪 = 色度で検出した玉、十字 = 糸が弛んだ後のコマに当てた放物線から読んだ着地点。皿を動かす根拠は右の画像だけです。*

### けん玉の基本の動き

日本けん玉協会の級の技のうち、玉を真上に引き上げて皿で受ける 4 つを扱います。

| 技 | 持ち方 | 受ける皿 |
|---|---|---|
| 大皿 | 皿持ち(けん先は斜め下、大皿が上) | 大皿 |
| 小皿 | 同じ持ち方 | 小皿 |
| 中皿 | けん持ち(けん先をほぼ真下) | 中皿 |
| ろうそく | けん先をつまむ | 中皿 |

手本の手順は共通です: 膝で真上に引き上げる → **糸が弛んでからけんを動かす** → 落ちてくる所の真下へ皿を水平に運ぶ(すくいに行かない)→ 着地で膝を曲げて衝撃を吸う。この PoC はこの手順をそのまま制御の段階にしました。

約束は 4 つです。**(1)** 玉を動かすのは重力と糸の張力だけ(張力 ≥ 0 の片側拘束)。**(2)** けんと皿胴は 1 つの剛体で、位置は自由に動かしてよい。**(3)** 玉は糸が弛んだ後に昇り、頂点を越えて下りてくるところを受ける(真上の軌道も放物線と見なす)。**(4)** けん先は玉の穴にだけ使う —— 皿の技でけん先や皿胴に玉が触れたら失敗です。

### 手順

```
形     : 日本けん玉協会の公表値(玉 60 mm・横幅 70 mm・全長 180 mm)と JKA 16-2 型の説明(けん 160 mm、皿 42 / 38 / 35 mm)で、
         けんと皿胴を回転体に。玉は穴(直径 17 mm・深さ 40 mm のくぼみ)ごと回転体
力学   : 糸 = 張力 ≥ 0 の片側拘束(弛めば自由落下、張った瞬間に径方向の速さを失う)を射影法で。空気抵抗つき
世界   : 2 台のカメラ(480 × 360、100 fps)。真値を持った合成世界。さらに 3D Gaussian Splatting にしてから描く
知覚   : 色度で玉を検出 → 2 台で三角測量 → 玉と糸穴の距離が糸より短いコマが 2 回続いたら「弛んだ」→ 重力つきの放物線(未知 6)を当てる
制御   : lift(膝で真上に)→ wait(弛むまで動かさない)→ hold(玉がけんを越えるまで寄せない)→ carry(皿を着地点の真下へ水平に)
         → absorb(着地で下げる)
採点   : 縁に触れた瞬間に 横ずれ ≤ 縁の半径・相対速さ ≤ 1 m/s・下降中。けんに触れたら hit_ken(失敗)
```

**かみ砕き**: 糸は押せません。引くことしかできない「片側の拘束」です。だから玉を真上に強く引き上げると、ある瞬間に糸が弛み、そこから玉は放物線で飛びます。放物線は重力だけで決まるので、弛んだ後の数コマの位置が分かれば、どこに落ちてくるかが計算できます。皿はそこへ先回りして待てばよい。人が「玉をよく見て、落ちてくる所で待つ」とやっていることを、画像と放物線でやります。

[![4 技の持ち方](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup.png)

*↑ 4 技の持ち方の姿勢。けんと皿胴は 1 つの剛体で、持つ所だけが違う。寸法は頂点から測って公表値と 1e-9 で一致する。*

### 門と成績

| # | 門 | 真値 | 成績 |
|---|---|---|---|
| 1 | 楕円積分と大振幅振り子の周期 | 公表値 K(0.5) と定理 T = 4√(L/g)K(sin θ₀/2) | K の誤差 0、周期はひも 3.0e-4・棒 8.9e-11 |
| 2 | 張力と弛む角 | 閉形式 m(v²/L + g cos θ)、cos θ_s = (2/3) cos θ₀ | 張力 0.26 %、弛む角 125.04°(閉形式 125.26°) |
| 3 | エネルギーと snap | 飛翔中は保存、張った瞬間の損失 = ½ m v_r² | 飛翔中の幅 2.5e-15 J、snap 0.2362 J vs 0.2367 J、散逸は dt に 1 次(比 9.7) |
| 4 | 形 | 公表値(横幅 70・けん 160・皿 42/38/35・玉 60・全長 180 mm) | すべて 1e-9 |
| 5 | 真値の知覚で大皿 | 段階の順・けんに触れない・弛んだ後に昇って下降中に受ける | 横ずれ 4.22 mm で捕る。手元を逃がさないと 0.260 s に皿胴に当たる |
| 6 | 検出 → 三角測量 → 弛み | 世界の真値 | 誤差 中央値 **0.51 mm**、弛みの検出は真値より +23 ms |
| 7 | 画像だけの閉ループ | 真値の知覚との成功率 | 20 試行で真値 1.00 / 画像 **1.00**(計画に渡った推定 390 回は全部画像から) |
| 8 | 同じ計画で 3 技 + ろうそく | 飛び方とけんとの接触 | 小皿 1.00、中皿 0.95、ろうそく(真値)0.95。着地で下げると相対速さ 0.91 → 0.61 m/s |
| 9 | 予測誤差 | 捕球の瞬間の玉の位置 | 弛んだ後 3 → 44 コマで **10.51 → 0.98 mm** |
| 10 | 画素雑音 | 成功率 | 0〜2 px で 1.00、8 px 0.90、16 px 0.40 |
| 11 | 穴の向き(静止した玉) | 真の穴の軸 | 40 姿勢中 14 で 2 台に見え、誤差 中央値 **1.8°** |
| 12 | 推奨品(大皿 49 mm) | JKA 型の成功率 | 1.00 vs 1.00 |
| 13 | **3DGS の世界で閉ループ** | 真値の知覚 | 間隔 4 mm の 3DGS の画像だけで 1 + 2 試行すべて捕る、三角測量の誤差 中央値 **0.30 mm** |
| 14 | 3DGS のつまみ | 検出率 | 間隔 2〜64 mm で 1.00、位置の誤差 20 mm で 0.25、色の誤差 0.3 で 0.00 |
| 15 | 3DGS の上の穴 | 真の穴の軸 | 480 × 360 では 40 姿勢中 1、解像度 × 2・間隔 2 mm で 16(中央値 2.3°)、間隔 4 mm では 0 |
| 16 | **連続技 10 回**(もしかめ・3 皿) | 放つ頂点 v²/2g、けん玉に触れない、昇ってから下降中 | 画像だけで両方 **10 回連続**(5 級相当)、相対速さ 0.41〜0.48 m/s |

[![y–z 面の軌跡](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz.png)

*↑ 玉は糸が弛んでから昇り、皿は玉がけんを越えるまで待ってから水平に戻り、着地の直前に下がって受ける。点は 2 台の三角測量。*

**門 9 の読み方**。弛んだ直後の 3 コマで当てた放物線は、捕球の瞬間の位置を 1 cm 外します。短い区間の速度に三角測量の誤差が乗るからです。コマが増えるほど誤差は減り、44 コマで 1 mm を切る。皿は毎コマ新しい予測へ運び直すので、最初の予測が外れていても間に合います —— 大皿の縁の半径は 21 mm、それが「待てる」余裕です。門 10 で画素雑音 2 px まで成功率が落ちないのも同じ余裕で、落ちないあいだも横ずれは 2.4 → 4.1 mm と増えています。

### 3DGS にしてから認識する

合成世界のメッシュをそのまま描くと、画像は「きれいすぎ」ます。実際のシーンを 3D Gaussian Splatting(3DGS)で再構成すると、形はぼけ、位置にも色にも誤差が乗ります。そこで、**世界を 3DGS にしてから描き、同じ画像処理にかける**層を足しました(`gsplatnp`、numpy だけ)。

```
ガウシアン : 世界の面に貼る(面の番号 + 重心座標 + 面の局所座標での誤差を固定で持つ)。頂点が動けば付いて動く
大きさ     : σ = 間隔(3DGS の初期値と同じ)。曲面からはみ出さない σ ≤ 0.5 R、角(皿の縁・穴の口)に接する面は 1/4
描画       : EWA 投影 Σ' = J W Σ Wᵀ Jᵀ + 0.3 I、手前から α 合成、Mip-Splatting の不透明度の補正
つまみ     : 間隔(密度)・位置の誤差・色の誤差
```

[![メッシュと 3DGS](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/08_gs_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/08_gs_views.png)

*↑ 同じ近接カメラで、メッシュと 3DGS(間隔 2 mm・16 mm・誤差つき)。粗いと滲み、誤差を載せると毛羽立って色がにじむ。*

描画の門は 3 つの式です: 1 個のガウシアンの α 像の 2 次モーメントが Σ' と一致する(別の投影で 3 次元の標本を写した共分散とも)、2 個重なった画素の色が手前からの合成の式どおり(並び順を変えても同じ像)、世界を剛体で動かすとガウシアンが同じ変換で動く。

結果は表の 13〜15 です。玉を追う分には 3DGS でもほとんど困りません —— 間隔を 64 mm まで粗くしても玉の検出率は 1.00 のまま(曲率の上限で玉の上には 146 個以上が残る)。崩すのは**位置の誤差**と**色の誤差**です。色度で検出する以上、色の誤差が検出器の許容(0.12)を越えれば見えなくなる。穴は違います。

| 穴を読めた姿勢(40 中) | メッシュ | 3DGS 間隔 2 mm | 3DGS 間隔 4 mm |
|---|---|---|---|
| 480 × 360 | 14 | 1 | — |
| 解像度 × 2 | 23 | 16(誤差 中央値 2.3°) | 0 |

480 × 360 だと玉は 17 px、穴は 5 px です。3DGS のぼけ(1 px ほど)が両側から入って、穴が塗りつぶされる。**穴を読むには玉に画素が要り、穴の中にガウシアンが要る**。とめけん(けん先を穴に入れる技)をやるなら、カメラをこの表の右下より良い側に置く必要があります。

### 続けて別の皿で受ける(連続技)

受けたら、その状態から続けて別の皿で受けます。協会の級の技の**もしかめ**(大皿と中皿を交互に)と、大皿 → 小皿 → 中皿 の 3 皿の連続です。

```
放つ     : 玉が乗った皿を上へ加速し、g より強く止める → 皿が玉より速く減速した瞬間に玉が離れる(頂点 = 離れた瞬間の v²/2g)
持ち替え : 飛んでいる間に けんと皿胴(1 つの剛体)を回して次の皿を上に(手首 ≤ 30 rad/s、仮定)
受ける   : 次の皿を着地点の真下へ運び、落ちてくる玉と同じ向きに皿を動かして速さを合わせる(位置と速度を目標にする手元の制御)
知覚     : 皿からの「飛び始め」も画像から(皿の受け位置から 12 mm 離れたコマが 2 回続いたら)→ 放物線 → 次の皿
```

![連続技の玉の高さ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/11_combo_height.png)

*↑ もしかめ 10 回連続の玉の高さ(画像だけの閉ループ)。放物線で昇って下りてくるところを、持ち替えた次の皿で受ける。受けた後に少し沈むのは、皿を玉と同じ向きに動かして速さを合わせた分(膝のクッション)。*

画像だけで もしかめも 3 皿も **10 回連続**(協会のもしかめの級で 5 級相当)、着地の相対速さは 0.41〜0.48 m/s です。**位置だけを目標にする手元の制御では、頂点を皿の 20 cm 上にすると 1 回も受けられません** —— 皿が目標の位置で止まろうとするので、1.9 m/s で落ちてくる玉に速さを合わせられない。人の「膝で受ける」は、速度を合わせる制御です。

正直に書くと、雑音が無いと 100 回続いても同じ 1 周期の繰り返しで(放つ動きは閉形式で決まり、玉は真上に上がる)、回数は頑健さの証拠になりません。画素雑音 2 px を足すと もしかめ 3 回・3 皿 6 回で崩れます(着地の直前に当て直すたびに目標が揺れる)。

### ★ 実装すると、ここで間違える

#### 1. 知覚を足しても、それが制御の入力になっていないことがある

画像から三角測量して放物線を当てる部品を作っても、皿を動かす計画には世界の真値 (p, v) を渡したまま、ということが起きます。予測は「採点」にしか使われず、閉ループは画像を見ていない。門は「計画に渡った推定の回数 = 画像から出た推定の回数」で立てます(表の 7 と 13)。

#### 2. 糸は 109.47° より上では張っていられない

静止から放した振り子の周期の門を「ひもで 120°」にすると落ちます。θ₀ > 90° では最初から張力が負で、真下から打ち出しても cos θ_s = (2/3) cos θ₀ の角で弛む。大振幅の周期は棒で測り、ひもには弛む角の門を立てます。

#### 3. 手元を逃がさないと、真下から昇る玉は皿胴に当たる

真上に引き上げると、玉はけん玉の真下から昇ってきます。そのままだと皿胴を突き抜ける(物理は衝突を解かないので、黙って通る)。玉とけん玉の隙間を毎 step 測って失敗に数え、振り上げの後半で手元を糸穴の側へ 10 cm 逃がします。逆側へ逃がすと、カメラからけんが玉を隠して予測が悪くなりました。

#### 4. 「弛んだ」を 1 コマで決めると、張っている間に誤検出する

玉と糸穴の距離が糸より短い、を 1 コマで判定すると、画素雑音 2 px で張っている間に「弛んだ」と出ます。2 コマ続いたら、にします。

#### 5. 穴を「表面に貼った暗い円盤」にすると、3DGS では消える

メッシュでは円盤でも穴に見えます。3DGS はガウシアンを中心の深さで並べて重ねるので、斜めから見ると手前の玉のガウシアンが 0.3 mm 浮いた円盤を覆い、40 姿勢中 0 回しか読めませんでした。本物どおり深さ 40 mm のくぼみ(暗い壁と底)にします。

#### 6. 画素より細いガウシアンは、補正しないと太る

抗エイリアスのために 2 次元の共分散へ 0.3 px² を足すと、画素より細いガウシアン(糸・皿の縁)が不透明のまま 0.55 px 以上に太ります(糸が 3 画素の太さで写った)。足したぶんだけ不透明度を √(det Σ / det(Σ + 0.3 I)) 倍にする(Mip-Splatting)と、α の総和が保たれます(門にした)。

### 向かないこと

**本物の映像ではありません。** 真値を持った合成世界です。3DGS も写真から学習したものではなく、真の形から作って誤差のつまみで崩したものです。「3DGS の表現と描画の上で画像処理が動くか」を測る道具で、再構成の質そのものは主張しません。

**玉の回転は解いていません。** 張っている間は糸穴が結び目を向き、弛んだら最後の姿勢のまま、という描画の約束です。飛んでいる間の穴の向きは真値ではなく、とめけんはまだ入れていません。

**捕球は幾何の判定です。** 縁での跳ねと転がりは扱わず、相対速さ ≤ 1 m/s は仮定の閾値です。皿持ちの傾き 15°、皿の深さ、玉 75 g も仮定。JKA 16-2 型の寸法はユーザーが提供した説明で、一次資料は未確認です。

**ろうそくが中皿より難しい理由は表せません。** けんを剛体・並進だけで動かすので、つまんだ指の支えの弱さが入らず、数字は中皿と同じ相対運動になります。

### 動かす

```bash
py -3.11 examples/poc_kendama.py            # 門 16 本(図なしで約 171 秒)
```

```python
import numpy as np
import fullseye as fs

kp = fs.ledger.kendama_params(trick="ozara")          # JKA 16-2 型、大皿(皿持ち)
print(round(np.degrees(fs.ledger.tether_slack_angle(np.radians(150.0), kp["pendulum_length"])), 2))
# 125.26                                               ← 真下から 150° 相当で打ち出すと、この角で糸が弛む

w = fs.ledger.kendama_world(kp)                       # 真値を持った世界(けん・皿胴・玉・糸)
gs = fs.ledger.gs_from_world(w, spacing=0.004)        # 世界を 3DGS に(間隔 4 mm)
rig = fs.ledger.kendama_rig(kp)                       # 2 台のカメラ
c = rig[0]
img = fs.ledger.gs_render(gs, c["pose"], c["K"], c["width"], c["height"])["color"]
print(img.shape)
# (360, 480, 3)
```

`kendama_params` の `trick` を `"kozara"` / `"chuzara"` / `"rousoku"` にすると、同じ計画のまま持ち方だけが変わります。`camera_perceiver(world, rig, render_fn=fs.ledger.gs_render_fn(gs))` にすると、閉ループの知覚が 3DGS の画像を見ます。

---

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_kendama)

#### この回の残りの図

![メッシュの世界で大皿に受ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)

*↑ メッシュの世界の画像だけの閉ループ(カメラ 2、100 fps を 1/10 速)。十字は予測した着地点。*

![予測誤差とコマ数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/06_prediction_error_vs_frames.png)

*↑ 弛んだ後の n コマで当てた放物線から読んだ、捕球の瞬間の位置の誤差(縦軸は log10 mm)。*

![3DGS のつまみ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs.png)

*↑ 3DGS のつまみと玉の検出率。間隔は効かず、位置と色の誤差が効く。*

[![張力の閉形式](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form.png)

*↑ 積分器の張力と閉形式 m(v²/L + g cos θ)。0 になった角で糸が弛む。*

[![画素雑音と成功率](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise.png)

*↑ 画素雑音と成功率(20 試行ずつ)。2 px まで平らなのは皿の縁の余裕。*

[![カメラのコマ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view.png)

*↑ カメラ 2 のコマ(玉が頂点)。左の枠は同じカメラで 3 倍の解像度に描き直した窓。*

---

## 第 3 回: 回転で曲がる球を撮って、回転を 2 通りで読む —— 曲がり方から / 模様から

![横から見た 3 本](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)

*↑ 同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から。トップスピン(橙)は沈んで手前に、無回転(黄)は真ん中に、バックスピン(青)は浮いて奥に落ちます。違うのは回転(150 rad/s ≈ 1,430 rpm)だけ。球は見やすさのため 1.6 倍で描いています。240 fps の全コマの動画(1/8 スロー)は [MP4](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.mp4)。*

回転している球には、進む向きと回転軸の両方に垂直な力(マグヌス力、ω × v の向き)がかかります。前回転なら下向き、下回転なら上向き、横回転なら横向きです。だから**軌跡の曲がり方には回転が書いてある**。一方で球の表面の模様は、回転そのものを直接見せます。この回は同じ打球の回転を、この 2 つの独立な手がかりで読み、互いに照合します。

### 手順

1. 回転だけ違う 4 本(トップ・無回転・バック・横)を、台を挟んだ 2 台のカメラ(240 fps、1024 × 800)で撮る。
2. 色で球を見つけて三角測量し、3-D の軌跡にする。高速カメラの ROI 読み出しと同じく、前 2 コマの等速予測の周り 160 × 160 px だけを読みます(見失ったら全画面)。
3. **曲がり方から**: 跳ねる前の軌跡に、抗力 + マグヌスの運動方程式を**位置・速度・回転の 9 パラメータ**で当てる(`fit_spin`)。
4. **模様から**: 同じ打球を近接カメラ(1000 fps、20 コマ)で撮り、黒い模様(14 個)の向きの動きを Kabsch で当てる(`spin_from_markers`)。
5. 2 つを照合し、読んだ回転で着地点を先読みして真値と比べる。

![上から見た横回転](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)

*↑ 上から。横回転(紫)は無回転(黄)と同じ打ち出しから 15 cm 横に逸れて落ちます。[MP4](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.mp4)*

![近接カメラの模様](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)

*↑ 近接カメラ(1000 fps)のトップスピン、20 ms を 1/100 スローで。見えている 4〜6 個の模様を前のコマと向きで対応づけ、回転を当てます。[MP4](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.mp4)*

### 門と成績

| 門 | 真値の出どころ | 成績 |
|---|---|---|
| 恒等式 | 真値の軌跡を `fit_spin` に入れる | 回転が 1.3 × 10⁻⁴ rad/s で戻る |
| 読めない成分 | 定理: ω × v なので、進行方向に平行な回転は力を生まない | 瞬間の加速度の差 4.8 × 10⁻¹⁷ m/s²。0.25 s 飛んでも 7.1 mm(垂直な回転なら 5.4 cm) |
| 着地点 | 真値を持った世界 | 読んだ回転で先読みした着地点が 4 本とも 2 cm 以内(x = 0.488 / 0.754 / 1.124 m、順はトップ < 無回転 < バック) |
| 曲がり方から回転 | 同上 | 垂直成分の誤差 トップ 3.9 %・バック 0.9 %・横 1.7 %、無回転は 7.6 rad/s |
| 模様から回転 | 同上 | トップ 4.8 %・バック 3.2 %・横 0.9 %、無回転は 2.0 rad/s |
| 2 通りの一致 | 第 2 実装(片方は軌跡だけ、片方は模様だけを見る) | 3.0 %・3.1 %・1.9 % |
| 長さの効き | 同上 | 使う軌跡が 42 ms だと 400 %、321 ms で 4 % |

![2 通りの読み](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings.png)

*↑ 2 通りの読みの比較。曲がり方からは進行方向に平行な成分が読めないので、垂直成分で比べています。*

![長さの効き](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length.png)

*↑ 曲がりが見えるまで、回転は読めない。先頭 n コマだけで読むと、短いうちは曲がり(マグヌスの分)が三角測量の誤差 1〜2 mm に埋もれます。*

### 実装で踏む穴

- **進行方向を軸にした回転は、曲がり方からは読めない。** マグヌス力は ω × v なので、ω の v に平行な成分は力を生みません。無回転の球で当てはめが出した 22 rad/s の回転も、ほとんどがこの向きでした。`fit_spin` は読める成分を `omega_perp` として別に返します。模様からは全成分が読めるので、ここが 2 つの手がかりの役割分担になります。
- **回転の大きさが決まらないことがある。** 揚力係数の模型 C_L = 1/(2 + 1/S)(S = rω/v)は回転が大きいと 0.5 で頭打ちになります。軌跡が短く雑音が勝つと、当てはめは「もっと強い力を」と |ω| を際限なく大きくします(減衰の無い Gauss–Newton だと 1 歩で 10⁷ rad/s に飛びます)。`fit_spin` は減衰つきで当て、上限(既定 1,000 rad/s)に張り付いたら `at_bound = True` を返します —— そのときは大きさを信じないでください。
- **ネットが球を半分隠す。** 打つ側のカメラからは、ネットの向こうで低く飛ぶ球の上半分がネットの白帯に隠れます。色の重心が見えている下半分へ寄り、三角測量で最大 26 mm ずれました。像の半径が前後の 0.8 倍未満の検出は捨てています。
- **画面を横切る球では、視線の変化が回転に見える。** 球の像を円板とみなし、中心からの距離で模様の向きを出す式は、球が光軸の上にあるときにしか正しくありません。0.6 m 先を 6 m/s で横切る球は 1 ms で視線が 0.01 rad 回り、1 コマの回転(0.15 rad)に 7 % が上乗せされます。`marker_direction(..., K)` とカメラの K を渡すと、模様の画素の視線を球面と交差させる透視の厳密な式で解きます。

### 向かないこと

- 空力の模型(C_d = 0.4、スピン比の C_L)は真値を作った式と同じです。曲がり方から回転を読む手は、模型が正しいことを前提にしています。実測の C_L はスピン比 0.5 付近に谷があるという報告もあります(Miyazaki ら 2017)。実物ではまず C_L を測る必要があります。
- 回転は飛行中一定としています(減衰なし)。
- 球の検出は色が分かっている合成映像です。実写の照明・ぼけ・背景はありません。近接カメラは、球が視野に入る 20 ms だけの都合のよい配置です。

### 動かす

```python
import numpy as np
import fullseye as fs

bp = fs.ledger.ball_params()                               # 40 mm・2.7 g、抗力 0.4、揚力はスピン比から
t = np.arange(0.0, 0.30, 1 / 240)                          # 240 fps で 0.3 s
f = fs.ledger.flight_ode([-1.3, 0.0, 1.01], [6.0, 0.0, 1.3], [0.0, 150.0, 0.0], bp, 0.31, 1e-4)
p = np.column_stack([np.interp(t, f["t"], f["p"][:, k]) for k in range(3)])
p_obs = p + np.random.default_rng(0).normal(0.0, 1.5e-3, p.shape)     # 三角測量の誤差 1.5 mm 相当

r = fs.ledger.fit_spin(t, p_obs, bp)
print(np.round(r["omega"], 1), np.round(r["omega_perp"], 1), r["at_bound"])
# [ 16.5 157.8  -5.1] [  1.5 157.7  -8.4] False      ← 回転 [rad/s]、読める成分、上限に張り付いたか

r10 = fs.ledger.fit_spin(t[:15], p_obs[:15], bp)          # 先頭 62 ms だけ
print(np.round(r10["omega_perp"], 1), r10["at_bound"])
# [ -1.8 -93.8   8.1] True                            ← 短いと読めない(上限に張り付く)
```

PoC 全体は `py -3.11 examples/poc_table_tennis_spin.py`(図と動画は `FULLSEYE_FIGURE_DIR` を設定したとき)。

---

## 次回

**跳ねと摩擦を映像から測り、公表値と照合する。** 台の上で跳ねる球を高速カメラ 1 台で撮り、反発係数 e と摩擦係数 μ を画像から出します。真値の出どころは公表値: ITTF のルールの台の跳ね(30 cm から落として約 23 cm)、台の上の反発係数と摩擦係数の実測(Inaba ら 2017、打ち込む速さへの依存つき)、薄い殻の球が跳ねで「転がりに移るか滑ったままか」の境目の閉形式(Cross 2002)。その先で、とめけん(けん先を玉の穴に入れる技)に戻ります。
