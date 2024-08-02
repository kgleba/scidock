FROM python:3.12-slim-bookworm

WORKDIR /app
COPY . .

RUN pip install uv && uv venv --seed
RUN uv pip install .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000
CMD uvicorn web.main:app --host 0.0.0.0 --port 5000 --workers 4