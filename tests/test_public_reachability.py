# -*- coding: utf-8 -*-
"""配布しているのに**公開経路のどこからも呼べない**モジュールを数える門。

2026-09-06 に見つかった穴がこの門の理由です。`fourierdesc`(楕円フーリエ
記述子 7 本)・`imagemorph`(TPS/区分アフィンのワープ 6 本)・`measuring1d`
(1-D 測定のサブピクセルエッジ 6 本)・`scale`(大画像のタイル処理 6 本)は、

* wheel に同梱されていて(`pyproject.toml` の ``py-modules``)、
* 専用テストがあって **7/7・6/6・6/6・6/6 が実際に呼ばれていて**、
* それでも ``fullseye.<名前>`` にも ``fullseye.ledger.<名前>`` にも
  ``fullseye.op.<名前>`` にも一つも出ていませんでした。

つまり「実装した・テストも書いた」で終わっていて、**利用者から見ると存在
しない**。ギャラリー生成器と tests だけが呼んでいたので、どの検査も緑のまま
気づけませんでした。これは
``docs/ops`` の drift 検査でも op→example のカバレッジでも捕まりません ——
それらは**すでに登録された op** を数える門で、登録されなかったものは
最初から母集団に入らないからです。

## この門が言うこと

1. 下の台帳に**載っていない**モジュールが不可視になったら落ちる(新規の
   取りこぼしを止める)。
2. 台帳に載っているのに**実は届くようになっていた**ら落ちる(直したら
   台帳から消す、を強制する。台帳が古い言い訳の置き場にならないように)。
3. 台帳に載っているモジュールの**不可視な関数が増えた**ら落ちる。既に
   隠れている場所へ新しい関数を足すのが、いちばん起きやすい事故なので。

## 台帳の読み方

数字は「そのモジュールで公開経路から呼べない関数の本数」です。0 にする
必要はありません —— **内部専用だと宣言したもの**(GUI・生成器・ベンチ・
backend の実装側)はそのまま置いておきます。**利用者に出すべきなのに
出ていないもの**は `_PENDING_EXPOSURE` に分けてあり、こちらは減らして
いく側です。隠さず並べて、埋まった順に外します。
"""
from __future__ import annotations

import importlib
import io
import os
import re
import warnings

import pytest

from conftest import requires_full_registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#: **内部専用**。利用者に出すつもりが無いモジュール。GUI(`studio`)、
#: コード生成器・スクレイパ・ベンチ、`backends_*` の実装側(op 名と関数名が
#: 違うので名前照合では届かないが、op 経由では毎回走っている)、例の登録簿。
#: 数字は不可視な関数の本数で、増減しても意図的なら書き換えてよい。
_INTERNAL = {
    "accel_bridge": 9, "accel_match": 6, "accel_vol": 3, "accuracy_bench": 4,
    "algo_codegen": 4, "algo_difftest": 8, "backends": 4, "backends_auto": 2,
    "backends_color": 3, "backends_cv2b": 1, "backends_dl": 3, "backends_extra": 1,
    "backends_halcon_ext": 1, "backends_kornia": 1, "backends_macro": 1,
    "backends_pil": 1, "backends_r3": 1, "backends_scipy": 1, "backends_ski2": 1,
    "backends_typed": 1, "baseline": 4, "bench": 1, "catalog": 2, "codegen": 2,
    "difftest": 1, "dispositions": 3, "evis_fullseye_bridge": 4, "evolve": 2,
    "examples2d": 11, "examples3d": 11, "fast": 31, "final_genuine": 20,
    "final_genuine2": 9, "fscript": 29, "fsruntime": 8, "g1_policy_bridge": 5,
    "gi_render": 2, "graph": 3, "graph_seed": 2, "halcon_coverage": 9,
    "halcon_scrape": 9, "honest_summary": 1, "imgevolve": 14, "lib_coverage": 3,
    "param_specs": 10, "parity": 2, "problems": 2, "recipes": 4, "references": 2,
    "report": 1, "robust": 3, "samples": 2, "shapematch_gpu": 3, "sim_source": 9,
    "studio": 65, "sweep": 1, "typed_catalog": 1, "verify_auto": 2,
}

#: **出すべきなのに出ていない**。ここは減らしていく側の台帳です。
#: 「実装はある・動く・テストもある、しかし利用者からは存在しない」もの。
#: 直したらこの表から**行を消す**こと(消し忘れは 2 番目の検査が落とします)。
_PENDING_EXPOSURE = {
    # --- 2-D 幾何とパノラマ。射影変換の推定・合成・束調整が一式ある ---
    "transforms": 50,       # hom_mat2d_* の代数一式 + projective_trans_point_2d
    "mosaic": 15,           # gen_projective_mosaic / bundle_adjust_mosaic / RANSAC 対応付け
    "fit_transform": 5,     # hom_vector_to_proj_hom_mat2d(4 点以上→H)/ Umeyama
    "tools_geom": 14,
    "matrix": 33,
    # --- 形状マッチング・3-D モデル照合 ---
    "shapematch": 39,
    "objmodel3d": 35,
    "matching3d": 12,
    "matching": 4,
    # --- カメラ校正(facade に出ていないのは既知の宿題) ---
    "calib": 12,
    "caltab": 10,
    "calibration3d": 4,
    # --- 2-D の基本演算。領域・輪郭・チャネル・周波数 ---
    "contours_xld": 16,
    "contours_xld2": 20,
    "image_channels": 22,
    "filters_freq": 18,
    "filters_flow": 10,
    "regions_setops": 17,
    "regions_gen": 5,
    "region_morph": 3,
    "morph_minkowski": 6,
    "segmentation": 9,
    "image_gen": 11,
    "image_paint": 9,
    "misc_vision": 13,
    "imgops_nary": 4,
    "scattered": 6,
    "inspection": 3,
    "pipeline3d": 6,
    "watershed3d": 3,
    "mesh_decimate": 1,
    "metrology": 8,
    "sample_data": 7,       # CLI からは届くが Python API からは届かない
    # --- 2026-09-06 に見つけた 4 件。テストが 100% 通っているのに不可視 ---
    "fourierdesc": 7,
    "imagemorph": 6,
    "measuring1d": 6,
    "scale": 6,
}

