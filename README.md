# imgevolve (working name)

画像処理アルゴリズムを**設計する** AI の PoC。型付き画像 op-DSL を進化させ、
holdout で正直にゲートする。raptor work-graph 上で自律実行(S0+S1)。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

- `ops.py` 型付き op-DSL + genome + dataset + PSNR
- `baseline.py` S0 honest floor (hand-built + random search)
- `evolve.py` S1 memetic 進化 (train fitness / holdout はトラックのみ)
- `report.py` S1 honest gate (champion vs baseline, 汎化 gap, overfit flag)
- `specs/*.json` CommandWorker specs

公開名は衝突実測後に確定。
