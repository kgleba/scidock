FROM python:3.12-slim AS build

RUN pip install uv && uv venv --seed
#RUN uv pip install --no-cache-dir -r ${EDITION}.frozen-requirements.txt
RUN uv pip install torch==2.3.1+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html spacy transformers flask
RUN uv pip install keybert --no-deps
RUN uv pip install numpy>=1.18.5 rich>=10.4.0 scikit-learn>=0.22.2

FROM python:3.12-slim

WORKDIR /app
COPY --from=build /.venv .venv
COPY app .

# fixed an issue with importing `sentence-transformers` not present in this image
RUN mv updated_backend_init.py .venv/lib/python3.12/site-packages/keybert/backend/__init__.py

ENV PATH="/app/.venv/bin:$PATH"
RUN python -m spacy download en_core_web_trf && rm -rf /root/.cache/pip

EXPOSE 7234
CMD python main.py