<!-- i18n-source-sha: aaba6c6be932 -->
# GPU Optimization Design-Pattern Catalog (for RTX 5090 / Blackwell sm_120)

[日本語](./GPU_OPTIMIZATION_PATTERNS.md) · **English**

**Target GPU (confirmed)**: NVIDIA RTX 5090, Blackwell, compute capability **sm_120**, 32 GB VRAM, driver 610.74.
**Current state (confirmed)**: Only `torch 2.11.0+cpu` and `jax 0.7.1` (CpuDevice) are installed, so **nothing runs on the GPU right now**. sm_120 requires a build from the CUDA 12.8+ generation.
**Nature of this catalog**: Written without web search, from the RAD corpus (`D:/docs/*_corpus_v2/`, existence confirmed) plus a knowledge base. **Guesses are explicitly marked "(guess)"**. Each workload is tied back to real code that was read (`physarum_search.py` / `shapematch.py` / `afterman/eco_world.py`).

Source notation:
- **[corpus]** = a paper whose existence was confirmed in the RAD corpus (cited with its arXiv number).
- **[knowledge]** = general GPU programming knowledge (outside the corpus).
- **(guess)** = an unverified hunch. Do not trust it until confirmed by measurement or primary sources.

---

## 0. Structure of our three workloads (measured from the code)

| # | Workload | Compute core | Current bottleneck | Batch dimension | Precision requirement |
|---|---|---|---|---|---|
| 1 | Physarum solver `physarum_search.py` | Linear solve of the Laplacian `L(D)p=b` × time iteration (conductivity D updated every iteration) | **Dense n×n solved every iteration** with `torch.linalg.solve` (O(n³)). Worse, `A` is rebuilt every iteration with `torch.zeros(n,n)` | Many mazes × many parameters (μ, dt, D_init) | **fp64** (measured from code: fixed to `torch.float64`. The Laplacian is prone to poor conditioning) |
| 2 | Shape matching `shapematch.py` | Inner product of template edge-gradient vectors with image gradients, evaluated over many positions × scales × angles | Python double loop `_scan_flat` / `_score_at` (fancy-index inner products). Scale/angle are also Python loops | Position × scale × angle × multiple instances | fp32 is enough (inner product of gradient directions; the dynamic range of the correlation is narrow) |
| 3 | Afterman evolution `afterman/eco_world.py` | Parallel forward evaluation of a population (RNN policies) + structural evolution | **Already cleanly batched in JAX** (per-individual weights `w_in/w_rec/w_out` via `einsum("nij,nj->ni")`, T steps via `lax.scan`, `jit(static_argnums=1)`) | Population size n | fp32/bf16 is enough (evolutionary fitness only needs to be approximate) |

**Key asymmetry**: #3 is already written GPU-ready (SoA + batched einsum + scan). #1 and #2 are "Python loops + sequential dense solve" and have the most headroom for GPU acceleration. **Priority: #1 and #2 first; #3 mostly just works once the wheel is installed and `jax.devices()` becomes cuda** (details in §5).

---

## 1. Design-pattern catalog

Each pattern = **name / when to use / pitfall / which of ours it helps**.

### Types of parallelism

#### P1. Data-parallel (straightforward SIMT parallelism)
- **When**: the same operation applied to independent elements (per pixel, per individual, per edge). The most natural form for a GPU.
- **Pitfall**: branch divergence (if threads within a warp take different paths, they serialize). Branches like `if cfg.contested:` should take **the same branch across the whole batch** to avoid warp divergence [knowledge].
- **Helps**: all of them. Especially #3 (per-individual independent RNNs) and #2 (per-position independent scoring).

