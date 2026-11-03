# GPU の損益分岐とパイプライン(第 5 便、2026-11-02〜03)

`device="auto"` が「GPU が在れば常に GPU」から、**入力の大きさ・op・空き VRAM を見て CPU / GPU を選ぶ**ように
なった根拠の実測。規則の表は `fullseye/data/DEVICE_RULES.json`(生成 `tools/gen_device_rules.py`、生ログ
`docs/perf/logs/crossover/*.jsonl` から決定的に作る。`regen_all` の鎖に入っている)。

## 要点

- **単独 op**: 手書きの GPU 経路を持つ 90 op のうち 62 op に「この大きさ未満は CPU」の閾値が付いた
  (CPU に残す上限は一辺 127〜2048、族ごとの内訳は下の表)。28 op は測った最小の寸法から GPU が勝つ(median・周波数・多くの形態)。
  点演算の `threshold` / `invert` は一辺 4096 でも GPU が勝たない(転送が計算より重い)。
- **採用(after < before)**: 規則が CPU に回す 474 点を、規則の前(`cuda`)と後(`auto`)で同じプロセスで
  測った 2 回目で、揺れの幅(10 % かつ 50 µs)を超えて遅くなった点は **0**。合計 3.92 s → 0.79 s。
  1 回目は 568 点中 14 点が 10〜47 % 遅くなったので、閾値の決め方を直してから測り直した(下の「経緯」)。
- **初回起動**: 小さい仕事を `auto` で 1 本のプロセスに流すと、CUDA の文脈を作らないぶん 1.9〜18 倍速い
  (12 点、合計 4.52 s → 0.80 s)。
- **パイプライン**: 全段 GPU の常駐は一辺 512 以上でほぼ全部 GPU の勝ち(最大 60 倍、一辺 4096 の
  `interleaved_worst`)。途中に GPU 経路の無い段が挟まると往復が段の数だけ増え、一辺 2048 で倍率は 1.3〜6.0 倍に落ちる。
  鎖の規則「GPU 段が全部単独でも CPU に残る大きさなら鎖も CPU」は測った 87 点で遅くなる点が無く採用
  (CPU に回るのは `shading_blob` の一辺 128 の 2 点だけ)。
- **許可リストの道**(`gpu_shadow`、CuPy): 抜き取り 12 op を一辺 2048 で `auto` に通すと全部 GPU に乗り
  1.9〜80 倍速い。一辺 1024 では測った大きさ未満なので CPU のまま(before と同じ時間)。
- **VRAM**: 既定の閾値 2048 MiB(下の「VRAM の閾値」)。

## 測定条件

- 機械: RTX 5090(32 GB、ドライバ 610.88)、Intel 24 論理コア。GPU = torch 2.11.0+cu128 / numpy 1.24.4 /
  scipy 1.15.2 / CuPy 13.6(loco 環境)。CPU も同じ環境で測った(規則が比べるのは同じプロセスの CPU と GPU)。
- 同じ前生成の画像(乱数生成は時間に入れない)。各点は複数回の中央値(格子 3〜7 回、掃引 3〜5 回、
  鎖の測り直し 15 回)。GPU は `torch.cuda.synchronize()` の後に時計を読み、**転送込み**。
- CPU が 1 回 90 s を超えた点は打ち切り(`cutoff`)、外挿しない。GPU が窓の上限まで返らなかった点は番犬が
  止めて `aborted`(VRAM 溢れのページング、WDDM は OOM を出さない)。どちらも表にそのまま書く。
- GPU は共有資源。共有ロックを取って 1 窓 7〜8 分以内、窓の間は譲った。UnrealEditor が居る間は測らない。
- 異常に速い値の内訳: 一辺 2048 の 1 枚(float32 16 MiB)の往路は 14〜62 ms で、12 GB/s の物理下限
  (1.4 ms)より遅い側にある(float64 → float32 の変換と同期を含む)。60 倍の `interleaved_worst` は
  CPU 側の median(一辺 4096 で 6.95 s)が重いことによる。

## 1. 単独 op の損益分岐(代表 33 op、一辺 64〜4096 × 枚数 1〜100)

