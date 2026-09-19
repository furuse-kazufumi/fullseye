---
id: pose-helpers-could-not-take-their-own-matrix
date: 2026-09-20
found_by: genspark_external_review
kind: implementation-bug
severity: medium
where: [pose_quat.py]
ops: []
gate: [test_pose_helpers_accept_their_own_homogeneous_matrix, test_other_shapes_say_what_a_pose_is]
status: fixed
---

# pose ヘルパが、自分の出力(4×4 同次行列)を受け取れなかった

## 症状

GenSpark 第 14 報(公開 API 955 本の一括スモークを有効引数で再検証した回)。ライブラリ自身の往復で落ちる:

```python
H = fullseye.pose_to_hom_mat3d_local(np.array([0.1, 0.2, 0.3, 0., 0., 0., 1.]))   # (4, 4)
fullseye.pose_to_quat(H)
# IndexError: index 4 is out of bounds for axis 0 with size 4   (pose_quat.py, _pose_to_R: pose[3], pose[4], pose[5])
```

`pose_to_dual_quat` / `pose_to_hom_mat3d_local` も同じ。3×3 の回転行列も IndexError、dict は `KeyError: 3`。3 関数とも docstring が空で、受ける形が書いてなかった。

## なぜ門が通したか

`_pose_to_R` は `pose[3], pose[4], pose[5]` の素の添字で、形を見ていない。4×4 を渡すと `pose[3]` は 4 行目(行ベクトル)、`pose[4]` で範囲外 —— 「pose とは 6/7 要素のベクトル」という前提が関数の中にしか無く、テストも 6/7 ベクトルだけを流していた。同じモジュールに `hom_mat3d_to_pose_local`(4×4 → pose)が在るのに、入口で使っていなかった([[feedback_one_probe_input_is_not_coverage]]: 自分の出力を自分の入力に戻す探針が無い)。

## 直し

`pose_quat._as_pose(pose, fn)` —— 6/7 ベクトルはそのまま、**4×4 は `hom_mat3d_to_pose_local` で pose に戻し**、3×3 は並進 0 の 4×4 として同じ道を通す。他の形(5 要素・2×2・dict・スカラー)は「pose must be a 6/7-vector (tx, ty, tz, rx, ry, rz[, type]) or a 3x3 / 4x4 matrix, got …」の `ValueError`。`_pose_to_R` / `pose_to_hom_mat3d_local` / `pose_to_dual_quat` の入口で呼び、3 関数に docstring(受ける形・回転順 `Rz·Ry·Rx`・四元数の並び)を書いた。

門: 4×4 → quat / dual quat が元ベクトルからの結果と一致 / 3×3 は双対部 0 / 7 要素(type 付き)は従来どおり / 5 種の外れた形が同じ文で断られる。

**同報で設計・誤検知として残したもの**: D-2(index の 1,940)= 層の合算で内訳を併記済み。D-7(a=-1.0 が「clamped」なのに a=1.0 と違う)は −1 → 0 への丸めなので当然 a=1.0 とは違う(a=1e9 → 1.0 と同一なのは正しい丸め)。D-8 / D-9(値域と NaN を入口で検査しない)= `extra_checks` の設計と、第 3 陣の非有限出力の記録。run_pipeline / Export の以前の主張は GenSpark 自身が撤回。
