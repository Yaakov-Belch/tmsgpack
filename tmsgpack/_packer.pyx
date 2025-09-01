# coding: utf-8

from cpython cimport *
from cpython.bytearray cimport PyByteArray_Check, PyByteArray_CheckExact

cdef extern from "Python.h":

    int PyMemoryView_Check(object obj)
    char* PyUnicode_AsUTF8AndSize(object obj, Py_ssize_t *l) except NULL


cdef extern from "pack.h":
    struct tmsgpack_packer:
        char* buf
        size_t length
        size_t buf_size
        bint use_bin_type

    int tmsgpack_pack_int(tmsgpack_packer* pk, int d)
    int tmsgpack_pack_nil(tmsgpack_packer* pk)
    int tmsgpack_pack_true(tmsgpack_packer* pk)
    int tmsgpack_pack_false(tmsgpack_packer* pk)
    int tmsgpack_pack_long(tmsgpack_packer* pk, long d)
    int tmsgpack_pack_long_long(tmsgpack_packer* pk, long long d)
    int tmsgpack_pack_unsigned_long_long(tmsgpack_packer* pk, unsigned long long d)
    int tmsgpack_pack_float(tmsgpack_packer* pk, float d)
    int tmsgpack_pack_double(tmsgpack_packer* pk, double d)
    int tmsgpack_pack_list(tmsgpack_packer* pk, size_t l)
    int tmsgpack_pack_dict(tmsgpack_packer* pk, size_t l)
    int tmsgpack_pack_raw(tmsgpack_packer* pk, size_t l)
    int tmsgpack_pack_bin(tmsgpack_packer* pk, size_t l)
    int tmsgpack_pack_raw_body(tmsgpack_packer* pk, char* body, size_t l)
    int tmsgpack_pack_unicode(tmsgpack_packer* pk, object o, long long limit)

cdef extern from "buff_converter.h":
    object buff_to_buff(char *, Py_ssize_t)

cdef int DEFAULT_RECURSE_LIMIT=511
cdef long long ITEM_LIMIT = (2**32)-1


cdef inline int PyBytesLike_Check(object o):
    return PyBytes_Check(o) or PyByteArray_Check(o)


cdef inline int PyBytesLike_CheckExact(object o):
    return PyBytes_CheckExact(o) or PyByteArray_CheckExact(o)


