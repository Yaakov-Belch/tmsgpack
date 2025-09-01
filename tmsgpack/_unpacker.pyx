# coding: utf-8

from cpython cimport *
cdef extern from "Python.h":
    ctypedef struct PyObject
    object PyMemoryView_GetContiguous(object obj, int buffertype, char order)

from libc.stdlib cimport *
from libc.string cimport *
from libc.limits cimport *
from libc.stdint cimport uint64_t

from .exceptions import (
    BufferFull,
    OutOfData,
    ExtraData,
    FormatError,
    StackError,
)
cdef object giga = 1_000_000_000

cdef extern from "unpack.h":
    ctypedef struct tmsgpack_user:
        bint use_tuple
        bint raw
        bint object_as_pairs
        bint strict_dict_key

        PyObject* from_dict;
        PyObject* from_list;

        PyObject *giga;
        char *unicode_errors
        Py_ssize_t max_str_len
        Py_ssize_t max_bin_len
        Py_ssize_t max_list_len
        Py_ssize_t max_dict_len

    ctypedef struct unpack_context:
        tmsgpack_user user
        PyObject* obj
        Py_ssize_t count

    ctypedef int (*execute_fn)(unpack_context* ctx, const char* data,
                               Py_ssize_t len, Py_ssize_t* off) except? -1
    execute_fn unpack_construct
    void unpack_init(unpack_context* ctx)
    object unpack_data(unpack_context* ctx)
    void unpack_clear(unpack_context* ctx)

cdef inline init_ctx(unpack_context *ctx,
                     object from_dict, object from_list,
                     bint object_as_pairs,
                     bint use_tuple, bint raw,
                     bint strict_dict_key,
                     const char* unicode_errors,
                     Py_ssize_t max_str_len, Py_ssize_t max_bin_len,
                     Py_ssize_t max_list_len, Py_ssize_t max_dict_len):
    unpack_init(ctx)
    ctx.user.use_tuple = use_tuple
    ctx.user.raw = raw
    ctx.user.strict_dict_key = strict_dict_key

    ctx.user.from_dict = <PyObject*>from_dict
    ctx.user.from_list = <PyObject*>from_list

    ctx.user.max_str_len  = max_str_len
    ctx.user.max_bin_len  = max_bin_len
    ctx.user.max_list_len = max_list_len
    ctx.user.max_dict_len = max_dict_len

    ctx.user.object_as_pairs = object_as_pairs

    ctx.user.giga = <PyObject*>giga
    ctx.user.unicode_errors = unicode_errors

cdef inline int get_data_from_buffer(object obj,
                                     Py_buffer *view,
                                     char **buf,
                                     Py_ssize_t *buffer_len) except 0:
    cdef object contiguous
    cdef Py_buffer tmp
    if PyObject_GetBuffer(obj, view, PyBUF_FULL_RO) == -1:
        raise
    if view.itemsize != 1:
        PyBuffer_Release(view)
        raise BufferError("cannot unpack from multi-byte object")
    if PyBuffer_IsContiguous(view, b'A') == 0:
        PyBuffer_Release(view)
        # create a contiguous copy and get buffer
        contiguous = PyMemoryView_GetContiguous(obj, PyBUF_READ, b'C')
        PyObject_GetBuffer(contiguous, view, PyBUF_SIMPLE)
        # view must hold the only reference to contiguous,
        # so memory is freed when view is released
        Py_DECREF(contiguous)
    buffer_len[0] = view.len
    buf[0] = <char*> view.buf
    return 1


