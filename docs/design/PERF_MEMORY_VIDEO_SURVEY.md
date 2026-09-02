# op の高速化・省メモリ化・動画処理 — 実測にもとづく調査報告(2026-09-03)

> 目的: 「op の高速化と省メモリ化について調査した上で着手したい。動画(動画像処理)も扱えるようにしたいが、そこが課題になるはず」(ユーザー、2026-09-03)への **実装前の調査**。
> 性格: **実測値 + コードの根本原因(file:line)+ 選択肢の順位づけ**。実装はしていない(この文書 1 本だけを追加)。
> 規律: 数字はすべてこの PC でこの日に測ったもの。**熱定常でない**(`docs/FSCRIPT_MEASUREMENTS.md` §0-a の 1.7 倍ぶれ問題は本測定にも当てはまる)ので、絶対値は ±30〜70 % の幅を持って読む。倍率(内訳の構造)のほうが信頼できる。

---

## 0. 結論(先に要点)

1. **遅さの正体は「Python」ではなく「scipy.ndimage を float64 で単スレッド実行している」こと**。同じ処理を cv2(IPP+SIMD+24 スレッド)で走らせると 2048² で gaussian **58 → 8.6 ms(6.8×)**、median **1827 → 44.6 ms(41×、生の cv2 uint8 なら 3.4 ms = 540×)**、gray opening **154 → 17 ms(9×)**、canny **205 → 38 ms(5×)**、CLAHE **386 → 41 ms(9×)**。cv2 経路は **registry に既にある**(`cv_*` 76 op、`backends.py`)が、コア名(`gaussian` / `median` …)の既定実装は scipy のままなので、進化 champion もユーザーの `fullseye.apply(x, "gauss_filter")` も遅い方を踏む。
2. **1080p @ 30 fps(62 Mpx/s)に今のコア実装で届く op は 56 中 25**(§1.4)。`median` / `percentile`(2.3 Mpx/s、**27 倍不足**)、FFT 系(12〜19 Mpx/s)、幾何変換(16〜18 Mpx/s)、`corner_response` / `clahe`(11 Mpx/s)が **10 倍級**で外れる。cv2 ラッパ側は同じ処理が 100〜580 Mpx/s。
3. **メモリは「入力の何倍か」で見ると 1〜8 倍、最悪 22 倍**。`corner_response` 8×(2048² で 256 MB)、FFT lowpass/highpass 7.1×(complex128 の中間)、`cfa_to_rgb` 6×、`ncc_locate`/`shape_locate` は RSS ピーク **21〜22×**(`ndimage.correlate` の内部バッファ)。core の separable filter 系は 1.0×(出力のみ)で健全。float64 という選択自体が uint8 比 **8 倍**の常駐コスト。
4. **dtype の実態**: 公開契約は float64 [0,1](`api.py:19-22`)だが、facade は uint8 を **拒否しない**(`api.py:1089-1103` は「数値 dtype か」しか見ない)。uint8 を通すと core op の出力が **uint8 のまま(gaussian/mean_box/gerode/rotate_img)/float16(sobel_mag)/全画素 1(threshold)** になり、例外を出さずに間違う(§1.3)。**uint8 の高速経路は存在せず、uint8 の拒否も存在しない** — 両方欠けている。
5. **動画**: 読む側(`video.iter_frames`)は **18 fps(1080p gray)**、同じファイルを cv2 で素読みすると **204 fps**。差の 11 倍は **1 フレームごとの uint8→float64 変換 + 輝度 matmul**(`video.py:62-97`)で、デコードではない。時間軸 op(`videops.py`)は **全フレームを (T,H,W) float64 で一括保持**する API(`videops.py:42-71`)で、30 フレームの 1080p = **475 MB(RSS ピーク 947 MB)**。ストリーミング・リングバッファ・状態つき op の契約は **無い**(registry の `video` sort は 2 op のみ、`backends_typed.py:100`)。
6. **GPU 経路は本物だが「1 op ずつ D2H/H2D」だと転送床(1080p 1 枚で 13.7 ms、8 枚で 110 ms)に食われる**。常駐で 5-op 連鎖を回すと 1080p **2.1 ms/フレーム(計算のみ)**、転送込み 16 ms、CPU 連鎖 111 ms(§1.6)。動画向けには **フレームを GPU に常駐させたままリングで回す**設計が要る。
7. **明日着手する 3 件**(§4.3): (h) `tools/bench_ops.py` + JSON ベースライン、(a′) **コア op の CPU 高速 twin テーブル(cv2)+ parity ゲート + uint8 fail-closed**、(d) **`VideoPipeline`(ストリーミング reader / uint8 ゼロコピー / リングバッファ / 状態つき op 契約)**。

---

## 0.1 測定環境

| 項目 | 値(実測) |
|---|---|
| CPU | Intel Core Ultra 7 270K Plus、24 論理コア(`Get-CimInstance Win32_Processor`: cores=24, logical=24) |
| RAM | 128 GB(psutil 127.5 GiB) |
| GPU | NVIDIA GeForce RTX 5090 32 GB、driver 610.74(`nvidia-smi`) |
| Python | 3.11.9 (MSC) `py -3.11` |
| numpy / scipy | 2.4.6(OpenBLAS 0.3.31, 24 threads)/ 1.15.2 |
| OpenCV | 5.0.0(FFMPEG YES avcodec 61.19、Intel IPP 2026.0、Parallel=Concurrency、`getNumThreads()=24`) |
| scikit-image / kornia / PIL | 0.26.0 / 0.8.3 / 12.3.0 |
| torch | グローバル: **2.11.0+cpu(CUDA 不可)**。GPU 実測は `C:/dev/venvs/loco/Scripts/python.exe`(2.11.0+cu128、numpy 1.24.4、scipy 1.15.2)で `accel.py` / `accel_vol.py` のみ実行 |
| 動画 I/O | imageio 2.37.4 + imageio-ffmpeg 0.6.0(同梱 ffmpeg 7.1 バイナリ)。**システム ffmpeg 無し**、`av` / `numba` / `cupy` / `pyfftw` **無し**、psutil 7.2.2 あり |
| スレッド | threadpoolctl: openblas 24 / openmp 24、torch 24、cv2 24。**scipy.ndimage は常に単スレッド**(スレッドプールを持たない) |

レジストリ実測: **860 op**(image 518 / region 129 / contour 65 / points 44 / signal 26 / volume 14 / color 11 / video 2 …)、うち guard 付き 475。定義元: backends_auto 227 / backends_typed 122 / backends_halcon_ext 81 / ops.py 76 / backends.py(sk_/cv_) 76 / backends_r3 56 …。accel(GPU)対応 90 mapping + volume 10。

測定方法(使い捨てスクリプト、リポジトリ外 `scratchpad/prof_ops.py`・`prof_accel.py`):
- すべて **`api.apply(x, name, 0.5, 0.5)` の実経路**(`_coerce_input` → `_guard_input` → `_run_guarded` → guard → sanitize)。
- 時間 = warm-up 1 回 + 3 回の最小(1 s 超は 1 回)。tracemalloc ピーク(numpy 配列)と、0.4 ms ポーリングの RSS ピーク(C 内部バッファも含む。短い op は取りこぼす)の **2 本立て**。
- 入力 = 円板 60 個 + 照明勾配 + 3 % ノイズの合成シーン(`scene()`)。float64 [0,1] と、同じ画を 0..255 の uint8 にしたもの。512²、2048²、1920×1080、128³。
- 「バックエンド」= op 関数の定義モジュール(`fn.__wrapped__.__module__`)。fallback ledger(`backend_safe.events_since`)で **降格が起きたか**を毎回確認 → **全 op・全サイズで降格 0 件、入力の破壊 0 件、入力と出力のメモリ共有は `identity` のみ**。
- 総所要 364 s(2-D 241 s 含む)。

---

## 1. ベースライン実測

### 1.1 2048² float64(4.19 Mpx)— 主表

tm× = tracemalloc ピーク ÷ 入力バイト(32 MB)、rss× = RSS ピーク増分 ÷ 入力バイト。「ms (u8 in)」は同じ op に 0..255 の uint8 を渡した時間、「out dtype」はそのときの出力 dtype(**正しさの検査ではなく挙動の記録**)。

