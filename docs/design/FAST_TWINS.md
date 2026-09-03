# CPU 高速 twin(`fast.py`)— 実装記録と実測(2026-09-03)

> 出典: `docs/design/PERF_MEMORY_VIDEO_SURVEY.md` の **recommendation (a′)**
> (§4 順位 2 / §4.1 / §4.3-2)。「コア op の CPU 高速 twin テーブル(cv2)+ parity ゲート
> + uint8 fail-closed」。
> 姿勢: **faithful なものだけ載せる。「速いが違う」は作らない。** 落とした候補も
> 実測誤差つきでこの文書に残す(§3)。
> 数字はこの PC・この日の実測。**熱定常ではない**(`docs/FSCRIPT_MEASUREMENTS.md` §0-a
> の 1.7 倍ぶれは本測定にも当てはまる)。**倍率**のほうが絶対値より信頼できる。

---

## 0. 何が入ったか(3 行)

1. `fast.py` — core op の **cv2 twin 41 件**(+ uint8 整数カーネル 21 件)と、
   `accel.parity` と同じ方法の **parity ゲート**(5 (a,b) × 6 画像、interior max-abs)。
2. `api.py` — `apply(..., fast=True)` / `run_pipeline(..., fast=True)` / 環境変数
   `FULLSEYE_FAST=1` の **opt-in 配線**(`_try_accel` と同型: 失敗は ledger に
   `source="fast"`、`on_error="raise"` で再送出、サーキットブレーカ付き)。
   **このセッションでは既定 OFF**。既定 ON にするかは別セッションでベンチしてから。
3. `api.py` — 整数 image 入力の **fail-closed 化**(§4)と、調査 §5.3 item 3 / 4
   (`np.unique` → O(N) / ACCEL 逆引きのキャッシュ)。

---

## 1. 実測: core vs twin(2048² float64、reps=5 の中央値、同一プロセス)

入力 = 円板 60 個 + 照明勾配 + 3 % ノイズの合成シーン(調査 §0.1 と同じ作り。
**ノイズ入り** — median の scipy 実装は内容で 10 倍変わるので平滑画像で測ってはいけない)。
cv2 threads = 24。

| op | a (カーネル) | core ms | twin ms | 倍率 |
|---|---|---:|---:|---:|
| `gaussian` | 0.50 (σ=1.65) | 61.0 | **7.1** | **8.6×** |
| `mean_box` | 0.50 (k=7) | 53.1 | **11.2** | 4.7× |
| `median` | 0.25 (**k=5**) | 1010.8 | **34.9** | **29.0×** |
| `median` | 0.50 (k=7) | 1803.0 | 1808.1 | **1.0×**(= core を呼んでいる。§2 の honest) |
| `gopen` | 0.50 (k=7) | 150.9 | **19.8** | 7.6× |
| `gerode` | 0.50 (k=7) | 89.4 | **6.1** | 14.6× |
| `sobel_mag` | 0.50 (3×3) | 141.9 | 51.2 | 2.8× |
| `std_filter` | 0.50 (k=7) | 167.6 | 83.9 | 2.0× |
| `canny` | 0.50 (σ=1.25) | 204.9 | 71.8 | 2.9× |

uint8 の整数カーネル(`fast.apply_uint8`、入力も出力も uint8。**facade は通さない**):

| uint8 カーネル | core(f64)ms | uint8 twin ms | 倍率 |
|---|---:|---:|---:|
| `median` a=0.25 (k=5) | 1011.5 | **5.5** | **185×** |
| `median` a=0.50 (k=7) | 1816.6 | **64.2** | 28× |
| `mean_box` a=0.50 | 52.4 | **2.0** | 27× |
| `gopen` a=0.50 | 152.0 | **3.1** | 50× |

5-op 連鎖(`gaussian → gopen → sobel_mag → gerode → threshold`、`api.run_pipeline` 経由。
facade のオーバーヘッド込み):

| 形状 | core | fast | 倍率 | fps |
|---|---:|---:|---:|---|
| 2048² | 456.5 ms | **94.2 ms** | 4.8× | 2.2 → 10.6 fps |
| 1920×1080 | 161.6 ms | **51.3 ms** | 3.1× | 6.2 → **19.5 fps** |

