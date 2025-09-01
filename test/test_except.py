#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl
from pytest import raises
from tmsgpack import packb, unpackb, Unpacker, FormatError, StackError, OutOfData


def test_invalidvalue():
    incomplete = b"\xd9\x97#DL_"  # raw8 - length=0x97
    with raises(ValueError):
        unpackb(incomplete, unpack_ctrl=uctrl())

    with raises(OutOfData):
        unpacker = Unpacker(unpack_ctrl=uctrl())
        unpacker.feed(incomplete)
        unpacker.unpack()

    with raises(FormatError):
        unpackb(b"\xc1", unpack_ctrl=uctrl())  # (undefined tag)

    with raises(FormatError):
        unpackb(b"\x91\xc1", unpack_ctrl=uctrl())  # fixlist(len=1) [ (undefined tag) ]

    with raises(StackError):
        unpackb(b"\x91" * 3000, unpack_ctrl=uctrl())  # nested fixlist(len=1)


def test_strict_dict_key():
    valid = {"unicode": 1, b"bytes": 2}
    packed = packb(valid, pack_ctrl=pctrl(use_bin_type=True))
    assert valid == unpackb(packed, unpack_ctrl=uctrl(raw=False, strict_dict_key=True))

    invalid = {42: 1}
    packed = packb(invalid, pack_ctrl=pctrl(use_bin_type=True))
    with raises(ValueError):
        unpackb(packed, unpack_ctrl=uctrl(raw=False, strict_dict_key=True))