| op | family | module | ms (f64) | Mpx/s | tm× | rss× | ms (u8 in) | out dtype (u8 in) |
|---|---|---|---:|---:|---:|---:|---:|---|
| cfa_to_rgb | color | backends_color | 81.8 | 51 | 6.1 | 6.1 | 88.6 | float64 |
| principal_comp | color | backends_color | 352.5 | 12 | 5.0 | 5.0 | 374.1 | float64 |
| rgb1_to_gray | color | backends_color | 72.9 | 58 | 2.0 | 2.0 | 96.3 | float64 |
| trans_from_rgb | color | backends_color | 124.3 | 34 | 2.1 | 2.1 | 145.0 | float64 |
| canny | edge | ops | 204.9 | 20 | 4.0 | 4.0 | 174.9 | float64 |
| corner_response | edge | ops | 386.7 | 11 | 8.0 | 8.0 | 233.6 | float64 |
| cv_canny | edge | backends | 38.3 | 110 | 2.0 | 2.0 | 21.8 | float64 |
| fft_image | fft | backends_auto | 225.5 | 19 | 4.0 | 4.0 | 220.4 | float64 |
| highpass | fft | ops | 339.5 | 12 | 7.1 | 7.1 | 322.2 | float64 |
| lowpass | fft | ops | 313.3 | 13 | 7.1 | 7.1 | 296.4 | float64 |
| sk_butterworth | fft | backends | 107.6 | 39 | 2.5 | 3.5 | 115.7 | float64 |
| cv_bilateral | filter | backends | 20.8 | 201 | 1.5 | 1.4 | 18.9 | float64 |
| cv_box | filter | backends | 10.5 | 398 | 1.1 | 1.1 | 2.5 | **uint8** |
| cv_gaussian | filter | backends | 8.6 | 486 | 1.1 | 1.1 | 1.3 | **uint8** |
| cv_median | filter | backends | 44.6 | 94 | 2.0 | 2.0 | 27.2 | float64 |
| cv_scharr | filter | backends | 67.8 | 62 | 3.0 | 3.0 | 60.9 | float64 |
| gauss_filter | filter | backends_auto | 60.9 | 69 | 1.1 | 1.1 | 76.0 | float64 |
| gaussian | filter | ops | 58.2 | 72 | 1.0 | 1.0 | 38.3 | **uint8** |
| log | filter | ops | 161.7 | 26 | 2.0 | 2.0 | 92.1 | float64 |
| mean_box | filter | ops | 53.6 | 78 | 1.0 | 1.0 | 31.3 | **uint8** |
| median | filter | ops | **1827.3** | **2.3** | 1.0 | 1.0 | 1767.3 | **uint8** |
| percentile | filter | ops | **1844.6** | **2.3** | 1.0 | 1.0 | 1741.5 | **uint8** |
| sobel_mag | filter | ops | 150.2 | 28 | 3.0 | 3.0 | 110.7 | **float16** |
| std_filter | filter | ops | 167.3 | 25 | 4.0 | 4.0 | 104.7 | float64 |
| unsharp | filter | ops | 93.1 | 45 | 2.0 | 2.0 | 63.8 | float64 |
| xkor_gaussian | filter | backends_kornia | 39.2 | 107 | 1.5 | **4.5** | 47.6 | float64 |
| clahe | gray | ops | 386.2 | 11 | 3.3 | 3.3 | 188.6 | float64 |
| cv_clahe | gray | backends | 41.3 | 102 | 2.0 | 2.0 | 25.4 | float64 |
| equalize | gray | ops | 109.4 | 38 | 2.0 | 2.0 | 42.4 | float64 |
| gamma | gray | ops | 39.8 | 105 | 2.0 | 2.0 | 11.9 | float64 |
| invert | gray | ops | 17.2 | 244 | 2.0 | 2.0 | 8.5 | float64 |
| identity | gray | ops | 0.0 | — | 0.0 | 0.0 | 0.0 | uint8 |
| cv_open | morph | backends | 17.4 | 241 | 1.1 | 2.0 | 3.5 | **uint8** |
| fill_holes | morph | ops | 80.7 | 52 | 1.2 | 1.2 | 84.7 | float64 |
| gerode | morph | ops | 88.9 | 47 | 1.0 | 1.0 | 67.2 | **uint8** |
| gopen | morph | ops | 153.9 | 27 | 2.0 | 2.0 | 111.0 | **uint8** |
| opening_circle | morph | backends_auto | 67.4 | 62 | 1.4 | 1.3 | 73.2 | float64 |
| reg_dilate | morph | ops | 42.0 | 100 | 1.2 | 1.2 | 47.6 | float64 |
| reg_erode | morph | ops | 36.6 | 115 | 1.2 | 1.2 | 43.7 | float64 |
| tophat | morph | ops | 177.3 | 24 | 2.0 | 2.0 | 123.1 | float64 |
| area_frac | props | ops | 22.9 | 184 | 1.2 | 1.2 | 29.9 | float |
| blob_count | props | ops | 28.1 | 149 | 1.2 | 1.2 | 34.7 | float |
| circularity | props | backends_auto | 90.6 | 46 | 3.1 | 3.1 | 96.7 | float |
| count_obj | props | backends_auto | 28.8 | 146 | 1.2 | 1.2 | 34.8 | float |
| dist_transform | props | ops | 293.7 | 14 | 4.1 | 4.1 | 300.8 | float64 |
| remove_small | props | ops | 79.9 | 53 | 3.0 | 3.0 | 85.3 | float64 |
| select_largest | props | ops | 84.0 | 50 | 3.0 | 3.0 | 88.3 | float64 |
| cv_otsu | seg | backends | 38.8 | 108 | 2.0 | 2.0 | 24.2 | float64 |
| dyn_threshold | seg | backends_auto | 90.7 | 46 | 3.0 | 3.0 | 91.8 | float64 |
| otsu | seg | ops | 34.7 | 121 | 2.1 | 2.1 | 33.9 | float64 |
| threshold | seg | ops | 9.4 | 447 | 1.1 | 1.1 | 8.8 | float64 |
| affine_warp | xform | ops | 266.2 | 16 | 2.0 | 2.0 | 249.3 | **uint8** |
| rescale_img | xform | ops | 229.0 | 18 | 2.0 | 2.0 | 204.9 | **uint8** |
| rotate_image | xform | backends_auto | 270.3 | 16 | 2.0 | 2.0 | 280.4 | float64 |
| rotate_img | xform | ops | 270.4 | 16 | 2.0 | 2.0 | 246.1 | **uint8** |
| zoom_image_size | xform | backends_auto | 87.5 | 48 | 3.0 | 3.0 | 96.7 | float64 |

重い op(2048² は時間予算外なので 512² のみ):

| op | module | 512² ms | Mpx/s | tm× | rss× |
|---|---|---:|---:|---:|---:|
| shape_locate(48² テンプレ、30° 刻み 12 回転) | ops | **3076.6** | 0.09 | 7.2 | **22.3** |
| sk_tv(Chambolle TV) | backends | 502.1 | 0.52 | 10.0 | 10.0 |
| lines_gauss | backends_auto | 366.3 | 0.72 | 15.0 | 14.6 |
| ncc_locate(48² テンプレ) | ops | 260.9 | 1.0 | 6.1 | **21.3** |
| bilateral(純 numpy 25 シフト) | ops | 127.9 | 2.05 | 6.0 | 6.0 |
| edges_sub_pix | backends_auto | 27.7 | 9.5 | 6.0 | 5.1 |
| sk_canny | backends | 12.0 | 21.9 | 6.0 | 5.5 |
| sk_find_contours | backends | 3.7 | 71.6 | 1.7 | 1.4 |

**注意(honest)**: `median` / `percentile` の scipy 実装は **入力の内容で 10 倍変わる**。3 % ノイズ入りのシーンで 2048² 1827 ms、ノイズ無しの平滑画像(clip で飽和多数)では 197 ms、別測で 92 ms(選択アルゴリズムが同値の多さに依存)。cv2 の `medianBlur(uint8, 5)` は内容によらず 3.4 ms。**「実画像(ノイズあり)」でこそ最悪側に落ちる**ので、ベンチにはノイズ入りを使うべき。

### 1.2 Top-10(画素あたり最遅 / メモリ最大)

**画素あたり最遅(Mpx/s、低い順)**: 1 shape_locate 0.09 / 2 sk_tv 0.52 / 3 lines_gauss 0.72 / 4 ncc_locate 1.0 / 5 bilateral 2.05 / 6 percentile 2.3 / 7 median 2.3 / 8 edges_sub_pix 9.5 / 9 corner_response 10.9 / 10 clahe 10.9(次点 principal_comp 11.9、highpass 12.4、lowpass 13.4、dist_transform 14.3)。

