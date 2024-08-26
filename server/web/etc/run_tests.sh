#!/bin/bash

python -m pip install -r /app/requirements-dev.lock

python -m pytest --cov --cov-report lcov
