from contexts_for_tests import pctrl, uctrl
from tmsgpack import packb, unpackb

def round_trip(input, expected=None):
    if expected is None: expected = input
    packed = packb(input, pack_ctrl=pctrl())
    unpacked = unpackb(packed, unpack_ctrl=uctrl())
    assert unpacked == expected

def test_roundtrip_many():
    test_cases = [
        0, 1, 2, 127, 128, 12345, 123456789,
        -1, -2, -62, -63, -64, -65, -126, -127, -128, -129, -12345, -123456789,
        0.1, 1.1, -1.1, 1.234567e89, -1.234567e-89,
        [], [1], [1,2], [1,2,3], [1]*7, [1]*8, [1]*9, [1]*12345,
        {}, {1:2}, {1:2, 2:3, 3:4},
        '', '1', '123', '12'*12345,
        b'', b'1', b'123', b'12'*12345,
        None, False, True,
    ]

    for d in test_cases:
        round_trip(d)




