**メモリ最大(入力の倍率、2048² f64)**: 1 ncc_locate/shape_locate rss **21〜22×**(512² 実測)/ 2 lines_gauss 15× / 3 sk_tv 10× / 4 corner_response **8.0×**(256 MB)/ 5 lowpass・highpass **7.1×**(228 MB)/ 6 cfa_to_rgb 6.1× / 7 bilateral 6.0× / 8 principal_comp 5.0×(480 MB)/ 9 xkor_gaussian rss 4.5×(torch 常駐分)/ 10 dist_transform・std_filter・fft_image・canny 4.0×。

### 1.3 dtype 昇格・コピー・バックエンド

- **float64 入力で「コピー」する op はほぼ無い**(`np.asarray(v, np.float64)` は f64 に対しては no-op)。tm× 1.0 の op(gaussian / mean_box / median / gerode …)は出力 1 枚しか確保していない。2.0× は出力 + 中間 1 枚(`_norm` の除算、`np.clip`、`astype(np.float64)`)。
- **uint8 入力は 8 倍に膨れる op と、膨れずに壊れる op に二分される**:
  - 膨れる: `np.asarray(v, np.float64)` を頭で掛ける backends_auto / backends_color / backends_typed 系(tm× 16〜57、例 lowpass 57× = 4 MB の uint8 に対し 228 MB)。
  - 壊れる: ops.py のコア(`ndimage.*` を dtype 無指定で呼ぶ `ops.py:163-172`)は **uint8 のまま計算して uint8 を返す**(gaussian / mean_box / gerode / gopen / rotate_img / rescale_img / affine_warp / median / percentile)。`sobel_mag`(`ops.py:176`)は `np.hypot(uint8, uint8)` → **float16**。`threshold`(`ops.py:240`)は `v > 0.5` が全画素 True。
  - 拒否もされない: `api._check_input_sort`(`api.py:1089-1103`)は `dtype.kind in "biufc"` と ndim だけを見る。
- **cv2 ラッパの dtype 往復**: `cv_median` は `_u8(v)`(`backends.py:72-73`: clip → ×255 → uint8)で 1 往復、`cv_bilateral` は `astype(float32)` → `astype(float64)`(`backends.py:217-218`)、`cv_clahe` / `cv_otsu` / `cv_canny` も `_u8` 往復。往復コストは 2048² で **約 17 ms(u8→f64 /255 が 17.5 ms、f64→f32 5.1 ms)** — cv2 の本体(GaussianBlur u8 0.84〜1.05 ms、medianBlur u8 3.4 ms)より **往復のほうが 5〜20 倍高い**。
- **kornia 経路**(`backends_kornia.py:77-84`): clip(コピー)→ float32(コピー)→ tensor → 戻りで float64(コピー)、バッチ無し、op ごとに `torch.as_tensor`。CPU torch なので 2048² gaussian 39 ms(scipy 58 ms よりは速いが cv2 8.6 ms に負ける)。
- **実際に走ったバックエンド**: 表の module 列。全 op で fallback 0 件(ledger で確認)。同名衝突で捨てられた 4 件(`ops.DROPPED_DUPLICATES` = laplace / dyn_threshold / local_max / edges_sub_pix)は backends_auto 版が勝っている(`ops.py:995-1003`)。

### 1.4 1080p(1920×1080 = 2.07 Mpx)の fps — 30 fps(62 Mpx/s)予算

| 判定 | op(fps) |
|---|---|
| **30 fps 以上(25 op)** | cv_gaussian 279 / threshold 215 / cv_box 184 / invert 118 / cv_bilateral 107 / area_frac 101 / cv_open 91 / blob_count 80 / count_obj 80 / mean_box 69 / otsu 59 / xkor_gaussian 58 / reg_erode 58 / cv_canny 54 / cv_otsu 53 / **gaussian 53** / gamma 53 / reg_dilate 51 / gauss_filter 48 / cv_clahe 48 / cv_median 46 / cv_scharr 32 / opening_circle 32 / dyn_threshold 30 |
| 10〜30 fps(29 op) | gerode 30 / unsharp 29 / rgb1_to_gray 29 / fill_holes 26 / remove_small 26 / cfa_to_rgb 25 / select_largest 25 / zoom_image_size 23 / circularity 23 / **sobel_mag 21** / sk_butterworth 20 / equalize 18 / log 18 / gopen 17 / trans_from_rgb 17 / std_filter 16 / tophat 14 / **canny 14** / fft_image 11 / dist_transform 10 |
| 3〜10 fps | rescale_img 9.9 / lowpass 8.5 / rotate_img 8.1 / affine_warp 8.1 / rotate_image 8.0 / highpass 7.8 / corner_response 6.9 / principal_comp 5.7 / clahe 5.4 |
| **10 倍以上不足** | **median 1.1 / percentile 1.1**(+ 512² 実測から換算: bilateral ≈ 1 fps、ncc_locate ≈ 0.5 fps、sk_tv ≈ 0.25 fps、shape_locate ≈ 0.04 fps) |

読み: **1 op 単体**なら半数弱が届くが、動画パイプラインは 3〜6 op を連ねるので、**「コア実装の 5-op 連鎖」は 1080p で 111 ms = 9 fps**(§1.6 の CPU chain)。cv2 twin に載せ替えられれば同じ連鎖が ~20 ms 台。

### 1.5 3-D volume(128³ = 2.1 M voxel、16 MB f64)

| op | ms (f64) | tm× | ms (u8 in) | out dtype (u8) | GPU(RTX 5090)ms | GPU 倍率 |
|---|---:|---:|---:|---|---:|---:|
| vol_gaussian | 33.5 | 1.0 | 18.4 | **uint8** | 14.8(転送込み) | 2.3× |
| vol_median | **539.8** | 1.0 | 525.2 | **uint8** | 25.1 | **21×** |
| vol_erode | 53.0 | 1.0 | 36.7 | **uint8** | 14.3 | 3.7× |
| vol_threshold | 4.6 | 1.1 | 4.6 | float64 | 14.0 | 0.3×(転送負け) |
| vol_count | 6.1 | 0.6 | 8.2 | float | — | — |
| vol_dilation_ball | 35.6 | 1.1 | 8.6 | float64(u8 は 9×) | — | — |
| vol_opening_ball | 39.9 | 1.1 | 32.7 | float64 | — | — |
| macro_vol_denoise | 44.8 | 2.0 | 48.5 | float64(u8 は 17×) | — | — |

3-D も uint8 問題は同じ(`ops.py:725-738`)。GPU は単発でも median が 21 倍(`docs/GPU_ACCEL_PLAN.md` の「~64×」は 128³×4 バッチ・常駐での値で、単発転送込みはこの表の通り)。

### 1.6 既存 accel / GPU パイプライン(`accel.py`, `accel_vol.py`)

`accel.run_batch` = H2D → op → D2H(`accel.py:769-774`)、`run_pipeline` = 転送 1 回で op 連鎖(`accel.py:777-796`)。loco venv(cu128)で RTX 5090、同期つき最小時間。「CPU RT」は `ops.RT` 直接(numpy 1.24 環境)。

| 形状 | 転送のみ | gaussian GPU / CPU | median GPU / CPU | bilateral GPU / CPU | lowpass GPU / CPU | threshold GPU / CPU | 5-op 連鎖 GPU 転送込み / **常駐計算のみ** / CPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| 512² ×1 | 1.25 ms | 2.1 / 2.1 | 2.2 / 111 | 3.7 / 121 | 1.6 / 11.1 | 1.4 / 0.54 | 2.6 / **1.17** / 13.7 |
| 512² ×8 | 9.4 | 10.0 / 16.6 | 15.0 / 892 | 12.3 / 968 | 14.3 / 90.8 | 9.6 / 4.4 | 15.9 / **1.59** / 111 |
| 1080p ×1 | 13.7 | 14.1 / 18.9 | 18.2 / 880 | 14.0 / 986 | 16.0 / 96 | 11.6 / 4.6 | 16.1 / **2.08** / 111 |
| 1080p ×8 | 110 | 125 / 155 | 132 / 7046 | 116 / 7859 | 81 / 746 | 78 / 37.7 | 84 / **3.71** / 926 |
| 2048² ×1 | 19.7 | 20.5 / 58.2 | 37.9 / 1784 | 23.2 / 1964 | 26.1 / 272 | 27.7 / 9.4 | 33.0 / **6.73** / 291 |

