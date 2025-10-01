import { TMsgpackEncodingError, TMsgpackDecodingError } from "./exceptions.js"

export class EncodeBuffer {
    constructor(initialSize, maxByteLength) {
        this.buffer  = new ArrayBuffer(initialSize, {maxByteLength});
        this.pos     = 0;
        this.max_pos = initialSize;

        this.textEncoder = new TextEncoder()
        this.collator = new Intl.Collator('en', {
            sensitivity: 'base',
            numeric: false,
            caseFirst: 'false'
        });
    }

    wr_window(n, asUint8Array=false) {
        const old_pos = this.pos;
        this.pos += n;

        if (this.pos > this.max_pos) {
            // Calculate new size - double until it's large enough
            let new_size = this.max_pos;
            while (new_size < this.pos) { new_size *= 2; }
            this.buffer.resize(new_size)
            this.max_pos = new_size;
        }

        return asUint8Array
            ? new Uint8Array(this.buffer, old_pos, n)
            : new DataView(this.buffer, old_pos, n);
    }

    put_bytes(value) {  // bytes means: Uint8Array
        this.wr_window(value.length, true).set(value)
        return this;
    }

    put_int1(value) {
        this.wr_window(1).setInt8(0, value, true);
        return this;
    }

    put_int2(value) {
        this.wr_window(2).setInt16(0, value, true); // true = little-endian
        return this;
    }

    put_int4(value) {
        this.wr_window(4).setInt32(0, value, true);
        return this;
    }

    put_int8(value) {
        this.wr_window(8).setBigInt64(0, BigInt(value), true);
        return this;
    }

    put_uint1(value) {
        this.wr_window(1).setUint8(0, value, true);
        return this;
    }

    put_uint2(value) {
        this.wr_window(2).setUint16(0, value, true);
        return this;
    }

    put_uint4(value) {
        this.wr_window(4).setUint32(0, value, true);
        return this;
    }

    put_uint8(value) {
        this.wr_window(8).setBigUint64(0, BigInt(value), true);
        return this;
    }

    put_float4(value) {
        this.wr_window(4).setFloat32(0, value, true);
        return this;
    }

    put_float8(value) {
        this.wr_window(8).setFloat64(0, value, true);
        return this;
    }

    as_bytes() {
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
