#!/usr/bin/env python
from contexts_for_tests import pctrl, uctrl
from tmsgpack import packb, unpackb
from collections import namedtuple
from pytest import raises



class MyDict(dict):
    pass


class MyTuple(tuple):
    pass

class MyList(list):
    pass

MyNamedTuple = namedtuple("MyNamedTuple", "x y")


def test_types():
    with raises(TypeError): packb(MyDict(),  pack_ctrl=pctrl())
    with raises(TypeError): packb(MyList(),  pack_ctrl=pctrl())
    with raises(TypeError): packb(MyTuple(), pack_ctrl=pctrl())
    with raises(TypeError): packb(MyNamedTuple(1, 2), pack_ctrl=pctrl())
