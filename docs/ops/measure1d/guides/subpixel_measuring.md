---
guide: subpixel_measuring
dim: measure1d
title: サブピクセル計測(測定線と計測モデル) — 使い方ガイド
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
---

# サブピクセル計測(測定線と計測モデル) — 使い方ガイド

## この族は何をする道具箱か

**画像のどこを、どの向きに見るかを先に決めてから測る**層です。14 op / 3 カテゴリ:

- **caliper(6)** — `gen_measure_rectangle2` / `gen_measure_arc` /
  `translate_measure` / `measure_pos` / `measure_pairs` /
  `fuzzy_measure_pairing`: 測定線に沿ってエッジをサブピクセルで取り、対にして幅を出す。
- **model(6)** — `create_metrology_model` と `add_metrology_object_*` 5 本:
  直線・円・矩形・楕円をモデルに登録する。
- **apply(2)** — `align_metrology_model` / `apply_metrology_model`:
  モデルを画像へ当てて、当てはめ結果をまとめて返す。

## なぜ台帳に載せたか —— 見えていなかったから、ただし測ってから

2026-09-06、この 2 モジュールが**公開経路のどこからも呼べない**ことが分かりました
(`fs.` / `fs.ledger.` / `fs.op.` のいずれからも **0/14**)。

同じ日に、同じく埋もれていた `mosaic` を実測したところ `bundle_adjust_mosaic` が
36 枚中 30 枚を単位行列で返す(束調整ではない)ことが分かったので、
**出す前に実地で測る**方針を取りました(`examples/poc_dimensional_inspection.py`)。

結果は **14/14 が動作**。ゼロ点(大津の整数幅)比 **41 倍**で、スロット幅
50.50 px の偏りは −0.5000 → **−0.0113 px**、合成不確かさ u_c = 0.0196 px
= 0.245 µm。`mosaic` とは違い、これは出す価値がありました。

## 全体の流れ

```mermaid
flowchart LR
    A["gen_measure_rectangle2<br/>直線の測定線"] --> C["measure_pos<br/>サブピクセルのエッジ位置"]
    B["gen_measure_arc<br/>円弧の測定線"] --> C
    A --> D["measure_pairs<br/>対にして幅を出す"]
    B --> D
    D --> E["fuzzy_measure_pairing<br/>想定幅に近い対を優先"]
    A --> F["translate_measure<br/>測定線を平行移動"]
    G["create_metrology_model"] --> H["add_metrology_object_*<br/>直線 円 矩形 楕円"]
    H --> I["align_metrology_model<br/>位置合わせ"]
    I --> J["apply_metrology_model<br/>まとめて当てはめ"]
```

## いちばん短い例

```python
import numpy as np
import measuring1d as M

img = np.zeros((64, 128)); img[:, 40:80] = 1.0        # 真値 40.0 px の帯
meas = M.gen_measure_rectangle2(row=32.0, col=64.0, phi=0.0,
                                length1=50.0, length2=3.0, shape=img.shape)
pairs = M.measure_pairs(img, meas, sigma=1.0, threshold=0.1)
print(pairs[0]["width"])       # 40.0000
```

## 落とし穴 5 つ(どれも実測つき)

### 1. 斜めの測定線に cos 補正は入っていない

測定線が輪郭に対して斜めだと、測定値 / 真値がちょうど 1/cos になります
(70 度で 2.9105 対 2.9238)。**呼ぶ側が cos を掛けてください**。掛ければ
60 度まで 0.04 px 以内、70 度で −0.139 px 残ります。

### 2. エッジが近いと幅は必ず大きく出る。しかも失敗を返さない

壊れるのは「ぼけ」そのものではなく **エッジ間距離 / PSF 幅**です:

| w / σ | 幅の偏り |
|---|---|
| 3.09 | 0.05 px を超え始める |
| 2.06 | **+2.43 px** |
| 1.58 | それでも「対が見つかった」と 100 % 答える |

対が互いを押し広げるので**必ず大きい側**へ偏ります。`measure_pairs` は
信頼度を返さないので、危険域かどうかは呼ぶ側が見張るしかありません。

### 3. 縁の定義を宣言しないと 16 px 動く

面取りや丸みのある実際の縁では「どこがエッジか」が定義依存です。実測:

| 縁の形 | 測定値 |
|---|---|
| 面取り 5 px | 90.35(底面幅側) |
| 面取り 6 px | **78.61(上面幅側)** |
| 丸み 8 px | 上面幅 74.50 / 底面幅 90.50 / 50 % 交差 87.55 |

面取りが PSF に対して分解できた瞬間、答えが**黙って 11.7 px 飛びます**。
定義の違いで **16 px = 200 µm** —— サブピクセルの 3 桁上です。

**丸い縁は必ず小さく出ます**。直径誤差 ≈ −σ²/ρ で、実測 / 予測は 1.24 / 1.09
/ 1.02(ρ=8、σ=0.8/1.2/2.0)、0.94(ρ=16)。円弧キャリパーの −0.311 px は
この光学側の偏りで説明でき、**道具自体はほぼ偏りません**。

### 4. `measure_pairs` は極性の順序を問わない

docstring は「立ち上がり→立ち下がり」と読めますが、実装は**極性が交互なら
順序を問いません**。円弧測定では「立ち下がり→立ち上がり」= 暗い穴を対に
します。**明るい構造の幅を期待して呼ぶと暗い構造の幅が返ることがあります**。
選ぶ引数(`transition`)がまだありません。

### 5. `metrology` の矩形は往復しない

`add` は (phi, l1, l2) を受けますが、`apply` は l1 ≥ l2 に正規化して返します。
l1 < l2 で入れると phi が 90 度回ります(実測: 入力 phi=0 / l1=25.25 /
l2=55.00 → 出力 phi=−90.00 / l1=55.020 / l2=25.256)。

矩形の当てはめは**最小面積外接矩形**(凸包の極値点のみ)なので、60 点中
1 点を 1.5 px 外へ動かすだけで幅が **+1.50 px** 動きます(最小二乗なら
0.050 px)。ただし rms が 0.022 → 0.734 に上がるので、**rms を必ずゲートに
してください**。

## 窓の置き方が精度より効く

外形幅を測る列がボルト穴を踏むと 220.45 → **186.75**(−33.75 px)。
エラーも警告も出ません。サブピクセルの議論より前に、測定線がどこを通るかです。

## 関連

- `examples/poc_dimensional_inspection.py` —— この族を実地評価した PoC。
- `docs/ops/roughness/guides/surface_roughness.md` —— 面の粗さ(こちらは寸法)。
- `docs/ops/profile/guides/profile_metrology.md` —— 1-D 断面の形状計測。
