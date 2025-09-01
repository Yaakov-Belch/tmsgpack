/*
 * MessagePack unpacking routine template
 *
 * Copyright (C) 2008-2010 FURUHASHI Sadayuki
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

#ifndef USE_CASE_RANGE
#if !defined(_MSC_VER)
#define USE_CASE_RANGE
#endif
#endif

typedef struct unpack_stack {
    PyObject* obj;
    Py_ssize_t size;
    Py_ssize_t count;
    unsigned int ct;
    unsigned int ct_next;
    PyObject* object_type;
    PyObject* dict_key;
} unpack_stack;

struct unpack_context {
    unpack_user user;
    unsigned int cs;
    unsigned int trail;
    unsigned int top;
    /*
    unpack_stack* stack;
    unsigned int stack_size;
    unpack_stack embed_stack[MSGPACK_EMBED_STACK_SIZE];
    */
    unpack_stack stack[MSGPACK_EMBED_STACK_SIZE];
};


static inline void unpack_init(unpack_context* ctx)
{
    ctx->cs = CS_HEADER;
    ctx->trail = 0;
    ctx->top = 0;
    /*
    ctx->stack = ctx->embed_stack;
    ctx->stack_size = MSGPACK_EMBED_STACK_SIZE;
    */
    ctx->stack[0].obj = unpack_callback_root(&ctx->user);
}

/*
static inline void unpack_destroy(unpack_context* ctx)
{
    if(ctx->stack_size != MSGPACK_EMBED_STACK_SIZE) {
        free(ctx->stack);
    }
}
*/

static inline PyObject* unpack_data(unpack_context* ctx)
{
    return (ctx)->stack[0].obj;
}

static inline void unpack_clear(unpack_context *ctx)
{
    Py_CLEAR(ctx->stack[0].obj);
}

