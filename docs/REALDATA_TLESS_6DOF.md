# BOP T-LESS 実機深度 6 自由度 PoC

`examples/poc_real_tless_6dof.py` は、PrimeSense Carmine 1.09 の実測深度を点群へ戻し、法線推定、RANSAC による作業台除去、Euclidean clustering、Point Pair Features、ICP を順に適用します。BOP toolkit は使わず、BOP JSON、16-bit depth PNG、ASCII PLY、対称性を自前で読みます。

## データ、ライセンス、引用

BOP の一次配布ページの T-LESS 欄は `license: CC BY 4.0` と明記しています。このため再配布と派生物の公開が可能です。データはリポジトリに含めず、`tools/fetch_tless.py` が外部キャッシュへ取得します。

- 一次配布・ライセンス: https://bop.felk.cvut.cz/datasets/
- 配布ファイル: https://huggingface.co/datasets/bop-benchmark/tless
- T-LESS: Hodaň et al., WACV 2017, https://doi.org/10.1109/WACV.2017.8
- BOP 指標: Hodaň et al., ECCVW 2020, https://doi.org/10.1007/978-3-030-68223-0_12

取得した公式 LFS オブジェクトは次のとおりです。

| ファイル | bytes | SHA-256 |
|---|---:|---|
| `tless_base.zip` | 49,597 | `dd70ca884b7c471a530a952f70c5ab2c212f3d2c2f371be86397442b97d70a7e` |
| `tless_models.zip` | 33,468,762 | `6a29c59766b8d2af05e62e71739f0ca7243ad81bc3c7f9a24925504a8cb37928` |
| `tless_test_primesense_bop19.zip` | 825,276,992 | `1a18f6bbfb5ac4ced8529f7a35225adfed88c0f62ef38067933e2b541ef1d00b` |

## 固定した評価条件

可視率 `visib_fract >= 0.50` を対象とし、scene 1 / image 157 の分離した4対象と scene 8 / image 263 の接触・遮蔽を含む6対象を評価しました。前者は4クラスタ対4対象、後者は9クラスタ対6対象です。後者では過分割と、obj 19/20 を同じクラスタへ割り当てる結合が同時に起きます。

| scene | image | 欠測depth [px] | 飛び候補 [px] | dense点 | 4 mm voxel | ground | object点 | cluster / 対象 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 157 | 3,678 | 0 | 186,038 | 12,542 | 9,689 | 2,806 | 4 / 4 |
| 8 | 263 | 3,204 | 3 | 183,622 | 15,080 | 11,420 | 3,079 | 9 / 6 |

## 結果

MSSD は物体径の `0.05d..0.50d`、MSPD は `5..50 px` の10閾値で recall を平均しました。PoC は VSD を計算しないため、公式ARは出しません。また、公開値は公式全テスト、PoCは固定10対象なので、同一標本の直接対決ではありません。

| 方法 | official AR | AR_MSSD | AR_MSPD |
|---|---:|---:|---:|
| Fullseye PPF+ICP（PoC 10対象） | — | 0.290 | 0.320 |
| Drost-CVPR10-3D-Only（公式全test） | 0.444 | 0.478 | 0.480 |
| Vidal-Sensors18（公式全test） | 0.538 | 0.575 | 0.574 |

PoC は両公開ベースラインに負けています。同じモデルと真値姿勢から作った理想 z-buffer 深度では0.880/0.880です。合成から実機への低下は MSSD 0.590、MSPD 0.560でした。ICPを外すと0.280/0.250、法線の符号をカメラ向きに揃えないと0.200/0.230です。

| scene | obj | 可視率 | 結合cluster | MSSD [mm] | MSPD [px] | ADD-S [mm] | 対称性最良 R [deg] | t [mm] |
|---:|---:|---:|:---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0.969 | no | 64.34 | 70.75 | 4.72 | 101.8 | 17.0 |
| 1 | 25 | 0.984 | no | 17.64 | 13.88 | 6.74 | 6.5 | 12.2 |
| 1 | 29 | 1.000 | no | 89.10 | 102.00 | 14.67 | 89.3 | 22.9 |
| 1 | 30 | 0.960 | no | 15.11 | 17.03 | 8.03 | 3.2 | 13.1 |
| 8 | 19 | 1.000 | yes | 12.59 | 12.34 | 6.41 | 6.9 | 8.8 |
| 8 | 20 | 0.569 | yes | 108.60 | 94.17 | 18.88 | 121.6 | 30.9 |
| 8 | 21 | 0.843 | no | 97.52 | 140.78 | 8.98 | 145.0 | 22.7 |
| 8 | 22 | 0.960 | no | 100.11 | 127.94 | 15.81 | 137.8 | 32.4 |
| 8 | 23 | 0.648 | no | 96.06 | 103.30 | 10.46 | 174.5 | 21.9 |
| 8 | 24 | 0.985 | no | 12.90 | 7.99 | 5.53 | 4.9 | 10.0 |

失敗を `MSSD > 0.2d` とすると6/10です。重複を許した内訳は、結合クラスタ1、可視率0.8未満2、厚さ/径0.45未満2、可視マスク内の深度欠損1%超1、対称部品4でした。

## 実行

```powershell
py -3.11 tools/fetch_tless.py
py -3.11 examples/poc_real_tless_6dof.py
```

CIなどデータが無い環境では取得を始めず、PoCに固定した `RECORDED` を表示します。図を所定の場所へ再生成する場合だけ `FULLSEYE_FIGURE_DIR=docs/articles/assets/poc/poc_real_tless_6dof` を設定します。

## 図

1. `01_pose_overlay.png`: 推定姿勢（橙）と公開真値（青）。代表図。
2. `02_rgb_depth.png`: 実RGBと実機depth。
3. `03_mssd_by_object.png`: 対象ごとのMSSD recall。
4. `04_synthetic_vs_real.png`: 理想深度と実機深度。
5. `05_failure.png`: 接触・遮蔽を含む失敗例。
