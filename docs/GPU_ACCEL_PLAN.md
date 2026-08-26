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
| **volume 群** vol_median/vol_gaussian/vol_erode/vol_dilate/vol_threshold | vol_count, vol_denoise を **0%→~100%** | 最大(2 champion を丸ごと) | 中(3D pool/conv、要 volume sort) |
| **illuminate** | edge, locate, locate_rot(3) | 高(3 champion に共通) | 中 |
| **領域モルフォロジ** reg_dilate/erosion_golay/opening_circle/gdilate | binarize, count, edge | 中(projective_trans_region が残る) | 中 |
| **ncc_locate**(NCC) | locate, locate_rot(2) | 中(shapematch_gpu の conv2d を流用可) | 低 |
| backend 固有 sk_tv/cv_sharpen/simulate_defocus/xsitk_*/xcv_*/sk_scharr | 各 1 | 低 | 高 |
| projective_trans_region(幾何) | binarize, count | — | wave2(order3 spline でブロック中) |

→ **次波 = volume 群**(最ROI・2 champion を丸ごと GPU 化、既存 2D op の 3D 版)。

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
      wave 優先度を出す(`report_champions`)。**残: 実 champion での E2E スループット計測は、
      champion の GPU カバレッジが上がってから(現状 4/38 段では転送償却の効きが薄い)**。
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
