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
| **領域モルフォロジ** reg_dilate/erosion_golay/opening_circle | binarize, count(各 2) | 中(GPU 化しても末尾 projective が残り 5/6 止まり) | 中(binary_dilation=反復十字 SE) |
| backend 固有 sk_tv/cv_sharpen/simulate_defocus/xsitk_*/xcv_*/sk_scharr/gdilate | 各 1 | 低 | 高 |
| projective_trans_region(幾何) | binarize, count | — | wave2(order3 spline でブロック中) |

**教訓(honest)**: 「champion 頻度」≠「E2E レバレッジ」。illuminate は 3 champion 頻出だが edge では CPU op に挟まれた 1-op 島(低レバレッジ)。**pipeline を丸ごと GPU にできる塊(volume / locate 一族)が高レバレッジ**。次候補 = 領域モルフォロジ(binarize/count を 5/6 まで、ただし projective が残る)or fullseye API device 引数。

## 設計原則(honest parity gate)
- accel op は **core registry と interior <5e-3 一致(faithful)** を満たすものだけ載せる。
  満たせない op(例 diff_of_gauss = _norm 全体 max abs が大 sigma で端差を全体に乗せる)は
  accel に載せず CPU に委ねる。**「速いが違う」を作らない**。
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
- **champion GPU カバレッジ: 4/38 → 26/38 段。4 champion が 100% GPU**(locate/locate_rot/
  vol_count/vol_denoise)、**binarize/count は 5/6**(残 projective のみ)。
- [ ] **fullseye API から device 指定**: 公開 API(api.py / fslib)で device="cuda" を通す。

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
