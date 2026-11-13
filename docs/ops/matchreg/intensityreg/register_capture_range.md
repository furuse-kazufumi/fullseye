---
op: register_capture_range
dim: matchreg
category: intensityreg
in: image2d
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# register_capture_range — MATCHREG `intensityreg` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_capture_range(fixed, method='ecc', offsets_px=(1, 2, 4, 8, 12, 16, 24, 32), n_directions=8, success_px=0.5, rotation_deg=0.0, modality='same', noise_sigma=0.0, margin=8, seed=0, method_kwargs=None)` (実装を直接呼ぶなら `import intensityreg; intensityreg.register_capture_range(fixed, method='ecc', offsets_px=(1, 2, 4, 8, 12, 16, 24, 32), n_directions=8, success_px=0.5, rotation_deg=0.0, modality='same', noise_sigma=0.0, margin=8, seed=0, method_kwargs=None)`、台帳から引くなら `opsmatchreg.get("register_capture_range")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

初期のずれの大きさごとに、恒等から始めた位置合わせが真値へ戻る割合を返す(収束の範囲)。→ table。

大きさ ``d``(``offsets_px``)の並進を ``n_directions`` 方向(+ 任意の回転 ``rotation_deg``)で
合成し(:func:`synthesize_moving`)、``method`` を**恒等の初期値から**走らせ、内側の画素の EPE の
平均が ``success_px`` 未満なら成功。method が例外で止まったら失敗として数える(理由を ``failures``
に数える)。``capture_range_px`` は、それ以下のすべての大きさで成功率が 0.9 以上になる最大の ``d``
(最小の大きさで届かなければ 0)。

ECC のような局所の最適化は、ずれが模様の大きさを超えると別の極値に落ちる。位相相関(``"phase"``)は
大域の探索なので並進には範囲が広いが、回転が入ると崩れる —— 同じ表で比べられる。

Args:
    fixed: 基準の 2-D 画像。
    method: :data:`ACCURACY_METHODS`。
    offsets_px: 試す並進の大きさ [px] の並び(正、昇順でなくてよい)。
    n_directions: 方向の数。
    success_px: 成功とみなす EPE の平均の上限 [px]。
    rotation_deg: 並進に加える回転(中心まわり、度)。
    modality / noise_sigma / seed / method_kwargs: :func:`register_accuracy_map` と同じ。
    margin: 縁から除く画素数(大きなずれで moving の外から来る画素も除く)。

Returns:
    dict(``kind="capture_range"``)。``rows``(大きさごとの ``offset_px`` / ``success_rate`` /
    ``median_epe`` / ``n_trials`` / ``failures``)/ ``capture_range_px`` / ``method`` / ``success_px`` /
    ``rotation_deg`` / ``modality``。

Raises:
    ValueError: 画像が不正 / method・modality が違う / 引数が値域外。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](../featmatch/features_match.md) · [ransac_homography](../featmatch/ransac_homography.md) · [ransac_fundamental](../featmatch/ransac_fundamental.md) · [registration_to_flow2d](registration_to_flow2d.md)

## 同カテゴリ(`intensityreg`)

[register_ecc](register_ecc.md) · [register_mi](register_mi.md) · [register_ffd](register_ffd.md) · [registration_to_flow2d](registration_to_flow2d.md) · [register_accuracy_map](register_accuracy_map.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
