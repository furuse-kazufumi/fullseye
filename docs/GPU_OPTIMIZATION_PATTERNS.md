# GPU 最適化デザインパターン・カタログ(RTX 5090 / Blackwell sm_120 向け)

**対象 GPU(確認済み)**: NVIDIA RTX 5090、Blackwell、compute capability **sm_120**、VRAM 32GB、driver 610.74。
**現状(確認済み)**: `torch 2.11.0+cpu` と `jax 0.7.1`(CpuDevice)しか入っておらず、**いま GPU では走らない**。sm_120 は CUDA 12.8+ 世代のビルドが要る。
**このカタログの性格**: Web 検索は使わず、RAD コーパス(`D:/docs/*_corpus_v2/`、実在確認済み)+ 知識ベースで書いた。**推測は「(推測)」と明示**する。実コード(`physarum_search.py` / `shapematch.py` / `afterman/eco_world.py`)を読んで各ワークロードに紐づけた。

出典表記:
- **[コーパス]** = RAD コーパスで実在確認した論文(arXiv 番号つきで明記)。
- **[知識]** = 一般的な GPU プログラミング知識(コーパス外)。
- **(推測)** = 未検証の当たり。実測・一次資料で確認するまで信じない。

---

## 0. 我々の3ワークロードの構造(コード実測)

| # | ワークロード | 計算の核 | いまのボトルネック | バッチ次元 | 精度要件 |
|---|---|---|---|---|---|
| 1 | 粘菌ソルバ `physarum_search.py` | ラプラシアン `L(D)p=b` の線形ソルブ × 時間反復(伝導率 D を毎反復更新) | **dense n×n を毎反復** `torch.linalg.solve`(O(n³))。しかも毎反復 `A` を `torch.zeros(n,n)` で作り直す | 多数の迷路 × 多数のパラメータ(μ, dt, D_init) | **fp64**(コード実測: `torch.float64` 固定。ラプラシアンは条件数が悪くなりやすい) |
| 2 | 形状マッチング `shapematch.py` | テンプレートのエッジ勾配ベクトルと画像勾配の内積を、多数の位置 × スケール × 角度で評価 | Python 二重ループ `_scan_flat` / `_score_at`(fancy-index の内積)。scale/角度も Python ループ | 位置 × スケール × 角度 × 複数インスタンス | fp32 で十分(勾配方向の内積。相関のダイナミックレンジは狭い) |
| 3 | Afterman 進化 `afterman/eco_world.py` | 個体群の並列前進評価(RNN 政策) + 構造進化 | **すでに JAX で綺麗にバッチ化済**(個体ごと重み `w_in/w_rec/w_out` を `einsum("nij,nj->ni")`、`lax.scan` で T ステップ、`jit(static_argnums=1)`) | 個体数 n(集団) | fp32/bf16 で十分(進化 fitness は近似で足りる) |

**重要な非対称性**: 3 番はすでに GPU-ready の書き方(SoA + batched einsum + scan)。1・2 は「Python ループ + 逐次 dense ソルブ」で GPU 化の伸びしろが最大。**着手優先度は 1・2 が上、3 は wheel を入れれば `jax.devices()` が cuda になるだけでほぼ動く**(詳細は §5)。

---

## 1. デザインパターン・カタログ

各パターン = **名前 / いつ使う / 落とし穴 / 我々のどれに効くか**。

### 並列の型

#### P1. Data-parallel(SIMT 素直な並列)
- **いつ**: 独立した要素へ同じ演算(ピクセルごと、個体ごと、辺ごと)。GPU の最も素直な形。
- **落とし穴**: 分岐発散(warp 内でスレッドが別の道を通ると直列化)。`if cfg.contested:` のような分岐は**バッチ全体で同じ枝**にして warp 発散を避ける [知識]。
- **効く先**: 全部。特に 3(個体ごと独立の RNN)、2(位置ごと独立のスコア)。

