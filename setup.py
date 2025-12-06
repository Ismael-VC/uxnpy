from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
import subprocess
import sys
import os
import shutil

class BuildPyWithLib(build_py):
    def run(self):
        print("Building C library with make...")
        result = subprocess.run(['make', 'all'], check=False)
        if result.returncode != 0:
            print("Warning: make failed, library may not be available")

        build_py.run(self)

        lib_name = self._get_lib_name()
        src_lib = os.path.join('build', lib_name)

        if os.path.exists(src_lib):
            if self.build_lib:
                dest_dir = os.path.join(self.build_lib, 'uxn')
                os.makedirs(dest_dir, exist_ok=True)
                dest_lib = os.path.join(dest_dir, lib_name)
                shutil.copy2(src_lib, dest_lib)
                print(f"Copied {src_lib} to {dest_lib}")

    @staticmethod
    def _get_lib_name():
        import platform
        system = platform.system()
        if system == "Linux":
            return "libuxn.so"
        elif system == "Darwin":
            return "libuxn.dylib"
        elif system == "Windows":
            return "uxn.dll"
        return "libuxn.so"

class EggInfo(egg_info):
    def initialize_options(self):
        egg_info.initialize_options(self)
        self.egg_base = 'build'

try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'Python wrapper for Uxn Virtual Machine'

setup(
    name='uxn',
    version='0.1.0',
    author='Ismael Venegas Castelló',
    author_email='ismael.vc13337@gmail.com',
    description='Python wrapper for Uxn Virtual Machine',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Ismael-VC/uxnpy',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={
        'uxn': ['*.so', '*.dylib', '*.dll'],
    },
    cmdclass={
        'build_py': BuildPyWithLib,
        'egg_info': EggInfo,
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: C',
    ],
    python_requires='>=3.7',
    install_requires=[],
    zip_safe=False,
)
