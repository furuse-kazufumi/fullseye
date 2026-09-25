# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`device.capabilities()` が名乗る 12 の driver に、全部「扉」が在ることを見る門。

★2026-09-25 の実測: `device.capabilities()` は **12 driver** を名乗るのに、Fullseye
から開ける口が在ったのは `DigitalIO` の **3 backend** だけだった。残り 9(dynamixel /
ur-rtde / xarm / ROS …)には**入口が 1 つも無い** —— 名簿には載っているのに、そこから
何かを始める方法が無い。しかも開ける 3 つですら、**名簿の綴りと構築子の綴りが違う**
(`io-modbus` と `DigitalIO("modbus")`)ので、名簿を読んでそのまま渡すと `ValueError`
になっていた。

同じ問いに `comm` は既に答えている: `comm.open_channel` は、開けない protocol にも
**何を入れればよいか名指しする** `CommError` を返す。つまりこれは「機能が無い」のでは
なく、**片側の入口だけが塞がれていた**型([[feedback_a_fix_leaves_the_twin_surface_open]])。

★ここで固定する主張は 2 つだけで、**どの環境でも測れる**ものにしてある:

1. **名簿に載る名前は、全部 `open_driver` が知っている**(開くか、`DeviceError` で
   断るか。`KeyError` や素の例外は落ちる)。SDK が入っているかどうかは環境で変わる
   ので、**開けたかどうかは主張しない**。
2. **断り文句は、何を入れればよいかを言う**(driver 名と、pip 名 or import 名)。
   「使えません」とだけ言う口は、口が無いのとほとんど変わらない。
