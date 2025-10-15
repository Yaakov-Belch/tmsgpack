#!/bin/bash
# `cd` into the directory of this script to find the sources.
SCRIPT_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
echo cd "$SCRIPT_DIR"; cd "$SCRIPT_DIR"

# Extract the version number from the JavaScript package:
VERSION=$(node -p "require('../JavaScript/package.json').version")
echo version: $VERSION
echo $VERSION > Automatic-Version

cat <<EOF | cat - tmsgpack/src-parts/* > tmsgpack/cython/tmsgpack.pyx
# THIS FILE IS AUTOMATICALLY CREATED BY THE test-cython-run.sh SCRIPT!
# DON'T EDIT THIS FILE.  EDIT THE SOURCES, INSTEAD: tmsgpack/src-parts/*

__version__ = "$VERSION"

EOF

echo "Building and testing..."

./venv/bin/python setup.py build_ext --inplace && python test-cython.py
