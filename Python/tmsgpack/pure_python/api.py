from abc import abstractmethod
from typing import Any, Tuple
from dataclasses import dataclass

from .exceptions  import TMsgpackEncodingError, TMsgpackDecodingError
from .buffers import EncodeBuffer, DecodeBuffer
from .engine import ebuf_put_value, dbuf_take_value

class CodecAPI:
    sort_keys: bool

    @abstractmethod
    def prep_encode(self, value:Any, target:Any) -> Tuple[Any, 'CodecAPI', Any]:
        """Determine actual codec for encoding and decoding."""
        return [None, self, value]          # This uses the same codec.

    @abstractmethod
    def decode_codec(self, codec_type:Any, source:Any) -> 'CodecAPI':
        if codec_type is None: return self  # Allow to use the same codec.

    @abstractmethod
    def decompose_value(self, value) -> Tuple[int, Any, Any]:
        """
        Extension/Hook: Define how to encode value.

        returns: [_mode, _type, _new_value]
            _mode=0:  Encode _new_value instead of value.
            _mode=1:  Encode as typed bytes.
            _mode=2:  Encode as typed tuple.
            _mode=3:  Use _mode 4 or 5 depending on self.sort_keys
            _mode=4:  Encode as typed dict with sorted keys
            _mode=5:  Encode as typed dict with unsorted keys (python order)
        """

    @abstractmethod
    def value_from_bytes(self, obj_type, data: bytes):
        """Extension/Hook: Define how to decode typed bytes."""

    @abstractmethod
    def value_from_list(self, obj_type, values: list) -> Any:
        """Extension/Hook: Define how to decode typed tuples / dicts."""

    @abstractmethod
    def encode(self, value, target=None):
        """Encode value to msg.  Provided by the EncodeDecode mixin."""

    @abstractmethod
    def ebuf_put_value(self, ebuf, value):
        """Add encoded value to EncodeBuffer ebuf. Provided by the EncodeDecode mixin."""

    @abstractmethod
    def decode(self, msg, source=None):
        """Decode msg to value.  Provided by the EncodeDecode mixin."""

    @abstractmethod
    def dbuf_take_value(self, dbuf):
        """Take one msg from DecodeBuffer dbuf. Provided by the EncodeDecode mixin."""

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
    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackDecodingError(f'Unsupported codec_type: {codec_type}')

    def decompose_value(self, value):
        raise TMsgpackEncodingError(f'Unsupported value: {value}')

    def value_from_bytes(self, obj_type, data: bytes):
        raise TMsgpackDecodingError(f'No bytes extension defined: {obj_type=} {data=}')

    def value_from_list(self, obj_type, values: list):
        raise TMsgpackDecodingError(f'No tuple extension defined: {obj_type=} {values=}')


basic_codec = BasicCodec()
