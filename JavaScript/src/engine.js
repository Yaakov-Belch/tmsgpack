import { TMsgpackEncodingError, TMsgpackDecodingError } from "./exceptions.js"

const i1_max = 2**7;
const i2_max = 2**15;
const i4_max = 2**31;

const ui1_max = 2**8;
const ui2_max = 2**16;

const FixInt2 = 129;
const FixInt4 = 130;
const FixInt8 = 131;
const FixFloat8 = 132;

const FixStr0 = 133;
const VarStr1 = 149;
const VarStr2 = 150;
const VarStr8 = 151;

const FixBytes0 = 152;
const FixBytes1 = 153;
const FixBytes2 = 154;
const FixBytes4 = 155;
const FixBytes8 = 156;
const FixBytes16 = 157;
const FixBytes20 = 158;
const FixBytes32 = 159;
const VarBytes1 = 160;
const VarBytes2 = 161;
const VarBytes8 = 162;

const FixTuple0 = 163;
const VarTuple1 = 180;
const VarTuple2 = 181;
const VarTuple8 = 182;
const ConstValStart = 183;
const ConstValTrue = 183;
const ConstValFalse = 184;
const ConstValNone = 185;
const NotUsed = 186;
const ConstNegInt = 192;

const min_ConstNegInt = ConstNegInt - ui1_max; // This is -64

class EncodeCtx {
    constructor(codec, ebuf) {
        this.codec     = codec;
        this.ebuf      = ebuf;
        this.value     = null;
        this.sort_keys = codec.sort_keys
        this._used     = true;   // Set to false direclty before use.
    }

    _v(value) { this.value=value; this._used=false; return this}

    _mark_use(expect_used) {
        if(expect_used !== this._used) {
            if(expect_used) { throw new TMsgpackEncodingError('ectx was not used.') }
            else            { throw new TMsgpackEncodingError('ectx used twice.')   }
        }
    }

    put_bytes(_type, value) {
        this._mark_use(false);
        const ebuf = this.ebuf;

        if (!(value instanceof Uint8Array)) {
            throw new TMsgpackEncodingError(`not Uint8Array: ${value}`);
        }

        const _len = value.length;
        if (_len === 0)          ebuf.put_uint1(FixBytes0);
        else if (_len === 1)     ebuf.put_uint1(FixBytes1);
        else if (_len === 2)     ebuf.put_uint1(FixBytes2);
        else if (_len === 4)     ebuf.put_uint1(FixBytes4);
        else if (_len === 8)     ebuf.put_uint1(FixBytes8);
        else if (_len === 16)    ebuf.put_uint1(FixBytes16);
        else if (_len === 20)    ebuf.put_uint1(FixBytes20);
        else if (_len === 32)    ebuf.put_uint1(FixBytes32);
        else if (_len < ui1_max) ebuf.put_uint1(VarBytes1).put_uint1(_len);
        else if (_len < ui2_max) ebuf.put_uint1(VarBytes2).put_uint2(_len);
        else                     ebuf.put_uint1(VarBytes8).put_uint8(_len);

        ectx_put_value(this, _type);
        return ebuf.put_bytes(value);
    }

    put_sequence(_type, value) {
        this._mark_use(false)
        const _len = value.length;
        const ebuf = this.ebuf

        _list_header(ebuf, _len)

        ectx_put_value(this, _type);
        for (const v of value) { ectx_put_value(this, v) }
    }

    put_dict(_type, value, sort=false) {
        const ebuf  = this.ebuf
        let   pairs = Object.entries(value);
        const _len  = 2 * pairs.length;
        _list_header(ebuf, _len)

        if (sort) { pairs = pairs.sort(([a], [b]) => ebuf.collator.compare(a, b)) }

        ectx_put_value(this, _type);
        for (const [k, v] of pairs) {
            ectx_put_value(this, k);
            ectx_put_value(this, v);
        }
    }
}

function _list_header(ebuf, _len) {
    if      (_len < 17)      { ebuf.put_uint1(FixTuple0 + _len);          }
    else if (_len < ui1_max) { ebuf.put_uint1(VarTuple1).put_uint1(_len); }
    else if (_len < ui2_max) { ebuf.put_uint1(VarTuple2).put_uint2(_len); }
    else                     { ebuf.put_uint1(VarTuple8).put_uint8(_len); }
}

export function ebuf_put_value(codec, ebuf, value) {
    return ectx_put_value(new EncodeCtx(codec, ebuf), value)
}

