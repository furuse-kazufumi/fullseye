# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""docs/gsplat/ の公開ページ(3DGS の商品ビューアとカタログ)を作り直す。

    py -3.11 tools/build_gsplat_pages.py

中身は ``examples/gsplat_product_viewer.py`` の ``build()``(形 = Fullseye の符号付き距離場の op + marching cubes、
3DGS = gs_from_world、ページ = gsviewer.gs_viewer_html / gs_catalog_html)。出力:

* ``docs/gsplat/headphones.html`` —— 1 品のビューア(注記点・寸法つき)
* ``docs/gsplat/catalog.html``    —— 5 品のカタログ(サムネイルから選ぶ)
* ``docs/gsplat/headphones_trained.html`` —— GPU で学習した版。こちらは GPU の torch が要るので別に
  ``FULLSEYE_TORCH_PYTHON=<CUDA の python> py -3.11 examples/gsplat_trained_product.py --out docs/gsplat`` で作る。

regen_all の鎖には入れない(EXCLUDED): marching cubes に scikit-image(任意の依存)が要り、5 品の 3DGS 化と
サムネイルの numpy 描画で 1 分ほどかかり、出力は 1 本数 MB。ページを変える回は手で回して commit する。
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))

import gsplat_product_viewer  # noqa: E402


def main() -> int:
    r = gsplat_product_viewer.build(os.path.join(ROOT, "docs", "gsplat"))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
