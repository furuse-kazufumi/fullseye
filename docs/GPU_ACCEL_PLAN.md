# op の GPU 化ロードマップ(E2E の本丸)

> 方針(ユーザー、2026-08-26)「op の GPU 化は E2E の本丸。他プロジェクトの土台としても効く」。
> 計画的・セッション横断で進めるための正本。GPU 実行 = loco venv(torch cu128 / RTX 5090)。
> 詳細所見 = docs/HIGHSPEED_VISION.md「op の GPU 化 = E2E の本丸」/ docs/GPU_OPTIMIZATION_PATTERNS.md。

## 到達点(2026-08-26)
- **形状マッチング一族 GPU 化 完了**: 勾配方向スコア = conv2d。単一/回転/スケール/異方/
  複数インスタンス。34-88x、位置は CPU 一致。`shapematch_gpu.py`。
- **accel(密画素並列 op)wave1/3/4 完了**: 11→26 op。median 60x / percentile 46.6x、集計 9.50x。
- **E2E 常駐パイプライン `accel.run_pipeline`**: 転送1回で op 連鎖。5-op で per-op 比 4.9x、
  CPU 比 12.6x。run_batch 逐次適用とビット一致。
- **E2E ブリッジ `accel_bridge.py` 完了**: 進化 champion(genome/pipeline)を GPU 常駐区間
  (accel 対応)+ CPU 区間(未対応)へ自動分割して実行。連続 accel op は 1 転送に償却。
  **honest metric 検証**: GPU ルーティングは denoise champion の **PSNR を ±0.01 dB で保存**
  (holdout −0.006 / locked −0.011 dB)。pixel は median 端差 → 後段 sk_tv(全域 TV)伝播で
  ~0.06 ずれるが、**タスク指標は不変** = GPU 化は champion を壊さない。tests/test_accel_bridge.py。
- **粘菌ソルバ GPU 化**: matrix-free バッチ CG + CUDA graph、最大 162x(参考=起動律速の逆例)。

## ★データ駆動の wave 優先度(2026-08-26、accel_bridge.report_champions 実測)
現状 champion 実 op のうち GPU 稼働は **4/38 段のみ**(threshold×2 / median / percentile)。
残りは全て CPU。ランダムに op を足すのでなく、進化が実際に選ぶ op を頻度順で GPU 化する:

| 未対応 op(群) | 登場 champion | GPU 化の効き | 難度 |
|---|---|---|---|
| ~~**volume 群** vol_median/vol_gaussian/vol_erode/vol_dilate/vol_threshold~~ **完了 2026-08-26** | vol_count 5/5・vol_denoise 4/4(**100% GPU**、~64x) | 済 | 済(`accel_vol.py`) |
| ~~**illuminate**~~ **完了** | edge, locate, locate_rot | 済(bit-exact) | 済(`accel.py` symmetric conv) |
| ~~**ncc_locate**~~ **完了** | locate, locate_rot(**100% GPU**、4-6x) | 済(位置 Δ=0) | 済(`accel_match.py`) |
| ~~**領域モルフォロジ** reg_dilate/erosion_golay/opening_circle~~ **完了** | binarize/count **5/6 GPU**(3-5x、Δ=0) | 済(bit-exact) | 済(`accel.py` conv2d 二値) |
| backend 固有 sk_tv/cv_sharpen/simulate_defocus/xsitk_*/xcv_*/sk_scharr/gdilate | 各 1 | 低 | 高 |
| projective_trans_region(幾何) | binarize, count | 5/6→6/6 の最後の 1 | wave2(order3 spline でブロック中) |
| decode_barcode / xcv2_lap_var / xsitk_closing_by_recon | 各 1(barcode/classify) | 低(feature 終端) | 中〜高 |

**教訓(honest)**: 「champion 頻度」≠「E2E レバレッジ」。**pipeline を丸ごと GPU にできる塊(volume / locate / binarize-count 一族)が高レバレッジ**。illuminate は edge では CPU op 島で低レバレッジだった。**高レバレッジな塊はほぼ回収済**。残りは (a) projective_trans_region(幾何=wave2 の order3 spline を解けば binarize/count が 6/6)、(b) backend 固有 op(各 1 champion=低レバレッジ・高難度)、(c) **fullseye API device 引数**(公開層で GPU 経路を通す=横展開)。次の実質前進は (c) or (a)。