「一辺 X から GPU」= その寸法以上で GPU が CPU より揺れの幅(10 %)を超えて速い。括弧は、いったん GPU が
勝った後に再び CPU が勝った寸法。角括弧は打ち切り・停止・未測定の点(`CPU の状態/GPU の状態`)。
体積は一辺 32〜512、`ncc_locate` は画像の一辺。体積の 16 / 100 枚は格子に無い。体積 512³ × 4 枚は
`vol_median` が VRAM を溢れて返らなかった(番犬で停止)ので、他の体積 op も測っていない。

| 族 | op | 1 枚 | 4 枚 | 16 枚 | 100 枚 | 4096² 1 枚 CPU / GPU(ms) |
|---|---|---|---|---|---|---|
| point | `threshold` | GPU 勝たず | GPU 勝たず | GPU 勝たず | GPU 勝たず | 138.52 / 186.56 |
| point | `invert` | GPU 勝たず | GPU 勝たず | GPU 勝たず | GPU 勝たず | 158.87 / 193.73 |
| point | `gamma` | 一辺 256 から GPU | 一辺 128 から GPU(256 で再び CPU) | 一辺 64 から GPU(1024 で再び CPU) | 一辺 64 から GPU(256 で再び CPU) | 283.19 / 231.71 |
| point | `sigmoid` | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 64 から GPU(128,256,512 で再び CPU) | 一辺 512 から GPU | 502.61 / 127.07 |
| point | `scale_clip` | 一辺 128 から GPU(256 で再び CPU) | 一辺 512 から GPU | 一辺 64 から GPU(128,256 で再び CPU) | 一辺 512 から GPU | 327.75 / 111.02 |
| separable | `gaussian` | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 64 から GPU | 一辺 64 から GPU[4096:ok/aborted] | 569.75 / 131.04 |
| separable | `mean_box` | 一辺 1024 から GPU | 一辺 1024 から GPU | 一辺 1024 から GPU | 一辺 1024 から GPU | 1114 / 196.87 |
| separable | `sobel_mag` | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 128 から GPU | 一辺 64 から GPU | 1625 / 82.22 |
| separable | `dog` | 一辺 256 から GPU | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 1215 / 87.79 |
| separable | `unsharp` | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 64 から GPU(128 で再び CPU) | 一辺 64 から GPU | 596.77 / 80.40 |
| nonseparable | `median` | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU[4096:cutoff/skipped_vram] | 一辺 64 から GPU[2048:cutoff/aborted] | 8564 / 192.10 |
| nonseparable | `percentile` | 一辺 64 から GPU | 一辺 64 から GPU(4096 で再び CPU) | 一辺 64 から GPU(2048 で再び CPU)[4096:cutoff/skipped_vram] | 一辺 64 から GPU[1024:ok/aborted; 2048:cutoff/skipped_vram] | 9231 / 196.10 |
| nonseparable | `bilateral` | 一辺 256 から GPU | 一辺 64 から GPU | 一辺 64 から GPU[2048:cutoff/ok; 4096:cutoff/ok] | 一辺 64 から GPU[1024:cutoff/ok; 2048:cutoff/ok] | 14788 / 121.03 |
| nonseparable | `std_filter` | 一辺 256 から GPU | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 1073 / 94.52 |
| nonseparable | `laplace` | 一辺 512 から GPU | 一辺 256 から GPU | 一辺 128 から GPU | 一辺 64 から GPU | 679.18 / 110.41 |
| morphology | `min_filter` | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 799.83 / 107.64 |
| morphology | `gopen` | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 975.92 / 110.79 |
| morphology | `tophat` | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 1004 / 120.16 |
| morphology | `erosion_circle` | 一辺 1024 から GPU | 一辺 128 から GPU(256,512 で再び CPU) | 一辺 64 から GPU | 一辺 64 から GPU | 257.55 / 107.45 |
| morphology | `reg_dilate` | 一辺 256 から GPU | 一辺 64 から GPU(256 で再び CPU) | 一辺 64 から GPU | 一辺 64 から GPU | 270.73 / 90.35 |
| frequency | `lowpass` | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 2414 / 91.57 |
| frequency | `highpass` | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 2411 / 89.28 |
| iterative | `sk_tv` | 一辺 256 から GPU | 一辺 256 から GPU[4096:cutoff/ok] | 一辺 128 から GPU[2048:cutoff/ok; 4096:cutoff/ok] | 一辺 64 から GPU[1024:cutoff/ok; 2048:cutoff/ok] | 47330 / 202.82 |
| iterative | `fill_holes` | GPU 勝たず | GPU 勝たず | GPU 勝たず | 一辺 64 から GPU(512,1024 で再び CPU)[2048:ok/aborted] | 1053 / — |
| iterative | `canny` | 一辺 256 から GPU | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 1944 / 98.07 |
| iterative | `equalize` | 一辺 128 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU | 555.09 / 107.98 |
| iterative | `otsu` | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 512 から GPU | 一辺 512 から GPU | 423.59 / 118.84 |
| volume | `vol_gaussian` | 一辺 32 から GPU | 一辺 32 から GPU | GPU 未測定 | GPU 未測定 | — / — |
| volume | `vol_median` | 一辺 32 から GPU | 一辺 32 から GPU[512:cutoff/aborted] | GPU 未測定 | GPU 未測定 | — / — |
| volume | `vol_erode` | 一辺 32 から GPU | 一辺 32 から GPU | GPU 未測定 | GPU 未測定 | — / — |
| volume | `vol_threshold` | 一辺 32 から GPU(64 で再び CPU) | 一辺 64 から GPU | GPU 未測定 | GPU 未測定 | — / — |
| volume | `vol_opening_ball` | 一辺 32 から GPU | 一辺 32 から GPU | GPU 未測定 | GPU 未測定 | — / — |
| match | `ncc_locate` | 一辺 64 から GPU | 一辺 64 から GPU | 一辺 64 から GPU[4096:cutoff/ok] | 一辺 64 から GPU[2048:cutoff/ok] | 7827 / 159.13 |

