# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opassist — op ごとの入力補助(引数仕様・プリセット・入力の作り方・前提チェック)。

動機(2026-09-04、ユーザー「Studio の周りとか、入力補助機能とかもっと op 別にあったら
いいと思うよ」): `param_specs` は 2-D 側の **a, b という 0..1 ノブ 2 本**の見せ方を
説明する層で、台帳 op(3-D / optics / tomography …)には効かない。台帳 op は
`pitch_um` や `metal` や `n_sub` のような**実引数**を取るので、UI が助けられることが
まったく別にある:

  1. **引数仕様**   `param_spec(op)` — 名前 / 型 / 既定値 / 範囲 / 選択肢 / 単位 / 説明。
     署名と docstring から自動で取り、手書きの表で上書きする(推測を混ぜない)。
  2. **プリセット** `presets(op)` — 「CD / DVD / BD」「金 / 銀 / アルミ」「ヘアライン /
     旋盤目 / 梨地」のような**名前で選べる実在の設定**。数値を知らなくても試せる。
  3. **入力の作り方** `producers(sort)` — 「この op は normalmap が要る」→ それを
     **産む op の一覧**。型で繋ぐライブラリなので、これが一番効く導線になる。
  4. **試せる入力**  `sample_input(op)` — その op を今すぐ動かせる引数を 1 組作る。
  5. **前提チェック** `preflight(op, kwargs)` — 実行前に「これは動くが**意味のある絵に
     ならない**」を警告する。例: 回折は溝に直交して照らさないと色が出ない、
     全反射は密→疎でしか起きない。例外にはしない(実行は妨げない)。

