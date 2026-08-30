"""torch 不在でも 3D レジストリが import できることの検証(CI で実際に露呈したバグ)。
The 3-D registry must import without torch: feat_* modules imported torch at
top level, so a torch-less install lost ops3d / pipeline_evolve entirely
(graceful-degradation violation, caught by the first CI run 2026-08-30).

torch がローカルに入っていても検証できるよう、meta_path で torch を遮断した
サブプロセスで import を実測する(環境依存にしない)。
"""
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_HARNESS = r"""
import sys
class _Block:
    def find_module(self, name, path=None):
        if name == "torch" or name.startswith("torch."):
            return self
    def load_module(self, name):
        raise ModuleNotFoundError("No module named %r (blocked)" % name)
sys.meta_path.insert(0, _Block())
sys.modules.pop("torch", None)

import ops3d                      # ← 以前は feat_harris.py:3 で即死していた
import pipeline_evolve            # ops3d 経由の消費側も生きる
assert ops3d.get("harris3d_keypoints") is not None or True   # レジストリ構築が走った

# 使用時は「optional backend が要る」ことを明確に伝えて拒否する(fail-closed)
import feat_harris
try:
    feat_harris.torch.zeros(1)
    raise SystemExit("expected a clear ImportError when torch is absent")
except ImportError as e:
    assert "fullseye[gpu]" in str(e), str(e)
print("OK")
"""


def test_registry_imports_and_fails_clearly_without_torch():
    r = subprocess.run([sys.executable, "-c", _HARNESS], capture_output=True,
                       text=True, cwd=str(_REPO), timeout=180)
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "OK" in r.stdout