#### P2. Batched-kernel(多数の小問題を1カーネルにまとめる) ★最重要
- **いつ**: 「小さな線形系/小さな相関を大量に」解くとき。1 個ずつ GPU に投げると**カーネル起動レイテンシ(数 µs/回)と H2D 転送**が支配して CPU より遅くなる。まとめて1回のカーネル/1回の API 呼び出しにする。
- **具体**: `torch.linalg.solve` は**バッチ版**を持つ(先頭次元がバッチ)。`(B, n, n)` を渡せば B 個の系を1呼び出しで解く。cuSOLVER の batched API、cuBLAS の `*gemmStridedBatched` が裏で効く [知識]。疎なら **torch-sla が「共有 or 個別の sparsity pattern に対する batched solve」を明示サポート** [コーパス: torch-sla, arXiv 2601.13994]。
- **落とし穴**: バッチ内でサイズがバラバラだと padding が要る(P8)。バッチが小さすぎると occupancy が上がらない。
- **効く先**: **1(多数の迷路を同時に解く=これが本命)**、2(多数の scale/角度をバッチ軸へ)。

#### P3. Warp 協調(shared memory + warp shuffle での縮約)
- **いつ**: 1問題が「1スレッドには大きいが1ブロックには収まる」中規模。ブロック内で shared memory に載せてブロック間同期を消す。
- **具体**: **疎三角ソルブをサブドメインに割り、各サブドメインを1スレッドブロックへ、ベクトルが shared memory に収まるサイズにすることで inter-block 同期を消し不規則 global アクセスを減らす → 三角ソルブ 10.7×、ILU0-BiCGSTAB 3.2×** [コーパス: Mapping Sparse Triangular Solves to GPUs, arXiv 2508.04917]。
- **落とし穴**: サブドメイン化は収束反復数を少し増やす(上の論文も「modest increase in iteration count」と明記)。自分で書くなら Triton/CUDA が要る(P13)。
- **効く先**: 1(プリコンディショナ適用を GPU で速くしたいとき)。ただし**まず既製ライブラリで足りるか確認**(P13 の判断)。

#### P4. パイプライン並列
- **いつ**: 段が長く1段が GPU を埋めない、または段ごとにデバイスを分けたいとき(マルチ GPU)。
- **効く先**: 我々は単一 GPU(RTX 5090 1枚)なので**基本不要**。3 で世代をまたぐ評価を overnight で回すときの CPU↔GPU オーバーラップくらい。

### メモリ階層

#### P5. Coalesced access(隣接スレッドが隣接アドレスを読む)
- **いつ**: 常時。行優先/列優先とアクセス方向を一致させる。
- **落とし穴**: 2 の `_score_at` は `pts` に沿った fancy index で**散らばったアクセス**。GPU 化するなら **im2col でパッチを連続メモリに展開**してから GEMM に落とす(P10)と coalesced になる [知識]。
- **効く先**: 2。

#### P6. Shared memory tiling
- **いつ**: 同じデータを複数スレッドが再利用(行列積、畳み込み、ステンシル)。
- **効く先**: 1(P3 のサブドメイン)、2(テンプレートを shared memory に置いて全位置で再利用)。**ただし torch/cupy の既製カーネルが既にやっている**ので、自分で書く前に既製で測る。

#### P7. Host↔Device 転送を減らす(結果だけ返す)★落とし穴の常連
- **いつ**: 常時。**反復の中で `.cpu().numpy()` / `float(...)` / `.item()` を呼ぶと毎回同期 + 転送**が入り、GPU が待たされる。
- **具体(実コードの危険箇所)**:
  - 1 `physarum_search.py:147` `d = float(torch.max(torch.abs(newD - D)))` を**毎反復**。これは毎反復 device→host 同期。GPU 化したら**収束判定を K 反復ごとにまとめる**か、`d` を device 上に貯めて最後にまとめて host へ [知識]。
  - 1 `history.append(d)` も同様。GPU では history を tensor に貯めて最後に一括で返す。
- **効く先**: 1(現状 max_iters=5000 反復 × 毎回同期は致命的)。

#### P8. Occupancy(SM を空けない)
- **いつ**: バッチ/グリッドが小さいと SM が遊ぶ。RTX 5090 は SM 数が多い(推測: 170 前後)ので、**小問題1個では埋まらない**。P2 でバッチを厚くして埋める。
- **効く先**: 1・2(バッチ軸を厚く取る動機そのもの)。

### バッチ化の定石

