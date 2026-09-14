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
    # ★2026-09-14: この 13 本は 2026-09-05 から wheel に**入っていなかった**もので、
    #   py-modules へ足した結果ここに現れた。演算子としては `unified._3DGS_OPS` が
    #   `_lazy_call(モジュール名, 関数名)` で**文字列から**登録しているので、利用者には
    #   `fullseye.op.<名前>` 経由で届く。ここに残る 1〜6 本は各モジュールのデモ入口
    #   (`render_*_gif` など)で、op ではなく**絵を作る側**。だから内部専用に置く。
    #   —— 「配布から消えていた」を直すと「公開経路から見えない」が現れる、という
    #   二段構えだった([[feedback_registered_only_gates_miss_unregistered]])。
    "bin_pick": 1, "event_camera": 1, "focus_stack": 1, "fullseye_3dgs": 3,
    "gaits": 2, "gsplat_sugar": 3, "lidar_sim": 1, "pick_render": 1,
    "polar_cam": 1, "sensor_fusion": 1, "stereo_sim": 1, "walk_physics": 6,
    "world_render": 1,
}

#: **出すべきなのに出ていない**。ここは減らしていく側の台帳です。
#: 「実装はある・動く・テストもある、しかし利用者からは存在しない」もの。
#: 直したらこの表から**行を消す**こと(消し忘れは 2 番目の検査が落とします)。
_PENDING_EXPOSURE: dict[str, int] = {
    # ★2026-09-15: 33 行すべてが公開経路(fullseye.<名前> / .ledger / .op)に届くように
    #   なっており、2 番目の検査が「この表から行を消すこと」と 33 件を挙げた。
    #   消した 33: transforms / mosaic / fit_transform / tools_geom / matrix / shapematch /
    #   objmodel3d / matching3d / matching / calib / caltab / calibration3d / contours_xld /
    #   contours_xld2 / image_channels / filters_freq / filters_flow / regions_setops /
    #   regions_gen / region_morph / morph_minkowski / segmentation / image_gen /
    #   image_paint / misc_vision / imgops_nary / scattered / inspection / pipeline3d /
    #   watershed3d / mesh_decimate / sample_data / scale。
    #   表は空でも残す —— 「出すべきなのに出ていない」ものが次に現れたときの器。
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
#: 2026-09-13: 1229 -> 1231。opsflyvision 台帳の内部 API(get/call/info/missing)を
#: 足したぶん(既存の各 ops<族> 台帳と同じ機構で、`fs.ledger` から op 自体は引ける)。
#: 2026-09-14: 1231 -> 1235。opsspc 台帳の内部 API(_build/list_ops/categories/get/call/
#: info/missing の非公開分)と spc.py の入力バリデータ(_as_float_array/_as_1d)。op 自身
#: (spc_xbar_r/spc_cusum/spc_capability/spc_hotelling_t2)は typed_catalog と api から引ける。
_HIDDEN_FUNCTIONS_TODAY = 1235


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
