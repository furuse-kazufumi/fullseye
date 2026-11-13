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
    "accel_bridge": 9, "accel_vol": 3,
    # 2026-11-03 device="auto" の判断(損益分岐の表・空き VRAM・段ごとの経路)。利用者の入口は
    # fullseye.explain_device / resolve_device で、この部品は api の内側からだけ呼ぶ。
    "device_policy": 6,
    "algo_codegen": 4, "algo_difftest": 8, "backends": 4, "backends_auto": 2,
    "backends_color": 3, "backends_cv2b": 1, "backends_dl": 3, "backends_extra": 1,
    "backends_halcon_ext": 1, "backends_kornia": 1, "backends_macro": 1,
    "backends_pil": 1, "backends_r3": 1, "backends_scipy": 1, "backends_ski2": 1,
    "backends_typed": 1, "baseline": 4, "bench": 1, "catalog": 2, "codegen": 2,
    "difftest": 1, "dispositions": 3, "evolve": 2,
    "examples2d": 11, "examples3d": 11, "fast": 31,
    "fscript": 29, "fsruntime": 8,
    "gi_render": 2, "graph": 3, "graph_seed": 2, "halcon_coverage": 10,
    "halcon_scrape": 9, "honest_summary": 1, "imgevolve": 14, "lib_coverage": 3,
    # 2026-11-12 safe_xml(1.1.1): XML を DOCTYPE・実体の増幅なしで読む内部の層 4 本(UnsafeXMLError /
    # safe_xml_parse / safe_xml_parse_zip_member / safe_xml_iterparse)。利用者は各形式の読み込み(CommonRoad・OSM・
    # OME-TIFF・SVG・3MF・CityGML …)から使う。公開の op にするかは 1.2.0 の定義ファイルの層で決める。
    "safe_xml": 6,
    "param_specs": 11, "parity": 2, "problems": 2, "recipes": 4, "references": 2,
    "report": 1, "robust": 3, "samples": 2, "shapematch_gpu": 3,
    # GPU 第 4 便: 一括経路。op でなく、raytrace / optics と同じ定義を (M, W, R) で計算する下回りの部品。
    "polar_gpu": 13,   # 2026-11-04 統合 GPU: 第 4 便の後半の commit で 12 → 13(実測)
    # studio 2026-10-03 +10: 結果プレビュー・台帳 op の実行窓・エディタへ繋ぐ部品(GUI の内側)
    # studio 2026-10-19 +4: 妥当性の判定 assess_validity と入力参照 input_reference / resolve_input_ref / file_sha256(GUI の内側の部品。テストが直接呼ぶ)
    # studio_search / studio_errors 2026-10-20: Studio の論理層(Qt 非依存)。UI への配線は次の片。
    #   search 6 本(current_sort_of / search_grouped / search_zero_results_help / canonical_sort / clear_caches / nearest_op_names)
    #   errors 3 本(explain_failure / format_failure / localize)。studio と同じ「GUI の内側の部品」で、テストが直接呼ぶ。
    # studio / studio_search 2026-11-13(初回起動の点検の直し、fix/studio-firstrun-2026-11-13): studio +13(op_insertable /
    #   not_insertable_text / starter_ops / entry_sort_of / op_is_ledger / sample_menu_order / format_pixel_readout /
    #   knob_dead_measured / knob_use / knob_role_text / help_plain_markup / plain_summary / help_query_target)、
    #   studio_search +1(samples_for)。どれも GUI の内側の部品で、試験が直接呼ぶ。
    "studio": 103, "studio_errors": 3, "studio_search": 8, "studio_roundtrip": 5, "studio_batch": 6, "studio_display": 8, "studio_layout": 6, "sweep": 1, "typed_catalog": 1, "verify_auto": 2,
    # ★2026-09-14: この 13 本は 2026-09-05 から wheel に**入っていなかった**もので、
    #   py-modules へ足した結果ここに現れた。演算子としては `unified._3DGS_OPS` が
    #   `_lazy_call(モジュール名, 関数名)` で**文字列から**登録しているので、利用者には
    #   `fullseye.vision.gsplat.<名前>` 経由で届く(2026-10-02 訂正: `fullseye.op.<名前>` は存在しない。
    #   unified registry を公開経路として数えたら 17 モジュールが島でなくなり行を消した)。
    #   ここに残る 1〜6 本は各モジュールのデモ入口(`render_*_gif` など)で、op ではなく**絵を作る側**。だから内部専用に置く。
    #   —— 「配布から消えていた」を直すと「公開経路から見えない」が現れる、という
    #   二段構えだった([[feedback_registered_only_gates_miss_unregistered]])。
    "fullseye_3dgs": 3, "gaits": 2,
    # ★2026-10-02: py-modules の数え漏れ(68 → 408 本)と facade 経路の数え忘れを直して初めて見えた 9 本。
    #   内部の道具(CLI・ヘルプ書庫・n-ary の組立て・Studio の索引・標本データの取得・大画像の実行補助)、
    #   api が別名で包むもの(mesh_decimate → mesh_decimate_preserving)、fs.<module>.<fn> でだけ届くもの
    #   (pipeline3d の合成 op 6 本 —— 2026-10-02 に fs.<名前> から出して行を消した)。
    #   (watershed3d の 3 本は 2026-10-02 に台帳 opssegmentation の watershed3d へ載せて行を消した。)
    "gsplat_cli": 2, "helpstore": 4, "imgops_nary": 4, "mesh_decimate": 1, "opsearch": 2,
    "sample_data": 7, "scale": 6,
    # ★2026-11-03: Reed-Solomon(GF(256) の表・符号化・復号)は記号の読み取りの族の内部部品。
    #   利用者は qr_* / dm_* / grade_datacode2d の返す訂正語数として使う(体そのものは op にしない)。
    "symrs": 5,
    # ★2026-11-04(統合 GPU): GPU 第 2・3 便(#240)の計算核の継ぎ目。accel_seam は contextvars で核だけを差し替える
    #   部品(kernel / use)、accel_typed は型付き op の GPU 経路の入口 call / call_candidate と torch の核 k_*(実測で計 14 本)。
    #   利用者は各 op の device 引数(既定 cpu)から使い、核そのものは op にしない。第 2・3 便のブランチは
    #   ここに書いていなかった(統合で門が赤になって分かった)。
    "accel_seam": 2, "accel_typed": 14,
    # ★2026-11-04(統合 GPU): 第 5 便の accel_label(連結成分のラベル付けと領域ごとの集計の torch 経路、label / table)。
    #   accel が import する核で、利用者は領域解析の op の device 引数から使う。
    "accel_label": 2,
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
    # ★2026-10-02: コメント行の ``[[feedback_...]]`` で非貪欲の ``\]`` が止まり、py-modules 407 本のうち
    #   68 本しか数えていなかった(339 本が門に映らない)。コメントを剥いでから囲みを取る。
    src = re.sub(r"#.*", "", src)
    body = re.search(r"py-modules\s*=\s*\[(.*?)\]", src, re.S)
    assert body, "pyproject.toml に py-modules が無い"
    names = re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', body.group(1))
    assert len(names) > 300, "py-modules を途中で切っている: %d 本" % len(names)
    return names


