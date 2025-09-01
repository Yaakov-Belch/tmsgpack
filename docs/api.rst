API reference
=============

.. module:: tmsgpack

.. autofunction:: pack

:func:`dump` is alias for :func:`pack`

.. autofunction:: packb

:func:`dumps` is alias for :func:`packb`

.. autofunction:: unpack

:func:`load` is alias for :func:`unpack`

.. autofunction:: unpackb

:func:`loads` is alias for :func:`unpackb`

.. autoclass:: Packer
    :members:

.. autoclass:: Unpacker
    :members:

.. autoclass:: ExtType

.. autoclass:: Timestamp
    :members:
    :special-members: __init__

exceptions
----------

These exceptions are accessible via `tmsgpack` package.
(For example, `tmsgpack.OutOfData` is shortcut
for `tmsgpack.exceptions.OutOfData`)

.. automodule:: tmsgpack.exceptions
    :members:
    :undoc-members:
    :show-inheritance:
