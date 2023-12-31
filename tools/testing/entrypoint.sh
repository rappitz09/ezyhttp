#!/bin/bash

[[ "$ezyhttp_NO_EXTENSIONS" != "y" ]] && make cythonize

python -m pytest -qx --no-cov $1
