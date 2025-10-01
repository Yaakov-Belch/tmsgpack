import struct
from dataclasses import dataclass, field

from .exceptions  import TMsgpackEncodingError, TMsgpackDecodingError

@dataclass
class EncodeBuffer:
    barray: bytearray = field(default_factory=bytearray)

    def put_bytes(self, value: bytes) -> 'EncodeBuffer':
        self.barray.extend(value)
        return self

    def put_str(self, value: str) -> 'EncodeBuffer':
        return self.put_bytes(value.encode('utf-8'))

    def put_int1(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<b', value))

    def put_int2(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<h', value))

    def put_int4(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<i', value))

    def put_int8(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<q', value))

    def put_uint1(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<B', value))

    def put_uint2(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<H', value))

    def put_uint4(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<I', value))

    def put_uint8(self, value: int) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<Q', value))

    def put_float4(self, value: float) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<f', value))

    def put_float8(self, value: float) -> 'EncodeBuffer':
        return self.put_bytes(struct.pack('<d', value))

    def as_bytes(self) -> bytes:
        return bytes(self.barray)

@dataclass
class DecodeBuffer:
    msg:   bytes
    start: int
    end:   int

    def take_bytes(self, n: int) -> bytes:
        new_start = self.start + n
        if new_start > self.end:
            raise TMsgpackDecodingError('Not enough input data')
        result = self.msg[self.start:new_start]
        self.start = new_start
        return result

    def take_str(self, n: int) -> str: return self.take_bytes(n).decode('utf-8')

    def take_int1(self)  -> int: return struct.unpack('<b', self.take_bytes(1))[0]
    def take_int2(self)  -> int: return struct.unpack('<h', self.take_bytes(2))[0]
    def take_int4(self)  -> int: return struct.unpack('<i', self.take_bytes(4))[0]
    def take_int8(self)  -> int: return struct.unpack('<q', self.take_bytes(8))[0]

    def take_uint1(self) -> int: return struct.unpack('<B', self.take_bytes(1))[0]
    def take_uint2(self) -> int: return struct.unpack('<H', self.take_bytes(2))[0]
    def take_uint4(self) -> int: return struct.unpack('<I', self.take_bytes(4))[0]
    def take_uint8(self) -> int: return struct.unpack('<Q', self.take_bytes(8))[0]

    def take_float8(self) -> float: return struct.unpack('<d', self.take_bytes(8))[0]

