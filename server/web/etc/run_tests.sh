#!/bin/bash

# use for testing inside a merged Dockerfile
# echo '127.0.0.1 nlp' >> /etc/hosts

python -m pip install -r /app/requirements-dev.lock

python -m pytest --cov --cov-report json
