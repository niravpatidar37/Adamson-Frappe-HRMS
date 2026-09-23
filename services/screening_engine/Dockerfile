FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml /app/
RUN uv sync --no-dev --no-install-project

COPY app /app/app
COPY screening /app/screening
RUN uv sync --no-dev

EXPOSE 8000

# One image, two roles. The worker overrides this command in compose.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