読み:
- **転送床 = 1080p 1 枚 13.7 ms、8 枚 110 ms**(float32 で片道 8.3 MB/枚)。gaussian のような軽い op は転送に埋まる(GPU 14.1 vs CPU 18.9)。threshold は GPU が負ける。
- **常駐計算だけなら 1080p 5-op = 2.1 ms(480 fps 相当)**、8 枚バッチで 3.7 ms(2160 fps 相当)。**動画でフレームを GPU に置いたまま回せば 30 fps 予算の 6 %**。現状の `api.apply(device="cuda")` は **1 枚ずつ `run_batch(.., [v], ..)`**(`api.py:1173`)なので毎回転送を払う。
- GPU メモリ: 1080p×8 の 5-op で 3.4 GB ピーク(中間を全部 float32 で持つ。`_unfold_reflect` 系の median/percentile が k²倍のバッファを作る)。32 GB あるので 1080p リングなら余裕、4K×バッチは要注意。
- CPU torch(グローバル python)の `run_batch` は scipy より速い op(median 2048² 240 ms vs 1783 ms、bilateral 99 vs 2003)もあるが、gaussian 30 vs 58 程度で cv2 8.6 には及ばず、vol_erode は **CPU torch が scipy より遅い**(148 vs 54 ms)。CPU の高速経路として torch を使う理由は薄い。

### 1.7 facade のオーバーヘッド(2048²)

| 項目 | 実測 | 出典 |
|---|---:|---|
| `find_op` 線形走査(先頭 / 末尾 / HALCON 別名) | 0.1 / 9.0 / 3.0 µs | `api.py:921-944`(860 要素の list 走査、1 apply で 2 回: `api.py:1239`, `1262`) |
| `api.apply(identity, 512²)` vs `RT` 直接 | 2 µs vs 0.1 µs | `api.py:1238-1276` |
| **`_coerce_input`(region f64)** | **17.6 ms**(`np.unique` 16.9 ms) | `api.py:1035-1038`: 毎回 `np.unique(a)`(ソート O(N log N)) |
| `api.apply(reg_erode)` / 同 `coerce=False` / `RT` 直接 | **35.0 / 18.2 / 17.8 ms** | region op は **coerce で 2 倍**になる |
| `sanitize`(image / region) | 1.9 / 6.1 ms | `backend_safe.py:387-389` isfinite 全走査、region は `region01` でさらに 2 走査(`:361`) |
| 段間 `np.clip`(新規配列) | 8.3 ms | `ops.py:1077-1084`(`_apply` は毎段 clip)、`api.run_pipeline` の CPU 経路は clip しない(`api.py:1338-1348`) |
| u8→f64 `/255` / f64→f32 | 17.5 / 5.1 ms | `video.py:62-72`, `accel.py:38-42` |
| `_try_accel` の辞書再構築 | 90 要素の内包表記を **毎 apply** | `api.py:1164` |

→ **facade の固定費は 1 op あたり数 ms(2048²)**で、op 本体(数十〜数百 ms)に比べれば小さい。ただし region op の `np.unique` と、動画で 30 fps × 5 op = 150 回/s 掛かる `sanitize`+`clip` は **1080p で 1 フレーム 10〜15 ms 分**になり、無視できなくなる。

### 1.8 タイル分割・フレーム並列・float32 の追加実測(2048²、`scale.process_tiled_mt` = 既存)

| op | 全体 | tiled w1 | **w8** | w16 | 全体との最大差 |
|---|---:|---:|---:|---:|---:|
| gaussian | 59.3 | 60.2 | **14.5(4.1×)** | 14.9 | 0.0 |
| median(平滑画像) | 196.6 | 228.0 | **55.2(3.6×)** | 51.9 | 0.0 |
| gerode | 51.0 | 51.3 | **13.4(3.8×)** | 13.3 | 0.0 |
| sobel_mag | 130.2 | 104.0 | 26.8(4.9×) | 22.1 | **0.98(不一致)** |
| canny | 192.2 | 152.6 | 32.9(5.8×) | 29.1 | **1.0(不一致)** |
| otsu | 41.5 | 59.0 | 29.6(1.4×) | 32.1 | **1.0(不一致)** |

- 局所 op は **タイル並列で 4 倍**(numpy/scipy が C カーネルで GIL を離す。`scale.py:122-160`)。8 → 16 スレッドで伸びないのは **メモリ帯域律速**。
- ★**`scale_class` は「edges」を tile_safe と分類する**(`scale.py:27,29`)が、`sobel_mag` / `canny` は `_norm`(画像全体の max で割る、`ops.py:128-130`)を含むため **タイル化で結果が変わる**(max 差 0.98)。既存 `docs` の「bit-identical」主張はカテゴリ判定が粗い。tiling を op 配線に載せるなら **op ごとに "global reduction を含むか" のフラグ**が要る(§4 (c) のリスク)。
- **フレーム並列(8 スレッド、8 枚の 1080p)**: gaussian 158.7 → 34.3 ms(4.6×、233 fps)、sobel_mag 4.7×、cv_median 4.6×、otsu 2.3×、cv_gaussian は 1.5×(cv2 は既に内部 24 スレッドなので伸びない)。
- **float32 を scipy に渡しても 10〜25 % しか速くならない**(gaussian 59→48、median 92→87、sobel 111→85)。「dtype を小さくする」だけでは効かず、**uint8 + cv2/IPP の整数 SIMD カーネル**(gaussian 1.05 ms、median 3.4 ms、open 2.2 ms、Scharr×2 f32 9.5 ms)に載せて初めて桁が変わる。

---

## 2. コードに見る根本原因

### 2.1 dtype と契約

- 公開契約は「image = H×W float64 in [0,1]」(`api.py:19-22`、`docs/ADDING_OPS.md:21`)。実装は **float64 決め打ち**: `ops._apply` は `np.asarray(img, np.float64)`(`ops.py:1078`)、backends_auto の各 fn は頭で `x = np.asarray(v, np.float64)`(例 `backends_auto.py:200-203`, `246-250`, `280-286`; ファイル内 72 箇所)、`_norm` / `_signed01` / `_shift_edge` も float64 化(`ops.py:128-146`, `backend_safe.py:263-265`)。
- **uint8 の受け口が無い**: `_check_input_sort` は dtype の kind と ndim だけ(`api.py:1089-1103`)。コア op は `ndimage.*` を dtype 無指定で呼ぶ(`ops.py:163-178`)ので、uint8 は **uint8 のまま切り捨て計算**される(§1.3)。「fail-closed」でも「変換」でもない **第 3 の状態(黙って別物)**。
- 逆方向の昇格: cv2/skimage ラッパは `_u8`(`backends.py:72-73`)/`astype(np.float32)`(`:218`, `:251-255`)で毎回往復。`astype(np.float64)` は ops.py 26 / backends.py 31 / backends_auto.py 63 箇所、`np.clip` は ops.py 24 / backends_auto.py 26 箇所(それぞれが全画素の新規配列)。

### 2.2 コピー・中間配列

- **`output=` の利用は 0 箇所**(`rg "output=" ops.py backends*.py filters*.py volops.py` → 0)。scipy.ndimage は全 op が `output=` を受けるので、in-place / 事前確保バッファが使えるのに使っていない。ただし実測では gaussian の `output=` 指定は **速くならない**(57.3 vs 57.4 ms)— 得られるのは **常駐メモリと GC 圧の削減**(動画のフレームループでの効き)であり速度ではない。
- 中間配列の多い op: `_bilateral`(`ops.py:203-211`)= 25 回のシフト(`_shift_edge` は `np.pad` で毎回コピー、`ops.py:133-146`)× 2 の exp → 6×; `_corner_response`(`ops.py:680-685`)= gx, gy, 3 つの積、3 つの gaussian、応答 → 8×; `_fft_mask`(`ops.py:219-224`)= fft2(complex128 16 B/px)+ mask 積 + ifft2 + real → 7.1×; `_std_filter`(`:214-216`)4×; `_ncc_map`(`:426-460`)は `ndimage.correlate`(テンプレサイズの直接畳み込み、O(N·T²))+ 2 つの uniform_filter → RSS 21×; `_shape_locate`(`:692-704`)はそれを **12 回転ぶん直列**。
- `sanitize` / `region01` の追加走査(`backend_safe.py:376-403`, `344-363`)は guard 付き 475 op の全出力に掛かる。`_finite` の失敗時 `np.where` はさらに 1 枚。

### 2.3 Python レベルの画素ループ

