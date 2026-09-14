# ---- build stage --------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Copied ALONE, before the source code. This layer is cached and only
# rebuilt when requirements.txt changes -- editing main.py will not
# reinstall every dependency. Reorder these two COPY lines and every build
# takes a minute instead of two seconds.
COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ---- runtime stage ------------------------------------------------------
# A separate stage: build tools and pip caches stay behind. ~150 MB instead
# of ~1 GB, which means faster CI pulls and a smaller CVE surface.
FROM python:3.12-slim

# Non-root. Docker has no user namespace by default, so UID 0 in the
# container is UID 0 on the host kernel: a container escape would cost you
# the machine. UID 1000 lands as a nobody.
RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=appuser:appuser app/ ./app/

USER appuser
EXPOSE 5000

# No curl in slim images, so probe with the Python already present.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health').status==200 else 1)"

# --host 0.0.0.0 is MANDATORY. Bound to 127.0.0.1 the app only accepts
# connections from inside its own container and the port mapping silently
# does nothing.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
