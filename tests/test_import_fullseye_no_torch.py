"""``import fullseye`` は torch を読まない(optional extra)/ importing fullseye must not pull torch.

実測(2026-11-11): ``import torch`` が ``import fullseye`` 約 2.8 秒のうち 1.6 秒で、読んでいたのは
``physarum_search`` の先頭の ``import torch``(opsgraph 経由)だけだった。遅延プロキシ(torch_lazy)に。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_import_does_not_load_torch():
    code = "import sys, fullseye; sys.exit(3 if 'torch' in sys.modules else 0)"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-500:] or "torch was imported by `import fullseye`"


def test_physarum_torch_path_still_works_lazily():
    """torch が入っていれば cpu 経路(最初の属性アクセスで読み込む)が numpy 経路と一致する。"""
    import numpy as np
    import pytest

    import physarum_search as ps
    if not ps._HAS_TORCH:
        pytest.skip("torch not installed")
    g = ps.maze_to_graph(np.ones((5, 5), dtype=bool))
    s, t = ps.node_at(g, 0, 0), ps.node_at(g, 4, 4)
    a = ps.solve_physarum(g, s, t, device="numpy")
    b = ps.solve_physarum(g, s, t, device="cpu")
    assert np.allclose(a.D, b.D, atol=1e-6)
    assert a.D.size > 0                       # 空比較でないこと