- registry 経路に残る **H×W 二重ループ**: `image_gray.gen_cooc_matrix`(`image_gray.py:103-121`、GLCM を画素ごとに Python で加算)、`backends_regions2._max_all_ones_rect`(`backends_regions2.py:245-262`、`r2_inner_rectangle1` と `regionprops3d.py:342` から呼ばれる)。コア filters には無い。
- **ベクトル化はされているが反復回数×全画素の op**: `_bilateral` 25 パス、`monotony` 8 パス(`backends_auto.py:173-179`、`np.roll` 2 回/パス)、`_clahe` の nb² タイル×補間(`ops.py:631-676`)、`_shape_locate` 12 回転、`flow.optical_flow_lk` の level×iters(`flow.py:79-138`、1 反復で ~15 枚の全画面 float64 中間 = 1080p で 437 MB 実測)、`flow.optical_flow_hs` iters=50 で **14.7 s**(`flow.py:146-227`)。
- 合計 139 箇所の `for … in range(shape)` 型ループ(tests/tools 除く)だが、大半は algo 層(`algo.py`、意図的な参照実装)、contours_xld2、mesh、synth 等の非画素経路。

### 2.4 全体処理 vs タイル

- 全 op が **画像全体を 1 配列で処理**。タイル化の道具 `scale.process_tiled` / `process_tiled_mt` / `process_tiled_memmap` は **存在する**(`scale.py:108-188`)が、facade(`api.apply` / `run_pipeline` / `engine`)からは呼ばれず、`scale_class` のカテゴリ判定は `_norm` を持つ edges を誤って tile_safe に入れる(§1.8)。

### 2.5 スレッド

- numpy(OpenBLAS 24)/ cv2(24)/ torch(24)はマルチスレッド設定だが、**測った op の大半は scipy.ndimage(単スレッド)か numpy 要素演算(単スレッド)**で、BLAS は使われない。多コアが効いているのは cv2 ラッパだけ。cv2 のスレッド数は `fsruntime._bound_cv2_threads`(`fsruntime.py:388-396`)/ Studio `set_system` から制御可能。
- 並列実行器は `scale.process_tiled_mt`(ThreadPoolExecutor)以外に無い。`videops.per_frame`(`videops.py:237-257`)と `optical_flow_sequence`(`:282-315`)は **直列 for ループ**。

### 2.6 accel パイプラインが既に持つもの

- 2-D 90 mapping(`accel.ACCEL`, `accel.py:622-696` + twin 別名)、3-D 10(`accel_vol.VOL_ACCEL`, `accel_vol.py:166-178`)、NCC(`accel_match.py`)、形状マッチ(`shapematch_gpu.py`)。parity ゲート(`accel.parity`, `accel.py:808-855`、interior <5e-3、5 点 a/b スイープ、定数・量子化画像を含む)。
- champion → GPU/CPU 区間分割 `accel_bridge.plan/run`(`accel_bridge.py:99-148`)。区間の境目で **list[float64 ndarray] に戻す**(`:135-146`)ので、CPU 区間を挟むたびに D2H/H2D + f32↔f64 が発生。
- facade からの経路: `api.apply(device=…)` → `_try_accel` → **バッチ 1 枚の `run_batch`**(`api.py:1151-1179`)、`api.run_pipeline(device=…)` → `accel_bridge.run`(`api.py:1312-1336`)。**フレーム列を GPU に常駐させる入口は無い**。
- 入口の転送: `_to_batch` は `np.stack([np.asarray(i, np.float32) …])`(`accel.py:38-42`)= f64→f32 のコピー + stack のコピー、戻りは `.astype(np.float64)`(`:45-46`)。1080p 1 枚で 13.7 ms の転送床のうち、この CPU 側のコピーが 5〜8 ms を占める(§1.7 の f64→f32 5.1 ms)。

---

## 3. 動画・画像列処理

### 3.1 いま在るもの(実コードで確認)

| モジュール | 役割 | 動画観点の性質 |
|---|---|---|
| `video.py` | `iter_frames`(generator、`video.py:116-195`)/ `read_frames`(全読み `np.stack`、`:198-214`)/ `frame_pairs` / `write_video` / `probe` | **ストリーミングはある**。ただし 1 フレームごとに `_to01`(uint8→f64 /255 + clip = 2 コピー、`:62-72`)と `_coerce`(RGB→gray を `a @ _LUMA` の float64 matmul、`:75-97`)を通す。imageio 優先、cv2 は fallback(`:99-113`) |
| `acquire.py` | `Camera.grab/stream`(`acquire.py:245-273`)= OpenCV / dir / callable / GenICam / Basler | 同じ `_coerce` で毎フレーム float64 化(`:88-108`) |
| `videops.py` | temporal_mean/median/std/max/min、frame_difference、background_subtraction、temporal_gradient、motion_energy、moving_average、spatiotemporal_gaussian/sobel、per_frame、flicker_reduce、optical_flow_sequence | **全部 (T,H,W) float64 を一括で受ける**(`_as_video`, `videops.py:42-71`: asarray + isfinite 全走査)。状態を跨いで持つ設計は無い |
| `flow.py` / `motion.py` / `sceneflow.py` | LK/HS 密フロー、支配運動、FoE/TTC | 2 フレーム関数(pure)。LK 1080p 1.26 s / 437 MB、HS iters=50 で 14.7 s |
| `events.py` | DVS 事象、time_surface(T スタック)、contrast_maximization | `time_surface` は T ループ内で 2 フレーム関数を呼ぶ(`events.py:158-162`)= ストリーム化しやすい形だが入口はスタック |
| `engine.py` / `graphengine.py` | pipeline / DAG の実行、`run_stepwise` は全中間結果を保持(`engine.py:221-237`) | フレーム概念無し(1 画像 → 1 結果) |
| `fsruntime.py` | `FullseyeRuntime.inspect` = 1 フレーム 1 サイクル、deadline は事後判定(`fsruntime.py:454-470`) | サイクル型。ストリーム/リングは無い |
| `backends_typed.py` | `video` sort の registry op は **2 つ**(`tb_temporal_bandpass`, `tb_temporal_band_power`、motionmag 由来) | どちらも (T,H,W) 一括 |
| `vloop.py` / `sim_source.py` | 遅延つき閉ループ台(MuJoCo)/ F4 契約 | 高速ビジョン計画(`docs/HIGHSPEED_VISION.md`)の実験台。op の速度が遅延に直結 |

### 3.2 実測(動画経路)

| 項目 | 実測 | 意味 |
|---|---:|---|
| `video.iter_frames(gray=True)` 1080p H.264 | **18.3 fps**、RSS ピーク +123 MB | 変換込み 55 ms/フレーム |
| 同 `gray=False`(RGB f64) | 21.3 fps | gray の方が遅い = 輝度 matmul が支配 |
| `read_frames` 30 フレーム | 17.0 fps、**475 MB**(RSS ピーク 947 MB) | 1 秒の 1080p で 0.5〜1 GB |
| cv2 `VideoCapture.read()` 素読み(BGR uint8) | **203.8 fps** | デコード自体は 4.9 ms/フレーム |
| cv2 素読み + `cvtColor` gray uint8 | 187.2 fps | gray 変換は 0.4 ms |
| `write_video` 30 フレーム 1080p | 582 ms(19 ms/フレーム) | imageio-ffmpeg 経由 |
| temporal_median(16×540×960 = 63 MB) | 113 ms(7.1 ms/フレーム)、1.1× | `np.median(axis=0)` のソート |
| background_subtraction | 166 ms、**2.1×**(vid − bg の (T,H,W) 差分を丸ごと作る、`videops.py:185-186`) | |
| moving_average(w=3) | 24 ms、1.0× | `uniform_filter1d` |
| spatiotemporal_gaussian | 73 ms、1.0× | |
| per_frame(gaussian) | 96 ms(6 ms/フレーム)、1.2× | 直列 |
| optical_flow_sequence(LK、4 フレーム) | 839 ms(280 ms/対 @540×960) | 1080p 換算 1.1 s/対 |
| simulate_events 1080p 対 | 70 ms、79 MB | 14 fps |
| frame_difference 2 フレーム 1080p | 20 ms、63 MB | |

**codec/I/O の結論**: この PC では **imageio-ffmpeg(同梱 ffmpeg 7.1)と cv2(FFMPEG/avcodec 61)の両方が使える**。デコード性能は十分(204 fps)で、**ボトルネックは 100 % Python 側の毎フレーム float64 化**。`av`(PyAV)は無い。

### 3.3 動画経路に必要なもの(現状との差)

