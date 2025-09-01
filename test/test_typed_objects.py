from tmsgpack import packb, unpackb, PackConfig, UnpackConfig
from dataclasses import dataclass, is_dataclass, fields
from typing import Dict

@dataclass
class TypedPackCtrl:
    def from_obj(self, obj):
        if type(obj) is tuple: return False, 'tuple', obj  # Special case for tuples.
        if not is_dataclass(obj): raise TypeError(f'Cannot serialize {type(obj)} object.')
        as_dict = not getattr(obj, 'as_list', False)
        object_type = obj.__class__.__name__
        if as_dict:
            data = {
                field.name: getattr(obj, field.name)
                for field in fields(obj)
            }
        else:
            data = [
                getattr(obj, field.name)
                for field in fields(obj)
            ]
        return as_dict, object_type, data
    options: PackConfig

    def pack(self, data):
        return packb(data, pack_ctrl=self)

@dataclass
class TypedUnpackCtrl:
    constructors: Dict[str, callable]
    def from_dict(self, ctype, data): return self.constructors[ctype](**data)
    def from_list(self, ctype, data): return self.constructors[ctype]( *data)
    options: UnpackConfig

    def unpack(self, packed):
        return unpackb(packed, unpack_ctrl=self)

def pc(**kwargs): return TypedPackCtrl(options=PackConfig(**kwargs))
def uc(fns, **kwargs):
    return TypedUnpackCtrl(
        constructors={fn.__name__:fn for fn in fns},
        options=UnpackConfig(**kwargs),
    )

@dataclass
class Foo:
    x: int = 1
    y: str = 'Y'

@dataclass
class Bar:
    x: int = 1
    y: str = 'Y'
    as_list = True

@dataclass
class Add:
    x: int = 10
    y: int = 20

class Expr:
    @staticmethod
    def Add(x:int, y:int): return x+y
    @staticmethod
    def tuple(*args): return args

def run(input, expected=None):
    if expected is None: expected = input

    constructors = [Foo, Bar, Expr.tuple, Expr.Add]

    pack_ctrl = pc(tuple_as_list=False) # We want to distinguish between tuples and lists.
    unpack_ctrl = uc(constructors)

    packed = pack_ctrl.pack(input)
    output = unpack_ctrl.unpack(packed)

    assert output == expected

def test_typed_foobar():
    run(Foo())  # Encoded as a typed dict
    run(Bar())  # Encoded as a typed list
    run((1,2,3)) # Tuples are encoded as a typed list with object_type='tuple'

def test_simple_expression():
    run(Add(Add(1,2), Add(2,3)), 8) # Unpacking is expression evaluation.

