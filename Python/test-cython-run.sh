#!/bin/bash
echo "Building and testing..."

python setup.py build_ext --inplace && python test-cython.py