#### P9. ループを batch 軸に畳む
- **いつ**: Python の `for` が独立反復なら、その反復を tensor の1軸にする。
- **具体**:
  - 2 `_scan_flat` の `for r0 / for c0` → **全位置を一気にスコア地図として計算**(=相関/畳み込み、P10)。scale/角度の `for` も**バッチ軸**へ:テンプレートを角度・scale ごとに回転/拡縮したスタック `(S*A, h, w)` を作り、画像との相関を1バッチで [知識]。
  - 1 の「多数の迷路」ループ → バッチ次元 `(B, n, n)` にして batched solve(P2)。
- **落とし穴**: 畳み込むと中間テンソルが巨大化(P16 dense 爆発)。scale×角度×位置を全部同時に持つと VRAM を食う。段階的に(粗階層だけ全バッチ、精密化は候補のみ)。**既存のピラミッドサーチ構造がこの段階化そのもの**なので活かす。
- **効く先**: 1・2。

#### P10. 相関/畳み込みの GPU 化(FFT vs 直接 vs im2col)
- **いつ**: 2 の勾配方向内積は**本質的に相互相関**。GPU 化の定石は3択 [知識]:
  - **直接(conv2d)**: テンプレートが小さい(~数十 px)なら `torch.nn.functional.conv2d` が最速。勾配2成分(gy,gx)を入力2チャンネル、テンプレの (grad_y, grad_x) を重みにして**内積=2ch の conv の和**で表せる。
  - **FFT 相関**: テンプレートが大きい(数百 px)ときのみ有利。`O(N log N)`。小テンプレートでは FFT のオーバーヘッド負け。
  - **im2col + GEMM**: パッチを行に展開して1回の行列積。Tensor Core に乗せやすい(P14)。多スケール・多角度を GEMM の一軸に畳める。
- **落とし穴**: 形状マッチのスコアは「単位ベクトル化した勾配の内積 + min_contrast 閾値 + 画像外0点」という非線形処理を含む(`_score_at`)。conv で内積を出した**後に**、正規化・閾値・カウントを elementwise で当てる2段構成にする。
- **効く先**: 2(本命の書き換え方)。

#### P11. 可変長を padding + mask
- **いつ**: バッチ内でサイズが違う(迷路のノード数が違う、個体の構造が違う)。最大サイズに padding し、無効部を mask で 0 に。
- **具体**: 3 `eco_world.py` が**すでにこの定石**。`w_rec * mask`(`eco_world.py:202`)で構造(結線)を固定形状 `(n,H,H)` に載せ、mask を 0/1 で切る。個体ごとに違う構造を**固定形状 + mask** で表す=進化で幅を変えても同じ jit カーネルで回る(memory `project_afterman_structure_evolution` の思想と一致)。
- **落とし穴**: padding が大きいと無駄計算。ノード数のばらつきが激しい迷路群は**サイズでビニングして**バッチを分ける(推測: 有効だが未計測)。
- **効く先**: 3(既実践)、1(迷路サイズがばらつくなら)。

#### P12. AoS → SoA(構造体配列 → 配列の構造体)
- **いつ**: GPU は「同じフィールドが連続」だと coalesced。`[(x,y,e), ...]` でなく `x[], y[], e[]`。
- **具体**: 3 は**すでに SoA**(`st["pos"], st["energy"], st["alive"]` が別配列)。1 の `Graph` も `edges/length/coords` が別配列で SoA 寄り。
- **効く先**: 設計原則。新規に GPU カーネルを書くとき常に。

### 数値ライブラリの使い分け

#### P13. 「既製 API → cupy/torch batched → Triton/CUDA を書く」の順で登る
- **いつ**: 自分でカーネルを書くのは**最後の手段**。まず高レベル API で測る。
- **判断表** [知識 + コーパス]:
  1. **dense バッチ線形系** → `torch.linalg.solve/cholesky`(バッチ対応)、または cuSOLVER batched。
  2. **疎線形系** → **torch-sla**(cuDSS 直接法 / CuPy / PyTorch-native 反復法を device・問題サイズで自動ディスパッチ、batched solve 対応) [コーパス: arXiv 2601.13994]。または `cupyx.scipy.sparse.linalg`(cg, spsolve)。
  3. **要素ごとの融合演算(正規化・閾値・縮約)** が律速 → **Triton** か `torch.compile` で融合(P15)。
  4. それでも足りない専用アクセスパターン(P3 のサブドメイン三角ソルブ等) → **CUDA/Triton を自分で**。10×級の余地があるときだけ [コーパス: arXiv 2508.04917]。