### 初回起動(別プロセス 10 回の中央値)

`import_api_s` は `import api` 全体(torch の import を含む)。`context_s` は CUDA の文脈を作る時間、
`first_op_s` は最初の op(kernel のコンパイル・cuDNN の選択を含む)、`second_op_s` は同じ op の 2 回目。
規則の表は**常駐後**(2 回目以降)の値で作った。初回の固定費(約 0.45 s)はプロセスに 1 回なので閾値には
入れず、before/after の「初回起動」の行で効き目を別に測った。

| 項目 | 中央値 | 回数 |
|---|---:|---:|
| `import_api_s` | 3061 ms | 10 |
| `is_available_s` | 22.16 ms | 10 |
| `context_s` | 129.36 ms | 10 |
| `first_op_s` | 325.61 ms | 10 |
| `second_op_s` | 25.78 ms | 10 |
| `first_other_op_s` | 56.28 ms | 10 |

## 2. パイプライン(4 本 × 全 GPU / 混在)

- `all` = 全段が GPU 経路を持つ(常駐、往復 1 回)。`mixed` = 途中に GPU 経路の無い段(`clahe` /
  `kirsch_amp` / `guided_filter`)が挟まる。全 CPU は `run_pipeline(device="cpu")`、GPU は
  `accel_bridge.run`(`run_pipeline(device="cuda")` の中身)。
- 一辺 4096 × 16 枚は median の展開で VRAM を溢れる見積りなので測っていない(未測定)。

**1 枚**(ms、CPU / GPU。GPU は転送込み)