"""
from __future__ import annotations

import inspect

import pytest

import device
import fullseye


# --------------------------------------------------------------------------- #
# 門の本体(壊して確かめられるように、判定は関数に出す)                          #
# --------------------------------------------------------------------------- #
#: ★**「相手が居ない」は「扉が無い」ではない。** この門を最初に書いたとき、
#: ``io-modbus`` が ``ConnectionRefusedError`` で落ちて 1 件挙がった —— が、それは
#: 「PLC に届く口が在って、線の先に誰も居なかった」ということで、口が無いのとは
#: **正反対**である。だから「この install が実際に開ける driver」からの ``OSError``
#: は通す。一緒くたにすると、門は CI に PLC を繋げと要求し始める —— 繋がりようの
#: ない要求をする門は、やがて外される。
def _assert_every_name_on_the_menu_has_a_door(names, opener, openable=()) -> None:
    """名簿の名前を 1 つずつ開けてみて、**扉の有無**だけを見る。

    *openable* はこの install が実際に開ける driver の集合(上の ★ を参照)。
    """
    missing, mute = [], []
    for name in names:
        try:
            got = opener(name)
        except device.DeviceError as e:
            msg = str(e)
            if name not in msg:
                mute.append((name, "断り文句が driver 名を言わない: %s" % msg))
            continue
        except OSError as e:
            if name not in openable:
                missing.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        except Exception as e:                       # KeyError も素の RuntimeError も駄目
            missing.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        if got is None:
            missing.append((name, "None を返した(開いたのか断ったのか分からない)"))
        else:
            _close(got)
    assert not missing, (
        "名簿に載っているのに扉が無い driver が %d 件: %s —— `open_driver` は開くか "
        "`DeviceError` で断るかのどちらかであること" % (len(missing), missing))
    assert not mute, "断り文句が何も教えていない: %s" % (mute,)


def _assert_every_refusal_names_what_is_needed(names, opener, catalogue) -> None:
    """断るときは **pip 名 or import 名**を必ず言う(入れれば動く、が分かること)。"""
    vague = []
    for name in names:
        try:
            got = opener(name)
        except device.DeviceError as e:
            msg = str(e)
            _n, module, pip, _kind, _family, _desc = catalogue[name]
            hints = [h for h in (module, pip) if h]
            #: ★pip も import 名も持たない driver は名簿に無い(在れば、その行が
            #: 「何も分からない行」なので、ここで落ちてよい)。
            if not hints or not any(h in msg for h in hints):
                vague.append((name, msg))
            continue
        except Exception:
            continue                                  # 扉の有無は別の門が見る
        else:
            _close(got)
    assert not vague, (
        "断り文句に入れるべき SDK 名が無い: %s —— pip 名か import 名のどちらかを "
        "必ず書くこと" % (vague,))


def _close(obj) -> None:
    try:
        obj.close()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# 実物に当てる                                                                   #
# --------------------------------------------------------------------------- #
def test_the_name_list_and_the_menu_agree():
    """`drivers()` と `capabilities()` は同じ名簿を見ていること。"""
    assert device.drivers() == sorted(c["name"] for c in device.capabilities())


def test_every_name_on_the_menu_can_be_opened_or_is_refused_by_name():
    _assert_every_name_on_the_menu_has_a_door(
        device.drivers(), device.open_driver, openable=set(device._OPENABLE))


def test_every_refusal_names_the_sdk_to_install():
    _assert_every_refusal_names_what_is_needed(
        device.drivers(), device.open_driver, device._BY_NAME)


def test_an_unknown_driver_is_a_key_error_that_lists_the_known_ones():
    """名簿に無い名前だけが `KeyError`(綴り間違いと「未対応」を混ぜない)。"""
    with pytest.raises(KeyError) as e:
        device.open_driver("ur-rtde-typo")
    for name in ("ur-rtde", "io-memory"):
        assert name in str(e.value), "既知の名前を並べていない"


def test_the_native_driver_really_opens_and_takes_its_options():
    """`io-memory` は**実際に開いて動く**(断り文句だけの口ではない)。"""
    io_ = device.open_driver("io-memory", initial={3: True})
    try:
        assert io_.get(3) is True, "opts が DigitalIO に渡っていない"
        io_.set(0, True)
        assert io_.get(0) is True
    finally:
        _close(io_)


def test_the_catalogue_spelling_is_translated_to_the_backend_spelling():
    """★名簿の綴り(`io-modbus`)を構築子の綴り(`modbus`)に**訳している**こと。

    ハードにも PLC にも触らずに確かめる —— `_open` を差し替えて、渡された backend
    の綴りだけを見る(`io-modbus` を開くと実際に TCP を叩きに行ってしまう)。
    """
    seen = {}
    orig = device.DigitalIO._open
    device.DigitalIO._open = lambda self: seen.__setitem__(self.backend, True)
    try:
        for name, backend in sorted(device._OPENABLE.items()):
            seen.clear()
            device.open_driver(name)
            assert backend in seen, "%s が backend %r に訳されていない" % (name, backend)
    finally:
        device.DigitalIO._open = orig


def test_every_backend_the_map_names_is_actually_dispatched():
    """訳した先を `DigitalIO._open` が本当に分岐していること(訳し先の存在確認)。"""
    src = inspect.getsource(device.DigitalIO._open)
    for name, backend in sorted(device._OPENABLE.items()):
        assert '== "%s"' % backend in src, (
            "%s の訳し先 %r を DigitalIO._open が知らない(ValueError になる)"
            % (name, backend))


def test_the_facade_exports_the_same_door():
    """公開パッケージの口から**同じ関数**に届くこと(export の抜けを止める)。"""
    assert fullseye.open_driver is device.open_driver
    assert fullseye.drivers is device.drivers
    assert fullseye.DeviceError is device.DeviceError
    for name in ("open_driver", "drivers", "DeviceError"):
        assert name in fullseye.__all__, "__all__ に %r が無い" % name


def test_the_device_error_is_catchable_as_a_runtime_error():
    """★既に `RuntimeError` で捕まえている呼び出し側を壊さないこと。"""
    assert issubclass(device.DeviceError, RuntimeError)


# --------------------------------------------------------------------------- #
# 門を壊して確かめる                                                             #
# --------------------------------------------------------------------------- #
def test_the_door_gate_catches_a_driver_with_no_entry_point():
    """名簿に在るのに `KeyError` になる driver を落とすこと(これが実際の欠陥の形)。"""
    def opener(name):
        if name == "xarm":
            raise KeyError(name)
        return device.open_driver(name)

    with pytest.raises(AssertionError) as e:
        _assert_every_name_on_the_menu_has_a_door(
            device.drivers(), opener, openable=set(device._OPENABLE))
    assert "扉が無い" in str(e.value) and "xarm" in str(e.value)


def test_the_door_gate_catches_a_refusal_that_is_not_a_device_error():
    """素の `RuntimeError` で断る口も落とす(呼び出し側が区別できない)。"""
    def opener(name):
        if name == "ros":
            raise RuntimeError("no")
        return device.open_driver(name)

    with pytest.raises(AssertionError) as e:
        _assert_every_name_on_the_menu_has_a_door(
            device.drivers(), opener, openable=set(device._OPENABLE))
    assert "ros" in str(e.value)


def test_the_message_gate_catches_a_refusal_that_names_nothing():
    """「使えません」とだけ言う口を落とすこと。"""
    def opener(name):
        raise device.DeviceError("driver %r is not available" % name)

    with pytest.raises(AssertionError) as e:
        _assert_every_refusal_names_what_is_needed(
            device.drivers(), opener, device._BY_NAME)
    assert "SDK 名が無い" in str(e.value)


def test_the_backend_dispatch_gate_catches_a_map_that_points_nowhere():
    """訳し先が存在しない対応表を落とすこと。"""
    orig = dict(device._OPENABLE)
    device._OPENABLE["io-memory"] = "memroy"          # 綴り間違い
    try:
        with pytest.raises(AssertionError) as e:
            test_every_backend_the_map_names_is_actually_dispatched()
        assert "知らない" in str(e.value)
    finally:
        device._OPENABLE.clear()
        device._OPENABLE.update(orig)


def test_the_door_gate_does_not_mistake_an_absent_plc_for_an_absent_door():
    """★開ける driver が `OSError` を投げても落とさないこと(線の先の話)。

    逆に、**開けないはずの driver** が `OSError` を投げたら落ちること —— そちらは
    「扉が無いのに何かが起きた」であって、通してはいけない。
    """
    def opener(name):
        raise ConnectionRefusedError("no PLC on the line")

    _assert_every_name_on_the_menu_has_a_door(
        sorted(device._OPENABLE), opener, openable=set(device._OPENABLE))

    with pytest.raises(AssertionError) as e:
        _assert_every_name_on_the_menu_has_a_door(
            ["xarm"], opener, openable=set(device._OPENABLE))
    assert "扉が無い" in str(e.value)
