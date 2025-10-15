from tmsgpack import basic_codec, __version__

print(f'{__version__=}')

def main():
    check_round_trip(range(-2000, 2000), 'small integers')
    check_round_trip([
       s * (2**e + d)
       for e in range(63)
       for d in range(-10, 10)
       for s in (-1, +1)
    ], 'integers')
    check_round_trip([3.1415926], 'float')
    check_round_trip([
       v
       for e in range(18)
       for d in range(-2, 2)
       for f in (1, 1/3)
       for n in [int(f * 2**e + d)]
       for v in [
           "*"*n,
           b"*"*n,
           [12]*n,
           (12,)*n,
           {m:3*m+1 for m in range(n)},
       ]
    ], 'strings, bytes, lists, tuples, dicts')
    check_round_trip([True, False, None], 'constants: True False None')
    check_round_trip([[
        1,2,3,4, {'a':'hello', 'b': ['world', 5,6,7]},
    ]], 'nested value')

    yhub=TestRouterHub(id=111); codec=MyCodec(yhub=yhub, types=(Foo, Bar))
    check_not_supported([yhub], codec=codec, comment='yhub not encodable')
    check_round_trip([Bar(1,2,yhub=yhub), Bar(11,22,yhub=yhub)], codec=codec)
    check_round_trip([Foo(1,2), Foo(2,3)], codec=codec)

def check_round_trip(values, comment='', codec=basic_codec):
    ok = not_ok = 0
    for value in values:
        msg       = codec.encode(value)
        new_value = codec.decode(msg)
        if new_value == value: ok += 1
        else:
            not_ok += 1
            print('----- Different -------')
            print(value)
            print(new_value)
            print('-----------------------')

    print(f'{ok=} {not_ok=} {comment}')

def check_not_supported(values, codec, comment):
    ok = not_ok = 0
    for value in values:
        try: codec.encode(value); not_ok+=1; print(f'MISSING ERROR: {value}')
        except TMsgpackError: ok += 1
    print(f'{ok=} {not_ok=} {comment}')

from tmsgpack import EncodeDecode, TMsgpackError
from dataclasses import dataclass
from typing import Sequence
from functools import cached_property
import inspect

@dataclass
class MyCodec(EncodeDecode):
    sort_keys = True
    use_cache = True

    yhub: 'TestRouterHub'
    types: Sequence

    @cached_property
    def constructors(self): return {t.__name__:t for t in self.types}

    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackError(f'Unsupported codec_type: {codec_type}')

    def decompose_value(self, ectx):
        type_name   = self.type_to_name(type(ectx.value))
        constructor = self.name_to_constructor(type_name)
        args        = self.constructor_to_args_without_yhub(constructor)
        ectx.set_dict_encode_handler(type_name, args)

    def value_from_bytes(self, dctx):
        raise TMsgpackError(f'No bytes extension defined: {obj_type=} {data=}')

    def value_from_list(self, dctx):
        constructor = self.name_to_constructor(dctx._type)
        with_yhub   = 'yhub' in self.constructor_to_args(constructor)
        if with_yhub: extra_kwargs = {'yhub': dctx.codec.yhub}
        else:         extra_kwargs = None
        return dctx.set_dict_decode_handler(constructor, extra_kwargs)

    def type_to_name(self, _type): return _type.__name__
    def name_to_constructor(self, name):
        if res := self.constructors.get(name, None): return res
        raise TMsgpackError(f'Unsupported type: {name}')
    def constructor_to_args(self, constructor):
        return inspect.signature(constructor).parameters.keys()
    def constructor_to_args_without_yhub(self, constructor):
        return [n for n in self.constructor_to_args(constructor) if n != 'yhub']


@dataclass
class Foo:
    x: int
    y: int

@dataclass
class Bar:
    x: int
    y: int
    yhub: 'TestRouterHub'

@dataclass
class TestRouterHub:  # This is not encodable
    id: int

if __name__ == '__main__':
    main()
