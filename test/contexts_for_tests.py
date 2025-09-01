from tmsgpack import PackConfig, UnpackConfig
from dataclasses import dataclass

@dataclass
class TestPackCtrl:
    def from_obj(self, obj):
        raise TypeError(f'Cannot serialize {type(obj)} object.')
    options: PackConfig

@dataclass
class TestUnpackCtrl:
    def from_dict(self, ctype, dct):
        raise ValueError(f'Unpack type not supported: {ctype} data: {dct}')
    def from_list(self, ctype, lst):
        raise ValueError(f'Unpack type not supported: {ctype} data: {lst}')
    options: UnpackConfig

def pctrl(**kwargs): return TestPackCtrl(options=PackConfig(**kwargs))
def uctrl(**kwargs): return TestUnpackCtrl(options=UnpackConfig(**kwargs))
