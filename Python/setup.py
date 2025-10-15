from setuptools import setup, find_packages
from Cython.Build import cythonize
import glob

# Automatically find all .pyx files in src/
pyx_files = glob.glob("tmsgpack/*.pyx")

print("Found packages:", find_packages())


setup(
    name="tmsgpack",
    packages=find_packages(),
    ext_modules=cythonize(
        pyx_files,
        compiler_directives={
            'language_level': 3,
            'boundscheck': True,
            'wraparound': False,
            'cdivision': True,
        }
    )
)
