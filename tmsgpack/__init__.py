from .exceptions import *
import os
import sys


version = (0, 0, 1)
__version__ = "0.1.0"


class PackConfig:
    """
    Config object for pack_ctrl.options

    :param bool use_single_float:
        Use single precision float type for float. (default: False)

    :param bool use_bin_type:
        Use bin type introduced in tmsgpack spec 2.0 for bytes.
        It also enables str8 type for unicode. (default: True)

    :param bool tuple_as_list:
        If true, tuples are serialized as lists.  (default: True)
        Otherwise, tuples are passed to pack_ctrl.from_obj(?).

    :param bool strict_types:
        If set to true, types will be checked to be exact. (default: False)
        Derived classes are distinct and passed to pack_ctrl.from_obj(?).
        Dicts, lists and tuples are not affected by strict_types.

    :param str unicode_errors:
        The error handler for encoding unicode. (default: 'strict')
        DO NOT USE THIS!!  This option is kept for very specific usage.

    :param bool sort_keys:
        Sort output dictionaries by key. (default: False)
    """

    def __init__(self, use_single_float=False, use_bin_type=True,
                 tuple_as_list=True, strict_types=False,
                 unicode_errors='strict', sort_keys=False):
        self.use_single_float = use_single_float
        self.tuple_as_list    = tuple_as_list
        self.use_bin_type     = use_bin_type
        self.strict_types     = strict_types
        self.unicode_errors   = unicode_errors
        self.sort_keys        = sort_keys

class UnpackConfig:
    """
    Config object for unpack_ctrl.options

    :param int read_size:
        Used as `file_like.read(read_size)`. (default: `min(16*1024, max_buffer_size)`)

    :param bool use_tuple:
        If true, unpack a tmsgpack list as a Python tuple. (default: False)

    :param bool raw:
        If true, unpack tmsgpack strings (raw) to Python bytes.
        Otherwise, unpack to Python str by decoding with UTF-8 encoding (default: False).

    :param bool strict_dict_key:
        If true only str or bytes are accepted for dict (dict) keys. (default: False).

    :param callable object_as_pairs:
        If true, handles dicts as tuples of pairs.
        Otherwise, as dicts (default: False).

    :param str unicode_errors:
        The error handler for decoding unicode. (default: 'strict')
        This option should be used only when you have tmsgpack data which
        contains invalid UTF-8 string.

    :param int max_buffer_size:
        Limits size of data waiting unpacked.  0 means 2**32-1.
        The default value is 100*1024*1024 (100MiB).
        Raises `BufferFull` exception when it is insufficient.
        You should set this parameter when unpacking data from untrusted source.

    :param int max_str_len:
        Limits max length of str. (default: max_buffer_size)

    :param int max_bin_len:
        Limits max length of bin. (default: max_buffer_size)

    :param int max_list_len:
        Limits max length of list.
        (default: max_buffer_size)

    :param int max_dict_len:
        Limits max length of dict.
        (default: max_buffer_size//2)
    """

    def __init__(self, read_size=16*1024, use_tuple=False, raw=False,
                 strict_dict_key=False, object_as_pairs=False,
                 unicode_errors='strict', max_buffer_size=0,
                 max_str_len=-1, max_bin_len=-1, max_list_len=-1, max_dict_len=-1):
        if max_buffer_size == 0: max_buffer_size = 2**32-1
        self.max_buffer_size = max_buffer_size
        self.read_size       = min(read_size, max_buffer_size)

        if max_str_len == -1:  max_str_len  = max_buffer_size
        if max_bin_len == -1:  max_bin_len  = max_buffer_size
        if max_list_len == -1: max_list_len = max_buffer_size
        if max_dict_len == -1: max_dict_len  = max_buffer_size//2

        self.max_str_len  = max_str_len
        self.max_bin_len  = max_bin_len
        self.max_list_len = max_list_len
        self.max_dict_len = max_dict_len

        self.use_tuple       = use_tuple
        self.raw             = raw
        self.strict_dict_key = strict_dict_key
        self.object_as_pairs = object_as_pairs
        self.unicode_errors  = unicode_errors

if os.environ.get("TMSGPACK_PUREPYTHON"):
    from .fallback import Packer, unpackb, Unpacker
else:
    try:
        from ._ctmsgpack import Packer, unpackb, Unpacker
    except ImportError:
        from .fallback import Packer, unpackb, Unpacker


def pack(o, stream, pack_ctrl):
    """
    Pack object `o` and write it to `stream`

    See :class:`Packer` for options.
    """
    packer = Packer(pack_ctrl=pack_ctrl)
    stream.write(packer.pack(o))


def packb(o, pack_ctrl):
    """
    Pack object `o` and return packed bytes

    See :class:`Packer` for options.
    """
    return Packer(pack_ctrl=pack_ctrl).pack(o)


def unpack(stream, unpack_ctrl):
    """
    Unpack an object from `stream`.

    Raises `ExtraData` when `stream` contains extra bytes.
    See :class:`Unpacker` for options.
    """
    data = stream.read()
    return unpackb(data, unpack_ctrl=unpack_ctrl)