cdef class Packer(object):
    """
    tmsgpack Packer

    Usage::

        packer = Packer()
        astream.write(packer.pack(a))
        astream.write(packer.pack(b))

    Packer's constructor has some keyword arguments:

    :param object pack_ctrl:
        Pack control context.
    """
    cdef object from_obj
    cdef tmsgpack_packer pk
    cdef object _berrors
    cdef const char *unicode_errors
    cdef bint tuple_as_list
    cdef bint strict_types
    cdef bint use_float
    cdef bool sort_keys

    def __cinit__(self):
        cdef int buf_size = 1024*1024
        self.pk.buf = <char*> PyMem_Malloc(buf_size)
        if self.pk.buf == NULL:
            raise MemoryError("Unable to allocate internal buffer.")
        self.pk.buf_size = buf_size
        self.pk.length = 0

    def __init__(self, *, object pack_ctrl):
        if pack_ctrl is None:
           raise(ValueError("No pack_ctrl supplied."))

        self.from_obj = pack_ctrl.from_obj

        o = pack_ctrl.options

        self.use_float       = o.use_single_float
        self.tuple_as_list   = o.tuple_as_list
        self.strict_types    = o.strict_types
        self.pk.use_bin_type = o.use_bin_type

        self._berrors = o.unicode_errors
        if o.unicode_errors is None:
            self.unicode_errors = NULL
        else:
            self.unicode_errors = self._berrors

        self.sort_keys = o.sort_keys

    def __dealloc__(self):
        PyMem_Free(self.pk.buf)
        self.pk.buf = NULL

    cdef int _pack(self, object o, int nest_limit=DEFAULT_RECURSE_LIMIT) except -1:
        cdef long long llval
        cdef unsigned long long ullval
        cdef unsigned long ulval
        cdef long longval
        cdef float fval
        cdef double dval
        cdef char* rawval
        cdef int ret
        cdef dict d
        cdef Py_ssize_t L
        cdef bint strict_types = self.strict_types
        cdef Py_buffer view
        cdef tuple_as_list = self.tuple_as_list

        if nest_limit < 0:
            raise ValueError("recursion limit exceeded.")

        while True:
            if o is None:
                ret = tmsgpack_pack_nil(&self.pk)
            elif o is True:
                ret = tmsgpack_pack_true(&self.pk)
            elif o is False:
                ret = tmsgpack_pack_false(&self.pk)
            elif PyLong_CheckExact(o) if strict_types else PyLong_Check(o):
                # PyInt_Check(long) is True for Python 3.
                # So we should test long before int.
                try:
                    if o > 0:
                        ullval = o
                        ret = tmsgpack_pack_unsigned_long_long(&self.pk, ullval)
                    else:
                        llval = o
                        ret = tmsgpack_pack_long_long(&self.pk, llval)
                except OverflowError as oe:
                    raise OverflowError("Integer value out of range")
            elif PyInt_CheckExact(o) if strict_types else PyInt_Check(o):
                longval = o
                ret = tmsgpack_pack_long(&self.pk, longval)
            elif PyFloat_CheckExact(o) if strict_types else PyFloat_Check(o):
                if self.use_float:
                   fval = o
                   ret = tmsgpack_pack_float(&self.pk, fval)
                else:
                   dval = o
                   ret = tmsgpack_pack_double(&self.pk, dval)
            elif PyBytesLike_CheckExact(o) if strict_types else PyBytesLike_Check(o):
                L = Py_SIZE(o)
                if L > ITEM_LIMIT:
                    PyErr_Format(ValueError, b"%.200s object is too large", Py_TYPE(o).tp_name)
                rawval = o
                ret = tmsgpack_pack_bin(&self.pk, L)
                if ret == 0:
                    ret = tmsgpack_pack_raw_body(&self.pk, rawval, L)
            elif PyUnicode_CheckExact(o) if strict_types else PyUnicode_Check(o):
                if self.unicode_errors == NULL:
                    ret = tmsgpack_pack_unicode(&self.pk, o, ITEM_LIMIT);
                    if ret == -2:
                        raise ValueError("unicode string is too large")
                else:
                    o = PyUnicode_AsEncodedString(o, NULL, self.unicode_errors)
                    L = Py_SIZE(o)
                    if L > ITEM_LIMIT:
                        raise ValueError("unicode string is too large")
                    ret = tmsgpack_pack_raw(&self.pk, L)
                    if ret == 0:
                        rawval = o
                        ret = tmsgpack_pack_raw_body(&self.pk, rawval, L)
            elif PyMemoryView_Check(o):
                if PyObject_GetBuffer(o, &view, PyBUF_SIMPLE) != 0:
                    raise ValueError("could not get buffer for memoryview")
                L = view.len
                if L > ITEM_LIMIT:
                    PyBuffer_Release(&view);
                    raise ValueError("memoryview is too large")
                ret = tmsgpack_pack_bin(&self.pk, L)
                if ret == 0:
                    ret = tmsgpack_pack_raw_body(&self.pk, <char*>view.buf, L)
                PyBuffer_Release(&view);
            else:
                if PyDict_CheckExact(o):
                    as_dict, object_type, data = True, None, o
                elif PyList_CheckExact(o) or (tuple_as_list and PyTuple_CheckExact(o)):
                    as_dict, object_type, data = False, None, o
                else:
                    as_dict, object_type, data = self.from_obj(o)

                if as_dict:
                    d = <dict>data
                    L = len(d)
                    if L > ITEM_LIMIT:
                        raise ValueError("dict is too large")
                    ret = tmsgpack_pack_dict(&self.pk, L)
                    if ret != 0: return ret
                    ret = self._pack(object_type, nest_limit-1)
                    if ret == 0:
                        _items = sorted(d.items()) if self.sort_keys else d.items()
                        for k, v in _items:
                            ret = self._pack(k, nest_limit-1)
                            if ret != 0: break
                            ret = self._pack(v, nest_limit-1)
                            if ret != 0: break
                else:
                    L = Py_SIZE(data)
                    if L > ITEM_LIMIT:
                        raise ValueError("list is too large")
                    ret = tmsgpack_pack_list(&self.pk, L)
                    if ret != 0: return ret
                    ret = self._pack(object_type, nest_limit-1)
                    if ret == 0:
                        for v in data:
                            ret = self._pack(v, nest_limit-1)
                            if ret != 0: break
            return ret

    cpdef pack(self, object obj):
        cdef int ret
        try:
            ret = self._pack(obj, DEFAULT_RECURSE_LIMIT)
        except:
            self.pk.length = 0
            raise
        if ret:  # should not happen.
            raise RuntimeError("internal error")
        buf = PyBytes_FromStringAndSize(self.pk.buf, self.pk.length)
        self.pk.length = 0
        return buf

    def pack_list_header(self, long long size):
        if size > ITEM_LIMIT:
            raise ValueError
        cdef int ret = tmsgpack_pack_list(&self.pk, size)
        if ret == -1:
            raise MemoryError
        elif ret:  # should not happen
            raise TypeError
        buf = PyBytes_FromStringAndSize(self.pk.buf, self.pk.length)
        self.pk.length = 0
        return buf

    def pack_dict_header(self, long long size):
        if size > ITEM_LIMIT:
            raise ValueError
        cdef int ret = tmsgpack_pack_dict(&self.pk, size)
        if ret == -1:
            raise MemoryError
        elif ret:  # should not happen
            raise TypeError
        buf = PyBytes_FromStringAndSize(self.pk.buf, self.pk.length)
        self.pk.length = 0
        return buf

    def pack_dict_pairs(self, object object_type, object pairs):
        """
        Pack *pairs* as tmsgpack dict type.

        *pairs* should be a sequence of pairs.
        (`len(pairs)` and `for k, v in pairs:` should be supported.)
        """
        cdef int ret = tmsgpack_pack_dict(&self.pk, len(pairs))
        if ret == 0:
            ret = self._pack(object_type)
        if ret == 0:
            for k, v in pairs:
                ret = self._pack(k)
                if ret != 0: break
                ret = self._pack(v)
                if ret != 0: break
        if ret == -1:
            raise MemoryError
        elif ret:  # should not happen
            raise TypeError
        buf = PyBytes_FromStringAndSize(self.pk.buf, self.pk.length)
        self.pk.length = 0
        return buf

    def bytes(self):
        """Return internal buffer contents as bytes object"""
        return PyBytes_FromStringAndSize(self.pk.buf, self.pk.length)

    def getbuffer(self):
        """Return view of internal buffer."""
        return buff_to_buff(self.pk.buf, self.pk.length)