def unpackb(object packed, *, object unpack_ctrl=None):
    """
    Unpack packed_bytes to object. Returns an unpacked object.

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``ValueError`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid tmsgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.

    See :class:`Unpacker` for options.

    *max_xxx_len* options are configured automatically from ``len(packed)``.
    """
    cdef unpack_context ctx
    cdef Py_ssize_t off = 0
    cdef int ret

    cdef Py_buffer view
    cdef char* buf = NULL
    cdef Py_ssize_t buf_len
    cdef const char* cerr = NULL

    if unpack_ctrl is None:
        raise(ValueError("No unpack_ctrl supplied."))

    cdef from_dict = unpack_ctrl.from_dict
    cdef from_list = unpack_ctrl.from_list

    o = unpack_ctrl.options
    if o.unicode_errors is not None:
        cerr = o.unicode_errors

    get_data_from_buffer(packed, &view, &buf, &buf_len)

    try:
        init_ctx(&ctx, from_dict, from_list, o.object_as_pairs,
                 o.use_tuple, o.raw, o.strict_dict_key, cerr,
                 min(buf_len, o.max_str_len),
                 min(buf_len, o.max_bin_len),
                 min(buf_len, o.max_list_len),
                 min(buf_len, o.max_dict_len))
        ret = unpack_construct(&ctx, buf, buf_len, &off)
    finally:
        PyBuffer_Release(&view);

    if ret == 1:
        obj = unpack_data(&ctx)
        if off < buf_len:
            raise ExtraData(obj, PyBytes_FromStringAndSize(buf+off, buf_len-off))
        return obj
    unpack_clear(&ctx)
    if ret == 0:
        raise ValueError("Unpack failed: incomplete input")
    elif ret == -2:
        raise FormatError
    elif ret == -3:
        raise StackError
    raise ValueError("Unpack failed: error = %d" % (ret,))


