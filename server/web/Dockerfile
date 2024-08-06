FROM python:3.12-slim-bookworm AS build

COPY . .

RUN pip install uv && uv venv --seed
RUN uv pip install -r requirements.lock

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=build /.venv .venv
COPY . .

RUN chmod +x /app/etc/run_scripts.sh

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000
CMD python -m uvicorn web.main:app --host 0.0.0.0 --port 5000 --workers 4