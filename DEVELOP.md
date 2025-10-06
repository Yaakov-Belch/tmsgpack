## JavaScript

```bash
# git clone git@github.com:Yaakov-Belch/tmsgpack.git # You need permissions.
git clone https://github.com/Yaakov-Belch/tmsgpack.git

cd tmsgpack/JavaScript

# 1. Install and test
npm install
npm test

# 2. Log into npm
npm login
npm whoami

# 3. Dry run to verify package contents
# npm pack                # Creates tarball. No npm login needed
npm publish --dry-run     # Checks publication readiness.

# 4. Publish when ready
npm publish
```

## Python

```bash
# git clone git@github.com:Yaakov-Belch/tmsgpack.git # You need permissions.
git clone https://github.com/Yaakov-Belch/tmsgpack.git

cd tmsgpack/Python

# Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate

# Install tools
pip install --upgrade pip
pip install setuptools Cython build twine

# Run tests -- this compiles sources and fetches __version__ from ../JavaScript
./test-cython-run.sh

rm -rf dist/     # remove old builds
python -m build  # puts results in dist/

cat MANIFEST.in
unzip -l dist/tmsgpack-*.whl

# Register at pypi.org if you haven't
# Connecting to upload.pypi.org
# twine upload dist/*  # This does not work: Platform incompatible.
twine upload dist/tmsgpack-*.tar.gz


# Test in a separate virtual environment
deactivate
rm -rf   ~/test-tmsgpack
mkdir -p ~/test-tmsgpack
cd       ~/test-tmsgpack
python -m venv venv-test
source venv-test/bin/activate
pip install --upgrade pip
pip install tmsgpack
python -c "import tmsgpack; print('Version:', tmsgpack.__version__)"
```

