"""Fallback pure Python implementation of tmsgpack"""
import sys
import struct

if hasattr(sys, "pypy_version_info"):
    # StringIO is slow on PyPy, StringIO is faster.  However: PyPy's own
    # StringBuilder is fastest.
    from __pypy__ import newlist_hint

    try:
        from __pypy__.builders import BytesBuilder as StringBuilder
    except ImportError:
        from __pypy__.builders import StringBuilder
    USING_STRINGBUILDER = True

    class StringIO:
        def __init__(self, s=b""):
            if s:
                self.builder = StringBuilder(len(s))
                self.builder.append(s)
            else:
                self.builder = StringBuilder()

        def write(self, s):
            if isinstance(s, memoryview):
                s = s.tobytes()
            elif isinstance(s, bytearray):
                s = bytes(s)
            self.builder.append(s)

        def getvalue(self):
            return self.builder.build()

else:
    USING_STRINGBUILDER = False
    from io import BytesIO as StringIO

    newlist_hint = lambda size: []


from .exceptions import BufferFull, OutOfData, ExtraData, FormatError, StackError

TYPE_IMMEDIATE = 0
TYPE_LIST = 1
TYPE_DICT = 2
TYPE_RAW  = 3
TYPE_BIN  = 4
TYPE_EXT  = 5

DEFAULT_RECURSE_LIMIT = 511

def _check_type_strict(obj, t, type=type):
    return type(obj) is t


def _get_data_from_buffer(obj):
    view = memoryview(obj)
    if view.itemsize != 1:
        raise ValueError("cannot unpack from multi-byte object")
    return view


def unpackb(packed, *, unpack_ctrl):
    """
    Unpack an object from `packed`.

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``ValueError`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid tmsgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.

    See :class:`Unpacker` for options.
    """
    unpacker = Unpacker(None, unpack_ctrl=unpack_ctrl, buffer_size=len(packed))
    unpacker.feed(packed)
    try:
        ret = unpacker._unpack()
    except OutOfData:
        raise ValueError("Unpack failed: incomplete input")
    except RecursionError:
        raise StackError
    if unpacker._got_extradata():
        raise ExtraData(ret, unpacker._get_extradata())
    return ret


