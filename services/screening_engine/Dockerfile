FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /srv

# Dependencies first, so editing code does not re-resolve them on rebuild.
COPY pyproject.toml /srv/
RUN uv pip install --system --no-cache -r pyproject.toml

# The package is not pip-installed, it is copied in. uvicorn happens to add
# the working directory itself, but celery and a bare `python -c` do not,
# so make it explicit rather than depend on one tool's convenience.
ENV PYTHONPATH=/srv \
    PYTHONUNBUFFERED=1

COPY alembic.ini /srv/
COPY app /srv/app
COPY screening /srv/screening

# Quarantined uploads. A volume in compose; created here so the image also
# runs standalone.
RUN useradd --system --uid 10001 --create-home screening \
    && mkdir -p /var/lib/screening/quarantine \
    && chown -R screening:screening /var/lib/screening

# This process handles candidate files from outside the company. It has no
# reason to be root.
USER screening

EXPOSE 8000

# One image, two roles. The worker overrides this command in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
