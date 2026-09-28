---
title: '自動運転のデモは動くので、誰も正しさを測らない ―― 定理と第 2 実装で採点する PoC シリーズ'
tags:
  - Python
  - NumPy
  - 自動運転
  - アルゴリズム
  - robotics
public_private: true
public_id: 1f128b8a36df373c11c7
---

> **言語 / Language**: **日本語** · [English](https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c)

# 自動運転のデモは動くので、誰も正しさを測らない ―― 定理と第 2 実装で採点する PoC シリーズ

<!--
  追記手順(ja / en の両方に同じ順で入れる。片方だけ足さない):
    1. 「シリーズの現在地」表に 1 行足す。
    2. 節を 1 つ足す —— 図 → 手順 → 門と成績 → 実装で踏む穴 → 向かないこと → 動かす。
    3. 図は raw.githubusercontent の絶対 URL。更新したら ?v=N を増やす。
    4. 末尾の「次回」を本節に昇格させ、新しい「次回」を置く。
  ★読者の役に立つことだけ書く。開発の経緯・こちらが踏んだ順番・直した履歴は書かない。
-->

![Hybrid A* の道を辿って 2 台の間に入る車](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/04_parking_gif.gif)

*↑ 車(橙)が Hybrid A* の道を辿って 2 台の間に入る。前進 30 区間・後退 12 区間、切替 8 回。**入った**ことは見れば分かる。**この道が下界からどれだけ離れているか**は、見ても分からない。*

## この記事について

車が縦列駐車に入る。車線を見つけて追従する。前の車との距離を保つ。自動運転のデモは**動きます**。そして動くものは、合っているかを誰も確かめません。

経路が最短でなくても車は駐車枡に入ります。衝突までの時間を 2 割多く見積もっても、たいていの場面では止まれます。車線の曲率が 1 割ずれていても、映像の上では線に沿って見えます。**間違いが動きに出ない**——これがこの分野を書くときの難所です。

そこで自動運転のコードを足すときの基準を 3 つに絞りました。

> **(i) 定理が門になるか、(ii) 閉形式の構造を仮定しない第 2 実装が真値になるか、(iii) 公表値(データセットの公式指標)があるか。**
> どれも満たさないものは書かない。**使った式で答え合わせをするのは禁止。**