| パイプライン | 変種 | 128 | 256 | 512 | 1024 | 2048 | 4096 |
|---|---|---|---|---|---|---|---|
| scratch_surface | all | 0.86 / 3.44 | 2.33 / 2.26 | 15.64 / 6.71 | 99.94 / 14.97 | 863.93 / 64.81 | 2331 / 196.27 |
| scratch_surface | mixed | 2.48 / 5.57 | 6.63 / 10.87 | 29.72 / 27.74 | 191.81 / 150.10 | 868.45 / 690.96 | 4611 / 2301 |
| edge_dimension | all | 5.64 / 32.67 | 20.49 / 52.37 | 108.09 / 138.39 | 428.89 / 210.13 | 1712 / 443.13 | 7695 / 4923 |
| edge_dimension | mixed | 5.93 / 75.46 | 24.46 / 109.71 | 163.39 / 174.89 | 591.09 / 441.04 | 2123 / 1415 | 8405 / 4233 |
| shading_blob | all | 1.92 / 1.72 | 6.06 / 1.58 | 54.29 / 2.96 | 227.26 / 7.64 | 1009 / 35.80 | 5027 / 104.11 |
| shading_blob | mixed | 1.89 / 1.65 | 5.57 / 2.03 | 31.63 / 7.65 | 131.30 / 24.67 | 582.97 / 97.50 | 2459 / 351.09 |
| interleaved_worst | all | 4.65 / 1.22 | 17.25 / 1.60 | 85.56 / 3.33 | 352.58 / 8.80 | 1569 / 32.60 | 6952 / 114.33 |
| interleaved_worst | mixed | 8.47 / 4.67 | 30.24 / 11.55 | 139.36 / 46.45 | 684.95 / 218.86 | 2818 / 808.82 | 11874 / 3206 |

**16 枚**(ms、CPU / GPU。GPU は転送込み)

| パイプライン | 変種 | 128 | 256 | 512 | 1024 | 2048 | 4096 |
|---|---|---|---|---|---|---|---|
| scratch_surface | all | 10.78 / 2.71 | 38.57 / 20.96 | 230.18 / 53.58 | 1684 / 189.73 | 13334 / 885.26 | 未測定 |
| scratch_surface | mixed | 37.63 / 40.11 | 99.80 / 116.95 | 508.11 / 469.63 | 3293 / 2407 | 17744 / 12917 | 未測定 |
| edge_dimension | all | 85.63 / 34.07 | 329.96 / 67.87 | 1514 / 281.25 | 6755 / 935.16 | 27882 / 7209 | 未測定 |
| edge_dimension | mixed | 141.35 / 99.42 | 510.14 / 357.92 | 2025 / 1109 | 8547 / 4965 | ok/aborted | 未測定 |
| shading_blob | all | 48.97 / 2.87 | 138.81 / 6.22 | 759.66 / 24.44 | 3601 / 101.83 | 15207 / 432.64 | 未測定 |
| shading_blob | mixed | 22.54 / 6.08 | 82.16 / 19.02 | 486.15 / 103.09 | 2190 / 344.18 | 9505 / 1434 | 未測定 |
| interleaved_worst | all | 68.08 / 2.74 | 271.55 / 13.34 | 1297 / 52.70 | 5936 / 118.40 | 25350 / 455.63 | 未測定 |
| interleaved_worst | mixed | 133.14 / 47.93 | 514.26 / 148.75 | 2263 / 758.50 | 10611 / 3314 | 44077 / 13184 | 未測定 |

**内訳**(1 枚、一辺 2048、ms。GPU 側の中央値の回の内訳)

| パイプライン | 変種 | GPU 区間 | GPU 段 | CPU 段 | 往路 回/ms | 復路 回/ms | CPU 段 ms | kernel ms | 計 ms |
|---|---|---:|---:|---:|---|---|---:|---:|---:|
| scratch_surface | all | 1 | 5 | 0 | 1 / 25.80 | 1 / 28.65 | 0.00 | 10.36 | 64.81 |
| scratch_surface | mixed | 2 | 5 | 1 | 2 / 62.05 | 2 / 44.72 | 558.28 | 25.90 | 690.96 |
| edge_dimension | all | 1 | 5 | 0 | 1 / 24.70 | 1 / 23.30 | 0.00 | 395.14 | 443.13 |
| edge_dimension | mixed | 2 | 4 | 1 | 2 / 26.72 | 2 / 57.71 | 746.49 | 583.94 | 1415 |
| shading_blob | all | 1 | 5 | 0 | 1 / 14.18 | 1 / 11.02 | 0.00 | 10.61 | 35.80 |
| shading_blob | mixed | 2 | 4 | 1 | 2 / 29.53 | 2 / 22.60 | 35.82 | 9.55 | 97.50 |
| interleaved_worst | all | 1 | 5 | 0 | 1 / 14.06 | 1 / 10.27 | 0.00 | 8.28 | 32.60 |
| interleaved_worst | mixed | 4 | 5 | 3 | 4 / 52.22 | 4 / 43.93 | 705.21 | 7.46 | 808.82 |

