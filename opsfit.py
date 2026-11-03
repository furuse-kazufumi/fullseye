"""Typed registry for rotation-invariant and subpixel fitting operations."""
import filters_freq
import measure

_MOD = {"measure": measure, "filters_freq": filters_freq}

_CATALOG = {
    "fit": [
        ("fit_circle_geometric", "measure", ["keypoints"], "table"),
        ("fit_curve_principal_axis", "measure", ["keypoints"], "table"),
    ],
    "registration": [
        ("phase_correlation_shift", "filters_freq", ["image2d", "image2d"], "table"),
    ],
}


def _build():
    out = {}
    for category, rows in _CATALOG.items():
        for name, module, inputs, output in rows:
            out[name] = {"func": getattr(_MOD[module], name), "module": module,
                         "in": inputs, "out": output, "category": category,
                         "streamable": False}
    return out


OPSFIT = _build()
RESULT_ADAPTERS = {}


def list_ops(category=None):
    return sorted(n for n, m in OPSFIT.items()
                  if category is None or m["category"] == category)


def categories():
    """分類の一覧。"""
    return sorted({m["category"] for m in OPSFIT.values()})


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSFIT[name]["func"]


# ★2026-11-03: この台帳だけ ``call`` / ``get`` / ``info`` が無く、``fs.ledger.fit_circle_geometric`` /
#   ``phase_correlation_shift`` などが ``AttributeError: module 'opsfit' has no attribute 'call'`` で
#   落ちていた(op ノートの「呼び出し」行が案内する入口そのもの)。レシピの e2e が見つけた。
#   他の台帳(opsaoi など)と同じ形にそろえ、tests/test_ledger_entry_points_2026_11_03.py で全台帳を見る。
def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSFIT[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSFIT[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSFIT.items() if m["func"] is None]