static inline int unpack_construct(unpack_context* ctx, const char* data, Py_ssize_t len, Py_ssize_t* off)
{
    assert(len >= *off);

    const unsigned char* p = (unsigned char*)data + *off;
    const unsigned char* const pe = (unsigned char*)data + len;
    const void* n = p;

    unsigned int trail = ctx->trail;
    unsigned int cs = ctx->cs;
    unsigned int top = ctx->top;
    unpack_stack* stack = ctx->stack;
    /*
    unsigned int stack_size = ctx->stack_size;
    */
    unpack_user* user = &ctx->user;

    PyObject* obj = NULL;
    unpack_stack* c = NULL;

    int ret;

#define push_simple_value(func) \
    if((unpack_callback ## func)(user, &obj) < 0) { goto _failed; } \
    goto _push
#define push_fixed_value(func, arg) \
    if((unpack_callback ## func)(user, arg, &obj) < 0) { goto _failed; } \
    goto _push
#define push_variable_value(func, base, pos, len) \
    if((unpack_callback ## func)(user, \
        (const char*)base, (const char*)pos, len, &obj) < 0) { goto _failed; } \
    goto _push

#define again_fixed_trail(_cs, trail_len) \
    trail = trail_len; \
    cs = _cs; \
    goto _fixed_trail_again
#define again_fixed_trail_if_zero(_cs, trail_len, ifzero) \
    trail = trail_len; \
    if(trail == 0) { goto ifzero; } \
    cs = _cs; \
    goto _fixed_trail_again

#define start_container(func, count_, ct_next_) \
    if(top >= MSGPACK_EMBED_STACK_SIZE) { ret = -3; goto _end; } \
    if((unpack_callback ## func)(user, count_, &stack[top].obj) < 0) { goto _failed; } \
    stack[top].ct      = CT_CONTAINER_TYPE; \
    stack[top].ct_next = ct_next_; \
    stack[top].size    = count_; \
    stack[top].count   = 0; \
    stack[top].object_type = stack[top].dict_key = NULL; \
    ++top; \
    goto _header_again

#define NEXT_CS(p)  ((unsigned int)*p & 0x1f)

#ifdef USE_CASE_RANGE
#define SWITCH_RANGE_BEGIN     switch(*p) {
#define SWITCH_RANGE(FROM, TO) case FROM ... TO:
#define SWITCH_RANGE_DEFAULT   default:
#define SWITCH_RANGE_END       }
#else
#define SWITCH_RANGE_BEGIN     { if(0) {
#define SWITCH_RANGE(FROM, TO) } else if(FROM <= *p && *p <= TO) {
#define SWITCH_RANGE_DEFAULT   } else {
#define SWITCH_RANGE_END       } }
#endif

    if(p == pe) { goto _out; }
    do {
        switch(cs) {
        case CS_HEADER:
            SWITCH_RANGE_BEGIN
            SWITCH_RANGE(0x00, 0x7f)  // Positive Fixnum
                push_fixed_value(_uint8, *(uint8_t*)p);
            SWITCH_RANGE(0xe0, 0xff)  // Negative Fixnum
                push_fixed_value(_int8, *(int8_t*)p);
            SWITCH_RANGE(0xc0, 0xdf)  // Variable
                switch(*p) {
                case 0xc0:  // nil
                    push_simple_value(_nil);
                //case 0xc1:  // never used
                case 0xc2:  // false
                    push_simple_value(_false);
                case 0xc3:  // true
                    push_simple_value(_true);
                case 0xc4:  // bin 8
                    again_fixed_trail(NEXT_CS(p), 1);
                case 0xc5:  // bin 16
                    again_fixed_trail(NEXT_CS(p), 2);
                case 0xc6:  // bin 32
                    again_fixed_trail(NEXT_CS(p), 4);

                case 0xc7:  // ext 8     -- removed
                case 0xc8:  // ext 16    -- removed
                case 0xc9:  // ext 32    -- removed
                    ret = -2;
                    goto _end;

                case 0xca:  // float
                case 0xcb:  // double
                case 0xcc:  // unsigned int  8
                case 0xcd:  // unsigned int 16
                case 0xce:  // unsigned int 32
                case 0xcf:  // unsigned int 64
                case 0xd0:  // signed int  8
                case 0xd1:  // signed int 16
                case 0xd2:  // signed int 32
                case 0xd3:  // signed int 64
                    again_fixed_trail(NEXT_CS(p), 1 << (((unsigned int)*p) & 0x03));

                case 0xd4:  // fixext 1  -- removed
                case 0xd5:  // fixext 2  -- removed
                case 0xd6:  // fixext 4  -- removed
                case 0xd7:  // fixext 8  -- removed
                case 0xd8:  // fixext 16 -- removed
                    ret = -2;
                    goto _end;

                case 0xd9:  // str 8
                    again_fixed_trail(NEXT_CS(p), 1);
                case 0xda:  // raw 16
                case 0xdb:  // raw 32
                case 0xdc:  // list 16
                case 0xdd:  // list 32
                case 0xde:  // dict 16
                case 0xdf:  // dict 32
                    again_fixed_trail(NEXT_CS(p), 2 << (((unsigned int)*p) & 0x01));
                default:
                    ret = -2;
                    goto _end;
                }
            SWITCH_RANGE(0xa0, 0xbf)  // FixRaw
                again_fixed_trail_if_zero(ACS_RAW_VALUE, ((unsigned int)*p & 0x1f), _raw_zero);
            SWITCH_RANGE(0x90, 0x9f)  // FixList
                start_container(_list, ((unsigned int)*p) & 0x0f, CT_LIST_ITEM);
            SWITCH_RANGE(0x80, 0x8f)  // FixDict
                start_container(_dict, ((unsigned int)*p) & 0x0f, CT_DICT_KEY);

            SWITCH_RANGE_DEFAULT
                ret = -2;
                goto _end;
            SWITCH_RANGE_END
            // end CS_HEADER


        _fixed_trail_again:
            ++p;

        default:
            if((size_t)(pe - p) < trail) { goto _out; }
            n = p;  p += trail - 1;
            switch(cs) {
            case CS_EXT_8:  // removed
            case CS_EXT_16: // removed
            case CS_EXT_32: // removed
                    ret = -2;
                    goto _end;

            case CS_FLOAT: {
                    double f;
#if PY_VERSION_HEX >= 0x030B00A7
                    f = PyFloat_Unpack4((const char*)n, 0);
#else
                    f = _PyFloat_Unpack4((unsigned char*)n, 0);
#endif
                    push_fixed_value(_float, f); }
            case CS_DOUBLE: {
                    double f;
#if PY_VERSION_HEX >= 0x030B00A7
                    f = PyFloat_Unpack8((const char*)n, 0);
#else
                    f = _PyFloat_Unpack8((unsigned char*)n, 0);
#endif
                    push_fixed_value(_double, f); }
            case CS_UINT_8:
                push_fixed_value(_uint8, *(uint8_t*)n);
            case CS_UINT_16:
                push_fixed_value(_uint16, _tmsgpack_load16(uint16_t,n));
            case CS_UINT_32:
                push_fixed_value(_uint32, _tmsgpack_load32(uint32_t,n));
            case CS_UINT_64:
                push_fixed_value(_uint64, _tmsgpack_load64(uint64_t,n));

            case CS_INT_8:
                push_fixed_value(_int8, *(int8_t*)n);
            case CS_INT_16:
                push_fixed_value(_int16, _tmsgpack_load16(int16_t,n));
            case CS_INT_32:
                push_fixed_value(_int32, _tmsgpack_load32(int32_t,n));
            case CS_INT_64:
                push_fixed_value(_int64, _tmsgpack_load64(int64_t,n));

            case CS_BIN_8:
                again_fixed_trail_if_zero(ACS_BIN_VALUE, *(uint8_t*)n, _bin_zero);
            case CS_BIN_16:
                again_fixed_trail_if_zero(ACS_BIN_VALUE, _tmsgpack_load16(uint16_t,n), _bin_zero);
            case CS_BIN_32:
                again_fixed_trail_if_zero(ACS_BIN_VALUE, _tmsgpack_load32(uint32_t,n), _bin_zero);
            case ACS_BIN_VALUE:
            _bin_zero:
                push_variable_value(_bin, data, n, trail);

            case CS_RAW_8:
                again_fixed_trail_if_zero(ACS_RAW_VALUE, *(uint8_t*)n, _raw_zero);
            case CS_RAW_16:
                again_fixed_trail_if_zero(ACS_RAW_VALUE, _tmsgpack_load16(uint16_t,n), _raw_zero);
            case CS_RAW_32:
                again_fixed_trail_if_zero(ACS_RAW_VALUE, _tmsgpack_load32(uint32_t,n), _raw_zero);
            case ACS_RAW_VALUE:
            _raw_zero:
                push_variable_value(_raw, data, n, trail);

            case CS_LIST_16:
                start_container(_list, _tmsgpack_load16(uint16_t,n), CT_LIST_ITEM);
            case CS_LIST_32:
                /* FIXME security guard */
                start_container(_list, _tmsgpack_load32(uint32_t,n), CT_LIST_ITEM);

            case CS_DICT_16:
                start_container(_dict, _tmsgpack_load16(uint16_t,n), CT_DICT_KEY);
            case CS_DICT_32:
                /* FIXME security guard */
                start_container(_dict, _tmsgpack_load32(uint32_t,n), CT_DICT_KEY);

            default:
                goto _failed;
            }
        }

_push:
    if(top == 0) { goto _finish; }
    c = &stack[top-1];
    switch(c->ct) {
    case CT_CONTAINER_TYPE:
        c->object_type = obj;
        c->ct = c->ct_next;
        goto _check_container_end;
    case CT_DICT_KEY:
        c->dict_key = obj;
        c->ct = CT_DICT_VALUE;
        goto _header_again;
    case CT_DICT_VALUE:
        if(unpack_callback_dict_item(user, c->count, &c->obj, c->dict_key, obj) < 0) { goto _failed; }
        ++c->count;
        c->ct = CT_DICT_KEY;
        goto _check_container_end;
    case CT_LIST_ITEM:
        if(unpack_callback_list_item(user, c->count, &c->obj, obj) < 0) { goto _failed; }
        ++c->count;
        goto _check_container_end;
    default:
        goto _failed;
    }

_check_container_end:
    c = &stack[top-1];
    if(c->count == c->size) {
        PyObject** object_type = &c->object_type;
        obj = c->obj;
        if(c->ct == CT_LIST_ITEM) {
           if (unpack_callback_list_end(user, object_type, &obj) < 0) { goto _failed; }
        } else if (c->ct == CT_DICT_KEY) {
           if (unpack_callback_dict_end(user, object_type, &obj) < 0) { goto _failed; }
        } else {
           goto _failed;
        }
        --top;
        goto _push;
    }
    goto _header_again;

_header_again:
        cs = CS_HEADER;
        ++p;
    } while(p != pe);
    goto _out;


_finish:
    stack[0].obj = obj;
    ++p;
    ret = 1;
    /*printf("-- finish --\n"); */
    goto _end;

_failed:
    /*printf("** FAILED **\n"); */
    ret = -1;
    goto _end;

_out:
    ret = 0;
    goto _end;

_end:
    ctx->cs = cs;
    ctx->trail = trail;
    ctx->top = top;
    *off = p - (const unsigned char*)data;

    return ret;
}

#undef SWITCH_RANGE_BEGIN
#undef SWITCH_RANGE
#undef SWITCH_RANGE_DEFAULT
#undef SWITCH_RANGE_END
#undef push_simple_value
#undef push_fixed_value
#undef push_variable_value
#undef again_fixed_trail
#undef again_fixed_trail_if_zero
#undef start_container

#undef SWITCH_RANGE_BEGIN
#undef SWITCH_RANGE
#undef SWITCH_RANGE_DEFAULT
#undef SWITCH_RANGE_END
#undef NEXT_CS

/* vim: set ts=4 sw=4 sts=4 expandtab  */