1. **ストリーミング**: `iter_frames` は既に generator。欠けているのは **`dtype="uint8"` で素通しする口**と、gray 変換を cv2 `cvtColor`(0.4 ms)に任せる分岐。これだけで 18 → ~180 fps。
2. **リングバッファ**: temporal median / 背景差分 / moving average / temporal gradient / time_surface / optical flow(前フレーム保持)は **窓 N フレームの状態**があれば 1 フレームずつ出せる。今は (T,H,W) 一括なので **メモリ = T × フレーム**(1 秒 = 0.5 GB f64、uint8 なら 62 MB)。リングなら **N × フレーム**(N=5 の uint8 1080p = 10 MB)。
3. **状態つき op の契約**: registry の `Op` は `fn(v, a, b)` の純関数(`ops.py:795-802`)で状態を表せない。表現案(§4 (d)): `Op` に `stateful: bool` と `state_factory()` を足し、`fn(v, a, b, state)` 規約の 2 番目のシグネチャを持つ、または **`video` sort の op を "reducer"** として `push(frame) -> out` を持つクラスで登録する。進化(`decode`/`_candidates`)は in_sort が `video` の op を既に別枠で扱える(`backends_typed.py:133-137` の `_NEW_SORTS`)ので、**genome 互換を壊さずに追加できる**。
4. **uint8 ゼロコピー経路**: 契約が float64 なので、今は uint8 を入れると壊れる(§1.3)。最低限 **入口で fail-closed(拒否 or 明示変換)**にし、その上で「uint8 で計算できる op」(cv2 twin)だけを uint8 のまま通す表を持つ。
5. **タイル**: 1080p は 16 MB f64 なので **L2 溢れによる 1.5〜1.8 倍**(512²→2048² で 28×、理想 16×)を除けば大きな問題ではない。4K 以上・複数フレーム同時処理で効く。既存 `process_tiled_mt` の 4 倍は魅力だが §1.8 の `_norm` 問題を先に解く。
6. **fps 予算**: §1.4。コア実装で 30 fps に届くのは 25/56、**連鎖なら 9 fps**。cv2 twin なら連鎖でも 30〜50 fps、GPU 常駐なら 480 fps 相当(計算のみ)。
7. **GPU**: 常駐リング(`torch` テンソルのまま N フレーム保持)+ `accel.run_pipeline` の「転送を外した版」(`accel.ACCEL[name][0](t, a, b, dev)` を直接連結)で 2.1 ms/フレーム。D2H は **結果(region/feature)だけ**にする。
8. **メモリ上限**: 1080p f64 1 枚 16.6 MB、op の中間 1〜8×、region op の `np.unique` が別に 1 枚、5-op 連鎖で **~100〜150 MB/フレーム**の瞬間ピーク。リング N=5 + 中間 8× でも 300 MB 以内 → 128 GB の PC では無問題だが、**組込み(evis/ロボ)側では uint8 リング + cv2 in-place が要る**。

---

## 4. 選択肢と推奨(実測の効き ÷ 手間 で順位づけ)

「効き」は §1 の実測から、「手間」は触るファイル数と契約変更の有無から。**fail-soft/ledger(`backend_safe.guard` → `record` → `sanitize`)は全案で温存**し、新経路の失敗も同じ ledger に `source="fast"` 等で記録する。

| 順位 | 案 | 仕組み | 期待効果(実測根拠) | 正しさのリスク | テスト戦略 | 手間 |
|---|---|---|---|---|---|---|
| **1** | **(h) ベンチ harness `tools/bench_ops.py` + JSON ベースライン** | 本調査の `prof_ops.py` を repo に移し、op 集合 × サイズ × dtype の (ms, Mpx/s, tm×, rss×, out dtype, fallback 数) を `out/bench_ops_baseline.json` に保存。CI/手動で **±X %(既定 30 %、熱ぶれ考慮)** 超過を検出。ノイズ入り画像を必ず含める(median の 10 倍差) | 効果は「退行を捕まえる」こと。§0-a の 1.7 倍ぶれがあるので **相対比較(cv2 twin vs core、GPU vs CPU)を同一 run 内で出す**設計にする | 無し(read-only) | harness 自身のスモーク(3 op、64²)。`tests/test_bench_ops.py` | **小**(1 ファイル + テスト) |
| **2** | **(a′) コア op の CPU 高速 twin テーブル(cv2/IPP)+ parity ゲート + uint8 fail-closed** | `accel.ACCEL` と同じ構造で `fast.FAST = {core_name: (fn_cv2, dtype_policy)}` を作り、`api._apply_impl` の `_call` で **`device="cpu"` かつ `fast` 有効かつ parity 済み**なら twin を呼ぶ(既定 ON にするかは parity 結果次第; まず opt-in `FULLSEYE_FAST=1` / `apply(fast=True)`)。同時に `_check_input_sort` に **dtype 方針**(uint8 → `on_error="raise"` なら拒否、既定は `/255` 明示変換 + ledger `source="input"`)を追加 | gaussian **6.8×**、median **41×**(uint8 twin なら 500×)、box 5×、gray open 9×、canny 5×、CLAHE 9×、otsu 1.1×(効かない op は載せない)。1080p 5-op 連鎖 111 → 推定 20〜25 ms(30 fps 圏内) | **境界規約と丸め**: cv2 の border(reflect101)と scipy(reflect=symmetric)は違う(accel で同じ罠を踏み修正済 `docs/GPU_ACCEL_PLAN.md` 2026-08-31 Batch 0)。uint8 twin は 1/255 量子化を伴う。→ **accel.parity と同じ 5 点 a/b × 6 画像(定数・量子化含む)の interior <5e-3 ゲートを通った op だけ載せる**。「速いが違う」は作らない | `tests/test_fast_parity.py`(ゲート自動化)、`tests/test_api.py` に uint8 拒否/変換のケース、bench で twin/コアの同 run 比較 | **中**(新規 1 ファイル + api 数行 + テスト) |
| **3** | **(d) `VideoPipeline` / 状態つき op 契約 + リングバッファ + uint8 ストリーム** | ① `video.iter_frames(dtype="uint8", gray_backend="cv2")`(18 → ~180 fps); ② `FrameRing(n, dtype)` (固定長 deque + 事前確保 (n,H,W) バッファ); ③ 状態つき op: `class TemporalOp: def push(self, frame) -> out`、registry には `Op(stateful=True, state_factory=…)` を追加し `in_sort="video"` で登録(genome 経路は `_NEW_SORTS` 扱いで既存 decode 不変); ④ `VideoPipeline(stages, ring=n, device=…)` が reader → ring → 段 → 結果だけ返す。temporal_median/背景差分/moving_average/time_surface/optical_flow を ring 版で提供 | 読み込み 11×、メモリ **T× → N×**(1 秒 1080p: 475 MB → N=5 uint8 で 10 MB)、temporal median は ring N=5 で 1080p 1 フレーム ~5 ms 見込み(63 MB 16 フレームで 113 ms から換算) | (T,H,W) 一括版との **数値一致**(窓の端処理: 一括版は全 T の中央値、ring 版は窓中央値 = 別物なので **同名にしない**。`temporal_median_window` 等) | ring 版 vs 一括版を **同じ窓幅**で比較する差分テスト、状態リセットのテスト、フレーム落ち(shape 不一致)は fail-closed | **中〜大**(video.py + 新規 videostream.py + ops.Op 拡張 + api) |
| 4 | (g) GPU フレームバッチ/常駐リング | `accel` に `Resident(device)`(テンソルのまま N フレーム保持)と `run_resident(steps, tensor)` を足し、VideoPipeline の `device="cuda"` で使う。D2H は終端(region/feature)だけ | 1080p 5-op **2.1 ms/フレーム(計算のみ)**、転送込みでも 16 ms。CPU 連鎖 111 ms から **50×** | accel の既存 parity(90/90 faithful)に依存。ring 版 temporal op の GPU 版は新規 parity 要 | 既存 `tests/test_accel_pipeline.py` 型 + loco venv でのみ走る GPU テスト(skip 条件) | 中(accel 数十行 + VideoPipeline 分岐)。**(d) の後** |
| 5 | (f) フレーム並列 executor | `VideoPipeline(workers=k)` で **フレーム単位**に ThreadPoolExecutor(GIL は numpy/scipy が離す)。順序保持は `ex.map` | 1080p gaussian 4.6×(233 fps)、sobel 4.7×、cv_median 4.6×。cv2 twin(既に 24 スレッド)には効かない(1.5×)。**状態つき op とは相性が悪い**(順序依存) | 状態つき段では並列不可 → パイプラインを「純関数区間(並列)/状態区間(直列)」に plan で分割(accel_bridge.plan と同型) | 並列/直列の結果一致テスト | 小〜中。**(a′) を入れると効きが減る**ので順位は下 |
| 6 | (c) 大フレームのハローつきタイル | 既存 `scale.process_tiled_mt` を `VideoPipeline` の「純関数・局所 op 区間」に配線。**`Op` に `global_reduction: bool`(`_norm`/`_signed01`/`otsu` 等)を持たせ、それを含む op は自動で除外** | 2048² で 4×(gaussian 59 → 14.5 ms、median 3.6×)。1080p では L2 溢れ分(~1.5×)。メモリは tile² に上限 | §1.8 の通り **edges/segmentation を誤分類**しており、sobel_mag/canny/otsu はタイルで別解になる。フラグ無しで配線してはいけない | 全 tile_safe op の tiled vs whole の bit 一致テスト(既存 `tests/test_scale.py` を op 全数に拡張) | 中(フラグ付与が 860 op に及ぶ → まず core 76 + cv_ 76) |
| 7 | (b) in-place / `out=` 配線 | guard に `out=` を通す、`_norm` を `np.divide(x, mx, out=x)`、段間 clip を `np.clip(v, 0, 1, out=v)`(自分の配列のときだけ) | 速度は **ほぼ変わらない**(gaussian `output=` 57.3 vs 57.4 ms、clip out= 8.7 vs 8.3)。得られるのはピークメモリ −1×(2×→1× の op)と GC 圧。1080p 30 fps で毎秒 150 枚の 16 MB 配列確保を消せる | 入力を書き換える op が混ざると **`input_mutated`** になる(今は 0 件)。`identity` は入力を共有して返すので in-place 後段が **入力を破壊**しうる | harness の `input_mutated` / `shares_mem` 列で常時監視 | 小だが効果も小。(d) の ring バッファ内で「事前確保 + out=」として実装するのが自然 |
| 8 | (e) メモリプール / スクラッチ | op ごとの中間配列(`_corner_response` 8×、FFT 7×)を `scratch(shape, dtype)` から借りる | 8× → 2〜3× に下げられるが速度は変わらない。GPU 側は torch のキャッシュアロケータが既にやっている | スレッド安全性(フレーム並列と競合)、ライフタイム | — | 中。**(b)(d) が済んでから**、必要なら |