設計方針: **台帳 op を増やさない**(これは UI 支援の層であって画像処理 op ではない)。
既存レジストリの上に乗るだけなので、台帳・ドキュメント生成には影響しない。
"""
from __future__ import annotations

import importlib
import inspect
import io
import os
import re
from typing import Any

#: 台帳(registry モジュール名, テーブル属性)。`tools/opdocs.LEDGER_DIMS` と同じ並び。
_LEDGERS = (
    ("ops3d", "OPS3D"), ("opsmath", "OPSMATH"), ("opsoptics", "OPSOPTICS"),
    ("opslightfield", "OPSLIGHTFIELD"), ("opsphoton", "OPSPHOTON"),
    ("opsspecular", "OPSSPECULAR"), ("opsmotionmag", "OPSMOTIONMAG"),
    ("opsquat", "OPSQUAT"), ("opsrangedoppler", "OPSRANGEDOPPLER"),
    ("opsacoustics", "OPSACOUSTICS"), ("opsinterferometry", "OPSINTERFEROMETRY"),
    ("opsflyvision", "OPSFLYVISION"), ("opsspc", "OPSSPC"),
    ("opstomography", "OPSTOMOGRAPHY"), ("opsvolcolor", "OPSVOLCOLOR"),
    ("opsreprconv", "OPSREPRCONV"), ("opscadmap", "OPSCADMAP"),
    ("opsannotate", "OPSANNOTATE"), ("opsgfx2d", "OPSGFX2D"),
    ("opsimgmetrics", "OPSIMGMETRICS"), ("opscolortransport", "OPSCOLORTRANSPORT"),
    ("opsimgforensics", "OPSIMGFORENSICS"), ("opsastrostack", "OPSASTROSTACK"),
    ("opsvideostream", "OPSVIDEOSTREAM"),
    ("opsdem", "OPSDEM"), ("opspiv", "OPSPIV"), ("opsprofile", "OPSPROFILE"),
    ("opsshapestat", "OPSSHAPESTAT"),
    ("opsshape2d", "OPSSHAPE2D"),
    ("opsroughness", "OPSROUGHNESS"),
    ("opsmeasure1d", "OPSMEASURE1D"),
    # ★2026-09-08: ops1d(dsp 16 + funct1d 23)は登録済みなのに、docs にも
    #   op_run / op_assist / op_find にも出ていなかった —— 「登録した」と
    #   「引ける」は別。opdocs に足したら、この門が引けない側を鳴らした。
    ("ops1d", "OPS1D"),
    ("opsblob", "OPSBLOB"),
    # 2026-09-20: 結合グラフ(connectome)解析。新語 conn_graph / synapse_table。
    ("opsconngraph", "OPSCONNGRAPH"),
    # 2026-09-23: 絵を作る側(錯視 / 無限描画 / 循環動画)。新語はゼロ ——
    #   返りは既存の rgb / rgbvideo / table。
    ("opsgenerative", "OPSGENERATIVE"),
    ("opsemproof", "OPSEMPROOF"),
    ("opsvideocube", "OPSVIDEOCUBE"),
    ("opslive4d", "OPSLIVE4D"),
    ("opsprintpath", "OPSPRINTPATH"),
    # 2026-09-24: LLM に至る系譜の芯(注意・RoPE・RMSNorm)。新語 tokens / attnmap。
    ("opsllmcore", "OPSLLMCORE"),
    ("opsgeocam", "OPSGEOCAM"),          # 2026-09-21: 固定カメラの向きを写真から(太陽・スカイライン、新語なし)      # 2026-09-21: 3D プリンタ(G-code / 3MF / スライス / 層画像の検査)            # 2026-09-21: 生きている組織の 3D+t(増幅・流れ・補間・高さ場)      # 2026-09-21: 動画の空間×時間の立方体(Video Summagator の再実装)          # 2026-09-21: EM 校正のセカンドオピニオン(labels2d / image2d / table)
)

#: 進化する 2-D op のレジストリ(``ops.REGISTRY``、882 op)。**台帳ではない** ——
#: つまみが ``a``/``b`` の 2 つに固定されており、:func:`run` の宣言型・プリセット・
#: 入力生成はどれも当てはまらない。ゆえに :func:`run` からは呼べず、
#: ``fullseye.apply(image, name)`` あるいは ``fullseye.op.<名前>(image)`` が入口。
#:
#: それでも :func:`find` はここも見る —— 見ないと「erosion」で引いて **1 件も
#: 出ない**(2026-09-06 に実測。gray_erosion も dilation_circle も、882 op すべてが
#: 検索から消えていた)。検索に出るのに :func:`run` では動かない食い違いを隠さない
#: ため、hit には呼び方 ``"call"``(``"run"`` か ``"apply"``)を必ず入れる。
_REGISTRY_LEDGER = "ops"

#: 引数名 → 単位(表示のみ)。名前から機械的に付けられるものだけ。推測はしない。
_UNIT_BY_SUFFIX = (
    ("_um", "µm"), ("_nm", "nm"), ("_mm", "mm"), ("_cm", "cm"), ("_deg", "°"),
    ("_px", "px"), ("_per_mm", "1/mm"), ("_hz", "Hz"), ("_ms", "ms"), ("_s", "s"),
)

#: **手書きの選択肢**。署名からは分からない列挙(モジュールの定数から引く)。
#: 値は (モジュール, 属性) で、実体は import 時ではなく参照時に解決する
#: (循環 import を避け、任意依存が無い環境でも opassist 自体は読める)。
_CHOICE_SOURCES = {
    ("metal_optical_constants", "metal"): ("glassmirror", "METALS"),
    ("metal_mirror_rgb", "metal"): ("glassmirror", "METALS"),
    ("finish_shade", "metal"): ("glassmirror", "METALS"),
    ("finish_shade", "kind"): ("metalfinish", "FINISHES"),
    ("tangent_field", "kind"): ("metalfinish", "FINISHES"),
    ("roughness_field", "kind"): ("metalfinish", "FINISHES"),
    ("micro_normals", "kind"): ("metalfinish", "FINISHES"),
    ("prism_min_deviation_deg", "glass"): ("raytrace", "GLASS_NAMES"),
    # conngraph(2026-09-20): 列挙はモジュール定数から(docstring の写しではなく)
    ("graph_motif_count", "motif"): ("conngraph", "MOTIFS"),
    ("reservoir_states", "nonlinearity"): ("conngraph", "NONLINEARITIES"),
    ("reservoir_encode", "nonlinearity"): ("conngraph", "NONLINEARITIES"),
    ("graph_adjacency_image", "order"): ("conngraph", "ADJACENCY_ORDERS"),
}

#: **手書きの列挙**(モジュール定数が無いもの)。docstring に列挙されている値を写した。
_CHOICE_LITERAL = {
    ("fresnel_dielectric", "polarization"): ("unpolarized", "s", "p"),
    ("fresnel_conductor", "polarization"): ("unpolarized", "s", "p"),
}

#: **プリセット** = 実在の設定に名前を付けたもの。数値を知らなくても試せるための導線。
#: 出典は各 op の docstring(CD/DVD/BD のピッチ、実硝材、材質の n,k)。
PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "grating_rgb": {
        "CD (1.6 µm)": {"pitch_um": 1.6},
        "DVD (0.74 µm)": {"pitch_um": 0.74},
        "Blu-ray (0.32 µm)": {"pitch_um": 0.32},
        "回折格子 600 本/mm": {"pitch_um": 1.0 / 0.6},
    },
    "grating_wavelengths": {
        "CD (1.6 µm)": {"pitch_um": 1.6},
        "DVD (0.74 µm)": {"pitch_um": 0.74},
        "Blu-ray (0.32 µm)": {"pitch_um": 0.32},
    },
    "thin_film_reflectance": {
        "シャボン膜 (水 380 nm)": {"thickness_nm": 380.0, "n_film": 1.33, "n_sub": 1.0},
        "陽極酸化被膜 (150 nm)": {"thickness_nm": 150.0, "n_film": 1.63, "n_sub": 1.5},
        "反射防止 (λ/4 MgF2)": {"thickness_nm": 550.0 / (4 * 1.38), "n_film": 1.38, "n_sub": 1.52},
        "焼き色 (チタン 90 nm)": {"thickness_nm": 90.0, "n_film": 2.4, "n_sub": 2.6},
    },
    "thin_film_rgb": {
        "シャボン膜 (380 nm)": {"thickness_nm": 380.0, "n_film": 1.33, "n_sub": 1.0},
        "陽極酸化 (150 nm)": {"thickness_nm": 150.0, "n_film": 1.63, "n_sub": 1.5},
    },
    "fresnel_dielectric": {
        "空気 → 水": {"n1": 1.0, "n2": 1.333},
        "空気 → BK7": {"n1": 1.0, "n2": 1.5168},
        "空気 → サファイア": {"n1": 1.0, "n2": 1.77},
        "ガラス → 空気 (全反射あり)": {"n1": 1.5168, "n2": 1.0},
    },
    "slab_transmittance": {
        "窓ガラス 3 mm": {"n2": 1.5168, "thickness_mm": 3.0, "sigma_per_mm": 0.0002},
        "厚板 19 mm (緑かぶり)": {"n2": 1.5168, "thickness_mm": 19.0, "sigma_per_mm": 0.002},
        "色ガラス 5 mm": {"n2": 1.52, "thickness_mm": 5.0, "sigma_per_mm": 0.05},
    },
    "prism_min_deviation_deg": {
        "N-BK7 60°": {"apex_deg": 60.0, "glass": "N-BK7"},
        "N-SF2 60° (分散大)": {"apex_deg": 60.0, "glass": "N-SF2"},
        "溶融石英 30°": {"apex_deg": 30.0, "glass": "SILICA"},
    },
    "ward_anisotropic": {
        "ヘアライン (強い異方性)": {"alpha_x": 0.32, "alpha_y": 0.022},
        "サテン (中)": {"alpha_x": 0.20, "alpha_y": 0.08},
        "等方 (梨地)": {"alpha_x": 0.16, "alpha_y": 0.16},
    },
    "oren_nayar": {
        "つるつる (Lambert 一致)": {"roughness_deg": 0.0},
        "紙": {"roughness_deg": 22.0},
        "石膏": {"roughness_deg": 30.0},
        "コンクリート": {"roughness_deg": 35.0},
    },
    "clearcoat_shade": {
        "光沢プラスチック": {"coat": 0.5, "coat_roughness": 0.10},
        "陶器の釉薬": {"coat": 0.9, "coat_roughness": 0.03},
        "車のクリア塗装": {"coat": 1.0, "coat_roughness": 0.02},
        "つや消し": {"coat": 0.05, "coat_roughness": 0.30},
    },
    "weave_normals": {
        "平織り": {"warp_px": 8.0, "weft_px": 8.0, "depth": 0.25},
        "カーボン綾織り": {"warp_px": 6.0, "weft_px": 12.0, "depth": 0.35},
        "粗い麻": {"warp_px": 14.0, "weft_px": 14.0, "depth": 0.45},
    },
    "corrosion_mask": {
        "点錆": {"coverage": 0.08, "scale_px": 10.0},
        "全面の錆": {"coverage": 0.55, "scale_px": 28.0},
        "緑青 (斑)": {"coverage": 0.30, "scale_px": 40.0},
    },
    "triangulate_column": {
        "構造化光ヘッド (基線 120 mm)": {"trans": (-120.0, 0.0, 0.0)},
    },
}

#: **前提チェック**。「動くが意味のある絵にならない」を警告する(例外にしない)。
#: 各項目 = (op 名, 判定関数, 警告文)。判定は解決済みの kwargs を受ける。
def _grating_light_across(kw):
    import numpy as np
    t = np.asarray(kw.get("tangent", (1.0, 0.0, 0.0)), float).ravel()[:3]
    l = np.asarray(kw.get("light", (0.0, 0.0, 1.0)), float).ravel()[:3]
    v = np.asarray(kw.get("view", (0.0, 0.0, 1.0)), float).ravel()[:3]
    d = l - v
    n = float(np.linalg.norm(d))
    if n < 1e-9:
        return True                                  # 光源と視線が同じ = 分散ゼロ
    across = float(np.linalg.norm(np.cross(t, d / n)))
    return across < 0.25                             # 溝とほぼ平行に振っている


_PREFLIGHT = (
    ("grating_rgb", _grating_light_across,
     "光源が溝とほぼ同じ向きです。回折の分散は**溝に直交する向き**にしか起きないので、"
     "この配置では λ = d·Δsin が可視域に届かず色が出ません(tangent に直交する向きへ "
     "light をずらしてください)。"),
    ("critical_angle_deg", lambda kw: float(kw.get("n1", 1.5)) <= float(kw.get("n2", 1.0)),
     "全反射は密→疎(n1 > n2)でしか起きません。この組では臨界角が存在せず ValueError になります。"),
    ("thin_film_reflectance", lambda kw: float(kw.get("thickness_nm", 350.0)) > 3000.0,
     "膜厚が可視光の波長より桁で大きいので、干渉の縞が積分の刻みより細かくなり、"
     "色ではなく平均値に潰れます(膜として意味を持つのは概ね 50–1000 nm)。"),
    ("slab_transmittance", lambda kw: float(kw.get("sigma_per_mm", 0.0)) * float(
        kw.get("thickness_mm", 3.0)) > 8.0,
     "σ·厚さ が 8 を超えています。透過率が 1e-4 未満になり、実質的に不透明です。"),
    ("oren_nayar", lambda kw: float(kw.get("roughness_deg", 20.0)) == 0.0,
     "roughness_deg=0 は Lambert と厳密に同じです(粗さの効果を見たいなら 15–35° 付近)。"),
    ("corrosion_mask", lambda kw: float(kw.get("coverage", 0.3)) <= 0.0,
     "coverage=0 は全面ゼロのマスクを返します(錆を出すなら 0.05 以上)。"),
)


#: tuple / list 引数の**構造**を推定するための名前ヒント。
#: 既定値の形(長さ・入れ子・要素型)だけでは「(0,0) が画素座標なのか範囲なのか」が
#: 決まらないので、名前で意味を足す。ここに無い名前は形だけで分類する(推測しない)。
_SEQ_ROLE_BY_NAME = {
    "light": ("vector3", ("x", "y", "z")), "view": ("vector3", ("x", "y", "z")),
    "tangent": ("vector3", ("x", "y", "z")), "normal": ("vector3", ("x", "y", "z")),
    "direction": ("vector3", ("x", "y", "z")), "axis": ("vector3", ("x", "y", "z")),
    "trans": ("vector3", ("x", "y", "z")), "translation": ("vector3", ("x", "y", "z")),
    "center": ("point", None), "origin": ("point", None),
    "albedo": ("rgb", ("R", "G", "B")), "color": ("rgb", ("R", "G", "B")),
    "rgb": ("rgb", ("R", "G", "B")), "background": ("rgb", ("R", "G", "B")),
    "size": ("shape", ("H", "W")), "shape": ("shape", ("H", "W")),
    "resolution": ("shape", ("H", "W")),
    "bounds": ("bounds", None), "extent": ("bounds", None), "range": ("range", ("min", "max")),
    "orders": ("list_int", None), "angles_deg": ("list_number", None),
    "wavelength_nm": ("list_number", None), "sigmas": ("list_number", None),
    # 行列(3x3)。tuple ではないが「数値 1 個ではない」点は同じで、UI は格子で見せる。
    "k_cam": ("matrix3", None), "k_proj": ("matrix3", None), "intrinsics": ("matrix3", None),
    "K": ("matrix3", None), "rot": ("matrix3", None), "R": ("matrix3", None),
    "pose": ("matrix4", None), "matrix": ("matrix", None),
    "t": ("vector3", ("x", "y", "z")),
}

#: 役割 → 既定の要素数(既定値が tuple で与えられていない引数のために使う)。
#: None = 可変長。行列は (行, 列)。
_ROLE_LENGTH = {
    "vector3": 3, "rgb": 3, "shape": 2, "range": 2, "point": None,
    "bounds": None, "list_int": None, "list_number": None,
    "matrix3": (3, 3), "matrix4": (4, 4), "matrix": None,
}


#: 容器の形の**統一スキーマ**。すべての引数がこの 1 つの形で容器を説明する。
#:
#:   form   "scalar" | "vector" | "matrix" | "list" | "nested"
#:   shape  常に tuple。スカラ = ()、3 ベクトル = (3,)、3x3 = (3, 3)、
#:          可変長 = (None,)、入れ子の可変長 = (None, 2)
#:   elem   要素の値型("number" / "int" / "bool" / "text")
#:   role   意味("vector3" / "rgb" / "point" / "shape" / "bounds" / "matrix3" …)
#:   labels 要素名(["x","y","z"] など)or None
#:
#: ★ 設計(2026-09-04、ユーザー「色々なコンテナ型は扱えるほうが良いけど、統一感も
#: 大事です」): 最初は `kind` に "seq" や "matrix" を混ぜていた ―― つまり**値の型**
#: (数値か整数か選択肢か)と**容器の形**(1 個かベクトルか行列か)が 1 つの欄で
#: 競合していた。UI から見ると「int の 3 ベクトル」が表現できず、行列だけ構造が
#: `seq` キーの下にあるなど、扱いがばらける。ここを直交させ、`kind` は値型だけ、
#: 容器は常に `container` に入れる形へ統一した。スカラも例外にしない
#: (`{"form": "scalar", "shape": ()}`)ので、UI は分岐を 1 本に書ける。
SCALAR_CONTAINER = {"form": "scalar", "shape": (), "elem": None, "role": "scalar",
                    "labels": None, "inner": None}


def _container_from_structure(st: dict) -> dict:
    """内部表現(`_seq_structure` の返り)→ 統一スキーマの容器記述。"""
    role = st.get("role") or "fixed"
    n = st.get("length")
    if str(role).startswith("matrix"):
        shape = tuple(n) if isinstance(n, (tuple, list)) else (None, None)
        form = "matrix"
    elif st.get("inner") is not None or role == "bounds":
        inner_n = (st.get("inner") or {}).get("length")
        shape = (n if isinstance(n, int) else None, inner_n if isinstance(inner_n, int) else None)
        form = "nested"
    elif n is None:
        shape, form = (None,), "list"
    else:
        shape, form = (int(n),), "vector"
    return {"form": form, "shape": shape, "elem": st.get("elem"), "role": role,
            "labels": st.get("labels"), "inner": st.get("inner")}


def _seq_structure(param: str, default) -> dict:
    """tuple / list の既定値 → UI がフォームを組める構造情報。

    返すキー: ``length``(None = 可変)/ ``elem``("int" | "number" | "seq" | "text")/
    ``role``("vector3" / "rgb" / "point" / "shape" / "bounds" / "range" /
    "list_int" / "list_number" / "nested" / "fixed")/ ``labels``(要素名 or None)/
    ``inner``(入れ子のときの 1 要素ぶんの構造)。

    ★ 形だけでは決まらないものがある: ``(0, 0)`` は画素座標にも範囲にもなりうるし、
    ``(0.0, 0.0, 1.0)`` は方向ベクトルにも RGB にもなる。だから名前ヒント
    (`_SEQ_ROLE_BY_NAME`)を先に見て、無ければ**形だけで**分類する ―― 推測で
    役割を付けると、UI が「x/y/z」と書いた欄に RGB を入れさせることになる。
    """
    seq = list(default)
    n = len(seq)
    inner = None
    if seq and all(isinstance(v, (tuple, list)) for v in seq):
        elem = "seq"
        inner = _seq_structure(param, seq[0])
        role = "bounds" if all(len(v) == 2 for v in seq) else "nested"
    elif all(isinstance(v, bool) for v in seq) and seq:
        elem, role = "bool", "fixed"
    elif all(isinstance(v, int) and not isinstance(v, bool) for v in seq) and seq:
        elem, role = "int", "fixed"
    elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seq) and seq:
        elem, role = "number", "fixed"
    elif all(isinstance(v, str) for v in seq) and seq:
        elem, role = "text", "fixed"
    else:
        elem, role = "mixed", "fixed"

    labels = None
    hint = _SEQ_ROLE_BY_NAME.get(param)
    if hint is not None and inner is None:
        role, labels = hint
        # 名前ヒントと実際の長さが食い違うときは**形を優先**する(名前は当てにならない)
        if role in ("vector3", "rgb") and n != 3:
            role, labels = ("list_number" if elem == "number" else "list_int"), None
        elif role in ("shape", "range") and n != 2:
            role, labels = ("list_number" if elem == "number" else "list_int"), None
    if labels is None and role == "point":
        labels = ("row", "col") if n == 2 else tuple("xyz"[:n]) if n == 3 else None
    variable = role in ("list_int", "list_number", "nested") or (
        hint is None and elem in ("int", "number") and n > 4)
    return {"length": None if variable else n, "elem": elem, "role": role,
            "labels": list(labels) if labels else None, "inner": inner}


def _ledger_entry(op_name: str):
    """op 名 → (台帳モジュール名, エントリ dict)。見つからなければ (None, None)。"""
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001 — 任意依存の台帳
            continue
        entries = getattr(mod, table, None)
        if isinstance(entries, dict) and op_name in entries:
            return mod_name, entries[op_name]
    return None, None


def known_ops() -> list[str]:
    """入力補助を出せる op(= どれかの台帳に載っている op)の一覧。"""
    names: set[str] = set()
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if isinstance(entries, dict):
            names.update(entries)
    return sorted(names)


#: 引数名そのものが単位を表す場合(接尾辞では拾えない)。`cie_xyz_from_wavelength(nm)`
#: のように名前が単位そのものの op があり、拾えないと種が汎用 0..1 になって動かない。
_UNIT_BY_NAME = {"nm": "nm", "wavelength": "nm", "um": "µm", "mm": "mm",
                 "deg": "°", "angle": "°", "px": "px"}


def _unit_for(param: str):
    exact = _UNIT_BY_NAME.get(param)
    if exact:
        return exact
    # ★ 最長一致。短い順に見ると `sigma_per_mm` が `_mm` に当たって "mm" になる
    #    (実際は 1/mm)。単位を間違えると UI の数字が黙って別物になる。
    for suffix, unit in sorted(_UNIT_BY_SUFFIX, key=lambda kv: -len(kv[0])):
        if param.endswith(suffix):
            return unit
    return None


def _doc_line(doc: str, param: str):
    """docstring から ``param:`` で始まる説明行を拾う(無ければ None)。"""
    if not doc:
        return None
    pat = re.compile(r"^\s*%s\s*[:：]\s*(.+)$" % re.escape(param), re.M)
    m = pat.search(doc)
    if m:
        return m.group(1).strip()
    # "a / b: ..." のようにまとめて書かれている行も拾う
    pat2 = re.compile(r"^\s*[\w_]+(?:\s*/\s*[\w_]+)*\s*[:：]\s*.+$", re.M)
    for line in pat2.findall(doc):
        head = line.split(":", 1)[0].split("：", 1)[0]
        if param in [t.strip() for t in head.split("/")]:
            return line.split(":", 1)[-1].strip()
    return None


def _choices_for(op_name: str, param: str):
    lit = _CHOICE_LITERAL.get((op_name, param))
    if lit is not None:
        return list(lit)
    src = _CHOICE_SOURCES.get((op_name, param))
    if src is None:
        return None
    try:
        mod = importlib.import_module(src[0])
        vals = getattr(mod, src[1], None)
    except Exception:                                # noqa: BLE001
        return None
    if vals is None:
        return None
    try:
        return [str(v) for v in vals]
    except TypeError:
        return None


#: パス名を取る引数の名前。宣言 sort が "file" のとき(読む側)だけデータ入力として扱う。
_PATH_PARAMS = frozenset({"path", "filename", "fname", "file", "out_path", "outpath"})


#: パス名を取る引数の名前。宣言 sort が "file" のとき(読む側)だけデータ入力として扱う。
_PATH_PARAMS = frozenset({"path", "filename", "fname", "file", "out_path", "outpath"})


def param_spec(op_name: str) -> list[dict]:
    """台帳 op の**実引数**の仕様を返す(UI がフォームを組める形)。

    返り値: 引数ごとの dict のリスト。キーは
    ``name`` / ``kind``("data" = 入力データ、"number" / "int" / "bool" / "choice" /
    "text" / "seq")/ ``default`` / ``required`` / ``unit`` / ``choices`` / ``doc``。

    第 1 引数から順に、台帳の宣言 in 型の本数だけを **データ入力**(``kind="data"``、
    ``sort`` に型名)として扱い、残りをパラメータとする ―― 台帳が「何本のデータを
    取るか」を持っているので、そこは推測せずに宣言に従う。

    未知の op には ``ValueError``(黙って空を返すと「引数が無い op」と区別できない)。
    """
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    fn = entry.get("func")
    ins = list(entry.get("in") or [])
    doc = inspect.getdoc(fn) or entry.get("doc") or ""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        params = []
    out = []
    di = 0                                           # 次に割り当てる宣言 in 型の番号
    for p in params:
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        spec = {"name": p.name, "doc": _doc_line(doc, p.name), "unit": _unit_for(p.name)}
        # ★2026-09-20(GenSpark 第 15 報 N71): ``write_wav(path, x, rate)`` は in=["signal"] なので、
        # 第 1 引数の ``path`` に signal が割り当てられ、``op_run("write_wav")`` が配列をファイル名として
        # 開こうとしていた。パス名の引数は、宣言 sort が "file" のときだけデータ(読む側)で、
        # それ以外は書き先のパラメータ —— データ型は次の引数へ送る。
        is_path = (p.name in _PATH_PARAMS and entry.get("out") == "file"
                   and not (di < len(ins) and ins[di] == "file"))
        if di < len(ins) and not is_path:
            spec.update(kind="data", sort=ins[di], required=True, default=None,
                        container=dict(SCALAR_CONTAINER, form="data", role=ins[di]))
            out.append(spec)
            di += 1
            continue
        default = None if p.default is inspect.Parameter.empty else p.default
        spec["default"] = default
        spec["required"] = p.default is inspect.Parameter.empty
        choices = _choices_for(op_name, p.name)
        if is_path:
            spec["kind"] = "text"                      # 書き先のパス名(サンプルは発明しない)
        elif choices is not None:
            spec.update(kind="choice", choices=choices)
        elif isinstance(default, bool):
            spec["kind"] = "bool"
        elif isinstance(default, int):
            spec["kind"] = "int"
        elif isinstance(default, float):
            spec["kind"] = "number"
        elif isinstance(default, str):
            spec["kind"] = "text"
        elif isinstance(default, (tuple, list)):
            st = _seq_structure(p.name, default)
            spec["kind"] = {"int": "int", "bool": "bool", "text": "text"}.get(st["elem"], "number")
            spec["container"] = _container_from_structure(st)
        else:
            # ★ ここが要点: **既定値が tuple で与えられていない**引数がある。
            # `center=None`(省略可の (row,col))、必須の `trans`(3 ベクトル)、
            # `k_cam`(3x3 行列)…… 既定値だけを見ると「数値 1 個」に見えてしまい、
            # UI が spin box を 1 個出して破綻する。名前で構造を補う。
            hint = _SEQ_ROLE_BY_NAME.get(p.name)
            if hint is not None:
                role, labels = hint
                st = {"length": _ROLE_LENGTH.get(role), "elem": "number", "role": role,
                      "labels": list(labels) if labels else None, "inner": None}
                spec["kind"] = "number"
                spec["container"] = _container_from_structure(st)
            else:
                spec["kind"] = "number" if default is None else "text"
        spec.setdefault("container", dict(SCALAR_CONTAINER))
        out.append(spec)
    return out


def presets(op_name: str) -> dict:
    """op の名前つきプリセット(``{表示名: {引数: 値}}``)。無ければ空 dict。

    数値を知らなくても「CD」「陶器の釉薬」「窓ガラス 3 mm」で試せるようにするための表。
    値の出どころは各 op の docstring(実在の規格値・実硝材・実材質)。

    ★2026-09-20(GenSpark 第 15 報 N69): 未知の op 名にも ``{}`` を返していた —— 「プリセットが無い op」と
    「存在しない op」が同じ答えになる。台帳に無い名前は :func:`assist` と同じ ``ValueError``。
    プリセットは実在の規格値・材質が意味を持つ op にだけ用意した表(2026-09-20 時点 13 op)なので、
    台帳にある op の ``{}`` は「意図して無し」を意味する。
    """
    if _ledger_entry(op_name)[1] is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    return {k: dict(v) for k, v in PRESETS.get(op_name, {}).items()}


def known_sorts() -> list[str]:
    """台帳のどれかが in か out に持つ型(sort)名の一覧(:func:`producers` / :func:`consumers` の引数)。"""
    sorts: set[str] = set()
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for info in entries.values():
            sorts.update(info.get("in") or [])
            if info.get("out"):
                sorts.add(info["out"])
    return sorted(sorts)


def _require_known_sort(fn: str, sort) -> None:
    """★2026-09-20(GenSpark 第 15 報 N68): ``op_producers("gaussian")`` が黙って ``[]`` を返していた。
    引数は型名(sort)であって op 名ではないが、空は「そういう型は無い」とも「産む op が無い」とも
    読めてしまう。未知の型は :func:`assist` と同じく **ValueError** —— op 名を渡された時はそう言う。
    """
    if not isinstance(sort, str) or not sort:
        raise ValueError("opassist.%s: sort must be a non-empty string" % fn)
    sorts = known_sorts()
    if sort in sorts:
        return
    if _ledger_entry(sort)[1] is not None or _is_registry_op(sort):
        raise ValueError(
            "opassist.%s: %r is an op name, not a sort (type) — %s takes a type such as 'normalmap' or 'signal'; "
            "an op's own types are op_assist(%r)['in'] / ['out']" % (fn, sort, fn, sort))
    raise ValueError("opassist.%s: unknown sort %r; known sorts: %s" % (fn, sort, ", ".join(sorts)))


def _is_registry_op(name: str) -> bool:
    try:
        import ops as _ops
        return any(o.name == name for o in _ops.REGISTRY)
    except Exception:                                # noqa: BLE001 - registry unavailable: not an op we can name
        return False


def producers(sort: str) -> list[str]:
    """その型(sort)を**産む** op の一覧。「この入力はどう作る?」への答え。

    型で繋ぐライブラリなので、UI で一番効く導線がこれ ―― 「normalmap が要る」と
    言われた利用者が、次にどの op を押せばよいかが分かる。引数は :func:`known_sorts` の
    型名。未知の型・op 名は ``ValueError``(黙って空を返さない)。
    """
    _require_known_sort("producers", sort)
    found = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            if info.get("out") == sort:
                found.append(name)
    return sorted(set(found))


def consumers(sort: str) -> list[str]:
    """その型を**受け取れる** op の一覧(産んだ後にどこへ繋げるか)。未知の型・op 名は ``ValueError``。"""
    _require_known_sort("consumers", sort)
    found = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            if sort in (info.get("in") or []):
                found.append(name)
    return sorted(set(found))


def preflight(op_name: str, kwargs=None) -> list[str]:
    """実行前の注意書き(0 件以上)。**例外にはしない** — 実行は妨げない。

    「動くが意味のある絵にならない」配置を先に伝えるための層。例: 回折を溝と同じ
    向きから照らしている / 全反射を疎→密で呼んでいる / 膜厚が桁違い。
    どれも実際に踏んだ失敗から起こしている(CHANGELOG 参照)。
    """
    kw = dict(kwargs or {})
    # 既定値で埋めてから判定する(利用者が省いた引数も既定の意味で効くため)
    try:
        for spec in param_spec(op_name):
            if spec["kind"] != "data" and spec["name"] not in kw and spec.get("default") is not None:
                kw.setdefault(spec["name"], spec["default"])
    except ValueError:
        return []
    notes = []
    for name, test, message in _PREFLIGHT:
        if name != op_name:
            continue
        try:
            if test(kw):
                notes.append(message)
        except Exception:                            # noqa: BLE001 — 補助が本体を壊さない
            continue
    return notes


def _sample_value(spec: dict):
    """必須パラメータの「とりあえず動く値」を**容器の形から**作る。

    ★ ここを値型だけで決めると壊れる: `corrosion_mask(shape, ...)` の `shape` は
    (H, W) の組なのに、kind だけ見て 1.0 を入れると op の中で
    「'float' object is not iterable」になる(実際に踏んだ)。容器の role と shape を
    見て、ベクトル・行列・画像サイズ・範囲をそれぞれ妥当な形で埋める。
    """
    import numpy as np
    c = spec.get("container") or {}
    role, shape = c.get("role"), c.get("shape") or ()
    if spec["kind"] == "choice":
        return (spec.get("choices") or ["default"])[0]
    if role == "shape":
        return (64, 64)
    if role == "bounds":
        return ((0.0, 10.0),) * 3
    if role == "range":
        return (0.0, 1.0)
    if role == "point":
        return (32.0, 32.0)
    if role == "rgb":
        return (0.6, 0.4, 0.3)
    if role == "vector3":
        return (0.0, 0.0, 1.0)
    if str(role).startswith("matrix"):
        n = shape[0] if shape and isinstance(shape[0], int) else 3
        return np.eye(int(n))
    if c.get("form") in ("vector", "list") and shape and isinstance(shape[0], int):
        return tuple([1.0] * shape[0]) if spec["kind"] == "number" else tuple([1] * shape[0])
    if spec["kind"] == "bool":
        return False
    if spec["kind"] == "text":
        return ""
    return 1.0 if spec["kind"] == "number" else 1


def sample_input(op_name: str):
    """その op を**今すぐ動かせる**引数を 1 組作って返す ``(args, kwargs)``。

    データ引数は宣言 sort に応じた最小の種を作る。作れない sort は ``None`` を入れて
    返す(黙って別の型を渡すより、埋められなかったことが見える方がよい)。
    """
    import numpy as np

    specs = param_spec(op_name)
    writes_file = (_ledger_entry(op_name)[1] or {}).get("out") == "file"
    seeds = {
        "image2d": lambda: np.linspace(0.0, 1.0, 64 * 64).reshape(64, 64),
        "depth": lambda: 500.0 + 30.0 * np.random.default_rng(0).random((64, 64)),
        "signal": lambda: np.linspace(0.0, 1.0, 64),
        "normalmap": _sample_normalmap,
        "rgbimage": lambda: np.tile(np.array([0.6, 0.4, 0.3]), (32, 32, 1)),
        "rgb": lambda: np.clip(np.random.default_rng(0).random((32, 32, 3)), 0, 1),
        "rgbvideo": lambda: np.clip(
            np.random.default_rng(0).random((5, 16, 16, 3)), 0, 1),
        "points": lambda: np.random.default_rng(0).normal(size=(64, 3)),
        "pointmap": lambda: np.random.default_rng(0).normal(size=(16, 16, 3)),
        "voxel": lambda: np.random.default_rng(0).random((16, 16, 16)),
        "sdf": lambda: np.random.default_rng(0).normal(size=(16, 16, 16)),
        "coordgrid": lambda: __import__("sdf_ops").grid_coords(((0.0, 10.0),) * 3, 16)[0],
        "images": lambda: [np.random.default_rng(k).random((32, 32)) for k in range(4)],
        # conngraph(2026-09-20): 12 ノードの 2 クリーク有向グラフと、それを産むシナプス表。
        # ★一様乱数の行列にしない —— 成分・モジュラリティ・rich club は構造が無いと
        #   「どのノブでも同じ数」になり、押して動いても意味のある絵にならない。
        "conn_graph": _sample_conn_graph,
        "synapse_table": _sample_synapse_table,
        # llmcore(2026-09-24): ★一様乱数にしない —— どの行も似た向きになり、
        #   注意の重みが全行ほぼ一様になって「押しても何も起きない」種になる。
        #   滑らかな画像を 8x8 パッチに切ると、近い場所が近い向きを向く。
        "tokens": _sample_tokens,
        "attnmap": _sample_attnmap,
    }
    #: 単位に合う種(汎用の 0..1 では意味を持たない量がある)。
    #: ★ 実測で判明: `prism_min_deviation_deg` の波長入力に 0..1 の汎用 signal を渡すと
    #: 「波長は正の値」で弾かれ、**サンプルが動かない op** になっていた。単位が分かる
    #: なら、その量として妥当な範囲を種にする方が「押せば動く」に近い。
    unit_seeds = {
        "nm": lambda: np.linspace(400.0, 700.0, 64),      # 可視域
        "µm": lambda: np.linspace(0.4, 0.7, 64),
        "mm": lambda: np.linspace(0.5, 20.0, 64),
        "°": lambda: np.linspace(0.0, 80.0, 64),
        "1/mm": lambda: np.linspace(0.0, 0.1, 64),
    }
    args, kwargs = [], {}
    for spec in specs:
        if spec["kind"] == "data":
            maker = None
            if spec.get("sort") in ("signal", "image2d") and spec.get("unit") in unit_seeds:
                maker = unit_seeds[spec["unit"]]
            if maker is None:
                maker = seeds.get(spec.get("sort"))
            args.append(maker() if maker is not None else None)
        elif spec["required"]:
            # 書き先のパス名は発明しない —— None を渡し、op が「path is None — pass a file path」と言う。
            kwargs[spec["name"]] = None if (writes_file and spec["name"] in _PATH_PARAMS) else _sample_value(spec)
    return args, kwargs


def _sample_tokens():
    """滑らかな画像を 8x8 で切った (16, 64) のパッチ列。llmcore の種。"""
    import numpy as np
    y, x = np.mgrid[0:32, 0:32]
    img = 0.5 + 0.5 * np.sin(x / 5.0) * np.cos(y / 7.0)
    return img.reshape(4, 8, 4, 8).transpose(0, 2, 1, 3).reshape(16, 64)


def _sample_attnmap():
    """`_sample_tokens` から実際に作った (16, 16) の注意行列(行和 1)。"""
    import llmcore
    t = _sample_tokens()
    return llmcore.attention_weights(llmcore.attention_scores(t, t))


def _sample_conn_graph():
    """12 ノード = 6 個ずつの 2 クリーク(内側は全結合・重み 1..5)+ 橋 2 本(重み 0.5)。"""
    import numpy as np
    W = np.zeros((12, 12))
    for base in (0, 6):
        for i in range(6):
            for j in range(6):
                if i != j:
                    W[base + i, base + j] = 1.0 + (i * 7 + j * 3) % 5
    W[5, 6] = 0.5
    W[11, 0] = 0.5
    return W


def _sample_synapse_table():
    """`_sample_conn_graph` と同じグラフのシナプス表 (m, 3) = (pre, post, count)。"""
    import numpy as np
    W = _sample_conn_graph()
    pre, post = np.nonzero(W)
    return np.stack([pre, post, np.ceil(W[pre, post])], axis=1).astype(np.float64)


def _sample_normalmap():
    import numpy as np
    y, x = np.mgrid[-1:1:64j, -1:1:64j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None]


#: 実測プローブ用の種。`sample_input` と同じ形だが、こちらは**宣言と違う型も**入れて
#: 「実は通る型」を探すために使う。小さめに作る(1 op あたり数十 ms に収める)。
def _probe_seeds():
    import numpy as np
    y, x = np.mgrid[-1:1:24j, -1:1:24j]
    r2 = x * x + y * y
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    nmap = np.stack([x, y, z], -1) * (r2 < 1.0)[..., None]
    rng = np.random.default_rng(0)
    return {
        "signal": np.linspace(0.05, 0.95, 32),
        "image2d": np.linspace(0.05, 0.95, 24 * 24).reshape(24, 24),
        "depth": 500.0 + 30.0 * rng.random((24, 24)),
        "normalmap": nmap,
        "rgbimage": np.tile(np.array([0.6, 0.4, 0.3]), (24, 24, 1)),
        "pointmap": rng.normal(size=(12, 12, 3)),
        "points": rng.normal(size=(48, 3)),
        "voxel": rng.random((12, 12, 12)),
        "sdf": rng.normal(size=(12, 12, 12)),
        "images": [rng.random((24, 24)) for _ in range(4)],
        "conn_graph": _sample_conn_graph(),
        "synapse_table": _sample_synapse_table(),
    }


def accepted_sorts(op_name: str, extra_kwargs=None) -> dict:
    """その op が**実際に受け取れる型**を測って返す(宣言ではなく実測)。

    返り値: ``{sort: "declared" | "works" | "rejected" | "error"}``。
      * ``declared`` 台帳が宣言している型(当然通る)
      * ``works``    宣言していないが**通った**型(= op は多態。UI はこれも許してよい)
      * ``rejected`` op 自身が ValueError で断った(fail-closed が効いている = 正しい)
      * ``error``    ValueError 以外の例外(素の TypeError 等 = 番人の穴かもしれない)

    動機(2026-09-04、ユーザー「op は複数の型に対応してるといいね」): 台帳は 1 op に
    1 つの入力型しか書けないが、実体は要素ごとの演算が多く、`signal` と宣言した op が
    `image2d` も `voxel` も通ることがある。**宣言を広げる**のは台帳と champion に
    波及するので、まずは「測って見せる」層としてここに置く ―― 数えられていない
    多態性は「無い」のと同じで、UI も利用者も使えないままになる。

    ★ 測るので**副作用のある op には使わない**こと(ここで扱う台帳 op は純関数)。
    第 1 引数だけを差し替えて呼び、返りが有限かどうかまでは見ない(型の受理のみ)。
    """
    import numpy as np

    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    specs = param_spec(op_name)
    data = [s for s in specs if s["kind"] == "data"]
    if not data:
        return {}
    fn = entry["func"]
    declared = list(entry.get("in") or [])
    seeds = _probe_seeds()

    # 第 2 引数以降のデータ入力と必須パラメータは宣言どおりに埋める
    base_args, base_kwargs = sample_input(op_name)
    base_kwargs.update(dict(extra_kwargs or {}))

    out = {}
    for sort, seed in seeds.items():
        if sort == declared[0] if declared else False:
            out[sort] = "declared"
            continue
        args = list(base_args)
        if not args:
            continue
        args[0] = seed
        try:
            res = fn(*args, **base_kwargs)
        except ValueError:
            out[sort] = "rejected"
            continue
        except Exception:                                # noqa: BLE001
            out[sort] = "error"
            continue
        ok = res is not None and (not isinstance(res, np.ndarray) or res.size > 0)
        out[sort] = "works" if ok else "rejected"
    if declared:
        out[declared[0]] = "declared"
    return out


# --------------------------------------------------------------------------- #
# 使いやすさ: 探す / すぐ動かす / 型を繋ぐ                                       #
# --------------------------------------------------------------------------- #
_WORD_RE = re.compile(r"[a-z0-9]+")

#: 和文(CJK)の連なり。★``_WORD_RE`` は ``[a-z0-9]+`` なので、日本語のクエリは
#: **語が 1 つも取れない**(``_WORD_RE.findall("点 検出") == []``)。語幹の段が
#: 死に、部分一致は空白ごと含む文字列を探すので、**和文の複数語クエリは構造的に
#: 必ず 0 件**だった —— docstring の大半が日本語で、6 言語を配っている製品で。
#: 2026-09-08 に `poc_search_sweep_width` が踏んで判明(``op_find("点 検出")`` /
#: ``("スポット 検出")`` / ``("小さい目標")`` がいずれも 0 件で、副画素重心つきの
#: 点目標検出は ``star_detect`` しか無いのに和文から辿り着けなかった)。
_CJK_RE = re.compile("[぀-ヿ㐀-䶿一-鿿ｦ-ﾟ]+")

#: ``op_find`` の採点で見る docstring。台帳の ``doc`` は **1 行目だけ**(30 文字
#: 程度)なので、説明語を足しても検索には効かなかった。ここでは生の ``__doc__``
#: 全文を継ぎ足した文字列を使う —— ただし **既存の点が 0 のときだけ**参照する
#: 追加の段なので、これまでの並び順は変わらない(語幹の段と同じ方針)。
_FULLDOC_CACHE: dict = {}


def _full_doc(ledger_mod: str, op_name: str, info: dict) -> str:
    """台帳の 1 行 doc + 実装の docstring 全文(小文字化・キャッシュ)。"""
    key = (ledger_mod, op_name)
    d = _FULLDOC_CACHE.get(key)
    if d is None:
        d = str(info.get("doc") or "")
        try:
            mod = importlib.import_module(str(info.get("module") or ledger_mod))
            fn = getattr(mod, op_name, None)
            if fn is not None and getattr(fn, "__doc__", None):
                d = d + chr(10) + fn.__doc__
        except Exception:                                # noqa: BLE001
            pass
        d = d.lower()
        _FULLDOC_CACHE[key] = d
    return d


def _cjk_fraction(q: str, hay: str) -> float:
    """和文クエリの当たった割合(0.0〜1.0)。空白で切った CJK の連なりごとに見る。

    日本語は語の切れ目が無いので、連なりが丸ごと当たれば 1.0、当たらなければ
    **文字 2-gram の一致率**で按分する(「スポット検出」→「検出」だけ当たる、
    のような部分一致を拾うため)。短い連なりはそのまま含有で判定する。
    """
    terms = [t for w in q.split() for t in _CJK_RE.findall(w)]
    if not terms:
        return 0.0
    tot = 0.0
    for t in terms:
        if t in hay:
            tot += 1.0
        elif len(t) >= 3:
            bg = [t[i:i + 2] for i in range(len(t) - 1)]
            tot += sum(1 for b in bg if b in hay) / len(bg)
    return tot / len(terms)

#: 語幹一致とみなす共通接頭辞の長さ。★4 にすると "median"/"medial" や
#: "contrast"/"contour" が繋がってしまい、5 で切ると
#: "correlation"/"correlate"(8)・"segmentation"/"segment"(7)・
#: "rotation"/"rotate"(5)・"gaussian"/"gauss"(5) は拾えて、上の 2 組は拾わない。
_STEM_MIN = 5

#: 語幹一致を採用する重み割合の下限(:func:`_stem_fraction` の注記)。
_STEM_FLOOR = 0.15


#: 共通接頭辞の**後ろに許す語尾**。★接頭辞の長さだけで判定すると
#: "median"/"medial" が繋がる(共通 "media" が 5 文字ある)。語尾が
#: 屈折語尾らしいかどうかを見ると、"correlation"/"correlate"(ion / e)は
#: 通り、"median"/"medial"(n / l)と "corner"/"cornea"(r / a)は落ちる。
_STEM_SUFFIXES = frozenset((
    "", "s", "e", "es", "ed", "d", "ing", "ion", "tion", "ation", "sion",
    "ate", "ated", "al", "ial", "ian", "ic", "ics", "y", "ly", "er", "or",
    "ers", "ness", "ment", "ments", "able", "ible", "ive", "ity", "ise",
    "ize", "izer", "izing", "ization", "isation",
))


def _stem_match(qt: str, ht: str) -> bool:
    """2 つの語が同じ語幹か。

    共通接頭辞が ``_STEM_MIN`` 以上あり、かつ**どちらかの残りが屈折語尾**
    (:data:`_STEM_SUFFIXES`)であること。長さだけで見ないのは上の注記の理由。
    """
    if qt == ht:
        return True
    n = min(len(qt), len(ht))
    if n < _STEM_MIN:
        return False
    k = 0
    while k < n and qt[k] == ht[k]:
        k += 1
    if k < _STEM_MIN:
        return False
    return qt[k:] in _STEM_SUFFIXES or ht[k:] in _STEM_SUFFIXES


#: 語 → その語を名前に含む op の数(1 度だけ数えて憶える)。
_TOKEN_DF: dict[str, int] | None = None
_N_OPS = 1


def _token_df() -> dict[str, int]:
    """全 op 名の語の出現数。語の**重み**(情報量)を決めるのに使う。"""
    global _TOKEN_DF, _N_OPS
    if _TOKEN_DF is None:
        import collections
        names = [op.name for op in _registry_ops()]
        for mod_name, table in _LEDGERS:
            try:
                entries = getattr(importlib.import_module(mod_name), table, None)
            except Exception:                            # noqa: BLE001
                continue
            if isinstance(entries, dict):
                names.extend(entries)
        cnt: collections.Counter = collections.Counter()
        for nm in names:
            cnt.update(set(_WORD_RE.findall(nm.lower())))
        _TOKEN_DF, _N_OPS = dict(cnt), max(len(names), 1)
    return _TOKEN_DF


_WEIGHT_CACHE: dict[str, float] = {}


def _token_weight(t: str) -> float:
    """語の重み。**ありふれた語ほど軽い**。

    ★これが無いと "digital image correlation" が `abs_image` / `acos_image` を
    先に返す(実測)—— 3 語のうち 1 語が当たっただけなのは
    `piv_cross_correlate` も同じで、素の割合では区別が付かないため。
    "image" は 1829 op のうち 59 個の名前に出るが "correlation" は 2 個しかない。

    ★数えるのは**語幹一致した数**であって、その語そのものの数ではない。
    "measurement" は op 名に 1 度も出ないが、語幹一致する "measure" は
    60 個以上に出る。素の出現数で重みを付けると "strain measurement" が
    `add_metrology_object_*_measure` を `piv_strain_rate` より上に置く(実測)。
    """
    w = _WEIGHT_CACHE.get(t)
    if w is None:
        import math
        df = _token_df()
        n = sum(c for tok, c in df.items() if _stem_match(t, tok))
        w = 1.0 / math.log2(2.0 + n)
        _WEIGHT_CACHE[t] = w
    return w


def _stem_fraction(q_tokens: list[str], hay: str) -> float:
    """``hay`` に語幹一致したクエリ語の**重み付き割合**(0.0〜1.0)。"""
    if not q_tokens:
        return 0.0
    h_tokens = _WORD_RE.findall(hay.lower())
    if not h_tokens:
        return 0.0
    tot = hit = 0.0
    for qt in q_tokens:
        w = _token_weight(qt)
        tot += w
        if any(_stem_match(qt, ht) for ht in h_tokens):
            hit += w
    frac = hit / tot if tot > 0 else 0.0
    # ★床。無い状態だと "zzz-nothing-matches" が `histogram_match` を返す
    #   ("matches" が `match_*` に語幹一致するため)。当たった語の重みが
    #   クエリ全体の 15 % に満たなければ「当たっていない」とみなす。
    #   実測: "digital image correlation" は 0.19(通す)、
    #   "zzz-nothing-matches" は 0.10(落とす)。
    return frac if frac >= _STEM_FLOOR else 0.0


_NOTE_LINES: dict | None = None


def _note_first_line(name: str) -> str:
    """op ノート(docs/ops/**/<name>.md、無ければ wheel 同梱の studio_assets/op_help/<name>.html)の最初の散文 1 行。

    ★2026-09-20(GenSpark 第 33・48・53 報 N119 / N162 / N178): `op_find("gaussian")` の ``doc`` が空だった ——
    registry の ``Op.doc`` は 931 op 中 422 にしか無く、正本はノートなのに find はノートを見ていなかった。
    ノートは全 op にある(門で固定)ので、そこから 1 行取れば doc の空欄は消える。
    """
    global _NOTE_LINES
    if _NOTE_LINES is None:
        import glob as _glob
        import html as _html
        import re as _re
        table: dict = {}
        here = os.path.dirname(os.path.abspath(__file__))
        for p in _glob.glob(os.path.join(here, "docs", "ops", "**", "*.md"), recursive=True):
            stem = os.path.basename(p)[:-3]
            if stem in table or stem.startswith("INDEX"):
                continue
            try:
                body = io.open(p, encoding="utf-8").read()
            except OSError:
                continue
            if body.startswith("---"):
                parts = body.split("---", 2)
                body = parts[2] if len(parts) == 3 else body
            # 「## 使い方」(無ければ Usage / What it does)の節の最初の散文を採る。冒頭は図と注(「*図は…*」)で、
            # そこを取ると doc が図の説明文になる(2026-09-20 に実際にそうなった)。
            lines = body.splitlines()
            start = 0
            for k, ln in enumerate(lines):
                if ln.startswith("## ") and any(w in ln for w in ("使い方", "Usage", "What it does", "How to use")):
                    start = k + 1
                    break
            for ln in lines[start:]:
                t = ln.strip()
                if not t or t.startswith(("#", "|", "<", "!", "```", "- ", "* ", "*", "[")):
                    if t.startswith("## ") and start:      # 次の節に入った: 使い方の節に散文が無かった
                        break
                    continue
                table[stem] = _re.sub(r"[`*]", "", t)[:200]          # _ は残す(gauss_filter を gaussfilter にしない)
                break
        if not table:                                    # wheel: ノートの本文は無く、help HTML だけがある
            for p in _glob.glob(os.path.join(here, "studio_assets", "op_help", "*.html")):
                stem = os.path.basename(p).split(".")[0]
                if stem in table:
                    continue
                try:
                    txt = _re.sub(r"<[^>]+>", " ", io.open(p, encoding="utf-8").read())
                except OSError:
                    continue
                txt = _html.unescape(_re.sub(r"\s+", " ", txt)).strip()
                if txt:
                    table[stem] = txt[:200]
        _NOTE_LINES = table
    return _NOTE_LINES.get(name, "")


def find(query: str, limit: int = 20) -> list[dict]:
    """自由語で op を探す(名前・説明・カテゴリ・モジュールを横断)。

    「虹」「rust」「fresnel」「旋盤」のように**やりたいこと**で引ける入口。
    完全一致 > 名前の部分一致 > 説明の一致 の順に並べる。各ヒットの ``match`` が何で当たったか
    (``exact`` / ``name`` / ``stem`` / ``doc``)を言う —— 「op が在るか」を問うなら ``doc`` を除くこと。

    ## 語幹と複数語(2026-09-06 追加)

    部分一致だけだと **"correlation" が `piv_cross_correlate` を出さない**
    (どちらも他方の部分文字列ではない)。実際にこれで既存の PIV 23 op を
    見落として同じものを作りかけたので、語幹の段を足した:

    * クエリを語に分け、**共通接頭辞 5 文字以上**を同じ語幹とみなす。
    * 複数語のクエリは**当たった語の割合**で点を按分する
      (以前は句全体が含まれないと 0 件だった —— "subpixel displacement" が
      その例)。

    点は部分一致より必ず下(名前 45 / 説明 22 を上限)なので、**既存の
    並び順は変わらない**。語幹の段は「これまで 0 件だったもの」を拾うだけ。

    **台帳と 2-D レジストリの両方**を見る(:data:`_REGISTRY_LEDGER` の注記)。
    どちらから来たかは ``"ledger"`` で、**呼び方の違い**は ``"call"`` で分かる:

    * ``"call": "run"``   —— :func:`run` / ``fullseye.<名前>(...)`` で呼べる。
    * ``"call": "apply"`` —— ``fullseye.apply(image, 名前)`` か
      ``fullseye.op.<名前>(image)``。つまみは ``a``/``b`` の 2 つだけ。

    返り値: ``[{"op", "ledger", "module", "category", "doc", "call", "score"}, ...]``
    """
    q = str(query).strip().lower()
    if not q:
        raise ValueError("opassist.find: query must not be empty")
    q_tokens = _WORD_RE.findall(q)
    hits = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                                # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            doc = str(info.get("doc") or "")
            hay_name = name.lower()
            score = 0
            if hay_name == q:
                score = 100
            elif q in hay_name:
                score = 60 + max(0, 20 - len(hay_name))
            elif q in doc.lower():
                score = 30
            elif q in str(info.get("category", "")).lower() or q in str(info.get("module", "")).lower():
                score = 20
            else:
                fr = _stem_fraction(q_tokens, hay_name)
                if fr:
                    score = int(round(45 * fr))
                else:
                    fr = _stem_fraction(q_tokens, doc)
                    score = int(round(22 * fr)) if fr else 0
                if not score:                            # ★和文の段(2026-09-08)
                    # 全文で拾い、**要約(名前 + 1 行 doc)に当たった分を重く**する。
                    # 深い本文の一致だけだと同点が並び、並び順が名前のアルファベット
                    # 順になって「どれでもよい 20 件」に見える。
                    fr = _cjk_fraction(q, hay_name + " "
                                       + _full_doc(mod_name, name, info))
                    if fr >= 0.5:
                        fs_ = _cjk_fraction(q, hay_name + " " + doc.lower())
                        score = int(round(16 * fr + 6 * fs_))
            if score:
                hits.append({"op": name, "ledger": mod_name, "module": info.get("module"),
                             "category": info.get("category"), "doc": doc,
                             "call": "run", "score": score})
    # 2-D レジストリ(882 op)。台帳と同じ採点で、同点なら台帳を先に出す(-1 点)。
    seen = {h["op"] for h in hits}
    for op in _registry_ops():
        if op.name in seen:
            continue
        doc = str(op.doc or "") or _note_first_line(op.name)
        hay_name = op.name.lower()
        if hay_name == q:
            score = 99
        elif q in hay_name:
            score = 59 + max(0, 20 - len(hay_name))
        elif q in doc.lower():
            score = 29
        elif q in str(op.category or "").lower() or q in str(op.halcon or "").lower():
            score = 19
        else:
            fr = _stem_fraction(q_tokens, hay_name)
            if fr:
                score = int(round(44 * fr))
            else:
                fr = _stem_fraction(q_tokens, doc)
                score = int(round(21 * fr)) if fr else 0
            if not score:                                # ★和文の段(2026-09-08)
                fr = _cjk_fraction(q, hay_name + " " + doc.lower())
                score = int(round(21 * fr)) if fr >= 0.5 else 0
            if not score:
                continue
        hits.append({"op": op.name, "ledger": _REGISTRY_LEDGER, "module": "ops",
                     "category": op.category, "doc": doc,
                     "call": "apply", "score": score})
    # n-ary 層(``imgops_nary``、17 op: add_image / sub_image / mult_image / div_image …)。
    # ★2026-09-19(GenSpark N2): ``fullseye.apply([x, y], "add_image")`` で**動く**のに、
    # ``op_names()`` にも ``op_find()`` にも載っていなかった(op_names は 1 入力のレジストリだけ、
    # op_find は台帳 + レジストリだけを見ていた)。呼べるものは探せなければならない。
    for nop in _nary_ops():
        if nop.name in seen:
            continue
        doc = str(getattr(nop, "desc", "") or "")
        hay_name = nop.name.lower()
        if hay_name == q:
            score = 99
        elif q in hay_name:
            score = 59 + max(0, 20 - len(hay_name))
        elif q in doc.lower():
            score = 29
        elif q in str(getattr(nop, "halcon", "") or "").lower():
            score = 19
        else:
            fr = _stem_fraction(q_tokens, hay_name)
            score = int(round(44 * fr)) if fr else 0
            if not score:
                fr = _stem_fraction(q_tokens, doc)
                score = int(round(21 * fr)) if fr else 0
            if not score:
                continue
        hits.append({"op": nop.name, "ledger": "nary", "module": "imgops_nary",
                     "category": "nary", "doc": doc,
                     "call": "apply([%s], name)" % ", ".join("x%d" % i for i in range(int(nop.arity))),
                     "score": score})
    # ★2026-09-20: 何で当たったかを ``match`` に(exact = 名前の完全一致 / name = 名前の部分一致 / stem = 語幹 /
  #   doc = 説明・カテゴリの語)。doc をノートで埋めた(N119)途端、PoC の「op が無い」検査が説明文の語で当たって
  #   落ちた —— 件数で「在る」と言わず、name 以上の当たりだけを見るための鍵。GenSpark 第 33 報の exact もこれで読める。
    for h in hits:
        sc = h["score"]
        h["match"] = "exact" if sc >= 99 else "name" if sc >= 59 else "stem" if sc >= 40 else "doc"
    hits.sort(key=lambda h: (-h["score"], h["op"]))
    return hits[: max(int(limit), 1)]


def _nary_ops():
    """``imgops_nary.build_nary()`` を遅延で読む(読めなければ空 —— 検索だけ痩せる)。"""
    try:
        return importlib.import_module("imgops_nary").build_nary()
    except Exception:                                    # noqa: BLE001
        return ()


def _registry_ops():
    """``ops.REGISTRY`` を遅延で読む(読めなければ空 —— 検索だけ痩せる)。"""
    try:
        return importlib.import_module("ops").REGISTRY
    except Exception:                                    # noqa: BLE001
        return ()


def _registry_hint(op_name: str) -> str:
    """台帳に無い名前が単入力 registry の op なら、走らせ方(apply)を 1 文で(op_run は台帳の入口)。"""
    try:
        import api as _api
        op = _api.find_op(op_name)
    except Exception:  # noqa: BLE001 - a hint must never replace the original error
        return ""
    if op is None:
        return ""
    return (" — %r is a single-image registry op, not a ledger op: run it with fullseye.apply(img, %r) "
            "(op_run is the entry for the typed ledgers; fullseye.op_find(%r) tells the tier)" % (op_name, op_name, op_name))


def run(op_name: str, *data, preset=None, strict: bool = False, **kwargs):
    """op を**1 行で**動かす(プリセット解決 → 前提チェック → 宣言型で返す)。

    ``opassist.run("grating_rgb", normals, preset="CD (1.6 µm)", light=(0, .55, .83))``

    data:   位置のデータ入力(省略すると `sample_input` の種を使う = そのまま試せる)。
    preset: `presets(op)` の表示名。中身は kwargs より**弱い**(明示指定が勝つ)。
    strict: True なら前提チェックの警告を ``ValueError`` にする。既定は False で、
            警告は返り値の ``notes`` に入れるだけで実行は妨げない。

    返り値: ``(result, notes)``。result は**台帳の宣言 out 型**(adapter 適用後)なので、
    そのまま次の op へ渡せる ―― 素の関数のタプル返しを呼び手が剥がす必要が無い。
    """
    # ★2026-09-20(GenSpark 第 55 報 N200): op_run(img, "gaussian") が `unhashable type: 'numpy.ndarray'`、
    #   op_run("gaussian", img) が「not in any ledger」で終わり、registry op は apply で走ることを言わなかった。
    if not isinstance(op_name, str):
        raise TypeError("opassist.run(name, *inputs): the first argument is the op name, got %s — the order is "
                        "op_run(name, <input>, ...), not op_run(<input>, name)" % type(op_name).__name__)
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger){_registry_hint(op_name)}")
    kw = {}
    if preset is not None:
        table = presets(op_name)
        if preset not in table:
            raise ValueError(f"opassist.run: unknown preset {preset!r} for {op_name}; "
                             f"available: {sorted(table)}")
        kw.update(table[preset])
    kw.update(kwargs)                                    # 明示指定がプリセットに勝つ

    args = list(data)
    if not args:
        args, auto_kw = sample_input(op_name)
        # ★2026-09-20(GenSpark 第 20 報 N87): 種を作れない型(mesh / lab / matrix …)は None のまま
        # 関数に渡り、IndexError / AttributeError / AxisError が利用者に届いていた(11 op)。
        # 呼ばずに、どの入力を渡せばよいかを言う。
        missing = [sp["sort"] for sp, a in zip([x for x in param_spec(op_name) if x["kind"] == "data"], args) if a is None]
        if missing:
            raise ValueError("opassist.run(%r): no built-in sample for input sort(s) %s — pass the input(s) "
                             "explicitly: op_run(%r, <%s>)" % (op_name, ", ".join(repr(m) for m in missing), op_name,
                                                              ">, <".join(sp["sort"] for sp in param_spec(op_name) if sp["kind"] == "data")))
        for k, v in auto_kw.items():
            kw.setdefault(k, v)
        auto_keys = {k for k, v in auto_kw.items() if k not in kwargs and v is not None}   # None = 発明しなかった値
    else:
        auto_keys = set()
    # ★2026-09-20(N71): データ引数が署名の先頭に無い op(write_wav(path, x))は名前で渡す —— 位置で渡すと
    # 配列が path に入る。データ引数の名前は param_spec が知っている。
    data_names = [sp["name"] for sp in param_spec(op_name) if sp["kind"] == "data"]
    try:
        leading = [q.name for q in inspect.signature(entry["func"]).parameters.values()][:len(args)]
    except (TypeError, ValueError):
        leading = data_names[:len(args)]
    if args and leading != data_names[:len(args)] and len(data_names) >= len(args):
        kw.update(zip(data_names, args))
        args = []
    # ★2026-09-20(GenSpark 第 34 報 N122、再現): 入力を一部だけ渡すと(blend_mode(base) で top 無し)Python の生の
    #   「missing 1 required positional argument」が届いていた。0 個のときは上で種を作って言うのに、1 個以上のときは
    #   検査が無かった。必須のデータ引数が位置でも名前でも来ていなければ、期待する形を 1 文で言う。
    req = [sp for sp in param_spec(op_name) if sp["kind"] == "data" and sp.get("required")]
    given = set(kw) | set(data_names[:len(args)])
    lacking = [sp for sp in req if sp["name"] not in given]
    if lacking and (args or kwargs):
        raise ValueError("opassist.run(%r): missing input(s) %s — this op takes %s: op_run(%r, <%s>)"
                         % (op_name, ", ".join("%s (%s)" % (sp["name"], sp["sort"]) for sp in lacking),
                            ", ".join(sp["name"] for sp in req), op_name, ">, <".join(sp["sort"] for sp in req)))
    notes = preflight(op_name, kw)
    if notes and strict:
        raise ValueError("opassist.run: preflight: " + " / ".join(notes))
    mod = importlib.import_module(mod_name)
    caller = getattr(mod, "call", None)
    try:
        result = caller(op_name, *args, **kw) if caller else entry["func"](*args, **kw)
    except (IndexError, AttributeError, TypeError) as e:
        # ★2026-09-20(N87): 自動の数値サンプル(1.0)が座標や行列を要する引数に合わないと、op の中の
        # IndexError がそのまま利用者に届いていた(scene_box の center_mm 等)。自動値が原因なら言う。
        if auto_keys:
            raise ValueError("opassist.run(%r): the built-in sample values for %s do not fit this op "
                             "(%s: %s) — pass them explicitly, e.g. op_run(%r, **{...})"
                             % (op_name, sorted(auto_keys), type(e).__name__, str(e)[:80], op_name)) from e
        raise
    return result, notes


def path(from_sort: str, to_sort: str, max_len: int = 4) -> list[list[str]]:
    """型 A から型 B へ**繋ぐ op の列**を探す(型グラフ上の最短路)。

    ``path("coordgrid", "mesh")`` → ``[["sphere_sdf", "marching_cubes"], ...]``
    のように、「持っているもの」から「欲しいもの」までの手順が出る。型で繋ぐ
    ライブラリなので、これが UI で一番効く導線になる(手順を知らなくても辿れる)。

    max_len: 段数の上限(既定 4)。同じ長さの経路は op 名の辞書順で返す。
    """
    if not isinstance(from_sort, str) or not isinstance(to_sort, str):
        raise ValueError("opassist.path: sorts must be strings")
    if from_sort == to_sort:
        return [[]]
    edges: dict[str, list[tuple[str, str]]] = {}
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                                # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            ins = info.get("in") or []
            out = info.get("out")
            if not out:
                continue
            for src in ins:
                edges.setdefault(src, []).append((name, out))
    # 幅優先。同じ段数の解を全部集めてから返す(最短だけを見せる)
    frontier = [(from_sort, [])]
    seen = {from_sort}
    for _ in range(max(int(max_len), 1)):
        found, nxt, reached = [], [], set()
        for sort, chain in frontier:
            for name, out in sorted(edges.get(sort, [])):
                if out == to_sort:
                    found.append(chain + [name])
                elif out not in seen and out not in reached:
                    reached.add(out)
                    nxt.append((out, chain + [name]))
        if found:
            return sorted(found)
        seen |= reached
        frontier = nxt
        if not frontier:
            break
    return []


def assist(op_name: str, measure: bool = True) -> dict:
    """UI が 1 回で取れるまとめ: 仕様・プリセット・入力の作り方・次に繋げる先・受理型。

    ``measure=True``(既定)は `accepted_sorts` を実測するので op を数回呼ぶ。
    一覧を作るときなど回数が要る場面では ``measure=False`` にする。
    """
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    specs = param_spec(op_name)
    needs = [s.get("sort") for s in specs if s["kind"] == "data"]
    return {
        "op": op_name,
        "ledger": mod_name,
        "module": entry.get("module"),
        "category": entry.get("category"),
        "doc": entry.get("doc"),
        "params": specs,
        "presets": presets(op_name),
        "inputs": {sort: producers(sort) for sort in dict.fromkeys(needs) if sort},
        "next": consumers(entry.get("out")) if entry.get("out") else [],
        "preflight": preflight(op_name),
        # 宣言は 1 型でも実体は多態なことが多い。UI が「この型も入る」を出せるよう
        # **実測**して返す(measure=False で省略できる — 一覧表示など数を捌く場面用)。
        "accepts": accepted_sorts(op_name) if measure else {},
    }


# --------------------------------------------------------------------------- #
# `fullseye.*` へ出す別名(名前が一般語すぎるものに op_ を付ける)                #
# --------------------------------------------------------------------------- #
#: `find` / `run` / `path` はトップレベルの名前として一般的すぎるので、公開名は
#: `op_find` / `op_run` / `op_path` にする(モジュール経由 `opassist.find` は不変)。
op_find = find
op_run = run
op_path = path
op_assist = assist
op_presets = presets
op_producers = producers
op_consumers = consumers
op_accepts = accepted_sorts
op_sorts = known_sorts
op_sorts = known_sorts
