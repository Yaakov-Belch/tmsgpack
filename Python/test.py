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

    codec=MyCodec(types=[Foo])
    check_round_trip([Foo(1,2), Foo(2,3)], codec=codec, comment='Foo')

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

def check_not_supported(values, codec, comment): # Not currently used.
    ok = not_ok = 0
    for value in values:
        try: codec.encode(value); not_ok+=1; print(f'MISSING ERROR: {value}')
        except TMsgpackError: ok += 1
    print(f'{ok=} {not_ok=} {comment}')

from tmsgpack import EncodeDecode, TMsgpackError
from dataclasses import dataclass, field
from typing import Sequence
from functools import cached_property
import inspect

@dataclass
class MyCodec(EncodeDecode):
    sort_keys = True
    types: Sequence

    encode_cache: dict = field(repr=False, default_factory=dict)
    decode_cache: dict = field(repr=False, default_factory=dict)

    @cached_property
    def constructors(self): return {t.__name__:t for t in self.types}

    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackError(f'Unsupported codec_type: {codec_type}')

    def decompose_value(self, ectx):
        t = type(ectx.value)
        if t not in self.encode_cache:
            type_name   = self.type_to_name(t)
            constructor = self.name_to_constructor(type_name)
            args        = self.constructor_to_args(constructor)

            def encode_handler(ectx):
                value = ectx.value
                ectx.put_dict(type_name, {a:getattr(value, a) for a in args})
            self.encode_cache[t] = encode_handler
        self.encode_cache[t](ectx)

    def value_from_bytes(self, dctx):
        raise TMsgpackError(f'No bytes extension defined: {dctx._type}')

    def value_from_list(self, dctx):
        _type = dctx._type
        if _type not in self.decode_cache:
            constructor = self.name_to_constructor(_type)
            def decode_handler(dctx): return constructor(**dctx.take_dict())
            self.decode_cache[_type] = decode_handler
        return self.decode_cache[_type](dctx)

    def type_to_name(self, _type): return _type.__name__
    def name_to_constructor(self, name):
        if res := self.constructors.get(name, None): return res
        raise TMsgpackError(f'Unsupported type: {name}')
    def constructor_to_args(self, constructor):
        return inspect.signature(constructor).parameters.keys()

@dataclass
class Foo:
    x: int
    y: int

if __name__ == '__main__':
    main()