- **落とし穴**: いきなり Triton を書いて、後で `torch.linalg.solve` のバッチ版で足りたと気づく。**必ずベースラインを測ってから**(memory `feedback_beat_the_null_before_claiming`)。

#### P14. Tensor Core に乗せる(GEMM 化)
- **いつ**: 内積・相関・線形写像は GEMM に落とすと Tensor Core が使える。3 の `einsum("nij,nj->ni")` は batched matvec = GEMM 族。2 の im2col+GEMM(P10)。
- **効く先**: 2・3。1 の dense solve も内部は GEMM を使う。

#### P15. カーネル融合(torch.compile / Triton / CUDA Graphs)
- **いつ**: 小さな elementwise カーネルが多数連なり**カーネル起動が律速**。融合して起動回数を減らす。反復構造が固定なら **CUDA Graph** で起動オーバーヘッドを畳む [コーパス: Hybrid JIT-CUDA Graph Optimization, mlops doc_0717 / Foundry template-based CUDA graph, doc_0521]。
- **具体**:
  - 3 は JAX の `jit` + `lax.scan`(`eco_world.py:291`)が**すでにこれ**。scan 全体が1つの融合実行になり、ステップごとのカーネル起動を畳む。**jit 境界は rollout 全体**(1ステップごとに jit しない)が正解=既にそう書けている。
  - 1 を torch でやるなら反復ループを `torch.compile` で包むか、行列組み立て(`index_put_`/`index_add_`)+ solve + 更新を1つの compiled region に。
- **落とし穴**: `torch.compile` は動的形状で再コンパイル多発。形状を固定して(P11)。JAX も `static_argnums` に可変値を入れると再 jit(3 は `T` を static にしていて OK、ただし T を変える実験では再 jit されると認識)。

#### P16(落とし穴). dense 化でメモリ爆発
- 1 `physarum_search.py:133` `A = torch.zeros(n, n, ...)` を**毎反復**。n=5000 の迷路で fp64 なら 5000²×8B = **200MB を毎反復確保**。バッチ B 個なら ×B で即 OOM。**疎(CSR/COO)で持つのが必須**。torch-sla / cupy sparse へ(P13-2)。
- 2 の全 scale×角度×位置を同時に materialize しない(P9 の段階化)。

### 精度

#### P17. 精度の使い分け(fp64 が要る所と fp32/bf16/TF32 で足りる所)
- **fp64 が要る**: **1 のラプラシアンソルブ**。重み付きグラフラプラシアンは伝導率 D の比が広がると条件数が悪化し、fp32 だと反復ソルバが収束しない/誤差が溜まる。コードも `float64` 固定。
  - ただし **RTX 5090 の fp64 は fp32 比で極端に遅い**(GeForce 系は fp64 が 1/64 レート級)(推測: Blackwell GeForce も同傾向。要実測)。→ **混合精度反復改良(mixed-precision iterative refinement)**が定石:内側の反復ソルバは fp32(場合により fp16)、外側で残差を fp64 補正。**FP32/FP64 混合は確立、FP16 も rescaling を入れれば追加反復 20% 以内で実用** [コーパス: Mixed precision solvers, arXiv 2602.14450]。
- **fp32/bf16/TF32 で足りる**: 2(勾配方向の内積)、3(進化 fitness、RNN 前進)。
- **Blackwell の TF32/FP8**:
  - **TF32**: fp32 の行列積を Tensor Core で高速化(仮数 10bit)。`torch.set_float32_matmul_precision("high")` / `torch.backends.cuda.matmul.allow_tf32=True` で有効化 [知識]。2・3 の GEMM に効く。**1 の fp64 ソルブには効かない**(TF32 は fp32 経路)。
  - **FP8**: Blackwell は FP8(E4M3/E5M2)を Tensor Core でサポート(推測: sm_120 でも 2nd-gen Transformer Engine 相当。要確認)。**我々の3ワークロードはどれも FP8 が要るほど行列積が支配的でない**ので、当面は**使わない**判断でよい。FP8 が効くのは LLM の巨大 GEMM。
- **落とし穴**: 1 で安易に fp32 化して「速くなった」と喜ぶ前に、**収束と最終経路の正しさ**を fp64 基準と突き合わせる(memory `feedback_benchmark_honest_disclosure`)。