function ectx_put_value(ectx, value) {
    const codec = ectx.codec
    const ebuf = ectx.ebuf

    if (typeof value === 'number') {
        if (Number.isSafeInteger(value)) {                       // Integer path
            if (min_ConstNegInt <= value && value < 0) {
                return ebuf.put_uint1(value + ui1_max);}
            if (0 <= value && value < FixInt2) {
                return ebuf.put_uint1(value);
            }
            if (-i2_max <= value && value < i2_max) {
                return ebuf.put_uint1(FixInt2).put_int2(value);
            }
            if (-i4_max <= value && value < i4_max) {
                return ebuf.put_uint1(FixInt4).put_int4(value);
            }
            // Safe integers fit the limits:
            return ebuf.put_uint1(FixInt8).put_int8(value);
        } else {                                                 // Float path
            return ebuf.put_uint1(FixFloat8).put_float8(value);
        }
    }

    if (typeof value === 'string') {
        const str_bytes = ebuf.textEncoder.encode(value);
        const _len = str_bytes.length;

        // Str length header -- followed by string characters
        if (_len < 16) {
            ebuf.put_uint1(FixStr0 + _len);
        } else if (_len < ui1_max) {
            ebuf.put_uint1(VarStr1).put_uint1(_len);
        } else if (_len < ui2_max) {
            ebuf.put_uint1(VarStr2).put_uint2(_len);
        } else {
            ebuf.put_uint1(VarStr8).put_uint8(_len);
        }
        return ebuf.put_bytes(str_bytes);
    }

    if (typeof value === 'boolean') {
        return ebuf.put_uint1(value ? ConstValTrue : ConstValFalse);
    }

    if (value === null || value === undefined) {
        return ebuf.put_uint1(ConstValNone);
    }

    // Type detection for complex types
    const is_bytes = value instanceof Uint8Array
    const is_list  = Array.isArray(value)
    const is_dict  = value && typeof value === 'object' && value.constructor === Object

    if      (is_bytes) { ectx._v(null).put_bytes(true, value) }
    else if (is_list)  { ectx._v(null).put_sequence(true, value) }
    else if (is_dict)  { ectx._v(null).put_dict(null, value, codec.sort_keys) }
    else               { codec.decompose_value(ectx._v(value)); ectx._mark_use(true) }
}

class DecodeCtx {
    constructor() {
        this.codec  = codec;
        this.ebuf   = ebuf;
        this._len   = 0;
        this._type  = null;
        this._bytes = false;
        this._used  = true;   // Set to false direclty before use.
    }

    _ltb(_len, _type, _bytes) {
        this._len   = _len;
        this._type  = _type;
        this._bytes = _bytes;
        this._used  = false;
        return this
    }

    _mark_use(expect_used) {
        if(expect_used !== this._used) {
            if(expect_used) { throw new TMsgpackDecodingError('dctx was not used.') }
            else            { throw new TMsgpackDecodingError('dctx used twice.')   }
        }
    }


}




export function dbuf_take_value(codec, dbuf) {
    const opcode = dbuf.take_uint1();

    if (!(0 <= opcode && opcode < ui1_max)) {
        throw new TMsgpackDecodingError(`Opcode out of range 0-255: ${opcode}`);
    }

    // Note: Reverse stacked ranges.
    // Every range is bounded above by the range right before it.
    // This is intentional and consistent with the format definition.
    // It provides correct upper bounds for opcodes in each range.

    if (ConstNegInt <= opcode)   { return opcode - ui1_max; } // negative integer
    if (NotUsed <= opcode) {
        throw new TMsgpackDecodingError(`Undefined opcode: ${opcode}`);
    }
    if (ConstValStart <= opcode) { return _map_consts[opcode - ConstValStart]; }

    if (FixTuple0 <= opcode) {
        let _len;
        if (opcode === VarTuple1)      { _len = dbuf.take_uint1();  }
        else if (opcode === VarTuple2) { _len = dbuf.take_uint2();  }
        else if (opcode === VarTuple8) { _len = dbuf.take_uint8();  }
        else                           { _len = opcode - FixTuple0; } // FixTuple0-16

        const _type = dbuf_take_value(codec, dbuf);
        const _list = [];
        for (let i = 0; i < _len; i++) { _list.push(dbuf_take_value(codec, dbuf)); }

        if (_type === true)  { return _list; }  // In JavaScript, tuples and list...
        if (_type === false) { return _list; }  // ... are the same.
        if (_type === null)  { return list_to_dict(_list); }

        return codec.value_from_list(_type, _list);
    }

    if (FixBytes0 <= opcode) {
        let _len;
        if (opcode === VarBytes1)      { _len = dbuf.take_uint1(); }
        else if (opcode === VarBytes2) { _len = dbuf.take_uint2(); }
        else if (opcode === VarBytes8) { _len = dbuf.take_uint8(); }
        else                           { _len = _map_01248_16_20_32[opcode - FixBytes0]; }
        // The else branch catches FixBytes0/1/2/4/8/16/20/32

        const _type  = dbuf_take_value(codec, dbuf);
        const _bytes = dbuf.take_bytes(_len);

        if (_type === true) return _bytes;
        return codec.value_from_bytes(_type, _bytes);
    }

    if (FixStr0 <= opcode) {
        if (opcode === VarStr1) { return dbuf.take_str(dbuf.take_uint1()); }
        if (opcode === VarStr2) { return dbuf.take_str(dbuf.take_uint2()); }
        if (opcode === VarStr8) { return dbuf.take_str(dbuf.take_uint8()); }
        else                    { return dbuf.take_str(opcode - FixStr0);  } // FixStr0-15
    }

    if (FixFloat8 <= opcode)    { return dbuf.take_float8(); }

    if (FixInt2 <= opcode) {
        if (opcode === FixInt2) { return dbuf.take_int2(); }
        if (opcode === FixInt4) { return dbuf.take_int4(); }
        if (opcode === FixInt8) { return dbuf.take_int8(); }
    }

    if (0 <= opcode) return opcode; // const integer

    throw new TMsgpackDecodingError(`Unhandled opcode: ${opcode}`);
}

function list_to_dict(t) {
    const result = {};
    for (let i = 0; i < t.length; i += 2) {
        result[t[i]] = t[i + 1];
    }
    return result;
}

const _map_01248_16_20_32 = [0, 1, 2, 4, 8, 16, 20, 32];
const _map_consts = [true, false, null];








