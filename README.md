# tmsgpack: Typed MessagePack-inspired pack/unpack component

The tmsgpack format expresses **typed objects**: maps and arrays (or: dicts and lists)
with an `object_type` property.

Unlike msgpack and pickle, this is not a batteries-included end-to-end serialization
solution.  It is a composable component that helps you to build end-to-end communication
solutions.

Your system solution design will make decisions on:
* What objects are serializable and what objects are not.
* What code to use (and, maybe, dynamically load) to instantiate serialized objects.
* How to represent objects that are unpacked but not supposed to 'live' in this process.
* How to share dynamic data between different packs/unpacks.
* How to asynchronously load and integrate shared data from different sources.
* How to map typed object meaning between different programming languages.
* Whether and how to convert persisted "old" data to current, new semantics (schemas).
* How much to attach explicit meaning and predictable schemas to your object types.
* Whether or not to use the 'expression execution' capabilities of tmsgpack.
* etc.

This python package makes a minimal (backwards-incompatible) modification to the
msgpack format to make all this elegantly possible.  This package is based on
`msgpack v1.0.5`.

## TODO: Installation

## Usage
Packing and unpacking data is controlled by `pack_ctrl` and `unpack_ctrl` objects (see
below for details how to create them):
```python
from tmsgpack import packb, unpackb
packed = packb(data, pack_ctrl=pack_ctrl)
unpacked = unpackb(packed, unpack_ctrl=unpack_ctrl)
```

## Streaming unpacking
For multiple uses, you can use packer and unpacker objects:
```python
from tmsgpack import Packer
packer = Packer(pack_ctrl=pack_ctrl)

packed = packer.pack(data) # Send these packages via a socket...

---
from tmsgpack import Packer, Unpacker

unpacker = Unpacker(unpack_ctrl=unpack_ctrl)
while buf := sock.recv(1024**2):
    unpacker.feed(buf)
    for o in unpacker:
        process(o)
```

## Minimal pack_ctrl and unpack_ctrl objects
Minimal controllers allow only JSON-like objects and raise errors when you ask for more
(below, we show examples for more useful controllers):
```python
from tmsgpack import PackConfig, UnpackConfig
from dataclasses import dataclass

@dataclass
class MinimalPackCtrl:
    def from_obj(self, obj):
        raise TypeError(f'Cannot serialize {type(obj)} object.')
    options: PackConfig

@dataclass
class MinimalUnpackCtrl:
    def from_dict(self, ctype, dct):
        raise ValueError(f'Unpack type not supported: {ctype} data: {dct}')
    def from_list(self, ctype, lst):
        raise ValueError(f'Unpack type not supported: {ctype} data: {lst}')
    options: UnpackConfig

def pctrl(**kwargs): return MinimalPackCtrl(options=PackConfig(**kwargs))
def uctrl(**kwargs): return MinimalUnpackCtrl(options=UnpackConfig(**kwargs))

minimal_pack_ctrl = pctrl()
minimal_unpack_ctrl = uctrl()
```

## The API and configuration
As you see, the `pack_ctrl` object provides a method `from_obj`. The `unpack_ctrl`
object provides the methods `from_dict` and `from_array`:
```python
as_dict, data_type, data = pack_ctrl.from(obj)

# When `as_dict` is true, then `data` should be a dictionary.
# When `as_dict` is false, then `data` should be a list.

unpacked = unpack_ctrl.from_dict(data_type, data) # used when as_dict is true.
unpacked = unpack_ctrl.from_list(data_type, data) # used when as_dict is false.
```

## PackConfig configuration objects for pack_ctrl
`PackConfig` objects provide the following options:
```python
from tmsgpack import PackConfig

config = PackConfig(
    use_single_float=False, use_bin_type=True,
    tuple_as_list=True, strict_types=False,
    unicode_errors='strict', sort_keys=False,
)
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
```
## UnpackConfig configuration objects for unpack_ctrl
`UnpackConfig` objects provide the following options:
```python
from tmsgpack import UnpackConfig

config = UnpackConfig(
    read_size=16*1024, use_tuple=False, raw=False,
    strict_dict_key=False, object_as_pairs=False,
    unicode_errors='strict', max_buffer_size=0,
    max_str_len=-1, max_bin_len=-1, max_list_len=-1, max_dict_len=-1,
)
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
```
## Packing and Unpacking dataclass objects
Here are the parts of one unit test that shows end-to-end packing and unpacking
of dataclass objects:

For the setup, we import tools and define the controllers:
```python
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
```
Notes:
* For conveninence, we added methods `pack_ctrl.pack(data)` and
  `unpack_ctrl.unpack(packed)`.
* The method `pack_ctrl.from_obj` decides whether to represent the dataclass object
  as a key-value dict or as a more compact list of values.
* It extracts the properties of the `obj` and sets the values `as_dict`, `object_type`
  and `data` appropriately.