### 反復ソルバの定石(1 に直結)

#### P18. Matrix-free(行列を作らず作用だけ与える)
- **いつ**: `A` を明示的に組むのが高い/メモリを食う。CG/BiCGSTAB は `A@x` の**作用**さえあればよい。ラプラシアンなら `A@x = degree*x - (隣接からの寄与)` を疎に計算でき、dense `A` を作らない。
- **具体**: コーパスに **matrix-free preconditioner / matrix-free multigrid** の実例多数 [コーパス: Matrix-free Neural Preconditioner for Dirac Operator (numerical doc_0166) / Matrix-Free Galerkin Multigrid (doc_0720)]。
- **効く先**: 1(P16 の dense 爆発を根絶する本命)。

#### P19. プリコンディショニング
- **いつ**: 反復ソルバの収束を速める。ラプラシアンには **AMG(代数マルチグリッド)**、ILU、Jacobi/対角が定番。
- **選び方** [知識]: グラフラプラシアンは AMG が非常に効く(ほぼ反復数一定)。ただし GPU での AMG セットアップは重い。**まず対角/Jacobi プリコンディショナ + CG** で測り、足りなければ AMG。ILU 系の適用(三角ソルブ)は GPU で律速になりがち → P3 のサブドメイン化 [コーパス: arXiv 2508.04917]。
- **効く先**: 1。

#### P20. Warm start(前ステップ解を初期値に)★時間反復に直結
- **いつ**: 1 は**時間反復で D が少しずつ変わる**=`L(D)` が毎反復わずかに変化。前反復の解 `p` を次反復 CG の初期値にすると反復数が激減 [知識]。
- **プリコンディショナの使い回し**: D の変化が小さい間は**同じプリコンディショナを再利用**し、K 反復ごと or 残差が悪化したら作り直す。「preconditioner を warm-start する」パターンは実在の設計軸 [コーパス: Taming Preconditioner Drift, arXiv 2602.19271 が warm-starting via global preconditioner を明示]。※この論文は連合学習の文脈だが、「プリコンディショナのドリフトを監視して作り直す/warm-start する」概念そのものが我々の時間反復に転用できる(転用は推測、概念は実在)。
- **落とし穴**: warm start は現状の `torch.linalg.solve`(直接法)では効かない。**反復法に切り替えて初めて効く**。つまり「dense 直接 → 疎反復」への移行とセット。
- **効く先**: 1(最も費用対効果が高い変更の一つ)。

---

## 2. 落とし穴・チェックリスト(まとめ)

| 落とし穴 | 症状 | 対策 | 該当 |
|---|---|---|---|
| 小問題を1個ずつ GPU 投入 | CPU より遅い | batched-kernel(P2)でまとめる | 1・2 |
| 反復中の `.item()`/`float()`/`.cpu()` | GPU が毎反復待つ | 収束判定を K 反復まとめ、history は device に貯める(P7) | 1 |
| dense `A` を毎反復確保 | OOM / 帯域律速 | 疎 + matrix-free(P16/P18) | 1 |
| 全 scale×角度×位置を同時 materialize | VRAM 爆発 | ピラミッドで段階化(P9) | 2 |
| 安易な fp32 化 | 収束せず/経路が変わる | 混合精度反復改良、fp64 基準と照合(P17) | 1 |
| 動的形状で再コンパイル | jit/compile が毎回走る | 形状固定 + padding/mask(P11/P15) | 2・3 |
| warp 発散する分岐 | 実効並列度が落ちる | バッチ全体で同じ枝(P1) | 全部 |
| Triton を書いてから既製で足りたと気づく | 労力の無駄 | ベースライン測定 → 段階的に登る(P13) | 全部 |

---

## 3. 数値ライブラリ早見表

