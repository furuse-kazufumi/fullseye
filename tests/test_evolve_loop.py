# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""進化型アルゴリズム開発環境(tools/evolve_loop)の契約テスト。

この driver の価値は自動化そのものではなく、**判定を通った op だけが語彙に入る**
という規律にある。だから固定すべき契約は次の 3 つ:

  1. 段の責務が混ざらないこと(``screen`` は「土俵に乗るか」だけを見て、
     有用性は判定しない — それは ``gate`` の仕事)。
  2. **落としたものが必ず数えられる**こと(無言の切り捨て禁止)。
  3. 名前解決が勝手に似た op へ寄らないこと(別の op を実行したら評価が嘘になる)。
"""
import sys

import pytest

pytest.importorskip("scipy")

sys.path.insert(0, "tools")

import ops                                              # noqa: E402
import problems                                         # noqa: E402
from evolve_loop import MAX_CHAIN_LEN, _registry_name, screen  # noqa: E402


def _cand(ops_chain, start="image", deterministic=True, out_type=None):
    return {"ops": list(ops_chain), "start": start,
            "deterministic": deterministic, "out_type": out_type or start}


def test_screen_counts_every_drop_with_a_reason():
    """落選は理由つきで必ず数える(無言の切り捨て禁止)。"""
    cands = [
        _cand([]),                                       # 空
        _cand(["gaussian"] * (MAX_CHAIN_LEN + 1)),       # 長すぎる
        _cand(["gaussian"], deterministic=False),        # 非決定的
        _cand(["x"], start="jones"),                     # 課題が受け付けない型
        _cand(["gaussian"]),                             # 残る
    ]
    kept, dropped = screen(cands, problems)
    assert len(kept) == 1
    assert sum(dropped.values()) == 4, dropped
    assert any("空" in r for r in dropped)
    assert any("長すぎる" in r for r in dropped)
    assert any("非決定的" in r for r in dropped)
    assert any("受け付けない" in r for r in dropped)


def test_screen_does_not_judge_usefulness():
    """恒等に近い連鎖でも screen は落とさない(有用性の判定は gate の責務)。

    段の責務が混ざると、安い判定で本物の発見を捨てたことに誰も気づけなくなる。
    """
    kept, _ = screen([_cand(["identity"])], problems)
    assert len(kept) == 1


def test_screen_accepts_only_sorts_the_workload_can_evaluate():
    """課題が持たない入力 sort は評価不能 = 通しても意味が無い。"""
    accepted = {p.in_sort for p in problems.PROBLEMS.values()}
    assert "image" in accepted, "前提が崩れている(image problem が無い)"
    kept, _ = screen([_cand(["gaussian"], start="image2d"),
                      _cand(["v"], start="voxel"),
                      _cand(["m"], start="matrix")], problems)
    starts = {c["start"] for c in kept}
    assert "matrix" not in starts


def test_registry_name_resolves_bridge_prefix_and_never_guesses():
    """カタログ名 → 進化レジストリ名。無ければ KeyError(似た名前へ寄せない)。"""
    assert _registry_name(ops, "gaussian") == "gaussian"
    bridged = [o.name for o in ops.REGISTRY if o.category == "typed"]
    if bridged:
        catalog_name = bridged[0][len("tb_"):]
        assert _registry_name(ops, catalog_name) == bridged[0]
    with pytest.raises(KeyError):
        _registry_name(ops, "definitely_not_an_op_name_xyz")
    # 部分一致で勝手に寄らない(gaussian が居ても gauss は解決しない)
    with pytest.raises(KeyError):
        _registry_name(ops, "gauss")
