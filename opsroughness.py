# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsroughness —— 表面粗さの統一レジストリ。

実体は ``roughness.py``(6 op / 3 カテゴリ。numpy と scipy.ndimage のみ)。

## なぜ足したか(2026-09-06)

表面粗さの PoC(``examples/poc_surface_roughness.py``)が「**粗さパラメータの op が
fullseye に 1 つも無い**」と実測つきで報告した。Sa/Sq/Sz も Ra/Rq/Rz も無く、
帯域を切るガウスフィルタも、PSD から真値つきの高さ場を作る合成器も無い。
既存の ``roughness_map`` は局所標準偏差の**画像**であってパラメータではなく、
``opsprofile`` の 12 op は翼型断面専用で無関係だった。

## この族の 3 つの約束

1. **真値を作れる**。``surface_synth_psd`` が解析 Sq を一緒に返す(実測で
   ``|std/analytic - 1|`` 最大 2.2e-16)。これが無いと粗さ検査に真値を用意できない。
2. **帯域未処理を静かに通さない**。``surface_params`` は既定
   ``assume_filtered=False`` で「うねりを含んで見える」配列を fail-closed で拒否する
   —— 生の rms を Sq と呼ぶと実測で **20.3 倍**(+1931 %)間違う。
3. **規約を引数で明示する**。``surface_psd`` の ``kind="areal"|"radial"`` は、
   既存の ``radial_power_spectrum`` が docstring に規約を書いていなかった反省。

**登録面は 6 つ**: この台帳 / ``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog``
(RESULT_ADAPTERS と PARAM_HINTS)/ ``chain_fuzz.TYPE_CHECKS`` の述語 /
``opassist._LEDGERS`` / ``pyproject`` の py-modules。
"""
import roughness

_MOD = {"roughness": roughness}

# --------------------------------------------------------------------------- #
# 型語彙: **新語を 1 つも作らない**。その判断の記録。
# --------------------------------------------------------------------------- #
# 高さ場は既存の ``depth``((H,W) の高さ格子)がそのまま当たる。``image2d`` でも
# 述語は通る(どちらも ndim==2)が、意味は高さなので ``depth`` を採る。
#
# パラメータの辞書は ``table``(list か dict)。``metrics`` にしなかったのは、
# あちらの述語が "contract" キーを要求する別の約束を持っているため。
#
# PSD の返り ``(q, C)`` は等長の 1-D 2 本なので、adapter で ``np.c_[q, C]`` に
# するまでもなく **``pairs``**((N,2))の述語をそのまま満たす形へ寄せた。
#
# **分けなかった理由**: この族には「粗さ成分」と「うねり成分」という 2 つの
# 高さ場が出るが、取り違えても**例外ではなく、もっともらしく間違った数値**が
# 出る……という条件は満たすものの、両者は同じ単位・同じ格子で、後段の op は
# どちらを渡されても正しく動く(``surface_params`` はうねりを含む側を
# fail-closed で拒否するので、そこで止まる)。**門が別に立っている型は
# 分けない** —— 型語彙を増やすほどプールが痩せて未実行が増える。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 合成 —— 真値を持つ粗さ面。族の入口(これが無いとプールが空になる)。
    "synth": [
        ("surface_synth_psd", "roughness", [], "depth"),
    ],
    # 前処理 —— 形状を除き、帯域を切る。粗さを測る前に必ず通る 2 段。
    "prepare": [
        ("surface_form_remove", "roughness", ["depth"], "depth"),
        ("surface_filter", "roughness", ["depth"], "depth"),
    ],
    # 計測 —— パラメータとスペクトル。
    "measure": [
        ("surface_params", "roughness", ["depth"], "table"),
        ("profile_params", "roughness", ["signal"], "table"),
        ("surface_psd", "roughness", ["depth"], "pairs"),
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


OPSROUGHNESS = _build()

#: 宣言 out 型と素の返りの橋渡し。この族は **3 op がタプルを返す**。
#: 旗で返り型が変える設計にはしていない(常にタプル)ので、adapter は先頭を
#: 取るだけで済む。捨てられる 2 番目(``coeffs`` / ``waviness`` /
#: ``sq_analytic``)は ``fullseye.ledger.<名前>.raw`` で取れる。
RESULT_ADAPTERS = {
    "surface_synth_psd": lambda r: r[0],      # (z, sq_analytic)
    "surface_form_remove": lambda r: r[0],    # (residual, coeffs)
    "surface_filter": lambda r: r[0],         # (roughness, waviness)
    "surface_psd": lambda r: __import__("numpy").c_[r[0], r[1]],   # (q, C) -> (N,2)
}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSROUGHNESS.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSROUGHNESS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSROUGHNESS[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSROUGHNESS[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSROUGHNESS.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsroughness: %d ops / %d categories"
          % (len(OPSROUGHNESS), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-9s %s" % (cat, ", ".join(list_ops(cat))))
