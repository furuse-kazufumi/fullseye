# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ

- GPU: **NVIDIA GeForce RTX 5090** / torch 2.11.0+cu128
- OpenCV: cv2 4.11.0(CPU、単画像 API をバッチループ)
- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。

## 結論(honest)

- **単発の軽量 2D フィルタは OpenCV CPU が速い**。cv2 は SIMD/多スレッドで極限まで最適化されており、GPU 側は **host↔device 転送が律速**(512²×32 で転送のみ **42 ms**、対して gaussian の実計算は **0.52 ms** = 転送の約 81 分の 1)。データが一度 GPU に載れば計算は桁違いに速いが、1 op だけでは転送を取り戻せない。
- **GPU が OpenCV に勝つのは 3 条件**: (1) 計算が重い op(NCC テンプレートマッチング)、(2) **多 op を常駐で連鎖**して転送を償却(= E2E 本丸 `accel.run_pipeline`)、(3) **3D**(cv2 に無い)。
- imgevolve の設計(常駐パイプライン + 進化 champion を丸ごと GPU)はまさに (2) を突く。以前の「64x/3-5x」は **scipy 比**であり、最強 CPU=cv2 比では上記の通り条件付き。正直に開示する。

## 常駐パイプラインの転送償却(N-op、512²×32)

同じ gaussian を N 回。cv2 は逐次、GPU は転送1回で N op 連鎖。**N が増えるほど GPU 有利**。

| N op | cv2 CPU (ms) | GPU 常駐 (ms) | speedup |
|---:|---:|---:|---:|
| 1 | 23.6 | 42.9 | 0.5× (cv2) |
| 3 | 50.8 | 43.8 | 1.2× (**GPU**) |
| 5 | 72.0 | 44.9 | 1.6× (**GPU**) |
| 10 | 129.8 | 46.6 | 2.8× (**GPU**) |
| 20 | 250.5 | 51.4 | 4.9× (**GPU**) |

## 3D volume(cv2 に 3D 無し → scipy 比)

| size×batch | scipy CPU (ms) | GPU (ms) | speedup |
|---|---:|---:|---:|
| 32³×32 | 554 | 8.6 | **65×** |
| 64³×16 | 2233 | 35.5 | **63×** |
| 128³×4 | 4555 | 70.5 | **65×** |

## 単発 op 比較 512×512, batch=32

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 25.81 | 42.77 | 0.6× (cv2) | 748 | 1240 |
| median 5x5 | 47.15 | 51.14 | 0.9× (cv2) | 626 | 679 |
| box mean 5x5 | 31.19 | 42.54 | 0.7× (cv2) | 752 | 1026 |
| dilate 5x5 | 21.99 | 42.36 | 0.5× (cv2) | 756 | 1455 |
| erode 5x5 | 21.81 | 42.39 | 0.5× (cv2) | 755 | 1467 |
| sobel mag | 51.97 | 42.57 | 1.2× (**GPU**) | 752 | 616 |
| threshold | 19.96 | 41.99 | 0.5× (cv2) | 762 | 1603 |
| sharpen 3x3 | 32.65 | 48.88 | 0.7× (cv2) | 655 | 980 |
| morph open disk | 7.44 | 51.31 | 0.1× (cv2) | 624 | 4303 |
| NCC template match | 84.76 | 48.94 | 1.7× (**GPU**) | 654 | 378 |
| binarize pipeline (5-op resident) | 11.23 | 44.72 | 0.3× (cv2) | 715 | 2850 |

## 単発 op 比較 1024×1024, batch=16

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 48.52 | 85.62 | 0.6× (cv2) | 187 | 330 |
| median 5x5 | 79.93 | 104.04 | 0.8× (cv2) | 154 | 200 |
| box mean 5x5 | 55.71 | 84.60 | 0.7× (cv2) | 189 | 287 |
| dilate 5x5 | 40.14 | 84.81 | 0.5× (cv2) | 189 | 399 |
| erode 5x5 | 37.67 | 103.02 | 0.4× (cv2) | 155 | 425 |
| sobel mag | 86.74 | 112.41 | 0.8× (cv2) | 142 | 184 |
| threshold | 39.55 | 84.46 | 0.5× (cv2) | 189 | 405 |
| sharpen 3x3 | 54.67 | 84.66 | 0.6× (cv2) | 189 | 293 |
| morph open disk | 27.29 | 85.45 | 0.3× (cv2) | 187 | 586 |
| NCC template match | 180.52 | 98.07 | 1.8× (**GPU**) | 163 | 89 |
| binarize pipeline (5-op resident) | 36.17 | 89.27 | 0.4× (cv2) | 179 | 442 |

## 単発 op 比較 256×256, batch=1

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 0.08 | 0.55 | 0.1× (cv2) | 1807 | 12136 |
| median 5x5 | 0.31 | 0.35 | 0.9× (cv2) | 2889 | 3186 |
| box mean 5x5 | 0.10 | 0.32 | 0.3× (cv2) | 3107 | 9671 |
| dilate 5x5 | 0.05 | 0.21 | 0.2× (cv2) | 4739 | 22173 |
| erode 5x5 | 0.04 | 0.24 | 0.2× (cv2) | 4090 | 25381 |
| sobel mag | 0.07 | 0.41 | 0.2× (cv2) | 2442 | 13405 |
| threshold | 0.02 | 0.24 | 0.1× (cv2) | 4153 | 43668 |
| sharpen 3x3 | 0.07 | 0.29 | 0.2× (cv2) | 3419 | 15129 |
| morph open disk | 0.06 | 0.56 | 0.1× (cv2) | 1777 | 17953 |
| NCC template match | 0.48 | 0.84 | 0.6× (cv2) | 1185 | 2080 |
| binarize pipeline (5-op resident) | 0.10 | 1.15 | 0.1× (cv2) | 868 | 10111 |