**測り直し**(1 枚、同じプロセスで CPU と GPU を交互に 15 回ずつ、中央値 ms)

| パイプライン | 変種 | 一辺 | 元の CPU / GPU | 測り直し CPU / GPU |
|---|---|---:|---|---|
| edge_dimension | all | 128 | 5.64 / 32.67 | 4.71 / 14.01 |
| edge_dimension | all | 256 | 20.49 / 52.37 | 18.46 / 27.98 |
| edge_dimension | mixed | 128 | 5.93 / 75.46 | 5.74 / 19.03 |
| edge_dimension | mixed | 256 | 24.46 / 109.71 | 21.58 / 30.76 |
| interleaved_worst | all | 128 | 4.65 / 1.22 | 3.89 / 1.45 |
| interleaved_worst | all | 256 | 17.25 / 1.60 | 15.03 / 1.85 |
| interleaved_worst | mixed | 128 | 8.47 / 4.67 | 6.52 / 4.97 |
| interleaved_worst | mixed | 256 | 30.24 / 11.55 | 22.82 / 11.46 |
| scratch_surface | all | 128 | 0.86 / 3.44 | 0.74 / 1.07 |
| scratch_surface | all | 256 | 2.33 / 2.26 | 2.24 / 1.14 |
| scratch_surface | mixed | 128 | 2.48 / 5.57 | 2.12 / 2.75 |
| scratch_surface | mixed | 256 | 6.63 / 10.87 | 5.62 / 4.87 |
| shading_blob | all | 128 | 1.92 / 1.72 | 1.60 / 1.66 |
| shading_blob | all | 256 | 6.06 / 1.58 | 5.54 / 1.76 |
| shading_blob | mixed | 128 | 1.89 / 1.65 | 1.43 / 1.66 |
| shading_blob | mixed | 256 | 5.57 / 2.03 | 4.52 / 2.24 |

## 3. 規則と採否

### 規則(`device_policy.route`)

1. 単独 op: op ごとの閾値(画素数)未満なら CPU。閾値は「掃引の全つまみ(a = 0.2 / 0.5 / 0.9)・全寸法
   (一辺 128〜2048)で、CPU が揺れの幅を超えて速かった最後の寸法の直後」。2048 まで CPU が勝ち続けた op は
   格子の一辺 4096 で同じ判定をする。さらに before/after の 1 回目で CPU が遅かった寸法は GPU に戻す。
2. 枚数 n > 1: 族ごとの枚数の表で閾値を下げる(GPU 寄りにしか動かない)。
3. 2 段以上の鎖: GPU 経路を持つ全段が単独で CPU に残る大きさなら CPU(`min_stage`)。測った鎖の全点で
   遅くならないときだけ採用する(表の `pipeline.adopted`、不採用なら負けた点を `violations` に残す)。
4. 判断できないとき(表が無い・壊れている・表に無い GPU 経路の op・大きさが判らない)は GPU(規則の前の挙動)。

族ごとの閾値(出荷する表):

| 族 | op 数 | CPU に残す上限の一辺(op 数) |
|---|---:|---|
| frequency | 2 | ≤128: 2 |
| geometry | 3 | ≤256: 2, ≤512: 1 |
| iterative | 7 | 0(常に GPU): 1, ≤128: 3, ≤2048: 2, ≤256: 1 |
| morphology | 31 | 0(常に GPU): 17, ≤127: 1, ≤128: 6, ≤256: 4, ≤361: 1, ≤512: 2 |
| nonseparable | 15 | 0(常に GPU): 10, ≤128: 3, ≤256: 2 |
| point | 10 | ≤1024: 1, ≤128: 2, ≤256: 2, ≤512: 5 |
| separable | 22 | ≤128: 8, ≤256: 9, ≤361: 1, ≤512: 4 |

### 経緯(失敗も残す)