補足(実測から落ちた案):
- **float32 一本化**(契約変更)は scipy 経路では 10〜25 % しか稼げず(§1.8)、860 op の契約を揺らすコストに見合わない。**dtype を変えるなら uint8 + 整数カーネル(cv2)に振り切る**方が桁が違う。
- **CPU torch を高速経路にする**案は、median/bilateral では scipy に勝つが cv2 に負け、vol_erode は scipy より遅い(§1.6)。GPU 専用に留める。

### 4.1 fail-soft / ledger との整合(全案共通)

- 高速 twin(a′)・GPU(g)・タイル(c)は **すべて "core と同じ答えを速く出す" 経路**なので、`accel` と同じ設計原則(`docs/GPU_ACCEL_PLAN.md` 設計原則: faithful なものだけ載せる)を踏襲する。twin が失敗したら **ledger に `source="fast"` で記録して core にフォールバック**、`on_error="raise"` なら再送出(`api._try_accel` と同型、`api.py:1151-1179`)。
- uint8 の扱いは **on_error 方針に従う**: `"raise"` → 拒否(fail-closed)、既定 → `/255` に明示変換 + ledger `source="input"`(今の「黙って壊れる」を「記録して直す」に変える)。既存の float64 呼び出しは 1 ビットも変えない。
- 状態つき op は **fail-soft の意味が変わる**(1 フレーム落としたら状態が汚れる)。ring 版は失敗時に **状態をリセットして記録**する(汚れた状態で続けない)。

### 4.2 各案の「効き」を一枚に

| 指標 | 現状 | (a′) cv2 twin | (d)+(g) GPU 常駐 | (c) tiling 4×(局所 op) | (f) フレーム並列 |
|---|---:|---:|---:|---:|---:|
| 1080p gaussian | 19 ms | **3.6 ms** | 0.4 ms(常駐)/14 ms(転送込み) | ~5 ms | 4.3 ms(8 枚並列の 1 枚あたり) |
| 1080p median 5×5 | 894 ms | **21.6 ms**(uint8 生なら ~2 ms) | 3.6 ms(常駐) | ~250 ms | ~190 ms |
| 1080p 5-op 連鎖 | 111 ms | ~20〜25 ms(推定、gaussian+sobel+threshold+dilate+erode の twin 合算) | **2.1 ms** | ~30 ms | ~25 ms |
| 動画読み 1080p gray | 18 fps | — | — | — | — |
| 動画読み uint8 素通し(d) | — | **~180 fps** | 同左 | — | — |
| 1 秒 1080p の常駐メモリ | 475 MB(f64 一括) | 同左 | GPU 側 ~60 MB(f32 ring 5) | — | — |
| 同 ring N=5 uint8(d) | — | **10 MB** | — | — | — |

### 4.3 明日着手する 3 件(順序つき)

1. **(h) `tools/bench_ops.py` + `out/bench_ops_baseline.json`** — 半日。理由: 以降の全案が「速くなったか」「壊れていないか(out dtype / fallback / mutated)」を **同じ物差し**で言う前提。今回の使い捨てスクリプトの再利用で済み、リスク 0。熱ぶれ対策として **同 run 内の相対値**と `--warm N` を必ず持つ。
2. **(a′) cv2 高速 twin テーブル + parity ゲート + uint8 fail-closed** — 1〜2 日。理由: **測定した中で最大の効き(6.8〜41×)を、契約を変えず・進化 champion を壊さず・既存の parity 手法(accel と同型)で**取れる。1080p で「コアの 5-op 連鎖 9 fps」を 30 fps 圏に入れる唯一の CPU 側の一手。uint8 の「黙って壊れる」を同時に閉じる(正しさの穴は速度の穴より先に塞ぐ)。
3. **(d) `VideoPipeline`(uint8 ストリーム reader + ring + 状態つき op 契約)** — 2〜3 日。理由: 動画対応の **構造的な欠落**(状態・リング・ストリーミング)はここでしか埋まらず、(g)(f)(c) はこの器の中の分岐として後から足せる。最初の実装範囲は reader + ring + temporal_median_window / background_subtraction_window / frame_difference / optical_flow(前フレーム保持)の 4 op + `engine` からの呼び出し。GPU 常駐(g)は (d) の `device` 引数として翌週。

やらないこと(今回の判断): float32 契約化、CPU torch の高速経路化、`output=` 配線を先にやること(速度が出ない)、`scale_class` のまま tiling を facade に載せること(誤分類)。

---

## 5. 付録

### 5.1 honest な限界

- 単一 PC・単一日の実測。**熱定常ではない**(連続 6 分の測定中に後半の op ほど暖まっている)。§0-a の教訓どおり絶対値は 1.5〜2 倍の幅を見る。GPU 側の「CPU RT」列は numpy 1.24 環境(loco venv)なので、グローバル環境(numpy 2.4.6)の数字と 1〜5 % ずれる。
- RSS ピークは 0.4 ms ポーリングなので **10 ms 未満の op では取りこぼす**(tracemalloc 側は numpy 配列のみ正確、C 内部バッファは見えない)。両方を並べたのはそのため。
- uint8 入力の測定は「契約外の入力を入れたときの挙動」であり、その出力の正しさは主張していない(むしろ壊れることを示した)。
- 動画は H.264 1080p 30 フレームを `write_video` で自作したもの 1 本。実カメラ(GenICam/Basler)経路は未測定(`acquire.py` の `_coerce` が同じなので変換コストの構造は同じ)。
- `median` の scipy 実装は内容依存(92〜1827 ms)。ベンチの入力を固定しないと比較にならない。

### 5.2 再現

- 使い捨てスクリプト(リポジトリ外): `%TEMP%\claude\…\scratchpad\prof_ops.py`(`PYTHONUTF8=1 py -3.11 prof_ops.py out.json`、~6 分)、`prof_accel.py`(`C:/dev/venvs/loco/Scripts/python.exe prof_accel.py --device cuda out.json`、~1 分)。(h) で `tools/bench_ops.py` として恒久化する。
- 追加実測(§1.8)は `scale.process_tiled_mt` / `ThreadPoolExecutor` / `cv2` を直接呼ぶ 40 行の一発スクリプト。