**honest な読み**:
- 調査 §4.2 の見積り「1080p 5-op 連鎖 111 → 20〜25 ms」には届かなかった(実測 51.3 ms)。
  差の主因は連鎖に **`sobel_mag`(2.8×)と `threshold`(twin 無し)** が入っていること、
  および facade の固定費(`sanitize` / guard)。**30 fps(33 ms)には未達**。
  gaussian/box/morph だけの連鎖ならもっと伸びる。
- `sobel_mag` / `std_filter` / `canny` が 2〜3 倍止まりなのは、これらが
  **`ops._norm`(画像全体の max を取る)+ `np.hypot`/`np.sqrt` の numpy 単スレッド部分**を
  含むため。cv2 化したのは畳み込みだけで、後段の要素演算は core と同じコードを通る。
- 熱ぶれ: 同じ表を続けて 2 回取ると ±10〜30 % 動く。**倍率(内訳の構造)で読むこと**。

---

## 2. 載せた twin(41 件)と parity 実測

ゲート = `fast.parity()`。**`accel.parity` と同じ方法**:

- **(a,b) 5 点** `((0.5,0.4), (0.25,0.75), (0.8,0.2), (0.0,0.5), (1.0,0.9))`
  — `_k(a)` の 4 段(3/5/7/9)を全部踏む。
- **画像 6 枚** — 自然画(円板+勾配+ノイズ)/ 純ノイズ / 定数 0.42 / uint8 量子化 /
  純勾配 / 小さい 64²(前 5 枚は 128²)。
- **interior** = 端から `max(3, k//2+1)` px を除いた **max-abs**。
- **二値(`out_sort == "region"`)の op だけ不一致率**で測る(max-diff は「刃の上の
  1 画素」で即 1.0 になるため。accel と同じ計量)。**ただし採否は accel より厳しく
  「不一致率 0」を要求する** — 二値の 1 画素差は目に見える差だから。

| twin(core registry 名) | full max-abs | interior | 実装 |
|---|---:|---:|---|
| `gaussian` / `gauss_filter` / `gauss_image` | 5.6e-16 | 5.6e-16 | `cv2.GaussianBlur`、**scipy の半径 `int(4σ+0.5)` を明示** + `BORDER_REFLECT` |
| `mean_box` / `mean_image` | 1.9e-15 | 1.9e-15 | `cv2.blur` |
| `median` / `median_image` / `median_separate` / `median_weighted` / `eliminate_min_max` | 2.98e-8 | 2.98e-8 | `cv2.medianBlur`(float32)。**symmetric pad で端も一致**。k≥7 は core |
| `min_filter` / `gerode` / `gray_erosion` / `gray_erosion_rect` | 0.0 | 0.0 | `cv2.erode`(矩形 k×k) |
| `max_filter` / `gdilate` / `gray_dilation` / `gray_dilation_rect` | 0.0 | 0.0 | `cv2.dilate` |
| `gopen` / `gray_opening` / `gray_opening_rect` | 0.0 | 0.0 | `morphologyEx OPEN` |
| `gclose` / `gray_closing` / `gray_closing_rect` | 0.0 | 0.0 | `morphologyEx CLOSE` |
| `tophat` / `gray_tophat` | 0.0 | 0.0 | `morphologyEx TOPHAT` + `_norm` |
| `bothat` / `gray_bothat` | 0.0 | 0.0 | `morphologyEx BLACKHAT` + `_norm` |
| `morph_grad` / `gray_range_rect` | 0.0 | 0.0 | `morphologyEx GRADIENT` + `_norm` |
| `sobel_mag` / `sobel_amp` | 3.3e-16 | 3.3e-16 | `cv2.Sobel`×2 + `hypot` + `_norm` |
| `laplace` | 1.4e-14 | 1.4e-14 | `cv2.Laplacian(ksize=1)` + `_norm` |
| `prewitt_mag` / `prewitt_amp` | 4.4e-16 | 4.4e-16 | `cv2.sepFilter2D([-1,0,1]/[1,1,1])`×2 |
| `dog` / `diff_of_gauss` | 3.7e-13 | 3.7e-13 | `GaussianBlur` 2 本の差 + `_norm` |
| `unsharp` | 6.7e-16 | 6.7e-16 | `v + k(v − GaussianBlur)` |
| `std_filter` / `deviation_image` | 3.1e-10 | 3.0e-11 | `box(v²) − box(v)²` の sqrt + `_norm` |
| `canny` | 0.0(不一致率) | 0.0 | core は hysteresis 無しなので **cv2 プリミティブで同式を組む** |

