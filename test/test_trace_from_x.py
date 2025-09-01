from contexts_for_tests import pctrl, uctrl
from tmsgpack import packb, unpackb, PackConfig, UnpackConfig
from pytest import raises
from dataclasses import dataclass, is_dataclass, fields

@dataclass
class PackTracer:
    def from_obj(self, obj):
        if type(obj) is tuple: return [False, 'tuple', obj]
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

@dataclass
class UnpackTracer:
    def from_dict(self, ctype, dct): return ['dict', ctype, dct]
    def from_list(self, ctype, lst): return ['list', ctype, lst]
    options: UnpackConfig


def pt(**kwargs): return PackTracer(options=PackConfig(**kwargs))
def ut(**kwargs): return UnpackTracer(options=UnpackConfig(**kwargs))

def run(
        input, expected,
        tuple_as_list=True, sort_keys=False,
        use_tuple=False, strict_dict_key=False, object_as_pairs=False,
):
    packed = packb(input, pack_ctrl=pt(tuple_as_list=tuple_as_list, sort_keys=sort_keys))
    output = unpackb(packed, unpack_ctrl=ut(
        use_tuple=use_tuple, strict_dict_key=strict_dict_key,
        object_as_pairs=object_as_pairs,
    ))
    assert output == expected


@dataclass
class Foo:
    y: str = 'Y'
    x: int = 1

@dataclass
class Bar:
    y: str = 'Y'
    x: int = 1
    as_list = True

@dataclass
class FooBar:
    y: str = 'Y'
    x: int = 1
    as_list: bool = False

def test_trace_tuples():
    run([1,2,3], [1,2,3])
    run((1,2,3), [1,2,3])
    run([1,2,3], (1,2,3), use_tuple=True)
    run([1,2,3], [1,2,3], tuple_as_list=False)
    run((1,2,3), ['list', 'tuple', [1, 2, 3]], tuple_as_list=False)
    run((1,2,3), ['list', 'tuple', (1, 2, 3)], tuple_as_list=False, use_tuple=True)

def test_trace_dicts():
    # Strangely: Even with sort_keys=False, dicts are unpacked sorted?
    run({3:1, 2:2, 1:3}, {1: 3, 2: 2, 3: 1},      sort_keys=False)
    run({'z':'a', 'a':'z'}, {'a': 'z', 'z': 'a'}, sort_keys=False)

    # Here, the order of dicts is preserved when they are not sortable:
    run({1:1, 'a':'a'}, {1:1, 'a':'a'})
    run({'a':'a', 1:1}, {'a':'a', 1:1},)

def test_trace_obj():
    # dataclass fields are sorted automatically -- as above!:
    run(Foo(), ['dict', 'Foo', {'x': 1, 'y': 'Y'}], sort_keys=False)
    run(Bar(), ['list', 'Bar', ['Y', 1]])
    run(FooBar(as_list=0), ['dict', 'FooBar', {'as_list': 0, 'x': 1, 'y': 'Y'}])
    run(FooBar(as_list=1), ['list', 'FooBar', ['Y', 1, 1]])

def test_object_as_pairs():
    run([1,2,3], [1,2,3],                                     object_as_pairs=True)
    run({'a':'a', 1:1}, ['dict', None, (('a', 'a'), (1, 1))], object_as_pairs=True)
    run(Foo(), ['dict', 'Foo', (('y', 'Y'), ('x', 1))],       object_as_pairs=True)
    run(Bar(), ['list', 'Bar', ['Y', 1]],                     object_as_pairs=True)