### 5.3 本調査で見つけた「速度以外」の不具合候補(要別途対応)

1. `api._check_input_sort`(`api.py:1089-1103`)が uint8 を通し、コア op が uint8 のまま計算する(`ops.py:163-178`, `240`, `725-738`)— 例外なしで別物の結果。
2. `scale.scale_class`(`scale.py:27,29,35-58`)が `_norm` を含む edges/segmentation を tile_safe に分類し、タイル結果が全体結果と一致しない(sobel_mag 差 0.98、canny 1.0)。
3. `api._coerce_input` の `np.unique`(`api.py:1036`)は region op を毎回 2 倍遅くする。`{0,1}` 判定は `np.isin`/min-max で O(N) にできる。
4. `api._try_accel`(`api.py:1164`)が呼ぶたびに ACCEL の逆引き辞書を作る(モジュールレベルにキャッシュ可)。

---

## 6. bench harness (実装済)

§4 の推奨 **(h)** を実装した(2026-09-03)。この調査の使い捨て profiler(`scratchpad/prof_ops.py`)を repo の恒久ツールに据えたもので、以降の (a′) cv2 twin / (d) VideoPipeline / (g) GPU 常駐 / (c) タイル が「本当に速くなったか」「壊れていないか」を **同じ 1 本の物差し**で言うための土台。

| 追加物 | 役割 |
|---|---|
| `tools/bench_ops.py` | 測定 harness + JSON ベースライン比較(CLI) |
| `tests/test_bench_ops.py` | harness 自身の契約テスト(3 op × 64² のスモーク、合成 2 倍退行の検出、未知 op の fail-closed、ノイズ画像の存在) |
| `bench/bench_ops_baseline.json` | 実測ベースライン(`--sizes 512,2048,1080p --dtypes float64`)。**`out/` は `.gitignore` 対象**なので、追跡したいベースラインは `bench/` に置く(`bench.py` は module、`bench/` は namespace dir なので `import bench` は従来どおり `bench.py` に解決する — 実測確認済み) |

### 6.1 使い方

```powershell
# 手元で 1 セット測る(既定 --set all / --sizes 512,2048,1080p / --dtypes float64)
PYTHONUTF8=1 py -3.11 tools/bench_ops.py --set core --sizes 512 --dtypes float64 --repeat 3

# op を名指し・複数サイズ・uint8 も込みで
PYTHONUTF8=1 py -3.11 tools/bench_ops.py --ops gaussian,median,cv_median --sizes 2048,1080p --dtypes float64,uint8

# ベースラインを書く(数分)
PYTHONUTF8=1 py -3.11 tools/bench_ops.py --sizes 512,2048,1080p --dtypes float64 --write-baseline bench/bench_ops_baseline.json

# 退行チェック(30 % 超で表を出して exit 1 = CI 用)
PYTHONUTF8=1 py -3.11 tools/bench_ops.py --baseline bench/bench_ops_baseline.json --tolerance 0.30
```

主なオプション: `--ops a,b,c` / `--set core|cv|all` / `--sizes 512,2048,1080p|WxH` / `--dtypes float64,uint8,float32` / `--images noisy,quantised,constant` / `--warm N`(既定 1)/ `--repeat N`(既定 3、**中央値**)/ `--out`(既定 `out/bench_ops.json`)/ `--baseline` / `--write-baseline` / `--tolerance`(既定 0.30)/ `--device cpu|cuda` / `--quiet`。

### 6.2 1 行に載るもの(速度だけを見ない)

`ms`(repeat の中央値。最小値だと外れ値で嘘の改善が出る)、`mpx_s`、`tm_peak_x`(tracemalloc ピーク ÷ 入力バイト)、`rss_peak_x`(0.4 ms ポーリング)、`out_dtype` / `out_shape`、`fallbacks`(`backend_safe.mark` / `events_since` で数えた **1 呼び出しあたり**の降格件数)、`input_mutated`、`shares_mem`(`np.shares_memory`)、`module`(実装モジュール)、`twin` / `accel_key`。**「速くなったが uint8 を返すようになった」「速くなったが毎回 fallback している」を同じ表で捕まえる**のが狙い(§1.3 の「黙って別物」を速度改善で再生産しないため)。

* 例外は握り潰さない: 行に `error` を載せて続行し、最後に件数を出す。時間予算外の重い op は行ごと消さず `skipped` に理由を残す(消すと「発見ゼロ」に化ける)。
* 未知の op 名は **fail-closed**(近い名前を挙げて exit 2)。ただし `--set` に含まれる任意バックエンド op(`cv_*`/`sk_*`/`xkor_*`)がその環境に無いのは打ち間違いではないので、落とさず `header.set_absent_ops` に記録する。

### 6.3 入力は「ノイズ入り」と「量子化」の 2 本が既定

§5.1 のとおり `median`/`percentile` は **内容で 10 倍変わる**。harness は同じシーンを

* `noisy` — 円板 60 個 + 照明勾配 + 3 % ガウスノイズ(実画像側 = 最悪側)
* `quantised` — ノイズ無し・16 階調(同値だらけ = 速い側)
* `constant` — 定数 0.42(縮退。`--images` で追加可能)

で作り、既定は `noisy,quantised` の 2 本。**ノイズ画像を外した `--images` は CLI が拒否する**(最悪側を隠すベンチは退行検出の役に立たない)。実測でも 512² `median` は noisy 113 ms / quantised 18.6 ms(**6.1 倍**)、`clahe` は 20.7 / 7.9 ms と分かれた。seed は固定(既定 7)なので run 間で入力は同一。

### 6.4 相対比較は同一 run の中でだけ

熱定常でないこの PC では絶対値が 1.5〜1.7 倍動く(§5.1)。そこで:

* **cv2 twin 対 core** は同じ run の中で測って `ratio_vs_core` に入れる。twin の対応表は**発明せず**、registry の `Op.halcon`(core と cv2 ラッパが共有する HALCON 名。`backends.py` の登録表)から引く。`edges_image` のように 2 つの cv2 op が名乗る別名は in/out sort で解く(`canny` → `cv_canny`、`cv_scharr` ではない)。候補が複数残る場合は登録順で先頭を採り、`twin_candidates` に全候補を残す。
* **GPU 対 CPU** は `--device cuda` のときに同じ行で CPU 経路も測り、`ratio_vs_core = "cpu:<op>"` として出す(accel 対応の判定は `accel.ACCEL` の `key -> (fn, core, halcon)` から)。
* run をまたぐ比較はベースラインの `--tolerance`(既定 30 %)がこの幅を吸収する前提。JSON の `header.caveat` に「熱定常でない」旨を必ず書き込む。

### 6.5 ベースラインのキーと判定

キーは `"gaussian|2048|float64"`。既定でない画像種のときだけ 4 番目の成分が付く(`"median|2048|float64|quantised"`)ので、画像種を増やしても既定キーは不変。比較は 4 つを別々に数える:

| 種別 | 意味 |
|---|---|
| `regressions` | `ms` がベースラインの `(1 + tolerance)` 倍超 → 表にして **exit 1** |
| `improvements` | 逆側(`1/(1+tolerance)` 未満) |
| `vanished` | ベースラインに在って**今回測れなかった**行(消えた op / 落ちた op。黙って無視すると「退行ゼロ」に化ける) |
| `dtype_changed` | `out_dtype` が変わった行(速くなっても別物なら別物) |

### 6.6 harness の限界(honest)

* 3-D volume op(§1.5)と動画経路(§3.2)、facade マイクロオーバーヘッド(§1.7)、タイル/フレーム並列(§1.8)は **まだ harness に入っていない**。調査の使い捨てスクリプトにはあり、(d) VideoPipeline を作るときに `--set vol` / `--set video` として足すのが自然。
* `rss_peak_x` は 0.4 ms ポーリングなので **10 ms 未満の op では取りこぼす**。`tm_peak_x` は numpy 配列しか見ない(C 内部バッファは見えない)。両方を並べているのはそのため。psutil があれば使い、無ければ Windows は `K32GetProcessMemoryInfo`、POSIX は `getrusage` にフォールバックする(どれも無ければ `rss_*` は `null`)。
* メモリ計測の呼び出しは **時間サンプルに数えない**(tracemalloc が実行時間を数倍にするため)。1 行あたりの呼び出し回数は `warm + 1 + repeat`。
* `--device cuda` はグローバル環境(torch CPU 版)では静かに CPU に落ちる。GPU 実測は loco venv(cu128)で走らせる(§1.6 と同じ条件)。
