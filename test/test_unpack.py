from contexts_for_tests import pctrl, uctrl
from io import BytesIO
import sys
from tmsgpack import Unpacker, packb, OutOfData
from pytest import raises, mark

try:
    from itertools import izip as zip
except ImportError:
    pass


def test_unpacker_tell():
    objects = 1, 2, "abc", "def", "ghi"
    packed = b"\x01\x02\xa3abc\xa3def\xa3ghi"
    positions = 1, 2, 6, 10, 14
    unpacker = Unpacker(BytesIO(packed), unpack_ctrl=uctrl())
    for obj, unp, pos in zip(objects, unpacker, positions):
        assert obj == unp
        assert pos == unpacker.tell()


def test_unpacker_tell_read_bytes():
    objects = 1, "abc", "ghi"
    packed = b"\x01\x02\xa3abc\xa3def\xa3ghi"
    raw_data = b"\x02", b"\xa3def", b""
    lenghts = 1, 4, 999
    positions = 1, 6, 14
    unpacker = Unpacker(BytesIO(packed), unpack_ctrl=uctrl())
    for obj, unp, pos, n, raw in zip(objects, unpacker, positions, lenghts, raw_data):
        assert obj == unp
        assert pos == unpacker.tell()
        assert unpacker.read_bytes(n) == raw
