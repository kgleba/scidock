FROM python:3.12-slim-bookworm AS build

RUN apt update && apt install -y git wget

RUN pip install uv && uv venv --seed
RUN uv pip install spacy flask git+https://github.com/kgleba/KeyBERT

RUN mkdir -p all-MiniLM-L6-v2 && \
    wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx -O all-MiniLM-L6-v2/model.onnx && \
    wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/tokenizer.json -O all-MiniLM-L6-v2/tokenizer.json

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=build /.venv .venv
COPY --from=build /all-MiniLM-L6-v2 all-MiniLM-L6-v2
COPY tiny .

ENV PATH="/app/.venv/bin:$PATH"
RUN python -m spacy download en_core_web_sm && rm -rf /root/.cache/pip

EXPOSE 7234
CMD python main.py