`py -3.11 fast.py` → **faithful: 41 / 41**。

### 2.1 境界規約(踏んではいけない罠)

`scipy.ndimage` の既定 `mode="reflect"` は **numpy の `"symmetric"`(端を複製する鏡映)**
であり、cv2 の既定 `BORDER_REFLECT_101`(端を複製しない鏡映)とは **別物**。
`accel` は 2026-08-31 にこの罠を踏み、`_sep_conv` が torch `reflect` のままで
sobel/dog/unsharp の端がずれ、`_norm` を通じて全体に乗っていた
(`docs/GPU_ACCEL_PLAN.md` Batch 0)。

ここでは **推測せず実測**した(64² 乱数+勾配、5 σ):

| 境界指定 | gaussian の max 差 vs scipy |
|---|---|
| `cv2.BORDER_REFLECT`(= symmetric) | **2.2e-16 〜 3.3e-16** |
| `cv2.BORDER_REFLECT_101`(cv2 の既定) | 2.2e-3 〜 **8.9e-2** |

→ 全 twin で `cv2.BORDER_REFLECT` を **明示**する。

`cv2.medianBlur` だけは borderType を選べず内部で `BORDER_REPLICATE` を使うので、
**入力を `np.pad(mode="symmetric")` で `k//2` だけ広げてから掛けて切り戻す**。
pad 無しだと端 3px で max **0.155** ずれる(実測)。pad 込みで full 2.98e-8。

### 2.2 dtype 方針(`dtype_policy`)

- `"f64"` — float64 twin のみ。
- `"f64+u8"` — `fast.apply_uint8(name, img_u8, a, b)` に **uint8 の整数カーネル**もある。
  21 件(median 系 5 / box 系 2 / モルフォロジ 14)。

**facade は uint8 経路を通さない**(公開契約は float64 [0,1] のまま)。使うのは
呼び出し側の明示的な選択 —— 動画のストリーミング((d) `VideoPipeline`)で uint8 の
リングを回すときの受け皿。

uint8 カーネルの実測誤差(ゲート画像 6 枚 × 5 点の最大、core float64 との差):

| 種類 | 誤差 | 理由 |
|---|---|---|
| median / モルフォロジ(erode/dilate/open/close) | **0.000 / 255** | 順序統計なので量子化後の入力には厳密 |
| box (`mean_box`/`mean_image`) | 0.494 / 255 | 整数丸め |
| **gaussian は載せていない** | 1.174 / 255 | cv2 の 8U GaussianBlur は **8 bit 固定小数のカーネル**。「1/255 まで一致」を満たさないので **uint8 版は置かない**(float64 twin は載っている)。2/255 という別契約が要るなら明示的に足すこと |

---

## 3. 載せなかった候補(「速いが違う」を作らないための記録)

すべて実装して同じゲートに掛け、**落ちたことを実測**してから外した。

