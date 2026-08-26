# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ

- GPU: **NVIDIA GeForce RTX 5090** / torch 2.11.0+cu128
- OpenCV: cv2 4.11.0(CPU、単画像 API をバッチループ)
- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。

## 結論(honest)

- **単発の軽量 2D フィルタは OpenCV CPU が速い**。cv2 は SIMD/多スレッドで極限まで最適化されており、GPU 側は **host↔device 転送が律速**(512²×32 で転送のみ **40 ms**、対して gaussian の実計算は **0.51 ms** = 転送の約 79 分の 1)。データが一度 GPU に載れば計算は桁違いに速いが、1 op だけでは転送を取り戻せない。
- **GPU が OpenCV に勝つのは 3 条件**: (1) 計算が重い op(NCC テンプレートマッチング)、(2) **多 op を常駐で連鎖**して転送を償却(= E2E 本丸 `accel.run_pipeline`)、(3) **3D**(cv2 に無い)。
- imgevolve の設計(常駐パイプライン + 進化 champion を丸ごと GPU)はまさに (2) を突く。以前の「64x/3-5x」は **scipy 比**であり、最強 CPU=cv2 比では上記の通り条件付き。正直に開示する。

## 常駐パイプラインの転送償却(N-op、512²×32)

同じ gaussian を N 回。cv2 は逐次、GPU は転送1回で N op 連鎖。**N が増えるほど GPU 有利**。

| N op | cv2 CPU (ms) | GPU 常駐 (ms) | speedup |
|---:|---:|---:|---:|
| 1 | 23.9 | 40.8 | 0.6× (cv2) |
| 3 | 47.7 | 41.6 | 1.1× (**GPU**) |
| 5 | 72.7 | 42.6 | 1.7× (**GPU**) |
| 10 | 130.0 | 44.6 | 2.9× (**GPU**) |
| 20 | 253.6 | 49.7 | 5.1× (**GPU**) |

## 3D volume(cv2 に 3D 無し → scipy 比)

| size×batch | scipy CPU (ms) | GPU (ms) | speedup |
|---|---:|---:|---:|
| 32³×32 | 551 | 7.8 | **71×** |
| 64³×16 | 2237 | 34.5 | **65×** |
| 128³×4 | 4567 | 71.1 | **64×** |

## 単発 op 比較 512×512, batch=32

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 23.33 | 39.97 | 0.6× (cv2) | 801 | 1372 |
| median 5x5 | 45.42 | 48.91 | 0.9× (cv2) | 654 | 704 |
| box mean 5x5 | 27.89 | 40.51 | 0.7× (cv2) | 790 | 1147 |
| dilate 5x5 | 20.06 | 40.06 | 0.5× (cv2) | 799 | 1595 |
| erode 5x5 | 19.40 | 39.86 | 0.5× (cv2) | 803 | 1650 |
| sobel mag | 46.06 | 40.16 | 1.1× (**GPU**) | 797 | 695 |
| threshold | 19.88 | 41.11 | 0.5× (cv2) | 778 | 1610 |
| sharpen 3x3 | 29.00 | 45.77 | 0.6× (cv2) | 699 | 1104 |
| morph open disk | 7.49 | 50.06 | 0.1× (cv2) | 639 | 4270 |
| NCC template match | 83.34 | 62.48 | 1.3× (**GPU**) | 512 | 384 |
| binarize pipeline (5-op resident) | 11.20 | 60.22 | 0.2× (cv2) | 531 | 2858 |

## 単発 op 比較 1024×1024, batch=16

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 47.45 | 95.06 | 0.5× (cv2) | 168 | 337 |
| median 5x5 | 79.40 | 101.48 | 0.8× (cv2) | 158 | 202 |
| box mean 5x5 | 54.61 | 84.01 | 0.7× (cv2) | 190 | 293 |
| dilate 5x5 | 36.51 | 82.79 | 0.4× (cv2) | 193 | 438 |
| erode 5x5 | 36.63 | 104.68 | 0.3× (cv2) | 153 | 437 |
| sobel mag | 86.30 | 108.90 | 0.8× (cv2) | 147 | 185 |
| threshold | 36.04 | 95.79 | 0.4× (cv2) | 167 | 444 |
| sharpen 3x3 | 55.37 | 100.63 | 0.6× (cv2) | 159 | 289 |
| morph open disk | 20.60 | 110.42 | 0.2× (cv2) | 145 | 777 |
| NCC template match | 182.34 | 98.63 | 1.8× (**GPU**) | 162 | 88 |
| binarize pipeline (5-op resident) | 37.32 | 86.70 | 0.4× (cv2) | 185 | 429 |

## 単発 op 比較 256×256, batch=1

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 0.08 | 0.50 | 0.2× (cv2) | 1985 | 12270 |
| median 5x5 | 0.34 | 0.34 | 1.0× (**GPU**) | 2930 | 2910 |
| box mean 5x5 | 0.10 | 0.27 | 0.4× (cv2) | 3679 | 9643 |
| dilate 5x5 | 0.04 | 0.21 | 0.2× (cv2) | 4715 | 23810 |
| erode 5x5 | 0.04 | 0.20 | 0.2× (cv2) | 4926 | 25381 |
| sobel mag | 0.08 | 0.37 | 0.2× (cv2) | 2737 | 12642 |
| threshold | 0.02 | 0.21 | 0.1× (cv2) | 4735 | 44053 |
| sharpen 3x3 | 0.07 | 0.29 | 0.2× (cv2) | 3416 | 14599 |
| morph open disk | 0.05 | 0.53 | 0.1× (cv2) | 1900 | 18587 |
| NCC template match | 0.48 | 0.87 | 0.6× (cv2) | 1152 | 2091 |
| binarize pipeline (5-op resident) | 0.10 | 1.13 | 0.1× (cv2) | 888 | 10373 |