## 2026-08-31 更新(Batch 0〜3)

- **境界 padding バグ修正(Batch 0)**: `_sep_conv`/`_conv`/`_unfold_reflect`/
  `_std_filter` が torch `reflect`(端非複製)のままで、symmetric 修正が gaussian 系に
  しか当たっていなかった → 全て `_pad_sym` 化。sobel/laplace/prewitt/unsharp/median/
  percentile/std が **full-image 一致**になり、**diff_of_gauss の「faithful 不可」判定は
  誤りだったと確定**(真因は _norm でなく _sep_conv の padding。sym 化で full 1e-5 級)。
- **parity ゲート強化**: 旧 (0.5,0.4) 1 点 + 固定 3px マージン → `PARITY_AB` 5 点
  スイープ + カーネル半径連動マージン(a>=0.75 の k=9 の穴を塞いだ)。
- **HALCON twin 別名 42 op(Batch 1)**: registry の同一実装 twin を自動探索
  (構造化 blob。塩ノイズ二値は erosion 全消え等の縮退で偽陽性を出す)+ PARITY_AB
  全点実測で登録。r3_label_to_region は灰色ラベル画像で別動作のため棄却。
- **関門 op(Batch 2)**: otsu / dyn_threshold / canny / local_max /
  adaptive_gauss_thresh(+twin local_threshold, nonmax_suppression_amp)。
  otsu の GPU 化で image→region 関門が開き区間分断が減少。
  ※ binary_threshold / auto_threshold / sk_otsu は otsu kernel と**一致しなかった**
  (実装が別物)。残 CPU。
- **二値 reconstruction(Batch 3 先行)**: fill_holes / fill_up(境界フラッド
  4 近傍、GT+連結規約テストつき)、bilateral(25 シフト反復)。
- 現在: **ACCEL 90 mapping / 89 faithful**(唯一の differ = projective_trans_region の
  metric-faithful 例外)。**出荷 RECIPES 段 GPU 15/33 → 26/33**。
  残 uncovered(各 1 レシピ): remove_small, count_obj, clahe, gabor,
  sk_corner_harris, sk_dog, distance_transform。
- 次: grayscale reconstruction primitive(xsitk_closing_by_recon /
  grindpeak = champion 残 2 op)/ 終端 reduction(count_obj, intensity 等 =
  D2H を画像→スカラー化、bridge の feature 出力対応が前提)/ RTX 5090 で速度実測。

## 設計原則(honest parity gate)
- accel op は **core registry と interior <5e-3 一致(faithful)** を満たすものだけ載せる。
  満たせない op は accel に載せず CPU に委ねる。**「速いが違う」を作らない**。
- 単発 op は転送律速で安い op は CPU に負ける。**勝ち筋は常駐パイプライン**(転送償却)と
  **高コスト op(median/percentile/morphology)**。
- チェーン parity は CPU と厳密一致しない(_norm 端差 + 末尾 threshold の二値増幅)。
  bit-faithful が要るなら float64 + チェーン途中の per-image-max 再正規化回避(将来課題)。

## 波(waves)—— 各 op = 実装(LLM)→ parity 検証 → bench → 登録
- [x] **wave1 密画素並列**: median, percentile, prewitt, roberts, opening, closing, tophat,
      bothat, std, unsharp, sigmoid(sobel/laplace/gauss/mean/morph/gamma/invert/scale/threshold は既存)。
- [ ] **wave2 幾何変換**(grid_sample): rotate_img, rescale_img, affine_warp。要注意 = 補間規約
      (order/mode)を core(ndimage.rotate/zoom/affine_transform)に合わせる。
- [x] **wave3 周波数**: lowpass, highpass(core は FFT マスク)。torch.fft で直移植、parity 高い見込み。
- [~] **wave4 ヒストグラム/テクスチャ**(kornia GPU へ経路): equalize, clahe, gabor, bilateral,
      corner_response。`backends_kornia.py`(torch GPU)を device=cuda で使う。core と近似一致を確認。
- [~] **wave5 grad_dir / log / dog 系**: grad_dir(atan2) 済(interior 完全一致)。log(gaussian_laplace は近似要検討)、dog は _norm 問題の
      回避法(faithful 化)を検討してから。