- WIP(PC 再起動で中断した版)の表は、ログの途中で生成されていた: 族の枚数表に 3 族しか無く、鎖の閾値
  66049(一辺 256 まで CPU)は `shading_blob` / `interleaved_worst` を測る前の値だった。全ログで作り直すと
  鎖の閾値は 0(`interleaved_worst` は一辺 128 から GPU が勝つ)になり、1 本の閾値では鎖を表せないことが
  分かった。そこで鎖の規則を段ごとの規則に替えた。
- 段ごとの規則は、元の測定(別プロセス・3〜5 回)では `shading_blob` の一辺 128 で GPU が 12〜15 % 速く
  不採用だった。1〜2 ms の点なので、規則の採否を分ける寸法(128 / 256)を**全パイプラインについて**同じ
  プロセスで交互に 15 回ずつ測り直した(上の「測り直し」)。CPU 1.60 / GPU 1.66 ms などで CPU が速く、採用。
  元の値もログに残してある(表は測り直しの値を使う)。
- 閾値を最初は「CPU が負けていない(10 % の揺れの範囲の引き分けも CPU)」で決めていた。before/after の
  1 回目で、掃引の間の寸法(一辺 362)や 10 % 以内だった 512 の 14 点が 10〜47 % 遅くなった。閾値は
  「CPU が揺れの幅を超えて速い」で決めるよう改め、1 回目の負けた寸法も GPU に戻した。検証は材料に使って
  いない 2 回目で行った。

### before / after

before = 規則の前(`device="cuda"` = CUDA が在れば常に GPU)、after = `device="auto"`。規則が CPU に回す
点だけを測る(GPU に送る点は before と同じ道なので差が出ない)。一辺は掃引の寸法と間の寸法
(90, 128, 181, 256, 362, 512, 724, 1024, 1448, 2048)、つまみ 0.5 / 0.9。初回起動は別プロセスで
`gaussian` 256² × 1 / 20 回、`threshold` 1024² × 20 回、`fill_holes` 1024² × 5 回を 3 回ずつ。

**before_after.jsonl**

- op: 合計 before 4.133 s → after 0.978 s
- op: 568 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)14、before/after の中央値 2.42 倍、最小 0.68 倍、最大 58.93 倍
  - 遅い: canny 一辺 256 a=0.5 before 1.20 ms after 1.38 ms
  - 遅い: dilation_circle 一辺 362 a=0.9 before 1.36 ms after 1.59 ms
  - 遅い: dilation_circle 一辺 512 a=0.9 before 2.70 ms after 3.12 ms
  - 遅い: dog 一辺 256 a=0.9 before 1.12 ms after 1.24 ms
  - 遅い: erosion_golay 一辺 362 a=0.9 before 1.00 ms after 1.18 ms
  - 遅い: erosion_golay 一辺 512 a=0.5 before 1.96 ms after 2.16 ms
  - 遅い: erosion_golay 一辺 512 a=0.9 before 1.97 ms after 2.36 ms
  - 遅い: gauss_filter 一辺 362 a=0.9 before 0.92 ms after 1.19 ms
  - 遅い: gauss_filter 一辺 512 a=0.5 before 1.84 ms after 2.28 ms
  - 遅い: gauss_filter 一辺 512 a=0.9 before 1.78 ms after 2.62 ms
  - 遅い: gdilate 一辺 128 a=0.5 before 0.23 ms after 0.28 ms
  - 遅い: gray_bothat 一辺 128 a=0.5 before 0.39 ms after 0.45 ms
  - 遅い: scale_image 一辺 362 a=0.5 before 0.99 ms after 1.17 ms
  - 遅い: scale_image 一辺 362 a=0.9 before 0.95 ms after 1.14 ms
- pipeline: 合計 before 0.023 s → after 0.006 s
- pipeline: 4 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)0、before/after の中央値 1.69 倍、最小 1.12 倍、最大 8.71 倍
- cold: 合計 before 4.516 s → after 0.844 s
- cold: 12 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)0、before/after の中央値 8.04 倍、最小 1.67 倍、最大 17.15 倍

**before_after_2.jsonl**

