# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ

- GPU: **NVIDIA GeForce RTX 5090** / torch 2.11.0+cu128
- OpenCV: cv2 4.11.0(CPU、単画像 API をバッチループ)
- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。

honest: **小さい単発画像は cv2 CPU が速い**(GPU は転送/起動律速)。GPU が効くのは**バッチ・大画像・常駐パイプライン**。以下は勝ち負け両方を出す。


## 512×512, batch=32

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 24.11 | 42.83 | 0.6× (cv2) | 747 | 1327 |
| median 5x5 | 48.34 | 51.49 | 0.9× (cv2) | 621 | 662 |
| box mean 5x5 | 31.17 | 42.47 | 0.7× (cv2) | 754 | 1027 |
| dilate 5x5 | 22.75 | 42.27 | 0.5× (cv2) | 757 | 1407 |
| erode 5x5 | 22.81 | 42.27 | 0.5× (cv2) | 757 | 1403 |
| sobel mag | 51.05 | 42.65 | 1.2× (**GPU**) | 750 | 627 |
| threshold | 20.13 | 42.22 | 0.5× (cv2) | 758 | 1589 |
| sharpen 3x3 | 32.81 | 42.43 | 0.8× (cv2) | 754 | 975 |
| morph open disk | 7.57 | 43.15 | 0.2× (cv2) | 742 | 4225 |
| NCC template match | 82.93 | 48.45 | 1.7× (**GPU**) | 661 | 386 |
| binarize pipeline (5-op resident) | 11.25 | 44.38 | 0.3× (cv2) | 721 | 2845 |

## 1024×1024, batch=16

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 53.76 | 102.82 | 0.5× (cv2) | 156 | 298 |
| median 5x5 | 80.75 | 101.71 | 0.8× (cv2) | 157 | 198 |
| box mean 5x5 | 54.78 | 84.84 | 0.6× (cv2) | 189 | 292 |
| dilate 5x5 | 37.00 | 85.00 | 0.4× (cv2) | 188 | 432 |
| erode 5x5 | 37.32 | 85.00 | 0.4× (cv2) | 188 | 429 |
| sobel mag | 87.42 | 85.56 | 1.0× (**GPU**) | 187 | 183 |
| threshold | 45.23 | 96.56 | 0.5× (cv2) | 166 | 354 |
| sharpen 3x3 | 55.39 | 100.47 | 0.6× (cv2) | 159 | 289 |
| morph open disk | 25.98 | 110.16 | 0.2× (cv2) | 145 | 616 |
| NCC template match | 181.24 | 97.29 | 1.9× (**GPU**) | 164 | 88 |
| binarize pipeline (5-op resident) | 34.41 | 87.43 | 0.4× (cv2) | 183 | 465 |

## 256×256, batch=1

| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |
|---|---:|---:|---:|---:|---:|
| gaussian σ=2.0 | 0.08 | 1.01 | 0.1× (cv2) | 987 | 11862 |
| median 5x5 | 0.32 | 0.47 | 0.7× (cv2) | 2122 | 3107 |
| box mean 5x5 | 0.10 | 0.42 | 0.2× (cv2) | 2360 | 9690 |
| dilate 5x5 | 0.04 | 0.25 | 0.2× (cv2) | 4062 | 25063 |
| erode 5x5 | 0.04 | 0.26 | 0.2× (cv2) | 3828 | 24155 |
| sobel mag | 0.08 | 0.40 | 0.2× (cv2) | 2515 | 13298 |
| threshold | 0.02 | 0.26 | 0.1× (cv2) | 3775 | 46948 |
| sharpen 3x3 | 0.07 | 0.29 | 0.2× (cv2) | 3465 | 14684 |
| morph open disk | 0.06 | 0.57 | 0.1× (cv2) | 1752 | 18116 |
| NCC template match | 0.48 | 0.86 | 0.6× (cv2) | 1160 | 2075 |
| binarize pipeline (5-op resident) | 0.10 | 1.19 | 0.1× (cv2) | 840 | 10278 |