| 候補 | 測った実装 | interior 誤差 | 落とした理由 |
|---|---|---:|---|
| `clahe` | `cv2.createCLAHE(clipLimit=1+4a, tile=(2+3a)²)` | **0.135** | clip limit の定義もタイル補間も core と別物(core は Zuiderveld 補間 + ビン平均に対する 256^b 倍) |
| `bilateral` | `cv2.bilateralFilter(d=5, σc, σs)` | **0.121** | cv2 の空間近傍は **半径 2 の円**(角 4 画素を落とす)。core は 5×5 全 25 画素 |
| `rotate_img` | `cv2.warpAffine INTER_CUBIC` | **0.870** | cv2 の cubic は Catmull-Rom、core は order=3 **B-spline**(prefilter あり) |
| `rescale_img` / `affine_warp` | 同上 | 同上 | 同じ理由。`b<0.5` の最近傍/双一次だけ一致しても部分的なので載せない |
| `equalize` | `cv2.equalizeHist` | **0.580** | uint8 の 256 段 vs core の float 256 bin + `np.interp` |
| `otsu` | `cv2.threshold(THRESH_OTSU)` | 0.0042 | 連続 op なら 5e-3 を通るが **二値 op なので不一致率 0 が条件**。uint8 ヒストグラムの閾値差で境界画素が動く |
| `dyn_threshold` | `v > cv2.blur(v) + c` | 二値不一致率 **2.97e-4** | `cv2.blur` と `ndimage.uniform_filter` の **最終 ulp 差**で閾値上の画素が反転。連続なら 5e-3 圏内だが二値なので不採用 |
| `edges_image` | `canny` twin | 二値不一致率 **1.00** | registry のこの名前は backends_auto の **skimage canny**(本物の hysteresis つき)。core の `canny` とは別アルゴリズム |
| `percentile` / `rank_image` | — | — | cv2 に任意パーセンタイルの rank filter が無い |
| `lowpass` / `highpass` | — | — | `cv2.dft` は `np.fft.fft2` とレイアウト規約が違い、調査でも cv2 の利得を測れていない |
| `gamma` / `invert` / `scale_clip` / `threshold` | — | — | 既に 100〜450 Mpx/s の numpy 要素演算。cv2 化の利得が無い(uint8 LUT は契約外) |

この表は `fast.NOT_LISTED` にも同じ内容で入れてあり、`tests/test_fast_parity.py::test_not_listed_documents_the_rejects` が
「載せていないこと」と「理由が残っていること」を両方検査する。

---

## 4. uint8 入力の fail-closed(調査 §1.3 / §2.1 / §5.3 item 1)

### 変わったこと

公開契約は「image = H×W float64 in [0,1]」だが、facade は uint8 を **拒否も変換もせず
素通し**していた。core op は `ndimage.*` を dtype 無指定で呼ぶので、uint8 は
**uint8 のまま計算されて uint8 で返る**(`gaussian` / `mean_box` / `gerode` /
`rotate_img`)、`sobel_mag` は `np.hypot(uint8,uint8)` で **float16**、`threshold` は
`v > 0.5` が 0..255 に効いて **全画素 1**。例外なし・もっともらしい配列・違う答え
—— 「受け入れる」と「拒否する」の間の **第 3 の状態**。

いまは `on_error` 方針に従う(`api._contract_dtype`):

| 方針 | 挙動 |
|---|---|
| `on_error="raise"` | `ValueError`。dtype 名と契約(float64 [0,1])と直し方を文面に含む |
| `"fallback"`(既定)/ `"warn"` | **明示変換 + ledger に記録**(`source="input"`、本文が `dtype_converted: uint8 -> float64 (/255)`) |

スケール: `uint8 → /255`、`uint16 → /65535`、`bool → astype(float64)`。
それ以外の整数 dtype は全域が決まらないので、**値が既に [0,1] に収まっていれば再型付けだけ**、
そうでなければ `np.iinfo(dtype).max` で割る(どちらでも記録は残す)。

**`region` sort は対象外**。int の {0,1} マスクは region の正当な入力で、
`_coerce_input` が既に再型付け(再スケールはしない)している。

### 既存の float64 呼び出しは 1 ビットも変わらない

`tests/test_api_dtype.py::test_float64_results_are_bit_identical_with_and_without_the_flag`
が 10 op(`gaussian` `mean_box` `median` `gerode` `gopen` `sobel_mag` `laplace`
`dog` `unsharp` `std_filter`)の出力を **SHA-256 でハッシュ**して、
① `fast=False` ② 既定(環境変数なし)③ `ops.RT` を直接叩いた値 —— の 3 つが
**同じ bytes** であることを検査する。

---

## 5. facade の配線(`api.py`)

```python
fullseye.apply(x, "gaussian", fast=True)          # 明示
FULLSEYE_FAST=1                                    # プロセス既定(このセッションでは OFF)
fullseye.run_pipeline(x, stages, fast=True)        # CPU 連鎖の全段
```

`_try_fast` は `_try_accel` と同型:

- `fast` / OpenCV が **無い**(`ImportError`)→ 黙って core(仕様)。
- その入力に twin が **無い**(`FastUnsupported`: 非 float64 / 非 2-D / 空)→ 黙って core。
  これは「壊れた」ではなく「無い」なので ledger には残さない。