このシリーズは、その基準で作った op を 1 本ずつ並べます。毎回、動く図と一緒に**成績表**が出ます。学習済みモデルは使いません——numpy と scipy だけで、どの数字も手元で再現できます。コードは [fullseye](https://github.com/furuse-kazufumi/fullseye) にあり、図はすべてスクリプト自身の出力です。

## シリーズの現在地

| 回 | 何を測るか | 門(真値の出どころ) |
|---|---|---|
| 1 | [車は最短でどう曲がるか](#第-1-回-車は最短でどう曲がるか) | Dubins / Reeds–Shepp の定理 / 前進積分 / SLSQP の第 2 実装 / 空の格子で Hybrid A* = 閉形式 |
| 2 | [教習所が開校する —— 真値を持った世界を先に作る](#第-2-回-教習所が開校する--真値を持った世界を先に作る) | 規格寸法の閉形式の面積 / 平面へのレイの閉形式 / 2 センサ 1 世界の恒等式 / 多角形の内外判定の 2 実装 |

---

## 第 1 回: 車は最短でどう曲がるか

### 手順

```
2 つの姿勢 (x, y, θ) → 相対座標に直す → 語ごとの区間長を閉形式で → 各候補を前進積分して終点を検証 → 最短を選ぶ
障害物あり: 占有格子の上で {左・直進・右} × {前進・後退} を A* で繋ぎ、節点から目標へ閉形式の一撃を試す
```

前輪で舵を切る車には**最小回転半径 ρ** があり、それより急には曲がれません。姿勢 (x, y, θ) から姿勢 (x', y', θ') へ移る最短の道は、この制約のもとで**定理として分かっています**。

| 言葉 | かみくだくと |
|---|---|
| Dubins(1957) | 前進だけの車の最短路は「円弧・直線・円弧」の 3 区間で、並べ方(語)は **LSL / RSR / LSR / RSL / RLR / LRL の 6 つ**しかない |
| Reeds–Shepp(1990) | 後退を許すと最短路は高々 5 区間、語は **48**(Sussmann–Tang 1991 で 46 に減る)。区間長は閉形式 |
| 語(word) | 区間の並び。L = 左いっぱい、S = 直進、R = 右いっぱい。**小文字は後退** |
| 占有格子 | 地面を升目に切って「障害物か否か」を置いた画像 |
| Hybrid A*(Dolgov ら 2010) | 連続な姿勢を離散セル (x, y, θ) で枝刈りしながら A* を回す。障害物があるときの実用解 |
| 許容ヒューリスティック | 真の残り費用を**超えない**見積り。障害物を無視した Reeds–Shepp 長がそれ |
| 解析的な一撃 | 探索の途中で「ここから目標まで閉形式の道が衝突せずに通るか」を試すこと。通れば探索は終わる |

op は 3 本です。

- `car_dubins_path(poses, radius)` —— 前進のみ、6 語の閉形式。
- `car_reeds_shepp_path(poses, radius)` —— 後退あり、48 語(OMPL と同じ 44 式)の閉形式。
- `car_hybrid_astar(occupancy, poses, radius, cell, footprint, ...)` —— 占有格子の上の Hybrid A*。車体の矩形か余白、後退・切替・舵の罰則。

閉形式の op は、**候補の一本一本を前進積分して終点に着くかを検証**し、届かない候補は捨てて `n_rejected` に数えます。式の写し間違いは例外ではなく**数に出ます**。

[![Dubins の 6 語](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words.png)

*↑ 同じ 2 姿勢に対する 6 語。この対では 5 語が目標に届き、いちばん短いものが答え。定理は「答えはこの 6 つの中にある」と言っているだけなので、6 つ全部を作って測る。*

### 門と成績

真値に使ったのは**定理・第 2 実装・下界**の 3 種類だけです。学習済みモデルも外部のプランナーも要りません。

| 主張 | 実測 | 真値の出どころ |
|---|---|---|
| 閉形式の候補は全部目標に着く | 乱数 400 対で落ちた候補 **0**、対あたり RS 候補 6.6 本(3〜12) | 前進積分 |
| 48 語の式が全部生きている | **18 の語族**が候補にも最短にも全部現れた | 語族を数える |
| 閉形式は本当に最短 | 3 対 × RS / Dubins の 6 件で第 2 実装と **1e-6** で一致 | 語ごとの区間長を SLSQP で解く(閉形式の構造は仮定しない) |
| 定理の不等式と対称 | 距離 ≤ RS ≤ Dubins、可逆、鏡映、剛体、ρ 比例、三角不等式が 400 対 + 200 組で全部成立 | 定理 |
| 後退が買う分 | Dubins − RS の最大 **10.647 m**(ρ = 1 m) | ― |
| 整列した目標 | Dubins 5.000000 = RS 5.000000、語 S。真後ろ 2 m は RS 2.000000、語 s | 距離が下界 |
| Hybrid A* は閉形式を再現する | 障害物の無い格子で費用 **23.353319 m = RS 23.353319 m**(展開 1、一撃)。前進のみでも Dubins 長と一致 | 閉形式 |
| 縦列駐車 | 費用 **16.018 m ≥ 下界 7.986 m**、展開 3,385、区間 42(後退 12・切替 8)、0.7 秒。姿勢列は車体で衝突せず、\|Δθ\| ≤ Δs/ρ | 下界と運動学 |
| 塞げば拒む | 壁で車室を塞ぐと `ValueError`。部分的な道は返さない | fail-closed |

第 2 実装の中身は、語の 5 区間の長さを未知数 l₁…l₅(符号つき、負 = 後退)にして、終点の 3 つの方程式(x, y, そして角は 2 sin(Δθ/2))を制約に Σ|lᵢ| を最小化するものです。多数の初期値から SLSQP で解いて最小を取ります。**閉形式が何も知らない**実装なので、一致すれば閉形式の写し間違いも語の漏れも同時に否定できます。

[![Reeds–Shepp の 16 目標](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery.png)

*↑ 原点から 16 の目標へ。赤 = 前進、青 = 後退、灰 = 同じ目標への Dubins(前進のみ)。小文字が後退の区間。後退を許すと Dubins より必ず短いか等しい。*

[![縦列駐車の探索木](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree.png)

*↑ 縦列駐車(18 × 8 m、cell 0.25 m、θ 72 分割、車体 4.5 × 1.8 m、ρ 5.5 m、7.5 m の車室)。灰 = 障害物(縁石・駐車車両 2 台)、薄緑の点 = 展開した姿勢、赤 = 前進、青 = 後退。障害物を無視した Reeds–Shepp の道(下界 7.986 m)は駐車車両を突き抜けるので、費用 16.018 m はその 2 倍。差の内訳は「障害物のぶん」と「枝刈りの近似のぶん」で、**この 2 つは分離できません**(後述)。*

### ★ 実装すると、ここで間違える

この筋道を自分で書く人が確実に踏む穴が 4 つあります。どれも**例外は出ず、車はそれらしく走る**ので、門を置かないと気づけません。

#### 1. mod 2π の折り方が違うと、8 つの語が一度も出てこない

Reeds–Shepp の 44 式は OMPL の実装から写すのが普通です。OMPL の `mod2pi` は **(−π, π] に折ります**。これを [0, 2π) に折る実装で写すと、区間長 t の条件 `t ≥ 0` が**常に真**になり、CCSC 系の 8 語(LRSL・LRSR とその対称)が一度も候補に出ません。負の区間長は 2π − |t| の遠回りに化けるので、**答えは出るし、目標にも着きます**——ただ最短ではありません。

これは「候補が目標に着くか」の門では見つかりません。着いているからです。**語族を数える門**——48 語を 18 の族に分け、乱数の姿勢で各族が候補にも最短にも現れることを要求する——で初めて出ます。乱数 400 対で 8 族が 0 回なら、式が死んでいます。

#### 2. 終点方程式を 4 本立てると、最適化器は収束しない

第 2 実装で終点の一致を「x、y、cos θ、sin θ」の 4 式にすると、未知数 5 に対して制約が実質 3 なのに 4 本あるので**過剰決定**になり、SLSQP は実行不能か inf を返します。角の一致は **1 本**——`2 sin((θ_end − θ_goal) / 2)`——で書いてください。sin と cos の両方を等式にしてはいけません。

#### 3. 衝突判定が時間の 8 割を食う

Hybrid A* の素朴な実装は、縦列駐車 1 回に数十秒かかります。プロファイルを取ると**衝突判定が 8 割**です。効くのは 3 つで、(a) 車体の矩形を標本点にして格子座標へ一括変換し、平坦な索引 `flat[iy·W + ix]` で引く、(b) 解析的な一撃は候補全部ではなく**最短候補だけ**を衝突判定する、(c) 一撃の頻度を目標に近いほど上げる(残り費用 h に対して ⌈h / step⌉ 回に 1 回)。この 3 つで **37 秒が 1 秒**になります。順番は (a) が先——(b)(c) は正しさを変えないぶん、効き目が測りにくいからです。

#### 4. 「到達不能」が正しい答えのことがある

離散化は答えを変えます。車長 + 2.0 m の 6.5 m の車室は、cell 0.25 m・θ 72 分割では**到達不能**でした。7.5 m なら入ります。また 12 × 8 m の狭い格子で前進のみ(Dubins)の道を求めると、最短路が**格子の外へ出る**ので到達不能が正解です。どちらも op は `ValueError` を投げます。部分的な道を返して「惜しかった」を装うより、拒んだほうが後段は安全です。**空の格子で閉形式と厳密一致する**門を持っていれば、到達不能が離散化のせいか実装のせいかを切り分けられます。

### 向かないこと

**動く障害物と速度は扱いません。** ここにあるのは幾何(どの道か)だけで、いつ・どの速さで走るかは別の層です。歩行者や対向車がいる場面の計画は、この op の上に時間軸を足す別の道具になります。

**Hybrid A* は最適ではありません。** 離散セルでの枝刈りが近似を入れるので、縦列駐車の 16.018 m が「障害物のもとでの最短」である保証はありません。下界 7.986 m との差 8 m のうち、障害物のぶんと近似のぶんは分離できません。言えるのは「下界以上・衝突なし・運動学的に実現可能」の 3 つだけで、成績表もそう書いてあります。

**曲率は連続ではありません。** Dubins も Reeds–Shepp も区間の境で舵を瞬時に切り替えます。実車ではクロソイド(曲率が線形に変わる曲線)で繋ぐ CC-steer や、後段の平滑化が要ります。

**大きな格子は遅いです。** 純 Python の heapq なので、100 × 100 m を cell 0.1 m で回す用途には向きません。研究の真値・小さな駐車場・教材の範囲です。

### 動かす

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_car_parking.py            # 門 7 本と図 5 枚、約 16 秒
```

```python
import numpy as np
import fullseye as fs

poses = np.array([[0.0, 0.0, 0.0],            # 始点 (x, y, θ)
                  [4.0, 3.0, np.pi / 2]])     # 目標
rs = fs.ledger.car_reeds_shepp_path(poses, radius=1.0)
print(rs["word"], round(rs["length"], 4), rs["n_candidates"], rs["n_rejected"])
# LSL 5.1763 9 0     ← 語、長さ [m]、生き残った候補、積分で落ちた候補(0 でなければ式を疑う)

occ = np.zeros((32, 72), bool)                # 8 × 18 m、cell 0.25 m
occ[:2, :] = True                              # 縁石
res = fs.ledger.car_hybrid_astar(occ, np.array([[2.0, 4.2, 0.0], [7.5, 1.5, 0.0]]),
                                 radius=5.5, cell=0.25, footprint=(4.5, 1.8, 1.0))
print(res["cost"], ">=", res["lower_bound"], res["n_expanded"])
```

`n_rejected` は必ず見てください。0 でない値が出たら、それは自分の姿勢が悪いのではなく**式のどこかが死んでいる**知らせです。

---

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_car_parking)

#### この回の残りの図

[![真値の散布](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths.png)

*↑ 真値 11 件の突き合わせ。第 2 実装 6 件、整列 3 件、空の格子 2 件。全部が対角線の上に乗る。*

## 第 2 回: 教習所が開校する —— 真値を持った世界を先に作る

![幹線で赤信号を待ち、クランクを抜けて周回コースへ合流する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/05_drive_gif.gif)

*↑ 追走カメラの画像に LiDAR(16 ビーム)の点を重ねる。灰 = 路面、黄 = 縁石、赤 = 車、緑 = 信号機。信号待ち → 交差点 → クランク(切り返しあり)→ 連絡路 → 周回コース。**車が走った**ことは見れば分かる。**その道が縁石線から何 cm 出たか、LiDAR の点がどの面から来たか**は見ても分からない——世界の側に真値があるから数えられる。*

第 1 回は道の幾何だけで、センサが無かった。センサを採点するには、**何を見たかが最初から決まっている世界**が要る。実写データセットの真値は人手のラベルで、箱の縁も点のラベルも人の判断だ。そこでこの回は世界を作る側に回った——ただし勝手な寸法ではなく、**道路交通法施行規則 別表第三(指定自動車教習所のコースの基準、普通免許)** の数字で。

### 手順

```
規格の寸法 → 課題ごとの多角形(クランク・S 字・坂道・縦列駐車・方向変換・踏切・周回・幹線) → (x, y, yaw) で配置 → 走れる領域の和
       → 3-D の世界: 路面の平面 + 縁石の帯 + 白線 + CC0 の車・信号機・標識(面ごとにラベルと色)
       → 回転式 LiDAR をメッシュに撃つ(点・range 画像・面のラベル) / 車載カメラで撮る(色・ラベル・深度)
       → 13 巡目の Hybrid A* で走らせ、全姿勢・全コマで採点する
```

| 用語 | ここでの意味 |
|---|---|
| 周回コース | 長円形。直線 80 m 以上・幅 8 m 以上。教習所の外周で、課題はこの内側にある |
| 幹線コース | 幅 7 m 以上の道が十字に交差し、周回と繋がる。すみ切り半径 3 m 以上 |
| 屈折コース(クランク) | 幅 3.5 m、曲角間 12 m、出入口 4 m 以上、内側のすみ切り 1 m(普通免許) |
| 曲線コース(S 字) | 幅 3.5 m、半径 7.5 m(外側の弧)、弧の長さは円周の 3/8 が 2 つ逆向きに |
| 方向変換 | 幅 3.5 m の道の脇に幅 3.5 m・奥行 5 m の車庫、すみ切り 1 m |
| 坂道 | 幅 7 m 以上、高さ 1.5 m 以上、緩坂 6.5〜9 %・急坂 10〜12.5 %、頂上の平坦部 4 m 以上 |
| レンジ画像 | LiDAR の一掃を 行 = 仰角(ビーム)、列 = 方位角 の格子にしたもの。画素値は距離 |
| 逆センサーモデル | 「この距離で反射が返った」から格子の各セルの占有を更新する規則(今回は縁石の点を落とすだけ) |

新しい op は 3 つのモジュールに分かれます。**drivecourse**(規格寸法の 2-D 多角形。真値は閉形式の面積)、**driveworld**(3-D の世界。CC0 の Kenney Car Kit / City Kit Roads を実寸に合わせて置く。カメラ像は三角形 id から色とラベルを引く)、**lidarsim**(Möller–Trumbore のレイ–三角形交差を、センサから見た各三角形の方位角・仰角の区間でビン分けして加速。8 万三角形 × 5.8 万レイで 1 秒未満)。

[![教習所の平面](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan.png)

*↑ 真上から。周回(直線 80 m・幅 8 m・半円 R 30)の中に幹線の十字(信号 4 基)。北東にクランク、南西に S 字、南東に坂道(暗い部分が斜面)、北西に縦列駐車と方向変換、東の幹線に踏切。課題の出口は連絡路で周回へ戻るので、ぐるぐる回れる。*

[![同じ世界を斜めから](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique.png)

*↑ 3-D の世界。縁石(高さ 0.15 m)と白線は多角形の縁に沿って生成し、継ぎ目には置かない。車・信号機・標識・街灯・コーンは CC0 のメッシュ。面ごとにラベルと色を持つ。*

### 門と成績

真値は**規格の寸法から導いた閉形式・平面と箱へのレイの閉形式・同じ世界を見る 2 つのセンサの恒等式**の 3 種類。学習済みモデルも外部のシミュレータも要りません。

| 主張 | 実測 | 真値の出どころ |
|---|---|---|
| 多角形は規格の寸法どおり | 弧のある 5 要素の靴紐面積は、弧の点数 16 → 64 → 256 → 1024 で閉形式へ**単調収束**(クランク 3.1e-5 → 7.5e-9、S 字 2.8e-3 → 6.8e-7)。弧の無い 4 要素は**厳密一致** | 閉形式(クランク = w·L + 2r²(1 − π/4)、S 字 = 2·(3/8)·π·(7.5² − 4²) + 出入口、半円 = π R w) |
| LiDAR は平面を正しく測る | 平らな路面に当たった **10,903 点**の range が h/(−sin e) と相対差 **2.1e-16** | 閉形式 |
| 2 つのセンサは同じ世界を見ている | LiDAR の 3,450 点をカメラに投影した画素の深度と点の深度: 相対差の中央値 **2.9e-3**、ラベル一致 **100 %**(1 画素の許容。ぴったりなら 99.1 %) | 恒等式 |
| 車の点は車の中 | ラベル「車」の 1,607 点が、置いた車の箱(姿勢 + 実寸)の内側 **100 %** | 世界の側の配置 |
| 縁石の点は道の外 | 縁石の 4,667 点から作った占有格子は、真の占有(多角形の外)の 1 セル膨張の部分集合(precision **1.0000**)。走行 68 コマ全部で 1.0000 | 多角形の内外判定(偶奇と巻き数の 2 実装) |
| 走った道は脱輪していない | 997 姿勢で車体 4 隅の縁石線からの越え幅は最大 **0.117 m ≤ 半セル 0.125 m**。厳密な多角形では 11 姿勢が越える(計画器の分解能) | 多角形 |
| ゼロ点 | クランクの入口→出口を直線で進むと 60 姿勢中 **50** で脱輪 | ― |
| カメラは信号を読む | 灯火 160 画素の点いた画素の色で 赤 → `red`、緑 → `green`。灯火を消すと `unknown` | 世界の側の状態 |

[![LiDAR の一掃](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep.png)

*↑ 停止線の 10 m 手前での一掃(32 ビーム、−25°〜+15°、0.5°、10,903 点が路面)。点は当たった面のラベルで塗ってある——これが人手のラベルでなく生成時の真値であることが、この世界の値打ち。*

[![車載カメラに LiDAR を重ねる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar.png)

*↑ 同じ瞬間の車載カメラ(60°、640 × 400)に LiDAR の点を投影して重ねた。点の深度と画素の深度、点のラベルと画素のラベルが一致することが「2 センサ 1 世界」の門。信号は赤。*

### ★ 実装すると、ここで間違える

#### 1. 規格の幅 3.5 m は、最大舵角と直進だけでは前進で通らない

第 1 回の Hybrid A* は {左・直進・右} × {前進・後退} の運動基本形です。4.5 × 1.8 m の車で規格のクランク(幅 3.5 m、すみ切り 1 m)を**前進のみ**で通そうとすると、格子 0.25 m・θ 72 分割でも、0.125 m・144 分割でも**到達不能**——探索は数十回の展開で open set を使い切ります。S 字(外側 7.5 m・内側 4 m)も同じです。後退を許すと通ります(クランク 費用 57.9 m・後退 14 区間、S 字 29.5 m・後退 1 区間)。実際の検定でも切り返しは許され、回数で減点されます。**中間の舵角を持つ基本形**が無いと、規格ぎりぎりの道は幾何的には通れても離散化では通れない——これは「動いたから合っている」の反対で、**動かなかったが間違っていない**例です。

#### 2. 計画器が「衝突なし」と言っても、多角形では 12 cm 出ている

衝突判定はセル(0.25 m)単位です。厳密な多角形で測ると 997 姿勢のうち 11 で車体の隅が縁石線を越え、最大 0.117 m でした。半セル以内なので計画器の約束どおりですが、**「衝突なし」の意味は分解能の分だけ緩い**。門は「半セル以内」に置き、越えた姿勢の数と最大幅を出しています。縁石に当てたくなければ clearance を足すか、格子を細かくするかで、どちらも時間を払います。

#### 3. 要素を辺で接すると、継ぎ目に縁石の壁が立つ

周回の直線と半円を辺どうしでぴったり接すると、それぞれの端の辺は「隣の要素の内側」ではないので縁石が生成され、**道を横切る壁**になります。LiDAR がそれを見て、走れるはずのセルに縁石の点が落ちました(precision 0.90)。直し方は 2 つ: 隣り合う要素を 5 cm 重ねる、そして縁の小片(0.5 m)は**両端と中点のどれかが隣の内側なら置かない**。中点だけ見ると、口に半分かかった小片が壁になります。

#### 4. 灯火は柱の頭の箱の中に埋まる

信号機のメッシュは頭部が箱で、灯火の円盤を頭の中心の少し手前に置くと箱の面に隠れて**カメラに 0 画素**でした。前面より外へ出すと 160 画素。もう 1 つ、点いた灯火 1 つと消えた灯火 2 つの**平均色**で判定すると、消えた 2 つの暗さが支配して緑が読めません。点いている画素(最大チャネル > 0.5)だけで判定します。

#### 5. 細い物は 1 画素ずれると別の面に落ちる

縁石は高さ 0.15 m、20 m 先では 2 画素の帯です。LiDAR の点をカメラに投影して**同じ画素**のラベルを見ると 99.1 % で、外れの大半は縁石の点が隣の路面の画素に落ちたもの。3 × 3 の窓に同じラベルがあれば一致とすると 100 %。白線(幅 0.12 m)は遠くで 1 画素未満なので、路面と同じ面として数えます。「ラベル一致 100 %」と書くとき、**許容が何画素か**を一緒に書かないと意味がありません。

#### 6. 巨大な三角形はカメラの背後で消える

路面を 2 枚の巨大な三角形にすると、車載カメラの像から路面ごと消えます。描画器はカメラの背後に頂点を持つ三角形を落とすからです(近クリップをしない設計)。4 m の格子に割ると、消えるのはカメラの真下の升だけになります。LiDAR 側にも似た罠があり、三角形の仰角の区間を頂点の最小・最大で取ると、**センサの真上を通る辺**の途中の仰角を取りこぼします(頂点 5.7° の辺の途中が 78.7°)。辺ごとに大円弧上の極値を足す必要がありました。

### 向かないこと

**動く物と時間は扱いません。** 世界は静止していて、車は姿勢列を辿るだけです。対向車の速度も歩行者もいません。信号は色が変わるだけで、変わる規則はありません。

**センサの物理は幾何だけです。** LiDAR は単一反射で、反射強度・ビームの広がり・雨や霧・回転中の自車の動きによる歪みはありません。カメラは Lambert の陰影だけで、影も露出も無い。「この検出器は実車で動く」の証拠にはならず、**幾何の間違いを見つける**道具です。

**車のメッシュは玩具の比率です。** Kenney の CC0 モデルを箱の寸法(車長 4.5 m・車幅 1.8 m)に軸ごとに引き伸ばしています。点群の形は本物の車と違います。

**縦列駐車の寸法は法令にありません。** 通達の別添は図で、数値の一次情報が取れなかったので、車長 + 3.0 m を既定にして docstring にそう書いてあります。

### 動かす

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_driving_school.py         # 門 14 本と図 6 枚、約 37 秒
```

```python
import numpy as np
import fullseye as fs

crank = fs.ledger.course_crank()                                  # 規格: 幅 3.5, 曲角間 12, 出入口 4, すみ切り 1
P = crank["polygon"]                                             # 反時計回りの多角形 (K, 2)
area = 0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))   # 靴紐
print(crank["params"]["regulation"], round(area, 3), round(crank["area_closed_form"], 3))
# {'A': 3.5, 'B': 12.0, 'C': 4.0, 'D': 1.0} 82.682 82.679

world = fs.ledger.world_build(crank, props=[("sedan", 20.0, 2.0, np.pi / 2)])   # 3-D 化して車を 1 台置く
spec = fs.ledger.lidar_spec(n_beams=16, azimuth_res_deg=1.0)
T = np.eye(4); T[:3, 3] = (2.0, 0.0, 1.64)                        # 入口の中、センサ高 1.64 m
scan = fs.ledger.lidar_scan(world["V"], world["F"], spec, T, labels=world["face_label"])
hit = scan["ranges"] > 0
print(scan["n_hits"], np.bincount(scan["labels"][hit]))
# 2641 [2455  140   22    0    0    0    0    0    0   24]   ← 点の数、面のラベル別(路面 2455・縁石 140・車 22・…・白線 24)
```

`labels` は当たった面のラベルです。**生成時の真値**なので、検出器を書いたらこれと突き合わせれば、人手のラベルを待たずに採点できます。

---

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_school)

#### この回の残りの図

[![真値の散布](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths.png)

*↑ 8 種の要素の面積(靴紐 vs 閉形式)と路面の range 200 点(実測 vs h/(−sin e))。全部が対角線の上。*

---

## 次回

**光学流から衝突までの時間、そして安全距離。** 正面から近づく平面では、衝突までの時間 τ は流れの発散だけで決まります(Lee 1976、TTC = 2 / 発散)——距離も速度も知らずに。この回で開校した教習所の世界に対向車を走らせ、車載カメラの 2 コマから光学流を取り、**真の TTC が分かる**接近で採点します。合わせて Mobileye の RSS(Shalev-Shwartz ら 2017)の安全距離の閉形式(Lemma 2)を、応答時間・加速度・減速度の公表値で確かめます。

## 出典

- L. E. Dubins, "On curves of minimal length with a constraint on average curvature, and with prescribed initial and terminal positions and tangents", *Amer. J. Math.* 79, 1957。
- J. A. Reeds and L. A. Shepp, "Optimal paths for a car that goes both forwards and backwards", *Pacific J. Math.* 145, 1990。
- H. J. Sussmann and G. Tang, "Shortest paths for the Reeds–Shepp car: a worked out example of the use of geometric techniques in nonlinear optimal control", *Rutgers SYCON 91-10*, 1991。
- A. M. Shkel and V. Lumelsky, "Classification of the Dubins set", *Robotics and Autonomous Systems* 34, 2001。
- D. Dolgov, S. Thrun, M. Montemerlo, J. Diebel, "Path planning for autonomous vehicles in unknown semi-structured environments", *Int. J. Robotics Research* 29, 2010。
- Reeds–Shepp の 44 式の並べ方は OMPL(`ReedsSheppStateSpace`)に従った。
