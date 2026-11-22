# BOP T-LESS CI subset

このディレクトリは、Fullseye の実データ門が毎回読む BOP T-LESS の小さな切り出しです。
場面2・画像3にある3個体のうち、obj 5とobj 6を採点するための入力を収録しています。
`scene_gt.json` と `scene_gt_info.json` の個体リストは、mask添字とクラスタ割当の前提を
保つため、obj 7を含む元の3個体を残しています。obj 7のモデルとmaskは収録しません。

## 出典・ライセンス・引用

- データセット: BOP T-LESS, https://bop.felk.cvut.cz/datasets/
- 配布物: Hugging Face `bop-benchmark/tless` の `tless_models.zip` と
  `tless_test_primesense_bop19.zip`
- 元アーカイブのSHA-256 (`tools/fetch_tless.py` の固定値):
  - `tless_base.zip`: `dd70ca884b7c471a530a952f70c5ab2c212f3d2c2f371be86397442b97d70a7e`
  - `tless_models.zip`: `6a29c59766b8d2af05e62e71739f0ca7243ad81bc3c7f9a24925504a8cb37928`
  - `tless_test_primesense_bop19.zip`: `1a18f6bbfb5ac4ced8529f7a35225adfed88c0f62ef38067933e2b541ef1d00b`
- ライセンス: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/

元データとともに作られる `TLESS_LICENSE.txt` は、CC BY 4.0であること、一次配布元、
論文への帰属表示、BOP形式・ベンチマークの引用先を示しています。このsubsetにも同じ
条件が適用されます。

引用: Hodaň et al., "T-LESS: An RGB-D Dataset for 6D Pose Estimation of
Texture-less Objects", WACV 2017, https://doi.org/10.1109/WACV.2017.8

BOP形式・ベンチマークの引用: Hodaň, Michel et al., "BOP: Benchmark for 6D
Object Pose Estimation", ECCV 2018, http://bop.felk.cvut.cz

BOP Challengeの引用: Hodaň et al., "BOP Challenge 2020 on 6D Object
Localization", https://doi.org/10.1007/978-3-030-68223-0_12

## 収録内容と変更点

- `test_primesense/000002`: `scene_camera.json`、`scene_gt.json`、
  `scene_gt_info.json` は画像キー `"3"` だけを残しました。RGB、depth、obj 5/6の
  visible maskは元ファイルをバイト単位で複写しています。
- `models_reconst/models_info.json`: obj 5/6のキーだけを残しました。
- `models_reconst/obj_000005.ply` と `obj_000006.ply`: PoCの `_cap` が
  1000点へ一様抽出するときに選ぶ頂点行だけを元の順で残しました。
- `models_cad/obj_000005.ply` と `obj_000006.ply`: PoCの評価点抽出関数が
  最大600点へ一様抽出するときに選ぶ頂点行だけを元の順で残しました。
- 間引いたPLYは `element vertex` を残した行数へ更新し、`element face`、face property、
  face行を落としました。頂点行の文字列は元ファイルのままです。

この規則はPoCの主経路が読み込むモデル点と評価点を変えません。一方、診断経路の
理想深度合成 `render_point_depth(model_full, ...)` はreconstの全頂点を使うため、間引きで
値が変わります。CI門は `diagnostics=False` として診断経路を実行しません。

## 作り直し方

元のBOP T-LESSを変更せず、repoルートから次を実行します。

```text
PYTHONUTF8=1 py -3.11 tools/make_tless_subset.py "<T-LESS root>"
```

`<T-LESS root>` を省略した場合は `FULLSEYE_TLESS_DATA`、未設定なら
`~/fullseye_data/tless` を読みます。期待値の記録は次のrepo内の道具で作り直せます。

```text
PYTHONUTF8=1 py -3.11 tools/make_tless_subset.py --record-expected
```

生成器は出力を作り直し、`SHA256SUMS` も決定的に更新します。