## E2E 統合(本丸の仕上げ)
- [x] **進化 champion → 常駐 GPU パイプライン**(`accel_bridge.py`): champion(genome/pipeline)を
      `accel.run_pipeline` の steps へ写像。accel 未対応 op が混ざる列は CPU 区間として併用、
      連続 accel op は 1 転送に償却。metric 保存(±0.01 dB)を検証済。未対応 op 頻度が上の
      wave 優先度を出す(`report_champions`)。bridge は image(`accel`)/ volume(`accel_vol`)/
      CPU の 3 種区間を自動分割。
- [x] **volume 群 GPU 化 完了**(`accel_vol.py`、2026-08-26): vol_median/vol_gaussian/vol_erode/
      vol_dilate/vol_threshold の 3D 版(conv3d/max_pool3d/reflect)。core と **5/5 faithful**
      (interior<5e-3、gaussian は端からカーネル半径内側)。**vol_count 5/5・vol_denoise 4/4 段が
      単一 GPU 常駐区間**に。RTX 5090 実測 **対 CPU ~64x**(32³B32:549→8.5ms / 128³B4:4547→70.7ms)、
      **常駐は per-op の 2.8x**(4段で転送 4→1 償却)。指標保存 = vol_count 完全一致・vol_denoise ±0.15 dB。
      tests/test_accel_vol.py(10 tests)。
- [x] **symmetric padding fix + illuminate GPU 化 完了**(2026-08-26): scipy.ndimage の既定
      mode='reflect' は **numpy 'symmetric'(端複製)** で torch 'reflect'(鏡映・端非複製)と別物。
      `_sym_idx`/`_pad_sym`/`_sep_conv_sym`(index_select、r>n も可)で symmetric conv を実装し、
      **大 σ gaussian が全サイズ bit 一致**(illuminate=大 σ unsharp は **exact**、gauss_filter/
      vol_gaussian も端まで faithful 化)。illuminate は edge/locate/locate_rot(3 champion)頻出。
- [x] **NCC マッチング ncc_locate GPU 化 完了**(`accel_match.py`、2026-08-26): normxcorr2 =
      correlate(mean-free T)+ uniform_filter(box)= conv2d/avg で GPU 化(shapematch_gpu と同機構)。
      core と score |Δ|~1e-6・**argmax 位置は完全一致**。bridge に MATCH 終端区間を追加し、
      **locate/locate_rot が 100% GPU**(illuminate+ncc)。RTX 5090 実測 **対 CPU 4-6x**
      (256²B8:38→6.2ms)、**タスク指標(位置誤差)は Δ=0 で完全一致**。tests/test_accel_match.py(5)。
- [x] **領域(2値)モルフォロジ GPU 化 完了**(2026-08-26): reg_dilate/reg_erode(cross×iter)、
      erosion_golay/erosion_circle/dilation_circle/opening_circle(disk footprint)を conv2d カウント
      +閾値で実装。**ndimage.binary_* と bit 一致**(zero-pad = border_value=0、dilation=count>0 /
      erosion=count==footprint 和)。disk は skimage 非依存で再現(x²+y²≤r²、loco venv に skimage 無し
      でも動く)。**binarize/count が 1/6 → 5/6 段を単一 GPU 常駐区間**に(threshold+opening_circle+
      reg_dilate+erosion_golay+reg_dilate、projective_trans_region のみ CPU)。RTX 5090 実測 **対 CPU
      3-5x**(256²B8:16.7→3.4ms)、常駐は per-op の 4.2x。**指標(IoU/count)完全一致 Δ=0**
      (bit-exact ゆえ)。tests/test_accel_region.py(20)。
- **champion GPU カバレッジ: 4/38 → 32/38 段。7 champion が 100% GPU**(binarize/count/**denoise**/
  locate/locate_rot/vol_count/vol_denoise)。残 CPU = edge/classify の xsitk_*/xcv_*/sk_scharr、
  barcode の decode_barcode(SimpleITK/OpenCV 固有・feature 終端で低レバレッジ)。
- **cv2 ≒ HALCON 級最適化 CPU** なので本ベンチは HALCON との性能差予測にもなる(ユーザー観点 2026-08-26)。
- [x] **残 op(gdilate/gerode/cv_sharpen/projective_trans_region)完了**(2026-08-26):
      gdilate/gerode=grey_dilation/erosion(size=_k(a))は maxpool/minpool の rect 版流用(exact)。
      cv_sharpen=3x3 conv(cv2.filter2D 既定 border=reflect と一致、exact)。projective_trans_region=
      透視ワープを grid_sample(bilinear/reflection)で近似 —— bit 一致でないが **binarize/count の
      指標(IoU/count)を Δ=0 で保存**(採否は指標で判定。honest に「metric-faithful, not bit-faithful」)。
      → **binarize/count が 6/6=100% GPU、単一常駐区間**に。sk_tv(Chambolle 反復)/simulate_defocus/
      xsitk_*/xcv_*/decode_barcode は backend 固有・各 1 champion=低レバレッジで CPU 残置(honest)。
