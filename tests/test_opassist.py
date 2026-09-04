"""opassist(op 別の入力補助)の単体テスト。

契約:
  * 台帳の宣言 in 型の本数ぶんだけが**データ入力**、残りがパラメータ。
  * **値型(kind)と容器型(container)は直交する**。kind は number/int/bool/choice/text/data
    だけ、容器は常に container(form / shape / elem / role / labels)。スカラも例外に
    しない(form="scalar", shape=())ので UI の分岐が 1 本で済む。
  * tuple / 行列は「数値 1 個」に潰さない。既定値が tuple のものは形から、
    **既定値が無いもの(center=None / 必須の trans / k_cam)は名前から**構造を補う。
  * 選択肢はモジュールの定数から引く(手で書いた列挙が実体とずれない)。
  * `producers` / `consumers` は台帳の宣言型どおりに引ける。
  * `preflight` は例外を投げない(実行を妨げない)が、実際の失敗配置を検出する。
  * 未知の op は fail-closed(黙って空を返さない)。
"""
import numpy as np
import pytest

import opassist as A


# --------------------------------------------------------------------------- #
# 引数仕様                                                                      #
# --------------------------------------------------------------------------- #
def test_data_inputs_follow_the_ledger_declaration():
    """宣言 in が 1 本なら第 1 引数だけがデータ、残りはパラメータ。"""
    specs = A.param_spec("grating_rgb")
    kinds = [s["kind"] for s in specs]
    assert kinds[0] == "data" and specs[0]["sort"] == "normalmap"
    assert "data" not in kinds[1:]
    names = [s["name"] for s in specs]
    assert names[0] == "normals" and "pitch_um" in names


def test_two_input_op_marks_both_as_data():
    specs = A.param_spec("absolute_phase")            # in = ["image2d", "image2d"]
    data = [s for s in specs if s["kind"] == "data"]
    assert len(data) == 2
    assert all(s["sort"] == "image2d" for s in data)


def test_units_come_from_the_parameter_name():
    by = {s["name"]: s for s in A.param_spec("grating_rgb")}
    assert by["pitch_um"]["unit"] == "µm"
    assert by["width_nm"]["unit"] == "nm"
    by2 = {s["name"]: s for s in A.param_spec("slab_transmittance")}
    assert by2["thickness_mm"]["unit"] == "mm"
    assert by2["sigma_per_mm"]["unit"] == "1/mm"


def test_choices_are_read_from_the_module_constants():
    """列挙を手書きしない: 実体(METALS / FINISHES)から引くのでずれない。"""
    import glassmirror
    import metalfinish
    by = {s["name"]: s for s in A.param_spec("finish_shade")}
    assert by["metal"]["kind"] == "choice"
    assert by["metal"]["choices"] == list(glassmirror.METALS)
    assert by["kind"]["choices"] == list(metalfinish.FINISHES)
    pol = {s["name"]: s for s in A.param_spec("fresnel_dielectric")}["polarization"]
    assert pol["kind"] == "choice" and "unpolarized" in pol["choices"]


def test_unknown_op_is_fail_closed():
    with pytest.raises(ValueError, match="unknown op"):
        A.param_spec("no_such_op_at_all")
    with pytest.raises(ValueError, match="unknown op"):
        A.assist("no_such_op_at_all")


# --------------------------------------------------------------------------- #
# tuple / 行列などの複合データ形式                                              #
# --------------------------------------------------------------------------- #
def test_tuple_default_keeps_its_shape_and_labels():
    by = {s["name"]: s for s in A.param_spec("grating_rgb")}
    light = by["light"]
    assert light["kind"] == "number"                  # 値型は数値
    assert light["container"]["form"] == "vector"     # 容器はベクトル
    assert light["container"]["shape"] == (3,)
    assert light["container"]["labels"] == ["x", "y", "z"]
    orders = by["orders"]
    assert orders["kind"] == "int"
    assert orders["container"]["form"] == "list"      # 可変長(次数は増やせる)
    assert orders["container"]["shape"] == (None,)


def test_tuple_without_a_default_is_still_recognised():
    """★ 既定値が tuple で与えられていない引数がある —— そこを名前で補う。

    `center=None`(省略可の (row,col))、必須の `trans`(3 ベクトル)、`k_cam`(3x3)。
    既定値だけを見ると「数値 1 個」に見え、UI が spin box を 1 個出して破綻する。
    """
    by = {s["name"]: s for s in A.param_spec("triangulate_column")}
    assert by["trans"]["container"]["shape"] == (3,)
    assert by["trans"]["container"]["labels"] == ["x", "y", "z"]
    assert by["k_cam"]["container"]["form"] == "matrix"
    assert by["k_cam"]["container"]["shape"] == (3, 3)
    assert by["rot"]["container"]["form"] == "matrix"
    center = {s["name"]: s for s in A.param_spec("finish_shade")}["center"]
    assert center["container"]["role"] == "point"


