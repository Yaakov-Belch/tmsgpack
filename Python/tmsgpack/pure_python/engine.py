from .exceptions  import TMsgpackEncodingError, TMsgpackDecodingError

def ebuf_put_value(codec, ebuf, value):
    """Encode value to a msg and put it into ebuf."""

    i1_max=2**7;       i2_max=2**15;       i4_max=2**31;        i8_max=2**63
    ui1_max=2**8;      ui2_max=2**16;                           ui8_max=2**64

    FixInt2=129; FixInt4=130; FixInt8=131
    FixFloat8=132

    FixStr0=133
    VarStr1=149; VarStr2=150; VarStr8=151

    FixBytes0=152;     FixBytes1=153;      FixBytes2=154;       FixBytes4=155
    FixBytes8=156;     FixBytes16=157;     FixBytes20=158;      FixBytes32=159
    VarBytes1=160;     VarBytes2=161;      VarBytes8=162;

    FixTuple0=163
    VarTuple1=180;     VarTuple2=181;      VarTuple8=182
    ConstValStart=183; ConstValTrue=183;   ConstValFalse=184;   ConstValNone=185;
    NotUsed=186;       ConstNegInt=192
    min_ConstNegInt=ConstNegInt-ui1_max  # This is -64.

    NoneType = type(None)

    t = type(value)
    if t is int:
        if min_ConstNegInt <= value < 0: return ebuf.put_uint1(value + ui1_max)
        if 0 <= value < FixInt2:         return ebuf.put_uint1(value)

        if -i2_max <= value < i2_max: return ebuf.put_uint1(FixInt2).put_int2(value)
        if -i4_max <= value < i4_max: return ebuf.put_uint1(FixInt4).put_int4(value)
        if -i8_max <= value < i8_max: return ebuf.put_uint1(FixInt8).put_int8(value)

        raise TMsgpackEncodingError(f'Integer too large: {value}')

    if t is float: return ebuf.put_uint1(FixFloat8).put_float8(value)

    if t is str:
        str_bytes = value.encode('utf8')
        _len = len(str_bytes)

        # Str length header -- followed by string characters.
        if   _len < 16:      ebuf.put_uint1(FixStr0 + _len)
        elif _len < ui1_max: ebuf.put_uint1(VarStr1).put_uint1(_len)
        elif _len < ui2_max: ebuf.put_uint1(VarStr2).put_uint2(_len)
        elif _len < ui8_max: ebuf.put_uint1(VarStr8).put_uint8(_len)
        else: raise TMsgpackEncodingError(f'String too long: {_len}')

        return ebuf.put_bytes(str_bytes)

    if t is bool:
        if value is True:  return ebuf.put_uint1(ConstValTrue)
        if value is False: return ebuf.put_uint1(ConstValFalse)
        raise TMsgpackEncodingError(f'Illegal boolean value: {value}')

    if t is NoneType: return ebuf.put_uint1(ConstValNone)

    if   t is bytes: _mode, _type, new_value = 1, True,  value
    elif t is tuple: _mode, _type, new_value = 2, True,  value
    elif t is list:  _mode, _type, new_value = 2, False, value
    elif t is dict:  _mode, _type, new_value = 4, None,  value
    else:            _mode, _type, new_value = codec.decompose_value(value)

    if _mode == 0: return ebuf_put_value(codec, ebuf, new_value)

    if _mode == 1:
        if type(new_value) is not bytes:
            raise TMsgpackEncodingError(f'not bytes: {new_value}')

        _len = len(new_value)
        if   _len ==  0:     ebuf.put_uint1(FixBytes0)
        elif _len ==  1:     ebuf.put_uint1(FixBytes1)
        elif _len ==  2:     ebuf.put_uint1(FixBytes2)
        elif _len ==  4:     ebuf.put_uint1(FixBytes4)
        elif _len ==  8:     ebuf.put_uint1(FixBytes8)
        elif _len == 16:     ebuf.put_uint1(FixBytes16)
        elif _len == 20:     ebuf.put_uint1(FixBytes20)
        elif _len == 32:     ebuf.put_uint1(FixBytes32)
        elif _len < ui1_max: ebuf.put_uint1(VarBytes1).put_uint1(_len)
        elif _len < ui2_max: ebuf.put_uint1(VarBytes2).put_uint2(_len)
        elif _len < ui8_max: ebuf.put_uint1(VarBytes8).put_uint8(_len)
        else: raise TMsgpackEncodingError(f'Bytes too long: {_len}')

        ebuf_put_value(codec, ebuf, _type)
        return ebuf.put_bytes(new_value)


    def _tuple_header(ebuf, _len):
        if   _len < 17: ebuf.put_uint1(FixTuple0 + _len)
        elif _len < ui1_max: ebuf.put_uint1(VarTuple1).put_uint1(_len)
        elif _len < ui2_max: ebuf.put_uint1(VarTuple2).put_uint2(_len)
        elif _len < ui8_max: ebuf.put_uint1(VarTuple8).put_uint8(_len)
        else: return False
        return True

    if _mode == 2:
        _len = len(new_value)

        if not _tuple_header(ebuf, _len):
            raise TMsgpackEncodingError(f'Tuple too long: {_len}')

        ebuf_put_value(codec, ebuf, _type)
        for v in new_value: ebuf_put_value(codec, ebuf, v)
        return ebuf

    if (_mode == 3):
        if codec.sort_keys: _mode = 4
        else:               _mode = 5

    if (_mode == 4) or (_mode == 5):
        if   _mode == 4: pairs = sorted(new_value.items())
        elif _mode == 5: pairs = new_value.items()
        else: raise TMsgpackEncodingError(f'Undefined _mode: {_mode}')
        _len = 2 * len(pairs)

        if not _tuple_header(ebuf, _len):
            raise TMsgpackEncodingError(f'Dict too big: {_len//2}')

        ebuf_put_value(codec, ebuf, _type)
        for k, v in pairs:
            ebuf_put_value(codec, ebuf, k)
            ebuf_put_value(codec, ebuf, v)
        return ebuf

    raise TMsgpackEncodingError(f'Undefined _mode: {_mode}')

