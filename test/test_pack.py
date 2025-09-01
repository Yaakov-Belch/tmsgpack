#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl
from collections import OrderedDict
from io import BytesIO
import struct
import sys

import pytest
from pytest import raises, xfail

from tmsgpack import packb, unpackb, Unpacker, Packer, pack


def check(data, use_tuple=True):
    re = unpackb(packb(data, pack_ctrl=pctrl()), unpack_ctrl=uctrl(use_tuple=use_tuple, strict_dict_key=False))
    assert re == data


def testPack():
    test_data = [
        0,
        1,
        127,
        128,
        255,
        256,
        65535,
        65536,
        4294967295,
        4294967296,
        -1,
        -32,
        -33,
        -128,
        -129,
        -32768,
        -32769,
        -4294967296,
        -4294967297,
        1.0,
        b"",
        b"a",
        b"a" * 31,
        b"a" * 32,
        None,
        True,
        False,
        (),
        ((),),
        ((), None),
        {None: 0},
        (1 << 23),
    ]
    for td in test_data:
        check(td)


def testPackUnicode():
    test_data = ["", "abcd", ["defgh"], "Русский текст"]
    for td in test_data:
        re = unpackb(packb(td, pack_ctrl=pctrl()), unpack_ctrl=uctrl(use_tuple=False, raw=False))
        assert re == td
        packer = Packer(pack_ctrl=pctrl())
        data = packer.pack(td)
        re = Unpacker(BytesIO(data), unpack_ctrl=uctrl(raw=False, use_tuple=False)).unpack()
        assert re == td


def testPackBytes():
    test_data = [b"", b"abcd", (b"defgh",)]
    for td in test_data:
        check(td)


def testPackByteArrays():
    test_data = [bytearray(b""), bytearray(b"abcd"), (bytearray(b"defgh"),)]
    for td in test_data:
        check(td)


def testIgnoreUnicodeErrors():
    re = unpackb(packb(b"abc\xeddef", pack_ctrl=pctrl(use_bin_type=False)), unpack_ctrl=uctrl(raw=False, unicode_errors="ignore"))
    assert re == "abcdef"


def testStrictUnicodeUnpack():
    packed = packb(b"abc\xeddef", pack_ctrl=pctrl(use_bin_type=False))
    with pytest.raises(UnicodeDecodeError):
        unpackb(packed, unpack_ctrl=uctrl(raw=False, use_tuple=False))


def testIgnoreErrorsPack():
    pack_ctrl=pctrl(use_bin_type=True, unicode_errors="ignore")
    re = unpackb(
        packb("abc\uDC80\uDCFFdef", pack_ctrl=pack_ctrl),
        unpack_ctrl=uctrl(raw=False, use_tuple=False),
    )
    assert re == "abcdef"


def testDecodeBinary():
    re = unpackb(packb(b"abc", pack_ctrl=pctrl()), unpack_ctrl=uctrl(use_tuple=False))
    assert re == b"abc"


def testPackFloat():
    assert packb(1.0, pack_ctrl=pctrl(use_single_float=True)) == b"\xca" + struct.pack(">f", 1.0)
    assert packb(1.0, pack_ctrl=pctrl(use_single_float=False)) == b"\xcb" + struct.pack(">d", 1.0)


def testListSize(sizes=[0, 5, 50, 1000]):
    bio = BytesIO()
    packer = Packer(pack_ctrl=pctrl())
    for size in sizes:
        bio.write(packer.pack_list_header(size))
        bio.write(packer.pack(None))
        for i in range(size):
            bio.write(packer.pack(i))

    bio.seek(0)
    unpacker = Unpacker(bio, unpack_ctrl=uctrl(use_tuple=False))
    for size in sizes:
        assert unpacker.unpack() == list(range(size))


def testDictSize(sizes=[0, 5, 50, 1000]):
    bio = BytesIO()
    packer = Packer(pack_ctrl=pctrl())
    for size in sizes:
        bio.write(packer.pack_dict_header(size))
        bio.write(packer.pack(None))
        for i in range(size):
            bio.write(packer.pack(i))  # key
            bio.write(packer.pack(i * 2))  # value

    bio.seek(0)
    unpacker = Unpacker(bio, unpack_ctrl=uctrl(strict_dict_key=False))
    for size in sizes:
        assert unpacker.unpack() == {i: i * 2 for i in range(size)}

def test_sort_keys(sizes=[3, 31, 127, 1023]):
    for size in sizes:
        keys  = range(1, 1000000000, 1000000000 // size)
        dict1 = {k: k for k in keys}
        dict2 = {k: k for k in reversed(keys)}
        assert packb(dict1, pack_ctrl=pctrl(sort_keys=False)) != packb(dict2, pack_ctrl=pctrl(sort_keys=False))
        assert packb(dict1, pack_ctrl=pctrl(sort_keys=True)) == packb(dict2, pack_ctrl=pctrl(sort_keys=True))
