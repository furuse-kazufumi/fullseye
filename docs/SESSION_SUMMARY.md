# Session Summary (auto-generated)

> 自動生成: `libexec/raptor-auto-summary` (Stop hook)
> 次回 ccr 起動時に CLAUDE.md SESSION START で自動的に読み取られる。

- **最終更新**: 2026-08-25 19:32:46
- **プロジェクト**: `C:/dev/projects/imgevolve`
- **ブランチ**: `master`

## 直近の git log

```
297fc8aa スケール系をピラミッドに乗せ、勾配の符号を既定へ戻した
59069172 形状マッチング一族の点検で7件の欠陥を修正
88adcb33 find_shape_model にピラミッドサーチ実装: 同じ答えで22-92倍速。画像をピラミッド化しモデルは各階層で作り直す。階層数は残るモデル点数で自動決定。テスト9件追加
4b467c15 ピラミッドの正体を一次ソースで確認: 画像をピラミッド化しモデルは各階層で作り直す。自分の測定を2回訂正。産物=NumLevelsを目視でなく実測で決める道具
f7aafe5b ピラミッドの関門: 判定はSpearmanρでなく上位k残存率。細線では解像度もモデル点数も使えずビット幅だけ生きる=軸は対象に依る。find_shape_modelにピラミッド無しのparity穴も記録
5bced271 H5 動的プロジェクションマッピング: 予測2/2的中。ズレ=並進速度xL(一定)+角速度xLx半径(比例)。大きな模様ほど回転に弱い
e8b46b80 H2b訂正: 円弧が遅かったのは私の二値実装のせい。プロファイル版で判別2.7倍早く、費用は解像度にほぼ非依存。交点は1024-2048pxで実測確認
04ef7cc6 H2b検算: 円弧は半径を最適化しても遅い。理由=グーを0と読むしきい値とチョキを早く読むしきい値が同一で両立しない+回転の投影はcosで動き始めが平坦
15c9f07a H2b完了: 予算=(reveal+hold)-判別時刻-形成時間 で台が閉じた形に。判別時刻と遅延は1対1で交換可能な同じ通貨
5ed57448 H2b じゃんけん: 円弧プロファイルを実装。較正済み半径1つで0/2/5に完全分離。予想外=円弧は判別が最も遅い(しきい値型)。度/ラジアンの罠を2回、実装の誤り4件を記録
```

## 現在の git status

```
M docs/SESSION_SUMMARY.md
?? studio_assets/sample_sources_ai/
?? tools/fops_article/
```

## 直近 2 時間に変更されたファイル

```
19:31 .pytest_cache/v/cache/nodeids
19:30 shapematch.py
19:29 docs/HIGHSPEED_VISION.md
19:27 .pytest_cache/v/cache/lastfailed
19:25 tests/test_shapematch_scale_pyramid.py
```

---

> このファイルは毎ターン自動上書きされます。**手動で書いた内容は失われます。**
> 永続化したいメモは `docs/PROGRESS.md`、`docs/next_plan.md`、または `docs/NOTES.md` を使ってください。
