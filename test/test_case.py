#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl
from tmsgpack import packb, unpackb


def check(length, obj, use_bin_type=True):
    v = packb(obj, pack_ctrl=pctrl(use_bin_type=use_bin_type))
    assert len(v) == length, f"{obj!r} length should be {length!r} but get {len(v)!r}"
    assert unpackb(v, unpack_ctrl=uctrl(use_tuple=True, raw=not use_bin_type)) == obj


def test_1():
    for o in [
        None,
        True,
        False,
        0,
        1,
        (1 << 6),
        (1 << 7) - 1,
        -1,
        -((1 << 5) - 1),
        -(1 << 5),
    ]:
        check(1, o)


def test_2():
    for o in [1 << 7, (1 << 8) - 1, -((1 << 5) + 1), -(1 << 7)]:
        check(2, o)


def test_3():
    for o in [1 << 8, (1 << 16) - 1, -((1 << 7) + 1), -(1 << 15)]:
        check(3, o)


def test_5():
    for o in [1 << 16, (1 << 32) - 1, -((1 << 15) + 1), -(1 << 31)]:
        check(5, o)


def test_9():
    for o in [
        1 << 32,
        (1 << 64) - 1,
        -((1 << 31) + 1),
        -(1 << 63),
        1.0,
        0.1,
        -0.1,
        -1.0,
    ]:
        check(9, o)


def check_raw(overhead, num):
    check(num + overhead, b" " * num, use_bin_type=False)


def test_fixraw():
    check_raw(1, 0)
    check_raw(1, (1 << 5) - 1)


def test_raw16():
    check_raw(3, 1 << 5)
    check_raw(3, (1 << 16) - 1)


def test_raw32():
    check_raw(5, 1 << 16)


def check_list(overhead, num):
    check(num + overhead + 1, (None,) * num)


def test_fixlist():
    check_list(1, 0)
    check_list(1, (1 << 4) - 1)


def test_list16():
    check_list(3, 1 << 4)
    check_list(3, (1 << 16) - 1)


def test_list32():
    check_list(5, (1 << 16))


def match(obj, buf):
    assert packb(obj, pack_ctrl=pctrl()) == buf
    assert unpackb(buf, unpack_ctrl=uctrl(use_tuple=True, strict_dict_key=False)) == obj


def test_match():
    cases = [
        (None, b"\xc0"),
        (False, b"\xc2"),
        (True, b"\xc3"),
        (0, b"\x00"),
        (127, b"\x7f"),
        (128, b"\xcc\x80"),
        (256, b"\xcd\x01\x00"),
        (-1, b"\xff"),
        (-33, b"\xd0\xdf"),
        (-129, b"\xd1\xff\x7f"),
        ({1: 1}, b"\x81\xc0\x01\x01"),
        (1.0, b"\xcb\x3f\xf0\x00\x00\x00\x00\x00\x00"),
        ((), b"\x90\xc0"),
        (
            tuple(range(15)),
            b"\x9f\xc0\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e",
        ),
        (
            tuple(range(16)),
            b"\xdc\x00\x10\xc0\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
        ),
        ({}, b"\x80\xc0"),
        (
            {x: x for x in range(15)},
            b"\x8f\xc0\x00\x00\x01\x01\x02\x02\x03\x03\x04\x04\x05\x05\x06\x06\x07\x07\x08\x08\t\t\n\n\x0b\x0b\x0c\x0c\r\r\x0e\x0e",
        ),
        (
            {x: x for x in range(16)},
            b"\xde\x00\x10\xc0\x00\x00\x01\x01\x02\x02\x03\x03\x04\x04\x05\x05\x06\x06\x07\x07\x08\x08\t\t\n\n\x0b\x0b\x0c\x0c\r\r\x0e\x0e\x0f\x0f",
        ),
    ]

    for v, p in cases:
        match(v, p)


def test_unicode():
    assert unpackb(packb("foobar", pack_ctrl=pctrl()), unpack_ctrl=uctrl(use_tuple=True)) == "foobar"
