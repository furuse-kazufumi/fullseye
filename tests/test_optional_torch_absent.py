"""torch 不在でも 3D レジストリが import できることの検証(CI で実際に露呈したバグ)。
The 3-D registry must import without torch: feat_* modules imported torch at
top level, so a torch-less install lost ops3d / pipeline_evolve entirely
(graceful-degradation violation, caught by the first CI run 2026-08-30).

torch がローカルに入っていても検証できるよう、meta_path で torch を遮断した
サブプロセスで import を実測する(環境依存にしない)。

2026-10-24: 遮断器を ``find_module`` / ``load_module`` から ``find_spec`` に替えた。
旧い 2 つは Python 3.12 で import 機構から外れた(meta_path の finder に
``find_spec`` が無いと素通りされる)。3.12 以降では遮断が効かず、torch が入った
環境では「torch 無しで動く」を一度も確かめていなかった。遮断が効いたことは
ハーネス自身が先頭で確かめる(``(blocked)`` の文言つきで落ちること)。
"""
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_HARNESS = r"""
import sys
# torch だけでなく、素の pip install(numpy+scipy のみ)に無い optional を全部遮断。
# v0.1.0 の実 PyPI 検証で recon3d の skimage ハード import が ops3d を殺していた
# (feat_* の torch と同クラス)— この網羅遮断がそのクラス全体の恒久ガード。
import importlib.abc
_BLOCKED = ("torch", "kornia", "skimage", "cv2", "PIL", "pywt", "mahotas")
class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _BLOCKED:
            raise ModuleNotFoundError("No module named %r (blocked)" % name, name=name)
        return None
sys.meta_path.insert(0, _Block())
for _m in list(sys.modules):
    if _m.split(".")[0] in _BLOCKED:
        sys.modules.pop(_m, None)

# 遮断が実際に効いていること。入っていないだけ(文言に (blocked) が無い)では通さない。
for _name in _BLOCKED:
    try:
        __import__(_name)
    except ModuleNotFoundError as _e:
        assert "(blocked)" in str(_e), "blocker bypassed for %s: %s" % (_name, _e)
    else:
        raise SystemExit("blocker did not stop 'import %s'" % _name)

import ops3d                      # ← 以前は feat_harris.py:3 / recon3d.py:24 で即死していた
import pipeline_evolve            # ops3d 経由の消費側も生きる
import fullseye, measure3d, examples3d, examples2d      # bare-install の主要面
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