#: ★2026-10-07: optional 依存が無いと import できない出荷モジュール ``{module: 許す欠落依存}``。
#: 以前は ``except Exception: continue`` で**どんな import 失敗も**母数から黙って外していた ——
#: 壊れたモジュールは「不可視の関数」の数にも島の検査にも入らず、ラチェットはむしろ緑に寄る。
#: ここに無いモジュールの import 失敗、ここにあっても別の理由の失敗は赤。
OPTIONAL_IMPORT_MODULES = {
    "gsplat_train_native": frozenset({"gsplat", "torch", "PIL"}),
    "gsplat_animate": frozenset({"gsplat", "torch", "PIL", "mujoco"}),
}


def _import_shipped(name):
    """出荷モジュールを import する。許された optional 依存の欠落だけ ``None``、他は赤。"""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as e:
        missing = (e.name or "").split(".")[0]
        if missing in OPTIONAL_IMPORT_MODULES.get(name, ()):
            return None
        raise AssertionError(
            "出荷モジュール %r が import できない(%s)。optional 依存なら "
            "OPTIONAL_IMPORT_MODULES に理由つきで足す" % (name, e)) from e
    except Exception as e:                                       # noqa: BLE001
        raise AssertionError("出荷モジュール %r の import が失敗した: %s: %s"
                             % (name, type(e).__name__, e)) from e


