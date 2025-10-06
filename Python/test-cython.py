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

    check_round_trip([Foo(1,2)], codec=MyCodec())

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


from tmsgpack import EncodeDecode, TMsgpackEncodingError, TMsgpackDecodingError
from dataclasses import dataclass

@dataclass
class MyCodec(EncodeDecode):
    sort_keys = True
    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackDecodingError(f'Unsupported codec_type: {codec_type}')

    def decompose_value(self, ectx):
        if type(value:=ectx.value) is Foo:
            ectx.put_dict('Foo', dict(x=value.x, y=value.y), ectx.sort_keys)
        else:
            raise TMsgpackEncodingError(f'Unsupported value: {ectx.value}')

    def value_from_bytes(self, obj_type, data: bytes):
        raise TMsgpackDecodingError(f'No bytes extension defined: {obj_type=} {data=}')

    def value_from_list(self, dctx):
        if dctx._type == 'Foo': return Foo(**dctx.take_dict())
        raise TMsgpackDecodingError(f'No tuple extension defined: {obj_type=} {values=}')

@dataclass
class Foo:
    x: int
    y: int


if __name__ == '__main__':
    main()
