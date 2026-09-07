FROM python:3.12-slim

# uv drives dependency resolution and the runtime venv; installed via pip so
# we don't depend on an external image's COPY --from layer.
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy the package source before syncing: hatchling builds the local `hrag`
# wheel as part of `uv sync`, so pyproject.toml + uv.lock alone are not
# enough to resolve the project itself.
COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --no-dev --extra gcp

RUN useradd --create-home --uid 10001 hrag \
    && chown -R hrag:hrag /app
USER hrag

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "hrag.api:app", "--host", "0.0.0.0", "--port", "8080"]
