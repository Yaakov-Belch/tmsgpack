#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl

import sys
import pytest
from tmsgpack import packb, unpackb


def test_unpack_buffer():
    from array import array

    buf = array("b")
    buf.frombytes(packb((b"foo", b"bar"), pack_ctrl=pctrl()))
    obj = unpackb(buf, unpack_ctrl=uctrl(use_tuple=False))
    assert [b"foo", b"bar"] == obj


def test_unpack_bytearray():
    buf = bytearray(packb((b"foo", b"bar"), pack_ctrl=pctrl()))
    obj = unpackb(buf, unpack_ctrl=uctrl(use_tuple=False))
    assert [b"foo", b"bar"] == obj
    expected_type = bytes
    assert all(type(s) == expected_type for s in obj)


def test_unpack_memoryview():
    buf = bytearray(packb((b"foo", b"bar"), pack_ctrl=pctrl()))
    view = memoryview(buf)
    obj = unpackb(view, unpack_ctrl=uctrl(use_tuple=False))
    assert [b"foo", b"bar"] == obj
    expected_type = bytes
    assert all(type(s) == expected_type for s in obj)