- [x] **denoise を 100% GPU 化 完了**(2026-08-26): simulate_defocus=uniform_filter(_k(a))は `_mean`
      流用(_mean を symmetric padding に修正=box も bit 一致に)。**sk_tv=Chambolle TV** を skimage
      `denoise_tv_chambolle` 忠実移植(tau=1/(2ndim)、勾配/発散、E 停止)。★バッチは **per-image freeze**
      (収束画像を凍結、全反復回すと早期停止画像を過剰平滑化する非faithful を回避)→ **bit-exact**。
      → denoise が median>sk_tv>simulate_defocus>cv_sharpen の **4/4 単一常駐区間**、PSNR Δ~0.01 dB。
      sk_tv は計算重(~200 反復)= GPU の本領(CPU-torch 比 5.9×)。
- [x] **OpenCV(cv2)比ベンチ 完了**(`bench_vs_opencv.py` → `docs/BENCH_VS_OPENCV.md`、2026-08-26):
      ★honest な結論 = **単発の軽量 2D フィルタは cv2 CPU が速い**(GPU は転送律速: 512²×32 で転送
      40ms vs gaussian 実計算 0.51ms = 約 79 倍差)。**GPU が cv2 に勝つのは 3 条件**: (1) NCC マッチング
      1.7-1.9×、(2) **多 op 常駐チェーン**(3op で交差、20op で **5.1×**)、(3) **3D**(cv2 に無い→scipy 比
      65-71×)。以前の「64x/3-5x」は scipy 比。cv2 は SIMD で極限最適化。**imgevolve の常駐設計は (2) を突く**
      = 進化 champion を丸ごと GPU に載せる時に効く。
- [x] **転送床の最適化**: `_to_batch` を float32 直積み(float64 中間を除去)。42→40ms(残りは実 PCIe +
      from_batch の float64 出力変換)。parity 不変。
- [x] **fullseye API から device 指定 完了**(2026-08-26): `api.run_pipeline(..., device="cuda")` /
      `api.apply(..., device="cuda")` を追加。device!="cpu" は accel_bridge の GPU 常駐経路(未対応 op
      は CPU、torch/GPU 不在は静かに CPU フォールバック)。既定 device="cpu" は挙動不変(回帰テスト)。
      **CUDA vs CPU-torch 実結果照合**(loco venv): region/volume は **bit 一致(0.0)**、illuminate/ncc は
      float32 epsilon(5.96e-08)、ncc 位置は完全一致 → GPU が正しく計算していることを確認。
      tests/test_api_device.py(4)。**これで公開層から GPU 経路が通り、他プロジェクトの土台になる。**

## Afterman トラック(集団評価を GPU バッチで)
- [ ] 構造進化の population 評価を GPU バッチ化(loco venv)。世代あたりの評価が集団サイズぶん
      並列化できる = GPU の本領。長時間・決定的なので **work-graph の tool ノード**に積んで
      detached driver に自走させる(セッション不在でも回る)。正本 = afterman 側 docs + memory。

## 検証ゲート(各 wave 完了の定義)
1. `py -3.11 accel.py`(CPU parity)+ loco `accel.py --device cuda`(GPU parity)で faithful 数を確認。
2. `bench.py --device cuda` で新 op のスループットを記録(honest: CPU 比、負ける op も明記)。
3. 影響テスト green(tests/test_accel_pipeline.py ほか)。
4. この doc の該当波にチェック + HIGHSPEED_VISION.md に実測追記。

## 進め方(計画的・セッション横断)
- op 実装は LLM 波(fresh セッションで Execute)。parity/bench は inline で速く回る(gate)。
- Afterman の長時間 GPU ラン等の**決定的・無人ジョブは work-graph**(raptor-worklog tool ノード +
  detached driver)。graph はセッションを跨いで生き残る = 別セッションが結果を受け取る。
- 中断・再開はこの doc の checklist と git log が正本。
