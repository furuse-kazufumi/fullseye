"""Runnable sample: make ground-truth tasks over MCP and score hand-written pipelines.

LLM の役を手書きの処理で演じる。族ごとに、

1. ``fullseye_make_task`` で真値付きの課題を作る(真値はサーバが持ち、返ってこない)。
2. 最初は「もっともらしく間違えた」処理を ``fullseye_score_pipeline`` に出す → 不合格と外れ方の説明。
3. 説明を読んで直した処理を出す → 合格(合格は、隠れた双子の課題でも合格したときだけ)。
   比較実験から外したキズの族(``known_weakness``)は、直した処理も双子の側で落ちることがあるので結果だけを示す。

外部資産は要らない(課題はシミュレーションで作る)。結果は自己検査する。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import call_tool

#: (族, 最初の案, 直した案, 直した理由)。
ATTEMPTS = [
    ("blob_count",
     [{"op": "otsu"}, {"op": "count_obj"}],
     [{"op": "gaussian"}, {"op": "tophat", "params": {"window_px": 9}}, {"op": "otsu"}, {"op": "count_obj"}],
     "照明むらで数え違いが大きい → 粒を包む 9 px の top-hat で背景を引いてから二値化する"),
    ("edge_subpixel",
     [{"op": "threshold_sub_pix"}],
     [{"op": "gaussian"}, {"op": "m1_measure_pos"}],
     "端の位置が 0.15 px を超えてずれる → しきい値でなく勾配の極大で端を取る"),
    ("defect_inspect",
     [{"op": "invert_image"}, {"op": "otsu"}, {"op": "select_largest"}],
     [{"op": "mean_box_wh", "params": {"window_width_px": 7, "window_height_px": 1}},
      {"op": "invert_image"}, {"op": "xsitk_maxentropy_thresh"}, {"op": "select_largest"}],
     "面積が何倍も大きい → 加工目の周期(横 7 px)で平均して縞を消し、暗い裾だけを拾う"),
    ("fringe_phase",
     [{"op": "wrapped_phase"}],
     [{"op": "decode_fringe"}],
     "位相の rms が 1 rad を超える → 巻き込みを展開する"),
]


def main() -> None:
    catalog = Catalog.load()
    store = HandleStore(roots=[])
    for kind, first, fixed, why in ATTEMPTS:
        task = call_tool("fullseye_make_task", {"kind": kind, "seed": 11}, catalog, store)["structuredContent"]
        print("== %s (%s)" % (kind, task["field"]))
        print("   課題: %s" % task["statement"])
        print("   許容: %s" % ", ".join("%s <= %g %s" % (m["name"], m["tolerance"], m["unit"])
                                       for m in task["metrics"]))
        r1 = call_tool("fullseye_score_pipeline", {"task_id": task["task_id"], "stages": first},
                       catalog, store)["structuredContent"]
        print("   案 1 %s: %s" % (" -> ".join(s["op"] for s in first), "合格" if r1["passed"] else "不合格"))
        for line in r1.get("explanation", [r1.get("message", "")]):
            print("        " + line)
        print("   直す: " + why)
        r2 = call_tool("fullseye_score_pipeline", {"task_id": task["task_id"], "stages": fixed},
                       catalog, store)["structuredContent"]
        print("   案 2 %s: %s" % (" -> ".join(s["op"] for s in fixed), "合格" if r2["passed"] else "不合格"))
        for line in r2.get("explanation", [r2.get("message", "")]):
            print("        " + line)
        assert r1["passed"] is False and r1["reason"] == "out_of_tolerance", r1
        assert r2["attempts_used"] == 2
        if task["comparison_ready"]:
            assert r2["passed"] is True, r2
        else:
            # 比較実験から外した族(正誤の分け方が弱い)。直した処理も、隠れた双子の課題で落ちることがある
            # (seed 50〜99 で約 6 %)。結果だけを示し、合否は門にしない。
            print("   注: %s" % task["known_weakness"])
            assert r2["passed"] is True or r2["reason"] == "hidden_check_failed", r2
    print("PASS: 4 族とも、もっともらしい間違いは数値の門で落ち、比較実験に使える 3 族では直した処理が合格した")


if __name__ == "__main__":
    main()
