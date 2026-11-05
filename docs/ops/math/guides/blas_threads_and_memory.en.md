---
guide: blas_threads_and_memory
dim: math
title: Why matrix decompositions are slow — BLAS threads, caches, memory layout
title_en: Why matrix decompositions are slow — BLAS threads, caches, memory layout
title_zh: 矩阵分解为何慢 —— BLAS 线程、缓存、内存布局
title_tw: 矩陣分解為何慢 —— BLAS 執行緒、快取、記憶體配置
title_ko: 행렬 분해가 느린 이유 — BLAS 스레드·캐시·메모리 배치
title_de: Warum Matrixzerlegungen langsam sind — BLAS-Threads, Caches, Speicherlayout
title_hi: Matrix decompositions धीमे क्यों हैं — BLAS threads, caches, memory layout
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: math/linalg, 2d/decomposition, 3d/robust_fit, 3d/surface_fit, 3d/curvature, 3d/feature_register
lang: en
translation_of: docs/ops/math/guides/blas_threads_and_memory.md
source_sha256: 41f775e68eb90744f52ed8e273adedd39378588b2ac46a9eba2ecb3f3f3167cd
---

# Why matrix decompositions are slow — BLAS threads, caches, memory layout

When an op that includes an SVD or eigendecomposition is "slow for some reason", the cause is often not the algorithm but
**how BLAS is being used**. This document is not a description of ops; it is teaching material on
the order in which to suspect things there, and how to measure and confirm.

All values were measured on my own machine on 2026-09-06, and the only source is my own measurement
(24 logical CPUs / OpenBLAS 0.3.31 / numpy 2.4.6 / Windows, other load stopped,
median). On other machines the numbers will change, but **the direction of the trends** should reproduce.

---

## 1. The most effective and the most overlooked — thread over-subscription

Both OpenBLAS and MKL set the thread count from the **number of logical CPUs** by default.
For matrix multiplication that is right. For decompositions it is not.

```
np.linalg.svd(n x n, full_matrices=False)      unit ms
n        1t      2t      4t      8t     24t   fastest
48    0.165   0.195   0.266   0.344   0.651   1t
96    0.650   0.918   1.081   1.305   2.217   1t
384  19.331  23.572  21.686  28.090  36.243   1t
512   45.9    44.0    45.5    47.3   105.3    2t
1024 351.7   320.0   259.4   262.4   868.8    4t
2048 2675    1950    1600    1344    3263     8t

For reference: matrix product a @ a has the opposite trend (at 768, 1t 14.0ms / 8t 2.4ms = 5.8 times faster)
```

Across 4 kinds (svd / eigh / qr / pinv) × 7 sizes, **there is not even 1 cell where 24 threads won**.
The GEMMs inside the decompositions are too small, so the cost of synchronisation exceeds the amount of computation.

### Decision

* If you think a decomposition is slow, **suspect the thread count before suspecting the algorithm**.
  The check is 1 line: if `OPENBLAS_NUM_THREADS=1 python your_script.py` makes it faster, that is it.
* **Do not throttle the whole process.** Matrix multiplication becomes slower instead. Throttle only around the decomposition.
* In fullseye, `fsthreads` does this automatically. To turn it off use
  `FULLSEYE_BLAS_THREADS=off`; to pin it use `FULLSEYE_BLAS_THREADS=1`.

### Trap — this is not only about speed

When the thread count changes, the order of reductions changes, so **the results of a decomposition change in the low-order bits**.

```
svd(64x64)   1t vs 24t   bitwise match False   max diff 3.6e-16
eigh(256)    1t vs 24t   bitwise match False   max diff 1.7e-12
```

The thread count is decided from the number of logical CPUs, so **doing nothing produces different values on different machines**.
The low-order bits of a decomposition do not match between a 4-core CI and a 24-core development machine.
This can be the cause of "passes locally but falls outside tolerance on CI".
If you need reproducibility, pin the thread count explicitly.

