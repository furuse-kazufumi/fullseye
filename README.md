# imgevolve (working name)

画像処理アルゴリズムを**設計する** AI の PoC。型付き画像 op-DSL を進化させ、
holdout で正直にゲートする。raptor work-graph 上で自律実行(S0+S1)。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

- `ops.py` 型付き op-DSL + genome + dataset + PSNR
- `baseline.py` S0 honest floor (hand-built + random search)
- `evolve.py` S1 memetic 進化 (train fitness / holdout はトラックのみ)
- `report.py` S1 honest gate (champion vs baseline, 汎化 gap, overfit flag)
- `specs/*.json` CommandWorker specs

公開名 = **fullseye**(2026-08-01 確定)。物理リネームは公開時まで保留。

## HALCON パリティ（同じことが「できる」）

目標は名前だけの被覆でなく、各 op が **HALCON と同じ処理を実際に行える**こと。
現状 **229 / 2313 の実 HALCON op を genuine 実装**（`docs/HALCON_PARITY.md`、実測）。

| 生成物 | 役割 |
|---|---|
| `graph.py` → `data/halcon_graph.json` | operator 知識グラフ（2313 ノード） |
| `backends_auto.py` | 固定 shape 語彙 + データ駆動 SPECS（偽名は fail-closed ドロップ） |
| `backends_color.py` | multichannel `color` sort（`cfa_to_rgb` bridge で進化から到達） |
| `imgops_nary.py` | 多入力 capability tier（画像演算・領域集合演算） |
| `verify_auto.py` / 各 `verify()` | 機能ゲート（例外なく宣言 sort を返す op のみ計上） |
| `honest_summary.py` → `docs/HALCON_PARITY.md` | 3 tier を1つの正直な数値に |

## 使い方（`imgevolve.py` CLI — 将来のエージェントも利用可）

```powershell
py -3.11 imgevolve.py ops --search edge      # 実装済み op を検索
py -3.11 imgevolve.py has gauss_filter       # ある HALCON op は実装済みか + 呼び方
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gauss_filter,sobel_amp,otsu"
py -3.11 imgevolve.py coverage               # 正直な被覆数
py -3.11 imgevolve.py index                  # 機械可読 docs/OP_INDEX.json を再生成
```

`docs/OP_INDEX.json` = 全 op（name / halcon / in→out sort / tier）の機械可読索引。
新しい op を1つ足すだけで進化・codegen・catalog・この索引が自動追従する設計。