_LEDGER = dict(_INTERNAL)
_LEDGER.update(_PENDING_EXPOSURE)


def _shipped_modules():
    """``pyproject.toml`` の ``py-modules`` —— **配布されるもの**だけを数える。

    リポジトリの `*.py` を走査すると spikes/ や tools/ まで拾ってしまう。
    門は「利用者の手元に届くもの」の上に立てる。
    """
    src = io.open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    body = re.search(r"py-modules\s*=\s*\[(.*?)\]", src, re.S)
    assert body, "pyproject.toml に py-modules が無い"
    return re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', body.group(1))


def _public_names():
    """公開経路 3 つの名前を集める(facade / 型つき台帳 / 進化する 2-D op)。"""
    import fullseye as fs
    import ops

    names = {n for n in dir(fs) if not n.startswith("_")}
    names |= {n for n in dir(fs.ledger) if not n.startswith("_")}
    names |= {o.name for o in ops.REGISTRY}
    return names


def _invisible_counts():
    """モジュール名 -> 公開経路から呼べない関数の本数(1 本以上のものだけ)。"""
    public = _public_names()
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in _shipped_modules():
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue                      # optional 依存で入らないものは数えない
            fns = [n for n in dir(mod)
                   if not n.startswith("_")
                   and callable(getattr(mod, n))
                   and getattr(getattr(mod, n), "__module__", "") == name]
            if not fns:
                continue
            hidden = [n for n in fns if n not in public]
            if len(hidden) == len(fns):       # 1 本も届かないモジュールだけを問題にする
                out[name] = len(hidden)
    return out


def test_no_new_module_becomes_invisible():
    """台帳に無いモジュールが丸ごと不可視になっていないこと。"""
    requires_full_registry()
    unlisted = sorted(set(_invisible_counts()) - set(_LEDGER))
    assert not unlisted, (
        "公開経路(fullseye.<名前> / .ledger / .op)のどこからも呼べないモジュールが "
        "増えた: " + ", ".join(unlisted) + "\n"
        "  利用者に出すなら台帳(ledger)へ登録する。内部専用なら "
        "tests/test_public_reachability.py の _INTERNAL に理由つきで足す。"
    )


def test_pending_exposure_shrinks_when_fixed():
    """出せたモジュールは台帳から消えていること(言い訳の置き場にしない)。"""
    requires_full_registry()
    now = _invisible_counts()
    fixed = sorted(n for n in _PENDING_EXPOSURE if n not in now)
    assert not fixed, (
        "公開経路から届くようになったのに _PENDING_EXPOSURE に残っている: "
        + ", ".join(fixed) + "  —— この表から行を消すこと。"
    )


#: 「1 本も届かない島」ではなく**部分的に隠れている**分の総数。2026-09-06 の実測で
#: 配布関数 2865 本のうち 1229 本(42.9%)が公開経路のどこからも呼べず、うち 425 本は
#: 「一部だけ出ている」モジュールの中に埋もれていた(`reconstruction` 28/29、
#: `geometry2d` 21/22、`filters_arith` 16/20 —— 名前が 1 つ出ているせいで
#: 島の検査には掛からない)。この総数が増えないことだけを見張り、減らす作業は
#: 上の `_PENDING_EXPOSURE` と一緒に進める。
_HIDDEN_FUNCTIONS_TODAY = 1229


def _hidden_total():
    public = _public_names()
    total = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in _shipped_modules():
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            total += sum(1 for n in dir(mod)
                         if not n.startswith("_")
                         and callable(getattr(mod, n))
                         and getattr(getattr(mod, n), "__module__", "") == name
                         and n not in public)
    return total


def test_hidden_function_total_does_not_grow():
    """半分だけ見えているモジュールも含めた総数のラチェット。

    島の検査(上の 3 本)は「1 本も届かない」モジュールしか見ない。名前が
    1 つでも出ていると素通しになるので、総数でも押さえる。
    """
    requires_full_registry()
    now = _hidden_total()
    assert now <= _HIDDEN_FUNCTIONS_TODAY, (
        "公開経路から呼べない関数が %d -> %d に増えた。新しく足した関数は "
        "facade / 型つき台帳 / 2-D op のどれかに載せること。"
        % (_HIDDEN_FUNCTIONS_TODAY, now)
    )


@pytest.mark.parametrize("name", sorted(_LEDGER))
def test_invisible_function_count_does_not_grow(name):
    """既に隠れている場所へ関数を足さないこと —— いちばん起きやすい事故。"""
    requires_full_registry()
    now = _invisible_counts().get(name)
    if now is None:
        pytest.skip("%s は届くようになった(別の検査が台帳の掃除を要求する)" % name)
    assert now <= _LEDGER[name], (
        "%s の不可視な関数が %d -> %d に増えた。公開経路に出すか、"
        "意図して内部に置くなら台帳の数字を更新すること。" % (name, _LEDGER[name], now)
    )