---

## 2. What to look at to set the cap — the short side. Not the long side, not the element count

On a grid of 92 cells of (m, n) (svd and lstsq), for each predictor I measured "the time lost when the
thread cap is decided by that rule alone".

```
Rule                            time lost   cells over 1.2x    worst
Do nothing (left at 24t)        3975ms       79/92 cells       19.91x
Short side <512:1 <1024:4 else:8 303ms        5/92 cells        1.41x
Elements <512:1 <1024:4 else:8   235ms       14/92 cells        2.50x
Long side <512:1 <1024:4 else:8  241ms       ---                3.89x
```

### Decision

**On the total, the element count and the long side win. The short side is adopted anyway.** The difference in the worst case
(1.41 times versus 2.50 / 3.89 times) weighs more than the 68ms difference in the total.
Being only 4 tenths slower even in the worst case is easier to operate with than being 1 tenth faster on average.

Reasoning: LAPACK's workload is roughly `長辺 × 短辺²` (long side × short side squared), and whether threads help is
decided by the block width of the short side. Counting a `16384x3` least-squares as a "large matrix" by its long side
would allow 8 threads, but in reality it is a QR of width 3.

### Rule-of-thumb conversion

| Short side | Threads allowed | Basis |
| --- | --- | --- |
| Under 32 | Do not touch | The throttling mechanism itself costs 2.4 µs. Wrapping it around decompositions faster than that is a loss |
| 32–511 | 1 | No cell in this range where multiple threads won |
| 512–1023 | 4 | Neck and neck with 1t; 4t begins to win at the upper end |
| 1024 and above | 8 | At 2048, 8t is 2.0 times faster than 1t. 24t is the worst everywhere |

---

## 3. Sides that are powers of 2 are slow due to cache conflicts (a story equivalent to `#pragma pack`)

When the leading dimension is a power of 2, cache sets collide and things slow down.
This is why dense-matrix libraries deliberately offset lda when allocating.

```
Single-thread effective GFLOPS of svd (* = power of 2)
n     255    256*    257    264      -> only the power is 13% slower
    27.9    26.1    30.4   30.9
n     511    512*    513    520      -> 18% slower
    41.4    34.6    41.2   44.1
n    1023   1024*   1025   1032      -> 19% slower
    43.9    35.9    44.4   44.5
At n = 64 / 128 there is no difference (it fits in cache, so no conflicts occur)
```

### Decision

* **13–19% is real.** If you benchmark only at power-of-2 sizes,
  you will record the values that are slow only there as "normal performance".
* However, **the fastest thread count does not change** (255/256/257/264 are all 1t,
  1023/1024/1025/1032 are all 4t). It does not affect the thread decision.
* When measuring performance, deliberately add 1 point off the power of 2.
  Otherwise "the distribution of cells" is biased — there will not be even 1 point like square 1023.

---

## 4. Row-major vs column-major — converting before use usually does not pay off

numpy is row-major and LAPACK is column-major, so a reordering happens at every decomposition.
It is tempting to think "then just pass it column-major", but **once the cost of conversion is included, it loses**.

```
lstsq                as is      convert & pass  column-major from start  conversion only
(65536,   36)         27.4ms    26.0 (0.95x)   17.6 (0.64x)     6.4ms
(16384,  128)         43.9      50.1 (1.14x)   39.0 (0.89x)     8.5
( 4096,  512)        414.5     676.5 (1.63x)  432.8 (1.04x)     8.8
( 1024, 1024)        172.3     178.6 (1.04x)  177.1 (1.03x)     3.6
```

Passing after `np.asfortranarray` **is slower** for 4 of the 5 shapes.
The copy takes 6–9 ms, and the saving is less than that.

### Isn't a transposed view free? — only the view is free