def test_nested_tuple_is_reported_as_bounds():
    by = {s["name"]: s for s in A.param_spec("integrate")}
    assert by["bounds"]["container"]["form"] == "nested"
    assert by["bounds"]["container"]["role"] == "bounds"
    assert len(by["bounds"]["container"]["shape"]) == 2


def test_shape_wins_over_the_name_hint_when_they_disagree():
    """名前は当てにならない: 3 要素のはずの役割に 5 要素が来たら**形を優先**する。"""
    st = A._seq_structure("light", (1.0, 2.0, 3.0, 4.0, 5.0))
    assert st["role"] == "list_number" and st["labels"] is None
    st3 = A._seq_structure("light", (0.0, 0.0, 1.0))
    assert st3["role"] == "vector3" and st3["labels"] == ["x", "y", "z"]


def test_every_ledger_op_has_a_spec_and_no_crash():
    """全台帳 op で仕様が取れる(署名が読めない op でも例外にしない)。"""
    ops = A.known_ops()
    assert len(ops) > 300
    bad = []
    for name in ops:
        try:
            specs = A.param_spec(name)
        except Exception as exc:                       # noqa: BLE001
            bad.append((name, repr(exc)))
            continue
        for s in specs:
            # 値型と容器型が直交していること(統一スキーマ)
            assert s["kind"] in ("data", "number", "int", "bool", "choice", "text"), (name, s)
            c = s["container"]
            assert c["form"] in ("scalar", "vector", "matrix", "list", "nested", "data"), (name, s)
            assert isinstance(c["shape"], tuple), (name, s)
            if c["form"] == "scalar":
                assert c["shape"] == ()
            if c["labels"] is not None:
                assert len(c["labels"]) == c["shape"][0], (name, s)
    assert not bad, bad[:5]


# --------------------------------------------------------------------------- #
# プリセット / 導線                                                             #
# --------------------------------------------------------------------------- #
def test_presets_only_name_real_parameters():
    """プリセットのキーが実在の引数名であること(綴り違いを持ち込まない)。"""
    for op, table in A.PRESETS.items():
        names = {s["name"] for s in A.param_spec(op)}
        for label, kw in table.items():
            unknown = set(kw) - names
            assert not unknown, (op, label, unknown)


def test_presets_actually_run():
    """CD / DVD / BD のプリセットで実際に呼べる(値が古びていない)。"""
    import matappear
    n = A._sample_normalmap()
    for label, kw in A.presets("grating_rgb").items():
        out = matappear.grating_rgb(n, light=(0.0, 0.55, 0.83), **kw)
        assert out.shape == n.shape and np.isfinite(out).all(), label


def test_producers_and_consumers_follow_the_ledger():
    prod = A.producers("normalmap")
    assert "tangent_field" in prod and "micro_normals" in prod
    cons = A.consumers("normalmap")
    assert "grating_rgb" in cons and "finish_shade" in cons
    assert A.producers("no_such_sort") == []
    with pytest.raises(ValueError):
        A.producers("")


# --------------------------------------------------------------------------- #
# 前提チェック                                                                  #
# --------------------------------------------------------------------------- #
def test_preflight_catches_the_grating_layout_mistake():
    """★ 実際に踏んだ失敗: 溝と同じ向きに照らすと色が出ない(バグではなく配置)。"""
    along = A.preflight("grating_rgb", {"tangent": (1, 0, 0), "light": (0.35, 0, 0.94),
                                        "view": (0, 0, 1)})
    across = A.preflight("grating_rgb", {"tangent": (1, 0, 0), "light": (0, 0.55, 0.83),
                                         "view": (0, 0, 1)})
    assert along and "溝" in along[0]
    assert not across


def test_preflight_catches_impossible_total_internal_reflection():
    assert A.preflight("critical_angle_deg", {"n1": 1.0, "n2": 1.5})
    assert not A.preflight("critical_angle_deg", {"n1": 1.5, "n2": 1.0})


def test_preflight_never_raises():
    for name in ("grating_rgb", "critical_angle_deg", "thin_film_reflectance",
                 "slab_transmittance", "oren_nayar", "corrosion_mask"):
        assert isinstance(A.preflight(name, {"garbage": object()}), list)
    assert A.preflight("no_such_op", {}) == []         # 未知でも落ちない(補助層なので)


# --------------------------------------------------------------------------- #
# 試せる入力 / まとめ                                                           #
# --------------------------------------------------------------------------- #
def test_sample_input_actually_runs_the_op():
    import opsoptics
    for name in ("grating_rgb", "thin_film_rgb", "ward_anisotropic", "oren_nayar",
                 "sheen_shade", "finish_shade"):
        args, kwargs = A.sample_input(name)
        out = opsoptics.get(name)(*args, **kwargs)
        assert np.isfinite(np.asarray(out, float)).all(), name


