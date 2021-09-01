# based on https://github.com/pypa/sampleproject/blob/master/setup.py
# see http://packaging.python.org/en/latest/tutorial.html#creating-your-own-project

from setuptools import setup, find_packages
from  setuptools.command.install import install  as  stdinstall
import codecs
import os
import re
import sys


def find_version(*file_paths):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, *file_paths), 'r', 'latin1') as f:
        version_file = f.read()
    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def get_file_contents(filename):
    with codecs.open(filename, encoding='utf-8') as f:
        contents = f.read()
    return contents


package_name = "typecheck-decorator"


class  install_with_test(stdinstall):
     def  run(self):
         stdinstall.run(self)  # normal install
         ##pip/setuptools makes this unbuffering unhelpful:
         #sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1) # make line-buffered
         #sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1) # make line-buffered
         #import typecheck.test_typecheck_decorator  # execute post-install test (during beta only)


setup(
    # setup customization:
    cmdclass={'install': install_with_test},

    # basic information:
    name=package_name,
    version=find_version('typecheck', '__init__.py'),
    description="flexible explicit run-time type checking of function arguments (Python3-only)",
    long_description=get_file_contents("README.rst"),

    # The project URL:
    url='http://github.com/prechelt/' + package_name,

    # Author details:
    author='Dmitry Dvoinikov, Lutz Prechelt',
    author_email='prechelt@inf.fu-berlin.de',

    # Classification:
    license='BSD License',
    classifiers=[
        'License :: OSI Approved :: BSD License',

        # How mature is this project? Common values are
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Documentation',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='type-checking',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages.
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),

    # List run-time dependencies here. These will be installed by pip when your
    # project is installed.
    install_requires = ['typing;python_version<"3.5"'],

    # If there are data files included in your packages that need to be
    # installed, specify them here. If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        # 'typecheck': ['package_data.dat'],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages.
    # see http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    ###data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    ### entry_points={
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
)