- twin が **失敗した** → `_bs.record(..., source="fast")` + サーキットブレーカを開けて
  core にフォールバック。`on_error="raise"`(= strict)なら再送出。
  `fullseye.fast_open_ops()` / `fullseye.reset_fast()` で観測・復帰。
- `device != "cpu"` のときは GPU 経路が優先(twin は CPU 専用)。

**既定 OFF の理由**(honest): parity は 41/41 通っているが、
① `median` は a≥0.5 で core に落ちるので「速くなる op と速くならない op が混ざる」、
② 5-op 連鎖の実測が見積り(20〜25 ms)に届かず 51 ms、
③ 進化 champion の再現性に効くので、既定を変えるなら
`tools/bench_ops.py`((h))のベースライン JSON を先に置いて、同じ物差しで
before/after を出してから。**次のセッションの判断材料はこの文書の §1**。

---

## 6. ついでに直した 2 件(調査 §5.3 item 3 / 4)

### item 3 — `_coerce_input` の `np.unique`

`np.unique` は配列全体をソートする(O(N log N))ので、**region op が facade 経由で
2 倍遅くなっていた**(2048² region: 35.0 ms のうち 17.6 ms、うち `np.unique` が 16.9 ms)。

`api._needs_binarise(a)` に置換して **O(N)**:

- min / max を取る。`min < 0` か `max > 1` なら二値化(旧 `vals.min()/max()` と同値)。
- 「相異なる値が 2 つ以下」は **`min != max` かつ `all((a == mn) | (a == mx))` が偽**
  と同値(min が `mn`・max が `mx` の配列は、全要素が `mn` か `mx` のときに限り
  レベルが 2 以下)。
- **NaN があるときだけ**旧 `np.unique` 経路をそのまま踏む(`nan < 0` は False なので
  旧コードの判定が min/max では再現できない唯一のケース)。

判定が変わっていないことは `test_needs_binarise_matches_np_unique`(15 の手書きケース:
定数・2 値・3 値・負・>1・空・int・NaN・±inf)と
`test_needs_binarise_matches_np_unique_on_random_arrays`(乱数 200 本、旧実装を
オラクルとして同居させて突き合わせ)で固定した。`_coerce_sort`(n-ary 版)にも同じ
helper を通してある。

### item 4 — `_try_accel` の ACCEL 逆引き

`{c: k for k, (_f, c, _h) in accel.ACCEL.items()}` を **毎 apply**(90+ 要素)作っていた。
`api._accel_reverse(accel)` でモジュールレベルにキャッシュし、
`(id(ACCEL), len(ACCEL))` をタグにして **テストが表を差し替えたら作り直す**
(古い辞書を返さない)。値は従来と同一(後勝ちの順序も含めて)。

---

## 7. テスト

```
PYTHONUTF8=1 py -3.11 -m pytest tests/test_fast_parity.py tests/test_api_dtype.py -q
  -> 100 passed

PYTHONUTF8=1 py -3.11 -m pytest tests/test_api.py tests/test_api_device.py \
    tests/test_backend_safe.py tests/test_fallback_policy.py \
    tests/test_accel_bridge.py tests/test_accel_smoothing.py -q
  -> 165 passed (上の 2 本を含む)
```

`tests/test_fast_parity.py` は **`fast.FAST` の全エントリを parametrize** するので、
新しい twin を足して parity を通さないと **その twin のテストが落ちる**(ゲートを
迂回して表に載せることができない)。`MIN_TWINS = 30` で「表が痩せたのに全部 pass」も塞いである。

---

## 8. 次にやること

1. **(h) `tools/bench_ops.py` + `out/bench_ops_baseline.json`** — §1 の表を repo の
   物差しにする。`fast` の on/off を同一 run 内の相対値で出す(熱ぶれ対策)。
2. `FULLSEYE_FAST` の既定を ON にするかの判断(上のベースラインが出てから)。
3. `median` の k=7/9: cv2 に float の道が無い。uint8 リング((d) `VideoPipeline`)側で
   `apply_uint8` を使うのが本筋。
4. `sobel_mag` / `std_filter` / `canny` の残り(`_norm` + `hypot` の numpy 単スレッド部)。
   タイル並列((c))か、`_norm` を含む op のフラグ化とセットで。