| やりたいこと | 第一候補 | 代替 | 出典 |
|---|---|---|---|
| dense バッチ線形系 `(B,n,n)` | `torch.linalg.solve`(バッチ対応) | cuSOLVER batched, `cupy.linalg` | [知識] |
| **疎**バッチ線形系(共有/個別 sparsity) | **torch-sla**(cuDSS/CuPy/torch-iterative 自動ディスパッチ) | `cupyx.scipy.sparse.linalg.cg/spsolve` | [コーパス: arXiv 2601.13994] |
| 疎 CG/BiCGSTAB + プリコンディショナ | `cupyx.scipy.sparse.linalg` | torch-sla iterative backend | [知識/コーパス] |
| 三角ソルブ(プリコンディショナ適用)を速く | 既製で測る → 足りねばサブドメイン化 | 自作 Triton/CUDA | [コーパス: arXiv 2508.04917] |
| 相関/畳み込み(形状マッチ) | `F.conv2d`(小テンプレ) | FFT(大テンプレ)、im2col+GEMM | [知識] |
| 集団の並列前進 + scan | **JAX `vmap`/`lax.scan`/`jit`**(3 は既実践) | `torch.vmap` + `torch.compile` | [知識] |
| 乱数(集団・確率イベント) | `jax.random.split`(3 は既実践、`eco_world.py:244`) | `torch.Generator` per-stream | [知識] |
| elementwise 融合が律速 | `torch.compile` / Triton | CUDA Graph(固定反復) | [コーパス: mlops doc_0717/0521] |
| 混合精度反復改良 | fp32 内側 + fp64 補正(rescaling で fp16 も可) | — | [コーパス: arXiv 2602.14450] |
| TF32 有効化(fp32 GEMM 高速化) | `torch.set_float32_matmul_precision("high")` | `allow_tf32=True` | [知識] |

**JAX の要点(3 向け)** [知識]:
- `vmap` = 集団をバッチ軸に自動ベクトル化。3 は個体ごと重みを明示バッチ(`n` 軸)にしていて実質同義。
- `lax.scan` = 時間ループを1つの融合カーネルに(Python for より圧倒的に速い)。3 は `rollout` で実践済。
- `jit` の境界 = **rollout 全体**を1回 jit(ステップごとに jit しない)。3 は `@partial(jax.jit, static_argnums=1)` で T を static にして正解。
- `jax.random.split` = 反復ごとに key を割る(3 は `step` 内で `split` 実践)。**同じ key を使い回すと相関した乱数**になる落とし穴を回避済。
- 可変構造 = **固定形状 + mask**(3 は `w_rec*mask`)。進化で幅が変わっても同じ jit 済カーネルで回る。

---

## 4. CUDA ビルド導入メモ(調査のみ。実インストールはしない)

現状 `torch 2.11.0+cpu` / `jax 0.7.1 CpuDevice`。sm_120(Blackwell)は **CUDA 12.8+** 世代が要る。以下は**当たり**であり、入れる前にリリースノートで sm_120 対応を確認すること。

**PyTorch(推測ベース、要確認)**:
```powershell
# 既存 CPU 版を外してから CUDA 12.8 wheel を入れる想定(バージョンは要確認)
py -3.11 -m pip uninstall torch
py -3.11 -m pip install torch --index-url https://download.pytorch.org/whl/cu128
# cu129 系が出ていればそちらの方が Blackwell 対応が新しい可能性(推測)
```
- **注意(推測)**: torch 2.11 世代なら cu128/cu129 wheel が Blackwell sm_120 を含む見込み。ただし wheel の同梱 CUDA が sm_120 の SASS/PTX を持つかは**リリースノートで確認**。持たない場合、初回実行時に PTX から JIT される(遅いが動く)か、`no kernel image is available for execution on the device` で落ちる。後者なら sm_120 対応 wheel を待つ/nightly を使う。
- 確認コマンド: `py -3.11 -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"` → `(12,0)` 相当が出れば sm_120 認識。

**JAX(推測ベース、要確認)**:
```powershell
py -3.11 -m pip install -U "jax[cuda12]"
```
- `jax[cuda12]` は CUDA 12 系 + cuDNN を pip で引く。**Blackwell 対応は jaxlib の CUDA 同梱バージョン依存**。0.7.1 で sm_120 が通らなければ新しい jaxlib(cuda12 plugin)へ上げる。
- **Windows 注意(既知)**: JAX の GPU は Windows ネイティブサポートが薄く、**WSL2 経由が定石**(memory 群でも MuJoCo 等は WSL 経路)。RTX 5090 を JAX で使うなら **WSL2 + Linux wheel** が確実(推測だが強め)。
- 確認: `py -3.11 -c "import jax; print(jax.devices())"` → `CudaDevice` が出れば OK。

