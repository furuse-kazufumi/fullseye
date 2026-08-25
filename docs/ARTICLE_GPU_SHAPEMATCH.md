# 記事材料: 形状マッチングを GPU に載せる —— HALCON がやらない conv2d 定式化

> Fullseye 記事の素材(2026-08-26 記録)。**これは記事の下書きでなく材料**。実測値・
> 出典・検証状態・語り口の候補をまとめる。最終記事は career-grade / 20 分読む価値
> (memory `feedback_articles_career_advancement` / `feedback_article_worth_20min_and_craft_corpus`)。
> トーンは自慢回避・確信度で語調を変える(`feedback_article_humility_tone`)。

---

## 1. 一撃の核(記事の背骨)

**Steger 流の勾配方向マッチングのスコアは、モデルを勾配カーネルに描いた
cross-correlation そのもの。cross-correlation は conv2d。conv2d は GPU の本領。**

スコアの定義(shapematch.py `_score_at`):

```
score(r0,c0) = ( Σ_pt  Uy[pt+off]·model_gy[pt]  +  Ux[pt+off]·model_gx[pt] ) / n
```

- `Uy, Ux` = 画像勾配を各画素で単位長に正規化したベクトル場(`gy/|g|`, `gx/|g|`)
- `model_gy, model_gx` = テンプレートのエッジ点の単位勾配(モデル)
- `off` = 点をテンプレート中心基準で画像位置 `(r0,c0)` に置くオフセット
- `n` = モデル点数(画像外に出た点は 0 点として分母に残す)

モデルを2枚の勾配カーネル画像 `Ky[pt]=model_gy`, `Kx[pt]=model_gx`(それ以外 0)に
描くと、全位置のスコアマップは

```
score_map = ( correlate(Uy, Ky) + correlate(Ux, Kx) ) / n
```

`torch.nn.functional.conv2d`(カーネル反転なし=相関)に `padding=h//2` を与えると、
出力の添字がそのまま `_score_at` の `r0` に一致する(下の付録に添字の対応を示す)。

metric(HALCON 同名):
- `use_polarity`(既定) → `max(0, score_map)`
- `ignore_global_polarity` → `abs(score_map)`
- `ignore_local_polarity`(点ごと abs)→ **和の前に非線形が入るので conv では表現不能**。
  HALCON も「偽陽性が出やすい」と警告する緩い metric。GPU 非対応 → CPU フォールバック。

---

## 2. 差別化(記事の主張)—— 王者がやっていないこと

**HALCON(MVTec)は看板の shape-based matching を GPU 化していない。** HALCON の GPU
(OpenCL ベースの "compute device")が加速するのは point-wise 演算・フィルタ
(convol/gauss/mean)・FFT・アフィン変換・一部の色/テクスチャ変換など「密な画素並列」系。
`find_shape_model` / NCC / deformable matching は高度に SIMD・マルチコア最適化された
**CPU** で回る。

> ★検証状態: 「matching が HALCON GPU 非対応」は MVTec の compute-device 対応
> オペレータ一覧に基づく理解。**記事化前に現行版の MVTec ドキュメントで一覧を再確認**
> すること(バージョンで増減しうる)。「correlation=convolution」「Steger スコア」は
> 確立知識。実測(§4)はこのリポジトリで再現可能。

だから「shape matching を conv2d で GPU 化」は新規研究ではなく、**古典アルゴリズムを、
インカンベントが CPU に留めている領域で素直に GPU に落とす**という工学的差別化。
Fullseye(evis の統一視覚 I/F / HALCON パリティ toolkit)の文脈にちょうど合う。

---

## 3. バッチの妙(記事の技術的ハイライト)

**変換(角度×スケール)を conv2d の出力チャンネル軸に積む。** 各変換はテンプレートを
回して/伸縮して作り直した別モデル = 別カーネル。画像 `Uy,Ux` は共有。

```
Ky: (B, 1, hmax, wmax)   # B 個の変換カーネルを中央寄せでパディング
cy = conv2d(Uy, Ky, padding=hmax//2)   # (1, B, H, W) を一撃
```

→ **全変換(角度 72 × スケール 3 = 216 とか)を 2 回の conv2d で同時評価。** これが
CPU のピラミッド探索(1変換ずつ粗密走査)を桁で上回る理由。異なるサイズのカーネルは
共通 `(hmax,wmax)` に中央寄せで埋め、`padding=hmax//2` と整合させる(各モデル自身の
`h//2` 中心が保たれる。付録参照)。

---

## 4. 実測(RTX 5090、2026-08-26)—— これは再現可能

`shapematch_gpu.py`(conv2d バッチ)vs `shapematch._search_transforms`(CPU ピラミッド)。
CPU 側は既にピラミッド最適化済み。それでも:

| 設定 | 変換数 | 画像 | CPU | GPU | 倍率 | 位置一致 |
|---|---|---|---|---|---|---|
| 粗角度 | 7 | 256² | 190 ms | 6 ms | **33.9x** | ✓ |
| 中角度 | 19 | 512² | 1,229 ms | 20 ms | **61.1x** | ✓ |
| 細角度×3スケール | 108 | 512² | 12,076 ms | 137 ms | **88.0x** | ✓ |

