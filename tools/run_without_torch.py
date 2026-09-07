"""torch が無い環境(CI の py3.10 / 3.12)を手元で再現して 1 本走らせる。

``importlib.util.find_spec("torch")`` を None にし(= torch_lazy.HAS_TORCH が False)、
meta_path でも実 import を塞ぐ。これで「手元には torch があるから気づけない」を潰す。
"""
import importlib.util
import runpy
import sys

_orig = importlib.util.find_spec


def _fake(name, *a, **k):
    if name == "torch" or name.startswith("torch."):
        return None
    return _orig(name, *a, **k)


importlib.util.find_spec = _fake


class _Block:
    def find_spec(self, name, path=None, target=None):
        if name == "torch" or name.startswith("torch."):
            raise ModuleNotFoundError("torch is blocked for this run")
        return None


sys.meta_path.insert(0, _Block())
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
