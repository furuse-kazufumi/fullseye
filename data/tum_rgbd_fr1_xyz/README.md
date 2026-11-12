# TUM RGB-D(freiburg1_xyz)の深度 32 枚と真値の軌跡

`examples/poc_real_tum_rgbd_slam.py` と `tests/test_poc_real_tum_rgbd_slam.py` が読む、公開されている実測データの切り出し。
**作り直していない** —— 配布元から取得したバイト列をそのまま置き、PoC が読む前にバイト数と SHA-256 を照合する(台帳は PoC の `BUNDLED`)。
ライセンスは Fullseye の Apache-2.0 とは別。取得は 2026-11-11。

## 出典とライセンス

- データ: TUM RGB-D benchmark の `rgbd_dataset_freiburg1_xyz`(Kinect で机の上を撮影、30.09 s、全 798 枚の深度)。
  <https://cvg.cit.tum.de/data/datasets/rgbd-dataset>(取得物は `freiburg1/rgbd_dataset_freiburg1_xyz.tgz`、448,204,271 バイト、
  SHA-256 `a0236d97b8c30cd93b653656d2b6c293ff7c982a4130ef2a1a8beecdb124ef98`)。
- ライセンス: 配布ページの License 節「Unless stated otherwise, all data in the TUM RGB-D benchmark is licensed under a Creative Commons 4.0 Attribution License (CC BY 4.0)
  and the accompanying source code is licensed under a BSD-2-Clause License.」(2026-11-11 に確認。この切り出しにソースコードは含めていない)。
- 表示(帰属): TUM(ミュンヘン工科大学)の Computer Vision Group。論文 J. Sturm, N. Engelhard, F. Endres, W. Burgard, D. Cremers,
  "A Benchmark for the Evaluation of RGB-D SLAM Systems", Proc. of the International Conference on Intelligent Robot Systems (IROS), Oct. 2012。

## 入っているもの(と加えた変更)

| ファイル | 中身 | 変更 |
|---|---|---|
| `depth/<timestamp>.png`(32 枚) | 16 bit の深度画像(640×480、値 / 5000 = m、0 = 欠測)。`depth.txt` の 0, 5, 10, …, 155 番目 | なし(バイト列のまま) |
| `depth_subset.txt` | 上の 32 枚の「時刻 ファイル名」(配布の `depth.txt` の該当行) | 行の抜き出し、先頭のコメント行を差し替え |
| `groundtruth_subset.txt` | 32 枚の時刻の前後 0.1 秒に入るモーションキャプチャの姿勢 537 行(`timestamp tx ty tz qx qy qz qw`) | 行の抜き出し(値は無改変)、先頭のコメント行を差し替え |

カラー画像(`rgb/`)・加速度計・元の `depth.txt` / `groundtruth.txt` の全体は入れていない(Pages の容量のため)。合計 約 3.9 MB。
各ファイルのバイト数と SHA-256 は PoC の `BUNDLED`(`tests/test_poc_real_tum_rgbd_slam.py` が照合)。

## 使うときの注意(PoC の限界欄と同じ)

- 密な深度の真値は無い(姿勢の真値だけ)。標本は 1 系列・32 枚。
- 内部パラメータは TUM のページが推奨する ROS の既定値(fx = fy = 525.0, cx = 319.5, cy = 239.5)を使い、深度の歪みは補正していない。
- 真値の姿勢と深度カメラの間の外部パラメータは補正していない。