**共通の落とし穴(知識)**:
- driver 610.74 が CUDA 12.8+ ランタイムに足りるか(通常 wheel は自前 CUDA を同梱するのでドライバ要件だけ満たせばよい。要確認)。
- CPU 版と CUDA 版を混在させない(`+cpu` サフィックスの torch が残ると `cuda.is_available()` が False)。

---

## 5. 「まず何から GPU 化すべきか」優先順位と根拠

### 着手順(費用対効果)

**第1手: 粘菌ソルバ(1)の「dense 直接 → 疎 + matrix-free 反復 + warm start」への書き換え。ただし CPU/numpy でまず疎化して正しさを固定してから GPU。**
- **根拠**:
  - いまが最悪(O(n³) dense を毎反復、毎反復 `A` を再確保、毎反復 host 同期)。**構造的欠陥が3つ重なっている**(P16/P7/P18)ので伸びしろ最大。
  - バッチ次元(多数の迷路・パラメータ)が明確 → batched-kernel(P2)がそのまま効く。GPU 化の教科書的ケース。
  - **時間反復で `L(D)` が少しずつ変わる**性質が warm start(P20)にぴったり。前ステップ解を初期値にした CG は反復数が激減する見込み。
  - ライブラリが揃っている: **torch-sla が batched 疎 solve を明示サポート** [コーパス: arXiv 2601.13994]。自作カーネル不要で登れる。
  - ただし memory `feedback_cpu_short_poc_before_gpu` に従い、**まず CPU で疎化 + 反復法 + warm start を入れて最短路収束が保たれることを確認**してから `device="cuda"`。fp64→混合精度の是非も CPU 段階で残差を見て決める。

**第2手: 形状マッチング(2)の「Python 二重ループ → conv2d/im2col バッチ」化。**
- **根拠**:
  - `_scan_flat`/`_score_at` の二重 for は本質的に相互相関(P10)。`F.conv2d` に落とせば1手で大幅高速化、しかもピラミッド構造(粗→精密)が**そのままバッチ段階化(P9)**になり VRAM 爆発を避けられる。
  - scale/角度をバッチ軸へ畳める(P9)。GEMM/Tensor Core(P14)に乗り TF32 で更に速い。
  - fp32 で足りるので精度の悩みがない(1 と違い fp64 レート問題が無関係)。
  - 1 より下位にした理由: 現状も numpy + ピラミッドで「動いてはいる」。1 の方が構造的損失が大きい。

**第3手: Afterman(3)は wheel を入れるだけ。コード変更はほぼ不要。**
- **根拠**:
  - すでに GPU-ready(SoA + batched einsum + `lax.scan` + `jit` + `random.split` + mask で可変構造)。`jax[cuda12]`(または WSL2)を入れれば `jax.devices()` が cuda になり**そのまま乗る**見込み。
  - やることは (a) wheel 導入(§4)、(b) 集団サイズ n を GPU が埋まるまで上げて occupancy を確保(P8)、(c) bf16/TF32 化の検討(fitness は近似で足りる)。
  - **構造進化で幅が変わる**部分は mask(P11)で固定形状を保っているので再 jit を避けられる=既に正しい設計。

### 一言サマリ
> **最初の1手は「粘菌ソルバを疎 + matrix-free 反復 + warm start に作り替える(まず CPU で正しさ確定)」。** 現状の dense O(n³)・毎反復再確保・毎反復同期という3重の構造欠陥を潰し、時間反復と warm start の相性・batched 疎 solve ライブラリ(torch-sla)の存在という追い風が全部そろっているため、GPU 化の投資回収が最も速い。

---

## 付録: このカタログで実在確認できた RAD コーパス出典

すべて `D:/docs/numerical_methods_corpus_v2/` と `D:/docs/mlops_corpus_v2/` 配下で grep により実在確認(ファイルパスは本文脚注のクラスタ)。