_NO_FORMAT_USED = ""
_MSGPACK_HEADERS = {
    0xC4: (1, _NO_FORMAT_USED, TYPE_BIN),
    0xC5: (2, ">H", TYPE_BIN),
    0xC6: (4, ">I", TYPE_BIN),
    0xC7: (2, "Bb", TYPE_EXT),     # TYPE_EXT raises FormatError.
    0xC8: (3, ">Hb", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xC9: (5, ">Ib", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xCA: (4, ">f"),
    0xCB: (8, ">d"),
    0xCC: (1, _NO_FORMAT_USED),
    0xCD: (2, ">H"),
    0xCE: (4, ">I"),
    0xCF: (8, ">Q"),
    0xD0: (1, "b"),
    0xD1: (2, ">h"),
    0xD2: (4, ">i"),
    0xD3: (8, ">q"),
    0xD4: (1, "b1s", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xD5: (2, "b2s", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xD6: (4, "b4s", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xD7: (8, "b8s", TYPE_EXT),    # TYPE_EXT raises FormatError.
    0xD8: (16, "b16s", TYPE_EXT),  # TYPE_EXT raises FormatError.
    0xD9: (1, _NO_FORMAT_USED, TYPE_RAW),
    0xDA: (2, ">H", TYPE_RAW),
    0xDB: (4, ">I", TYPE_RAW),
    0xDC: (2, ">H", TYPE_LIST),
    0xDD: (4, ">I", TYPE_LIST),
    0xDE: (2, ">H", TYPE_DICT),
    0xDF: (4, ">I", TYPE_DICT),
}


class Unpacker:
    """Streaming tmsgpack unpacker.

    Arguments:

    :param unpack_ctrl:
        Unpack control context.

    :param file_like:
        File-like object having `.read(n)` method.
        If specified, unpacker reads serialized data from it and :meth:`feed()` is not usable.

    :param buffer_size:
        Set the buffer_size.

    Example of streaming deserialize from file-like object::

        unpacker = Unpacker(file_like)
        for o in unpacker:
            process(o)

    Example of streaming deserialize from socket::

        unpacker = Unpacker()
        while True:
            buf = sock.recv(1024**2)
            if not buf:
                break
            unpacker.feed(buf)
            for o in unpacker:
                process(o)

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``OutOfData`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid tmsgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.
    """

    def __init__(
        self,
        file_like=None,
        unpack_ctrl=None,
        buffer_size=0,
    ):
        if unpack_ctrl is None:
            raise ValueError("No unpack_ctrl supplied.")

        self.from_dict = unpack_ctrl.from_dict
        self.from_list = unpack_ctrl.from_list
        if file_like is None:
            self._feeding = True
        else:
            if not callable(file_like.read):
                raise TypeError("`file_like.read` must be callable")
            self.file_like = file_like
            self._feeding = False

        #: array of bytes fed.
        self._buffer = bytearray()
        #: Which position we currently reads
        self._buff_i = 0

        # When Unpacker is used as an iterable, between the calls to next(),
        # the buffer is not "consumed" completely, for efficiency sake.
        # Instead, it is done sloppily.  To make sure we raise BufferFull at
        # the correct moments, we have to keep track of how sloppy we were.
        # Furthermore, when the buffer is incomplete (that is: in the case
        # we raise an OutOfData) we need to rollback the buffer to the correct
        # state, which _buf_checkpoint records.
        self._buf_checkpoint = 0

        o = unpack_ctrl.options
        if buffer_size == 0:
            self._max_buffer_size = o.max_buffer_size
            self._read_size       = o.read_size
        else:
            self._max_buffer_size = self._read_size = buffer_size

        self._read_size = o.read_size
        self._raw = bool(o.raw)
        self._strict_dict_key = bool(o.strict_dict_key)
        self._unicode_errors  = o.unicode_errors
        self._use_tuple       = o.use_tuple
        self._object_as_pairs = o.object_as_pairs
        self._max_str_len  = o.max_str_len
        self._max_bin_len  = o.max_bin_len
        self._max_list_len = o.max_list_len
        self._max_dict_len = o.max_dict_len

        self._stream_offset = 0

    def feed(self, next_bytes):
        assert self._feeding
        view = _get_data_from_buffer(next_bytes)
        if len(self._buffer) - self._buff_i + len(view) > self._max_buffer_size:
            raise BufferFull

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Use extend here: INPLACE_ADD += doesn't reliably typecast memoryview in jython
        self._buffer.extend(view)

    def _consume(self):
        """Gets rid of the used parts of the buffer."""
        self._stream_offset += self._buff_i - self._buf_checkpoint
        self._buf_checkpoint = self._buff_i

    def _got_extradata(self):
        return self._buff_i < len(self._buffer)

    def _get_extradata(self):
        return self._buffer[self._buff_i :]

    def read_bytes(self, n):
        ret = self._read(n, raise_outofdata=False)
        self._consume()
        return ret

    def _read(self, n, raise_outofdata=True):
        # (int) -> bytearray
        self._reserve(n, raise_outofdata=raise_outofdata)
        i = self._buff_i
        ret = self._buffer[i : i + n]
        self._buff_i = i + len(ret)
        return ret

    def _reserve(self, n, raise_outofdata=True):
        remain_bytes = len(self._buffer) - self._buff_i - n

        # Fast path: buffer has n bytes already
        if remain_bytes >= 0:
            return

        if self._feeding:
            self._buff_i = self._buf_checkpoint
            raise OutOfData

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Read from file
        remain_bytes = -remain_bytes
        if remain_bytes + len(self._buffer) > self._max_buffer_size:
            raise BufferFull
        while remain_bytes > 0:
            to_read_bytes = max(self._read_size, remain_bytes)
            read_data = self.file_like.read(to_read_bytes)
            if not read_data:
                break
            assert isinstance(read_data, bytes)
            self._buffer += read_data
            remain_bytes -= len(read_data)

        if len(self._buffer) < n + self._buff_i and raise_outofdata:
            self._buff_i = 0  # rollback
            raise OutOfData

    def _read_header(self):
        typ = TYPE_IMMEDIATE
        n = 0
        obj = None
        self._reserve(1)
        b = self._buffer[self._buff_i]
        self._buff_i += 1
        if b & 0b10000000 == 0:
            obj = b
        elif b & 0b11100000 == 0b11100000:
            obj = -1 - (b ^ 0xFF)
        elif b & 0b11100000 == 0b10100000:
            n = b & 0b00011111
            typ = TYPE_RAW
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif b & 0b11110000 == 0b10010000:
            n = b & 0b00001111
            typ = TYPE_LIST
            if n > self._max_list_len:
                raise ValueError(f"{n} exceeds max_list_len({self._max_list_len})")
        elif b & 0b11110000 == 0b10000000:
            n = b & 0b00001111
            typ = TYPE_DICT
            if n > self._max_dict_len:
                raise ValueError(f"{n} exceeds max_dict_len({self._max_dict_len})")
        elif b == 0xc0:
            obj = None
        # elif b == 0xc1: pass # never used
        elif b == 0xc2:
            obj = False
        elif b == 0xc3:
            obj = True
        elif 0xc4 <= b <= 0xc6:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                n = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_bin_len:
                raise ValueError(f"{n} exceeds max_bin_len({self._max_bin_len})")
            obj = self._read(n)
        # elif 0xc7 <= b <= 0xc9: # ext8..ext32 removed
        elif 0xca <= b <= 0xd3:
            size, fmt = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                obj = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                obj = self._buffer[self._buff_i]
            self._buff_i += size
        # elif 0xd4 <= b <= 0xd8: # fixext 1-16 removed
        elif 0xd9 <= b <= 0xdb:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif 0xdc <= b <= 0xdd:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_list_len:
                raise ValueError(f"{n} exceeds max_list_len({self._max_list_len})")
        elif 0xde <= b <= 0xdf:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_dict_len:
                raise ValueError(f"{n} exceeds max_dict_len({self._max_dict_len})")
        else:
            raise FormatError("Unknown header: 0x%x" % b)
        if typ == TYPE_EXT:
            raise FormatError("Ext header not supported: 0x%x" % b)

        return typ, n, obj

    def _unpack(self):
        typ, n, obj = self._read_header()

        # TODO should we eliminate the recursion?
        if typ == TYPE_LIST:
            object_type = self._unpack() # <= XXX
            ret = newlist_hint(n)
            for i in range(n):
                ret.append(self._unpack())
            if self._use_tuple:
                ret = tuple(ret)
            if object_type is not None:
                ret = self.from_list(object_type, ret)
            return ret
        if typ == TYPE_DICT:
            object_type = self._unpack() # <= XXX
            if self._object_as_pairs:
                ret = tuple((self._unpack(), self._unpack()) for _ in range(n))
                ret = self.from_dict(object_type, ret)
            else:
                ret = {}
                for _ in range(n):
                    key = self._unpack()
                    if self._strict_dict_key and type(key) not in (str, bytes):
                        raise ValueError("%s is not allowed for dict key" % str(type(key)))
                    if type(key) is str:
                        key = sys.intern(key)
                    ret[key] = self._unpack()
                if self._object_as_pairs or (object_type is not None):
                    ret = self.from_dict(object_type, ret)
            return ret
        if typ == TYPE_RAW:
            if self._raw:
                obj = bytes(obj)
            else:
                obj = obj.decode("utf_8", self._unicode_errors)
            return obj
        if typ == TYPE_BIN:
            return bytes(obj)
        assert typ == TYPE_IMMEDIATE
        return obj

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret = self._unpack()
            self._consume()
            return ret
        except OutOfData:
            self._consume()
            raise StopIteration
        except RecursionError:
            raise StackError

    next = __next__

    def unpack(self):
        try:
            ret = self._unpack()
        except RecursionError:
            raise StackError
        self._consume()
        return ret

    def tell(self):
        return self._stream_offset


class Packer:
    """
    tmsgpack Packer

    Usage::

        packer = Packer()
        astream.write(packer.pack(a))
        astream.write(packer.pack(b))

    Packer's constructor has some keyword arguments:

    :param pack_ctrl:
        Pack control context.

    Example of streaming deserialize from file-like object::

        unpacker = Unpacker(file_like)
        for o in unpacker:
            process(o)

    Example of streaming deserialize from socket::

        unpacker = Unpacker()
        while True:
            buf = sock.recv(1024**2)
            if not buf:
                break
            unpacker.feed(buf)
            for o in unpacker:
                process(o)

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``OutOfData`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid tmsgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.
    """

    def __init__(
        self,
        pack_ctrl=None,
    ):
        if pack_ctrl is None:
           raise(ValueError("No pack_ctrl supplied."))

        o = pack_ctrl.options
        self.from_obj = pack_ctrl.from_obj
        self._list_types = (list, tuple) if o.tuple_as_list else (list,)
        self._strict_types = o.strict_types
        self._use_float = o.use_single_float
        self._use_bin_type = o.use_bin_type
        self._buffer = StringIO()
        self._unicode_errors = o.unicode_errors
        self._sort_keys = o.sort_keys

    def _pack(
        self,
        obj,
        nest_limit=DEFAULT_RECURSE_LIMIT,
        check=isinstance,
        check_type_strict=_check_type_strict,
    ):
        list_types = self._list_types
        if self._strict_types:
            check = check_type_strict
        while True:
            if nest_limit < 0:
                raise ValueError("recursion limit exceeded")
            if obj is None:
                return self._buffer.write(b"\xc0")
            if check(obj, bool):
                if obj:
                    return self._buffer.write(b"\xc3")
                return self._buffer.write(b"\xc2")
            if check(obj, int):
                if 0 <= obj < 0x80:
                    return self._buffer.write(struct.pack("B", obj))
                if -0x20 <= obj < 0:
                    return self._buffer.write(struct.pack("b", obj))
                if 0x80 <= obj <= 0xFF:
                    return self._buffer.write(struct.pack("BB", 0xCC, obj))
                if -0x80 <= obj < 0:
                    return self._buffer.write(struct.pack(">Bb", 0xD0, obj))
                if 0xFF < obj <= 0xFFFF:
                    return self._buffer.write(struct.pack(">BH", 0xCD, obj))
                if -0x8000 <= obj < -0x80:
                    return self._buffer.write(struct.pack(">Bh", 0xD1, obj))
                if 0xFFFF < obj <= 0xFFFFFFFF:
                    return self._buffer.write(struct.pack(">BI", 0xCE, obj))
                if -0x80000000 <= obj < -0x8000:
                    return self._buffer.write(struct.pack(">Bi", 0xD2, obj))
                if 0xFFFFFFFF < obj <= 0xFFFFFFFFFFFFFFFF:
                    return self._buffer.write(struct.pack(">BQ", 0xCF, obj))
                if -0x8000000000000000 <= obj < -0x80000000:
                    return self._buffer.write(struct.pack(">Bq", 0xD3, obj))
                raise OverflowError("Integer value out of range")
            if check(obj, (bytes, bytearray)):
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("%s is too large" % type(obj).__name__)
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, str):
                obj = obj.encode("utf-8", self._unicode_errors)
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("String is too large")
                self._pack_raw_header(n)
                return self._buffer.write(obj)
            if check(obj, memoryview):
                n = obj.nbytes
                if n >= 2**32:
                    raise ValueError("Memoryview is too large")
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, float):
                if self._use_float:
                    return self._buffer.write(struct.pack(">Bf", 0xCA, obj))
                return self._buffer.write(struct.pack(">Bd", 0xCB, obj))

            if type(obj) is dict:
                as_dict, object_type, data = True, None, obj
            elif type(obj) in list_types:
                as_dict, object_type, data = False, None, obj
            else:
                as_dict, object_type, data = self.from_obj(obj)

            if as_dict:
                _items = sorted(data.items()) if self._sort_keys else data.items()
                _len   = len(_items)
                return self._pack_dict_pairs(_len, object_type, _items, nest_limit - 1)
            else:
                n = len(data)
                self._pack_list_header(n)
                self._pack(object_type, nest_limit - 1)
                for i in range(n):
                    self._pack(data[i], nest_limit - 1)
                return

    def pack(self, obj):
        try:
            self._pack(obj)
        except:
            self._buffer = StringIO()  # force reset
            raise
        ret = self._buffer.getvalue()
        self._buffer = StringIO()
        return ret

    def pack_dict_pairs(self, object_type, pairs):
        self._pack_dict_pairs(len(pairs), object_type, pairs)
        ret = self._buffer.getvalue()
        self._buffer = StringIO()
        return ret

    def pack_list_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_list_header(n)
        ret = self._buffer.getvalue()
        self._buffer = StringIO()
        return ret

    def pack_dict_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_dict_header(n)
        ret = self._buffer.getvalue()
        self._buffer = StringIO()
        return ret

    def _pack_list_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x90 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDC, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDD, n))
        raise ValueError("List is too large")

    def _pack_dict_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x80 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDE, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDF, n))
        raise ValueError("Dict is too large")

    def _pack_dict_pairs(self, n, object_type, pairs, nest_limit=DEFAULT_RECURSE_LIMIT):
        self._pack_dict_header(n)
        self._pack(object_type, nest_limit - 1)
        for k, v in pairs:
            self._pack(k, nest_limit - 1)
            self._pack(v, nest_limit - 1)

    def _pack_raw_header(self, n):
        if n <= 0x1F:
            self._buffer.write(struct.pack("B", 0xA0 + n))
        elif self._use_bin_type and n <= 0xFF:
            self._buffer.write(struct.pack(">BB", 0xD9, n))
        elif n <= 0xFFFF:
            self._buffer.write(struct.pack(">BH", 0xDA, n))
        elif n <= 0xFFFFFFFF:
            self._buffer.write(struct.pack(">BI", 0xDB, n))
        else:
            raise ValueError("Raw is too large")

    def _pack_bin_header(self, n):
        if not self._use_bin_type:
            return self._pack_raw_header(n)
        elif n <= 0xFF:
            return self._buffer.write(struct.pack(">BB", 0xC4, n))
        elif n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xC5, n))
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xC6, n))
        else:
            raise ValueError("Bin is too large")

    def bytes(self):
        """Return internal buffer contents as bytes object"""
        return self._buffer.getvalue()

    def getbuffer(self):
        """Return view of internal buffer."""
        if USING_STRINGBUILDER:
            return memoryview(self.bytes())
        else:
            return self._buffer.getbuffer()
