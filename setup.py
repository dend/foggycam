from distutils.core import setup
from subprocess import Popen, PIPE
import sys

process = Popen("git describe --tag".split(), stderr=PIPE, stdout=PIPE)
out, err = process.communicate()
version = out.decode()
setup (name = "foggycam",
       author="dend",
       version=version,
       description = "Utilities for NEST cam",
       url = "https://github.com/dend/foggycam",
       packages = ['foggycam'],
       package_dir = {'foggycam': 'src'},
       scripts=["scripts/foggycam"]
      )
    
