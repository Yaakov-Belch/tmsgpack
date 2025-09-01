#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl
import pytest

from tmsgpack import (
    packb,
    unpackb,
    Packer,
    Unpacker,
    PackOverflowError,
    PackValueError,
    UnpackValueError,
)


def test_integer():
    x = -(2**63)
    assert unpackb(packb(x, pack_ctrl=pctrl()), unpack_ctrl=uctrl()) == x
    with pytest.raises(PackOverflowError):
        packb(x - 1, pack_ctrl=pctrl())

    x = 2**64 - 1
    assert unpackb(packb(x, pack_ctrl=pctrl()), unpack_ctrl=uctrl()) == x
    with pytest.raises(PackOverflowError):
        packb(x + 1, pack_ctrl=pctrl())


def test_list_header():
    packer = Packer(pack_ctrl=pctrl())
    packer.pack_list_header(2**32 - 1)
    with pytest.raises(PackValueError):
        packer.pack_list_header(2**32)


def test_dict_header():
    packer = Packer(pack_ctrl=pctrl())
    packer.pack_dict_header(2**32 - 1)
    with pytest.raises(PackValueError):
        packer.pack_list_header(2**32)


def test_max_str_len():
    d = "x" * 3
    packed = packb(d, pack_ctrl=pctrl())

    unpacker = Unpacker(unpack_ctrl=uctrl( max_str_len=3, raw=False))
    unpacker.feed(packed)
    assert unpacker.unpack() == d

    unpacker = Unpacker(unpack_ctrl=uctrl(max_str_len=2, raw=False))
    with pytest.raises(UnpackValueError):
        unpacker.feed(packed)
        unpacker.unpack()


def test_max_bin_len():
    d = b"x" * 3
    packed = packb(d, pack_ctrl=pctrl(use_bin_type=True))

    unpacker = Unpacker(unpack_ctrl=uctrl(max_bin_len=3))
    unpacker.feed(packed)
    assert unpacker.unpack() == d

    unpacker = Unpacker(unpack_ctrl=uctrl(max_bin_len=2))
    with pytest.raises(UnpackValueError):
        unpacker.feed(packed)
        unpacker.unpack()


def test_max_list_len():
    d = [1, 2, 3]
    packed = packb(d, pack_ctrl=pctrl())

    unpacker = Unpacker(unpack_ctrl=uctrl(max_list_len=3))
    unpacker.feed(packed)
    assert unpacker.unpack() == d

    unpacker = Unpacker(unpack_ctrl=uctrl(max_list_len=2))
    with pytest.raises(UnpackValueError):
        unpacker.feed(packed)
        unpacker.unpack()


def test_max_dict_len():
    d = {1: 2, 3: 4, 5: 6}
    packed = packb(d, pack_ctrl=pctrl())

    unpacker = Unpacker(unpack_ctrl=uctrl(max_dict_len=3, strict_dict_key=False))
    unpacker.feed(packed)
    assert unpacker.unpack() == d

    unpacker = Unpacker(unpack_ctrl=uctrl(max_dict_len=2, strict_dict_key=False))
    with pytest.raises(UnpackValueError):
        unpacker.feed(packed)
        unpacker.unpack()


# PyPy fails following tests because of constant folding?
# https://bugs.pypy.org/issue1721
# @pytest.mark.skipif(True, reason="Requires very large memory.")
# def test_binary():
#    x = b'x' * (2**32 - 1)
#    assert unpackb(packb(x, pack_ctrl=pctrl()), unpack_ctrl=uctrl()) == x
#    del x
#    x = b'x' * (2**32)
#    with pytest.raises(ValueError):
#        packb(x, pack_ctrl=pctrl())
#
#
# @pytest.mark.skipif(True, reason="Requires very large memory.")
# def test_string():
#    x = 'x' * (2**32 - 1)
#    assert unpackb(packb(x, pack_ctrl=pctrl()), unpack_ctrl=uctrl()) == x
#    x += 'y'
#    with pytest.raises(ValueError):
#        packb(x, pack_ctrl=pctrl())
#
#
# @pytest.mark.skipif(True, reason="Requires very large memory.")
# def test_list():
#    x = [0] * (2**32 - 1)
#    assert unpackb(packb(x, pack_ctrl=pctrl()), unpack_ctrl=uctrl()) == x
#    x.append(0)
#    with pytest.raises(ValueError):
#        packb(x, pack_ctrl=pctrl())


# auto max len


def test_auto_max_list_len():
    packed = b"\xde\x00\x06zz"
    with pytest.raises(UnpackValueError):
        unpackb(packed, unpack_ctrl=uctrl(raw=False))

    unpacker = Unpacker(unpack_ctrl=uctrl(max_buffer_size=5, raw=False))
    unpacker.feed(packed)
    with pytest.raises(UnpackValueError):
        unpacker.unpack()


def test_auto_max_dict_len():
    # len(packed) == 6 -> max_dict_len == 3
    packed = b"\xde\x00\x04zzz"
    with pytest.raises(UnpackValueError):
        unpackb(packed, unpack_ctrl=uctrl(raw=False))

    unpacker = Unpacker(unpack_ctrl=uctrl(max_buffer_size=6, raw=False))
    unpacker.feed(packed)
    with pytest.raises(UnpackValueError):
        unpacker.unpack()
