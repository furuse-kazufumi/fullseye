"""Measure business-language recipe recall and publish the source inventory.

Three query sets, none of which names an operator:

* ``QUERIES`` — the original 6 (2026-10-29): hit when the expected existing recipe is in the top 2.
* ``E2E_TASKS`` — the 20 requests of the MCP agent e2e (PR #224, ``docs/ops/mcp_agent_tasks.json`` on
  ``feat/mcp-agent-e2e-eval-2026-11-01``) with that PR's ``EXPECTED_OPS`` per judge, copied verbatim. Hit when
  one of the top-2 recipes MCP would show (``runner == "mcp"``) contains an expected op.
* ``docs/recipe_blind_queries.json`` — 60 family queries written from docs/ops only, by a writer who did not
  see the recipes (method in the file). Hit@3 by family (a top-3 recipe of that family) and by op (a top-3
  recipe containing one of the listed ops).

``--baseline <RECIPE_INDEX.json>`` measures the same sets on another index and writes
docs/recipe_retrieval_baseline.json (the "before" side; frozen, then read by the normal run).
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from fullseye.recipesearch import find_recipes, load_recipe_index

OUT = ROOT / "docs/recipe_retrieval_report.json"
BASELINE = ROOT / "docs/recipe_retrieval_baseline.json"
BLIND = ROOT / "docs/recipe_blind_queries.json"

QUERIES = [
 ("remove impulse noise", "Denoise — median"),
 ("count holes in backlit plate", "FA — count holes in a back-lit plate"),
 ("uneven lighting document", "Binarize — document (adaptive)"),
 ("detect bright spots", "Spots — local maxima"),
 ("hairline metal scratch", "FA — scratch on hairline metal"),
 ("weld x-ray pores", "FA — weld porosity (X-ray)"),
]

#: PR #224 tools/mcp_agent_eval.py EXPECTED_OPS(写し)。
EXPECTED_OPS = {
    "judge_component_count": ["count_obj"],
    "judge_region_fraction": ["otsu", "cv_otsu", "sk_otsu"],
    "judge_smoothed_std": ["gaussian", "cv_gaussian"],
    "judge_feature_count": ["cv_good_features"],
    "judge_match_position": ["ncc_locate", "shape_locate"],
    "judge_dolp_mean": ["polarization_dolp_map"],
    "judge_phase_mean": ["wrapped_phase"],
    "judge_depth_mean": ["decode_fringe"],
}
#: PR #224 docs/ops/mcp_agent_tasks.json の (id, request, judge)(写し)。
E2E_TASKS = [
 ("ge_components_3", "画像中の明るい製品を背景から自動で分け、互いに離れた製品が何個あるか整数で答えてください。", "judge_component_count"),
 ("ge_components_5", "暗い背景に散らばる明るい部品を自動二値化し、独立した部品の総数を数えてください。", "judge_component_count"),
 ("ge_fill_fraction", "明るい検査対象を背景から自動で領域化し、画像全面に占める対象画素の割合を求めてください。", "judge_region_fraction"),
 ("ge_gaussian_noise", "センサーの細かなランダムノイズを正規分布状の平滑化で抑え、処理後画像の標準偏差を報告してください。", "judge_smoothed_std"),
 ("po_template_xy", "登録見本との正規化相関を使ってワークを探し、最良一致のスコアと中心の y, x 座標を求めてください。", "judge_match_position"),
 ("po_shape_pose", "輪郭形状を手掛かりにワークの位置を決め、中心の y, x 座標と向きを数値で求めてください。", "judge_match_position"),
 ("po_fixture_corners", "治具合わせに使える安定したコーナー特徴を画像から抽出し、検出数を報告してください。", "judge_feature_count"),
 ("po_grasp_corners", "ロボット把持前の位置合わせ用に良質な角点を抽出し、得られた点の数を報告してください。", "judge_feature_count"),
 ("mv_variant_template", "段取り替え後の部品を登録見本との相関で探し、最良一致位置の y, x 座標を求めてください。", "judge_match_position"),
 ("mv_variant_shape", "品種ごとの輪郭モデルを使って混流中の部品位置を探し、中心座標を求めてください。", "judge_match_position"),
 ("mv_common_corners_4", "形の異なる部品にも共通して使えるコーナー特徴を抽出し、検出数を答えてください。", "judge_feature_count"),
 ("mv_common_corners_6", "製品切替後も追跡に使える角点特徴を画像から取り、点の個数を報告してください。", "judge_feature_count"),
 ("sp_dolp_020", "偏光板を 0, 45, 90, 135 度に回して撮った4枚から、表面の線偏光度マップを求め、その平均値を報告してください。", "judge_dolp_mean"),
 ("sp_dolp_035", "4方向の偏光撮像から透明面の線偏光度を画素ごとに計算し、画像全体の平均を求めてください。角度順は 0, 45, 90, 135 度です。", "judge_dolp_mean"),
 ("sp_dolp_050", "鏡面反射の偏りを調べるため、0, 45, 90, 135 度の偏光画像列から線偏光度マップとその平均を出してください。", "judge_dolp_mean"),
 ("sp_dolp_065", "偏光方向別の4枚を合成して光沢面の線偏光度を求め、平均値を報告してください。フレームは 0, 45, 90, 135 度順です。", "judge_dolp_mean"),
 ("m3_wrapped_ramp_x", "等間隔に位相をずらした4枚の縞画像から、二πの範囲に巻かれた位相マップを計算し、その平均値を報告してください。", "judge_phase_mean"),
 ("m3_wrapped_ramp_y", "4ステップの位相シフト縞からラップされた位相を復元し、全画素の平均位相を求めてください。", "judge_phase_mean"),
 ("m3_depth_ramp_x", "4枚の位相シフト縞画像から連続した高さマップを一括復元し、平均高さを報告してください。較正係数は 1.0 です。", "judge_depth_mean"),
 ("m3_depth_ramp_y", "高速三次元計測用の4ステップ縞画像から連続位相の高さを復元し、その平均を求めてください。位相から高さへの係数は 1.0 です。", "judge_depth_mean"),
]


def _ops(recipe):
    return {s["op"] if isinstance(s, dict) else s[0] for s in recipe.get("stages", [])}


def measure(index):
    rows = []
    for query, want in QUERIES:
        got = [r["name"] for r in find_recipes(query, limit=2, index=index)]
        rows.append({"query": query, "expected": want, "top_2": got, "hit": want in got})
    e2e = []
    for tid, request, judge in E2E_TASKS:
        got = find_recipes(request, limit=2, runner="mcp", index=index)
        want = set(EXPECTED_OPS[judge])
        e2e.append({"id": tid, "judge": judge, "top_2": [r["name"] for r in got],
                    "hit": any(_ops(r) & want for r in got)})
    blind_rows = []
    if BLIND.exists():
        for q in json.loads(BLIND.read_text(encoding="utf-8"))["queries"]:
            got = find_recipes(q["query"], limit=3, lang=q.get("lang"), index=index)
            blind_rows.append({"family": q["family"], "query": q["query"], "top_3": [r["name"] for r in got],
                               "family_hit": any(r.get("family", "2d") == q["family"] for r in got),
                               "op_hit": any(_ops(r) & set(q["ops"]) for r in got)})
    n = lambda xs, k: round(sum(x[k] for x in xs) / len(xs), 4) if xs else None  # noqa: E731
    return {"recipes_in_index": len(index["recipes"]),
            "recipes_mcp": sum(r.get("runner", "mcp") == "mcp" for r in index["recipes"]),
            "recall_at_2": sum(r["hit"] for r in rows) / len(rows), "queries": rows,
            "e2e_task_recipe_hit_at_2": n(e2e, "hit"), "e2e_tasks": e2e,
            "blind_family_hit_at_3": n(blind_rows, "family_hit"), "blind_op_hit_at_3": n(blind_rows, "op_hit"),
            "blind_queries": blind_rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", help="RECIPE_INDEX.json of the 'before' side; writes %s" % BASELINE.name)
    ap.add_argument("--baseline-label", default="")
    a = ap.parse_args(argv)
    if a.baseline:
        old = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
        data = {"label": a.baseline_label, **measure(old)}
        BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(BASELINE); return 0
    data = {"method": "Business-language queries contain no operator names. recall_at_2: the expected existing "
                      "recipe is in the top 2. e2e_task_recipe_hit_at_2: one of the top-2 MCP-runnable recipes "
                      "contains an op PR #224's judge expects. blind_*_hit_at_3: queries written from docs/ops "
                      "without seeing the recipes; a top-3 recipe has that family / one of the listed ops.",
            **measure(load_recipe_index())}
    if BASELINE.exists():
        b = json.loads(BASELINE.read_text(encoding="utf-8"))
        keys = ("recipes_in_index", "recipes_mcp", "recall_at_2", "e2e_task_recipe_hit_at_2",
                "blind_family_hit_at_3", "blind_op_hit_at_3")
        data["before_after"] = {"before_label": b.get("label"),
                                **{k: {"before": b.get(k), "after": data.get(k)} for k in keys}}
    data["inventory"] = load_recipe_index()["inventory"]
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