def test_assist_bundles_everything_for_a_ui():
    info = A.assist("finish_shade")
    assert info["op"] == "finish_shade" and info["ledger"] == "opsoptics"
    assert info["module"] == "metalfinish" and info["category"] == "finish"
    assert any(s["kind"] == "choice" for s in info["params"])
    assert "normalmap" in info["inputs"] and info["inputs"]["normalmap"]
    assert isinstance(info["next"], list)
    assert isinstance(info["preflight"], list)


# --------------------------------------------------------------------------- #
# 多態性(宣言ではなく実測)                                                     #
# --------------------------------------------------------------------------- #
def test_accepted_sorts_measures_real_polymorphism():
    """★ 台帳は 1 op に 1 入力型しか書けないが、実体は多態なことが多い。

    要素ごとの演算は `signal` と宣言していても image2d / voxel / rgbimage を通す。
    数えられていない多態性は「無い」のと同じなので、宣言ではなく**実測**で出す。
    """
    r = A.accepted_sorts("fresnel_dielectric")
    assert r["signal"] == "declared"
    works = {k for k, v in r.items() if v == "works"}
    assert {"image2d", "voxel"} <= works, r
    # 断るときは ValueError(素の例外を漏らさない)= 番人が効いている
    assert "error" not in set(r.values()), r


def test_accepted_sorts_respects_fail_closed_ops():
    """形の契約が固い op は宣言以外を**断る**(通ってしまう方が問題)。"""
    r = A.accepted_sorts("oren_nayar")
    assert r["normalmap"] == "declared"
    assert r.get("points") in ("rejected", "error")
    assert r.get("signal") == "rejected"


def test_assist_can_skip_the_measurement():
    fast = A.assist("oren_nayar", measure=False)
    assert fast["accepts"] == {}
    full = A.assist("oren_nayar")
    assert full["accepts"]["normalmap"] == "declared"


# --------------------------------------------------------------------------- #
# 使いやすさ: 探す / すぐ動かす / 型を繋ぐ                                       #
# --------------------------------------------------------------------------- #
def test_find_searches_name_doc_and_category():
    """やりたいことの言葉(日本語も)で op に辿り着ける。"""
    assert "grating_rgb" in [h["op"] for h in A.find("回折")]
    assert "corrosion_mask" in [h["op"] for h in A.find("錆")]
    names = [h["op"] for h in A.find("fresnel")]
    assert names[0].startswith("fresnel")               # 名前一致が説明一致より上
    assert A.find("zzz-nothing-matches") == []
    with pytest.raises(ValueError):
        A.find("   ")


def test_run_resolves_presets_and_returns_the_declared_type():
    import opsoptics
    n = A._sample_normalmap()
    out, notes = A.run("grating_rgb", n, preset="CD (1.6 µm)", light=(0.0, 0.55, 0.83))
    assert out.shape == n.shape and notes == []
    # 明示指定はプリセットより強い
    a, _ = A.run("grating_rgb", n, preset="CD (1.6 µm)", pitch_um=0.32,
                 light=(0.0, 0.55, 0.83))
    b, _ = A.run("grating_rgb", n, preset="Blu-ray (0.32 µm)", light=(0.0, 0.55, 0.83))
    assert np.allclose(a, b)
    with pytest.raises(ValueError, match="unknown preset"):
        A.run("grating_rgb", n, preset="No Such Disc")


def test_run_works_with_no_arguments_at_all():
    """引数ゼロで動く = 「とりあえず押せば結果が出る」入口。"""
    for name in ("oren_nayar", "sheen_shade", "thin_film_rgb", "corrosion_mask"):
        out, notes = A.run(name)
        assert np.isfinite(np.asarray(out, float)).all(), name
        assert isinstance(notes, list)


def test_run_returns_the_ledger_declared_value_not_the_raw_tuple():
    """素の関数がタプルを返す op でも、宣言 out 型で受け取れる(呼び手が剥がさない)。"""
    out, _ = A.run("rough_transmission", np.array([1.0]), roughness=0.3)
    assert isinstance(out, np.ndarray) and out.shape[-1] == 2


def test_run_strict_turns_preflight_notes_into_errors():
    n = A._sample_normalmap()
    out, notes = A.run("grating_rgb", n, tangent=(1, 0, 0), light=(0.35, 0.0, 0.94))
    assert notes and out is not None                    # 既定は警告のみで実行する
    with pytest.raises(ValueError, match="preflight"):
        A.run("grating_rgb", n, tangent=(1, 0, 0), light=(0.35, 0.0, 0.94), strict=True)


def test_path_finds_a_shortest_chain_between_types():
    one = A.path("normalmap", "rgbimage")
    assert one and all(len(c) == 1 for c in one)
    assert "finish_shade" in {c[0] for c in one}
    longer = A.path("coordgrid", "mesh")
    assert longer and all(len(c) == len(longer[0]) for c in longer)
    assert longer[0][0] in ("box_sdf", "sphere_sdf")
    assert A.path("image2d", "image2d") == [[]]         # 同じ型は 0 段
    assert A.path("normalmap", "no_such_sort") == []