#### P2. Batched-kernel (fold many small problems into one kernel) ★ most important
- **When**: solving "a large number of small linear systems / small correlations". Submitting them to the GPU one at a time lets **kernel-launch latency (a few µs each) and H2D transfer** dominate, making it slower than CPU. Fold them into a single kernel / single API call.
- **Concretely**: `torch.linalg.solve` has a **batched form** (leading dimension is the batch). Passing `(B, n, n)` solves B systems in one call. cuSOLVER's batched API and cuBLAS `*gemmStridedBatched` do the work underneath [knowledge]. For sparse, **torch-sla explicitly supports "batched solve over a shared or per-instance sparsity pattern"** [corpus: torch-sla, arXiv 2601.13994].
- **Pitfall**: if sizes differ within the batch, padding is needed (P8). If the batch is too small, occupancy stays low.
- **Helps**: **#1 (solve many mazes at once — this is the main win)**, #2 (fold many scales/angles onto the batch axis).

#### P3. Warp cooperation (reduction via shared memory + warp shuffle)
- **When**: a problem that is "too big for one thread but fits in one block" — medium scale. Load it into shared memory within a block and eliminate inter-block synchronization.
- **Concretely**: **partition a sparse triangular solve into subdomains, map each subdomain to one thread block, size the vector to fit in shared memory to eliminate inter-block synchronization and reduce irregular global access → triangular solve 10.7×, ILU0-BiCGSTAB 3.2×** [corpus: Mapping Sparse Triangular Solves to GPUs, arXiv 2508.04917].
- **Pitfall**: subdomain partitioning slightly increases the iteration count for convergence (the paper above states "modest increase in iteration count"). Writing it yourself requires Triton/CUDA (P13).
- **Helps**: #1 (when you want to accelerate preconditioner application on the GPU). But **first check whether an off-the-shelf library is enough** (the P13 decision).

#### P4. Pipeline parallelism
- **When**: the pipeline is long and a single stage does not fill the GPU, or you want to split stages across devices (multi-GPU).
- **Helps**: we are on a single GPU (one RTX 5090), so **basically not needed**. At most, CPU↔GPU overlap when running cross-generation evaluation overnight in #3.

### Memory hierarchy

#### P5. Coalesced access (adjacent threads read adjacent addresses)
- **When**: always. Match the access direction to the storage order (row-major/column-major).
- **Pitfall**: `_score_at` in #2 uses fancy indexing along `pts`, giving **scattered access**. To GPU-ify it, **unroll patches into contiguous memory with im2col** and then drop it to a GEMM (P10) to make access coalesced [knowledge].
- **Helps**: #2.

#### P6. Shared-memory tiling
- **When**: the same data is reused by multiple threads (matrix multiply, convolution, stencil).
- **Helps**: #1 (P3 subdomains), #2 (place the template in shared memory and reuse it across all positions). **But torch/cupy's off-the-shelf kernels already do this**, so measure the off-the-shelf version before writing your own.

#### P7. Reduce host↔device transfers (return only the result) ★ a frequent pitfall
- **When**: always. **Calling `.cpu().numpy()` / `float(...)` / `.item()` inside a loop inserts a sync + transfer every time**, stalling the GPU.
- **Concretely (dangerous spots in the real code)**:
  - #1 `physarum_search.py:147` runs `d = float(torch.max(torch.abs(newD - D)))` **every iteration**. This is a device→host sync every iteration. Once on the GPU, **batch the convergence check every K iterations**, or accumulate `d` on the device and move it to the host all at once at the end [knowledge].
  - #1 `history.append(d)` has the same issue. On the GPU, accumulate the history into a tensor and return it in one shot at the end.
- **Helps**: #1 (with max_iters=5000, syncing every iteration is fatal).

#### P8. Occupancy (don't leave SMs idle)
- **When**: if the batch/grid is small, SMs sit idle. The RTX 5090 has a large SM count (guess: around 170), so **a single small problem won't fill it**. Use P2 to thicken the batch and fill it.
- **Helps**: #1 and #2 (this is the very reason to make the batch axis thick).

### Batching best practices

#### P9. Fold loops into a batch axis
- **When**: if a Python `for` iterates independently, make that iteration a tensor axis.
- **Concretely**:
  - #2 `_scan_flat` `for r0 / for c0` → **compute all positions at once as a score map** (= correlation/convolution, P10). Move the scale/angle `for` onto **batch axes** too: build a stack `(S*A, h, w)` of the template rotated/rescaled per angle and scale, and correlate against the image in one batch [knowledge].
  - #1's "many mazes" loop → make it a batch dimension `(B, n, n)` and do a batched solve (P2).
