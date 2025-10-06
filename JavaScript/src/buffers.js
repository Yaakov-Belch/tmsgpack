import { TMsgpackEncodingError, TMsgpackDecodingError } from "./exceptions.js"

export class EncodeBuffer {
    constructor(initialSize, maxByteLength) {
        this.buffer     = new ArrayBuffer(initialSize, {maxByteLength});
        this.data_view  = new DataView(this.buffer);
        this.uint8Array = new Uint8Array(this.buffer);
        this.pos        = 0;
        this.max_pos    = initialSize;

        this.textEncoder = new TextEncoder()
        this.collator = new Intl.Collator('en', {
            sensitivity: 'base',
            numeric: false,
            caseFirst: 'false'
        });
    }

    wr(method, n, value, setUint8Array=false) {
        const old_pos = this.pos;
        this.pos += n;

        if (this.pos > this.max_pos) {
            // Calculate new size - double until it's large enough
            let new_size = this.max_pos;
            while (new_size < this.pos) { new_size *= 2; }
            this.buffer.resize(new_size)
            this.max_pos    = new_size;
            this.data_view  = new DataView(this.buffer);
            this.uint8Array = new Uint8Array(this.buffer);
        }

        if(setUint8Array) {
          this.uint8Array[method](value, old_pos)       // method should be 'set'
        } else {
          this.data_view[method](old_pos, value, true)     // true means little-endian
        }
        return this
    }

    // 'bytes' means: Uint8Array
    put_bytes(value)  { return this.wr('set', value.length, value, true) }

    put_int1(value)   { return this.wr('setInt8',      1, value) }
    put_int2(value)   { return this.wr('setInt16',     2, value) }
    put_int4(value)   { return this.wr('setInt32',     4, value) }
    put_int8(value)   { return this.wr('setBigInt64',  8, BigInt(value)) }

    put_uint1(value)  { return this.wr('setUint8',     1, value) }
    put_uint2(value)  { return this.wr('setUint16',    2, value) }
    put_uint4(value)  { return this.wr('setUint32',    4, value) }
    put_uint8(value)  { return this.wr('setBigUint64', 8, BigInt(value)) }

    put_float4(value) { return this.wr('setFloat32',   4, value) }
    put_float8(value) { return this.wr('setFloat64',   8, value) }

    as_bytes() {
        // Copy buffer slice so that the result is not resizable!
        return new Uint8Array(this.buffer.slice(0, this.pos));
    } 
}

export class DecodeBuffer {
    constructor(bytes, start = 0, end = null) {
        this.buffer = bytes.buffer.slice(
            bytes.byteOffset, bytes.byteOffset + bytes.byteLength,
        );
        this.pos = start;
        this.end = end !== null ? end : this.buffer.byteLength;
        this.textDecoder = new TextDecoder('utf-8');
    }

    rd_window(n, asUint8Array = false) {
        const old_pos = this.pos;
        this.pos += n;

        if (this.pos > this.end) {
            throw new TMsgpackDecodingError('Not enough input data');
        }

        return asUint8Array
            ? new Uint8Array(this.buffer, old_pos, n)
            : new DataView(this.buffer, old_pos, n);
    }

    take_bytes(n) { return this.rd_window(n, true); }
    take_str(n)   { return this.textDecoder.decode(this.take_bytes(n)); }
    take_int1()   { return this.rd_window(1).getInt8(0, true); }
    take_int2()   { return this.rd_window(2).getInt16(0, true); }
    take_int4()   { return this.rd_window(4).getInt32(0, true); }
    take_int8()   { return Number(this.rd_window(8).getBigInt64(0, true)); }
    take_uint1()  { return this.rd_window(1).getUint8(0, true); }
    take_uint2()  { return this.rd_window(2).getUint16(0, true); }
    take_uint4()  { return this.rd_window(4).getUint32(0, true); }
    take_uint8()  { return Number(this.rd_window(8).getBigUint64(0, true)); }
    take_float8() { return this.rd_window(8).getFloat64(0, true); }
}