def _public_names():
    """公開経路 3 つの名前を集める(facade / 型つき台帳 / 進化する 2-D op)。"""
    import fullseye as fs
    import ops

    names = {n for n in dir(fs) if not n.startswith("_")}
    names |= {n for n in dir(fs.ledger) if not n.startswith("_")}
    names |= {o.name for o in ops.REGISTRY}
    # ★2026-10-02: 4 つ目の公開経路 = 知覚 facade(fullseye.vision.<群>.<関数>、halcon_facade_map.json の
    #   "module.func" が実体)。HALCON 章の実装(segmentation.py 等)はここからだけ届いていた。
    #   py-modules の数え漏れ(68 → 408 本)を直した途端に 35 モジュールが「見えない」と出たが、
    #   その多くは facade 経由で届く。利用者が呼べる経路は全部数える。
    import json
    with io.open(os.path.join(ROOT, "fullseye", "data", "halcon_facade_map.json"), encoding="utf-8") as f:
        fmap = json.load(f)
    names |= {v.rpartition(".")[2] for k, v in fmap.items() if not k.startswith("_") and isinstance(v, str)}
    # ★2026-10-02: 5 つ目の公開経路 = unified registry(``fs.vision.<名前空間>.<op>``)。3DGS などの op は
    #   文字列 "module.func" から ``_lazy_call`` で登録され、facade map にも台帳にも名前が出ない
    #   (sugar_mesh・tsdf_mesh・route_planning 等)。"module.func" 形の ``module`` 欄だけを数える
    #   (``fs.apply('x')`` のような呼び出し式は関数名ではない)。
    reg = fs.vision._ensure()
    uops = reg._ops.values() if isinstance(reg._ops, dict) else reg._ops
    unified = {u.module.rpartition(".")[2] for u in uops
               if isinstance(u.module, str) and re.fullmatch(r"[A-Za-z_][\w.]*", u.module)}
    assert len(unified) > 100, "unified registry を数え損ねている: %d" % len(unified)
    names |= unified
    return names


def _invisible_counts():
    """モジュール名 -> 公開経路から呼べない関数の本数(1 本以上のものだけ)。"""
    public = _public_names()
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in _shipped_modules():
            mod = _import_shipped(name)
            if mod is None:
                continue                      # 許された optional 依存の欠落だけ数えない
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

