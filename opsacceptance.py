# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsacceptance —— 光学式 3D センサの(仮想)受入試験の台帳。

Typed registry of the optical 3-D sensor acceptance-test family (``acceptance3d.py``, 8 ops /
4 categories), following the *ideas* of VDI/VDE 2634 Part 2/3 and ISO 10360-13 (no conformance claim:
the normative texts are not reproduced; definitions come from the open literature cited in the module).

呼び出し例 / Example::

    import fullseye as fs

    layout = fs.ledger.acceptance_layout()                       # 球 1・ダンベル 7 姿勢・平面 7 姿勢
    ideal = fs.ledger.virtual_acceptance_test({"kind": "ideal"}, layout)
    print("ideal max |SD| < 1e-6 mm:", max(abs(v) for v in ideal["sd"]) < 1e-6)
    scaled = fs.ledger.virtual_acceptance_test({"kind": "ideal", "range_scale": 1.001}, layout)
    print("SD = 0.001 L: %.4f mm (L = %.1f mm)" % (scaled["sd"][0], layout["bar_length_mm"]))

出力は ``ideal max |SD| < 1e-6 mm: True`` と ``SD = 0.001 L: 0.3144 mm (L = 314.4 mm)``(尺度の誤差 s は
SD に ``(s − 1)·L`` で**厳密に**出る —— ``tests/test_acceptance3d.py`` が確かめる)。

## なぜこの族か(2026-11-03)

監査(``completeness_audit_2026_11_03``)で、比較相手(HALCON・OpenCV・Open3D・PCL)の誰も受入試験の手順を
op として持っていないこと、Fullseye のソース全体でも ``2634|10360|probing error|sphere spacing`` が 0 件だった
ことを数えた。当てはめ(球・平面)は前からあるが、**受入の手順として束ねていなかった**。この族は
(1) 実機の点群にもシミュレーションの点群にも同じ評価 op を掛け、(2) シミュレーションのセンサで「買う前に」
受入試験を回し、(3) 誤差の要因のどれが合否を決めるかを数える —— の 3 段。

## 型語彙: **新語なし**

* ``points`` —— 試験体の点群 (N, 3)(センサ座標、mm)。評価 op の入力で、:func:`acceptance_scan` の出力。
* ``table`` —— 配置・センサの記述・評価の結果・MPE・誤差の要因の dict。
  センサにも試験体にも新しい型の語を与えなかった: 族の外に消費者がいない(判断の基準は opscalib と同じ)。
"""
import acceptance3d

_MOD = {"acceptance3d": acceptance3d}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 試験体の配置 —— 族の入口。入力なし(体積と試験体の寸法は引数)。
    "layout": [
        ("acceptance_layout", "acceptance3d", [], "table"),
    ],
    # 評価量 —— 実機の点群にもシミュレーションの点群にも同じ op。
    "evaluate": [
        ("sphere_probing_error", "acceptance3d", ["points"], "table"),
        ("sphere_spacing_error", "acceptance3d", ["points", "points"], "table"),
        ("plane_flatness_error", "acceptance3d", ["points"], "table"),
        ("acceptance_verdict", "acceptance3d", ["table", "table"], "table"),
    ],
    # シミュレーションのセンサで撮る —— 真値は場面の解析解。
    "simulate": [
        ("acceptance_scan", "acceptance3d", ["table", "table"], "points"),
        ("virtual_acceptance_test", "acceptance3d", ["table"], "table"),
    ],
    # 誤差の予算 —— どの要因が合否を決めるか。
    "budget": [
        ("acceptance_error_budget", "acceptance3d", ["table", "table", "table"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSACCEPTANCE = _build()

#: 宣言 out 型と素の返りの橋渡し。**空 —— 意図的に**(どの op も宣言どおりの型を素で返す)。
RESULT_ADAPTERS: dict = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSACCEPTANCE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSACCEPTANCE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSACCEPTANCE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSACCEPTANCE[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSACCEPTANCE.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsacceptance: %d ops / %d categories" % (len(OPSACCEPTANCE), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-10s %s" % (cat, ", ".join(list_ops(cat))))