- op: 合計 before 3.917 s → after 0.793 s
- op: 474 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)0、before/after の中央値 2.81 倍、最小 1.00 倍、最大 66.11 倍
- pipeline: 合計 before 0.004 s → after 0.003 s
- pipeline: 2 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)0、before/after の中央値 1.28 倍、最小 1.17 倍、最大 1.39 倍
- cold: 合計 before 4.518 s → after 0.802 s
- cold: 12 点、after が before より遅い点(揺れ 10% と 50 µs を超えて)0、before/after の中央値 8.60 倍、最小 1.89 倍、最大 18.12 倍

採用の門(`tests/test_device_rules.py`): 出荷する表で CPU に回る op の点の集合が 2 回目のログと一致し
(測り切っている)、揺れの幅を超えて遅い点が 0、合計で after < before。

## 4. 許可リストの道(`gpu_shadow`)

`fullseye/data/gpu_auto_allow.json`(機械的 GPU 化の掃引、`docs/perf/gpu_auto_sweep_2026-11-02.md`)の
701 行(単独 `ops` 521 / 常駐 `resident_ops` 141 / 鎖 `pipeline_ops` 39)を表の `shadow` に写した。
倍率は実寸(画像 2048²、体積 256³、信号 2²⁰ など)で測った値なので、`auto` は**測った大きさ以上の入力**
でだけこの道を選ぶ(`min_elements`、未満は `below_measured_size` で CPU)。測った形が判らない 79 行は
`auto` では選ばない(明示の `cuda` では使う)。常駐・鎖の枠は、隣の段も許可リストで GPU に載せたまま
続くときだけ使う(単独や孤立した段は `chain_only` で CPU)。

抜き取り(単独 `ops` の登録 op、入力 image、名前順に等間隔 12 件)。before = CPU(規則の前、手書き経路の
無い op は CPU)、after = `auto`:

| op | 一辺 | before(CPU)ms | after(auto)ms | 倍率 | after の経路 |
|---|---:|---:|---:|---:|---|
| `affine_trans_image` | 2048 | 271.34 | 15.68 | 17.30 | allow_single |
| `affine_trans_image` | 1024 | 66.84 | 66.88 | 1.00 | cpu(below_measured_size) |
| `aug_barrel` | 2048 | 307.20 | 23.40 | 13.13 | allow_single |
| `aug_barrel` | 1024 | 74.61 | 73.73 | 1.01 | cpu(below_measured_size) |
| `clahe` | 2048 | 343.41 | 36.65 | 9.37 | allow_single |
| `clahe` | 1024 | 89.21 | 89.67 | 0.99 | cpu(below_measured_size) |
| `edges_sub_pix` | 2048 | 1552 | 124.33 | 12.48 | allow_single |
| `edges_sub_pix` | 1024 | 196.42 | 196.20 | 1.00 | cpu(below_measured_size) |
| `gabor` | 2048 | 427.39 | 36.55 | 11.69 | allow_single |
| `gabor` | 1024 | 95.95 | 96.80 | 0.99 | cpu(below_measured_size) |
| `hx_gen_lowpass` | 2048 | 62.93 | 33.71 | 1.87 | allow_single |
| `hx_gen_lowpass` | 1024 | 12.56 | 12.23 | 1.03 | cpu(below_measured_size) |
| `it_bit_lshift` | 2048 | 124.41 | 37.71 | 3.30 | allow_single |
| `it_bit_lshift` | 1024 | 26.01 | 27.01 | 0.96 | cpu(below_measured_size) |
| `iv_wiener_deconv_spatial` | 2048 | 620.35 | 23.06 | 26.90 | allow_single |
| `iv_wiener_deconv_spatial` | 1024 | 130.82 | 130.07 | 1.01 | cpu(below_measured_size) |
| `median_rect` | 2048 | 1839 | 22.89 | 80.34 | allow_single |
| `median_rect` | 1024 | 457.88 | 456.25 | 1.00 | cpu(below_measured_size) |
| `quantize_lloyd_max` | 2048 | 1005 | 52.61 | 19.10 | allow_single |
| `quantize_lloyd_max` | 1024 | 248.15 | 247.55 | 1.00 | cpu(below_measured_size) |
| `sk_adjust_log` | 2048 | 104.53 | 38.19 | 2.74 | allow_single |
| `sk_adjust_log` | 1024 | 24.05 | 24.17 | 1.00 | cpu(below_measured_size) |
| `tf_gradient_domain_reintegrate` | 2048 | 592.97 | 23.85 | 24.86 | allow_single |
| `tf_gradient_domain_reintegrate` | 1024 | 121.01 | 113.41 | 1.07 | cpu(below_measured_size) |

