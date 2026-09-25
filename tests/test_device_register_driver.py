# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""利用者が自分の装置アダプタを名簿に載せられること(2026-09-26)。

`comm.register` の双子。**同じ問いに答える層は同じ語彙で答える**ことを門にする ——
`comm` は protocol を、`device` は driver を登録するが、引数の名前が層ごとに違うと
読む側は層ごとに学び直すことになる。

3 点セット(接続層の合格線)をここでも要求する:
1. 名簿に出る(`capabilities()` / `drivers()`)
2. **名簿の綴りでそのまま開く**(`open_driver(name)`)
3. 断るときは**次にやることを名指しする**(いまは「register_driver で自分で付けろ」)
"""
from __future__ import annotations

import inspect
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import comm  # noqa: E402
import device  # noqa: E402
import fullseye as fs  # noqa: E402


@pytest.fixture(autouse=True)
def _no_leak():
    """★登録はプロセスに残る。**残すと他の門の数が狂う**

    (`docs/COLLECTION_SIZES.json` の ``device.drivers`` は 12 を要求する)。
    試験の副作用が別の試験の合否を決める状態は、順番を変えた瞬間に嘘になる。

    ★後片付けは**公開の口**でやる。private の辞書を触って消すやり方だと、
    「公開の操作を公開の操作で取り消せない」ことに誰も気づかない
    —— このサンプルを書いていて実際に気づき、`unregister_driver` を足した。

    ★★後片付けを「増えた名前」で数えてはいけない —— **差し替えは名前が増えない**
    ので集合の差は空になり、`dynamixel` の差し替えが次の試験まで生き残った
    (実際にそれで別の試験が落ちた。しかも落ちたのは順番次第なので再現しにくい)。
    名簿の全行に外す口を当てる。同梱の行には効かない(`False` が返る)。
    """
    try:
        yield
    finally:
        for name in list(device.drivers()):
            fs.unregister_driver(name)


class _Fake:
    """開いたことが分かるだけの最小の駆動体。"""

    def __init__(self, **opts):
        self.opts = opts
        self.closed = False

    def close(self):
        self.closed = True


def _register(name="my-plc", **kw):
    kw.setdefault("native", True)
    kw.setdefault("desc", "in-house PLC over its own protocol")
    fs.register_driver(name, lambda **o: _Fake(**o), **kw)


# --------------------------------------------------------------------------- #
# 3 点セット
# --------------------------------------------------------------------------- #
def test_a_registered_driver_is_on_the_menu():
    _register()
    assert "my-plc" in fs.drivers()
    row = [r for r in device.capabilities() if r["name"] == "my-plc"]
    assert len(row) == 1, "名簿に 1 行だけ出ること"
    assert row[0]["implemented"] is True and row[0]["available"] is True
    assert row[0]["desc"] == "in-house PLC over its own protocol"


def test_the_menu_spelling_opens_it():
    _register()
    dev = fs.open_driver("my-plc", host="10.0.0.2", unit=3)
    assert isinstance(dev, _Fake) and dev.opts == {"host": "10.0.0.2", "unit": 3}


def test_every_name_on_the_menu_still_has_a_door_after_registering():
    """★既存の約束を壊していないこと —— 登録した後も名簿の全行が開くか断るかする。"""
    _register()
    for name in fs.drivers():
        try:
            dev = fs.open_driver(name)
            close = getattr(dev, "close", None)
            if callable(close):
                close()
        except device.DeviceError as e:
            assert "None" not in str(e), "断り文句が None を install しろと言っている: %s" % e
        except OSError:
            pass                      # 扉は開いた。線の向こうに相手が居なかっただけ
        except KeyError:              # noqa: PERF203
            pytest.fail("名簿に載っているのに扉が無い: %r" % name)


# --------------------------------------------------------------------------- #
# 名簿の行を自分のもので置き換える
# --------------------------------------------------------------------------- #
def test_registering_a_cataloged_name_makes_it_openable():
    """`dynamixel` は「名簿に在るが開けない」行。自分のアダプタでそこを埋められる。"""
    before = [r for r in device.capabilities() if r["name"] == "dynamixel"][0]
    assert before["implemented"] is False, "前提が崩れている(既に一級アダプタが在る?)"

    _register("dynamixel", native=False, pip="dynamixel-sdk", probe="dynamixel_sdk",
              family="servo", desc="自前の Dynamixel アダプタ")
    after = [r for r in device.capabilities() if r["name"] == "dynamixel"]
    assert len(after) == 1, "同梱の行と登録した行が二重に出ている"
    assert after[0]["implemented"] is True and after[0]["family"] == "servo"
    assert isinstance(fs.open_driver("dynamixel"), _Fake)


def test_replacing_a_row_does_not_change_how_many_rows_there_are():
    n = len(fs.drivers())
    _register("dynamixel")
    assert len(fs.drivers()) == n, "差し替えたのに行が増えた"
    _register("my-plc")
    assert len(fs.drivers()) == n + 1, "新しい名前は 1 行増えるべき"


def test_registration_does_not_leak_into_the_shipped_count():
    """★この門自身が `_no_leak` の見張り —— 後片付けが効いていることを確かめる。"""
    import json

    ledger = json.load(open(os.path.join(ROOT, "docs", "COLLECTION_SIZES.json"),
                            encoding="utf-8"))["sizes"]
    # ★台帳の門は `len(device.drivers())` を数える —— **登録は runtime でそこに
    #   入る**ので、後片付けを忘れた試験が 1 本あるだけで台帳の門が落ちる
    #   (しかも落ちるのは別のファイルなので、原因が遠くなる)。
    assert len(device._BY_NAME) == ledger["device.drivers"], \
        "同梱の名簿の数は登録の有無で動いてはいけない"
    assert len(device.drivers()) == ledger["device.drivers"], \
        "前の試験の登録が残っている(後片付けが効いていない)"
    # ★★**数だけ見る門は差し替えに盲目**。`dynamixel` を自前のもので置き換えても
    #   行は 12 のままなので、台帳の門は緑のまま通る。中身(何が implemented か)
    #   まで見て初めて、登録が残っていないと言える。
    assert not [r for r in device.capabilities() if r["implemented"]
                and r["name"] not in device._OPENABLE], \
        "同梱の実装(io-memory / io-modbus / gpio)以外が implemented になっている"


# --------------------------------------------------------------------------- #
# 断り方
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["dynamixel", "ur-rtde", "franka", "kinova", "ros",
                                  "canopen", "feetech", "robotiq", "xarm"])
def test_a_refusal_points_at_the_way_to_open_it_yourself(name):
    """★断り文句を「待て」で終わらせない。

    直す前は「a first-class Fullseye driver adapter is on the roadmap」で終わって
    いた —— 読んだ人が**今日できること**が 1 つも書いていない。`register_driver`
    を足した以上、断りはその綴りを名指しするべきである。
    """
    with pytest.raises(device.DeviceError) as ei:
        fs.open_driver(name)
    msg = str(ei.value)
    if "has no PyPI package" in msg:
        return                      # ベンダ配布 wheel: 先に手に入れる話が要る
    assert "register_driver" in msg, "断り文句が自分で扉を付ける道を書いていない: %s" % msg
    assert repr(name) in msg, "どの driver の話か書いていない: %s" % msg


def test_a_factory_that_cannot_be_called_is_refused_by_name():
    with pytest.raises(TypeError) as ei:
        fs.register_driver("broken", "not callable")
    assert "broken" in str(ei.value) and "str" in str(ei.value)
    assert "broken" not in fs.drivers(), "拒否したのに名簿に載せている"


def test_an_unknown_name_is_still_a_keyerror_that_lists_the_menu():
    with pytest.raises(KeyError) as ei:
        fs.open_driver("no-such-driver")
    assert "io-memory" in str(ei.value)


# --------------------------------------------------------------------------- #
# 層をまたいだ語彙の一致
# --------------------------------------------------------------------------- #
def test_the_two_registration_doors_use_the_same_words():
    """★`comm.register` と `device.register_driver` の引数名が一致すること。

    同じ問い(「自分のアダプタを足したい」)に層ごとに違う語で答えると、読む側は
    層の数だけ学び直す。`device` 側にだけ在る `family`(名簿の並びの分類)を除き、
    名前・既定値・順序まで揃える。
    """
    theirs = list(inspect.signature(comm.register).parameters)
    mine = [p for p in inspect.signature(device.register_driver).parameters
            if p != "family"]
    # comm 側の implemented は「載せるだけの行」を作るための欄で、登録すれば必ず
    # 開けられる device 側には対応物が無い。
    theirs = [p for p in theirs if p != "implemented"]
    assert mine == theirs, "登録の入口の語彙が層で割れている: device=%s comm=%s" % (mine, theirs)


def test_the_facade_hands_out_the_same_function():
    assert fs.register_driver is device.register_driver
    assert fs.unregister_driver is device.unregister_driver


# --------------------------------------------------------------------------- #
# 足したものは外せる(公開の操作は公開の操作で取り消せる)
# --------------------------------------------------------------------------- #
def test_what_you_registered_can_be_removed_again():
    n = len(fs.drivers())
    _register()
    assert len(fs.drivers()) == n + 1
    assert fs.unregister_driver("my-plc") is True
    assert len(fs.drivers()) == n and "my-plc" not in fs.drivers()
    with pytest.raises(KeyError):
        fs.open_driver("my-plc")


def test_removing_something_that_was_never_there_is_not_an_error():
    assert fs.unregister_driver("never-registered") is False


def test_removing_a_replacement_brings_the_shipped_row_back():
    """★差し替えを外したら**同梱の行が戻る**こと(消えたままにならない)。"""
    _register("dynamixel")
    assert [r for r in device.capabilities() if r["name"] == "dynamixel"][0]["implemented"]
    fs.unregister_driver("dynamixel")
    row = [r for r in device.capabilities() if r["name"] == "dynamixel"]
    assert len(row) == 1 and row[0]["implemented"] is False
    assert row[0]["pip"] == "dynamixel-sdk", "同梱の申告が戻っていない"


def test_a_shipped_driver_cannot_be_removed_by_unregistering():
    """同梱の行は :func:`register_driver` の産物ではないので、外す対象にならない。"""
    assert fs.unregister_driver("io-memory") is False
    assert "io-memory" in fs.drivers(), "同梱の driver が名簿から消えた"


def test_the_comm_twin_refuses_to_remove_a_shipped_protocol():
    """★comm 側も対にした。ただしそちらは**同梱を消せてしまうと重い**ので拒否する

    (`_REGISTRY` に同梱の protocol も入っているため。device 側は登録分だけを
    別の辞書に持つので、構造的に同梱へ届かない)。
    """
    n = len(comm.protocols())
    with pytest.raises(KeyError) as ei:
        comm.unregister_protocol("modbus-tcp")
    assert "ships with Fullseye" in str(ei.value)
    assert len(comm.protocols()) == n

    comm.register("tmp-bus", lambda **o: None, native=True, desc="試験用")
    try:
        assert "tmp-bus" in comm.protocols()
    finally:
        assert comm.unregister_protocol("tmp-bus") is True
    assert len(comm.protocols()) == n


def test_it_is_reachable_by_the_name_the_docs_use():
    doc = open(os.path.join(ROOT, "docs", "CONNECTIVITY.md"), encoding="utf-8").read()
    assert "register_driver" in doc, "使い方が接続層の文書に書かれていない"
