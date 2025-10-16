## Clone, test and publish

```bash
# git clone git@github.com:Yaakov-Belch/tmsgpack.git # You need permissions.
git clone https://github.com/Yaakov-Belch/tmsgpack.git

cd tmsgpack/

# Do this only once -- after cloning:
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install setuptools Cython build twine

# Tests:
(cd JavaScript; npm install; npm test)
./Python/test-run.sh  # This is needed to update the version number.

# Publish:
git commit -a
git tag v0.1.2  # use the correct version number
git push
git push --tags
```

# Test in a separate virtual environment
```bash
rm -rf   ~/test-tmsgpack
mkdir -p ~/test-tmsgpack
cd       ~/test-tmsgpack
python -m venv venv-test
source venv-test/bin/activate
pip install --upgrade pip
pip install tmsgpack
python -c "import tmsgpack; print('Version:', tmsgpack.__version__)"
```


