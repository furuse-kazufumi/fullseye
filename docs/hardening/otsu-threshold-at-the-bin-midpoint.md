---
id: otsu-threshold-at-the-bin-midpoint
date: 2026-09-25
found_by: line_handshake
kind: silent-wrong
severity: high
where: [ops.py, accel.py, detect.py, fscript.py]
ops: [otsu]
gate: [test_a_flat_plate_gives_exactly_the_bright_box, test_the_three_implementations_of_otsu_agree, test_the_gpu_port_agrees_with_the_core_op, test_the_threshold_is_equivariant_under_an_affine_map, test_the_midpoint_spelling_is_what_the_gate_catches, test_segment_objects_sees_one_box_not_one_frame, test_the_fscript_builtin_agrees_with_the_core_op]
status: fixed
---

# 大津のしきい値をビンの**中点**で取るので、背景の山を含むビンの画素が前景に入る

## 症状

値が 2 種類しかない板(背景 0.30・明部 0.90、20x20 = 400 px)で、`fullseye.apply(im, "otsu")` が **4,096 px 全部を前景**にする(期待 400)。例外も警告も出ない。

独立の 2 実装と突き合わせた(2026-09-25 実測):

| 実装 | しきい値 | 前景 |
|---|---|---|
| skimage `threshold_otsu` | 0.301172 | **400** |
| OpenCV `THRESH_OTSU` | 76/255 = 0.2980 | **400** |
| fullseye `otsu` | (ビン 76 の中点) 0.2988 | **4,096** |

同じ絵を 0.00 / 1.00 で作ると **400 で正しい**。つまり「値が 2 種類だから」ではなく、**背景の値がビンの境界のどちら側に落ちるか**で答えが変わる。雑音を載せた現実的な板でも **902 px**(真値 900)と 2 px 漏れる。

## 原因

`ops.py` の実装は 256 ビンのヒストグラムでクラス間分散を最大化したあと、

```python
return (x > mids[int(np.argmax(sb))]).astype(np.float64)
```

と **argmax ビンの中点**でしきい値を取る。ところが argmax が指すのは**背景の山を含むビン**である(そのビンから上では ω が動かないので、分散が同値で並ぶ先頭が選ばれる)。中点はそのビンの**内側**なので、同じビンに居る背景画素の一部(または全部)が `>` を満たしてしまう。背景が 0.30 のときはビン 76 = [0.296875, 0.300781) の中点 0.298828 < 0.30 で、**背景が丸ごと前景側に入る**。

これは、同じ関数の中に既に書かれている原則に反する:

> 大津のしきい値はアフィン変換に等変であるべきなので、これは仕様ではなく穴。

{0,1} を {0.3,0.9} にアフィン変換しただけで答えが 400 から 4,096 に変わっている。

## なぜ門が通したか

★**試験の入力に必ず雑音が載っていた。** 雑音があると背景が多数のビンに散らばるので、argmax ビンの中点が背景の大半より上に来て「だいたい合う」(902 対 900)。`feedback_random_test_data_hides_structural_defects` の型そのもので、**構造のある入力を 1 本混ぜていれば出ていた**。この一件は、接続層のサンプル(`line_handshake`)が「合成の板」を素直に平らに作ったことで出た。

## 同じ欠陥が 4 か所にあった

★直しに入って分かったこと —— **同じ式を 4 か所に別々に書いてあり、4 つとも中点で切っていた**。

| 面 | 誰が踏むか | 書き方 |
|---|---|---|
| `ops.py` `_otsu` | `fullseye.apply(im, "otsu")` / パイプラインの中核 op | `mids[k]` |
| `accel.py` `_otsu` | GPU 常駐経路(「core の逐語移植」と書いてある。**誤りも逐語だった**) | `mids[k]` |
| `detect.py` `_otsu_mask` | `segment_objects()` —— 利用者が最初に踏む高水準 API | `mids[k]` |
| `fscript.py` `_b_binary_threshold` | FScript の組み込み `binary_threshold` | **`(k + 0.5) / 256`** |

3 面目がいちばん質が悪い。平らな板を `segment_objects` に渡すと、画像全体が 1 つの
連結成分になり「面積 4,096、重心は画像中心」という**もっともらしい記録が 1 件**返る。
例外も警告も無いので、数を見ている人には「対象が 1 個見つかった」としか読めない。

★**4 面目は綴りで探しても出てこなかった。** `mids[` を grep して 3 面を直し、念のため
「同じ問いに答える入口」を数え直したところ、FScript が中点を `(k + 0.5) / 256` と
**別の書き方で**持っていた。欠陥を綴りで数えると、綴りが違う面だけが残る
(`feedback_a_fix_leaves_the_twin_surface_open` / `feedback_search_all_tiers_before_declaring_a_gap`)。

## 直し(2026-09-26 適用)

しきい値を argmax ビンの**上端**(`edges[k+1]`)で取り、`x >= t` を前景とする。
argmax ビンの画素は全部背景側に落ちるので、skimage / OpenCV と一致する。4 面とも直した。

**分ける山が無い入力は、ビン格子に決めさせない。** 定数画像は占有ビンが 1 つで、
そもそもしきい値が定義できない。ここで素朴に `edges[1]` を使うと、`[0,1]` の中では
docstring の約束(「0 なら背景、0 より大きければ前景」)が保たれる一方、範囲外の定数
(例 5.0)は背景に落ちて**約束が入力の範囲によって変わる**。占有ビンが 1 つのときは
`x > 0` と明示した —— 直す前は 5.0 の定数が背景、0.5 の定数が前景という一貫しない
答えだった(この非一貫は、直すまで誰も書いていなかった)。

### 効き目(適用後の実測)

| 板(雑音なし) | 直す前 | 直した後 | skimage | OpenCV |
|---|---|---|---|---|
| 0.30 / 0.90 | **4,096** | 400 | 400 | 400 |
| 0.00 / 1.00 | 400 | 400 | 400 | 400 |
| 0.10 / 0.60 | 400 | 400 | 400 | 400 |
| 0.25 / 0.75 | 400 | 400 | 400 | 400 |

実写系の画像では変化画素は中央値 0.000% / 最大 0.485%(測定 2026-09-25)。
**壊れていたのは平らな絵だけで、壊れ方が全面だった**——「たまに少し違う」ではなく
「合成の板でだけ全部前景」。検査の分野でいちばん出やすい絵がそれである。

## 門

`tests/test_otsu_threshold_2026_09_26.py`。**雑音を載せない板**で 4 面とも 400 px を
要求し、skimage と OpenCV の 2 つの独立実装と数を突き合わせ、アフィン等変性
(`otsu(0.6v+0.3) == otsu(v)`)を主張ごとに置く。加えて**門を壊して確かめる**試験
(`test_the_midpoint_spelling_is_what_the_gate_catches`)で、中点の式に戻すと板の門が
落ちることを固定した。落ちない門は「直した」の証拠にならない。