```
taking a.T                   0.10 µs     only swaps strides = truly free
np.ascontiguousarray(a.T)    6.5-8.7 ms  turning it back is a real copy
svd(A.T) then swap U,V:
  (16384,128) 1.90 times slower / (4096,512) 1.11 times / (1024,1024) 1.04 times
  (the singular values match. Mathematically correct, yet it loses on run time)
```

Since `A = (Aᵀ)ᵀ`, swapping U and V of `svd(A.T)` gives `svd(A)`, but
LAPACK goes down **a different path** for it as an (n, m) wide matrix, so it is slower.

### Decision

* "Column-major is faster" is correct only when the data **is already column-major**.
* It helps only when "it is assembled column-major from the start, and it is tall".
  Where a design matrix is built with `np.stack(..., axis=1)`, simply allocating with `order="F"`
  gains around 3 tenths when tall (0.64 times at `(65536,36)`).
* Otherwise, leave it alone. A design that transposes and transposes back costs more than it gains.

---

## 5. Using the contiguous axis deliberately — sorting and order statistics (a topic on a different axis from decompositions)

So far this has been about LAPACK, but there are also designs that actively use "the fast direction".
numpy is row-major, so **the last axis is contiguous**. If the same operation lets you choose the axis,
lean towards the contiguous axis.

```
np.sort (unit ms)
shape            dtype     axis=-1(contig.)  axis=0(strided)   ratio
(65536,   32)   float32        3.68           18.39        5.00
( 4096,  256)   float32        1.95            9.12        4.67
( 4096,  256)   float64        5.42           13.94        2.57
( 1024, 1024)   float64        5.91           12.27        2.08
```

### Trap — "a smaller type is faster" does not hold

Even if the same array is quantised, **comparison sorting does not get faster. It is actually slower.**

```
np.sort(axis=-1) on (1024,1024)
  float64  5.91ms      float32  3.04ms
  uint16  21.97ms      uint8   21.03ms      <- 3.6 times slower than float64
```

numpy's sort for floats goes down a SIMD-optimised path, but small integer types
are not on it (in this version). **Making the dtype smaller does not, by itself, buy speed.**

1 more trap: in the table above, only uint8 at `(256, 4096)` looks faster with `axis=0`
(19.45 vs 22.57). This is not an effect of layout but of **the length of 1 sort**:
`axis=0` performs 4096 sorts of length 256, and `axis=-1` performs 256 sorts of length 4096.
When comparing axes, first check **whether the length has changed**.

### What quantisation really buys — being able to skip sorting

The gain comes not from the type but from **the value range being finite**. uint8 has only 256 possible values, so
counting is enough without sorting.

```
Full sort of uint8
  n = 16,777,216   np.sort 355.8ms  ->  counting sort 66.7ms   5.33 times
  n =  2,097,152   np.sort  43.8ms  ->  counting sort  8.5ms   5.17 times

Median of uint8 (order statistics do not need sorting in the first place)
  n = 8,388,608    np.median 35.6ms -> histogram 27.6ms  1.3 times
  n = 1,048,576    np.median  6.4ms -> histogram  3.7ms  1.7 times
```

A counting sort just counts with `np.bincount(a, minlength=256)` and
expands with `np.repeat(np.arange(256, dtype=np.uint8), counts)`.
For the median, applying `searchsorted` to the cumulative sum means not even the expansion is needed.

### Decision

* Lean operations whose axis can be chosen (sort, cumulative, reduction) towards **the last axis**. 2–5 times.
* **If you introduce quantisation for speed, put it on the counting path, not comparison sorting.**
  Calling `np.sort` on uint8/uint16 as is ends up slower than float.
* Order statistics (median, percentile, rank filter), if quantised, can be replaced by
  the cumulative sum of a histogram. The sorting disappears.

### What did not work (kept on record)

For "distance + argmin" over N D-dimensional descriptors, I compared placing the descriptors in rows versus columns,
and **no significant difference appeared** (1.00 times at 4096×64, 1.06 times at 8192×128,
0.97 times at 2048×256), because `einsum` absorbs the strides.
The effect of layout is limited to "operations whose axis can be chosen", and does not appear in operations that involve contraction.

