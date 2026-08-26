# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ

- GPU: **NVIDIA GeForce RTX 5090** / torch 2.11.0+cu128
- OpenCV: cv2 4.11.0(CPU、単画像 API をバッチループ)
- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。

## 結論(honest)

- **単発の軽量 2D フィルタは OpenCV CPU が速い**。cv2 は SIMD/多スレッドで極限まで最適化されており、GPU 側は **host↔device 転送が律速**(512²×32 で転送のみ **39 ms**、対して gaussian の実計算は **0.49 ms** = 転送の約 80 分の 1)。データが一度 GPU に載れば計算は桁違いに速いが、1 op だけでは転送を取り戻せない。
- **GPU が OpenCV に勝つのは 3 条件**: (1) 計算が重い op(NCC テンプレートマッチング)、(2) **多 op を常駐で連鎖**して転送を償却(= E2E 本丸 `accel.run_pipeline`)、(3) **3D**(cv2 に無い)。
- imgevolve の設計(常駐パイプライン + 進化 champion を丸ごと GPU)はまさに (2) を突く。以前の「64x/3-5x」は **scipy 比**であり、最強 CPU=cv2 比では上記の通り条件付き。正直に開示する。
- **cv2 ≒ HALCON 級の最適化 CPU** なので、この比較は fullseye が目標とする HALCON との性能差の予測にもなる(単発は HALCON 級 CPU が速い / 常駐多op・NCC・3D で GPU が上回る、と読める)。

## 計算が重い op(GPU の本領、単発でも勝ちうる)

| op | baseline | baseline (ms) | GPU (ms) | speedup |
|---|---|---:|---:|---:|
| gaussian σ=8 (大kernel) | cv2 | 56.0 | 40.9 | 1.4× (**GPU**) |
| sk_tv TV denoise (B=8) | CPU-torch | 168.5 | 28.3 | 5.9× (**GPU**) |

## 常駐パイプラインの転送償却(N-op、512²×32)

同じ gaussian を N 回。cv2 は逐次、GPU は転送1回で N op 連鎖。**N が増えるほど GPU 有利**。

| N op | cv2 CPU (ms) | GPU 常駐 (ms) | speedup |
|---:|---:|---:|---:|
| 1 | 23.5 | 40.2 | 0.6× (cv2) |
| 3 | 48.5 | 41.1 | 1.2× (**GPU**) |
| 5 | 70.7 | 43.3 | 1.6× (**GPU**) |
| 10 | 130.3 | 45.0 | 2.9× (**GPU**) |
| 20 | 248.4 | 49.9 | 5.0× (**GPU**) |

## 3D volume(cv2 に 3D 無し → scipy 比)

| size×batch | scipy CPU (ms) | GPU (ms) | speedup |
|---|---:|---:|---:|
| 32³×32 | 552 | 7.9 | **69×** |
| 64³×16 | 2233 | 34.1 | **65×** |
| 128³×4 | 4558 | 69.3 | **66×** |

## 単発 op 比較 512×512, batch=32

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 23.66 | 40.42 | 0.6× (cv2) | 792 | 1353 |
| median 5x5 | 45.28 | 49.40 | 0.9× (cv2) | 648 | 707 |
| box mean 5x5 | 27.64 | 39.95 | 0.7× (cv2) | 801 | 1158 |
| dilate 5x5 | 19.42 | 40.75 | 0.5× (cv2) | 785 | 1648 |
| erode 5x5 | 19.48 | 39.69 | 0.5× (cv2) | 806 | 1643 |
| sobel mag | 45.96 | 42.46 | 1.1× (**GPU**) | 754 | 696 |
| threshold | 19.32 | 39.69 | 0.5× (cv2) | 806 | 1657 |
| sharpen 3x3 | 28.73 | 46.37 | 0.6× (cv2) | 690 | 1114 |
| morph open disk | 7.38 | 49.41 | 0.1× (cv2) | 648 | 4337 |
| NCC template match | 84.07 | 62.63 | 1.3× (**GPU**) | 511 | 381 |
| binarize pipeline (5-op resident) | 11.28 | 54.38 | 0.2× (cv2) | 588 | 2836 |

## 単発 op 比較 1024×1024, batch=16

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 47.40 | 96.85 | 0.5× (cv2) | 165 | 338 |
| median 5x5 | 80.57 | 100.65 | 0.8× (cv2) | 159 | 199 |
| box mean 5x5 | 54.55 | 81.79 | 0.7× (cv2) | 196 | 293 |
| dilate 5x5 | 36.44 | 81.85 | 0.4× (cv2) | 195 | 439 |
| erode 5x5 | 36.26 | 101.62 | 0.4× (cv2) | 157 | 441 |
| sobel mag | 87.07 | 111.51 | 0.8× (cv2) | 143 | 184 |
| threshold | 34.98 | 95.43 | 0.4× (cv2) | 168 | 457 |
| sharpen 3x3 | 55.09 | 101.19 | 0.5× (cv2) | 158 | 290 |
| morph open disk | 20.41 | 109.80 | 0.2× (cv2) | 146 | 784 |
| NCC template match | 182.44 | 97.57 | 1.9× (**GPU**) | 164 | 88 |
| binarize pipeline (5-op resident) | 33.19 | 84.56 | 0.4× (cv2) | 189 | 482 |

## 単発 op 比較 256×256, batch=1

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 0.08 | 0.53 | 0.2× (cv2) | 1881 | 12034 |
| median 5x5 | 0.32 | 0.33 | 1.0× (cv2) | 3017 | 3161 |
| box mean 5x5 | 0.10 | 0.42 | 0.2× (cv2) | 2378 | 9766 |
| dilate 5x5 | 0.04 | 0.20 | 0.2× (cv2) | 4948 | 24876 |
| erode 5x5 | 0.04 | 0.20 | 0.2× (cv2) | 4904 | 25252 |
| sobel mag | 0.07 | 0.38 | 0.2× (cv2) | 2654 | 13405 |
| threshold | 0.02 | 0.21 | 0.1× (cv2) | 4699 | 47169 |
| sharpen 3x3 | 0.07 | 0.27 | 0.2× (cv2) | 3716 | 15083 |
| morph open disk | 0.06 | 0.54 | 0.1× (cv2) | 1843 | 17544 |
| NCC template match | 0.48 | 0.91 | 0.5× (cv2) | 1103 | 2099 |
| binarize pipeline (5-op resident) | 0.10 | 1.11 | 0.1× (cv2) | 901 | 10215 |
