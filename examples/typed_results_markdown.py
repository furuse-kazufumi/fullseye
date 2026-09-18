# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""typed_results_markdown — 型付きの返り値を Markdown で読める形にし、JSON を埋め込んで戻す。

    py -3.11 examples/typed_results_markdown.py

【この例が示すこと】
``fs.to_markdown(value, sort)`` で table / points / region / image を Markdown に。表は本物の
GFM、画素にできないものは 1 行要約。``fs.json_block`` で厳密な JSON を ```json フェンスに包み、
``fs.extract_json`` で Markdown 文書から fullseye 封筒だけを bit 一致で回収する(assert)。
``fs.report`` は「読める」と「機械で戻せる」を 1 文書で両立する(with_json=True)。

EXTEND: 検査結果を報告書に載せるなら report(...) をファイルに書く。MCP の人間向け text と
structuredContent を 1 か所で作るのにも使える。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def main() -> int:
    rng = np.random.default_rng(0)
    blobs = [{"id": 1, "area": 12.5, "label": "A"},
             {"id": 2, "area": 3.0, "label": "B|C"}]     # パイプは自動でエスケープ
    pts = np.array([[1.5, 2.0], [3.25, 4.0], [1.0 / 3.0, np.pi]])
    region = (rng.random((12, 16)) > 0.6).astype(np.float64)
    img = rng.random((6, 8))

    print("--- to_markdown(table) ---")
    print(fs.to_markdown(blobs, "table"))
    print("\n--- to_markdown(points) ---")
    print(fs.to_markdown(pts, "points"))
    print("\n--- to_markdown(region) / (image) は 1 行要約 ---")
    print(fs.to_markdown(region, "region"))
    print(fs.to_markdown(img, "image"))

    # report: 読める + 機械で戻せる 1 文書。
    doc = fs.report([("Blobs", blobs, "table"),
                     ("Score", 0.873, "feature"),
                     ("Points", pts, "points")],
                    title="Inspection report", with_json=True)
    print("\n--- report(with_json=True) の冒頭 ---")
    print("\n".join(doc.splitlines()[:6]), "...")

    # 埋め込んだ厳密な JSON を回収 —— points は bit 一致で戻る。
    recovered = fs.extract_json(doc)
    got = {sort: val for val, sort in recovered}
    assert "points" in got and np.array_equal(got["points"].view(np.uint8), pts.view(np.uint8))
    print("\nextract_json: 回収した sort =", sorted(got))
    print("points 往復 bit 一致 =", np.array_equal(got["points"].view(np.uint8), pts.view(np.uint8)))

    # 異種フェンス(普通の json)は無視、fail-closed も確認。
    mixed = doc + "\n```json\n{\"not\": \"fullseye\"}\n```\n"
    assert len(fs.extract_json(mixed)) == len(recovered)
    try:
        fs.to_markdown(np.zeros(3), "match")
    except ValueError as exc:
        print("match は断られる:", str(exc)[:56])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