---

## 6. The order of suspicion

When processing that includes decompositions is slow, check in this order. The higher, the more likely to help and the cheaper to check.

1. **Thread count** — does `OPENBLAS_NUM_THREADS=1` make it faster (1 line, a few seconds)
2. **Size and shape of the matrix** — what is the short side? Tall or square?
3. **Number of calls** — is 1 call slow, or are you calling a small one tens of thousands of times?
   (In the latter case the cost of the throttling mechanism is the more expensive part. On a path that runs a 3×3 eigh 20,000 times,
   calling `threadpool_limits` every 1 call made it 1.9 times slower: 58.9ms → 112.9ms)
4. **Are the sizes powers of 2** — are the benchmark sizes biased?
5. **Memory layout** — only once you have got this far. And even then converting is of little value

### Cautions on measurement

* `threadpoolctl.threadpool_limits(...)` **recounts the already-loaded shared libraries** every time,
  so 1 call takes 312 µs. Holding 1 `ThreadpoolController` and
  reusing it takes 2.4 µs. Inside a loop use the latter, and even that should be placed **1 time outside the loop**.
* Take the **median**, not the minimum. The minimum picks up "the 1 run that happened to be fast"
  and does not represent everyday speed.
* Confirm that no other process is holding the CPU before measuring.
  The numbers in the first edition of this document were taken while 3 processes I had left running occupied 3 cores,
  and they overstated the ratios by 2–3 times (83 times at 48×48 → actually 27 times).

---

## 7. From symptom to cause

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| The machine with more cores is slower | BLAS thread over-subscription | Re-run with `OPENBLAS_NUM_THREADS=1`. If it gets faster, that is it |
| Fast locally but slow on CI (or the reverse) | Different number of logical CPUs | Print `threadpoolctl.threadpool_info()` on both and compare |
| Passes locally but falls outside tolerance on CI | The thread count changes the reduction order and the low-order bits move | Pin the same thread count on both and re-run. If the difference disappears, that is it |
| Processing that runs many small matrices got slower after throttling | The cost of the throttling mechanism itself (2.4 µs per 1 call; 312 µs if calling `threadpool_limits` directly) | Place it only 1 time outside the loop. If the short side is under 32, do nothing |
| Least squares on a tall matrix is slower than expected | It is judged a "large matrix" by its long side and threads are allowed | Judge by the short side (number of columns). `16384x3` is a QR of width 3 |
| Only the benchmark is oddly slow | Sizes are powers of 2, causing cache set conflicts | Measure n and n±1 side by side. If a 13–19% difference appears, that is it |
| Made it column-major but it did not get faster | The copy cost of `np.asfortranarray` exceeds the saving | Measure the conversion time alone and compare it with the saving |
| Quantised it but `np.sort` did not get faster | Small integer types are not on the SIMD path | Replace with a counting sort using `np.bincount` and compare |
| Stack median is slow | `np.median(cube, axis=0)` is a non-contiguous axis + full median computation | For an odd number of frames use `np.partition`; for many frames move the axis to the contiguous side |

---

## Related

* `fsthreads` — the layer in fullseye that implements this cap. The step table and measurements are in its docstring.
* `math_metrology` / `measurement_uncertainty` — handling of measured values (this document is about
  "the order in which to suspect speed before measuring", a different subject).

### External primary sources

**All numbers in this document are my own measurements**; not even 1 value is taken from outside.
The following are sources for the specifications and implementations themselves (reachability confirmed on 2026-09-06).

* threadpoolctl (implementation of thread caps. BSD-3) — <https://github.com/joblib/threadpoolctl>
* LAPACK Users' Guide (computational cost and blocking of decompositions) — <https://www.netlib.org/lapack/lug/>
* numpy's linear algebra API — <https://numpy.org/doc/stable/reference/routines.linalg.html>
