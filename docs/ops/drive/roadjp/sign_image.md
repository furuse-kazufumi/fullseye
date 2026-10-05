---
op: sign_image
dim: drive
category: roadjp
in: 
out: rgba
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sign_image — DRIVE `roadjp` op

- **データ種**: `なし` → `rgba`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sign_image(kind: 'str', *, size_px: 'int' = 128, value=None, font_path=None, side: 'float | None' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import roadjp; roadjp.sign_image(kind: 'str', *, size_px: 'int' = 128, value=None, font_path=None, side: 'float | None' = None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("sign_image")`)

## 使い方

標識の絵を RGBA float (H, W, 4) ∈ [0,1] で返す(板の外 = alpha 0)。幅 = ``size_px``、高さは形の比。

形と色(規格の配色、記号は単純化):
  * stop: 逆三角形・赤地・白の「止まれ」+ 下に小さく「STOP」。 slow: 逆三角形・白地・赤枠・青の「徐行」+「SLOW」。
  * speed_limit: 円・白地・赤枠・青の数字(``value``、既定 40)。 no_entry: 円・赤地・白の横棒。
  * no_parking: 円・青地・赤枠・赤の斜線(左上→右下)。 one_way: 横長の青地に白の矢印(右向き)。
  * crosswalk: 青地の五角形(家型)に白の歩行者と横断歩道の縞。
  * caution_crossing / caution_signal / caution_children: 黄地の菱形・黒縁、黒の記号
    (踏切 = 遮断機の棒 2 本と ×、信号機 = 3 つの円(赤黄青)、学童 = 2 人の人型)。
文字は PIL でラスタ化する(annotate と同じフォント探索。``font_path`` で固定できる)。**フォントに字形が無ければ
ValueError**(豆腐を黙って出さない)。``side`` は :func:`sign_params` と同じ(寸法比だけに効く)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgba` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [sign_mesh](sign_mesh.md) · [add_sign](add_sign.md) · [signal_jp_mesh](signal_jp_mesh.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