- **Pitfall**: folding blows up intermediate tensors (P16 dense explosion). Holding scale×angle×position all at once eats VRAM. Do it in stages (only the coarse level over the full batch, refinement only for candidates). **The existing pyramid-search structure is exactly this staging**, so exploit it.
- **Helps**: #1 and #2.

#### P10. GPU-ify correlation/convolution (FFT vs direct vs im2col)
- **When**: the gradient-direction inner product in #2 is **essentially cross-correlation**. The standard GPU approaches are three [knowledge]:
  - **Direct (conv2d)**: if the template is small (~tens of px), `torch.nn.functional.conv2d` is fastest. The two gradient components (gy, gx) become two input channels and the template's (grad_y, grad_x) become the weights, so the **inner product = the sum of a 2-channel conv**.
  - **FFT correlation**: advantageous only for large templates (hundreds of px). `O(N log N)`. For small templates the FFT overhead loses.
  - **im2col + GEMM**: unroll patches into rows for a single matrix multiply. Easy to put on Tensor Cores (P14). Multi-scale and multi-angle can be folded into one GEMM axis.
- **Pitfall**: the shape-match score includes nonlinear processing — "inner product of unit-normalized gradients + min_contrast threshold + zero for out-of-image points" (`_score_at`). Use a two-stage structure: produce the inner product with conv, and **then** apply normalization, thresholding, and counting elementwise.
- **Helps**: #2 (the main way to rewrite it).

#### P11. Variable length via padding + mask
- **When**: sizes differ within the batch (mazes have different node counts, individuals have different structures). Pad to the maximum size and mask invalid parts to 0.
- **Concretely**: #3 `eco_world.py` **already uses this best practice**. `w_rec * mask` (`eco_world.py:202`) puts the structure (connectivity) onto a fixed shape `(n,H,H)` and cuts it with a 0/1 mask. It represents each individual's differing structure with a **fixed shape + mask**, so evolving the width still runs on the same jit kernel (consistent with the philosophy in memory `project_afterman_structure_evolution`).
- **Pitfall**: large padding wastes computation. For a group of mazes with wildly varying node counts, **bin by size** and split the batch (guess: effective but unmeasured).
- **Helps**: #3 (already practiced), #1 (if maze sizes vary).

#### P12. AoS → SoA (array of structs → struct of arrays)
- **When**: the GPU is coalesced when "the same field is contiguous". Use `x[], y[], e[]` rather than `[(x,y,e), ...]`.
- **Concretely**: #3 is **already SoA** (`st["pos"], st["energy"], st["alive"]` are separate arrays). The `Graph` in #1 also leans SoA with `edges/length/coords` as separate arrays.
- **Helps**: a design principle. Always, when writing a new GPU kernel.

### Choosing numerical libraries

#### P13. Climb in the order "off-the-shelf API → cupy/torch batched → write Triton/CUDA"
- **When**: writing a kernel yourself is **the last resort**. Measure with a high-level API first.
- **Decision table** [knowledge + corpus]:
  1. **Dense batched linear systems** → `torch.linalg.solve/cholesky` (batch-capable), or cuSOLVER batched.
  2. **Sparse linear systems** → **torch-sla** (auto-dispatches among cuDSS direct / CuPy / PyTorch-native iterative by device and problem size; supports batched solve) [corpus: arXiv 2601.13994]. Or `cupyx.scipy.sparse.linalg` (cg, spsolve).
  3. **Fused elementwise operations (normalization, thresholding, reduction)** are the bottleneck → fuse with **Triton** or `torch.compile` (P15).
  4. A specialized access pattern that still isn't enough (e.g. the P3 subdomain triangular solve) → **write CUDA/Triton yourself**. Only when there's room for a 10×-class win [corpus: arXiv 2508.04917].
- **Pitfall**: writing Triton right away and only later realizing the batched form of `torch.linalg.solve` would have sufficed. **Always measure a baseline first** (memory `feedback_beat_the_null_before_claiming`).