* In this implementation, object types are the unqualified class names. There is
  a possibility that one class from one package can have the same name as a different
  class from a different package.
* Fully resolving naming spaces is a deep design problem.  You need to decide what
  you mean by 'meaning'.  Here, we exploit this overloadability...
* The `unpack_ctrl` object is created with a list of available constructor functions.

Now, we can define the data classes to be packed and unpacked:
```python
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
```
Notes:
* Class Bar has a class property `as_list=True`.  It will be packed compactly as
  a parameter value list.
* The function (static method) `Expr.Add` has the same name as the class constructor
  `Add`.  We will soon exploit this...

Here is a simple test runner to be used for several tests:
```python
def run(input, expected=None):
    if expected is None: expected = input

    constructors = [Foo, Bar, Expr.tuple, Expr.Add]

    pack_ctrl = pc(tuple_as_list=False) # We want to distinguish between tuples and lists.
    unpack_ctrl = uc(constructors)

    packed = pack_ctrl.pack(input)
    output = unpack_ctrl.unpack(packed)

    assert output == expected
```

And here are the first tests. The `Foo()` and `Bar()` objects are packed and unpacked
correctly:
```python
def test_typed_foobar():
    run(Foo())  # Encoded as a typed dict
    run(Bar())  # Encoded as a typed list
    run((1,2,3)) # Tuples are encoded as a typed list with object_type='tuple'
```

The second test shows that we can encode an object tree into an
binary expression buffer.  When unpacking this expression buffer, the expression
is evaluated.
```python
def test_simple_expression():
    run(Add(Add(1,2), Add(2,3)), 8) # Unpacking is expression evaluation.
```
Variables (parameters) can be implemented using a dictionary inside the `unpack_ctrl`
object.

## Development: Environment and testing

```
# Clone the repository
cd ~/git/
# git clone https://github.com/Yaakov-Belch/tmsgpack.git  # You need permissions for that.
git clone https://github.com/Yaakov-Belch/tmsgpack.git

# Create a virtual environment in your project directory
cd ~/git/tmsgpack
python -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip (recommended)
pip install --upgrade pip

# Install the required dependencies
pip install -r requirements.txt

# Now you can run the tests
make test

# Run one test
pytest -v test/test_typed_objects.py
```

## Build, test, and publish to PyPI
Follow the steps above in "Development": Clone this repository, create and activate
a virtual environment, upgrade pip, install required dependencies; make test.
```bash
cd ~/git/tmsgpack
source venv/bin/activate

pip install build
rm -rf dist/     # remove old builds
python -m build  # puts results in dist/

# Test the new package -- in a fresh test environment:

# Create a fresh test environment
deactivate
python -m venv venv-test
source venv-test/bin/activate
pip install --upgrade pip
pip install dist/tmsgpack-*.whl  # use the latest whl built.

pip install pytest

# These tests uses the source files:
pytest -v test/
TMSGPACK_PUREPYTHON=1 pytest -v test
python -c "import tmsgpack; print(tmsgpack.__file__)"

# These tests use the installed files:
cd test
pytest -v .
TMSGPACK_PUREPYTHON=1 pytest -v .
python -c "import tmsgpack; print(tmsgpack.__file__)"
cd ..
deactivate
rm -rf venv-test
```
Upload to PyPi:
```bash
pip install twine

# Register at pypi.org if you haven't
# Connecting to upload.pypi.org
# twine upload dist/*  # This does not work: Platform incompatible.
twine upload dist/tmsgpack-*.tar.gz
```

Test in a separate virtual environment
```bash
deactivate
rm -rf   ~/test-tmsgpack
mkdir -p ~/test-tmsgpack
cd       ~/test-tmsgpack
python -m venv venv-test
source venv-test/bin/activate
pip install --upgrade pip
pip install tmsgpack pytest
python -c "import tmsgpack; print('Version:', tmsgpack.__version__)"
pytest -v ~/git/tmsgpack/test/
TMSGPACK_PUREPYTHON=1 pytest -v ~/git/tmsgpack/test/
```

## The tmsgpack format (version 0.1.0)
The msgpack format defines two types of containers: maps and arrays (dicts and lists).
They are encoded by a `container_header` that identifies the container type and the
number of key-value pairs or array-elements that follow after the `container_header`:
```
   dict_container_header(3) key1 value1 key2 value2 key3 value3
   array_container_header(3) element1 element2 element3
```
The tmsgpack format uses the same rules -- but adds an `object_type` entry right
after every `container_header`:
```
   dict_container_header(3) object_type key1 value1 key2 value2 key3 value3
   array_container_header(3) object_type element1 element2 element3
```

## Future extensibility
In msgpack, possible `ExtType` values for the first `data_header` byte declare
this data element as an msgpack extension.  The tmsgpack format does not use this
extension mechanism -- and these eight values are available for future extensions.

The value `0xC1` is never used by the original msgpack specification.  It is also
available for future extensions of the tmsgpack format.