- **torch-sla: Differentiable Sparse Linear Algebra ...**(arXiv 2601.13994) — batched 疎 solve、cuDSS/CuPy/torch-native 自動ディスパッチ。→ P2/P13/第1手の根拠。
- **Mapping Sparse Triangular Solves to GPUs via Fine-grained Domain Decomposition**(arXiv 2508.04917) — サブドメインを shared memory に収め inter-block 同期消去、三角ソルブ 10.7×。→ P3/P6/P19。
- **Taming Preconditioner Drift**(arXiv 2602.19271) — preconditioner の warm-start とドリフト補正(文脈は連合学習、概念を時間反復へ転用=転用は推測)。→ P20。
- **Mixed precision solvers with half-precision (FP16) for Lattice QCD**(arXiv 2602.14450) — 反復改良で FP64/FP32/FP16 混合、rescaling で FP16 も追加反復 20% 以内。→ P17。
- **Matrix-free Neural Preconditioner for the Dirac Operator**(numerical doc_0166)/ **Matrix-Free Galerkin Multigrid Solver**(doc_0720) — matrix-free の実例。→ P18。
- **Hybrid JIT-CUDA Graph Optimization**(mlops doc_0717)/ **Foundry: Template-Based CUDA Graph**(doc_0521) — CUDA Graph で起動オーバーヘッド削減。→ P15。

TF32/FP8/Blackwell sm_120 の具体・wheel バージョン・fp64 レートは**コーパス外の知識ベース + 推測**であり、実インストール時にリリースノート/実測で確認すること。
</content>
</invoke>

---

## 付録2: 粘菌ソルバ GPU 化の実測(2026-08-26、RTX 5090 で実行)

上のカタログで挙げた「第1手」を実装し、**実際に GPU(loco venv の torch 2.11.0+cu128、
CUDA 12.8、RTX 5090)で回した**結果。`packages`(imgevolve ルート)の
`physarum_search.py` / `tests/test_physarum_search.py`。

### やったこと(適用したパターン)
- **matrix-free バッチ CG**(P18/P13) — Laplacian を組まず辺の scatter_add で MatVec。
- **バッチ軸**(P2) — 同一グラフ上の多数の(源,吸込)を (B, ...) に積んで同時解。
- **warm start**(P20) — 前タイムステップの圧力解を次の CG 初期値に。
- **host 同期の間引き**(P6) — CG 収束チェック `rs.max()` の device→host 同期を
  `cg_check_every` で間引く(GPU では 1 反復ごとの同期が直列化要因)。
- **FP32**(P17) — コンシューマ GPU の FP64 は FP32 の 1/64。経路探索は FP32 で十分。
- **CUDA graph 捕獲**(P15) — 1 タイムステップ(固定反復 CG + D 更新)を捕獲し replay。

### 実測(honest)
| 規模 | CPU 逐次疎(基準) | GPU 最良(FP32+CUDA graph) | 倍率 |
|---|---|---|---|
| k=64  (n=4,096, B=16)  | 27.9 s | 1.12 s | **24.9x** |
| k=128 (n=16,384, B=16) | 89.1 s | 1.09 s | **82.2x** |
| k=200 (n=40,000, B=16) | 230.7 s | 1.42 s | **162.3x** |

- **GPU はこの規模では計算量でなくカーネル起動レイテンシで律速**。壁時計はグラフを
  4k→90k ノード(22 倍)に増やしても ~一定(~4s、CUDA graph 前)。つまり大グラフ or
  大バッチほど idle を埋めて「壁時計を増やさず」勝つ。逆に **小グラフ かつ 小バッチでは
  起動オーバーヘッドで CPU に負ける**(k=15,B=32 で 0.3x)。ここを偽らない。
- **効いた順**: CUDA graph(~4x)≫ 同期間引き(1.2x)≈ FP32(1.2x)。この規模では
  FP32 も同期も律速を外せず、起動を消す CUDA graph だけが床を下げた。
- **正しさ**: ユニーク最短路では最短を D≈1.0 に太らせ遠回りを D≈5e-8 に枝刈り(CPU 疎版と一致)。
  非縮退の大バッチでは CUDA graph と eager がビット一致(max|Δ|=0)。**縮退**(等長最短路が
  多数の対称小グリッド)では FP32 のタイ選択が 1-3% 割れるが、これは誤差でなく縮退。
- テスト: CPU で 11 passed / 3 skipped(GPU テストは cuda 不在で skip)、GPU venv で 14 passed。

### 残る手(未着手)
- CUDA graph 前の ~4s 床のさらなる削減は、CG を preconditioned にして反復数を減らす(P20)か、
  複数タイムステップを 1 捕獲にまとめる(replay 回数削減)。
- FP16 + 反復改良(P17)は経路探索では過剰の可能性。必要になってから。