#### P14. Get onto Tensor Cores (turn it into GEMM)
- **When**: inner products, correlations, and linear maps use Tensor Cores when dropped to GEMM. #3's `einsum("nij,nj->ni")` is a batched matvec = part of the GEMM family. #2's im2col+GEMM (P10).
- **Helps**: #2 and #3. #1's dense solve also uses GEMM internally.

#### P15. Kernel fusion (torch.compile / Triton / CUDA Graphs)
- **When**: many small elementwise kernels chained together and **kernel launches are the bottleneck**. Fuse them to reduce the number of launches. If the iteration structure is fixed, **CUDA Graph** folds the launch overhead [corpus: Hybrid JIT-CUDA Graph Optimization, mlops doc_0717 / Foundry template-based CUDA graph, doc_0521].
- **Concretely**:
  - #3 **already does this** with JAX `jit` + `lax.scan` (`eco_world.py:291`). The whole scan becomes one fused execution, folding away per-step kernel launches. **The jit boundary is the entire rollout** (do not jit per step) — this is correct and already written that way.
  - To do #1 in torch, wrap the iteration loop in `torch.compile`, or put matrix assembly (`index_put_`/`index_add_`) + solve + update into a single compiled region.
- **Pitfall**: `torch.compile` recompiles frequently under dynamic shapes. Fix the shapes (P11). JAX also re-jits if you put a variable value in `static_argnums` (#3 keeps `T` static, which is OK — but be aware that experiments that vary T will re-jit).

#### P16 (pitfall). Memory explosion from densification
- #1 `physarum_search.py:133` builds `A = torch.zeros(n, n, ...)` **every iteration**. For a maze with n=5000 in fp64, 5000²×8B = **200 MB allocated every iteration**. With a batch of B, ×B means instant OOM. **Holding it sparse (CSR/COO) is mandatory**. Move to torch-sla / cupy sparse (P13-2).
- Do not materialize all of #2's scale×angle×position at once (the staging in P9).

### Precision

#### P17. Choosing precision (where fp64 is required vs. where fp32/bf16/TF32 suffices)
- **fp64 required**: **#1's Laplacian solve**. As the ratio of conductivities D widens, a weighted graph Laplacian's condition number worsens, and in fp32 the iterative solver fails to converge / accumulates error. The code is fixed to `float64`.
  - However, **fp64 on the RTX 5090 is extremely slow relative to fp32** (GeForce cards run fp64 at a ~1/64 rate) (guess: Blackwell GeForce likely follows the same trend; needs measurement). → **Mixed-precision iterative refinement** is the standard: the inner iterative solver runs in fp32 (fp16 in some cases), and the residual is corrected in fp64 on the outside. **FP32/FP64 mixing is established, and FP16 is practical too with rescaling, within 20% extra iterations** [corpus: Mixed precision solvers, arXiv 2602.14450].
- **fp32/bf16/TF32 suffices**: #2 (gradient-direction inner products), #3 (evolutionary fitness, RNN forward).
- **Blackwell TF32/FP8**:
  - **TF32**: accelerates fp32 matrix multiply on Tensor Cores (10-bit mantissa). Enable with `torch.set_float32_matmul_precision("high")` / `torch.backends.cuda.matmul.allow_tf32=True` [knowledge]. Helps #2 and #3's GEMMs. **Does not help #1's fp64 solve** (TF32 is on the fp32 path).
  - **FP8**: Blackwell supports FP8 (E4M3/E5M2) on Tensor Cores (guess: sm_120 likely has a 2nd-gen Transformer Engine equivalent; needs confirmation). **None of our three workloads are matrix-multiply-dominated enough to need FP8**, so for now the call is **not to use it**. FP8 pays off for the giant GEMMs of LLMs.
- **Pitfall**: for #1, before casually switching to fp32 and celebrating "it got faster", **check convergence and the correctness of the final path** against an fp64 reference (memory `feedback_benchmark_honest_disclosure`).

### Iterative-solver best practices (directly relevant to #1)

#### P18. Matrix-free (give the action without building the matrix)
- **When**: assembling `A` explicitly is expensive / memory-hungry. CG/BiCGSTAB only need the **action** `A@x`. For a Laplacian, `A@x = degree*x - (contributions from neighbors)` can be computed sparsely, without building the dense `A`.
- **Concretely**: the corpus has many examples of **matrix-free preconditioner / matrix-free multigrid** [corpus: Matrix-free Neural Preconditioner for Dirac Operator (numerical doc_0166) / Matrix-Free Galerkin Multigrid (doc_0720)].
- **Helps**: #1 (the main way to eradicate the P16 dense explosion).

#### P19. Preconditioning
- **When**: to speed the convergence of an iterative solver. For a Laplacian, **AMG (algebraic multigrid)**, ILU, and Jacobi/diagonal are the staples.
- **How to choose** [knowledge]: AMG is very effective for a graph Laplacian (nearly constant iteration count). But AMG setup on the GPU is heavy. **Measure diagonal/Jacobi preconditioner + CG first**, and go to AMG if that isn't enough. Applying ILU-family preconditioners (triangular solves) tends to become the bottleneck on the GPU → the P3 subdomain approach [corpus: arXiv 2508.04917].
- **Helps**: #1.

#### P20. Warm start (use the previous step's solution as the initial guess) ★ directly relevant to time iteration
- **When**: #1 is a **time iteration where D changes slightly** = `L(D)` changes a little each iteration. Using the previous iteration's solution `p` as the CG initial guess for the next iteration drastically cuts the iteration count [knowledge].
- **Reusing the preconditioner**: while D changes little, **reuse the same preconditioner** and rebuild it every K iterations or when the residual worsens. "Warm-starting the preconditioner" is a real design axis [corpus: Taming Preconditioner Drift, arXiv 2602.19271 explicitly does warm-starting via a global preconditioner]. Note: that paper is in a federated-learning context, but the very concept of "monitor preconditioner drift and rebuild / warm-start it" carries over to our time iteration (the transfer is a guess; the concept is real).
- **Pitfall**: warm start does not help the current `torch.linalg.solve` (a direct method). **It only helps once you switch to an iterative method**. In other words, it comes as a set with the migration from "dense direct → sparse iterative".
- **Helps**: #1 (one of the highest cost-benefit changes).

---

## 2. Pitfall checklist (summary)

| Pitfall | Symptom | Fix | Applies to |
|---|---|---|---|
| Submitting small problems to the GPU one at a time | Slower than CPU | Batch them with batched-kernel (P2) | #1, #2 |
| `.item()`/`float()`/`.cpu()` inside the loop | GPU waits every iteration | Batch the convergence check every K iterations, accumulate history on the device (P7) | #1 |
| Allocating dense `A` every iteration | OOM / bandwidth-bound | Sparse + matrix-free (P16/P18) | #1 |
| Materializing all scale×angle×position at once | VRAM explosion | Stage it with a pyramid (P9) | #2 |
| Careless switch to fp32 | Fails to converge / the path changes | Mixed-precision iterative refinement, check against an fp64 reference (P17) | #1 |
| Recompilation under dynamic shapes | jit/compile runs every time | Fixed shapes + padding/mask (P11/P15) | #2, #3 |
| Branches that cause warp divergence | Effective parallelism drops | Same branch across the whole batch (P1) | all |
| Writing Triton, then realizing off-the-shelf sufficed | Wasted effort | Measure a baseline → climb in stages (P13) | all |

---

## 3. Numerical-library quick reference

| What you want | First choice | Alternatives | Source |
|---|---|---|---|
| Dense batched linear systems `(B,n,n)` | `torch.linalg.solve` (batch-capable) | cuSOLVER batched, `cupy.linalg` | [knowledge] |
| **Sparse** batched linear systems (shared/per-instance sparsity) | **torch-sla** (auto-dispatch across cuDSS/CuPy/torch-iterative) | `cupyx.scipy.sparse.linalg.cg/spsolve` | [corpus: arXiv 2601.13994] |
| Sparse CG/BiCGSTAB + preconditioner | `cupyx.scipy.sparse.linalg` | torch-sla iterative backend | [knowledge/corpus] |
| Fast triangular solve (preconditioner application) | Measure off-the-shelf → subdomain approach if insufficient | Hand-written Triton/CUDA | [corpus: arXiv 2508.04917] |
| Correlation/convolution (shape match) | `F.conv2d` (small template) | FFT (large template), im2col+GEMM | [knowledge] |
| Parallel population forward + scan | **JAX `vmap`/`lax.scan`/`jit`** (#3 already practices this) | `torch.vmap` + `torch.compile` | [knowledge] |
| Random numbers (population, stochastic events) | `jax.random.split` (#3 already practices this, `eco_world.py:244`) | `torch.Generator` per-stream | [knowledge] |
| Elementwise fusion is the bottleneck | `torch.compile` / Triton | CUDA Graph (fixed iterations) | [corpus: mlops doc_0717/0521] |
| Mixed-precision iterative refinement | fp32 inner + fp64 correction (fp16 also possible with rescaling) | — | [corpus: arXiv 2602.14450] |
| Enable TF32 (accelerate fp32 GEMM) | `torch.set_float32_matmul_precision("high")` | `allow_tf32=True` | [knowledge] |

**JAX essentials (for #3)** [knowledge]:
- `vmap` = auto-vectorize the population onto a batch axis. #3 makes per-individual weights an explicit batch (the `n` axis), which is effectively the same thing.
- `lax.scan` = turn the time loop into one fused kernel (overwhelmingly faster than a Python for). #3 already practices this in `rollout`.
- The `jit` boundary = jit the **entire rollout** once (do not jit per step). #3 is correct with `@partial(jax.jit, static_argnums=1)` keeping T static.
- `jax.random.split` = split a key per iteration (#3 practices `split` inside `step`). It already avoids the pitfall of **reusing the same key**, which would produce correlated random numbers.
- Variable structure = **fixed shape + mask** (#3 uses `w_rec*mask`). It runs on the same jit-compiled kernel even when evolution changes the width.

---

## 4. Notes on introducing a CUDA build (investigation only; do not actually install)

Current state: `torch 2.11.0+cpu` / `jax 0.7.1 CpuDevice`. sm_120 (Blackwell) requires the **CUDA 12.8+** generation. The following are **hunches**; confirm sm_120 support in the release notes before installing.

**PyTorch (guess-based, needs confirmation)**:
```powershell
# Assumes uninstalling the existing CPU build, then installing the CUDA 12.8 wheel (version needs confirmation)
py -3.11 -m pip uninstall torch
py -3.11 -m pip install torch --index-url https://download.pytorch.org/whl/cu128
# If a cu129-family build exists, it may have newer Blackwell support (guess)
```
- **Note (guess)**: for the torch 2.11 generation, the cu128/cu129 wheels likely include Blackwell sm_120. But whether the wheel's bundled CUDA carries SASS/PTX for sm_120 **must be confirmed in the release notes**. If it doesn't, at first run it is either JIT-compiled from PTX (slow but works) or fails with `no kernel image is available for execution on the device`. In the latter case, wait for an sm_120-capable wheel / use a nightly.
- Check command: `py -3.11 -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"` → if it prints the equivalent of `(12,0)`, sm_120 is recognized.

**JAX (guess-based, needs confirmation)**:
```powershell
py -3.11 -m pip install -U "jax[cuda12]"
```
- `jax[cuda12]` pulls CUDA 12-family + cuDNN via pip. **Blackwell support depends on the CUDA version bundled in jaxlib**. If sm_120 doesn't work on 0.7.1, upgrade to a newer jaxlib (cuda12 plugin).
- **Windows note (known)**: JAX GPU support on native Windows is thin, so **going through WSL2 is standard** (in the memory set, MuJoCo etc. also go the WSL route). To use the RTX 5090 with JAX, **WSL2 + a Linux wheel** is the reliable path (a guess, but a strong one).
- Check: `py -3.11 -c "import jax; print(jax.devices())"` → OK if `CudaDevice` appears.

**Common pitfalls (knowledge)**:
- Whether driver 610.74 is sufficient for the CUDA 12.8+ runtime (usually the wheel bundles its own CUDA, so only the driver requirement must be met; needs confirmation).
- Do not mix CPU and CUDA builds (if a torch with the `+cpu` suffix lingers, `cuda.is_available()` is False).

---

## 5. "What to GPU-ify first" — priority and rationale

### Order of attack (cost-effectiveness)

**First move: rewrite the Physarum solver (#1) from "dense direct → sparse + matrix-free iterative + warm start". But sparsify on CPU/numpy first and lock in correctness before going to GPU.**
- **Rationale**:
  - It is currently the worst (O(n³) dense every iteration, `A` reallocated every iteration, host sync every iteration). **Three structural defects stack up** (P16/P7/P18), so the headroom is the largest.
  - The batch dimension (many mazes and parameters) is clear → batched-kernel (P2) applies directly. A textbook case for GPU acceleration.
  - The property that **`L(D)` changes slightly across the time iteration** fits warm start (P20) perfectly. CG with the previous step's solution as the initial guess should slash the iteration count.
  - The libraries are in place: **torch-sla explicitly supports batched sparse solve** [corpus: arXiv 2601.13994]. You can climb without a custom kernel.
  - But, per memory `feedback_cpu_short_poc_before_gpu`, **first put in sparsification + iterative method + warm start on CPU and confirm the shortest-path convergence is preserved**, then set `device="cuda"`. Also decide whether fp64→mixed precision is warranted by looking at the residual at the CPU stage.

**Second move: turn shape matching (#2) from "Python double loop → conv2d/im2col batch".**
- **Rationale**:
  - The double for in `_scan_flat`/`_score_at` is essentially cross-correlation (P10). Dropping it to `F.conv2d` gives a big speedup in one move, and the pyramid structure (coarse → fine) becomes **batch staging (P9) as-is**, avoiding VRAM explosion.
  - Scale/angle fold onto the batch axis (P9). It rides GEMM/Tensor Cores (P14) and is even faster with TF32.
  - fp32 suffices, so there is no precision worry (unlike #1, the fp64-rate problem is irrelevant).
  - Reason for ranking it below #1: it "does work" today with numpy + pyramid. #1 has the greater structural loss.

**Third move: Afterman (#3) just needs the wheel installed. Almost no code change.**
- **Rationale**:
  - It is already GPU-ready (SoA + batched einsum + `lax.scan` + `jit` + `random.split` + mask for variable structure). Once `jax[cuda12]` (or WSL2) is installed, `jax.devices()` becomes cuda and it **rides as-is**.
  - The tasks are (a) install the wheel (§4), (b) raise the population size n until the GPU fills, to secure occupancy (P8), (c) consider bf16/TF32 (fitness only needs to be approximate).
  - The part where **structural evolution changes the width** keeps a fixed shape via the mask (P11), avoiding re-jit = already the correct design.

### One-line summary
> **The first move is "rebuild the Physarum solver into sparse + matrix-free iterative + warm start (nail down correctness on CPU first)."** It crushes the triple structural defect of the current dense O(n³) / per-iteration reallocation / per-iteration sync, and the tailwinds — the affinity of time iteration with warm start, and the existence of a batched sparse-solve library (torch-sla) — all line up, so the return on the GPU investment is fastest.

---

## Appendix: RAD corpus sources whose existence was confirmed for this catalog

All confirmed to exist by grep under `D:/docs/numerical_methods_corpus_v2/` and `D:/docs/mlops_corpus_v2/` (file paths are the clusters in the body's footnotes).

- **torch-sla: Differentiable Sparse Linear Algebra ...** (arXiv 2601.13994) — batched sparse solve, cuDSS/CuPy/torch-native auto-dispatch. → basis for P2/P13/first move.
- **Mapping Sparse Triangular Solves to GPUs via Fine-grained Domain Decomposition** (arXiv 2508.04917) — fit subdomains into shared memory, eliminate inter-block sync, triangular solve 10.7×. → P3/P6/P19.
- **Taming Preconditioner Drift** (arXiv 2602.19271) — preconditioner warm-start and drift correction (the context is federated learning; carrying the concept over to time iteration is a guess). → P20.
- **Mixed precision solvers with half-precision (FP16) for Lattice QCD** (arXiv 2602.14450) — FP64/FP32/FP16 mixing via iterative refinement; FP16 within 20% extra iterations with rescaling. → P17.
- **Matrix-free Neural Preconditioner for the Dirac Operator** (numerical doc_0166) / **Matrix-Free Galerkin Multigrid Solver** (doc_0720) — examples of matrix-free. → P18.
- **Hybrid JIT-CUDA Graph Optimization** (mlops doc_0717) / **Foundry: Template-Based CUDA Graph** (doc_0521) — reduce launch overhead with CUDA Graph. → P15.

The specifics of TF32/FP8/Blackwell sm_120, wheel versions, and the fp64 rate are **from the out-of-corpus knowledge base + guesses**, and must be confirmed at actual install time against release notes / measurement.

---

## Appendix 2: Measured results of GPU-izing the Physarum solver (2026-08-26, run on the RTX 5090)

The results of implementing the "first move" listed in the catalog above and **actually running it on the GPU** (loco venv's torch 2.11.0+cu128, CUDA 12.8, RTX 5090). `physarum_search.py` / `tests/test_physarum_search.py` under `packages` (the imgevolve root).

### What was done (patterns applied)
- **Matrix-free batched CG** (P18/P13) — MatVec via edge scatter_add without assembling the Laplacian.
- **Batch axis** (P2) — stack many (source, sink) pairs on the same graph into (B, ...) and solve simultaneously.
- **Warm start** (P20) — use the previous time step's pressure solution as the next CG initial guess.
- **Thinning host syncs** (P6) — thin the device→host sync of the CG convergence check `rs.max()` via `cg_check_every` (on the GPU, syncing every iteration is a serialization factor).
- **FP32** (P17) — consumer-GPU FP64 is 1/64 of FP32. Path finding is fine in FP32.
- **CUDA graph capture** (P15) — capture one time step (fixed-iteration CG + D update) and replay it.

### Measurements (honest)
| Scale | CPU sequential sparse (baseline) | GPU best (FP32+CUDA graph) | Speedup |
|---|---|---|---|
| k=64  (n=4,096, B=16)  | 27.9 s | 1.12 s | **24.9x** |
| k=128 (n=16,384, B=16) | 89.1 s | 1.09 s | **82.2x** |
| k=200 (n=40,000, B=16) | 230.7 s | 1.42 s | **162.3x** |

- **At this scale the GPU is bound by kernel-launch latency, not by compute**. Wall time stays roughly constant (~4 s, pre-CUDA-graph) even when the graph grows from 4k→90k nodes (22×). That is, larger graphs or larger batches fill the idle time and win "without increasing wall time". Conversely, **with a small graph AND a small batch, launch overhead loses to the CPU** (0.3x at k=15, B=32). Do not lie about this.
- **Order of what worked**: CUDA graph (~4x) ≫ sync thinning (1.2x) ≈ FP32 (1.2x). At this scale neither FP32 nor sync thinning can shift the bottleneck; only the CUDA graph, which removes launches, lowered the floor.
- **Correctness**: for a unique shortest path, it thickens the shortest to D≈1.0 and prunes detours to D≈5e-8 (matching the CPU sparse version). For non-degenerate large batches, CUDA graph and eager are bit-identical (max|Δ|=0). For **degeneracy** (symmetric small grids with many equal-length shortest paths), FP32 tie-breaking splits by 1-3%, but this is degeneracy, not error.
- Tests: on CPU 11 passed / 3 skipped (GPU tests skipped due to no cuda present), 14 passed in the GPU venv.

### Remaining moves (not yet started)
- Further lowering the ~4 s floor before CUDA graph: either make CG preconditioned to reduce the iteration count (P20), or fold multiple time steps into one capture (fewer replays).
- FP16 + iterative refinement (P17) is likely overkill for path finding. Wait until it's needed.
