# -*- coding: utf-8 -*-
"""★PoC を**実際に走らせる**門。

## なぜ要るか(2026-09-06)

この日まで、`examples/poc_*.py` を実行するテストは 1 本も無かった。
`test_examples2d.py` は「登録と実体が一致するか」を見るだけ、
`test_example_figures.py` は「図の配線があるか」を静的に見るだけ。
つまり **32 本の看板作品が、誰にも走らされないまま置かれていた**。

結果として **4 本が exit 1 のまま気づかれずにいた** —— しかもどれも
「記録した穴が塞がったら鳴る」ように自分で仕掛けた assert で、
仕掛けは正しく鳴っていたのに、鳴らす人がいなかった:

* `poc_registration_basin` —— `fpfh` が回転不変になった(穴が塞がった)
* `poc_lightfield_depth` —— `disparity_subpixel` が divide 警告を出さなくなった
* `poc_dimensional_inspection` —— 届かないはずの 14 関数が公開経路から届くようになった
* `poc_ct_fidelity` —— 検出器数で質量欠損が動かなくなった(ランプの DC 項を直した副産物)

「登録済みを数える門は未登録に盲目」と同じ形で、**実行しない門は
実行時の壊れに盲目**だった。

## 費用

31 本を直列に走らせると 425 秒、6 並列なら **85 秒**(2026-09-06 実測、
この機械)。ここでは 1 つのセッション用フィクスチャで**まとめて並列に**
走らせ、各 PoC はその結果を見るだけにしてある —— こうすると
「どの PoC が落ちたか」が個別に出るのに、時間は 1 回ぶんで済む。
"""
from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: 同時に走らせる本数。上げすぎると 1 本あたりが遅くなって timeout に近づく。
WORKERS = 6

#: 1 本あたりの上限[秒]。いちばん重い `poc_motion_magnification` が 62 秒
#: (単独)、6 並列だと 2 倍近くになるので余裕を持たせる。
PER_SCRIPT_TIMEOUT = 600


def _poc_paths() -> list[Path]:
    return sorted((ROOT / "examples").glob("poc_*.py"))


def _run_one(path: Path) -> tuple[str, int, str]:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    # 図は書かせない(この門が見るのは数値の側。図の配線は
    # `test_example_figures.py` が別に見る)。
    env.pop("FULLSEYE_FIGURE_DIR", None)
    try:
        r = subprocess.run([sys.executable, str(path)], env=env,
                           cwd=str(path.parent), capture_output=True,
                           timeout=PER_SCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return path.name, -1, "%d 秒で返ってこなかった" % PER_SCRIPT_TIMEOUT
    # ★失敗時は stdout の末尾も返す。PoC は所見と「どの検査が落ちたか」を
    # stdout に印字して SystemExit(1) するので、stderr だけだと**空のまま
    # 「exit 1」しか分からない**(2026-09-07 の CI、py3.10 の poc_ct_fidelity)。
    tail = (r.stderr.decode("utf-8", "replace")[-1200:]
            + chr(10) + "--- stdout(末尾) ---" + chr(10)
            + r.stdout.decode("utf-8", "replace")[-1200:])
    if r.returncode == 0:
        out = r.stdout.decode("utf-8", "replace")
        if "\nPASS" not in out:
            # ★2026-09-07: ここは長らく **0 を返していた** ので、下の
            # `assert code == 0` を素通りしていた —— 合否を計算した直後に
            # 捨てる門(実測: PASS を一度も印字しない PoC が 3 本 ——
            # poc_dic_strain / poc_photoelasticity / poc_thermography_ndt)。
            # -2 を返して落ちるようにする。
            return path.name, -2, ("exit 0 だが PASS を印字していない"
                                   + chr(10) + "--- stdout(末尾) ---"
                                   + chr(10) + out[-1200:])
    return path.name, r.returncode, tail


@pytest.fixture(scope="session")
def poc_results() -> dict:
    """全 PoC をまとめて並列に走らせ、``{名前: (exit, 抜粋)}`` を返す。"""
    paths = _poc_paths()
    out: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, code, tail in ex.map(_run_one, paths):
            out[name] = (code, tail)
    return out


@pytest.mark.parametrize("name", [p.name for p in _poc_paths()])
def test_the_poc_runs_clean(poc_results, name):
    """★PoC は 1 本残らず exit 0 で終わり、``PASS`` を印字すること。

    落ちたときは**直す前に読むこと**: この repo の PoC は「いま在る穴」を
    assert で固定してある。だから落ちた理由は 2 つに 1 つで、
    **穴が塞がった**(所見と assert を書き換える)か、
    **本当に壊れた**(実装を直す)。assert を消して通すのは**どちらでもない**。
    """
    code, tail = poc_results[name]
    assert code == 0, "%s が exit %d:\n%s" % (name, code, tail)


def test_the_gate_actually_sees_all_of_them():
    """門が空振りしていないこと(数える側の検算)。"""
    assert len(_poc_paths()) >= 31, [p.name for p in _poc_paths()]
