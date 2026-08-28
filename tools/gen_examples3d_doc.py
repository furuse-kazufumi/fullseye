# -*- coding: utf-8 -*-
"""Regenerate docs/EXAMPLES_3D.md from the examples3d registry (single source of truth).

The gallery doc drifts if hand-maintained; this emits it from ``examples3d`` (ids,
tasks, names, summaries) and ``ops3d`` (op count) so it always matches what
``examples3d.validate()`` actually runs. Run after adding/removing examples::

    PYTHONPATH=<repo> PYTHONUTF8=1 py -3.11 tools/gen_examples3d_doc.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import examples3d as E
import ops3d

# task id -> Japanese section label (fallback: the raw task id)
TASK_LABEL = {
    "registration": "位置合わせ / SLAM",
    "metrology": "計測 / メトロロジー",
    "depth": "深度 / ステレオ / トモグラフィ",
    "reconstruction": "再構成",
    "modeling": "モデリング",
    "features": "特徴",
    "shape_analysis": "形状解析",
    "shape_fitting": "形状当てはめ",
    "shape_descriptors": "形状記述子",
    "shape_from_shading": "陰影からの形状復元",
    "segmentation": "セグメンテーション",
    "decimation": "間引き(decimation)",
    "mesh_process": "メッシュ処理",
    "pose_estimation": "姿勢推定",
    "structured_light": "構造化光",
    "optics": "光学(光線)",
    "mapping": "地図 / ナビゲーション",
    "range_sensing": "レンジセンシング",
    "motion": "運動 / シーンフロー",
    "deformable_registration": "非剛体位置合わせ",
    "augmentation": "データ拡張",
    "rendering": "レンダリング品質",
}

# data provenance id -> Japanese label
DATA_LABEL = {
    "synthetic": "合成データ(制御GT)",
    "procedural": "手続き生成(GTは幾何/解析)",
    "skeleton_ct": "骨格CT(MS-Human-700 実解剖骨)",
    "itokawa": "小惑星イトカワ(Gaskell形状モデル/JAXA)",
    "download": "DL実データ(オプトイン取得 / fullseye samples)",
}

# section order (most-covered first, then any unseen tasks appended)
ORDER = ["registration", "reconstruction", "modeling", "features", "shape_analysis",
         "shape_fitting", "shape_descriptors", "shape_from_shading", "metrology",
         "depth", "segmentation", "decimation", "mesh_process", "pose_estimation",
         "structured_light", "optics", "mapping", "range_sensing", "motion",
         "deformable_registration", "augmentation", "rendering"]


def main():
    n_ops = sum(len(ops3d.list_ops(c)) for c in ops3d.categories())
    by_task = E.by_task()
    by_data = E.by_data()
    n_ex = len(E.names())
    get = E.get

    out = []
    out.append("# Fullseye 3-D ビジョン — 事例ギャラリー(EXAMPLES_3D)\n")
    out.append(f"Fullseye の 3-D オペレータ群(`ops3d` = {n_ops} の型付き op)を、"
               f"**実問題を解く実行可能な事例**（全 {n_ex} 件）で示します。")
    out.append("各事例は自己完結・自己検証のスクリプト(`examples_3d/<id>.py`)で、"
               "データを読み・op を呼び・**ground truth を print して assert** します。")
    out.append("一覧は `examples3d.py` レジストリが正本で、"
               "`examples3d.validate()` が全件を実行して**動くものだけ**を掲示します。")
    out.append("\n> このファイルは `tools/gen_examples3d_doc.py` が"
               "レジストリから自動生成します(手編集しないこと)。\n")
    out.append("```python")
    out.append("import examples3d")
    out.append("examples3d.names()                 # 全事例 id")
    out.append("print(examples3d.code('cad_to_scan'))  # 実行可能ソース")
    out.append("examples3d.validate()              # 全件実行(動作確認)")
    out.append("```\n")
    out.append("直接実行も可能:\n")
    out.append("```")
    out.append("PYTHONPATH=<repo> PYTHONUTF8=1 py -3.11 examples_3d/<id>.py")
    out.append("```\n")

    # provenance summary
    out.append("## 実データ源\n")
    for d in ["synthetic", "procedural", "skeleton_ct", "itokawa", "download"]:
        if d in by_data:
            out.append(f"- **{DATA_LABEL.get(d, d)}** — {len(by_data[d])} 事例")
    for d in sorted(by_data):
        if d not in DATA_LABEL:
            out.append(f"- **{d}** — {len(by_data[d])} 事例")
    out.append("\n実データの帰属・引用は `studio_assets/sample_3d/ATTRIBUTION.md`(骨格CT/イトカワ)"
               "および `fullseye samples list`(DL実データの各ソース URL / ライセンス)を参照。\n")

    # examples by task
    out.append("## タスク別 事例\n")
    seen = set()
    tasks = [t for t in ORDER if t in by_task] + [t for t in sorted(by_task) if t not in ORDER]
    for t in tasks:
        if t in seen:
            continue
        seen.add(t)
        out.append(f"### {TASK_LABEL.get(t, t)}\n")
        for eid in by_task[t]:
            meta = get(eid)
            out.append(f"- **{meta['name']}** (`{eid}`, {meta['data']}) — {meta['summary']}")
        out.append("")

    doc = "\n".join(out) + "\n"
    dst = os.path.join(ROOT, "docs", "EXAMPLES_3D.md")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {dst} ({len(doc)} bytes, {n_ex} examples across {len(tasks)} tasks, {n_ops} ops)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
