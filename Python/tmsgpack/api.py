from typing import Any, Tuple
from dataclasses import dataclass
from tmsgpack.cython import EncodeBuffer, DecodeBuffer
from tmsgpack.cython import ebuf_put_value, dbuf_take_value
from tmsgpack.cython import TMsgpackError

class EncodeDecode:
    def encode(self, value, target=None):
        codec_type, new_codec, new_value = self.prep_encode(value, target)
        ebuf = EncodeBuffer()
        self.ebuf_put_value(ebuf, codec_type)
        if new_codec is None: ebuf.put_bytes(new_value)
        else:                 new_codec.ebuf_put_value(ebuf, new_value)
        return ebuf.as_bytes()

    def ebuf_put_value(self, ebuf, value): ebuf_put_value(self, ebuf, value)

    def decode(self, msg, source=None):
        dbuf       = DecodeBuffer(msg=msg, start=0, end=len(msg))
        codec_type = self.dbuf_take_value(dbuf)
        new_codec  = self.decode_codec(codec_type, source)
        value      = new_codec.dbuf_take_value(dbuf)
        return value

    def dbuf_take_value(self, dbuf): return dbuf_take_value(self, dbuf)


@dataclass
class BasicCodec(EncodeDecode):
    sort_keys = True
    use_cache = False
    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackError(f'Unsupported codec_type: {codec_type}')

    def decompose_value(self, ectx):
        raise TMsgpackError(f'Unsupported value: {ectx.value}')

    def value_from_bytes(self, obj_type, data: bytes):
        raise TMsgpackError(f'No bytes extension defined: {obj_type=} {data=}')

    def value_from_list(self, obj_type, values: list):
        raise TMsgpackError(f'No tuple extension defined: {obj_type=} {values=}')


basic_codec = BasicCodec()
