/*
 * MessagePack for Python unpacking routine
 *
 * Copyright (C) 2009 Naoki INADA
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

#define MSGPACK_EMBED_STACK_SIZE  (1024)
#include "unpack_define.h"

typedef struct unpack_user {
    bool use_tuple;
    bool raw;
    bool object_as_pairs;
    bool strict_dict_key;

    PyObject* from_dict;
    PyObject* from_list;

    PyObject *giga;
    const char *unicode_errors;
    Py_ssize_t max_str_len, max_bin_len, max_list_len, max_dict_len;
} unpack_user;

typedef PyObject* tmsgpack_unpack_object;
struct unpack_context;
typedef struct unpack_context unpack_context;
typedef int (*execute_fn)(unpack_context *ctx, const char* data, Py_ssize_t len, Py_ssize_t* off);

static inline tmsgpack_unpack_object unpack_callback_root(unpack_user* u)
{
    return NULL;
}

static inline int unpack_callback_uint16(unpack_user* u, uint16_t d, tmsgpack_unpack_object* o)
{
    PyObject *p = PyInt_FromLong((long)d);
    if (!p)
        return -1;
    *o = p;
    return 0;
}
static inline int unpack_callback_uint8(unpack_user* u, uint8_t d, tmsgpack_unpack_object* o)
{
    return unpack_callback_uint16(u, d, o);
}


static inline int unpack_callback_uint32(unpack_user* u, uint32_t d, tmsgpack_unpack_object* o)
{
    PyObject *p = PyInt_FromSize_t((size_t)d);
    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_uint64(unpack_user* u, uint64_t d, tmsgpack_unpack_object* o)
{
    PyObject *p;
    if (d > LONG_MAX) {
        p = PyLong_FromUnsignedLongLong((unsigned PY_LONG_LONG)d);
    } else {
        p = PyInt_FromLong((long)d);
    }
    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_int32(unpack_user* u, int32_t d, tmsgpack_unpack_object* o)
{
    PyObject *p = PyInt_FromLong(d);
    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_int16(unpack_user* u, int16_t d, tmsgpack_unpack_object* o)
{
    return unpack_callback_int32(u, d, o);
}

static inline int unpack_callback_int8(unpack_user* u, int8_t d, tmsgpack_unpack_object* o)
{
    return unpack_callback_int32(u, d, o);
}

static inline int unpack_callback_int64(unpack_user* u, int64_t d, tmsgpack_unpack_object* o)
{
    PyObject *p;
    if (d > LONG_MAX || d < LONG_MIN) {
        p = PyLong_FromLongLong((PY_LONG_LONG)d);
    } else {
        p = PyInt_FromLong((long)d);
    }
    *o = p;
    return 0;
}

static inline int unpack_callback_double(unpack_user* u, double d, tmsgpack_unpack_object* o)
{
    PyObject *p = PyFloat_FromDouble(d);
    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_float(unpack_user* u, float d, tmsgpack_unpack_object* o)
{
    return unpack_callback_double(u, d, o);
}

static inline int unpack_callback_nil(unpack_user* u, tmsgpack_unpack_object* o)
{ Py_INCREF(Py_None); *o = Py_None; return 0; }

static inline int unpack_callback_true(unpack_user* u, tmsgpack_unpack_object* o)
{ Py_INCREF(Py_True); *o = Py_True; return 0; }

static inline int unpack_callback_false(unpack_user* u, tmsgpack_unpack_object* o)
{ Py_INCREF(Py_False); *o = Py_False; return 0; }

static inline int unpack_callback_list(unpack_user* u, unsigned int n, tmsgpack_unpack_object* o)
{
    if (n > u->max_list_len) {
        PyErr_Format(PyExc_ValueError, "%u exceeds max_list_len(%zd)", n, u->max_list_len);
        return -1;
    }
    PyObject *p = u->use_tuple ? PyTuple_New(n) : PyList_New(n);

    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_list_item(unpack_user* u, unsigned int current, tmsgpack_unpack_object* c, tmsgpack_unpack_object o)
{
    if (u->use_tuple)
        PyTuple_SET_ITEM(*c, current, o);
    else
        PyList_SET_ITEM(*c, current, o);
    return 0;
}

static inline int unpack_callback_list_end(
    unpack_user* u, PyObject** object_type, tmsgpack_unpack_object* c
)
{
    if(*object_type != Py_None) {
        PyObject *new_c = PyObject_CallFunctionObjArgs(
            u->from_list, *object_type, *c, NULL
        );
        Py_DECREF(*c);
        *c = new_c;
    }
    Py_DECREF(*object_type);
    *object_type = NULL;

    if(*c) { return 0;  }
    else   { return -1; }
}

static inline int unpack_callback_dict(unpack_user* u, unsigned int n, tmsgpack_unpack_object* o)
{
    if (n > u->max_dict_len) {
        PyErr_Format(PyExc_ValueError, "%u exceeds max_dict_len(%zd)", n, u->max_dict_len);
        return -1;
    }
    PyObject *p;
    if (u->object_as_pairs) {
        p = PyTuple_New(n); // Or use tuple?
    }
    else {
        p = PyDict_New();
    }
    if (!p)
        return -1;
    *o = p;
    return 0;
}

static inline int unpack_callback_dict_item(unpack_user* u, unsigned int current, tmsgpack_unpack_object* c, tmsgpack_unpack_object k, tmsgpack_unpack_object v)
{
    if (u->strict_dict_key && !PyUnicode_CheckExact(k) && !PyBytes_CheckExact(k)) {
        PyErr_Format(PyExc_ValueError, "%.100s is not allowed for dict key when strict_dict_key=True", Py_TYPE(k)->tp_name);
        return -1;
    }
    if (PyUnicode_CheckExact(k)) {
        PyUnicode_InternInPlace(&k);
    }
    if (u->object_as_pairs) {
        tmsgpack_unpack_object item = PyTuple_Pack(2, k, v);
        if (!item)
            return -1;
        Py_DECREF(k);
        Py_DECREF(v);
        PyTuple_SET_ITEM(*c, current, item);
        return 0;
    }
    else if (PyDict_SetItem(*c, k, v) == 0) {
        Py_DECREF(k);
        Py_DECREF(v);
        return 0;
    }
    return -1;
}

static inline int unpack_callback_dict_end(
    unpack_user* u, PyObject** object_type, tmsgpack_unpack_object* c
){
    if(u->object_as_pairs || *object_type != Py_None) {
        PyObject *new_c = PyObject_CallFunctionObjArgs(
            u->from_dict, *object_type, *c, NULL
        );
        Py_DECREF(*c);
        *c = new_c;
    }
    Py_DECREF(*object_type);
    *object_type = NULL;

    if(*c) { return 0;  }
    else   { return -1; }
}

static inline int unpack_callback_raw(unpack_user* u, const char* b, const char* p, unsigned int l, tmsgpack_unpack_object* o)
{
    if (l > u->max_str_len) {
        PyErr_Format(PyExc_ValueError, "%u exceeds max_str_len(%zd)", l, u->max_str_len);
        return -1;
    }

    PyObject *py;

    if (u->raw) {
        py = PyBytes_FromStringAndSize(p, l);
    } else {
        py = PyUnicode_DecodeUTF8(p, l, u->unicode_errors);
    }
    if (!py)
        return -1;
    *o = py;
    return 0;
}

static inline int unpack_callback_bin(unpack_user* u, const char* b, const char* p, unsigned int l, tmsgpack_unpack_object* o)
{
    if (l > u->max_bin_len) {
        PyErr_Format(PyExc_ValueError, "%u exceeds max_bin_len(%zd)", l, u->max_bin_len);
        return -1;
    }

    PyObject *py = PyBytes_FromStringAndSize(p, l);
    if (!py)
        return -1;
    *o = py;
    return 0;
}

#include "unpack_template.h"
