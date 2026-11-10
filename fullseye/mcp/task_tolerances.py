# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye_score_pipeline`` の許容範囲の表(事前登録)。

**作法(2026-11-10、独立レビュー F8)**: 許容範囲・指標・その根拠を変えるときは、

1. この表だけを変えた commit を先に作る(採点の結果・合格数・正しい処理の選び方はまだ含めない)。
2. ``SCORING_VERSION`` を同じ commit で上げる(``task_id`` に混ざるので古い課題は別物になる)。
3. その後の commit で、採点の実装・正しい処理・合格数を足す。

こうすると「結果を見てから許容を動かしていない」ことを git の履歴で確かめられる
(比較実験の事前登録にあたる)。``tests/test_mcp_task_score_2026_11_09.py`` は、採点が実際に
使う許容と、課題が公表する許容と、この表の 3 つが一致することを見る。

許容は「誤差 <= 許容」で合格。``fringe_phase`` だけは雑音から決まる式
``max(floor, sigma_multiple * noise / (modulation * sqrt(2)))``(4 歩の位相雑音の理論値の倍数)。
"""
from __future__ import annotations

#: 採点規則の版。この表を変えたら上げる。
SCORING_VERSION = "2026-11-10.1"

TOLERANCES: dict[str, dict[str, object]] = {
    "blob_count": {"count_error": 0.0},
    "edge_subpixel": {"top_edge_error": 0.15, "bottom_edge_error": 0.15},
    # 2026-11-10 追加: mask_iou_deficit = 1 - IoU(真値のマスクとの重なり)。結果を見る前に決めた。
    "defect_inspect": {"centroid_error": 1.5, "area_rel_error": 0.30, "mask_iou_deficit": 0.40},
    "fringe_phase": {"phase_rms_error": {"floor": 0.05, "sigma_multiple": 3.0}},
}

RATIONALE: dict[str, str] = {
    "blob_count": "計数は離散で、1 個の数え違いは検査の誤判定そのもの。許容 0。",
    "edge_subpixel": ("画素単位の測定は量子化で最大 0.5 px・rms 0.29 px ずれる。サブピクセルを名乗るには"
                      "その約半分の 0.15 px 以下。雑音による理論限界(~0.03 px)より十分大きい。"),
    "defect_inspect": ("打痕は面積 55〜170 px。縁の 1 画素の含め方で面積は 2〜3 割動くので面積の相対誤差 0.30。"
                       "重心は縁の揺れでは 1 px 未満しか動かないので 1.5 px。IoU は 0.60 以上"
                       "(1 - IoU <= 0.40): いちばん小さい打痕(半径 5 x 3.5 px、面積 55 px、周長 27 px)で"
                       "縁が ±0.5 px ずれると IoU = (55 - 13.5) / (55 + 13.5) = 0.61。"
                       "IoU 0.60 は「いちばん小さい打痕でも縁が半画素以内」に当たる。"),
    "fringe_phase": ("4 歩の位相雑音の理論値 σ = noise / (B √2)。その 3 倍(下限 0.05 rad)を許す。"
                     "展開し忘れると 2π の段差が残り rms は 1 rad を超える。"),
}