# 2026-10-22 Studio 第8片: studio_batch のQt非依存部品6本で実測 892 → 898。
# 2026-10-22 Studio 第9片: studio_display のQt非依存部品6本を内部部品として登録。実測 898 → 904。
# 2026-10-22 Studio 第9片修正: range_info / mark_nonfinite の2本を追加。実測 904 → 906。
# 2026-10-23 opsaoi 台帳(AOI の前段 3 op): 台帳の内部 API(list_ops/categories/get/call/info/missing
#   のうち公開経路に出ない分)で実測 912 → 916。op 自身は fs.ledger と typed_catalog から引ける。
# 2026-10-23 opscalib 台帳(カメラ校正 21 op): 台帳の内部 API 4 本で実測 916 → 920。21 op 自身は
#   fs.ledger から引けるようになった(以前は fs.<名前> の camera_calibration 1 本だけ)。
# 2026-10-25 fail-soft 監査: backend_safe.missing_dependency / require_dependency(各 backend が使う fail-closed の
#   入口 2 本)、backends_tomo.sart_np(skimage 無しの近似を**別名で**残したもの、登録 op の答えにはしない)、
#   numpy_twins の 19 本(scikit-image と bit 一致する双子。利用者は op 経由で使う —— 双子そのものは公開経路に
#   載せない。正本は scikit-image で、同名で出すと「fullseye の API」に見える)。実測 920 → 942。
# 2026-10-23 フーリエ・タイコグラフィの例外の型 fourierptycho.FPNotConvergedError(converge の NotConvergedError と同じ形、
#   6 op 本体は fs.ledger に載る)。実測 942 → 943。
# 2026-10-23 組紐の例外の型 braidpath.TriplePointError(射影の三重点で組紐語が決まらない —— ValueError の子、
#   12 op 本体は fs.ledger に載る)。実測 943 → 944。
# 2026-10-31 opsfileio 台帳(メモリ内 file I/O 14 op): 台帳の内部 API 4 本で実測 944 → 948。
#   op 自身は fs.ledger から引ける。
# 2026-11-03 opsacceptance 台帳(光学式 3D センサの仮想受入試験 8 op): 台帳の内部 API 4 本で実測 948 → 952。
#   op 自身は fs.ledger から引ける。
# 2026-11-03 opsmatchreg 台帳(照合と位置合わせ 12 op): 台帳の内部 API 4 本で実測 948 → 952。12 op 自身は
#   fs.ledger から、合成の道具 7 本(synthetic_scene / warp_homography / corner_error / condition_homography /
#   warp_parametric / synthesize_moving / smooth_test_field)は fs.<名前> から引ける。
# 2026-11-03 opssymbol 台帳(記号の読み取り 33 op): 台帳の内部 API 4 本、例外の型 3 本
#   (Barcode1DError / QRDecodeError / DMDecodeError、どれも ValueError の子)、symrs の 5 本(内部部品、
#   _INTERNAL)、symbol_scene(render_symbol の中身)・grade_letter(等級 → 文字)・zxing_available。
#   実測 948 → 963。33 op 自身は fs.ledger から引ける。
# 2026-11-04 統合(integrate/2026-11-04-families): 上の 3 台帳はどれも 948 から測っていたので、重ねると
#   948 + 4(opsacceptance)+ 4(opsmatchreg)+ 15(opssymbol)= 971。実測も 971(各ブランチで認めた増分の和で、新しい増分はない)。
# 2026-11-03 opsfit に台帳の内部 API 4 本(call / get / info / missing。f9743b1301)を足した: 実測 948 → 952。
#   fs.ledger.fit_circle_geometric / phase_correlation_shift が AttributeError で落ちていた修正で、他の台帳
#   (opscalib / opsfileio / opsmath / opsshape2d …)も同じ 4 本を公開経路に載せていない。op 自身は fs.ledger から引ける。
# 2026-11-04 統合に W2(opsfit の 4 本)を重ねた: 948 + 4(opsacceptance)+ 4(opsmatchreg)+ 15(opssymbol)
#   + 4(opsfit)= 975。実測も 975(各ブランチで認めた増分の和で、新しい増分はない)。
# 2026-11-02 CT の共通の核 tomography_gpu の内部部品 7 本(forward_project / adjoint_project / voxel_backproject /
#   filter_rows / parallel_slice_geometry / gpu_memory_peak_bytes / reset_gpu_memory_peak)で実測 948 → 955。利用者は
#   ctscan の 11 op と tomography の device 引数から使う(核そのものは公開経路に載せない)。
# 2026-11-04 統合 GPU(integrate/2026-11-04-gpu): 975(上の 4 台帳まで)+ 7(tomography_gpu、CT の第 8 便)
#   + 17(GPU 第 2・3 便 #240 の内部の核: accel.run_nary、accel_seam.kernel / use、accel_typed.call / call_candidate
#   と k_* 計 14 本。利用者は device 引数から使う。★第 2・3 便のブランチはこの上限を書き換えていなかった)= 999。実測も 999。
# 2026-11-02 GPU 第 4 便: 一括経路 lens_gpu / polar_gpu の下回りの部品(op でなく、raytrace / optics と同じ定義を
#   (M, W, R) で計算する)。実測 948 → 977。公開 op として載せる判断は次の便。
# 2026-11-04 統合 GPU: 999 + 35(第 4 便 lens_gpu 22・polar_gpu 13。ブランチの注記は 29 だが、その後の commit
#   21ba71f0bf / 959c474b26 で増えた分が数え直されていなかった)= 1034。実測も 1034。
# 2026-11-02 opsmv 台帳(工業用ビジョンの定番 47 op): 台帳の内部 API 4 本、除算モデルの 2 本
#   (distort_division / undistort_division、op の部品)、opassist.ledger_halcon_map。実測 948 → 955。
# 2026-11-04 統合 GPU: 1034 + 7(opsmv)= 1041。実測も 1041。
# 2026-11-02 gpu_shadow(機械的 GPU の影の層 10 本)。CuPy は任意依存で、入口は gpu_shadow.apply / run_allowed。実測 948 → 958。
# 2026-11-04 統合 GPU: 1041 + 11(gpu_shadow。ブランチの注記は 10 本、実測は 11 本 = GpuAutoError / ShadowImporter / Stats /
#   allowed_ops / available / get_shadow / resident_ops / run_allowed / shadow_fn / to_cpu / to_gpu)= 1052。実測も 1052。
# 2026-11-03 GPU 第 5 便: device_policy(auto の判断 6 本)・gpu_route(GPU 経路を決める唯一の関数と Route 型、
#   実行の入口の 9 本)・gpu_shadow の鎖の 2 本(pipeline_ops / run_chain)。利用者の入口は fullseye.explain_device
#   と fullseye_describe の gpu_paths で、部品そのものは公開経路に載せない。実測 958 → 975。
# 2026-11-04 統合 GPU: 1052 + 19(第 5 便 device_policy 6・gpu_route 9・gpu_shadow の鎖 2・accel_label 2。
#   ブランチの注記は 17、accel_label の 2 本が数えられていなかった)= 1071。実測も 1071。
# 2026-11-05 敵対的検証の統合(integrate/redteam-2026-11-05、claims D6/D7): 1071 + 2。
#   halcon_coverage.source_breakdown_text(成熟度の文面を出所別に組む補助。呼ぶのは honest_summary だけ)と
#   realdata.mark_read(PoC が「実データを読んだ」印を記録に足す補助。呼ぶのは data: real の例だけで、op ではない)。
#   同じ便の source_of / covered_by_source はモジュールの中でしか使わないので _ を付けて内部にした(数えない)。
# 2026-11-12 1.1.1(fix/studio-p-items-2026-11-12): 1073 + 11 = 1084。safe_xml 4(上の注記)・
#   param_specs.half_then_thirds_index 1(端の扱い・構造要素の形のつまみの対応。Studio と MCP の内側の部品)・
#   studio_search.staples_for 1(検索の「定番」の群。Studio の内側)・studio 3(lang_from_locale ほか、GUI の内側)・
#   backend_safe.which_outside_cwd 1・engine.check_pipeline_header 1。どれも GUI・読み込み・外部コマンド探しの内側の部品で、op ではない。実測 1084。
# 2026-11-13(Studio の初回起動の点検の直し): 1086 + 15 = 1101。studio 13・studio_search 1(上の _INTERNAL の注記)と、
#   studio.CLOSE_CONFIRM_HOOK 1(M10 の終了の確認の差し替え口。関数を指す名前なので総数に入る)。どれも GUI の内側の部品で、op ではない。
_HIDDEN_FUNCTIONS_TODAY = 1101


def _hidden_total():
    public = _public_names()
    total = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in _shipped_modules():
            mod = _import_shipped(name)
            if mod is None:
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


def test_internal_rows_are_still_islands():
    """_INTERNAL の行は「1 本も届かない島」であり続けること(届くようになったら行を消す)。

    2026-10-02: unified registry を公開経路に数えたら 17 行が島でなくなったが、下の検査は
    skip するだけで誰も掃除を要求していなかった(skip の文言は存在しない検査を指していた)。
    """
    requires_full_registry()
    now = _invisible_counts()
    stale = sorted(n for n in _INTERNAL if n not in now)
    assert not stale, (
        "公開経路から届くようになったのに _INTERNAL に残っている: " + ", ".join(stale)
        + "  —— この表から行を消すこと。"
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