# --------------------------------------------------------------------------

def dbuf_take_value(codec, dbuf):
    """Take one msg out of dbuf and return the decoded value."""


    i1_max=2**7;       i2_max=2**15;       i4_max=2**31;        i8_max=2**63
    ui1_max=2**8;      ui2_max=2**16;                           ui8_max=2**64

    FixInt2=129; FixInt4=130; FixInt8=131
    FixFloat8=132

    FixStr0=133
    VarStr1=149; VarStr2=150; VarStr8=151

    FixBytes0=152;     FixBytes1=153;      FixBytes2=154;       FixBytes4=155
    FixBytes8=156;     FixBytes16=157;     FixBytes20=158;      FixBytes32=159
    VarBytes1=160;     VarBytes2=161;      VarBytes8=162;

    FixTuple0=163
    VarTuple1=180;     VarTuple2=181;      VarTuple8=182
    ConstValStart=183; ConstValTrue=183;   ConstValFalse=184;   ConstValNone=185;
    NotUsed=186;       ConstNegInt=192
    min_ConstNegInt=ConstNegInt-ui1_max  # This is -64.

    NoneType = type(None)


    _map_01248_16_20_32 = (0,1,2,4,8,16,20,32)
    _map_consts = (True, False, None)

    opcode = dbuf.take_uint1()

    if not (0 <= opcode < ui1_max):
        raise TMsgpackDecodingError(f'Opcode out of range 0-255: {opcode}')

    # Note: Reverse stacked ranges.
    # Every range is bounded above by the range right before it.
    # This is intentional and consistent with the format definition.
    # It provides correct upper bounds for opcodes in earch range.

    if ConstNegInt <= opcode : return opcode-ui1_max  # negative integer

    if NotUsed <= opcode: raise TMsgpackDecodingError(f'Undefined opcode: {opcode}')
    if ConstValStart <= opcode: return _map_consts[opcode-ConstValStart]

    if FixTuple0 <= opcode:
        if   opcode == VarTuple1: _len = dbuf.take_uint1()
        elif opcode == VarTuple2: _len = dbuf.take_uint2()
        elif opcode == VarTuple8: _len = dbuf.take_uint8()
        else:                     _len = opcode-FixTuple0  # FixTuple0, ..., FixTuple16

        _type = dbuf_take_value(codec, dbuf)
        _list = [dbuf_take_value(codec, dbuf) for _ in range(_len)]

        if _type is True:  return tuple(_list)
        if _type is False: return _list
        if _type is None:  return list_to_dict(_list)

        return codec.value_from_list(_type, _list)

    if FixBytes0 <= opcode:
        if   opcode == VarBytes1: _len = dbuf.take_uint1()
        elif opcode == VarBytes2: _len = dbuf.take_uint2()
        elif opcode == VarBytes8: _len = dbuf.take_uint8()
        else:                     _len = _map_01248_16_20_32[opcode-FixBytes0]
        # The else branch catches FixBytes0/1/2/4/8/16/20/32

        _type  = dbuf_take_value(codec, dbuf)
        _bytes = dbuf.take_bytes(_len)

        if _type is True: return _bytes
        return codec.value_from_bytes(_type, _bytes)

    if FixStr0 <= opcode:
        if opcode == VarStr1: return dbuf.take_str(dbuf.take_uint1())
        if opcode == VarStr2: return dbuf.take_str(dbuf.take_uint2())
        if opcode == VarStr8: return dbuf.take_str(dbuf.take_uint8())
        else:                 return dbuf.take_str(opcode-FixStr0)
        # The else branch catches FixStr0, ..., FixStr15

    if FixFloat8 <= opcode:   return dbuf.take_float8()
    if FixInt2   <= opcode:
        if opcode == FixInt2: return dbuf.take_int2()
        if opcode == FixInt4: return dbuf.take_int4()
        if opcode == FixInt8: return dbuf.take_int8()

    if 0         <= opcode:   return opcode  # const integer

def list_to_dict(t): return dict(zip(t[::2], t[1::2]))