`hx_gen_lowpass`(1.9 倍)・`sk_adjust_log`(2.7 倍)・`it_bit_lshift`(3.3 倍)は許可リストの 5 倍に
届いていない(掃引と別の環境・別の時刻。どれも CPU より速いので after < before は保たれる)。

## 5. VRAM の閾値

`auto` は GPU を選ぶ前に空き VRAM(`torch.cuda.mem_get_info`、無ければ CuPy の `memGetInfo`、どちらも
装置全体の空き = 他のプロセスの使用分を引いた値)を見て、`FULLSEYE_GPU_MIN_FREE_MB` 未満なら CPU
(`vram_low`)。問い合わせられなければ判定しない。値は 1 秒覚える。`0` で判定を切る。明示の `cuda` と
`FULLSEYE_DEVICE` はこの判定より優先する。

既定 **2048 MiB** の根拠(実測、`docs/perf/logs/crossover/ctx_mem.jsonl` と格子の `peak_mib`):

- CUDA の文脈: torch で 547 MiB(使用量 1123 → 1670 MiB)。CuPy は同じ文脈を使い増えなかった。
- 一辺 4096 の `gaussian` 1 枚で torch の確保 260 MiB。格子の一辺 4096 × 1 枚の作業領域は中央値 320 MiB、
  90 パーセンタイル 720 MiB(上位は `median` 3.4 GB・`percentile` 12.6 GB)。一辺 2048 × 1 枚は
  中央値 80 MiB・最大 3.2 GB。
- 文脈 550 + 一辺 4096 の 90 パーセンタイル 720 = 約 1.3 GB に、断片化と同時実行の余裕を足して 2048 MiB。
  `median` / `percentile` の大きい寸法はこれでも足りない(WDDM では OOM にならずページングで止まる)。
  LLM と GPU を分け合う機械では大きめに設定する。

## 6. 開示(AI と人が選ぶために)

- `fullseye.explain_device(device, stages=..., shape=...)` / `api.last_device_decision()`: 要求・出所・
  解決値・実際の装置・経路(`accel` / `allow_single` / `allow_resident` / `allow_pipeline` / `cpu` /
  `mixed`)・CPU を選んだ理由(`requested_cpu` / `env_cpu` / `no_cuda` / `vram_low` / `crossover` /
  `not_listed` / `chain_only` / `no_cupy` / `below_measured_size`)・段ごとの内訳・空き VRAM。
- MCP の結果の `acceleration` に `path` / `reason` / `resolved` / `source` / VRAM を追加(既存の
  `requested` / `device` / `approximate` はそのまま)。GPU で失敗して CPU で続いたときは `gpu_failed`。
  `fullseye_pipeline` は段ごとの行(`stages`)を返し、`n_transfers` は GPU で走った段ごとに往復 1 回で数える
  (MCP の pipeline は段ごとに `apply` を呼ぶので、常駐の区間の数ではない)。
- `fullseye_describe`(kind `op`)に `gpu_paths`: 手書き経路の有無、許可リストの枠と倍率、測った形、
  `auto` が GPU を選び始める大きさ(`auto_gpu_min_pixels`)。

## 測れなかったもの・残り

- 体積 512³ × 4 枚(VRAM 溢れ)、一辺 4096 × 100 枚(点演算以外)、鎖の一辺 4096 × 16 枚は測っていない。
- 閾値は 1 台の実測。GPU の弱い機械では境界は大きい側へ動くだけなので「CPU に残す」判断は崩れないが、
  CPU の極端に弱い機械では小さい画像で GPU の勝ちを取りこぼすことがある。
- `edge_dimension` は一辺 512 まで CPU が速いが、段に `median`(常に GPU)を含むので鎖の規則は GPU に
  残す(遅くはならないが取りこぼし)。
- 許可リストの道の自動選択は、測った大きさ以上だけ。小さい寸法の損益分岐は測っていない。