- **スコアは `_score_at` とビット一致**(mc=0・float64 で Δ~1e-16)。conv 定式化が厳密。
- 位置/角度/スケールは全ケースで CPU と一致。むしろ GPU は全解像度で網羅探索するので、
  CPU ピラミッド(近似・粗密)より**スコアが僅かに高い**(ピークを取り逃さない)。
- 変換数が増えるほど倍率が伸びる(GPU の並列を埋めるため)。

再現:
```powershell
$loco = "C:\dev\venvs\loco\Scripts\python.exe"   # torch cu128 / RTX 5090
& $loco C:\Users\...\scratchpad\sm_gpu_bench.py   # or tests/test_shapematch_gpu.py
```

---

## 5. いちばん面白い対比(記事の山場候補)—— 同じ GPU、真逆のボトルネック

同じ日に同じ RTX 5090 へ「粘菌ソルバ」と「形状マッチング」を載せた。**効き方が真逆。**

| | 粘菌(physarum、疎グラフ CG) | 形状マッチング(conv2d) |
|---|---|---|
| 演算の性質 | 微小カーネルの逐次反復(4万回) | 密な大カーネル1〜2発 |
| 律速 | **カーネル起動レイテンシ** | **計算スループット** |
| FP32 の効果 | ほぼ無(1.2x) | 効く(そもそも conv が速い) |
| host 同期削減 | 1.2x | 元から不要 |
| CUDA graph | **効く(4x)** —— 起動を消す | 不要 |
| CPU 比 | 25–162x(大グラフ/大バッチ時) | 34–88x(変換が多いほど) |
| 小問題での挙動 | **CPU に負ける**(起動律速) | 小さくても勝ちやすい |

**教訓**: 「GPU に載せる」は一枚岩でない。まず **どのボトルネックか**(起動 vs 計算 vs
メモリ vs 同期)を実測で見極めてから道具(CUDA graph / FP32 / バッチ / 疎化)を選ぶ。
起動律速に FP32 を投げても無駄、計算律速に CUDA graph を足しても無駄。この見極めの
プロセスそのものが記事の価値(design-pattern 適用も transformer 化も「最適化を探る
試行手段の一つ」という、ユーザーの観察とも接続する)。

---

## 6. 先行研究アンカー(記事の related work、honest な区別つき)

- **Steger, "Occlusion, Clutter, and Illumination Invariant Object Recognition"(2002)/
  MVTec の shape-based matching** —— 勾配方向の内積スコア。`find_shape_model` の中身。
  → 本実装の CPU 側もこれに準拠(`_score_at`)。[確立知識、原典要確認]
- **相関定理(correlation = convolution)** —— template matching を相関で解くのは textbook
  (OpenCV `matchTemplate`、FFT 相関)。本実装は空間 conv2d(小カーネルなので FFT より
  素直)。[textbook]
- **conv2d のカーネル=バッチ軸** —— DL の標準プリミティブ。変換を out_channels に積むのが
  本実装の再定式化。[標準手法の転用]
- **RAD コーパス実在確認**: `D:/docs/image_corpus_v2` は NeRF/3DGS など現代 DL 視覚中心で、
  古典 shape matching の一次論文は薄い(=この差別化は新規研究でなく工学的移植、と正直に
  書ける)。GPU 最適化パターンの出典は `docs/GPU_OPTIMIZATION_PATTERNS.md` 付録に実在確認済。

---

## 7. 記事の骨格候補(4言語=別記事、`feedback_articles_per_language_separate`)

1. つかみ: 「HALCON が20年 CPU に置いてきた看板機能を、conv2d 3行で GPU に載せたら 88 倍だった」
2. かみ砕き3段(`feedback_kamikudaki_chugakusei`): マッチング=型紙の重ね合わせ → 型紙の
   輪郭の"向き"を見る → 向きの一致度は畳み込みで一発
3. 数式(§1)を最小限で。用語は「日本語(English)」表記(`feedback_term_format_jp_en`)
4. バッチの妙(§3)= 角度も倍率も型紙の"束"にして一発
5. 山場: 真逆のボトルネック(§5)—— ここが retention の核
6. honest disclosure: 小問題では GPU が負ける/ignore_local は CPU/HALCON 一覧は要再確認
7. 次回に続く(`feedback_article_cliffhanger`): 複数インスタンス検出の GPU 化、evis 視覚への移植

---

## 付録: conv2d の添字が `_score_at` の r0 に一致する理由

`conv2d(U, K, padding=p)` は相関(反転なし): `out[i,j] = Σ_{u,v} U[i+u-p, j+v-p]·K[u,v]`。
カーネルを `p=h//2` でパディングすると `out[i,j] = Σ_{u,v} U[i+u-h//2, j+v-h//2]·K[u,v]`。
点 `pt=(u,v)` について `U` の添字は `i + u - h//2` = `_score_at` の `ys = pt_row - h//2 + r0`
(`r0=i`)と一致。偶数サイズは出力が +1 大きくなるので `[:H,:W]` に切る。異なる `h,w` の
カーネルは `(hmax,wmax)` に中央寄せで埋めるので、各モデル自身の中心 `h//2` が保たれる。