cdef class Unpacker(object):
    """Streaming tmsgpack unpacker.

    Arguments:

    :param file_like:
        File-like object having `.read(n)` method.
        If specified, unpacker reads serialized data from it and :meth:`feed()` is not usable.

    :param unpack_ctrl:
        Unpack control context.

    :param buffer_size:
        Set the buffer_size directly.

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
    cdef unpack_context ctx
    cdef char* buf
    cdef Py_ssize_t buf_size, buf_head, buf_tail
    cdef object file_like
    cdef object file_like_read
    cdef Py_ssize_t read_size
    # To maintain refcnt.
    cdef object from_dict
    cdef object from_list
    cdef bint object_as_pairs
    cdef object unicode_errors
    cdef Py_ssize_t max_buffer_size
    cdef uint64_t stream_offset

    def __cinit__(self):
        self.buf = NULL

    def __dealloc__(self):
        PyMem_Free(self.buf)
        self.buf = NULL

    def __init__(
        self, file_like=None, *, object unpack_ctrl=None, Py_ssize_t buffer_size=0,
    ):
        cdef const char *cerr=NULL

        if unpack_ctrl is None:
           raise(ValueError("No unpack_ctrl supplied."))

        self.from_dict = unpack_ctrl.from_dict
        self.from_list = unpack_ctrl.from_list

        self.file_like = file_like
        if file_like:
            self.file_like_read = file_like.read
            if not PyCallable_Check(self.file_like_read):
                raise TypeError("`file_like.read` must be a callable.")

        o = unpack_ctrl.options
        if buffer_size == 0:
            self.max_buffer_size = <Py_ssize_t>o.max_buffer_size
            self.read_size       = <Py_ssize_t>o.read_size
        else:
            self.max_buffer_size = self.read_size = <Py_ssize_t>buffer_size

        self.buf = <char*>PyMem_Malloc(self.read_size)
        if self.buf == NULL:
            raise MemoryError("Unable to allocate internal buffer.")
        self.buf_size = <Py_ssize_t>o.read_size
        self.buf_head = 0
        self.buf_tail = 0
        self.stream_offset = 0

        if o.unicode_errors is not None:
            cerr = self.unicode_errors = o.unicode_errors

        init_ctx(&self.ctx,
                 self.from_dict, self.from_list,
                 o.object_as_pairs,
                 o.use_tuple, o.raw, o.strict_dict_key, <const char*>cerr,
                 o.max_str_len, o.max_bin_len, o.max_list_len, o.max_dict_len)

    def feed(self, object next_bytes):
        """Append `next_bytes` to internal buffer."""
        cdef Py_buffer pybuff
        cdef char* buf
        cdef Py_ssize_t buf_len

        if self.file_like is not None:
            raise AssertionError(
                    "unpacker.feed() is not be able to use with `file_like`.")

        get_data_from_buffer(next_bytes, &pybuff, &buf, &buf_len)
        try:
            self.append_buffer(buf, buf_len)
        finally:
            PyBuffer_Release(&pybuff)

    cdef append_buffer(self, void* _buf, Py_ssize_t _buf_len):
        cdef:
            char* buf = self.buf
            char* new_buf
            Py_ssize_t head = self.buf_head
            Py_ssize_t tail = self.buf_tail
            Py_ssize_t buf_size = self.buf_size
            Py_ssize_t new_size

        if tail + _buf_len > buf_size:
            if ((tail - head) + _buf_len) <= buf_size:
                # move to front.
                memmove(buf, buf + head, tail - head)
                tail -= head
                head = 0
            else:
                # expand buffer.
                new_size = (tail-head) + _buf_len
                if new_size > self.max_buffer_size:
                    raise BufferFull
                new_size = min(new_size*2, self.max_buffer_size)
                new_buf = <char*>PyMem_Malloc(new_size)
                if new_buf == NULL:
                    # self.buf still holds old buffer and will be freed during
                    # obj destruction
                    raise MemoryError("Unable to enlarge internal buffer.")
                memcpy(new_buf, buf + head, tail - head)
                PyMem_Free(buf)

                buf = new_buf
                buf_size = new_size
                tail -= head
                head = 0

        memcpy(buf + tail, <char*>(_buf), _buf_len)
        self.buf = buf
        self.buf_head = head
        self.buf_size = buf_size
        self.buf_tail = tail + _buf_len

    cdef int read_from_file(self) except -1:
        cdef Py_ssize_t remains = self.max_buffer_size - (self.buf_tail - self.buf_head)
        if remains <= 0:
            raise BufferFull

        next_bytes = self.file_like_read(min(self.read_size, remains))
        if next_bytes:
            self.append_buffer(PyBytes_AsString(next_bytes), PyBytes_Size(next_bytes))
        else:
            self.file_like = None
        return 0

    cdef object _unpack(self, bint iter=0):
        cdef int ret
        cdef object obj
        cdef Py_ssize_t prev_head

        while 1:
            prev_head = self.buf_head
            if prev_head < self.buf_tail:
                ret = unpack_construct(&self.ctx, self.buf, self.buf_tail, &self.buf_head)
                self.stream_offset += self.buf_head - prev_head
            else:
                ret = 0

            if ret == 1:
                obj = unpack_data(&self.ctx)
                unpack_init(&self.ctx)
                return obj
            elif ret == 0:
                if self.file_like is not None:
                    self.read_from_file()
                    continue
                if iter:
                    raise StopIteration("No more data to unpack.")
                else:
                    raise OutOfData("No more data to unpack.")
            elif ret == -2:
                raise FormatError
            elif ret == -3:
                raise StackError
            else:
                raise ValueError("Unpack failed: error = %d" % (ret,))

    def read_bytes(self, Py_ssize_t nbytes):
        """Read a specified number of raw bytes from the stream"""
        cdef Py_ssize_t nread
        nread = min(self.buf_tail - self.buf_head, nbytes)
        ret = PyBytes_FromStringAndSize(self.buf + self.buf_head, nread)
        self.buf_head += nread
        if nread < nbytes and self.file_like is not None:
            ret += self.file_like.read(nbytes - nread)
            nread = len(ret)
        self.stream_offset += nread
        return ret

    def unpack(self):
        """Unpack one object

        Raises `OutOfData` when there are no more bytes to unpack.
        """
        return self._unpack()

    def tell(self):
        """Returns the current position of the Unpacker in bytes, i.e., the
        number of bytes that were read from the input, also the starting
        position of the next object.
        """
        return self.stream_offset

    def __iter__(self):
        return self

    def __next__(self):
        return self._unpack(1)

    # for debug.
    #def _buf(self):
    #    return PyString_FromStringAndSize(self.buf, self.buf_tail)

    #def _off(self):
    #    return self.buf_head
