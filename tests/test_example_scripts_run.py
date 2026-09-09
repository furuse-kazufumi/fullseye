# -*- coding: utf-8 -*-
"""★PoC **以外**の 2-D 例も、実際に走らせる門。

## なぜ要るか(2026-09-09)

2026-09-06 に「PoC を走らせる門が 1 本も無い」ことが分かり、`test_poc_scripts_run.py`
を作った。そのとき **PoC しか見ていなかった**。台帳 `examples2d.EXAMPLES` は 199 件で、
うち `poc_*` は 116 件。**残り 83 件を実行する門は、その日も無いままだった。**

「登録済みを数える門は未登録に盲目」と同じ形が、1 つ内側で再演していた ——
*走らせる門を作ったのに、走らせる対象を数え直さなかった*。

実測(2026-09-09、83 本を副プロセスで): **2 本が exit 1**。どちらも同じ型で、
repo 直下のモジュール(`pivops` / `profileops`)を import するのに `sys.path` へ
repo 直下を足しておらず、**チェックアウトからそのまま走らせると
ModuleNotFoundError** になっていた(他の 81 本は家の作法どおり足していた)。

## この門が PYTHONPATH を**渡さない**理由

`test_poc_scripts_run.py` は長らく `PYTHONPATH=<repo>` を渡していた。渡すと
上の 2 本は**通ってしまう** —— 門が事故の起きる場所に立っていないことになる。
利用者は `py -3.11 examples/<name>.py` と打つだけで、環境変数は設定しない。
だからここでは**利用者と同じ条件**(PYTHONPATH 無し、cwd は repo 直下)で走らせる。

## 費用

83 本を直列で 273 秒(この機械、2026-09-09 実測)。いちばん重いのは
`quickstart` の 81.5 秒。並列にまとめて 1 回だけ走らせ、各テストは結果を見るだけ。
"""
from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examples2d as EX2                                  # noqa: E402
from conftest import FULL_REGISTRY_BACKENDS, _have_backend, requires_backend  # noqa: E402

#: 例ごとに要る optional backend(空 = numpy+scipy だけで走る)。
#:
#: ★2026-09-09、この門を入れた最初の CI で **7 本が py3.12 で落ちた**(py3.11 は緑)。
#: CI は意図的に **py3.11 だけ** torch / kornia / mahotas / opencv-contrib を入れ、
#: 他の版では入れない。テスト側には ``requires_backend`` という宣言の仕組みが既に
#: あったのに、**例を走らせる門にはそれが無かった** —— 仕組みがあることと、
#: 全経路が通っていることは別。
#:
#: ``gallery2d_*`` は「その族の op を全部動かす」ギャラリーなので、契約そのものが
#: **どの backend が入っているかに依存する**(op 名を直書きしてレジストリと突き合わせ、
#: 1 つでも欠けると「OPS に余分」で落ちる)。だから族ごと宣言する。残り 2 本は
#: torch を直に使う(``fit_zernike`` / ``match_logpolar_z``)。
#: 完全環境(CI の py3.11、``FULLSEYE_REQUIRE_OPTIONAL=1``)では skip が**失敗**に
#: なるので、宣言の付け過ぎも付け忘れも両方向で落ちる。
NEEDS = {
    "lens_design_demo": ("torch",),
    "representation_conversion": ("torch",),
}


def _needs(stem: str) -> tuple:
    if stem.startswith("gallery2d_"):
        return FULL_REGISTRY_BACKENDS
    return NEEDS.get(stem, ())


#: 同時に走らせる本数。共有ランナー(2〜4 vCPU)では CPU 数に合わせる。
WORKERS = max(2, min(8, (os.cpu_count() or 4)))

#: 1 本あたりの上限[秒]。単独で最長の `quickstart` が 81 秒なので、並列で
#: 数倍に伸びても届く余裕を取る。
PER_SCRIPT_TIMEOUT = 600


def _targets() -> list[Path]:
    """台帳にある 2-D 例のうち ``poc_*`` **以外**(あちらは別の門が見る)。"""
    return [ROOT / "examples" / (e["id"] + ".py")
            for e in EX2.EXAMPLES if not e["id"].startswith("poc_")]


def _run_one(path: Path) -> tuple[str, int, str]:
    # ★PYTHONPATH を渡さない(この門の要点)。利用者は環境変数を設定しない。
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    # 図は書かせない —— 図の配線は `test_example_figures.py` が別に見る。
    env.pop("FULLSEYE_FIGURE_DIR", None)
    try:
        r = subprocess.run([sys.executable, str(path)], env=env, cwd=str(ROOT),
                           capture_output=True, timeout=PER_SCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return path.name, -1, "%d 秒で返ってこなかった" % PER_SCRIPT_TIMEOUT
    tail = (r.stderr.decode("utf-8", "replace")[-1200:]
            + chr(10) + "--- stdout(末尾) ---" + chr(10)
            + r.stdout.decode("utf-8", "replace")[-800:])
    return path.name, r.returncode, tail


@pytest.fixture(scope="session")
def example_results() -> dict:
    """対象をまとめて並列に走らせ、``{名前: (exit, 抜粋)}`` を返す。"""
    out: dict = {}
    # backend が足りない例は**走らせない**(走らせれば必ず ImportError で落ちる)。
    # 合否は各テスト先頭の `requires_backend` が決める —— skip として正直に出る。
    runnable = [p for p in _targets()
                if all(_have_backend(b) for b in _needs(p.stem))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, code, tail in ex.map(_run_one, runnable):
            out[name] = (code, tail)
    return out


@pytest.mark.timeout(5400)
@pytest.mark.parametrize("name", [p.name for p in _targets()])
def test_the_example_runs_from_a_bare_checkout(example_results, name):
    """例は 1 本残らず exit 0 で終わること(PYTHONPATH 無しで)。

    ★``PASS`` の印字は求めない —— PoC と違ってこれらは見せるための例で、
    主張を assert するものではないから。ここで見るのは「利用者が打つとおりに
    打って、最後まで走るか」だけ。
    """
    code, tail = example_results[name]
    assert code == 0, "examples/%s が exit %s\n%s" % (name, code, tail)


def test_every_registered_2d_example_is_covered_by_one_of_the_two_gates():
    """台帳の 2-D 例は、**全件**どちらかの門が走らせること。

    ★この検査が本体。2026-09-06 に PoC の門を作ったとき、対象を数え直さなかった
    せいで 83 件が外に残った。ここで台帳から引き算しておけば、次に例を足した人が
    どちらの門にも入れ忘れることができない。
    """
    listed = {e["id"] for e in EX2.EXAMPLES}
    poc = {i for i in listed if i.startswith("poc_")}
    mine = {p.stem for p in _targets()}
    assert poc | mine == listed, "どちらの門にも入っていない例: %s" % sorted(
        listed - (poc | mine))
    missing = [p.name for p in _targets() if not p.exists()]
    assert not missing, "台帳にあるのにファイルが無い: %s" % missing
