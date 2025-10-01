"""tmsgpack - Typed MessagePack serializer"""

####################### Keep version in sync with setup.cfg #######################
__version__ = '0.2.0'                                                             #
###################################################################################

__all__ = [
    'EncodeDecode', 'basic_codec', 'BasicCodec',
    'EncodeBuffer', 'DecodeBuffer',
    'ebuf_put_value', 'dbuf_take_value',
]

def __getattr__(name):
    if name in __all__:
        from .cython.tmsgpack import EncodeBuffer, DecodeBuffer
        from .cython.tmsgpack import ebuf_put_value, dbuf_take_value
        from .cython.api      import EncodeDecode, BasicCodec, basic_codec
        return locals()[name]
    elif name == 'pure_python':
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

